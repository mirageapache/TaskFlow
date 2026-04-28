from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class Workspace(BaseModel):
    """工作區：團隊協作的最高層級容器，內可包含多個 Project。

    `owner` 採 PROTECT 避免帳號刪除時連帶刪除整個工作區（需先轉移擁有權）。
    """
    name = models.CharField(max_length=100)
    description = models.TextField(default='', blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_workspaces',
    )
    avatar_url = models.URLField(blank=True, default='')

    class Meta:
        db_table = 'workspaces'


class WorkspaceMember(BaseModel):
    """工作區成員與角色關聯表。

    `(workspace, user)` 為唯一鍵，避免同一使用者被加入兩次。
    """

    class Role(models.TextChoices):
        OWNER = 'owner', 'Owner'
        ADMIN = 'admin', 'Admin'
        MEMBER = 'member', 'Member'
        GUEST = 'guest', 'Guest'

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='members',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workspace_memberships',
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'workspace_members'
        constraints = [
            models.UniqueConstraint(
                fields=['workspace', 'user'],
                name='unique_workspace_member',
            ),
        ]
