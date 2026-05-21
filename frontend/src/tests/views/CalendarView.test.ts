/**
 * CalendarView 測試
 * 規格：.doc/taskflow-frontend.md §10（FullCalendar 整合：月／週／日視圖）
 *
 * 涵蓋：
 * - 掛載時抓 workspace 列表並自動選第一個
 * - FullCalendar options：含 month / week / day 三視圖、初始 dayGridMonth
 * - FullCalendar 的 datesSet callback 觸發 calendar store 抓取對應範圍
 * - 切換 workspace 會重新抓取
 * - calendar store 的 events 映射為 FullCalendar EventInput（含 allDay）
 *
 * 注意：FullCalendar 與 plugin 真正掛載需要 DOM 量測，jsdom 不支援；
 * 這裡用 vi.mock 把 @fullcalendar/vue3 換成簡單 stub，從外部觀察 props.options。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import type { Router } from 'vue-router'
import { nextTick } from 'vue'

import client from '@/api/client'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

// FullCalendar 與 plugin 在 jsdom 無法跑（需 DOM 量測），改用 stub
vi.mock('@fullcalendar/vue3', () => ({
  default: {
    name: 'FullCalendar',
    props: ['options'],
    template: '<div data-test="fullcalendar-stub" />',
  },
}))
vi.mock('@fullcalendar/daygrid', () => ({ default: { name: 'dayGridPlugin' } }))
vi.mock('@fullcalendar/timegrid', () => ({ default: { name: 'timeGridPlugin' } }))

import CalendarView from '@/views/CalendarView.vue'

function buildRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/calendar', name: 'calendar', component: CalendarView }],
  })
}

async function mountView(router: Router) {
  await router.push('/calendar')
  await router.isReady()
  return mount(CalendarView, { global: { plugins: [router] } })
}

const workspacesPayload = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: 'w1',
      name: '個人工作區',
      description: '',
      avatar_url: null,
      owner: 'u1',
      created_at: '',
      updated_at: '',
    },
    {
      id: 'w2',
      name: '專案 A',
      description: '',
      avatar_url: null,
      owner: 'u1',
      created_at: '',
      updated_at: '',
    },
  ],
}

const sampleEvents = [
  {
    id: 'e1',
    workspace: 'w1',
    creator: 'u1',
    title: '專案開工',
    description: '',
    start_at: '2026-05-21T09:00:00Z',
    end_at: '2026-05-21T10:00:00Z',
    is_all_day: false,
    recurrence_rule: '',
    created_at: '',
    updated_at: '',
  },
  {
    id: 'e2',
    workspace: 'w1',
    creator: 'u1',
    title: '全天活動',
    description: '',
    start_at: '2026-05-22T00:00:00Z',
    end_at: '2026-05-23T00:00:00Z',
    is_all_day: true,
    recurrence_rule: '',
    created_at: '',
    updated_at: '',
  },
]

/**
 * 把 client.get 設成依 URL 分派的 mock：
 * - /workspaces/         → workspacesPayload（分頁包裝）
 * - /calendar/           → sampleEvents（純陣列；expand=true 行為）
 */
function setupClientGetByUrl() {
  vi.mocked(client.get).mockImplementation((url: string) => {
    if (url === '/workspaces/') return Promise.resolve({ data: workspacesPayload })
    if (url === '/calendar/') return Promise.resolve({ data: sampleEvents })
    return Promise.resolve({ data: null })
  })
}

describe('CalendarView', () => {
  beforeEach(() => {
    vi.mocked(client.get).mockReset()
  })

  it('掛載時抓 workspace 並自動選第一個', async () => {
    setupClientGetByUrl()
    const wrapper = await mountView(buildRouter())
    await flushPromises()

    const select = wrapper.find('[data-test="workspace-select"]')
    expect(select.exists()).toBe(true)
    // 自動選第一個
    expect((select.element as HTMLSelectElement).value).toBe('w1')
    // 兩個工作區選項都存在
    expect(wrapper.html()).toContain('個人工作區')
    expect(wrapper.html()).toContain('專案 A')
  })

  it('渲染 FullCalendar stub 並帶 month / week / day 三視圖', async () => {
    setupClientGetByUrl()
    const wrapper = await mountView(buildRouter())
    await flushPromises()

    const fc = wrapper.find('[data-test="fullcalendar-stub"]')
    expect(fc.exists()).toBe(true)

    const fcComp = wrapper.findComponent({ name: 'FullCalendar' })
    const options = fcComp.props('options') as Record<string, unknown>
    expect(options.initialView).toBe('dayGridMonth')

    const toolbar = options.headerToolbar as { right: string }
    expect(toolbar.right).toContain('dayGridMonth')
    expect(toolbar.right).toContain('timeGridWeek')
    expect(toolbar.right).toContain('timeGridDay')
  })

  it('FullCalendar datesSet callback 觸發 store.fetchByRange，帶 workspace + 範圍', async () => {
    setupClientGetByUrl()
    const wrapper = await mountView(buildRouter())
    await flushPromises()

    const fcComp = wrapper.findComponent({ name: 'FullCalendar' })
    const options = fcComp.props('options') as { datesSet?: (a: unknown) => unknown }
    expect(typeof options.datesSet).toBe('function')

    vi.mocked(client.get).mockClear()
    setupClientGetByUrl()
    // 模擬 FullCalendar 切到 5 月時呼叫 datesSet
    await options.datesSet?.({
      start: new Date('2026-05-01T00:00:00Z'),
      end: new Date('2026-05-31T23:59:59Z'),
    })
    await flushPromises()

    const calls = vi.mocked(client.get).mock.calls.filter((c) => c[0] === '/calendar/')
    expect(calls).toHaveLength(1)
    expect(calls[0][1]).toEqual({
      params: {
        workspace: 'w1',
        start: '2026-05-01T00:00:00.000Z',
        end: '2026-05-31T23:59:59.000Z',
        expand: 'true',
      },
    })
  })

  it('store 的 events 映射為 FullCalendar EventInput（含 allDay）', async () => {
    setupClientGetByUrl()
    const wrapper = await mountView(buildRouter())
    await flushPromises()

    const fcComp = wrapper.findComponent({ name: 'FullCalendar' })
    const options = fcComp.props('options') as { datesSet?: (a: unknown) => Promise<void> }

    await options.datesSet?.({
      start: new Date('2026-05-01T00:00:00Z'),
      end: new Date('2026-05-31T23:59:59Z'),
    })
    await flushPromises()
    await nextTick()

    const after = fcComp.props('options') as { events: Array<Record<string, unknown>> }
    expect(after.events).toHaveLength(2)
    expect(after.events[0]).toMatchObject({
      id: 'e1',
      title: '專案開工',
      start: '2026-05-21T09:00:00Z',
      end: '2026-05-21T10:00:00Z',
      allDay: false,
    })
    expect(after.events[1]).toMatchObject({
      id: 'e2',
      title: '全天活動',
      allDay: true,
    })
  })

  it('切換 workspace 後重新抓取對應的事件', async () => {
    setupClientGetByUrl()
    const wrapper = await mountView(buildRouter())
    await flushPromises()

    // 先觸發一次初始 datesSet 用以建立目前範圍
    const fcComp = wrapper.findComponent({ name: 'FullCalendar' })
    const options = fcComp.props('options') as { datesSet?: (a: unknown) => Promise<void> }
    await options.datesSet?.({
      start: new Date('2026-05-01T00:00:00Z'),
      end: new Date('2026-05-31T23:59:59Z'),
    })
    await flushPromises()

    vi.mocked(client.get).mockClear()
    setupClientGetByUrl()

    // 切到 w2
    const select = wrapper.find('[data-test="workspace-select"]')
    await select.setValue('w2')
    await flushPromises()

    const calendarCalls = vi.mocked(client.get).mock.calls.filter((c) => c[0] === '/calendar/')
    expect(calendarCalls.length).toBeGreaterThanOrEqual(1)
    expect(calendarCalls[calendarCalls.length - 1][1]).toMatchObject({
      params: expect.objectContaining({ workspace: 'w2', expand: 'true' }),
    })
  })

  it('沒有 workspace 時不顯示 select、也不觸發 fetch', async () => {
    vi.mocked(client.get).mockImplementation((url: string) => {
      if (url === '/workspaces/') {
        return Promise.resolve({ data: { count: 0, next: null, previous: null, results: [] } })
      }
      return Promise.resolve({ data: [] })
    })
    const wrapper = await mountView(buildRouter())
    await flushPromises()

    expect(wrapper.find('[data-test="workspace-select"]').exists()).toBe(false)

    // datesSet 即使被 FullCalendar 觸發，沒有 selected workspace 也不該打 API
    const fcComp = wrapper.findComponent({ name: 'FullCalendar' })
    const options = fcComp.props('options') as { datesSet?: (a: unknown) => Promise<void> }
    vi.mocked(client.get).mockClear()
    await options.datesSet?.({
      start: new Date('2026-05-01T00:00:00Z'),
      end: new Date('2026-05-31T23:59:59Z'),
    })
    await flushPromises()
    const calendarCalls = vi.mocked(client.get).mock.calls.filter((c) => c[0] === '/calendar/')
    expect(calendarCalls).toHaveLength(0)
  })
})
