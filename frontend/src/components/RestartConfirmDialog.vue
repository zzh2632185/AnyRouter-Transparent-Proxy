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
          class="relative bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md mx-4 w-full shadow-xl"
          role="dialog"
          aria-modal="true"
          aria-labelledby="restart-dialog-title"
          aria-describedby="restart-dialog-description"
          tabindex="-1"
        >
          <!-- 标题区域 -->
          <div class="flex items-start mb-4">
            <div
              class="flex-shrink-0 w-12 h-12 rounded-full bg-yellow-100 dark:bg-yellow-900/30 flex items-center justify-center"
            >
              <svg
                class="w-6 h-6 text-yellow-600 dark:text-yellow-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <div class="ml-4 flex-1">
              <h3
                id="restart-dialog-title"
                class="text-lg font-medium text-gray-900 dark:text-white"
              >
                需要重启服务
              </h3>
              <button
                type="button"
                @click="handleClose"
                class="absolute top-4 right-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
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
          </div>

          <!-- 说明文本 -->
          <div id="restart-dialog-description" class="mb-6 ml-16">
            <p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
              配置已成功保存，但需要重启代理服务才能使更改生效。
            </p>
            <div
              class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md p-3"
            >
              <p class="text-sm text-blue-800 dark:text-blue-300 font-medium mb-1">
                ℹ️ 重启说明
              </p>
              <ul class="text-sm text-blue-700 dark:text-blue-400 space-y-1 ml-5 list-disc">
                <li>重启过程约需 3-5 秒</li>
                <li>重启期间代理服务将暂时不可用</li>
                <li>建议在流量较少时进行重启</li>
              </ul>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="flex items-center justify-end space-x-3 ml-16">
            <button
              type="button"
              @click="handleLater"
              class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            >
              稍后重启
            </button>
            <button
              type="button"
              ref="confirmButtonRef"
              @click="handleConfirm"
              class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
            >
              立即重启
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'

interface Props {
  visible: boolean
}

interface Emits {
  (e: 'confirm'): void
  (e: 'later'): void
  (e: 'close'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const modalRef = ref<HTMLDivElement | null>(null)
const confirmButtonRef = ref<HTMLButtonElement | null>(null)
const previousActiveElement = ref<HTMLElement | null>(null)

watch(
  () => props.visible,
  async (newValue) => {
    if (newValue) {
      previousActiveElement.value = document.activeElement as HTMLElement
      await nextTick()
      confirmButtonRef.value?.focus()
      document.addEventListener('keydown', handleKeydown)
    } else {
      document.removeEventListener('keydown', handleKeydown)
      previousActiveElement.value?.focus()
      previousActiveElement.value = null
    }
  }
)

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown)
})

const handleKeydown = (e: KeyboardEvent) => {
  if (e.key === 'Tab' && modalRef.value) {
    if (!modalRef.value.contains(document.activeElement)) {
      return
    }

    e.preventDefault()

    const focusableElements = [
      ...modalRef.value.querySelectorAll<HTMLElement>(
        'a[href], button, input, textarea, select, [tabindex]:not([tabindex="-1"])'
      ),
    ].filter((el) => !el.hasAttribute('disabled'))

    if (focusableElements.length === 0) return

    let currentIndex = focusableElements.indexOf(
      document.activeElement as HTMLElement
    )

    if (currentIndex === -1) {
      currentIndex = 0
    }

    let nextIndex = 0
    if (e.shiftKey) {
      nextIndex = currentIndex > 0 ? currentIndex - 1 : focusableElements.length - 1
    } else {
      nextIndex = currentIndex < focusableElements.length - 1 ? currentIndex + 1 : 0
    }
    focusableElements[nextIndex]?.focus()
  }
}

const handleConfirm = () => {
  emit('confirm')
}

const handleLater = () => {
  emit('later')
}

const handleClose = () => {
  emit('close')
}
</script>
