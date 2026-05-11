"""整合測試 — Celery task 建立通知後透過 Channel Layer 推送至 WebSocket。

驗證 notifications/tasks.py 的 _push_notification_to_ws 整合流程。
"""
import pytest
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator

from apps.notifications.consumers import NotificationConsumer
from tests.factories import UserFactory, TaskFactory


def _make_communicator(user):
    from django.contrib.auth.models import AnonymousUser
    communicator = WebsocketCommunicator(
        NotificationConsumer.as_asgi(),
        '/ws/notifications/',
    )
    communicator.scope['user'] = user or AnonymousUser()
    return communicator


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestWebSocketPushIntegration:
    async def test_task_assigned_pushes_to_websocket(self):
        """create_task_assigned_notification task 建立通知後推送到 WS client。"""
        from apps.notifications.tasks import create_task_assigned_notification
        from apps.tasks.models import TaskAssignee

        user = await database_sync_to_async(UserFactory)()
        task = await database_sync_to_async(TaskFactory)()

        communicator = _make_communicator(user)
        await communicator.connect()
        await communicator.receive_json_from()  # 初始 unread_count

        # 同步呼叫 Celery task（eager 模式）
        await database_sync_to_async(create_task_assigned_notification)(
            recipient_id=str(user.pk),
            task_id=str(task.pk),
            task_title=task.title,
        )

        response = await communicator.receive_json_from()
        assert response['type'] == 'notification'
        assert response['data']['notif_type'] == 'task_assigned'
        assert task.title in response['data']['title']
        await communicator.disconnect()

    async def test_workspace_invite_pushes_to_websocket(self):
        """create_workspace_invite_notification task 建立通知後推送到 WS client。"""
        from apps.notifications.tasks import create_workspace_invite_notification
        from tests.factories import WorkspaceFactory

        user = await database_sync_to_async(UserFactory)()
        workspace = await database_sync_to_async(WorkspaceFactory)()

        communicator = _make_communicator(user)
        await communicator.connect()
        await communicator.receive_json_from()

        await database_sync_to_async(create_workspace_invite_notification)(
            recipient_id=str(user.pk),
            workspace_id=str(workspace.pk),
            workspace_name=workspace.name,
        )

        response = await communicator.receive_json_from()
        assert response['type'] == 'notification'
        assert response['data']['notif_type'] == 'workspace_invite'
        assert workspace.name in response['data']['title']
        await communicator.disconnect()
