"""JWT 認證端到端整合測試。

不同於 view 層的單元測試（用 force_authenticate 跳過認證），這裡走完整的
SimpleJWT 簽發 / refresh / 黑名單流程，確保 settings、middleware、
APIView.initial() patch、httpOnly cookie 串接全部正確。

涵蓋情境：
- 註冊後拿到 access、cookie 含 refresh
- 用 access 訪問受保護端點 200
- 沒帶 access 訪問受保護端點 401
- /auth/refresh/ 用 cookie 換新 access
- logout 把 refresh token 加進黑名單，被黑名單過的 refresh 不可再用
"""
import pytest
from django.conf import settings

REGISTER_URL = '/api/v1/auth/register/'
LOGIN_URL = '/api/v1/auth/login/'
REFRESH_URL = '/api/v1/auth/refresh/'
LOGOUT_URL = '/api/v1/auth/logout/'
ME_URL = '/api/v1/users/me/'

REFRESH_COOKIE_KEY = settings.REFRESH_TOKEN_COOKIE['key']


@pytest.mark.django_db
class TestJwtEndToEndFlow:
    """從註冊到登出的完整 JWT 流程；任何一步出錯都代表整合層有問題。"""

    def test_register_then_access_protected_endpoint(self, api_client):
        """註冊成功 → 用回傳的 access token 立刻訪問 /me/ 應 200"""
        register = api_client.post(REGISTER_URL, {
            'email': 'integ@example.com',
            'username': 'integ',
            'password': 'StrongP@ssw0rd!',
        })
        assert register.status_code == 201
        access = register.data['access']
        assert access

        # 帶 access 訪問受保護端點
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        me = api_client.get(ME_URL)
        assert me.status_code == 200
        assert me.data['email'] == 'integ@example.com'

    def test_protected_endpoint_rejects_unauthenticated(self, api_client):
        """未帶 token → /me/ 應 401（confirms IsAuthenticated 預設啟用）"""
        response = api_client.get(ME_URL)
        assert response.status_code == 401

    def test_login_sets_refresh_cookie_and_returns_access(self, api_client, user):
        """login 成功應同時：
        1. response.data 含 access
        2. set-cookie 含 refresh_token（httpOnly）
        """
        user.set_password('LoginPwd1!')
        user.save()

        response = api_client.post(LOGIN_URL, {
            'email': user.email,
            'password': 'LoginPwd1!',
        })
        assert response.status_code == 200
        assert 'access' in response.data
        assert REFRESH_COOKIE_KEY in response.cookies
        # cookie 必須是 httpOnly，避免被 JS 讀
        cookie = response.cookies[REFRESH_COOKIE_KEY]
        assert cookie['httponly']

    def test_refresh_endpoint_issues_new_access(self, api_client, user):
        """用 login 拿到的 refresh cookie 換新 access，新 access 可訪問受保護端點。"""
        user.set_password('LoginPwd1!')
        user.save()
        login = api_client.post(LOGIN_URL, {
            'email': user.email,
            'password': 'LoginPwd1!',
        })
        assert login.status_code == 200
        # api_client 會在 cookie jar 自動維持 cookie，後續 request 自動帶上

        refresh_response = api_client.post(REFRESH_URL)
        assert refresh_response.status_code == 200
        new_access = refresh_response.data['access']
        assert new_access
        # 新 access 不應與舊 access 相同
        assert new_access != login.data['access']

        # 用新 access 確認可正常訪問
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access}')
        me = api_client.get(ME_URL)
        assert me.status_code == 200

    def test_logout_blacklists_refresh_token(self, api_client, user):
        """logout 後再用同一個 refresh cookie 應該被拒絕（已黑名單）。"""
        user.set_password('LoginPwd1!')
        user.save()
        login = api_client.post(LOGIN_URL, {
            'email': user.email,
            'password': 'LoginPwd1!',
        })
        access = login.data['access']

        # 1. 登出（需要 access token 認證，refresh 由 cookie 自動帶）
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        logout = api_client.post(LOGOUT_URL)
        assert logout.status_code in (200, 204)

        # 2. 試圖用同一個 refresh cookie 再換 access → 應失敗
        api_client.credentials()  # 清掉 access header（避免干擾）
        retry = api_client.post(REFRESH_URL)
        assert retry.status_code == 401


@pytest.mark.django_db
class TestJwtAuthClientFixture:
    """驗證 jwt_auth_client fixture 能用真實 token 通過認證。"""

    def test_jwt_auth_client_can_access_protected_endpoint(self, jwt_auth_client):
        response = jwt_auth_client.get(ME_URL)
        assert response.status_code == 200

    def test_jwt_auth_client_token_is_actual_jwt(self, jwt_auth_client, user):
        """fixture 設定的 Authorization header 應該是 Bearer + JWT，
        不是 force_authenticate 的假 session。"""
        # APIClient.credentials 會把 header 存到 _credentials
        creds = jwt_auth_client._credentials
        assert 'HTTP_AUTHORIZATION' in creds
        token = creds['HTTP_AUTHORIZATION'].replace('Bearer ', '')
        # JWT 至少有兩個 dot（header.payload.signature）
        assert token.count('.') == 2
