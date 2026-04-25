import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Phase 2 引入 Django Channels 後，會改為 ProtocolTypeRouter（詳見 .doc/taskflow-backend.md §4.2）
application = get_asgi_application()
