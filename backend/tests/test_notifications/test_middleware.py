"""WebSocket JWT 認證 Middleware 測試。

測試 JWTAuthMiddleware 從 query_string 解析 token 並注入 scope['user']。
"""
import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

from apps.notifications.consumers import NotificationConsumer
from apps.notifications.middleware import JWTAuthMiddleware
from tests.factories import UserFactory


def _make_app():
    """建立包含 JWTAuthMiddleware 的 ASGI app。"""
    from channels.routing import URLRouter
    from django.urls import re_path
    return JWTAuthMiddleware(
        URLRouter([
            re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
        ])
    )


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestJWTAuthMiddleware:
    async def test_valid_token_authenticates_user(self):
        """有效的 JWT token → scope['user'] 為對應 User。"""
        from channels.db import database_sync_to_async
        user = await database_sync_to_async(UserFactory)()
        token = str(AccessToken.for_user(user))

        app = _make_app()
        communicator = WebsocketCommunicator(app, f'/ws/notifications/?token={token}')
        connected, _ = await communicator.connect()
        assert connected is True

        # 應收到初始 unread_count（代表成功認證）
        response = await communicator.receive_json_from()
        assert response['type'] == 'unread_count'
        await communicator.disconnect()

    async def test_invalid_token_gets_anonymous(self):
        """無效 token → scope['user'] 為 AnonymousUser → 連線被拒。"""
        app = _make_app()
        communicator = WebsocketCommunicator(app, '/ws/notifications/?token=invalid-jwt')
        connected, code = await communicator.connect()
        assert connected is False
        assert code == 4401

    async def test_no_token_gets_anonymous(self):
        """未提供 token → scope['user'] 為 AnonymousUser → 連線被拒。"""
        app = _make_app()
        communicator = WebsocketCommunicator(app, '/ws/notifications/')
        connected, code = await communicator.connect()
        assert connected is False
        assert code == 4401

    async def test_expired_token_rejected(self):
        """過期的 token → 連線被拒。"""
        from channels.db import database_sync_to_async
        from datetime import timedelta
        user = await database_sync_to_async(UserFactory)()
        token = AccessToken.for_user(user)
        token.set_exp(lifetime=-timedelta(hours=1))  # 已過期
        token_str = str(token)

        app = _make_app()
        communicator = WebsocketCommunicator(app, f'/ws/notifications/?token={token_str}')
        connected, code = await communicator.connect()
        assert connected is False
        assert code == 4401
