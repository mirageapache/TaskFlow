"""通知 Model（Phase 2）。

由 apps/notifications/signals.py 在以下事件自動寫入：
- 任務被指派 (`task_assigned`)
- 任務有新留言 (`task_comment`)
- 你負責的任務狀態變更 (`task_status_changed`)
- 在留言中被 @ 提及 (`mention`，留待後續實作 mention 解析)
- 被邀請加入工作區 (`workspace_invite`)

規格：.doc/taskflow-database.md §3.14
"""
from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Notification(BaseModel):
    """單筆通知；recipient 為被通知對象，actor 隱含於 payload。"""

    class NotifType(models.TextChoices):
        TASK_ASSIGNED = 'task_assigned', 'Task Assigned'
        TASK_COMMENT = 'task_comment', 'Task Comment'
        TASK_STATUS_CHANGED = 'task_status_changed', 'Task Status Changed'
        MENTION = 'mention', 'Mention'
        WORKSPACE_INVITE = 'workspace_invite', 'Workspace Invite'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notif_type = models.CharField(max_length=30, choices=NotifType.choices)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default='')
    payload = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            # 最常見查詢：未讀通知數
            models.Index(fields=['recipient', 'is_read']),
        ]
