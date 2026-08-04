<script setup>
/**
 * ★ 案件详情 — Plane 风格 Tab 布局
 * POLICE_REQUIREMENTS §8.4.3
 */
import { onMounted, ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePoliceStore } from '@/stores/police'
import { policeAgentApi } from '@/apis/police_api'
import { message } from 'ant-design-vue'
import {
  ArrowLeftOutlined, UserOutlined, ClockCircleOutlined,
  DollarOutlined, EnvironmentOutlined, TeamOutlined,
  AppstoreOutlined, UnorderedListOutlined
} from '@ant-design/icons-vue'

const route = useRoute()
const router = useRouter()
const policeStore = usePoliceStore()

const activeTab = ref('overview')
const loading = ref(false)
const showCreateTaskModal = ref(false)
const showPhaseModal = ref(false)
const taskViewMode = ref('table') // table / kanban — 任务 tab 内双视图切换

const caseId = computed(() => parseInt(route.params.caseId))
const caseData = computed(() => policeStore.currentCase)

const phaseText = { research: '研判', arrest: '抓捕', handling: '办理', prosecution: '移送' }
const statusText = { draft: '草稿', investigation: '侦查中', arrest: '抓捕', handling: '办理中', prosecution: '待移送', closed: '已结案' }

const taskColumns = [
  { title: '任务', dataIndex: 'title', key: 'title', ellipsis: true },
  { title: '类型', dataIndex: 'type', key: 'type', width: 140 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '执行人', dataIndex: 'assignees', key: 'assignees', width: 180 },
  { title: '优先级', dataIndex: 'priority', key: 'priority', width: 80 },
  { title: '操作', key: 'action', width: 80 },
]

const taskStatusText = { pending: '待处理', in_progress: '进行中', review: '待审核', completed: '已完成', blocked: '已驳回' }
const taskStatusColor = { pending: 'default', in_progress: 'processing', review: 'warning', completed: 'success', blocked: 'error' }

// ── 看板视图常量（案件内看板）─────
const statusColumns = [
  { key: 'pending', title: '待处理', color: '#718096' },
  { key: 'in_progress', title: '进行中', color: '#3182CE' },
  { key: 'review', title: '待审核', color: '#D69E2E' },
  { key: 'completed', title: '已完成', color: '#38A169' },
  { key: 'blocked', title: '已驳回', color: '#E53E3E' },
]

const typeText = {
  transcript_analysis: '笔录分析', fund_analysis: '资金分析', evidence_collection: '调证生成',
  evidence_submission: '证据提交', legal_review: '法制审核', document_generation: '文书生成',
  investigation: '侦查', interrogation: '审讯', arrest: '抓捕', cyber_inquiry: '网警查询',
  knowledge_extraction: '知识抽取',
}

const priorityColor = { urgent: 'red', high: 'orange', medium: 'blue', low: 'default' }

/** 按状态分组的任务（仅含当前案件） */
const tasksByStatus = computed(() => {
  const map = {}
  for (const col of statusColumns) {
    map[col.key] = policeStore.tasks.filter(t => t.status === col.key)
  }
  return map
})

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

// 可选的分配对象——人类（案件成员）
const humanOptions = computed(() => {
  const members = caseData.value?.members || []
  return members.map(m => ({
    label: `${m.username || m.user_name || '未命名'} (${{ commander: '指挥员', handler: '办案人', reviewer: '审核员', observer: '观察员' }[m.role] || m.role})`,
    value: m.user_id,
    name: m.username || m.user_name || '',
  }))
})

// 可选的分配对象——智能体
const agentOptions = ref([])
const agentsLoading = ref(false)

async function loadAgents() {
  agentsLoading.value = true
  try {
    const res = await policeAgentApi.list({ page_size: 50 })
    agentOptions.value = (res.items || []).map(a => ({
      label: `${a.name || a.display_name || '未命名智能体'} (${a.type || a.agent_type || '-'})`,
      value: a.id,
      name: a.name || a.display_name || '',
    }))
  } catch (e) {
    // 智能体列表加载失败不阻塞主流程
    agentOptions.value = []
  } finally {
    agentsLoading.value = false
  }
}

/** 当前分配选项（根据 assignee_type 切换） */
const currentAssigneeOptions = computed(() =>
  taskForm.value.assignee_type === 'agent' ? agentOptions.value : humanOptions.value
)

function handleAssigneeChange(value, option) {
  taskForm.value.assignee_id = value
  taskForm.value.assignee_name = option?.name || option?.label || ''
}

function handleAssigneeTypeChange(val) {
  // 切换类型时清空已选分配对象
  taskForm.value.assignee_type = val
  taskForm.value.assignee_id = null
  taskForm.value.assignee_name = ''
}

// ── 任务列表内分配已有任务（表格行 / 看板卡片共用） ──
const assignModalVisible = ref(false)
const assignTaskId = ref(null)
const assignLoading = ref(false)
// 多执行人表单：支持同时选多个民警和多个智能体
const assignForm = ref({
  selectedHumans: [],    // [{value, label, name}]
  selectedAgents: [],   // [{value, label, name}]
})

function showAssignModalFor(task) {
  assignTaskId.value = task.id
  // 预填已有的执行人（编辑模式）
  const existing = task.assignees || []
  assignForm.value = {
    selectedHumans: existing.filter(a => a.assignee_type === 'human').map(a => ({
      value: a.assignee_id, label: a.assignee_name, name: a.assignee_name,
    })),
    selectedAgents: existing.filter(a => a.assignee_type === 'agent').map(a => ({
      value: a.assignee_id, label: a.assignee_name, name: a.assignee_name,
    })),
  }
  assignModalVisible.value = true
}

/** 构造后端需要的 assignees 数组 */
function buildAssigneesPayload() {
  const assignees = [
    ...assignForm.value.selectedHumans.map(h => ({
      assignee_type: 'human',
      assignee_id: h.value,
      assignee_name: h.name || h.label || '',
      role: 'executor',
    })),
    ...assignForm.value.selectedAgents.map(a => ({
      assignee_type: 'agent',
      assignee_id: a.value,
      assignee_name: a.name || a.label || '',
      role: 'executor',
    })),
  ]
  return assignees
}

async function handleAssignTask() {
  const payload = buildAssigneesPayload()
  if (payload.length === 0) {
    message.warning('请至少选择一名办案民警或智能体')
    return
  }
  assignLoading.value = true
  try {
    await policeStore.assignTask(assignTaskId.value, { assignees: payload })
    message.success(`任务已分配给 ${payload.length} 名执行人`)
    assignModalVisible.value = false
    await policeStore.loadTasks({ case_id: caseId.value, page_size: 100 })
  } catch (e) {
    message.error('分配失败')
  } finally {
    assignLoading.value = false
  }
}

/** 格式化任务执行人显示（支持多人） */
function formatAssignees(task) {
  const assignees = task.assignees || []
  if (assignees.length === 0) return task.assignee_name || '未分配'
  if (assignees.length <= 2) {
    return assignees.map(a => a.assignee_name).join('、')
  }
  return `${assignees[0].assignee_name} 等 ${assignees.length} 人`
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

onMounted(() => { loadCase(); loadAgents() })
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

      <!-- 任务（整合看板/表格双视图） -->
      <a-tab-pane key="tasks" tab="任务">
        <div class="tab-toolbar">
          <div class="toolbar-left">
            <a-radio-group v-model:value="taskViewMode" button-style="solid" size="small">
              <a-radio-button value="table"><UnorderedListOutlined /> 表格</a-radio-button>
              <a-radio-button value="kanban"><AppstoreOutlined /> 看板</a-radio-button>
            </a-radio-group>
          </div>
          <a-button type="primary" size="small" @click="showCreateTaskModal = true">创建任务</a-button>
        </div>

        <!-- 表格视图 -->
        <div v-if="taskViewMode === 'table'">
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
              <template v-else-if="column.key === 'assignees'">
                <span v-if="record.assignees && record.assignees.length">
                  <a-tag v-for="a in record.assignees.slice(0, 3)" :key="a.id" :color="a.assignee_type === 'agent' ? 'purple' : 'blue'" size="small">
                    {{ a.assignee_name }}
                  </a-tag>
                  <a-tag v-if="record.assignees.length > 3" size="small">+{{ record.assignees.length - 3 }}</a-tag>
                </span>
                <span v-else class="text-gray">{{ formatAssignees(record) }}</span>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-button type="link" size="small" @click="goTask(record.id)">详情</a-button>
                <a-button type="link" size="small" @click="showAssignModalFor(record)">分配</a-button>
              </template>
            </template>
          </a-table>
        </div>

        <!-- 看板视图 -->
        <div v-else class="kanban-board">
          <div v-for="col in statusColumns" :key="col.key" class="kanban-column">
            <div class="kanban-column-header" :style="{ borderTopColor: col.color }">
              <span class="column-title">{{ col.title }}</span>
              <span class="column-count">{{ tasksByStatus[col.key]?.length || 0 }}</span>
            </div>
            <div class="kanban-column-body">
              <div
                v-for="task in (tasksByStatus[col.key] || [])"
                :key="task.id"
                class="kanban-card"
                @click="goTask(task.id)"
              >
                <div class="card-title">{{ task.title }}</div>
                <div class="card-meta">
                  <a-tag size="small">{{ typeText[task.type] || task.type }}</a-tag>
                  <a-tag :color="priorityColor[task.priority]" size="small">{{ task.priority }}</a-tag>
                </div>
                <div class="card-footer">
                  <span class="card-assignee">
                    <a-avatar size="small" style="background: var(--main-color, #24839b)">
                      {{ (task.assignee_name || '?')[0] }}
                    </a-avatar>
                    <span>{{ task.assignee_name || '未分配' }}</span>
                  </span>
                  <a-button type="link" size="small" @click.stop="showAssignModalFor(task)">分配</a-button>
                </div>
              </div>
              <div v-if="!tasksByStatus[col.key]?.length" class="kanban-empty">暂无任务</div>
            </div>
          </div>
        </div>
      </a-tab-pane>

      <!-- 证据 -->
      <a-tab-pane key="evidence" tab="证据">
        <EvidenceTab :case-id="caseId" />
      </a-tab-pane>

      <!-- 工作区 -->
      <a-tab-pane key="workspace" tab="工作区">
        <WorkspaceTab :case-id="caseId" />
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
        <a-form-item label="分配给">
          <div style="display: flex; gap: 8px; margin-bottom: 8px;">
            <a-radio-group v-model:value="taskForm.assignee_type" size="small" @change="(e) => handleAssigneeTypeChange(e.target.value)">
              <a-radio-button value="human">
                <UserOutlined /> 办案民警
              </a-radio-button>
              <a-radio-button value="agent">
                <TeamOutlined /> 智能体
              </a-radio-button>
            </a-radio-group>
          </div>
          <a-select
            v-model:value="taskForm.assignee_id"
            :options="currentAssigneeOptions"
            :placeholder="taskForm.assignee_type === 'agent' ? '选择智能体' : '选择办案民警'"
            :loading="taskForm.assignee_type === 'agent' ? agentsLoading : loading"
            allow-clear
            show-search
            option-filter-prop="label"
            @change="handleAssigneeChange"
            :not-found-content="taskForm.assignee_type === 'agent' ? (agentsLoading ? '加载中...' : '暂无可用智能体') : '暂无案件成员'"
          />
        </a-form-item>
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

        <!-- 列表内分配任务弹窗（多人+多智能体协同） -->
    <a-modal
      v-model:open="assignModalVisible"
      title="分配任务"
      :confirm-loading="assignLoading"
      @ok="handleAssignTask"
      ok-text="确认分配"
      cancel-text="取消"
      width="520px"
    >
      <a-form layout="vertical" style="margin-top: 16px">
        <a-form-item label="办案民警（可多选）">
          <a-select
            mode="multiple"
            v-model:value="assignForm.selectedHumans"
            :options="humanOptions"
            placeholder="选择要分配的办案民警"
            :loading="loading"
            allow-clear
            show-search
            option-filter-prop="label"
            :not-found-content="loading ? '加载中...' : '暂无案件成员'"
          />
        </a-form-item>
        <a-form-item label="智能体（可多选，与民警协同执行）">
          <a-select
            mode="multiple"
            v-model:value="assignForm.selectedAgents"
            :options="agentOptions"
            placeholder="选择要参与的智能体（可选）"
            :loading="agentsLoading"
            allow-clear
            show-search
            option-filter-prop="label"
            :not-found-content="agentsLoading ? '加载中...' : '暂无可用智能体'"
          />
        </a-form-item>
        <div class="assign-summary" v-if="assignForm.selectedHumans.length || assignForm.selectedAgents.length">
          <a-tag v-for="h in assignForm.selectedHumans" :key="'h-'+h.value" color="blue">
            <UserOutlined /> {{ h.label }}
          </a-tag>
          <a-tag v-for="a in assignForm.selectedAgents" :key="'a'+a.value" color="purple">
            <TeamOutlined /> {{ a.label }}
          </a-tag>
          <span class="assign-count">共 {{ assignForm.selectedHumans.length + assignForm.selectedAgents.length }} 名执行人</span>
        </div>
      </a-form>
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
import WorkspaceTab from './WorkspaceTab.vue'
export default { components: { EvidenceTab, CaseTimeline, WorkspaceTab } }
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
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ── 看板视图（任务 tab 内） ── */
.kanban-board {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 8px;
}

.kanban-column {
  min-width: 240px;
  flex: 1;
  max-width: 280px;
  background: var(--gray-10, #f7fafc);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
}

.kanban-column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-top: 3px solid;
  border-radius: 10px 10px 0 0;
}

.column-title {
  font-size: 13px;
  font-weight: 600;
}

.column-count {
  font-size: 11px;
  background: var(--gray-50, #e2e8f0);
  padding: 2px 8px;
  border-radius: 10px;
  color: var(--gray-600, #4a5568);
}

.kanban-column-body {
  padding: 8px;
  flex: 1;
  min-height: 80px;
}

.kanban-card {
  background: var(--gray-0, #fff);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: box-shadow 0.15s;
}

.kanban-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.card-title {
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 6px;
  line-height: 1.4;
}

.card-meta {
  display: flex;
  gap: 4px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--gray-500, #718096);
}

.card-assignee {
  display: flex;
  align-items: center;
  gap: 4px;
}

.kanban-empty {
  text-align: center;
  color: var(--gray-400, #a0aec0);
  padding: 20px 0;
  font-size: 12px;
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

/* 多执行人分配弹窗 */
.assign-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  padding: 12px;
  background: #f6f8fa;
  border-radius: 8px;
  margin-top: 4px;
}
.assign-count {
  font-size: 12px;
  color: #718096;
  margin-left: 4px;
}
.text-gray { color: #a0aec0; }
</style>
