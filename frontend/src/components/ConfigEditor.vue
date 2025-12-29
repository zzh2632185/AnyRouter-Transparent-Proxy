<template>
  <div class="space-y-6">
    <div
      v-for="(entry, index) in localConfig"
      :key="entry.key"
      class="grid grid-cols-1 md:grid-cols-3 gap-4 items-start"
      :class="{ 'opacity-60': !entry.metadata.editable }"
    >
      <!-- Label and Description -->
      <div class="md:col-span-1">
        <label
          :for="`config-input-${entry.key}`"
          class="block text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          <span class="font-semibold">{{ entry.key }}</span>
          <span
            v-if="entry.metadata.requires_restart"
            class="ml-2 inline-block text-yellow-500 hover:text-yellow-700 transition-colors"
            title="此项配置需要重启服务才能生效"
          >
            <svg class="inline h-4 w-4" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/>
            </svg>
            <span class="sr-only">此项配置需要重启服务才能生效</span>
          </span>
        </label>
        <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
          {{ entry.metadata.description }}
        </p>
      </div>

      <!-- Input Control -->
      <div class="md:col-span-2">
        <!-- String Input -->
        <template v-if="entry.metadata.value_type === 'string'">
          <input
            :id="`config-input-${entry.key}`"
            v-model="localConfig[index].value"
            type="text"
            :readonly="!entry.metadata.editable"
            :aria-invalid="!!validationErrors[entry.key]"
            :aria-describedby="validationErrors[entry.key] ? `config-error-${entry.key}` : undefined"
            :class="[baseInputClass, { 'cursor-not-allowed': !entry.metadata.editable }]"
            :placeholder="entry.metadata.example?.toString() || '请输入文本值...'"
            @input="handleInputChange(index)"
          />
        </template>

        <!-- Number Input -->
        <template v-else-if="entry.metadata.value_type === 'number'">
          <input
            :id="`config-input-${entry.key}`"
            v-model.number="localConfig[index].value"
            type="number"
            :readonly="!entry.metadata.editable"
            :aria-invalid="!!validationErrors[entry.key]"
            :aria-describedby="validationErrors[entry.key] ? `config-error-${entry.key}` : undefined"
            :class="[baseInputClass, { 'cursor-not-allowed': !entry.metadata.editable }]"
            :placeholder="entry.metadata.example?.toString() || '请输入数字...'"
            @input="handleInputChange(index)"
          />
        </template>

        <!-- Boolean Toggle -->
        <template v-else-if="entry.metadata.value_type === 'boolean'">
          <label
            :for="`config-input-${entry.key}`"
            class="relative inline-flex items-center"
            :class="[entry.metadata.editable ? 'cursor-pointer' : 'cursor-not-allowed']"
          >
            <input
              :id="`config-input-${entry.key}`"
              v-model="localConfig[index].value"
              type="checkbox"
              :disabled="!entry.metadata.editable"
              class="sr-only peer"
              @change="handleInputChange(index)"
            />
            <div
              class="w-11 h-6 bg-gray-200 rounded-full peer dark:bg-gray-600 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-500 peer-checked:bg-blue-600"
              :class="{ 'opacity-50': !entry.metadata.editable }"
            ></div>
            <span class="ml-3 text-sm font-medium text-gray-900 dark:text-gray-300">
              {{ localConfig[index].value ? '启用' : '禁用' }}
            </span>
          </label>
        </template>

        <!-- JSON Editor -->
        <template v-else-if="entry.metadata.value_type === 'json'">
          <textarea
            :id="`config-input-${entry.key}`"
            :value="jsonTextValues[entry.key]"
            @input="handleJsonInput(entry.key, ($event.target as HTMLTextAreaElement).value)"
            rows="5"
            :readonly="!entry.metadata.editable"
            :aria-invalid="!!validationErrors[entry.key]"
            :aria-describedby="validationErrors[entry.key] ? `config-error-${entry.key}` : undefined"
            :class="[
              baseInputClass,
              'font-mono',
              'text-sm',
              { 'cursor-not-allowed': !entry.metadata.editable },
              { 'border-red-500 dark:border-red-500': validationErrors[entry.key] }
            ]"
            :placeholder="JSON.stringify(entry.metadata.example, null, 2) || '请输入有效的 JSON...'"
          ></textarea>
        </template>

        <!-- Validation Error -->
        <p
          v-if="validationErrors[entry.key]"
          :id="`config-error-${entry.key}`"
          class="mt-2 text-sm text-red-600 dark:text-red-400"
          role="alert"
        >
          {{ validationErrors[entry.key] }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onBeforeUnmount } from 'vue'
import { validateByType } from '@/utils/configValidation'
import type { ValidationOptions } from '@/utils/configValidation'

type ConfigValue = string | number | boolean | Record<string, any> | Array<any>

interface ConfigMetadata {
  value_type: 'string' | 'number' | 'boolean' | 'json'
  editable: boolean
  requires_restart: boolean
  description: string
  category: string
  example?: ConfigValue
}

export interface ConfigEntry {
  key: string
  value: ConfigValue
  metadata: ConfigMetadata
}

interface Props {
  modelValue: ConfigEntry[]
}

interface Emits {
  (e: 'update:modelValue', value: ConfigEntry[]): void
  (e: 'validate', status: { isValid: boolean }): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const localConfig = ref<ConfigEntry[]>([])
const validationErrors = ref<Record<string, string | null>>({})
const jsonTextValues = ref<Record<string, string>>({})
const syncingFromParent = ref(false)

const baseInputClass = 'w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white transition-all'

const jsonInputTimers = new Map<string, ReturnType<typeof setTimeout>>()
const cloneEntries = (entries: ConfigEntry[]) => JSON.parse(JSON.stringify(entries)) as ConfigEntry[]

const getEntryIndex = (key: string) => localConfig.value.findIndex(e => e.key === key)

const getValidationOptions = (key: string): ValidationOptions => {
  if (key === 'port') return { numberMin: 1, numberMax: 65535, numberAllowFloat: false }
  if (key === 'dashboard_api_key') return { allowEmptyString: true, trimString: true }
  return {}
}

const validateEntry = (entry: ConfigEntry): boolean => {
  if (!entry.metadata.editable) {
    validationErrors.value[entry.key] = null
    return true
  }

  const result = validateByType(
    entry.metadata.value_type,
    entry.value,
    getValidationOptions(entry.key)
  )

  if (!result.valid) {
    validationErrors.value[entry.key] = result.error || '验证失败'
    return false
  } else {
    validationErrors.value[entry.key] = null
    if (result.normalized !== undefined) {
      entry.value = result.normalized
    }
    return true
  }
}

const handleInputChange = (index: number) => {
  const entry = localConfig.value[index]
  validateEntry(entry)
}

const handleJsonInput = (key: string, textValue: string) => {
  jsonTextValues.value[key] = textValue
  const index = getEntryIndex(key)
  if (index === -1) return

  const existingTimer = jsonInputTimers.get(key)
  if (existingTimer) clearTimeout(existingTimer)

  const timer = setTimeout(() => {
    try {
      const parsed = JSON.parse(textValue)
      localConfig.value[index].value = parsed
      validationErrors.value[key] = null
      emit('validate', { isValid: isFormValid.value })
    } catch (err) {
      validationErrors.value[key] = 'JSON 格式无效：' + (err as Error).message
      emit('validate', { isValid: false })
    }
    jsonInputTimers.delete(key)
  }, 300)

  jsonInputTimers.set(key, timer)
}

const isFormValid = computed(() => {
  return Object.values(validationErrors.value).every(error => error === null)
})

watch(() => props.modelValue, (newValue) => {
  syncingFromParent.value = true
  localConfig.value = cloneEntries(newValue)

  localConfig.value.forEach(entry => {
    if (entry.metadata.value_type === 'json') {
      jsonTextValues.value[entry.key] = JSON.stringify(entry.value, null, 2)
    }
    validateEntry(entry)
  })
  emit('validate', { isValid: isFormValid.value })
}, { deep: true, immediate: true })

watch(localConfig, (newValue) => {
  if (syncingFromParent.value) {
    syncingFromParent.value = false
    return
  }
  emit('update:modelValue', cloneEntries(newValue))
  emit('validate', { isValid: isFormValid.value })
}, { deep: true })

onBeforeUnmount(() => {
  jsonInputTimers.forEach(timer => clearTimeout(timer))
  jsonInputTimers.clear()
})
</script>
