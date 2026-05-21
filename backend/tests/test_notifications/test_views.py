"""Notification API 測試（Phase 2）。

端點：
  GET  /api/v1/notifications/              列出自己的通知
  PATCH /api/v1/notifications/{id}/         單筆標已讀（is_read=True 同時寫 read_at）
  POST /api/v1/notifications/mark-all-read/ 全部標已讀
"""
import pytest

from apps.notifications.models import Notification
from tests.factories import NotificationFactory, UserFactory

NOTIF_URL = '/api/v1/notifications/'
MARK_ALL_URL = '/api/v1/notifications/mark-all-read/'


@pytest.mark.django_db
class TestNotificationList:
    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(NOTIF_URL)
        assert response.status_code == 401

    def test_lists_only_own_notifications(self, auth_client, user, other_user):
        NotificationFactory(recipient=user, title='mine')
        NotificationFactory(recipient=other_user, title='theirs')

        response = auth_client.get(NOTIF_URL)
        assert response.status_code == 200
        titles = [n['title'] for n in response.data['results']]
        assert 'mine' in titles
        assert 'theirs' not in titles

    def test_filter_unread_only(self, auth_client, user):
        NotificationFactory(recipient=user, is_read=True, title='read')
        NotificationFactory(recipient=user, is_read=False, title='unread')

        response = auth_client.get(f'{NOTIF_URL}?is_read=false')
        assert response.status_code == 200
        titles = [n['title'] for n in response.data['results']]
        assert titles == ['unread']


@pytest.mark.django_db
class TestNotificationMarkRead:
    def test_mark_single_as_read(self, auth_client, user):
        n = NotificationFactory(recipient=user, is_read=False)
        response = auth_client.patch(f'{NOTIF_URL}{n.id}/', {'is_read': True}, format='json')
        assert response.status_code == 200
        n.refresh_from_db()
        assert n.is_read is True
        assert n.read_at is not None

    def test_cannot_mark_others_notification(self, auth_client, other_user):
        n = NotificationFactory(recipient=other_user)
        response = auth_client.patch(f'{NOTIF_URL}{n.id}/', {'is_read': True}, format='json')
        # 別人的通知對我而言應該 404（隔離），不是 403
        assert response.status_code == 404

    def test_mark_all_read_endpoint_marks_only_own_unread(self, auth_client, user, other_user):
        NotificationFactory(recipient=user, is_read=False)
        NotificationFactory(recipient=user, is_read=False)
        other_n = NotificationFactory(recipient=other_user, is_read=False)

        response = auth_client.post(MARK_ALL_URL)
        assert response.status_code == 200
        # 自己的兩筆都應為已讀
        assert Notification.objects.filter(
            recipient=user, is_read=True,
        ).count() == 2
        # 別人的不應被改
        other_n.refresh_from_db()
        assert other_n.is_read is False

    def test_mark_all_read_response_returns_count(self, auth_client, user):
        NotificationFactory(recipient=user, is_read=False)
        NotificationFactory(recipient=user, is_read=False)
        NotificationFactory(recipient=user, is_read=True)  # 已讀的不算

        response = auth_client.post(MARK_ALL_URL)
        assert response.status_code == 200
        assert response.data == {'updated': 2}
