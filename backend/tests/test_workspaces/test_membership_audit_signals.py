"""WorkspaceMember / ProjectMember 變動自動寫入 MembershipAuditLog 的 Signal 測試。

涵蓋：
- 新增成員 → member_added，new_role 為角色，old_role 空
- 變更角色 → role_changed，old_role 與 new_role 不同
- 軟刪除成員 → member_removed，old_role 為刪除前角色
- 同一筆儲存無實質變更 → 不寫 log
- actor 從 thread-local（CurrentUserMiddleware）抓取
"""
import pytest

from apps.users.middleware import _set_current_user
from apps.workspaces.models import MembershipAuditLog, WorkspaceMember
from apps.projects.models import ProjectMember
from tests.factories import (
    ProjectFactory,
    ProjectMemberFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMemberFactory,
)


@pytest.fixture(autouse=True)
def _clear_thread_local():
    """每個測試前後清空 thread-local，避免 actor 漏接到別的測試。"""
    _set_current_user(None)
    yield
    _set_current_user(None)


def _logs_for(scope_type, scope_id):
    return MembershipAuditLog.objects.filter(
        scope_type=scope_type, scope_id=scope_id,
    ).order_by('changed_at')


# ────────────────  WorkspaceMember signals ────────────────


@pytest.mark.django_db
class TestWorkspaceMemberSignals:
    def test_create_writes_member_added_log(self):
        actor = UserFactory()
        target = UserFactory()
        ws = WorkspaceFactory(owner=actor)
        _set_current_user(actor)

        WorkspaceMember.objects.create(
            workspace=ws, user=target, role=WorkspaceMember.Role.MEMBER,
        )

        logs = list(_logs_for('workspace', ws.id))
        assert len(logs) == 1
        log = logs[0]
        assert log.action == MembershipAuditLog.Action.MEMBER_ADDED
        assert log.actor_id == actor.id
        assert log.target_user_id == target.id
        assert log.new_role == 'member'
        assert log.old_role == ''  # 新增時無 old_role

    def test_role_change_writes_role_changed_log(self):
        actor = UserFactory()
        ws = WorkspaceFactory(owner=actor)
        member = WorkspaceMemberFactory(
            workspace=ws, role=WorkspaceMember.Role.MEMBER,
        )
        _set_current_user(actor)
        # 清掉 add 時寫的 log，只看後續變更
        MembershipAuditLog.objects.all().delete()

        member.role = WorkspaceMember.Role.ADMIN
        member.save()

        logs = list(_logs_for('workspace', ws.id))
        assert len(logs) == 1
        log = logs[0]
        assert log.action == MembershipAuditLog.Action.ROLE_CHANGED
        assert log.old_role == 'member'
        assert log.new_role == 'admin'
        assert log.target_user_id == member.user_id

    def test_save_without_change_does_not_write_log(self):
        ws = WorkspaceFactory()
        member = WorkspaceMemberFactory(
            workspace=ws, role=WorkspaceMember.Role.MEMBER,
        )
        MembershipAuditLog.objects.all().delete()

        member.save()  # 沒有改任何欄位

        assert _logs_for('workspace', ws.id).count() == 0

    def test_soft_delete_writes_member_removed_log(self):
        actor = UserFactory()
        ws = WorkspaceFactory(owner=actor)
        member = WorkspaceMemberFactory(
            workspace=ws, role=WorkspaceMember.Role.ADMIN,
        )
        _set_current_user(actor)
        MembershipAuditLog.objects.all().delete()

        member.soft_delete()

        logs = list(_logs_for('workspace', ws.id))
        assert len(logs) == 1
        log = logs[0]
        assert log.action == MembershipAuditLog.Action.MEMBER_REMOVED
        assert log.actor_id == actor.id
        assert log.target_user_id == member.user_id
        assert log.old_role == 'admin'  # 刪除前角色仍記下來

    def test_actor_is_none_when_no_request_context(self):
        """無 HTTP 請求（如 management command、Celery task）時 actor=None。"""
        # 不呼叫 _set_current_user → thread-local 為 None
        ws = WorkspaceFactory()
        WorkspaceMemberFactory(workspace=ws)
        log = _logs_for('workspace', ws.id).first()
        assert log.actor is None


# ────────────────  ProjectMember signals ────────────────


@pytest.mark.django_db
class TestProjectMemberSignals:
    def test_create_writes_member_added_log_with_project_scope(self):
        actor = UserFactory()
        target = UserFactory()
        proj = ProjectFactory()
        _set_current_user(actor)

        ProjectMember.objects.create(
            project=proj, user=target, role=ProjectMember.Role.MEMBER,
        )

        logs = list(_logs_for('project', proj.id))
        assert len(logs) == 1
        log = logs[0]
        assert log.action == MembershipAuditLog.Action.MEMBER_ADDED
        assert log.scope_type == MembershipAuditLog.ScopeType.PROJECT
        assert log.scope_id == proj.id
        assert log.new_role == 'member'

    def test_role_change_writes_role_changed_log(self):
        actor = UserFactory()
        member = ProjectMemberFactory(role=ProjectMember.Role.MEMBER)
        _set_current_user(actor)
        MembershipAuditLog.objects.all().delete()

        member.role = ProjectMember.Role.MANAGER
        member.save()

        logs = list(_logs_for('project', member.project_id))
        assert len(logs) == 1
        assert logs[0].action == MembershipAuditLog.Action.ROLE_CHANGED
        assert logs[0].old_role == 'member'
        assert logs[0].new_role == 'manager'

    def test_soft_delete_writes_member_removed_log(self):
        actor = UserFactory()
        member = ProjectMemberFactory(role=ProjectMember.Role.MANAGER)
        _set_current_user(actor)
        MembershipAuditLog.objects.all().delete()

        member.soft_delete()

        logs = list(_logs_for('project', member.project_id))
        assert len(logs) == 1
        assert logs[0].action == MembershipAuditLog.Action.MEMBER_REMOVED
        assert logs[0].old_role == 'manager'


# ────────────────  scope 隔離 ────────────────


@pytest.mark.django_db
class TestScopeIsolation:
    def test_workspace_and_project_logs_do_not_mix(self):
        """workspace member 與 project member 的稽核紀錄各自獨立。"""
        ws = WorkspaceFactory()
        proj = ProjectFactory()
        WorkspaceMemberFactory(workspace=ws)
        ProjectMemberFactory(project=proj)

        ws_logs = MembershipAuditLog.objects.filter(scope_type='workspace')
        proj_logs = MembershipAuditLog.objects.filter(scope_type='project')

        assert ws_logs.count() == 1
        assert proj_logs.count() == 1
        assert ws_logs.first().scope_id == ws.id
        assert proj_logs.first().scope_id == proj.id
