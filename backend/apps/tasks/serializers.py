"""任務模組的 DRF Serializer。

包含：
- `TaskSerializer` / `TaskDetailSerializer`：列表 / 詳情
- `TaskCommentSerializer`：留言
- `TaskActivityLogSerializer`：變更紀錄
- `TaskAssigneeSerializer`：指派
- `AttachmentRequestSerializer`：附件上傳請求驗證（檔案大小 / MIME 白名單）
- `TaskAttachmentSerializer`：附件 metadata 輸出
"""
from rest_framework import serializers

from apps.tasks.models import (
    Task,
    TaskActivityLog,
    TaskAssignee,
    TaskAttachment,
    TaskComment,
    Tag,
)
from apps.users.serializers import UserSerializer


# 附件白名單與大小上限；新增類型時更新此處
ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'application/pdf', 'text/plain',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class TaskSerializer(serializers.ModelSerializer):
    """列表頁與寫入用 Serializer。

    寫入欄位：
      - `status_id`：以 UUID 指定看板欄位
      - `assignee_ids`：建立 / 更新時的指派人 UUID 陣列
      - `tag_ids`：建立 / 更新時的標籤 UUID 陣列
    """
    status_id = serializers.UUIDField(write_only=True, required=False)
    assignees = UserSerializer(many=True, read_only=True)
    assignee_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False,
    )
    tag_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False,
    )

    class Meta:
        model = Task
        fields = [
            'id', 'project', 'parent_task', 'status', 'status_id',
            'creator', 'title', 'description', 'priority',
            'start_date', 'due_date', 'estimated_hours', 'order',
            'assignees', 'assignee_ids', 'tags', 'tag_ids',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'project', 'creator', 'status', 'tags',
            'created_at', 'updated_at',
        ]


class TaskDetailSerializer(TaskSerializer):
    """任務詳情：在列表 Serializer 之上展開 status / tags 為巢狀物件。"""
    from apps.projects.serializers import ProjectStatusSerializer
    from apps.workspaces.serializers import TagSerializer

    status = ProjectStatusSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)


class TaskCommentSerializer(serializers.ModelSerializer):
    """任務留言；author 由 view 自動填入登入者。"""
    author = UserSerializer(read_only=True)

    class Meta:
        model = TaskComment
        fields = ['id', 'author', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']


class TaskActivityLogSerializer(serializers.ModelSerializer):
    """變更紀錄唯讀輸出。"""
    actor = UserSerializer(read_only=True)

    class Meta:
        model = TaskActivityLog
        fields = ['id', 'actor', 'action', 'detail', 'created_at']
        read_only_fields = fields


class TaskAssigneeSerializer(serializers.ModelSerializer):
    """指派紀錄 Serializer：寫入帶 user_id，讀取展開為巢狀 user。"""
    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = TaskAssignee
        fields = ['id', 'user', 'user_id', 'assigned_at']
        read_only_fields = ['id', 'assigned_at']


class AttachmentRequestSerializer(serializers.Serializer):
    """檔案上傳請求驗證（取得 Presigned URL 前的 input check）。

    僅做 input 驗證，不對應 Model；驗證項目：
    - `file_size` 不得超過 10MB
    - `mime_type` 必須在白名單內
    """
    file_name = serializers.CharField(max_length=255)
    file_size = serializers.IntegerField(min_value=1)
    mime_type = serializers.CharField(max_length=100)

    def validate(self, data):
        if data['file_size'] > MAX_FILE_SIZE:
            raise serializers.ValidationError({'file_size': '檔案大小不得超過 10MB。'})
        if data['mime_type'] not in ALLOWED_MIME_TYPES:
            raise serializers.ValidationError({'mime_type': '不支援的檔案類型。'})
        return data


class TaskAttachmentSerializer(serializers.ModelSerializer):
    """附件 metadata 輸出（`file_key` 直接揭露，但 URL 仍需另呼叫 download 端點）。"""
    uploader = UserSerializer(read_only=True)

    class Meta:
        model = TaskAttachment
        fields = [
            'id', 'uploader', 'file_name', 'file_key', 'file_size',
            'mime_type', 'is_confirmed', 'created_at', 'updated_at',
        ]
        read_only_fields = fields
