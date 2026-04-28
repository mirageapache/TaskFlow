"""
User API TDD 測試 — Phase 1
規格：.doc/taskflow-api_doc.md §8
端點：
  GET / PATCH /api/v1/users/me/
  GET / PATCH /api/v1/users/me/profile/
"""
import pytest

ME_URL = '/api/v1/users/me/'
ME_PROFILE_URL = '/api/v1/users/me/profile/'


@pytest.mark.django_db
class TestMeView:
    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(ME_URL)
        assert response.status_code == 401

    def test_get_me_returns_user_data(self, auth_client, user):
        response = auth_client.get(ME_URL)
        assert response.status_code == 200
        assert response.data['email'] == user.email
        assert response.data['username'] == user.username
        assert str(response.data['id']) == str(user.id)

    def test_patch_username(self, auth_client, user):
        response = auth_client.patch(ME_URL, {'username': 'updated_name'})
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.username == 'updated_name'

    def test_email_is_readonly(self, auth_client, user):
        original_email = user.email
        response = auth_client.patch(ME_URL, {'email': 'newmail@example.com'})
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.email == original_email


@pytest.mark.django_db
class TestMeProfileView:
    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(ME_PROFILE_URL)
        assert response.status_code == 401

    def test_get_profile_creates_if_missing(self, auth_client, user):
        response = auth_client.get(ME_PROFILE_URL)
        assert response.status_code == 200
        assert response.data['timezone'] == 'Asia/Taipei'
        assert response.data['language'] == 'zh-TW'

    def test_patch_profile_fields(self, auth_client):
        response = auth_client.patch(ME_PROFILE_URL, {
            'display_name': '小明',
            'theme': 'dark',
            'timezone': 'America/Los_Angeles',
        })
        assert response.status_code == 200
        assert response.data['display_name'] == '小明'
        assert response.data['theme'] == 'dark'
        assert response.data['timezone'] == 'America/Los_Angeles'

    def test_patch_bio_and_avatar(self, auth_client):
        response = auth_client.patch(ME_PROFILE_URL, {
            'bio': 'Hello world',
            'avatar_url': 'https://example.com/avatar.png',
        })
        assert response.status_code == 200
        assert response.data['bio'] == 'Hello world'
        assert response.data['avatar_url'] == 'https://example.com/avatar.png'
