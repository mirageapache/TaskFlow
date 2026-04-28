"""
Project Model TDD 測試 — Phase 1
規格：.doc/taskflow-database.md §3.6-3.8、.doc/taskflow-backend.md §5.4
"""
import uuid
import pytest
from django.db.utils import IntegrityError


@pytest.mark.django_db
class TestProject:
    def test_create_project(self, workspace):
        from apps.projects.models import Project
        project = Project.objects.create(name='Test Project', workspace=workspace)
        assert project.pk is not None
        assert project.name == 'Test Project'

    def test_uuid_primary_key(self, workspace):
        from apps.projects.models import Project
        project = Project.objects.create(name='Test', workspace=workspace)
        assert isinstance(project.pk, uuid.UUID)

    def test_description_defaults_to_empty(self, workspace):
        from apps.projects.models import Project
        project = Project.objects.create(name='Test', workspace=workspace)
        assert project.description == ''

    def test_color_defaults_to_indigo(self, workspace):
        from apps.projects.models import Project
        project = Project.objects.create(name='Test', workspace=workspace)
        assert project.color == '#6366f1'

    def test_workspace_relationship(self, workspace):
        from apps.projects.models import Project
        project = Project.objects.create(name='Test', workspace=workspace)
        assert project.workspace == workspace

    def test_workspace_can_have_multiple_projects(self, workspace):
        from apps.projects.models import Project
        Project.objects.create(name='Project A', workspace=workspace)
        Project.objects.create(name='Project B', workspace=workspace)
        assert Project.objects.filter(workspace=workspace).count() == 2

    def test_soft_delete_sets_deleted_at(self, workspace):
        from apps.projects.models import Project
        project = Project.objects.create(name='Test', workspace=workspace)
        project.soft_delete()
        assert project.deleted_at is not None

    def test_soft_deleted_project_not_in_active_objects(self, workspace):
        from apps.projects.models import Project
        project = Project.objects.create(name='Test', workspace=workspace)
        project.soft_delete()
        assert not Project.objects.filter(pk=project.pk).exists()

    def test_soft_deleted_project_visible_via_all_objects(self, workspace):
        from apps.projects.models import Project
        project = Project.objects.create(name='Test', workspace=workspace)
        project.soft_delete()
        assert Project.all_objects.filter(pk=project.pk).exists()


@pytest.mark.django_db
class TestProjectStatus:
    def test_create_project_status(self, project):
        from apps.projects.models import ProjectStatus
        status = ProjectStatus.objects.create(name='待處理', project=project)
        assert status.pk is not None
        assert status.name == '待處理'

    def test_uuid_primary_key(self, project):
        from apps.projects.models import ProjectStatus
        status = ProjectStatus.objects.create(name='Test', project=project)
        assert isinstance(status.pk, uuid.UUID)

    def test_color_defaults_to_slate(self, project):
        from apps.projects.models import ProjectStatus
        status = ProjectStatus.objects.create(name='Test', project=project)
        assert status.color == '#94a3b8'

    def test_order_defaults_to_zero(self, project):
        from apps.projects.models import ProjectStatus
        status = ProjectStatus.objects.create(name='Test', project=project)
        assert status.order == 0

    def test_is_completed_defaults_to_false(self, project):
        from apps.projects.models import ProjectStatus
        status = ProjectStatus.objects.create(name='Test', project=project)
        assert status.is_completed is False

    def test_project_relationship(self, project):
        from apps.projects.models import ProjectStatus
        status = ProjectStatus.objects.create(name='Test', project=project)
        assert status.project == project

    def test_ordering_by_order_field(self, project):
        from apps.projects.models import ProjectStatus
        ProjectStatus.objects.create(name='第三欄', project=project, order=2)
        ProjectStatus.objects.create(name='第一欄', project=project, order=0)
        ProjectStatus.objects.create(name='第二欄', project=project, order=1)
        statuses = list(ProjectStatus.objects.filter(project=project))
        assert statuses[0].name == '第一欄'
        assert statuses[1].name == '第二欄'
        assert statuses[2].name == '第三欄'

    def test_soft_delete_status(self, project):
        from apps.projects.models import ProjectStatus
        status = ProjectStatus.objects.create(name='Test', project=project)
        status.soft_delete()
        assert status.deleted_at is not None
        assert not ProjectStatus.objects.filter(pk=status.pk).exists()


@pytest.mark.django_db
class TestProjectMember:
    def test_create_member(self, project, user):
        from apps.projects.models import ProjectMember
        member = ProjectMember.objects.create(
            project=project,
            user=user,
            role=ProjectMember.Role.MANAGER,
        )
        assert member.pk is not None

    def test_default_role_is_member(self, project, other_user):
        from apps.projects.models import ProjectMember
        member = ProjectMember.objects.create(project=project, user=other_user)
        assert member.role == ProjectMember.Role.MEMBER

    def test_all_role_choices_exist(self):
        from apps.projects.models import ProjectMember
        roles = {r.value for r in ProjectMember.Role}
        assert roles == {'manager', 'member', 'viewer'}

    def test_project_relationship(self, project, user):
        from apps.projects.models import ProjectMember
        member = ProjectMember.objects.create(project=project, user=user)
        assert member.project == project

    def test_user_relationship(self, project, other_user):
        from apps.projects.models import ProjectMember
        member = ProjectMember.objects.create(project=project, user=other_user)
        assert member.user == other_user

    def test_soft_delete_member(self, project, user):
        from apps.projects.models import ProjectMember
        member = ProjectMember.objects.create(project=project, user=user)
        member.soft_delete()
        assert member.deleted_at is not None
        assert not ProjectMember.objects.filter(pk=member.pk).exists()

    def test_same_user_can_be_member_in_different_projects(self, workspace, user):
        from apps.projects.models import Project, ProjectMember
        p1 = Project.objects.create(name='Project 1', workspace=workspace)
        p2 = Project.objects.create(name='Project 2', workspace=workspace)
        ProjectMember.objects.create(project=p1, user=user, role=ProjectMember.Role.MANAGER)
        ProjectMember.objects.create(project=p2, user=user, role=ProjectMember.Role.MEMBER)
        assert ProjectMember.objects.filter(user=user).count() == 2


@pytest.mark.django_db(transaction=True)
class TestProjectMemberConstraints:
    def test_duplicate_member_raises_error(self, project, user):
        from apps.projects.models import ProjectMember
        ProjectMember.objects.create(project=project, user=user, role=ProjectMember.Role.MANAGER)
        with pytest.raises(IntegrityError):
            ProjectMember.objects.create(project=project, user=user, role=ProjectMember.Role.MEMBER)
