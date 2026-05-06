"""通知產生 Signal 測試（Phase 2）。

對應觸發點：
- TaskAssignee 新增   → recipient = 被指派者，notif_type = task_assigned
- TaskComment 新增    → recipient = 任務 assignees（排除留言者本人），notif_type = task_comment
- Task.status 變更    → recipient = assignees（排除動作者），notif_type = task_status_changed
- WorkspaceMember 新增 → recipient = 新成員，notif_type = workspace_invite

actor 來源：apps.users.middleware._set_current_user 寫入 thread-local。
規則：自我操作（actor == target）不重複通知自己。
"""
import pytest

from apps.notifications.models import Notification
from apps.tasks.models import Task, TaskAssignee, TaskComment
from apps.users.middleware import _set_current_user
from apps.workspaces.models import WorkspaceMember
from tests.factories import (
    ProjectStatusFactory,
    TaskFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMemberFactory,
)


@pytest.fixture(autouse=True)
def _clear_thread_local():
    _set_current_user(None)
    yield
    _set_current_user(None)


def _notif_count(recipient, notif_type):
    return Notification.objects.filter(
        recipient=recipient, notif_type=notif_type,
    ).count()


# ────────────────  Task assignment ────────────────


@pytest.mark.django_db
class TestTaskAssignedNotification:
    def test_assigning_user_creates_notification_for_assignee(self):
        actor = UserFactory()
        assignee = UserFactory()
        task = TaskFactory(creator=actor)
        _set_current_user(actor)

        TaskAssignee.objects.create(task=task, user=assignee)

        assert _notif_count(assignee, Notification.NotifType.TASK_ASSIGNED) == 1
        n = Notification.objects.get(recipient=assignee, notif_type='task_assigned')
        assert n.payload == {'task_id': str(task.id)}
        assert task.title in n.title  # 標題應提到任務名

    def test_self_assignment_does_not_create_notification(self):
        """自己指派自己不要再通知自己。"""
        u = UserFactory()
        task = TaskFactory(creator=u)
        _set_current_user(u)

        TaskAssignee.objects.create(task=task, user=u)

        assert _notif_count(u, Notification.NotifType.TASK_ASSIGNED) == 0


# ────────────────  Task comment ────────────────


@pytest.mark.django_db
class TestTaskCommentNotification:
    def test_comment_notifies_all_assignees_except_commenter(self):
        author = UserFactory()
        assignee_a = UserFactory()
        assignee_b = UserFactory()
        task = TaskFactory()
        TaskAssignee.objects.create(task=task, user=assignee_a)
        TaskAssignee.objects.create(task=task, user=assignee_b)
        # 把 author 也設為 assignee；驗證留言時不通知自己
        TaskAssignee.objects.create(task=task, user=author)
        _set_current_user(author)

        TaskComment.objects.create(task=task, author=author, content='hi')

        assert _notif_count(assignee_a, Notification.NotifType.TASK_COMMENT) == 1
        assert _notif_count(assignee_b, Notification.NotifType.TASK_COMMENT) == 1
        assert _notif_count(author, Notification.NotifType.TASK_COMMENT) == 0


# ────────────────  Task status change ────────────────


@pytest.mark.django_db
class TestTaskStatusChangedNotification:
    def test_status_change_notifies_assignees_except_actor(self):
        actor = UserFactory()
        assignee = UserFactory()
        task = TaskFactory(creator=actor)
        TaskAssignee.objects.create(task=task, user=assignee)
        TaskAssignee.objects.create(task=task, user=actor)

        # 換到同 project 的另一個 status
        new_status = ProjectStatusFactory(project=task.project, name='Doing')
        _set_current_user(actor)

        task.status = new_status
        task.save()

        assert _notif_count(assignee, Notification.NotifType.TASK_STATUS_CHANGED) == 1
        # 動作者本人不該收到
        assert _notif_count(actor, Notification.NotifType.TASK_STATUS_CHANGED) == 0

    def test_no_status_change_no_notification(self):
        """純改 title 等其他欄位不觸發 status 通知。"""
        u = UserFactory()
        task = TaskFactory()
        TaskAssignee.objects.create(task=task, user=u)
        _set_current_user(UserFactory())

        task.title = 'Updated title'
        task.save()

        assert _notif_count(u, Notification.NotifType.TASK_STATUS_CHANGED) == 0


# ────────────────  Workspace invite ────────────────


@pytest.mark.django_db
class TestWorkspaceInviteNotification:
    def test_adding_member_creates_invite_notification_for_new_member(self):
        actor = UserFactory()
        new_member = UserFactory()
        ws = WorkspaceFactory(owner=actor)
        _set_current_user(actor)

        WorkspaceMember.objects.create(
            workspace=ws, user=new_member, role=WorkspaceMember.Role.MEMBER,
        )

        assert _notif_count(new_member, Notification.NotifType.WORKSPACE_INVITE) == 1
        n = Notification.objects.get(
            recipient=new_member, notif_type='workspace_invite',
        )
        assert n.payload == {'workspace_id': str(ws.id)}

    def test_role_change_does_not_create_invite_notification(self):
        actor = UserFactory()
        ws = WorkspaceFactory(owner=actor)
        member = WorkspaceMemberFactory(workspace=ws, role='member')
        _set_current_user(actor)
        Notification.objects.all().delete()

        member.role = WorkspaceMember.Role.ADMIN
        member.save()

        assert _notif_count(member.user, Notification.NotifType.WORKSPACE_INVITE) == 0
