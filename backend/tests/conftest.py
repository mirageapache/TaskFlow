import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """未登入的 API Client"""
    return APIClient()


# TODO: Phase 1 TDD — 實作 User Model 後取消以下註解
# from tests.factories import UserFactory, WorkspaceFactory, ProjectFactory, ProjectStatusFactory
#
# @pytest.fixture
# def user(db):
#     return UserFactory()
#
# @pytest.fixture
# def other_user(db):
#     return UserFactory()
#
# @pytest.fixture
# def auth_client(api_client, user):
#     api_client.force_authenticate(user=user)
#     return api_client
#
# @pytest.fixture
# def workspace(user):
#     return WorkspaceFactory(owner=user)
#
# @pytest.fixture
# def project(workspace):
#     return ProjectFactory(workspace=workspace)
#
# @pytest.fixture
# def status(project):
#     return ProjectStatusFactory(project=project)
