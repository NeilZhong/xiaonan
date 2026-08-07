<script setup>
/**
 * ★ 案件内「统计」Tab
 * 消费 GET /api/police/cases/:id/stats
 * 展示：概览指标卡 / 状态分布 / 人机（民警·数字民警）占比 / 燃尽图 / 风险清单
 * 图表参考 Plane 的模块化解法，但渲染用项目既有 ECharts 体系（非 Tailwind）。
 */
import { ref, onMounted, onBeforeUnmount, watch, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { policeCaseApi } from '@/apis/police_api'
import { useThemeStore } from '@/stores/theme'

const props = defineProps({
  caseId: { type: [Number, String], required: true },
})

const themeStore = useThemeStore()
const loading = ref(false)
const stats = ref(null)

// ── 概览指标卡定义 ──
const overviewCards = computed(() => {
  const o = stats.value?.overview || {}
  return [
    { key: 'total', label: '任务总数', value: o.total || 0, color: 'var(--main-color, #24839b)' },
    { key: 'completed', label: '已完成', value: o.completed || 0, color: '#38A169' },
    { key: 'in_progress', label: '进行中', value: o.in_progress || 0, color: '#3182CE' },
    { key: 'pending', label: '待处理', value: o.pending || 0, color: '#718096' },
    { key: 'review', label: '待审核', value: o.review || 0, color: '#D69E2E' },
    { key: 'overdue', label: '已逾期', value: o.overdue || 0, color: '#E53E3E' },
    { key: 'unclaimed', label: '待认领', value: o.unclaimed || 0, color: '#9F7AEA' },
    { key: 'time_undetermined', label: '时限待定', value: o.time_undetermined || 0, color: '#4A5568' },
  ]
})

const riskLevelColor = { high: 'red', medium: 'orange', low: 'blue' }
const riskTypeText = {
  legal_time_limit: '法定/计划时限',
  due_soon: '即将到期',
  procedure_compliance: '程序合规',
}

// ── 图表实例 ──
const statusChartRef = ref(null)
const workerChartRef = ref(null)
const burndownChartRef = ref(null)
let statusChart = null
let workerChart = null
let burndownChart = null

function chartTextColor() {
  return themeStore.isDark ? '#cbd5e0' : '#2d3748'
}

async function loadStats() {
  if (!props.caseId) return
  loading.value = true
  try {
    const res = await policeCaseApi.getStats(props.caseId)
    stats.value = res.data || null
  } catch (e) {
    stats.value = null
  } finally {
    loading.value = false
    nextTick(() => renderCharts())
  }
}

function renderCharts() {
  if (!stats.value) return
  renderStatusChart()
  renderWorkerChart()
  renderBurndownChart()
}

function renderStatusChart() {
  if (!statusChartRef.value) return
  if (statusChart) { statusChart.dispose(); statusChart = null }
  statusChart = echarts.init(statusChartRef.value)
  const o = stats.value.overview || {}
  const items = [
    { name: '已完成', value: o.completed || 0, color: '#38A169' },
    { name: '进行中', value: o.in_progress || 0, color: '#3182CE' },
    { name: '待处理', value: o.pending || 0, color: '#718096' },
    { name: '待审核', value: o.review || 0, color: '#D69E2E' },
    { name: '已逾期', value: o.overdue || 0, color: '#E53E3E' },
    { name: '待认领', value: o.unclaimed || 0, color: '#9F7AEA' },
  ]
  statusChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: 8, right: 16, top: 16, bottom: 8, containLabel: true },
    xAxis: { type: 'category', data: items.map(i => i.name), axisLabel: { color: chartTextColor() } },
    yAxis: { type: 'value', axisLabel: { color: chartTextColor() }, splitLine: { lineStyle: { color: themeStore.isDark ? '#2d3748' : '#edf2f7' } } },
    series: [{
      type: 'bar',
      data: items.map(i => ({ value: i.value, itemStyle: { color: i.color, borderRadius: [4, 4, 0, 0] } })),
      barWidth: '52%',
    }],
  })
}

function renderWorkerChart() {
  if (!workerChartRef.value) return
  if (workerChart) { workerChart.dispose(); workerChart = null }
  workerChart = echarts.init(workerChartRef.value)
  const w = stats.value.worker_distribution || {}
  const data = [
    { name: '办案民警', value: w.human || 0 },
    { name: '数字民警', value: w.agent || 0 },
  ]
  workerChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0, textStyle: { color: chartTextColor() } },
    series: [{
      type: 'pie',
      radius: ['45%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      label: { color: chartTextColor() },
      data: data.map((d, idx) => ({
        ...d,
        itemStyle: { color: idx === 0 ? '#3182CE' : '#9F7AEA' },
      })),
    }],
  })
}

function renderBurndownChart() {
  if (!burndownChartRef.value) return
  if (burndownChart) { burndownChart.dispose(); burndownChart = null }
  burndownChart = echarts.init(burndownChartRef.value)
  const list = stats.value.burndown || []
  burndownChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['已完成累计', '剩余'], bottom: 0, textStyle: { color: chartTextColor() } },
    grid: { left: 8, right: 16, top: 16, bottom: 32, containLabel: true },
    xAxis: { type: 'category', data: list.map(d => d.date), axisLabel: { color: chartTextColor(), hideOverlap: true } },
    yAxis: { type: 'value', axisLabel: { color: chartTextColor() }, splitLine: { lineStyle: { color: themeStore.isDark ? '#2d3748' : '#edf2f7' } } },
    series: [
      { name: '已完成累计', type: 'line', smooth: true, data: list.map(d => d.completed), itemStyle: { color: '#38A169' }, areaStyle: { opacity: 0.12 } },
      { name: '剩余', type: 'line', smooth: true, data: list.map(d => d.remaining), itemStyle: { color: '#E53E3E' } },
    ],
  })
}

function handleResize() {
  statusChart?.resize()
  workerChart?.resize()
  burndownChart?.resize()
}

onMounted(() => { loadStats(); window.addEventListener('resize', handleResize) })

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  statusChart?.dispose(); workerChart?.dispose(); burndownChart?.dispose()
})

// 切换案件 / 主题变化时重渲染
watch(() => props.caseId, () => loadStats())
watch(() => themeStore.isDark, () => nextTick(renderCharts))
</script>

<template>
  <div class="case-stats-tab">
    <a-spin :spinning="loading">
      <template v-if="stats">
        <!-- 概览指标卡 -->
        <div class="overview-cards">
          <div v-for="c in overviewCards" :key="c.key" class="ov-card">
            <div class="ov-value" :style="{ color: c.color }">{{ c.value }}</div>
            <div class="ov-label">{{ c.label }}</div>
          </div>
        </div>

        <!-- 图表区 -->
        <a-row :gutter="16" class="chart-row">
          <a-col :xs="24" :lg="14">
            <a-card title="任务状态分布" size="small" class="chart-card">
              <div ref="statusChartRef" class="chart"></div>
            </a-card>
          </a-col>
          <a-col :xs="24" :lg="10">
            <a-card title="人机协作占比（执行人次）" size="small" class="chart-card">
              <div ref="workerChartRef" class="chart"></div>
            </a-card>
          </a-col>
        </a-row>

        <a-row :gutter="16" class="chart-row">
          <a-col :span="24">
            <a-card title="任务燃尽图（累计完成 / 剩余）" size="small" class="chart-card">
              <div ref="burndownChartRef" class="chart chart-tall"></div>
            </a-card>
          </a-col>
        </a-row>

        <!-- 风险清单 -->
        <a-card title="风险预警" size="small" class="chart-card risk-card">
          <a-empty v-if="!stats.risks?.length" description="暂无风险预警" />
          <ul v-else class="risk-list">
            <li v-for="r in stats.risks" :key="r.task_id + r.type" class="risk-item">
              <a-tag :color="riskLevelColor[r.level]">
                {{ { high: '高', medium: '中', low: '低' }[r.level] }}
              </a-tag>
              <span class="risk-type">{{ riskTypeText[r.type] || r.type }}</span>
              <span class="risk-title">{{ r.title }}</span>
              <span class="risk-detail">{{ r.detail }}</span>
            </li>
          </ul>
        </a-card>
      </template>
      <a-empty v-else description="暂无统计数据" />
    </a-spin>
  </div>
</template>

<style scoped>
.case-stats-tab { padding: 4px 0; }

.overview-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
@media (max-width: 900px) { .overview-cards { grid-template-columns: repeat(2, 1fr); } }

.ov-card {
  background: var(--gray-10, #f7fafc);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 10px;
  padding: 14px 16px;
  text-align: center;
}
.ov-value { font-size: 26px; font-weight: 700; line-height: 1.1; }
.ov-label { font-size: 12px; color: var(--gray-500, #718096); margin-top: 4px; }

.chart-row { margin-bottom: 16px; }
.chart-card { height: 100%; }
.chart { height: 240px; }
.chart-tall { height: 280px; }

.risk-card { margin-bottom: 8px; }
.risk-list { list-style: none; margin: 0; padding: 0; }
.risk-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 4px;
  border-bottom: 1px solid var(--gray-50, #e2e8f0);
  font-size: 13px;
}
.risk-item:last-child { border-bottom: none; }
.risk-type {
  color: var(--gray-600, #4a5568);
  min-width: 84px;
}
.risk-title { font-weight: 600; color: var(--gray-1000, #1a202c); }
.risk-detail { color: var(--gray-500, #718096); margin-left: auto; text-align: right; }
</style>
