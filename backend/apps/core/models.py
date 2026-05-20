import uuid

from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    """軟刪除查詢管理器：只回傳 `deleted_at IS NULL` 的資料列。

    繼承 BaseModel 的 Model 預設使用此 Manager（`objects`），
    若需要查詢「含已刪除」資料，請改用 `all_objects`。
    """

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class BaseModel(models.Model):
    """所有業務 Model 的基底類別。

    提供：
      - UUID 主鍵 (`id`)：避免序號流水號被列舉
      - 建立 / 更新 / 軟刪除時間戳記
      - 兩個 Manager：`objects`（過濾已刪除） / `all_objects`（含已刪除）
    `abstract = True` 表示本類別不會建立實際資料表，僅供繼承。
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def soft_delete(self):
        """將 `deleted_at` 設為現在時間，達成軟刪除（不真的 DELETE FROM）。"""
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    class Meta:
        abstract = True
