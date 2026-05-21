"""Celery tasks 單元測試 — apps.notifications.tasks

驗證每個非同步通知 task 能正確建立 Notification 紀錄。
Celery 在測試中以 ALWAYS_EAGER 模式執行（同步），不需要 Redis。
"""
import pytest

from apps.notifications.models import Notification
from apps.notifications.tasks import (
    create_task_assigned_notification,
    create_task_comment_notifications,
    create_task_status_changed_notifications,
    create_workspace_invite_notification,
)
from apps.tasks.models import TaskAssignee, TaskComment
from tests.factories import (
    TaskFactory,
    UserFactory,
    WorkspaceFactory,
)


@pytest.mark.django_db
class TestCreateTaskAssignedNotification:
    def test_creates_notification(self):
        user = UserFactory()
        task = TaskFactory()

        create_task_assigned_notification(
            recipient_id=str(user.id),
            task_id=str(task.id),
            task_title=task.title,
        )

        assert Notification.objects.filter(
            recipient=user,
            notif_type=Notification.NotifType.TASK_ASSIGNED,
        ).count() == 1
        n = Notification.objects.get(recipient=user)
        assert task.title in n.title
        assert n.payload['task_id'] == str(task.id)


@pytest.mark.django_db
class TestCreateTaskCommentNotifications:
    def test_notifies_assignees_excluding_commenter(self):
        commenter = UserFactory()
        assignee_a = UserFactory()
        assignee_b = UserFactory()
        task = TaskFactory()
        TaskAssignee.objects.create(task=task, user=assignee_a)
        TaskAssignee.objects.create(task=task, user=assignee_b)
        TaskAssignee.objects.create(task=task, user=commenter)
        comment = TaskComment.objects.create(
            task=task, author=commenter, content='test comment',
        )

        # 清除 signal 自動建立的通知，只測試 task 函式本身
        Notification.objects.all().delete()

        create_task_comment_notifications(
            task_id=str(task.id),
            task_title=task.title,
            comment_id=str(comment.id),
            comment_preview='test comment',
            exclude_user_id=str(commenter.id),
        )

        assert Notification.objects.filter(
            recipient=assignee_a,
            notif_type=Notification.NotifType.TASK_COMMENT,
        ).count() == 1
        assert Notification.objects.filter(
            recipient=assignee_b,
            notif_type=Notification.NotifType.TASK_COMMENT,
        ).count() == 1
        # 留言者不應收到通知
        assert Notification.objects.filter(
            recipient=commenter,
            notif_type=Notification.NotifType.TASK_COMMENT,
        ).count() == 0

    def test_no_assignees_no_notifications(self):
        task = TaskFactory()
        comment = TaskComment.objects.create(
            task=task, author=None, content='orphan comment',
        )
        Notification.objects.all().delete()

        create_task_comment_notifications(
            task_id=str(task.id),
            task_title=task.title,
            comment_id=str(comment.id),
            comment_preview='orphan comment',
            exclude_user_id=None,
        )

        assert Notification.objects.count() == 0


@pytest.mark.django_db
class TestCreateTaskStatusChangedNotifications:
    def test_notifies_assignees_excluding_actor(self):
        actor = UserFactory()
        assignee = UserFactory()
        task = TaskFactory()
        TaskAssignee.objects.create(task=task, user=assignee)
        TaskAssignee.objects.create(task=task, user=actor)

        create_task_status_changed_notifications(
            task_id=str(task.id),
            task_title=task.title,
            old_status_id='old-uuid',
            new_status_id='new-uuid',
            exclude_user_id=str(actor.id),
        )

        assert Notification.objects.filter(
            recipient=assignee,
            notif_type=Notification.NotifType.TASK_STATUS_CHANGED,
        ).count() == 1
        assert Notification.objects.filter(
            recipient=actor,
            notif_type=Notification.NotifType.TASK_STATUS_CHANGED,
        ).count() == 0

    def test_no_assignees_no_notifications(self):
        task = TaskFactory()

        create_task_status_changed_notifications(
            task_id=str(task.id),
            task_title=task.title,
            old_status_id=None,
            new_status_id=None,
            exclude_user_id=None,
        )

        assert Notification.objects.filter(
            notif_type=Notification.NotifType.TASK_STATUS_CHANGED,
        ).count() == 0


@pytest.mark.django_db
class TestCreateWorkspaceInviteNotification:
    def test_creates_notification(self):
        user = UserFactory()
        ws = WorkspaceFactory()

        create_workspace_invite_notification(
            recipient_id=str(user.id),
            workspace_id=str(ws.id),
            workspace_name=ws.name,
        )

        assert Notification.objects.filter(
            recipient=user,
            notif_type=Notification.NotifType.WORKSPACE_INVITE,
        ).count() == 1
        n = Notification.objects.get(recipient=user)
        assert ws.name in n.title
        assert n.payload['workspace_id'] == str(ws.id)
