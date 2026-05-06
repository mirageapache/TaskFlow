"""Event Model 單元測試（Phase 2）。

規格：.doc/taskflow-database.md §3.15
"""
import pytest
from django.utils import timezone

from apps.calendar_events.models import Event
from tests.factories import (
    EventFactory,
    UserFactory,
    WorkspaceFactory,
)


@pytest.mark.django_db
class TestEventModel:
    def test_create_one_off_event(self):
        """單次活動：recurrence_rule 為空字串。"""
        ws = WorkspaceFactory()
        creator = UserFactory()
        start = timezone.now()
        end = start + timezone.timedelta(hours=1)
        event = Event.objects.create(
            workspace=ws,
            creator=creator,
            title='Sprint Planning',
            start_at=start,
            end_at=end,
        )
        assert event.pk is not None
        assert event.recurrence_rule == ''
        assert event.is_all_day is False

    def test_create_recurring_event(self):
        ws = WorkspaceFactory()
        event = EventFactory(
            workspace=ws,
            recurrence_rule='FREQ=WEEKLY;BYDAY=MO,WE,FR',
        )
        assert event.recurrence_rule == 'FREQ=WEEKLY;BYDAY=MO,WE,FR'

    def test_workspace_cascade_deletes_events(self):
        ws = WorkspaceFactory()
        EventFactory(workspace=ws)
        EventFactory(workspace=ws)
        assert Event.objects.filter(workspace=ws).count() == 2
        ws.delete()  # hard delete
        assert Event.objects.filter(workspace_id=ws.id).count() == 0

    def test_creator_set_null_on_user_delete(self):
        creator = UserFactory()
        event = EventFactory(creator=creator)
        creator.delete()
        event.refresh_from_db()
        assert event.creator is None

    def test_default_ordering_is_start_at_ascending(self):
        ws = WorkspaceFactory()
        now = timezone.now()
        e2 = EventFactory(workspace=ws, start_at=now + timezone.timedelta(hours=2))
        e1 = EventFactory(workspace=ws, start_at=now + timezone.timedelta(hours=1))
        ordered = list(Event.objects.filter(workspace=ws))
        assert ordered[0].id == e1.id
        assert ordered[1].id == e2.id

    def test_event_inherits_basemodel_soft_delete(self):
        """Event 繼承 BaseModel，應有 deleted_at 軟刪除欄位。"""
        event = EventFactory()
        event.soft_delete()
        assert event.deleted_at is not None
        # 預設 manager 過濾掉軟刪除
        assert Event.objects.filter(pk=event.pk).count() == 0
        assert Event.all_objects.filter(pk=event.pk).count() == 1
