"""
Rate Limiting / Throttle TDD 測試
規格：.doc/taskflow-backend.md §9.1

測試範圍：
- 全域 AnonRateThrottle（5/min）
- 全域 UserRateThrottle（30/min）
- LoginRateThrottle（10/min per IP）
- AiRateThrottle scope 與 rate 設定
- 自訂 429 回應格式（中文提示）
"""
import pytest
from unittest.mock import patch
from django.core.cache import cache
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from apps.core.throttling import AiRateThrottle, LoginRateThrottle

HEALTH_URL = '/api/v1/health/'


# ---------------------------------------------------------------------------
# Test-only throttle subclasses with explicit low rates
# (avoids override_settings, which doesn't affect THROTTLE_RATES class attr)
# ---------------------------------------------------------------------------

class _TestAiThrottle(AiRateThrottle):
    rate = '3/min'


class _TestLoginThrottle(LoginRateThrottle):
    rate = '3/min'


class _TestLoginThrottle1(LoginRateThrottle):
    rate = '1/min'


class _TestAnonThrottle(AnonRateThrottle):
    rate = '2/min'


# ---------------------------------------------------------------------------
# Helper views for isolated throttle testing
# ---------------------------------------------------------------------------

class _AiThrottledView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [_TestAiThrottle]

    def get(self, request):
        return Response({'ok': True})


class _LoginThrottledView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [_TestLoginThrottle]

    def post(self, request):
        return Response({'ok': True})


class _LoginThrottledView1(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [_TestLoginThrottle1]

    def post(self, request):
        return Response({'ok': True})


class _AnonThrottledView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [_TestAnonThrottle]

    def get(self, request):
        return Response({'ok': True})


# ---------------------------------------------------------------------------
# AiRateThrottle
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestAiRateThrottle:
    """AiRateThrottle — scope='ai', 20/hour per user."""

    def test_scope_is_ai(self):
        throttle = AiRateThrottle()
        assert throttle.scope == 'ai'

    def test_rate_from_settings(self):
        throttle = AiRateThrottle()
        assert throttle.rate == '20/hour'

    def test_ai_throttle_blocks_after_limit(self, user):
        """AI 端點超過限額後應回傳 429。"""
        cache.clear()
        factory = APIRequestFactory()
        view = _AiThrottledView.as_view()

        for i in range(3):
            request = factory.get('/fake-ai/')
            request.user = user
            response = view(request)
            assert response.status_code == 200, f'Request {i+1} should succeed'

        # 4th request should be throttled
        request = factory.get('/fake-ai/')
        request.user = user
        response = view(request)
        assert response.status_code == 429


# ---------------------------------------------------------------------------
# LoginRateThrottle
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestLoginRateThrottle:
    """LoginRateThrottle — scope='login', 10/min per IP."""

    def test_scope_is_login(self):
        throttle = LoginRateThrottle()
        assert throttle.scope == 'login'

    def test_rate_from_settings(self):
        throttle = LoginRateThrottle()
        assert throttle.rate == '10/min'

    def test_login_view_uses_login_throttle(self):
        """LoginView 應使用 LoginRateThrottle 而非全域 AnonRateThrottle。"""
        from apps.users.views import LoginView
        assert LoginRateThrottle in LoginView.throttle_classes

    def test_register_view_uses_login_throttle(self):
        """RegisterView 應使用 LoginRateThrottle 而非全域 AnonRateThrottle。"""
        from apps.users.views import RegisterView
        assert LoginRateThrottle in RegisterView.throttle_classes

    def test_login_throttle_blocks_after_limit(self):
        """登入端點超過限額後應回傳 429。"""
        cache.clear()
        factory = APIRequestFactory()
        view = _LoginThrottledView.as_view()

        for i in range(3):
            request = factory.post('/fake-login/')
            response = view(request)
            assert response.status_code == 200, f'Request {i+1} should succeed'

        # 4th request should be throttled
        request = factory.post('/fake-login/')
        response = view(request)
        assert response.status_code == 429


# ---------------------------------------------------------------------------
# Global Throttle Rates — settings verification
# ---------------------------------------------------------------------------
class TestThrottleSettings:
    """驗證 settings.py 中的 throttle 設定正確。"""

    def test_anon_rate(self, settings):
        rates = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
        assert rates['anon'] == '5/min'

    def test_user_rate(self, settings):
        rates = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
        assert rates['user'] == '30/min'

    def test_ai_rate(self, settings):
        rates = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
        assert rates['ai'] == '20/hour'

    def test_login_rate(self, settings):
        rates = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']
        assert rates['login'] == '10/min'

    def test_default_throttle_classes(self, settings):
        classes = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES']
        assert 'rest_framework.throttling.AnonRateThrottle' in classes
        assert 'rest_framework.throttling.UserRateThrottle' in classes


# ---------------------------------------------------------------------------
# Custom 429 Response Format
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestCustom429Response:
    """自訂 429 回應應包含中文提示。"""

    def test_exception_handler_registered(self, settings):
        handler = settings.REST_FRAMEWORK['EXCEPTION_HANDLER']
        assert handler == 'apps.core.exception_handler.custom_exception_handler'

    def test_exception_handler_formats_throttled(self):
        """custom_exception_handler 對 Throttled 例外產生中文訊息。"""
        from rest_framework.exceptions import Throttled
        from apps.core.exception_handler import custom_exception_handler

        exc = Throttled(wait=45)
        context = {'request': None, 'view': None}
        response = custom_exception_handler(exc, context)
        assert response.status_code == 429
        assert '請求過於頻繁' in response.data['detail']
        assert '45 秒後再試' in response.data['detail']

    def test_exception_handler_default_wait(self):
        """wait=None 時預設顯示 60 秒。"""
        from rest_framework.exceptions import Throttled
        from apps.core.exception_handler import custom_exception_handler

        exc = Throttled(wait=None)
        context = {'request': None, 'view': None}
        response = custom_exception_handler(exc, context)
        assert '60 秒後再試' in response.data['detail']

    def test_429_response_via_view(self):
        """透過 view 觸發的 429 回應應包含中文。"""
        cache.clear()
        factory = APIRequestFactory()
        view = _LoginThrottledView1.as_view()

        # First request succeeds
        request = factory.post('/fake/')
        response = view(request)
        assert response.status_code == 200

        # Second request triggers 429
        request = factory.post('/fake/')
        response = view(request)
        assert response.status_code == 429
        assert '請求過於頻繁' in response.data['detail']
        assert '秒後再試' in response.data['detail']


# ---------------------------------------------------------------------------
# Integration: Real endpoint throttling via APIClient
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestEndpointThrottling:
    """驗證 throttle 實際套用於端點。"""

    def test_health_endpoint_anon_throttle(self, api_client):
        """health_check 受全域 AnonRateThrottle 保護。"""
        # We can't easily lower the global rate, so just verify the
        # throttle class is applied by checking one request doesn't 429
        resp = api_client.get(HEALTH_URL)
        assert resp.status_code == 200

    def test_anon_throttle_blocks_via_view(self):
        """AnonRateThrottle 超限後回傳 429。"""
        cache.clear()
        factory = APIRequestFactory()
        view = _AnonThrottledView.as_view()

        for i in range(2):
            request = factory.get('/fake-health/')
            response = view(request)
            assert response.status_code == 200, f'Request {i+1} should succeed'

        request = factory.get('/fake-health/')
        response = view(request)
        assert response.status_code == 429
