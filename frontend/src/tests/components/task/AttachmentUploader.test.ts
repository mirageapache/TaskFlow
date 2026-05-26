/**
 * AttachmentUploader 元件測試
 *
 * 規格：.doc/taskflow-frontend.md（Phase 2）+ .doc/taskflow-backend.md §7.3
 *
 * Presigned URL 六步流程：
 *  1. 前端驗證（MIME / size）後 POST /tasks/{taskId}/attachments/request-upload/
 *  2. 後端產生 S3 presigned POST + 建立 is_confirmed=false 的 Attachment
 *  3. 回傳 { attachment_id, upload_url, fields }
 *  4. 前端以 multipart/form-data 直傳 S3（**不能帶 JWT**，所以走原生 fetch、不能用 axios client）
 *  5. PATCH /tasks/{taskId}/attachments/{attachmentId}/confirm/ → is_confirmed=true
 *  6. （下載另外走）GET /tasks/{taskId}/attachments/{attachmentId}/download/
 *
 * 涵蓋：
 *   - 檔案過大（>10MB）：阻擋、不呼叫 API、顯示錯誤
 *   - MIME 不在白名單：阻擋、不呼叫 API、顯示錯誤
 *   - happy path：six-step 完成後 emit uploaded(Attachment)
 *   - S3 直傳失敗：呼叫 request-upload 後若 fetch 失敗，不呼叫 confirm，顯示錯誤
 *   - confirm 失敗：fetch 成功但 PATCH 失敗，顯示錯誤
 *   - 上傳中：button 應 disabled，避免重複觸發
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

import client from '@/api/client'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

import AttachmentUploader from '@/components/task/AttachmentUploader.vue'

function makeFile(name: string, sizeBytes: number, type: string): File {
  // 以 Object.defineProperty 把 size 改成測試需要的值，避免真的配置這麼大記憶體
  const blob = new Blob(['x'], { type })
  const file = new File([blob], name, { type })
  Object.defineProperty(file, 'size', { value: sizeBytes })
  return file
}

function setFileInput(input: HTMLInputElement, files: File[]) {
  Object.defineProperty(input, 'files', { value: files, configurable: true })
  input.dispatchEvent(new Event('change'))
}

const successResponse = {
  ok: true,
  status: 204,
  text: async () => '',
} as unknown as Response

describe('AttachmentUploader', () => {
  beforeEach(() => {
    vi.mocked(client.get).mockReset()
    vi.mocked(client.post).mockReset()
    vi.mocked(client.patch).mockReset()
    vi.mocked(client.delete).mockReset()
    // 用 spyOn 包 global.fetch，避免污染其他測試檔
    vi.spyOn(globalThis, 'fetch').mockReset()
  })

  it('檔案超過 10MB：不呼叫 request-upload，顯示錯誤訊息', async () => {
    const wrapper = mount(AttachmentUploader, { props: { taskId: 't1' } })
    const input = wrapper.find('[data-test="file-input"]').element as HTMLInputElement
    const tooBig = makeFile('big.pdf', 10 * 1024 * 1024 + 1, 'application/pdf')

    setFileInput(input, [tooBig])
    await flushPromises()

    expect(client.post).not.toHaveBeenCalled()
    expect(globalThis.fetch).not.toHaveBeenCalled()
    expect(wrapper.find('[data-test="upload-error"]').text()).toMatch(/10\s*MB|過大|too\s*large/i)
  })

  it('MIME 不在白名單：不呼叫 API，顯示錯誤訊息', async () => {
    const wrapper = mount(AttachmentUploader, { props: { taskId: 't1' } })
    const input = wrapper.find('[data-test="file-input"]').element as HTMLInputElement
    const badType = makeFile('virus.exe', 1024, 'application/x-msdownload')

    setFileInput(input, [badType])
    await flushPromises()

    expect(client.post).not.toHaveBeenCalled()
    expect(globalThis.fetch).not.toHaveBeenCalled()
    expect(wrapper.find('[data-test="upload-error"]').exists()).toBe(true)
  })

  it('happy path：完成 6 步流程後 emit uploaded 帶 Attachment', async () => {
    const file = makeFile('spec.pdf', 1024, 'application/pdf')

    // step 1+3：request-upload 回 presigned POST 參數
    vi.mocked(client.post).mockResolvedValueOnce({
      data: {
        attachment_id: 'a1',
        upload_url: 'https://s3.example.com/bucket',
        fields: { key: 'tasks/t1/spec.pdf', policy: 'POLICY', signature: 'SIG' },
      },
    })
    // step 4：S3 直傳成功
    vi.mocked(globalThis.fetch).mockResolvedValueOnce(successResponse)
    // step 5：confirm 回完整 Attachment
    const confirmed = {
      id: 'a1',
      uploader: { id: 'u1', email: 'a@b.com', username: 'A', avatar_url: null },
      file_name: 'spec.pdf',
      file_key: 'tasks/t1/spec.pdf',
      file_size: 1024,
      mime_type: 'application/pdf',
      is_confirmed: true,
      created_at: '2026-05-22T00:00:00Z',
      updated_at: '2026-05-22T00:00:00Z',
    }
    vi.mocked(client.patch).mockResolvedValueOnce({ data: confirmed })

    const wrapper = mount(AttachmentUploader, { props: { taskId: 't1' } })
    const input = wrapper.find('[data-test="file-input"]').element as HTMLInputElement
    setFileInput(input, [file])
    await flushPromises()

    // step 1：request-upload
    expect(client.post).toHaveBeenCalledWith(
      '/tasks/t1/attachments/request-upload/',
      { file_name: 'spec.pdf', file_size: 1024, mime_type: 'application/pdf' },
    )

    // step 4：fetch S3 with multipart/form-data；不能帶 Authorization
    expect(globalThis.fetch).toHaveBeenCalledTimes(1)
    const [url, init] = vi.mocked(globalThis.fetch).mock.calls[0]
    expect(url).toBe('https://s3.example.com/bucket')
    expect(init?.method).toBe('POST')
    const body = init?.body as FormData
    expect(body).toBeInstanceOf(FormData)
    expect(body.get('key')).toBe('tasks/t1/spec.pdf')
    expect(body.get('policy')).toBe('POLICY')
    expect(body.get('signature')).toBe('SIG')
    // file 必須是 multipart 最後一欄
    expect(body.get('file')).toBeInstanceOf(File)
    // 不能帶 Authorization header（S3 會拒收）
    expect(init?.headers).toBeUndefined()

    // step 5：confirm
    expect(client.patch).toHaveBeenCalledWith('/tasks/t1/attachments/a1/confirm/')

    // emit
    expect(wrapper.emitted('uploaded')).toBeTruthy()
    expect(wrapper.emitted('uploaded')![0][0]).toEqual(confirmed)
  })

  it('S3 直傳失敗：不呼叫 confirm、顯示錯誤', async () => {
    const file = makeFile('a.png', 2048, 'image/png')

    vi.mocked(client.post).mockResolvedValueOnce({
      data: { attachment_id: 'a1', upload_url: 'https://s3', fields: {} },
    })
    vi.mocked(globalThis.fetch).mockResolvedValueOnce({
      ok: false,
      status: 403,
      text: async () => 'AccessDenied',
    } as unknown as Response)

    const wrapper = mount(AttachmentUploader, { props: { taskId: 't1' } })
    const input = wrapper.find('[data-test="file-input"]').element as HTMLInputElement
    setFileInput(input, [file])
    await flushPromises()

    expect(client.patch).not.toHaveBeenCalled()
    expect(wrapper.find('[data-test="upload-error"]').exists()).toBe(true)
    expect(wrapper.emitted('uploaded')).toBeFalsy()
  })

  it('confirm 失敗：S3 已直傳，仍顯示錯誤、不 emit uploaded', async () => {
    const file = makeFile('a.png', 2048, 'image/png')

    vi.mocked(client.post).mockResolvedValueOnce({
      data: { attachment_id: 'a1', upload_url: 'https://s3', fields: {} },
    })
    vi.mocked(globalThis.fetch).mockResolvedValueOnce(successResponse)
    vi.mocked(client.patch).mockRejectedValueOnce(new Error('500'))

    const wrapper = mount(AttachmentUploader, { props: { taskId: 't1' } })
    const input = wrapper.find('[data-test="file-input"]').element as HTMLInputElement
    setFileInput(input, [file])
    await flushPromises()

    expect(wrapper.find('[data-test="upload-error"]').exists()).toBe(true)
    expect(wrapper.emitted('uploaded')).toBeFalsy()
  })

  it('上傳中：input 進入 disabled 狀態、防止重複觸發', async () => {
    const file = makeFile('a.png', 2048, 'image/png')

    let resolveRequest: (v: unknown) => void = () => {}
    vi.mocked(client.post).mockReturnValueOnce(
      new Promise((resolve) => {
        resolveRequest = resolve
      }),
    )

    const wrapper = mount(AttachmentUploader, { props: { taskId: 't1' } })
    const input = wrapper.find('[data-test="file-input"]').element as HTMLInputElement
    setFileInput(input, [file])
    await flushPromises()

    expect(input.disabled).toBe(true)

    resolveRequest({ data: { attachment_id: 'a1', upload_url: 'https://s3', fields: {} } })
    vi.mocked(globalThis.fetch).mockResolvedValueOnce(successResponse)
    vi.mocked(client.patch).mockResolvedValueOnce({
      data: {
        id: 'a1',
        uploader: null,
        file_name: 'a.png',
        file_key: 'k',
        file_size: 2048,
        mime_type: 'image/png',
        is_confirmed: true,
        created_at: '',
        updated_at: '',
      },
    })
    await flushPromises()

    expect(input.disabled).toBe(false)
  })
})
