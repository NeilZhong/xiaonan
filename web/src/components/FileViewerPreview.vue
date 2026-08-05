<template>
  <div class="file-viewer-preview" :class="{ 'is-full-height': fullHeight }">
    <div v-if="loadError" class="file-viewer-error">
      <AlertTriangle :size="20" />
      <span>文档预览加载失败，请下载后查看。</span>
    </div>
    <file-viewer
      v-else-if="objectUrl"
      :url="objectUrl"
      :filename="filename"
      :options="viewerOptions"
      class="file-viewer-host"
      @viewer-event="onViewerEvent"
    />
  </div>
</template>

<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { AlertTriangle } from 'lucide-vue-next'
import { FileViewer } from '@file-viewer/vue3'
import officePreset from '@file-viewer/preset-office'
import { useThemeStore } from '@/stores/theme'

const props = defineProps({
  blob: { type: Blob, required: true },
  filename: { type: String, default: '' },
  fullHeight: { type: Boolean, default: false }
})

const themeStore = useThemeStore()
const objectUrl = ref('')
const loadError = ref(false)

const buildObjectUrl = () => {
  if (objectUrl.value) {
    window.URL.revokeObjectURL(objectUrl.value)
    objectUrl.value = ''
  }
  loadError.value = false
  try {
    const source = props.filename ? new File([props.blob], props.filename) : props.blob
    objectUrl.value = window.URL.createObjectURL(source)
  } catch (error) {
    console.warn('创建 File Viewer 对象 URL 失败:', error)
    loadError.value = true
  }
}

watch([() => props.blob, () => props.filename], buildObjectUrl, { immediate: true })

onUnmounted(() => {
  if (objectUrl.value) window.URL.revokeObjectURL(objectUrl.value)
})

const viewerOptions = computed(() => ({
  preset: officePreset,
  rendererMode: 'replace',
  theme: themeStore.isDark ? 'dark' : 'light',
  toolbar: { position: 'bottom-right' },
  search: { enabled: true }
}))

const onViewerEvent = (event) => {
  if (event?.type === 'error' || event?.reason === 'load-failed') {
    loadError.value = true
  }
}
</script>

<style scoped lang="less">
.file-viewer-preview {
  position: relative;
  width: 100%;
  min-height: 300px;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.file-viewer-preview.is-full-height {
  height: 100%;
  min-height: 0;
}

.file-viewer-host {
  flex: 1 1 auto;
  min-height: 0;
  width: 100%;
  border: none;
  background: var(--gray-0);
}

.file-viewer-error {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 100%;
  min-height: 240px;
  padding: 24px;
  color: var(--gray-600);
  font-size: 14px;
  line-height: 1.6;
  text-align: center;
}
</style>
