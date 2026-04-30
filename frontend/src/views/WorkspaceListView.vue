<template>
  <div>
    <!-- Page header -->
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-3xl font-bold tracking-tight text-stone-900 dark:text-stone-50">
          工作區
        </h1>
        <p class="mt-1 text-sm text-stone-600 dark:text-stone-400">
          管理你的工作區與其下專案。
        </p>
      </div>
      <button
        data-test="toggle-create"
        class="h-10 px-4 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium inline-flex items-center gap-2 transition-colors duration-150"
        @click="showCreateForm = !showCreateForm"
      >
        <i :class="['pi', showCreateForm ? 'pi-times' : 'pi-plus']"></i>
        <span>{{ showCreateForm ? '取消' : '建立工作區' }}</span>
      </button>
    </div>

    <!-- Create form (inline) -->
    <form
      v-if="showCreateForm"
      data-test="create-form"
      class="mt-6 p-6 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 shadow-xs space-y-4"
      @submit.prevent="onCreate"
    >
      <div>
        <label
          for="ws-name"
          class="block text-xs font-medium text-stone-800 dark:text-stone-200"
        >
          名稱 <span class="text-red-500">*</span>
        </label>
        <input
          id="ws-name"
          v-model="newName"
          name="name"
          type="text"
          required
          maxlength="50"
          placeholder="工作區名稱"
          class="mt-1 block w-full h-10 px-3 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 focus:outline-none focus:border-orange-500 focus:ring-[3px] focus:ring-orange-500/25 transition-colors duration-150"
        />
      </div>
      <div>
        <label
          for="ws-desc"
          class="block text-xs font-medium text-stone-800 dark:text-stone-200"
        >
          描述
        </label>
        <textarea
          id="ws-desc"
          v-model="newDescription"
          name="description"
          rows="2"
          placeholder="這個工作區的用途…"
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
      v-if="store.loading && !store.loaded"
      class="mt-12 text-center text-stone-500"
    >
      <i class="pi pi-spinner pi-spin text-3xl"></i>
    </div>

    <!-- Error -->
    <div
      v-else-if="store.error && !store.loaded"
      class="mt-8 p-4 rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 text-red-700 dark:text-red-300 flex items-center gap-3"
      role="alert"
    >
      <i class="pi pi-exclamation-circle"></i>
      <span class="flex-1">{{ store.error }}</span>
      <button
        class="text-sm font-medium hover:underline"
        @click="store.fetchAll({ force: true }).catch(() => {})"
      >
        重試
      </button>
    </div>

    <!-- Empty state (§8.6) -->
    <div
      v-else-if="store.list.length === 0"
      class="py-16 text-center"
    >
      <i class="pi pi-th-large text-6xl text-stone-300 dark:text-stone-600"></i>
      <h2 class="mt-4 text-xl font-semibold text-stone-900 dark:text-stone-50">
        還沒有工作區
      </h2>
      <p class="mt-2 text-sm text-stone-500 dark:text-stone-400">
        建立第一個工作區來開始你的協作 →
      </p>
    </div>

    <!-- List -->
    <div
      v-else
      class="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      <RouterLink
        v-for="ws in store.list"
        :key="ws.id"
        :to="`/workspaces/${ws.id}/projects`"
        class="block p-6 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 shadow-xs hover:shadow-sm hover:border-orange-500 transition-all duration-150"
      >
        <h3
          class="text-lg font-semibold tracking-tight text-stone-900 dark:text-stone-50 truncate"
        >
          {{ ws.name }}
        </h3>
        <p
          class="mt-1 text-sm text-stone-600 dark:text-stone-400 line-clamp-2 min-h-[40px]"
        >
          {{ ws.description || '—' }}
        </p>
        <div class="mt-4 inline-flex items-center gap-1 text-sm font-medium text-orange-600">
          <span>進入</span>
          <i class="pi pi-arrow-right text-xs"></i>
        </div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * WorkspaceListView — 工作區列表頁。
 *
 * 狀態邏輯：
 * - loading + 未載入過 → spinner
 * - error + 未載入過 → 錯誤訊息 + 重試
 * - loaded + list 為空 → empty state
 * - loaded + list 有值 → grid 卡片
 *
 * 規格：.doc/taskflow_layout_design.md §8.3 Card / §8.6 Empty State
 */
import { onMounted, ref } from 'vue'

import { useWorkspaceStore } from '@/stores/workspace'
import { parseApiError } from '@/utils/api-errors'

const store = useWorkspaceStore()

const showCreateForm = ref(false)
const newName = ref('')
const newDescription = ref('')
const creating = ref(false)
const createError = ref<string | null>(null)

onMounted(() => {
  store.fetchAll().catch(() => {
    // 錯誤訊息已由 store.error 提供
  })
})

async function onCreate() {
  if (!newName.value.trim()) return
  creating.value = true
  createError.value = null
  try {
    await store.create({
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
