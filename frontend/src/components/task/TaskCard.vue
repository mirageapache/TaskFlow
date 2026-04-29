<template>
  <div
    class="block w-full text-left p-3 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 shadow-xs hover:shadow-sm hover:border-orange-500 transition-all duration-150 cursor-pointer"
    role="button"
    tabindex="0"
    @click="emit('click', task)"
    @keydown.enter="emit('click', task)"
    @keydown.space.prevent="emit('click', task)"
  >
    <!-- 上方：優先級 dot + 標題 -->
    <div class="flex items-start gap-2">
      <span
        data-test="priority-dot"
        :class="['w-2 h-2 rounded-full mt-1.5 shrink-0', priorityDotClass]"
        :title="priorityLabel"
        :aria-label="`優先級 ${priorityLabel}`"
      ></span>
      <h4 class="flex-1 text-sm font-medium text-stone-900 dark:text-stone-50 line-clamp-2">
        {{ task.title }}
      </h4>
    </div>

    <!-- Tags 數量徽章 -->
    <div v-if="task.tags.length > 0" class="mt-2">
      <span
        data-test="tag-badge"
        class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-stone-100 dark:bg-stone-700 text-stone-700 dark:text-stone-200"
      >
        <i class="pi pi-tag text-[10px]"></i>
        <span>{{ task.tags.length }}</span>
      </span>
    </div>

    <!-- 下方：截止日 + assignees -->
    <div
      v-if="task.due_date || task.assignees.length > 0"
      class="mt-3 flex items-center justify-between gap-2"
    >
      <span
        v-if="task.due_date"
        data-test="due-date"
        :class="[
          'inline-flex items-center gap-1 text-xs',
          isOverdue ? 'text-red-600 font-medium' : 'text-stone-500 dark:text-stone-400',
        ]"
      >
        <i class="pi pi-calendar text-[11px]"></i>
        <span>{{ formattedDueDate }}</span>
      </span>
      <div v-else></div>

      <div
        v-if="task.assignees.length > 0"
        class="flex -space-x-1.5"
        :aria-label="`${task.assignees.length} 位指派人`"
      >
        <span
          v-for="user in visibleAssignees"
          :key="user.id"
          data-test="assignee-avatar"
          class="w-6 h-6 rounded-full bg-orange-500 text-white text-[10px] font-medium inline-flex items-center justify-center ring-2 ring-white dark:ring-stone-800"
          :title="user.username"
        >
          {{ initial(user.username) }}
        </span>
        <span
          v-if="overflowCount > 0"
          data-test="assignee-overflow"
          class="w-6 h-6 rounded-full bg-stone-300 dark:bg-stone-600 text-stone-700 dark:text-stone-100 text-[10px] font-medium inline-flex items-center justify-center ring-2 ring-white dark:ring-stone-800"
        >
          +{{ overflowCount }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * TaskCard — Kanban 看板上的任務卡片。
 *
 * 規格：.doc/taskflow_layout_design.md §9.3 / §1.4 優先級色
 *
 * Props:
 *   - task: Task — 完整任務物件（含 assignees）
 *
 * Emits:
 *   - click(task) — 點卡片時，由父層決定動作（通常是開啟 TaskDrawer）
 */
import { computed } from 'vue'
import dayjs from 'dayjs'

import type { Task, TaskPriority } from '@/types'

const props = defineProps<{ task: Task }>()
const emit = defineEmits<{ (e: 'click', task: Task): void }>()

const MAX_VISIBLE_ASSIGNEES = 3

// §1.4 priority colors
const PRIORITY_COLORS: Record<TaskPriority, string> = {
  urgent: 'bg-red-700',
  high: 'bg-rose-600',
  medium: 'bg-blue-600',
  low: 'bg-stone-500',
}

const PRIORITY_LABELS: Record<TaskPriority, string> = {
  urgent: '緊急',
  high: '高',
  medium: '中',
  low: '低',
}

const priorityDotClass = computed(() => PRIORITY_COLORS[props.task.priority])
const priorityLabel = computed(() => PRIORITY_LABELS[props.task.priority])

const formattedDueDate = computed(() =>
  props.task.due_date ? dayjs(props.task.due_date).format('M/D') : '',
)

const isOverdue = computed(() => {
  if (!props.task.due_date) return false
  return dayjs(props.task.due_date).isBefore(dayjs(), 'day')
})

const visibleAssignees = computed(() =>
  props.task.assignees.slice(0, MAX_VISIBLE_ASSIGNEES),
)

const overflowCount = computed(() =>
  Math.max(0, props.task.assignees.length - MAX_VISIBLE_ASSIGNEES),
)

function initial(name: string): string {
  return name?.[0]?.toUpperCase() ?? '?'
}
</script>
