"""Calendar Event API Views（Phase 2）。

端點：
- GET /api/v1/calendar/                列出我能存取的事件，可帶 ?workspace= / ?start= / ?end= / ?expand=
- POST /api/v1/calendar/               建立事件（必須是該 workspace 的成員）
- GET / PATCH / DELETE /api/v1/calendar/{id}/

權限：必須為 event.workspace 的 owner 或 member（與 Workspace API 對齊）。
"""
import datetime
from typing import Iterable

from dateutil import parser as date_parser, rrule
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.calendar_events.models import Event
from apps.calendar_events.serializers import EventSerializer
from apps.workspaces.models import Workspace, WorkspaceMember


def _user_in_workspace(user, workspace):
    if workspace.owner_id == user.id:
        return True
    return WorkspaceMember.objects.filter(workspace=workspace, user=user).exists()


def _accessible_workspace_ids(user) -> list:
    """user 為 owner 或 member 的所有 workspace id。"""
    return list(
        Workspace.objects.filter(
            Q(owner=user) | Q(members__user=user),
        ).values_list('id', flat=True).distinct()
    )


def _parse_iso_or_400(value: str, field: str) -> datetime.datetime:
    try:
        return date_parser.isoparse(value)
    except (ValueError, TypeError):
        raise ValidationError({field: '時間格式錯誤，需為 ISO 8601。'})


def _expand_event(event: Event, range_start: datetime.datetime, range_end: datetime.datetime) -> Iterable[dict]:
    """把事件展開為 [range_start, range_end) 內的 occurrences，每筆是 dict。"""
    duration = event.end_at - event.start_at
    base = EventSerializer(event).data

    if not event.recurrence_rule:
        # 單次：在範圍內就回一筆
        if range_start <= event.start_at < range_end:
            yield base
        return

    # 重複：用 dateutil 展開
    rule = rrule.rrulestr(f'RRULE:{event.recurrence_rule}', dtstart=event.start_at)
    for occ_start in rule.between(range_start, range_end, inc=True):
        yield {
            **base,
            'start_at': occ_start.isoformat(),
            'end_at': (occ_start + duration).isoformat(),
        }


class EventListCreateView(generics.ListCreateAPIView):
    """GET / POST /api/v1/calendar/"""
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Event.objects.filter(
            workspace_id__in=_accessible_workspace_ids(self.request.user),
        )
        ws_id = self.request.query_params.get('workspace')
        if ws_id:
            qs = qs.filter(workspace_id=ws_id)
        start = self.request.query_params.get('start')
        end = self.request.query_params.get('end')
        if start:
            qs = qs.filter(start_at__gte=_parse_iso_or_400(start, 'start'))
        if end:
            qs = qs.filter(start_at__lte=_parse_iso_or_400(end, 'end'))
        return qs.order_by('start_at')

    def list(self, request, *args, **kwargs):
        if request.query_params.get('expand') == 'true':
            return self._list_expanded(request)
        return super().list(request, *args, **kwargs)

    def _list_expanded(self, request):
        start = request.query_params.get('start')
        end = request.query_params.get('end')
        if not start or not end:
            raise ValidationError({
                'expand': '使用 expand=true 時必須同時帶 start 與 end。',
            })
        range_start = _parse_iso_or_400(start, 'start')
        range_end = _parse_iso_or_400(end, 'end')

        # 找候選事件：start_at <= range_end（重複事件可能更早就開始，這裡先粗篩）
        # 接著由 _expand_event 用 RRULE 精算實際 occurrences
        qs = Event.objects.filter(
            workspace_id__in=_accessible_workspace_ids(request.user),
            start_at__lte=range_end,
        )
        ws_id = request.query_params.get('workspace')
        if ws_id:
            qs = qs.filter(workspace_id=ws_id)

        results: list = []
        for event in qs:
            results.extend(_expand_event(event, range_start, range_end))
        return Response(results)

    def perform_create(self, serializer):
        ws_id = serializer.validated_data.get('workspace_id')
        if not ws_id:
            raise ValidationError({'workspace_id': '此欄位為必填。'})
        ws = get_object_or_404(Workspace, pk=ws_id)
        if not _user_in_workspace(self.request.user, ws):
            raise PermissionDenied('您不是此工作區的成員。')
        serializer.save(workspace=ws, creator=self.request.user)


class EventDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET / PATCH / DELETE /api/v1/calendar/{id}/"""
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Event.objects.all()

    def get_object(self):
        event = super().get_object()
        if not _user_in_workspace(self.request.user, event.workspace):
            raise PermissionDenied('您不是此工作區的成員。')
        return event

    def perform_destroy(self, instance):
        instance.soft_delete()
