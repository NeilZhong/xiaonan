import { ref, onMounted, onUnmounted } from 'vue'

/**
 * 近实时刷新 composable（WebSocket 轻量替代方案）
 *
 * 以固定间隔轮询回调实现「准实时」刷新；后续如需更低延迟，可在此封装内
 * 替换为 WebSocket/SSE，调用方无需改动。
 *
 * @param {Function} fetcher 异步刷新函数（返回 Promise）
 * @param {Object} options { interval, immediate }
 */
export function useRealtime(fetcher, { interval = 30000, immediate = true } = {}) {
  const loading = ref(false)
  const lastUpdated = ref(null)
  const error = ref(null)
  let timer = null
  let stopped = false

  async function refresh() {
    if (stopped || typeof fetcher !== 'function') return
    loading.value = true
    try {
      await fetcher()
      lastUpdated.value = new Date()
      error.value = null
    } catch (e) {
      error.value = e
      // 轮询失败不应打断用户体验，仅记录
      console.warn('useRealtime 刷新失败:', e)
    } finally {
      loading.value = false
    }
  }

  function start() {
    stopped = false
    if (!timer) timer = setInterval(refresh, interval)
  }

  function stop() {
    stopped = true
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  onMounted(() => {
    if (immediate) refresh()
    start()
  })
  onUnmounted(stop)

  return { loading, lastUpdated, error, refresh, start, stop }
}
