/**
 * Project Store 單元測試
 *
 * Project 以 workspaceId 分桶快取（不同 workspace 各自獨立快取）。
 *
 * 行為：
 * - fetchByWorkspace(id) 會帶 ?workspace=<id> query
 * - 同一 workspace 已 loaded 時不再打 API（除 force）
 * - 不同 workspace 互不影響快取
 * - create() 把新建 project 加到對應 workspace 的快取
 * - getByWorkspace() 永遠回 array（無資料則 []）
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

import client from '@/api/client'
import { useProjectStore } from '@/stores/project'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

const projectsW1 = [
  {
    id: 'p1',
    workspace: 'w1',
    name: '官網改版',
    description: '',
    color: '#F97316',
    created_at: '2026-04-01T00:00:00Z',
    updated_at: '2026-04-01T00:00:00Z',
  },
  {
    id: 'p2',
    workspace: 'w1',
    name: '客服自動化',
    description: '',
    color: '#2563EB',
    created_at: '2026-04-02T00:00:00Z',
    updated_at: '2026-04-02T00:00:00Z',
  },
]

const projectsW2 = [
  {
    id: 'p3',
    workspace: 'w2',
    name: '行銷活動',
    description: '',
    color: '#059669',
    created_at: '2026-04-03T00:00:00Z',
    updated_at: '2026-04-03T00:00:00Z',
  },
]

function paginated<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results }
}

describe('useProjectStore', () => {
  beforeEach(() => {
    vi.mocked(client.get).mockReset()
    vi.mocked(client.post).mockReset()
  })

  it('初始狀態：byWorkspace 為空、loading=false', () => {
    const store = useProjectStore()
    expect(store.byWorkspace).toEqual({})
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('fetchByWorkspace(id) 帶 ?workspace 並寫入對應快取', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated(projectsW1) })

    const store = useProjectStore()
    await store.fetchByWorkspace('w1')

    expect(client.get).toHaveBeenCalledWith('/projects/', { params: { workspace: 'w1' } })
    expect(store.byWorkspace.w1).toEqual(projectsW1)
  })

  it('同一 workspace 已 loaded 時不再打 API', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated(projectsW1) })
    const store = useProjectStore()
    await store.fetchByWorkspace('w1')
    vi.mocked(client.get).mockClear()

    await store.fetchByWorkspace('w1')

    expect(client.get).not.toHaveBeenCalled()
  })

  it('fetchByWorkspace({ force: true }) 強制重抓', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce({ data: paginated([projectsW1[0]]) })
      .mockResolvedValueOnce({ data: paginated(projectsW1) })

    const store = useProjectStore()
    await store.fetchByWorkspace('w1')
    expect(store.byWorkspace.w1).toHaveLength(1)

    await store.fetchByWorkspace('w1', { force: true })
    expect(store.byWorkspace.w1).toHaveLength(2)
    expect(client.get).toHaveBeenCalledTimes(2)
  })

  it('不同 workspace 各自獨立快取', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce({ data: paginated(projectsW1) })
      .mockResolvedValueOnce({ data: paginated(projectsW2) })

    const store = useProjectStore()
    await store.fetchByWorkspace('w1')
    await store.fetchByWorkspace('w2')

    expect(store.byWorkspace.w1).toEqual(projectsW1)
    expect(store.byWorkspace.w2).toEqual(projectsW2)
    expect(client.get).toHaveBeenCalledTimes(2)
  })

  it('fetchByWorkspace 失敗：error 有值、loading reset、未寫入快取', async () => {
    vi.mocked(client.get).mockRejectedValueOnce(new Error('500'))
    const store = useProjectStore()

    await expect(store.fetchByWorkspace('w1')).rejects.toThrow()

    expect(store.error).not.toBeNull()
    expect(store.byWorkspace.w1).toBeUndefined()
    expect(store.loading).toBe(false)
  })

  it('create() 將新建 project 加到對應 workspace 快取', async () => {
    const newProject = {
      id: 'p9',
      workspace: 'w1',
      name: '新專案',
      description: '',
      color: '#F97316',
      created_at: '2026-04-29T00:00:00Z',
      updated_at: '2026-04-29T00:00:00Z',
    }
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated(projectsW1) })
    vi.mocked(client.post).mockResolvedValueOnce({ data: newProject })

    const store = useProjectStore()
    await store.fetchByWorkspace('w1')

    const result = await store.create({ workspace_id: 'w1', name: '新專案' })

    expect(client.post).toHaveBeenCalledWith('/projects/', {
      workspace_id: 'w1',
      name: '新專案',
    })
    expect(result).toEqual(newProject)
    expect(store.byWorkspace.w1).toHaveLength(3)
    expect(store.byWorkspace.w1[2]).toEqual(newProject)
  })

  it('create() 對未載入的 workspace 也能寫入（建立新桶）', async () => {
    const newProject = {
      id: 'p9',
      workspace: 'w-new',
      name: '新專案',
      description: '',
      color: '#F97316',
      created_at: '2026-04-29T00:00:00Z',
      updated_at: '2026-04-29T00:00:00Z',
    }
    vi.mocked(client.post).mockResolvedValueOnce({ data: newProject })

    const store = useProjectStore()
    await store.create({ workspace_id: 'w-new', name: '新專案' })

    expect(store.byWorkspace['w-new']).toEqual([newProject])
  })

  it('getByWorkspace 未載入時回空陣列', () => {
    const store = useProjectStore()
    expect(store.getByWorkspace('not-loaded')).toEqual([])
  })
})
