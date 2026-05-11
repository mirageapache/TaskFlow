"""WebSocket URL routing — 通知即時推送。

詳見 .doc/taskflow-backend.md §4.2
"""
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]
