from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.projects.models import Project, ProjectStatus


class Tag(BaseModel):
    """工作區層級的標籤，可跨專案使用。

    `(workspace, name)` 為唯一鍵，避免同一工作區出現重複標籤。
    用 string FK `'workspaces.Workspace'` 引用避免與 workspaces 互相 import 形成循環。
    """
    workspace = models.ForeignKey(
        'workspaces.Workspace', on_delete=models.CASCADE, related_name='tags',
    )
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#94a3b8')

    class Meta:
        db_table = 'tags'
        constraints = [
            models.UniqueConstraint(fields=['workspace', 'name'], name='unique_workspace_tag'),
        ]


class Task(BaseModel):
    """任務 Model — 系統最複雜也最核心的實體。

    關聯：
      - `project`: 所屬專案（CASCADE）
      - `status`: 看板欄位（PROTECT，避免欄位被刪除時誤砍任務）
      - `parent_task`: 自關聯，用於子任務（self FK）
      - `creator`: 建立者（SET_NULL，使用者刪除時保留歷史紀錄）
      - `assignees`: 多對多透過 `TaskAssignee` 中介表，含指派時間
      - `tags`: 多對多到 Tag
      - `dependencies`: 自關聯多對多（非對稱），表示前置任務
    """

    class Priority(models.TextChoices):
        URGENT = 'urgent', 'Urgent'
        HIGH = 'high', 'High'
        MEDIUM = 'medium', 'Medium'
        LOW = 'low', 'Low'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    parent_task = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='subtasks',
    )
    status = models.ForeignKey(ProjectStatus, on_delete=models.PROTECT, related_name='tasks')
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    estimated_hours = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='TaskAssignee',
        related_name='assigned_tasks',
        blank=True,
    )
    tags = models.ManyToManyField(Tag, related_name='tasks', blank=True)
    dependencies = models.ManyToManyField(
        'self', symmetrical=False, related_name='dependents', blank=True,
    )

    class Meta:
        db_table = 'tasks'
        ordering = ['order']


class TaskAssignee(models.Model):
    """Task ↔ User M2M 中介表，含指派時間。

    刻意不繼承 BaseModel：用整數 PK 即可，且不需軟刪除（解除指派直接 DELETE）。
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'task_assignees'
        constraints = [
            models.UniqueConstraint(fields=['task', 'user'], name='unique_task_assignee'),
        ]


class TaskComment(BaseModel):
    """任務留言。`author` 採 SET_NULL 保留刪除者留言（顯示為「已刪除使用者」）。"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='task_comments',
    )
    content = models.TextField()

    class Meta:
        db_table = 'task_comments'
        ordering = ['created_at']


class TaskAttachment(BaseModel):
    """任務附件 metadata（實際檔案在 S3，此處只記錄 key 與狀態）。

    `is_confirmed=False` 表示已產生 Presigned URL 但前端尚未通知上傳完成。
    Phase 2 可加排程清理超過 24 小時未確認的紀錄。
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='task_attachments',
    )
    file_name = models.CharField(max_length=255)
    file_key = models.CharField(max_length=512)
    file_size = models.PositiveIntegerField()
    mime_type = models.CharField(max_length=100)
    is_confirmed = models.BooleanField(default=False)

    class Meta:
        db_table = 'task_attachments'


class TaskActivityLog(models.Model):
    """任務變更紀錄。

    刻意不繼承 BaseModel：紀錄為 append-only，不需軟刪除；用整數 PK 提升寫入效能。
    Phase 1 由 view 層手動寫入；Phase 2 規劃改由 Django Signal 自動產生。
    """
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='activity_logs')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
    )
    action = models.CharField(max_length=50)
    detail = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'task_activity_logs'
        ordering = ['-created_at']
