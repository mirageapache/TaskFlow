"""
Auth API TDD 測試 — Phase 1
規格：.doc/taskflow-backend.md §7、.doc/taskflow-api_doc.md §1
端點：
  POST /api/v1/auth/register/
  POST /api/v1/auth/login/
  POST /api/v1/auth/refresh/
  POST /api/v1/auth/logout/
"""
import pytest

from tests.factories import UserFactory


REGISTER_URL = '/api/v1/auth/register/'
LOGIN_URL = '/api/v1/auth/login/'
REFRESH_URL = '/api/v1/auth/refresh/'
LOGOUT_URL = '/api/v1/auth/logout/'


@pytest.mark.django_db
class TestRegister:
    def test_register_success(self, api_client):
        data = {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password': 'StrongP@ssw0rd!',
        }
        response = api_client.post(REGISTER_URL, data)
        assert response.status_code == 201
        assert 'access' in response.data
        assert response.data['user']['email'] == 'newuser@example.com'

    def test_register_sets_refresh_cookie(self, api_client):
        data = {
            'email': 'cookie@example.com',
            'username': 'cookieuser',
            'password': 'StrongP@ssw0rd!',
        }
        response = api_client.post(REGISTER_URL, data)
        assert response.status_code == 201
        assert 'refresh_token' in response.cookies
        assert response.cookies['refresh_token']['httponly']

    def test_register_duplicate_email(self, api_client):
        UserFactory(email='dup@example.com')
        data = {
            'email': 'dup@example.com',
            'username': 'someoneelse',
            'password': 'StrongP@ssw0rd!',
        }
        response = api_client.post(REGISTER_URL, data)
        assert response.status_code == 400
        assert 'email' in response.data

    def test_register_missing_fields(self, api_client):
        response = api_client.post(REGISTER_URL, {'email': 'x@example.com'})
        assert response.status_code == 400

    def test_register_weak_password(self, api_client):
        data = {
            'email': 'weak@example.com',
            'username': 'weak',
            'password': '123',
        }
        response = api_client.post(REGISTER_URL, data)
        assert response.status_code == 400
        assert 'password' in response.data


@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, api_client):
        UserFactory(email='login@example.com')
        # UserFactory 預設密碼為 testpass123
        response = api_client.post(LOGIN_URL, {
            'email': 'login@example.com',
            'password': 'testpass123',
        })
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh_token' in response.cookies

    def test_login_wrong_password(self, api_client):
        UserFactory(email='wrong@example.com')
        response = api_client.post(LOGIN_URL, {
            'email': 'wrong@example.com',
            'password': 'incorrect',
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, api_client):
        response = api_client.post(LOGIN_URL, {
            'email': 'nobody@example.com',
            'password': 'whatever',
        })
        assert response.status_code == 401

    def test_login_inactive_user(self, api_client):
        user = UserFactory(email='inactive@example.com')
        user.is_active = False
        user.save()
        response = api_client.post(LOGIN_URL, {
            'email': 'inactive@example.com',
            'password': 'testpass123',
        })
        assert response.status_code == 401


@pytest.mark.django_db
class TestRefresh:
    def test_refresh_with_cookie(self, api_client):
        UserFactory(email='refresh@example.com')
        login = api_client.post(LOGIN_URL, {
            'email': 'refresh@example.com',
            'password': 'testpass123',
        })
        assert login.status_code == 200

        response = api_client.post(REFRESH_URL)
        assert response.status_code == 200
        assert 'access' in response.data

    def test_refresh_without_cookie(self, api_client):
        response = api_client.post(REFRESH_URL)
        assert response.status_code == 401

    def test_refresh_with_invalid_cookie(self, api_client):
        api_client.cookies['refresh_token'] = 'invalid.token.value'
        response = api_client.post(REFRESH_URL)
        assert response.status_code == 401


@pytest.mark.django_db
class TestLogout:
    def test_logout_clears_cookie(self, api_client):
        UserFactory(email='logout@example.com')
        api_client.post(LOGIN_URL, {
            'email': 'logout@example.com',
            'password': 'testpass123',
        })
        response = api_client.post(LOGOUT_URL)
        assert response.status_code == 204
        # Cookie should be expired
        assert response.cookies.get('refresh_token').value == ''

    def test_logout_without_login(self, api_client):
        # 即使無 cookie 也應允許登出（冪等）
        response = api_client.post(LOGOUT_URL)
        assert response.status_code in (204, 401)
