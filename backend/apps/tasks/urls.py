"""任務路由（掛在 /api/v1/tasks/ 之下）。"""
from django.urls import path

from apps.tasks.views import (
    TaskActivityLogListView,
    TaskAssigneeDeleteView,
    TaskAssigneeListCreateView,
    TaskAttachmentConfirmView,
    TaskAttachmentDownloadView,
    TaskAttachmentListView,
    TaskAttachmentRequestUploadView,
    TaskCommentListCreateView,
    TaskDetailView,
    TaskListCreateView,
)

urlpatterns = [
    # Task CRUD
    path('', TaskListCreateView.as_view(), name='task-list'),
    path('<uuid:pk>/', TaskDetailView.as_view(), name='task-detail'),

    # 子資源：留言、變更紀錄、指派
    path(
        '<uuid:task_id>/comments/',
        TaskCommentListCreateView.as_view(),
        name='task-comments',
    ),
    path(
        '<uuid:task_id>/activity-logs/',
        TaskActivityLogListView.as_view(),
        name='task-activity-logs',
    ),
    path(
        '<uuid:task_id>/assignees/',
        TaskAssigneeListCreateView.as_view(),
        name='task-assignees',
    ),
    path(
        '<uuid:task_id>/assignees/<uuid:user_id>/',
        TaskAssigneeDeleteView.as_view(),
        name='task-assignee-detail',
    ),

    # 附件 Presigned URL 流程
    path(
        '<uuid:task_id>/attachments/',
        TaskAttachmentListView.as_view(),
        name='task-attachments',
    ),
    path(
        '<uuid:task_id>/attachments/request-upload/',
        TaskAttachmentRequestUploadView.as_view(),
        name='task-attachment-request-upload',
    ),
    path(
        '<uuid:task_id>/attachments/<uuid:pk>/confirm/',
        TaskAttachmentConfirmView.as_view(),
        name='task-attachment-confirm',
    ),
    path(
        '<uuid:task_id>/attachments/<uuid:pk>/download/',
        TaskAttachmentDownloadView.as_view(),
        name='task-attachment-download',
    ),
]
