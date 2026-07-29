<script setup>
/**
 * ★ 案件详情 — Plane 风格 Tab 布局
 * POLICE_REQUIREMENTS §8.4.3
 */
import { onMounted, ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePoliceStore } from '@/stores/police'
import { message } from 'ant-design-vue'
import {
  ArrowLeftOutlined, UserOutlined, ClockCircleOutlined,
  DollarOutlined, EnvironmentOutlined, TeamOutlined
} from '@ant-design/icons-vue'

const route = useRoute()
const router = useRouter()
const policeStore = usePoliceStore()

const activeTab = ref('overview')
const loading = ref(false)
const showCreateTaskModal = ref(false)
const showPhaseModal = ref(false)

const caseId = computed(() => parseInt(route.params.caseId))
const caseData = computed(() => policeStore.currentCase)

const phaseText = { research: '研判', arrest: '抓捕', handling: '办理', prosecution: '移送' }
const statusText = { draft: '草稿', investigation: '侦查中', arrest: '抓捕', handling: '办理中', prosecution: '待移送', closed: '已结案' }

const taskColumns = [
  { title: '任务', dataIndex: 'title', key: 'title', ellipsis: true },
  { title: '类型', dataIndex: 'type', key: 'type', width: 140 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '分配给', dataIndex: 'assignee_name', key: 'assignee_name', width: 140 },
  { title: '优先级', dataIndex: 'priority', key: 'priority', width: 80 },
  { title: '操作', key: 'action', width: 80 },
]

const taskStatusText = { pending: '待处理', in_progress: '进行中', review: '待审核', completed: '已完成', blocked: '已驳回' }
const taskStatusColor = { pending: 'default', in_progress: 'processing', review: 'warning', completed: 'success', blocked: 'error' }

const phaseSteps = [
  { key: 'research', title: '前期研判' },
  { key: 'arrest', title: '抓捕审讯' },
  { key: 'handling', title: '案件办理' },
  { key: 'prosecution', title: '移送起诉' },
]

const currentPhaseIndex = computed(() => {
  if (!caseData.value) return 0
  return phaseSteps.findIndex(p => p.key === caseData.value.phase)
})

// ── 创建任务 ──────────────────────────────────────────────
const taskForm = ref({
  title: '', type: 'evidence_collection', assignee_type: 'human',
  assignee_id: null, assignee_name: '', priority: 'medium',
  instructions: '',
})

const taskTypes = [
  { label: '笔录分析', value: 'transcript_analysis' },
  { label: '资金分析', value: 'fund_analysis' },
  { label: '调证生成', value: 'evidence_collection' },
  { label: '证据提交', value: 'evidence_submission' },
  { label: '法制审核', value: 'legal_review' },
  { label: '文书生成', value: 'document_generation' },
  { label: '侦查', value: 'investigation' },
  { label: '审讯', value: 'interrogation' },
  { label: '抓捕', value: 'arrest' },
  { label: '网警查询', value: 'cyber_inquiry' },
  { label: '知识抽取', value: 'knowledge_extraction' },
]

async function loadCase() {
  loading.value = true
  try {
    await policeStore.loadCase(caseId.value)
    await policeStore.loadTasks({ case_id: caseId.value, page_size: 100 })
  } finally {
    loading.value = false
  }
}

async function handleCreateTask() {
  if (!taskForm.value.title) {
    message.warning('请填写任务标题')
    return
  }
  try {
    await policeStore.createTask({
      ...taskForm.value,
      case_id: caseId.value,
      phase: caseData.value?.phase,
    })
    message.success('任务创建成功')
    showCreateTaskModal.value = false
    taskForm.value = { title: '', type: 'evidence_collection', assignee_type: 'human', assignee_id: null, assignee_name: '', priority: 'medium', instructions: '' }
    await policeStore.loadTasks({ case_id: caseId.value, page_size: 100 })
  } catch (e) {
    message.error('创建失败')
  }
}

async function handlePhaseChange(phase) {
  try {
    await policeStore.updatePhase(caseId.value, phase)
    message.success(`已切换到 ${phaseText[phase]} 阶段`)
    showPhaseModal.value = false
  } catch (e) {
    message.error('切换阶段失败')
  }
}

function goTask(taskId) {
  router.push(`/police/tasks/${taskId}`)
}

onMounted(loadCase)
watch(caseId, loadCase)
</script>

<template>
  <div class="case-detail-page" v-if="caseData">
    <!-- 顶部导航 -->
    <div class="detail-header">
      <div class="header-left">
        <a-button type="text" @click="router.push('/police/cases')">
          <template #icon><ArrowLeftOutlined /></template>
          返回
        </a-button>
        <div class="case-title-block">
          <div class="case-number">{{ caseData.case_number }}</div>
          <h1 class="case-title">{{ caseData.title }}</h1>
        </div>
      </div>
      <div class="header-right">
        <a-button @click="showPhaseModal = true">切换阶段</a-button>
        <a-button type="primary" @click="showCreateTaskModal = true">创建任务</a-button>
      </div>
    </div>

    <!-- 阶段进度条 -->
    <div class="phase-steps">
      <div
        v-for="(step, idx) in phaseSteps"
        :key="step.key"
        class="phase-step"
        :class="{ active: idx <= currentPhaseIndex, current: idx === currentPhaseIndex }"
      >
        <div class="phase-dot">{{ idx + 1 }}</div>
        <div class="phase-label">{{ step.title }}</div>
        <div v-if="idx < phaseSteps.length - 1" class="phase-line" :class="{ done: idx < currentPhaseIndex }"></div>
      </div>
    </div>

    <!-- Tab 区域 -->
    <a-tabs v-model:activeKey="activeTab" class="case-tabs">
      <!-- 概览 -->
      <a-tab-pane key="overview" tab="概览">
        <div class="overview-grid">
          <div class="info-card">
            <h3>案件信息</h3>
            <div class="info-list">
              <div class="info-item">
                <span class="info-label">案件编号</span>
                <span class="info-value">{{ caseData.case_number }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">案件类型</span>
                <span class="info-value">{{ caseData.case_type || '—' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">当前阶段</span>
                <span class="info-value"><a-tag color="blue">{{ phaseText[caseData.phase] }}</a-tag></span>
              </div>
              <div class="info-item">
                <span class="info-label">案件状态</span>
                <span class="info-value"><a-tag>{{ statusText[caseData.status] }}</a-tag></span>
              </div>
              <div class="info-item">
                <span class="info-label"><DollarOutlined /> 涉案金额</span>
                <span class="info-value">{{ caseData.total_amount ? '¥' + Number(caseData.total_amount).toLocaleString() : '—' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label"><EnvironmentOutlined /> 案发地点</span>
                <span class="info-value">{{ caseData.incident_location || '—' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label"><ClockCircleOutlined /> 创建时间</span>
                <span class="info-value">{{ caseData.created_at?.substring(0, 10) }}</span>
              </div>
            </div>
          </div>

          <div class="info-card">
            <h3>案件描述</h3>
            <div class="case-description">
              {{ caseData.description || '暂无描述' }}
            </div>

            <h3 style="margin-top: 24px">受害人信息</h3>
            <div class="case-description">
              <template v-if="caseData.victim_info && Object.keys(caseData.victim_info).length">
                <pre>{{ JSON.stringify(caseData.victim_info, null, 2) }}</pre>
              </template>
              <template v-else>暂无</template>
            </div>
          </div>
        </div>
      </a-tab-pane>

      <!-- 任务 -->
      <a-tab-pane key="tasks" tab="任务">
        <div class="tab-toolbar">
          <a-button type="primary" size="small" @click="showCreateTaskModal = true">创建任务</a-button>
        </div>
        <a-table
          :columns="taskColumns"
          :data-source="policeStore.tasks"
          row-key="id"
          size="middle"
          :pagination="false"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'title'">
              <a class="task-link" @click="goTask(record.id)">{{ record.title }}</a>
            </template>
            <template v-else-if="column.key === 'status'">
              <a-badge :status="taskStatusColor[record.status]" :text="taskStatusText[record.status]" />
            </template>
            <template v-else-if="column.key === 'priority'">
              <a-tag :color="{ urgent: 'red', high: 'orange', medium: 'blue', low: 'default' }[record.priority]">
                {{ record.priority }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <a-button type="link" size="small" @click="goTask(record.id)">详情</a-button>
            </template>
          </template>
        </a-table>
      </a-tab-pane>

      <!-- 证据 -->
      <a-tab-pane key="evidence" tab="证据">
        <EvidenceTab :case-id="caseId" />
      </a-tab-pane>

      <!-- 动态 -->
      <a-tab-pane key="timeline" tab="动态">
        <CaseTimeline :case-id="caseId" />
      </a-tab-pane>

      <!-- 成员 -->
      <a-tab-pane key="members" tab="成员">
        <div class="members-list">
          <div v-for="m in (caseData.members || [])" :key="m.id" class="member-item">
            <a-avatar size="small"><template #icon><UserOutlined /></template></a-avatar>
            <span class="member-name">用户 #{{ m.user_id }}</span>
            <a-tag>{{ { commander: '指挥员', handler: '办案人', reviewer: '审核员', observer: '观察员' }[m.role] || m.role }}</a-tag>
          </div>
          <div v-if="!caseData.members?.length" class="empty-text">暂无成员</div>
        </div>
      </a-tab-pane>
    </a-tabs>

    <!-- 创建任务弹窗 -->
    <a-modal v-model:open="showCreateTaskModal" title="创建任务" @ok="handleCreateTask" width="560px">
      <a-form layout="vertical" style="margin-top: 16px">
        <a-form-item label="任务标题" required>
          <a-input v-model:value="taskForm.title" placeholder="如: 调取工行账户6222****1234流水" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="任务类型">
              <a-select v-model:value="taskForm.type">
                <a-select-option v-for="t in taskTypes" :key="t.value" :value="t.value">{{ t.label }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="优先级">
              <a-select v-model:value="taskForm.priority">
                <a-select-option value="urgent">紧急</a-select-option>
                <a-select-option value="high">高</a-select-option>
                <a-select-option value="medium">中</a-select-option>
                <a-select-option value="low">低</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="分配对象类型">
              <a-radio-group v-model:value="taskForm.assignee_type">
                <a-radio value="human">民警</a-radio>
                <a-radio value="agent">智能体</a-radio>
              </a-radio-group>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="分配给">
              <a-input v-model:value="taskForm.assignee_name" placeholder="姓名或智能体名称" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="任务指引">
          <a-textarea v-model:value="taskForm.instructions" :rows="3" placeholder="任务详细要求和注意事项" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 阶段切换弹窗 -->
    <a-modal v-model:open="showPhaseModal" title="切换案件阶段" :footer="null" width="400px">
      <div class="phase-select-list">
        <div
          v-for="step in phaseSteps"
          :key="step.key"
          class="phase-select-item"
          :class="{ current: step.key === caseData.phase }"
          @click="handlePhaseChange(step.key)"
        >
          <span>{{ step.title }}</span>
          <a-tag v-if="step.key === caseData.phase" color="blue">当前</a-tag>
        </div>
      </div>
    </a-modal>
  </div>
  <div v-else class="loading-state">
    <a-spin size="large" />
  </div>
</template>

<script>
// 子组件内联 (避免额外文件)
import EvidenceTab from './EvidenceTab.vue'
import CaseTimeline from './CaseTimeline.vue'
export default { components: { EvidenceTab, CaseTimeline } }
</script>

<style scoped>
.case-detail-page {
  padding: 24px 32px;
  max-width: 1400px;
  margin: 0 auto;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.case-title-block {
  padding-top: 4px;
}

.case-number {
  font-size: 12px;
  color: var(--gray-500, #718096);
  margin-bottom: 2px;
}

.case-title {
  font-size: 22px;
  font-weight: 600;
  margin: 0;
}

.header-right {
  display: flex;
  gap: 8px;
}

/* 阶段步骤条 */
.phase-steps {
  display: flex;
  align-items: center;
  margin-bottom: 24px;
  padding: 16px 24px;
  background: var(--gray-0, #fff);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 12px;
}

.phase-step {
  display: flex;
  align-items: center;
  gap: 8px;
}

.phase-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  background: var(--gray-50, #e2e8f0);
  color: var(--gray-400, #a0aec0);
}

.phase-step.active .phase-dot {
  background: var(--main-color, #24839b);
  color: #fff;
}

.phase-step.current .phase-dot {
  box-shadow: 0 0 0 3px var(--main-color, #24839b)33;
}

.phase-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--gray-400, #a0aec0);
}

.phase-step.active .phase-label {
  color: var(--gray-1000, #1a1a1a);
}

.phase-line {
  width: 60px;
  height: 2px;
  background: var(--gray-50, #e2e8f0);
  margin: 0 8px;
}

.phase-line.done {
  background: var(--main-color, #24839b);
}

/* Tab */
.case-tabs {
  background: var(--gray-0, #fff);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 12px;
  padding: 0 20px 20px;
}

.tab-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

/* 概览 */
.overview-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.info-card {
  background: var(--gray-10, #f7fafc);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 10px;
  padding: 20px;
}

.info-card h3 {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px 0;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 13px;
}

.info-label {
  color: var(--gray-500, #718096);
}

.info-value {
  font-weight: 500;
}

.case-description {
  font-size: 13px;
  color: var(--gray-700, #4a5568);
  line-height: 1.6;
}

.case-description pre {
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}

/* 成员 */
.members-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.member-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--gray-10, #f7fafc);
}

.member-name {
  flex: 1;
  font-size: 14px;
}

.empty-text {
  text-align: center;
  color: var(--gray-400, #a0aec0);
  padding: 24px;
}

/* 阶段选择 */
.phase-select-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 16px;
}

.phase-select-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
  font-size: 14px;
}

.phase-select-item:hover {
  border-color: var(--main-color, #24839b);
}

.phase-select-item.current {
  background: var(--main-color, #24839b)10;
  border-color: var(--main-color, #24839b);
}

.task-link {
  color: var(--main-color, #24839b);
  cursor: pointer;
  font-weight: 500;
}

.loading-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}
</style>
