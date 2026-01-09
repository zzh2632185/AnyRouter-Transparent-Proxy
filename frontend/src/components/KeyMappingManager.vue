<template>
  <div class="space-y-4">
    <!-- 标题和添加按钮 -->
    <div class="flex items-center justify-between">
      <div>
        <h4 class="text-base font-medium text-gray-900 dark:text-white">
          Key-目标服务器映射
        </h4>
        <p class="text-sm text-gray-500 dark:text-gray-400">
          根据请求中的 API Key 动态路由到不同的目标服务器
        </p>
      </div>
      <button
        v-if="isAuthenticated"
        @click="showAddTargetModal = true"
        class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors flex items-center"
      >
        <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd"/>
        </svg>
        添加目标
      </button>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="flex items-center justify-center py-8">
      <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
      <span class="ml-2 text-gray-600 dark:text-gray-400">加载中...</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="mappings.length === 0" class="text-center py-8 text-gray-500 dark:text-gray-400">
      <svg class="w-12 h-12 mx-auto mb-3 text-gray-300 dark:text-gray-600" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" clip-rule="evenodd"/>
      </svg>
      <p>暂无映射配置</p>
      <p class="text-sm mt-1">未匹配的 Key 将使用默认目标服务器地址</p>
    </div>

    <!-- 映射列表 -->
    <div v-else class="space-y-3">
      <div
        v-for="mapping in mappings"
        :key="mapping.target_url"
        class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden"
      >
        <!-- 目标服务器头部 -->
        <div class="bg-gray-50 dark:bg-gray-800 px-4 py-3 flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <div class="flex-shrink-0 w-2 h-2 bg-green-500 rounded-full"></div>
            <div>
              <div class="font-medium text-gray-900 dark:text-white">
                {{ mapping.target_url }}
              </div>
              <div class="text-sm text-gray-500 dark:text-gray-400">
                {{ mapping.keys.length }} 个关联 Key
              </div>
            </div>
          </div>
          <div v-if="isAuthenticated" class="flex items-center space-x-2">
            <button
              @click="editingTarget = mapping"
              class="p-1.5 text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 transition-colors"
              title="编辑"
            >
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/>
              </svg>
            </button>
            <button
              @click="handleRemoveTarget(mapping.target_url)"
              class="p-1.5 text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 transition-colors"
              title="删除"
            >
              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Keys 列表 -->
        <div class="px-4 py-3 space-y-2">
          <div v-if="mapping.keys.length === 0" class="text-sm text-gray-500 dark:text-gray-400 italic">
            暂无关联 Key
          </div>
          <div v-else class="flex flex-wrap gap-2">
            <div
              v-for="key in mapping.keys"
              :key="key"
              class="inline-flex items-center px-2.5 py-1 bg-gray-100 dark:bg-gray-700 rounded-md text-sm"
            >
              <span class="font-mono text-gray-700 dark:text-gray-300">
                {{ isAuthenticated ? key : maskKey(key) }}
              </span>
              <button
                v-if="isAuthenticated"
                @click="handleRemoveKey(mapping.target_url, key)"
                class="ml-1.5 text-gray-400 hover:text-red-500 transition-colors"
              >
                <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- 添加 Key 输入框 -->
          <div v-if="isAuthenticated" class="flex items-center space-x-2 mt-2">
            <input
              v-model="newKeyInputs[mapping.target_url]"
              type="text"
              placeholder="输入新的 API Key"
              class="flex-1 px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              @keyup.enter="handleAddKey(mapping.target_url)"
            />
            <button
              @click="handleAddKey(mapping.target_url)"
              :disabled="!newKeyInputs[mapping.target_url]?.trim()"
              class="px-3 py-1.5 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white text-sm rounded-md transition-colors"
            >
              添加
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 统计信息 -->
    <div v-if="!loading && mappings.length > 0" class="text-sm text-gray-500 dark:text-gray-400 pt-2 border-t border-gray-200 dark:border-gray-700">
      共 {{ mappings.length }} 个目标服务器，{{ totalKeys }} 个 Key 映射
    </div>

    <!-- 添加目标服务器弹窗 -->
    <div v-if="showAddTargetModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4">
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">
            添加目标服务器
          </h3>
        </div>
        <div class="px-6 py-4 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              目标服务器地址 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="newTargetUrl"
              type="url"
              placeholder="https://api.example.com"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              初始 Keys（可选，每行一个）
            </label>
            <textarea
              v-model="newTargetKeys"
              rows="3"
              placeholder="sk-xxx1&#10;sk-xxx2"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
            ></textarea>
          </div>
        </div>
        <div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end space-x-3">
          <button
            @click="showAddTargetModal = false"
            class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            @click="handleAddTarget"
            :disabled="!newTargetUrl.trim() || addingTarget"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg transition-colors"
          >
            {{ addingTarget ? '添加中...' : '添加' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 编辑目标服务器弹窗 -->
    <div v-if="editingTarget" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4">
        <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white">
            编辑目标服务器
          </h3>
        </div>
        <div class="px-6 py-4 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              目标服务器地址
            </label>
            <input
              v-model="editTargetUrl"
              type="url"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Keys（每行一个）
            </label>
            <textarea
              v-model="editTargetKeys"
              rows="5"
              class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg dark:bg-gray-700 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
            ></textarea>
          </div>
        </div>
        <div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end space-x-3">
          <button
            @click="editingTarget = null"
            class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            @click="handleUpdateTarget"
            :disabled="!editTargetUrl.trim() || updatingTarget"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg transition-colors"
          >
            {{ updatingTarget ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { keyMappingApi } from '@/services/api'
import type { TargetMapping } from '@/types'

const props = defineProps<{
  isAuthenticated: boolean
}>()

const emit = defineEmits<{
  (e: 'error', message: string): void
  (e: 'success', message: string): void
}>()

const loading = ref(false)
const mappings = ref<TargetMapping[]>([])
const newKeyInputs = ref<Record<string, string>>({})

const showAddTargetModal = ref(false)
const newTargetUrl = ref('')
const newTargetKeys = ref('')
const addingTarget = ref(false)

const editingTarget = ref<TargetMapping | null>(null)
const editTargetUrl = ref('')
const editTargetKeys = ref('')
const updatingTarget = ref(false)

const totalKeys = computed(() => mappings.value.reduce((sum, m) => sum + m.keys.length, 0))

const maskKey = (key: string): string => {
  if (key.length <= 8) return '****'
  return key.substring(0, 8) + '...'
}

const loadMappings = async () => {
  loading.value = true
  try {
    if (props.isAuthenticated) {
      const response = await keyMappingApi.getMappingsPrivate()
      mappings.value = response.mappings
    } else {
      const response = await keyMappingApi.getMappings()
      mappings.value = response.mappings.map(m => ({
        target_url: m.target_url,
        keys: m.keys_preview
      }))
    }
  } catch (err: any) {
    emit('error', err?.message || '加载映射失败')
  } finally {
    loading.value = false
  }
}

const handleAddTarget = async () => {
  if (!newTargetUrl.value.trim()) return

  addingTarget.value = true
  try {
    const keys = newTargetKeys.value
      .split('\n')
      .map(k => k.trim())
      .filter(k => k)

    await keyMappingApi.addTarget({
      target_url: newTargetUrl.value.trim(),
      keys
    })

    emit('success', '目标服务器添加成功')
    showAddTargetModal.value = false
    newTargetUrl.value = ''
    newTargetKeys.value = ''
    await loadMappings()
  } catch (err: any) {
    emit('error', err?.message || '添加失败')
  } finally {
    addingTarget.value = false
  }
}

const handleRemoveTarget = async (targetUrl: string) => {
  if (!confirm(`确定要删除目标服务器 ${targetUrl} 吗？\n关联的所有 Key 映射也将被删除。`)) return

  try {
    await keyMappingApi.removeTarget(targetUrl)
    emit('success', '目标服务器已删除')
    await loadMappings()
  } catch (err: any) {
    emit('error', err?.message || '删除失败')
  }
}

const handleUpdateTarget = async () => {
  if (!editingTarget.value || !editTargetUrl.value.trim()) return

  updatingTarget.value = true
  try {
    const keys = editTargetKeys.value
      .split('\n')
      .map(k => k.trim())
      .filter(k => k)

    await keyMappingApi.updateTarget(editingTarget.value.target_url, {
      new_target_url: editTargetUrl.value !== editingTarget.value.target_url ? editTargetUrl.value : undefined,
      keys
    })

    emit('success', '目标服务器已更新')
    editingTarget.value = null
    await loadMappings()
  } catch (err: any) {
    emit('error', err?.message || '更新失败')
  } finally {
    updatingTarget.value = false
  }
}

const handleAddKey = async (targetUrl: string) => {
  const key = newKeyInputs.value[targetUrl]?.trim()
  if (!key) return

  try {
    await keyMappingApi.addKeyToTarget(targetUrl, key)
    emit('success', 'Key 已添加')
    newKeyInputs.value[targetUrl] = ''
    await loadMappings()
  } catch (err: any) {
    emit('error', err?.message || '添加 Key 失败')
  }
}

const handleRemoveKey = async (targetUrl: string, key: string) => {
  if (!confirm(`确定要删除 Key "${key}" 吗？`)) return

  try {
    await keyMappingApi.removeKeyFromTarget(targetUrl, key)
    emit('success', 'Key 已删除')
    await loadMappings()
  } catch (err: any) {
    emit('error', err?.message || '删除 Key 失败')
  }
}

watch(() => editingTarget.value, (target) => {
  if (target) {
    editTargetUrl.value = target.target_url
    editTargetKeys.value = target.keys.join('\n')
  }
})

watch(() => props.isAuthenticated, () => {
  loadMappings()
})

onMounted(() => {
  loadMappings()
})

defineExpose({
  reload: loadMappings
})
</script>
