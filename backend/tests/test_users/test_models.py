"""
User Model TDD 測試 — Phase 1
規格：.doc/taskflow-backend.md §5.2、taskflow-database.md §3.1–3.3
"""
import uuid

import pytest
from django.db.utils import IntegrityError

# ---------------------------------------------------------------------------
# BaseModel 通用行為（abstract，透過 User 驗證）
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBaseModel:

    def test_uuid_primary_key_generated(self):
        from apps.users.models import User
        user = User.objects.create_user(email='a@example.com', username='a', password='p')
        assert isinstance(user.pk, uuid.UUID)

    def test_created_at_auto_populated(self):
        from apps.users.models import User
        user = User.objects.create_user(email='a@example.com', username='a', password='p')
        assert user.created_at is not None

    def test_updated_at_auto_populated(self):
        from apps.users.models import User
        user = User.objects.create_user(email='a@example.com', username='a', password='p')
        assert user.updated_at is not None

    def test_deleted_at_is_null_by_default(self):
        from apps.users.models import User
        user = User.objects.create_user(email='a@example.com', username='a', password='p')
        assert user.deleted_at is None

    def test_soft_delete_sets_deleted_at(self):
        from apps.users.models import User
        user = User.objects.create_user(email='a@example.com', username='a', password='p')
        user.soft_delete()
        user.refresh_from_db()
        assert user.deleted_at is not None


# ---------------------------------------------------------------------------
# User 軟刪除行為
# 規格：objects=UserManager（不過濾）、active_objects=SoftDeleteManager（過濾）
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserSoftDelete:

    def test_soft_delete_sets_is_active_false(self):
        """軟刪除後帳號停用，避免 Django auth backend 允許登入"""
        from apps.users.models import User
        user = User.objects.create_user(email='a@example.com', username='a', password='p')
        user.soft_delete()
        user.refresh_from_db()
        assert user.is_active is False

    def test_soft_deleted_user_not_in_active_objects(self):
        """active_objects（商業邏輯查詢）不回傳已刪除使用者"""
        from apps.users.models import User
        user = User.objects.create_user(email='a@example.com', username='a', password='p')
        user.soft_delete()
        assert User.active_objects.filter(pk=user.pk).count() == 0

    def test_soft_deleted_user_visible_via_all_objects(self):
        """all_objects 可查到已刪除使用者"""
        from apps.users.models import User
        user = User.objects.create_user(email='a@example.com', username='a', password='p')
        user.soft_delete()
        assert User.all_objects.filter(pk=user.pk).count() == 1

    def test_objects_manager_includes_deleted_for_auth_backend(self):
        """objects（UserManager）不過濾軟刪除，供 Django auth backend 使用"""
        from apps.users.models import User
        user = User.objects.create_user(email='a@example.com', username='a', password='p')
        user.soft_delete()
        assert User.objects.filter(pk=user.pk).count() == 1

    def test_same_email_can_register_after_soft_delete(self):
        """帳號刪除後，相同 email 可重新註冊（條件唯一約束）"""
        from apps.users.models import User
        user = User.objects.create_user(email='reuse@example.com', username='user1', password='p')
        user.soft_delete()
        new_user = User.objects.create_user(email='reuse@example.com', username='user2', password='p')
        assert new_user.pk is not None

    def test_same_username_can_register_after_soft_delete(self):
        """帳號刪除後，相同 username 可重新使用"""
        from apps.users.models import User
        user = User.objects.create_user(email='user1@example.com', username='shared', password='p')
        user.soft_delete()
        new_user = User.objects.create_user(email='user2@example.com', username='shared', password='p')
        assert new_user.pk is not None


# ---------------------------------------------------------------------------
# UserManager 行為
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserManager:

    def test_create_user_sets_fields(self):
        from apps.users.models import User
        user = User.objects.create_user(email='alice@example.com', username='alice', password='pass123')
        assert user.email == 'alice@example.com'
        assert user.username == 'alice'
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_user_requires_email(self):
        from apps.users.models import User
        with pytest.raises(ValueError, match='Email is required'):
            User.objects.create_user(email='', username='alice', password='pass123')

    def test_create_user_hashes_password(self):
        from apps.users.models import User
        user = User.objects.create_user(email='alice@example.com', username='alice', password='pass123')
        assert user.password != 'pass123'
        assert user.check_password('pass123')

    def test_create_user_normalizes_email(self):
        """email domain 轉小寫"""
        from apps.users.models import User
        user = User.objects.create_user(email='Alice@EXAMPLE.COM', username='alice', password='p')
        assert user.email == 'Alice@example.com'

    def test_create_superuser_sets_staff_and_superuser(self):
        from apps.users.models import User
        user = User.objects.create_superuser(email='admin@example.com', username='admin', password='adminpass')
        assert user.is_staff is True
        assert user.is_superuser is True


# ---------------------------------------------------------------------------
# 條件唯一約束（Partial Unique Index，需 PostgreSQL）
# transaction=True：IntegrityError 需要真實 transaction 才能正確捕捉
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestUserUniqueConstraints:

    def test_duplicate_active_email_raises_error(self):
        from apps.users.models import User
        User.objects.create_user(email='dupe@example.com', username='user1', password='p')
        with pytest.raises(IntegrityError):
            User.objects.create_user(email='dupe@example.com', username='user2', password='p')

    def test_duplicate_active_username_raises_error(self):
        from apps.users.models import User
        User.objects.create_user(email='user1@example.com', username='shared', password='p')
        with pytest.raises(IntegrityError):
            User.objects.create_user(email='user2@example.com', username='shared', password='p')


# ---------------------------------------------------------------------------
# UserProfile Model
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserProfile:

    def test_profile_can_be_linked_to_user(self):
        from apps.users.models import User, UserProfile
        user = User.objects.create_user(email='a@example.com', username='a', password='p')
        profile = UserProfile.objects.create(user=user)
        assert profile.pk is not None
        assert user.profile == profile

    def test_profile_default_values(self):
        from apps.users.models import User, UserProfile
        user = User.objects.create_user(email='a@example.com', username='a', password='p')
        profile = UserProfile.objects.create(user=user)
        assert profile.timezone == 'Asia/Taipei'
        assert profile.language == 'zh-TW'
        assert profile.theme == 'system'
        assert profile.display_name == ''
        assert profile.bio == ''
        assert profile.avatar_url == ''

    def test_profile_one_to_one_constraint(self):
        """每個 User 只能有一個 Profile"""
        from apps.users.models import User, UserProfile
        user = User.objects.create_user(email='a@example.com', username='a', password='p')
        UserProfile.objects.create(user=user)
        with pytest.raises(IntegrityError):
            UserProfile.objects.create(user=user)


# ---------------------------------------------------------------------------
# UserSocialAccount Model
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestUserSocialAccount:

    def test_create_social_account(self):
        from apps.users.models import User, UserSocialAccount
        user = User.objects.create_user(email='a@example.com', username='a', password='p')
        account = UserSocialAccount.objects.create(
            user=user,
            provider=UserSocialAccount.Provider.GOOGLE,
            provider_user_id='google_uid_123',
        )
        assert account.pk is not None
        assert account.provider == 'google'

    def test_user_can_link_multiple_providers(self):
        from apps.users.models import User, UserSocialAccount
        user = User.objects.create_user(email='a@example.com', username='a', password='p')
        UserSocialAccount.objects.create(user=user, provider='google', provider_user_id='g_123')
        UserSocialAccount.objects.create(user=user, provider='line', provider_user_id='l_456')
        assert user.social_accounts.count() == 2

    def test_provider_user_id_unique_per_provider(self):
        """同一 Provider 的 provider_user_id 全域唯一"""
        from apps.users.models import User, UserSocialAccount
        user1 = User.objects.create_user(email='u1@example.com', username='u1', password='p')
        user2 = User.objects.create_user(email='u2@example.com', username='u2', password='p')
        UserSocialAccount.objects.create(user=user1, provider='google', provider_user_id='same_uid')
        with pytest.raises(IntegrityError):
            UserSocialAccount.objects.create(user=user2, provider='google', provider_user_id='same_uid')

    def test_same_provider_user_id_allowed_across_providers(self):
        """不同 Provider 可以有相同 provider_user_id"""
        from apps.users.models import User, UserSocialAccount
        user = User.objects.create_user(email='a@example.com', username='a', password='p')
        UserSocialAccount.objects.create(user=user, provider='google', provider_user_id='uid_xyz')
        account = UserSocialAccount.objects.create(user=user, provider='line', provider_user_id='uid_xyz')
        assert account.pk is not None
