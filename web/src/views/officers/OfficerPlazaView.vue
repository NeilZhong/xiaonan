<template>
  <div class="officer-plaza">
    <div class="plaza-header">
      <div class="plaza-title">
        <span class="plaza-emoji">🚓</span>
        <div>
          <h2>数字警员广场</h2>
          <p class="plaza-sub">每位数字警员都是一个专业智能体 —— 填写名称即可创建，开箱即用</p>
        </div>
      </div>
      <div class="plaza-actions">
        <a-input-search
          v-model:value="keyword"
          placeholder="搜索数字警员"
          allow-clear
          class="plaza-search"
          @search="loadAgents"
        />
        <a-button type="primary" @click="openCreate">
          <span class="plus-icon">＋</span> 新建数字警员
        </a-button>
        <a-button v-if="isSuperAdmin" @click="handleSeed" :loading="seeding">
          初始化预设警员
        </a-button>
      </div>
    </div>

    <div class="plaza-filters">
      <a-segmented
        v-model:value="statusFilter"
        :options="statusOptions"
        @change="loadAgents"
        class="plaza-status"
      />
    </div>

    <div v-if="loading" class="plaza-loading">
      <a-spin tip="加载数字警员中..." />
    </div>

    <a-empty
      v-else-if="agents.length === 0"
      description="还没有数字警员，点击右上角「新建数字警员」创建"
    />

    <div v-else class="plaza-grid">
      <div
        v-for="agent in agents"
        :key="agent.id"
        class="officer-card"
        :class="`theme-${agent.color_theme || 'blue'}`"
        @click="goProfile(agent.id)"
      >
        <div class="card-topbar" />
        <div class="card-head">
          <div class="avatar" :class="`bg-${agent.color_theme || 'blue'}`">
            {{ avatarEmoji(agent.avatar) }}
          </div>
          <div class="head-info">
            <div class="name-row">
              <span class="name">{{ agent.name }}</span>
              <a-badge
                :status="statusBadge(agent.status)"
                :text="statusText(agent.status)"
              />
            </div>
            <div class="badge-no">工号 {{ agent.badge_number || '—' }}</div>
          </div>
        </div>

        <div class="meta-row">
          <span class="meta-chip">{{ agent.rank || '—' }}</span>
          <span class="meta-chip">{{ agent.department || '—' }}</span>
        </div>

        <div class="specialty">{{ agent.specialty || agent.description || '—' }}</div>

        <div class="capabilities">
          <a-tag
            v-for="cap in (agent.capabilities || []).slice(0, 4)"
            :key="cap"
            class="cap-tag"
          >{{ cap }}</a-tag>
          <span v-if="(agent.capabilities || []).length > 4" class="more-cap">
            +{{ (agent.capabilities || []).length - 4 }}
          </span>
        </div>

        <div class="card-foot">
          <div class="stat">
            <span class="stat-num">{{ workCount(agent) }}</span>
            <span class="stat-label">工作次数</span>
          </div>
          <div class="enter-hint">查看档案 →</div>
        </div>
      </div>
    </div>

    <OfficerFormDrawer
      v-model:open="createOpen"
      mode="create"
      @success="onCreated"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { policeAgentApi } from '@/apis/police_api'
import { message } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import { storeToRefs } from 'pinia'
import OfficerFormDrawer from './OfficerFormDrawer.vue'

const router = useRouter()
const userStore = useUserStore()
const { isSuperAdmin } = storeToRefs(userStore)

const agents = ref([])
const loading = ref(false)
const keyword = ref('')
const statusFilter = ref('')
const seeding = ref(false)
const createOpen = ref(false)

function openCreate() {
  createOpen.value = true
}
function onCreated() {
  loadAgents()
}

const statusOptions = [
  { label: '全部', value: '' },
  { label: '在线', value: 'active' },
  { label: '训练中', value: 'training' },
  { label: '离线', value: 'offline' },
]

const AVATAR_EMOJI = {
  pencil: '✏️',
  chart: '📊',
  file: '📄',
  shield: '🛡️',
  network: '🕸️',
}

function avatarEmoji(name) {
  return AVATAR_EMOJI[name] || '🤖'
}

function statusBadge(status) {
  return { active: 'success', training: 'processing', offline: 'default' }[status] || 'default'
}

function statusText(status) {
  return { active: '在线', training: '训练中', offline: '离线' }[status] || '离线'
}

function workCount(agent) {
  const s = agent.work_stats || {}
  return s.tasks_completed ?? s.cases_handled ?? 0
}

async function loadAgents() {
  loading.value = true
  try {
    const params = {
      page: 1,
      page_size: 50,
    }
    if (keyword.value) params.keyword = keyword.value
    if (statusFilter.value) params.status = statusFilter.value
    const res = await policeAgentApi.list(params)
    agents.value = res.items || []
  } catch (e) {
    message.error('加载数字警员失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

async function handleSeed() {
  seeding.value = true
  try {
    const res = await policeAgentApi.seed()
    message.success(`已初始化 ${res.created ?? 0} 个数字警员（同步 ${res.synced ?? 0} 个）`)
    await loadAgents()
  } catch (e) {
    message.error('初始化失败: ' + (e.message || e))
  } finally {
    seeding.value = false
  }
}

function goProfile(id) {
  router.push(`/police/officers/${id}`)
}

onMounted(loadAgents)
</script>

<style scoped>
.officer-plaza {
  padding: var(--page-padding);
  max-width: 1280px;
  margin: 0 auto;
}

/* 海军蓝基调，呼应 v1.3 公安属性（局部作用域，不改动全局主题） */
.plaza-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 22px;
}
.plaza-title {
  display: flex;
  gap: 14px;
  align-items: center;
}
.plaza-emoji {
  font-size: 38px;
  filter: drop-shadow(0 2px 4px var(--shadow-1));
}
.plaza-title h2 {
  margin: 0;
  font-size: 22px;
  color: #1A365D;
  font-weight: 700;
  letter-spacing: 0.5px;
}
.plaza-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--gray-600);
}
.plaza-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
.plaza-search {
  width: 240px;
}

.plaza-filters {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
}
.plaza-status {
  background: var(--gray-100);
  border-radius: 8px;
}

.plaza-loading {
  display: flex;
  justify-content: center;
  padding: 80px 0;
}

.plaza-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 18px;
}

/* 手绘风卡片：圆角、柔和阴影、顶部主题色条 */
.officer-card {
  position: relative;
  background: #fff;
  border-radius: 18px;
  padding: 18px 18px 14px;
  cursor: pointer;
  box-shadow: 0 6px 18px var(--shadow-1);
  border: 1px solid var(--gray-150);
  overflow: hidden;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.officer-card:hover {
  transform: translateY(-4px) rotate(-0.4deg);
  box-shadow: 0 14px 30px var(--shadow-2);
}
.card-topbar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 6px;
}
.theme-blue .card-topbar { background: linear-gradient(90deg, #2B6CB0, #3182CE); }
.theme-green .card-topbar { background: linear-gradient(90deg, #2F855A, #38A169); }
.theme-amber .card-topbar { background: linear-gradient(90deg, #B7791F, #D69E2E); }
.theme-coral .card-topbar { background: linear-gradient(90deg, #C53030, #E53E3E); }
.theme-purple .card-topbar { background: linear-gradient(90deg, #6B46C1, #805AD5); }

.card-head {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 4px;
}
.avatar {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  color: #fff;
  flex-shrink: 0;
}
.bg-blue { background: #2B6CB0; }
.bg-green { background: #2F855A; }
.bg-amber { background: #B7791F; }
.bg-coral { background: #C53030; }
.bg-purple { background: #6B46C1; }

.head-info { flex: 1; min-width: 0; }
.name-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.name {
  font-size: 16px;
  font-weight: 600;
  color: #1A202C;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.badge-no {
  font-size: 12px;
  color: var(--gray-500);
  margin-top: 2px;
}

.meta-row {
  display: flex;
  gap: 8px;
  margin: 12px 0 8px;
  flex-wrap: wrap;
}
.meta-chip {
  font-size: 12px;
  color: #1A365D;
  background: #EBF2FA;
  border-radius: 10px;
  padding: 2px 10px;
}

.specialty {
  font-size: 13px;
  color: var(--gray-700);
  line-height: 1.5;
  min-height: 38px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.capabilities {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 12px 0;
  min-height: 26px;
}
.cap-tag {
  font-size: 11px;
  border-radius: 8px;
  background: var(--gray-100);
  color: var(--gray-700);
  border: none;
  margin: 0;
}
.more-cap {
  font-size: 11px;
  color: var(--gray-500);
  align-self: center;
}

.card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px dashed var(--gray-200);
  padding-top: 10px;
  margin-top: 4px;
}
.stat {
  display: flex;
  flex-direction: column;
}
.stat-num {
  font-size: 18px;
  font-weight: 700;
  color: #1A365D;
}
.stat-label {
  font-size: 11px;
  color: var(--gray-500);
}
.enter-hint {
  font-size: 12px;
  color: var(--gray-500);
  transition: color 0.15s ease;
}
.officer-card:hover .enter-hint {
  color: #2B6CB0;
}
</style>
