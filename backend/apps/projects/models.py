from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.workspaces.models import Workspace


class Project(BaseModel):
    """專案：隸屬於某 Workspace，包含多個 Task 與自訂狀態（看板欄位）。"""
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    color = models.CharField(max_length=7, default='#6366f1')

    class Meta:
        db_table = 'projects'


class ProjectStatus(BaseModel):
    """專案自訂看板欄位（如：待處理、進行中、已完成）。

    `order` 控制看板顯示順序；`is_completed` 標記完成欄位用於統計。
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='statuses')
    name = models.CharField(max_length=50)
    color = models.CharField(max_length=7, default='#94a3b8')
    order = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)

    class Meta:
        db_table = 'project_statuses'
        ordering = ['order']


class ProjectMember(BaseModel):
    """專案成員與角色關聯。

    Manager: 可管理專案設定 / 狀態欄位 / 邀請成員
    Member:  可建立 / 修改任務
    Viewer:  唯讀
    """

    class Role(models.TextChoices):
        MANAGER = 'manager', 'Manager'
        MEMBER = 'member', 'Member'
        VIEWER = 'viewer', 'Viewer'

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_memberships',
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)

    class Meta:
        db_table = 'project_members'
        constraints = [
            models.UniqueConstraint(fields=['project', 'user'], name='unique_project_member'),
        ]
