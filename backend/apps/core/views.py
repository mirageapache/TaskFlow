from pathlib import Path

from django.conf import settings
from django.db import connection
from django.db.utils import OperationalError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """服務健康狀態檢查端點（無需 JWT）。

    回傳 JSON：

        {
            "Backend": "ok",
            "DataBase": { ... },
            "Redis": "ok" | "unavailable" | "not_configured"
        }

    供 Load Balancer / Kubernetes liveness probe 探測使用，並協助開發者
    確認當下究竟連到 SQLite fallback 還是 Supabase / 自架 PostgreSQL。
    """
    db_status = 'ok'
    try:
        connection.ensure_connection()
    except OperationalError:
        db_status = 'unavailable'

    return Response({
        'Backend': 'ok',
        'DataBase': _db_info(db_status),
        'Redis': _redis_status(),
    })


def _db_info(status: str) -> dict:
    """從 connection.settings_dict 抽出 DB 識別資訊（不含 password）。"""
    settings_dict = connection.settings_dict
    engine_full = settings_dict.get('ENGINE') or ''
    # 'django.db.backends.postgresql' → 'postgresql'
    # 'django.db.backends.sqlite3'    → 'sqlite3'
    engine = engine_full.rsplit('.', 1)[-1] or 'unknown'

    name = str(settings_dict.get('NAME') or '')
    host = settings_dict.get('HOST') or ''
    port = settings_dict.get('PORT') or ''

    info: dict = {
        'status': status,
        'engine': engine,
    }

    if engine.startswith('sqlite'):
        # SQLite NAME 是檔案路徑，只露檔名避免洩漏目錄結構
        info['name'] = Path(name).name or name
    else:
        info['name'] = name
        if host:
            info['host'] = f'{host}:{port}' if port else host

    return info


def _redis_status() -> str:
    """嘗試 PING Redis，回傳 'ok' | 'unavailable' | 'not_configured'。"""
    redis_url = getattr(settings, 'REDIS_URL', '')
    if not redis_url:
        return 'not_configured'
    try:
        import redis as redis_lib
        r = redis_lib.from_url(redis_url, socket_connect_timeout=2)
        r.ping()
        return 'ok'
    except Exception:
        return 'unavailable'
