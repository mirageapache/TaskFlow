"""TaskFlow 主路由設定。

所有 API 端點統一掛載於 /api/v1/ 前綴下，依 app 拆分到各自的 urls.py：
- /api/v1/auth/          → apps.users.auth_urls    (註冊 / 登入 / refresh / logout)
- /api/v1/users/         → apps.users.profile_urls (個人資料 /me/、偏好 /me/profile/)
- /api/v1/workspaces/    → apps.workspaces.urls    (工作區 / 成員 / 標籤 / 稽核紀錄)
- /api/v1/projects/      → apps.projects.urls      (專案 / 看板狀態 / 成員)
- /api/v1/tasks/         → apps.tasks.urls         (任務 / 留言 / 指派 / 附件)
- /api/v1/calendar/      → apps.calendar_events.urls (行程事件 + 重複規則展開)
- /api/v1/notifications/ → apps.notifications.urls   (通知列表 / 已讀標記)
- /api/v1/health/        → 健康檢查（無需 JWT，供 Load Balancer 探測）
- /api/schema/           → OpenAPI 3.0 規格（drf-spectacular）
- /api/schema/swagger-ui/→ Swagger UI 互動式文件
- /api/schema/redoc/     → ReDoc 文件頁
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.core.views import health_check


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.users.auth_urls')),
    path('api/v1/users/', include('apps.users.profile_urls')),
    path('api/v1/workspaces/', include('apps.workspaces.urls')),
    path('api/v1/projects/', include('apps.projects.urls')),
    path('api/v1/tasks/', include('apps.tasks.urls')),
    path('api/v1/calendar/', include('apps.calendar_events.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/health/', health_check),
    # OpenAPI / Swagger UI（drf-spectacular 自動產生）
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
