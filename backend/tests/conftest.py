import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _clear_throttle_cache():
    """每個測試前清除 DRF throttle 計數，避免測試間互相影響"""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    """未登入的 API Client"""
    return APIClient()


@pytest.fixture
def user(db):
    """已儲存至測試 DB 的使用者"""
    return UserFactory()


@pytest.fixture
def other_user(db):
    """另一個使用者，用於測試越權存取"""
    return UserFactory()


@pytest.fixture
def auth_client(api_client, user):
    """已認證的 API Client（force_authenticate，不走 JWT 流程）"""
    api_client.force_authenticate(user=user)
    return api_client


from tests.factories import WorkspaceFactory, ProjectFactory, ProjectStatusFactory, TaskFactory


@pytest.fixture
def workspace(db, user):
    return WorkspaceFactory(owner=user)


@pytest.fixture
def project(workspace):
    return ProjectFactory(workspace=workspace)


@pytest.fixture
def status(project):
    return ProjectStatusFactory(project=project)


@pytest.fixture
def task(project, status, user):
    return TaskFactory(project=project, status=status, creator=user)
