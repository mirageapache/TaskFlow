"""Calendar Event API 測試（Phase 2）。

端點：
  /api/v1/calendar/                       GET, POST
  /api/v1/calendar/{id}/                  GET, PATCH, DELETE

行為重點：
- 必須登入、且只能看到 user 所屬 workspace 的 events
- 列表支援 ?workspace=&start=&end= 範圍過濾
- 重複行程：?expand=true 時回傳該範圍內展開後的 occurrences（每筆含 start_at/end_at）
"""
import datetime

import pytest
from django.utils import timezone

from apps.calendar_events.models import Event
from tests.factories import (
    EventFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMemberFactory,
)

CALENDAR_URL = '/api/v1/calendar/'


# ────────────────  CRUD ────────────────


@pytest.mark.django_db
class TestEventList:
    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(CALENDAR_URL)
        assert response.status_code == 401

    def test_list_returns_only_events_in_my_workspaces(self, auth_client, user):
        my_ws = WorkspaceFactory(owner=user)
        EventFactory(workspace=my_ws, title='Mine')

        other_ws = WorkspaceFactory()  # 我不是成員
        EventFactory(workspace=other_ws, title='NotMine')

        response = auth_client.get(CALENDAR_URL)
        assert response.status_code == 200
        titles = [e['title'] for e in response.data['results']]
        assert 'Mine' in titles
        assert 'NotMine' not in titles

    def test_filter_by_workspace_query(self, auth_client, user):
        ws_a = WorkspaceFactory(owner=user)
        ws_b = WorkspaceFactory(owner=user)
        EventFactory(workspace=ws_a, title='A')
        EventFactory(workspace=ws_b, title='B')

        response = auth_client.get(f'{CALENDAR_URL}?workspace={ws_a.id}')
        assert response.status_code == 200
        titles = [e['title'] for e in response.data['results']]
        assert titles == ['A']

    def test_filter_by_date_range(self, auth_client, user):
        ws = WorkspaceFactory(owner=user)
        now = timezone.now()
        EventFactory(workspace=ws, title='past', start_at=now - datetime.timedelta(days=10),
                     end_at=now - datetime.timedelta(days=10) + datetime.timedelta(hours=1))
        EventFactory(workspace=ws, title='in-range', start_at=now,
                     end_at=now + datetime.timedelta(hours=1))
        EventFactory(workspace=ws, title='future', start_at=now + datetime.timedelta(days=10),
                     end_at=now + datetime.timedelta(days=10) + datetime.timedelta(hours=1))

        start = (now - datetime.timedelta(days=1)).isoformat().replace('+00:00', 'Z')
        end = (now + datetime.timedelta(days=1)).isoformat().replace('+00:00', 'Z')
        response = auth_client.get(f'{CALENDAR_URL}?start={start}&end={end}')

        assert response.status_code == 200
        titles = [e['title'] for e in response.data['results']]
        assert titles == ['in-range']


@pytest.mark.django_db
class TestEventCreate:
    def test_workspace_member_can_create_event(self, auth_client, user):
        ws = WorkspaceFactory(owner=user)
        now = timezone.now()
        response = auth_client.post(CALENDAR_URL, {
            'workspace_id': str(ws.id),
            'title': 'Sprint Planning',
            'start_at': now.isoformat().replace('+00:00', 'Z'),
            'end_at': (now + datetime.timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),
        }, format='json')
        assert response.status_code == 201
        assert response.data['title'] == 'Sprint Planning'
        assert Event.objects.filter(workspace=ws).count() == 1

    def test_non_member_cannot_create_event(self, api_client, other_user):
        ws = WorkspaceFactory()  # other_user 不是成員
        api_client.force_authenticate(user=other_user)
        now = timezone.now()
        response = api_client.post(CALENDAR_URL, {
            'workspace_id': str(ws.id),
            'title': 'Forbidden',
            'start_at': now.isoformat().replace('+00:00', 'Z'),
            'end_at': (now + datetime.timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),
        }, format='json')
        assert response.status_code == 403

    def test_end_at_before_start_at_returns_400(self, auth_client, user):
        ws = WorkspaceFactory(owner=user)
        now = timezone.now()
        response = auth_client.post(CALENDAR_URL, {
            'workspace_id': str(ws.id),
            'title': 'Bad',
            'start_at': now.isoformat().replace('+00:00', 'Z'),
            'end_at': (now - datetime.timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),
        }, format='json')
        assert response.status_code == 400

    def test_invalid_recurrence_rule_returns_400(self, auth_client, user):
        ws = WorkspaceFactory(owner=user)
        now = timezone.now()
        response = auth_client.post(CALENDAR_URL, {
            'workspace_id': str(ws.id),
            'title': 'Bad RRULE',
            'start_at': now.isoformat().replace('+00:00', 'Z'),
            'end_at': (now + datetime.timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),
            'recurrence_rule': 'NOT_A_VALID_RRULE',
        }, format='json')
        assert response.status_code == 400


@pytest.mark.django_db
class TestEventDetail:
    def test_member_can_update_event(self, auth_client, user):
        ws = WorkspaceFactory(owner=user)
        event = EventFactory(workspace=ws)
        response = auth_client.patch(
            f'{CALENDAR_URL}{event.id}/',
            {'title': 'Updated'}, format='json',
        )
        assert response.status_code == 200
        assert response.data['title'] == 'Updated'

    def test_non_member_cannot_view_event(self, api_client, other_user):
        ws = WorkspaceFactory()
        event = EventFactory(workspace=ws)
        api_client.force_authenticate(user=other_user)
        response = api_client.get(f'{CALENDAR_URL}{event.id}/')
        assert response.status_code == 403

    def test_member_can_soft_delete_event(self, auth_client, user):
        ws = WorkspaceFactory(owner=user)
        event = EventFactory(workspace=ws)
        response = auth_client.delete(f'{CALENDAR_URL}{event.id}/')
        assert response.status_code == 204
        event.refresh_from_db()
        assert event.deleted_at is not None


# ────────────────  RRULE expansion ────────────────


@pytest.mark.django_db
class TestRecurrenceExpansion:
    """?expand=true 時，重複行程展開為查詢區間內的 occurrences。

    展開規則：每個 occurrence 維持與原 event 的時段長度（end_at - start_at）。
    """

    def test_expand_returns_occurrences_within_range(self, auth_client, user):
        ws = WorkspaceFactory(owner=user)
        # 從週一 09:00 起每週一三五，共 6 週可能命中
        start = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0) \
            - datetime.timedelta(days=timezone.now().weekday())  # 對齊到本週週一
        EventFactory(
            workspace=ws,
            title='Standup',
            start_at=start,
            end_at=start + datetime.timedelta(minutes=30),
            recurrence_rule='FREQ=WEEKLY;BYDAY=MO,WE,FR;COUNT=6',
        )

        # 查詢 start 起兩週的範圍 → 預期 6 occurrences
        end = start + datetime.timedelta(days=14)
        response = auth_client.get(
            f'{CALENDAR_URL}?expand=true&start={start.isoformat().replace('+00:00', 'Z')}&end={end.isoformat().replace('+00:00', 'Z')}'
        )
        assert response.status_code == 200
        # 沒分頁包裝（expand 直接回 list），或把 results 拿出來都接受
        items = response.data if isinstance(response.data, list) else response.data['results']
        assert len(items) == 6
        # 每筆都有完整的 start_at / end_at
        for occ in items:
            assert 'start_at' in occ
            assert 'end_at' in occ
            assert occ['title'] == 'Standup'

    def test_one_off_event_appears_once_in_expand(self, auth_client, user):
        ws = WorkspaceFactory(owner=user)
        now = timezone.now()
        EventFactory(
            workspace=ws, title='Once',
            start_at=now, end_at=now + datetime.timedelta(hours=1),
            recurrence_rule='',
        )

        end = now + datetime.timedelta(days=30)
        response = auth_client.get(
            f'{CALENDAR_URL}?expand=true&start={now.isoformat().replace('+00:00', 'Z')}&end={end.isoformat().replace('+00:00', 'Z')}'
        )
        assert response.status_code == 200
        items = response.data if isinstance(response.data, list) else response.data['results']
        once_items = [i for i in items if i['title'] == 'Once']
        assert len(once_items) == 1

    def test_expand_requires_start_and_end(self, auth_client, user):
        WorkspaceFactory(owner=user)
        response = auth_client.get(f'{CALENDAR_URL}?expand=true')
        assert response.status_code == 400


# ────────────────  Member workspace（不只 owner）也能操作 ────────────────


@pytest.mark.django_db
class TestMemberAccess:
    def test_workspace_member_can_list_events(self, api_client):
        u = UserFactory()
        ws = WorkspaceFactory()  # 別人擁有
        WorkspaceMemberFactory(workspace=ws, user=u, role='member')
        EventFactory(workspace=ws, title='Visible')

        api_client.force_authenticate(user=u)
        response = api_client.get(f'{CALENDAR_URL}?workspace={ws.id}')
        assert response.status_code == 200
        titles = [e['title'] for e in response.data['results']]
        assert 'Visible' in titles
