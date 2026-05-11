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
- 通知建立委派給 Celery task 非同步執行（apps.notifications.tasks），
  避免在 HTTP request 中阻塞。Celery eager 模式下仍為同步。
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.notifications.tasks import (
    create_task_assigned_notification,
    create_task_comment_notifications,
    create_task_status_changed_notifications,
    create_workspace_invite_notification,
)
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

    create_task_assigned_notification.delay(
        recipient_id=str(recipient.id),
        task_id=str(instance.task_id),
        task_title=instance.task.title,
    )


# ────────────────  Task comment ────────────────


@receiver(post_save, sender=TaskComment)
def notify_task_comment(sender, instance, created, **kwargs):
    if not created:
        return

    create_task_comment_notifications.delay(
        task_id=str(instance.task_id),
        task_title=instance.task.title,
        comment_id=str(instance.id),
        comment_preview=instance.content[:120],
        exclude_user_id=str(instance.author_id) if instance.author_id else None,
    )


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
    actor_id = str(actor.id) if actor else None

    create_task_status_changed_notifications.delay(
        task_id=str(instance.id),
        task_title=instance.title,
        old_status_id=str(old_status_id) if old_status_id else None,
        new_status_id=str(instance.status_id) if instance.status_id else None,
        exclude_user_id=actor_id,
    )


# ────────────────  Workspace invite ────────────────


@receiver(post_save, sender=WorkspaceMember)
def notify_workspace_invite(sender, instance, created, **kwargs):
    if not created:
        return
    actor = get_current_user()
    recipient = instance.user
    if actor and recipient.id == actor.id:
        return

    create_workspace_invite_notification.delay(
        recipient_id=str(recipient.id),
        workspace_id=str(instance.workspace_id),
        workspace_name=instance.workspace.name,
    )

