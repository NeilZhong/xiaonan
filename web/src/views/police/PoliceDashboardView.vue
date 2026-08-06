<script setup>
/**
 * ★ 公安个人工作台 — 四组待办聚合 (POLICE_REQUIREMENTS §8.4.1)
 * 待审查(推进智能体草案) / 待审核 / 待处理 / 通知
 * 通过 useRealtime 准实时刷新。
 *
 * v2 设计：
 *  - 渐变欢迎横幅 + 5 项统计卡片（含「我的案件」真实数据）
 *  - 左主列：待处理任务 + 我的案件（近期）
 *  - 右辅列：待审查草案 + 待审核（含智能体全局共享审批）+ 通知
 *  - 底部：常用数字警员快捷入口 + 快捷操作（全部修复为真实路由）
 */
import { onMounted, computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { usePoliceStore } from '@/stores/police'
import { useUserStore } from '@/stores/user'
import { useRealtime } from '@/composables/useRealtime'
import { policeAgentApi, policeCaseApi, policeDashboardApi } from '@/apis/police_api'
import TaskCard from '@/components/police/TaskCard.vue'
import {
  InboxOutlined, ClockCircleOutlined, FileSearchOutlined,
  ExclamationCircleOutlined, CheckCircleOutlined, PlusOutlined, UploadOutlined, BellOutlined,
  FolderOpenOutlined, RobotOutlined, BookOutlined, MessageOutlined,
  ArrowRightOutlined, DatabaseOutlined, AppstoreOutlined
} from '@ant-design/icons-vue'

const router = useRouter()
const policeStore = usePoliceStore()
const userStore = useUserStore()

const isSuperAdmin = computed(() => userStore.isSuperAdmin)

// ── 工作台三 Tab（模块 G+F）────────────────────────
const activeTab = ref('office')
const tabOptions = [
  { label: '日常办公', value: 'office' },
  { label: '能力演进', value: 'evolution' },
  { label: '智能孵化', value: 'incubation' },
]
const evolutionInput = ref('')
const evolutionData = ref({ skill_diagnostics: {}, connectors: {}, partners: [] })
const incubateInput = ref('')
const incubateMode = ref('create')
const incubateExamples = [
  '帮我孵化一个笔录分析数字民警',
  '帮我孵化一个资金追踪助手',
  '帮我孵化一个法制审核专家',
]
const draftResult = ref(null)
const incubationItems = ref([])

async function onTabChange() {
  if (activeTab.value === 'evolution' && !evolutionData.value.skill_diagnostics?.template_count) {
    loadEvolution()
  }
  if (activeTab.value === 'incubation') {
    loadIncubation()
  }
}

async function loadEvolution() {
  try {
    const res = await policeDashboardApi.evolution()
    evolutionData.value = res.data || {}
  } catch (e) {
    message.error('加载能力演进失败: ' + (e.message || e))
  }
}

async function loadIncubation() {
  try {
    const res = await policeDashboardApi.incubation()
    incubationItems.value = res.data?.items || []
  } catch (e) {
    message.error('加载智能孵化失败: ' + (e.message || e))
  }
}

function onEvolutionSearch() {
  if (!evolutionInput.value.trim()) return
  message.info('能力沉淀建议生成依赖 LLM，当前为规则化 MVP——请前往「办案复盘」手动触发沉淀')
}

async function incubateCreate() {
  if (!incubateInput.value.trim()) {
    message.warning('请先描述想孵化的数字民警')
    return
  }
  try {
    const res = await policeDashboardApi.incubateCreate(incubateInput.value.trim())
    draftResult.value = res.draft || null
    if (!draftResult.value) message.warning('未生成草案，请调整描述')
  } catch (e) {
    message.error('孵化失败: ' + (e.message || e))
  }
}

async function confirmDraft() {
  // 保存为草稿：调现有数字民警创建接口（status=draft）
  try {
    await policeAgentApi.create({
      name: draftResult.value.name,
      description: draftResult.value.description,
      type: 'incubation',
      category: draftResult.value.department_tag || '综合',
      system_prompt: draftResult.value.system_prompt,
      status: 'draft',
    })
    message.success('草稿已保存，可在「智能体」中继续完善')
    draftResult.value = null
    loadIncubation()
  } catch (e) {
    message.error('保存失败: ' + (e.message || e))
  }
}

function goTemplates() { router.push('/police/task-templates') }
function goRuntimeConsole() { router.push('/police/runtime-console') }
function goPartners() { router.push('/police/partners') }
function goProfile(item) { router.push(`/agent-manage/${item.id}`) }
function goChat(item) { router.push({ path: '/agent', query: { agent_id: item.badge_number || item.id } }) }
function goPublish(item) { router.push(`/agent-manage/${item.id}?publish=1`) }

// ── 智能体全局共享审批（仅超级管理员可见）────────────
const pendingAgents = ref([])
const approvingAgentId = ref(null)

async function loadPendingAgents() {
  if (!isSuperAdmin.value) {
    pendingAgents.value = []
    return
  }
  try {
    const res = await policeAgentApi.listPending({ page_size: 20 })
    pendingAgents.value = res.items || []
  } catch (e) {
    pendingAgents.value = []
  }
}

async function approveAgentShare(agent, approved) {
  approvingAgentId.value = agent.id
  try {
    await policeAgentApi.approveAgent(agent.id, {
      approved,
      reviewer_id: userStore.user?.id
    })
    message.success(approved ? '已通过全局共享，该智能体已上架并授予警号' : '已驳回全局共享申请')
    await loadPendingAgents()
  } catch (e) {
    message.error(e?.message || '操作失败')
  } finally {
    approvingAgentId.value = null
  }
}

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return '上午好'
  if (h < 18) return '下午好'
  return '晚上好'
})
const userName = computed(() => userStore.username || '警官')
const departmentName = computed(() => userStore.departmentName || '公安业务协作平台')
const todayText = computed(() =>
  new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
)

// ── 我的案件（近期）────────────────────────────────
const myCases = ref([])
const myCasesTotal = ref(0)

async function loadMyCases() {
  try {
    const res = await policeCaseApi.list({ page: 1, page_size: 5, mine: true })
    myCases.value = res?.data?.items || res?.items || []
    myCasesTotal.value = res?.data?.total || res?.total || 0
  } catch (e) {
    myCases.value = []
    myCasesTotal.value = 0
  }
}

const caseStatusText = { draft: '草稿', investigation: '侦查中', arrest: '抓捕', handling: '办理中', prosecution: '待移送', closed: '已结案' }
const caseStatusColor = { draft: 'default', investigation: 'processing', arrest: 'warning', handling: 'blue', prosecution: 'orange', closed: 'success' }
const casePhaseText = { research: '研判', arrest: '抓捕', handling: '办理', prosecution: '移送' }

// ── 常用数字警员（快捷对话入口）────────────────────
const topAgents = ref([])

async function loadTopAgents() {
  try {
    const res = await policeAgentApi.list({ page: 1, page_size: 6 })
    topAgents.value = (res.items || res.agents || []).slice(0, 6)
  } catch (e) {
    topAgents.value = []
  }
}

function goAgentChat(agent) {
  const chatId = agent?.slug || agent?.agent_id || agent?.id
  if (!chatId) return
  router.push({ path: '/agent', query: { agent_id: chatId } })
}

// ── 统计卡片 ───────────────────────────────────────
const statCards = computed(() => [
  { title: '待审查', value: policeStore.myDrafts.length, icon: InboxOutlined, color: '#B7791F', bg: '#FEF3C7' },
  { title: '待办任务', value: policeStore.stats.my_pending_count, icon: ClockCircleOutlined, color: '#D69E2E', bg: '#FEFCE8' },
  { title: '进行中', value: policeStore.stats.my_in_progress_count, icon: FileSearchOutlined, color: '#3182CE', bg: '#EBF8FF' },
  { title: '待审核', value: policeStore.stats.review_count, icon: ExclamationCircleOutlined, color: '#E53E3E', bg: '#FED7D7' },
  { title: '我的案件', value: myCasesTotal, icon: FolderOpenOutlined, color: '#38A169', bg: '#F0FFF4' },
])

// 待处理 = 分配给我的待开始 / 进行中任务
const myActiveTasks = computed(() =>
  policeStore.myTasks.filter((t) => ['pending', 'in_progress'].includes(t.status))
)

// 通知 = 推进智能体活动（按案件聚合的待审查草案提醒）
const notifications = computed(() => {
  const byCase = {}
  for (const d of policeStore.myDrafts) {
    byCase[d.case_id] = (byCase[d.case_id] || 0) + 1
  }
  return Object.entries(byCase).map(([cid, n]) => ({
    case_id: Number(cid),
    count: n,
    text: `案件 #${cid} 有 ${n} 条待审查任务草案（推进智能体生成）`,
  }))
})

// 任务详情路由保留（/police/tasks/:taskId）；全局任务看板已移除，
// “查看看板/查看全部”统一跳转到案件详情（案件内自带该案件的任务看板）。
function goTask(task) {
  router.push(`/police/tasks/${task.id}`)
}
function goDraft(task) {
  router.push(`/police/tasks/${task.id}`)
}
function goCaseTasks(caseId) {
  router.push(`/police/cases/${caseId}`)
}
function goCase(caseItem) {
  router.push(`/police/cases/${caseItem.id}`)
}
function goCreateCase() {
  router.push({ path: '/police/cases', query: { create: '1' } })
}

// ── 快捷操作（全部为真实路由）──────────────────────
const quickActions = computed(() => {
  const items = [
    { title: '创建案件', icon: PlusOutlined, color: '#3182CE', onClick: goCreateCase },
    { title: '导入笔录', icon: UploadOutlined, color: '#B7791F', to: '/police/import' },
    { title: '案件管理', icon: FolderOpenOutlined, color: '#38A169', to: '/police/cases' },
    { title: '智能体管理', icon: RobotOutlined, color: '#805AD5', to: '/agent-manage' },
    { title: '新建对话', icon: MessageOutlined, color: '#24839B', to: '/agent' },
    { title: '知识库 · 技能', icon: BookOutlined, color: '#DD6B20', to: '/extensions' },
  ]
  if (userStore.isAdmin) {
    items.push({ title: '任务模板', icon: AppstoreOutlined, color: '#2C5282', to: '/police/task-templates' })
    items.push({ title: '运行时控制台', icon: DatabaseOutlined, color: '#6B46C1', to: '/police/runtime-console' })
  }
  return items
})

function runQuickAction(action) {
  if (action.onClick) return action.onClick()
  router.push(action.to)
}

// ── 工作台内联审核（普通用户也可审核，无需跳转任务详情）────────────
// 「待审核」列表由后端按 reviewer_id=当前用户 过滤，普通用户作为审核人时自然出现在此处。
const reviewModalVisible = ref(false)
const reviewTaskId = ref(null)
const reviewApproved = ref(true)
const reviewComment = ref('')
const reviewLoading = ref(false)
const reviewTaskDetail = ref(null)

function openReview(task, approved) {
  reviewTaskId.value = task.id
  reviewApproved.value = approved
  reviewComment.value = ''
  reviewTaskDetail.value = null
  reviewModalVisible.value = true
  // 拉取完整任务（含 AI 产出 result）用于审核预览
  policeStore.loadTask(task.id)
    .then(() => { reviewTaskDetail.value = policeStore.currentTask })
    .catch(() => {})
}

async function handleDashboardReview() {
  if (!reviewTaskId.value) return
  reviewLoading.value = true
  try {
    await policeStore.reviewTask(reviewTaskId.value, reviewApproved.value, reviewComment.value)
    message.success(reviewApproved.value ? '审核通过' : '已驳回')
    reviewModalVisible.value = false
    // 刷新工作台：待审核 / 统计 / 我的任务
    await Promise.all([
      policeStore.loadReviewTasks(1, 6, true),
      policeStore.loadStats(true),
      policeStore.loadMyTasks(1, 10, true),
    ])
  } catch (e) {
    message.error(e?.message || '审核失败')
  } finally {
    reviewLoading.value = false
  }
}

// ── 准实时刷新（后台轮询，遇 401 静默处理、不触发全局登出）────────────
useRealtime(() => policeStore.loadMyDrafts(true), { interval: 30000 })
useRealtime(() => policeStore.loadReviewTasks(1, 6, true), { interval: 30000 })
useRealtime(() => policeStore.loadMyTasks(1, 10, true), { interval: 30000 })
useRealtime(() => policeStore.loadStats(true), { interval: 60000 })
useRealtime(() => loadPendingAgents(), { interval: 30000 })
useRealtime(() => loadMyCases(), { interval: 60000 })
useRealtime(() => loadTopAgents(), { interval: 60000 })

onMounted(() => {
  loadPendingAgents()
  loadMyCases()
  loadTopAgents()
})
</script>

<template>
  <div class="police-dashboard">
    <!-- 顶部三 Tab：日常办公 / 能力演进 / 智能孵化（模块 G+F） -->
    <div class="dashboard-tabs">
      <a-segmented
        v-model:value="activeTab"
        :options="tabOptions"
        block
        @change="onTabChange"
      />
    </div>

    <!-- ===== Tab1 日常办公（原 v2 数据驾驶舱） ===== -->
    <div v-if="activeTab === 'office'">
    <!-- 顶部欢迎横幅 -->
    <div class="welcome-banner">
      <div class="banner-glow banner-glow-1"></div>
      <div class="banner-glow banner-glow-2"></div>
      <div class="banner-content">
        <div class="banner-text">
          <h1 class="banner-greeting">{{ greeting }}，{{ userName }}</h1>
          <p class="banner-meta">
            <span class="banner-dept">{{ departmentName }}</span>
            <span class="banner-date">{{ todayText }}</span>
          </p>
        </div>
        <div class="banner-actions">
          <a-button class="banner-btn banner-btn-ghost" @click="router.push('/police/import')">
            <template #icon><UploadOutlined /></template>
            导入笔录
          </a-button>
          <a-button class="banner-btn banner-btn-primary" @click="goCreateCase">
            <template #icon><PlusOutlined /></template>
            创建案件
          </a-button>
        </div>
      </div>
      <div class="banner-stats">
        <div v-for="card in statCards" :key="card.title" class="banner-stat">
          <span class="banner-stat-value">{{ card.value }}</span>
          <span class="banner-stat-label">{{ card.title }}</span>
        </div>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-cards">
      <div v-for="card in statCards" :key="card.title" class="stat-card">
        <div class="stat-icon" :style="{ background: card.bg, color: card.color }">
          <component :is="card.icon" />
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.title }}</div>
        </div>
      </div>
    </div>

    <!-- 主区域：左任务 + 右审核 -->
    <div class="dashboard-grid">
      <!-- 左列：待处理任务 -->
      <div class="dash-left">
        <div class="dashboard-panel">
          <div class="panel-header">
            <h3><ClockCircleOutlined class="panel-icon" /> 待处理</h3>
            <span class="panel-count">{{ myActiveTasks.length }}</span>
            <a-button type="link" size="small" class="panel-more" @click="router.push('/police/cases')">查看全部 <ArrowRightOutlined /></a-button>
          </div>
          <div class="panel-body">
            <div v-if="myActiveTasks.length === 0" class="empty-state">
              <a-empty :image="false" description="暂无待处理任务，一切就绪" />
            </div>
            <TaskCard
              v-for="task in myActiveTasks"
              :key="task.id"
              :task="task"
              @click="goTask"
            />
          </div>
        </div>

        <!-- 我的案件 -->
        <div class="dashboard-panel">
          <div class="panel-header">
            <h3><FolderOpenOutlined class="panel-icon" /> 我的案件</h3>
            <span class="panel-count">{{ myCasesTotal }}</span>
            <a-button type="link" size="small" class="panel-more" @click="router.push('/police/cases')">查看全部 <ArrowRightOutlined /></a-button>
          </div>
          <div class="panel-body">
            <div v-if="myCases.length === 0" class="empty-state">
              <a-empty :image="false" description="暂无参与的案件，点击右上角创建" />
            </div>
            <div v-for="c in myCases" :key="c.id" class="case-row" @click="goCase(c)">
              <div class="case-row-main">
                <div class="case-row-title">{{ c.title }}</div>
                <div class="case-row-meta">
                  <span class="case-number">{{ c.case_number }}</span>
                  <a-tag size="small">{{ casePhaseText[c.phase] || c.phase || '未分阶段' }}</a-tag>
                </div>
              </div>
              <a-badge :status="caseStatusColor[c.status] || 'default'" :text="caseStatusText[c.status] || c.status" />
            </div>
          </div>
        </div>
      </div>

      <!-- 右列：待审查 + 待审核 + 通知 -->
      <div class="dash-right">
        <!-- 待审查：推进智能体草案 -->
        <div class="dashboard-panel">
          <div class="panel-header">
            <h3><InboxOutlined class="panel-icon" /> 待审查</h3>
            <span class="panel-count">{{ policeStore.myDrafts.length }}</span>
            <a-button type="link" size="small" class="panel-more" @click="router.push('/police/cases')">查看案件</a-button>
          </div>
          <div class="panel-body">
            <div v-if="policeStore.myDrafts.length === 0" class="empty-state">
              <a-empty :image="false" description="暂无待审查草案" />
            </div>
            <TaskCard
              v-for="d in policeStore.myDrafts"
              :key="d.id"
              :task="d"
              @click="goDraft"
            />
          </div>
        </div>

        <!-- 待审核 -->
        <div class="dashboard-panel">
          <div class="panel-header">
            <h3><ExclamationCircleOutlined class="panel-icon" /> 待审核</h3>
            <span class="panel-count">{{ policeStore.reviewTasks.length }}</span>
            <a-button type="link" size="small" class="panel-more" @click="router.push('/police/cases')">查看全部</a-button>
          </div>
          <div class="panel-body">
            <div v-if="policeStore.reviewTasks.length === 0" class="empty-state">
              <a-empty :image="false" description="暂无待审核任务" />
            </div>
            <div
              v-for="task in policeStore.reviewTasks"
              :key="task.id"
              class="task-item review-item"
            >
              <div class="task-item-main">
                <div class="task-item-title">{{ task.title }}</div>
                <div class="task-item-meta">
                  <a-tag color="warning" size="small">待我审核</a-tag>
                  <span class="task-item-assignee">{{ task.assignee_name || '未分配' }}</span>
                </div>
              </div>
              <div class="task-item-actions">
                <a-button size="small" @click="goTask(task)">查看</a-button>
                <a-button type="primary" size="small" @click="openReview(task, true)">通过</a-button>
                <a-button danger size="small" @click="openReview(task, false)">驳回</a-button>
              </div>
            </div>

            <!-- 智能体全局共享审批（仅超级管理员可见） -->
            <template v-if="isSuperAdmin">
              <a-divider class="review-divider">智能体全局共享</a-divider>
              <div v-if="pendingAgents.length === 0" class="empty-state">
                <a-empty :image="false" description="暂无待审批的全局共享申请" />
              </div>
              <div
                v-for="agent in pendingAgents"
                :key="agent.id"
                class="task-item review-item agent-review-item"
              >
                <div class="task-item-main">
                  <div class="task-item-title">{{ agent.name }}</div>
                  <div class="task-item-meta">
                    <a-tag color="purple" size="small">待我审核</a-tag>
                    <span class="task-item-assignee">{{ agent.department || '全局共享' }}</span>
                    <span v-if="agent.applicant_name" class="task-item-assignee">申请人：{{ agent.applicant_name }}</span>
                  </div>
                </div>
                <div class="task-item-actions">
                  <a-button
                    type="primary"
                    size="small"
                    :loading="approvingAgentId === agent.id"
                    @click="approveAgentShare(agent, true)"
                  >通过</a-button>
                  <a-button
                    danger
                    size="small"
                    :loading="approvingAgentId === agent.id"
                    @click="approveAgentShare(agent, false)"
                  >驳回</a-button>
                </div>
              </div>
            </template>
          </div>
        </div>

        <!-- 通知：推进智能体活动 -->
        <div class="dashboard-panel">
          <div class="panel-header">
            <h3><BellOutlined class="panel-icon" /> 通知</h3>
            <span class="panel-count">{{ notifications.length }}</span>
          </div>
          <div class="panel-body">
            <div v-if="notifications.length === 0" class="empty-state">
              <a-empty :image="false" description="暂无新通知" />
            </div>
            <div
              v-for="n in notifications"
              :key="n.case_id"
              class="notify-item"
              @click="goCaseTasks(n.case_id)"
            >
              <BellOutlined class="notify-icon" />
              <span class="notify-text">{{ n.text }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部：常用数字警员 + 快捷操作 -->
    <div class="bottom-section">
      <!-- 常用数字警员 -->
      <div class="dashboard-panel agent-strip-panel">
        <div class="panel-header">
          <h3><RobotOutlined class="panel-icon" /> 常用数字警员</h3>
          <a-button type="link" size="small" class="panel-more" @click="router.push('/agent-manage')">全部智能体 <ArrowRightOutlined /></a-button>
        </div>
        <div class="panel-body">
          <div v-if="topAgents.length === 0" class="empty-state">
            <a-empty :image="false" description="暂无可用智能体" />
          </div>
          <div v-else class="agent-strip">
            <div
              v-for="agent in topAgents"
              :key="agent.id"
              class="agent-chip"
              @click="goAgentChat(agent)"
            >
              <div class="agent-chip-avatar">
                <img v-if="agent.icon" :src="agent.icon" :alt="agent.name" />
                <RobotOutlined v-else />
              </div>
              <div class="agent-chip-info">
                <div class="agent-chip-name">{{ agent.name }}</div>
                <div class="agent-chip-role">{{ agent.rank || agent.category || '数字警员' }}</div>
              </div>
              <MessageOutlined class="agent-chip-chat" />
            </div>
          </div>
        </div>
      </div>

      <!-- 快捷操作 -->
      <div class="dashboard-panel">
        <div class="panel-header">
          <h3><AppstoreOutlined class="panel-icon" /> 快捷操作</h3>
        </div>
        <div class="panel-body">
          <div class="quick-action-grid">
            <div
              v-for="action in quickActions"
              :key="action.title"
              class="quick-action-card"
              @click="runQuickAction(action)"
            >
              <component :is="action.icon" class="quick-action-icon" :style="{ color: action.color }" />
              <span>{{ action.title }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 工作台内联审核弹窗（普通用户也可审核，无需跳转任务详情） -->
    <a-modal
      v-model:open="reviewModalVisible"
      :title="reviewApproved ? '审核通过' : '驳回任务'"
      :confirm-loading="reviewLoading"
      :width="720"
      ok-text="确认"
      cancel-text="取消"
      :ok-button-props="{ danger: !reviewApproved }"
      @ok="handleDashboardReview"
    >
      <div v-if="reviewTaskDetail" class="review-modal-body">
        <div class="rm-task-title">{{ reviewTaskDetail.title }}</div>
        <div class="rm-section-label">执行结果（AI 产出）</div>
        <div class="rm-result">
          <template v-if="typeof reviewTaskDetail.result === 'string'">{{ reviewTaskDetail.result }}</template>
          <template v-else>
            <div v-if="reviewTaskDetail.result?.summary">{{ reviewTaskDetail.result.summary }}</div>
            <details v-if="reviewTaskDetail.result?.agent_results?.length" style="margin-top: 8px">
              <summary style="cursor: pointer; color: #24839b;">查看各智能体详细结果 ({{ reviewTaskDetail.result.agent_results.length }})</summary>
              <div v-for="(ar, idx) in reviewTaskDetail.result.agent_results" :key="idx" style="margin-top: 8px; padding: 8px; background: #f6f8fa; border-radius: 6px;">
                <strong>{{ ar.agent_name }}</strong>
                <pre v-if="ar.result" style="white-space: pre-wrap; font-size: 12px; margin-top: 4px;">{{ ar.result }}</pre>
                <span v-if="ar.error" style="color: #e53e3e;">执行错误: {{ ar.error }}</span>
              </div>
            </details>
          </template>
        </div>
        <a-textarea
          v-model:value="reviewComment"
          :placeholder="reviewApproved ? '审核备注（可选）...' : '请输入驳回原因...'"
          :rows="4"
          :maxlength="500"
          show-count
          style="margin-top: 12px"
        />
      </div>
      <div v-else style="padding: 24px; text-align: center; color: #999;">加载中...</div>
    </a-modal>
    </div>
    <!-- ===== Tab1 结束 ===== -->

    <!-- ===== Tab2 能力演进 ===== -->
    <div v-else-if="activeTab === 'evolution'" class="evolution-tab">
      <div class="tab-hero">
        <h2 class="tab-title">🧬 能力演进</h2>
        <p class="tab-sub">打造或诊断优化技能、连接器、协助伙伴</p>
        <a-input-search
          v-model:value="evolutionInput"
          placeholder="描述要沉淀的方法论，或说「把刚才的做法沉淀成技能」"
          size="large"
          enter-button="生成建议"
          class="evolution-input"
          @search="onEvolutionSearch"
        />
      </div>

      <div class="evo-grid">
        <!-- 技能诊断 -->
        <div class="evo-card evo-skill" @click="goTemplates">
          <div class="evo-icon">📦</div>
          <div class="evo-name">技能诊断</div>
          <div class="evo-stats">
            <span class="evo-stat"><b>{{ evolutionData.skill_diagnostics?.template_count ?? 0 }}</b> 模板</span>
            <span class="evo-stat"><b>{{ evolutionData.skill_diagnostics?.success_rate ?? 0 }}%</b> 成功率</span>
            <span class="evo-stat"><b>{{ (evolutionData.skill_diagnostics?.low_hit_templates || []).length }}</b> 待优化</span>
          </div>
          <div class="evo-action">点击「诊断」→ 任务模板 →</div>
        </div>

        <!-- 连接器 -->
        <div class="evo-card evo-conn" @click="goRuntimeConsole">
          <div class="evo-icon">🔌</div>
          <div class="evo-name">连接器</div>
          <div class="evo-stats">
            <span class="evo-stat"><b>{{ evolutionData.connectors?.enabled_count ?? 0 }}</b> 已启用</span>
            <span class="evo-stat"><b>{{ evolutionData.connectors?.success_rate ?? 0 }}%</b> 成功率</span>
            <span class="evo-stat"><b>{{ (evolutionData.connectors?.offline || []).length }}</b> 异常</span>
          </div>
          <div class="evo-action">点击「管理」→ 运行时控制台 →</div>
        </div>

        <!-- 协助伙伴 -->
        <div class="evo-card evo-partner" @click="goPartners">
          <div class="evo-icon">🤝</div>
          <div class="evo-name">协助伙伴 · 高频协作</div>
          <div class="evo-list">
            <div v-for="p in (evolutionData.partners || []).slice(0, 3)" :key="p.agent_id" class="evo-partner-item">
              <span class="evo-dot" />{{ p.name }} · {{ p.run_count }} 次
            </div>
            <div v-if="!(evolutionData.partners || []).length" class="evo-empty">暂无协作数据</div>
          </div>
          <div class="evo-action">点击「查看」→ 档案 →</div>
        </div>
      </div>
    </div>

    <!-- ===== Tab3 智能孵化 ===== -->
    <div v-else-if="activeTab === 'incubation'" class="incubation-tab">
      <div class="tab-hero">
        <h2 class="tab-title">🛠️ 智能孵化</h2>
        <p class="tab-sub">从零孵化或继续打磨数字民警</p>
        <a-input-search
          v-model:value="incubateInput"
          placeholder="描述想孵化的数字民警：服务谁、负责什么、在哪里用"
          size="large"
          enter-button="生成草案"
          class="evolution-input"
          @search="incubateCreate"
        />
        <div class="incubate-chips">
          <a-tag v-for="chip in incubateExamples" :key="chip" class="incubate-chip" @click="incubateInput = chip">
            {{ chip }}
          </a-tag>
        </div>
      </div>

      <!-- 两种模式 -->
      <div class="incubate-modes">
        <div class="incubate-mode" :class="{ active: incubateMode === 'create' }" @click="incubateMode = 'create'">
          <div class="mode-icon">✨</div>
          <div class="mode-name">从零孵化</div>
          <div class="mode-desc">创建一个新的数字民警</div>
        </div>
        <div class="incubate-mode" :class="{ active: incubateMode === 'refine' }" @click="incubateMode = 'refine'">
          <div class="mode-icon">🔨</div>
          <div class="mode-name">继续打磨</div>
          <div class="mode-desc">优化已有的数字民警草稿</div>
        </div>
      </div>

      <!-- 从零孵化草案结果 -->
      <div v-if="draftResult" class="draft-result">
        <h3 class="draft-title">孵化草案</h3>
        <div class="draft-name">{{ draftResult.name }}</div>
        <div class="draft-desc">{{ draftResult.description }}</div>
        <div class="draft-block">
          <div class="draft-label">灵魂（system_prompt）</div>
          <pre class="draft-prompt">{{ draftResult.system_prompt }}</pre>
        </div>
        <div v-if="draftResult.recommended_skills?.length" class="draft-block">
          <div class="draft-label">推荐技能</div>
          <div class="draft-skills">
            <a-tag v-for="s in draftResult.recommended_skills" :key="s.template_id" class="draft-skill">{{ s.name }}</a-tag>
          </div>
        </div>
        <div class="draft-ops">
          <a-button type="primary" @click="confirmDraft">保存为草稿</a-button>
          <a-button @click="draftResult = null">重新生成</a-button>
        </div>
      </div>

      <!-- 我的数字民警（完成度） -->
      <div class="incubate-list">
        <h3 class="draft-title">我的数字民警</h3>
        <div v-for="item in incubationItems" :key="item.id" class="incubate-item">
          <div class="ii-head">
            <span class="ii-name">{{ item.name }}</span>
            <a-tag v-if="item.approval_status === 'approved'" color="success">已发布</a-tag>
            <a-tag v-else color="processing">草稿</a-tag>
            <span class="ii-badge">{{ item.badge_number }}</span>
          </div>
          <div class="ii-progress">
            <a-progress :percent="item.completeness?.percent || 0" :show-info="false" size="small" />
            <span class="ii-percent">{{ item.completeness?.percent || 0 }}%</span>
          </div>
          <div v-if="item.completeness?.next_steps?.length" class="ii-next">
            建议：{{ item.completeness.next_steps.join('；') }}
          </div>
          <div class="ii-ops">
            <a-button size="small" @click="goProfile(item)">编辑</a-button>
            <a-button size="small" @click="goChat(item)">去对话</a-button>
            <a-button size="small" type="primary" ghost @click="goPublish(item)">发布</a-button>
          </div>
        </div>
        <a-empty v-if="!incubationItems.length" description="还没有数字民警，去上面孵化一个吧" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.police-dashboard {
  padding: 24px 32px 48px;
  max-width: 1500px;
  margin: 0 auto;
}

/* ═══════ 欢迎横幅 ═══════ */
.welcome-banner {
  position: relative;
  overflow: hidden;
  background: linear-gradient(120deg, #1a365d 0%, #2b6cb0 55%, #24839b 100%);
  border-radius: 16px;
  padding: 28px 32px 20px;
  margin-bottom: 20px;
  color: #fff;
  box-shadow: 0 8px 24px rgba(26, 54, 93, 0.18);
}
.banner-glow {
  position: absolute;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.12) 0%, transparent 70%);
  pointer-events: none;
}
.banner-glow-1 { width: 320px; height: 320px; top: -140px; right: 8%; }
.banner-glow-2 { width: 240px; height: 240px; bottom: -120px; left: 30%; }
.banner-content {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}
.banner-greeting {
  font-size: 26px;
  font-weight: 700;
  margin: 0 0 8px 0;
  letter-spacing: 0.5px;
}
.banner-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  font-size: 14px;
  opacity: 0.92;
}
.banner-dept {
  padding: 2px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
  font-size: 12px;
  font-weight: 500;
}
.banner-actions { display: flex; gap: 10px; }
.banner-btn { height: 38px; border-radius: 10px; font-weight: 500; border: none; }
.banner-btn-ghost {
  background: rgba(255, 255, 255, 0.14);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.35);
}
.banner-btn-ghost:hover { background: rgba(255, 255, 255, 0.24); color: #fff; }
.banner-btn-primary { background: #fff; color: #1a365d; }
.banner-btn-primary:hover { background: #ebf8ff; color: #1a365d; }
.banner-stats {
  position: relative;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid rgba(255, 255, 255, 0.18);
}
.banner-stat { display: flex; flex-direction: column; gap: 2px; }
.banner-stat-value { font-size: 24px; font-weight: 700; line-height: 1.2; }
.banner-stat-label { font-size: 12px; opacity: 0.85; }

/* ═══════ 统计卡片 ═══════ */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}
.stat-card {
  background: var(--gray-0, #fff);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 12px;
  padding: 18px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  transition: box-shadow 0.2s, transform 0.2s;
}
.stat-card:hover {
  box-shadow: 0 6px 20px rgba(16, 30, 54, 0.08);
  transform: translateY(-2px);
}
.stat-icon {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 21px;
  flex-shrink: 0;
}
.stat-value { font-size: 26px; font-weight: 700; line-height: 1.2; color: var(--gray-1000, #1a1a1a); }
.stat-label { font-size: 13px; color: var(--gray-500, #718096); }

/* ═══════ 主网格 ═══════ */
.dashboard-grid {
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
.dash-left, .dash-right {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
.dashboard-panel {
  background: var(--gray-0, #fff);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 12px;
  overflow: hidden;
}
.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--gray-50, #e2e8f0);
}
.panel-header h3 {
  font-size: 15px;
  font-weight: 600;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 6px;
}
.panel-icon { color: var(--main-color, #24839b); }
.panel-count {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--main-color, #24839b);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  line-height: 20px;
  text-align: center;
}
.panel-more { margin-left: auto; }
.panel-body { padding: 12px; max-height: 480px; overflow-y: auto; }
.empty-state { padding: 28px 0; }

/* ═══════ 案件行 ═══════ */
.case-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}
.case-row:hover { background: var(--gray-10, #f7fafc); }
.case-row-main { flex: 1; min-width: 0; }
.case-row-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.case-row-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--gray-500, #718096);
}
.case-number { color: var(--gray-400, #a0aec0); }

/* ═══════ 任务/通知 ═══════ */
.task-item {
  display: flex;
  align-items: center;
  padding: 12px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}
.task-item:hover { background: var(--gray-10, #f7fafc); }
.task-item-main { flex: 1; min-width: 0; }
.task-item-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.task-item-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--gray-500, #718096);
}
.task-item-assignee { color: var(--gray-400, #a0aec0); }
.task-item-actions { display: flex; gap: 6px; flex-shrink: 0; }
.review-item { align-items: center; }
.review-divider { margin: 14px 0 6px; font-size: 12px; color: var(--gray-500, #718096); }
.agent-review-item { background: color-mix(in srgb, #8b5cf6 6%, transparent); }
.notify-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  font-size: 13px;
}
.notify-item:hover { background: var(--gray-10, #f7fafc); }
.notify-icon { color: #8b5cf6; flex-shrink: 0; }
.notify-text { color: var(--gray-700, #4a5568); }

/* ═══════ 底部：数字警员条 + 快捷操作 ═══════ */
.bottom-section {
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  gap: 16px;
}
.agent-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.agent-chip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
  min-width: 0;
}
.agent-chip:hover {
  border-color: var(--main-color, #24839b);
  box-shadow: 0 4px 14px rgba(16, 30, 54, 0.08);
}
.agent-chip-avatar {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: var(--main-20, #e0f0f4);
  color: var(--main-color, #24839b);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  overflow: hidden;
  flex-shrink: 0;
}
.agent-chip-avatar img { width: 100%; height: 100%; object-fit: cover; }
.agent-chip-info { flex: 1; min-width: 0; }
.agent-chip-name {
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.agent-chip-role {
  font-size: 11px;
  color: var(--gray-500, #718096);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.agent-chip-chat { color: var(--gray-400, #a0aec0); flex-shrink: 0; }
.agent-chip:hover .agent-chip-chat { color: var(--main-color, #24839b); }
.agent-strip-panel .panel-body { max-height: none; }

.quick-action-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.quick-action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px 8px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s, transform 0.15s;
  font-size: 13px;
  font-weight: 500;
  color: var(--gray-700, #4a5568);
}
.quick-action-card:hover {
  background: var(--gray-10, #f7fafc);
  transform: translateY(-2px);
}
.quick-action-icon { font-size: 22px; }

/* ═══════ 审核弹窗 ═══════ */
.review-modal-body { max-height: 60vh; overflow-y: auto; }
.rm-task-title { font-size: 16px; font-weight: 600; margin-bottom: 12px; }
.rm-section-label { font-size: 13px; font-weight: 600; color: var(--gray-600, #4a5568); margin-bottom: 6px; }
.rm-result {
  background: var(--gray-10, #f7fafc);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 8px;
  padding: 12px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

/* ═══════ 响应式 ═══════ */
@media (max-width: 1100px) {
  .dashboard-grid, .bottom-section { grid-template-columns: 1fr; }
  .stat-cards { grid-template-columns: repeat(2, 1fr); }
  .banner-stats { grid-template-columns: repeat(3, 1fr); }
  .agent-strip { grid-template-columns: repeat(2, 1fr); }
  .quick-action-grid { grid-template-columns: repeat(3, 1fr); }
}

/* ===== 三 Tab 切换 ===== */
.dashboard-tabs {
  margin-bottom: 20px;
}
.dashboard-tabs :deep(.ant-segmented) {
  background: var(--gray-100);
  border-radius: 10px;
  padding: 4px;
}

/* ===== 能力演进 / 智能孵化 公共 ===== */
.tab-hero {
  background: linear-gradient(160deg, #eef4fd 0%, #f7f8fa 50%, #eef0f4 100%);
  border-radius: 18px;
  padding: 22px 24px;
  margin-bottom: 18px;
  box-shadow: 0 4px 16px rgba(16, 30, 54, 0.06);
}
.tab-title {
  margin: 0;
  font-size: 20px;
  color: #1a365d;
  font-weight: 700;
}
.tab-sub {
  margin: 6px 0 14px;
  font-size: 13px;
  color: var(--gray-600);
}
.evolution-input {
  max-width: 640px;
}

/* ===== 能力演进三卡 ===== */
.evo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
.evo-card {
  border-radius: 16px;
  padding: 18px;
  cursor: pointer;
  color: #fff;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 150px;
}
.evo-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 24px rgba(16, 30, 54, 0.15);
}
.evo-skill { background: linear-gradient(135deg, #2b6cb0, #3182ce); }
.evo-conn { background: linear-gradient(135deg, #6b46c1, #805ad5); }
.evo-partner { background: linear-gradient(135deg, #2f855a, #38a169); }
.evo-icon {
  font-size: 26px;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
}
.evo-name {
  font-size: 15px;
  font-weight: 700;
}
.evo-stats {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}
.evo-stat {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
}
.evo-stat b {
  font-size: 16px;
  color: #fff;
}
.evo-action {
  margin-top: auto;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
}
.evo-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.9);
}
.evo-partner-item {
  display: flex;
  align-items: center;
  gap: 6px;
}
.evo-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #fff;
}
.evo-empty {
  color: rgba(255, 255, 255, 0.7);
}

/* ===== 智能孵化 ===== */
.incubate-chips {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.incubate-chip {
  cursor: pointer;
  border-radius: 999px;
  background: #fff;
  border: 1px solid var(--gray-200);
  color: var(--gray-700);
  padding: 3px 12px;
  font-size: 12px;
}
.incubate-chip:hover {
  border-color: var(--main-400);
  color: var(--main-600);
}
.incubate-modes {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}
.incubate-mode {
  background: #fff;
  border: 1px solid var(--gray-200);
  border-radius: 14px;
  padding: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: border-color 0.16s ease, background 0.16s ease;
}
.incubate-mode:hover {
  border-color: var(--main-300);
}
.incubate-mode.active {
  border-color: #1a365d;
  background: #ebf2fa;
}
.mode-icon {
  font-size: 26px;
}
.mode-name {
  font-size: 14px;
  font-weight: 700;
  color: #1a202c;
}
.mode-desc {
  font-size: 11px;
  color: var(--gray-500);
}
.draft-result {
  background: #fff;
  border: 1px solid var(--gray-150);
  border-radius: 14px;
  padding: 18px;
  margin-bottom: 18px;
  box-shadow: 0 4px 16px rgba(16, 30, 54, 0.06);
}
.draft-title {
  margin: 0 0 12px;
  font-size: 15px;
  color: #1a365d;
}
.draft-name {
  font-size: 18px;
  font-weight: 700;
  color: #1a202c;
}
.draft-desc {
  font-size: 13px;
  color: var(--gray-700);
  margin: 6px 0 12px;
  line-height: 1.6;
}
.draft-block {
  margin-bottom: 12px;
}
.draft-label {
  font-size: 12px;
  color: var(--gray-500);
  margin-bottom: 6px;
}
.draft-prompt {
  background: var(--gray-100);
  border-radius: 10px;
  padding: 12px;
  font-size: 12px;
  color: var(--gray-800);
  white-space: pre-wrap;
  line-height: 1.6;
}
.draft-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.draft-skill {
  border-radius: 8px;
}
.draft-ops {
  display: flex;
  gap: 10px;
  margin-top: 4px;
}
.incubate-list {
  background: #fff;
  border: 1px solid var(--gray-150);
  border-radius: 14px;
  padding: 18px;
}
.incubate-item {
  border-top: 1px dashed var(--gray-200);
  padding: 14px 0;
}
.incubate-item:first-of-type {
  border-top: none;
}
.ii-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ii-name {
  font-size: 14px;
  font-weight: 600;
  color: #1a202c;
}
.ii-badge {
  margin-left: auto;
  font-size: 11px;
  color: var(--gray-500);
}
.ii-progress {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 10px 0 6px;
}
.ii-progress :deep(.ant-progress) {
  flex: 1;
}
.ii-percent {
  font-size: 12px;
  color: var(--gray-600);
}
.ii-next {
  font-size: 12px;
  color: #b7791f;
  margin-bottom: 10px;
}
.ii-ops {
  display: flex;
  gap: 8px;
}
</style>
