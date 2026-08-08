<script setup>
/**
 * ★ 公安个人工作台 — 可拖拽面板聚合 (POLICE_REQUIREMENTS §8.4.1)
 *
 * 设计：
 *  - 顶部仅保留「统计卡片」：待办 / 待审查 / 进行中 / 待审核 / 我的案件
 *  - 功能面板（统一样式 + 可拖拽排序 + 可添加/移除，localStorage 持久化）：
 *      待处理 / 通知 / 常用链接 / 月视图日程 / 任务统计 / 案件统计 / 智能体使用情况
 *  - 「待处理」面板以 tab 融合：待办任务 / 待审查成果 / 待审核事项
 *    （待审核事项含任务审核 + 智能体上架审批 ← 原审核台功能并入）
 *  - 运行中心（默认运行模式 & 智能体状态总览）作为超管专属面板。
 *
 * 准实时刷新 via useRealtime。
 */
import { onMounted, computed, ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { usePoliceStore } from '@/stores/police'
import { useUserStore } from '@/stores/user'
import { useRealtime } from '@/composables/useRealtime'
import { policeAgentApi, policeCaseApi, policeGovernanceApi } from '@/apis/police_api'
import TaskCard from '@/components/police/TaskCard.vue'
import TaskDetailModal from '@/components/police/TaskDetailModal.vue'
import TaskCalendarView from '@/components/police/TaskCalendarView.vue'
import WorkbenchPanel from '@/components/police/WorkbenchPanel.vue'
import {
  InboxOutlined, ClockCircleOutlined, FileSearchOutlined,
  ExclamationCircleOutlined, PlusOutlined, UploadOutlined, BellOutlined,
  FolderOpenOutlined, RobotOutlined, BookOutlined, MessageOutlined,
  ArrowRightOutlined, DatabaseOutlined, AppstoreOutlined
} from '@ant-design/icons-vue'
import {
  ClipboardList, Bell, Link2, CalendarDays, BarChart3,
  FolderKanban, Bot, Gauge, Plus
} from 'lucide-vue-next'

const router = useRouter()
const policeStore = usePoliceStore()
const userStore = useUserStore()

const isSuperAdmin = computed(() => userStore.isSuperAdmin)
const isAdmin = computed(() => userStore.isAdmin)

// ═══════════════════ 面板布局持久化（localStorage）═══════════════════
const PANELS_KEY = 'xiaonan.workbench.panels.v1'
const ALL_PANELS = [
  { key: 'pending', title: '待处理', icon: ClipboardList },
  { key: 'notices', title: '通知', icon: Bell },
  { key: 'links', title: '常用链接', icon: Link2 },
  { key: 'calendar', title: '月视图日程', icon: CalendarDays },
  { key: 'taskStats', title: '任务统计', icon: BarChart3 },
  { key: 'caseStats', title: '案件统计', icon: FolderKanban },
  { key: 'agentUsage', title: '智能体使用情况', icon: Bot },
  { key: 'runtime', title: '运行中心', icon: Gauge, superAdminOnly: true },
]

// 已启用的面板 key 顺序（默认全部，超管专属除外按角色过滤）
function defaultEnabled() {
  const base = ALL_PANELS.filter((p) => !p.superAdminOnly || isSuperAdmin.value).map((p) => p.key)
  return base
}
const enabledPanelKeys = ref(defaultEnabled())

function loadLayout() {
  try {
    const saved = JSON.parse(localStorage.getItem(PANELS_KEY) || 'null')
    if (Array.isArray(saved) && saved.length) {
      // 过滤掉已不存在的面板 key，并补齐超管专属
      const known = ALL_PANELS.map((p) => p.key)
      const valid = saved.filter((k) => known.includes(k))
      const superPanels = ALL_PANELS.filter((p) => p.superAdminOnly && isSuperAdmin.value).map((p) => p.key)
      const merged = [...new Set([...valid, ...superPanels])]
      enabledPanelKeys.value = merged
    }
  } catch (e) {
    enabledPanelKeys.value = defaultEnabled()
  }
}
function persistLayout() {
  localStorage.setItem(PANELS_KEY, JSON.stringify(enabledPanelKeys.value))
}
loadLayout()

const panelMetaOf = (key) => ALL_PANELS.find((p) => p.key === key)

// 拖拽状态
const dragKey = ref(null)
function onPanelDragStart(key) {
  dragKey.value = key
}
function onPanelDragOver(targetKey) {
  if (!dragKey.value || dragKey.value === targetKey) return
  const list = enabledPanelKeys.value
  const from = list.indexOf(dragKey.value)
  const to = list.indexOf(targetKey)
  if (from < 0 || to < 0) return
  list.splice(from, 1)
  list.splice(to, 0, dragKey.value)
  enabledPanelKeys.value = [...list]
  persistLayout()
}
function onPanelDragEnd() {
  dragKey.value = null
}
function removePanel(key) {
  enabledPanelKeys.value = enabledPanelKeys.value.filter((k) => k !== key)
  persistLayout()
}
// 添加面板（从候选区）
const addPanelOpen = ref(false)
const removablePanels = computed(() =>
  ALL_PANELS.filter((p) => !p.superAdminOnly || isSuperAdmin.value).filter((p) => !enabledPanelKeys.value.includes(p.key))
)
function addPanel(key) {
  if (enabledPanelKeys.value.includes(key)) return
  enabledPanelKeys.value.push(key)
  persistLayout()
  message.success(`已添加「${panelMetaOf(key).title}」面板`)
}

// ═══════════════════ 智能体上架审批（原审核台并入，仅超管）═══════════════════
const pendingItems = ref([])
const approvingId = ref(null)
async function loadPendingReview() {
  if (!isSuperAdmin.value) return
  try {
    const res = await policeGovernanceApi.reviewPending({ page: 1, page_size: 20 })
    pendingItems.value = res.items || []
  } catch (e) {
    pendingItems.value = []
  }
}
async function approvePending(it, approved) {
  approvingId.value = it.id
  try {
    await policeGovernanceApi.decide(it.request_type, it.id, { approved, reason: approved ? null : '由工作台驳回' })
    message.success(approved ? '已通过并上架' : '已驳回')
    await loadPendingReview()
    await policeStore.loadStats(true)
  } catch (e) {
    message.error(e?.message || '操作失败')
  } finally {
    approvingId.value = null
  }
}

// ═══════════════════ 常用数字警员 / 智能体使用情况 ═══════════════════
const topAgents = ref([])
async function loadTopAgents() {
  try {
    const res = await policeAgentApi.list({ page: 1, page_size: 200 })
    topAgents.value = (res.items || res.agents || [])
      .filter((a) => !a.is_subagent && !a.is_system)
      .slice(0, 8)
  } catch (e) {
    topAgents.value = []
  }
}
function goAgentChat(agent) {
  const chatId = agent?.slug || agent?.agent_id || agent?.id
  if (!chatId) return
  router.push({ path: '/agent', query: { agent_id: chatId } })
}

// ═══════════════════ 我的案件 ═══════════════════
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

// ═══════════════════ 统计卡片（仅保留卡片样式）═══════════════════
const statCards = computed(() => [
  { title: '待办', value: policeStore.stats.my_pending_count || 0, icon: ClockCircleOutlined, color: '#D69E2E', bg: '#FEFCE8' },
  { title: '待审查', value: policeStore.myDrafts.length, icon: InboxOutlined, color: '#B7791F', bg: '#FEF3C7' },
  { title: '进行中', value: policeStore.stats.my_in_progress_count || 0, icon: FileSearchOutlined, color: '#3182CE', bg: '#EBF8FF' },
  { title: '待审核', value: policeStore.stats.review_count || 0, icon: ExclamationCircleOutlined, color: '#E53E3E', bg: '#FED7D7' },
  { title: '我的案件', value: myCasesTotal, icon: FolderOpenOutlined, color: '#38A169', bg: '#F0FFF4' },
])

// 问候语
const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return '上午好'
  if (h < 18) return '下午好'
  return '晚上好'
})
const userName = computed(() => userStore.username || '警官')
const departmentName = computed(() => userStore.departmentName || '公安业务协作平台')

// ═══════════════════ 待处理面板（tab：待办 / 待审查 / 待审核）═══════════════════
const pendingTab = ref('todo')
const myActiveTasks = computed(() =>
  policeStore.myTasks.filter((t) => ['pending', 'in_progress'].includes(t.status))
)
// 待审核 tab 数据 = 任务审核 + 智能体上架审批（渲染时区分）
const reviewList = computed(() => policeStore.reviewTasks || [])

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

// 任务详情弹窗
const detailModalVisible = ref(false)
const detailTaskId = ref(null)
function goTask(task) {
  detailTaskId.value = task.id
  detailModalVisible.value = true
}
function closeTaskDetail() {
  detailModalVisible.value = false
  detailTaskId.value = null
  Promise.all([
    policeStore.loadMyDrafts(true),
    policeStore.loadReviewTasks(1, 6, true),
    policeStore.loadMyTasks(1, 10, true),
  ]).catch(() => {})
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

// 工作台内联审核（普通用户也可审核，无需跳转任务详情）
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

// ═══════════════════ 常用链接 ═══════════════════
const quickActions = computed(() => {
  const items = [
    { title: '创建案件', icon: PlusOutlined, color: '#3182CE', onClick: goCreateCase },
    { title: '导入笔录', icon: UploadOutlined, color: '#B7791F', to: '/police/import' },
    { title: '案件管理', icon: FolderOpenOutlined, color: '#38A169', to: '/police/cases' },
    { title: '数字警员', icon: RobotOutlined, color: '#805AD5', to: '/agent-manage' },
    { title: '新建对话', icon: MessageOutlined, color: '#24839B', to: '/agent' },
    { title: '知识库 · 技能', icon: BookOutlined, color: '#DD6B20', to: '/extensions' },
  ]
  if (isAdmin.value) {
    items.push({ title: '任务模板', icon: AppstoreOutlined, color: '#2C5282', to: '/police/task-templates' })
    items.push({ title: '运行时控制台', icon: DatabaseOutlined, color: '#6B46C1', to: '/police/runtime-console' })
  }
  return items
})
function runQuickAction(action) {
  if (action.onClick) return action.onClick()
  router.push(action.to)
}

// ═══════════════════ 任务统计面板 ═══════════════════
const taskStatItems = computed(() => [
  { label: '我的待办', value: policeStore.stats.my_pending_count || 0, color: '#D69E2E' },
  { label: '进行中', value: policeStore.stats.my_in_progress_count || 0, color: '#3182CE' },
  { label: '待审核', value: policeStore.stats.review_count || 0, color: '#E53E3E' },
  { label: '我的任务总数', value: policeStore.stats.my_tasks_total || policeStore.myTasksTotal || 0, color: '#805AD5' },
])

// ═══════════════════ 智能体使用情况面板 ═══════════════════
const agentUsageCards = computed(() => {
  const officerCount = topAgents.value.filter((a) => !a.is_subagent).length
  return [
    { label: '可用数字警员', value: officerCount, color: '#24839B' },
    { label: '常用智能体', value: Math.min(topAgents.value.length, 8), color: '#38A169' },
    { label: '内置能力', value: 4, color: '#805AD5' },
  ]
})

// ═══════════════════ 准实时刷新 ═══════════════════
useRealtime(() => policeStore.loadMyDrafts(true), { interval: 30000 })
useRealtime(() => policeStore.loadReviewTasks(1, 10, true), { interval: 30000 })
useRealtime(() => policeStore.loadMyTasks(1, 10, true), { interval: 30000 })
useRealtime(() => policeStore.loadStats(true), { interval: 60000 })
useRealtime(() => loadPendingReview(), { interval: 30000 })
useRealtime(() => loadMyCases(), { interval: 60000 })
useRealtime(() => loadTopAgents(), { interval: 60000 })

onMounted(() => {
  loadPendingReview()
  loadMyCases()
  loadTopAgents()
})
</script>

<template>
  <div class="police-dashboard">
    <!-- ═══════ 顶部：欢迎横幅 + 统计卡片 ═══════ -->
    <div class="welcome-banner">
      <div class="banner-glow banner-glow-1"></div>
      <div class="banner-glow banner-glow-2"></div>
      <div class="banner-content">
        <div class="banner-text">
          <h1 class="banner-greeting">{{ greeting }}，{{ userName }}</h1>
          <p class="banner-meta">
            <span class="banner-dept">{{ departmentName }}</span>
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
    </div>

    <!-- ═══════ 统计卡片（仅卡片样式）═══════ -->
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

    <!-- ═══════ 面板工具条：添加面板 ═══════ -->
    <div class="wb-toolbar">
      <span class="wb-toolbar-hint">面板可拖拽排序、自由添加或移除</span>
      <a-dropdown v-model:open="addPanelOpen" placement="bottomRight">
        <a-button size="small" class="wb-add-btn">
          <Plus :size="13" /> 添加面板
        </a-button>
        <template #overlay>
          <div class="wb-add-menu">
            <button
              v-for="p in removablePanels"
              :key="p.key"
              type="button"
              class="wb-add-item"
              @click="addPanel(p.key); addPanelOpen = false"
            >
              <component :is="p.icon" :size="14" />
              {{ p.title }}
            </button>
            <div v-if="!removablePanels.length" class="wb-add-empty">所有面板均已添加</div>
          </div>
        </template>
      </a-dropdown>
    </div>

    <!-- ═══════ 可拖拽面板网格 ═══════ -->
    <div class="wb-grid">
      <WorkbenchPanel
        v-for="key in enabledPanelKeys"
        :key="key"
        :panel-key="key"
        :title="panelMetaOf(key).title"
        :icon="panelMetaOf(key).icon"
        :full="['pending', 'calendar', 'runtime'].includes(key)"
        :count="key === 'pending' ? (policeStore.stats.my_pending_count || 0) + (policeStore.stats.review_count || 0) + policeStore.myDrafts.length : undefined"
        :show-count="key === 'pending'"
        @dragstart="onPanelDragStart"
        @dragover="onPanelDragOver"
        @drop="() => {}"
        @dragend="onPanelDragEnd"
        @remove="removePanel(key)"
      >
        <!-- ── 待处理面板：tab 融合 ── -->
        <template v-if="key === 'pending'">
          <div class="pending-tabs">
            <button
              type="button"
              class="ptab"
              :class="{ active: pendingTab === 'todo' }"
              @click="pendingTab = 'todo'"
            >待办任务 <span class="ptab-count">{{ policeStore.stats.my_pending_count || 0 }}</span></button>
            <button
              type="button"
              class="ptab"
              :class="{ active: pendingTab === 'draft' }"
              @click="pendingTab = 'draft'"
            >待审查成果 <span class="ptab-count">{{ policeStore.myDrafts.length }}</span></button>
            <button
              type="button"
              class="ptab"
              :class="{ active: pendingTab === 'review' }"
              @click="pendingTab = 'review'"
            >待审核事项 <span class="ptab-count">{{ policeStore.stats.review_count || 0 }}</span></button>
          </div>

          <!-- 待办任务 -->
          <div v-if="pendingTab === 'todo'" class="panel-scroll">
            <div v-if="myActiveTasks.length === 0" class="empty-state">
              <a-empty :image="false" description="暂无待办任务，一切就绪" />
            </div>
            <TaskCard v-for="task in myActiveTasks" :key="task.id" :task="task" @click="goTask" />
          </div>

          <!-- 待审查成果 -->
          <div v-else-if="pendingTab === 'draft'" class="panel-scroll">
            <div v-if="policeStore.myDrafts.length === 0" class="empty-state">
              <a-empty :image="false" description="暂无待审查草案" />
            </div>
            <TaskCard v-for="d in policeStore.myDrafts" :key="d.id" :task="d" @click="goTask" />
          </div>

          <!-- 待审核事项：任务审核 + 智能体上架审批（原审核台） -->
          <div v-else class="panel-scroll">
            <div v-if="reviewList.length === 0 && (!isSuperAdmin || pendingItems.length === 0)" class="empty-state">
              <a-empty :image="false" description="暂无待审核事项" />
            </div>
            <div
              v-for="task in reviewList"
              :key="'task-' + task.id"
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

            <!-- 智能体上架审批（原审核台，仅超管） -->
            <template v-if="isSuperAdmin && pendingItems.length">
              <a-divider class="review-divider">智能体上架审批</a-divider>
              <div
                v-for="it in pendingItems"
                :key="'agent-' + it.id"
                class="task-item review-item agent-review-item"
              >
                <div class="task-item-main">
                  <div class="task-item-title">{{ it.name }}</div>
                  <div class="task-item-meta">
                    <a-tag :color="it.request_type === 'partner' ? 'purple' : 'blue'" size="small">
                      {{ it.request_type === 'partner' ? '协助伙伴' : '数字警员' }}
                    </a-tag>
                    <span class="task-item-assignee">{{ it.category || '待上架' }}</span>
                  </div>
                </div>
                <div class="task-item-actions">
                  <a-button
                    type="primary" size="small"
                    :loading="approvingId === it.id"
                    @click="approvePending(it, true)"
                  >通过</a-button>
                  <a-button
                    danger size="small"
                    :loading="approvingId === it.id"
                    @click="approvePending(it, false)"
                  >驳回</a-button>
                </div>
              </div>
            </template>
          </div>
        </template>

        <!-- ── 通知面板 ── -->
        <template v-else-if="key === 'notices'">
          <div class="panel-scroll">
            <div v-if="notifications.length === 0" class="empty-state">
              <a-empty :image="false" description="暂无新通知" />
            </div>
            <div v-for="n in notifications" :key="n.case_id" class="notify-item" @click="goCaseTasks(n.case_id)">
              <BellOutlined class="notify-icon" />
              <span class="notify-text">{{ n.text }}</span>
            </div>
          </div>
        </template>

        <!-- ── 常用链接面板 ── -->
        <template v-else-if="key === 'links'">
          <div class="quick-action-grid">
            <div v-for="action in quickActions" :key="action.title" class="quick-action-card" @click="runQuickAction(action)">
              <component :is="action.icon" class="quick-action-icon" :style="{ color: action.color }" />
              <span>{{ action.title }}</span>
            </div>
          </div>
        </template>

        <!-- ── 月视图日程面板 ── -->
        <template v-else-if="key === 'calendar'">
          <TaskCalendarView :tasks="policeStore.myTasks" @open-task="goTask" />
        </template>

        <!-- ── 任务统计面板 ── -->
        <template v-else-if="key === 'taskStats'">
          <div class="mini-stat-grid">
            <div v-for="s in taskStatItems" :key="s.label" class="mini-stat">
              <div class="mini-stat-value" :style="{ color: s.color }">{{ s.value }}</div>
              <div class="mini-stat-label">{{ s.label }}</div>
            </div>
          </div>
        </template>

        <!-- ── 案件统计面板 ── -->
        <template v-else-if="key === 'caseStats'">
          <div class="my-cases-mini">
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
        </template>

        <!-- ── 智能体使用情况面板 ── -->
        <template v-else-if="key === 'agentUsage'">
          <div class="mini-stat-grid">
            <div v-for="s in agentUsageCards" :key="s.label" class="mini-stat">
              <div class="mini-stat-value" :style="{ color: s.color }">{{ s.value }}</div>
              <div class="mini-stat-label">{{ s.label }}</div>
            </div>
          </div>
          <div v-if="topAgents.length" class="agent-chips">
            <div v-for="agent in topAgents" :key="agent.id" class="agent-chip-mini" @click="goAgentChat(agent)">
              <div class="agent-chip-avatar">
                <img v-if="agent.icon" :src="agent.icon" :alt="agent.name" />
                <span v-else>{{ (agent.name || '?').slice(0, 1) }}</span>
              </div>
              <div class="agent-chip-info">
                <div class="agent-chip-name">{{ agent.name }}</div>
                <div class="agent-chip-role">{{ agent.rank || agent.department || '数字警员' }}</div>
              </div>
            </div>
          </div>
        </template>

        <!-- ── 运行中心面板（超管）── -->
        <template v-else-if="key === 'runtime'">
          <div class="runtime-hint">
            <a-button type="link" @click="router.push('/police/governance/runtime')">
              查看完整运行中心 <ArrowRightOutlined />
            </a-button>
          </div>
        </template>
      </WorkbenchPanel>
    </div>

    <!-- ═══════ 工作台内联审核弹窗 ═══════ -->
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

    <!-- 任务详情弹窗 -->
    <TaskDetailModal
      :visible="detailModalVisible"
      :task-id="detailTaskId"
      @close="closeTaskDetail"
      @refresh="closeTaskDetail"
    />
  </div>
</template>

<style lang="less" scoped>
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
  padding: 24px 32px 20px;
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
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}
.banner-greeting {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 6px 0;
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

/* ═══════ 统计卡片 ═══════ */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 16px;
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

/* ═══════ 面板工具条 ═══════ */
.wb-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-bottom: 14px;
}
.wb-toolbar-hint {
  color: var(--gray-500, #718096);
  font-size: 12px;
}
.wb-add-btn {
  border-radius: 8px;
}
.wb-add-menu {
  padding: 6px;
  min-width: 180px;
}
.wb-add-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--gray-800, #2d3748);
  font-size: 13px;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s;
}
.wb-add-item:hover {
  background: var(--main-20, #e0f0f4);
}
.wb-add-empty {
  padding: 12px;
  text-align: center;
  color: var(--gray-400, #a0aec0);
  font-size: 12px;
}

/* ═══════ 面板网格（统一 2 列，待处理/日历/运行中心跨列）═══════ */
.wb-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  align-items: start;
}
.wb-grid :deep(.wb-panel--full) {
  grid-column: 1 / -1;
}

/* 待处理 tab */
.pending-tabs {
  display: flex;
  gap: 4px;
  padding: 2px;
  background: var(--gray-50, #f2f6f7);
  border-radius: 9px;
  margin-bottom: 10px;
}
.ptab {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 6px 8px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--gray-600, #718096);
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}
.ptab:hover { color: var(--gray-900, #1a202c); }
.ptab.active {
  background: #fff;
  color: var(--main-800, #1a6d80);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}
.ptab-count {
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: var(--main-100, #cfe3e8);
  color: var(--main-800, #1a6d80);
  font-size: 11px;
  line-height: 18px;
  font-weight: 700;
}

.panel-scroll {
  max-height: 420px;
  overflow-y: auto;
}

/* 任务/通知行 */
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
.review-divider { margin: 10px 0 6px; font-size: 12px; color: var(--gray-500, #718096); }
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

.empty-state { padding: 24px 0; }

/* 常用链接 */
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

/* 案件行 */
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

/* 迷你统计 */
.mini-stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}
.mini-stat {
  padding: 14px;
  border-radius: 10px;
  background: var(--gray-10, #f7fafc);
  border: 1px solid var(--gray-50, #e2e8f0);
  text-align: center;
}
.mini-stat-value {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}
.mini-stat-label {
  margin-top: 4px;
  font-size: 12px;
  color: var(--gray-500, #718096);
}

/* 智能体 chips */
.agent-chips {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-top: 12px;
}
.agent-chip-mini {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.15s;
  min-width: 0;
}
.agent-chip-mini:hover { border-color: var(--main-color, #24839b); }
.agent-chip-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--main-20, #e0f0f4);
  color: var(--main-color, #24839b);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  overflow: hidden;
  flex-shrink: 0;
}
.agent-chip-avatar img { width: 100%; height: 100%; object-fit: cover; }
.agent-chip-info { flex: 1; min-width: 0; }
.agent-chip-name {
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.agent-chip-role {
  font-size: 10px;
  color: var(--gray-500, #718096);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.runtime-hint {
  display: flex;
  justify-content: center;
  padding: 20px 0;
}

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
  .wb-grid { grid-template-columns: 1fr; }
  .stat-cards { grid-template-columns: repeat(2, 1fr); }
  .quick-action-grid { grid-template-columns: repeat(3, 1fr); }
  .agent-chips { grid-template-columns: repeat(2, 1fr); }
}
</style>