<template>
  <div class="officer-profile" v-if="agent">
    <!-- 返回 + 标题栏 -->
    <div class="profile-bar">
      <a-button type="text" @click="goBack">
        <span class="back-arrow">←</span> 返回广场
      </a-button>
      <div class="bar-actions">
        <a-button @click="goCases">编入专案组</a-button>
        <a-button @click="openEdit">编辑</a-button>
        <a-popconfirm
          title="确认删除该数字警员？"
          description="删除后其对话智能体也将一并移除，不可恢复。"
          ok-text="删除"
          cancel-text="取消"
          :ok-button-props="{ danger: true }"
          @confirm="handleDelete"
        >
          <a-button danger>删除</a-button>
        </a-popconfirm>
        <a-button type="primary" @click="goChat">发起对话</a-button>
      </div>
    </div>

    <!-- 头部档案卡 -->
    <div class="profile-head" :class="`theme-${agent.color_theme || 'blue'}`">
      <div class="head-avatar" :class="`bg-${agent.color_theme || 'blue'}`">
        <img class="head-avatar-img" :src="resolveAgentAvatar(agent)" :alt="agent.name" />
      </div>
      <div class="head-main">
        <div class="head-line1">
          <h2>{{ agent.name }}</h2>
          <a-badge :status="statusBadge(agent.status)" :text="statusText(agent.status)" />
        </div>
        <div class="head-line2">
          <span class="tag-pill">工号 {{ agent.badge_number || '—' }}</span>
          <span class="tag-pill">{{ agent.rank || '—' }}</span>
          <span class="tag-pill">{{ agent.department || '—' }}</span>
        </div>
        <div class="head-specialty">{{ agent.specialty || agent.description || '—' }}</div>
      </div>
      <div class="head-exp">
        <div class="exp-num">Lv.{{ agent.experience_level || 1 }}</div>
        <div class="exp-label">经验等级</div>
      </div>
    </div>

    <a-row :gutter="16" class="profile-body">
      <!-- 左列：能力矩阵 + 技能 + SOP -->
      <a-col :xs="24" :lg="14">
        <a-card class="block" title="能力矩阵">
          <div class="cap-matrix">
            <div v-for="cap in (agent.capabilities || [])" :key="cap" class="cap-item">
              <span class="cap-dot" />{{ cap }}
            </div>
            <a-empty v-if="!(agent.capabilities || []).length" description="暂无能力标签" />
          </div>
        </a-card>

        <a-card class="block" title="技能列表">
          <a-tag v-for="s in (agent.skills || [])" :key="s" class="skill-tag">{{ s }}</a-tag>
          <div v-if="!(agent.skills || []).length" class="muted">暂未挂载技能</div>
        </a-card>

        <a-card class="block" title="关联 SOP / 办案规程">
          <div v-for="sop in (agent.sops || [])" :key="sop.id" class="sop-item">
            <div class="sop-name">{{ sop.name }}</div>
            <div class="sop-desc">{{ sop.description || '—' }}</div>
          </div>
          <a-empty v-if="!(agent.sops || []).length" description="暂无关联 SOP" />
        </a-card>
      </a-col>

      <!-- 右列：工作统计 + 工作记录 + 成长轨迹 -->
      <a-col :xs="24" :lg="10">
        <a-card class="block" title="工作统计">
          <a-row :gutter="12">
            <a-col :span="8" v-for="stat in statCards" :key="stat.label" class="stat-cell">
              <div class="stat-num">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </a-col>
          </a-row>
        </a-card>

        <a-card class="block" title="工作记录">
          <a-timeline v-if="(agent.recent_runs || []).length">
            <a-timeline-item
              v-for="run in agent.recent_runs"
              :key="run.id"
              :color="runColor(run.status)"
            >
              <div class="run-row">
                <span class="run-title">运行 #{{ run.id }}</span>
                <a-tag :color="runColor(run.status)" class="run-status">
                  {{ runText(run.status) }}
                </a-tag>
              </div>
              <div class="run-meta">
                案件 #{{ run.case_id }} · {{ run.tokens_used || 0 }} tokens
                <span v-if="run.started_at"> · {{ run.started_at }}</span>
              </div>
            </a-timeline-item>
          </a-timeline>
          <a-empty v-else description="暂无运行记录" />
        </a-card>

        <a-card class="block" title="成长轨迹">
          <a-timeline v-if="(agent.growth_log || []).length">
            <a-timeline-item
              v-for="(g, i) in agent.growth_log"
              :key="i"
              color="#1A365D"
            >
              <div class="growth-event">{{ g.event }}</div>
              <div class="growth-desc">{{ g.description }}</div>
              <div class="growth-date" v-if="g.date">{{ g.date }}</div>
            </a-timeline-item>
          </a-timeline>
          <a-empty v-else description="暂无成长事件" />
        </a-card>
      </a-col>
    </a-row>
  </div>

  <div v-else class="profile-loading">
    <a-spin tip="加载数字警员档案中..." />
  </div>

  <OfficerFormDrawer
    v-model:open="editOpen"
    mode="edit"
    :agent="agent"
    @success="onEdited"
  />
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { policeAgentApi } from '@/apis/police_api'
import { message } from 'ant-design-vue'
import { resolveAgentAvatar } from '@/utils/policeAvatar'
import OfficerFormDrawer from './OfficerFormDrawer.vue'

const route = useRoute()
const router = useRouter()
const agent = ref(null)
const loading = ref(false)
const editOpen = ref(false)

function openEdit() {
  editOpen.value = true
}
async function onEdited() {
  await load()
}
async function handleDelete() {
  try {
    await policeAgentApi.delete(agent.value.id)
    message.success('数字警员已删除')
    router.push('/police/officers')
  } catch (e) {
    message.error('删除失败: ' + (e.message || e))
  }
}

function statusBadge(s) { return { active: 'success', training: 'processing', offline: 'default' }[s] || 'default' }
function statusText(s) { return { active: '在线', training: '训练中', offline: '离线' }[s] || '离线' }
function runColor(s) {
  return { queued: 'gray', running: 'blue', completed: 'green', failed: 'red', cancelled: 'gray' }[s] || 'gray'
}
function runText(s) {
  return { queued: '排队中', running: '运行中', completed: '已完成', failed: '失败', cancelled: '已取消' }[s] || s
}

const statCards = computed(() => {
  const s = agent.value?.work_stats || {}
  return [
    { label: '完成任务', value: s.tasks_completed ?? 0 },
    { label: '处理案件', value: s.cases_handled ?? 0 },
    { label: '好评率', value: s.feedback_positive != null ? `${s.feedback_positive}%` : '—' },
  ]
})

async function load() {
  loading.value = true
  try {
    const res = await policeAgentApi.get(route.params.id)
    agent.value = res
  } catch (e) {
    message.error('加载档案失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

function goBack() { router.push('/police/officers') }
function goChat() {
  // 数字警员已桥接为 yuxi 主对话智能体（slug=工号小写），直接带 slug 打开 /agent 对话页
  const raw = agent.value?.badge_number || agent.value?.agent_id
  const slug = raw ? String(raw).toLowerCase() : ''
  if (slug) {
    router.push({ path: '/agent', query: { agent_id: slug } })
  } else {
    router.push('/agent')
  }
}
function goCases() { router.push('/police/cases') }

onMounted(load)
</script>

<style scoped>
.officer-profile {
  padding: var(--page-padding);
  max-width: 1180px;
  margin: 0 auto;
}

.profile-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.back-arrow { font-size: 16px; margin-right: 4px; }
.bar-actions { display: flex; gap: 10px; }

.profile-head {
  position: relative;
  display: flex;
  align-items: center;
  gap: 18px;
  background: #fff;
  border-radius: 18px;
  padding: 22px 24px;
  box-shadow: 0 6px 18px var(--shadow-1);
  border: 1px solid var(--gray-150);
  overflow: hidden;
  margin-bottom: 18px;
}
.profile-head::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 6px;
}
.theme-blue::before { background: #2B6CB0; }
.theme-green::before { background: #2F855A; }
.theme-amber::before { background: #B7791F; }
.theme-coral::before { background: #C53030; }
.theme-purple::before { background: #6B46C1; }

.head-avatar {
  width: 72px; height: 72px;
  border-radius: 18px;
  display: flex; align-items: center; justify-content: center;
  font-size: 38px; color: #fff; flex-shrink: 0;
  overflow: hidden;
}
.head-avatar-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.bg-blue { background: #2B6CB0; }
.bg-green { background: #2F855A; }
.bg-amber { background: #B7791F; }
.bg-coral { background: #C53030; }
.bg-purple { background: #6B46C1; }

.head-main { flex: 1; min-width: 0; }
.head-line1 { display: flex; align-items: center; gap: 12px; }
.head-line1 h2 { margin: 0; font-size: 22px; color: #1A365D; font-weight: 700; }
.head-line2 { display: flex; gap: 8px; margin: 8px 0; flex-wrap: wrap; }
.tag-pill {
  font-size: 12px; color: #1A365D; background: #EBF2FA;
  border-radius: 10px; padding: 2px 10px;
}
.head-specialty { font-size: 13px; color: var(--gray-700); line-height: 1.5; }

.head-exp {
  text-align: center; flex-shrink: 0;
  background: #F7FAFC; border-radius: 14px; padding: 10px 16px;
}
.exp-num { font-size: 20px; font-weight: 700; color: #1A365D; }
.exp-label { font-size: 11px; color: var(--gray-500); }

.profile-body { margin: 0 !important; }
.block {
  border-radius: 16px;
  margin-bottom: 16px;
  border: 1px solid var(--gray-150);
  box-shadow: 0 4px 12px var(--shadow-1);
}
.block :deep(.ant-card-head-title) { font-weight: 600; color: #1A365D; }

.cap-matrix {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
}
.cap-item {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; color: var(--gray-800);
  background: var(--gray-50); border-radius: 10px; padding: 8px 12px;
}
.cap-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #2B6CB0; flex-shrink: 0;
}

.skill-tag {
  font-size: 12px; margin: 0 6px 6px 0;
  border-radius: 8px; background: #EBF2FA; color: #1A365D; border: none;
}
.muted { color: var(--gray-500); font-size: 13px; }

.sop-item {
  padding: 10px 0;
  border-bottom: 1px dashed var(--gray-200);
}
.sop-item:last-child { border-bottom: none; }
.sop-name { font-size: 14px; font-weight: 600; color: #1A202C; }
.sop-desc { font-size: 12px; color: var(--gray-600); margin-top: 2px; }

.stat-cell { text-align: center; margin-bottom: 8px; }
.stat-num { font-size: 20px; font-weight: 700; color: #1A365D; }
.stat-label { font-size: 11px; color: var(--gray-500); margin-top: 2px; }

.run-row { display: flex; align-items: center; gap: 8px; }
.run-title { font-size: 13px; font-weight: 600; color: var(--gray-900); }
.run-status { font-size: 11px; }
.run-meta { font-size: 12px; color: var(--gray-500); margin-top: 2px; }

.growth-event { font-size: 13px; font-weight: 600; color: #1A202C; }
.growth-desc { font-size: 12px; color: var(--gray-600); margin-top: 2px; }
.growth-date { font-size: 11px; color: var(--gray-400); margin-top: 2px; }

.profile-loading {
  display: flex; justify-content: center; padding: 120px 0;
}
</style>
