from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel, SoftDeleteManager


class UserManager(BaseUserManager):
    """自訂使用者建立 Manager。

    Django 認證機制要求 User Model 提供 `create_user()` / `create_superuser()`，
    繼承 `BaseUserManager` 取得 `normalize_email()` 等工具方法。
    本 Manager 不過濾軟刪除（`deleted_at`）的使用者，避免影響 Django auth backend
    在登入流程中的查詢；商業邏輯查詢請改用下方的 `active_objects`。
    """

    def create_user(self, email, username, password=None, **extra_fields):
        """建立一般使用者；密碼會經由 `set_password()` 雜湊後儲存。"""
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        """建立後台管理員（`is_staff=True`、`is_superuser=True`）。"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """專案核心使用者 Model。

    - `AbstractBaseUser`：提供密碼欄位、`set_password()`、`check_password()` 等
    - `PermissionsMixin`：提供 Django 權限框架（groups / user_permissions）
    - `BaseModel`：提供 UUID 主鍵與軟刪除欄位
    使用 Email 作為登入帳號（`USERNAME_FIELD = 'email'`），並透過條件唯一索引
    （`WHERE deleted_at IS NULL`）允許帳號軟刪除後相同 Email 可重新註冊。
    """
    email = models.EmailField()
    username = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # UserManager 不過濾軟刪除，供 Django auth backend 使用
    objects = UserManager()
    # 商業邏輯查詢使用 active_objects（過濾已刪除）
    active_objects = SoftDeleteManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        constraints = [
            # 條件唯一：僅對「未刪除」的列強制 email 唯一，允許帳號重生
            models.UniqueConstraint(
                fields=['email'],
                condition=Q(deleted_at__isnull=True),
                name='unique_active_user_email',
            ),
            models.UniqueConstraint(
                fields=['username'],
                condition=Q(deleted_at__isnull=True),
                name='unique_active_username',
            ),
        ]

    def soft_delete(self):
        """軟刪除同時停用帳號，避免被刪除的使用者繼續登入。"""
        self.is_active = False
        self.save(update_fields=['is_active'])
        super().soft_delete()


class UserProfile(BaseModel):
    """使用者個人偏好資料（時區、語系、佈景主題等）。

    與 User 採 1:1（`OneToOneField`）關聯；首次需要時於 `MeProfileView`
    中以 `get_or_create()` 建立，避免註冊流程強耦合。
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)
    timezone = models.CharField(max_length=50, default='Asia/Taipei')
    language = models.CharField(max_length=10, default='zh-TW')
    theme = models.CharField(max_length=10, default='system')

    class Meta:
        db_table = 'user_profiles'


class UserSocialAccount(BaseModel):
    """OAuth 第三方登入綁定紀錄（Google / LINE）。

    每位 User 可同時綁定多個 Provider，`(provider, provider_user_id)` 為唯一鍵。
    """

    class Provider(models.TextChoices):
        GOOGLE = 'google', 'Google'
        LINE = 'line', 'LINE'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='social_accounts')
    provider = models.CharField(max_length=20, choices=Provider.choices)
    provider_user_id = models.CharField(max_length=255)

    class Meta:
        db_table = 'user_social_accounts'
        constraints = [
            models.UniqueConstraint(
                fields=['provider', 'provider_user_id'],
                name='unique_social_provider_user',
            ),
        ]
