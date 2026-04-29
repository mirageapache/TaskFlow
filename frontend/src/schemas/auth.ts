/**
 * Auth 表單的 Zod Schema 定義。
 *
 * 與 vee-validate 整合方式：
 *   import { toTypedSchema } from '@vee-validate/zod'
 *   useForm({ validationSchema: toTypedSchema(LoginSchema) })
 *
 * 規格：.doc/taskflow-frontend.md §4.6
 */
import { z } from 'zod'

export const LoginSchema = z.object({
  email: z.string().email('請輸入有效的 Email'),
  password: z.string().min(8, '密碼至少 8 個字元'),
})

export const RegisterSchema = z
  .object({
    email: z.string().email('請輸入有效的 Email'),
    username: z.string().min(3, '使用者名至少 3 個字元').max(50, '使用者名最多 50 個字元'),
    password: z.string().min(8, '密碼至少 8 個字元'),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: '密碼不一致',
    path: ['confirmPassword'],
  })

export type LoginFormData = z.infer<typeof LoginSchema>
export type RegisterFormData = z.infer<typeof RegisterSchema>
