<script setup>
/**
 * ★ 案件独立工作区 Tab — 证据/材料/研判报告统一存储视图
 * POLICE_REQUIREMENTS §案件工作区
 */
import { onMounted, ref, computed, watch } from 'vue'
import { policeWorkspaceApi } from '@/apis/police_api'
import { apiGet } from '@/apis/base'
import { message, Upload } from 'ant-design-vue'
import {
  UploadOutlined, FileTextOutlined, FileImageOutlined, FileOutlined,
  DownloadOutlined, DeleteOutlined, FolderOpenOutlined,
} from '@ant-design/icons-vue'

const props = defineProps({ caseId: { type: Number, required: true } })

const loading = ref(false)
const data = ref(null) // { workspace, files, stats }

const categoryMeta = {
  evidence: { label: '证据', icon: FileTextOutlined, uploadable: false, hint: '请使用「证据」标签页上传并审核签名' },
  materials: { label: '材料', icon: FileOutlined, uploadable: true, hint: '调证文书、笔录原件等办案材料' },
  reports: { label: '研判报告', icon: FileTextOutlined, uploadable: true, hint: '民警生成的研判/分析产物' },
}
const categoryOrder = ['evidence', 'materials', 'reports']

const groupedFiles = computed(() => {
  const groups = { evidence: [], materials: [], reports: [], other: [] }
  for (const f of data.value?.files || []) {
    groups[f.category] = groups[f.category] || []
    groups[f.category].push(f)
  }
  return groups
})

const stats = computed(() => data.value?.stats || {})
const workspaceInfo = computed(() => data.value?.workspace || {})

function formatSize(bytes) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let v = bytes
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++ }
  return `${v.toFixed(1)} ${units[i]}`
}

async function loadData() {
  loading.value = true
  try {
    const res = await policeWorkspaceApi.get(props.caseId)
    data.value = res.data
  } catch (e) {
    message.error('加载工作区失败')
  } finally {
    loading.value = false
  }
}

function fileIcon(type) {
  return categoryMeta[type]?.icon || FileOutlined
}

function customRequest({ file, onSuccess, onError }, category) {
  policeWorkspaceApi.upload(props.caseId, category, file)
    .then(() => { onSuccess({}, file); message.success(`${file.name} 上传成功`); loadData() })
    .catch(() => { onError(); message.error('上传失败') })
}

async function handleDownload(file) {
  try {
    const url = `/api/police/workspaces/${props.caseId}/download?object_name=${encodeURIComponent(file.object_name)}`
    const resp = await apiGet(url, {}, true, 'blob')
    const blob = await resp.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = file.name
    a.click()
    URL.revokeObjectURL(a.href)
  } catch (e) {
    message.error('下载失败')
  }
}

async function handleDelete(file) {
  try {
    await policeWorkspaceApi.remove(props.caseId, file.object_name)
    message.success('已删除')
    await loadData()
  } catch (e) {
    message.error('删除失败')
  }
}

onMounted(loadData)
watch(() => props.caseId, loadData)
</script>

<template>
  <div class="workspace-tab">
    <!-- 工作区概览 -->
    <div class="ws-overview" v-if="workspaceInfo.storage_prefix">
      <div class="ws-overview-icon"><FolderOpenOutlined /></div>
      <div class="ws-overview-body">
        <div class="ws-overview-title">案件独立工作区</div>
        <div class="ws-overview-path">
          <span class="ws-label">存储路径</span>
          <code>{{ workspaceInfo.storage_prefix }}</code>
          <a-tag size="small">MinIO: {{ workspaceInfo.storage_bucket }}</a-tag>
        </div>
        <div class="ws-stats">
          <div class="ws-stat"><span class="ws-stat-num">{{ stats.evidence_count || 0 }}</span><span class="ws-stat-label">证据</span></div>
          <div class="ws-stat"><span class="ws-stat-num">{{ stats.material_count || 0 }}</span><span class="ws-stat-label">材料</span></div>
          <div class="ws-stat"><span class="ws-stat-num">{{ stats.report_count || 0 }}</span><span class="ws-stat-label">研判报告</span></div>
          <div class="ws-stat"><span class="ws-stat-num">{{ formatSize(stats.total_size) }}</span><span class="ws-stat-label">总大小</span></div>
        </div>
      </div>
    </div>

    <a-spin :spinning="loading">
      <div class="ws-categories">
        <div v-for="cat in categoryOrder" :key="cat" class="ws-category">
          <div class="ws-category-head">
            <component :is="categoryMeta[cat].icon" class="ws-category-icon" />
            <span class="ws-category-label">{{ categoryMeta[cat].label }}</span>
            <span class="ws-category-count">{{ (groupedFiles[cat] || []).length }}</span>
            <a-upload
              v-if="categoryMeta[cat].uploadable"
              :custom-request="(o) => customRequest(o, cat)"
              :show-upload-list="false"
            >
              <a-button type="primary" size="small">
                <template #icon><UploadOutlined /></template>
                上传{{ categoryMeta[cat].label }}
              </a-button>
            </a-upload>
          </div>
          <div class="ws-category-hint" v-if="categoryMeta[cat].hint">{{ categoryMeta[cat].hint }}</div>

          <div class="ws-file-grid" v-if="(groupedFiles[cat] || []).length">
            <div v-for="f in groupedFiles[cat]" :key="f.object_name" class="ws-file-card">
              <div class="ws-file-icon"><component :is="fileIcon(cat)" /></div>
              <div class="ws-file-info">
                <div class="ws-file-name" :title="f.name">{{ f.name }}</div>
                <div class="ws-file-meta">
                  <span>{{ formatSize(f.size) }}</span>
                  <span v-if="f.last_modified">{{ f.last_modified.substring(0, 10) }}</span>
                </div>
              </div>
              <div class="ws-file-actions">
                <a-button type="link" size="small" @click="handleDownload(f)">
                  <template #icon><DownloadOutlined /></template>
                </a-button>
                <a-button type="link" size="small" danger @click="handleDelete(f)">
                  <template #icon><DeleteOutlined /></template>
                </a-button>
              </div>
            </div>
          </div>
          <a-empty v-else :description="`暂无${categoryMeta[cat].label}`" style="padding: 20px" />
        </div>
      </div>
    </a-spin>
  </div>
</template>

<style scoped>
.workspace-tab { padding: 12px 0; }

/* 概览 */
.ws-overview {
  display: flex; gap: 14px; align-items: flex-start;
  padding: 16px; border: 1px solid var(--gray-50, #e2e8f0); border-radius: 12px;
  background: var(--gray-10, #f7fafc); margin-bottom: 18px;
}
.ws-overview-icon { font-size: 30px; color: var(--main-color, #24839b); padding-top: 2px; }
.ws-overview-body { flex: 1; min-width: 0; }
.ws-overview-title { font-size: 15px; font-weight: 600; margin-bottom: 6px; }
.ws-overview-path { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12px; color: var(--gray-600, #4a5568); margin-bottom: 10px; }
.ws-label { color: var(--gray-500, #718096); }
.ws-overview-path code { background: var(--gray-0, #fff); padding: 2px 8px; border-radius: 6px; border: 1px solid var(--gray-50, #e2e8f0); font-family: monospace; }
.ws-stats { display: flex; gap: 24px; }
.ws-stat { display: flex; flex-direction: column; }
.ws-stat-num { font-size: 18px; font-weight: 600; color: var(--main-color, #24839b); }
.ws-stat-label { font-size: 12px; color: var(--gray-500, #718096); }

/* 分类 */
.ws-category { margin-bottom: 18px; }
.ws-category-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.ws-category-icon { font-size: 18px; color: var(--main-color, #24839b); }
.ws-category-label { font-size: 14px; font-weight: 600; }
.ws-category-count {
  font-size: 12px; color: var(--gray-500, #718096); background: var(--gray-10, #f7fafc);
  border-radius: 10px; padding: 0 8px; min-width: 20px; text-align: center;
}
.ws-category-head .ant-upload { margin-left: auto; }
.ws-category-hint { font-size: 12px; color: var(--gray-400, #a0aec0); margin-bottom: 8px; }

/* 文件网格 */
.ws-file-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }
.ws-file-card {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 14px; border: 1px solid var(--gray-50, #e2e8f0); border-radius: 10px;
  background: var(--gray-0, #fff); transition: box-shadow 0.15s;
}
.ws-file-card:hover { box-shadow: 0 2px 6px rgba(0,0,0,0.05); }
.ws-file-icon { font-size: 26px; color: var(--main-color, #24839b); padding-top: 2px; }
.ws-file-info { flex: 1; min-width: 0; }
.ws-file-name { font-size: 14px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px; }
.ws-file-meta { display: flex; gap: 10px; font-size: 12px; color: var(--gray-500, #718096); }
.ws-file-actions { flex-shrink: 0; display: flex; gap: 2px; }
</style>
