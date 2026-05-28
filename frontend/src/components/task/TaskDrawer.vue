<template>
  <Teleport to="body">
    <Transition name="task-drawer">
      <div
        v-if="show"
        data-test="task-drawer"
        class="fixed inset-0 z-[1200] flex"
        role="dialog"
        aria-modal="true"
      >
        <!-- 背景遮罩，點擊關閉 -->
        <div class="absolute inset-0 bg-black/40" @click="emit('close')"></div>

        <!-- 抽屜本體：右側滑入 -->
        <aside
          class="ml-auto relative w-full sm:w-[640px] h-full bg-white dark:bg-stone-800 shadow-lg flex flex-col"
          @click.stop
        >
          <TaskDetailPanel
            v-if="internalTask"
            :task="internalTask"
            @close="emit('close')"
            @deleted="emit('deleted')"
          />
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * TaskDrawer — 右側滑入抽屜外殼。
 *
 * 規格：.doc/taskflow_layout_design.md §9.5
 *
 * 使用 `show` prop 控制開關（而非父層 v-if），讓 leave 動畫能正確執行。
 * 切換任務時暫存最後一個非 null 的 task，確保關閉動畫期間面板仍有內容顯示。
 *
 * Props:
 *   - show: boolean   — 是否顯示抽屜
 *   - task: Task|null — 要顯示的任務（null 時保留上次任務直到動畫結束）
 *
 * Emits:
 *   - close()   — 關閉抽屜
 *   - deleted() — 任務刪除後通知父層
 */
import { ref, watch } from 'vue'

import type { Task } from '@/types'
import TaskDetailPanel from '@/components/task/TaskDetailPanel.vue'

const props = defineProps<{ show: boolean; task: Task | null }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'deleted'): void }>()

// 保留最後一次非 null 的 task，leave 動畫期間面板才不會因 task=null 而閃白
const internalTask = ref<Task | null>(props.task)
watch(
  () => props.task,
  (t) => {
    if (t !== null) internalTask.value = t
  },
)
</script>

<style scoped>
/* 背景遮罩 fade */
.task-drawer-enter-active,
.task-drawer-leave-active {
  transition: opacity 0.25s ease;
}
.task-drawer-enter-from,
.task-drawer-leave-to {
  opacity: 0;
}

/* aside 從右滑入 */
.task-drawer-enter-active :deep(aside),
.task-drawer-leave-active :deep(aside) {
  transition: transform 0.25s ease;
}
.task-drawer-enter-from :deep(aside),
.task-drawer-leave-to :deep(aside) {
  transform: translateX(100%);
}
</style>
