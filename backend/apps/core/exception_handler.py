"""自訂 DRF 例外處理器。

將 Throttled (429) 回應替換為中文提示訊息，格式：
    {"detail": "請求過於頻繁，請在 60 秒後再試。"}
"""
import math

from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """DRF EXCEPTION_HANDLER 入口。

    僅攔截 Throttled 例外以自訂 429 回應訊息，其餘例外沿用 DRF 預設行為。
    """
    response = exception_handler(exc, context)
    if response is not None and isinstance(exc, Throttled):
        wait = math.ceil(exc.wait) if exc.wait else 60
        response.data = {
            'detail': f'請求過於頻繁，請在 {wait} 秒後再試。',
        }
    return response
