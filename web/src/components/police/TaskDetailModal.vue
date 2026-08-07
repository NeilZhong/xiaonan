<script setup>
/**
 * ★ 任务详情弹窗（Plane 风格两列布局）
 * 案件任务板块点击任务 → 以弹窗展示详情，替代整页路由跳转。
 *
 * 布局：白底圆角弹窗（rounded-2xl / shadow-2xl），约 760px 宽，
 *   左列 68% = 标题 + 正文小节 + AI 成果 + 事件时间线 + 评论区
 *   右列 32% = 属性栏（状态/处理人/开始/截止/优先级/标签）+ 操作区
 *
 * 能力（与后端 police_task_router 对齐）：
 *   - 分配处理人（多执行人：民警 + 数字警员）assign
 *   - 开始执行 start（含数字警员自动执行，轮询成果）
 *   - 提交完成 complete（写执行结果 → review）
 *   - 审核通过/驳回 review（权限：指定审核人或管理员）
 *   - 重跑 rerun（驳回/已完成/待审核 → 重置执行态重新触发）
 *
 * 技术取舍：项目无 Tailwind，按 AGENTS.md 规范用 scoped CSS + 语义 token
 * 实现同等视觉效果（语义 token 明暗自适应，符合 DESIGN.md 规范框架）。
 */
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { policeTaskApi, policeAgentApi, policeCaseApi } from '@/apis/police_api'
import { useUserStore } from '@/stores/user'
import { message } from 'ant-design-vue'
import TaskPropPopover from '@/components/police/TaskPropPopover.vue'
import TaskDatePopover from '@/components/police/TaskDatePopover.vue'
import MarkdownPreview from '@/components/common/MarkdownPreview.vue'
import {
  MessageSquare,
  MoreHorizontal,
  X,
  Calendar,
  Circle,
  Flag,
  Plus,
  Send,
  Clock,
  Play,
  CheckCircle2,
  FileCheck,
  AlertTriangle,
  RotateCcw,
  Bot,
  Users,
  Zap,
  Sparkles,
  Square,
  ChevronDown,
} from 'lucide-vue-next'
const props = defineProps({
  /** 打开时传入的任务 ID；null/0 表示关闭 */
  taskId: { type: [Number, String], default: null },
  visible: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'refresh'])

const userStore = useUserStore()

const loading = ref(false)
const task = ref(null)
const events = ref([])
const comments = ref([])
const commentText = ref('')
const commenting = ref(false)
/** 数字警员执行中（开始后轮询） */
const agentExecuting = ref(false)
let pollTimer = null

// ── 状态 / 优先级映射 ──────────────────────────────
// 状态按规格展示：待开始(Gray)/进行中(Blue)/已暂停(Orange)/已完成(Green)；
// 保留后端完整状态集（pending/in_progress/paused/review/completed/blocked/cancelled）
const statusMap = {
  pending: { text: '待开始', color: '#64748b', dot: '#94a3b8' },
  in_progress: { text: '进行中', color: '#2563eb', dot: '#3b82f6' },
  paused: { text: '已暂停', color: '#ea580c', dot: '#f97316' },
  review: { text: '待审核', color: '#d97706', dot: '#f59e0b' },
  completed: { text: '已完成', color: '#16a34a', dot: '#22c55e' },
  blocked: { text: '已驳回', color: '#dc2626', dot: '#ef4444' },
  cancelled: { text: '已取消', color: '#64748b', dot: '#94a3b8' },
}
/** 下拉选项（状态） */
const statusOptions = computed(() => ['pending', 'in_progress', 'paused', 'review', 'completed', 'blocked', 'cancelled']
  .map(k => ({ value: k, label: statusMap[k].text, dot: statusMap[k].dot })))

const priorityMap = {
  urgent: { text: '紧急', pill: 'rose' },
  high: { text: '高', pill: 'orange' },
  medium: { text: '中', pill: 'blue' },
  low: { text: '低', pill: 'green' },
}
const priorityOptions = computed(() => ['urgent', 'high', 'medium', 'low']
  .map(k => ({ value: k, label: priorityMap[k].text, pill: priorityMap[k].pill })))
const typeMap = {
  transcript_analysis: '笔录分析', fund_analysis: '资金分析', evidence_collection: '调证生成',
  evidence_submission: '证据提交', legal_review: '法制审核', document_generation: '文书生成',
  investigation: '侦查', interrogation: '审讯', arrest: '抓捕', cyber_inquiry: '网警查询',
  knowledge_extraction: '知识抽取',
}
const eventTypeMap = {
  created: { text: '创建', color: 'gray' },
  assigned: { text: '分配', color: 'blue' },
  started: { text: '开始', color: 'cyan' },
  completed: { text: '提交完成', color: 'green' },
  reviewed: { text: '审核', color: 'purple' },
  rerun: { text: '重跑', color: 'orange' },
  blocked: { text: '驳回', color: 'red' },
}

// ── 派生数据 ──────────────────────────────────────
const statusInfo = computed(() => statusMap[task.value?.status] || statusMap.pending)
const priorityInfo = computed(() => priorityMap[task.value?.priority] || priorityMap.medium)
const typeText = computed(() => typeMap[task.value?.type] || task.value?.type || '—')

const assignees = computed(() => task.value?.assignees || [])
const humanNames = computed(() => assignees.value.filter(a => a.assignee_type === 'human').map(a => a.assignee_name).filter(Boolean))
const agentNames = computed(() => assignees.value.filter(a => a.assignee_type === 'agent').map(a => a.assignee_name).filter(Boolean))
const hasAgentAssignee = computed(() => agentNames.value.length > 0)
const assigneeText = computed(() => {
  const all = [...humanNames.value, ...agentNames.value]
  if (!all.length) return task.value?.assignee_name || '未分配'
  if (all.length <= 2) return all.join('、')
  return `${all[0]} 等 ${all.length} 名`
})

/** AI 成果：result 结构化拆分（summary + 各智能体明细） */
const aiResult = computed(() => {
  const r = task.value?.result
  if (!r) return null
  if (typeof r === 'string') return { summary: r, agentResults: [], executedBy: '', raw: r }
  return {
    summary: r.summary || '',
    agentResults: Array.isArray(r.agent_results) ? r.agent_results : [],
    executedBy: r.executed_by || '',
    raw: r,
  }
})

// ════════════════════════════════════════════════════════
// ★ AI 数字警员协同工作流（idle | running | reviewing | completed）
// ════════════════════════════════════════════════════════
/** 标签（持久化到 task.extra.tags） */
const TAGS_OPTIONS = [
  { value: 'backend', label: 'backend' },
  { value: 'frontend', label: 'frontend' },
  { value: 'agent', label: 'agent' },
  { value: 'evidence', label: '证据' },
  { value: 'fund', label: '资金' },
  { value: 'urgent', label: '加急' },
]
const taskTags = computed(() => {
  const tags = task.value?.extra?.tags
  return Array.isArray(tags) ? tags : []
})
const allTags = computed(() => {
  const merged = new Map(TAGS_OPTIONS.map(t => [t.value, t]))
  taskTags.value.forEach(v => { if (!merged.has(v)) merged.set(v, { value: v, label: v }) })
  return Array.from(merged.values())
})

async function updateTags(tags) {
  try {
    const extra = { ...(task.value?.extra || {}), tags }
    await policeTaskApi.update(props.taskId, { extra })
    task.value.extra = extra
    emit('refresh')
  } catch {
    message.error('标签更新失败')
  }
}

/** AI 协助人：当前指派到本任务的数字警员 */
const aiAgent = computed(() => {
  const list = task.value?.assignees || []
  return list.find(a => a.assignee_type === 'agent') || null
})
/** AI 生命周期：idle 等待触发 / running 运行中 / reviewing 待审核 / completed 已完成 */
const aiLifecycle = computed(() => {
  if (!aiAgent.value) return null
  const st = task.value?.status
  if (st === 'completed') return 'completed'
  if (st === 'review') return 'reviewing'
  if (st === 'in_progress') return 'running'
  return 'idle'
})
const aiLifecycleText = {
  idle: '等待触发',
  running: '运行中...',
  reviewing: '待审核',
  completed: '已完成',
}
const aiLifecyclePill = {
  idle: 'gray',
  running: 'blue',
  reviewing: 'orange',
  completed: 'green',
}
/** 是否可唤醒（有 AI 且非运行中） */
const canWakeAI = computed(() => !!aiAgent.value && aiLifecycle.value !== 'running' && !['cancelled'].includes(task.value?.status))
/** 唤醒按钮文案 */
const wakeButtonText = computed(() => {
  if (aiLifecycle.value === 'idle') return '🚀 唤醒 AI 执行任务'
  if (aiLifecycle.value === 'reviewing' || aiLifecycle.value === 'completed') return '🔄 重新执行'
  return '🚀 唤醒 AI 执行任务'
})

/** AI 执行动态卡片：是否展开、取消态 */
const aiCardOpen = ref(true)
const aiSteps = ref([])
const aiCanceled = ref(false)

/** 模拟步骤日志（真实执行由后端 _execute_agents 驱动，前端展示过渡步骤 + 轮询真实状态） */
const AI_STEP_SCRIPT = [
  '正在读取案件上下文...',
  '正在检索案件材料与证据链...',
  '正在分析任务要求并规划执行路径...',
  '正在生成成果...',
]

/** 唤醒 AI：pending→start；review/completed/blocked→rerun */
async function wakeAI() {
  if (!aiAgent.value) return
  aiSteps.value = [...AI_STEP_SCRIPT]
  aiCanceled.value = false
  aiCardOpen.value = true
  agentExecuting.value = true
  try {
    if (['pending'].includes(task.value?.status)) {
      await policeTaskApi.start(props.taskId)
    } else {
      await policeTaskApi.rerun(props.taskId)
    }
    message.success('数字警员正在自动执行...')
    await load()
    emit('refresh')
    startPolling()
  } catch {
    message.error('唤醒失败')
    agentExecuting.value = false
  }
}

/** 取消执行：重置为 pending（尽力而为） */
async function cancelAI() {
  stopPolling()
  aiCanceled.value = true
  agentExecuting.value = false
  try {
    await policeTaskApi.update(props.taskId, { status: 'pending' })
    await load()
    emit('refresh')
  } catch {
    // best-effort
  }
}

// ── AI 成果审核操作 ──────────────────────────────
/** 采纳并完成：结果已由 AI 生成，审核通过归档 */
async function acceptAndComplete() {
  try {
    await policeTaskApi.review(props.taskId, true, 'AI 成果已采纳')
    message.success('已采纳并归档')
    await load()
    emit('refresh')
  } catch (e) {
    message.error(e?.message || '操作失败')
  }
}

// 重新运行（带微调 Prompt）
const rerunModalVisible = ref(false)
const rerunPrompt = ref('')
const rerunLoading = ref(false)

function openRerunModal() {
  rerunPrompt.value = ''
  rerunModalVisible.value = true
}

async function handleRerunWithPrompt() {
  rerunLoading.value = true
  try {
    const prompt = rerunPrompt.value.trim()
    if (prompt) {
      // 追加微调指引到 instructions，供 AI 下次执行参考
      const base = task.value?.instructions || task.value?.description || ''
      const newInstructions = base ? `${base}\n\n【微调要求】${prompt}` : `【微调要求】${prompt}`
      await policeTaskApi.update(props.taskId, { instructions: newInstructions })
    }
    await policeTaskApi.rerun(props.taskId)
    message.success('已重新执行' + (prompt ? '（携带微调要求）' : ''))
    rerunModalVisible.value = false
    aiSteps.value = [...AI_STEP_SCRIPT]
    aiCardOpen.value = true
    agentExecuting.value = true
    await load()
    emit('refresh')
    startPolling()
  } catch {
    message.error('重跑失败')
  } finally {
    rerunLoading.value = false
  }
}

// 驳回（带修改意见）
const rejectModalVisible = ref(false)
const rejectComment = ref('')
const rejectLoading = ref(false)

function openRejectModal() {
  rejectComment.value = ''
  rejectModalVisible.value = true
}

async function handleRejectWithFeedback() {
  rejectLoading.value = true
  try {
    await policeTaskApi.review(props.taskId, false, rejectComment.value || '需修改')
    message.success('已驳回，意见已反馈给 AI')
    rejectModalVisible.value = false
    await load()
    emit('refresh')
  } catch (e) {
    message.error(e?.message || '操作失败')
  } finally {
    rejectLoading.value = false
  }
}

/** 正文小节（描述/指引/溯源/附件） */
const sections = computed(() => {
  const t = task.value
  if (!t) return []
  const s = []
  if (t.description) s.push({ title: '内容', items: [t.description] })
  else if (t.instructions) s.push({ title: '内容', items: [t.instructions] })
  if (t.instructions && t.description) s.push({ title: '任务指引', items: [t.instructions] })
  const adv = t.extra?.advancement
  if (adv) {
    const refs = []
    if (adv.template_code) refs.push(`任务模板：${adv.template_code}`)
    if (adv.element_type) refs.push(`要素类型：${adv.element_type}（${adv.element_value || ''}）`)
    if (adv.origin === 'template') refs.push('来源：模板确定性映射')
    else if (adv.origin === 'chain') refs.push('来源：模板链式推导')
    else if (adv.origin === 'llm') refs.push('来源：智能体推演')
    if (refs.length) s.push({ title: '参考', items: refs })
  }
  if (t.attachments && t.attachments.length) {
    s.push({ title: '涉及文件', items: t.attachments.map(a => (typeof a === 'string' ? a : a.name || JSON.stringify(a))) })
  }
  if (t.require_approval === 1 || t.status === 'review') {
    const acc = ['任务产出需由指定审核人确认后方可归档']
    if (t.reviewer_id) acc.push('审核人：用户 #' + t.reviewer_id)
    s.push({ title: '验收标准', items: acc })
  }
  return s
})

// ── 按钮权限（对齐 TaskDetailView 逻辑） ────────────
const canAssign = computed(() => !!task.value && task.value.status !== 'completed')
const canStart = computed(() => task.value?.status === 'pending')
const canComplete = computed(() => task.value?.status === 'in_progress')
const canReview = computed(() => {
  if (task.value?.status !== 'review') return false
  const rid = task.value?.reviewer_id
  if (rid != null && rid !== userStore.userId && !userStore.isAdmin) return false
  return true
})
const canRerun = computed(() => ['review', 'completed', 'blocked'].includes(task.value?.status))

const startButtonText = computed(() =>
  hasAgentAssignee.value ? '开始执行（数字警员自动运行）' : '开始执行'
)

// ── 时间格式化 ────────────────────────────────────
function fmtDate(v) {
  if (!v) return ''
  return String(v).substring(0, 10)
}
function fmtDateTime(v) {
  if (!v) return ''
  const s = String(v)
  return s.length >= 16 ? s.substring(0, 16) : s
}

// ── 加载 ──────────────────────────────────────────
async function load() {
  if (!props.taskId) return
  loading.value = true
  try {
    const [taskRes, eventsRes] = await Promise.allSettled([
      policeTaskApi.get(props.taskId),
      policeTaskApi.events(props.taskId),
    ])
    task.value = taskRes.status === 'fulfilled' ? taskRes.value.data || null : null
    events.value = eventsRes.status === 'fulfilled' ? eventsRes.value.data || [] : []
    await loadComments()
    // 预加载处理人选项（民警 + 数字警员），供右侧属性栏浮层即时可用
    loadAssignOptions()
  } catch {
    task.value = null
    message.error('任务加载失败')
  } finally {
    loading.value = false
  }
}

async function loadComments() {
  if (!props.taskId) return
  try {
    const res = await policeTaskApi.comments(props.taskId)
    comments.value = res.data || []
  } catch {
    comments.value = []
  }
}

async function submitComment() {
  const text = commentText.value.trim()
  if (!text) return
  commenting.value = true
  try {
    await policeTaskApi.addComment(props.taskId, text)
    commentText.value = ''
    await loadComments()
  } catch {
    message.error('评论发送失败')
  } finally {
    commenting.value = false
  }
}

// ── 分配处理人（多执行人浮层 / 弹窗共用） ──────────
const assignModalVisible = ref(false)
const assignLoading = ref(false)
const assignForm = ref({ selectedHumans: [], selectedAgents: [] })
const humanOptions = ref([])
const agentOptions = ref([])
const optionsLoading = ref(false)

/** 处理人浮层选项：AI 数字警员分组 + 办案民警分组（带 AI 标识） */
const assigneeOptions = computed(() => {
  const humans = humanOptions.value.map(h => ({
    value: `human:${h.value}`, label: h.label, name: h.name, type: 'human', group: '办案民警',
  }))
  const agents = agentOptions.value.map(a => ({
    value: `agent:${a.value}`, label: a.label, name: a.name, type: 'agent', group: 'AI 数字警员',
    icon: Bot,
  }))
  return [...agents, ...humans]
})

/** 当前执行人 → 浮层选中值（'human:1' / 'agent:2'） */
const assigneeSelectedValues = computed(() => {
  const list = task.value?.assignees || []
  return list.map(a => `${a.assignee_type}:${a.assignee_id}`)
})

/** 浮层多选变更：统一走 assign API（民警 + 数字警员） */
async function handleAssigneePick(picks) {
  const payload = picks.map(p => {
    const [type, id] = String(p).split(':')
    const opt = assigneeOptions.value.find(o => o.value === p)
    return {
      assignee_type: type,
      assignee_id: Number(id),
      assignee_name: opt?.name || opt?.label || '',
      role: 'executor',
    }
  })
  if (payload.length === 0) {
    message.warning('请至少选择一名处理人')
    return
  }
  assignLoading.value = true
  try {
    await policeTaskApi.assign(props.taskId, { assignees: payload })
    message.success(`处理人已更新为 ${payload.length} 名`)
    await load()
    emit('refresh')
  } catch {
    message.error('分配失败')
  } finally {
    assignLoading.value = false
  }
}

function showAssignModal() {
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
  optionsLoading.value = true
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
      humanOptions.value = (caseRes.value.members || []).map(m => ({
        label: `${m.username || '未命名'} (${{ commander: '指挥员', handler: '办案人', reviewer: '审核员', observer: '观察员' }[m.role] || m.role})`,
        value: m.user_id,
        name: m.username || '',
      }))
    }
  } catch {
    // 加载失败不阻塞
  } finally {
    optionsLoading.value = false
  }
}

async function handleAssign() {
  const payload = [
    ...assignForm.value.selectedHumans.map(h => ({
      assignee_type: 'human', assignee_id: h.value,
      assignee_name: h.name || h.label || '', role: 'executor',
    })),
    ...assignForm.value.selectedAgents.map(a => ({
      assignee_type: 'agent', assignee_id: a.value,
      assignee_name: a.name || a.label || '', role: 'executor',
    })),
  ]
  if (payload.length === 0) {
    message.warning('请至少选择一名办案民警或数字警员')
    return
  }
  assignLoading.value = true
  try {
    await policeTaskApi.assign(props.taskId, { assignees: payload })
    message.success(`任务已分配给 ${payload.length} 名执行人`)
    assignModalVisible.value = false
    await load()
    emit('refresh')
  } catch {
    message.error('分配失败')
  } finally {
    assignLoading.value = false
  }
}

// ── 执行 / 完成 / 审核 / 重跑 ─────────────────────
async function handleStart() {
  try {
    agentExecuting.value = hasAgentAssignee.value
    await policeTaskApi.start(props.taskId)
    message.success(hasAgentAssignee.value ? '任务已启动，数字警员正在自动执行...' : '任务已开始执行')
    await load()
    emit('refresh')
    if (hasAgentAssignee.value) startPolling()
  } catch {
    message.error('操作失败')
    agentExecuting.value = false
  }
}

/** 轮询数字警员执行结果（开始后每 3s 查一次，直到进入 review/completed） */
function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const res = await policeTaskApi.get(props.taskId)
      task.value = res.data || task.value
      if (['review', 'completed', 'blocked'].includes(task.value?.status)) {
        stopPolling()
        agentExecuting.value = false
        message.info(task.value.status === 'review' ? '数字警员执行完成，待审核' : '任务状态已更新')
        emit('refresh')
      }
    } catch {
      // 轮询失败静默，下轮重试
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

// 完成弹窗
const completeModalVisible = ref(false)
const completeResult = ref('')
const completeLoading = ref(false)

function showCompleteModal() {
  completeResult.value = ''
  completeModalVisible.value = true
}

async function handleComplete() {
  completeLoading.value = true
  try {
    await policeTaskApi.complete(props.taskId, completeResult.value ? { summary: completeResult.value } : null)
    message.success('任务已完成，等待审核')
    completeModalVisible.value = false
    await load()
    emit('refresh')
  } catch {
    message.error('操作失败')
  } finally {
    completeLoading.value = false
  }
}

// 审核弹窗
const reviewModalVisible = ref(false)
const reviewApproved = ref(true)
const reviewComment = ref('')
const reviewLoading = ref(false)

function showReviewModal(approved) {
  reviewApproved.value = approved
  reviewComment.value = ''
  reviewModalVisible.value = true
}

async function handleReview() {
  reviewLoading.value = true
  try {
    await policeTaskApi.review(props.taskId, reviewApproved.value, reviewComment.value)
    message.success(reviewApproved.value ? '审核通过' : '已驳回')
    reviewModalVisible.value = false
    await load()
    emit('refresh')
  } catch (e) {
    message.error(e?.message || '操作失败')
  } finally {
    reviewLoading.value = false
  }
}

/** 重跑：重置执行态并重新触发（有数字警员则自动执行） */
async function handleRerun() {
  try {
    agentExecuting.value = hasAgentAssignee.value
    await policeTaskApi.rerun(props.taskId)
    message.success('任务已重跑' + (hasAgentAssignee.value ? '，数字警员正在自动执行...' : ''))
    await load()
    emit('refresh')
    if (hasAgentAssignee.value) startPolling()
  } catch {
    message.error('重跑失败')
    agentExecuting.value = false
  }
}

// ── 属性编辑 ──────────────────────────────────────
async function updatePriority(value) {
  try {
    await policeTaskApi.update(props.taskId, { priority: value })
    task.value.priority = value
    message.success('优先级已更新')
    emit('refresh')
  } catch {
    message.error('更新失败')
  }
}

async function updateStatus(value) {
  try {
    await policeTaskApi.update(props.taskId, { status: value })
    task.value.status = value
    message.success('状态已更新')
    emit('refresh')
  } catch {
    message.error('更新失败')
  }
}

async function updateDueDate(value) {
  try {
    await policeTaskApi.update(props.taskId, { due_date: value || null })
    task.value.due_date = value || null
    message.success(value ? `截止日期已设为 ${value}` : '已清除截止日期')
    emit('refresh')
  } catch {
    message.error('更新失败')
  }
}

/** 评论输入框聚焦（header 评论图标） */
function focusComment() {
  nextTick(() => {
    document.querySelector('.tdm-comment-input input')?.focus()
  })
}

function close() {
  stopPolling()
  emit('close')
}

watch(() => [props.visible, props.taskId], ([v]) => {
  if (v) load()
  else stopPolling()
})

onBeforeUnmount(stopPolling)
</script>

<template>
  <a-modal
    :open="props.visible"
    :footer="null"
    :closable="false"
    width="760px"
    wrap-class-name="tdm-wrap"
    :body-style="{ padding: 0 }"
    class="task-detail-modal"
    @cancel="close"
  >
    <div class="tdm" v-if="task">
      <!-- 两列主体：左 68% 主内容 + 右 32% 属性栏 -->
      <div class="tdm-body">
        <!-- ══ 左列：主内容 ══ -->
        <div class="tdm-main">
          <!-- 顶部 Header：标题 + 轻量图标 -->
          <header class="tdm-header">
            <h2 class="tdm-title">{{ task.title }}</h2>
            <div class="tdm-header-actions">
              <button class="tdm-icon-btn" title="评论" @click="focusComment">
                <MessageSquare :size="16" />
              </button>
              <button class="tdm-icon-btn" title="刷新" @click="load">
                <MoreHorizontal :size="16" />
              </button>
              <button class="tdm-icon-btn" title="关闭" @click="close">
                <X :size="16" />
              </button>
            </div>
          </header>

          <!-- 摘要行：状态徽章 + 优先级 + 类型 + AI执行中 -->
          <div class="tdm-summary">
            <span class="tdm-chip" :style="{ color: statusInfo.color, background: statusInfo.color + '14' }">
              <span class="tdm-dot" :style="{ background: statusInfo.dot }"></span>
              {{ statusInfo.text }}
            </span>
            <span class="tdm-priority" :class="`is-${priorityInfo.pill}`">{{ priorityInfo.text }}</span>
            <span class="tdm-type">{{ typeText }}</span>
            <span v-if="agentExecuting" class="tdm-ai-running">
              <Zap :size="11" /> 数字警员执行中
            </span>
          </div>

          <!-- 操作区：按状态显示可用操作 -->
          <div class="tdm-actions" v-if="canAssign || canStart || canComplete || canReview || canRerun">
            <button v-if="canAssign" class="tdm-act-btn" @click="showAssignModal">
              <Users :size="13" /> 分配处理人
            </button>
            <button v-if="canStart" class="tdm-act-btn is-primary" @click="handleStart">
              <Play :size="13" /> {{ startButtonText }}
            </button>
            <button v-if="canComplete" class="tdm-act-btn is-primary" @click="showCompleteModal">
              <CheckCircle2 :size="13" /> 提交完成
            </button>
            <template v-if="canReview">
              <button class="tdm-act-btn is-success" @click="showReviewModal(true)">
                <FileCheck :size="13" /> 审核通过
              </button>
              <button class="tdm-act-btn is-danger" @click="showReviewModal(false)">
                <AlertTriangle :size="13" /> 驳回
              </button>
            </template>
            <button v-if="canRerun" class="tdm-act-btn" title="重新执行（清空上次结果）" @click="handleRerun">
              <RotateCcw :size="13" /> 重跑
            </button>
          </div>

          <!-- ★ AI 执行动态卡片（running 时展示，浅紫高亮，可折叠） -->
          <div class="tdm-ai-live" v-if="aiLifecycle === 'running'">
            <div class="tdm-ai-live-head" @click="aiCardOpen = !aiCardOpen">
              <span class="tdm-ai-live-title">
                <span class="tdm-ai-live-pulse"></span>
                <Zap :size="13" /> AI 执行中
              </span>
              <div class="tdm-ai-live-actions">
                <button class="tdm-ai-cancel" @click.stop="cancelAI">
                  <Square :size="11" /> 取消执行
                </button>
                <ChevronDown :size="13" :class="{ 'is-open': aiCardOpen }" class="tdm-ai-live-chevron" />
              </div>
            </div>
            <div v-show="aiCardOpen" class="tdm-ai-live-body">
              <div v-for="(step, i) in aiSteps" :key="i" class="tdm-ai-step">
                <span class="tdm-ai-step-dot" :class="{ done: i < aiSteps.length - 1 }"></span>
                <span class="tdm-ai-step-text" :class="{ done: i < aiSteps.length - 1 }">{{ step }}</span>
                <span v-if="i === aiSteps.length - 1" class="tdm-ai-step-spinner"></span>
              </div>
              <div class="tdm-ai-live-note" v-if="aiCanceled">已取消执行，可重新唤醒</div>
            </div>
          </div>

          <!-- 正文小节 -->
          <div class="tdm-sections">
            <section v-for="(sec, i) in sections" :key="i" class="tdm-section">
              <h3 class="tdm-section-title">{{ sec.title }}</h3>
              <ul class="tdm-section-list">
                <li v-for="(item, j) in sec.items" :key="j">{{ item }}</li>
              </ul>
            </section>
            <div v-if="!sections.length" class="tdm-empty">暂无详细描述</div>
          </div>

          <!-- ★ AI 产出成果卡片（reviewing/completed 时展示 + 审核操作栏） -->
          <div class="tdm-ai-deliverable" v-if="aiResult && (aiLifecycle === 'reviewing' || aiLifecycle === 'completed')">
            <div class="tdm-ai-deliverable-head">
              <h3 class="tdm-section-title">
                <Sparkles :size="13" class="ai-sparkle" />
                AI 产出成果
                <span v-if="aiResult.executedBy === 'agent_auto'" class="tdm-ai-badge">
                  <Zap :size="10" /> 数字警员自动生成
                </span>
              </h3>
            </div>

            <!-- 成果内容：Markdown 渲染 / 结构化摘要 -->
            <div class="tdm-ai-deliverable-body">
              <template v-if="typeof aiResult.raw === 'string'">
                <MarkdownPreview :content="aiResult.raw" :code-copy="true" compact />
              </template>
              <template v-else>
                <div v-if="aiResult.summary" class="tdm-ai-summary">
                  <MarkdownPreview :content="aiResult.summary" :code-copy="true" compact />
                </div>
                <details v-if="aiResult.agentResults.length" class="tdm-ai-details">
                  <summary class="tdm-ai-summary-toggle">
                    查看各数字警员详细结果 ({{ aiResult.agentResults.length }})
                  </summary>
                  <div v-for="(ar, idx) in aiResult.agentResults" :key="idx" class="tdm-ai-agent">
                    <div class="tdm-ai-agent-head">
                      <Bot :size="13" />
                      <strong>{{ ar.agent_name }}</strong>
                      <span v-if="ar.error" class="tdm-ai-error">执行错误</span>
                    </div>
                    <div v-if="ar.result" class="tdm-ai-agent-result">
                      <MarkdownPreview :content="ar.result" :code-copy="true" compact />
                    </div>
                    <span v-if="ar.error" class="tdm-ai-error-text">{{ ar.error }}</span>
                  </div>
                </details>
              </template>
            </div>

            <!-- 审核操作栏 -->
            <div class="tdm-ai-deliverable-actions" v-if="aiLifecycle === 'reviewing'">
              <button class="tdm-ai-act is-accept" @click="acceptAndComplete">
                <CheckCircle2 :size="13" /> 采纳并完成
              </button>
              <button class="tdm-ai-act" @click="openRerunModal">
                <RotateCcw :size="13" /> 重新运行
              </button>
              <button class="tdm-ai-act is-reject" @click="openRejectModal">
                <AlertTriangle :size="13" /> 驳回/修改
              </button>
            </div>
          </div>

          <!-- 审核信息 -->
          <div class="tdm-review" v-if="task.reviewed_by">
            <span class="tdm-review-label"><FileCheck :size="13" /> 已审核</span>
            <span>{{ task.reviewed_by_name || task.reviewed_by }} · {{ fmtDateTime(task.reviewed_at) }}</span>
            <code v-if="task.signed_hash" class="tdm-hash">{{ task.signed_hash.slice(0, 24) }}…</code>
          </div>

          <!-- 事件时间线 -->
          <div class="tdm-timeline">
            <h3 class="tdm-section-title">动态</h3>
            <a-empty v-if="!events.length" description="暂无动态" :image="null" />
            <div v-else class="tdm-timeline-list">
              <div v-for="(evt, idx) in events" :key="idx" class="tdm-tl-item">
                <span class="tdm-tl-dot" :style="{ background: eventTypeMap[evt.event_type]?.color === 'red' ? '#ef4444' : (eventTypeMap[evt.event_type]?.color === 'green' ? '#22c55e' : (eventTypeMap[evt.event_type]?.color === 'orange' ? '#f59e0b' : (eventTypeMap[evt.event_type]?.color === 'purple' ? '#8b5cf6' : (eventTypeMap[evt.event_type]?.color === 'cyan' ? '#06b6d4' : (eventTypeMap[evt.event_type]?.color === 'blue' ? '#3b82f6' : '#94a3b8'))))) }"></span>
                <div class="tdm-tl-content">
                  <span class="tdm-tl-type">{{ eventTypeMap[evt.event_type]?.text || evt.event_type }}</span>
                  <span class="tdm-tl-time">{{ fmtDateTime(evt.created_at) }}</span>
                  <div v-if="evt.event_type === 'reviewed'" class="tdm-tl-desc">
                    {{ evt.event_data?.approved ? '审核通过' : '已驳回' }}<span v-if="evt.event_data?.comment"> — {{ evt.event_data.comment }}</span>
                  </div>
                  <div v-else-if="evt.event_type === 'assigned'" class="tdm-tl-desc">
                    分配给 {{ evt.event_data?.count || evt.event_data?.assignees?.length || evt.event_data?.assignee_name || '' }} 名执行人
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 评论区 -->
          <div class="tdm-comments">
            <h3 class="tdm-section-title">评论 <span class="tdm-count" v-if="comments.length">{{ comments.length }}</span></h3>
            <div v-if="comments.length" class="tdm-comment-list">
              <div v-for="c in comments" :key="c.id" class="tdm-comment">
                <span class="tdm-comment-name">{{ c.user_name || '匿名' }}</span>
                <span class="tdm-comment-text">{{ c.content }}</span>
                <span class="tdm-comment-time">{{ fmtDateTime(c.created_at) }}</span>
              </div>
            </div>
            <div v-else class="tdm-comment-empty">暂无评论，说点什么吧</div>

            <div class="tdm-comment-input">
              <input
                v-model="commentText"
                class="tdm-input"
                placeholder="添加评论"
                @keyup.enter="submitComment"
              />
              <button class="tdm-send-btn" :disabled="commenting || !commentText.trim()" @click="submitComment">
                <Send :size="14" />
              </button>
            </div>
          </div>
        </div>

        <!-- ══ 右列：属性栏 ══ -->
        <aside class="tdm-sidebar">
          <!-- 状态：点击开合下拉（对勾切换） -->
          <div class="tdm-prop">
            <span class="tdm-prop-label"><Circle :size="13" :color="statusInfo.dot" /> 状态</span>
            <TaskPropPopover
              :model-value="task.status"
              :options="statusOptions"
              width="190"
              @update:model-value="updateStatus"
            >
              <template #trigger>
                <span class="tdm-field-trigger" :style="{ color: statusInfo.color }">
                  <span class="tdm-dot" :style="{ background: statusInfo.dot }"></span>
                  {{ statusInfo.text }}
                  <ChevronDown :size="12" class="tdm-field-chevron" />
                </span>
              </template>
            </TaskPropPopover>
          </div>

          <!-- 处理人：搜索 + AI 分组 + 复选浮层 -->
          <div class="tdm-prop">
            <span class="tdm-prop-label"><span class="tdm-avatar">N</span> 处理人</span>
            <TaskPropPopover
              :model-value="assigneeSelectedValues"
              :options="assigneeOptions"
              multiple
              searchable
              search-placeholder="搜索处理人"
              width="240"
              @update:model-value="handleAssigneePick"
            >
              <template #trigger>
                <span class="tdm-field-trigger">
                  {{ assigneeText }}
                  <Plus v-if="canAssign" :size="12" class="tdm-field-chevron" />
                </span>
              </template>
            </TaskPropPopover>
          </div>

          <!-- 开始日期（系统记录，只读展示） -->
          <div class="tdm-prop">
            <span class="tdm-prop-label"><Calendar :size="13" /> 开始日期</span>
            <span class="tdm-prop-value">{{ fmtDate(task.started_at || task.assigned_at) || '—' }}</span>
          </div>

          <!-- 截止日期：日历浮层可编辑 -->
          <div class="tdm-prop">
            <span class="tdm-prop-label"><Clock :size="13" /> 截止日期</span>
            <TaskDatePopover
              :model-value="task.due_date ? fmtDate(task.due_date) : null"
              placeholder="选择截止日期"
              @update:model-value="updateDueDate"
            />
          </div>

          <!-- 优先级：搜索/新增 + 色块 + 下拉 -->
          <div class="tdm-prop">
            <span class="tdm-prop-label"><Flag :size="13" /> 优先级</span>
            <TaskPropPopover
              :model-value="task.priority"
              :options="priorityOptions"
              width="180"
              @update:model-value="updatePriority"
            >
              <template #trigger>
                <span class="tdm-field-trigger">
                  <span class="tdm-priority-dot" :class="`is-${priorityInfo.pill}`"></span>
                  {{ priorityInfo.text }}
                  <ChevronDown :size="12" class="tdm-field-chevron" />
                </span>
              </template>
            </TaskPropPopover>
          </div>

          <!-- 标签：搜索 + 多选 + 外部同步 -->
          <div class="tdm-prop tdm-prop-tags">
            <span class="tdm-prop-label">标签</span>
            <TaskPropPopover
              :model-value="taskTags"
              :options="allTags"
              multiple
              searchable
              search-placeholder="搜索标签"
              width="200"
              empty-text="输入回车新增"
              @update:model-value="updateTags"
            >
              <template #trigger>
                <div class="tdm-tags tdm-tags-trigger">
                  <span v-if="taskTags.length === 0" class="tdm-tag is-add">+ 添加标签</span>
                  <template v-else>
                    <span v-for="t in taskTags.slice(0, 3)" :key="t" class="tdm-tag">{{ t }}</span>
                    <span v-if="taskTags.length > 3" class="tdm-tag">+{{ taskTags.length - 3 }}</span>
                  </template>
                </div>
              </template>
            </TaskPropPopover>
            <span v-if="!taskTags.length" class="tdm-tags-static">{{ typeText }} · {{ task.phase || '未分阶段' }}</span>
          </div>

          <!-- ★ AI 协助人 -->
          <div class="tdm-prop tdm-ai-prop">
            <span class="tdm-prop-label"><Sparkles :size="13" class="ai-sparkle" /> AI 协助人</span>
            <div class="tdm-ai-row">
              <template v-if="aiAgent">
                <span class="tdm-ai-chip">
                  <Bot :size="13" class="ai-sparkle" />
                  {{ aiAgent.assignee_name }}
                </span>
                <span class="tdm-ai-pill" :class="`is-${aiLifecyclePill[aiLifecycle]}`">
                  <span v-if="aiLifecycle === 'running'" class="tdm-ai-spin"></span>
                  {{ aiLifecycleText[aiLifecycle] }}
                </span>
              </template>
              <button v-else class="tdm-ai-assign" @click="showAssignModal">
                <Plus :size="12" /> 指派数字警员
              </button>
            </div>
            <button v-if="canWakeAI" class="tdm-wake-btn" @click="wakeAI">
              {{ wakeButtonText }}
            </button>
          </div>

          <!-- 新增属性 -->
          <button class="tdm-add-prop">
            <Plus :size="13" />
            新增属性
          </button>

          <!-- 创建时间脚注 -->
          <div class="tdm-footnote">创建于 {{ fmtDateTime(task.created_at) }}</div>
        </aside>
      </div>
    </div>

    <!-- 加载态 -->
    <div class="tdm-loading" v-else-if="loading">
      <a-spin />
    </div>
  </a-modal>

  <!-- 分配处理人弹窗 -->
  <a-modal
    v-model:open="assignModalVisible"
    title="分配处理人"
    :confirm-loading="assignLoading"
    @ok="handleAssign"
    ok-text="确认分配"
    cancel-text="取消"
    width="520px"
  >
    <a-form layout="vertical" style="margin-top: 12px">
      <a-form-item label="办案民警（可多选）">
        <a-select
          mode="multiple"
          v-model:value="assignForm.selectedHumans"
          :options="humanOptions"
          placeholder="选择要分配的办案民警"
          :loading="optionsLoading"
          allow-clear
          show-search
          option-filter-prop="label"
        />
      </a-form-item>
      <a-form-item label="数字警员（可多选，将自动执行）">
        <a-select
          mode="multiple"
          v-model:value="assignForm.selectedAgents"
          :options="agentOptions"
          placeholder="选择要参与的数字警员（可选）"
          :loading="optionsLoading"
          allow-clear
          show-search
          option-filter-prop="label"
        />
      </a-form-item>
      <div v-if="assignForm.selectedAgents.length" class="tdm-assign-hint">
        <Zap :size="13" />
        分配数字警员后，开始执行时警员将自动完成任务并产出成果，由你审核后归档。
      </div>
    </a-form>
  </a-modal>

  <!-- 提交完成弹窗 -->
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
      :rows="4"
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
      :rows="4"
      :maxlength="500"
      show-count
    />
  </a-modal>

  <!-- 重新运行（带微调 Prompt）弹窗 -->
  <a-modal
    v-model:open="rerunModalVisible"
    title="🔄 重新运行 AI"
    :confirm-loading="rerunLoading"
    @ok="handleRerunWithPrompt"
    ok-text="重新运行"
    cancel-text="取消"
  >
    <div class="tdm-modal-hint">
      可输入微调要求（可选），将附加到任务指引后供 AI 下次执行参考。
    </div>
    <a-textarea
      v-model:value="rerunPrompt"
      placeholder="例如：增加日志输出后重试；补充资金来源分析维度..."
      :rows="3"
      :maxlength="500"
      show-count
    />
  </a-modal>

  <!-- 驳回/修改（带反馈意见）弹窗 -->
  <a-modal
    v-model:open="rejectModalVisible"
    title="❌ 驳回 / 修改要求"
    :confirm-loading="rejectLoading"
    @ok="handleRejectWithFeedback"
    ok-text="提交驳回"
    cancel-text="取消"
    :ok-button-props="{ danger: true }"
  >
    <div class="tdm-modal-hint">
      填写修改意见，将反馈给 AI 用于下一轮生成。
    </div>
    <a-textarea
      v-model:value="rejectComment"
      placeholder="例如：分析维度不全，缺少资金去向追踪；补充取证建议..."
      :rows="3"
      :maxlength="500"
      show-count
    />
  </a-modal>
</template>

<style scoped>
/* 规格：白底圆角弹窗（rounded-2xl ≈ 16px）、shadow-2xl 阴影、两列布局
 * modal 经 teleport 挂到 body，scoped :deep 匹配不到，用 wrapClassName + 全局样式
 */
:global(.tdm-wrap .ant-modal-content) {
  border-radius: 16px;
  padding: 0;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}
:global(.tdm-wrap .ant-modal-body) {
  max-height: 78vh;
  overflow: auto;
}

.tdm-body {
  display: flex;
  background: var(--gray-0, #fff);
  color: var(--gray-1000, #0f172a);
}

/* ── 左列主内容 68% ── */
.tdm-main {
  flex: 0 0 68%;
  max-width: 68%;
  padding: 20px 22px;
  border-right: 1px solid var(--gray-50, #e2e8f0);
  display: flex;
  flex-direction: column;
}

.tdm-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.tdm-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--gray-1000, #0f172a);
  line-height: 1.35;
  margin: 0;
  word-break: break-word;
}
.tdm-header-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
.tdm-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-500, #64748b);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.tdm-icon-btn:hover { background: var(--gray-50, #e2e8f0); color: var(--gray-800, #334155); }
.tdm-icon-btn:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 1px;
}

.tdm-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 0 10px;
  flex-wrap: wrap;
}
.tdm-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 500;
  padding: 2px 10px;
  border-radius: 9999px;
}
.tdm-dot { width: 7px; height: 7px; border-radius: 50%; }
.tdm-priority {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 9999px;
}
.tdm-priority.is-rose { background: #ffe4e6; color: #e11d48; }
.tdm-priority.is-orange { background: #ffedd5; color: #ea580c; }
.tdm-priority.is-blue { background: #dbeafe; color: #2563eb; }
.tdm-priority.is-green { background: #dcfce7; color: #16a34a; }
.tdm-priority.is-default { background: var(--gray-50, #e2e8f0); color: var(--gray-600, #475569); }
.tdm-type { font-size: 12px; color: var(--gray-500, #64748b); }
.tdm-ai-running {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #6d28d9;
  background: #f5f3ff;
  padding: 2px 10px;
  border-radius: 9999px;
}

/* 操作区 */
.tdm-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}
.tdm-act-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  font-weight: 500;
  padding: 5px 14px;
  border-radius: 8px;
  border: 1px solid var(--gray-50, #e2e8f0);
  background: var(--gray-0, #fff);
  color: var(--gray-700, #334155);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}
.tdm-act-btn:hover { border-color: var(--main-color, #24839b); color: var(--main-color, #24839b); }
.tdm-act-btn:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 1px;
}
.tdm-act-btn.is-primary { background: var(--main-color, #24839b); border-color: var(--main-color, #24839b); color: #fff; }
.tdm-act-btn.is-primary:hover { opacity: 0.88; color: #fff; }
.tdm-act-btn.is-success { background: var(--color-success-500, #22c55e); border-color: var(--color-success-500, #22c55e); color: #fff; }
.tdm-act-btn.is-success:hover { opacity: 0.88; color: #fff; }
.tdm-act-btn.is-danger { background: var(--color-error-500, #ef4444); border-color: var(--color-error-500, #ef4444); color: #fff; }
.tdm-act-btn.is-danger:hover { opacity: 0.88; color: #fff; }

.tdm-sections { flex: 1; }
.tdm-section { margin-bottom: 18px; }
.tdm-section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 700;
  color: var(--gray-1000, #0f172a);
  margin: 0 0 8px;
}
.tdm-section-list {
  margin: 0;
  padding-left: 20px;
  color: var(--gray-600, #475569);
  font-size: 14px;
  line-height: 1.7;
}
.tdm-section-list li + li { margin-top: 4px; }
.tdm-empty { color: var(--gray-400, #94a3b8); font-size: 13px; }

/* ★ AI 成果 */
.tdm-ai-result {
  margin-bottom: 18px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #faf9ff;
  border: 1px solid #ede9fe;
}
.tdm-ai-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  font-weight: 600;
  color: #6d28d9;
  background: #ede9fe;
  padding: 1px 8px;
  border-radius: 9999px;
}
.tdm-ai-summary {
  font-size: 13px;
  color: var(--gray-700, #334155);
  line-height: 1.6;
  white-space: pre-wrap;
}
.tdm-ai-details { margin-top: 8px; }
.tdm-ai-summary-toggle {
  cursor: pointer;
  font-size: 12px;
  color: var(--main-color, #24839b);
}
.tdm-ai-agent {
  margin-top: 8px;
  padding: 8px 10px;
  background: var(--gray-0, #fff);
  border-radius: 8px;
  border: 1px solid var(--gray-50, #e2e8f0);
}
.tdm-ai-agent-head {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--gray-700, #334155);
}
.tdm-ai-pre {
  white-space: pre-wrap;
  font-size: 12px;
  margin: 6px 0 0;
  color: var(--gray-600, #475569);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.tdm-ai-error { color: var(--color-error-500, #ef4444); font-size: 11px; margin-left: auto; }
.tdm-ai-error-text { color: var(--color-error-500, #ef4444); font-size: 12px; }

/* 审核信息 */
.tdm-review {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 12px;
  color: var(--gray-500, #64748b);
  margin-bottom: 14px;
}
.tdm-review-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--color-success-500, #22c55e);
  font-weight: 600;
}
.tdm-hash {
  font-size: 11px;
  background: var(--gray-10, #f1f5f9);
  padding: 2px 6px;
  border-radius: 4px;
}

/* 事件时间线 */
.tdm-timeline { margin-bottom: 16px; }
.tdm-timeline-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 160px;
  overflow: auto;
}
.tdm-tl-item {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.tdm-tl-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 5px;
  flex-shrink: 0;
}
.tdm-tl-content { display: flex; flex-direction: column; gap: 1px; }
.tdm-tl-type { font-size: 12px; font-weight: 600; color: var(--gray-700, #334155); }
.tdm-tl-time { font-size: 11px; color: var(--gray-400, #94a3b8); }
.tdm-tl-desc { font-size: 12px; color: var(--gray-500, #64748b); }

/* 评论区 */
.tdm-comments { margin-top: 8px; }
.tdm-count {
  font-size: 12px;
  font-weight: 500;
  color: var(--gray-400, #94a3b8);
}
.tdm-comment-list { margin-bottom: 10px; }
.tdm-comment {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 13px;
  padding: 6px 0;
}
.tdm-comment-name { font-weight: 600; color: var(--gray-700, #334155); flex-shrink: 0; }
.tdm-comment-text { color: var(--gray-600, #475569); flex: 1; word-break: break-word; }
.tdm-comment-time { color: var(--gray-400, #94a3b8); font-size: 12px; flex-shrink: 0; }
.tdm-comment-empty { color: var(--gray-400, #94a3b8); font-size: 13px; margin-bottom: 10px; }

.tdm-comment-input {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--gray-10, #f1f5f9);
  border-radius: 10px;
  padding: 6px 8px 6px 14px;
}
.tdm-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 13px;
  color: var(--gray-1000, #0f172a);
  padding: 6px 0;
}
.tdm-input::placeholder { color: var(--gray-400, #94a3b8); }
.tdm-input:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 2px;
  border-radius: 4px;
}
.tdm-send-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 8px;
  background: var(--main-color, #24839b);
  color: #fff;
  cursor: pointer;
  transition: opacity 0.15s;
}
.tdm-send-btn:hover { opacity: 0.88; }
.tdm-send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.tdm-send-btn:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 1px;
}

/* ── 右列属性栏 32% ── */
.tdm-sidebar {
  flex: 1;
  min-width: 0;
  padding: 20px 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.tdm-prop {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
}
.tdm-prop-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--gray-500, #64748b);
  font-size: 12px;
}
.tdm-prop-value {
  color: var(--gray-800, #1e293b);
  word-break: break-word;
}
.tdm-prop-value.is-overdue {
  color: var(--color-error-500, #dc2626);
  font-weight: 600;
}
.tdm-assignee-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  padding: 0;
  font-size: 13px;
  color: var(--gray-800, #1e293b);
  cursor: pointer;
  text-align: left;
}
.tdm-assignee-btn:hover { color: var(--main-color, #24839b); }
.tdm-assignee-btn:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 1px;
  border-radius: 4px;
}
.tdm-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #22c55e;
  color: #fff;
  font-size: 10px;
  font-weight: 700;
}
.tdm-select { width: 100%; }
.tdm-prop-tags { gap: 6px; }
.tdm-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.tdm-tag {
  font-size: 12px;
  background: var(--gray-10, #f1f5f9);
  color: var(--gray-600, #475569);
  padding: 2px 10px;
  border-radius: 9999px;
}
.tdm-add-prop {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  align-self: flex-start;
  border: none;
  background: transparent;
  color: var(--gray-500, #64748b);
  font-size: 13px;
  cursor: pointer;
  padding: 4px 0;
}
.tdm-add-prop:hover { color: var(--main-color, #24839b); }
.tdm-add-prop:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 1px;
  border-radius: 4px;
}
.tdm-footnote {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--gray-50, #e2e8f0);
  color: var(--gray-400, #94a3b8);
  font-size: 12px;
}
.tdm-assign-hint {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  color: #6d28d9;
  background: #f5f3ff;
  border-radius: 8px;
  padding: 8px 10px;
}

.tdm-loading { padding: 60px 0; text-align: center; }

/* 窄屏：两列 → 上下堆叠 */
@media (max-width: 640px) {
  .tdm-body { flex-direction: column; }
  .tdm-main {
    flex: 1;
    max-width: 100%;
    border-right: none;
    border-bottom: 1px solid var(--gray-50, #e2e8f0);
  }
}

/* 减少动效偏好 */
@media (prefers-reduced-motion: reduce) {
  .tdm-icon-btn, .tdm-send-btn, .tdm-add-prop, .tdm-act-btn { transition: none; }
}

/* ═══════ 属性栏字段触发器（Click-to-Open） ═══════ */
.tdm-field-trigger {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  width: 100%;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  font-size: 13px;
  color: var(--gray-800, #1e293b);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.tdm-field-trigger:hover { background: var(--gray-10, #f1f5f9); border-color: var(--gray-50, #e2e8f0); }
.tdm-field-trigger:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 1px;
}
.tdm-field-chevron { color: var(--gray-400, #94a3b8); margin-left: auto; flex-shrink: 0; }
.tdm-priority-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}
.tdm-priority-dot.is-rose { background: #f43f5e; }
.tdm-priority-dot.is-orange { background: #f97316; }
.tdm-priority-dot.is-blue { background: #3b82f6; }
.tdm-priority-dot.is-green { background: #22c55e; }
.tdm-tags-trigger { cursor: pointer; padding: 2px 0; }
.tdm-tag.is-add {
  border: 1px dashed var(--gray-200, #cbd5e1);
  background: transparent;
  color: var(--gray-400, #94a3b8);
}
.tdm-tags-static { font-size: 12px; color: var(--gray-400, #94a3b8); }

/* ═══════ AI 协助人属性区 ═══════ */
.tdm-ai-prop { gap: 6px; }
.ai-sparkle { color: #7c3aed; }
.tdm-ai-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.tdm-ai-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: #6d28d9;
  background: #f5f3ff;
  border: 1px solid #ede9fe;
  border-radius: 9999px;
  padding: 2px 10px;
}
.tdm-ai-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  border-radius: 9999px;
  padding: 1px 9px;
}
.tdm-ai-pill.is-gray { background: var(--gray-10, #f1f5f9); color: var(--gray-500, #64748b); }
.tdm-ai-pill.is-blue { background: #dbeafe; color: #2563eb; }
.tdm-ai-pill.is-orange { background: #ffedd5; color: #ea580c; }
.tdm-ai-pill.is-green { background: #dcfce7; color: #16a34a; }
.tdm-ai-spin {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  border: 2px solid #93c5fd;
  border-top-color: #2563eb;
  animation: tdm-spin 0.8s linear infinite;
}
@keyframes tdm-spin { to { transform: rotate(360deg); } }
.tdm-ai-assign {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px dashed var(--gray-200, #cbd5e1);
  background: transparent;
  color: #7c3aed;
  font-size: 12px;
  border-radius: 8px;
  padding: 3px 10px;
  cursor: pointer;
}
.tdm-ai-assign:hover { border-color: #c4b5fd; background: #faf5ff; }
.tdm-ai-assign:focus-visible {
  outline: 2px solid #7c3aed;
  outline-offset: 1px;
}
.tdm-wake-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  width: 100%;
  border: none;
  border-radius: 8px;
  background: linear-gradient(120deg, #6d28d9 0%, #7c3aed 55%, #8b5cf6 100%);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  padding: 8px 0;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(124, 58, 237, 0.25);
  transition: opacity 0.15s, transform 0.15s;
}
.tdm-wake-btn:hover { opacity: 0.9; transform: translateY(-1px); }
.tdm-wake-btn:active { transform: translateY(0); }
.tdm-wake-btn:focus-visible {
  outline: 2px solid #6d28d9;
  outline-offset: 2px;
}

/* ═══════ AI 执行动态卡片（浅紫高亮，可折叠） ═══════ */
.tdm-ai-live {
  margin-bottom: 16px;
  border-radius: 12px;
  border: 1px solid #e0d4fc;
  background: linear-gradient(135deg, #faf7ff 0%, #f5f0ff 100%);
  overflow: hidden;
}
.tdm-ai-live-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  cursor: pointer;
  user-select: none;
}
.tdm-ai-live-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #6d28d9;
}
.tdm-ai-live-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #7c3aed;
  animation: tdm-pulse 1.2s ease-in-out infinite;
}
@keyframes tdm-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.45; transform: scale(0.8); }
}
.tdm-ai-live-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.tdm-ai-cancel {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: 1px solid #e0d4fc;
  background: #fff;
  color: #6d28d9;
  font-size: 11px;
  border-radius: 6px;
  padding: 2px 8px;
  cursor: pointer;
}
.tdm-ai-cancel:hover { background: #faf5ff; }
.tdm-ai-cancel:focus-visible {
  outline: 2px solid #7c3aed;
  outline-offset: 1px;
}
.tdm-ai-live-chevron { color: #a78bfa; transition: transform 0.15s; }
.tdm-ai-live-chevron.is-open { transform: rotate(180deg); }
.tdm-ai-live-body {
  padding: 2px 14px 12px;
  border-top: 1px dashed #e0d4fc;
}
.tdm-ai-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}
.tdm-ai-step-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #c4b5fd;
  flex-shrink: 0;
}
.tdm-ai-step-dot.done { background: #7c3aed; }
.tdm-ai-step-text { font-size: 12px; color: var(--gray-500, #64748b); }
.tdm-ai-step-text.done { color: var(--gray-700, #334155); }
.tdm-ai-step-spinner {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  border: 2px solid #c4b5fd;
  border-top-color: #7c3aed;
  animation: tdm-spin 0.8s linear infinite;
  margin-left: auto;
}
.tdm-ai-live-note { font-size: 12px; color: #7c3aed; padding: 6px 0 2px; }

/* ═══════ AI 产出成果卡片（含审核操作栏） ═══════ */
.tdm-ai-deliverable {
  margin-bottom: 18px;
  border-radius: 12px;
  border: 1px solid #d8caf7;
  background: linear-gradient(135deg, #fdfbff 0%, #f7f3ff 100%);
  overflow: hidden;
}
.tdm-ai-deliverable-head {
  padding: 12px 14px 0;
}
.tdm-ai-deliverable-body {
  padding: 10px 14px;
}
.tdm-ai-deliverable-actions {
  display: flex;
  gap: 8px;
  padding: 0 14px 12px;
  flex-wrap: wrap;
}
.tdm-ai-act {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  padding: 5px 12px;
  border-radius: 8px;
  border: 1px solid var(--gray-50, #e2e8f0);
  background: #fff;
  color: var(--gray-700, #334155);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.tdm-ai-act:hover { border-color: #c4b5fd; background: #faf5ff; color: #6d28d9; }
.tdm-ai-act:focus-visible {
  outline: 2px solid #7c3aed;
  outline-offset: 1px;
}
.tdm-ai-act.is-accept {
  background: var(--color-success-500, #22c55e);
  border-color: var(--color-success-500, #22c55e);
  color: #fff;
}
.tdm-ai-act.is-accept:hover { opacity: 0.88; color: #fff; background: var(--color-success-500, #22c55e); }
.tdm-ai-act.is-reject {
  background: var(--color-error-500, #ef4444);
  border-color: var(--color-error-500, #ef4444);
  color: #fff;
}
.tdm-ai-act.is-reject:hover { opacity: 0.88; color: #fff; background: var(--color-error-500, #ef4444); }
.tdm-ai-agent-result { margin-top: 4px; }
.tdm-modal-hint {
  font-size: 12px;
  color: var(--gray-500, #64748b);
  margin-bottom: 10px;
  line-height: 1.6;
}
</style>
