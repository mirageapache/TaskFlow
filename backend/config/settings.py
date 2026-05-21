"""
TaskFlow Django settings — Phase 1 MVP 骨架
完整規格見 .doc/taskflow-backend.md §4
"""
from datetime import timedelta
from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='dev-insecure-secret-key-change-me')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = [h.strip() for h in config('ALLOWED_HOSTS', default='').split(',') if h.strip()]

DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',
    'channels',
    'drf_spectacular',
]

LOCAL_APPS = [
    'apps.core',
    'apps.users',
    'apps.workspaces',
    'apps.projects',
    'apps.tasks',
    'apps.calendar_events',
    'apps.notifications',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 必須放在 AuthenticationMiddleware 之後，request.user 才存在；
    # 此 middleware 把 request.user 暫存到 thread-local 供 Signal handler 使用
    'apps.users.middleware.CurrentUserMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
# Supabase 連線資訊填入 .env 後自動切到 PostgreSQL
# DB_HOST 留空時使用本機 SQLite，方便第一次啟動即可跑通前後端連通
if config('DB_HOST', default=''):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '5/min',
        'user': '30/min',
        'ai': '20/hour',
        'login': '10/min',
    },
    'EXCEPTION_HANDLER': 'apps.core.exception_handler.custom_exception_handler',
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'PAGE_SIZE': 20,
}

# JWT
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# Refresh Token httpOnly Cookie（Phase 1 TDD 實作認證 API 時使用）
REFRESH_TOKEN_COOKIE = {
    'key': 'refresh_token',
    'httponly': True,
    'secure': not DEBUG,
    'samesite': 'Lax',
    'max_age': 60 * 60 * 24 * 7,
}

# Internationalization
LANGUAGE_CODE = 'zh-hant'
TIME_ZONE = 'Asia/Taipei'
USE_I18N = True
USE_TZ = True

# CORS
CORS_ALLOWED_ORIGINS = [o.strip() for o in config('CORS_ALLOWED_ORIGINS', default='http://localhost:5173').split(',') if o.strip()]
CORS_ALLOW_CREDENTIALS = True

# Static & Media
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# S3 / Object Storage（附件 Presigned URL）
AWS_S3_BUCKET = config('AWS_S3_BUCKET', default='taskflow-attachments-dev')
AWS_S3_REGION = config('AWS_S3_REGION', default='ap-northeast-1')
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')
AWS_S3_ENDPOINT_URL = config('AWS_S3_ENDPOINT_URL', default='')  # MinIO 等本地 S3 相容服務
PRESIGNED_URL_EXPIRES_SECONDS = 60 * 15  # 15 分鐘

# auth.E003 要求 USERNAME_FIELD 有 unique=True
# 本專案改用條件唯一約束（WHERE deleted_at IS NULL），允許軟刪除後相同 email 重新註冊
# 詳見 .doc/taskflow-backend.md §5.2
SILENCED_SYSTEM_CHECKS = ['auth.E003']

# ─── Redis & Celery ──────────────────────────────────────────────────────
# REDIS_URL 留空時 Celery 自動 fallback 到 memory://（不需 Redis 即可開發）
REDIS_URL = config('REDIS_URL', default='')

CELERY_BROKER_URL = REDIS_URL or 'memory://'
CELERY_RESULT_BACKEND = REDIS_URL or 'cache+memory://'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = not bool(REDIS_URL)  # 無 Redis 時同步執行，方便開發與測試
CELERY_TASK_EAGER_PROPAGATES = True  # eager 模式下例外直接拋出，方便偵錯

# ─── Django Channels ─────────────────────────────────────────────────────
# 有 Redis 時使用 RedisChannelLayer，無 Redis 時 fallback 到 InMemoryChannelLayer
if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }
# ─── Email ────────────────────────────────────────────────────────────────
# EMAIL_HOST 留空時使用 console backend（開發用，不實際發信）
EMAIL_HOST = config('EMAIL_HOST', default='')
if EMAIL_HOST:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='TaskFlow <noreply@taskflow.local>')
# 是否啟用 Email 通知（可在 .env 中關閉）
EMAIL_NOTIFICATIONS_ENABLED = config('EMAIL_NOTIFICATIONS_ENABLED', default=bool(EMAIL_HOST), cast=bool)

# ─── Sentry 錯誤監控 ──────────────────────────────────────────────────────────
# SENTRY_DSN 留空時自動停用（本地開發 / CI 不需發送錯誤到 Sentry）
# 啟用時整合 Django + Celery，自動捕捉：
#   - 未處理的 500 錯誤（含 stack trace、request payload、user context）
#   - Celery 任務拋出的例外
#   - 透過 logging 寫入 ERROR 級別的訊息
SENTRY_DSN = config('SENTRY_DSN', default='')
SENTRY_ENVIRONMENT = config('SENTRY_ENVIRONMENT', default='development')
SENTRY_TRACES_SAMPLE_RATE = config('SENTRY_TRACES_SAMPLE_RATE', default=0.2, cast=float)

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENVIRONMENT,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,  # 避免把 request body / cookies 等個資送到 Sentry
        attach_stacktrace=True,
    )

# ─── drf-spectacular（OpenAPI / Swagger 文件自動產生）─────────────────────────
# /api/schema/            → OpenAPI 3.0 JSON/YAML
# /api/schema/swagger-ui/ → 互動式 Swagger UI（可直接在瀏覽器試打 API）
# /api/schema/redoc/      → ReDoc 文件頁
SPECTACULAR_SETTINGS = {
    'TITLE': 'TaskFlow API',
    'DESCRIPTION': 'TaskFlow 任務協作平台 REST API 文件。所有端點掛載於 /api/v1/ 之下。',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,  # 不在 Swagger UI 內嵌完整 schema，改由獨立端點提供
    'SCHEMA_PATH_PREFIX': r'/api/v1',
    'COMPONENT_SPLIT_REQUEST': True,  # request / response schema 分開，避免欄位混淆（如 read_only）
    'SERVERS': [{'url': '/', 'description': 'Current host'}],
    'SECURITY': [{'jwtAuth': []}],
    'APPEND_COMPONENTS': {
        'securitySchemes': {
            'jwtAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    },
}