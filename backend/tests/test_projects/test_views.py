"""
Project API TDD 測試 — Phase 1
規格：.doc/taskflow-api_doc.md §4、§9.1
端點：
  /api/v1/projects/                                        GET, POST
  /api/v1/projects/{id}/                                   GET, PATCH, DELETE
  /api/v1/projects/{id}/statuses/                          GET, POST
  /api/v1/projects/{id}/statuses/{status_id}/              PATCH, DELETE
  /api/v1/projects/{id}/members/                           GET, POST
  /api/v1/projects/{id}/members/{user_id}/                 PATCH, DELETE
"""
import pytest

from tests.factories import (
    ProjectFactory,
    ProjectMemberFactory,
    ProjectStatusFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMemberFactory,
)

PROJECTS_URL = '/api/v1/projects/'


@pytest.mark.django_db
class TestProjectList:
    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(PROJECTS_URL)
        assert response.status_code == 401

    def test_workspace_owner_can_list(self, auth_client, workspace):
        ProjectFactory(workspace=workspace, name='A')
        ProjectFactory(workspace=workspace, name='B')
        response = auth_client.get(PROJECTS_URL)
        assert response.status_code == 200
        names = {p['name'] for p in response.data['results']}
        assert names == {'A', 'B'}

    def test_workspace_member_can_list(self, api_client, other_user, workspace):
        WorkspaceMemberFactory(workspace=workspace, user=other_user)
        ProjectFactory(workspace=workspace, name='Visible')
        api_client.force_authenticate(user=other_user)
        response = api_client.get(PROJECTS_URL)
        assert response.status_code == 200
        assert response.data['count'] == 1

    def test_stranger_cannot_see_projects(self, api_client, other_user, workspace):
        ProjectFactory(workspace=workspace, name='Hidden')
        api_client.force_authenticate(user=other_user)
        response = api_client.get(PROJECTS_URL)
        assert response.status_code == 200
        assert response.data['count'] == 0

    def test_create_project_in_own_workspace(self, auth_client, workspace):
        response = auth_client.post(PROJECTS_URL, {
            'name': '新專案',
            'workspace_id': str(workspace.id),
        })
        assert response.status_code == 201
        assert response.data['name'] == '新專案'

    def test_create_project_requires_workspace_id(self, auth_client):
        response = auth_client.post(PROJECTS_URL, {'name': 'X'})
        assert response.status_code == 400

    def test_non_workspace_member_cannot_create(self, api_client, other_user, workspace):
        api_client.force_authenticate(user=other_user)
        response = api_client.post(PROJECTS_URL, {
            'name': '無權建立',
            'workspace_id': str(workspace.id),
        })
        assert response.status_code == 403


@pytest.mark.django_db
class TestProjectDetail:
    def test_workspace_owner_can_get(self, auth_client, project):
        response = auth_client.get(f'{PROJECTS_URL}{project.id}/')
        assert response.status_code == 200

    def test_stranger_cannot_get(self, api_client, other_user, project):
        api_client.force_authenticate(user=other_user)
        response = api_client.get(f'{PROJECTS_URL}{project.id}/')
        assert response.status_code == 403

    def test_workspace_owner_can_patch(self, auth_client, project):
        response = auth_client.patch(
            f'{PROJECTS_URL}{project.id}/', {'name': 'New Name'},
        )
        assert response.status_code == 200
        assert response.data['name'] == 'New Name'

    def test_member_role_cannot_patch(self, api_client, other_user, project):
        ProjectMemberFactory(project=project, user=other_user, role='member')
        api_client.force_authenticate(user=other_user)
        response = api_client.patch(
            f'{PROJECTS_URL}{project.id}/', {'name': 'X'},
        )
        assert response.status_code == 403

    def test_manager_can_patch(self, api_client, other_user, project):
        ProjectMemberFactory(project=project, user=other_user, role='manager')
        api_client.force_authenticate(user=other_user)
        response = api_client.patch(
            f'{PROJECTS_URL}{project.id}/', {'name': 'OK'},
        )
        assert response.status_code == 200

    def test_workspace_owner_can_delete(self, auth_client, project):
        response = auth_client.delete(f'{PROJECTS_URL}{project.id}/')
        assert response.status_code == 204


@pytest.mark.django_db
class TestProjectStatuses:
    def test_owner_can_list_statuses(self, auth_client, project):
        ProjectStatusFactory(project=project, name='Todo', order=0)
        ProjectStatusFactory(project=project, name='Doing', order=1)
        response = auth_client.get(f'{PROJECTS_URL}{project.id}/statuses/')
        assert response.status_code == 200
        assert response.data['count'] == 2

    def test_owner_can_create_status(self, auth_client, project):
        response = auth_client.post(
            f'{PROJECTS_URL}{project.id}/statuses/',
            {'name': 'Done', 'order': 5, 'is_completed': True},
        )
        assert response.status_code == 201
        assert response.data['name'] == 'Done'
        assert response.data['is_completed'] is True

    def test_member_cannot_create_status(self, api_client, other_user, project):
        ProjectMemberFactory(project=project, user=other_user, role='member')
        api_client.force_authenticate(user=other_user)
        response = api_client.post(
            f'{PROJECTS_URL}{project.id}/statuses/',
            {'name': 'X', 'order': 0},
        )
        assert response.status_code == 403

    def test_owner_can_update_status(self, auth_client, project):
        s = ProjectStatusFactory(project=project, name='Old')
        response = auth_client.patch(
            f'{PROJECTS_URL}{project.id}/statuses/{s.id}/',
            {'name': 'New'},
        )
        assert response.status_code == 200
        assert response.data['name'] == 'New'

    def test_owner_can_delete_status(self, auth_client, project):
        s = ProjectStatusFactory(project=project)
        response = auth_client.delete(
            f'{PROJECTS_URL}{project.id}/statuses/{s.id}/',
        )
        assert response.status_code == 204


@pytest.mark.django_db
class TestProjectMembers:
    def test_owner_can_list(self, auth_client, project, other_user):
        ProjectMemberFactory(project=project, user=other_user)
        response = auth_client.get(f'{PROJECTS_URL}{project.id}/members/')
        assert response.status_code == 200
        assert response.data['count'] == 1

    def test_owner_can_invite(self, auth_client, project):
        new_user = UserFactory()
        response = auth_client.post(
            f'{PROJECTS_URL}{project.id}/members/',
            {'user_id': str(new_user.id), 'role': 'member'},
        )
        assert response.status_code == 201

    def test_member_cannot_invite(self, api_client, other_user, project):
        ProjectMemberFactory(project=project, user=other_user, role='member')
        api_client.force_authenticate(user=other_user)
        candidate = UserFactory()
        response = api_client.post(
            f'{PROJECTS_URL}{project.id}/members/',
            {'user_id': str(candidate.id), 'role': 'member'},
        )
        assert response.status_code == 403

    def test_manager_can_invite(self, api_client, other_user, project):
        ProjectMemberFactory(project=project, user=other_user, role='manager')
        api_client.force_authenticate(user=other_user)
        candidate = UserFactory()
        response = api_client.post(
            f'{PROJECTS_URL}{project.id}/members/',
            {'user_id': str(candidate.id), 'role': 'member'},
        )
        assert response.status_code == 201

    def test_owner_can_change_role(self, auth_client, project, other_user):
        ProjectMemberFactory(project=project, user=other_user, role='member')
        response = auth_client.patch(
            f'{PROJECTS_URL}{project.id}/members/{other_user.id}/',
            {'role': 'manager'},
        )
        assert response.status_code == 200
        assert response.data['role'] == 'manager'

    def test_owner_can_remove(self, auth_client, project, other_user):
        ProjectMemberFactory(project=project, user=other_user)
        response = auth_client.delete(
            f'{PROJECTS_URL}{project.id}/members/{other_user.id}/',
        )
        assert response.status_code == 204
