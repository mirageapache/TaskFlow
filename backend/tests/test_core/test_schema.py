"""
drf-spectacular OpenAPI 文件 TDD 測試
規格：.doc/taskflow-backend.md §9.2

測試範圍：
- /api/schema/ 回傳合法的 OpenAPI 3.x 規格
- /api/schema/swagger-ui/ 與 /api/schema/redoc/ 可正常渲染
- schema 內包含 JWT bearer security scheme
- schema 涵蓋專案核心端點（auth、health）
- 文件端點允許匿名存取，不被 IsAuthenticated 擋下
"""
import pytest
import yaml
from django.urls import reverse

SCHEMA_URL = '/api/schema/'
SWAGGER_URL = '/api/schema/swagger-ui/'
REDOC_URL = '/api/schema/redoc/'


@pytest.mark.django_db
class TestSchemaEndpoint:
    """/api/schema/ — OpenAPI 3.x 規格輸出。"""

    def test_schema_returns_200_anonymous(self, api_client):
        """schema 端點應允許匿名存取，否則前後端對接會卡關。"""
        response = api_client.get(SCHEMA_URL)
        assert response.status_code == 200

    def test_schema_is_valid_openapi(self, api_client):
        """回應內容應是合法 YAML 並符合 OpenAPI 3.x 基本結構。"""
        response = api_client.get(SCHEMA_URL)
        schema = yaml.safe_load(response.content)
        assert schema['openapi'].startswith('3.')
        assert schema['info']['title'] == 'TaskFlow API'
        assert schema['info']['version'] == '1.0.0'
        assert 'paths' in schema
        assert isinstance(schema['paths'], dict) and len(schema['paths']) > 0

    def test_schema_includes_jwt_security_scheme(self, api_client):
        """SPECTACULAR_SETTINGS 註冊的 jwtAuth bearer scheme 應出現在 components。"""
        response = api_client.get(SCHEMA_URL)
        schema = yaml.safe_load(response.content)
        schemes = schema.get('components', {}).get('securitySchemes', {})
        assert 'jwtAuth' in schemes
        assert schemes['jwtAuth']['type'] == 'http'
        assert schemes['jwtAuth']['scheme'] == 'bearer'
        assert schemes['jwtAuth']['bearerFormat'] == 'JWT'

    def test_schema_lists_core_endpoints(self, api_client):
        """schema 應涵蓋登入、健康檢查等核心端點。"""
        response = api_client.get(SCHEMA_URL)
        schema = yaml.safe_load(response.content)
        paths = schema['paths']
        assert '/api/v1/auth/login/' in paths
        assert '/api/v1/auth/register/' in paths
        assert '/api/v1/health/' in paths

    def test_schema_url_resolves_by_name(self):
        """URL name='schema' 應可被 reverse 解析，供前端或 CI 抓取。"""
        assert reverse('schema') == SCHEMA_URL


@pytest.mark.django_db
class TestSwaggerUI:
    """/api/schema/swagger-ui/ — 互動式文件頁。"""

    def test_swagger_ui_returns_html(self, api_client):
        response = api_client.get(SWAGGER_URL)
        assert response.status_code == 200
        assert 'text/html' in response['Content-Type']

    def test_swagger_ui_references_schema(self, api_client):
        """Swagger UI 頁面應指向 /api/schema/ 作為資料來源。"""
        response = api_client.get(SWAGGER_URL)
        body = response.content.decode('utf-8')
        assert SCHEMA_URL in body

    def test_swagger_ui_url_name(self):
        assert reverse('swagger-ui') == SWAGGER_URL


@pytest.mark.django_db
class TestRedoc:
    """/api/schema/redoc/ — ReDoc 文件頁。"""

    def test_redoc_returns_html(self, api_client):
        response = api_client.get(REDOC_URL)
        assert response.status_code == 200
        assert 'text/html' in response['Content-Type']

    def test_redoc_url_name(self):
        assert reverse('redoc') == REDOC_URL


@pytest.mark.django_db
class TestSpectacularSettings:
    """settings.SPECTACULAR_SETTINGS 與 REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] 配置。"""

    def test_default_schema_class_is_spectacular(self, settings):
        assert settings.REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] == \
            'drf_spectacular.openapi.AutoSchema'

    def test_spectacular_title_and_version(self, settings):
        assert settings.SPECTACULAR_SETTINGS['TITLE'] == 'TaskFlow API'
        assert settings.SPECTACULAR_SETTINGS['VERSION'] == '1.0.0'

    def test_spectacular_serve_include_schema_disabled(self, settings):
        """SERVE_INCLUDE_SCHEMA=False 避免 Swagger UI 內嵌完整 schema 造成載入肥大。"""
        assert settings.SPECTACULAR_SETTINGS['SERVE_INCLUDE_SCHEMA'] is False

    def test_spectacular_app_installed(self, settings):
        assert 'drf_spectacular' in settings.INSTALLED_APPS
