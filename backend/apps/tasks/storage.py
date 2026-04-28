"""S3 Presigned URL 工具，集中於此以便測試 mock。

本檔案只負責「產生簽名 URL」，不會實際傳檔。
- `generate_upload_post()`：產生上傳用 multipart/form-data 表單（POST 直傳 S3）
- `generate_download_url()`：產生短期效期的下載 URL（GET）
測試時於 view 層 mock 這兩個函式即可，避免實際打 AWS。
"""
import uuid

import boto3
from django.conf import settings


def _client():
    """建立 boto3 S3 client；支援 MinIO 等 S3 相容服務（透過 endpoint_url）。"""
    kwargs = {'region_name': settings.AWS_S3_REGION}
    if settings.AWS_ACCESS_KEY_ID:
        kwargs['aws_access_key_id'] = settings.AWS_ACCESS_KEY_ID
        kwargs['aws_secret_access_key'] = settings.AWS_SECRET_ACCESS_KEY
    if settings.AWS_S3_ENDPOINT_URL:
        kwargs['endpoint_url'] = settings.AWS_S3_ENDPOINT_URL
    return boto3.client('s3', **kwargs)


def build_object_key(task_id, file_name):
    """組出 S3 物件 key：`attachments/<task_uuid>/<random>-<original-name>`。

    隨機後綴避免同名檔案覆蓋；同時將路徑分隔符轉為底線防 path traversal。
    """
    safe = file_name.replace('/', '_').replace('\\', '_')
    return f'attachments/{task_id}/{uuid.uuid4().hex[:8]}-{safe}'


def generate_upload_post(file_key, mime_type, max_size):
    """產生 Presigned POST：限制 Content-Type 與檔案大小，避免被濫用上傳任意檔。"""
    return _client().generate_presigned_post(
        Bucket=settings.AWS_S3_BUCKET,
        Key=file_key,
        Fields={'Content-Type': mime_type},
        Conditions=[
            {'Content-Type': mime_type},
            ['content-length-range', 1, max_size],
        ],
        ExpiresIn=settings.PRESIGNED_URL_EXPIRES_SECONDS,
    )


def generate_download_url(file_key):
    """產生短期效期（預設 15 分鐘）的下載 URL。"""
    return _client().generate_presigned_url(
        'get_object',
        Params={'Bucket': settings.AWS_S3_BUCKET, 'Key': file_key},
        ExpiresIn=settings.PRESIGNED_URL_EXPIRES_SECONDS,
    )
