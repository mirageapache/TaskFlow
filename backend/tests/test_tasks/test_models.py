"""
Task Model TDD 測試 — Phase 1
規格：.doc/taskflow-database.md §3.9-3.13、§4.1-4.3、.doc/taskflow-backend.md §5.5
"""
import uuid
import pytest
from django.db.utils import IntegrityError


@pytest.mark.django_db
class TestTag:
    def test_create_tag(self, workspace):
        from apps.tasks.models import Tag
        tag = Tag.objects.create(name='設計', workspace=workspace)
        assert tag.pk is not None
        assert tag.name == '設計'

    def test_uuid_primary_key(self, workspace):
        from apps.tasks.models import Tag
        tag = Tag.objects.create(name='Test', workspace=workspace)
        assert isinstance(tag.pk, uuid.UUID)

    def test_color_defaults_to_slate(self, workspace):
        from apps.tasks.models import Tag
        tag = Tag.objects.create(name='Test', workspace=workspace)
        assert tag.color == '#94a3b8'

    def test_workspace_relationship(self, workspace):
        from apps.tasks.models import Tag
        tag = Tag.objects.create(name='Test', workspace=workspace)
        assert tag.workspace == workspace

    def test_soft_delete(self, workspace):
        from apps.tasks.models import Tag
        tag = Tag.objects.create(name='Test', workspace=workspace)
        tag.soft_delete()
        assert tag.deleted_at is not None
        assert not Tag.objects.filter(pk=tag.pk).exists()


@pytest.mark.django_db(transaction=True)
class TestTagConstraints:
    def test_duplicate_name_in_same_workspace_raises_error(self, workspace):
        from apps.tasks.models import Tag
        Tag.objects.create(name='設計', workspace=workspace)
        with pytest.raises(IntegrityError):
            Tag.objects.create(name='設計', workspace=workspace)

    def test_same_name_allowed_in_different_workspaces(self, user, other_user):
        from apps.tasks.models import Tag
        from apps.workspaces.models import Workspace
        w1 = Workspace.objects.create(name='Workspace 1', owner=user)
        w2 = Workspace.objects.create(name='Workspace 2', owner=other_user)
        Tag.objects.create(name='設計', workspace=w1)
        tag2 = Tag.objects.create(name='設計', workspace=w2)
        assert tag2.pk is not None


@pytest.mark.django_db
class TestTask:
    def test_create_task(self, project, status, user):
        from apps.tasks.models import Task
        task = Task.objects.create(
            title='實作登入功能',
            project=project,
            status=status,
            creator=user,
        )
        assert task.pk is not None
        assert task.title == '實作登入功能'

    def test_uuid_primary_key(self, project, status):
        from apps.tasks.models import Task
        task = Task.objects.create(title='Test', project=project, status=status)
        assert isinstance(task.pk, uuid.UUID)

    def test_description_defaults_to_empty(self, project, status):
        from apps.tasks.models import Task
        task = Task.objects.create(title='Test', project=project, status=status)
        assert task.description == ''

    def test_priority_defaults_to_medium(self, project, status):
        from apps.tasks.models import Task
        task = Task.objects.create(title='Test', project=project, status=status)
        assert task.priority == Task.Priority.MEDIUM

    def test_all_priority_choices_exist(self):
        from apps.tasks.models import Task
        priorities = {p.value for p in Task.Priority}
        assert priorities == {'urgent', 'high', 'medium', 'low'}

    def test_order_defaults_to_zero(self, project, status):
        from apps.tasks.models import Task
        task = Task.objects.create(title='Test', project=project, status=status)
        assert task.order == 0

    def test_start_date_nullable(self, project, status):
        from apps.tasks.models import Task
        task = Task.objects.create(title='Test', project=project, status=status)
        assert task.start_date is None

    def test_due_date_nullable(self, project, status):
        from apps.tasks.models import Task
        task = Task.objects.create(title='Test', project=project, status=status)
        assert task.due_date is None

    def test_estimated_hours_nullable(self, project, status):
        from apps.tasks.models import Task
        task = Task.objects.create(title='Test', project=project, status=status)
        assert task.estimated_hours is None

    def test_creator_nullable(self, project, status):
        from apps.tasks.models import Task
        task = Task.objects.create(title='Test', project=project, status=status, creator=None)
        assert task.creator is None

    def test_parent_task_nullable_for_top_level(self, project, status):
        from apps.tasks.models import Task
        task = Task.objects.create(title='Top-level', project=project, status=status)
        assert task.parent_task is None

    def test_subtask_relationship(self, project, status):
        from apps.tasks.models import Task
        parent = Task.objects.create(title='Parent', project=project, status=status)
        child = Task.objects.create(
            title='Child', project=project, status=status, parent_task=parent,
        )
        assert child.parent_task == parent
        assert parent.subtasks.filter(pk=child.pk).exists()

    def test_ordering_by_order_field(self, project, status):
        from apps.tasks.models import Task
        Task.objects.create(title='Third', project=project, status=status, order=2)
        Task.objects.create(title='First', project=project, status=status, order=0)
        Task.objects.create(title='Second', project=project, status=status, order=1)
        tasks = list(Task.objects.filter(project=project))
        assert tasks[0].title == 'First'
        assert tasks[1].title == 'Second'
        assert tasks[2].title == 'Third'

    def test_soft_delete(self, project, status):
        from apps.tasks.models import Task
        task = Task.objects.create(title='Test', project=project, status=status)
        task.soft_delete()
        assert task.deleted_at is not None
        assert not Task.objects.filter(pk=task.pk).exists()
        assert Task.all_objects.filter(pk=task.pk).exists()


@pytest.mark.django_db
class TestTaskM2M:
    def test_add_tag_to_task(self, task, workspace):
        from apps.tasks.models import Tag
        tag = Tag.objects.create(name='設計', workspace=workspace)
        task.tags.add(tag)
        assert task.tags.filter(pk=tag.pk).exists()

    def test_assign_user_to_task(self, task, other_user):
        from apps.tasks.models import TaskAssignee
        TaskAssignee.objects.create(task=task, user=other_user)
        assert task.assignees.filter(pk=other_user.pk).exists()

    def test_task_dependency(self, project, status):
        from apps.tasks.models import Task
        prerequisite = Task.objects.create(title='前置任務', project=project, status=status)
        dependent = Task.objects.create(title='後續任務', project=project, status=status)
        dependent.dependencies.add(prerequisite)
        assert dependent.dependencies.filter(pk=prerequisite.pk).exists()
        assert prerequisite.dependents.filter(pk=dependent.pk).exists()


@pytest.mark.django_db
class TestTaskAssignee:
    def test_create_assignee(self, task, other_user):
        from apps.tasks.models import TaskAssignee
        assignee = TaskAssignee.objects.create(task=task, user=other_user)
        assert assignee.pk is not None

    def test_assigned_at_auto_populated(self, task, other_user):
        from apps.tasks.models import TaskAssignee
        assignee = TaskAssignee.objects.create(task=task, user=other_user)
        assert assignee.assigned_at is not None

    def test_has_integer_pk_not_uuid(self, task, other_user):
        from apps.tasks.models import TaskAssignee
        assignee = TaskAssignee.objects.create(task=task, user=other_user)
        assert isinstance(assignee.pk, int)


@pytest.mark.django_db(transaction=True)
class TestTaskAssigneeConstraints:
    def test_duplicate_assignee_raises_error(self, task, other_user):
        from apps.tasks.models import TaskAssignee
        TaskAssignee.objects.create(task=task, user=other_user)
        with pytest.raises(IntegrityError):
            TaskAssignee.objects.create(task=task, user=other_user)


@pytest.mark.django_db
class TestTaskComment:
    def test_create_comment(self, task, user):
        from apps.tasks.models import TaskComment
        comment = TaskComment.objects.create(task=task, author=user, content='LGTM！')
        assert comment.pk is not None
        assert comment.content == 'LGTM！'

    def test_uuid_primary_key(self, task, user):
        from apps.tasks.models import TaskComment
        comment = TaskComment.objects.create(task=task, author=user, content='Test')
        assert isinstance(comment.pk, uuid.UUID)

    def test_author_nullable(self, task):
        from apps.tasks.models import TaskComment
        comment = TaskComment.objects.create(task=task, author=None, content='匿名留言')
        assert comment.author is None

    def test_soft_delete(self, task, user):
        from apps.tasks.models import TaskComment
        comment = TaskComment.objects.create(task=task, author=user, content='Test')
        comment.soft_delete()
        assert comment.deleted_at is not None
        assert not TaskComment.objects.filter(pk=comment.pk).exists()

    def test_ordering_by_created_at(self, task, user):
        from apps.tasks.models import TaskComment
        c1 = TaskComment.objects.create(task=task, author=user, content='First')
        c2 = TaskComment.objects.create(task=task, author=user, content='Second')
        comments = list(TaskComment.objects.filter(task=task))
        assert comments[0].pk == c1.pk
        assert comments[1].pk == c2.pk


@pytest.mark.django_db
class TestTaskAttachment:
    def test_create_attachment(self, task, user):
        from apps.tasks.models import TaskAttachment
        attachment = TaskAttachment.objects.create(
            task=task,
            uploader=user,
            file_name='report.pdf',
            file_key='attachments/abc/report.pdf',
            file_size=102400,
            mime_type='application/pdf',
        )
        assert attachment.pk is not None

    def test_is_confirmed_defaults_to_false(self, task, user):
        from apps.tasks.models import TaskAttachment
        attachment = TaskAttachment.objects.create(
            task=task, uploader=user, file_name='f.pdf',
            file_key='key', file_size=1024, mime_type='application/pdf',
        )
        assert attachment.is_confirmed is False

    def test_uploader_nullable(self, task):
        from apps.tasks.models import TaskAttachment
        attachment = TaskAttachment.objects.create(
            task=task, uploader=None, file_name='f.pdf',
            file_key='key', file_size=1024, mime_type='application/pdf',
        )
        assert attachment.uploader is None

    def test_soft_delete(self, task, user):
        from apps.tasks.models import TaskAttachment
        attachment = TaskAttachment.objects.create(
            task=task, uploader=user, file_name='f.pdf',
            file_key='key', file_size=1024, mime_type='application/pdf',
        )
        attachment.soft_delete()
        assert attachment.deleted_at is not None
        assert not TaskAttachment.objects.filter(pk=attachment.pk).exists()


@pytest.mark.django_db
class TestTaskActivityLog:
    def test_create_activity_log(self, task, user):
        from apps.tasks.models import TaskActivityLog
        log = TaskActivityLog.objects.create(task=task, actor=user, action='created')
        assert log.pk is not None

    def test_has_integer_pk_not_uuid(self, task, user):
        from apps.tasks.models import TaskActivityLog
        log = TaskActivityLog.objects.create(task=task, actor=user, action='created')
        assert isinstance(log.pk, int)

    def test_detail_defaults_to_empty_dict(self, task, user):
        from apps.tasks.models import TaskActivityLog
        log = TaskActivityLog.objects.create(task=task, actor=user, action='created')
        assert log.detail == {}

    def test_actor_nullable(self, task):
        from apps.tasks.models import TaskActivityLog
        log = TaskActivityLog.objects.create(task=task, actor=None, action='created')
        assert log.actor is None

    def test_ordering_newest_first(self, task, user):
        from apps.tasks.models import TaskActivityLog
        log1 = TaskActivityLog.objects.create(task=task, actor=user, action='created')
        log2 = TaskActivityLog.objects.create(task=task, actor=user, action='status_changed')
        logs = list(TaskActivityLog.objects.filter(task=task))
        assert logs[0].pk == log2.pk
        assert logs[1].pk == log1.pk
