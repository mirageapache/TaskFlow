"""個人資料路由（掛在 /api/v1/users/ 之下）。"""
from django.urls import path

from apps.users.views import MeProfileView, MeView


urlpatterns = [
    path('me/', MeView.as_view(), name='users-me'),
    path('me/profile/', MeProfileView.as_view(), name='users-me-profile'),
]
