<template>
  <div class="explore-view">
    <!-- 头部：标题 + 搜索 + 发布 -->
    <div class="explore-header">
      <div class="explore-title">
        <span class="explore-emoji">🛒</span>
        <div>
          <h2>小南市场</h2>
          <p class="explore-sub">浏览数字民警、协助伙伴与侦查模板，一键申请使用或发布你的创作</p>
        </div>
      </div>
      <div class="explore-actions">
        <a-input-search
          v-model:value="keyword"
          placeholder="搜索数字民警、技能、工具..."
          allow-clear
          class="explore-search"
          @search="load"
        />
        <a-button type="primary" class="publish-btn" @click="openPublish">
          ＋ 发布
        </a-button>
      </div>
    </div>

    <!-- 分类 Tabs -->
    <a-segmented
      v-model:value="activeType"
      :options="typeOptions"
      class="explore-tabs"
      @change="onTypeChange"
    />

    <!-- 最受欢迎（取数字民警前 3，简化横幅） -->
    <div v-if="hotAgents.length" class="hot-section">
      <h3 class="hot-title">🔥 最受欢迎方案</h3>
      <div class="hot-row">
        <div
          v-for="agent in hotAgents"
          :key="`hot-${agent.id}`"
          class="hot-card"
          @click="goDetail(agent)"
        >
          <div class="hot-avatar" :class="`bg-${agent.color_theme || 'blue'}`">
            <img :src="resolveAgentAvatar(agent)" :alt="agent.name" loading="lazy" />
          </div>
          <div class="hot-meta">
            <div class="hot-name">
              {{ agent.name }}
              <span class="hot-crown">👑</span>
            </div>
            <div class="hot-author">作者 · {{ agent.badge_number || '小南官方' }}</div>
            <div class="hot-stats">
              <span>使用 {{ workCount(agent) }}</span>
              <span class="hot-rating">★★★★★</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 资产卡片网格 -->
    <div v-if="loading" class="explore-loading">
      <a-spin tip="加载市场中..." />
    </div>

    <a-empty
      v-else-if="!items.length"
      description="暂无相关资产，去发布第一个数字民警吧"
    />

    <div v-else class="market-grid">
      <div v-for="item in items" :key="`${item.type}-${item.id}`" class="market-card">
        <div class="mc-head">
          <div class="mc-avatar" :class="`bg-${avatarTheme(item)}`">
            <img :src="assetAvatar(item)" :alt="item.name" loading="lazy" />
          </div>
          <div class="mc-head-info">
            <div class="mc-name" :title="item.name">{{ item.name }}</div>
            <div class="mc-author">{{ item.author }}</div>
          </div>
          <a-tag class="mc-type" :color="typeColor(item.type)">{{ typeLabel(item.type) }}</a-tag>
        </div>

        <div class="mc-desc">{{ item.description || '暂无简介' }}</div>

        <div class="mc-tags">
          <a-tag v-for="tag in (item.tags || []).slice(0, 3)" :key="tag" class="mc-tag">
            {{ tag }}
          </a-tag>
          <span v-if="item.category" class="mc-cat">{{ item.category }}</span>
        </div>

        <div class="mc-foot">
          <div class="mc-stats">
            <span>使用 {{ item.stats?.usage ?? 0 }}</span>
            <span class="mc-rate">★ {{ item.stats?.rating ?? 0 }}</span>
          </div>
          <a-button
            size="small"
            :type="appliedSet.has(markKey(item)) ? 'default' : 'primary'"
            :disabled="appliedSet.has(markKey(item))"
            @click="handleApply(item)"
          >
            {{ buttonLabel(item) }}
          </a-button>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="total > pageSize" class="explore-pager">
      <a-pagination
        v-model:current="page"
        :total="total"
        :page-size="pageSize"
        :show-size-changer="false"
        size="small"
        @change="load"
      />
    </div>

    <!-- 发布抽屉 -->
    <MarketPublishDrawer v-model:open="publishOpen" @published="onPublished" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { policeMarketApi, policeAgentApi, policeConnectionApi } from '@/apis/police_api'
import { resolveAgentAvatar, getOfficerAvatar } from '@/utils/policeAvatar'
import MarketPublishDrawer from '@/components/police/MarketPublishDrawer.vue'

const items = ref([])
const hotAgents = ref([])
const loading = ref(false)
const keyword = ref('')
const activeType = ref('all')
const page = ref(1)
const pageSize = 50
const total = ref(0)
const publishOpen = ref(false)
const appliedSet = ref(new Set())

const typeOptions = [
  { label: '全部', value: 'all' },
  { label: '数字民警', value: 'agent' },
  { label: '协助伙伴', value: 'partner' },
  { label: '技能模板', value: 'template' },
]

const typeLabel = (t) =>
  ({ agent: '数字民警', partner: '协助伙伴', template: '技能模板' }[t] || t)
const typeColor = (t) =>
  ({ agent: 'blue', partner: 'purple', template: 'green' }[t] || 'default')

const markKey = (item) => `${item.type}-${item.id}`
const buttonLabel = (item) =>
  item.apply_mode === 'connect'
    ? (appliedSet.value.has(markKey(item)) ? '已连接' : '申请使用')
    : item.apply_mode === 'equip_guided'
      ? (appliedSet.value.has(markKey(item)) ? '已关注' : '关注使用')
      : '选用模板'

const avatarTheme = (item) =>
  ({ agent: 'blue', partner: 'purple', template: 'green' }[item.type] || 'blue')

const assetAvatar = (item) => {
  if (item.type === 'template') return getOfficerAvatar(item.id)
  return resolveAgentAvatar({ id: item.id, name: item.name, icon: item.avatar })
}

function workCount(agent) {
  const s = agent.work_stats || {}
  return s.tasks_completed ?? s.cases_handled ?? 0
}

async function load() {
  loading.value = true
  try {
    const res = await policeMarketApi.explore({
      type: activeType.value,
      keyword: keyword.value || undefined,
      page: page.value,
      page_size: pageSize,
    })
    items.value = res.items || []
    total.value = res.total || 0
    // 已连接/已关注标记：数字民警来自连接列表
    if (activeType.value === 'all' || activeType.value === 'agent') {
      const conns = await policeConnectionApi.list()
      appliedSet.value = new Set(
        (conns.items || []).filter((c) => c.agent).map((c) => `agent-${c.agent.id}`)
      )
    }
  } catch (e) {
    message.error('加载市场失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

async function loadHot() {
  try {
    const res = await policeAgentApi.list({ page: 1, page_size: 5 })
    hotAgents.value = (res.items || []).slice(0, 3)
  } catch {
    hotAgents.value = []
  }
}

function onTypeChange() {
  page.value = 1
  load()
}

async function handleApply(item) {
  try {
    const res = await policeMarketApi.apply(item.type, item.id)
    appliedSet.value.add(markKey(item))
    message.success(res?.message || '操作成功')
  } catch (e) {
    message.error('申请失败: ' + (e.message || e))
  }
}

function goDetail(agent) {
  // 数字民警详情跳转档案页
  window.location.href = `/police/officers/${agent.id}`
}

function openPublish() {
  publishOpen.value = true
}

function onPublished() {
  message.success('已进入审核，通过后将在市场可见')
  load()
}

onMounted(() => {
  load()
  loadHot()
})
</script>

<style scoped>
.explore-view {
  padding: var(--page-padding);
  max-width: 1280px;
  margin: 0 auto;
}

.explore-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 18px;
}
.explore-title {
  display: flex;
  gap: 14px;
  align-items: center;
}
.explore-emoji {
  font-size: 36px;
  filter: drop-shadow(0 2px 4px var(--shadow-1));
}
.explore-title h2 {
  margin: 0;
  font-size: 22px;
  color: #1a365d;
  font-weight: 700;
}
.explore-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--gray-600);
}
.explore-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}
.explore-search {
  width: 240px;
}
.publish-btn {
  background: #1a365d;
  border-color: #1a365d;
}

.explore-tabs {
  background: var(--gray-100);
  border-radius: 8px;
  margin-bottom: 20px;
}

/* 最受欢迎 */
.hot-section {
  margin-bottom: 22px;
}
.hot-title {
  font-size: 15px;
  color: #1a365d;
  margin: 0 0 12px;
}
.hot-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
}
.hot-card {
  display: flex;
  gap: 12px;
  align-items: center;
  background: linear-gradient(135deg, #1a365d 0%, #2b6cb0 100%);
  border-radius: 16px;
  padding: 14px;
  cursor: pointer;
  transition: transform 0.18s ease;
}
.hot-card:hover {
  transform: translateY(-3px);
}
.hot-avatar {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  overflow: hidden;
  background: #fff;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.hot-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.hot-meta {
  min-width: 0;
}
.hot-name {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hot-crown {
  font-size: 12px;
}
.hot-author {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.75);
  margin-top: 2px;
}
.hot-stats {
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.85);
  margin-top: 4px;
}
.hot-rating {
  color: #fbbf24;
}

/* 卡片网格 */
.explore-loading {
  display: flex;
  justify-content: center;
  padding: 80px 0;
}
.market-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.market-card {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 4px 16px rgba(16, 30, 54, 0.06);
  border: 1px solid var(--gray-150);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.mc-head {
  display: flex;
  gap: 10px;
  align-items: center;
}
.mc-avatar {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.bg-blue { background: linear-gradient(135deg, #2b6cb0, #3182ce); }
.bg-purple { background: linear-gradient(135deg, #6b46c1, #805ad5); }
.bg-green { background: linear-gradient(135deg, #2f855a, #38a169); }
.mc-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.mc-head-info {
  flex: 1;
  min-width: 0;
}
.mc-name {
  font-size: 15px;
  font-weight: 600;
  color: #1a202c;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.mc-author {
  font-size: 11px;
  color: var(--gray-500);
  margin-top: 2px;
}
.mc-type {
  margin: 0;
  flex-shrink: 0;
}
.mc-desc {
  font-size: 13px;
  color: var(--gray-700);
  line-height: 1.5;
  min-height: 38px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.mc-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  min-height: 24px;
}
.mc-tag {
  font-size: 11px;
  border-radius: 8px;
  background: var(--gray-100);
  color: var(--gray-700);
  border: none;
  margin: 0;
}
.mc-cat {
  font-size: 11px;
  color: var(--gray-500);
}
.mc-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px dashed var(--gray-200);
  padding-top: 10px;
}
.mc-stats {
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: var(--gray-500);
}
.mc-rate {
  color: #b7791f;
}
.explore-pager {
  display: flex;
  justify-content: center;
  margin-top: 22px;
}
</style>
