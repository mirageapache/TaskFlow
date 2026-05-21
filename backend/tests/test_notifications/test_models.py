"""Notification Model 測試（Phase 2）。

規格：.doc/taskflow-database.md §3.14
"""
import pytest

from apps.notifications.models import Notification
from tests.factories import NotificationFactory, UserFactory


@pytest.mark.django_db
class TestNotificationModel:
    def test_create_notification(self):
        u = UserFactory()
        n = Notification.objects.create(
            recipient=u,
            notif_type=Notification.NotifType.TASK_ASSIGNED,
            title='You were assigned a task',
            body='Task: implement feature',
            payload={'task_id': 'abc'},
        )
        assert n.pk is not None
        assert n.is_read is False
        assert n.read_at is None

    def test_recipient_cascade_on_user_delete(self):
        u = UserFactory()
        n = NotificationFactory(recipient=u)
        u.delete()
        assert Notification.objects.filter(pk=n.pk).count() == 0

    def test_default_ordering_is_created_at_desc(self):
        u = UserFactory()
        n1 = NotificationFactory(recipient=u)
        n2 = NotificationFactory(recipient=u)
        ordered = list(Notification.objects.filter(recipient=u))
        assert ordered[0].id == n2.id  # 較新在前
        assert ordered[1].id == n1.id

    def test_inherits_basemodel_soft_delete(self):
        n = NotificationFactory()
        n.soft_delete()
        assert Notification.objects.filter(pk=n.pk).count() == 0
        assert Notification.all_objects.filter(pk=n.pk).count() == 1

    def test_payload_persists_as_dict(self):
        n = NotificationFactory(payload={'task_id': 't1', 'comment_id': 'c1'})
        n.refresh_from_db()
        assert n.payload == {'task_id': 't1', 'comment_id': 'c1'}
