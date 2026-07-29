<script setup>
/**
 * ★ 任务详情页 — POLICE_REQUIREMENTS §8.4.4
 * 展示任务信息、操作按钮、事件时间线
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePoliceStore } from '@/stores/police'
import { policeTaskApi } from '@/apis/police_api'
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
  Flag
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

const assigneeTypeMap = {
  human: { text: '人工', icon: User },
  agent: { text: '智能体', icon: Bot }
}

const eventTypeMap = {
  created: { text: '任务创建', color: 'blue' },
  assigned: { text: '任务分配', color: 'cyan' },
  started: { text: '开始执行', color: 'processing' },
  completed: { text: '任务完成', color: 'gold' },
  reviewed: { text: '审核结果', color: 'green' },
  phase_changed: { text: '阶段变更', color: 'purple' }
}

// ── 计算属性 ──────────────────────────────────────────────
const statusInfo = computed(() => statusMap[task.value?.status] || statusMap.pending)
const priorityInfo = computed(() => priorityMap[task.value?.priority] || priorityMap.medium)
const assigneeInfo = computed(() => assigneeTypeMap[task.value?.assignee_type] || assigneeTypeMap.human)

const canStart = computed(() => task.value?.status === 'pending')
const canComplete = computed(() => task.value?.status === 'in_progress')
const canReview = computed(() => task.value?.status === 'review')

// ── 数据加载 ──────────────────────────────────────────────
async function loadTask() {
  loading.value = true
  try {
    const taskId = route.params.taskId
    await policeStore.loadTask(taskId)
    if (!policeStore.currentTask) {
      message.error('任务不存在')
      router.replace('/police/tasks')
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
    await policeStore.startTask(route.params.taskId)
    message.success('任务已开始执行')
    await loadTask()
    await loadEvents()
  } catch (e) {
    message.error('操作失败')
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

function goBack() {
  router.push('/police/tasks')
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
            </div>
          </div>
          <div class="task-meta-row">
            <span class="meta-item case-link" @click="goToCase">
              <Briefcase :size="14" />
              {{ task.case_name || `案件 #${task.case_id}` }}
            </span>
            <span class="meta-divider">|</span>
            <span class="meta-item">
              <component :is="assigneeInfo.icon" :size="14" />
              {{ assigneeInfo.text }}{{ task.assignee_name ? ` · ${task.assignee_name}` : '' }}
            </span>
            <span class="meta-divider" v-if="task.due_date">|</span>
            <span class="meta-item" v-if="task.due_date">
              <Calendar :size="14" />
              截止 {{ formatDateTime(task.due_date) }}
            </span>
          </div>
        </div>

        <!-- 操作按钮区 -->
        <div class="action-bar" v-if="canStart || canComplete || canReview">
          <a-button v-if="canStart" type="primary" @click="handleStart">
            <Play :size="15" style="margin-right: 4px" />
            开始执行
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
          </div>
          <div class="card-content description-text">{{ task.result }}</div>
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
                      分配给：{{ evt.event_data.assignee_name || evt.event_data.assignee_id }}
                    </template>
                    <template v-else-if="evt.event_type === 'reviewed'">
                      {{ evt.event_data.approved ? '审核通过' : '已驳回' }}
                      <span v-if="evt.event_data.comment"> — {{ evt.event_data.comment }}</span>
                    </template>
                    <template v-else-if="evt.event_type === 'completed' && evt.event_data.result">
                      结果：{{ evt.event_data.result }}
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
              <span class="info-val">{{ task.task_type || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-key">案件阶段</span>
              <span class="info-val">{{ task.phase || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-key">分配类型</span>
              <span class="info-val">{{ assigneeInfo.text }}</span>
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
