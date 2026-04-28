"""
Workspace API TDD 測試 — Phase 1
規格：.doc/taskflow-api_doc.md §9
端點：
  /api/v1/workspaces/                                         GET, POST
  /api/v1/workspaces/{id}/                                    GET, PATCH, DELETE
  /api/v1/workspaces/{id}/members/                            GET, POST
  /api/v1/workspaces/{id}/members/{user_id}/                  PATCH, DELETE
  /api/v1/workspaces/{id}/tags/                               GET, POST
  /api/v1/workspaces/{id}/tags/{tag_id}/                      PATCH, DELETE
"""
import pytest

from tests.factories import (
    UserFactory,
    WorkspaceFactory,
    WorkspaceMemberFactory,
    TagFactory,
)


WORKSPACE_URL = '/api/v1/workspaces/'


@pytest.mark.django_db
class TestWorkspaceList:
    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(WORKSPACE_URL)
        assert response.status_code == 401

    def test_lists_only_user_workspaces(self, auth_client, user, other_user):
        WorkspaceFactory(owner=user, name='Mine A')
        ws_member = WorkspaceFactory(owner=other_user, name='Joined')
        WorkspaceMemberFactory(workspace=ws_member, user=user)
        WorkspaceFactory(owner=other_user, name='Stranger')

        response = auth_client.get(WORKSPACE_URL)
        assert response.status_code == 200
        names = {w['name'] for w in response.data['results']}
        assert names == {'Mine A', 'Joined'}

    def test_create_workspace_sets_owner(self, auth_client, user):
        response = auth_client.post(WORKSPACE_URL, {'name': '我的工作區'})
        assert response.status_code == 201
        assert response.data['name'] == '我的工作區'
        assert str(response.data['owner']['id']) == str(user.id)

    def test_create_workspace_requires_name(self, auth_client):
        response = auth_client.post(WORKSPACE_URL, {})
        assert response.status_code == 400
        assert 'name' in response.data


@pytest.mark.django_db
class TestWorkspaceDetail:
    def test_owner_can_get(self, auth_client, workspace):
        response = auth_client.get(f'{WORKSPACE_URL}{workspace.id}/')
        assert response.status_code == 200

    def test_non_member_cannot_get(self, api_client, other_user, workspace):
        api_client.force_authenticate(user=other_user)
        response = api_client.get(f'{WORKSPACE_URL}{workspace.id}/')
        assert response.status_code == 403

    def test_owner_can_patch(self, auth_client, workspace):
        response = auth_client.patch(
            f'{WORKSPACE_URL}{workspace.id}/', {'name': '改名'},
        )
        assert response.status_code == 200
        assert response.data['name'] == '改名'

    def test_member_cannot_patch(self, api_client, other_user, workspace):
        WorkspaceMemberFactory(workspace=workspace, user=other_user, role='member')
        api_client.force_authenticate(user=other_user)
        response = api_client.patch(
            f'{WORKSPACE_URL}{workspace.id}/', {'name': 'X'},
        )
        assert response.status_code == 403

    def test_admin_can_patch(self, api_client, other_user, workspace):
        WorkspaceMemberFactory(workspace=workspace, user=other_user, role='admin')
        api_client.force_authenticate(user=other_user)
        response = api_client.patch(
            f'{WORKSPACE_URL}{workspace.id}/', {'name': 'OK'},
        )
        assert response.status_code == 200

    def test_owner_can_delete(self, auth_client, workspace):
        response = auth_client.delete(f'{WORKSPACE_URL}{workspace.id}/')
        assert response.status_code == 204

    def test_admin_cannot_delete(self, api_client, other_user, workspace):
        WorkspaceMemberFactory(workspace=workspace, user=other_user, role='admin')
        api_client.force_authenticate(user=other_user)
        response = api_client.delete(f'{WORKSPACE_URL}{workspace.id}/')
        assert response.status_code == 403


@pytest.mark.django_db
class TestWorkspaceMembers:
    def test_owner_can_list(self, auth_client, workspace, other_user):
        WorkspaceMemberFactory(workspace=workspace, user=other_user)
        response = auth_client.get(f'{WORKSPACE_URL}{workspace.id}/members/')
        assert response.status_code == 200
        assert response.data['count'] == 1

    def test_owner_can_invite(self, auth_client, workspace):
        new_user = UserFactory()
        response = auth_client.post(
            f'{WORKSPACE_URL}{workspace.id}/members/',
            {'user_id': str(new_user.id), 'role': 'member'},
        )
        assert response.status_code == 201
        assert response.data['user']['id'] == str(new_user.id)

    def test_member_cannot_invite(self, api_client, other_user, workspace):
        WorkspaceMemberFactory(workspace=workspace, user=other_user, role='member')
        api_client.force_authenticate(user=other_user)
        candidate = UserFactory()
        response = api_client.post(
            f'{WORKSPACE_URL}{workspace.id}/members/',
            {'user_id': str(candidate.id), 'role': 'member'},
        )
        assert response.status_code == 403

    def test_invite_nonexistent_user_returns_400(self, auth_client, workspace):
        import uuid
        response = auth_client.post(
            f'{WORKSPACE_URL}{workspace.id}/members/',
            {'user_id': str(uuid.uuid4()), 'role': 'member'},
        )
        assert response.status_code == 400

    def test_owner_can_change_role(self, auth_client, workspace, other_user):
        WorkspaceMemberFactory(workspace=workspace, user=other_user, role='member')
        response = auth_client.patch(
            f'{WORKSPACE_URL}{workspace.id}/members/{other_user.id}/',
            {'role': 'admin'},
        )
        assert response.status_code == 200
        assert response.data['role'] == 'admin'

    def test_owner_can_remove(self, auth_client, workspace, other_user):
        WorkspaceMemberFactory(workspace=workspace, user=other_user)
        response = auth_client.delete(
            f'{WORKSPACE_URL}{workspace.id}/members/{other_user.id}/',
        )
        assert response.status_code == 204


@pytest.mark.django_db
class TestWorkspaceTags:
    def test_owner_can_list_tags(self, auth_client, workspace):
        TagFactory(workspace=workspace, name='設計')
        TagFactory(workspace=workspace, name='開發')
        response = auth_client.get(f'{WORKSPACE_URL}{workspace.id}/tags/')
        assert response.status_code == 200
        assert response.data['count'] == 2

    def test_owner_can_create_tag(self, auth_client, workspace):
        response = auth_client.post(
            f'{WORKSPACE_URL}{workspace.id}/tags/',
            {'name': '緊急', 'color': '#ff0000'},
        )
        assert response.status_code == 201
        assert response.data['name'] == '緊急'

    def test_duplicate_tag_returns_400(self, auth_client, workspace):
        TagFactory(workspace=workspace, name='重複')
        response = auth_client.post(
            f'{WORKSPACE_URL}{workspace.id}/tags/',
            {'name': '重複'},
        )
        assert response.status_code == 400

    def test_non_member_cannot_list_tags(self, api_client, other_user, workspace):
        api_client.force_authenticate(user=other_user)
        response = api_client.get(f'{WORKSPACE_URL}{workspace.id}/tags/')
        assert response.status_code == 403

    def test_owner_can_update_tag(self, auth_client, workspace):
        tag = TagFactory(workspace=workspace, name='舊名')
        response = auth_client.patch(
            f'{WORKSPACE_URL}{workspace.id}/tags/{tag.id}/',
            {'name': '新名'},
        )
        assert response.status_code == 200
        assert response.data['name'] == '新名'

    def test_owner_can_delete_tag(self, auth_client, workspace):
        tag = TagFactory(workspace=workspace)
        response = auth_client.delete(
            f'{WORKSPACE_URL}{workspace.id}/tags/{tag.id}/',
        )
        assert response.status_code == 204
