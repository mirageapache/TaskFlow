"""行程事件 Model（Phase 2）。

工作區層級的行程，支援單次與 iCal RRULE 重複規則。
App 名稱故意用 `calendar_events`（非 `calendar`）以避開 Python 內建模組衝突。

規格：.doc/taskflow-database.md §3.15
"""
from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.workspaces.models import Workspace


class Event(BaseModel):
    """行程事件。

    `recurrence_rule` 為空字串 → 單次活動；非空 → 以 iCal RRULE 解析展開。
    `is_all_day=True` 時 `start_at` / `end_at` 的時分秒由前端忽略。
    `creator` 採 SET_NULL，避免帳號刪除時連帶刪掉行程；workspace 採 CASCADE。
    """

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='events',
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_events',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    is_all_day = models.BooleanField(default=False)
    recurrence_rule = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        db_table = 'events'
        ordering = ['start_at']
        indexes = [
            # 月曆範圍查詢的主索引
            models.Index(fields=['workspace', 'start_at']),
        ]
