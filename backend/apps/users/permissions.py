"""DRF 物件層級權限類別集合。

每個 Permission class 在 `has_object_permission()` 內判斷請求者是否擁有
特定 Workspace / Project 角色。視圖透過 `permission_classes = [...]` 套用。
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.projects.models import ProjectMember
from apps.workspaces.models import WorkspaceMember


class IsWorkspaceMember(BasePermission):
    """必須是該工作區的成員（含 Owner）才能存取。"""

    def has_object_permission(self, request, view, obj):
        workspace = getattr(obj, 'workspace', obj)
        if workspace.owner_id == request.user.id:
            return True
        return WorkspaceMember.objects.filter(
            workspace=workspace, user=request.user,
        ).exists()


class IsWorkspaceAdminOrOwner(BasePermission):
    """需要 Admin 或 Owner 角色（如邀請成員、刪除工作區）。"""

    def has_object_permission(self, request, view, obj):
        workspace = getattr(obj, 'workspace', obj)
        if workspace.owner_id == request.user.id:
            return True
        return WorkspaceMember.objects.filter(
            workspace=workspace,
            user=request.user,
            role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.ADMIN],
        ).exists()


class IsProjectMember(BasePermission):
    """必須是專案成員（含 Viewer）或工作區 Owner 才能存取。"""

    def has_object_permission(self, request, view, obj):
        project = getattr(obj, 'project', obj)
        if project.workspace.owner_id == request.user.id:
            return True
        return ProjectMember.objects.filter(
            project=project, user=request.user,
        ).exists()


class IsProjectManagerOrAbove(BasePermission):
    """需要 Manager 角色（如刪除專案、管理狀態欄位）；工作區 Owner 永遠視為 Manager。"""

    def has_object_permission(self, request, view, obj):
        project = getattr(obj, 'project', obj)
        if project.workspace.owner_id == request.user.id:
            return True
        return ProjectMember.objects.filter(
            project=project,
            user=request.user,
            role=ProjectMember.Role.MANAGER,
        ).exists()


class IsTaskEditableByUser(BasePermission):
    """任務可被指派人或專案 Manager 修改，其他成員為唯讀。

    - 安全方法（GET/HEAD/OPTIONS）：所有專案成員皆可
    - 寫入方法：需是指派人 / 專案 Manager / 工作區 Owner
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            project = obj.project
            if project.workspace.owner_id == request.user.id:
                return True
            return ProjectMember.objects.filter(
                project=project, user=request.user,
            ).exists()
        if obj.project.workspace.owner_id == request.user.id:
            return True
        is_assignee = obj.assignees.filter(id=request.user.id).exists()
        is_manager = ProjectMember.objects.filter(
            project=obj.project,
            user=request.user,
            role=ProjectMember.Role.MANAGER,
        ).exists()
        return is_assignee or is_manager
