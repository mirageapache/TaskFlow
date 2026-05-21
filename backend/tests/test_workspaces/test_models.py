"""
Workspace Model TDD 測試 — Phase 1
規格：.doc/taskflow-database.md §3.4-3.5
"""
import pytest
from django.db.utils import IntegrityError


@pytest.mark.django_db
class TestWorkspace:
    def test_create_workspace(self, user):
        from apps.workspaces.models import Workspace
        workspace = Workspace.objects.create(name='Test Workspace', owner=user)
        assert workspace.pk is not None
        assert workspace.name == 'Test Workspace'

    def test_uuid_primary_key(self, user):
        import uuid

        from apps.workspaces.models import Workspace
        workspace = Workspace.objects.create(name='Test', owner=user)
        assert isinstance(workspace.pk, uuid.UUID)

    def test_description_defaults_to_empty(self, user):
        from apps.workspaces.models import Workspace
        workspace = Workspace.objects.create(name='Test', owner=user)
        assert workspace.description == ''

    def test_avatar_url_defaults_to_empty(self, user):
        from apps.workspaces.models import Workspace
        workspace = Workspace.objects.create(name='Test', owner=user)
        assert workspace.avatar_url == ''

    def test_owner_relationship(self, user):
        from apps.workspaces.models import Workspace
        workspace = Workspace.objects.create(name='Test', owner=user)
        assert workspace.owner == user
        assert workspace.owner.pk == user.pk

    def test_user_can_own_multiple_workspaces(self, user):
        from apps.workspaces.models import Workspace
        Workspace.objects.create(name='Workspace A', owner=user)
        Workspace.objects.create(name='Workspace B', owner=user)
        assert Workspace.objects.filter(owner=user).count() == 2

    def test_soft_delete_sets_deleted_at(self, user):
        from apps.workspaces.models import Workspace
        workspace = Workspace.objects.create(name='Test', owner=user)
        workspace.soft_delete()
        assert workspace.deleted_at is not None

    def test_soft_deleted_workspace_not_in_active_objects(self, user):
        from apps.workspaces.models import Workspace
        workspace = Workspace.objects.create(name='Test', owner=user)
        workspace.soft_delete()
        assert not Workspace.objects.filter(pk=workspace.pk).exists()

    def test_soft_deleted_workspace_visible_via_all_objects(self, user):
        from apps.workspaces.models import Workspace
        workspace = Workspace.objects.create(name='Test', owner=user)
        workspace.soft_delete()
        assert Workspace.all_objects.filter(pk=workspace.pk).exists()


@pytest.mark.django_db
class TestWorkspaceMember:
    def test_create_member(self, user):
        from apps.workspaces.models import Workspace, WorkspaceMember
        workspace = Workspace.objects.create(name='Test', owner=user)
        member = WorkspaceMember.objects.create(
            workspace=workspace,
            user=user,
            role=WorkspaceMember.Role.OWNER,
        )
        assert member.pk is not None

    def test_default_role_is_member(self, user, other_user):
        from apps.workspaces.models import Workspace, WorkspaceMember
        workspace = Workspace.objects.create(name='Test', owner=user)
        member = WorkspaceMember.objects.create(workspace=workspace, user=other_user)
        assert member.role == WorkspaceMember.Role.MEMBER

    def test_joined_at_auto_populated(self, user):
        from apps.workspaces.models import Workspace, WorkspaceMember
        workspace = Workspace.objects.create(name='Test', owner=user)
        member = WorkspaceMember.objects.create(
            workspace=workspace, user=user, role=WorkspaceMember.Role.OWNER,
        )
        assert member.joined_at is not None

    def test_all_role_choices_exist(self):
        from apps.workspaces.models import WorkspaceMember
        roles = {r.value for r in WorkspaceMember.Role}
        assert roles == {'owner', 'admin', 'member', 'guest'}

    def test_member_workspace_relationship(self, user):
        from apps.workspaces.models import Workspace, WorkspaceMember
        workspace = Workspace.objects.create(name='Test', owner=user)
        member = WorkspaceMember.objects.create(
            workspace=workspace, user=user, role=WorkspaceMember.Role.OWNER,
        )
        assert member.workspace == workspace

    def test_member_user_relationship(self, user, other_user):
        from apps.workspaces.models import Workspace, WorkspaceMember
        workspace = Workspace.objects.create(name='Test', owner=user)
        member = WorkspaceMember.objects.create(
            workspace=workspace, user=other_user, role=WorkspaceMember.Role.MEMBER,
        )
        assert member.user == other_user

    def test_soft_delete_member(self, user):
        from apps.workspaces.models import Workspace, WorkspaceMember
        workspace = Workspace.objects.create(name='Test', owner=user)
        member = WorkspaceMember.objects.create(
            workspace=workspace, user=user, role=WorkspaceMember.Role.OWNER,
        )
        member.soft_delete()
        assert member.deleted_at is not None
        assert not WorkspaceMember.objects.filter(pk=member.pk).exists()

    def test_same_user_can_join_multiple_workspaces(self, user, other_user):
        from apps.workspaces.models import Workspace, WorkspaceMember
        w1 = Workspace.objects.create(name='Workspace 1', owner=user)
        w2 = Workspace.objects.create(name='Workspace 2', owner=other_user)
        WorkspaceMember.objects.create(workspace=w1, user=user, role=WorkspaceMember.Role.OWNER)
        WorkspaceMember.objects.create(workspace=w2, user=user, role=WorkspaceMember.Role.MEMBER)
        assert WorkspaceMember.objects.filter(user=user).count() == 2


@pytest.mark.django_db(transaction=True)
class TestWorkspaceMemberConstraints:
    def test_duplicate_member_raises_error(self, user):
        from apps.workspaces.models import Workspace, WorkspaceMember
        workspace = Workspace.objects.create(name='Test', owner=user)
        WorkspaceMember.objects.create(
            workspace=workspace, user=user, role=WorkspaceMember.Role.OWNER,
        )
        with pytest.raises(IntegrityError):
            WorkspaceMember.objects.create(
                workspace=workspace, user=user, role=WorkspaceMember.Role.MEMBER,
            )
