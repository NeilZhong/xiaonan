<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePoliceStore } from '@/stores/police'
import { message } from 'ant-design-vue'
import {
  ArrowLeft, Zap, Activity, FileText, Clock,
  TrendingUp, Award, Bot, Cpu
} from 'lucide-vue-next'
import '@/assets/police-sketch-theme.css'

const route = useRoute()
const router = useRouter()
const store = usePoliceStore()

const loading = ref(false)
const activeTab = ref('profile')

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

const agent = computed(() => store.currentAgent.value || null)

const stats = computed(() => {
  const s = agent.value?.work_stats || {}
  return {
    tasks_completed: s.tasks_completed || 0,
    tasks_total: s.tasks_total || 0,
    success_rate: s.success_rate ? (s.success_rate * 100).toFixed(0) : '100',
    cases_handled: s.cases_handled || 0,
    feedback_positive: s.feedback_positive || 0,
    feedback_negative: s.feedback_negative || 0,
  }
})

const growthLog = computed(() => agent.value?.growth_log || [])
const recentRuns = computed(() => agent.value?.recent_runs || [])
const sops = computed(() => agent.value?.sops || [])

function getAvatar() {
  if (!agent.value) return '\ud83e\udd16'
  if (agent.value.avatar && agent.value.avatar.length <= 2) return agent.value.avatar
  return avatarEmoji[agent.value.type] || '\ud83e\udd16'
}

function getColorClass() {
  return colorMap[agent.value?.color_theme] || colorMap.blue
}

function getTagClass() {
  return tagColorMap[agent.value?.color_theme] || tagColorMap.blue
}

function formatTime(t) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function runStatusColor(status) {
  const map = { completed: 'sketch-tag-green', running: 'sketch-tag-blue', failed: 'sketch-tag-coral', queued: 'sketch-tag-amber' }
  return map[status] || ''
}

async function loadData() {
  loading.value = true
  await store.loadAgent(Number(route.params.agentId))
  loading.value = false
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div style="background: var(--sketch-bg); min-height: calc(100vh - 48px); padding: 24px;">
    <!-- Loading -->
    <div v-if="loading" style="text-align: center; padding: 60px;">
      <a-spin size="large" />
    </div>

    <template v-else-if="agent">
      <!-- Back button -->
      <button class="sketch-btn" style="margin-bottom: 16px;" @click="router.push('/police/agents')">
        <ArrowLeft :size="16" />
        返回数字警员列表
      </button>

      <!-- Header Card -->
      <div class="sketch-card" style="padding: 24px; margin-bottom: 20px;">
        <div style="display: flex; align-items: flex-start; gap: 20px; flex-wrap: wrap;">
          <div :class="['sketch-avatar', 'sketch-avatar-lg', getColorClass()]" style="width: 96px; height: 96px; font-size: 44px;">
            {{ getAvatar() }}
          </div>
          <div style="flex: 1; min-width: 200px;">
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
              <h2 style="font-size: 22px; font-weight: 600; color: var(--sketch-text); margin: 0;">
                {{ agent.name }}
              </h2>
              <span :class="['sketch-tag', getTagClass()]">
                {{ agent.status === 'active' ? '在线' : '离线' }}
              </span>
            </div>
            <p style="font-size: 13px; color: var(--sketch-text-secondary); margin: 4px 0 0;">
              {{ agent.badge_number }} · {{ agent.rank || '数字警员' }} · {{ agent.department || '' }}
            </p>
            <p style="font-size: 12px; color: var(--sketch-text-muted); margin: 6px 0 0; display: flex; align-items: center; gap: 6px;">
              <span class="sketch-tag sketch-tag-purple" style="font-size: 11px;">小南智能体</span>
              <span v-if="agent.backend_id">{{ agent.backend_id }}</span>
              <span v-if="agent.agent_id" style="opacity: 0.7;">· ID {{ agent.agent_id }}</span>
              <span v-else style="color: var(--sketch-amber);">· 未对接</span>
            </p>
            <p style="font-size: 13px; color: var(--sketch-text-secondary); margin: 8px 0 0; line-height: 1.6;">
              {{ agent.description || agent.specialty || '暂无描述' }}
            </p>
            <!-- Capabilities -->
            <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px;">
              <span
                v-for="cap in (agent.capabilities || [])"
                :key="cap"
                :class="['sketch-tag', getTagClass()]"
                style="font-size: 11px;"
              >
                {{ cap }}
              </span>
            </div>
          </div>
          <!-- Stats column -->
          <div style="display: flex; gap: 16px; min-width: 200px;">
            <div class="sketch-stat">
              <div class="sketch-stat-num">{{ stats.tasks_completed }}</div>
              <div class="sketch-stat-label">已完成</div>
            </div>
            <div class="sketch-stat">
              <div class="sketch-stat-num" style="color: var(--sketch-green);">{{ stats.success_rate }}%</div>
              <div class="sketch-stat-label">准确率</div>
            </div>
            <div class="sketch-stat">
              <div class="sketch-stat-num" style="color: var(--sketch-blue);">{{ stats.cases_handled }}</div>
              <div class="sketch-stat-label">参与案件</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Two column layout -->
      <div style="display: flex; gap: 20px; flex-wrap: wrap;">
        <!-- Main column -->
        <div style="flex: 1; min-width: 400px;">
          <!-- Tab navigation -->
          <div style="display: flex; gap: 4px; margin-bottom: 16px; flex-wrap: wrap;">
            <button
              v-for="tab in [
                { key: 'profile', label: '档案', icon: FileText },
                { key: 'runs', label: '工作记录', icon: Activity },
                { key: 'sop', label: 'SOP 流程', icon: Cpu },
                { key: 'growth', label: '成长轨迹', icon: TrendingUp },
              ]"
              :key="tab.key"
              :class="['sketch-tag', activeTab === tab.key ? 'sketch-tag-amber' : '']"
              :style="activeTab === tab.key ? 'cursor: pointer; font-weight: 600; font-size: 13px; padding: 4px 14px;' : 'cursor: pointer; opacity: 0.7; font-size: 13px; padding: 4px 14px;'"
              @click="activeTab = tab.key"
            >
              <component :is="tab.icon" :size="14" style="margin-right: 4px;" />
              {{ tab.label }}
            </button>
          </div>

          <!-- Profile Tab -->
          <div v-show="activeTab === 'profile'" class="sketch-card" style="padding: 20px;">
            <div class="sketch-section-title">基本信息</div>
            <div class="sketch-list-item">
              <span style="color: var(--sketch-text-secondary); font-size: 12px; width: 100px; display: inline-block;">工号</span>
              <span style="color: var(--sketch-text); font-size: 13px;">{{ agent.badge_number || '-' }}</span>
            </div>
            <div class="sketch-list-item">
              <span style="color: var(--sketch-text-secondary); font-size: 12px; width: 100px; display: inline-block;">警衔</span>
              <span style="color: var(--sketch-text); font-size: 13px;">{{ agent.rank || '-' }}</span>
            </div>
            <div class="sketch-list-item">
              <span style="color: var(--sketch-text-secondary); font-size: 12px; width: 100px; display: inline-block;">专业领域</span>
              <span style="color: var(--sketch-text); font-size: 13px;">{{ agent.specialty || '-' }}</span>
            </div>
            <div class="sketch-list-item">
              <span style="color: var(--sketch-text-secondary); font-size: 12px; width: 100px; display: inline-block;">所属部门</span>
              <span style="color: var(--sketch-text); font-size: 13px;">{{ agent.department || '-' }}</span>
            </div>
            <div class="sketch-list-item">
              <span style="color: var(--sketch-text-secondary); font-size: 12px; width: 100px; display: inline-block;">经验等级</span>
              <span style="color: var(--sketch-text); font-size: 13px;">Lv.{{ agent.experience_level || 1 }}</span>
            </div>

            <hr class="sketch-divider" />

            <div class="sketch-section-title">能力矩阵</div>
            <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px;">
              <span
                v-for="cap in (agent.capabilities || [])"
                :key="'cap-' + cap"
                :class="['sketch-tag', getTagClass()]"
              >
                {{ cap }}
              </span>
            </div>

            <div class="sketch-section-title" style="margin-top: 16px;">工具与技能</div>
            <div style="display: flex; flex-wrap: wrap; gap: 6px;">
              <span v-for="tool in (agent.tools || [])" :key="'t-' + tool" class="sketch-tag" style="font-size: 11px;">
                {{ tool }}
              </span>
              <span v-for="skill in (agent.skills || [])" :key="'s-' + skill" class="sketch-tag sketch-tag-purple" style="font-size: 11px;">
                {{ skill }}
              </span>
            </div>

            <hr class="sketch-divider" />

            <div class="sketch-section-title">系统指令</div>
            <div class="sketch-card-flat" style="padding: 12px; font-size: 12px; color: var(--sketch-text-secondary); line-height: 1.6; white-space: pre-wrap; max-height: 200px; overflow-y: auto;">
              {{ agent.system_prompt }}
            </div>
          </div>

          <!-- Work Records Tab -->
          <div v-show="activeTab === 'runs'" class="sketch-card" style="padding: 20px;">
            <div class="sketch-section-title">最近运行记录</div>
            <div v-if="recentRuns.length === 0" class="sketch-empty">
              <div class="sketch-empty-icon"><Activity :size="40" /></div>
              <p style="font-size: 13px;">暂无运行记录</p>
            </div>
            <div v-else>
              <div
                v-for="run in recentRuns"
                :key="run.id"
                class="sketch-timeline-item"
              >
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                  <span :class="['sketch-tag', 'sketch-tag-' + (runStatusColor(run.status) || '').replace('sketch-tag-', '')]" style="font-size: 11px;">
                    {{ run.status }}
                  </span>
                  <span style="font-size: 11px; color: var(--sketch-text-muted);">
                    {{ formatTime(run.created_at) }}
                  </span>
                </div>
                <div v-if="run.error" style="font-size: 12px; color: var(--sketch-coral); margin-top: 4px;">
                  {{ run.error }}
                </div>
                <div v-if="run.output" style="font-size: 12px; color: var(--sketch-text-secondary); margin-top: 4px;">
                  {{ JSON.stringify(run.output).slice(0, 100) }}...
                </div>
                <div style="font-size: 11px; color: var(--sketch-text-muted); margin-top: 4px;">
                  Tokens: {{ run.tokens_used || 0 }}
                  <span v-if="run.duration_ms"> · {{ run.duration_ms }}ms</span>
                </div>
              </div>
            </div>
          </div>

          <!-- SOP Tab -->
          <div v-show="activeTab === 'sop'" class="sketch-card" style="padding: 20px;">
            <div class="sketch-section-title">SOP 流程技能</div>
            <div v-if="sops.length === 0" class="sketch-empty">
              <div class="sketch-empty-icon"><Cpu :size="40" /></div>
              <p style="font-size: 13px;">暂无 SOP 流程</p>
              <p style="font-size: 11px; margin-top: 4px;">SOP 是状态机驱动的流程技能，将公安办案流程定义为可执行的结构化步骤</p>
            </div>
            <div v-else>
              <div
                v-for="sop in sops"
                :key="sop.id"
                class="sketch-card-flat"
                style="padding: 14px; margin-bottom: 12px;"
              >
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
                  <h4 style="font-size: 14px; font-weight: 600; color: var(--sketch-text); margin: 0;">
                    {{ sop.name }}
                  </h4>
                  <span :class="['sketch-tag', sop.is_published ? 'sketch-tag-green' : 'sketch-tag-amber']" style="font-size: 11px;">
                    {{ sop.is_published ? '已发布' : '草稿' }}
                  </span>
                </div>
                <p style="font-size: 12px; color: var(--sketch-text-secondary); margin: 0 0 8px;">
                  {{ sop.description || '暂无描述' }}
                </p>
                <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                  <span
                    v-for="(state, idx) in (sop.states || [])"
                    :key="state.id || idx"
                    class="sketch-tag"
                    :style="state.id === sop.initial_state ? 'font-size: 11px; border-color: var(--sketch-accent); color: #b8722a;' : 'font-size: 11px;'"
                  >
                    {{ idx + 1 }}. {{ state.name }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Growth Tab -->
          <div v-show="activeTab === 'growth'" class="sketch-card" style="padding: 20px;">
            <div class="sketch-section-title">成长轨迹</div>
            <div v-if="growthLog.length === 0" class="sketch-empty">
              <div class="sketch-empty-icon"><TrendingUp :size="40" /></div>
              <p style="font-size: 13px;">暂无成长记录</p>
            </div>
            <div v-else>
              <div
                v-for="(entry, idx) in growthLog"
                :key="idx"
                class="sketch-timeline-item"
              >
                <div style="display: flex; align-items: center; gap: 8px;">
                  <Award :size="14" color="var(--sketch-accent)" />
                  <span style="font-size: 13px; font-weight: 500; color: var(--sketch-text);">
                    {{ entry.event }}
                  </span>
                </div>
                <p style="font-size: 12px; color: var(--sketch-text-secondary); margin: 4px 0 0;">
                  {{ entry.description }}
                </p>
                <p style="font-size: 11px; color: var(--sketch-text-muted); margin: 2px 0 0;">
                  {{ formatTime(entry.date) }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Sidebar -->
        <div style="width: 280px; flex-shrink: 0;">
          <div class="sketch-card" style="padding: 16px; margin-bottom: 16px;">
            <div class="sketch-section-title">工作统计</div>
            <div class="sketch-list-item">
              <span style="color: var(--sketch-text-secondary); font-size: 12px;">已完成任务</span>
              <span style="float: right; font-size: 14px; font-weight: 600; color: var(--sketch-text);">
                {{ stats.tasks_completed }}
              </span>
            </div>
            <div class="sketch-list-item">
              <span style="color: var(--sketch-text-secondary); font-size: 12px;">总任务数</span>
              <span style="float: right; font-size: 14px; font-weight: 600; color: var(--sketch-text);">
                {{ stats.tasks_total }}
              </span>
            </div>
            <div class="sketch-list-item">
              <span style="color: var(--sketch-text-secondary); font-size: 12px;">准确率</span>
              <span style="float: right; font-size: 14px; font-weight: 600; color: var(--sketch-green);">
                {{ stats.success_rate }}%
              </span>
            </div>
            <div class="sketch-list-item">
              <span style="color: var(--sketch-text-secondary); font-size: 12px;">参与案件</span>
              <span style="float: right; font-size: 14px; font-weight: 600; color: var(--sketch-blue);">
                {{ stats.cases_handled }}
              </span>
            </div>
            <div class="sketch-list-item">
              <span style="color: var(--sketch-text-secondary); font-size: 12px;">好评</span>
              <span style="float: right; font-size: 14px; font-weight: 600; color: var(--sketch-green);">
                {{ stats.feedback_positive }}
              </span>
            </div>
            <div class="sketch-list-item">
              <span style="color: var(--sketch-text-secondary); font-size: 12px;">差评</span>
              <span style="float: right; font-size: 14px; font-weight: 600; color: var(--sketch-coral);">
                {{ stats.feedback_negative }}
              </span>
            </div>
          </div>

          <div class="sketch-card" style="padding: 16px;">
            <div class="sketch-section-title">模型配置</div>
            <div class="sketch-list-item">
              <span style="color: var(--sketch-text-secondary); font-size: 12px;">Provider</span>
              <span style="float: right; font-size: 12px; color: var(--sketch-text);">
                {{ agent.model_config?.provider || '-' }}
              </span>
            </div>
            <div class="sketch-list-item">
              <span style="color: var(--sketch-text-secondary); font-size: 12px;">Model</span>
              <span style="float: right; font-size: 12px; color: var(--sketch-text);">
                {{ agent.model_config?.model || '-' }}
              </span>
            </div>
            <div class="sketch-list-item">
              <span style="color: var(--sketch-text-secondary); font-size: 12px;">Temperature</span>
              <span style="float: right; font-size: 12px; color: var(--sketch-text);">
                {{ agent.model_config?.temperature ?? '-' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Not found -->
    <div v-else class="sketch-empty">
      <div class="sketch-empty-icon"><Bot :size="48" /></div>
      <p style="font-size: 14px;">数字警员未找到</p>
      <button class="sketch-btn" style="margin-top: 12px;" @click="router.push('/police/agents')">
        返回列表
      </button>
    </div>
  </div>
</template>
