"""Celery tasks 單元測試 — apps.tasks.tasks

測試 send_deadline_reminders task：
- 今日到期且未完成的任務 → 對 assignees 發送通知
- 已完成狀態的任務 → 不發送
- 無到期任務 → 回傳 0
- 無 assignee 的到期任務 → 不建立通知

注意：TaskAssignee.objects.create() 會觸發 notify_task_assigned signal，
自動產生 task_assigned 通知。測試中需先清除或按 notif_type 過濾。
"""
from datetime import date, timedelta

import pytest

from apps.notifications.models import Notification
from apps.tasks.models import TaskAssignee
from apps.tasks.tasks import send_deadline_reminders
from tests.factories import (
    ProjectStatusFactory,
    TaskFactory,
    UserFactory,
)

DEADLINE_NOTIF_TYPE = Notification.NotifType.TASK_ASSIGNED


def _deadline_notifs(recipient=None):
    """取得由 send_deadline_reminders 產生的通知（body 含「截止日」關鍵字區分）。"""
    qs = Notification.objects.filter(title__contains='今日到期')
    if recipient:
        qs = qs.filter(recipient=recipient)
    return qs


@pytest.mark.django_db
class TestSendDeadlineReminders:
    def test_sends_notification_for_due_today_task(self):
        """今日到期的未完成任務 → 通知 assignee。"""
        user = UserFactory()
        task = TaskFactory(due_date=date.today())
        TaskAssignee.objects.create(task=task, user=user)
        Notification.objects.all().delete()  # 清除 signal 產生的通知

        count = send_deadline_reminders()

        assert count == 1
        n = _deadline_notifs(recipient=user).get()
        assert '今日到期' in n.title
        assert task.title in n.title
        assert n.payload == {'task_id': str(task.id)}

    def test_skips_completed_tasks(self):
        """已完成狀態的任務不發提醒。"""
        user = UserFactory()
        completed_status = ProjectStatusFactory(is_completed=True)
        task = TaskFactory(
            due_date=date.today(),
            status=completed_status,
            project=completed_status.project,
        )
        TaskAssignee.objects.create(task=task, user=user)
        Notification.objects.all().delete()

        count = send_deadline_reminders()

        assert count == 0
        assert _deadline_notifs().count() == 0

    def test_skips_tasks_due_tomorrow(self):
        """明日到期的不在今天發送。"""
        user = UserFactory()
        task = TaskFactory(due_date=date.today() + timedelta(days=1))
        TaskAssignee.objects.create(task=task, user=user)
        Notification.objects.all().delete()

        count = send_deadline_reminders()

        assert count == 0

    def test_no_due_tasks_returns_zero(self):
        """無任何今日到期任務。"""
        TaskFactory(due_date=date.today() + timedelta(days=7))

        count = send_deadline_reminders()

        assert count == 0

    def test_task_with_no_assignees(self):
        """到期但無人指派 → 不建立通知。"""
        TaskFactory(due_date=date.today())

        count = send_deadline_reminders()

        assert count == 0

    def test_multiple_assignees_get_separate_notifications(self):
        """一個任務多個 assignee，每人各收一則。"""
        u1 = UserFactory()
        u2 = UserFactory()
        task = TaskFactory(due_date=date.today())
        TaskAssignee.objects.create(task=task, user=u1)
        TaskAssignee.objects.create(task=task, user=u2)
        Notification.objects.all().delete()

        count = send_deadline_reminders()

        assert count == 2
        assert _deadline_notifs(recipient=u1).count() == 1
        assert _deadline_notifs(recipient=u2).count() == 1

    def test_multiple_due_tasks(self):
        """多個今日到期任務。"""
        user = UserFactory()
        t1 = TaskFactory(due_date=date.today())
        t2 = TaskFactory(due_date=date.today())
        TaskAssignee.objects.create(task=t1, user=user)
        TaskAssignee.objects.create(task=t2, user=user)
        Notification.objects.all().delete()

        count = send_deadline_reminders()

        assert count == 2
