from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'

    def ready(self):
        """app 載入完成時 patch DRF APIView，使 thread-local 能在 DRF auth 後同步。"""
        from apps.users.middleware import patch_drf_apiview
        patch_drf_apiview()
