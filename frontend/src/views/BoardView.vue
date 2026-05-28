<template>
  <div class="flex flex-col flex-1 min-h-0">
    <!-- Breadcrumb -->
    <nav class="text-xs text-stone-500 dark:text-stone-400 mb-2">
      <RouterLink to="/workspaces" class="hover:text-orange-600 hover:underline">
        工作區
      </RouterLink>
      <span class="mx-1">/</span>
      <RouterLink
        v-if="project?.workspace"
        :to="`/workspaces/${project.workspace}/projects`"
        class="hover:text-orange-600 hover:underline"
      >
        專案
      </RouterLink>
      <span class="mx-1">/</span>
      <span class="text-stone-700 dark:text-stone-200">看板</span>
    </nav>

    <!-- Page header -->
    <div class="flex items-center justify-between gap-4">
      <div class="flex items-center gap-2 min-w-0">
        <span
          v-if="project?.color"
          class="w-3 h-3 rounded-full shrink-0"
          :style="{ backgroundColor: project.color }"
        ></span>
        <h1 class="text-2xl font-bold tracking-tight text-stone-900 dark:text-stone-50 truncate">
          {{ project?.name ?? '看板' }}
        </h1>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="mt-12 text-center text-stone-500">
      <i class="pi pi-spinner pi-spin text-3xl"></i>
    </div>

    <!-- Empty status -->
    <div
      v-else-if="statuses.length === 0"
      data-test="empty-statuses"
      class="mt-12 py-16 text-center"
    >
      <i class="pi pi-th-large text-6xl text-stone-300 dark:text-stone-600"></i>
      <h2 class="mt-4 text-xl font-semibold text-stone-900 dark:text-stone-50">
        還沒有看板欄位
      </h2>
      <p class="mt-2 text-sm text-stone-500 dark:text-stone-400">
        一鍵建立預設欄位（待辦／進行中／完成）即可開始追蹤任務。
      </p>
      <button
        data-test="bootstrap-defaults"
        :disabled="bootstrapping"
        class="mt-6 h-10 px-5 rounded-lg bg-orange-500 hover:bg-orange-600 active:bg-orange-700 text-white text-sm font-medium disabled:opacity-60 disabled:cursor-not-allowed transition-colors duration-150 inline-flex items-center gap-2"
        @click="bootstrapDefaults"
      >
        <i :class="['pi', bootstrapping ? 'pi-spinner pi-spin' : 'pi-plus']"></i>
        <span>{{ bootstrapping ? '建立中…' : '建立預設欄位' }}</span>
      </button>
      <p
        v-if="bootstrapError"
        class="mt-4 text-sm text-red-600 dark:text-red-400"
        role="alert"
      >
        {{ bootstrapError }}
      </p>
    </div>

    <!-- Kanban columns -->
    <div v-else class="flex-1 min-h-0 mt-6 overflow-x-auto pb-4 -mx-4 px-4 sm:-mx-6 sm:px-6">
      <div class="flex gap-4 min-w-max items-start">
        <section
          v-for="(col, idx) in columns"
          :key="col.status.id"
          data-test="kanban-column"
          class="w-80 shrink-0 bg-stone-100 dark:bg-stone-800/50 rounded-xl p-3"
        >
          <header class="flex items-center justify-between mb-3 px-1">
            <div class="flex items-center gap-2">
              <span
                class="w-2 h-2 rounded-full"
                :style="{ backgroundColor: col.status.color }"
              ></span>
              <h3 class="text-sm font-semibold text-stone-900 dark:text-stone-50">
                {{ col.status.name }}
              </h3>
              <span
                data-test="task-count"
                class="text-xs text-stone-500 px-1.5 py-0.5 rounded bg-stone-200 dark:bg-stone-700"
              >
                {{ col.tasks.length }}
              </span>
            </div>
            <button
              class="p-1 rounded text-stone-500 hover:bg-stone-200 dark:hover:bg-stone-700"
              :aria-label="`在「${col.status.name}」新增任務`"
              @click="startCreate(col.status.id)"
            >
              <i class="pi pi-plus"></i>
            </button>
          </header>

          <draggable
            v-model="columns[idx].tasks"
            :group="{ name: 'tasks' }"
            item-key="id"
            class="space-y-2 min-h-[40px]"
            ghost-class="opacity-40"
            :animation="150"
            @change="(e: DragChange) => onChange(col.status.id, e)"
          >
            <template #item="{ element }">
              <div
                data-test="task-card-wrapper"
                class="cursor-grab active:cursor-grabbing"
                @click="openDrawer(element)"
              >
                <TaskCard :task="element" />
              </div>
            </template>
          </draggable>

          <!-- Inline create form -->
          <form
            v-if="creatingFor === col.status.id"
            class="mt-2 p-2 rounded-lg bg-white dark:bg-stone-800 border border-stone-200 dark:border-stone-700"
            @submit.prevent="submitCreate(col.status.id)"
          >
            <input
              v-model="newTitle"
              type="text"
              required
              maxlength="255"
              autofocus
              placeholder="任務標題…"
              class="w-full h-9 px-2 rounded border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 text-sm focus:outline-none focus:border-orange-500 focus:ring-[3px] focus:ring-orange-500/25"
            />
            <div class="mt-2 flex justify-end gap-2">
              <button
                type="button"
                class="h-8 px-3 rounded text-xs text-stone-600 hover:bg-stone-100 dark:hover:bg-stone-700"
                @click="cancelCreate"
              >
                取消
              </button>
              <button
                type="submit"
                :disabled="creating"
                class="h-8 px-3 rounded bg-orange-500 hover:bg-orange-600 text-white text-xs font-medium disabled:opacity-60"
              >
                建立
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>

    <!-- Task Drawer -->
    <TaskDrawer
      :show="!!selectedTask"
      :task="selectedTask"
      @close="closeDrawer"
      @deleted="closeDrawer"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * BoardView — 專案看板（Kanban + 拖曳）。
 *
 * 規格：.doc/taskflow_layout_design.md §9.3
 *
 * 流程：
 * 1. 從路由 :id 取 projectId，並行抓 project 詳情、status 欄位、tasks
 * 2. 將 tasks 依 status 分組為欄位（columns）
 * 3. vuedraggable 處理跨欄拖曳；@change 觸發 useDragAndDrop.onTaskDropped（樂觀更新 + 失敗回滾）
 * 4. 點 TaskCard 開啟 TaskDrawer；任一欄 + 號展開 inline 建立表單
 *
 * vuedraggable 注意：
 * - v-model 的目標必須是可寫陣列，故 columns 是 ref 而非 computed
 * - watch task store 的 byProject + statuses，store 變動時重新組欄
 */
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import draggable from 'vuedraggable'

import TaskCard from '@/components/task/TaskCard.vue'
import TaskDrawer from '@/components/task/TaskDrawer.vue'
import { useDragAndDrop } from '@/composables/useDragAndDrop'
import { useProjectStore } from '@/stores/project'
import { useTaskStore } from '@/stores/task'
import type { ProjectStatus, Task } from '@/types'
import { parseApiError } from '@/utils/api-errors'

interface DragChange {
  added?: { element: Task; newIndex: number }
  removed?: { element: Task; oldIndex: number }
  moved?: { element: Task; newIndex: number; oldIndex: number }
}

const route = useRoute()
const projectStore = useProjectStore()
const taskStore = useTaskStore()
const { onTaskDropped } = useDragAndDrop()

const projectId = computed(() => route.params.id as string)
const project = computed(() => projectStore.getById(projectId.value))
const statuses = computed(() => projectStore.getStatuses(projectId.value))

const loading = ref(true)
const columns = ref<{ status: ProjectStatus; tasks: Task[] }[]>([])

const selectedTask = ref<Task | null>(null)
const creatingFor = ref<string | null>(null)
const newTitle = ref('')
const creating = ref(false)

// 同步 columns ←→ store
watch(
  [statuses, () => taskStore.byProject[projectId.value]],
  () => {
    columns.value = statuses.value.map((s) => ({
      status: s,
      tasks: [...taskStore.getByProjectAndStatus(projectId.value, s.id)],
    }))
  },
  { deep: true, immediate: true },
)

async function init() {
  loading.value = true
  try {
    await Promise.all([
      projectStore.fetchById(projectId.value),
      projectStore.fetchStatuses(projectId.value),
      taskStore.fetchByProject(projectId.value),
    ])
  } finally {
    loading.value = false
  }
}
init()

watch(projectId, () => init())

function onChange(targetStatusId: string, evt: DragChange) {
  if (evt.added?.element) {
    onTaskDropped(evt.added.element.id, targetStatusId)
  }
}

function openDrawer(task: Task) {
  // 從 store 取最新狀態（樂觀更新後 task 物件可能不同步）
  selectedTask.value = taskStore.getById(task.id) ?? task
}

function closeDrawer() {
  selectedTask.value = null
}

function startCreate(statusId: string) {
  creatingFor.value = statusId
  newTitle.value = ''
}

function cancelCreate() {
  creatingFor.value = null
  newTitle.value = ''
}

async function submitCreate(statusId: string) {
  if (!newTitle.value.trim()) return
  creating.value = true
  try {
    await taskStore.create({
      project: projectId.value,
      title: newTitle.value.trim(),
      status_id: statusId,
    })
    cancelCreate()
  } finally {
    creating.value = false
  }
}

const bootstrapping = ref(false)
const bootstrapError = ref<string | null>(null)

/** 為舊專案一鍵補上預設看板欄位。成功後 store 會 emit、watch 自動重組 columns。 */
async function bootstrapDefaults() {
  bootstrapping.value = true
  bootstrapError.value = null
  try {
    await projectStore.bootstrapDefaultStatuses(projectId.value)
  } catch (err) {
    const { banner } = parseApiError(err)
    bootstrapError.value = banner ?? '建立預設欄位失敗，請稍後再試。'
  } finally {
    bootstrapping.value = false
  }
}
</script>
