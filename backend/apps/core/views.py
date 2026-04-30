from pathlib import Path

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
            "DataBase": {
                "status": "ok" | "unavailable",
                "engine": "postgresql" | "sqlite3" | ...,
                "name": "<db name 或檔名>",
                "host": "<host:port>"   # 僅遠端 DB（PostgreSQL 等）才會出現
            }
        }

    供 Load Balancer / Kubernetes liveness probe 探測使用，並協助開發者
    確認當下究竟連到 SQLite fallback 還是 Supabase / 自架 PostgreSQL。

    Phase 1 僅檢查 DB；Phase 2 導入 Redis / Celery 後會擴充其他相依檢查。
    """
    db_status = 'ok'
    try:
        connection.ensure_connection()
    except OperationalError:
        db_status = 'unavailable'

    return Response({
        'Backend': 'ok',
        'DataBase': _db_info(db_status),
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
