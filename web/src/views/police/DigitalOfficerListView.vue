<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePoliceStore } from '@/stores/police'
import { message } from 'ant-design-vue'
import { Users, Plus, Sparkles, Zap } from 'lucide-vue-next'
import '@/assets/police-sketch-theme.css'

const router = useRouter()
const store = usePoliceStore()

const loading = ref(false)
const keyword = ref('')
const typeFilter = ref('')
const showCreateModal = ref(false)

const typeOptions = [
  { label: '全部', value: '' },
  { label: '笔录分析', value: 'transcript_analyst' },
  { label: '资金追踪', value: 'fund_analyst' },
  { label: '调证生成', value: 'evidence_collector' },
  { label: '法制审核', value: 'legal_reviewer' },
  { label: '案件编排', value: 'case_orchestrator' },
]

const avatarEmoji = {
  transcript_analyst: '\u270f\ufe0f',
  fund_analyst: '\ud83d\udcc8',
  evidence_collector: '\ud83d\udcc4',
  legal_reviewer: '\u2696\ufe0f',
  case_orchestrator: '\ud83e\udd16',
}

const colorMap = {
  blue: 'sketch-avatar-blue',
  green: 'sketch-avatar-green',
  coral: 'sketch-avatar-coral',
  amber: 'sketch-avatar-amber',
  purple: 'sketch-avatar-purple',
}

const tagColorMap = {
  blue: 'sketch-tag-blue',
  green: 'sketch-tag-green',
  coral: 'sketch-tag-coral',
  amber: 'sketch-tag-amber',
  purple: 'sketch-tag-purple',
}

const filteredAgents = computed(() => store.agents)

async function loadData() {
  loading.value = true
  await store.loadAgents({
    keyword: keyword.value || undefined,
    type: typeFilter.value || undefined,
  })
  loading.value = false
}

async function handleSeed() {
  try {
    const res = await store.seedAgents()
    if (res?.created > 0) {
      message.success(`初始化了 ${res.created} 名数字警员`)
    } else {
      message.info('数字警员已存在，无需重复初始化')
    }
    await loadData()
  } catch (e) {
    message.error('初始化失败')
  }
}

function getAvatar(agent) {
  if (agent.avatar && agent.avatar.length <= 2) return agent.avatar
  return avatarEmoji[agent.type] || '\ud83e\udd16'
}

function getColorClass(agent) {
  return colorMap[agent.color_theme] || colorMap.blue
}

function getTagClass(agent) {
  return tagColorMap[agent.color_theme] || tagColorMap.blue
}

function getStats(agent) {
  const s = agent.work_stats || {}
  return {
    tasks: s.tasks_completed || 0,
    success: s.success_rate ? `${(s.success_rate * 100).toFixed(0)}%` : '100%',
    cases: s.cases_handled || 0,
  }
}

function goToDetail(agent) {
  router.push(`/police/agents/${agent.id}`)
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="police-agent-list" style="background: var(--sketch-bg); min-height: calc(100vh - 48px); padding: 24px;">
    <!-- Header -->
    <div class="sketch-panel" style="margin-bottom: 20px;">
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <div class="sketch-avatar sketch-avatar-lg" style="background: var(--sketch-accent-light); border-color: var(--sketch-accent);">
            <Users :size="32" color="#b8722a" />
          </div>
          <div>
            <h2 style="font-size: 20px; font-weight: 600; color: var(--sketch-text); margin: 0;">数字警员</h2>
            <p style="font-size: 13px; color: var(--sketch-text-secondary); margin: 4px 0 0;">
              像管理真实员工一样管理 AI — 每位数字警员有档案、能力、工作记录和成长轨迹
            </p>
          </div>
        </div>
        <div style="display: flex; gap: 8px;">
          <button class="sketch-btn" @click="handleSeed">
            <Sparkles :size="16" />
            初始化预设
          </button>
          <button class="sketch-btn sketch-btn-primary" @click="showCreateModal = true">
            <Plus :size="16" />
            创建数字警员
          </button>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="sketch-card-flat" style="padding: 12px 16px; margin-bottom: 20px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap;">
      <a-input-search
        v-model:value="keyword"
        placeholder="搜索数字警员名称..."
        style="max-width: 240px;"
        @search="loadData"
        allow-clear
        @change="loadData"
      />
      <div style="display: flex; gap: 6px; flex-wrap: wrap;">
        <button
          v-for="opt in typeOptions"
          :key="opt.value"
          :class="['sketch-tag', typeFilter === opt.value ? tagColorMap.amber : '']"
          :style="typeFilter === opt.value ? 'cursor: pointer; font-weight: 600;' : 'cursor: pointer; opacity: 0.7;'"
          @click="typeFilter = opt.value; loadData()"
        >
          {{ opt.label }}
        </button>
      </div>
    </div>

    <!-- Agent Cards Grid -->
    <div v-if="loading" style="text-align: center; padding: 60px;">
      <a-spin size="large" />
    </div>

    <div v-else-if="filteredAgents.length === 0" class="sketch-empty">
      <div class="sketch-empty-icon">
        <Zap :size="48" />
      </div>
      <p style="font-size: 14px;">还没有数字警员</p>
      <p style="font-size: 12px; margin-top: 4px;">点击"初始化预设"创建 5 名预设数字警员</p>
    </div>

    <div v-else style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px;">
      <div
        v-for="agent in filteredAgents"
        :key="agent.id"
        class="sketch-card"
        style="padding: 20px; cursor: pointer;"
        @click="goToDetail(agent)"
      >
        <!-- Top: Avatar + Name + Badge -->
        <div style="display: flex; align-items: flex-start; gap: 12px; margin-bottom: 16px;">
          <div :class="['sketch-avatar sketch-avatar-lg', getColorClass(agent)]">
            {{ getAvatar(agent) }}
          </div>
          <div style="flex: 1; min-width: 0;">
            <h3 style="font-size: 16px; font-weight: 600; color: var(--sketch-text); margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              {{ agent.name }}
            </h3>
            <p style="font-size: 12px; color: var(--sketch-text-secondary); margin: 2px 0 0;">
              {{ agent.badge_number }} · {{ agent.rank || '数字警员' }}
            </p>
            <p style="font-size: 11px; color: var(--sketch-text-muted); margin: 2px 0 0;">
              {{ agent.department || '' }}
            </p>
          </div>
          <span :class="['sketch-tag', getTagClass(agent)]" style="font-size: 11px;">
            {{ agent.status === 'active' ? '在线' : '离线' }}
          </span>
        </div>

        <!-- Specialty -->
        <p style="font-size: 12px; color: var(--sketch-text-secondary); margin: 0 0 12px; line-height: 1.5;">
          {{ agent.specialty || '暂无专长描述' }}
        </p>

        <!-- Capabilities -->
        <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 16px; min-height: 28px;">
          <span
            v-for="cap in (agent.capabilities || []).slice(0, 4)"
            :key="cap"
            class="sketch-tag"
            style="font-size: 11px; padding: 1px 8px;"
          >
            {{ cap }}
          </span>
          <span
            v-if="(agent.capabilities || []).length > 4"
            class="sketch-tag"
            style="font-size: 11px; padding: 1px 8px; opacity: 0.6;"
          >
            +{{ (agent.capabilities || []).length - 4 }}
          </span>
        </div>

        <hr class="sketch-divider" style="margin: 12px 0;" />

        <!-- Work Stats -->
        <div style="display: flex; justify-content: space-around;">
          <div class="sketch-stat">
            <div class="sketch-stat-num">{{ getStats(agent).tasks }}</div>
            <div class="sketch-stat-label">已完成任务</div>
          </div>
          <div class="sketch-stat">
            <div class="sketch-stat-num" style="color: var(--sketch-green);">{{ getStats(agent).success }}</div>
            <div class="sketch-stat-label">准确率</div>
          </div>
          <div class="sketch-stat">
            <div class="sketch-stat-num" style="color: var(--sketch-blue);">{{ getStats(agent).cases }}</div>
            <div class="sketch-stat-label">参与案件</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Modal (placeholder) -->
    <a-modal
      v-model:open="showCreateModal"
      title="创建数字警员"
      :footer="null"
      width="600px"
    >
      <a-alert message="数字警员创建功能开发中，可先使用'初始化预设'创建 5 名预设警员。" type="info" show-icon />
    </a-modal>
  </div>
</template>
