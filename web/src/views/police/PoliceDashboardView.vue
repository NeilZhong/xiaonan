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
import { policeAgentApi, policeCaseApi } from '@/apis/police_api'
import TaskCard from '@/components/police/TaskCard.vue'
import TaskDetailModal from '@/components/police/TaskDetailModal.vue'
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

// 任务详情统一用弹窗展示（废弃整页 TaskDetailView 路由）：
// “待处理/待审查/待审核”点击任务 → 弹窗详情，弹窗内含完整操作（分配/执行/审核/重跑）。
const detailModalVisible = ref(false)
const detailTaskId = ref(null)

function goTask(task) {
  detailTaskId.value = task.id
  detailModalVisible.value = true
}
function goDraft(task) {
  detailTaskId.value = task.id
  detailModalVisible.value = true
}
function closeTaskDetail() {
  detailModalVisible.value = false
  detailTaskId.value = null
  // 关闭弹窗后刷新工作台列表（可能有状态变更）
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

    <!-- 任务详情弹窗（统一弹窗展示，替代整页路由） -->
    <TaskDetailModal
      :visible="detailModalVisible"
      :task-id="detailTaskId"
      @close="closeTaskDetail"
      @refresh="closeTaskDetail"
    />
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
</style>
