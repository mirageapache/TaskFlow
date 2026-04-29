/**
 * AuthLayout 測試
 * 規格：.doc/taskflow_layout_design.md §9.1
 *
 * 驗證：
 * - 渲染預設 slot 內容
 * - 顯示 TaskFlow 品牌面板
 * - 品牌面板帶 hidden + lg:flex（行動版隱藏，桌面顯示）
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'

import AuthLayout from '@/layouts/AuthLayout.vue'

describe('AuthLayout', () => {
  it('渲染 slot 內容', () => {
    const wrapper = mount(AuthLayout, {
      slots: {
        default: '<div data-test="form">表單內容</div>',
      },
    })
    expect(wrapper.find('[data-test="form"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('表單內容')
  })

  it('顯示 TaskFlow 品牌面板', () => {
    const wrapper = mount(AuthLayout)
    expect(wrapper.text()).toContain('TaskFlow')
  })

  it('品牌面板（aside）行動版隱藏、桌面顯示', () => {
    const wrapper = mount(AuthLayout)
    const aside = wrapper.find('aside')
    expect(aside.exists()).toBe(true)
    // hidden + lg:flex 是 §9.1 行動版單欄/桌面雙欄的實作
    expect(aside.classes()).toContain('hidden')
    expect(aside.classes()).toContain('lg:flex')
  })
})
