import { ref } from 'vue'
import { healthApi } from '@/services/api'

export function useServiceRestart() {
  const isRestarting = ref(false)
  const restartStatus = ref('')
  let pollTimer: number | null = null

  const startRestartWatcher = (
    oldBootId: string | null,
    onSuccess: () => void,
    onError: (message: string) => void,
    options: { pollInterval?: number; timeout?: number } = {}
  ) => {
    if (!oldBootId) {
      onError('无法获取服务状态，请手动刷新页面确认配置是否生效。')
      return
    }

    const { pollInterval = 1500, timeout = 30000 } = options
    const startTime = Date.now()

    isRestarting.value = true
    restartStatus.value = '正在等待服务重启...'

    const poll = async () => {
      if (Date.now() - startTime > timeout) {
        stopPolling()
        isRestarting.value = false
        onError('服务重启超时，请手动刷新页面或检查服务状态。')
        return
      }

      try {
        const health = await healthApi.checkHealth()

        if (oldBootId && health.boot_id === oldBootId) {
          restartStatus.value = `等待服务重启... (${Math.round((Date.now() - startTime) / 1000)}s)`
          pollTimer = window.setTimeout(poll, pollInterval)
          return
        }

        stopPolling()
        restartStatus.value = '服务已成功重启！正在刷新页面...'
        isRestarting.value = false
        onSuccess()
      } catch (error) {
        restartStatus.value = `正在连接服务... (${Math.round((Date.now() - startTime) / 1000)}s)`
        pollTimer = window.setTimeout(poll, pollInterval)
      }
    }

    const stopPolling = () => {
      if (pollTimer) {
        clearTimeout(pollTimer)
        pollTimer = null
      }
    }

    setTimeout(poll, pollInterval)
  }

  return {
    isRestarting,
    restartStatus,
    startRestartWatcher
  }
}
