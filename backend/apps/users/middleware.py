"""把當前 request 的使用者暫存到 thread-local，供 Django Signal handler 取用。

Signal handler（如 `apps.tasks.signals.task_log_save`）執行時拿不到 `request` 物件，
但需要知道「是誰執行了這次寫入」才能填到 `TaskActivityLog.actor`。

實作有兩個進入點：
1. **CurrentUserMiddleware**：處理一般 Django view（admin、health_check）
2. **DRF APIView.initial() patch**：處理 DRF view（在 apps.users.apps.UsersConfig.ready() 註冊）

需要兩條進入點的原因：
- 一般 Django middleware 的 `request.user` 由 `AuthenticationMiddleware` 從 session 設定
- DRF 的 `request.user` 由 DRF authentication class 在 view 內部設定（middleware 階段尚未執行），
  且測試常用的 `force_authenticate` 也只在 DRF 的 dispatch 流程中生效
- 因此需要在 DRF 完成 auth 之後（即 `APIView.initial()` 內）再次更新 thread-local

注意：thread-local 在 async 環境下需改為 contextvars，Phase 1 暫不處理。
"""
from threading import local

_thread_locals = local()


def get_current_user():
    """從 thread-local 取得當前使用者；無認證或非 HTTP context 時回傳 None。"""
    return getattr(_thread_locals, 'user', None)


def _set_current_user(user):
    """更新 thread-local。已認證者寫入物件本身，否則寫 None。"""
    _thread_locals.user = (
        user if (user is not None and getattr(user, 'is_authenticated', False)) else None
    )


class CurrentUserMiddleware:
    """為一般 Django view 設定 thread-local；DRF view 由 APIView.initial() patch 補上。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _set_current_user(getattr(request, 'user', None))
        try:
            return self.get_response(request)
        finally:
            _thread_locals.user = None


def patch_drf_apiview():
    """在 DRF 完成 authentication / permission 後更新 thread-local。

    `APIView.initial()` 內會呼叫 `perform_authentication()` 設定 `request.user`，
    覆寫此方法即可在 view 真正執行前確保 thread-local 與 request.user 同步。
    `force_authenticate`（測試常用）也是經由此流程，不會被繞過。
    """
    from rest_framework.views import APIView

    if getattr(APIView, '_taskflow_patched', False):
        return

    original_initial = APIView.initial

    def patched_initial(self, request, *args, **kwargs):
        original_initial(self, request, *args, **kwargs)
        _set_current_user(getattr(request, 'user', None))

    APIView.initial = patched_initial
    APIView._taskflow_patched = True
