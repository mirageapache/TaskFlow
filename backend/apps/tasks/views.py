"""任務 API View（掛在 /api/v1/tasks/ 之下）。

涵蓋：任務 CRUD、留言、變更紀錄、指派、附件（Presigned URL 流程）。
任務權限模型較複雜，集中在 `_user_can_create_task` / `_user_can_edit_task` 兩個 helper。
"""
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.projects.models import Project, ProjectMember, ProjectStatus
from apps.tasks.models import (
    Tag,
    Task,
    TaskActivityLog,
    TaskAssignee,
    TaskAttachment,
    TaskComment,
)
from apps.tasks.serializers import (
    AttachmentRequestSerializer,
    MAX_FILE_SIZE,
    TaskActivityLogSerializer,
    TaskAssigneeSerializer,
    TaskAttachmentSerializer,
    TaskCommentSerializer,
    TaskDetailSerializer,
    TaskSerializer,
)
from apps.tasks.storage import (
    build_object_key,
    generate_download_url,
    generate_upload_post,
)
from apps.users.models import User
from apps.workspaces.models import WorkspaceMember


# ────────────── 共用權限工具 ──────────────

def _user_in_project(user, project):
    """判斷 user 是否為該專案的成員（含工作區 Owner）。"""
    if project.workspace.owner_id == user.id:
        return True
    return ProjectMember.objects.filter(project=project, user=user).exists()


def _user_can_create_task(user, project):
    """是否可在該專案建立任務：工作區 Owner、Project Manager / Member 可，Viewer 唯讀。"""
    if project.workspace.owner_id == user.id:
        return True
    return ProjectMember.objects.filter(
        project=project, user=user,
        role__in=[ProjectMember.Role.MANAGER, ProjectMember.Role.MEMBER],
    ).exists()


def _user_can_edit_task(user, task):
    """是否可修改 / 刪除任務：被指派人、Manager 或工作區 Owner。"""
    if task.project.workspace.owner_id == user.id:
        return True
    if task.assignees.filter(id=user.id).exists():
        return True
    return ProjectMember.objects.filter(
        project=task.project, user=user, role=ProjectMember.Role.MANAGER,
    ).exists()


def _apply_task_writes(task, validated):
    """共用 create / update 中的 M2M 關聯寫入邏輯（指派人、標籤）。

    - `assignee_ids`：先清空再重建（避免重複），確保最終狀態與請求一致
    - `tag_ids`：限制只能指派同工作區的 Tag，避免跨工作區引用
    """
    if 'assignee_ids' in validated:
        task.assignees.clear()
        for uid in validated['assignee_ids']:
            TaskAssignee.objects.create(task=task, user_id=uid)
    if 'tag_ids' in validated:
        tags = Tag.objects.filter(id__in=validated['tag_ids'], workspace=task.project.workspace)
        task.tags.set(tags)


# ────────────── Task CRUD ──────────────

class TaskListCreateView(generics.ListCreateAPIView):
    """GET / POST /api/v1/tasks/  — 列出我可見的任務、建立新任務。"""
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['project', 'priority', 'status']

    def get_queryset(self):
        """任務可見性：工作區 Owner / 工作區 Member / 專案 Member 皆可見。"""
        u = self.request.user
        return Task.objects.filter(
            Q(project__workspace__owner=u)
            | Q(project__members__user=u)
            | Q(project__workspace__members__user=u),
        ).distinct().order_by('order', '-created_at')

    def create(self, request, *args, **kwargs):
        """建立任務並寫入 ActivityLog。

        流程：驗證 status_id → 推導 project → 權限檢查 → 建立 Task →
        套用指派人 / 標籤 → 寫 ActivityLog → 回傳 Detail Serializer。
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        status_id = validated.get('status_id')
        if not status_id:
            raise ValidationError({'status_id': '此欄位為必填。'})
        status_obj = get_object_or_404(ProjectStatus, pk=status_id)
        project = status_obj.project

        if not _user_can_create_task(request.user, project):
            raise PermissionDenied('您沒有在此專案建立任務的權限。')

        # 子任務必須與父任務同一個 project，避免跨專案引用造成資料混亂
        parent = validated.get('parent_task')
        if parent and parent.project_id != project.id:
            raise ValidationError({'parent_task': '父任務必須屬於同一專案。'})

        task = Task.objects.create(
            project=project,
            status=status_obj,
            creator=request.user,
            parent_task=parent,
            title=validated['title'],
            description=validated.get('description', ''),
            priority=validated.get('priority', Task.Priority.MEDIUM),
            start_date=validated.get('start_date'),
            due_date=validated.get('due_date'),
            estimated_hours=validated.get('estimated_hours'),
            order=validated.get('order', 0),
        )
        # ActivityLog 由 apps.tasks.signals.task_log_save (post_save) 自動寫入
        _apply_task_writes(task, validated)
        out = TaskDetailSerializer(task)
        return Response(out.data, status=status.HTTP_201_CREATED)


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/v1/tasks/{id}/  — 任務詳情、更新、軟刪除。"""
    serializer_class = TaskDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Task.objects.all()

    def get_object(self):
        """限制只有專案成員可見。"""
        task = super().get_object()
        if not _user_in_project(self.request.user, task.project):
            raise PermissionDenied('您不是此專案的成員。')
        return task

    def update(self, request, *args, **kwargs):
        """更新任務並寫入 ActivityLog。

        覆寫 update() 而非 perform_update() 以便：
        1. 用 TaskSerializer 驗證輸入（含 status_id / assignee_ids / tag_ids）
        2. 手動處理 M2M 寫入
        3. 回傳 Detail Serializer 含巢狀資料
        """
        task = self.get_object()
        if not _user_can_edit_task(request.user, task):
            raise PermissionDenied('您沒有修改此任務的權限。')

        partial = kwargs.pop('partial', False)
        serializer = TaskSerializer(task, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        # status_id 須為同專案的 ProjectStatus
        if 'status_id' in validated:
            status_obj = get_object_or_404(
                ProjectStatus, pk=validated['status_id'], project=task.project,
            )
            task.status = status_obj

        for field in [
            'title', 'description', 'priority', 'start_date',
            'due_date', 'estimated_hours', 'order', 'parent_task',
        ]:
            if field in validated:
                setattr(task, field, validated[field])
        task.save()
        # ActivityLog（含 diff）由 apps.tasks.signals.task_log_save (post_save) 自動寫入
        _apply_task_writes(task, validated)
        out = TaskDetailSerializer(task)
        return Response(out.data)

    def perform_destroy(self, instance):
        """軟刪除任務，需編輯權限。"""
        if not _user_can_edit_task(self.request.user, instance):
            raise PermissionDenied('您沒有刪除此任務的權限。')
        instance.soft_delete()


# ────────────── 子資源 ──────────────

class TaskCommentListCreateView(generics.ListCreateAPIView):
    """GET / POST /api/v1/tasks/{id}/comments/  — 列出 / 新增任務留言。"""
    serializer_class = TaskCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_task(self):
        """取得任務並驗證請求者為專案成員。"""
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        if not _user_in_project(self.request.user, task.project):
            raise PermissionDenied('您不是此專案的成員。')
        return task

    def get_queryset(self):
        return TaskComment.objects.filter(task=self.get_task())

    def perform_create(self, serializer):
        """新增留言；author 由登入者自動填入，不接受前端傳值。"""
        serializer.save(task=self.get_task(), author=self.request.user)


class TaskActivityLogListView(generics.ListAPIView):
    """GET /api/v1/tasks/{id}/activity-logs/  — 任務變更歷史（唯讀，倒序）。"""
    serializer_class = TaskActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_task(self):
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        if not _user_in_project(self.request.user, task.project):
            raise PermissionDenied('您不是此專案的成員。')
        return task

    def get_queryset(self):
        return TaskActivityLog.objects.filter(task=self.get_task())


class TaskAssigneeListCreateView(generics.ListCreateAPIView):
    """GET / POST /api/v1/tasks/{id}/assignees/  — 列出 / 新增指派人。"""
    serializer_class = TaskAssigneeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_task(self):
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        if not _user_in_project(self.request.user, task.project):
            raise PermissionDenied('您不是此專案的成員。')
        return task

    def get_queryset(self):
        return TaskAssignee.objects.filter(task=self.get_task())

    def create(self, request, *args, **kwargs):
        """指派一位使用者；命中 unique_task_assignee 則回 400。"""
        task = self.get_task()
        if not _user_can_edit_task(request.user, task):
            raise PermissionDenied('您沒有指派此任務的權限。')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data['user_id']
        if not User.objects.filter(pk=user_id).exists():
            raise ValidationError({'user_id': '使用者不存在。'})
        try:
            assignee = TaskAssignee.objects.create(task=task, user_id=user_id)
        except IntegrityError:
            raise ValidationError({'user_id': '此使用者已被指派。'})
        out = self.get_serializer(assignee)
        return Response(out.data, status=status.HTTP_201_CREATED)


class TaskAssigneeDeleteView(generics.GenericAPIView):
    """DELETE /api/v1/tasks/{id}/assignees/{user_id}/  — 移除指派（直接 DELETE，不軟刪除）。"""
    permission_classes = [permissions.IsAuthenticated]

    def get_task(self):
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        if not _user_in_project(self.request.user, task.project):
            raise PermissionDenied('您不是此專案的成員。')
        return task

    def delete(self, request, *args, **kwargs):
        task = self.get_task()
        if not _user_can_edit_task(request.user, task):
            raise PermissionDenied('您沒有移除指派的權限。')
        assignee = get_object_or_404(
            TaskAssignee, task=task, user_id=self.kwargs['user_id'],
        )
        assignee.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ────────────── 附件（Presigned URL 流程） ──────────────

class TaskAttachmentRequestUploadView(generics.GenericAPIView):
    """POST /api/v1/tasks/{id}/attachments/request-upload/

    驗證上傳請求 → 產生 S3 Presigned POST → 建立未確認的 Attachment 記錄。
    回傳 `{ attachment_id, upload_url, fields }` 供前端直傳 S3。
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttachmentRequestSerializer

    def get_task(self):
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        if not _user_in_project(self.request.user, task.project):
            raise PermissionDenied('您不是此專案的成員。')
        return task

    def post(self, request, *args, **kwargs):
        task = self.get_task()
        if not _user_can_edit_task(request.user, task):
            raise PermissionDenied('您沒有上傳附件的權限。')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file_name = serializer.validated_data['file_name']
        file_size = serializer.validated_data['file_size']
        mime_type = serializer.validated_data['mime_type']
        file_key = build_object_key(task.id, file_name)

        presigned = generate_upload_post(file_key, mime_type, MAX_FILE_SIZE)

        # 先建立 is_confirmed=False 的 attachment；前端上傳完成後會打 confirm 端點翻牌
        attachment = TaskAttachment.objects.create(
            task=task,
            uploader=request.user,
            file_name=file_name,
            file_key=file_key,
            file_size=file_size,
            mime_type=mime_type,
            is_confirmed=False,
        )
        return Response({
            'attachment_id': str(attachment.id),
            'upload_url': presigned['url'],
            'fields': presigned['fields'],
        }, status=status.HTTP_200_OK)


class TaskAttachmentConfirmView(generics.GenericAPIView):
    """PATCH /api/v1/tasks/{id}/attachments/{aid}/confirm/

    前端直傳 S3 完成後，呼叫此端點將 `is_confirmed` 設為 True，附件才會出現在下載列表。
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskAttachmentSerializer

    def get_task(self):
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        if not _user_in_project(self.request.user, task.project):
            raise PermissionDenied('您不是此專案的成員。')
        return task

    def patch(self, request, *args, **kwargs):
        task = self.get_task()
        attachment = get_object_or_404(
            TaskAttachment, pk=self.kwargs['pk'], task=task,
        )
        # 上傳者本人或編輯權限者可確認；避免他人冒名翻牌
        if attachment.uploader_id != request.user.id and not _user_can_edit_task(request.user, task):
            raise PermissionDenied('僅上傳者或具編輯權限者可確認附件。')
        attachment.is_confirmed = True
        attachment.save(update_fields=['is_confirmed', 'updated_at'])
        return Response(self.get_serializer(attachment).data)


class TaskAttachmentDownloadView(generics.GenericAPIView):
    """GET /api/v1/tasks/{id}/attachments/{aid}/download/

    產生 15 分鐘效期的 Presigned GET URL。每次呼叫都重新簽名，避免長期可下載連結外洩。
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_task(self):
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        if not _user_in_project(self.request.user, task.project):
            raise PermissionDenied('您不是此專案的成員。')
        return task

    def get(self, request, *args, **kwargs):
        task = self.get_task()
        attachment = get_object_or_404(
            TaskAttachment, pk=self.kwargs['pk'], task=task,
        )
        if not attachment.is_confirmed:
            raise ValidationError({'detail': '附件尚未上傳完成。'})
        url = generate_download_url(attachment.file_key)
        return Response({'download_url': url})


class TaskAttachmentListView(generics.ListAPIView):
    """GET /api/v1/tasks/{id}/attachments/  — 任務附件列表（含未確認的，前端可自行過濾）。"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskAttachmentSerializer

    def get_task(self):
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        if not _user_in_project(self.request.user, task.project):
            raise PermissionDenied('您不是此專案的成員。')
        return task

    def get_queryset(self):
        return TaskAttachment.objects.filter(task=self.get_task()).order_by('-created_at')
