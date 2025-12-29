<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-opacity duration-200"
      leave-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <div
        v-if="visible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
        @click.self="handleClose"
        @keydown.esc="handleClose"
      >
        <div
          ref="modalRef"
          class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md mx-4 w-full shadow-xl"
          role="dialog"
          aria-modal="true"
          aria-labelledby="auth-modal-title"
        >
          <!-- 标题 -->
          <div class="flex items-center justify-between mb-4">
            <h3
              id="auth-modal-title"
              class="text-lg font-medium text-gray-900 dark:text-white"
            >
              🔐 配置编辑认证
            </h3>
            <button
              @click="handleClose"
              :disabled="loading"
              class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="关闭对话框"
            >
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fill-rule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clip-rule="evenodd"
                />
              </svg>
            </button>
          </div>

          <!-- 说明文本 -->
          <p class="text-sm text-gray-600 dark:text-gray-400 mb-6">
            为了保护配置安全，编辑配置需要提供 DASHBOARD_API_KEY 进行认证。
          </p>

          <!-- 表单 -->
          <form @submit.prevent="handleSubmit">
            <div class="mb-4">
              <label
                for="api-key-input"
                class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                API Key
              </label>
              <div class="relative">
                <input
                  id="api-key-input"
                  ref="inputRef"
                  v-model="apiKey"
                  :type="showPassword ? 'text' : 'password'"
                  :disabled="loading"
                  :aria-invalid="hasError"
                  :aria-describedby="activeErrorId"
                  class="w-full px-4 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                  :class="{
                    'border-red-500 dark:border-red-500': validationError
                  }"
                  placeholder="请输入 DASHBOARD_API_KEY"
                  autocomplete="off"
                  @input="clearValidationError"
                />
                <!-- 显示/隐藏密码切换按钮 -->
                <button
                  type="button"
                  @click="showPassword = !showPassword"
                  :disabled="loading"
                  :aria-pressed="showPassword"
                  class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                >
                  <svg
                    v-if="!showPassword"
                    class="w-5 h-5"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                    <path
                      fill-rule="evenodd"
                      d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
                      clip-rule="evenodd"
                    />
                  </svg>
                  <svg v-else class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fill-rule="evenodd"
                      d="M3.707 2.293a1 1 0 00-1.414 1.414l14 14a1 1 0 001.414-1.414l-1.473-1.473A10.014 10.014 0 0019.542 10C18.268 5.943 14.478 3 10 3a9.958 9.958 0 00-4.512 1.074l-1.78-1.781zm4.261 4.26l1.514 1.515a2.003 2.003 0 012.45 2.45l1.514 1.514a4 4 0 00-5.478-5.478z"
                      clip-rule="evenodd"
                    />
                    <path
                      d="M12.454 16.697L9.75 13.992a4 4 0 01-3.742-3.741L2.335 6.578A9.98 9.98 0 00.458 10c1.274 4.057 5.065 7 9.542 7 .847 0 1.669-.105 2.454-.303z"
                    />
                  </svg>
                </button>
              </div>
              <!-- 验证错误提示 -->
              <p
                v-if="validationError"
                id="api-key-validation-error"
                class="mt-2 text-sm text-red-600 dark:text-red-400"
              >
                {{ validationError }}
              </p>
            </div>

            <!-- 错误提示 -->
            <div
              v-if="errorMessage"
              id="api-key-server-error"
              class="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
            >
              <div class="flex items-start">
                <svg
                  class="w-5 h-5 text-red-600 dark:text-red-400 mr-2 flex-shrink-0 mt-0.5"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fill-rule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clip-rule="evenodd"
                  />
                </svg>
                <p class="text-sm text-red-800 dark:text-red-200">
                  {{ errorMessage }}
                </p>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="flex justify-end space-x-3">
              <button
                type="button"
                @click="handleClose"
                :disabled="loading"
                class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                取消
              </button>
              <button
                type="submit"
                :disabled="loading || !apiKey.trim()"
                class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                <svg
                  v-if="loading"
                  class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    class="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="4"
                  ></circle>
                  <path
                    class="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                {{ loading ? '验证中...' : '确认' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'

interface Props {
  visible: boolean
  loading?: boolean
  error?: string | null
}

interface Emits {
  (e: 'authenticate', apiKey: string): void
  (e: 'close'): void
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  error: null
})

const emit = defineEmits<Emits>()

const apiKey = ref('')
const showPassword = ref(false)
const validationError = ref<string | null>(null)
const errorMessage = ref<string | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
const modalRef = ref<HTMLDivElement | null>(null)

const hasError = computed(() => !!validationError.value || !!errorMessage.value)
const activeErrorId = computed(() => {
  if (validationError.value) return 'api-key-validation-error'
  if (errorMessage.value) return 'api-key-server-error'
  return undefined
})

watch(
  () => props.visible,
  async (newValue) => {
    if (newValue) {
      await nextTick()
      inputRef.value?.focus()
      document.addEventListener('keydown', handleKeydown)
    } else {
      apiKey.value = ''
      showPassword.value = false
      validationError.value = null
      errorMessage.value = null
      document.removeEventListener('keydown', handleKeydown)
    }
  }
)

watch(
  () => props.error,
  (newError) => {
    errorMessage.value = newError
  }
)

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    handleClose()
    return
  }

  if (e.key === 'Tab' && modalRef.value) {
    e.preventDefault()

    const focusableElements = [
      ...modalRef.value.querySelectorAll<HTMLElement>(
        'a[href], button, input, textarea, select, [tabindex]:not([tabindex="-1"])'
      ),
    ].filter((el) => !el.hasAttribute('disabled'))

    if (focusableElements.length === 0) return

    const currentIndex = focusableElements.indexOf(
      document.activeElement as HTMLElement
    )

    let nextIndex = 0
    if (e.shiftKey) {
      nextIndex = currentIndex > 0 ? currentIndex - 1 : focusableElements.length - 1
    } else {
      nextIndex = currentIndex < focusableElements.length - 1 ? currentIndex + 1 : 0
    }
    focusableElements[nextIndex]?.focus()
  }
}

const clearValidationError = () => {
  validationError.value = null
  errorMessage.value = null
}

const handleSubmit = () => {
  const trimmedKey = apiKey.value.trim()

  if (!trimmedKey) {
    validationError.value = 'API Key 不能为空'
    return
  }

  if (trimmedKey.length < 8) {
    validationError.value = 'API Key 长度至少为 8 个字符'
    return
  }

  emit('authenticate', trimmedKey)
}

const handleClose = () => {
  if (!props.loading) {
    emit('close')
  }
}
</script>
