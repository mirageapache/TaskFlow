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


class MembershipAuditLog(models.Model):
    """工作區 / 專案成員資格變更稽核紀錄。

    特性（與一般 BaseModel 不同）：
    - 永久保留，**不繼承 BaseModel**（沒有軟刪除欄位、PK 用 BigAutoField 而非 UUID）
    - `actor` / `target_user` 用 SET_NULL：當帳號刪除時稽核紀錄仍可保留
    - `scope_id` 不設 FK 約束：workspace / project 被刪後，紀錄仍能呈現「曾經對某 ID 做過的操作」

    寫入路徑：apps/workspaces/signals.py 監聽 WorkspaceMember / ProjectMember
    的 pre_save / post_save 自動寫入；不應由業務邏輯手動 create。

    規格：.doc/taskflow-database.md §3.18
    """

    class Action(models.TextChoices):
        MEMBER_ADDED = 'member_added', 'Member Added'
        MEMBER_REMOVED = 'member_removed', 'Member Removed'
        ROLE_CHANGED = 'role_changed', 'Role Changed'

    class ScopeType(models.TextChoices):
        WORKSPACE = 'workspace', 'Workspace'
        PROJECT = 'project', 'Project'

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='membership_audit_actions',
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='membership_audit_targets',
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    scope_type = models.CharField(max_length=10, choices=ScopeType.choices)
    scope_id = models.UUIDField()
    old_role = models.CharField(max_length=10, blank=True, default='')
    new_role = models.CharField(max_length=10, blank=True, default='')
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'membership_audit_logs'
        ordering = ['-changed_at']
        indexes = [
            # 查特定 workspace / project 的稽核歷史
            models.Index(fields=['scope_type', 'scope_id']),
            # 查特定使用者的權限變更歷史
            models.Index(fields=['target_user']),
        ]
