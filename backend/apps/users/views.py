"""使用者相關 API View。

涵蓋兩組路由：
- `/api/v1/auth/`：註冊、登入、Refresh、Logout（auth_urls.py 對應）
- `/api/v1/users/`：個人資料 `/me/` 與偏好 `/me/profile/`（profile_urls.py 對應）
"""
from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import User, UserProfile
from apps.users.serializers import (
    LoginSerializer,
    MeSerializer,
    RegisterSerializer,
    UserProfileSerializer,
)


REFRESH_COOKIE_KEY = settings.REFRESH_TOKEN_COOKIE['key']


def _set_refresh_cookie(response, refresh_token):
    """將 refresh token 寫入 httpOnly Cookie，避免前端 JS 讀取造成 XSS 風險。"""
    cfg = settings.REFRESH_TOKEN_COOKIE
    response.set_cookie(
        key=cfg['key'],
        value=str(refresh_token),
        httponly=cfg['httponly'],
        secure=cfg['secure'],
        samesite=cfg['samesite'],
        max_age=cfg['max_age'],
    )
    return response


def _issue_tokens_for(user):
    """為指定 User 產生一對 access / refresh JWT。"""
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


class RegisterView(APIView):
    """POST /api/v1/auth/register/  — 註冊新帳號並回傳 access token。"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        tokens = _issue_tokens_for(user)
        response = Response(
            {
                'access': tokens['access'],
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'username': user.username,
                },
            },
            status=status.HTTP_201_CREATED,
        )
        return _set_refresh_cookie(response, tokens['refresh'])


class LoginView(APIView):
    """POST /api/v1/auth/login/  — 帳密登入，發 access token + 設 refresh cookie。"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            # 統一以 401 回覆，避免洩露「帳號存在 vs 密碼錯誤」差異
            raise AuthenticationFailed(detail='帳號或密碼錯誤。')
        user = serializer.validated_data['user']
        tokens = _issue_tokens_for(user)
        response = Response({'access': tokens['access']}, status=status.HTTP_200_OK)
        return _set_refresh_cookie(response, tokens['refresh'])


class RefreshView(APIView):
    """POST /api/v1/auth/refresh/  — 以 cookie 中的 refresh token 換新的 access token。

    若 settings 啟用 `ROTATE_REFRESH_TOKENS`，舊 refresh 會被加入黑名單並換發新的。
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        raw = request.COOKIES.get(REFRESH_COOKIE_KEY)
        if not raw:
            raise AuthenticationFailed(detail='缺少 refresh token。')
        try:
            refresh = RefreshToken(raw)
        except (InvalidToken, TokenError):
            raise AuthenticationFailed(detail='Refresh token 無效或已過期。')

        access = str(refresh.access_token)
        response_payload = {'access': access}

        # ROTATE_REFRESH_TOKENS=True：將舊 token 加入黑名單，並重新發行 refresh
        if settings.SIMPLE_JWT.get('ROTATE_REFRESH_TOKENS'):
            try:
                refresh.blacklist()
            except AttributeError:
                pass
            user_id = refresh.payload.get('user_id')
            user = User.objects.get(pk=user_id)
            new_refresh = RefreshToken.for_user(user)
            response = Response(response_payload, status=status.HTTP_200_OK)
            return _set_refresh_cookie(response, new_refresh)

        return Response(response_payload, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """POST /api/v1/auth/logout/  — 將 refresh token 加入黑名單並清除 cookie（冪等）。"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        raw = request.COOKIES.get(REFRESH_COOKIE_KEY)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except (InvalidToken, TokenError, AttributeError):
                # 即使 token 已過期或無效，仍視為登出成功
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(REFRESH_COOKIE_KEY)
        return response


class MeView(generics.RetrieveUpdateAPIView):
    """GET / PATCH /api/v1/users/me/  — 讀取或更新登入者的基本資料。"""
    serializer_class = MeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """略過 lookup，直接回傳 request.user，確保使用者只能存取自己的資料。"""
        return self.request.user


class MeProfileView(generics.RetrieveUpdateAPIView):
    """GET / PATCH /api/v1/users/me/profile/  — 讀取或更新個人偏好設定。"""
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """若使用者尚未建立 Profile，則 lazy 建立一筆預設值。"""
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
