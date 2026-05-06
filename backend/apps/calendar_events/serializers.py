"""Event Serializer + RRULE 驗證（Phase 2）。"""
from dateutil import rrule
from rest_framework import serializers

from apps.calendar_events.models import Event


def validate_rrule_string(value: str) -> str:
    """空字串代表單次活動，直接通過；非空時用 dateutil 解析確認 syntax。"""
    if not value:
        return value
    try:
        # 用任意 dtstart 嘗試解析；若 syntax 錯誤會 raise
        rrule.rrulestr(f'RRULE:{value}', dtstart=__import__('datetime').datetime(2000, 1, 1))
    except (ValueError, TypeError) as exc:
        raise serializers.ValidationError(f'recurrence_rule 格式錯誤：{exc}')
    return value


class EventSerializer(serializers.ModelSerializer):
    """事件 Serializer：寫入時帶 `workspace_id`，讀取時 `workspace` 為 UUID。"""
    workspace_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Event
        fields = [
            'id',
            'workspace', 'workspace_id',
            'creator',
            'title', 'description',
            'start_at', 'end_at',
            'is_all_day',
            'recurrence_rule',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'workspace', 'creator', 'created_at', 'updated_at']

    def validate_recurrence_rule(self, value):
        return validate_rrule_string(value)

    def validate(self, attrs):
        start = attrs.get('start_at') or getattr(self.instance, 'start_at', None)
        end = attrs.get('end_at') or getattr(self.instance, 'end_at', None)
        if start and end and end <= start:
            raise serializers.ValidationError({
                'end_at': 'end_at 必須晚於 start_at。',
            })
        return attrs
