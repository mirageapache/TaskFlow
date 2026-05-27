<template>
  <div data-test="settings-view" class="space-y-6">
    <!-- Header -->
    <header>
      <h1 class="text-3xl font-bold tracking-tight text-stone-900 dark:text-stone-50">設定</h1>
      <p class="mt-1 text-sm text-stone-600 dark:text-stone-400">
        管理你的個人資料與偏好設定。
      </p>
    </header>

    <!-- Initial loading -->
    <div v-if="loading" class="py-12 text-center text-stone-500">
      <i class="pi pi-spinner pi-spin text-3xl"></i>
    </div>

    <template v-else>
      <!-- 個人資料 -->
      <section
        data-test="profile-section"
        class="p-6 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 shadow-xs"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-lg font-semibold text-stone-900 dark:text-stone-50">個人資料</h2>
            <p class="mt-1 text-xs text-stone-500 dark:text-stone-400">
              更新顯示名稱、頭像與自我介紹。
            </p>
          </div>
        </div>

        <form class="mt-6 space-y-4" novalidate @submit.prevent="saveProfile">
          <div
            v-if="profileError"
            class="rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 p-3 text-sm text-red-600 dark:text-red-300"
            role="alert"
          >
            <i class="pi pi-exclamation-circle mr-2"></i>{{ profileError }}
          </div>

          <!-- Avatar + URL -->
          <div class="flex items-center gap-4">
            <span
              class="w-16 h-16 rounded-full bg-orange-500 text-white inline-flex items-center justify-center text-xl font-medium overflow-hidden shrink-0"
            >
              <img
                v-if="profileForm.avatar_url"
                :src="profileForm.avatar_url"
                alt="頭像預覽"
                class="w-full h-full object-cover"
                @error="onAvatarError"
              />
              <template v-else>{{ usernameInitial }}</template>
            </span>
            <div class="flex-1 min-w-0">
              <label
                for="avatar-url"
                class="block text-xs font-medium text-stone-800 dark:text-stone-200"
              >
                頭像網址
              </label>
              <input
                id="avatar-url"
                v-model="profileForm.avatar_url"
                data-test="avatar-url"
                type="url"
                placeholder="https://..."
                class="mt-1 block w-full h-10 px-3 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-50 placeholder-stone-400 transition-colors duration-150 focus:outline-none focus:ring-[3px] focus:border-orange-500 focus:ring-orange-500/25"
              />
            </div>
          </div>

          <!-- Email (readonly) -->
          <div>
            <label
              for="email"
              class="block text-xs font-medium text-stone-800 dark:text-stone-200"
            >
              Email
            </label>
            <input
              id="email"
              :value="email"
              data-test="email"
              type="email"
              readonly
              class="mt-1 block w-full h-10 px-3 rounded-lg border border-stone-200 dark:border-stone-700 bg-stone-50 dark:bg-stone-900/60 text-stone-500 dark:text-stone-400 cursor-not-allowed"
            />
            <p class="mt-1 text-xs text-stone-500">Email 無法在此修改。</p>
          </div>

          <!-- Username -->
          <div>
            <label
              for="username"
              class="block text-xs font-medium text-stone-800 dark:text-stone-200"
            >
              使用者名稱 <span class="text-red-500">*</span>
            </label>
            <input
              id="username"
              v-model="profileForm.username"
              data-test="username"
              type="text"
              minlength="3"
              maxlength="50"
              required
              class="mt-1 block w-full h-10 px-3 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-50 placeholder-stone-400 transition-colors duration-150 focus:outline-none focus:ring-[3px] focus:border-orange-500 focus:ring-orange-500/25"
            />
          </div>

          <!-- Display name -->
          <div>
            <label
              for="display-name"
              class="block text-xs font-medium text-stone-800 dark:text-stone-200"
            >
              顯示名稱
            </label>
            <input
              id="display-name"
              v-model="profileForm.display_name"
              data-test="display-name"
              type="text"
              maxlength="100"
              placeholder="於通知、評論中顯示的名稱"
              class="mt-1 block w-full h-10 px-3 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-50 placeholder-stone-400 transition-colors duration-150 focus:outline-none focus:ring-[3px] focus:border-orange-500 focus:ring-orange-500/25"
            />
          </div>

          <!-- Bio -->
          <div>
            <label
              for="bio"
              class="block text-xs font-medium text-stone-800 dark:text-stone-200"
            >
              自我介紹
            </label>
            <textarea
              id="bio"
              v-model="profileForm.bio"
              data-test="bio"
              rows="3"
              maxlength="500"
              placeholder="關於你..."
              class="mt-1 block w-full px-3 py-2 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-50 placeholder-stone-400 transition-colors duration-150 focus:outline-none focus:ring-[3px] focus:border-orange-500 focus:ring-orange-500/25 resize-y"
            ></textarea>
          </div>

          <div class="flex justify-end pt-2">
            <button
              type="submit"
              data-test="save-profile"
              :disabled="profileSaving || !profileForm.username.trim()"
              class="h-10 px-5 rounded-lg bg-orange-500 hover:bg-orange-600 active:bg-orange-700 text-white text-sm font-medium disabled:opacity-60 disabled:cursor-not-allowed transition-colors duration-150 inline-flex items-center gap-2"
            >
              <i v-if="profileSaving" class="pi pi-spinner pi-spin"></i>
              <span>{{ profileSaving ? '儲存中…' : '儲存個人資料' }}</span>
            </button>
          </div>
        </form>
      </section>

      <!-- 偏好設定（自動儲存） -->
      <section
        data-test="preferences-section"
        class="p-6 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 shadow-xs"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 class="text-lg font-semibold text-stone-900 dark:text-stone-50">偏好設定</h2>
            <p class="mt-1 text-xs text-stone-500 dark:text-stone-400">
              變更後自動儲存。主題會立即套用，時區與語系會影響日期與通知顯示。
            </p>
          </div>
          <span
            data-test="prefs-status"
            class="shrink-0 inline-flex items-center gap-1.5 text-xs"
            :class="prefsStatusColor"
          >
            <i v-if="prefsStatus === 'saving'" class="pi pi-spinner pi-spin"></i>
            <i v-else-if="prefsStatus === 'saved'" class="pi pi-check-circle"></i>
            <i v-else-if="prefsStatus === 'error'" class="pi pi-exclamation-circle"></i>
            <span v-if="prefsStatusLabel">{{ prefsStatusLabel }}</span>
          </span>
        </div>

        <div class="mt-6 space-y-5">
          <div
            v-if="preferencesError"
            class="rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 p-3 text-sm text-red-600 dark:text-red-300"
            role="alert"
          >
            <i class="pi pi-exclamation-circle mr-2"></i>{{ preferencesError }}
          </div>

          <!-- Theme: 3 radio cards -->
          <fieldset>
            <legend class="block text-xs font-medium text-stone-800 dark:text-stone-200">
              主題
            </legend>
            <div class="mt-2 grid grid-cols-3 gap-3">
              <label
                v-for="opt in THEME_OPTIONS"
                :key="opt.value"
                :data-test="`theme-${opt.value}`"
                class="cursor-pointer p-3 rounded-lg border text-sm flex flex-col items-center gap-2 transition-colors duration-150"
                :class="
                  preferencesForm.theme === opt.value
                    ? 'border-orange-500 bg-orange-50 dark:bg-orange-950/30 text-orange-700 dark:text-orange-300 ring-[3px] ring-orange-500/25'
                    : 'border-stone-200 dark:border-stone-700 hover:bg-stone-50 dark:hover:bg-stone-700/40 text-stone-700 dark:text-stone-200'
                "
              >
                <input
                  v-model="preferencesForm.theme"
                  type="radio"
                  :value="opt.value"
                  class="sr-only"
                />
                <i :class="['pi', opt.icon, 'text-xl']"></i>
                <span class="font-medium">{{ opt.label }}</span>
              </label>
            </div>
          </fieldset>

          <!-- Language -->
          <div>
            <label
              for="language"
              class="block text-xs font-medium text-stone-800 dark:text-stone-200"
            >
              語系
            </label>
            <select
              id="language"
              v-model="preferencesForm.language"
              data-test="language"
              class="mt-1 block w-full h-10 px-3 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-50 transition-colors duration-150 focus:outline-none focus:ring-[3px] focus:border-orange-500 focus:ring-orange-500/25"
            >
              <option v-for="opt in LANGUAGE_OPTIONS" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

          <!-- Timezone -->
          <div>
            <label
              for="timezone"
              class="block text-xs font-medium text-stone-800 dark:text-stone-200"
            >
              時區
            </label>
            <select
              id="timezone"
              v-model="preferencesForm.timezone"
              data-test="timezone"
              class="mt-1 block w-full h-10 px-3 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-50 transition-colors duration-150 focus:outline-none focus:ring-[3px] focus:border-orange-500 focus:ring-orange-500/25"
            >
              <option v-for="opt in TIMEZONE_OPTIONS" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </option>
            </select>
          </div>

        </div>
      </section>
    </template>

    <!-- 未儲存變更提示彈窗（個人資料 dirty 時觸發） -->
    <div
      v-if="showLeaveConfirm"
      data-test="leave-confirm"
      class="fixed inset-0 z-[1300] bg-black/40 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="leave-confirm-title"
      @click.self="cancelLeave"
    >
      <div
        class="w-full max-w-sm rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 shadow-lg"
      >
        <div class="p-5">
          <div class="flex items-start gap-3">
            <span
              class="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-950/50 text-amber-600 inline-flex items-center justify-center shrink-0"
            >
              <i class="pi pi-exclamation-triangle"></i>
            </span>
            <div class="min-w-0">
              <h3
                id="leave-confirm-title"
                class="text-base font-semibold text-stone-900 dark:text-stone-50"
              >
                有未儲存的變更
              </h3>
              <p class="mt-1 text-sm text-stone-600 dark:text-stone-400">
                你修改了個人資料但尚未儲存,離開此頁後變更將會遺失。
              </p>
            </div>
          </div>
        </div>
        <div
          class="px-5 py-3 border-t border-stone-200 dark:border-stone-700 flex justify-end gap-2"
        >
          <button
            type="button"
            data-test="leave-cancel"
            class="h-9 px-4 rounded-lg border border-stone-200 dark:border-stone-700 bg-transparent text-sm font-medium text-stone-700 dark:text-stone-200 hover:bg-stone-50 dark:hover:bg-stone-700 transition-colors duration-150"
            @click="cancelLeave"
          >
            留在此頁
          </button>
          <button
            type="button"
            data-test="leave-confirm-btn"
            class="h-9 px-4 rounded-lg bg-red-500 hover:bg-red-600 text-white text-sm font-medium transition-colors duration-150"
            @click="confirmLeave"
          >
            放棄變更並離開
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * SettingsView — 個人資料與偏好設定。
 *
 * 分兩張卡片各自獨立儲存：
 * - 個人資料：PATCH /users/me/（username）+ PATCH /users/me/profile/（display_name、bio、avatar_url）
 * - 偏好設定：PATCH /users/me/profile/（theme、language、timezone）
 *
 * 主題切換即時套用到 <html>，並寫 localStorage；後端 PATCH 失敗時不回滾，因為 UI 已切換、
 * 使用者體感優先。下次登入時以後端值為準（fetchUser 完成後 applyTheme 同步）。
 *
 * 規格：.doc/taskflow-api_doc.md §8、.doc/taskflow-frontend.md
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { useToast } from 'primevue/usetoast'

import client from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { parseApiError } from '@/utils/api-errors'
import { applyTheme, type ThemePreference } from '@/utils/theme'

interface ProfileResponse {
  id: string
  email: string
  username: string
  profile: {
    display_name: string
    bio: string
    avatar_url: string
    timezone: string
    language: string
    theme: ThemePreference
  } | null
}

const THEME_OPTIONS = [
  { value: 'light' as const, label: '亮色', icon: 'pi-sun' },
  { value: 'dark' as const, label: '深色', icon: 'pi-moon' },
  { value: 'system' as const, label: '跟隨系統', icon: 'pi-desktop' },
]

const LANGUAGE_OPTIONS = [
  { value: 'zh-TW', label: '繁體中文' },
  { value: 'en-US', label: 'English' },
]

const TIMEZONE_OPTIONS = [
  { value: 'Asia/Taipei', label: '台北 (UTC+8)' },
  { value: 'Asia/Tokyo', label: '東京 (UTC+9)' },
  { value: 'Asia/Singapore', label: '新加坡 (UTC+8)' },
  { value: 'America/Los_Angeles', label: '洛杉磯 (UTC-8/-7)' },
  { value: 'America/New_York', label: '紐約 (UTC-5/-4)' },
  { value: 'Europe/London', label: '倫敦 (UTC+0/+1)' },
  { value: 'UTC', label: 'UTC' },
]

const toast = useToast()
const authStore = useAuthStore()

const loading = ref(true)
const profileSaving = ref(false)
const profileError = ref<string | null>(null)
const preferencesError = ref<string | null>(null)

const email = ref('')

interface ProfileFormState {
  username: string
  display_name: string
  bio: string
  avatar_url: string
}

const profileForm = reactive<ProfileFormState>({
  username: '',
  display_name: '',
  bio: '',
  avatar_url: '',
})

/** 從伺服器載入時的快照,用來判斷 profile 是否有未儲存的變更。 */
const profileInitial = ref<ProfileFormState>({
  username: '',
  display_name: '',
  bio: '',
  avatar_url: '',
})

const profileDirty = computed(() => {
  const a = profileForm
  const b = profileInitial.value
  return (
    a.username !== b.username
    || a.display_name !== b.display_name
    || a.bio !== b.bio
    || a.avatar_url !== b.avatar_url
  )
})

const preferencesForm = reactive<{
  theme: ThemePreference
  language: string
  timezone: string
}>({
  theme: 'system',
  language: 'zh-TW',
  timezone: 'Asia/Taipei',
})

const usernameInitial = computed(
  () => profileForm.username?.[0]?.toUpperCase() ?? authStore.user?.username?.[0]?.toUpperCase() ?? '?',
)

// ────────────── 偏好設定:自動儲存狀態 ──────────────

type PrefsStatus = 'idle' | 'saving' | 'saved' | 'error'

const prefsStatus = ref<PrefsStatus>('idle')

const prefsStatusLabel = computed(() => {
  switch (prefsStatus.value) {
    case 'saving': return '儲存中…'
    case 'saved': return '已儲存'
    case 'error': return '儲存失敗'
    default: return ''
  }
})

const prefsStatusColor = computed(() => {
  switch (prefsStatus.value) {
    case 'saving': return 'text-stone-500 dark:text-stone-400'
    case 'saved': return 'text-emerald-600 dark:text-emerald-400'
    case 'error': return 'text-red-600 dark:text-red-400'
    default: return 'text-transparent'
  }
})

// ────────────── 未儲存變更:離開頁面確認 ──────────────

const showLeaveConfirm = ref(false)
/** 使用者按下「放棄變更並離開」後要執行的導航動作(由 onBeforeRouteLeave 設定)。 */
let pendingNav: (() => void) | null = null

/** 在 loadMe 完成前不啟動偏好自動儲存,避免初次寫入觸發 PATCH。 */
let prefsAutoSaveArmed = false
/** 偏好設定 debounce timer。 */
let prefsSaveTimer: ReturnType<typeof setTimeout> | null = null
/** 「已儲存」狀態自動淡出計時器。 */
let prefsSavedDismissTimer: ReturnType<typeof setTimeout> | null = null

/** 把目前 profileForm 的值快照成「已儲存狀態」,用於 dirty 比對。 */
function snapshotProfile() {
  profileInitial.value = {
    username: profileForm.username,
    display_name: profileForm.display_name,
    bio: profileForm.bio,
    avatar_url: profileForm.avatar_url,
  }
}

/** 載入 /users/me/ 填入兩個表單。 */
async function loadMe() {
  try {
    const { data } = await client.get<ProfileResponse>('/users/me/')
    email.value = data.email
    profileForm.username = data.username
    if (data.profile) {
      profileForm.display_name = data.profile.display_name ?? ''
      profileForm.bio = data.profile.bio ?? ''
      profileForm.avatar_url = data.profile.avatar_url ?? ''
      preferencesForm.theme = data.profile.theme ?? 'system'
      preferencesForm.language = data.profile.language ?? 'zh-TW'
      preferencesForm.timezone = data.profile.timezone ?? 'Asia/Taipei'
      // 後端為主:同步套用主題(覆蓋 localStorage 上次的值)
      applyTheme(preferencesForm.theme)
    }
    snapshotProfile()
    // 等下一個 tick 才開始監聽偏好設定,避免 loadMe 寫入時誤觸自動儲存
    prefsAutoSaveArmed = true
  } catch (err) {
    const { banner } = parseApiError(err)
    profileError.value = banner ?? '無法載入個人資料,請重新整理頁面再試。'
  } finally {
    loading.value = false
  }
}

async function saveProfile() {
  profileError.value = null
  profileSaving.value = true
  try {
    // username → /users/me/，其他 → /users/me/profile/
    await Promise.all([
      client.patch('/users/me/', { username: profileForm.username.trim() }),
      client.patch('/users/me/profile/', {
        display_name: profileForm.display_name.trim(),
        bio: profileForm.bio,
        avatar_url: profileForm.avatar_url.trim(),
      }),
    ])
    // 讓 AppLayout 的使用者選單即時反映新的 username / avatar
    await authStore.fetchUser().catch(() => {})
    snapshotProfile()
    toast.add({
      severity: 'success',
      summary: '個人資料已更新',
      life: 3000,
    })
  } catch (err) {
    const { banner, fieldErrors } = parseApiError(err, ['username', 'display_name', 'bio', 'avatar_url'])
    const fieldMsgs = Object.entries(fieldErrors)
      .map(([f, m]) => `${f}: ${m}`)
      .join('；')
    profileError.value = banner ?? fieldMsgs ?? '儲存失敗,請稍後再試。'
  } finally {
    profileSaving.value = false
  }
}

// ────────────── 偏好設定:自動儲存 ──────────────

const PREFS_DEBOUNCE_MS = 500

/** 將目前偏好設定 PATCH 回後端。 */
async function flushPreferences() {
  preferencesError.value = null
  prefsStatus.value = 'saving'
  try {
    await client.patch('/users/me/profile/', {
      theme: preferencesForm.theme,
      language: preferencesForm.language,
      timezone: preferencesForm.timezone,
    })
    prefsStatus.value = 'saved'
    // 2 秒後淡出「已儲存」標籤
    if (prefsSavedDismissTimer) clearTimeout(prefsSavedDismissTimer)
    prefsSavedDismissTimer = setTimeout(() => {
      if (prefsStatus.value === 'saved') prefsStatus.value = 'idle'
    }, 2000)
  } catch (err) {
    prefsStatus.value = 'error'
    const { banner } = parseApiError(err)
    preferencesError.value = banner ?? '偏好設定儲存失敗,請稍後再試。'
  }
}

// 主題:同步套用 .dark class(不等 debounce,使用者期待立即看到效果)
watch(
  () => preferencesForm.theme,
  (newTheme) => {
    if (!prefsAutoSaveArmed) return
    applyTheme(newTheme)
  },
)

// 任一偏好欄位變更 → debounce 後 PATCH
watch(
  preferencesForm,
  () => {
    if (!prefsAutoSaveArmed) return
    if (prefsSaveTimer) clearTimeout(prefsSaveTimer)
    prefsStatus.value = 'saving'
    prefsSaveTimer = setTimeout(() => {
      prefsSaveTimer = null
      flushPreferences()
    }, PREFS_DEBOUNCE_MS)
  },
  { deep: true },
)

// ────────────── 未儲存變更:離開頁面提示 ──────────────

function confirmLeave() {
  showLeaveConfirm.value = false
  // 放棄變更:把表單還原成快照,避免 onBeforeRouteLeave 再次攔截
  Object.assign(profileForm, profileInitial.value)
  const nav = pendingNav
  pendingNav = null
  nav?.()
}

function cancelLeave() {
  showLeaveConfirm.value = false
  pendingNav = null
}

onBeforeRouteLeave((_to, _from, next) => {
  if (!profileDirty.value || showLeaveConfirm.value) {
    next()
    return
  }
  pendingNav = () => next()
  showLeaveConfirm.value = true
  next(false)
})

/** 攔截分頁關閉 / 重新整理:有未儲存變更時觸發瀏覽器原生提示。 */
function handleBeforeUnload(e: BeforeUnloadEvent) {
  if (profileDirty.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}

/** 頭像 URL 載入失敗時清空欄位以回退到字母佔位。 */
function onAvatarError() {
  profileForm.avatar_url = ''
}

onMounted(() => {
  loadMe()
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(() => {
  window.removeEventListener('beforeunload', handleBeforeUnload)
  if (prefsSaveTimer) {
    clearTimeout(prefsSaveTimer)
    // 元件卸載前若還有未送出的偏好變更,立即送出(fire-and-forget)
    flushPreferences()
  }
  if (prefsSavedDismissTimer) clearTimeout(prefsSavedDismissTimer)
})
</script>
