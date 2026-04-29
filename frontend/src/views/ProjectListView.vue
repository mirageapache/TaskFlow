<template>
  <div>
    <!-- Breadcrumb -->
    <nav class="text-xs text-stone-500 dark:text-stone-400 mb-2">
      <RouterLink to="/workspaces" class="hover:text-orange-600 hover:underline">
        工作區
      </RouterLink>
      <span class="mx-1">/</span>
      <span class="text-stone-700 dark:text-stone-200">{{ workspaceName }}</span>
    </nav>

    <!-- Page header -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-3xl font-bold tracking-tight text-stone-900 dark:text-stone-50">
          {{ workspaceName }}
        </h1>
        <p class="mt-1 text-sm text-stone-600 dark:text-stone-400">
          管理此工作區的專案與看板。
        </p>
      </div>
      <button
        data-test="toggle-create"
        class="h-10 px-4 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium inline-flex items-center gap-2 transition-colors duration-150"
        @click="showCreateForm = !showCreateForm"
      >
        <i :class="['pi', showCreateForm ? 'pi-times' : 'pi-plus']"></i>
        <span>{{ showCreateForm ? '取消' : '建立專案' }}</span>
      </button>
    </div>

    <!-- Create form -->
    <form
      v-if="showCreateForm"
      data-test="create-form"
      class="mt-6 p-6 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 shadow-xs space-y-4"
      @submit.prevent="onCreate"
    >
      <div>
        <label for="proj-name" class="block text-xs font-medium text-stone-800 dark:text-stone-200">
          名稱 <span class="text-red-500">*</span>
        </label>
        <input
          id="proj-name"
          v-model="newName"
          name="name"
          type="text"
          required
          maxlength="100"
          placeholder="專案名稱"
          class="mt-1 block w-full h-10 px-3 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 focus:outline-none focus:border-orange-500 focus:ring-[3px] focus:ring-orange-500/25 transition-colors duration-150"
        />
      </div>
      <div>
        <label for="proj-desc" class="block text-xs font-medium text-stone-800 dark:text-stone-200">
          描述
        </label>
        <textarea
          id="proj-desc"
          v-model="newDescription"
          name="description"
          rows="2"
          placeholder="專案說明…"
          class="mt-1 block w-full px-3 py-2 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 focus:outline-none focus:border-orange-500 focus:ring-[3px] focus:ring-orange-500/25 transition-colors duration-150"
        ></textarea>
      </div>
      <div v-if="createError" class="text-sm text-red-600">
        {{ createError }}
      </div>
      <div class="flex justify-end gap-2">
        <button
          type="button"
          class="h-10 px-4 rounded-lg border border-stone-200 dark:border-stone-700 text-stone-800 dark:text-stone-100 text-sm font-medium hover:bg-stone-100 dark:hover:bg-stone-700"
          @click="cancelCreate"
        >
          取消
        </button>
        <button
          type="submit"
          :disabled="creating"
          class="h-10 px-4 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium inline-flex items-center justify-center gap-2 disabled:opacity-60"
        >
          <i v-if="creating" class="pi pi-spinner pi-spin"></i>
          <span>建立</span>
        </button>
      </div>
    </form>

    <!-- Loading -->
    <div
      v-if="projectStore.loading && projects.length === 0 && !projectStore.error"
      class="mt-12 text-center text-stone-500"
    >
      <i class="pi pi-spinner pi-spin text-3xl"></i>
    </div>

    <!-- Error -->
    <div
      v-else-if="projectStore.error && projects.length === 0"
      class="mt-8 p-4 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 flex items-center gap-3"
      role="alert"
    >
      <i class="pi pi-exclamation-circle"></i>
      <span class="flex-1">{{ projectStore.error }}</span>
      <button
        class="text-sm font-medium hover:underline"
        @click="reload"
      >
        重試
      </button>
    </div>

    <!-- Empty state -->
    <div
      v-else-if="projects.length === 0"
      class="py-16 text-center"
    >
      <i class="pi pi-folder-open text-6xl text-stone-300 dark:text-stone-600"></i>
      <h2 class="mt-4 text-xl font-semibold text-stone-900 dark:text-stone-50">
        還沒有專案
      </h2>
      <p class="mt-2 text-sm text-stone-500 dark:text-stone-400">
        建立第一個專案來開始追蹤任務 →
      </p>
    </div>

    <!-- List -->
    <div
      v-else
      class="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      <RouterLink
        v-for="proj in projects"
        :key="proj.id"
        :to="`/project/${proj.id}/board`"
        class="block p-6 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 shadow-xs hover:shadow-sm hover:border-orange-500 transition-all duration-150"
      >
        <div class="flex items-start gap-3">
          <span
            class="w-3 h-3 rounded-full mt-1.5 shrink-0"
            :style="{ backgroundColor: proj.color || '#F97316' }"
            aria-hidden="true"
          ></span>
          <div class="flex-1 min-w-0">
            <h3 class="text-lg font-semibold tracking-tight text-stone-900 dark:text-stone-50 truncate">
              {{ proj.name }}
            </h3>
            <p class="mt-1 text-sm text-stone-600 dark:text-stone-400 line-clamp-2 min-h-[40px]">
              {{ proj.description || '—' }}
            </p>
          </div>
        </div>
        <div class="mt-4 inline-flex items-center gap-1 text-sm font-medium text-orange-600">
          <span>查看看板</span>
          <i class="pi pi-arrow-right text-xs"></i>
        </div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ProjectListView — 單一 workspace 之下的專案列表頁。
 *
 * 路由：/workspaces/:id/projects
 * - 從路由取 workspaceId，呼叫 projectStore.fetchByWorkspace(id)
 * - workspace 名稱優先用 workspaceStore 快取；無快取時退回 fetchAll
 *
 * 規格：.doc/taskflow_layout_design.md §8.3 / §8.6
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { useProjectStore } from '@/stores/project'
import { useWorkspaceStore } from '@/stores/workspace'
import { parseApiError } from '@/utils/api-errors'

const route = useRoute()
const projectStore = useProjectStore()
const workspaceStore = useWorkspaceStore()

const workspaceId = computed(() => route.params.id as string)
const projects = computed(() => projectStore.getByWorkspace(workspaceId.value))

const workspaceName = computed(() => {
  const ws = workspaceStore.getById(workspaceId.value)
  return ws?.name ?? '專案'
})

const showCreateForm = ref(false)
const newName = ref('')
const newDescription = ref('')
const creating = ref(false)
const createError = ref<string | null>(null)

onMounted(() => {
  projectStore.fetchByWorkspace(workspaceId.value).catch(() => {})
  // 確保 workspace 名稱可顯示（若使用者直接打開此 URL 而沒先逛 list 頁）
  if (!workspaceStore.loaded) {
    workspaceStore.fetchAll().catch(() => {})
  }
})

// 路由 :id 變化（在 SPA 內切換不同 workspace）時重抓
watch(workspaceId, (id) => {
  if (id) projectStore.fetchByWorkspace(id).catch(() => {})
})

function reload() {
  projectStore.fetchByWorkspace(workspaceId.value, { force: true }).catch(() => {})
}

async function onCreate() {
  if (!newName.value.trim()) return
  creating.value = true
  createError.value = null
  try {
    await projectStore.create({
      workspace_id: workspaceId.value,
      name: newName.value.trim(),
      description: newDescription.value.trim(),
    })
    cancelCreate()
  } catch (err) {
    const { banner, fieldErrors } = parseApiError(err, ['name', 'description'])
    const fieldMsgs = Object.entries(fieldErrors).map(([f, m]) => `${f}：${m}`)
    createError.value = [banner, ...fieldMsgs].filter(Boolean).join('；') || '建立失敗，請稍後再試'
  } finally {
    creating.value = false
  }
}

function cancelCreate() {
  showCreateForm.value = false
  newName.value = ''
  newDescription.value = ''
  createError.value = null
}
</script>
