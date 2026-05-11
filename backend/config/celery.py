"""Celery application 設定。

規格參考：.doc/taskflow-backend.md §4.2

啟動 worker：
    celery -A config worker -l info

啟動 beat（定時排程）：
    celery -A config beat -l info
"""
import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('taskflow')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Beat Schedule — 定時任務
app.conf.beat_schedule = {
    'send-deadline-reminders': {
        'task': 'apps.tasks.tasks.send_deadline_reminders',
        'schedule': crontab(hour=9, minute=0),  # 每天 09:00
    },
}
