"""工作區、成員、標籤的 DRF Serializer。"""
from rest_framework import serializers

from apps.tasks.models import Tag
from apps.users.serializers import UserSerializer
from apps.workspaces.models import Workspace, WorkspaceMember


class WorkspaceSerializer(serializers.ModelSerializer):
    """Workspace 通用 Serializer：列表 / 建立 / 更新共用。"""
    owner = UserSerializer(read_only=True)

    class Meta:
        model = Workspace
        fields = ['id', 'name', 'description', 'avatar_url', 'owner', 'created_at', 'updated_at']
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    """成員列表 / 邀請 Serializer：寫入時帶 `user_id`，讀取時展開為 `user` 巢狀物件。"""
    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = WorkspaceMember
        fields = ['id', 'user', 'user_id', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class WorkspaceMemberRoleUpdateSerializer(serializers.ModelSerializer):
    """成員角色變更專用：限制可寫入的欄位只有 `role`。"""

    class Meta:
        model = WorkspaceMember
        fields = ['role']


class TagSerializer(serializers.ModelSerializer):
    """工作區層級標籤 Serializer。"""

    class Meta:
        model = Tag
        fields = ['id', 'name', 'color', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
