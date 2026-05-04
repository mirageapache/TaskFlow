"""工作區路由（掛在 /api/v1/workspaces/ 之下）。"""
from django.urls import path

from apps.workspaces.views import (
    TagDetailView,
    TagListCreateView,
    WorkspaceAuditLogListView,
    WorkspaceDetailView,
    WorkspaceListCreateView,
    WorkspaceMemberDetailView,
    WorkspaceMemberListCreateView,
)


urlpatterns = [
    path('', WorkspaceListCreateView.as_view(), name='workspace-list'),
    path('<uuid:pk>/', WorkspaceDetailView.as_view(), name='workspace-detail'),
    path(
        '<uuid:workspace_id>/members/',
        WorkspaceMemberListCreateView.as_view(),
        name='workspace-members',
    ),
    path(
        '<uuid:workspace_id>/members/<uuid:user_id>/',
        WorkspaceMemberDetailView.as_view(),
        name='workspace-member-detail',
    ),
    path(
        '<uuid:workspace_id>/tags/',
        TagListCreateView.as_view(),
        name='workspace-tags',
    ),
    path(
        '<uuid:workspace_id>/tags/<uuid:pk>/',
        TagDetailView.as_view(),
        name='workspace-tag-detail',
    ),
    path(
        '<uuid:workspace_id>/audit-logs/',
        WorkspaceAuditLogListView.as_view(),
        name='workspace-audit-logs',
    ),
]
