"""WebSocket Consumer 測試 — NotificationConsumer

使用 channels.testing.WebsocketCommunicator 測試：
- 已認證使用者可連線、收到未讀數量
- 未認證使用者被拒絕（close code 4401）
- 接收來自 channel layer 的即時通知推送
- mark_read 操作後更新未讀數量
- 多使用者之間通知隔離
"""
import pytest
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator

from apps.notifications.consumers import NotificationConsumer, _user_group_name
from apps.notifications.models import Notification
from tests.factories import NotificationFactory, UserFactory


def _make_communicator(user=None):
    """建立已認證或未認證的 WebsocketCommunicator。

    直接注入 scope['user'] 跳過 JWT middleware（middleware 有獨立測試）。
    """
    from django.contrib.auth.models import AnonymousUser
    communicator = WebsocketCommunicator(
        NotificationConsumer.as_asgi(),
        '/ws/notifications/',
    )
    communicator.scope['user'] = user or AnonymousUser()
    return communicator


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestNotificationConsumerConnect:
    async def test_authenticated_user_connects_successfully(self):
        """已認證使用者可成功建立 WebSocket 連線。"""
        user = await database_sync_to_async(UserFactory)()
        communicator = _make_communicator(user)
        connected, _ = await communicator.connect()
        assert connected is True

        # 應立即收到 unread_count 訊息
        response = await communicator.receive_json_from()
        assert response['type'] == 'unread_count'
        assert response['count'] == 0
        await communicator.disconnect()

    async def test_anonymous_user_rejected(self):
        """未認證使用者被拒絕，close code = 4401。"""
        communicator = _make_communicator()
        connected, code = await communicator.connect()
        assert connected is False
        assert code == 4401

    async def test_unread_count_reflects_existing_notifications(self):
        """連線時收到正確的未讀數量。"""
        user = await database_sync_to_async(UserFactory)()
        await database_sync_to_async(NotificationFactory.create_batch)(3, recipient=user)

        communicator = _make_communicator(user)
        await communicator.connect()
        response = await communicator.receive_json_from()
        assert response['type'] == 'unread_count'
        assert response['count'] == 3
        await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestNotificationConsumerReceive:
    async def test_notification_push_from_channel_layer(self):
        """透過 channel layer group_send 推送通知到 WebSocket client。"""
        user = await database_sync_to_async(UserFactory)()
        communicator = _make_communicator(user)
        await communicator.connect()
        # 消耗初始 unread_count
        await communicator.receive_json_from()

        channel_layer = get_channel_layer()
        group_name = _user_group_name(user.pk)
        notification_data = {
            'id': '00000000-0000-0000-0000-000000000001',
            'notif_type': 'task_assigned',
            'title': '你被指派了任務「測試」',
            'body': '',
            'payload': {'task_id': '00000000-0000-0000-0000-000000000002'},
            'is_read': False,
            'created_at': '2026-05-11T10:00:00+08:00',
        }
        await channel_layer.group_send(
            group_name,
            {
                'type': 'notification.send',
                'data': notification_data,
            },
        )

        response = await communicator.receive_json_from()
        assert response['type'] == 'notification'
        assert response['data'] == notification_data
        await communicator.disconnect()

    async def test_mark_read_action(self):
        """前端傳送 mark_read action 後通知標為已讀，回傳更新的 unread_count。"""
        user = await database_sync_to_async(UserFactory)()
        notif = await database_sync_to_async(NotificationFactory)(recipient=user)

        communicator = _make_communicator(user)
        await communicator.connect()
        # 消耗初始 unread_count
        initial = await communicator.receive_json_from()
        assert initial['count'] == 1

        # 發送 mark_read
        await communicator.send_json_to({
            'action': 'mark_read',
            'notification_id': str(notif.pk),
        })

        response = await communicator.receive_json_from()
        assert response['type'] == 'unread_count'
        assert response['count'] == 0

        # 驗證 DB 已更新
        await database_sync_to_async(notif.refresh_from_db)()
        assert notif.is_read is True
        assert notif.read_at is not None
        await communicator.disconnect()

    async def test_mark_read_wrong_user_ignored(self):
        """不能標記別人的通知為已讀。"""
        user1 = await database_sync_to_async(UserFactory)()
        user2 = await database_sync_to_async(UserFactory)()
        notif = await database_sync_to_async(NotificationFactory)(recipient=user2)

        communicator = _make_communicator(user1)
        await communicator.connect()
        await communicator.receive_json_from()  # 初始 unread_count

        await communicator.send_json_to({
            'action': 'mark_read',
            'notification_id': str(notif.pk),
        })

        response = await communicator.receive_json_from()
        assert response['type'] == 'unread_count'
        assert response['count'] == 0  # user1 沒有通知

        # user2 的通知仍然未讀
        await database_sync_to_async(notif.refresh_from_db)()
        assert notif.is_read is False
        await communicator.disconnect()


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestNotificationConsumerIsolation:
    async def test_notifications_only_reach_target_user(self):
        """推送只到達目標使用者，不會跨 group 外洩。"""
        user1 = await database_sync_to_async(UserFactory)()
        user2 = await database_sync_to_async(UserFactory)()

        comm1 = _make_communicator(user1)
        comm2 = _make_communicator(user2)
        await comm1.connect()
        await comm2.connect()
        await comm1.receive_json_from()  # initial unread_count
        await comm2.receive_json_from()

        # 只推送給 user1
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            _user_group_name(user1.pk),
            {
                'type': 'notification.send',
                'data': {'id': 'test', 'title': 'for user1 only'},
            },
        )

        response = await comm1.receive_json_from()
        assert response['data']['title'] == 'for user1 only'

        # user2 不應收到任何東西
        assert await comm2.receive_nothing() is True

        await comm1.disconnect()
        await comm2.disconnect()

    async def test_unread_count_update_event(self):
        """unread_count_update 事件正確轉發。"""
        user = await database_sync_to_async(UserFactory)()
        communicator = _make_communicator(user)
        await communicator.connect()
        await communicator.receive_json_from()  # initial

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            _user_group_name(user.pk),
            {
                'type': 'unread_count.update',
                'count': 42,
            },
        )

        response = await communicator.receive_json_from()
        assert response['type'] == 'unread_count'
        assert response['count'] == 42
        await communicator.disconnect()
