"""專案 API View（掛在 /api/v1/projects/ 之下）。

涵蓋：專案 CRUD、看板狀態欄管理、專案成員管理。
"""
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.projects.models import Project, ProjectMember, ProjectStatus
from apps.projects.serializers import (
    ProjectMemberRoleUpdateSerializer,
    ProjectMemberSerializer,
    ProjectSerializer,
    ProjectStatusSerializer,
)
from apps.users.models import User
from apps.workspaces.models import Workspace, WorkspaceMember

# 新專案建立時自動帶入的預設看板欄位。
# 顏色取自 Tailwind 色票：slate-400 / blue-500 / emerald-500。
# 最後一欄 is_completed=True 用於 Dashboard 計算「完成率」等統計。
DEFAULT_PROJECT_STATUSES = (
    {'name': '待辦', 'color': '#94a3b8', 'order': 0, 'is_completed': False},
    {'name': '進行中', 'color': '#3b82f6', 'order': 1, 'is_completed': False},
    {'name': '完成', 'color': '#10b981', 'order': 2, 'is_completed': True},
)


def _create_default_statuses(project):
    """為新建專案 bulk_create 三個預設看板欄位。"""
    ProjectStatus.objects.bulk_create([
        ProjectStatus(project=project, **fields) for fields in DEFAULT_PROJECT_STATUSES
    ])


def _user_in_workspace(user, workspace):
    """判斷 user 是否為該工作區的 Owner 或成員。"""
    if workspace.owner_id == user.id:
        return True
    return WorkspaceMember.objects.filter(workspace=workspace, user=user).exists()


def _user_in_project(user, project):
    """判斷 user 是否為該專案的成員（含工作區 Owner）。"""
    if project.workspace.owner_id == user.id:
        return True
    return ProjectMember.objects.filter(project=project, user=user).exists()


def _user_is_project_manager(user, project):
    """判斷 user 是否擁有 Project Manager 權限（工作區 Owner 視為 Manager）。"""
    if project.workspace.owner_id == user.id:
        return True
    return ProjectMember.objects.filter(
        project=project, user=user, role=ProjectMember.Role.MANAGER,
    ).exists()


class ProjectListCreateView(generics.ListCreateAPIView):
    """GET / POST /api/v1/projects/  — 列出我可見的專案、建立新專案。"""
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['workspace']

    def get_queryset(self):
        """專案可見性：工作區 Owner / 工作區 Member / 專案 Member 皆可見。"""
        u = self.request.user
        return Project.objects.filter(
            Q(workspace__owner=u) | Q(members__user=u) | Q(workspace__members__user=u),
        ).distinct().order_by('-created_at')

    def create(self, request, *args, **kwargs):
        """建立專案：透過 `workspace_id` 指定所屬工作區，需為該工作區成員。

        建立同時自動帶入三個預設看板欄位（待辦／進行中／完成），整個流程包在
        transaction.atomic 內 — 若預設欄位寫入失敗會一併回滾，避免出現
        「專案存在但沒有任何欄位」的破口（這正是先前 BoardView 看到空白的根因）。
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace_id = serializer.validated_data.get('workspace_id')
        if not workspace_id:
            raise ValidationError({'workspace_id': '此欄位為必填。'})
        workspace = get_object_or_404(Workspace, pk=workspace_id)
        if not _user_in_workspace(request.user, workspace):
            raise PermissionDenied('您不是此工作區的成員。')
        with transaction.atomic():
            project = Project.objects.create(
                workspace=workspace,
                name=serializer.validated_data['name'],
                description=serializer.validated_data.get('description', ''),
                color=serializer.validated_data.get('color', '#6366f1'),
            )
            _create_default_statuses(project)
        out = self.get_serializer(project)
        return Response(out.data, status=status.HTTP_201_CREATED)


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/v1/projects/{id}/  — 專案詳情、更新、軟刪除。"""
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Project.objects.all()

    def get_object(self):
        """限制只有專案成員可見。"""
        project = super().get_object()
        if not _user_in_project(self.request.user, project):
            raise PermissionDenied('您不是此專案的成員。')
        return project

    def perform_update(self, serializer):
        """更新需 Manager 權限。"""
        if not _user_is_project_manager(self.request.user, self.get_object()):
            raise PermissionDenied('需要 Project Manager 權限。')
        serializer.save()

    def perform_destroy(self, instance):
        """刪除需 Manager 權限（採軟刪除）。"""
        if not _user_is_project_manager(self.request.user, instance):
            raise PermissionDenied('需要 Project Manager 權限。')
        instance.soft_delete()


class ProjectStatusListCreateView(generics.ListCreateAPIView):
    """GET / POST /api/v1/projects/{id}/statuses/  — 列出 / 新增看板欄位。"""
    serializer_class = ProjectStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_project(self):
        """取得專案並驗證請求者為成員。"""
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        if not _user_in_project(self.request.user, project):
            raise PermissionDenied('您不是此專案的成員。')
        return project

    def get_queryset(self):
        return ProjectStatus.objects.filter(project=self.get_project())

    def perform_create(self, serializer):
        """新增看板欄位，需 Manager 權限。"""
        project = self.get_project()
        if not _user_is_project_manager(self.request.user, project):
            raise PermissionDenied('需要 Project Manager 權限。')
        serializer.save(project=project)


class ProjectStatusBootstrapDefaultsView(generics.GenericAPIView):
    """POST /api/v1/projects/{id}/statuses/bootstrap-defaults/

    為「沒有任何看板欄位」的舊專案一鍵補上預設三欄（待辦／進行中／完成）。
    需 Manager 權限；若專案已有欄位則回 409 避免覆蓋既有設定。
    """
    serializer_class = ProjectStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        if not _user_in_project(request.user, project):
            raise PermissionDenied('您不是此專案的成員。')
        if not _user_is_project_manager(request.user, project):
            raise PermissionDenied('需要 Project Manager 權限。')
        if ProjectStatus.objects.filter(project=project).exists():
            return Response(
                {'detail': '此專案已有看板欄位，無法重複建立預設值。'},
                status=status.HTTP_409_CONFLICT,
            )
        with transaction.atomic():
            _create_default_statuses(project)
        statuses = ProjectStatus.objects.filter(project=project).order_by('order')
        out = ProjectStatusSerializer(statuses, many=True)
        return Response(out.data, status=status.HTTP_201_CREATED)


class ProjectStatusDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/v1/projects/{id}/statuses/{status_id}/  — 看板欄位 CRUD。"""
    serializer_class = ProjectStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_project(self):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        if not _user_in_project(self.request.user, project):
            raise PermissionDenied('您不是此專案的成員。')
        return project

    def get_object(self):
        project = self.get_project()
        return get_object_or_404(ProjectStatus, pk=self.kwargs['pk'], project=project)

    def perform_update(self, serializer):
        if not _user_is_project_manager(self.request.user, self.get_project()):
            raise PermissionDenied('需要 Project Manager 權限。')
        serializer.save()

    def perform_destroy(self, instance):
        if not _user_is_project_manager(self.request.user, self.get_project()):
            raise PermissionDenied('需要 Project Manager 權限。')
        instance.soft_delete()


class ProjectMemberListCreateView(generics.ListCreateAPIView):
    """GET / POST /api/v1/projects/{id}/members/  — 列出 / 邀請專案成員。"""
    serializer_class = ProjectMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_project(self):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        if not _user_in_project(self.request.user, project):
            raise PermissionDenied('您不是此專案的成員。')
        return project

    def get_queryset(self):
        return ProjectMember.objects.filter(
            project=self.get_project(),
        ).order_by('created_at')

    def create(self, request, *args, **kwargs):
        """邀請成員，需 Manager 權限；驗證 user 存在 + 防止重複邀請。"""
        project = self.get_project()
        if not _user_is_project_manager(request.user, project):
            raise PermissionDenied('需要 Project Manager 權限。')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data['user_id']
        if not User.objects.filter(pk=user_id).exists():
            raise ValidationError({'user_id': '使用者不存在。'})
        try:
            member = ProjectMember.objects.create(
                project=project,
                user_id=user_id,
                role=serializer.validated_data.get('role', ProjectMember.Role.MEMBER),
            )
        except IntegrityError as exc:
            raise ValidationError({'user_id': '此使用者已是專案成員。'}) from exc
        out = self.get_serializer(member)
        return Response(out.data, status=status.HTTP_201_CREATED)


class ProjectMemberDetailView(generics.GenericAPIView):
    """PATCH / DELETE /api/v1/projects/{id}/members/{user_id}/  — 變更角色 / 移除成員。"""
    serializer_class = ProjectMemberRoleUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_project(self):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        if not _user_in_project(self.request.user, project):
            raise PermissionDenied('您不是此專案的成員。')
        return project

    def get_member(self):
        return get_object_or_404(
            ProjectMember,
            project=self.get_project(),
            user_id=self.kwargs['user_id'],
        )

    def patch(self, request, *args, **kwargs):
        """變更成員角色，需 Manager 權限。"""
        if not _user_is_project_manager(request.user, self.get_project()):
            raise PermissionDenied('需要 Project Manager 權限。')
        member = self.get_member()
        serializer = self.get_serializer(member, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        out = ProjectMemberSerializer(member)
        return Response(out.data)

    def delete(self, request, *args, **kwargs):
        """移除成員（軟刪除），需 Manager 權限。"""
        if not _user_is_project_manager(request.user, self.get_project()):
            raise PermissionDenied('需要 Project Manager 權限。')
        member = self.get_member()
        member.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
