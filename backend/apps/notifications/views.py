"""Notification API Views（Phase 2）。

端點：
- GET   /api/v1/notifications/              列出自己的通知（支援 ?is_read=true|false 過濾）
- PATCH /api/v1/notifications/{id}/         標單筆已讀（記 read_at）
- POST  /api/v1/notifications/mark-all-read/ 一次標所有未讀

設計：
- 通知是私人資料；queryset 一律 filter(recipient=request.user)，跨使用者一律當不存在（404）
- 僅 `is_read` 可寫；其餘欄位由 signal 寫入後不可改
"""
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    """GET /api/v1/notifications/"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user)
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            # 'true' / 'false' / '1' / '0' 都接受
            qs = qs.filter(is_read=is_read.lower() in ('true', '1'))
        return qs.order_by('-created_at')


class NotificationDetailView(generics.RetrieveUpdateAPIView):
    """GET / PATCH /api/v1/notifications/{id}/

    - 跨使用者：因 queryset 只含 own，會回 404 而非 403
    - PATCH 只允許切 `is_read`；切到 True 時自動填 `read_at`
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    def perform_update(self, serializer):
        is_read = serializer.validated_data.get('is_read')
        # 切換成已讀時記時間；切回未讀時清空
        if is_read is True and not serializer.instance.is_read:
            serializer.save(read_at=timezone.now())
        elif is_read is False and serializer.instance.is_read:
            serializer.save(read_at=None)
        else:
            serializer.save()


class NotificationMarkAllReadView(APIView):
    """POST /api/v1/notifications/mark-all-read/

    將自己所有未讀通知一次標為已讀；回傳更新筆數。
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        now = timezone.now()
        updated = Notification.objects.filter(
            recipient=request.user, is_read=False,
        ).update(is_read=True, read_at=now)
        return Response({'updated': updated}, status=status.HTTP_200_OK)
