"""專案、看板狀態、成員的 DRF Serializer。"""
from rest_framework import serializers

from apps.projects.models import Project, ProjectMember, ProjectStatus
from apps.users.serializers import UserSerializer


class ProjectStatusSerializer(serializers.ModelSerializer):
    """看板欄位 Serializer：列表與寫入共用。"""

    class Meta:
        model = ProjectStatus
        fields = ['id', 'name', 'color', 'order', 'is_completed', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectSerializer(serializers.ModelSerializer):
    """Project Serializer。

    寫入時透過 `workspace_id` 指定所屬工作區（避免直接寫入關聯欄位被竄改）；
    讀取時 `workspace` 為 read-only UUID。
    """
    workspace_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Project
        fields = [
            'id', 'workspace', 'workspace_id', 'name', 'description', 'color',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'workspace', 'created_at', 'updated_at']


class ProjectMemberSerializer(serializers.ModelSerializer):
    """專案成員 Serializer：寫入時帶 `user_id`，讀取時展開為巢狀 user 物件。"""
    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = ProjectMember
        fields = ['id', 'user', 'user_id', 'role', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProjectMemberRoleUpdateSerializer(serializers.ModelSerializer):
    """成員角色變更專用：限制可寫入欄位只有 `role`。"""

    class Meta:
        model = ProjectMember
        fields = ['role']
