"""Celery tasks for the tasks app.

目前包含：
- send_deadline_reminders：每日 09:00 由 Beat 排程觸發，掃描今日到期任務並發送通知。
"""
import logging
from datetime import date

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name='apps.tasks.tasks.send_deadline_reminders')
def send_deadline_reminders():
    """掃描今日到期的未完成任務，對每個 assignee 發送截止日提醒通知。

    此 task 由 Celery Beat 每天 09:00 觸發（見 config/celery.py beat_schedule）。
    """
    from apps.notifications.models import Notification
    from apps.projects.models import ProjectStatus
    from apps.tasks.models import Task, TaskAssignee

    today = date.today()

    # 找出所有今日到期、且尚未標記為完成的任務
    completed_status_ids = ProjectStatus.objects.filter(
        is_completed=True,
    ).values_list('id', flat=True)

    due_today_tasks = Task.objects.filter(
        due_date=today,
    ).exclude(
        status_id__in=completed_status_ids,
    ).only('id', 'title')

    if not due_today_tasks.exists():
        logger.info('send_deadline_reminders: 今日無到期任務。')
        return 0

    notifications = []
    for task in due_today_tasks:
        assignee_ids = TaskAssignee.objects.filter(
            task=task,
        ).values_list('user_id', flat=True)

        for uid in assignee_ids:
            notifications.append(
                Notification(
                    recipient_id=uid,
                    notif_type=Notification.NotifType.TASK_ASSIGNED,
                    title=f'任務「{task.title}」今日到期',
                    body='請確認任務進度，並在截止日前完成。',
                    payload={'task_id': str(task.id)},
                )
            )

    if notifications:
        Notification.objects.bulk_create(notifications)
        logger.info(
            'send_deadline_reminders: 已發送 %d 則截止日提醒通知。',
            len(notifications),
        )

    return len(notifications)
