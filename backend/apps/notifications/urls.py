"""通知路由（掛在 /api/v1/notifications/ 之下）。"""
from django.urls import path

from apps.notifications.views import (
    NotificationDetailView,
    NotificationListView,
    NotificationMarkAllReadView,
)


urlpatterns = [
    path('', NotificationListView.as_view(), name='notification-list'),
    path('mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification-mark-all-read'),
    path('<uuid:pk>/', NotificationDetailView.as_view(), name='notification-detail'),
]
