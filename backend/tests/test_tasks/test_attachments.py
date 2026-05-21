"""
Attachment API TDD 測試 — Phase 1
規格：.doc/taskflow-backend.md §7.3、.doc/taskflow-api_doc.md §5
端點：
  POST   /api/v1/tasks/{id}/attachments/request-upload/
  PATCH  /api/v1/tasks/{id}/attachments/{aid}/confirm/
  GET    /api/v1/tasks/{id}/attachments/{aid}/download/
  GET    /api/v1/tasks/{id}/attachments/
S3 互動以 mock 方式驗證，不實際呼叫 AWS。
"""
from unittest.mock import patch

import pytest

from apps.tasks.serializers import AttachmentRequestSerializer
from tests.factories import ProjectMemberFactory, UserFactory

TASKS_URL = '/api/v1/tasks/'


# ────────────── Serializer 驗證 ──────────────

class TestAttachmentRequestSerializer:
    """純驗證測試，不需 DB"""

    def test_valid_pdf(self):
        data = {
            'file_name': 'report.pdf',
            'file_size': 1024 * 100,
            'mime_type': 'application/pdf',
        }
        serializer = AttachmentRequestSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_file_size_over_limit(self):
        data = {
            'file_name': 'big.pdf',
            'file_size': 11 * 1024 * 1024,
            'mime_type': 'application/pdf',
        }
        serializer = AttachmentRequestSerializer(data=data)
        assert not serializer.is_valid()
        assert 'file_size' in serializer.errors

    def test_invalid_mime_type(self):
        data = {
            'file_name': 'script.exe',
            'file_size': 1024,
            'mime_type': 'application/x-msdownload',
        }
        serializer = AttachmentRequestSerializer(data=data)
        assert not serializer.is_valid()
        assert 'mime_type' in serializer.errors

    def test_negative_file_size(self):
        data = {
            'file_name': 'x.pdf',
            'file_size': -1,
            'mime_type': 'application/pdf',
        }
        serializer = AttachmentRequestSerializer(data=data)
        assert not serializer.is_valid()


# ────────────── 上傳請求 ──────────────

@pytest.mark.django_db
class TestRequestUpload:
    @patch('apps.tasks.views.generate_upload_post')
    def test_request_upload_returns_presigned(self, mock_gen, auth_client, task):
        mock_gen.return_value = {
            'url': 'https://s3.example.com/bucket',
            'fields': {'key': 'attachments/x', 'Content-Type': 'application/pdf'},
        }
        response = auth_client.post(
            f'{TASKS_URL}{task.id}/attachments/request-upload/',
            {
                'file_name': 'spec.pdf',
                'file_size': 4096,
                'mime_type': 'application/pdf',
            },
            format='json',
        )
        assert response.status_code == 200
        assert response.data['upload_url'].startswith('https://')
        assert 'attachment_id' in response.data
        assert mock_gen.called

    @patch('apps.tasks.views.generate_upload_post')
    def test_request_upload_creates_attachment_record(self, mock_gen, auth_client, task):
        mock_gen.return_value = {'url': 'https://s3', 'fields': {}}
        response = auth_client.post(
            f'{TASKS_URL}{task.id}/attachments/request-upload/',
            {'file_name': 'a.pdf', 'file_size': 100, 'mime_type': 'application/pdf'},
            format='json',
        )
        assert response.status_code == 200
        from apps.tasks.models import TaskAttachment
        att = TaskAttachment.objects.get(pk=response.data['attachment_id'])
        assert att.is_confirmed is False
        assert att.file_size == 100
        assert att.uploader_id == task.creator_id

    def test_request_upload_invalid_mime(self, auth_client, task):
        response = auth_client.post(
            f'{TASKS_URL}{task.id}/attachments/request-upload/',
            {'file_name': 'x.exe', 'file_size': 1, 'mime_type': 'application/x-msdownload'},
            format='json',
        )
        assert response.status_code == 400

    def test_request_upload_oversize(self, auth_client, task):
        response = auth_client.post(
            f'{TASKS_URL}{task.id}/attachments/request-upload/',
            {'file_name': 'big.pdf', 'file_size': 11 * 1024 * 1024, 'mime_type': 'application/pdf'},
            format='json',
        )
        assert response.status_code == 400

    def test_stranger_cannot_request(self, api_client, other_user, task):
        api_client.force_authenticate(user=other_user)
        response = api_client.post(
            f'{TASKS_URL}{task.id}/attachments/request-upload/',
            {'file_name': 'x.pdf', 'file_size': 1, 'mime_type': 'application/pdf'},
            format='json',
        )
        assert response.status_code == 403


# ────────────── 確認上傳 ──────────────

@pytest.mark.django_db
class TestConfirmUpload:
    def _create_pending(self, task, uploader):
        from apps.tasks.models import TaskAttachment
        return TaskAttachment.objects.create(
            task=task, uploader=uploader,
            file_name='f.pdf', file_key='attachments/x/f.pdf',
            file_size=1024, mime_type='application/pdf',
            is_confirmed=False,
        )

    def test_uploader_can_confirm(self, auth_client, task, user):
        att = self._create_pending(task, uploader=user)
        response = auth_client.patch(
            f'{TASKS_URL}{task.id}/attachments/{att.id}/confirm/',
        )
        assert response.status_code == 200
        att.refresh_from_db()
        assert att.is_confirmed is True

    def test_workspace_owner_can_confirm_others_upload(self, auth_client, task):
        other_uploader = UserFactory()
        att = self._create_pending(task, uploader=other_uploader)
        response = auth_client.patch(
            f'{TASKS_URL}{task.id}/attachments/{att.id}/confirm/',
        )
        assert response.status_code == 200

    def test_random_member_cannot_confirm(self, api_client, other_user, task, user):
        ProjectMemberFactory(project=task.project, user=other_user, role='member')
        att = self._create_pending(task, uploader=user)
        api_client.force_authenticate(user=other_user)
        response = api_client.patch(
            f'{TASKS_URL}{task.id}/attachments/{att.id}/confirm/',
        )
        assert response.status_code == 403


# ────────────── 下載 ──────────────

@pytest.mark.django_db
class TestDownload:
    @patch('apps.tasks.views.generate_download_url')
    def test_download_returns_presigned_url(self, mock_dl, auth_client, task, user):
        mock_dl.return_value = 'https://s3.example.com/signed-get'
        from apps.tasks.models import TaskAttachment
        att = TaskAttachment.objects.create(
            task=task, uploader=user,
            file_name='f.pdf', file_key='attachments/x/f.pdf',
            file_size=1024, mime_type='application/pdf',
            is_confirmed=True,
        )
        response = auth_client.get(
            f'{TASKS_URL}{task.id}/attachments/{att.id}/download/',
        )
        assert response.status_code == 200
        assert response.data['download_url'].startswith('https://')

    def test_download_unconfirmed_returns_400(self, auth_client, task, user):
        from apps.tasks.models import TaskAttachment
        att = TaskAttachment.objects.create(
            task=task, uploader=user,
            file_name='f.pdf', file_key='attachments/x/f.pdf',
            file_size=1024, mime_type='application/pdf',
            is_confirmed=False,
        )
        response = auth_client.get(
            f'{TASKS_URL}{task.id}/attachments/{att.id}/download/',
        )
        assert response.status_code == 400

    def test_stranger_cannot_download(self, api_client, other_user, task, user):
        from apps.tasks.models import TaskAttachment
        att = TaskAttachment.objects.create(
            task=task, uploader=user,
            file_name='f.pdf', file_key='attachments/x/f.pdf',
            file_size=1024, mime_type='application/pdf',
            is_confirmed=True,
        )
        api_client.force_authenticate(user=other_user)
        response = api_client.get(
            f'{TASKS_URL}{task.id}/attachments/{att.id}/download/',
        )
        assert response.status_code == 403


# ────────────── 列表 ──────────────

@pytest.mark.django_db
class TestAttachmentList:
    def test_list_returns_attachments(self, auth_client, task, user):
        from apps.tasks.models import TaskAttachment
        TaskAttachment.objects.create(
            task=task, uploader=user, file_name='a.pdf',
            file_key='k/a', file_size=1, mime_type='application/pdf',
        )
        TaskAttachment.objects.create(
            task=task, uploader=user, file_name='b.pdf',
            file_key='k/b', file_size=1, mime_type='application/pdf',
        )
        response = auth_client.get(f'{TASKS_URL}{task.id}/attachments/')
        assert response.status_code == 200
        assert response.data['count'] == 2
