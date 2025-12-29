import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import RestartConfirmDialog from '@/components/RestartConfirmDialog.vue'

describe('RestartConfirmDialog', () => {
  it('renders when visible', () => {
    const wrapper = mount(RestartConfirmDialog, {
      props: { visible: true }
    })
    expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
  })

  it('emits confirm on confirm button click', async () => {
    const wrapper = mount(RestartConfirmDialog, {
      props: { visible: true }
    })

    const confirmBtn = wrapper.findAll('button').find(btn =>
      btn.text().includes('立即重启')
    )
    await confirmBtn?.trigger('click')

    expect(wrapper.emitted('confirm')).toBeTruthy()
  })

  it('emits later on later button click', async () => {
    const wrapper = mount(RestartConfirmDialog, {
      props: { visible: true }
    })

    const laterBtn = wrapper.findAll('button').find(btn =>
      btn.text().includes('稍后重启')
    )
    await laterBtn?.trigger('click')

    expect(wrapper.emitted('later')).toBeTruthy()
  })

  it('emits close on close button click', async () => {
    const wrapper = mount(RestartConfirmDialog, {
      props: { visible: true }
    })

    const closeBtn = wrapper.findAll('button').find(btn =>
      btn.attributes('aria-label')?.includes('关闭')
    )
    await closeBtn?.trigger('click')

    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emits close on Escape key press', async () => {
    const wrapper = mount(RestartConfirmDialog, {
      props: { visible: true }
    })

    await wrapper.find('[role="dialog"]').trigger('keydown.escape')

    expect(wrapper.emitted('close')).toBeTruthy()
  })
})
