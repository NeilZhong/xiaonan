<script setup>
/**
 * ★ 公安个人工作台 — 四组待办聚合 (POLICE_REQUIREMENTS §8.4.1)
 * 待审查(推进智能体草案) / 待审核 / 待处理 / 通知
 * 通过 useRealtime 准实时刷新。
 */
import { onMounted, computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { usePoliceStore } from '@/stores/police'
import { useUserStore } from '@/stores/user'
import { useRealtime } from '@/composables/useRealtime'
import TaskCard from '@/components/police/TaskCard.vue'
import {
  InboxOutlined, ClockCircleOutlined, FileSearchOutlined,
  ExclamationCircleOutlined, CheckCircleOutlined, PlusOutlined, UploadOutlined, BellOutlined, CloseCircleOutlined
} from '@ant-design/icons-vue'

const router = useRouter()
const policeStore = usePoliceStore()
const userStore = useUserStore()

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 12) return '上午好'
  if (h < 18) return '下午好'
  return '晚上好'
})
const userName = computed(() => userStore.username || '警官')

const statCards = computed(() => [
  { title: '待审查', value: policeStore.myDrafts.length, icon: InboxOutlined, color: '#B7791F' },
  { title: '待办任务', value: policeStore.stats.my_pending_count, icon: ClockCircleOutlined, color: '#D69E2E' },
  { title: '进行中', value: policeStore.stats.my_in_progress_count, icon: FileSearchOutlined, color: '#3182CE' },
  { title: '待审核', value: policeStore.stats.review_count, icon: ExclamationCircleOutlined, color: '#E53E3E' },
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

onMounted(() => {
  // 初次加载已通过 useRealtime immediate 触发，这里补充案件列表用于跳转上下文
})
</script>

<template>
  <div class="police-dashboard">
    <!-- 顶部欢迎 -->
    <div class="dashboard-header">
      <div>
        <h1 class="page-title">{{ greeting }}，{{ userName }}</h1>
        <p class="page-subtitle">{{ new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }) }}</p>
      </div>
      <div class="header-actions">
        <a-button type="primary" @click="router.push('/police/cases/new')">
          <template #icon><PlusOutlined /></template>
          创建案件
        </a-button>
        <a-button @click="router.push('/police/cases')">
          <template #icon><UploadOutlined /></template>
          导入笔录
        </a-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stat-cards">
      <div v-for="card in statCards" :key="card.title" class="stat-card">
        <div class="stat-icon" :style="{ background: card.color + '15', color: card.color }">
          <component :is="card.icon" />
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ card.value }}</div>
          <div class="stat-label">{{ card.title }}</div>
        </div>
      </div>
    </div>

    <!-- 四组待办 -->
    <div class="dashboard-grid">
      <!-- 待审查：推进智能体草案 -->
      <div class="dashboard-panel">
        <div class="panel-header">
          <h3><InboxOutlined class="panel-icon" /> 待审查</h3>
          <a-button type="link" size="small" @click="router.push('/police/cases')">查看案件</a-button>
        </div>
        <div class="panel-body">
          <div v-if="policeStore.myDrafts.length === 0" class="empty-state">
            <a-empty description="暂无待审查草案" />
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
          <a-button type="link" size="small" @click="router.push('/police/cases')">查看全部</a-button>
        </div>
        <div class="panel-body">
          <div v-if="policeStore.reviewTasks.length === 0" class="empty-state">
            <a-empty description="暂无待审核任务" />
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
        </div>
      </div>

      <!-- 待处理 -->
      <div class="dashboard-panel">
        <div class="panel-header">
          <h3><ClockCircleOutlined class="panel-icon" /> 待处理</h3>
          <a-button type="link" size="small" @click="router.push('/police/cases')">查看全部</a-button>
        </div>
        <div class="panel-body">
          <div v-if="myActiveTasks.length === 0" class="empty-state">
            <a-empty description="暂无进行中任务" />
          </div>
          <TaskCard
            v-for="task in myActiveTasks"
            :key="task.id"
            :task="task"
            @click="goTask"
          />
        </div>
      </div>

      <!-- 通知：推进智能体活动 -->
      <div class="dashboard-panel">
        <div class="panel-header">
          <h3><BellOutlined class="panel-icon" /> 通知</h3>
        </div>
        <div class="panel-body">
          <div v-if="notifications.length === 0" class="empty-state">
            <a-empty description="暂无新通知" />
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

    <!-- 快捷操作 -->
    <div class="quick-actions">
      <h3>快捷操作</h3>
      <div class="quick-action-grid">
        <div class="quick-action-card" @click="router.push('/police/cases')">
          <FileSearchOutlined class="quick-action-icon" />
          <span>案件管理</span>
        </div>
        <div class="quick-action-card" @click="router.push('/police/cases')">
          <CheckCircleOutlined class="quick-action-icon" />
          <span>案件任务</span>
        </div>
        <div class="quick-action-card" @click="router.push('/police/evidence')">
          <UploadOutlined class="quick-action-icon" />
          <span>证据管理</span>
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
</template>

<style scoped>
.police-dashboard {
  padding: 24px 32px;
  max-width: 1500px;
  margin: 0 auto;
}
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}
.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 4px 0;
  color: var(--gray-1000, #1a1a1a);
}
.page-subtitle {
  font-size: 14px;
  color: var(--gray-500, #718096);
  margin: 0;
}
.header-actions {
  display: flex;
  gap: 8px;
}
.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--gray-0, #fff);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: box-shadow 0.2s;
}
.stat-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
}
.stat-label {
  font-size: 13px;
  color: var(--gray-500, #718096);
}
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
}
.dashboard-panel {
  background: var(--gray-0, #fff);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 12px;
  overflow: hidden;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
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
.panel-icon {
  color: var(--main-color, #24839b);
}
.panel-body {
  padding: 12px;
  max-height: 460px;
  overflow-y: auto;
}
.empty-state {
  padding: 32px 0;
}
.task-item {
  display: flex;
  align-items: center;
  padding: 12px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}
.task-item:hover {
  background: var(--gray-10, #f7fafc);
}
.task-item-main {
  flex: 1;
  min-width: 0;
}
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
.task-item-assignee {
  color: var(--gray-400, #a0aec0);
}
.task-item-due {
  font-size: 12px;
  color: var(--gray-500, #718096);
  white-space: nowrap;
}
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
.notify-item:hover {
  background: var(--gray-10, #f7fafc);
}
.notify-icon {
  color: #8b5cf6;
  flex-shrink: 0;
}
.notify-text {
  color: var(--gray-700, #4a5568);
}
.quick-actions h3 {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 12px 0;
}
.quick-action-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}
.quick-action-card {
  background: var(--gray-0, #fff);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 10px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  font-weight: 500;
}
.quick-action-card:hover {
  border-color: var(--main-color, #24839b);
  color: var(--main-color, #24839b);
}
.quick-action-icon {
  font-size: 24px;
}
.review-item {
  align-items: center;
}
.task-item-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
.review-modal-body {
  max-height: 60vh;
  overflow-y: auto;
}
.rm-task-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
}
.rm-section-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-600, #4a5568);
  margin-bottom: 6px;
}
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
</style>
