"""Calendar 路由（掛在 /api/v1/calendar/ 之下）。"""
from django.urls import path

from apps.calendar_events.views import EventDetailView, EventListCreateView

urlpatterns = [
    path('', EventListCreateView.as_view(), name='calendar-event-list'),
    path('<uuid:pk>/', EventDetailView.as_view(), name='calendar-event-detail'),
]
