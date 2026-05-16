"""自訂 DRF Throttle Classes。

- AiRateThrottle：AI 端點專用，scope='ai'（20/hour）
- LoginRateThrottle：登入/註冊端點，scope='login'（10/min per IP）
"""
from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle


class AiRateThrottle(UserRateThrottle):
    """AI 端點限流，對應 settings.DEFAULT_THROTTLE_RATES['ai'] = '20/hour'。"""
    scope = 'ai'


class LoginRateThrottle(SimpleRateThrottle):
    """登入/註冊端點限流，以 IP 為單位。

    對應 settings.DEFAULT_THROTTLE_RATES['login'] = '10/min'。
    比全域 AnonRateThrottle (5/min) 寬鬆，但專屬於 auth 端點，
    不與其他匿名請求共用配額。
    """
    scope = 'login'

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': self.get_ident(request),
        }
