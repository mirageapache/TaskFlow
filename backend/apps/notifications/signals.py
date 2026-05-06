"""通知產生 Signals（Phase 2）。

監聽：
- TaskAssignee post_save (created)  → 通知被指派者 'task_assigned'
- TaskComment post_save (created)   → 通知任務 assignees（排除留言者） 'task_comment'
- Task pre_save                     → 抓舊 status_id
  Task post_save                    → 若 status 變動且非新建，通知 assignees（排除動作者） 'task_status_changed'
- WorkspaceMember post_save (created) → 通知新成員 'workspace_invite'

通用規則：
- actor 取自 thread-local（apps.users.middleware.get_current_user）
- 自我操作（actor == recipient）不發通知，避免噪音
- 重複的 ProjectStatus / WorkspaceMember Signal 不會在這裡寫稽核紀錄
  （那是 apps.workspaces.signals 的職責）
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.notifications.models import Notification
from apps.tasks.models import Task, TaskAssignee, TaskComment
from apps.users.middleware import get_current_user
from apps.workspaces.models import WorkspaceMember


# ────────────────  Task assignment ────────────────


@receiver(post_save, sender=TaskAssignee)
def notify_task_assigned(sender, instance, created, **kwargs):
    if not created:
        return
    actor = get_current_user()
    recipient = instance.user
    if actor and recipient.id == actor.id:
        return  # 自己指派自己不通知

    Notification.objects.create(
        recipient=recipient,
        notif_type=Notification.NotifType.TASK_ASSIGNED,
        title=f'你被指派了任務「{instance.task.title}」',
        body='',
        payload={'task_id': str(instance.task_id)},
    )


# ────────────────  Task comment ────────────────


@receiver(post_save, sender=TaskComment)
def notify_task_comment(sender, instance, created, **kwargs):
    if not created:
        return
    actor = instance.author
    task = instance.task

    # 通知所有 assignees（排除留言者本人；author 為 None 時不排除任何人）
    qs = TaskAssignee.objects.filter(task=task)
    if actor is not None:
        qs = qs.exclude(user_id=actor.id)
    assignee_ids = qs.values_list('user_id', flat=True)

    notifications = [
        Notification(
            recipient_id=uid,
            notif_type=Notification.NotifType.TASK_COMMENT,
            title=f'「{task.title}」有新留言',
            body=instance.content[:120],
            payload={
                'task_id': str(task.id),
                'comment_id': str(instance.id),
            },
        )
        for uid in assignee_ids
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)


# ────────────────  Task status change ────────────────


@receiver(pre_save, sender=Task)
def task_capture_old_status(sender, instance, **kwargs):
    """pre_save：抓舊 status_id 給 post_save 比對。

    與 apps.tasks.signals 的 task_capture_old_state 同模組獨立運作；不重用其
    `_activity_old` attribute 以免兩個 signal 互相覆蓋。
    """
    instance._notif_old_status_id = None
    if instance.pk is None:
        return
    try:
        old = Task.all_objects.only('status_id').get(pk=instance.pk)
    except Task.DoesNotExist:
        return
    instance._notif_old_status_id = old.status_id


@receiver(post_save, sender=Task)
def notify_task_status_changed(sender, instance, created, **kwargs):
    if created:
        return
    old_status_id = getattr(instance, '_notif_old_status_id', None)
    if old_status_id == instance.status_id:
        return  # 沒換 status 就不通知

    actor = get_current_user()
    actor_id = actor.id if actor else None

    assignee_ids = TaskAssignee.objects.filter(task=instance).exclude(
        user_id=actor_id,
    ).values_list('user_id', flat=True) if actor_id else \
        TaskAssignee.objects.filter(task=instance).values_list('user_id', flat=True)

    notifications = [
        Notification(
            recipient_id=uid,
            notif_type=Notification.NotifType.TASK_STATUS_CHANGED,
            title=f'「{instance.title}」狀態已變更',
            body='',
            payload={
                'task_id': str(instance.id),
                'old_status_id': str(old_status_id) if old_status_id else None,
                'new_status_id': str(instance.status_id) if instance.status_id else None,
            },
        )
        for uid in assignee_ids
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)


# ────────────────  Workspace invite ────────────────


@receiver(post_save, sender=WorkspaceMember)
def notify_workspace_invite(sender, instance, created, **kwargs):
    if not created:
        return
    actor = get_current_user()
    recipient = instance.user
    if actor and recipient.id == actor.id:
        return

    Notification.objects.create(
        recipient=recipient,
        notif_type=Notification.NotifType.WORKSPACE_INVITE,
        title=f'你被邀請加入工作區「{instance.workspace.name}」',
        body='',
        payload={'workspace_id': str(instance.workspace_id)},
    )
