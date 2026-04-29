<template>
  <div
    class="w-full max-w-md p-8 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 shadow-md"
  >
    <div>
      <h1 class="text-3xl font-bold tracking-tight text-stone-900 dark:text-stone-50">登入</h1>
      <p class="mt-2 text-sm text-stone-600 dark:text-stone-400">
        登入以管理你的工作區與任務。
      </p>
    </div>

    <form class="mt-8 space-y-4" novalidate @submit.prevent="onSubmit">
      <div
        v-if="apiError"
        class="rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900 p-3 text-sm text-red-600 dark:text-red-300"
        role="alert"
      >
        <i class="pi pi-exclamation-circle mr-2"></i>{{ apiError }}
      </div>

      <div>
        <label for="email" class="block text-xs font-medium text-stone-800 dark:text-stone-200">
          Email <span class="text-red-500">*</span>
        </label>
        <input
          id="email"
          v-model="email"
          type="email"
          autocomplete="email"
          placeholder="you@example.com"
          class="mt-1 block w-full h-10 px-3 rounded-lg border bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-50 placeholder-stone-400 transition-colors duration-150 focus:outline-none focus:ring-[3px]"
          :class="
            emailError
              ? 'border-red-500 focus:border-red-500 focus:ring-red-500/25'
              : 'border-stone-200 dark:border-stone-700 focus:border-orange-500 focus:ring-orange-500/25'
          "
        />
        <p v-if="emailError" class="mt-2 text-xs text-red-600 dark:text-red-400" role="alert">
          {{ emailError }}
        </p>
      </div>

      <div>
        <label
          for="password"
          class="block text-xs font-medium text-stone-800 dark:text-stone-200"
        >
          密碼 <span class="text-red-500">*</span>
        </label>
        <input
          id="password"
          v-model="password"
          type="password"
          autocomplete="current-password"
          placeholder="••••••••"
          class="mt-1 block w-full h-10 px-3 rounded-lg border bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-50 placeholder-stone-400 transition-colors duration-150 focus:outline-none focus:ring-[3px]"
          :class="
            passwordError
              ? 'border-red-500 focus:border-red-500 focus:ring-red-500/25'
              : 'border-stone-200 dark:border-stone-700 focus:border-orange-500 focus:ring-orange-500/25'
          "
        />
        <p v-if="passwordError" class="mt-2 text-xs text-red-600 dark:text-red-400" role="alert">
          {{ passwordError }}
        </p>
      </div>

      <button
        type="submit"
        :disabled="isSubmitting"
        class="w-full h-10 px-4 rounded-lg bg-orange-500 hover:bg-orange-600 active:bg-orange-700 text-white text-sm font-medium disabled:opacity-60 disabled:cursor-not-allowed transition-colors duration-150 inline-flex items-center justify-center gap-2"
      >
        <i v-if="isSubmitting" class="pi pi-spinner pi-spin"></i>
        <span>{{ isSubmitting ? '登入中…' : '登入' }}</span>
      </button>

      <div class="relative my-6" aria-hidden="true">
        <div class="absolute inset-0 flex items-center">
          <div class="w-full border-t border-stone-200 dark:border-stone-700"></div>
        </div>
        <div class="relative flex justify-center text-xs">
          <span class="px-3 bg-white dark:bg-stone-800 text-stone-500">或使用第三方登入</span>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <button
          type="button"
          disabled
          class="h-10 px-4 rounded-lg border border-stone-200 dark:border-stone-700 bg-transparent text-stone-800 dark:text-stone-100 text-sm font-medium hover:bg-stone-100 dark:hover:bg-stone-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors duration-150 inline-flex items-center justify-center gap-2"
        >
          <i class="pi pi-google"></i>
          <span>Google</span>
        </button>
        <button
          type="button"
          disabled
          class="h-10 px-4 rounded-lg border border-stone-200 dark:border-stone-700 bg-transparent text-stone-800 dark:text-stone-100 text-sm font-medium hover:bg-stone-100 dark:hover:bg-stone-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors duration-150 inline-flex items-center justify-center gap-2"
        >
          <i class="pi pi-comments"></i>
          <span>LINE</span>
        </button>
      </div>
    </form>

    <p
      class="mt-6 pt-6 border-t border-stone-200 dark:border-stone-700 text-sm text-center text-stone-600 dark:text-stone-400"
    >
      還沒有帳號？
      <a href="/register" class="font-medium text-orange-600 hover:text-orange-700 hover:underline">
        前往註冊
      </a>
    </p>
  </div>
</template>

<script setup lang="ts">
/**
 * LoginView — 帳密登入頁。
 *
 * 外殼版型由 AuthLayout 提供（左側品牌 / 右側中央），本元件只負責表單卡片本身。
 *
 * - 表單驗證：vee-validate (useForm + useField) + Zod (LoginSchema)
 * - 成功登入後依 ?redirect= query 或 fallback /dashboard 導頁
 * - API 錯誤訊息優先取後端 detail
 *
 * 規格：.doc/taskflow-frontend.md §4.6、.doc/taskflow_layout_design.md §9.1
 */
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useForm, useField } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'

import { LoginSchema } from '@/schemas/auth'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const apiError = ref<string | null>(null)

const { handleSubmit, isSubmitting } = useForm({
  validationSchema: toTypedSchema(LoginSchema),
  initialValues: { email: '', password: '' },
})

const { value: email, errorMessage: emailError } = useField<string>('email')
const { value: password, errorMessage: passwordError } = useField<string>('password')

const onSubmit = handleSubmit(async (values) => {
  apiError.value = null
  try {
    await authStore.login(values.email, values.password)
    const redirect =
      typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    await router.push(redirect)
  } catch (err: unknown) {
    apiError.value = extractError(err)
  }
})

function extractError(err: unknown): string {
  if (err && typeof err === 'object' && 'response' in err) {
    const r = (err as { response?: { data?: { detail?: string } } }).response
    if (r?.data?.detail) return r.data.detail
  }
  return '登入失敗，請稍後再試'
}
</script>
