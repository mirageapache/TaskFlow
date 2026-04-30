/**
 * Workspace Store 單元測試
 * 規格：.doc/taskflow-frontend.md §4.4 / 列表取得與快取
 *
 * 行為：
 * - fetchAll() 取列表並設定 loaded=true
 * - 已 loaded 時 fetchAll() 不再打 API（除非 force）
 * - create() 建立後加入快取
 * - getById() 從快取取單一筆
 * - 失敗時 error 有值、原 loaded 狀態維持
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

import client from '@/api/client'
import { useWorkspaceStore } from '@/stores/workspace'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

const mockWorkspaces = [
  {
    id: 'w1',
    name: '個人',
    description: '私人空間',
    avatar_url: null,
    owner: 'u1',
    created_at: '2026-04-01T00:00:00Z',
    updated_at: '2026-04-01T00:00:00Z',
  },
  {
    id: 'w2',
    name: '團隊 Alpha',
    description: '產品團隊',
    avatar_url: null,
    owner: 'u1',
    created_at: '2026-04-02T00:00:00Z',
    updated_at: '2026-04-02T00:00:00Z',
  },
]

function paginated<T>(results: T[]) {
  return { count: results.length, next: null, previous: null, results }
}

describe('useWorkspaceStore', () => {
  beforeEach(() => {
    vi.mocked(client.get).mockReset()
    vi.mocked(client.post).mockReset()
  })

  it('初始狀態：list 為空、loaded=false', () => {
    const store = useWorkspaceStore()
    expect(store.list).toEqual([])
    expect(store.loaded).toBe(false)
    expect(store.loading).toBe(false)
    expect(store.error).toBeNull()
  })

  it('fetchAll() 取列表、解開 paginated.results、設定 loaded=true', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated(mockWorkspaces) })

    const store = useWorkspaceStore()
    await store.fetchAll()

    expect(client.get).toHaveBeenCalledWith('/workspaces/')
    expect(store.list).toEqual(mockWorkspaces)
    expect(store.loaded).toBe(true)
    expect(store.loading).toBe(false)
  })

  it('已 loaded 時再呼叫 fetchAll() 不打 API（快取）', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated(mockWorkspaces) })
    const store = useWorkspaceStore()
    await store.fetchAll()
    vi.mocked(client.get).mockClear()

    await store.fetchAll()

    expect(client.get).not.toHaveBeenCalled()
  })

  it('fetchAll({ force: true }) 強制重抓、覆蓋快取', async () => {
    vi.mocked(client.get)
      .mockResolvedValueOnce({ data: paginated([mockWorkspaces[0]]) })
      .mockResolvedValueOnce({ data: paginated(mockWorkspaces) })

    const store = useWorkspaceStore()
    await store.fetchAll()
    expect(store.list).toHaveLength(1)

    await store.fetchAll({ force: true })

    expect(client.get).toHaveBeenCalledTimes(2)
    expect(store.list).toHaveLength(2)
  })

  it('fetchAll() API 失敗：error 有值、loaded 仍為 false、loading reset', async () => {
    vi.mocked(client.get).mockRejectedValueOnce(new Error('network'))
    const store = useWorkspaceStore()

    await expect(store.fetchAll()).rejects.toThrow()

    expect(store.error).not.toBeNull()
    expect(store.loaded).toBe(false)
    expect(store.loading).toBe(false)
  })

  it('create() 建立 workspace 後加入快取尾端', async () => {
    const newWs = {
      id: 'w3',
      name: '新空間',
      description: '',
      avatar_url: null,
      owner: 'u1',
      created_at: '2026-04-29T00:00:00Z',
      updated_at: '2026-04-29T00:00:00Z',
    }
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated(mockWorkspaces) })
    vi.mocked(client.post).mockResolvedValueOnce({ data: newWs })

    const store = useWorkspaceStore()
    await store.fetchAll()

    const result = await store.create({ name: '新空間' })

    expect(client.post).toHaveBeenCalledWith('/workspaces/', { name: '新空間' })
    expect(result).toEqual(newWs)
    expect(store.list).toHaveLength(3)
    expect(store.list[2]).toEqual(newWs)
  })

  it('getById() 從快取取得對應 workspace；找不到回 null', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: paginated(mockWorkspaces) })
    const store = useWorkspaceStore()
    await store.fetchAll()

    expect(store.getById('w1')).toEqual(mockWorkspaces[0])
    expect(store.getById('not-exists')).toBeNull()
  })
})
