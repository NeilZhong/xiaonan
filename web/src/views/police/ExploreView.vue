<template>
  <div class="xn-explore">
    <!-- 顶部 Hero（悟帆式发现区） -->
    <section class="xe-hero">
      <div class="xe-hero-glow" />
      <div class="xe-hero-inner">
        <div class="xe-hero-head">
          <h1 class="xe-hero-title">探索市场</h1>
          <p class="xe-hero-tagline">连接一切能力 · 协同每一次办案</p>
        </div>
        <p class="xe-hero-sub">
          浏览并申请数字民警、协助伙伴与侦查模板，把经过验证的能力一键装进你的工作流。
        </p>
        <div class="xe-chips">
          <button
            v-for="u in useCases"
            :key="u"
            type="button"
            class="xe-chip"
            :title="u"
            @click="startChat(u)"
          >
            <span class="xe-chip-text">{{ u }}</span>
            <span class="xe-chip-icon"><ArrowUpRight :size="13" /></span>
          </button>
        </div>
      </div>
    </section>

    <!-- 工具条：分类 Tab + 搜索 + 发布 -->
    <div class="xe-toolbar">
      <a-segmented
        v-model:value="activeType"
        :options="typeOptions"
        class="xe-tabs"
        @change="onTypeChange"
      />
      <div class="xe-toolbar-right">
        <a-input-search
          v-model:value="keyword"
          placeholder="搜索数字民警、技能、工具..."
          allow-clear
          class="xe-search"
          @search="onSearch"
        />
        <a-button type="primary" class="xe-publish" @click="openPublish">
          <template #icon><Plus :size="14" /></template>
          发布
        </a-button>
      </div>
    </div>

    <!-- 资产卡片网格 -->
    <div v-if="loading" class="xe-loading">
      <a-spin tip="加载市场中..." />
    </div>

    <a-empty
      v-else-if="!items.length"
      description="暂无相关资产，去发布第一个数字民警吧"
    />

    <div v-else class="xe-grid">
      <div v-for="item in items" :key="`${item.type}-${item.id}`" class="xe-card xe-clickable" @click="openDetail(item)">
        <div class="xe-card-top">
          <div class="xe-avatar" :class="`bg-${avatarTheme(item)}`">
            <img :src="assetAvatar(item)" :alt="item.name" loading="lazy" />
          </div>
          <div class="xe-card-head">
            <div class="xe-name" :title="item.name">{{ item.name }}</div>
            <div class="xe-author">{{ item.author || item.badge_number || '小南官方' }}</div>
          </div>
          <a-tag class="xe-type" :color="typeColor(item.type)">{{ typeLabel(item.type) }}</a-tag>
        </div>

        <div class="xe-desc">{{ item.description || '暂无简介' }}</div>

        <div v-if="(item.tags && item.tags.length) || item.category" class="xe-tags">
          <a-tag v-for="tag in (item.tags || []).slice(0, 3)" :key="tag" class="xe-tag">{{ tag }}</a-tag>
          <span v-if="item.category" class="xe-cat">{{ item.category }}</span>
        </div>

        <div class="xe-foot">
          <div class="xe-stats">
            <span>使用 {{ item.stats?.usage ?? 0 }}</span>
            <span class="xe-rate">★ {{ item.stats?.rating ?? 0 }}</span>
          </div>
          <a-button
            size="small"
            :type="appliedSet.has(markKey(item)) ? 'default' : 'primary'"
            :disabled="appliedSet.has(markKey(item))"
            @click.stop="handleApply(item)"
          >
            {{ actionLabel(item) }}
          </a-button>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="total > pageSize && !loading" class="xe-pager">
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

    <!-- 资产详情弹窗（悟帆式结构，适配小南浅色品牌） -->
    <transition name="xe-fade">
      <div v-if="detailOpen" class="xe-overlay" @click.self="closeDetail">
        <div class="xe-modal" role="dialog" aria-modal="true">
          <button class="xe-modal-close" aria-label="关闭" @click="closeDetail">
            <X :size="14" />
          </button>

          <!-- 顶部 Hero（品牌色渐变） -->
          <div class="xe-modal-hero">
            <div class="xe-hero-row">
              <span class="xe-creator">
                <span class="xe-creator-avatar">
                  <img v-if="detailView.icon" :src="detailView.icon" :alt="detailView.author" />
                  <span v-else>{{ (detailView.author || '?').slice(0, 1) }}</span>
                </span>
                <span class="xe-creator-name">{{ detailView.author }}</span>
              </span>
              <span class="xe-type-pill">{{ typeLabel(detailView.type) }}</span>
            </div>
            <div class="xe-hero-title">{{ detailView.name }}</div>
            <p class="xe-hero-desc">{{ detailView.description || '暂无简介' }}</p>
          </div>

          <!-- 操作栏 -->
          <div class="xe-modal-actions">
            <div class="xe-modal-actions-left">
              <a-button
                v-if="detailView.type === 'agent'"
                class="xe-ghost-btn"
                @click="enterChat(detailView)"
              >
                <template #icon><Eye :size="14" /></template>
                进入对话
              </a-button>
            </div>
            <div class="xe-modal-actions-right">
              <a-button
                v-if="!appliedSet.has(markKey(detailView))"
                type="primary"
                :loading="applying"
                @click.stop="handleApply(detailView)"
              >{{ actionLabel(detailView) }}</a-button>
              <a-button v-else disabled>{{ appliedText(detailView) }}</a-button>
              <a-button class="xe-icon-btn" @click="shareAsset" aria-label="分享">
                <template #icon><Share2 :size="14" /></template>
              </a-button>
            </div>
          </div>

          <div class="xe-divider" />

          <!-- 介绍 -->
          <div class="xe-modal-body" v-if="detailData || selectedItem">
            <h4 class="xe-section-title">介绍</h4>
            <div class="xe-intro">
              <p v-if="detailView.systemPrompt" class="xe-intro-text">{{ detailView.systemPrompt }}</p>
              <p v-else-if="detailView.description" class="xe-intro-text">{{ detailView.description }}</p>
              <p v-else class="xe-muted">该资产暂未填写详细介绍。</p>
            </div>
            <div v-if="detailView.tags && detailView.tags.length" class="xe-tags">
              <a-tag v-for="t in detailView.tags" :key="t" class="xe-tag">{{ t }}</a-tag>
            </div>

            <!-- 评价 -->
            <h4 class="xe-section-title xe-review-title">
              评价 <span class="xe-review-count">({{ reviewTotal }})</span>
              <span v-if="detailView.stats && detailView.stats.rating" class="xe-review-stats">
                ★ {{ detailView.stats.rating }}
                <span class="xe-muted">· {{ detailView.stats.usage || 0 }} 次使用</span>
              </span>
            </h4>

            <template v-if="detailView.type === 'agent'">
              <div v-if="reviews.length" class="xe-review-list">
                <div v-for="r in reviews" :key="r.id" class="xe-review">
                  <div class="xe-review-avatar">{{ (r.user_name || '?').slice(0, 1) }}</div>
                  <div class="xe-review-main">
                    <div class="xe-review-head">
                      <span class="xe-review-name">{{ r.user_name || '匿名用户' }}</span>
                      <span v-if="r.rating" class="xe-review-stars">
                        <Star v-for="n in r.rating" :key="n" :size="11" class="xe-star-on" />
                      </span>
                    </div>
                    <p class="xe-review-content">{{ r.content }}</p>
                    <div class="xe-review-date">{{ formatDate(r.created_at) }}</div>
                  </div>
                </div>
              </div>
              <div v-else class="xe-empty">暂无评价，快来抢沙发</div>

              <div class="xe-review-form">
                <div class="xe-review-input">
                  <button
                    v-for="n in 5" :key="n"
                    type="button"
                    class="xe-star-btn"
                    :class="{ on: reviewRating >= n }"
                    :aria-label="`${n} 星`"
                    @click="reviewRating = n"
                  ><Star :size="16" /></button>
                  <span class="xe-muted xe-review-hint">{{ reviewRating ? reviewRating + ' 星' : '点击打分' }}</span>
                </div>
                <a-textarea
                  v-model:value="reviewText"
                  placeholder="说说你的使用体验（选填）"
                  :rows="3"
                  class="xe-review-textarea"
                />
                <div class="xe-review-submit">
                  <a-button
                    type="primary"
                    size="small"
                    :disabled="!reviewText.trim() || submittingReview"
                    :loading="submittingReview"
                    @click="submitReview"
                  >提交</a-button>
                </div>
              </div>
            </template>
            <p v-else class="xe-muted xe-review-disabled">该类型资产暂未开放评价。</p>

            <div class="xe-meta">
              <span>{{ detailView.category }}</span>
              <span class="xe-dot">·</span>
              <span>发布于 {{ formatDate(detailView.createdAt) }}</span>
            </div>
          </div>
          <div v-else class="xe-modal-loading">
            <a-spin tip="加载详情中..." />
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { ArrowUpRight, Plus, Eye, Share2, X, Star } from 'lucide-vue-next'
import { policeMarketApi, policeAgentApi, policeConnectionApi } from '@/apis/police_api'
import { resolveAgentAvatar, getOfficerAvatar } from '@/utils/policeAvatar'
import MarketPublishDrawer from '@/components/police/MarketPublishDrawer.vue'

const router = useRouter()

const items = ref([])
const loading = ref(false)
const keyword = ref('')
const activeType = ref('all')
const page = ref(1)
const pageSize = 50
const total = ref(0)
const publishOpen = ref(false)
const appliedSet = ref(new Set())

// 资产详情弹窗
const detailOpen = ref(false)
const selectedItem = ref(null)
const detailData = ref(null)
const applying = ref(false)
const reviews = ref([])
const reviewTotal = ref(0)
const reviewText = ref('')
const reviewRating = ref(0)
const submittingReview = ref(false)

// 悟帆式推荐用例：点击进入对话（/agent），把用例作为初始提示词
const useCases = [
  '笔录结构化分析，提取关键要素与矛盾点',
  '根据案情生成初查提纲与取证清单',
  '梳理证据链，标注缺失与薄弱环节',
  '起草询问 / 讯问提纲',
  '生成案件复盘报告要点',
  '对比类案裁判要点',
]

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

const actionLabel = (item) => {
  if (appliedSet.value.has(markKey(item))) return '已申请'
  if (item.apply_mode === 'connect') return '申请使用'
  if (item.apply_mode === 'equip_guided') return '关注使用'
  return '选用模板'
}

const avatarTheme = (item) =>
  ({ agent: 'blue', partner: 'purple', template: 'green' }[item.type] || 'blue')

const assetAvatar = (item) => {
  if (item.type === 'template') return getOfficerAvatar(item.id)
  return resolveAgentAvatar({ id: item.id, name: item.name, icon: item.avatar })
}

function startChat(useCase) {
  // 进入对话页，把用例作为初始提示词（best-effort：依赖 AgentView 读取 query.prompt）
  router.push({ path: '/agent', query: { prompt: useCase } })
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
    // 已申请标记：数字民警来自连接列表
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

function onTypeChange() {
  page.value = 1
  load()
}

function onSearch() {
  page.value = 1
  load()
}

async function handleApply(item) {
  if (applying.value) return
  applying.value = true
  try {
    const res = await policeMarketApi.apply(item.type, item.id)
    appliedSet.value.add(markKey(item))
    message.success(res?.message || '操作成功')
  } catch (e) {
    message.error('申请失败: ' + (e.message || e))
  } finally {
    applying.value = false
  }
}

const appliedText = (item) => {
  if (item.type === 'agent') return '已申请'
  if (item.type === 'partner') return '已关注'
  return '已选用'
}

// 弹窗视图：以卡片(item) 为基础，叠加详情(detail) 的真实字段
const detailView = computed(() => {
  const base = selectedItem.value || {}
  const d = detailData.value || {}
  const type = base.type || d.type || 'agent'
  const baseTags = base.tags || []
  const dCaps = d.capabilities || []
  return {
    id: base.id ?? d.id,
    type,
    name: base.name || d.name || '',
    description: base.description || d.description || '',
    systemPrompt: d.system_prompt || '',
    category: base.category || d.category || (type === 'partner' ? '协助伙伴' : type === 'template' ? '任务模板' : '数字民警'),
    author: base.author || d.badge_number || d.author || '小南官方',
    icon: base.icon || base.avatar || d.icon || '',
    tags: dCaps.length ? dCaps : baseTags,
    stats: d.stats || base.stats || { usage: 0, rating: 0, review_count: 0 },
    slug: d.slug || base.slug,
    createdAt: base.created_at || d.created_at || '',
  }
})

async function openDetail(item) {
  selectedItem.value = item
  detailData.value = null
  reviews.value = []
  reviewTotal.value = 0
  reviewText.value = ''
  reviewRating.value = 0
  detailOpen.value = true
  try {
    detailData.value = await policeMarketApi.detail(item.type, item.id)
  } catch (e) {
    // 详情拉取失败时仍用卡片基础字段渲染
    console.warn('加载资产详情失败', e)
  }
  if (item.type === 'agent') loadReviews()
}

function closeDetail() {
  detailOpen.value = false
}

function enterChat(item) {
  // best-effort：进入对话页并带上智能体标识（依赖 AgentView 读取 query.agent）
  router.push({ path: '/agent', query: { agent: item.slug || item.id } })
}

async function shareAsset() {
  const url = `${location.origin}/police/explore?asset=${detailView.value.type}-${detailView.value.id}`
  try {
    await navigator.clipboard.writeText(url)
    message.success('链接已复制，可分享给同事')
  } catch {
    message.info('分享链接：' + url)
  }
}

async function loadReviews() {
  const id = detailView.value.id
  if (id == null) return
  try {
    const res = await policeAgentApi.listComments(id)
    reviews.value = res?.items || []
    reviewTotal.value = res?.total || 0
  } catch (e) {
    reviews.value = []
  }
}

async function submitReview() {
  const id = detailView.value.id
  if (!reviewText.value.trim() || submittingReview.value) return
  submittingReview.value = true
  try {
    await policeAgentApi.createComment(id, reviewText.value.trim(), reviewRating.value || null)
    message.success('评价已提交')
    reviewText.value = ''
    reviewRating.value = 0
    await loadReviews()
  } catch (e) {
    message.error('提交失败: ' + (e.message || e))
  } finally {
    submittingReview.value = false
  }
}

function formatDate(s) {
  if (!s) return '未知'
  const d = new Date(s)
  if (isNaN(d.getTime())) return s
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
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
})
</script>

<style scoped lang="less">
.xn-explore {
  padding: var(--page-padding);
  max-width: 1280px;
  margin: 0 auto;
}

/* ===== Hero（悟帆式发现区） ===== */
.xe-hero {
  position: relative;
  overflow: hidden;
  border-radius: 18px;
  padding: 28px 30px;
  margin-bottom: 20px;
  background: linear-gradient(120deg, rgba(46, 109, 206, 0.10), rgba(46, 109, 206, 0.03));
  border: 1px solid var(--gray-150);
}
.xe-hero-glow {
  position: absolute;
  top: -120px;
  right: -80px;
  width: 320px;
  height: 320px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(46, 109, 206, 0.18) 0%, transparent 70%);
  pointer-events: none;
}
.xe-hero-inner {
  position: relative;
}
.xe-hero-head {
  display: flex;
  align-items: baseline;
  gap: 14px;
  flex-wrap: wrap;
}
.xe-hero-title {
  margin: 0;
  font-size: 26px;
  font-weight: 800;
  color: var(--color-accent-700, #174591);
  letter-spacing: 0.5px;
}
.xe-hero-tagline {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-accent-500, #2e6dce);
}
.xe-hero-sub {
  margin: 10px 0 16px;
  max-width: 640px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--gray-600);
}
.xe-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.xe-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  max-width: 320px;
  padding: 8px 12px 8px 14px;
  font-size: 12.5px;
  line-height: 1.4;
  color: var(--gray-800);
  background: var(--gray-0, #fff);
  border: 1px solid var(--gray-200);
  border-radius: 999px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s, transform 0.12s;
}
.xe-chip:hover {
  color: var(--color-accent-700, #174591);
  border-color: var(--color-accent-500, #2e6dce);
  background: rgba(46, 109, 206, 0.04);
  transform: translateY(-1px);
}
.xe-chip-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.xe-chip-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--gray-100);
  color: var(--gray-600);
  flex-shrink: 0;
  transition: background 0.15s, color 0.15s;
}
.xe-chip:hover .xe-chip-icon {
  background: var(--color-accent-500, #2e6dce);
  color: #fff;
}

/* ===== 工具条 ===== */
.xe-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 18px;
}
.xe-tabs {
  background: var(--gray-100);
  border-radius: 8px;
}
.xe-toolbar-right {
  display: flex;
  gap: 10px;
  align-items: center;
}
.xe-search {
  width: 260px;
}
.xe-publish {
  background: var(--color-accent-700, #174591);
  border-color: var(--color-accent-700, #174591);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* ===== 卡片网格 ===== */
.xe-loading {
  display: flex;
  justify-content: center;
  padding: 80px 0;
}
.xe-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.xe-card {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 4px 16px rgba(16, 30, 54, 0.06);
  border: 1px solid var(--gray-150);
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.xe-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 10px 28px rgba(16, 30, 54, 0.12);
}
.xe-card-top {
  display: flex;
  gap: 10px;
  align-items: center;
}
.xe-avatar {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
}
.bg-blue { background: linear-gradient(135deg, #2b6cb0, #3182ce); }
.bg-purple { background: linear-gradient(135deg, #6b46c1, #805ad5); }
.bg-green { background: linear-gradient(135deg, #2f855a, #38a169); }
.xe-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.xe-card-head {
  flex: 1;
  min-width: 0;
}
.xe-name {
  font-size: 15px;
  font-weight: 600;
  color: #1a202c;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.xe-author {
  font-size: 11px;
  color: var(--gray-500);
  margin-top: 2px;
}
.xe-type {
  margin: 0;
  flex-shrink: 0;
}
.xe-desc {
  font-size: 13px;
  color: var(--gray-700);
  line-height: 1.5;
  min-height: 38px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.xe-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  min-height: 24px;
}
.xe-tag {
  font-size: 11px;
  border-radius: 8px;
  background: var(--gray-100);
  color: var(--gray-700);
  border: none;
  margin: 0;
}
.xe-cat {
  font-size: 11px;
  color: var(--gray-500);
}
.xe-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px dashed var(--gray-200);
  padding-top: 10px;
}
.xe-stats {
  display: flex;
  gap: 10px;
  font-size: 11px;
  color: var(--gray-500);
}
.xe-rate {
  color: #b7791f;
}
.xe-pager {
  display: flex;
  justify-content: center;
  margin-top: 22px;
}

/* ===== 详情弹窗（悟帆式，浅色品牌） ===== */
.xe-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.44);
  padding: 20px;
}
.xe-modal {
  position: relative;
  width: 880px;
  max-width: 94vw;
  max-height: 820px;
  border-radius: 20px;
  background: var(--gray-0, #fff);
  border: 1px solid var(--gray-200);
  box-shadow: 0 8px 40px rgba(16, 30, 54, 0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.xe-modal-close {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 20;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  color: #fff;
  background: rgba(15, 23, 42, 0.42);
  transition: background 0.15s;
}
.xe-modal-close:hover {
  background: rgba(15, 23, 42, 0.6);
}
.xe-modal-hero {
  position: relative;
  min-height: 200px;
  padding: 22px 28px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: linear-gradient(135deg, #174591 0%, #2e6dce 55%, #4f8fe0 100%);
  color: #fff;
}
.xe-hero-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.xe-creator {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px 4px 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
  backdrop-filter: blur(6px);
  font-size: 12px;
  color: #fff;
}
.xe-creator-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.3);
  font-size: 11px;
  font-weight: 600;
}
.xe-creator-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.xe-creator-name {
  white-space: nowrap;
}
.xe-type-pill {
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(6px);
  font-size: 11px;
  color: #fff;
}
.xe-hero-title {
  font-size: 26px;
  font-weight: 800;
  letter-spacing: 0.3px;
  line-height: 1.25;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
}
.xe-hero-desc {
  margin: 8px 0 0;
  font-size: 13.5px;
  line-height: 1.55;
  color: rgba(255, 255, 255, 0.9);
  max-width: 560px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.xe-modal-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 14px 28px;
}
.xe-modal-actions-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.xe-ghost-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.xe-icon-btn {
  width: 38px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.xe-divider {
  height: 1px;
  background: var(--gray-150);
  margin: 0 28px;
}
.xe-modal-body {
  padding: 18px 28px 24px;
  overflow-y: auto;
}
.xe-modal-loading {
  padding: 60px 0;
  display: flex;
  justify-content: center;
}
.xe-section-title {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--gray-500);
  margin: 0 0 12px;
}
.xe-intro-text {
  font-size: 13px;
  line-height: 1.7;
  color: var(--gray-700);
  white-space: pre-wrap;
  margin: 0 0 12px;
}
.xe-muted {
  color: var(--gray-500);
  font-size: 12px;
}
.xe-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}
.xe-tag {
  font-size: 11px;
  border-radius: 8px;
  background: var(--gray-100);
  color: var(--gray-700);
  border: none;
  margin: 0;
}
.xe-review-title {
  margin-top: 22px;
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.xe-review-count {
  color: var(--gray-400);
  font-weight: 600;
}
.xe-review-stats {
  font-size: 12px;
  color: var(--gray-600);
  font-weight: 600;
}
.xe-review-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}
.xe-review {
  display: flex;
  gap: 10px;
  background: var(--gray-50, #f7f9fc);
  border: 1px solid var(--gray-150);
  border-radius: 10px;
  padding: 12px;
}
.xe-review-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #6b7280, #4b5563);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
}
.xe-review-main {
  flex: 1;
  min-width: 0;
}
.xe-review-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.xe-review-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--gray-800);
}
.xe-review-stars {
  display: inline-flex;
  gap: 1px;
}
.xe-star-on {
  color: #f5a623;
  fill: #f5a623;
}
.xe-review-content {
  margin: 6px 0 4px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--gray-700);
}
.xe-review-date {
  font-size: 10.5px;
  color: var(--gray-400);
}
.xe-empty {
  font-size: 12px;
  color: var(--gray-400);
  padding: 14px 0;
  text-align: center;
  background: var(--gray-50, #f7f9fc);
  border-radius: 10px;
}
.xe-review-form {
  background: var(--gray-50, #f7f9fc);
  border: 1px solid var(--gray-150);
  border-radius: 10px;
  padding: 12px;
}
.xe-review-input {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 8px;
}
.xe-star-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--gray-300);
  padding: 2px;
  line-height: 0;
  transition: color 0.12s;
}
.xe-star-btn.on {
  color: #f5a623;
  fill: #f5a623;
}
.xe-star-btn:hover {
  color: #f5a623;
}
.xe-review-hint {
  margin-left: 6px;
}
.xe-review-textarea {
  margin-bottom: 8px;
}
.xe-review-submit {
  display: flex;
  justify-content: flex-end;
}
.xe-review-disabled {
  margin-top: 12px;
}
.xe-meta {
  margin-top: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  color: var(--gray-500);
  border-top: 1px solid var(--gray-150);
  padding-top: 12px;
}
.xe-dot {
  opacity: 0.5;
}
.xe-clickable {
  cursor: pointer;
}
.xe-fade-enter-active,
.xe-fade-leave-active {
  transition: opacity 0.18s ease;
}
.xe-fade-enter-from,
.xe-fade-leave-to {
  opacity: 0;
}
</style>
