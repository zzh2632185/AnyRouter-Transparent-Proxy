import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ConfigAuthModal from '@/components/ConfigAuthModal.vue'

describe('ConfigAuthModal', () => {
  it('renders when visible', () => {
    const wrapper = mount(ConfigAuthModal, {
      props: { visible: true }
    })
    expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
  })

  it('emits authenticate with API key', async () => {
    const wrapper = mount(ConfigAuthModal, {
      props: { visible: true }
    })

    const input = wrapper.find('input[type="password"]')
    await input.setValue('test-key-12345')

    const form = wrapper.find('form')
    await form.trigger('submit.prevent')

    expect(wrapper.emitted('authenticate')).toBeTruthy()
    expect(wrapper.emitted('authenticate')[0]).toEqual(['test-key-12345'])
  })

  it('does not emit authenticate with empty API key', async () => {
    const wrapper = mount(ConfigAuthModal, {
      props: { visible: true }
    })

    const input = wrapper.find('input[type="password"]')
    await input.setValue('')

    const form = wrapper.find('form')
    await form.trigger('submit.prevent')

    expect(wrapper.emitted('authenticate')).toBeFalsy()
  })

  it('shows validation error when API key is too short', async () => {
    const wrapper = mount(ConfigAuthModal, {
      props: { visible: true }
    })

    const input = wrapper.find('input[type="password"]')
    await input.setValue('short')

    const form = wrapper.find('form')
    await form.trigger('submit.prevent')
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('至少为 8 个字符')
    expect(wrapper.emitted('authenticate')).toBeFalsy()
  })

  it('emits close on close button click', async () => {
    const wrapper = mount(ConfigAuthModal, {
      props: { visible: true }
    })

    const closeBtn = wrapper.findAll('button').find(btn =>
      btn.attributes('aria-label')?.includes('关闭')
    )
    await closeBtn?.trigger('click')

    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emits close on Escape key press', async () => {
    const wrapper = mount(ConfigAuthModal, {
      props: { visible: true }
    })

    await wrapper.find('[role="dialog"]').trigger('keydown.escape')

    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('does not emit close while loading', async () => {
    const wrapper = mount(ConfigAuthModal, {
      props: { visible: true, loading: true }
    })

    await wrapper.find('[role="dialog"]').trigger('keydown.escape')

    expect(wrapper.emitted('close')).toBeFalsy()
  })

  it('shows error message', () => {
    const wrapper = mount(ConfigAuthModal, {
      props: { visible: true, error: 'Invalid key' }
    })
    expect(wrapper.text()).toContain('Invalid key')
  })
})
