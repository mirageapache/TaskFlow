"""專案路由（掛在 /api/v1/projects/ 之下）。"""
from django.urls import path

from apps.projects.views import (
    ProjectDetailView,
    ProjectListCreateView,
    ProjectMemberDetailView,
    ProjectMemberListCreateView,
    ProjectStatusDetailView,
    ProjectStatusListCreateView,
)

urlpatterns = [
    path('', ProjectListCreateView.as_view(), name='project-list'),
    path('<uuid:pk>/', ProjectDetailView.as_view(), name='project-detail'),
    path(
        '<uuid:project_id>/statuses/',
        ProjectStatusListCreateView.as_view(),
        name='project-statuses',
    ),
    path(
        '<uuid:project_id>/statuses/<uuid:pk>/',
        ProjectStatusDetailView.as_view(),
        name='project-status-detail',
    ),
    path(
        '<uuid:project_id>/members/',
        ProjectMemberListCreateView.as_view(),
        name='project-members',
    ),
    path(
        '<uuid:project_id>/members/<uuid:user_id>/',
        ProjectMemberDetailView.as_view(),
        name='project-member-detail',
    ),
]
