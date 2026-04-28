"""工作區 API View（掛在 /api/v1/workspaces/ 之下）。

涵蓋：工作區 CRUD、成員管理、Tag 管理。
權限以模組內 helper（`_user_in_workspace` / `_user_is_admin_or_owner`）做物件層級檢查。
"""
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.tasks.models import Tag
from apps.users.models import User
from apps.workspaces.models import Workspace, WorkspaceMember
from apps.workspaces.serializers import (
    TagSerializer,
    WorkspaceMemberRoleUpdateSerializer,
    WorkspaceMemberSerializer,
    WorkspaceSerializer,
)


def _user_in_workspace(user, workspace):
    """判斷 user 是否為該工作區的 Owner 或成員。"""
    if workspace.owner_id == user.id:
        return True
    return WorkspaceMember.objects.filter(workspace=workspace, user=user).exists()


def _user_is_admin_or_owner(user, workspace):
    """判斷 user 是否擁有 Admin / Owner 等高權限角色。"""
    if workspace.owner_id == user.id:
        return True
    return WorkspaceMember.objects.filter(
        workspace=workspace, user=user,
        role__in=[WorkspaceMember.Role.OWNER, WorkspaceMember.Role.ADMIN],
    ).exists()


class WorkspaceListCreateView(generics.ListCreateAPIView):
    """GET / POST /api/v1/workspaces/  — 列出我加入的工作區、建立新工作區。"""
    serializer_class = WorkspaceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """只列出 user 是 Owner 或 Member 的工作區，避免越權瀏覽。"""
        u = self.request.user
        return Workspace.objects.filter(
            Q(owner=u) | Q(members__user=u),
        ).distinct().order_by('-created_at')

    def perform_create(self, serializer):
        """建立工作區時自動將請求者設為 owner。"""
        serializer.save(owner=self.request.user)


class WorkspaceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/v1/workspaces/{id}/  — 工作區詳情、更新、軟刪除。"""
    serializer_class = WorkspaceSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Workspace.objects.all()

    def get_object(self):
        """檢查請求者是否為成員，否則回 403。"""
        ws = super().get_object()
        if not _user_in_workspace(self.request.user, ws):
            raise PermissionDenied('您不是此工作區的成員。')
        return ws

    def perform_update(self, serializer):
        """更新需 Admin 或 Owner 權限。"""
        if not _user_is_admin_or_owner(self.request.user, self.get_object()):
            raise PermissionDenied('需要 Admin 或 Owner 權限。')
        serializer.save()

    def perform_destroy(self, instance):
        """僅 Owner 可刪除工作區（採軟刪除）。"""
        if instance.owner_id != self.request.user.id:
            raise PermissionDenied('僅 Workspace Owner 可刪除工作區。')
        instance.soft_delete()


class WorkspaceMemberListCreateView(generics.ListCreateAPIView):
    """GET / POST /api/v1/workspaces/{id}/members/  — 列出 / 邀請成員。"""
    serializer_class = WorkspaceMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_workspace(self):
        """取得 workspace 並驗證請求者為成員，否則回 403。"""
        ws = get_object_or_404(Workspace, pk=self.kwargs['workspace_id'])
        if not _user_in_workspace(self.request.user, ws):
            raise PermissionDenied('您不是此工作區的成員。')
        return ws

    def get_queryset(self):
        return WorkspaceMember.objects.filter(
            workspace=self.get_workspace(),
        ).order_by('joined_at')

    def create(self, request, *args, **kwargs):
        """邀請成員：需 Admin/Owner 權限；驗證 user 存在 + 防止重複邀請。"""
        ws = self.get_workspace()
        if not _user_is_admin_or_owner(request.user, ws):
            raise PermissionDenied('需要 Admin 或 Owner 權限。')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data['user_id']
        if not User.objects.filter(pk=user_id).exists():
            raise ValidationError({'user_id': '使用者不存在。'})
        try:
            member = WorkspaceMember.objects.create(
                workspace=ws,
                user_id=user_id,
                role=serializer.validated_data.get('role', WorkspaceMember.Role.MEMBER),
            )
        except IntegrityError:
            # 命中 unique_workspace_member 約束 → 該 user 已加入
            raise ValidationError({'user_id': '此使用者已是工作區成員。'})
        out = self.get_serializer(member)
        return Response(out.data, status=status.HTTP_201_CREATED)


class WorkspaceMemberDetailView(generics.GenericAPIView):
    """PATCH / DELETE /api/v1/workspaces/{id}/members/{user_id}/  — 變更角色、移除成員。"""
    serializer_class = WorkspaceMemberRoleUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_workspace(self):
        """取得 workspace 並驗證請求者為成員。"""
        ws = get_object_or_404(Workspace, pk=self.kwargs['workspace_id'])
        if not _user_in_workspace(self.request.user, ws):
            raise PermissionDenied('您不是此工作區的成員。')
        return ws

    def get_member(self):
        """取得欲操作的成員列；不存在則 404。"""
        ws = self.get_workspace()
        return get_object_or_404(
            WorkspaceMember, workspace=ws, user_id=self.kwargs['user_id'],
        )

    def patch(self, request, *args, **kwargs):
        """變更成員角色，需 Admin/Owner 權限。"""
        ws = self.get_workspace()
        if not _user_is_admin_or_owner(request.user, ws):
            raise PermissionDenied('需要 Admin 或 Owner 權限。')
        member = self.get_member()
        serializer = self.get_serializer(member, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        out = WorkspaceMemberSerializer(member)
        return Response(out.data)

    def delete(self, request, *args, **kwargs):
        """移除成員（軟刪除），需 Admin/Owner 權限。"""
        ws = self.get_workspace()
        if not _user_is_admin_or_owner(request.user, ws):
            raise PermissionDenied('需要 Admin 或 Owner 權限。')
        member = self.get_member()
        member.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagListCreateView(generics.ListCreateAPIView):
    """GET / POST /api/v1/workspaces/{id}/tags/  — 工作區標籤列表 / 建立。"""
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_workspace(self):
        ws = get_object_or_404(Workspace, pk=self.kwargs['workspace_id'])
        if not _user_in_workspace(self.request.user, ws):
            raise PermissionDenied('您不是此工作區的成員。')
        return ws

    def get_queryset(self):
        return Tag.objects.filter(workspace=self.get_workspace()).order_by('name')

    def perform_create(self, serializer):
        """建立標籤時帶入 workspace；命中唯一鍵約束時回 400。"""
        ws = self.get_workspace()
        try:
            serializer.save(workspace=ws)
        except IntegrityError:
            raise ValidationError({'name': '此標籤名稱已存在。'})


class TagDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/v1/workspaces/{id}/tags/{tag_id}/  — 標籤更新與軟刪除。"""
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_workspace(self):
        ws = get_object_or_404(Workspace, pk=self.kwargs['workspace_id'])
        if not _user_in_workspace(self.request.user, ws):
            raise PermissionDenied('您不是此工作區的成員。')
        return ws

    def get_object(self):
        ws = self.get_workspace()
        return get_object_or_404(Tag, pk=self.kwargs['pk'], workspace=ws)

    def perform_destroy(self, instance):
        instance.soft_delete()
