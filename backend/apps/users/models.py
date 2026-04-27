from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models import Q

from apps.core.models import BaseModel, SoftDeleteManager


class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
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
        """軟刪除同時停用帳號，確保 Django auth backend 不允許已刪除帳號登入"""
        self.is_active = False
        self.save(update_fields=['is_active'])
        super().soft_delete()


class UserProfile(BaseModel):
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
