"""
Task API TDD 測試 — Phase 1
規格：.doc/taskflow-api_doc.md §4、§5
端點：
  /api/v1/tasks/                                       GET, POST
  /api/v1/tasks/{id}/                                  GET, PATCH, DELETE
  /api/v1/tasks/{id}/comments/                         GET, POST
  /api/v1/tasks/{id}/activity-logs/                    GET
  /api/v1/tasks/{id}/assignees/                        GET, POST
  /api/v1/tasks/{id}/assignees/{user_id}/              DELETE
"""
import pytest

from tests.factories import (
    ProjectMemberFactory,
    ProjectStatusFactory,
    TagFactory,
    TaskFactory,
    UserFactory,
)

TASKS_URL = '/api/v1/tasks/'


@pytest.mark.django_db
class TestTaskList:
    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get(TASKS_URL)
        assert response.status_code == 401

    def test_owner_lists_tasks(self, auth_client, project, status):
        TaskFactory(project=project, status=status, title='A')
        TaskFactory(project=project, status=status, title='B')
        response = auth_client.get(TASKS_URL)
        assert response.status_code == 200
        assert response.data['count'] == 2

    def test_stranger_sees_no_tasks(self, api_client, other_user, project, status):
        TaskFactory(project=project, status=status)
        api_client.force_authenticate(user=other_user)
        response = api_client.get(TASKS_URL)
        assert response.status_code == 200
        assert response.data['count'] == 0

    def test_project_member_sees_tasks(self, api_client, other_user, project, status):
        ProjectMemberFactory(project=project, user=other_user, role='member')
        TaskFactory(project=project, status=status, title='Visible')
        api_client.force_authenticate(user=other_user)
        response = api_client.get(TASKS_URL)
        assert response.status_code == 200
        assert response.data['count'] == 1


@pytest.mark.django_db
class TestTaskCreate:
    def test_create_success(self, auth_client, status):
        response = auth_client.post(TASKS_URL, {
            'title': '我的新任務',
            'status_id': str(status.id),
            'priority': 'high',
        })
        assert response.status_code == 201
        assert response.data['title'] == '我的新任務'
        assert response.data['priority'] == 'high'

    def test_title_required(self, auth_client, status):
        response = auth_client.post(TASKS_URL, {
            'title': '', 'status_id': str(status.id),
        })
        assert response.status_code == 400

    def test_title_max_255(self, auth_client, status):
        response = auth_client.post(TASKS_URL, {
            'title': 'x' * 256, 'status_id': str(status.id),
        })
        assert response.status_code == 400

    def test_invalid_priority(self, auth_client, status):
        response = auth_client.post(TASKS_URL, {
            'title': 'X', 'status_id': str(status.id), 'priority': 'INVALID',
        })
        assert response.status_code == 400

    def test_status_id_required(self, auth_client):
        response = auth_client.post(TASKS_URL, {'title': 'X'})
        assert response.status_code == 400

    def test_non_project_member_cannot_create(self, api_client, other_user, status):
        api_client.force_authenticate(user=other_user)
        response = api_client.post(TASKS_URL, {
            'title': 'X', 'status_id': str(status.id),
        })
        assert response.status_code == 403

    def test_viewer_cannot_create(self, api_client, other_user, project, status):
        ProjectMemberFactory(project=project, user=other_user, role='viewer')
        api_client.force_authenticate(user=other_user)
        response = api_client.post(TASKS_URL, {
            'title': 'X', 'status_id': str(status.id),
        })
        assert response.status_code == 403

    def test_creator_set_automatically(self, auth_client, status, user):
        response = auth_client.post(TASKS_URL, {
            'title': 'creator test', 'status_id': str(status.id),
        })
        assert response.status_code == 201
        from apps.tasks.models import Task
        task = Task.objects.get(id=response.data['id'])
        assert task.creator_id == user.id

    def test_subtask_parent_must_match_project(self, auth_client, project, status, workspace):
        from tests.factories import ProjectFactory, ProjectStatusFactory
        other_project = ProjectFactory(workspace=workspace)
        other_status = ProjectStatusFactory(project=other_project)
        parent = TaskFactory(project=other_project, status=other_status)
        response = auth_client.post(TASKS_URL, {
            'title': 'sub', 'status_id': str(status.id),
            'parent_task': str(parent.id),
        })
        assert response.status_code == 400

    def test_create_with_assignees_and_tags(self, auth_client, status, workspace):
        u1 = UserFactory()
        tag = TagFactory(workspace=workspace)
        response = auth_client.post(TASKS_URL, {
            'title': '帶標籤任務',
            'status_id': str(status.id),
            'assignee_ids': [str(u1.id)],
            'tag_ids': [str(tag.id)],
        }, format='json')
        assert response.status_code == 201
        assert len(response.data['assignees']) == 1
        assert len(response.data['tags']) == 1


@pytest.mark.django_db
class TestTaskDetailUpdate:
    def test_get_task(self, auth_client, task):
        response = auth_client.get(f'{TASKS_URL}{task.id}/')
        assert response.status_code == 200

    def test_stranger_cannot_get(self, api_client, other_user, task):
        api_client.force_authenticate(user=other_user)
        response = api_client.get(f'{TASKS_URL}{task.id}/')
        assert response.status_code == 403

    def test_workspace_owner_can_patch(self, auth_client, task):
        response = auth_client.patch(
            f'{TASKS_URL}{task.id}/', {'title': '改了'},
        )
        assert response.status_code == 200
        assert response.data['title'] == '改了'

    def test_assignee_can_patch(self, api_client, other_user, task):
        from apps.tasks.models import TaskAssignee
        ProjectMemberFactory(project=task.project, user=other_user, role='member')
        TaskAssignee.objects.create(task=task, user=other_user)
        api_client.force_authenticate(user=other_user)
        response = api_client.patch(
            f'{TASKS_URL}{task.id}/', {'title': 'assignee edit'},
        )
        assert response.status_code == 200

    def test_random_member_cannot_patch(self, api_client, other_user, task):
        ProjectMemberFactory(project=task.project, user=other_user, role='member')
        api_client.force_authenticate(user=other_user)
        response = api_client.patch(
            f'{TASKS_URL}{task.id}/', {'title': 'no'},
        )
        assert response.status_code == 403

    def test_workspace_owner_can_delete(self, auth_client, task):
        response = auth_client.delete(f'{TASKS_URL}{task.id}/')
        assert response.status_code == 204


@pytest.mark.django_db
class TestTaskComments:
    def test_member_can_list(self, auth_client, task):
        from apps.tasks.models import TaskComment
        TaskComment.objects.create(task=task, author=task.creator, content='hi')
        response = auth_client.get(f'{TASKS_URL}{task.id}/comments/')
        assert response.status_code == 200
        assert response.data['count'] == 1

    def test_member_can_post(self, auth_client, task, user):
        response = auth_client.post(
            f'{TASKS_URL}{task.id}/comments/',
            {'content': '留言內容'},
        )
        assert response.status_code == 201
        assert response.data['content'] == '留言內容'
        assert str(response.data['author']['id']) == str(user.id)

    def test_stranger_cannot_post(self, api_client, other_user, task):
        api_client.force_authenticate(user=other_user)
        response = api_client.post(
            f'{TASKS_URL}{task.id}/comments/',
            {'content': 'X'},
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestTaskActivityLogs:
    def test_logs_created_on_task_create(self, auth_client, status):
        response = auth_client.post(TASKS_URL, {
            'title': 'logged', 'status_id': str(status.id),
        })
        task_id = response.data['id']
        logs = auth_client.get(f'{TASKS_URL}{task_id}/activity-logs/')
        assert logs.status_code == 200
        assert logs.data['count'] >= 1
        actions = [log['action'] for log in logs.data['results']]
        assert 'created' in actions


@pytest.mark.django_db
class TestTaskAssignees:
    def test_owner_can_assign(self, auth_client, task):
        new_user = UserFactory()
        response = auth_client.post(
            f'{TASKS_URL}{task.id}/assignees/',
            {'user_id': str(new_user.id)},
        )
        assert response.status_code == 201
        assert response.data['user']['id'] == str(new_user.id)

    def test_duplicate_assignee_returns_400(self, auth_client, task, other_user):
        from apps.tasks.models import TaskAssignee
        TaskAssignee.objects.create(task=task, user=other_user)
        response = auth_client.post(
            f'{TASKS_URL}{task.id}/assignees/',
            {'user_id': str(other_user.id)},
        )
        assert response.status_code == 400

    def test_owner_can_unassign(self, auth_client, task, other_user):
        from apps.tasks.models import TaskAssignee
        TaskAssignee.objects.create(task=task, user=other_user)
        response = auth_client.delete(
            f'{TASKS_URL}{task.id}/assignees/{other_user.id}/',
        )
        assert response.status_code == 204
