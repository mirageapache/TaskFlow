"""MembershipAuditLog Model 單元測試。

規格：.doc/taskflow-database.md §3.18 / .doc/taskflow-backend.md §9.1
"""
import pytest

from apps.workspaces.models import MembershipAuditLog
from tests.factories import UserFactory, WorkspaceFactory


@pytest.mark.django_db
class TestMembershipAuditLogModel:
    def test_create_member_added_log(self):
        actor = UserFactory()
        target = UserFactory()
        ws = WorkspaceFactory(owner=actor)
        log = MembershipAuditLog.objects.create(
            actor=actor,
            target_user=target,
            action=MembershipAuditLog.Action.MEMBER_ADDED,
            scope_type=MembershipAuditLog.ScopeType.WORKSPACE,
            scope_id=ws.id,
            new_role='member',
        )
        assert log.pk is not None
        assert log.changed_at is not None

    def test_role_changed_log_records_old_and_new_role(self):
        ws = WorkspaceFactory()
        log = MembershipAuditLog.objects.create(
            target_user=UserFactory(),
            action=MembershipAuditLog.Action.ROLE_CHANGED,
            scope_type=MembershipAuditLog.ScopeType.WORKSPACE,
            scope_id=ws.id,
            old_role='member',
            new_role='admin',
        )
        assert log.old_role == 'member'
        assert log.new_role == 'admin'

    def test_actor_set_null_on_user_delete(self):
        """actor 帳號被硬刪後稽核紀錄仍保留（actor → NULL）。"""
        actor = UserFactory()
        target = UserFactory()
        ws = WorkspaceFactory()
        log = MembershipAuditLog.objects.create(
            actor=actor, target_user=target,
            action=MembershipAuditLog.Action.MEMBER_ADDED,
            scope_type=MembershipAuditLog.ScopeType.WORKSPACE,
            scope_id=ws.id, new_role='member',
        )
        actor.delete()  # hard delete
        log.refresh_from_db()
        assert log.actor is None
        assert log.target_user_id == target.id

    def test_target_user_set_null_on_user_delete(self):
        actor = UserFactory()
        target = UserFactory()
        ws = WorkspaceFactory()
        log = MembershipAuditLog.objects.create(
            actor=actor, target_user=target,
            action=MembershipAuditLog.Action.MEMBER_REMOVED,
            scope_type=MembershipAuditLog.ScopeType.WORKSPACE,
            scope_id=ws.id, old_role='member',
        )
        target.delete()
        log.refresh_from_db()
        assert log.target_user is None

    def test_scope_id_persists_after_workspace_deletion(self):
        """scope_id 沒設 FK，workspace 被刪稽核紀錄仍可查到原 scope_id。"""
        ws = WorkspaceFactory()
        original_id = ws.id
        log = MembershipAuditLog.objects.create(
            target_user=UserFactory(),
            action=MembershipAuditLog.Action.MEMBER_ADDED,
            scope_type=MembershipAuditLog.ScopeType.WORKSPACE,
            scope_id=original_id, new_role='member',
        )
        ws.delete()
        log.refresh_from_db()
        assert log.scope_id == original_id

    def test_default_ordering_is_descending_changed_at(self):
        ws = WorkspaceFactory()
        l1 = MembershipAuditLog.objects.create(
            target_user=UserFactory(),
            action=MembershipAuditLog.Action.MEMBER_ADDED,
            scope_type=MembershipAuditLog.ScopeType.WORKSPACE,
            scope_id=ws.id, new_role='member',
        )
        l2 = MembershipAuditLog.objects.create(
            target_user=UserFactory(),
            action=MembershipAuditLog.Action.MEMBER_ADDED,
            scope_type=MembershipAuditLog.ScopeType.WORKSPACE,
            scope_id=ws.id, new_role='member',
        )
        ordered = list(MembershipAuditLog.objects.all())
        # 後建立的應排在前面（-changed_at）
        assert ordered[0].id == l2.id
        assert ordered[1].id == l1.id

    def test_does_not_inherit_basemodel_fields(self):
        """稽核紀錄不該有 BaseModel 的 deleted_at / UUID PK（永久保留 + BIGSERIAL）。"""
        ws = WorkspaceFactory()
        log = MembershipAuditLog.objects.create(
            target_user=UserFactory(),
            action=MembershipAuditLog.Action.MEMBER_ADDED,
            scope_type=MembershipAuditLog.ScopeType.WORKSPACE,
            scope_id=ws.id, new_role='member',
        )
        # PK 是 int（BigAutoField），不是 UUID
        assert isinstance(log.pk, int)
        # 沒有 deleted_at 屬性
        assert not hasattr(log, 'deleted_at')
