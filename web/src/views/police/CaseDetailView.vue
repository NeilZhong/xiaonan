<script setup>
/**
 * ★ 案件详情 — Plane 风格 Tab 布局
 * POLICE_REQUIREMENTS §8.4.3
 */
import { onMounted, ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePoliceStore } from '@/stores/police'
import { policeAgentApi } from '@/apis/police_api'
import TaskViewSwitcher from '@/components/police/TaskViewSwitcher.vue'
import TaskTreeView from '@/components/police/TaskTreeView.vue'
import TaskCalendarView from '@/components/police/TaskCalendarView.vue'
import TaskKanbanView from '@/components/police/TaskKanbanView.vue'
import CaseStatsTab from '@/components/police/CaseStatsTab.vue'
import TaskDetailModal from '@/components/police/TaskDetailModal.vue'
import TaskCreateModal from '@/components/police/TaskCreateModal.vue'
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
// 任务视图偏好持久化（借鉴 Plane 的 displayFilters.layout 持久化，先存 localStorage）
const TASK_VIEW_KEY = 'xiaonan.taskViewMode'
const taskLayouts = ['table', 'kanban', 'tree', 'gantt', 'calendar']
const taskViewMode = ref(localStorage.getItem(TASK_VIEW_KEY) || 'table')
watch(taskViewMode, (v) => localStorage.setItem(TASK_VIEW_KEY, v))

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
  { title: '截止', dataIndex: 'due_date', key: 'due_date', width: 110 },
  { title: '操作', key: 'action', width: 80 },
]

const taskStatusText = { pending: '待处理', in_progress: '进行中', review: '待审核', completed: '已完成', blocked: '已驳回' }
const taskStatusColor = { pending: 'default', in_progress: 'processing', review: 'warning', completed: 'success', blocked: 'error' }

const typeText = {
  transcript_analysis: '笔录分析', fund_analysis: '资金分析', evidence_collection: '调证生成',
  evidence_submission: '证据提交', legal_review: '法制审核', document_generation: '文书生成',
  investigation: '侦查', interrogation: '审讯', arrest: '抓捕', cyber_inquiry: '网警查询',
  knowledge_extraction: '知识抽取',
}

const priorityColor = { urgent: 'red', high: 'orange', medium: 'blue', low: 'default' }
// 优先级中文文案（表格视图展示中文，避免裸英文 value）
const priorityText = { urgent: '紧急', high: '高', medium: '中', low: '低' }

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
// 表单逻辑已下沉到 TaskCreateModal.vue，此处仅保留弹窗开关状态

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
// 注：创建任务的分配逻辑已下沉 TaskCreateModal；此处保留的 human/agent 选项供「列表内分配弹窗」使用

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

async function handlePhaseChange(phase) {
  try {
    await policeStore.updatePhase(caseId.value, phase)
    message.success(`已切换到 ${phaseText[phase]} 阶段`)
    showPhaseModal.value = false
  } catch (e) {
    message.error('切换阶段失败')
  }
}

// 任务详情弹窗（点击任务 → 弹窗展示，替代整页路由跳转）
const detailModalVisible = ref(false)
const detailTaskId = ref(null)

function goTask(taskId) {
  detailTaskId.value = taskId
  detailModalVisible.value = true
}

function closeTaskDetail() {
  detailModalVisible.value = false
  detailTaskId.value = null
}

/** 任务是否已逾期（有截止、未关闭、当前时间超过截止） */
function isOverdue(task) {
  if (!task.due_date || ['completed', 'cancelled', 'terminated'].includes(task.status)) return false
  return new Date(task.due_date) < new Date()
}

function reloadTasks() {
  policeStore.loadTasks({ case_id: caseId.value, page_size: 100 })
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
      <!-- 概览（信息卡片 + 统计图表 左右分栏） -->
      <a-tab-pane key="overview" tab="概览">
        <div class="overview-layout">
          <!-- 左栏：信息卡片 -->
          <div class="overview-left">
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
            </div>

            <div class="info-card">
              <h3>受害人信息</h3>
              <div class="case-description">
                <template v-if="caseData.victim_info && Object.keys(caseData.victim_info).length">
                  <pre>{{ JSON.stringify(caseData.victim_info, null, 2) }}</pre>
                </template>
                <template v-else>暂无</template>
              </div>
            </div>
          </div>

          <!-- 右栏：统计图表 -->
          <div class="overview-right">
            <CaseStatsTab :case-id="caseId" />
          </div>
        </div>
      </a-tab-pane>

      <!-- 任务（整合看板/表格双视图） -->
      <a-tab-pane key="tasks" tab="任务">
        <div class="tab-toolbar">
          <div class="toolbar-left">
            <TaskViewSwitcher v-model="taskViewMode" :layouts="taskLayouts" />
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
                <a-tag v-if="record.priority === 'urgent'" color="red" class="priority-urgent">紧急</a-tag>
                <a-tag v-else :color="priorityColor[record.priority]">
                  {{ priorityText[record.priority] || record.priority }}
                </a-tag>
              </template>
              <template v-else-if="column.key === 'due_date'">
                <span v-if="record.due_date" :class="{ 'due-overdue': isOverdue(record) }">
                  {{ String(record.due_date).substring(0, 10) }}
                </span>
                <span v-else class="text-gray">—</span>
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

        <!-- 看板视图（Plane 风格拖拽） -->
        <div v-else-if="taskViewMode === 'kanban'">
          <TaskKanbanView
            :tasks="policeStore.tasks"
            @open-task="goTask"
            @assign-task="showAssignModalFor"
            @refresh="reloadTasks"
          />
        </div>

        <!-- 树状视图（基于任务父子层级 parent_task_id） -->
        <div v-else-if="taskViewMode === 'tree'" class="task-placeholder">
          <TaskTreeView
            :tasks="policeStore.tasks"
            @open-task="goTask"
            @assign-task="showAssignModalFor"
          />
        </div>

        <!-- 甘特视图（基于任务起止 / 时限） -->
        <div v-else-if="taskViewMode === 'gantt'" class="task-placeholder">
          <a-empty description="甘特视图开发中（基于任务起止 / 法定时限）" />
        </div>

        <!-- 日历视图（基于任务时限 due_date） -->
        <div v-else-if="taskViewMode === 'calendar'" class="task-placeholder">
          <TaskCalendarView
            :tasks="policeStore.tasks"
            @open-task="goTask"
            @assign-task="showAssignModalFor"
          />
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
        <div class="members-list t-avatar-group">
          <div v-for="m in (caseData.members || [])" :key="m.id" class="member-item">
            <a-avatar size="small" class="t-avatar"><template #icon><UserOutlined /></template></a-avatar>
            <span class="member-name">用户 #{{ m.user_id }}</span>
            <a-tag>{{ { commander: '指挥员', handler: '办案人', reviewer: '审核员', observer: '观察员' }[m.role] || m.role }}</a-tag>
          </div>
          <div v-if="!caseData.members?.length" class="empty-text">暂无成员</div>
        </div>
      </a-tab-pane>
    </a-tabs>

    <!-- 创建任务弹窗（与详情弹窗统一风格） -->
    <TaskCreateModal
      :visible="showCreateTaskModal"
      :case-id="caseId"
      :phase="caseData.phase"
      @close="showCreateTaskModal = false"
      @created="reloadTasks"
    />

    <!-- 阶段切换弹窗 -->
    <a-modal v-model:open="showPhaseModal" title="切换案件阶段" :footer="null" width="400px">
      <div class="phase-select-list">
        <div
          v-for="step in phaseSteps"
          :key="step.key"
          class="phase-select-item"
          :class="{ current: step.key === caseData.phase }"
          role="button"
          :tabindex="0"
          :aria-label="`切换到${step.title}阶段`"
          @click="handlePhaseChange(step.key)"
          @keydown="(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handlePhaseChange(step.key) } }"
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

    <!-- 任务详情弹窗（点击任务 → 弹窗展示） -->
    <TaskDetailModal
      :visible="detailModalVisible"
      :task-id="detailTaskId"
      @close="closeTaskDetail"
      @refresh="reloadTasks"
    />
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

/* 概览 — 信息卡 + 统计图表 左右分栏 */
.overview-layout {
  display: grid;
  grid-template-columns: 380px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.overview-left {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.overview-right {
  min-width: 0;
}

@media (max-width: 1200px) {
  .overview-layout {
    grid-template-columns: 1fr;
  }
}

.info-card {
  background: var(--task-card-muted-bg, #f7fafc);
  border: 1px solid var(--task-card-border, #e4e6e6);
  border-radius: var(--radius-md, 8px);
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

/* avatar-group-hover：悬停头像上浮放大，其余下沉 */
.members-list.t-avatar-group:hover .t-avatar {
  --shift: 6px;
}
.members-list.t-avatar-group .t-avatar:hover {
  --shift: -6px;
  --scale-active: 1.12;
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
  border-radius: var(--radius-md, 8px);
  cursor: pointer;
  transition: all var(--motion-instant, 150ms);
  font-size: 14px;
}

.phase-select-item:hover {
  border-color: var(--main-color, #24839b);
}
.phase-select-item:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 2px;
}

.phase-select-item.current {
  background: var(--color-accent-10, #eef4ff);
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
  background: var(--task-card-muted-bg, #f6f8fa);
  border-radius: var(--radius-md, 8px);
  margin-top: 4px;
}
.assign-count {
  font-size: var(--task-font-size-sm, 12px);
  color: var(--gray-500, #718096);
  margin-left: 4px;
}
.text-gray { color: var(--gray-400, #a0aec0); }

.priority-urgent {
  font-weight: 600;
}
.due-overdue {
  color: var(--color-error-500, #e53e3e);
  font-weight: 600;
}
</style>
