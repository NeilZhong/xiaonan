<template>
  <div class="file-viewer-preview" :class="{ 'is-full-height': fullHeight }">
    <div v-if="loadError" class="file-viewer-error">
      <AlertTriangle :size="20" />
      <span>文档预览加载失败，请下载后查看。</span>
    </div>
    <!--
      Vue3 的 <file-viewer> 只认 url / file / options 三个 prop，filename 是 Vue2/React 的参数，Vue3 直接忽略。
      因此必须用 :file 传入「带扩展名的 File」对象，库才能从 file.name 识别 .docx/.xlsx 等格式；
      若传 :url="blob:..."（无扩展名）会被判为不支持，弹出库自带的“不支持当前文件格式”提示。
    -->
    <file-viewer
      v-else-if="fileObject"
      :file="fileObject"
      :options="viewerOptions"
      class="file-viewer-host"
      @viewer-event="onViewerEvent"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
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
const fileObject = ref(null)
const loadError = ref(false)

const buildFile = () => {
  loadError.value = false
  try {
    // 包装成带扩展名的 File：库依据 file.name 的扩展名选择 renderer。
    fileObject.value = props.filename
      ? new File([props.blob], props.filename, { type: props.blob.type || '' })
      : props.blob
  } catch (error) {
    console.warn('构建 File Viewer 文件对象失败:', error)
    loadError.value = true
  }
}

watch([() => props.blob, () => props.filename], buildFile, { immediate: true })

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
