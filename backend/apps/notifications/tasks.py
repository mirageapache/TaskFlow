"""Celery tasks for the notifications app.

Signal handler 改為呼叫這些 async task，將通知建立移到背景執行，
避免在 HTTP request 中阻塞。

每個 task 接收純量參數（UUID string / dict），不傳 Django model instance，
確保可正確 JSON 序列化。
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def create_task_assigned_notification(
    recipient_id: str,
    task_id: str,
    task_title: str,
):
    """任務被指派時，通知被指派者。"""
    from apps.notifications.models import Notification

    Notification.objects.create(
        recipient_id=recipient_id,
        notif_type=Notification.NotifType.TASK_ASSIGNED,
        title=f'你被指派了任務「{task_title}」',
        body='',
        payload={'task_id': task_id},
    )


@shared_task
def create_task_comment_notifications(
    task_id: str,
    task_title: str,
    comment_id: str,
    comment_preview: str,
    exclude_user_id: str | None,
):
    """任務有新留言時，通知所有 assignees（排除留言者）。"""
    from apps.notifications.models import Notification
    from apps.tasks.models import TaskAssignee

    qs = TaskAssignee.objects.filter(task_id=task_id)
    if exclude_user_id:
        qs = qs.exclude(user_id=exclude_user_id)
    assignee_ids = list(qs.values_list('user_id', flat=True))

    if not assignee_ids:
        return

    notifications = [
        Notification(
            recipient_id=uid,
            notif_type=Notification.NotifType.TASK_COMMENT,
            title=f'「{task_title}」有新留言',
            body=comment_preview,
            payload={
                'task_id': task_id,
                'comment_id': comment_id,
            },
        )
        for uid in assignee_ids
    ]
    Notification.objects.bulk_create(notifications)


@shared_task
def create_task_status_changed_notifications(
    task_id: str,
    task_title: str,
    old_status_id: str | None,
    new_status_id: str | None,
    exclude_user_id: str | None,
):
    """任務狀態變更時，通知 assignees（排除操作者）。"""
    from apps.notifications.models import Notification
    from apps.tasks.models import TaskAssignee

    qs = TaskAssignee.objects.filter(task_id=task_id)
    if exclude_user_id:
        qs = qs.exclude(user_id=exclude_user_id)
    assignee_ids = list(qs.values_list('user_id', flat=True))

    if not assignee_ids:
        return

    notifications = [
        Notification(
            recipient_id=uid,
            notif_type=Notification.NotifType.TASK_STATUS_CHANGED,
            title=f'「{task_title}」狀態已變更',
            body='',
            payload={
                'task_id': task_id,
                'old_status_id': old_status_id,
                'new_status_id': new_status_id,
            },
        )
        for uid in assignee_ids
    ]
    Notification.objects.bulk_create(notifications)


@shared_task
def create_workspace_invite_notification(
    recipient_id: str,
    workspace_id: str,
    workspace_name: str,
):
    """被邀請加入工作區時通知新成員。"""
    from apps.notifications.models import Notification

    Notification.objects.create(
        recipient_id=recipient_id,
        notif_type=Notification.NotifType.WORKSPACE_INVITE,
        title=f'你被邀請加入工作區「{workspace_name}」',
        body='',
        payload={'workspace_id': workspace_id},
    )
