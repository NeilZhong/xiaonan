<script setup>
/**
 * ★ 任务详情页 — POLICE_REQUIREMENTS §8.4.4
 * 支持多人/多智能体协同执行、智能体自动执行、动态审核权限
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePoliceStore } from '@/stores/police'
import { policeTaskApi, policeAgentApi, policeCaseApi } from '@/apis/police_api'
import { message } from 'ant-design-vue'
import {
  ArrowLeft,
  Calendar,
  User,
  Bot,
  Briefcase,
  CheckCircle2,
  Play,
  FileCheck,
  Clock,
  AlertTriangle,
  Flag,
  Users,
  Zap
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const policeStore = usePoliceStore()

const task = computed(() => policeStore.currentTask)
const events = ref([])
const loading = ref(false)
const eventsLoading = ref(false)

// 审核弹窗
const reviewModalVisible = ref(false)
const reviewApproved = ref(true)
const reviewComment = ref('')
const reviewLoading = ref(false)

// 完成弹窗
const completeModalVisible = ref(false)
const completeResult = ref('')
const completeLoading = ref(false)

// 分配弹窗（多人+多智能体）
const assignModalVisible = ref(false)
const assignLoading = ref(false)
const assignForm = ref({
  selectedHumans: [],
  selectedAgents: [],
})
const agentOptions = ref([])
const agentsLoading = ref(false)
const caseMembers = ref([])
const membersLoading = ref(false)

// 智能体执行状态
const agentExecuting = ref(false)

// ── 状态映射 ──────────────────────────────────────────────
const statusMap = {
  pending: { text: '待处理', color: 'default' },
  in_progress: { text: '进行中', color: 'processing' },
  review: { text: '待审核', color: 'warning' },
  completed: { text: '已完成', color: 'success' },
  blocked: { text: '已驳回', color: 'error' },
  cancelled: { text: '已取消', color: 'default' }
}

const priorityMap = {
  urgent: { text: '紧急', color: 'red' },
  high: { text: '高', color: 'orange' },
  medium: { text: '中', color: 'blue' },
  low: { text: '低', color: 'default' }
}

// ── 计算属性：执行人信息 ────────────────────────────────
const statusInfo = computed(() => statusMap[task.value?.status] || statusMap.pending)
const priorityInfo = computed(() => priorityMap[task.value?.priority] || priorityMap.medium)

/** 任务的全部执行人（从 assignees 数组取，兼容旧单字段） */
const assignees = computed(() => task.value?.assignees || [])
/** 民警执行人列表 */
const humanAssignees = computed(() => assignees.value.filter(a => a.assignee_type === 'human'))
/** 智能体执行人列表 */
const agentAssignees = computed(() => assignees.value.filter(a => a.assignee_type === 'agent'))
/** 是否有智能体参与 */
const hasAgentAssignee = computed(() => agentAssignees.value.length > 0)
/** 是否有民警参与 */
const hasHumanAssignee = computed(() => humanAssignees.value.length > 0)

/** 格式化执行人显示文本 */
const assigneeDisplayText = computed(() => {
  if (assignees.value.length === 0) return task.value?.assignee_name || '未分配'
  const names = assignees.value.map(a => a.assignee_name).filter(Boolean)
  if (names.length <= 2) return names.join('、')
  return `${names[0]} 等 ${names.length} 名`
})

// ── 按钮权限（核心业务逻辑） ──────────────────────────
const canStart = computed(() => task.value?.status === 'pending')
const canComplete = computed(() => task.value?.status === 'in_progress')
const canReview = computed(() => task.value?.status === 'review')
const canAssign = computed(() => !!task.value && task.value.status !== 'completed')

/** 开始任务按钮文案：根据是否有智能体显示不同提示 */
const startButtonText = computed(() => {
  if (hasAgentAssignee.value) return '开始执行（智能体将自动运行）'
  return '开始执行'
})

// ── 数据加载 ──────────────────────────────────────────────
async function loadTask() {
  loading.value = true
  try {
    const taskId = route.params.taskId
    await policeStore.loadTask(taskId)
    if (!policeStore.currentTask) {
      message.error('任务不存在')
      router.replace('/police/cases')
    }
  } catch (e) {
    message.error('加载任务失败')
  } finally {
    loading.value = false
  }
}

async function loadEvents() {
  eventsLoading.value = true
  try {
    const taskId = route.params.taskId
    const res = await policeTaskApi.events(taskId)
    events.value = res.data || []
  } catch (e) {
    console.error('加载事件失败', e)
  } finally {
    eventsLoading.value = false
  }
}

// ── 操作 ──────────────────────────────────────────────────
async function handleStart() {
  try {
    agentExecuting.value = hasAgentAssignee.value
    await policeStore.startTask(route.params.taskId)
    message.success(hasAgentAssignee.value ? '任务已启动，智能体正在自动执行...' : '任务已开始执行')
    await loadTask()
    await loadEvents()
    // 如果有智能体，几秒后刷新状态检查是否已完成
    if (hasAgentAssignee.value) {
      setTimeout(async () => {
        await loadTask()
        agentExecuting.value = false
        if (task.value?.status === 'review') {
          message.info('智能体执行完成，待审核')
        }
      }, 3000)
    }
  } catch (e) {
    message.error('操作失败')
    agentExecuting.value = false
  }
}

function showCompleteModal() {
  completeResult.value = ''
  completeModalVisible.value = true
}

async function handleComplete() {
  completeLoading.value = true
  try {
    await policeStore.completeTask(route.params.taskId, completeResult.value)
    message.success('任务已完成，等待审核')
    completeModalVisible.value = false
    await loadTask()
    await loadEvents()
  } catch (e) {
    message.error('操作失败')
  } finally {
    completeLoading.value = false
  }
}

function showReviewModal(approved) {
  reviewApproved.value = approved
  reviewComment.value = ''
  reviewModalVisible.value = true
}

async function handleReview() {
  reviewLoading.value = true
  try {
    await policeStore.reviewTask(route.params.taskId, reviewApproved.value, reviewComment.value)
    message.success(reviewApproved.value ? '审核通过' : '已驳回')
    reviewModalVisible.value = false
    await loadTask()
    await loadEvents()
  } catch (e) {
    message.error('操作失败')
  } finally {
    reviewLoading.value = false
  }
}

// ── 多人分配 ──────────────────────────────────────────────
function showAssignModal() {
  // 预填已有执行人
  const existing = task.value?.assignees || []
  assignForm.value = {
    selectedHumans: existing.filter(a => a.assignee_type === 'human').map(a => ({
      value: a.assignee_id, label: a.assignee_name, name: a.assignee_name,
    })),
    selectedAgents: existing.filter(a => a.assignee_type === 'agent').map(a => ({
      value: a.assignee_id, label: a.assignee_name, name: a.assignee_name,
    })),
  }
  assignModalVisible.value = true
  loadAssignOptions()
}

async function loadAssignOptions() {
  agentsLoading.value = true
  membersLoading.value = true
  try {
    const [agentsRes, caseRes] = await Promise.allSettled([
      policeAgentApi.list({ page_size: 50 }),
      task.value?.case_id ? policeCaseApi.get(task.value.case_id) : Promise.reject('no_case'),
    ])
    if (agentsRes.status === 'fulfilled') {
      agentOptions.value = (agentsRes.value.items || []).map(a => ({
        label: `${a.name || a.display_name || '未命名'} (${a.type || '-'})`,
        value: a.id,
        name: a.name || a.display_name || '',
      }))
    }
    if (caseRes.status === 'fulfilled') {
      caseMembers.value = (caseRes.value.members || []).map(m => ({
        label: `${m.username || '未命名'} (${{ commander:'指挥员', handler:'办案人', reviewer:'审核员', observer:'观察员' }[m.role] || m.role})`,
        value: m.user_id,
        name: m.username || '',
      }))
    }
  } catch (e) {
    // 加载失败不阻塞
  } finally {
    agentsLoading.value = false
    membersLoading.value = false
  }
}

function buildAssigneesPayload() {
  return [
    ...assignForm.value.selectedHumans.map(h => ({
      assignee_type: 'human', assignee_id: h.value,
      assignee_name: h.name || h.label || '', role: 'executor',
    })),
    ...assignForm.value.selectedAgents.map(a => ({
      assignee_type: 'agent', assignee_id: a.value,
      assignee_name: a.name || a.label || '', role: 'executor',
    })),
  ]
}

async function handleAssign() {
  const payload = buildAssigneesPayload()
  if (payload.length === 0) {
    message.warning('请至少选择一名办案民警或智能体')
    return
  }
  assignLoading.value = true
  try {
    await policeStore.assignTask(route.params.taskId, { assignees: payload })
    message.success(`任务已分配给 ${payload.length} 名执行人`)
    assignModalVisible.value = false
    await loadTask()
    await loadEvents()
  } catch (e) {
    message.error('分配失败')
  } finally {
    assignLoading.value = false
  }
}

function goBack() {
  if (task.value?.case_id) {
    router.push(`/police/cases/${task.value.case_id}`)
  } else {
    router.push('/police/cases')
  }
}

function goToCase() {
  if (task.value?.case_id) {
    router.push(`/police/cases/${task.value.case_id}`)
  }
}

function formatDateTime(dt) {
  if (!dt) return '-'
  return new Date(dt).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}

onMounted(() => {
  loadTask()
  loadEvents()
})
</script>

<template>
  <div class="task-detail-page">
    <!-- 顶部导航栏 -->
    <div class="page-header">
      <div class="header-left">
        <button class="back-btn" @click="goBack">
          <ArrowLeft :size="18" />
          <span>返回任务列表</span>
        </button>
      </div>
    </div>

    <div class="page-body" v-if="task">
      <!-- 主内容区 -->
      <div class="main-content">
        <!-- 任务标题区 -->
        <div class="task-header-card">
          <div class="task-title-row">
            <h1 class="task-title">{{ task.title }}</h1>
            <div class="task-badges">
              <a-tag :color="statusInfo.color">{{ statusInfo.text }}</a-tag>
              <a-tag :color="priorityInfo.color">
                <Flag :size="11" style="margin-right: 2px" />
                {{ priorityInfo.text }}
              </a-tag>
              <!-- 智能体执行中标记 -->
              <a-tag v-if="agentExecuting" color="processing">
                <Zap :size="11" style="margin-right: 2px" />
                AI 执行中
              </a-tag>
            </div>
          </div>
          <div class="task-meta-row">
            <span class="meta-item case-link" @click="goToCase">
              <Briefcase :size="14" />
              {{ task.case_name || `案件 #${task.case_id}` }}
            </span>
            <span class="meta-divider">|</span>
            <span class="meta-item" :title="`共 ${assignees.length} 名执行人`">
              <Users :size="14" />
              {{ assigneeDisplayText }}
            </span>
            <span class="meta-divider" v-if="task.due_date">|</span>
            <span class="meta-item" v-if="task.due_date">
              <Calendar :size="14" />
              截止 {{ formatDateTime(task.due_date) }}
            </span>
          </div>
        </div>

        <!-- 操作按钮区 -->
        <div class="action-bar" v-if="canStart || canComplete || canReview || canAssign">
          <a-button v-if="canAssign" @click="showAssignModal">
            <User :size="15" style="margin-right: 4px" />
            分配任务
          </a-button>
          <a-button v-if="canStart" type="primary" @click="handleStart">
            <Play :size="15" style="margin-right: 4px" />
            {{ startButtonText }}
          </a-button>
          <a-button v-if="canComplete" type="primary" @click="showCompleteModal">
            <CheckCircle2 :size="15" style="margin-right: 4px" />
            提交完成
          </a-button>
          <template v-if="canReview">
            <a-button type="primary" @click="showReviewModal(true)">
              <FileCheck :size="15" style="margin-right: 4px" />
              审核通过
            </a-button>
            <a-button danger @click="showReviewModal(false)">
              <AlertTriangle :size="15" style="margin-right: 4px" />
              驳回
            </a-button>
          </template>
        </div>

        <!-- ★ 执行人团队卡片 -->
        <div class="info-card assignee-card" v-if="assignees.length > 0">
          <div class="card-label"><Users :size="15" /> 执行团队</div>
          <div class="card-content">
            <div class="assignee-group" v-if="humanAssignees.length">
              <div class="assignee-group-label">办案民警</div>
              <div class="assignee-tags">
                <a-tag v-for="h in humanAssignees" :key="h.id" color="blue">
                  <User :size="12" /> {{ h.assignee_name }}{{ h.role !== 'executor' ? ` (${h.role})` : '' }}
                </a-tag>
              </div>
            </div>
            <div class="assignee-group" v-if="agentAssignees.length">
              <div class="assignee-group-label">数字警员</div>
              <div class="assignee-tags">
                <a-tag v-for="a in agentAssignees" :key="a.id" :color="agentExecuting ? 'processing' : 'purple'">
                  <Bot :size="12" /> {{ a.assignee_name }}
                  <span v-if="agentExecuting" class="agent-running-dot"></span>
                </a-tag>
              </div>
            </div>
            <div class="review-hint" v-if="task.status === 'review'">
              <FileCheck :size="13" />
              <span v-if="hasHumanAssignee">由以上民警审核成果</span>
              <span v-else>由案件指挥员审核成果（纯智能体任务）</span>
            </div>
          </div>
        </div>

        <!-- 任务描述 -->
        <div class="info-card" v-if="task.description">
          <div class="card-label">任务描述</div>
          <div class="card-content description-text">{{ task.description }}</div>
        </div>

        <!-- 任务结果 -->
        <div class="info-card result-card" v-if="task.result">
          <div class="card-label">
            <CheckCircle2 :size="15" />
            执行结果
            <a-tag v-if="task.result?.executed_by === 'agent_auto'" size="small" color="purple" style="margin-left: 8px">
              <Zap :size="10" /> 智能体自动生成
            </a-tag>
          </div>
          <div class="card-content description-text">
            <template v-if="typeof task.result === 'string'">{{ task.result }}</template>
            <template v-else>
              <div v-if="task.result.summary">{{ task.result.summary }}</div>
              <details v-if="task.result.agent_results?.length" style="margin-top: 8px">
                <summary style="cursor: pointer; color: #24839b;">查看各智能体详细结果 ({{ task.result.agent_results.length }})</summary>
                <div v-for="(ar, idx) in task.result.agent_results" :key="idx" style="margin-top: 8px; padding: 8px; background: #f6f8fa; border-radius: 6px;">
                  <strong>{{ ar.agent_name }}</strong>
                  <pre v-if="ar.result" style="white-space: pre-wrap; font-size: 12px; margin-top: 4px;">{{ ar.result }}</pre>
                  <span v-if="ar.error" style="color: #e53e3e;">执行错误: {{ ar.error }}</span>
                </div>
              </details>
            </template>
          </div>
        </div>

        <!-- 审核信息 -->
        <div class="info-card review-card" v-if="task.reviewed_by">
          <div class="card-label">
            <FileCheck :size="15" />
            审核信息
          </div>
          <div class="card-content">
            <div class="review-row">
              <span class="review-label">审核人：</span>
              <span>{{ task.reviewed_by_name || task.reviewed_by }}</span>
            </div>
            <div class="review-row">
              <span class="review-label">审核时间：</span>
              <span>{{ formatDateTime(task.reviewed_at) }}</span>
            </div>
            <div class="review-row" v-if="task.signed_hash">
              <span class="review-label">签名哈希：</span>
              <code class="hash-text">{{ task.signed_hash }}</code>
            </div>
          </div>
        </div>

        <!-- 事件时间线 -->
        <div class="info-card">
          <div class="card-label">
            <Clock :size="15" />
            事件时间线
          </div>
          <div class="card-content">
            <a-empty v-if="!eventsLoading && events.length === 0" description="暂无事件" />
            <a-timeline v-else>
              <a-timeline-item
                v-for="(evt, idx) in events"
                :key="idx"
                :color="eventTypeMap[evt.event_type]?.color || 'gray'"
              >
                <div class="event-item">
                  <div class="event-header">
                    <span class="event-type">{{ eventTypeMap[evt.event_type]?.text || evt.event_type }}</span>
                    <span class="event-time">{{ formatDateTime(evt.created_at) }}</span>
                  </div>
                  <div class="event-desc" v-if="evt.event_data">
                    <template v-if="evt.event_type === 'assigned'">
                      <span v-if="evt.event_data.assignees">
                        分配给 {{ evt.event_data.count || evt.event_data.assignees?.length }} 名执行人
                      </span>
                      <span v-else>分配给：{{ evt.event_data.assignee_name || evt.event_data.assignee_id }}</span>
                    </template>
                    <template v-else-if="evt.event_type === 'reviewed'">
                      {{ evt.event_data.approved ? '审核通过' : '已驳回' }}
                      <span v-if="evt.event_data.comment"> — {{ evt.event_data.comment }}</span>
                    </template>
                    <template v-else-if="evt.event_type === 'completed' && evt.event_data.result">
                      结果：{{ typeof evt.event_data.result === 'object' ? '已完成（含结构化结果）' : evt.event_data.result }}
                    </template>
                    <template v-else-if="evt.event_type === 'phase_changed'">
                      {{ evt.event_data.from }} → {{ evt.event_data.to }}
                    </template>
                  </div>
                  <div class="event-actor" v-if="evt.created_by_name">
                    by {{ evt.created_by_name }}
                  </div>
                </div>
              </a-timeline-item>
            </a-timeline>
          </div>
        </div>
      </div>

      <!-- 侧边信息栏 -->
      <div class="sidebar">
        <div class="sidebar-card">
          <div class="sidebar-title">任务信息</div>
          <div class="info-list">
            <div class="info-row">
              <span class="info-key">任务类型</span>
              <span class="info-val">{{ task.type || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-key">案件阶段</span>
              <span class="info-val">{{ task.phase || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-key">执行人数</span>
              <span class="info-val">{{ assignees.length > 0 ? `${assignees.length} 人` : (task.assignee_name || '-') }}</span>
            </div>
            <div class="info-row">
              <span class="info-key">创建人</span>
              <span class="info-val">{{ task.created_by_name || task.created_by || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-key">创建时间</span>
              <span class="info-val">{{ formatDateTime(task.created_at) }}</span>
            </div>
            <div class="info-row">
              <span class="info-key">更新时间</span>
              <span class="info-val">{{ formatDateTime(task.updated_at) }}</span>
            </div>
            <div class="info-row" v-if="task.due_date">
              <span class="info-key">截止时间</span>
              <span class="info-val">{{ formatDateTime(task.due_date) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 加载中 -->
    <div class="loading-state" v-if="loading">
      <a-spin size="large" tip="加载中..." />
    </div>

    <!-- 完成弹窗 -->
    <a-modal
      v-model:open="completeModalVisible"
      title="提交任务完成"
      :confirm-loading="completeLoading"
      @ok="handleComplete"
      ok-text="提交"
      cancel-text="取消"
    >
      <a-textarea
        v-model:value="completeResult"
        placeholder="请输入任务执行结果..."
        :rows="5"
        :maxlength="2000"
        show-count
      />
    </a-modal>

    <!-- 审核弹窗 -->
    <a-modal
      v-model:open="reviewModalVisible"
      :title="reviewApproved ? '审核通过' : '驳回任务'"
      :confirm-loading="reviewLoading"
      @ok="handleReview"
      ok-text="确认"
      cancel-text="取消"
      :ok-button-props="{ danger: !reviewApproved }"
    >
      <a-textarea
        v-model:value="reviewComment"
        :placeholder="reviewApproved ? '审核备注（可选）...' : '请输入驳回原因...'"
        :rows="5"
        :maxlength="500"
        show-count
      />
    </a-modal>

    <!-- 分配弹窗（多人+多智能体） -->
    <a-modal
      v-model:open="assignModalVisible"
      title="分配任务"
      :confirm-loading="assignLoading"
      @ok="handleAssign"
      ok-text="确认分配"
      cancel-text="取消"
      width="520px"
    >
      <a-form layout="vertical" style="margin-top: 16px">
        <a-form-item label="办案民警（可多选）">
          <a-select
            mode="multiple"
            v-model:value="assignForm.selectedHumans"
            :options="caseMembers"
            placeholder="选择要分配的办案民警"
            :loading="membersLoading"
            allow-clear
            show-search
            option-filter-prop="label"
            :not-found-content="membersLoading ? '加载中...' : '暂无案件成员'"
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
            <User :size="12" /> {{ h.label }}
          </a-tag>
          <a-tag v-for="a in assignForm.selectedAgents" :key="'a'+a.value" color="purple">
            <Bot :size="12" /> {{ a.label }}
          </a-tag>
          <span class="assign-count">共 {{ assignForm.selectedHumans.length + assignForm.selectedAgents.length }} 名执行人</span>
        </div>
      </a-form>
    </a-modal>
  </div>
</template>

<style lang="less" scoped>
@police-bg: #f7f8fa;
@police-border: #e8e8ec;
@police-text: #1a1a2e;
@police-text-secondary: #6b7280;
@police-primary: #24839b;

.task-detail-page {
  height: 100%;
  overflow-y: auto;
  background: @police-bg;
  display: flex;
  flex-direction: column;
}

.page-header {
  flex-shrink: 0;
  padding: 16px 32px;
  background: #fff;
  border-bottom: 1px solid @police-border;

  .back-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border: 1px solid @police-border;
    border-radius: 8px;
    background: transparent;
    color: @police-text-secondary;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      border-color: @police-primary;
      color: @police-primary;
      background: fade(@police-primary, 4%);
    }
  }
}

.page-body {
  flex: 1;
  display: flex;
  gap: 24px;
  padding: 24px 32px;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
}

.main-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sidebar {
  flex: 0 0 280px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

// ── 任务标题卡片 ──
.task-header-card {
  background: #fff;
  border: 1px solid @police-border;
  border-radius: 12px;
  padding: 24px;

  .task-title-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 12px;
  }

  .task-title {
    margin: 0;
    font-size: 22px;
    font-weight: 650;
    color: @police-text;
    line-height: 1.4;
    flex: 1;
  }

  .task-badges {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
  }

  .task-meta-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    font-size: 13px;
    color: @police-text-secondary;

    .meta-item {
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .case-link {
      cursor: pointer;
      color: @police-primary;
      &:hover { text-decoration: underline; }
    }

    .meta-divider {
      color: #d1d5db;
    }
  }
}

// ── 操作栏 ──
.action-bar {
  display: flex;
  gap: 12px;
  padding: 16px 24px;
  background: #fff;
  border: 1px solid @police-border;
  border-radius: 12px;
}

// ── 信息卡片 ──
.info-card {
  background: #fff;
  border: 1px solid @police-border;
  border-radius: 12px;
  padding: 20px 24px;

  &.assignee-card {
    border-color: fade(@police-primary, 20%);
    background: fade(@police-primary, 1%);
  }

  .card-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    font-weight: 600;
    color: @police-text-secondary;
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .card-content {
    font-size: 14px;
    color: @police-text;
    line-height: 1.7;
  }

  .description-text {
    white-space: pre-wrap;
    word-break: break-word;
  }

  &.result-card {
    border-color: fade(@police-primary, 20%);
    background: fade(@police-primary, 2%);
  }

  &.review-card {
    border-color: fade(#52c41a, 20%);
    background: fade(#52c41a, 2%);
  }
}

// ── 执行人团队 ──
.assignee-card {
  .assignee-group {
    margin-bottom: 10px;

    &:last-child { margin-bottom: 0; }
  }

  .assignee-group-label {
    font-size: 11px;
    font-weight: 600;
    color: @police-text-secondary;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
  }

  .assignee-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .review-hint {
    margin-top: 12px;
    padding: 10px 14px;
    background: #fffbe6;
    border: 1px solid #ffe58f;
    border-radius: 8px;
    font-size: 13px;
    color: #ad6800;
    display: flex;
    align-items: center;
    gap: 6px;
  }
}

.agent-running-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #1890ff;
  animation: pulse 1s infinite;
  margin-left: 4px;
  vertical-align: middle;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

// ── 分配弹窗 ──
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

// ── 审核行 ──
.review-row {
  display: flex;
  margin-bottom: 8px;
  font-size: 14px;

  &:last-child { margin-bottom: 0; }

  .review-label {
    flex: 0 0 80px;
    color: @police-text-secondary;
  }

  .hash-text {
    font-family: 'SF Mono', 'Consolas', monospace;
    font-size: 12px;
    color: @police-text-secondary;
    background: #f3f4f6;
    padding: 2px 8px;
    border-radius: 4px;
    word-break: break-all;
  }
}

// ── 事件时间线 ──
.event-item {
  .event-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 4px;
  }

  .event-type {
    font-size: 14px;
    font-weight: 500;
    color: @police-text;
  }

  .event-time {
    font-size: 12px;
    color: @police-text-secondary;
  }

  .event-desc {
    font-size: 13px;
    color: @police-text-secondary;
    line-height: 1.5;
  }

  .event-actor {
    font-size: 12px;
    color: #9ca3af;
    margin-top: 2px;
  }
}

// ── 侧边栏 ──
.sidebar-card {
  background: #fff;
  border: 1px solid @police-border;
  border-radius: 12px;
  padding: 20px;

  .sidebar-title {
    font-size: 14px;
    font-weight: 600;
    color: @police-text;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid @police-border;
  }
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  font-size: 13px;

  .info-key {
    color: @police-text-secondary;
    flex-shrink: 0;
  }

  .info-val {
    color: @police-text;
    text-align: right;
    word-break: break-word;
  }
}

// ── 加载状态 ──
.loading-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
}
</style>
