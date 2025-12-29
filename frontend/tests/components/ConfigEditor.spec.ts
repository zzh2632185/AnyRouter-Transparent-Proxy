import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ConfigEditor from '@/components/ConfigEditor.vue'

const mockConfig = [
  {
    key: 'test_string',
    value: 'hello',
    metadata: {
      value_type: 'string',
      editable: true,
      requires_restart: false,
      description: 'Test string',
      category: 'Test',
      example: 'example'
    }
  },
  {
    key: 'test_number',
    value: 42,
    metadata: {
      value_type: 'number',
      editable: true,
      requires_restart: false,
      description: 'Test number',
      category: 'Test',
      example: 0
    }
  },
  {
    key: 'test_boolean',
    value: true,
    metadata: {
      value_type: 'boolean',
      editable: true,
      requires_restart: false,
      description: 'Test boolean',
      category: 'Test',
      example: false
    }
  },
  {
    key: 'test_json',
    value: { foo: 'bar' },
    metadata: {
      value_type: 'json',
      editable: true,
      requires_restart: false,
      description: 'Test json',
      category: 'Test',
      example: { foo: 'example' }
    }
  }
]

describe('ConfigEditor', () => {
  it('renders different input types', () => {
    const wrapper = mount(ConfigEditor, {
      props: { modelValue: mockConfig }
    })

    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
    expect(wrapper.find('input[type="number"]').exists()).toBe(true)
    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(true)
    expect(wrapper.find('textarea').exists()).toBe(true)
  })

  it('emits update on input change', async () => {
    const wrapper = mount(ConfigEditor, {
      props: { modelValue: mockConfig }
    })

    const input = wrapper.find('input[type="text"]')
    await input.setValue('new value')

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    const emittedValue = wrapper.emitted('update:modelValue')[0][0]
    expect(emittedValue.find(c => c.key === 'test_string').value).toBe('new value')
  })

  it('emits validate event', async () => {
    const wrapper = mount(ConfigEditor, {
      props: { modelValue: mockConfig }
    })

    const input = wrapper.find('input[type="text"]')
    await input.setValue('test')

    expect(wrapper.emitted('validate')).toBeTruthy()
  })

  it('validates json input and emits invalid state on parse error', async () => {
    vi.useFakeTimers()
    const wrapper = mount(ConfigEditor, {
      props: { modelValue: mockConfig }
    })

    const textarea = wrapper.find('textarea')
    await textarea.setValue('{ invalid json')

    vi.advanceTimersByTime(350)
    await nextTick()

    const validateEvents = wrapper.emitted('validate')?.map(e => e[0].isValid)
    expect(validateEvents?.includes(false)).toBe(true)
    expect(wrapper.text()).toContain('JSON 格式无效')
    vi.useRealTimers()
  })
})
