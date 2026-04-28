from django.apps import AppConfig


class TasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tasks'

    def ready(self):
        """app 載入完成時匯入 signals 模組，註冊所有 @receiver 處理器。"""
        from apps.tasks import signals  # noqa: F401
