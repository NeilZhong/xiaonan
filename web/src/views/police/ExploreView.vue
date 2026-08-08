<template>
  <div class="xn-explore">
    <!-- ===== 1. 顶部分类与搜索栏 ===== -->
    <div class="xe-toolbar">
      <div class="xe-pills">
        <button
          v-for="p in pills"
          :key="p.value"
          type="button"
          class="xe-pill"
          :class="{ active: activeType === p.value }"
          @click="onPill(p.value)"
        >
          {{ p.label }}
        </button>
      </div>
      <div class="xe-right">
        <a-select
          v-if="activeType === 'partner'"
          v-model:value="categoryFilter"
          placeholder="按功能分类筛选"
          allow-clear
          class="xe-category-filter"
          :options="CATEGORY_OPTIONS"
          @change="onCategoryChange"
        />
        <a-input-search
          v-model:value="keyword"
          placeholder="搜索数字民警、技能、工具..."
          allow-clear
          class="xe-search"
          @search="onSearch"
        />
        <button type="button" class="xe-publish" @click="openPublish">
          <Plus :size="14" /> 发布
        </button>
      </div>
    </div>

    <!-- ===== 加载 / 空态 ===== -->
    <div v-if="loading" class="xe-loading">
      <a-spin tip="加载市场中..." />
    </div>
    <a-empty
      v-else-if="!showHero && !digitalOfficers.length && !partnerOfficers.length && !skillRows.length && !comingSoon"
      :description="activeType === 'all' ? '暂无相关资产，去发布第一个数字民警吧' : '该分类暂无内容'"
    />

    <!-- ===== 2. 本周 / 本月 · 最受欢迎（Hero 展位） ===== -->
    <section v-if="showHero && featured.length" class="xe-feature">
      <div class="xe-eyebrow-row">
        <div class="xe-eyebrow">🔥 最受欢迎</div>
        <a-segmented
          v-model:value="trendPeriod"
          :options="trendOptions"
          size="small"
          class="xe-trend-switch"
        />
      </div>
      <div class="xe-banner">
        <div
          v-for="(f, i) in featured"
          :key="`feat-${f.type}-${f.id}`"
          class="xe-hero-card"
          :class="gradientClass(i)"
          @click="openDetail(f)"
        >
          <!-- 皇冠：仅排名第一 -->
          <div v-if="i === 0" class="xe-crown-svg" aria-hidden="true">
            <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: rgb(253, 230, 138); fill: rgb(251, 191, 36);">
              <path d="M11.562 3.266a.5.5 0 0 1 .876 0L15.39 8.87a1 1 0 0 0 1.516.294L21.183 5.5a.5.5 0 0 1 .798.519l-2.834 10.246a1 1 0 0 1-.956.734H5.81a1 1 0 0 1-.957-.734L2.02 6.02a.5.5 0 0 1 .798-.519l4.276 3.664a1 1 0 0 0 1.516-.294z"></path>
              <path d="M5 21h14"></path>
            </svg>
          </div>
          <div class="xe-hero-shade" />
          <div class="xe-hero-content">
            <h3 class="xe-hero-title">{{ f.name }}</h3>
            <p class="xe-hero-desc">{{ f.description || '经过实战验证的高质效能力，点击查看详情' }}</p>
            <div class="xe-hero-author">
              <span class="xe-author-av">{{ initial(f.author) }}</span>
              <span class="xe-author-name">{{ f.author }}</span>
              <span class="xe-author-meta">★ {{ ratingText(f) }} · ↓ {{ f.stats?.usage ?? 0 }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== 3a. 数字警员模块（横向 Swipe 滑动） ===== -->
    <section v-if="showDigitalOfficers" class="xe-section">
      <header class="xe-sec-head">
        <h2 class="xe-sec-title">{{ digitalSectionTitle }}</h2>
        <a class="xe-sec-more" @click="onPill('agent')">查看全部 →</a>
      </header>
      <div
        class="swipe-container"
        @pointerdown="onSwipeDown"
        @pointermove="onSwipeMove"
        @pointerup="onSwipeUp"
        @pointerleave="onSwipeUp"
      >
        <div
          v-for="(item, i) in digitalOfficers"
          :key="`${item.type}-${item.id}`"
          class="swipe-item xe-officer-card"
          :class="gradientClass(i)"
          @click="onOfficerClick(item)"
        >
          <span class="xe-officer-badge">{{ typeLabel(item.type) }}</span>
          <div class="xe-officer-main">
            <div class="xe-officer-avatar">{{ initial(item.name) }}</div>
            <div class="xe-officer-name" :title="item.name">{{ item.name }}</div>
            <div class="xe-officer-desc" :title="item.description">{{ item.description || '暂无简介' }}</div>
          </div>
          <div class="xe-officer-foot">
            <span class="xe-meta"><Download :size="12" /> {{ item.stats?.usage ?? 0 }}</span>
            <span class="xe-meta xe-star">★ {{ ratingText(item) }}</span>
            <span class="xe-meta xe-time">{{ relativeTime(item.created_at) }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== 4. 技能 / 工具 / MCP / 卡片 · 开箱即用模块 ===== -->
    <section v-if="showSkills" class="xe-section">
      <header class="xe-sec-head">
        <h2 class="xe-sec-title">{{ skillSectionTitle }}</h2>
        <a class="xe-sec-more" @click="onPill('skill')">查看全部 →</a>
      </header>
      <div v-if="skillRows.length" class="xe-list">
        <div v-for="row in skillRows" :key="row.key" class="xe-row" @click="openSkillDetail(row)">
          <div class="xe-row-icon">
            <span v-if="isEmoji(row.icon)">{{ row.icon }}</span>
            <component :is="row.iconComp" v-else :size="18" />
          </div>
          <div class="xe-row-main">
            <div class="xe-row-title" :title="row.name">{{ row.name }}</div>
            <div class="xe-row-desc" :title="row.description">{{ row.description || '暂无描述' }}</div>
          </div>
          <div class="xe-row-action" @click.stop>
            <span v-if="row.installed" class="xe-installed">已安装</span>
            <button
              v-else
              type="button"
              class="xe-add"
              :disabled="row.pending"
              :title="'添加到当前空间'"
              @click="toggleRow(row)"
            >
              <Plus :size="13" />
            </button>
          </div>
        </div>
      </div>
      <a-empty v-else description="该分类市场内容建设中，敬请期待" />
    </section>

    <!-- ===== 5. 协助伙伴模块（样式与数字警员一致） ===== -->
    <section v-if="showPartnerOfficers" class="xe-section">
      <header class="xe-sec-head">
        <h2 class="xe-sec-title">{{ partnerSectionTitle }}</h2>
        <a class="xe-sec-more" @click="onPill('partner')">查看全部 →</a>
      </header>
      <div
        class="swipe-container"
        @pointerdown="onSwipeDown"
        @pointermove="onSwipeMove"
        @pointerup="onSwipeUp"
        @pointerleave="onSwipeUp"
      >
        <div
          v-for="(item, i) in partnerOfficers"
          :key="`${item.type}-${item.id}`"
          class="swipe-item xe-officer-card"
          :class="gradientClass(i)"
          @click="onOfficerClick(item)"
        >
          <span class="xe-officer-badge">{{ typeLabel(item.type) }}</span>
          <div class="xe-officer-main">
            <div class="xe-officer-avatar">{{ initial(item.name) }}</div>
            <div class="xe-officer-name" :title="item.name">{{ item.name }}</div>
            <div class="xe-officer-desc" :title="item.description">{{ item.description || '暂无简介' }}</div>
          </div>
          <div class="xe-officer-foot">
            <span class="xe-meta"><Download :size="12" /> {{ item.stats?.usage ?? 0 }}</span>
            <span class="xe-meta xe-star">★ {{ ratingText(item) }}</span>
            <span class="xe-meta xe-time">{{ relativeTime(item.created_at) }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ===== 发布抽屉 ===== -->
    <MarketPublishDrawer v-model:open="publishOpen" @published="onPublished" />

    <!-- ===== 资产详情弹窗（Hero 区为深色玻璃，跟随系统浅色主题） ===== -->
    <transition name="xe-fade">
      <div v-if="detailOpen" class="xe-overlay" @click.self="closeDetail">
        <div class="xe-modal" role="dialog" aria-modal="true">
          <button class="xe-modal-close" aria-label="关闭" @click="closeDetail">
            <X :size="14" />
          </button>

          <div class="xe-modal-hero gradient-card-blue">
            <div class="xe-hero-row">
              <span class="xe-creator">
                <span class="xe-creator-avatar">{{ initial(detailView.author) }}</span>
                <span class="xe-creator-name">{{ detailView.author }}</span>
              </span>
              <span class="xe-type-pill">{{ typeLabel(detailView.type) }}</span>
            </div>
            <div class="xe-hero-title">{{ detailView.name }}</div>
            <p class="xe-hero-desc">{{ detailView.description || '暂无简介' }}</p>
          </div>

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

          <div class="xe-modal-body" v-if="detailData || selectedItem">
            <h4 class="xe-section-title">介绍</h4>
            <div class="xe-intro">
              <p v-if="detailView.systemPrompt" class="xe-intro-text">{{ detailView.systemPrompt }}</p>
              <p v-else-if="detailView.description" class="xe-intro-text">{{ detailView.description }}</p>
              <p v-else class="xe-muted">该资产暂未填写详细介绍。</p>
            </div>
            <div v-if="detailView.tags && detailView.tags.length" class="xe-tags">
              <span v-for="t in detailView.tags" :key="t" class="xe-tag">{{ t }}</span>
            </div>

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
                  <div class="xe-review-avatar">{{ initial(r.user_name) }}</div>
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

    <!-- ===== ★ 技能/工具/MCP/卡片 详情弹窗 ===== -->
    <transition name="xe-fade">
      <div v-if="skillDetailOpen && skillDetailItem" class="xe-overlay" @click.self="closeSkillDetail">
        <div class="xe-modal" role="dialog" aria-modal="true">
          <button class="xe-modal-close" aria-label="关闭" @click="closeSkillDetail">
            <X :size="14" />
          </button>

          <div class="xe-modal-hero gradient-card-blue">
            <div class="xe-hero-row">
              <span class="xe-creator">
                <span class="xe-creator-avatar">{{ initial(skillDetailItem.author || skillDetailItem.created_by || '小南') }}</span>
                <span class="xe-creator-name">{{ skillDetailItem.author || skillDetailItem.created_by || '小南官方' }}</span>
              </span>
              <span class="xe-type-pill">{{ skillDetailItem.source || (skillDetailItem.source_type === 'builtin' ? '内置技能' : '通用技能') }}</span>
            </div>
            <div class="xe-hero-title">{{ skillDetailItem.name }}</div>
            <p class="xe-hero-desc">{{ skillDetailItem.description || '暂无简介' }}</p>
          </div>

          <div class="xe-modal-actions">
            <div class="xe-modal-actions-left">
              <span class="xe-meta-line">
                <span class="xe-dot-sep">版本</span> {{ skillDetailItem.version || '—' }}
              </span>
              <span v-if="skillDetailItem.installed" class="xe-installed xe-installed--lg">当前空间已安装</span>
              <button
                v-else
                type="button"
                class="xe-add xe-add--lg"
                :disabled="skillDetailItem.pending"
                @click="toggleRow(skillDetailItem)"
              >
                <Plus :size="14" /> 添加到当前空间
              </button>
            </div>
          </div>

          <div class="xe-divider" />

          <div class="xe-modal-body">
            <h4 class="xe-section-title">完整介绍</h4>
            <p class="xe-intro-text">{{ skillDetailItem.description || '该技能暂未填写详细介绍。' }}</p>

            <h4 class="xe-section-title xe-mt">依赖</h4>
            <div class="xe-deps">
              <span
                v-if="!(skillDetailItem.tool_dependencies || []).length && !(skillDetailItem.mcp_dependencies || []).length && !(skillDetailItem.skill_dependencies || []).length"
                class="xe-muted"
              >无外部依赖</span>
              <span
                v-for="t in skillDetailItem.tool_dependencies || []"
                :key="`tool-${t}`"
                class="xe-dep-chip xe-dep-tool"
              >工具 · {{ t }}</span>
              <span
                v-for="m in skillDetailItem.mcp_dependencies || []"
                :key="`mcp-${m}`"
                class="xe-dep-chip xe-dep-mcp"
              >MCP · {{ m }}</span>
              <span
                v-for="s in skillDetailItem.skill_dependencies || []"
                :key="`skill-${s}`"
                class="xe-dep-chip xe-dep-skill"
              >技能 · {{ s }}</span>
            </div>

            <div class="xe-meta">
              <span>目录：{{ skillDetailItem.dir_path || '—' }}</span>
              <span class="xe-dot">·</span>
              <span>更新于 {{ formatDate(skillDetailItem.updated_at || skillDetailItem.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  Plus, Eye, Share2, X, Star, Download, Box, Bot,
} from 'lucide-vue-next'
import { policeMarketApi, policeAgentApi, policeConnectionApi } from '@/apis/police_api'
import { skillApi } from '@/apis/skill_api'
import MarketPublishDrawer from '@/components/police/MarketPublishDrawer.vue'

const router = useRouter()

const items = ref([])
const loading = ref(false)
const keyword = ref('')
const activeType = ref('all')
const publishOpen = ref(false)
const appliedSet = ref(new Set())

// 技能横向列表（真实数据源）
const skills = ref([])
const officersLoaded = ref(false)
const skillsLoaded = ref(false)

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

// ★ 技能/工具/MCP/卡片详情弹窗（独立状态，避免与数字警员弹窗耦合）
const skillDetailOpen = ref(false)
const skillDetailItem = ref(null)

// 横向滑动容器与拖拽状态
const drag = reactive({ active: false, startX: 0, startScroll: 0, moved: false, el: null })

const pills = [
  { label: '全部', value: 'all' },
  { label: '数字民警', value: 'agent' },
  { label: '技能', value: 'skill' },
  { label: '工具', value: 'tool' },
  { label: 'MCP', value: 'mcp' },
  { label: '卡片', value: 'card' },
  { label: '协助伙伴', value: 'partner' },
]

// P5：本周 / 本月 切换（默认本周）
const trendPeriod = ref('week')
const trendOptions = [
  { label: '本周', value: 'week' },
  { label: '本月', value: 'month' },
]

// P5：协助伙伴按功能分类筛选（与数字警员管理页 AGENT_CATEGORIES 一致）
const CATEGORY_OPTIONS = [
  { value: 'case_analysis', label: '案件分析' },
  { value: 'fund_tracking', label: '资金追踪' },
  { value: 'intelligence', label: '情报研判' },
  { value: 'evidence_mgmt', label: '调证取证' },
  { value: 'legal_review', label: '法制审核' },
  { value: 'interrogation', label: '审讯辅助' },
  { value: 'image_recon', label: '图像侦查' },
  { value: 'anti_fraud', label: '反诈劝阻' },
  { value: 'command', label: '指挥调度' },
  { value: 'partner_generic', label: '通用协助' },
]
const categoryFilter = ref('')

const GRADIENTS = ['gradient-card-blue', 'gradient-card-purple', 'gradient-card-emerald', 'gradient-card-dark']
const gradientClass = (i) => GRADIENTS[((i % 4) + 4) % 4]

// 区块可见性
const showHero = computed(() => activeType.value === 'all')
const showOfficers = computed(() => ['all', 'agent', 'partner'].includes(activeType.value))
const showSkills = computed(() => ['all', 'skill', 'tool', 'mcp', 'card'].includes(activeType.value))

// 数字警员卡片（仅数字民警）
const digitalOfficers = computed(() => {
  const want = activeType.value
  if (want === 'partner') return []
  return items.value.filter((it) => it.type === 'agent')
})

// 协助伙伴卡片（样式与数字警员一致）
const partnerOfficers = computed(() => {
  const want = activeType.value
  if (want === 'agent') return []
  return items.value.filter((it) => it.type === 'partner')
})

// 数字警员区块可见性
const showDigitalOfficers = computed(() => ['all', 'agent'].includes(activeType.value) && digitalOfficers.value.length > 0)
// 协助伙伴区块可见性
const showPartnerOfficers = computed(() => ['all', 'partner'].includes(activeType.value) && partnerOfficers.value.length > 0)

const digitalSectionTitle = computed(() => (activeType.value === 'agent' ? '数字警员' : '数字警员'))
const partnerSectionTitle = computed(() => (activeType.value === 'partner' ? '协助伙伴' : '协助伙伴'))

// 最受欢迎：按「本周 / 本月」时间窗过滤后，按评分 + 使用量取前 2
const inPeriod = (item) => {
  if (!item?.created_at) return true // 无时间戳不参与过滤（兜底展示）
  const ts = new Date(item.created_at).getTime()
  if (isNaN(ts)) return true
  const days = trendPeriod.value === 'week' ? 7 : 30
  return Date.now() - ts <= days * 86400_000
}
const featured = computed(() => {
  if (!showHero.value) return []
  const pool = [...digitalOfficers.value, ...partnerOfficers.value].filter(inPeriod)
  const ranked = [...pool].sort(
    (a, b) => (b.stats?.rating ?? 0) - (a.stats?.rating ?? 0) || (b.stats?.usage ?? 0) - (a.stats?.usage ?? 0)
  )
  // 时间窗内无数据时回退到全量最受欢迎，避免 Hero 空白
  return (ranked.length ? ranked : [...digitalOfficers.value, ...partnerOfficers.value])
    .sort((a, b) => (b.stats?.rating ?? 0) - (a.stats?.rating ?? 0) || (b.stats?.usage ?? 0) - (a.stats?.usage ?? 0))
    .slice(0, 2)
})

// 开箱即用列表项（仅 技能 / 全部 展示真实技能数据）
const skillRows = computed(() => {
  if (activeType.value !== 'skill' && activeType.value !== 'all') return []
  return skills.value.map((s) => ({
    key: s.slug || s.name,
    slug: s.slug,
    name: s.name,
    description: s.description,
    icon: s.icon,
    iconComp: s.icon && !isEmoji(s.icon) ? Box : Bot,
    installed: !!s.enabled,
    pending: false,
    source_type: s.source_type,
    source: s.source_type === 'builtin' ? '内置技能' : (s.source_type || '通用技能'),
    created_by: s.created_by,
    author: s.created_by === 'system' ? '小南官方' : (s.created_by || '小南官方'),
    version: s.version,
    dir_path: s.dir_path,
    tool_dependencies: s.tool_dependencies,
    mcp_dependencies: s.mcp_dependencies,
    skill_dependencies: s.skill_dependencies,
    updated_at: s.updated_at,
    created_at: s.created_at,
  }))
})

const comingSoon = computed(
  () => showSkills.value && activeType.value !== 'skill' && activeType.value !== 'all' && skillRows.value.length === 0,
)

const skillSectionTitle = computed(() => {
  if (activeType.value === 'skill') return '技能市场'
  if (activeType.value === 'tool') return '工具市场'
  if (activeType.value === 'mcp') return 'MCP 连接器'
  if (activeType.value === 'card') return '卡片市场'
  return '技能 / 工具 / MCP / 卡片 · 开箱即用'
})

const typeLabel = (t) =>
  ({ agent: '数字民警', partner: '协助伙伴', template: '技能模板' }[t] || t)
const markKey = (item) => `${item.type}-${item.id}`

const actionLabel = (item) => {
  if (appliedSet.value.has(markKey(item))) return '已申请'
  if (item.type === 'partner') return '添加'
  if (item.apply_mode === 'connect') return '申请使用'
  if (item.apply_mode === 'equip_guided') return '关注使用'
  return '选用模板'
}
const appliedText = (item) => {
  if (item.type === 'agent') return '已申请'
  if (item.type === 'partner') return '已关注'
  return '已选用'
}
const metaLine = (item) => item.category || item.badge_number || item.author || '小南官方'
const ratingText = (item) => (item.stats?.rating ? Number(item.stats.rating).toFixed(1) : '0.0')
const initial = (s) => (s || '?').toString().slice(0, 1)
const isEmoji = (s) => typeof s === 'string' && s.length <= 2 && /\p{Emoji}/u.test(s)

function startChat(useCase) {
  router.push({ path: '/agent', query: { prompt: useCase } })
}

async function fetchOfficers() {
  const res = await policeMarketApi.explore({
    type: 'all',
    keyword: keyword.value || undefined,
    category: categoryFilter.value || undefined,
    page: 1,
    page_size: 50,
  })
  items.value = res.items || []
  const conns = await policeConnectionApi.list()
  appliedSet.value = new Set(
    (conns.items || [])
      .filter((c) => c.agent)
      .map((c) => (c.agent.is_subagent ? `partner-${c.agent.id}` : `agent-${c.agent.id}`)),
  )
}

async function load() {
  loading.value = true
  try {
    const tasks = []
    if (showOfficers.value && !officersLoaded.value) {
      tasks.push(fetchOfficers().then(() => { officersLoaded.value = true }))
    }
    if (showSkills.value && (activeType.value === 'skill' || activeType.value === 'all') && !skillsLoaded.value) {
      tasks.push(skillApi.listSkills().then((s) => {
        // 后端返回 { success, data: [...] } 包装，兼容直接数组
        skills.value = Array.isArray(s) ? s : (s?.data || [])
        skillsLoaded.value = true
      }))
    }
    await Promise.all(tasks)
  } catch (e) {
    message.error('加载市场失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

function onPill(val) {
  activeType.value = val
  // 切出协助伙伴 tab 时清空分类筛选，避免残留过滤影响其它 tab
  if (val !== 'partner') categoryFilter.value = ''
  load()
}

function onCategoryChange() {
  officersLoaded.value = false
  load()
}

function onSearch() {
  officersLoaded.value = false
  skillsLoaded.value = false
  load()
}

// ===== 横向滑动：鼠标拖拽（数字警员 / 协助伙伴 各自容器独立） =====
function onSwipeDown(e) {
  const el = e.currentTarget
  if (!el) return
  drag.active = true
  drag.moved = false
  drag.el = el
  drag.startX = e.pageX - el.getBoundingClientRect().left
  drag.startScroll = el.scrollLeft
}
function onSwipeMove(e) {
  if (!drag.active || !drag.el) return
  const x = e.pageX - drag.el.getBoundingClientRect().left
  const walk = x - drag.startX
  if (Math.abs(walk) > 4) drag.moved = true
  drag.el.scrollLeft = drag.startScroll - walk
}
function onSwipeUp() {
  drag.active = false
  drag.el = null
}
function onOfficerClick(item) {
  if (drag.moved) {
    drag.moved = false
    return
  }
  openDetail(item)
}

async function toggleRow(row) {
  if (row.pending) return
  row.pending = true
  const next = !row.installed
  try {
    await skillApi.updateSkillEnabled(row.slug, next)
    row.installed = next
    // 同步弹窗中显示的启用状态
    if (skillDetailItem.value?.slug === row.slug) {
      skillDetailItem.value = { ...skillDetailItem.value, installed: next }
    }
    message.success(next ? '已启用该技能' : '已关闭该技能')
  } catch (e) {
    message.error('操作失败: ' + (e.message || e))
  } finally {
    row.pending = false
  }
}

// ★ 技能卡片点击 → 打开详情弹窗
function openSkillDetail(row) {
  skillDetailItem.value = { ...row }
  skillDetailOpen.value = true
}
function closeSkillDetail() {
  skillDetailOpen.value = false
  skillDetailItem.value = null
}

async function handleApply(item) {
  if (applying.value) return
  applying.value = true
  try {
    const res = await policeMarketApi.apply(item.type, item.id)
    appliedSet.value.add(markKey(item))
    // P5：添加数字警员时若级联关联了协助伙伴，须明确提示一并添加
    const cascaded = res?.cascaded_partner_ids
    if (cascaded?.length) {
      message.success(`已添加「${item.name}」，并一并添加 ${cascaded.length} 个关联协助伙伴`)
    } else {
      message.success(res?.message || '操作成功')
    }
  } catch (e) {
    message.error('申请失败: ' + (e.message || e))
  } finally {
    applying.value = false
  }
}

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
    category: base.category || d.category || (type === 'partner' ? '协助伙伴' : '数字民警'),
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
    console.warn('加载资产详情失败', e)
  }
  if (item.type === 'agent') loadReviews()
}

function closeDetail() {
  detailOpen.value = false
}

function enterChat(item) {
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
  } catch {
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

function relativeTime(s) {
  if (!s) return '未知'
  const d = new Date(s)
  if (isNaN(d.getTime())) return '未知'
  const diff = (Date.now() - d.getTime()) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return Math.floor(diff / 60) + ' 分钟前'
  if (diff < 86400) return Math.floor(diff / 3600) + ' 小时前'
  const days = Math.floor(diff / 86400)
  if (days < 30) return days + ' 天前'
  if (days < 365) return Math.floor(days / 30) + ' 月前'
  return Math.floor(days / 365) + ' 年前'
}

function openPublish() {
  publishOpen.value = true
}

function onPublished() {
  message.success('已进入审核，通过后将在市场可见')
  officersLoaded.value = false
  load()
}

onMounted(() => {
  load()
})
</script>

<style scoped lang="less">
.xn-explore {
  padding: 28px 28px 56px;
  max-width: 1280px;
  margin: 0 auto;
  min-height: 100vh;
  color: var(--gray-1000);
  // 页面跟随系统浅色背景，不再强制深色；仅卡片使用深色 Mesh 渐变作为高级感点缀
  background: transparent;
  border-radius: 18px;
}

/* ===== 1. 顶部分类与搜索栏 ===== */
.xe-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 14px;
  margin-bottom: 26px;
}
.xe-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}
.xe-pill {
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-700);
  background: var(--gray-100);
  border: 1px solid var(--gray-200);
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.16s ease;
}
.xe-pill:hover {
  color: var(--gray-1000);
  background: var(--main-20);
  border-color: var(--main-200);
}
.xe-pill.active {
  color: var(--main-900);
  background: var(--main-20);
  border-color: var(--main-300);
  box-shadow: 0 2px 10px rgba(46, 109, 206, 0.18);
}
.xe-right {
  display: flex;
  gap: 10px;
  align-items: center;
}
.xe-search {
  width: 260px;
  :deep(.ant-input),
  :deep(.ant-input-search-button) {
    background: #fff;
    border-color: var(--gray-200);
    color: var(--gray-1000);
  }
  :deep(.ant-input::placeholder) {
    color: var(--gray-500);
  }
}
// 黑底高亮发布按钮
.xe-publish {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  background: #0f172a;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.16s ease;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.32);
}
.xe-publish:hover {
  background: #1e293b;
  transform: translateY(-1px);
}

/* ===== 加载 / 空态 ===== */
.xe-loading {
  display: flex;
  justify-content: center;
  padding: 80px 0;
}

/* ===== 2. Hero 最受欢迎（深色微光 + 遮罩） ===== */
.xe-feature {
  margin-bottom: 30px;
}
.xe-eyebrow-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.xe-eyebrow {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.6px;
  color: var(--gray-600);
}
.xe-trend-switch :deep(.ant-segmented-item) {
  font-size: 12px;
}
.xe-banner {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}
.xe-hero-card {
  position: relative;
  min-height: 200px;
  border-radius: 18px;
  overflow: hidden;
  padding: 22px 24px;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  cursor: pointer;
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.28);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.xe-hero-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.4);
  border-color: rgba(255, 255, 255, 0.28);
}
.xe-crown-svg {
  position: absolute;
  top: 12px;
  right: 14px;
  z-index: 3;
  pointer-events: none;
  transform: rotate(14deg);
  filter: drop-shadow(0 0 14px rgba(251, 191, 36, 0.75))
          drop-shadow(0 4px 10px rgba(217, 119, 6, 0.55));
  animation: explore-crown-float 3.4s ease-in-out infinite;
}
@keyframes explore-crown-float {
  0%, 100% { transform: rotate(14deg) translateY(0); }
  50%      { transform: rotate(14deg) translateY(-6px); }
}
.xe-hero-shade {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0) 32%, rgba(0, 0, 0, 0.5) 100%);
  pointer-events: none;
  z-index: 1;
}
.xe-hero-content {
  position: relative;
  z-index: 2;
}
.xe-hero-title {
  margin: 0;
  font-size: 21px;
  font-weight: 800;
  color: #fff;
  letter-spacing: 0.4px;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.35);
}
.xe-hero-desc {
  margin: 8px 0 14px;
  max-width: 460px;
  font-size: 13px;
  line-height: 1.55;
  color: rgba(255, 255, 255, 0.82);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.xe-hero-author {
  display: flex;
  align-items: center;
  gap: 9px;
}
.xe-author-av {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid rgba(255, 255, 255, 0.3);
}
.xe-author-name {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}
.xe-author-meta {
  margin-left: auto;
  font-size: 11.5px;
  color: rgba(255, 255, 255, 0.78);
}

/* ===== 通用区块 ===== */
.xe-section {
  margin-bottom: 30px;
}
.xe-sec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.xe-sec-title {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  color: var(--gray-1000);
  letter-spacing: 0.3px;
}
.xe-sec-more {
  font-size: 13px;
  font-weight: 600;
  color: var(--main-700);
  cursor: pointer;
  user-select: none;
  transition: color 0.15s ease;
}
.xe-sec-more:hover {
  color: var(--main-900);
}

/* ===== 3. 横向 Swipe 滑动容器 ===== */
.swipe-container {
  display: flex;
  gap: 16px;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  padding-bottom: 12px;
  cursor: grab;
  user-select: none;
  scrollbar-width: none;
  &::-webkit-scrollbar { display: none; }
}
.swipe-container:active { cursor: grabbing; }
.swipe-item {
  flex: 0 0 calc(25% - 12px);
  min-width: 280px;
  scroll-snap-align: start;
}

/* 数字警员暗色 Glassmorphism + Mesh 渐变卡片 */
.xe-officer-card {
  position: relative;
  min-height: 248px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.25);
  padding: 18px;
  display: flex;
  flex-direction: column;
  color: #fff;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}
.xe-officer-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 16px 38px rgba(15, 23, 42, 0.42);
  border-color: rgba(255, 255, 255, 0.3);
}
.xe-officer-badge {
  position: absolute;
  top: 14px;
  right: 14px;
  padding: 3px 10px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.26);
  border-radius: 999px;
  backdrop-filter: blur(2px);
}
.xe-officer-main {
  flex: 1;
  min-height: 0;
}
.xe-officer-avatar {
  width: 46px;
  height: 46px;
  border-radius: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 800;
  color: #fff;
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.28);
  margin-bottom: 14px;
}
.xe-officer-name {
  font-size: 16px;
  font-weight: 800;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.3);
}
.xe-officer-desc {
  margin-top: 6px;
  font-size: 12.5px;
  line-height: 1.55;
  color: rgba(255, 255, 255, 0.8);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.xe-officer-foot {
  display: flex;
  align-items: center;
  gap: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.16);
  padding-top: 12px;
  margin-top: 12px;
  font-size: 11.5px;
  color: rgba(255, 255, 255, 0.78);
}
.xe-meta {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.xe-star {
  color: #fbbf24;
  font-weight: 700;
}

/* ===== 4. 开箱即用：自适应多列网格（更紧凑） ===== */
.xe-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}
.xe-row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid var(--gray-200);
  box-shadow: 0 6px 18px var(--shadow-1);
  background: #fff;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  cursor: pointer;
}
.xe-row:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 28px var(--shadow-3);
  border-color: var(--main-300);
}
.xe-row-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: #fff;
  background: linear-gradient(135deg, var(--main-500), var(--color-accent-700));
  border: 1px solid var(--main-300);
}
.xe-row-main {
  flex: 1;
  min-width: 0;
}
.xe-row-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--gray-1000);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.xe-row-desc {
  margin-top: 3px;
  font-size: 12px;
  color: var(--gray-600);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.xe-row-action {
  flex-shrink: 0;
}
.xe-installed {
  padding: 5px 11px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--color-success-700);
  background: var(--color-success-50);
  border: 1px solid var(--color-success-100);
  border-radius: 999px;
}
.xe-installed--lg {
  padding: 7px 14px;
  font-size: 13px;
}
.xe-add {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  cursor: pointer;
  color: #fff;
  background: var(--color-primary-500);
  border: 1px solid var(--color-primary-700);
  transition: all 0.15s ease;
}
.xe-add:hover {
  background: var(--color-primary-700);
}
.xe-add--lg {
  width: auto;
  height: auto;
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  gap: 4px;
}

/* ===== 技能详情弹窗专属样式 ===== */
.xe-meta-line {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--gray-700);
}
.xe-dot-sep {
  font-size: 12px;
  color: var(--gray-500);
}
.xe-deps {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
}
.xe-dep-chip {
  padding: 3px 10px;
  font-size: 11.5px;
  font-weight: 600;
  border-radius: 999px;
  background: var(--gray-50);
  color: var(--gray-800);
  border: 1px solid var(--gray-200);
}
.xe-dep-tool {
  background: color-mix(in srgb, #38a169 8%, transparent);
  color: #22543d;
  border-color: color-mix(in srgb, #38a169 20%, transparent);
}
.xe-dep-mcp {
  background: color-mix(in srgb, #805ad5 8%, transparent);
  color: #44337a;
  border-color: color-mix(in srgb, #805ad5 20%, transparent);
}
.xe-dep-skill {
  background: color-mix(in srgb, #3182ce 8%, transparent);
  color: #2a4365;
  border-color: color-mix(in srgb, #3182ce 20%, transparent);
}
.xe-mt {
  margin-top: 22px;
}

/* ===== 详情弹窗（Hero 区深色，正文跟随系统浅色） ===== */
.xe-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(4px);
  padding: 20px;
}
.xe-modal {
  position: relative;
  width: 880px;
  max-width: 94vw;
  max-height: 84vh;
  border-radius: 20px;
  background: #fff;
  border: 1px solid var(--gray-200);
  box-shadow: 0 24px 70px var(--shadow-4);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: var(--gray-1000);
}
.xe-modal-close {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 20;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  color: var(--gray-700);
  background: rgba(255, 255, 255, 0.72);
  transition: background 0.15s;
}
.xe-modal-close:hover {
  background: var(--gray-100);
}
.xe-modal-hero {
  position: relative;
  min-height: 188px;
  padding: 22px 28px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
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
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.6);
  font-size: 12px;
  color: var(--gray-900);
}
.xe-creator-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--main-100);
  color: var(--main-900);
  font-size: 11px;
  font-weight: 700;
}
.xe-creator-name {
  white-space: nowrap;
}
.xe-type-pill {
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.6);
  font-size: 11px;
  color: var(--gray-900);
}
.xe-modal-hero .xe-hero-title {
  font-size: 25px;
  font-weight: 800;
  letter-spacing: 0.3px;
  line-height: 1.25;
  color: #fff;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
}
.xe-modal-hero .xe-hero-desc {
  margin: 8px 0 0;
  font-size: 13.5px;
  line-height: 1.55;
  color: rgba(255, 255, 255, 0.82);
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
  background: var(--gray-200);
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
  color: var(--gray-800);
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
  border: 1px solid var(--gray-200);
  padding: 2px 9px;
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
  color: var(--gray-700);
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
  background: var(--gray-50);
  border: 1px solid var(--gray-200);
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
  background: var(--main-100);
  color: var(--main-900);
  font-size: 11px;
  font-weight: 700;
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
  color: var(--gray-1000);
}
.xe-review-stars {
  display: inline-flex;
  gap: 1px;
}
.xe-star-on {
  color: var(--color-warning-500);
  fill: var(--color-warning-500);
}
.xe-review-content {
  margin: 6px 0 4px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--gray-800);
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
  background: var(--gray-50);
  border-radius: 10px;
}
.xe-review-form {
  background: var(--gray-50);
  border: 1px solid var(--gray-200);
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
  color: var(--gray-400);
  padding: 2px;
  line-height: 0;
  transition: color 0.12s;
}
.xe-star-btn.on {
  color: var(--color-warning-500);
  fill: var(--color-warning-500);
}
.xe-star-btn:hover {
  color: var(--color-warning-500);
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
  border-top: 1px solid var(--gray-200);
  padding-top: 12px;
}
.xe-dot {
  opacity: 0.5;
}

/* ===== 4 套深色 Mesh 渐变预设（纯 CSS，离线可用） ===== */
.gradient-card-blue {
  background:
    radial-gradient(120% 120% at 10% 10%, rgba(0, 240, 255, 0.34) 0%, rgba(0, 240, 255, 0) 55%),
    radial-gradient(120% 120% at 90% 22%, rgba(59, 130, 246, 0.42) 0%, rgba(59, 130, 246, 0) 55%),
    #0f172a;
}
.gradient-card-purple {
  background:
    radial-gradient(120% 120% at 10% 10%, rgba(139, 92, 246, 0.36) 0%, rgba(139, 92, 246, 0) 55%),
    radial-gradient(120% 120% at 90% 22%, rgba(236, 72, 153, 0.40) 0%, rgba(236, 72, 153, 0) 55%),
    #130f26;
}
.gradient-card-emerald {
  background:
    radial-gradient(120% 120% at 10% 10%, rgba(16, 185, 129, 0.34) 0%, rgba(16, 185, 129, 0) 55%),
    radial-gradient(120% 120% at 90% 22%, rgba(6, 182, 212, 0.40) 0%, rgba(6, 182, 212, 0) 55%),
    #06201b;
}
.gradient-card-dark {
  background:
    radial-gradient(120% 120% at 10% 10%, rgba(245, 158, 11, 0.30) 0%, rgba(245, 158, 11, 0) 55%),
    radial-gradient(120% 120% at 90% 22%, rgba(99, 102, 241, 0.40) 0%, rgba(99, 102, 241, 0) 55%),
    #18181b;
}

.xe-fade-enter-active,
.xe-fade-leave-active {
  transition: opacity 0.18s ease;
}
.xe-fade-enter-from,
.xe-fade-leave-to {
  opacity: 0;
}

@media (max-width: 1080px) {
  .xe-banner { grid-template-columns: 1fr; }
  .swipe-item { flex: 0 0 calc(50% - 8px); }
  // .xe-list 用 auto-fill 自适应多列，小屏自动变单列，无需强制
}
@media (max-width: 640px) {
  .swipe-item { flex: 0 0 84%; }
}
</style>
