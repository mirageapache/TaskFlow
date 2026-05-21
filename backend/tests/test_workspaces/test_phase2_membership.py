"""Phase 2 — 成員邀請與角色權限控管（強化）+ 稽核紀錄 API。

涵蓋：
- Owner 保護：不可透過 members API 移除 / 降級 workspace.owner
- 自我保護：不可移除自己
- 稽核紀錄 API：GET /api/v1/workspaces/{id}/audit-logs/
"""
import pytest

from apps.workspaces.models import MembershipAuditLog, WorkspaceMember
from tests.factories import (
    UserFactory,
    WorkspaceFactory,
    WorkspaceMemberFactory,
)

WORKSPACE_URL = '/api/v1/workspaces/'


# ────────────────  Owner / 自我保護 ────────────────


@pytest.mark.django_db
class TestWorkspaceOwnerProtection:
    """workspace.owner 是工作區的「實質擁有者」（FK + PROTECT），
    不應該被透過一般 members API 操作。"""

    def test_cannot_demote_workspace_owner_via_member_api(self, auth_client, user, workspace):
        """owner 即使有 member 列也不能降級。"""
        # 假設管理流程把 owner 自己也加到 members（Phase 2 之前可能會發生）
        WorkspaceMemberFactory(workspace=workspace, user=user, role='owner')

        response = auth_client.patch(
            f'{WORKSPACE_URL}{workspace.id}/members/{user.id}/',
            {'role': 'member'},
        )
        assert response.status_code == 403

    def test_cannot_remove_workspace_owner_via_member_api(self, auth_client, user, workspace):
        WorkspaceMemberFactory(workspace=workspace, user=user, role='owner')

        response = auth_client.delete(
            f'{WORKSPACE_URL}{workspace.id}/members/{user.id}/',
        )
        assert response.status_code == 403

    def test_admin_can_still_modify_normal_members(self, auth_client, workspace, other_user):
        """Owner 保護不應誤傷一般成員的角色變更流程。"""
        WorkspaceMemberFactory(workspace=workspace, user=other_user, role='member')
        response = auth_client.patch(
            f'{WORKSPACE_URL}{workspace.id}/members/{other_user.id}/',
            {'role': 'admin'},
        )
        assert response.status_code == 200
        assert response.data['role'] == 'admin'


@pytest.mark.django_db
class TestSelfRemoveProtection:
    """成員不可呼叫 DELETE 端點移除自己（應走專屬 leave 流程，Phase 2 此項僅阻擋）。"""

    def test_member_cannot_remove_self_via_member_api(self, api_client, workspace):
        """非 owner 的成員嘗試移除自己 → 403。"""
        u = UserFactory()
        WorkspaceMemberFactory(workspace=workspace, user=u, role='admin')
        api_client.force_authenticate(user=u)

        response = api_client.delete(
            f'{WORKSPACE_URL}{workspace.id}/members/{u.id}/',
        )
        assert response.status_code == 403


# ────────────────  Audit Log API ────────────────


AUDIT_LOG_PATH = '{}{}/audit-logs/'


@pytest.mark.django_db
class TestAuditLogList:
    def test_unauthenticated_returns_401(self, api_client, workspace):
        response = api_client.get(AUDIT_LOG_PATH.format(WORKSPACE_URL, workspace.id))
        assert response.status_code == 401

    def test_non_member_returns_403(self, api_client, other_user, workspace):
        api_client.force_authenticate(user=other_user)
        response = api_client.get(AUDIT_LOG_PATH.format(WORKSPACE_URL, workspace.id))
        assert response.status_code == 403

    def test_member_without_admin_returns_403(self, api_client, workspace):
        """一般 member 看不到稽核紀錄（敏感資訊）。"""
        u = UserFactory()
        WorkspaceMemberFactory(workspace=workspace, user=u, role='member')
        api_client.force_authenticate(user=u)
        response = api_client.get(AUDIT_LOG_PATH.format(WORKSPACE_URL, workspace.id))
        assert response.status_code == 403

    def test_admin_can_list_workspace_audit_logs(self, auth_client, user, workspace):
        """workspace.owner（auth_client 對應的使用者）可以看到自己工作區的紀錄。"""
        # 觸發一條稽核紀錄
        WorkspaceMemberFactory(workspace=workspace, role='member')

        response = auth_client.get(AUDIT_LOG_PATH.format(WORKSPACE_URL, workspace.id))
        assert response.status_code == 200
        assert response.data['count'] >= 1
        first = response.data['results'][0]
        assert first['scope_type'] == 'workspace'
        assert first['scope_id'] == str(workspace.id)
        assert first['action'] == MembershipAuditLog.Action.MEMBER_ADDED

    def test_audit_logs_scoped_to_workspace_only(self, auth_client, workspace):
        """另一個 workspace 的紀錄不應該外漏。"""
        other_ws = WorkspaceFactory()
        WorkspaceMemberFactory(workspace=other_ws)  # 在另一個 workspace 寫紀錄

        WorkspaceMemberFactory(workspace=workspace, role='member')  # 此 workspace 一條

        response = auth_client.get(AUDIT_LOG_PATH.format(WORKSPACE_URL, workspace.id))
        assert response.status_code == 200
        # 只有 1 條（且 scope_id 是請求的 workspace）
        assert all(
            log['scope_id'] == str(workspace.id) for log in response.data['results']
        )

    def test_audit_logs_ordered_by_changed_at_desc(self, auth_client, workspace):
        """最新的紀錄排在前面。"""
        WorkspaceMemberFactory(workspace=workspace, role='member')
        member = WorkspaceMemberFactory(workspace=workspace, role='member')
        member.role = WorkspaceMember.Role.ADMIN
        member.save()

        response = auth_client.get(AUDIT_LOG_PATH.format(WORKSPACE_URL, workspace.id))
        assert response.status_code == 200
        results = response.data['results']
        # 第一條應該是 role_changed（最新）
        assert results[0]['action'] == MembershipAuditLog.Action.ROLE_CHANGED
