"""Email 通知發送（Celery 非同步）。

由 notification Celery tasks 在建立 in-app 通知後呼叫，
將同樣內容以 Email 發送給使用者。

設計原則：
- EMAIL_NOTIFICATIONS_ENABLED=False 時靜默跳過（開發環境預設）
- EMAIL_HOST 留空時 Django 自動使用 console backend（印在 stdout）
- 發送失敗不影響 in-app 通知，僅記錄 log
- 所有參數為純量（str），確保 Celery JSON 序列化相容
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)

# ── 通知類型 → Email 主旨前綴對照 ──────────────────────────────────────
_SUBJECT_PREFIX = {
    'task_assigned': '[TaskFlow] 任務指派通知',
    'task_comment': '[TaskFlow] 任務留言通知',
    'task_status_changed': '[TaskFlow] 任務狀態變更通知',
    'workspace_invite': '[TaskFlow] 工作區邀請通知',
    'mention': '[TaskFlow] 你被提及了',
}


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_notification_email(
    self,
    recipient_email: str,
    notif_type: str,
    title: str,
    body: str,
    payload: dict | None = None,
):
    """寄送通知 Email 給指定收件者。

    Parameters
    ----------
    recipient_email : str
        收件者 Email 地址
    notif_type : str
        通知類型（對應 Notification.NotifType）
    title : str
        通知標題（用作 Email 內文主標題）
    body : str
        通知內文
    payload : dict, optional
        附帶資料（可用於產生連結）
    """
    from django.conf import settings

    if not getattr(settings, 'EMAIL_NOTIFICATIONS_ENABLED', False):
        return

    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags

    subject = _SUBJECT_PREFIX.get(notif_type, '[TaskFlow] 通知')
    payload = payload or {}

    # 構建 Email 內容
    context = {
        'title': title,
        'body': body,
        'notif_type': notif_type,
        'payload': payload,
        'frontend_url': getattr(settings, 'CORS_ALLOWED_ORIGINS', [''])[0],
    }

    try:
        html_message = render_to_string(
            'notifications/email_notification.html', context,
        )
        plain_message = strip_tags(html_message)
    except Exception:
        # Template 不存在時 fallback 到純文字
        plain_message = f'{title}\n\n{body}' if body else title
        html_message = None

    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient_email],
        html_message=html_message,
        fail_silently=False,
    )
    logger.info('Email notification sent to %s [%s]', recipient_email, notif_type)
