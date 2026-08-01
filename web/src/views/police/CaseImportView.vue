<script setup>
/**
 * ★ 笔录智能导入 — 上传/粘贴笔录 → AI 分析 → 民警确认 → 一键建案并生成任务
 * 对应 POLICE_REQUIREMENTS Phase 2：笔录分析智能体 + 案件智能创建
 */
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { UploadOutlined, FileTextOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { apiPost } from '@/apis/base'

const router = useRouter()

const uploadFile = ref(null)
const pasteText = ref('')
const analyzing = ref(false)
const confirming = ref(false)
const draft = ref(null) // 原始 AI 草稿（含 victim/suspects/key_facts 等只读字段）

// 可编辑的案件概览表单
const overview = reactive({
  title: '',
  case_type: 'fraud',
  priority: 'medium',
  incident_date: '',
  incident_location: '',
  total_amount: null,
  summary: '',
})

// 可编辑的建议任务列表
const tasks = ref([])

const caseTypeOptions = [
  { label: '诈骗', value: 'fraud' },
  { label: '盗窃', value: 'theft' },
  { label: '毒品', value: 'drug' },
  { label: '经济犯罪', value: 'economic' },
  { label: '其他', value: 'other' },
]
const priorityOptions = [
  { label: '紧急', value: 'urgent' },
  { label: '高', value: 'high' },
  { label: '中', value: 'medium' },
  { label: '低', value: 'low' },
]

function beforeUpload(file) {
  uploadFile.value = file
  return false // 阻止自动上传，仅保留文件引用
}

function resetDraft() {
  draft.value = null
  tasks.value = []
  Object.assign(overview, {
    title: '', case_type: 'fraud', priority: 'medium',
    incident_date: '', incident_location: '', total_amount: null, summary: '',
  })
}

async function analyze() {
  if (!uploadFile.value && !pasteText.value.trim()) {
    message.warning('请先上传笔录文件或粘贴笔录文本')
    return
  }
  analyzing.value = true
  try {
    const fd = new FormData()
    if (uploadFile.value) fd.append('file', uploadFile.value)
    else fd.append('text', pasteText.value)
    const res = await apiPost('/api/police/import/transcript', fd)
    const data = res.data || {}
    draft.value = data
    const ov = data.case_overview || {}
    Object.assign(overview, {
      title: ov.title || '',
      case_type: caseTypeOptions.some(o => o.value === ov.case_type) ? ov.case_type : 'other',
      priority: priorityOptions.some(o => o.value === ov.priority) ? ov.priority : 'medium',
      incident_date: ov.incident_date || '',
      incident_location: ov.incident_location || '',
      total_amount: ov.total_amount ?? null,
      summary: ov.summary || '',
    })
    tasks.value = (data.suggested_tasks || []).map(t => ({
      title: t.title || '',
      type: t.type || '',
      priority: priorityOptions.some(o => o.value === t.priority) ? t.priority : 'medium',
      description: t.description || '',
      assignee_type: t.assignee_type || 'human',
    }))
  } catch (e) {
    message.error('分析失败: ' + (e.message || '未知错误'))
  } finally {
    analyzing.value = false
  }
}

function addTask() {
  tasks.value.push({ title: '', type: '', priority: 'medium', description: '', assignee_type: 'human' })
}

function removeTask(i) {
  tasks.value.splice(i, 1)
}

async function confirm() {
  if (!overview.title) {
    message.warning('请填写案件名称')
    return
  }
  if (tasks.value.length === 0) {
    message.warning('请至少保留一条任务')
    return
  }
  confirming.value = true
  try {
    const body = {
      overview: {
        ...overview,
        victim: draft.value?.case_overview?.victim || null,
        suspects: draft.value?.case_overview?.suspects || null,
        key_facts: draft.value?.case_overview?.key_facts || null,
      },
      tasks: tasks.value,
      description: overview.summary,
    }
    const res = await apiPost('/api/police/import/transcript/confirm', body)
    const caseId = res.data?.case_id
    message.success('案件创建成功，已生成初始任务')
    router.push(`/police/cases/${caseId}`)
  } catch (e) {
    message.error('建案失败: ' + (e.message || '未知错误'))
  } finally {
    confirming.value = false
  }
}
</script>

<template>
  <div class="import-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">笔录智能导入</h1>
        <p class="page-subtitle">上传或粘贴讯问/询问笔录，AI 自动提取案件概览并生成初始任务</p>
      </div>
      <a-button @click="router.push('/police/cases')">返回案件列表</a-button>
    </div>

    <!-- 第一步：上传 / 粘贴 -->
    <a-card class="step-card" title="1. 提交笔录">
      <a-upload-dragger
        :before-upload="beforeUpload"
        :show-upload-list="false"
        accept=".txt,.md,.pdf,.png,.jpg,.jpeg"
      >
        <p class="ant-upload-drag-icon"><FileTextOutlined /></p>
        <p class="ant-upload-text">点击或拖拽笔录文件到此处</p>
        <p class="ant-upload-hint">支持 txt / md / pdf / png / jpg（PDF 与图片需 OCR 服务已启动）</p>
      </a-upload-dragger>

      <div v-if="uploadFile" class="file-tag">
        <a-tag color="blue"><UploadOutlined /> {{ uploadFile.name }}</a-tag>
        <a-button type="link" size="small" @click="uploadFile = null">移除</a-button>
      </div>

      <a-divider orientation="left">或粘贴文本</a-divider>
      <a-textarea
        v-model:value="pasteText"
        :rows="5"
        placeholder="直接粘贴笔录文本内容……"
      />

      <div class="actions">
        <a-button type="primary" :loading="analyzing" @click="analyze">
          <template #icon><UploadOutlined /></template>
          AI 分析笔录
        </a-button>
        <a-button v-if="draft" @click="resetDraft">清空重来</a-button>
      </div>
    </a-card>

    <!-- 第二步：AI 结果 -->
    <template v-if="draft">
      <a-card class="step-card" title="2. 核对案件概览（可编辑）">
        <a-form layout="vertical">
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="案件名称" required>
                <a-input v-model:value="overview.title" placeholder="如：张某被诈骗案" />
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item label="案件类型">
                <a-select v-model:value="overview.case_type" :options="caseTypeOptions" />
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item label="优先级">
                <a-select v-model:value="overview.priority" :options="priorityOptions" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-row :gutter="16">
            <a-col :span="8">
              <a-form-item label="案发时间">
                <a-input v-model:value="overview.incident_date" placeholder="如：2026-03-12" />
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="案发地点">
                <a-input v-model:value="overview.incident_location" placeholder="如：某市某区" />
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="涉案金额">
                <a-input-number v-model:value="overview.total_amount" style="width: 100%" :min="0" :precision="2" placeholder="0.00" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-form-item label="案件概述">
            <a-textarea v-model:value="overview.summary" :rows="3" placeholder="AI 提取的案件概述，可修改" />
          </a-form-item>

          <a-descriptions title="AI 提取的当事人信息（确认时一并入库）" bordered size="small" :column="1">
            <a-descriptions-item label="受害人">
              {{ draft.case_overview?.victim?.name || '—' }}
              <span v-if="draft.case_overview?.victim?.role">（{{ draft.case_overview.victim.role }}）</span>
            </a-descriptions-item>
            <a-descriptions-item label="嫌疑人">
              <template v-if="(draft.case_overview?.suspects || []).length">
                <a-tag v-for="(s, i) in draft.case_overview.suspects" :key="i" color="red">
                  {{ s.name }}<span v-if="s.role">（{{ s.role }}）</span>
                </a-tag>
              </template>
              <span v-else>—</span>
            </a-descriptions-item>
            <a-descriptions-item label="关键事实">
              <template v-if="(draft.case_overview?.key_facts || []).length">
                <li v-for="(f, i) in draft.case_overview.key_facts" :key="i">{{ f }}</li>
              </template>
              <span v-else>—</span>
            </a-descriptions-item>
          </a-descriptions>
        </a-form>
      </a-card>

      <a-card class="step-card" title="3. 初始任务（可增删/编辑）">
        <div v-for="(t, i) in tasks" :key="i" class="task-row">
          <a-input v-model:value="t.title" placeholder="任务标题" style="width: 240px" />
          <a-input v-model:value="t.type" placeholder="类型，如：证据收集" style="width: 160px" />
          <a-select v-model:value="t.priority" :options="priorityOptions" style="width: 100px" />
          <a-input v-model:value="t.description" placeholder="任务说明" style="flex: 1" />
          <a-button type="link" danger @click="removeTask(i)"><DeleteOutlined /></a-button>
        </div>
        <a-button type="dashed" block @click="addTask"><PlusOutlined /> 添加任务</a-button>

        <div class="actions confirm-actions">
          <a-button type="primary" :loading="confirming" @click="confirm">
            确认建案并生成任务
          </a-button>
        </div>
      </a-card>
    </template>
  </div>
</template>

<style scoped>
.import-page {
  padding: 24px 32px;
  max-width: 1100px;
  margin: 0 auto;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}
.page-title {
  font-size: 22px;
  font-weight: 600;
  margin: 0 0 4px 0;
}
.page-subtitle {
  font-size: 13px;
  color: var(--gray-500, #718096);
  margin: 0;
}
.step-card {
  margin-bottom: 16px;
}
.file-tag {
  margin: 12px 0;
}
.actions {
  margin-top: 16px;
  display: flex;
  gap: 8px;
}
.task-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.confirm-actions {
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
