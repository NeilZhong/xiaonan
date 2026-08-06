<script setup>
/**
 * 数字警员 / 智能体档案页（悟帆 AI 员工页风格）
 *
 * 左侧：头像 + 名称/介绍/状态 + 对话按钮 的头部卡，下方为 5 个可点击区块
 *      （灵魂 / 技能 / 连接器 / 协助伙伴 / 记忆），点击跳转到对应子页。
 * 右侧：工作概览（历史数据 / 今日数据 / 趋势图 / 今日记录）。
 */
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { Sparkles, Wrench, Cable, Users, Brain, ChevronRight } from 'lucide-vue-next'
import * as echarts from 'echarts'

import { agentApi } from '@/apis/agent_api'
import { policeAgentApi, policeEquipApi } from '@/apis/police_api'
import AgentEditModal from '@/components/model-management/AgentEditModal.vue'
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

// ============ 左侧 5 个区块（跳转子页） ============
const sections = [
  { key: 'soul', title: '灵魂', subtitle: '系统提示词 · 智能体人格', icon: Sparkles },
  { key: 'skills', title: '技能', subtitle: '能力标签与工具', icon: Wrench },
  { key: 'connectors', title: '连接器与工具', subtitle: 'MCP 服务与平台内置工具', icon: Cable },
  { key: 'partners', title: '协助伙伴', subtitle: '协作的数字警员', icon: Users },
  { key: 'memory', title: '记忆', subtitle: '对当前用户的记忆', icon: Brain },
]

// 协助伙伴徽标数（来自数字警员装备区，已装备的协助伙伴数量）
const partnerCount = ref(0)
async function loadPartnerCount() {
  const id = agent.value?.id
  if (!id) return
  try {
    const res = await policeEquipApi.listEquipped(id)
    partnerCount.value = res?.total ?? res?.items?.length ?? 0
  } catch (_) {
    partnerCount.value = 0
  }
}

// 各区块的徽标数据（来自已加载的 agent / officer）
const sectionMeta = computed(() => {
  const caps = agent.value?.capabilities || agent.value?.skills || []
  const tools = agent.value?.tools || []
  // Agent 上无 mcp_dependencies 字段，真实连接器/工具配置在 config_json.context.mcps / .tools
  // 语意：数组为显式白名单；null 表示「默认全部启用」（此处无法获知平台总数，以「全部」标识）
  const ctx = agent.value?.config_json?.context || {}
  const mcpArr = Array.isArray(ctx.mcps) ? ctx.mcps : null
  const toolArr = Array.isArray(ctx.tools) ? ctx.tools : null
  // 协助伙伴徽标：真实已装备数来自数字警员装备区（officer.partners 字段不存在）
  return {
    soul: agent.value?.system_prompt ? '已配置' : '未配置',
    skills: caps.length + tools.length,
    connectors:
      mcpArr === null && toolArr === null ? '全部' : (mcpArr?.length || 0) + (toolArr?.length || 0),
    partners: partnerCount.value,
    memory: null,
  }
})

function goSection(key) {
  const id = agent.value?.slug || agent.value?.id
  if (!id) return
  router.push({ path: `/agent-manage/${encodeURIComponent(id)}/section/${key}` })
}

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
    await loadPartnerCount()
    nextTick(() => { renderChart() })
  } catch (e) { message.error('加载档案失败: ' + (e.message || e)) }
  finally { loading.value = false }
}

onMounted(() => {
  load()
  loadBackends()
})
onUnmounted(() => { destroyChart() })
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
        <!-- 头部卡：头像 + 名称/介绍/状态 + 对话 -->
        <div class="ap-profile">
          <div class="ap-profile-top">
            <div class="ap-profile-avatar">
              <img :src="avatarUrl" :alt="`${agent.name}头像`" />
            </div>
            <div class="ap-profile-head">
              <h1 class="ap-profile-name">{{ agent.name }}</h1>
              <span class="ap-hero-status" :class="`s-${statusColor}`">
                <span class="s-dot" /><span>{{ statusText }}</span>
              </span>
            </div>
          </div>
          <p class="ap-profile-desc">{{ agent.description || officer?.description || '暂无介绍' }}</p>
          <div class="ap-profile-meta">
            <div class="ap-meta-row"><span class="ap-meta-k">入职部门</span><span class="ap-meta-v">{{ officer?.department || '—' }}</span></div>
            <div class="ap-meta-row"><span class="ap-meta-k">入职时间</span><span class="ap-meta-v">{{ officer?.created_at?.substring(0, 10) || agent.created_at?.substring(0, 10) || '—' }}</span></div>
            <div class="ap-meta-row"><span class="ap-meta-k">共享范围</span><span class="ap-meta-v">{{ officer?.share_config?.access_level === 'global' ? '全局可见' : officer?.share_config?.access_level === 'department' ? '部门内可见' : officer?.share_config?.access_level === 'user' ? '仅自己' : '—' }}</span></div>
          </div>
          <button type="button" class="ap-profile-chat" @click="goChat">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            与 TA 对话
          </button>
        </div>

        <!-- 5 个区块卡（点击跳转子页） -->
        <button
          v-for="s in sections"
          :key="s.key"
          type="button"
          class="ap-section-card"
          @click="goSection(s.key)"
        >
          <span class="ap-section-icon"><component :is="s.icon" :size="18" /></span>
          <span class="ap-section-body">
            <span class="ap-section-title">{{ s.title }}</span>
            <span class="ap-section-sub">{{ s.subtitle }}</span>
          </span>
          <span class="ap-section-extra">
            <span v-if="s.key === 'soul'" class="ap-section-tag" :class="sectionMeta.soul === '已配置' ? 'on' : 'off'">{{ sectionMeta.soul }}</span>
            <span v-else-if="sectionMeta[s.key] != null" class="ap-section-count">{{ sectionMeta[s.key] }}</span>
          </span>
          <ChevronRight :size="16" class="ap-section-chevron" />
        </button>
      </div>

      <!-- ========== 右侧：工作概览 ============ -->
      <div class="ap-right">
        <div class="ap-stats-card">
          <!-- 历史数据 -->
          <div class="ap-stats-section ap-stats-history">
            <div class="ap-stats-section-title">历史数据</div>
            <div class="ap-stats-grid">
              <div v-for="c in statCards.history" :key="c.label" :class="['ap-stat-card', `ap-stat-${c.variant}`]">
                <div class="ap-stat-val">{{ c.value }}</div>
                <div class="ap-stat-lbl">{{ c.label }}</div>
              </div>
            </div>
          </div>

          <!-- 今日数据 -->
          <div class="ap-stats-section ap-stats-today">
            <div class="ap-stats-section-title">今日数据</div>
            <div class="ap-stats-grid">
              <div v-for="c in statCards.today" :key="c.label" :class="['ap-stat-card', `ap-stat-${c.variant}`]">
                <div class="ap-stat-val">{{ c.value }}</div>
                <div class="ap-stat-lbl">{{ c.label }}</div>
              </div>
            </div>
          </div>

          <!-- 图表区域 -->
          <div class="ap-chart-section">
            <div class="ap-stats-section-title">对话与任务趋势</div>
            <div v-if="dailyRuns.length" ref="chartRef" class="ap-chart" />
            <div v-else class="ap-chart-empty"><span>暂无数据</span></div>
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
                <span>今日暂无记录</span>
              </div>
            </div>
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
  grid-template-columns: minmax(0, 380px) 1fr;
  gap: 24px;
  align-items: start;
}
.ap-left {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

// ============ 头部卡 ============
.ap-profile {
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid var(--gray-150);
  box-shadow: 0 2px 10px rgba(16,30,54,.05);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.ap-profile-top {
  display: flex;
  align-items: center;
  gap: 16px;
}
.ap-profile-avatar {
  width: 96px;
  height: 96px;
  border-radius: 20px;
  overflow: hidden;
  background: transparent;
  box-shadow: none;
  flex-shrink: 0;
  img { display: block; width: 100%; height: 100%; object-fit: cover; }
}
.ap-profile-head {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  min-width: 0;
}
.ap-profile-name {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #1a365d;
  line-height: 1.2;
}
.ap-profile-desc {
  margin: 0;
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
}
.ap-profile-meta {
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--gray-100);
  padding-top: 12px;
}
.ap-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 0;
  font-size: 13px;
  border-bottom: 1px solid var(--gray-100);
  &:last-child { border-bottom: none; }
}
.ap-meta-k { color: var(--gray-500); flex-shrink: 0; }
.ap-meta-v { color: var(--gray-800); text-align: right; word-break: break-all; }
.ap-profile-chat {
  margin-top: 2px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 9px 0;
  border: none;
  border-radius: 12px;
  background: var(--main-700);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
  &:hover { background: var(--main-800); }
}

// ============ 状态胶囊 ============
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

// ============ 区块卡（跳转子页） ============
.ap-section-card {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  text-align: left;
  padding: 14px 16px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid var(--gray-150);
  box-shadow: 0 1px 4px rgba(16,30,54,.04);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, transform 0.12s;
  &:hover {
    background: #f8fafc;
    border-color: var(--main-300);
    transform: translateY(-1px);
  }
}
.ap-section-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #eef2ff;
  color: var(--main-700);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ap-section-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}
.ap-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1a365d;
}
.ap-section-sub {
  font-size: 11px;
  color: var(--gray-500);
}
.ap-section-extra {
  flex-shrink: 0;
}
.ap-section-count {
  font-size: 13px;
  font-weight: 700;
  color: var(--main-700);
  background: #eef2ff;
  border-radius: 999px;
  padding: 2px 10px;
  min-width: 28px;
  text-align: center;
}
.ap-section-tag {
  font-size: 11px;
  font-weight: 600;
  border-radius: 999px;
  padding: 2px 10px;
  &.on { background: #dcfce7; color: #15803d; }
  &.off { background: #f1f5f9; color: #94a3b8; }
}
.ap-section-chevron {
  color: var(--gray-400);
  flex-shrink: 0;
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
  align-items: center;
  justify-content: center;
  height: 160px;
  color: var(--gray-400);
  font-size: 13px;
  background: #ffffff;
  border-radius: 12px;
  border: 1px dashed var(--gray-300);
}

// ============ 今日记录 ============
.ap-today-section { padding-top: 4px; }
.ap-today-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 320px;
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
.ap-today-title { font-size: 13px; font-weight: 600; color: #1a202c; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 320px; }
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
  align-items: center;
  justify-content: center;
  padding: 24px 0;
  color: var(--gray-400);
  font-size: 13px;
  background: #ffffff;
  border-radius: 10px;
  border: 1px dashed var(--gray-300);
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
  .ap-profile-top { flex-direction: column; align-items: flex-start; }
  .ap-profile-avatar { width: 80px; height: 80px; border-radius: 18px; }
  .ap-profile-name { font-size: 18px; }
}
</style>
