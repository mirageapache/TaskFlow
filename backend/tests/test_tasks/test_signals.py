"""
Task ActivityLog 自動寫入測試（Django Signals）
規格：.doc/taskflow-backend.md §10 Phase 1 — 活動紀錄自動寫入

驗證 view 不再手動呼叫 TaskActivityLog.objects.create() 後，
仍能由 signals 在以下情境自動寫入正確的 log。
"""
import pytest

from apps.tasks.models import (
    Task,
    TaskActivityLog,
    TaskAssignee,
    TaskComment,
)
from tests.factories import (
    ProjectMemberFactory,
    TagFactory,
    TaskFactory,
    UserFactory,
)


TASKS_URL = '/api/v1/tasks/'


def _logs(task, action=None):
    qs = TaskActivityLog.objects.filter(task=task)
    if action:
        qs = qs.filter(action=action)
    return list(qs)


# ────────────── 建立 / 更新 / 刪除 ──────────────

@pytest.mark.django_db
class TestTaskLifecycleLogs:
    def test_create_logs_created_action(self, auth_client, status):
        response = auth_client.post(TASKS_URL, {
            'title': 'New Task',
            'status_id': str(status.id),
        })
        assert response.status_code == 201
        task = Task.objects.get(pk=response.data['id'])
        created_logs = _logs(task, 'created')
        assert len(created_logs) == 1
        assert created_logs[0].detail.get('title') == 'New Task'

    def test_create_log_actor_is_request_user(self, auth_client, status, user):
        response = auth_client.post(TASKS_URL, {
            'title': 'X', 'status_id': str(status.id),
        })
        log = TaskActivityLog.objects.get(task_id=response.data['id'], action='created')
        assert log.actor_id == user.id

    def test_update_logs_diff(self, auth_client, task):
        response = auth_client.patch(
            f'{TASKS_URL}{task.id}/',
            {'title': 'Renamed', 'priority': 'high'},
        )
        assert response.status_code == 200
        updated_logs = _logs(task, 'updated')
        assert len(updated_logs) == 1
        changes = updated_logs[0].detail['changes']
        assert 'title' in changes
        assert changes['title']['to'] == 'Renamed'
        assert 'priority' in changes
        assert changes['priority']['to'] == 'high'

    def test_update_with_no_change_does_not_log(self, auth_client, task):
        # PATCH 沒有實際改變欄位 → 不應產生 'updated' log
        TaskActivityLog.objects.filter(task=task).delete()
        response = auth_client.patch(
            f'{TASKS_URL}{task.id}/', {'title': task.title},
        )
        assert response.status_code == 200
        assert _logs(task, 'updated') == []

    def test_soft_delete_logs_deleted(self, auth_client, task):
        response = auth_client.delete(f'{TASKS_URL}{task.id}/')
        assert response.status_code == 204
        deleted_logs = _logs(task, 'deleted')
        assert len(deleted_logs) == 1


# ────────────── 指派 ──────────────

@pytest.mark.django_db
class TestAssigneeLogs:
    def test_assign_logs_assignee_added(self, auth_client, task):
        new_user = UserFactory()
        response = auth_client.post(
            f'{TASKS_URL}{task.id}/assignees/',
            {'user_id': str(new_user.id)},
        )
        assert response.status_code == 201
        added_logs = _logs(task, 'assignee_added')
        assert len(added_logs) == 1
        assert added_logs[0].detail['user_id'] == str(new_user.id)

    def test_unassign_logs_assignee_removed(self, auth_client, task, other_user):
        TaskAssignee.objects.create(task=task, user=other_user)
        TaskActivityLog.objects.filter(task=task).delete()  # 清掉前置動作的 log
        response = auth_client.delete(
            f'{TASKS_URL}{task.id}/assignees/{other_user.id}/',
        )
        assert response.status_code == 204
        removed_logs = _logs(task, 'assignee_removed')
        assert len(removed_logs) == 1
        assert removed_logs[0].detail['user_id'] == str(other_user.id)


# ────────────── 標籤 ──────────────

@pytest.mark.django_db
class TestTagLogs:
    def test_set_tags_logs_added(self, auth_client, task, workspace):
        tag = TagFactory(workspace=workspace)
        TaskActivityLog.objects.filter(task=task).delete()
        response = auth_client.patch(
            f'{TASKS_URL}{task.id}/',
            {'tag_ids': [str(tag.id)]},
            format='json',
        )
        assert response.status_code == 200
        added_logs = _logs(task, 'tags_added')
        assert len(added_logs) == 1
        assert str(tag.id) in added_logs[0].detail['tag_ids']


# ────────────── 留言 ──────────────

@pytest.mark.django_db
class TestCommentLogs:
    def test_post_comment_logs_comment_added(self, auth_client, task):
        TaskActivityLog.objects.filter(task=task).delete()
        response = auth_client.post(
            f'{TASKS_URL}{task.id}/comments/',
            {'content': 'LGTM'},
        )
        assert response.status_code == 201
        added_logs = _logs(task, 'comment_added')
        assert len(added_logs) == 1
        assert added_logs[0].detail['comment_id'] == response.data['id']

    def test_edit_comment_does_not_log(self, auth_client, task, user):
        comment = TaskComment.objects.create(task=task, author=user, content='初版')
        TaskActivityLog.objects.filter(task=task).delete()
        comment.content = '修訂版'
        comment.save()
        # 編輯既有留言不應產生新的 comment_added log
        assert _logs(task, 'comment_added') == []


# ────────────── actor 來源驗證 ──────────────

@pytest.mark.django_db
class TestActorSource:
    def test_actor_set_for_authenticated_request(self, auth_client, task, user):
        TaskActivityLog.objects.filter(task=task).delete()
        auth_client.patch(f'{TASKS_URL}{task.id}/', {'title': 'changed'})
        log = TaskActivityLog.objects.get(task=task, action='updated')
        assert log.actor_id == user.id

    def test_actor_none_when_no_http_context(self, task, user):
        """非 HTTP 流程（如 management command）寫入時 actor 為 None。"""
        # 直接呼叫 ORM，不經過 middleware
        task.title = '系統改的'
        task.save()
        log = TaskActivityLog.objects.filter(task=task, action='updated').first()
        assert log is not None
        assert log.actor is None


# ────────────── 不重複 / 不遺漏 ──────────────

@pytest.mark.django_db
class TestNoDuplicateLog:
    def test_view_does_not_double_log_create(self, auth_client, status):
        """確認 view 已移除手動寫入：建立任務只會產生一筆 'created' log。"""
        response = auth_client.post(TASKS_URL, {
            'title': 'X', 'status_id': str(status.id),
        })
        task_id = response.data['id']
        created_logs = TaskActivityLog.objects.filter(task_id=task_id, action='created')
        assert created_logs.count() == 1

    def test_view_does_not_double_log_update(self, auth_client, task):
        TaskActivityLog.objects.filter(task=task).delete()
        auth_client.patch(f'{TASKS_URL}{task.id}/', {'title': 'X'})
        updated_logs = _logs(task, 'updated')
        assert len(updated_logs) == 1
