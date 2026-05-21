<template>
  <div data-test="calendar-view" class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold text-stone-900 dark:text-stone-50">行事曆</h1>
      <select
        v-if="workspaceList.length > 0"
        v-model="selectedWorkspaceId"
        data-test="workspace-select"
        class="rounded-md border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-800 px-3 py-1.5 text-sm text-stone-800 dark:text-stone-100"
      >
        <option v-for="w in workspaceList" :key="w.id" :value="w.id">
          {{ w.name }}
        </option>
      </select>
    </div>

    <div
      v-if="calendarStore.error"
      class="text-sm text-red-600 bg-red-50 dark:bg-red-950/30 px-3 py-2 rounded-md"
    >
      {{ calendarStore.error }}
    </div>

    <div
      data-test="calendar-container"
      class="bg-white dark:bg-stone-800 rounded-lg p-4 border border-stone-200 dark:border-stone-700"
    >
      <FullCalendar :options="calendarOptions" />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * CalendarView — 工作區行事曆。
 *
 * 使用 FullCalendar 提供月／週／日三種視圖：
 * - dayGridMonth：月視圖（dayGrid plugin）
 * - timeGridWeek / timeGridDay：週／日視圖（timeGrid plugin）
 *
 * 資料抓取策略：
 * - FullCalendar 在初次掛載與每次切換視圖／月份時都會呼叫 `datesSet`，
 *   把當前可見範圍（start / end）丟進來；我們在這裡 fetchByRange，
 *   後端 `expand=true` 會展開 RRULE 重複事件為 occurrences。
 * - 切換工作區時 `datesSet` 不會自動觸發，靠 `watch(selectedWorkspaceId)` 補一次抓取。
 *
 * 規格：.doc/taskflow-frontend.md §10
 */
import { computed, onMounted, ref, watch } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import type { CalendarOptions, DatesSetArg, EventInput } from '@fullcalendar/core'

import { useCalendarStore } from '@/stores/calendar'
import { useWorkspaceStore } from '@/stores/workspace'

const workspaceStore = useWorkspaceStore()
const calendarStore = useCalendarStore()

const workspaceList = computed(() => workspaceStore.list)
const selectedWorkspaceId = ref<string>('')

/** 目前可見的範圍；切換 workspace 時用來重新抓取。 */
const currentRange = ref<{ start: string; end: string } | null>(null)

const fcEvents = computed<EventInput[]>(() =>
  calendarStore.events.map((e) => ({
    id: e.id,
    title: e.title,
    start: e.start_at,
    end: e.end_at,
    allDay: e.is_all_day,
  })),
)

async function handleDatesSet(arg: DatesSetArg) {
  currentRange.value = {
    start: arg.start.toISOString(),
    end: arg.end.toISOString(),
  }
  if (!selectedWorkspaceId.value) return
  try {
    await calendarStore.fetchByRange({
      workspaceId: selectedWorkspaceId.value,
      start: currentRange.value.start,
      end: currentRange.value.end,
    })
  } catch {
    // 錯誤訊息已存於 calendarStore.error，由模板顯示
  }
}

const calendarOptions = computed<CalendarOptions>(() => ({
  plugins: [dayGridPlugin, timeGridPlugin],
  initialView: 'dayGridMonth',
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,timeGridWeek,timeGridDay',
  },
  buttonText: { today: '今天', month: '月', week: '週', day: '日' },
  locale: 'zh-tw',
  firstDay: 1,
  height: 'auto',
  events: fcEvents.value,
  datesSet: handleDatesSet,
}))

onMounted(async () => {
  await workspaceStore.fetchAll().catch(() => {})
  if (workspaceList.value.length > 0 && !selectedWorkspaceId.value) {
    selectedWorkspaceId.value = workspaceList.value[0].id
  }
})

watch(selectedWorkspaceId, async (newId) => {
  if (!newId || !currentRange.value) return
  try {
    await calendarStore.fetchByRange({
      workspaceId: newId,
      start: currentRange.value.start,
      end: currentRange.value.end,
    })
  } catch {
    // 錯誤訊息已存於 calendarStore.error
  }
})
</script>
