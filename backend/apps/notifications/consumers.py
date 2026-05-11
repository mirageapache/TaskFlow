"""WebSocket Consumer — 即時通知推送。

前端以 `ws://host/ws/notifications/?token=<jwt>` 連線，
Consumer 依據認證結果決定是否接受連線，並將使用者加入
以 user_id 命名的 Channel Group，供後端推送使用。

推送格式：
{
    "type": "notification",
    "data": {
        "id": "<uuid>",
        "notif_type": "task_assigned",
        "title": "...",
        "body": "...",
        "payload": {...},
        "is_read": false,
        "created_at": "2026-..."
    }
}

另支援 `unread_count` 推送：
{
    "type": "unread_count",
    "count": 5
}
"""
import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


def _user_group_name(user_id) -> str:
    """統一的 group name 產生函式，供 consumer 與 task 共用。"""
    return f'notifications_{user_id}'


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """每位已認證使用者維持一條 WebSocket 連線，接收即時通知。"""

    async def connect(self):
        user = self.scope.get('user', AnonymousUser())
        if not user or user.is_anonymous:
            await self.close(code=4401)
            return

        self.group_name = _user_group_name(user.pk)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # 連線後立即推送目前未讀數量
        count = await self._get_unread_count(user)
        await self.send_json({
            'type': 'unread_count',
            'count': count,
        })

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        """處理前端傳來的訊息。

        目前僅支援 mark_read 操作：
        { "action": "mark_read", "notification_id": "<uuid>" }
        """
        action = content.get('action')
        if action == 'mark_read':
            notification_id = content.get('notification_id')
            if notification_id:
                user = self.scope['user']
                await self._mark_notification_read(user, notification_id)
                count = await self._get_unread_count(user)
                await self.send_json({
                    'type': 'unread_count',
                    'count': count,
                })

    # ── Channel Layer event handlers ─────────────────────────────────
    # 這些 method 由 channel_layer.group_send() 觸發

    async def notification_send(self, event):
        """接收從 Celery task 推送來的通知，轉發給 WebSocket client。"""
        await self.send_json({
            'type': 'notification',
            'data': event['data'],
        })

    async def unread_count_update(self, event):
        """接收未讀數量更新事件。"""
        await self.send_json({
            'type': 'unread_count',
            'count': event['count'],
        })

    # ── DB helpers ───────────────────────────────────────────────────

    @database_sync_to_async
    def _get_unread_count(self, user):
        from apps.notifications.models import Notification
        return Notification.objects.filter(recipient=user, is_read=False).count()

    @database_sync_to_async
    def _mark_notification_read(self, user, notification_id):
        from django.utils import timezone
        from apps.notifications.models import Notification
        Notification.objects.filter(
            pk=notification_id, recipient=user, is_read=False,
        ).update(is_read=True, read_at=timezone.now())
