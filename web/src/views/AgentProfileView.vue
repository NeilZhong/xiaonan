<script setup>
/**
 * 数字警员 / 智能体档案页 StaffDeck 风格
 *
 * 左侧：大头像 hero（头像高出背景色块） + 基本信息/身份统计合并栏 + 留言板块
 * 右侧：大卡片整合历史数据（淡蓝）+ 今日数据（深蓝）+ 融合图表（绿底）+ 今日记录
 */
import { ref, reactive, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { Send, MessageSquare } from 'lucide-vue-next'
import * as echarts from 'echarts'

import { agentApi } from '@/apis/agent_api'
import { policeAgentApi } from '@/apis/police_api'
import AgentEditModal from '@/components/model-management/AgentEditModal.vue'
import EquipPartnersPanel from '@/components/police/EquipPartnersPanel.vue'
import AgentRuntimeCenter from '@/components/police/AgentRuntimeCenter.vue'
import { isBuiltinAgent, useAgentStore } from '@/stores/agent'
import { resolveAgentAvatar } from '@/utils/policeAvatar'

const route = useRoute()
const router = useRouter()
const agentStore = useAgentStore()

const agent = ref(null)
const officer = ref(null)
const loading = ref(false)
const agentEditModalRef = ref(null)
const backendOptions = ref([])
const runtimeCenterOpen = ref(false)

const isOfficer = computed(() => !!officer.value)

const statusText = computed(() => {
  if (!agent.value) return '未知'
  if (isOfficer.value) {
    const s = officer.value?.status
    return { active: '在线', training: '训练中', offline: '离线' }[s] || '离线'
  }
  return '正常'
})
const statusColor = computed(() => {
  if (isOfficer.value) {
    const s = officer.value?.status
    return { active: 'green', training: 'orange', offline: 'red' }[s] || 'red'
  }
  return 'green'
})
const avatarUrl = computed(() => resolveAgentAvatar(agent.value))
const jobTitle = computed(() => officer.value?.rank || officer.value?.department || '通用智能体')

// ============ 身份统计：资料/技能/工具 ============
const identityStats = computed(() => {
  const skills = (officer.value?.skills || []).length
  const tools = (agent.value?.tools || agent.value?.tool_ids || []).length
  return [
    { label: '资料', value: officer.value?.doc_count ?? 0 },
    { label: '技能', value: skills },
    { label: '工具', value: tools }
  ]
})

// ============ 右侧统计卡（历史+今日） ============
const statCards = computed(() => {
  const s = officer.value?.work_stats || {}
  return {
    history: [
      { label: '累计对话', value: s.total_conversations ?? 0, variant: 'default' },
      { label: '完成任务', value: s.total_tasks ?? 0, variant: 'default' },
      { label: '好评率', value: s.feedback_positive != null ? `${s.feedback_positive}%` : '—', variant: 'good' },
      { label: '差评数', value: s.feedback_negative ?? 0, variant: 'bad' }
    ],
    today: [
      { label: '今日对话', value: s.daily_conversations ?? 0, variant: 'default' },
      { label: '今日任务', value: s.daily_tasks ?? 0, variant: 'default' },
      { label: '今日好评', value: s.daily_positive ?? 0, variant: 'good-text' },
      { label: '今日差评', value: s.daily_negative ?? 0, variant: 'bad-text' }
    ]
  }
})

// ============ 趋势图表（融合对话+任务） ============
const chartRef = ref(null)
let chartInst = null

const dailyRuns = computed(() => {
  // 优先使用后端真实聚合的 14 天趋势（对话/任务分日统计）
  const trend = officer.value?.daily_trend
  if (Array.isArray(trend) && trend.length) {
    return trend.map((t) => ({
      date: t.date,
      conversations: t.conversations ?? 0,
      tasks: t.tasks ?? 0,
    }))
  }
  // 兜底：由最近运行记录推断（旧数据兼容）
  const runs = officer.value?.recent_runs || []
  const map = new Map()
  for (const r of runs) {
    const d = r.started_at?.substring(0, 10) || '—'
    if (!map.has(d)) map.set(d, { date: d, conversations: 0, tasks: 0 })
    const e = map.get(d)
    if (r.type === 'task') e.tasks += 1
    else e.conversations += 1
  }
  return Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date))
})

function renderChart() {
  if (!chartRef.value) return
  if (!chartInst) chartInst = echarts.init(chartRef.value)
  const data = dailyRuns.value
  chartInst.setOption(data.length
    ? {
        grid: { left: 40, right: 20, top: 30, bottom: 30, containLabel: false },
        tooltip: { trigger: 'axis' },
        legend: { data: ['对话', '任务'], top: 4, right: 12, textStyle: { fontSize: 11 } },
        xAxis: {
          type: 'category',
          data: data.map((d) => d.date.slice(5)),
          axisLine: { lineStyle: { color: '#E2E8F0' } },
          axisTick: { show: false },
          axisLabel: { color: '#718096', fontSize: 11 }
        },
        yAxis: {
          type: 'value',
          splitLine: { lineStyle: { type: 'dashed', color: '#E8F5E9' } },
          axisLabel: { color: '#94A3B8', fontSize: 11 }
        },
        series: [
          {
            name: '对话',
            type: 'line',
            data: data.map((d) => d.conversations),
            smooth: true,
            symbol: 'circle',
            symbolSize: 6,
            lineStyle: { color: '#22C55E', width: 2.5 },
            itemStyle: { color: '#22C55E' },
            areaStyle: { color: 'rgba(34,197,94,0.12)' }
          },
          {
            name: '任务',
            type: 'line',
            data: data.map((d) => d.tasks),
            smooth: true,
            symbol: 'circle',
            symbolSize: 6,
            lineStyle: { color: '#3B82F6', width: 2.5 },
            itemStyle: { color: '#3B82F6' },
            areaStyle: { color: 'rgba(59,130,246,0.12)' }
          }
        ]
      }
    : {
        grid: { left: 40, right: 20, top: 30, bottom: 30 },
        xAxis: { type: 'category', show: false },
        yAxis: { type: 'value', show: false },
        series: [
          { type: 'line', data: [], show: false, name: '对话' },
          { type: 'line', data: [], show: false, name: '任务' }
        ]
      }
  )
}

function destroyChart() {
  chartInst?.dispose()
  chartInst = null
}

// ============ 今日记录 ============
const todayRuns = computed(() => {
  const runs = officer.value?.recent_runs || []
  const today = new Date().toISOString().substring(0, 10)
  return runs.filter((r) => (r.started_at || '').startsWith(today))
})

// 运行记录徽标语义：任务运行状态（完成/失败/进行中），而非好评/差评
function runStatusBadge(r) {
  if (r.status === 'completed') return { text: '已完成', cls: 'good' }
  if (r.status === 'failed' || r.status === 'cancelled') return { text: '失败', cls: 'bad' }
  return { text: '进行中', cls: '' }
}

// ============ 留言板 ============
const commentText = ref('')
const comments = reactive([])
const loadingComments = ref(false)
const showEmojiPicker = ref(false)
const emojiPickerRef = ref(null)

// 常用表情列表
const EMOJIS = ['😀', '😃', '😊', '😍', '🤔', '👍', '👎', '🎉', '🔥', '❤️', '🙏', '😂', '🤝', '💪', '✨', '✅', '❌', '⚠️', '💡', '📌']

function toggleEmojiPicker(e) {
  e.stopPropagation()
  showEmojiPicker.value = !showEmojiPicker.value
}

function insertEmoji(emoji) {
  commentText.value += emoji
  showEmojiPicker.value = false
}

async function loadComments() {
  const agentId = isOfficer.value ? officer.value.id : agent.value?.id
  if (!agentId) return
  loadingComments.value = true
  try {
    const res = await policeAgentApi.listComments(agentId)
    comments.length = 0
    comments.push(...(res.items || []))
  } catch (e) {
    console.warn('加载留言失败', e)
  } finally {
    loadingComments.value = false
  }
}

async function addComment() {
  const text = commentText.value.trim()
  if (!text) return
  const agentId = isOfficer.value ? officer.value.id : agent.value?.id
  if (!agentId) return
  try {
    await policeAgentApi.createComment(agentId, text)
    commentText.value = ''
    await loadComments()
    message.success('留言已发送')
  } catch (e) {
    message.error('发送失败: ' + (e.message || e))
  }
}

function deleteComment(commentId, e) {
  e.stopPropagation()
  Modal.confirm({
    title: '删除留言',
    content: '确认删除这条留言？',
    okText: '删除', okType: 'danger', cancelText: '取消',
    async onOk() {
      const agentId = isOfficer.value ? officer.value.id : agent.value?.id
      if (!agentId) return
      try {
        await policeAgentApi.deleteComment(agentId, commentId)
        const idx = comments.findIndex(c => c.id === commentId)
        if (idx !== -1) comments.splice(idx, 1)
        message.success('已删除')
      } catch (e) {
        message.error('删除失败: ' + (e.message || e))
      }
    }
  })
}

// 点击外部关闭表情选择器
function handleClickOutside(e) {
  if (showEmojiPicker.value && emojiPickerRef.value && !emojiPickerRef.value.contains(e.target)) {
    showEmojiPicker.value = false
  }
}

// 辅助函数：格式化评论文本
function formatCommentText(text) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

// 判断是否可以删除评论
function canDeleteComment(_comment) {
  return true
}

// ============ 导航 & 操作 ============
function goBack() { router.push({ path: '/agent-manage' }) }
function goChat() {
  const slug = agent.value?.slug || agent.value?.id
  if (slug) router.push({ path: '/agent', query: { agent_id: slug } })
  else router.push('/agent')
}
function openEdit() { agentEditModalRef.value?.openEdit(agent.value?.slug || agent.value?.id) }
async function onEdited() { await load() }
async function handleDelete() {
  const name = agent.value?.name || '该智能体'
  Modal.confirm({
    title: `删除 ${name}`,
    content: isOfficer.value ? '删除后该数字警员及其关联的对话智能体也将一并移除，不可恢复。' : '删除后不可恢复。',
    okText: '删除', okType: 'danger', cancelText: '取消',
    async onOk() {
      try {
        if (isOfficer.value) await policeAgentApi.delete(officer.value.id)
        else await agentApi.deleteAgent(agent.value.id)
        message.success('已删除')
        router.push({ path: '/agent-manage' })
      } catch (e) { message.error('删除失败: ' + (e.message || e)) }
    }
  })
}
// ============ 数据加载 ============
async function loadBackends() {
  try {
    const res = await agentApi.getAgentBackends()
    backendOptions.value = (res.backends || []).map((b) => ({ label: b.name || b.backend_id, value: b.backend_id }))
  } catch (_) {}
}
async function load() {
  loading.value = true
  try {
    const id = route.params.id
    const isBadge = /^DA-[\w-]+$/.test(id || '')
    const policeData = isBadge ? await policeAgentApi.getByBadgeNumber(id).catch(() => null) : null
    if (policeData?.id) {
      // 单表化：police 记录即 agents 行，officer 与 agent 同源。
      // 直接以 policeData 作为 agent，避免再用 slug 调 yuxi 详情导致 404。
      officer.value = policeData
      agent.value = policeData
    } else {
      const agentResp = await agentApi.getAgentDetail(id)
      const agentObj = agentResp?.agent || agentResp
      agent.value = agentObj
      const yuxiId = agentObj?.id
      if (yuxiId != null) {
        const pd = await policeAgentApi.getByYuxiId(yuxiId).catch(() => null)
        if (pd && (pd.id || pd.agent_id)) officer.value = pd
      }
    }
    nextTick(() => { renderChart() })
    await loadComments()
  } catch (e) { message.error('加载档案失败: ' + (e.message || e)) }
  finally { loading.value = false }
}

onMounted(() => {
  load()
  loadBackends()
  document.addEventListener('click', handleClickOutside)
})
onUnmounted(() => { destroyChart(); document.removeEventListener('click', handleClickOutside) })
</script>

<template>
  <div v-if="agent" class="ap-container">
    <!-- ===== 顶部操作栏 ===== -->
    <div class="ap-bar">
      <a-button type="text" class="ap-back-btn" @click="goBack">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M8.5 11.5L3.5 7l5-4.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        返回列表
      </a-button>
      <div class="ap-bar-actions">
        <a-button v-if="isOfficer" @click="runtimeCenterOpen = true">运行中心</a-button>
        <a-button v-if="agent.can_manage || isBuiltinAgent(agent) || isOfficer" @click="openEdit">编辑</a-button>
        <a-popconfirm v-if="!isBuiltinAgent(agent)" title="确认删除？"
          :description="isOfficer ? '关联的对话智能体也将一并移除' : '删除后不可恢复'"
          ok-text="删除" cancel-text="取消" :ok-button-props="{ danger: true }" @confirm="handleDelete">
          <a-button danger>删除</a-button>
        </a-popconfirm>
      </div>
    </div>

    <!-- ===== 主内容区 ===== -->
    <div class="ap-main">
      <!-- ========== 左侧 ========== -->
      <div class="ap-left">
        <!-- Hero：头像 + 名称/职位/状态 + 对话按钮 -->
        <div class="ap-hero">
          <!-- 背景色块：圆角带阴影，内含名称/职务/状态与对话按钮 -->
          <div class="ap-hero-bg">
            <div class="ap-hero-text">
              <h1 class="ap-hero-name">{{ agent.name }}</h1>
              <p class="ap-hero-job">{{ jobTitle }}</p>
              <span class="ap-hero-status" :class="`s-${statusColor}`">
                <span class="s-dot" /><span>{{ statusText }}</span>
              </span>
            </div>
            <!-- 对话按钮：背景色块内，上下居中 -->
            <button type="button" class="ap-chat-btn" @click="goChat" :title="`与 ${agent.name} 对话`">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            </button>
          </div>
          <!-- 头像：浮在背景色块上方，与 ap-hero 上/左/下保留间距 -->
          <div class="ap-hero-avatar">
            <img :src="avatarUrl" :alt="`${agent.name}头像`" />
          </div>
        </div>

        <!-- 身份统计 + 基本信息合并栏 -->
        <div class="ap-card ap-info-card">
          <div class="ap-identity-row">
            <div v-for="s in identityStats" :key="s.label" class="ap-identity-item">
              <span class="ap-identity-val">{{ s.value }}</span>
              <span class="ap-identity-lbl">{{ s.label }}</span>
            </div>
          </div>
          <div class="ap-info-divider"></div>
          <div class="ap-info-rows">
            <div class="ap-info-row"><span class="ap-info-k">基本介绍</span><span class="ap-info-v">{{ officer?.description || agent.description || '暂无介绍' }}</span></div>
            <div class="ap-info-row"><span class="ap-info-k">警号</span><span class="ap-info-v">{{ officer?.is_global_approved ? (officer?.badge_number || '—') : '—' }}</span></div>
            <div class="ap-info-row"><span class="ap-info-k">入职部门</span><span class="ap-info-v">{{ officer?.department || '—' }}</span></div>
            <div class="ap-info-row"><span class="ap-info-k">入职时间</span><span class="ap-info-v">{{ officer?.created_at?.substring(0, 10) || agent.created_at?.substring(0, 10) || '—' }}</span></div>
            <div class="ap-info-row"><span class="ap-info-k">共享范围</span><span class="ap-info-v">{{ officer?.share_config?.access_level === 'global' ? '全局可见' : officer?.share_config?.access_level === 'department' ? '部门内可见' : officer?.share_config?.access_level === 'user' ? '仅自己' : '—' }}</span></div>
          </div>
        </div>

        <!-- 留言板 -->
        <div class="ap-card ap-comment-card">
          <div class="ap-card-title-row">
            <h3 class="ap-card-title"><MessageSquare :size="14"/> 留言板</h3>
            <span class="ap-comment-count">{{ comments.length }} 条留言</span>
          </div>
          <div class="ap-comment-input-area" ref="emojiPickerRef">
            <div class="ap-comment-input">
              <input
                v-model="commentText"
                type="text"
                :max-length="200"
                placeholder="添加评论…"
                class="ap-comment-textarea"
                @keydown.enter.prevent="addComment"
              />
              <div class="ap-comment-actions">
                <button type="button" class="ap-emoji-btn" @click="toggleEmojiPicker" title="表情">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>
                </button>
                <button
                  type="button"
                  class="ap-comment-send-btn"
                  :disabled="!commentText.trim()"
                  @click="addComment"
                  title="发送"
                >
                  <Send :size="16" />
                </button>
              </div>
            </div>
            <!-- 表情选择器 -->
            <div v-if="showEmojiPicker" class="ap-emoji-picker">
              <button v-for="e in EMOJIS" :key="e" type="button" class="ap-emoji-item" @click="insertEmoji(e)">{{ e }}</button>
            </div>
          </div>
          <div class="ap-comment-list">
            <div v-if="loadingComments" class="ap-comment-loading">
              <a-spin size="small" />
            </div>
            <div v-else v-for="c in comments" :key="c.id" class="ap-comment-item">
              <div class="ap-comment-avatar">
                <img v-if="c.user_avatar" :src="c.user_avatar" class="ap-comment-user-img" />
                <span v-else>U</span>
              </div>
              <div class="ap-comment-body">
                <div class="ap-comment-text" v-html="formatCommentText(c.content)"></div>
                <div class="ap-comment-meta">
                  <span>{{ c.created_at?.substring(0, 16).replace('T', ' ') }}</span>
                  <button v-if="canDeleteComment(c)" type="button" class="ap-comment-del" @click="deleteComment(c.id, $event)">删除</button>
                </div>
              </div>
            </div>
            <div v-if="!loadingComments && !comments.length" class="ap-comment-empty">
              <MessageSquare :size="24" />
              <span>还没有留言，来做第一个留言的人吧</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ========== 右侧：大卡片整合 ============ -->
      <div class="ap-right">
        <div class="ap-stats-card">
          <!-- 历史数据（淡蓝色） -->
          <div class="ap-stats-section ap-stats-history">
            <div class="ap-stats-section-title">历史数据</div>
            <div class="ap-stats-grid">
              <div v-for="c in statCards.history" :key="c.label" :class="['ap-stat-card', `ap-stat-${c.variant}`]">
                <div class="ap-stat-val">{{ c.value }}</div>
                <div class="ap-stat-lbl">{{ c.label }}</div>
              </div>
            </div>
          </div>

          <!-- 今日数据（深蓝色） -->
          <div class="ap-stats-section ap-stats-today">
            <div class="ap-stats-section-title">今日数据</div>
            <div class="ap-stats-grid">
              <div v-for="c in statCards.today" :key="c.label" :class="['ap-stat-card', `ap-stat-${c.variant}`]">
                <div class="ap-stat-val">{{ c.value }}</div>
                <div class="ap-stat-lbl">{{ c.label }}</div>
              </div>
            </div>
          </div>

          <!-- 图表区域（绿色底） -->
          <div class="ap-chart-section">
            <div class="ap-stats-section-title">对话与任务趋势</div>
            <div v-if="dailyRuns.length" ref="chartRef" class="ap-chart" />
            <div v-else class="ap-chart-empty"><MessageSquare :size="24" /><span>暂无数据</span></div>
          </div>

          <!-- 今日记录 -->
          <div class="ap-today-section">
            <div class="ap-stats-section-title">今日记录</div>
            <div class="ap-today-list">
              <div v-for="r in todayRuns" :key="r.id" class="ap-today-item">
                <div class="ap-today-main">
                  <span class="ap-today-title">{{ r.title || r.task_name || `运行 #${r.id}` }}</span>
                  <span class="ap-today-badge" :class="runStatusBadge(r).cls">
                    {{ runStatusBadge(r).text }}
                  </span>
                </div>
                <span class="ap-today-time">{{ r.started_at || '—' }}</span>
              </div>
              <div v-if="!todayRuns.length" class="ap-today-empty">
                <MessageSquare :size="24" /><span>今日暂无记录</span>
              </div>
            </div>
          </div>

          <!-- 装备伙伴（协助伙伴挂载区） -->
          <div v-if="isOfficer" class="ap-partner-section">
            <div class="ap-stats-section-title">装备伙伴</div>
            <EquipPartnersPanel v-if="officer" :agent="officer" />
          </div>
        </div>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <AgentEditModal ref="agentEditModalRef" :backend-options="backendOptions" @saved="onEdited" />

    <!-- 运行中心抽屉 -->
    <AgentRuntimeCenter v-model:open="runtimeCenterOpen" :agent="officer || agent" />
  </div>

  <div v-else class="ap-loading"><a-spin tip="加载智能体档案中…" /></div>
</template>

<style lang="less" scoped>
// ============ 整体布局 ============
.ap-container {
  padding: 24px var(--page-padding) 48px;
  max-width: 1360px;
  margin: 0 auto;
}

.ap-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.ap-back-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--gray-600);
  font-size: 13px;
  padding: 0;
  &:hover { color: var(--main-700); }
}
.ap-bar-actions { display: flex; gap: 8px; }

.ap-main {
  display: grid;
  grid-template-columns: minmax(0, 520px) 1fr;
  gap: 24px;
  align-items: start;
}
.ap-left {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

// ============ 卡片通用 ============
.ap-card {
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid var(--gray-150);
  box-shadow: 0 2px 10px rgba(16,30,54,.05);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.ap-card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.ap-card-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1a365d;
  display: flex;
  align-items: center;
  gap: 6px;
}

// ============ Hero 区域 ============
.ap-hero {
  position: relative;
  border-radius: 20px;
  overflow: visible;
  min-height: 220px;
  padding: 0;
}
.ap-hero-bg {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 80%;
  margin: 0;
  padding: 18px 24px 18px 224px;
  display: flex;
  align-items: center;
  gap: 12px;
  background: linear-gradient(160deg, #eef4fd 0%, #f7f8fa 50%, #eef0f4 100%);
  border-radius: 20px;
  box-shadow: 0 4px 16px rgba(16,30,54,.08);
}
.ap-hero-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}
.ap-hero-avatar {
  position: absolute;
  top: 18px;
  left: 18px;
  z-index: 2;
  width: 184px;
  height: 184px;
  border-radius: 24px;
  overflow: hidden;
  background: transparent; // 透明底色，与档案背景块自然衔接
  border: 1px solid var(--gray-150);
  box-shadow: none;
  img { display: block; width: 100%; height: 100%; object-fit: cover; }
}
.ap-hero-name {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #1a365d;
  line-height: 1.2;
}
.ap-hero-job {
  margin: 0;
  font-size: 13px;
  color: #475569;
}
.ap-hero-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 60px;
  box-sizing: border-box;
  white-space: nowrap;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 999px;
  border: 1px solid transparent;
  &.s-green { background: #f0fdf4; color: #15803d; border-color: #bbf7d0; }
  &.s-red { background: #fef2f2; color: #b91c1c; border-color: #fecaca; }
  &.s-orange { background: #fff7ed; color: #c2410c; border-color: #fed7aa; }
}
.s-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: currentColor;
}
.ap-chat-btn {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  border: 1px solid var(--gray-200);
  background: #ffffff;
  color: var(--gray-600);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  z-index: 3;
  &:hover {
    background: var(--main-700);
    color: #ffffff;
    border-color: var(--main-700);
    transform: scale(1.05);
  }
}

// ============ 身份统计 + 基本信息合并栏 ============
.ap-info-card {
  gap: 14px;
}
.ap-identity-row {
  display: flex;
  gap: 1px;
  background: var(--gray-150);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--gray-150);
}
.ap-identity-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 8px;
  background: #ffffff;
  & + & { border-left: 1px solid var(--gray-150); }
}
.ap-identity-val {
  font-size: 22px;
  font-weight: 700;
  color: #1a365d;
  line-height: 1;
}
.ap-identity-lbl {
  font-size: 12px;
  color: var(--gray-500);
  margin-top: 4px;
}
.ap-info-divider {
  height: 1px;
  background: var(--gray-150);
  margin: 2px 0;
}
.ap-info-rows { display: flex; flex-direction: column; gap: 0; }
.ap-info-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--gray-100);
  gap: 12px;
  &:last-child { border-bottom: none; }
}
.ap-info-k { font-size: 12px; color: var(--gray-500); flex-shrink: 0; width: 72px; }
.ap-info-v { font-size: 13px; color: var(--gray-800); text-align: right; word-break: break-all; flex: 1; }

// ============ 留言板 ============
.ap-comment-card { min-height: 320px; }
.ap-comment-input-area { position: relative; }
.ap-comment-input {
  position: relative;
  border: 2px solid var(--gray-200);
  border-radius: 12px;
  background: #ffffff;
  padding: 10px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: border-color 0.2s, box-shadow 0.2s;
  &:focus-within {
    border-color: #0EA5E9;
    box-shadow: 0 0 0 3px rgba(14,165,233,0.1);
  }
}
.ap-comment-textarea {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-size: 14px;
  color: #1a1a1a;
  resize: none;
  :deep(.ant-input) {
    border: none;
    background: transparent;
    box-shadow: none;
    font-size: 14px;
    color: #1a1a1a;
  }
  :deep(.ant-input[placeholder]) {
    color: #94a3b8;
  }
}
.ap-comment-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.ap-emoji-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: background 0.15s;
  &:hover { background: rgba(0,0,0,0.05); }
}
.ap-comment-send-btn {
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--gray-500);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  &:hover {
    background: rgba(0,0,0,0.05);
    color: var(--main-700);
  }
  &:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }
}
.ap-comment-count { font-size: 12px; color: var(--gray-400); }
.ap-emoji-picker {
  position: absolute;
  bottom: 100%;
  left: 0;
  background: #ffffff;
  border: 1px solid var(--gray-200);
  border-radius: 12px;
  padding: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  box-shadow: 0 4px 12px rgba(0,0,0,.1);
  z-index: 10;
  margin-bottom: 8px;
  max-width: 280px;
}
.ap-emoji-item {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  font-size: 18px;
  cursor: pointer;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
  &:hover { background: var(--gray-100); }
}
.ap-comment-list {
  max-height: 260px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-right: 2px;
  scrollbar-width: thin;
  scrollbar-color: var(--gray-200) transparent;
}
.ap-comment-loading {
  display: flex;
  justify-content: center;
  padding: 20px 0;
}
.ap-comment-item {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  background: #f8fafc;
  border-radius: 12px;
  transition: background 0.15s;
  &:hover { background: #f1f5f9; }
}
.ap-comment-avatar {
  width: 32px; height: 32px;
  border-radius: 50%;
  background: var(--main-100);
  color: var(--main-700);
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}
.ap-comment-user-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.ap-comment-body { flex: 1; min-width: 0; }
.ap-comment-text { font-size: 13px; color: var(--gray-800); line-height: 1.55; word-break: break-word; white-space: pre-wrap; }
.ap-comment-meta {
  font-size: 11px;
  color: var(--gray-400);
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.ap-comment-del {
  font-size: 11px;
  color: var(--gray-400);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  &:hover { color: #ef4444; }
}
.ap-comment-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px 0;
  color: var(--gray-400);
  font-size: 13px;
  svg { color: var(--gray-200); }
}

// ============ 右侧大卡片 ============
.ap-stats-card {
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid var(--gray-150);
  box-shadow: 0 2px 10px rgba(16,30,54,.05);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.ap-stats-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ap-stats-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #1a365d;
  padding-bottom: 8px;
  margin-bottom: 10px;
  border-bottom: 2px solid var(--gray-200);
}
.ap-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.ap-stat-card {
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid var(--gray-200);
  padding: 14px 10px;
  text-align: center;
  transition: transform 0.15s, box-shadow 0.15s;
  &:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,.08); }
}
.ap-stat-default {
  .ap-stat-val { color: #1a1a1a; }
  .ap-stat-lbl { color: var(--gray-600); }
}
.ap-stat-good {
  background: #dcfce7;
  border-color: #86efac;
  .ap-stat-val { color: #16a34a; }
  .ap-stat-lbl { color: #15803d; }
}
.ap-stat-bad {
  background: #fee2e2;
  border-color: #fca5a5;
  .ap-stat-val { color: #dc2626; }
  .ap-stat-lbl { color: #b91c1c; }
}
.ap-stat-good-text {
  .ap-stat-val { color: #16a34a; }
  .ap-stat-lbl { color: #15803d; }
}
.ap-stat-bad-text {
  .ap-stat-val { color: #dc2626; }
  .ap-stat-lbl { color: #b91c1c; }
}
.ap-stat-val { font-size: 22px; font-weight: 700; color: #1a1a1a; line-height: 1.1; }
.ap-stat-lbl { font-size: 11px; color: var(--gray-600); margin-top: 4px; }

// ============ 图表 ============
.ap-chart-section { padding-top: 4px; }
.ap-chart {
  width: 100%;
  height: 200px;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid var(--gray-200);
}
.ap-chart-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 160px;
  color: var(--gray-400);
  font-size: 13px;
  background: #ffffff;
  border-radius: 12px;
  border: 1px dashed var(--gray-300);
  svg { color: var(--gray-300); }
}

// ============ 今日记录 ============
.ap-today-section { padding-top: 4px; }

// ============ 装备伙伴 ============
.ap-partner-section {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--gray-150);
  .ap-stats-section-title {
    margin-bottom: 12px;
  }
}
.ap-today-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 240px;
  overflow-y: auto;
}
.ap-today-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid var(--gray-200);
  border-radius: 10px;
  &:hover { background: var(--gray-50); }
}
.ap-today-main { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1; }
.ap-today-title { font-size: 13px; font-weight: 600; color: #1a202c; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px; }
.ap-today-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--gray-100);
  color: var(--gray-600);
  flex-shrink: 0;
  &.good { background: #dcfce7; color: #15803d; }
  &.bad { background: #fee2e2; color: #b91c1c; }
}
.ap-today-time { font-size: 11px; color: var(--gray-400); flex-shrink: 0; }
.ap-today-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px 0;
  color: var(--gray-400);
  font-size: 13px;
  background: #ffffff;
  border-radius: 10px;
  border: 1px dashed var(--gray-300);
  svg { color: var(--gray-300); }
}

// ============ 加载 ============
.ap-loading { display: flex; justify-content: center; padding: 120px 0; }

// ============ 响应式 ============
@media (max-width: 1100px) {
  .ap-main { grid-template-columns: 1fr; }
  .ap-stats-grid { grid-template-columns: repeat(4, 1fr); }
}
@media (max-width: 640px) {
  .ap-stats-grid { grid-template-columns: repeat(2, 1fr); }
  .ap-hero { min-height: 208px; padding: 0; }
  .ap-hero-bg { position: absolute; left: 0; right: 0; bottom: 0; height: 80%; margin: 0; padding: 14px 16px 14px 142px; }
  .ap-hero-avatar { width: 116px; height: 116px; border-radius: 18px; left: 14px; top: 14px; }
  .ap-hero-name { font-size: 18px; }
}
</style>
