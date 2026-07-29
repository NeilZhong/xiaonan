<script setup>
/**
 * ★ 证据管理 Tab — 案件详情内嵌
 */
import { onMounted, ref, watch } from 'vue'
import { policeEvidenceApi } from '@/apis/police_api'
import { message, Upload } from 'ant-design-vue'
import { UploadOutlined, FileTextOutlined, FileImageOutlined, FileOutlined } from '@ant-design/icons-vue'

const props = defineProps({ caseId: { type: Number, required: true } })

const loading = ref(false)
const evidenceList = ref([])
const total = ref(0)
const filterType = ref(undefined)

const typeText = {
  transcript: '笔录', bank_flow: '银行流水', screenshot: '截图', audio: '音频',
  video: '视频', document: '文档', report: '报告', other: '其他',
}

const typeIcon = {
  transcript: FileTextOutlined, bank_flow: FileTextOutlined, screenshot: FileImageOutlined,
  document: FileOutlined, report: FileTextOutlined, audio: FileOutlined, video: FileOutlined, other: FileOutlined,
}

async function loadData() {
  loading.value = true
  try {
    const res = await policeEvidenceApi.list(props.caseId, { evidence_type: filterType.value })
    evidenceList.value = res.data?.items || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

async function handleUpload({ file }) {
  if (file.status === 'done') {
    message.success(`${file.name} 上传成功`)
    await loadData()
  } else if (file.status === 'error') {
    message.error(`${file.name} 上传失败`)
  }
}

function customRequest({ file, onSuccess, onError }) {
  policeEvidenceApi.upload(props.caseId, file, { evidence_type: filterType.value || 'document' })
    .then(() => onSuccess({}, file))
    .catch(err => onError(err))
}

function fileIcon(type) {
  return typeIcon[type] || FileOutlined
}

async function reviewEvidence(id) {
  try {
    await policeEvidenceApi.review(id)
    message.success('审核签名成功')
    await loadData()
  } catch (e) {
    message.error('审核失败')
  }
}

onMounted(loadData)
watch(() => props.caseId, loadData)
</script>

<template>
  <div class="evidence-tab">
    <div class="evidence-toolbar">
      <a-select v-model:value="filterType" placeholder="全部类型" style="width: 140px" allow-clear @change="loadData">
        <a-select-option v-for="(label, value) in typeText" :key="value" :value="value">{{ label }}</a-select-option>
      </a-select>
      <a-upload :custom-request="customRequest" :show-upload-list="false" @change="handleUpload">
        <a-button type="primary" size="small">
          <template #icon><UploadOutlined /></template>
          上传证据
        </a-button>
      </a-upload>
    </div>

    <div class="evidence-grid" v-if="evidenceList.length">
      <div v-for="ev in evidenceList" :key="ev.id" class="evidence-card">
        <div class="evidence-icon">
          <component :is="fileIcon(ev.type)" />
        </div>
        <div class="evidence-info">
          <div class="evidence-name" :title="ev.name">{{ ev.name }}</div>
          <div class="evidence-meta">
            <a-tag size="small">{{ typeText[ev.type] || ev.type }}</a-tag>
            <span v-if="ev.file_size">{{ (ev.file_size / 1024).toFixed(1) }} KB</span>
            <span>{{ ev.created_at?.substring(0, 10) }}</span>
          </div>
          <div class="evidence-hash" v-if="ev.file_hash">
            <a-tooltip :title="ev.file_hash">
              <span>SHA-256: {{ ev.file_hash.substring(0, 16) }}...</span>
            </a-tooltip>
          </div>
        </div>
        <div class="evidence-actions">
          <a-tag v-if="ev.signed_hash" color="success" size="small">已签名</a-tag>
          <a-button v-else type="link" size="small" @click="reviewEvidence(ev.id)">审核签名</a-button>
        </div>
      </div>
    </div>
    <a-empty v-else description="暂无证据材料" style="padding: 40px" />
  </div>
</template>

<style scoped>
.evidence-tab { padding: 12px 0; }
.evidence-toolbar { display: flex; justify-content: space-between; margin-bottom: 12px; }
.evidence-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }
.evidence-card {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 14px; border: 1px solid var(--gray-50, #e2e8f0); border-radius: 10px;
  background: var(--gray-0, #fff); transition: box-shadow 0.15s;
}
.evidence-card:hover { box-shadow: 0 2px 6px rgba(0,0,0,0.05); }
.evidence-icon { font-size: 28px; color: var(--main-color, #24839b); padding-top: 2px; }
.evidence-info { flex: 1; min-width: 0; }
.evidence-name { font-size: 14px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px; }
.evidence-meta { display: flex; gap: 8px; font-size: 12px; color: var(--gray-500, #718096); align-items: center; }
.evidence-hash { font-size: 11px; color: var(--gray-400, #a0aec0); margin-top: 4px; font-family: monospace; }
.evidence-actions { flex-shrink: 0; }
</style>
