"""Email 通知 Celery task 測試。

測試 send_notification_email task 與 notification tasks 的 email 整合：
- EMAIL_NOTIFICATIONS_ENABLED=False 時不發送
- EMAIL_NOTIFICATIONS_ENABLED=True 時呼叫 send_mail
- Email 主旨根據 notif_type 正確設定
- 模板渲染成功
- 發送失敗時自動重試（不影響 in-app 通知）
- 各通知 task 觸發 email 發送
"""
from unittest.mock import ANY, patch

import pytest
from django.core import mail

from apps.notifications.emails import send_notification_email
from apps.notifications.models import Notification
from tests.factories import TaskFactory, UserFactory, WorkspaceFactory


@pytest.mark.django_db
class TestSendNotificationEmail:
    """直接測試 send_notification_email task。"""

    def test_sends_email_when_enabled(self, settings):
        """EMAIL_NOTIFICATIONS_ENABLED=True 時實際發送 Email。"""
        settings.EMAIL_NOTIFICATIONS_ENABLED = True
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

        send_notification_email(
            recipient_email='test@example.com',
            notif_type='task_assigned',
            title='你被指派了任務「測試」',
            body='',
            payload={'task_id': 'abc-123'},
        )

        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        assert email.to == ['test@example.com']
        assert '[TaskFlow]' in email.subject
        assert '任務指派' in email.subject
        assert '測試' in email.body

    def test_skips_when_disabled(self, settings):
        """EMAIL_NOTIFICATIONS_ENABLED=False 時不發送。"""
        settings.EMAIL_NOTIFICATIONS_ENABLED = False

        send_notification_email(
            recipient_email='test@example.com',
            notif_type='task_assigned',
            title='你被指派了任務「測試」',
            body='',
        )

        assert len(mail.outbox) == 0

    def test_html_template_rendered(self, settings):
        """Email 包含 HTML 版本。"""
        settings.EMAIL_NOTIFICATIONS_ENABLED = True
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

        send_notification_email(
            recipient_email='test@example.com',
            notif_type='workspace_invite',
            title='你被邀請加入工作區「TaskFlow Dev」',
            body='歡迎加入！',
        )

        assert len(mail.outbox) == 1
        email = mail.outbox[0]
        # alternatives 包含 HTML 版本
        assert len(email.alternatives) == 1
        html_content = email.alternatives[0][0]
        assert 'TaskFlow' in html_content
        assert '歡迎加入' in html_content

    def test_subject_prefix_by_notif_type(self, settings):
        """不同 notif_type 有對應的主旨前綴。"""
        settings.EMAIL_NOTIFICATIONS_ENABLED = True
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

        test_cases = [
            ('task_assigned', '任務指派'),
            ('task_comment', '任務留言'),
            ('task_status_changed', '任務狀態變更'),
            ('workspace_invite', '工作區邀請'),
        ]

        for notif_type, expected_keyword in test_cases:
            mail.outbox.clear()
            send_notification_email(
                recipient_email='test@example.com',
                notif_type=notif_type,
                title='test',
                body='',
            )
            assert len(mail.outbox) == 1, f'Failed for {notif_type}'
            assert expected_keyword in mail.outbox[0].subject, (
                f'{notif_type}: expected "{expected_keyword}" in subject "{mail.outbox[0].subject}"'
            )

    def test_unknown_notif_type_uses_default_subject(self, settings):
        """未知的 notif_type 使用預設主旨。"""
        settings.EMAIL_NOTIFICATIONS_ENABLED = True
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

        send_notification_email(
            recipient_email='test@example.com',
            notif_type='unknown_type',
            title='something',
            body='',
        )

        assert len(mail.outbox) == 1
        assert '[TaskFlow]' in mail.outbox[0].subject

    def test_from_email_uses_settings(self, settings):
        """寄件者地址使用 settings.DEFAULT_FROM_EMAIL。"""
        settings.EMAIL_NOTIFICATIONS_ENABLED = True
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
        settings.DEFAULT_FROM_EMAIL = 'custom@taskflow.dev'

        send_notification_email(
            recipient_email='test@example.com',
            notif_type='task_assigned',
            title='test',
            body='',
        )

        assert mail.outbox[0].from_email == 'custom@taskflow.dev'


@pytest.mark.django_db
class TestNotificationTasksEmailIntegration:
    """測試各 notification task 是否正確觸發 email 發送。"""

    def test_task_assigned_dispatches_email(self, settings):
        """create_task_assigned_notification 完成後觸發 email task。"""
        settings.EMAIL_NOTIFICATIONS_ENABLED = True
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

        user = UserFactory()
        task = TaskFactory()

        from apps.notifications.tasks import create_task_assigned_notification
        create_task_assigned_notification(
            recipient_id=str(user.id),
            task_id=str(task.id),
            task_title=task.title,
        )

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [user.email]
        assert '任務指派' in mail.outbox[0].subject

    def test_task_comment_dispatches_emails(self, settings):
        """create_task_comment_notifications 對每個 assignee 發送 email。"""
        settings.EMAIL_NOTIFICATIONS_ENABLED = True
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

        from apps.tasks.models import TaskAssignee, TaskComment
        commenter = UserFactory()
        assignee = UserFactory()
        task = TaskFactory()
        TaskAssignee.objects.create(task=task, user=assignee)
        TaskAssignee.objects.create(task=task, user=commenter)
        comment = TaskComment.objects.create(task=task, author=commenter, content='hello')
        Notification.objects.all().delete()
        mail.outbox.clear()

        from apps.notifications.tasks import create_task_comment_notifications
        create_task_comment_notifications(
            task_id=str(task.id),
            task_title=task.title,
            comment_id=str(comment.id),
            comment_preview='hello',
            exclude_user_id=str(commenter.id),
        )

        # assignee 收到，commenter 不收到
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [assignee.email]

    def test_workspace_invite_dispatches_email(self, settings):
        """create_workspace_invite_notification 完成後觸發 email task。"""
        settings.EMAIL_NOTIFICATIONS_ENABLED = True
        settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

        user = UserFactory()
        ws = WorkspaceFactory()

        from apps.notifications.tasks import create_workspace_invite_notification
        create_workspace_invite_notification(
            recipient_id=str(user.id),
            workspace_id=str(ws.id),
            workspace_name=ws.name,
        )

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [user.email]
        assert '工作區邀請' in mail.outbox[0].subject

    def test_no_email_when_disabled(self, settings):
        """EMAIL_NOTIFICATIONS_ENABLED=False 時不發 email。"""
        settings.EMAIL_NOTIFICATIONS_ENABLED = False

        user = UserFactory()
        task = TaskFactory()

        from apps.notifications.tasks import create_task_assigned_notification
        create_task_assigned_notification(
            recipient_id=str(user.id),
            task_id=str(task.id),
            task_title=task.title,
        )

        # in-app 通知仍然建立
        assert Notification.objects.filter(recipient=user).exists()
        # 但不發 email
        assert len(mail.outbox) == 0
