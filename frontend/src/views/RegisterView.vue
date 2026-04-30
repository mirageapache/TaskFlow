<template>
  <div
    class="w-full max-w-md p-8 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 shadow-md"
  >
    <div>
      <h1 class="text-3xl font-bold tracking-tight text-stone-900 dark:text-stone-50">
        建立帳號
      </h1>
      <p class="mt-2 text-sm text-stone-600 dark:text-stone-400">
        註冊後將自動登入並進入儀表板。
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
          name="email"
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
          for="username"
          class="block text-xs font-medium text-stone-800 dark:text-stone-200"
        >
          使用者名稱 <span class="text-red-500">*</span>
        </label>
        <input
          id="username"
          v-model="username"
          name="username"
          type="text"
          autocomplete="username"
          placeholder="3–50 字元"
          class="mt-1 block w-full h-10 px-3 rounded-lg border bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-50 placeholder-stone-400 transition-colors duration-150 focus:outline-none focus:ring-[3px]"
          :class="
            usernameError
              ? 'border-red-500 focus:border-red-500 focus:ring-red-500/25'
              : 'border-stone-200 dark:border-stone-700 focus:border-orange-500 focus:ring-orange-500/25'
          "
        />
        <p v-if="usernameError" class="mt-2 text-xs text-red-600 dark:text-red-400" role="alert">
          {{ usernameError }}
        </p>
      </div>

      <div>
        <label
          for="password"
          class="block text-xs font-medium text-stone-800 dark:text-stone-200"
        >
          密碼 <span class="text-red-500">*</span>
        </label>
        <div class="mt-1 relative">
          <input
            id="password"
            v-model="password"
            name="password"
            :type="passwordVisible ? 'text' : 'password'"
            autocomplete="new-password"
            placeholder="至少 8 個字元"
            class="block w-full h-10 pl-3 pr-10 rounded-lg border bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-50 placeholder-stone-400 transition-colors duration-150 focus:outline-none focus:ring-[3px]"
            :class="
              passwordError
                ? 'border-red-500 focus:border-red-500 focus:ring-red-500/25'
                : 'border-stone-200 dark:border-stone-700 focus:border-orange-500 focus:ring-orange-500/25'
            "
          />
          <button
            type="button"
            data-test="toggle-password"
            class="absolute inset-y-0 right-0 flex items-center px-3 text-stone-400 hover:text-stone-600 dark:hover:text-stone-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/50 rounded-r-lg"
            :aria-label="passwordVisible ? '隱藏密碼' : '顯示密碼'"
            @click="passwordVisible = !passwordVisible"
          >
            <i :class="passwordVisible ? 'pi pi-eye' : 'pi pi-eye-slash'"></i>
          </button>
        </div>
        <p v-if="passwordError" class="mt-2 text-xs text-red-600 dark:text-red-400" role="alert">
          {{ passwordError }}
        </p>
      </div>

      <div>
        <label
          for="confirmPassword"
          class="block text-xs font-medium text-stone-800 dark:text-stone-200"
        >
          確認密碼 <span class="text-red-500">*</span>
        </label>
        <div class="mt-1 relative">
          <input
            id="confirmPassword"
            v-model="confirmPassword"
            name="confirmPassword"
            :type="confirmPasswordVisible ? 'text' : 'password'"
            autocomplete="new-password"
            placeholder="再輸入一次密碼"
            class="block w-full h-10 pl-3 pr-10 rounded-lg border bg-white dark:bg-stone-900 text-stone-900 dark:text-stone-50 placeholder-stone-400 transition-colors duration-150 focus:outline-none focus:ring-[3px]"
            :class="
              confirmPasswordError
                ? 'border-red-500 focus:border-red-500 focus:ring-red-500/25'
                : 'border-stone-200 dark:border-stone-700 focus:border-orange-500 focus:ring-orange-500/25'
            "
          />
          <button
            type="button"
            data-test="toggle-confirm-password"
            class="absolute inset-y-0 right-0 flex items-center px-3 text-stone-400 hover:text-stone-600 dark:hover:text-stone-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-500/50 rounded-r-lg"
            :aria-label="confirmPasswordVisible ? '隱藏密碼' : '顯示密碼'"
            @click="confirmPasswordVisible = !confirmPasswordVisible"
          >
            <i :class="confirmPasswordVisible ? 'pi pi-eye' : 'pi pi-eye-slash'"></i>
          </button>
        </div>
        <p
          v-if="confirmPasswordError"
          class="mt-2 text-xs text-red-600 dark:text-red-400"
          role="alert"
        >
          {{ confirmPasswordError }}
        </p>
      </div>

      <button
        type="submit"
        :disabled="isSubmitting"
        class="w-full h-10 px-4 rounded-lg bg-orange-500 hover:bg-orange-600 active:bg-orange-700 text-white text-sm font-medium disabled:opacity-60 disabled:cursor-not-allowed transition-colors duration-150 inline-flex items-center justify-center gap-2"
      >
        <i v-if="isSubmitting" class="pi pi-spinner pi-spin"></i>
        <span>{{ isSubmitting ? '註冊中…' : '建立帳號' }}</span>
      </button>
    </form>

    <p
      class="mt-6 pt-6 border-t border-stone-200 dark:border-stone-700 text-sm text-center text-stone-600 dark:text-stone-400"
    >
      已經有帳號？
      <a href="/login" class="font-medium text-orange-600 hover:text-orange-700 hover:underline">
        前往登入
      </a>
    </p>
  </div>
</template>

<script setup lang="ts">
/**
 * RegisterView — 註冊頁。
 *
 * 外殼版型由 AuthLayout 提供，本元件只負責表單卡片本身。
 *
 * - 表單驗證：vee-validate (useForm + useField) + Zod (RegisterSchema)
 * - 註冊成功後 authStore.register 內部會自動 login，再導 /dashboard
 * - API 錯誤訊息優先取後端 detail
 *
 * 規格：.doc/taskflow-frontend.md §4.6、.doc/taskflow_layout_design.md §9.1
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useForm, useField } from 'vee-validate'
import { toTypedSchema } from '@vee-validate/zod'

import { RegisterSchema } from '@/schemas/auth'
import { useAuthStore } from '@/stores/auth'
import { parseApiError } from '@/utils/api-errors'

const router = useRouter()
const authStore = useAuthStore()

const apiError = ref<string | null>(null)
const passwordVisible = ref(false)
const confirmPasswordVisible = ref(false)

const KNOWN_FIELDS = ['email', 'username', 'password', 'confirmPassword'] as const
type RegisterField = (typeof KNOWN_FIELDS)[number]

const { handleSubmit, isSubmitting, setFieldError } = useForm({
  validationSchema: toTypedSchema(RegisterSchema),
  initialValues: { email: '', username: '', password: '', confirmPassword: '' },
})

const { value: email, errorMessage: emailError } = useField<string>('email')
const { value: username, errorMessage: usernameError } = useField<string>('username')
const { value: password, errorMessage: passwordError } = useField<string>('password')
const { value: confirmPassword, errorMessage: confirmPasswordError } =
  useField<string>('confirmPassword')

const onSubmit = handleSubmit(async (values) => {
  apiError.value = null
  try {
    await authStore.register(values.email, values.username, values.password)
    await router.push('/dashboard')
  } catch (err: unknown) {
    const { banner, fieldErrors } = parseApiError(err, [...KNOWN_FIELDS])
    for (const [field, message] of Object.entries(fieldErrors)) {
      setFieldError(field as RegisterField, message)
    }
    if (banner) {
      apiError.value = banner
    } else if (Object.keys(fieldErrors).length === 0) {
      apiError.value = '註冊失敗，請稍後再試'
    }
  }
})
</script>
