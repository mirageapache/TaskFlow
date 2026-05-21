from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications'

    def ready(self):
        """app 載入時匯入 signals 模組，註冊 task / workspace 變動的通知產生 handler。"""
        from apps.notifications import signals  # noqa: F401
