from django.apps import AppConfig


class WorkspacesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.workspaces'

    def ready(self):
        """app 載入完成時匯入 signals 模組，註冊 WorkspaceMember/ProjectMember 的稽核 handler。"""
        from apps.workspaces import signals  # noqa: F401
