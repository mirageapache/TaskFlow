"""
ASGI entrypoint — Django Channels ProtocolTypeRouter
HTTP 走 Django ASGI，WebSocket 走 Channels routing。
詳見 .doc/taskflow-backend.md §4.2
"""
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 必須在 django.setup() 之前（get_asgi_application 內部會呼叫）才 import routing
django_asgi_app = get_asgi_application()

import apps.notifications.routing as notification_routing  # noqa: E402
from apps.notifications.middleware import JWTAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': JWTAuthMiddleware(
        URLRouter(notification_routing.websocket_urlpatterns)
    ),
})
