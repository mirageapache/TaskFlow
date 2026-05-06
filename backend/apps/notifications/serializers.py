"""Notification Serializer（Phase 2）。"""
from rest_framework import serializers

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id',
            'recipient',
            'notif_type',
            'title', 'body',
            'payload',
            'is_read', 'read_at',
            'created_at',
        ]
        read_only_fields = [
            'id', 'recipient', 'notif_type', 'title', 'body', 'payload',
            'read_at', 'created_at',
        ]
