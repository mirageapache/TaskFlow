"""Celery 基礎設定整合測試。

確認：
- Celery app 能正確載入
- Beat schedule 已註冊 send_deadline_reminders
- settings 中 CELERY_TASK_ALWAYS_EAGER=True（測試環境同步執行）
"""
import pytest
from django.conf import settings


class TestCeleryConfiguration:
    def test_celery_app_loads(self):
        from config.celery import app
        assert app.main == 'taskflow'

    def test_beat_schedule_contains_deadline_reminders(self):
        from config.celery import app
        assert 'send-deadline-reminders' in app.conf.beat_schedule
        entry = app.conf.beat_schedule['send-deadline-reminders']
        assert entry['task'] == 'apps.tasks.tasks.send_deadline_reminders'

    def test_eager_mode_in_tests(self):
        """測試環境下 CELERY_TASK_ALWAYS_EAGER 應為 True（REDIS_URL 為空）。"""
        assert settings.CELERY_TASK_ALWAYS_EAGER is True

    def test_celery_autodiscover_finds_tasks(self):
        from config.celery import app
        # 觸發 autodiscover
        app.autodiscover_tasks()
        # 確認 task 已註冊
        assert 'apps.tasks.tasks.send_deadline_reminders' in app.tasks


@pytest.mark.django_db
class TestHealthCheckRedis:
    def test_health_check_includes_redis_field(self, api_client):
        response = api_client.get('/api/v1/health/')
        assert response.status_code == 200
        data = response.json()
        assert 'Redis' in data
        # 測試環境沒設 REDIS_URL，應為 not_configured
        assert data['Redis'] == 'not_configured'
