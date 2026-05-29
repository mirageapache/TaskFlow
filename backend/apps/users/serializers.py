"""使用者相關的 DRF Serializer。

命名慣例：
- `UserSerializer`：基礎、僅輸出 id/email/username，給其他模組巢狀使用
- `MeSerializer`：`/me/` 端點專用，含 profile 巢狀
- `RegisterSerializer` / `LoginSerializer`：寫入專用，含驗證邏輯
"""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from apps.users.models import User, UserProfile
from apps.workspaces.models import Workspace, WorkspaceMember


class UserSerializer(serializers.ModelSerializer):
    """基礎使用者序列化器，用於列表與其他模組的巢狀引用（read only）。"""

    class Meta:
        model = User
        fields = ['id', 'email', 'username']
        read_only_fields = ['id', 'email']


class UserProfileSerializer(serializers.ModelSerializer):
    """個人偏好序列化器，對應 `/me/profile/` 端點。"""

    class Meta:
        model = UserProfile
        fields = [
            'display_name', 'bio', 'avatar_url',
            'timezone', 'language', 'theme',
        ]


class MeSerializer(serializers.ModelSerializer):
    """`/api/v1/users/me/` 端點，含 profile 巢狀資料。"""
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'profile']
        read_only_fields = ['id', 'email', 'profile']


class RegisterSerializer(serializers.ModelSerializer):
    """註冊用 Serializer：驗證唯一性、密碼強度，並透過 `create_user()` 建立帳號。"""
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['email', 'username', 'password']

    def validate_email(self, value):
        """確保 Email 尚未被使用（DB 條件唯一索引另外把關）。"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('此 Email 已被註冊。')
        return value

    def validate_username(self, value):
        """確保 Username 尚未被使用。"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('此使用者名稱已被使用。')
        return value

    def validate_password(self, value):
        """套用 Django 內建密碼強度驗證器（settings.AUTH_PASSWORD_VALIDATORS）。"""
        validate_password(value)
        return value

    def create(self, validated_data):
        """建立 User，並同步建立 UserProfile 與預設工作區。

        預設工作區讓使用者首次登入即有工作區可顯示（owner 身分）。
        全程包在 transaction.atomic：任一步驟失敗則整批回滾，不留半套資料。
        """
        password = validated_data.pop('password')
        with transaction.atomic():
            user = User.objects.create_user(password=password, **validated_data)
            UserProfile.objects.create(user=user)
            workspace = Workspace.objects.create(
                name=f'{user.username} 的工作區',
                owner=user,
            )
            WorkspaceMember.objects.create(
                workspace=workspace,
                user=user,
                role=WorkspaceMember.Role.OWNER,
            )
        return user


class LoginSerializer(serializers.Serializer):
    """登入用 Serializer：透過 Django `authenticate()` 驗證帳密。

    成功時將 user 物件存入 `validated_data['user']`，由 View 接續發 token。
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get('request'),
            email=attrs['email'],
            password=attrs['password'],
        )
        if user is None or not user.is_active:
            raise serializers.ValidationError('帳號或密碼錯誤。', code='authorization')
        attrs['user'] = user
        return attrs
