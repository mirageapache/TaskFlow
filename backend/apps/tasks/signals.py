"""Task 變更紀錄自動寫入（Django Signals）。

設計：
- `pre_save`  從 DB 抓舊值，掛到 instance._activity_old，供 post_save 算 diff
- `post_save` 視情況寫 'created' / 'updated' / 'deleted' log
- `TaskAssignee` post_save / post_delete 寫 'assignee_added' / 'assignee_removed'
- `Task.tags.through` m2m_changed 寫 'tags_added' / 'tags_removed' / 'tags_cleared'
- `TaskComment` post_save 寫 'comment_added'

actor 來源：`apps.users.middleware.get_current_user()`（thread-local），無 HTTP context 時為 None。
"""
from django.db.models.signals import (
    m2m_changed,
    post_delete,
    post_save,
    pre_save,
)
from django.dispatch import receiver

from apps.tasks.models import (
    Task,
    TaskActivityLog,
    TaskAssignee,
    TaskComment,
)
from apps.users.middleware import get_current_user

# Task 上會被追蹤 diff 的純量欄位（M2M / FK 用其他 signal 處理）
# 用 *_id 而非物件本身，避免 access 觸發額外查詢
TRACKED_FIELDS = [
    'title', 'description', 'priority',
    'status_id', 'parent_task_id',
    'start_date', 'due_date', 'estimated_hours', 'order',
]


@receiver(pre_save, sender=Task)
def task_capture_old_state(sender, instance, **kwargs):
    """save() 之前從 DB 抓舊值快照，掛到 instance 供 post_save 比對。

    新建立的 Task 雖然 instance.pk 已有 UUID（default=uuid.uuid4），
    但 DB 還沒這筆紀錄，`Task.all_objects.get` 會 raise DoesNotExist，
    此時 _activity_old 設為 None，告訴 post_save 「這是新增不是更新」。
    """
    instance._activity_old = None
    instance._activity_old_deleted_at = None
    if instance.pk is None:
        return
    try:
        old = Task.all_objects.get(pk=instance.pk)
    except Task.DoesNotExist:
        return
    instance._activity_old = {f: getattr(old, f) for f in TRACKED_FIELDS}
    instance._activity_old_deleted_at = old.deleted_at


@receiver(post_save, sender=Task)
def task_log_save(sender, instance, created, **kwargs):
    """依事件類型寫對應的 ActivityLog：created / deleted / updated。"""
    actor = get_current_user()

    if created:
        TaskActivityLog.objects.create(
            task=instance, actor=actor,
            action='created',
            detail={'title': instance.title},
        )
        return

    # 偵測「軟刪除」轉換：deleted_at 從 None → 有值
    if instance.deleted_at and not getattr(instance, '_activity_old_deleted_at', None):
        TaskActivityLog.objects.create(
            task=instance, actor=actor, action='deleted', detail={},
        )
        return

    # 計算欄位 diff
    old = getattr(instance, '_activity_old', None)
    if not old:
        return
    changes = {}
    for field in TRACKED_FIELDS:
        old_val = old[field]
        new_val = getattr(instance, field)
        if old_val != new_val:
            changes[field] = {
                'from': str(old_val) if old_val is not None else None,
                'to': str(new_val) if new_val is not None else None,
            }
    if changes:
        TaskActivityLog.objects.create(
            task=instance, actor=actor,
            action='updated',
            detail={'changes': changes},
        )


@receiver(post_save, sender=TaskAssignee)
def assignee_added(sender, instance, created, **kwargs):
    """TaskAssignee 採自訂 through，需直接監聽其 post_save 而非 m2m_changed。"""
    if not created:
        return
    TaskActivityLog.objects.create(
        task=instance.task,
        actor=get_current_user(),
        action='assignee_added',
        detail={'user_id': str(instance.user_id)},
    )


@receiver(post_delete, sender=TaskAssignee)
def assignee_removed(sender, instance, **kwargs):
    """指派移除：包括明確 DELETE 端點與 task.assignees.clear()。"""
    TaskActivityLog.objects.create(
        task=instance.task,
        actor=get_current_user(),
        action='assignee_removed',
        detail={'user_id': str(instance.user_id)},
    )


@receiver(m2m_changed, sender=Task.tags.through)
def tags_changed(sender, instance, action, pk_set, **kwargs):
    """Tags 為純 M2M（無自訂 through），靠 m2m_changed 處理。"""
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    actor = get_current_user()
    if action == 'post_clear':
        TaskActivityLog.objects.create(
            task=instance, actor=actor, action='tags_cleared', detail={},
        )
        return
    log_action = 'tags_added' if action == 'post_add' else 'tags_removed'
    TaskActivityLog.objects.create(
        task=instance, actor=actor, action=log_action,
        detail={'tag_ids': sorted(str(pk) for pk in (pk_set or set()))},
    )


@receiver(post_save, sender=TaskComment)
def comment_added(sender, instance, created, **kwargs):
    """新增留言時自動寫 log；編輯既有留言不寫（避免噪音）。"""
    if not created:
        return
    TaskActivityLog.objects.create(
        task=instance.task,
        actor=get_current_user(),
        action='comment_added',
        detail={'comment_id': str(instance.id)},
    )
