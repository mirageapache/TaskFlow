"""認證流程路由（掛在 /api/v1/auth/ 之下）。"""
from django.urls import path

from apps.users.views import LoginView, LogoutView, RefreshView, RegisterView


urlpatterns = [
    path('register/', RegisterView.as_view(), name='auth-register'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('refresh/', RefreshView.as_view(), name='auth-refresh'),
    path('logout/', LogoutView.as_view(), name='auth-logout'),
]
