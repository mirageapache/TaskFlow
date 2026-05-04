"""Membership 變動自動寫入 MembershipAuditLog（Django Signals）。

監聽：
- WorkspaceMember 與 ProjectMember 的 pre_save / post_save / post_delete

行為：
- pre_save：抓舊 role / 舊 deleted_at 快照，掛在 instance 給 post_save 比對
- post_save (created=True)：寫 'member_added'
- post_save (deleted_at: None → 有值)：寫 'member_removed'
- post_save (role 變更)：寫 'role_changed'，附 old_role / new_role
- post_delete：寫 'member_removed'（hard delete，避免漏記）
- 其他 save（無實質變化）：不寫，避免噪音

actor 來源：apps.users.middleware.get_current_user()（thread-local，無 HTTP context 時為 None）

設計：兩個 Member 模型結構相同（role + soft delete），用共用 helper
`_emit_audit_log` 處理寫入，避免 workspace / project 兩份重複邏輯。

規格：.doc/taskflow-backend.md §9.1 / .doc/taskflow-database.md §3.18
"""
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.projects.models import ProjectMember
from apps.users.middleware import get_current_user
from apps.workspaces.models import MembershipAuditLog, WorkspaceMember


def _capture_old_state(sender, instance, **_kwargs):
    """pre_save：用 sender.all_objects 從 DB 抓舊狀態，掛在 instance。

    用 all_objects（含已軟刪）才抓得到剛被 soft_delete 過、再次 save 的紀錄。
    新建 instance 還沒入 DB → DoesNotExist → 設 None，post_save 視為 created。
    """
    instance._audit_old_role = None
    instance._audit_old_deleted_at = None
    if instance.pk is None:
        return
    try:
        old = sender.all_objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    instance._audit_old_role = old.role
    instance._audit_old_deleted_at = old.deleted_at


def _emit_audit_log(instance, scope_type, scope_id, *, created):
    """依事件類型寫對應的 MembershipAuditLog；無變更則不寫。"""
    actor = get_current_user()
    target = instance.user

    if created:
        MembershipAuditLog.objects.create(
            actor=actor,
            target_user=target,
            action=MembershipAuditLog.Action.MEMBER_ADDED,
            scope_type=scope_type,
            scope_id=scope_id,
            new_role=instance.role,
        )
        return

    # 偵測「軟刪除」：deleted_at 從 None → 有值
    old_deleted_at = getattr(instance, '_audit_old_deleted_at', None)
    if instance.deleted_at and not old_deleted_at:
        MembershipAuditLog.objects.create(
            actor=actor,
            target_user=target,
            action=MembershipAuditLog.Action.MEMBER_REMOVED,
            scope_type=scope_type,
            scope_id=scope_id,
            old_role=instance.role,
        )
        return

    # 角色變更
    old_role = getattr(instance, '_audit_old_role', None)
    if old_role is not None and old_role != instance.role:
        MembershipAuditLog.objects.create(
            actor=actor,
            target_user=target,
            action=MembershipAuditLog.Action.ROLE_CHANGED,
            scope_type=scope_type,
            scope_id=scope_id,
            old_role=old_role,
            new_role=instance.role,
        )


# ────────────── WorkspaceMember ──────────────


@receiver(pre_save, sender=WorkspaceMember)
def workspace_member_capture_old(sender, instance, **kwargs):
    _capture_old_state(sender, instance, **kwargs)


@receiver(post_save, sender=WorkspaceMember)
def workspace_member_log_save(sender, instance, created, **kwargs):
    _emit_audit_log(
        instance,
        scope_type=MembershipAuditLog.ScopeType.WORKSPACE,
        scope_id=instance.workspace_id,
        created=created,
    )


@receiver(post_delete, sender=WorkspaceMember)
def workspace_member_log_delete(sender, instance, **kwargs):
    """hard delete 路徑（極少用，預設都走 soft_delete；保險起見補上）。"""
    MembershipAuditLog.objects.create(
        actor=get_current_user(),
        target_user=instance.user,
        action=MembershipAuditLog.Action.MEMBER_REMOVED,
        scope_type=MembershipAuditLog.ScopeType.WORKSPACE,
        scope_id=instance.workspace_id,
        old_role=instance.role,
    )


# ────────────── ProjectMember ──────────────


@receiver(pre_save, sender=ProjectMember)
def project_member_capture_old(sender, instance, **kwargs):
    _capture_old_state(sender, instance, **kwargs)


@receiver(post_save, sender=ProjectMember)
def project_member_log_save(sender, instance, created, **kwargs):
    _emit_audit_log(
        instance,
        scope_type=MembershipAuditLog.ScopeType.PROJECT,
        scope_id=instance.project_id,
        created=created,
    )


@receiver(post_delete, sender=ProjectMember)
def project_member_log_delete(sender, instance, **kwargs):
    MembershipAuditLog.objects.create(
        actor=get_current_user(),
        target_user=instance.user,
        action=MembershipAuditLog.Action.MEMBER_REMOVED,
        scope_type=MembershipAuditLog.ScopeType.PROJECT,
        scope_id=instance.project_id,
        old_role=instance.role,
    )
