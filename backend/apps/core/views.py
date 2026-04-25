from django.db import connection
from django.db.utils import OperationalError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """服務健康狀態檢查端點（無需 JWT）。

    Phase 1 僅檢查 DB 連線；Phase 2 導入 Redis 後會加上 redis 檢查。
    """
    db_status = 'ok'
    try:
        connection.ensure_connection()
    except OperationalError:
        db_status = 'unavailable'

    return Response({
        'status': 'ok',
        'db': db_status,
    })
