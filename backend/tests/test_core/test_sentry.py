"""
Sentry 監控整合 TDD 測試
規格：.doc/taskflow-backend.md §9.2

測試範圍：
- SENTRY_DSN 為空時不初始化（本地開發 / CI 不發送錯誤）
- 有 DSN 時 sentry_sdk.init 被正確呼叫，且帶入 Django + Celery 整合
- traces_sample_rate / environment 從 settings 讀取
- send_default_pii=False（避免洩漏使用者 request body / cookies）
"""
import importlib
import sys
from unittest.mock import patch

import pytest
from django.conf import settings


class TestSentryDisabled:
    """SENTRY_DSN 為空時，不應呼叫 sentry_sdk.init。"""

    def test_dsn_default_empty(self):
        """settings 中 SENTRY_DSN 預設應為空字串。"""
        # 本機 / CI 環境變數不該有 DSN，預設停用
        assert settings.SENTRY_DSN == ''

    def test_init_skipped_when_dsn_empty(self):
        """以空 DSN 重新匯入 settings 時 sentry_sdk.init 不該被呼叫。"""
        with patch('sentry_sdk.init') as mock_init:
            # 強制重新載入 settings module 模擬空 DSN 的 import-time 行為
            with patch.dict(
                'os.environ',
                {'SENTRY_DSN': '', 'SECRET_KEY': 'test'},
                clear=False,
            ):
                if 'config.settings' in sys.modules:
                    importlib.reload(sys.modules['config.settings'])
            mock_init.assert_not_called()


class TestSentryEnabled:
    """SENTRY_DSN 有值時，sentry_sdk.init 應被正確呼叫。"""

    FAKE_DSN = 'https://abc123@o12345.ingest.sentry.io/67890'

    def test_init_called_with_dsn(self):
        with patch('sentry_sdk.init') as mock_init:
            with patch.dict(
                'os.environ',
                {
                    'SENTRY_DSN': self.FAKE_DSN,
                    'SECRET_KEY': 'test',
                },
                clear=False,
            ):
                importlib.reload(sys.modules['config.settings'])

            mock_init.assert_called_once()
            kwargs = mock_init.call_args.kwargs
            assert kwargs['dsn'] == self.FAKE_DSN

    def test_init_integrations_include_django_and_celery(self):
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.django import DjangoIntegration

        with patch('sentry_sdk.init') as mock_init:
            with patch.dict(
                'os.environ',
                {'SENTRY_DSN': self.FAKE_DSN, 'SECRET_KEY': 'test'},
                clear=False,
            ):
                importlib.reload(sys.modules['config.settings'])

            integrations = mock_init.call_args.kwargs['integrations']
            integration_types = {type(i) for i in integrations}
            assert DjangoIntegration in integration_types
            assert CeleryIntegration in integration_types

    def test_send_default_pii_disabled(self):
        """預設不送 PII，避免 request body / cookies / user email 進 Sentry。"""
        with patch('sentry_sdk.init') as mock_init:
            with patch.dict(
                'os.environ',
                {'SENTRY_DSN': self.FAKE_DSN, 'SECRET_KEY': 'test'},
                clear=False,
            ):
                importlib.reload(sys.modules['config.settings'])

            assert mock_init.call_args.kwargs['send_default_pii'] is False

    def test_traces_sample_rate_from_env(self):
        """SENTRY_TRACES_SAMPLE_RATE 可從環境變數覆寫，預設 0.2。"""
        with patch('sentry_sdk.init') as mock_init:
            with patch.dict(
                'os.environ',
                {
                    'SENTRY_DSN': self.FAKE_DSN,
                    'SENTRY_TRACES_SAMPLE_RATE': '0.5',
                    'SECRET_KEY': 'test',
                },
                clear=False,
            ):
                importlib.reload(sys.modules['config.settings'])

            assert mock_init.call_args.kwargs['traces_sample_rate'] == 0.5

    def test_environment_from_env(self):
        with patch('sentry_sdk.init') as mock_init:
            with patch.dict(
                'os.environ',
                {
                    'SENTRY_DSN': self.FAKE_DSN,
                    'SENTRY_ENVIRONMENT': 'production',
                    'SECRET_KEY': 'test',
                },
                clear=False,
            ):
                importlib.reload(sys.modules['config.settings'])

            assert mock_init.call_args.kwargs['environment'] == 'production'


@pytest.fixture(autouse=True)
def _restore_settings():
    """每個測試後重新載入 settings 模組，確保不污染其他測試。"""
    yield
    importlib.reload(sys.modules['config.settings'])
