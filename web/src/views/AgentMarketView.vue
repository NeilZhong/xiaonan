<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  Store, Download, Search, FileText, BarChart3,
  ShieldCheck, ClipboardList, FileSearch, Users, Car,
  BrainCircuit, Sparkles, Check, User,
} from 'lucide-vue-next'

import PageHeader from '@/components/shared/PageHeader.vue'
import FallbackAvatar from '@/components/common/FallbackAvatar.vue'
import { policeAgentApi } from '@/apis/police_api'

const router = useRouter()

// ── 来源 Tab ──
const SOURCES = [
  { key: 'builtin', label: '内置模板', icon: Store },
  { key: 'shared', label: '来自分享', icon: User },
]
const activeSource = ref('builtin')

// ── 市场分类定义（9 类，参照 WorkBuddy 专家团按业务领域划分） ──
const CATEGORIES = [
  { key: '', label: '全部', icon: Store },
  { key: 'case_analysis', label: '案件分析', icon: FileText },
  { key: 'fund_tracking', label: '资金追踪', icon: BarChart3 },
  { key: 'legal_review', label: '法制审核', icon: ShieldCheck },
  { key: 'evidence_mgmt', label: '证据管理', icon: ClipboardList },
  { key: 'doc_office', label: '文书办公', icon: FileSearch },
  { key: 'intel_analysis', label: '情报研判', icon: BrainCircuit },
  { key: 'community_police', label: '社区警务', icon: Users },
  { key: 'traffic_mgmt', label: '交通管理', icon: Car },
  { key: 'general_assist', label: '综合辅助', icon: Sparkles },
]

const CATEGORY_MAP = Object.fromEntries(CATEGORIES.filter(c => c.key).map(c => [c.key, c]))

// ── 状态 ──
const activeCategory = ref('')
const keyword = ref('')
const loading = ref(false)
const templates = ref([])
const total = ref(0)
const installingId = ref(null)
const installedTemplateIds = ref(new Set())

// ── 加载模板列表 ──
async function loadTemplates() {
  loading.value = true
  try {
    const res = await policeAgentApi.listTemplates({
      category: activeCategory.value || undefined,
      keyword: keyword.value || undefined,
      source: activeSource.value || undefined,
    })
    templates.value = res.items || []
    total.value = res.total || 0
    installedTemplateIds.value = new Set(res.installed_template_ids || [])
  } catch (e) {
    console.error('加载市场模板失败:', e)
    templates.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

loadTemplates()

function onSourceChange(key) {
  activeSource.value = key
  activeCategory.value = '' // 切换来源时重置分类
  loadTemplates()
}

function onCategoryChange(key) {
  activeCategory.value = key
  loadTemplates()
}

function onSearch() {
  loadTemplates()
}

// ── 一键安装（内置模板和分享的智能体都支持安装） ──
async function handleInstall(tpl) {
  if (installingId.value === tpl.id) return
  installingId.value = tpl.id
  try {
    const newAgent = await policeAgentApi.installTemplate(tpl.id)
    if (!newAgent || !newAgent.agent_id) {
      throw new Error(newAgent?.error || '安装失败')
    }
    message.success(`「${tpl.name}」已安装`)
    installedTemplateIds.value.add(tpl.id)
  } catch (e) {
    const msg = e?.response?.data?.error || e?.message || '安装失败，请重试'
    message.error(msg)
  } finally {
    installingId.value = null
  }
}

// ── 辅助 ──
function getCategoryLabel(categoryKey) {
  return CATEGORY_MAP[categoryKey]?.label || categoryKey || '未分类'
}

function getCategoryIcon(categoryKey) {
  return CATEGORY_MAP[categoryKey]?.icon || Sparkles
}

/** 是否为「来自分享」来源 */
function isSharedSource() {
  return activeSource.value === 'shared'
}

function isInstalled(template) {
  return installedTemplateIds.value.has(template.id)
}

/** 审批状态文字 */
function approvalStatusText(status) {
  return { pending: '待审批', approved: '已上架', rejected: '已拒绝' }[status] || ''
}

defineExpose({
  loading,
  refresh: loadTemplates
})
</script>

<template>
  <div class="agent-market-view">
    <PageHeader title="智能体市场" :show-border="true">
      <template #info>
        <div class="summary-strip">
          <span>{{ total }} 个{{ isSharedSource() ? '分享' : '可用' }}模板</span>
          <span>{{ isSharedSource() ? '来自同事/部门分享的智能体' : '一键安装到工作台' }}</span>
        </div>
      </template>
    </PageHeader>

    <!-- 搜索 + 来源 + 分类筛选 -->
    <div class="market-toolbar">
      <div class="market-search">
        <Search :size="16" :stroke-width="1.8" class="search-icon" />
        <input
          v-model="keyword"
          type="text"
          placeholder="搜索智能体..."
          class="search-input"
          @keyup.enter="onSearch"
        />
        <button v-if="keyword" class="search-clear" @click="keyword = ''; loadTemplates()">×</button>
      </div>

      <!-- 来源 Tab -->
      <div class="source-tabs">
        <button
          v-for="src in SOURCES"
          :key="src.key"
          :class="['source-tab', { active: activeSource === src.key }]"
          @click="onSourceChange(src.key)"
        >
          <component :is="src.icon" :size="14" :stroke-width="1.8" />
          {{ src.label }}
        </button>
      </div>

      <!-- 分类 Tab（仅内置模板显示分类） -->
      <div v-if="!isSharedSource()" class="category-tabs">
        <button
          v-for="cat in CATEGORIES"
          :key="cat.key"
          :class="['cat-tab', { active: activeCategory === cat.key }]"
          @click="onCategoryChange(cat.key)"
        >
          <component :is="cat.icon" :size="14" :stroke-width="1.8" />
          {{ cat.label }}
        </button>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading && !templates.length" class="market-loading">
      <div class="loading-spinner" />
      <p>正在加载...</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!templates.length" class="market-empty">
      <Store :size="40" :stroke-width="1.4" />
      <h2 class="empty-title">{{ keyword ? '没有找到匹配结果' : isSharedSource() ? '暂无分享的智能体' : '暂无可用模板' }}</h2>
      <p class="empty-desc">{{ keyword ? '试试其他关键词' : isSharedSource() ? '同事分享的智能体会出现在这里' : '管理员尚未发布市场模板' }}</p>
    </div>

    <!-- 卡片网格 -->
    <div v-else class="template-grid">
      <div
        v-for="tpl in templates"
        :key="tpl.id"
        :class="['template-card', { 'shared-card': isSharedSource() }]"
      >
        <!-- 右上角操作按钮 -->
        <button
          v-if="!isInstalled(tpl)"
          class="card-action-btn install-action"
          :class="{ installing: installingId === tpl.id, disabled: installingId !== null && installingId !== tpl.id }"
          :disabled="installingId !== null"
          :title="'安装「' + tpl.name + '」'"
          @click="handleInstall(tpl)"
        >
          <Download v-if="installingId !== tpl.id" :size="17" :stroke-width="1.8" />
          <span v-else class="action-spinner" />
        </button>
        <div
          v-else
          class="card-action-btn installed-action"
          title="已安装"
        >
          <Check :size="17" :stroke-width="2.4" />
        </div>

        <div class="card-header">
          <FallbackAvatar
            class="tpl-avatar"
            :src="tpl.icon || tpl.avatar"
            :default-src="undefined"
            :name="tpl.name"
            :seed="String(tpl.id)"
            kind="agent"
            :size="48"
            shape="rounded"
          />
          <div class="card-info">
            <div class="name-row">
              <h3 class="tpl-name">{{ tpl.name }}</h3>
              <span class="tpl-installs">
                <Download :size="11" :stroke-width="1.8" />
                {{ tpl.install_count || 0 }}
              </span>
            </div>
            <div class="meta-row">
              <!-- 分类标签（内置模板） -->
              <span v-if="!isSharedSource() && tpl.category" class="tpl-category">
                <component :is="getCategoryIcon(tpl.category)" :size="12" :stroke-width="2" />
                {{ getCategoryLabel(tpl.category) }}
              </span>
              <!-- 来源标签（分享的智能体） -->
              <span v-else-if="isSharedSource()" class="source-badge">来自分享</span>
              <!-- 审批状态（待审批/已拒绝） -->
              <span
                v-if="tpl.approval_status === 'pending'"
                class="approval-badge pending"
              >待审批</span>
              <span
                v-else-if="tpl.approval_status === 'rejected'"
                class="approval-badge rejected"
              >已拒绝</span>
            </div>
            <!-- 作者信息（非内置 / 分享的智能体） -->
            <div v-if="isSharedSource() || !tpl.is_template" class="author-row">
              <User :size="11" :stroke-width="2" />
              <span class="author-name">{{ tpl.author_name || '未知作者' }}</span>
              <span v-if="tpl.department" class="author-dept">{{ tpl.department }}</span>
            </div>
          </div>
        </div>

        <p class="tpl-desc">{{ tpl.description || tpl.specialty || '暂无描述' }}</p>

        <div v-if="tpl.capabilities?.length" class="tpl-tags">
          <span v-for="cap in (tpl.capabilities.slice(0, 4))" :key="cap" class="cap-tag">{{ cap }}</span>
          <span v-if="tpl.capabilities.length > 4" class="cap-tag more">+{{ tpl.capabilities.length - 4 }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="less" scoped>
.agent-market-view {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  background: var(--gray-0);
  color: var(--gray-1000);
}

.summary-strip {
  display: flex;
  gap: 8px;

  span {
    padding: 6px 10px;
    border: 1px solid var(--gray-100);
    border-radius: 7px;
    background: var(--gray-10);
    color: var(--gray-700);
    font-size: 12px;
    line-height: 18px;
  }
}

.market-toolbar {
  padding: 16px 20px 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.market-search {
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: var(--gray-400);
  pointer-events: none;
}

.search-input {
  width: 100%;
  height: 38px;
  padding: 0 36px 0 38px;
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  background: white;
  font-size: 13px;
  color: var(--gray-900);
  outline: none;
  transition: border-color 0.2s;

  &:focus {
    border-color: var(--main-400);
    box-shadow: 0 0 0 2px rgba(var(--main-rgb), 0.08);
  }

  &::placeholder {
    color: var(--gray-400);
  }
}

.search-clear {
  position: absolute;
  right: 10px;
  width: 22px;
  height: 22px;
  border: none;
  background: var(--gray-100);
  border-radius: 50%;
  color: var(--gray-500);
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    background: var(--gray-200);
    color: var(--gray-700);
  }
}

/* 来源 Tab */
.source-tabs {
  display: flex;
  gap: 6px;
}

.source-tab {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 16px;
  border: 1px solid var(--gray-200);
  border-radius: 999px;
  background: white;
  color: var(--gray-600);
  font-size: 13px;
  font-weight: 500;
  line-height: 18px;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    border-color: var(--main-300);
    color: var(--main-600);
  }

  &.active {
    background: var(--main-600);
    border-color: var(--main-600);
    color: white;
  }
}

/* 分类 Tab */
.category-tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.cat-tab {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border: 1px solid var(--gray-200);
  border-radius: 999px;
  background: white;
  color: var(--gray-600);
  font-size: 12px;
  line-height: 18px;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;

  &:hover {
    border-color: var(--main-300);
    color: var(--main-600);
  }

  &.active {
    background: var(--main-600);
    border-color: var(--main-600);
    color: white;
  }
}

.market-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 0;
  color: var(--gray-500);

  p {
    font-size: 13px;
  }
}

.loading-spinner {
  width: 28px;
  height: 28px;
  border: 2.5px solid var(--gray-200);
  border-top-color: var(--main-500);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.market-empty {
  max-width: 480px;
  margin: 48px auto;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;

  > svg {
    width: 72px;
    height: 72px;
    border-radius: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--gray-50);
    color: var(--gray-400);
    border: 1px solid var(--gray-150);
    padding: 16px;
  }
}

.empty-title {
  margin: 0;
  font-size: 17px;
  font-weight: 500;
  color: var(--gray-800);
}

.empty-desc {
  margin: 0;
  font-size: 13px;
  color: var(--gray-500);
  line-height: 1.6;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
  padding: 16px 20px 32px;
}

.template-card {
  position: relative;
  background: white;
  border: 1px solid var(--gray-150);
  border-radius: 11px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: border-color 0.15s, box-shadow 0.15s;
  overflow: visible;

  &.shared-card {
    border-left: 3px solid var(--main-200);
  }

  &:hover {
    border-color: var(--gray-250);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
  }
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tpl-avatar {
  flex-shrink: 0;
}

.card-info {
  flex: 1;
  min-width: 0;
  padding-right: 44px;
}

.name-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}

.tpl-name {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--gray-900);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 3px;
}

.tpl-category {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: var(--gray-500);
}

.source-badge {
  font-size: 11px;
  color: var(--main-600);
  background: var(--main-50);
  padding: 1px 8px;
  border-radius: 999px;
  font-weight: 500;
}

.approval-badge {
  font-size: 10px;
  padding: 1px 8px;
  border-radius: 999px;
  font-weight: 500;

  &.pending {
    background: #fff7e6;
    color: #d48806;
    border: 1px solid #ffe58f;
  }

  &.rejected {
    background: var(--gray-50);
    color: var(--gray-500);
    border: 1px solid var(--gray-200);
  }
}

.author-row {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 3px;
  font-size: 11px;
  color: var(--gray-500);

  .author-name {
    color: var(--gray-700);
    font-weight: 500;
  }

  .author-dep {
    color: var(--gray-400);
    &::before { content: '·'; margin: 0 2px; }
  }
}

.tpl-installs {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 11px;
  color: var(--gray-400);
  flex-shrink: 0;
  white-space: nowrap;
}

.tpl-desc {
  margin: 0;
  font-size: 12px;
  color: var(--gray-600);
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.tpl-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.cap-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--gray-50);
  border: 1px solid var(--gray-150);
  font-size: 11px;
  color: var(--gray-600);
  line-height: 18px;

  &.more {
    background: transparent;
    border: none;
    color: var(--gray-400);
  }
}

/* ── 右上角操作按钮 ── */
.card-action-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 36px;
  height: 36px;
  border-radius: 9px;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
  z-index: 2;
}

.install-action {
  background: white;
  color: var(--gray-500);
  border: 1px solid var(--gray-200);

  &:hover:not(.disabled):not(.installing) {
    border-color: var(--main-400);
    color: var(--main-600);
    background: var(--main-50);
    transform: scale(1.08);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  &.installing {
    background: var(--gray-50);
    color: var(--gray-300);
    cursor: wait;
    border-color: var(--gray-200);
  }

  &.disabled {
    opacity: 0.4;
    cursor: not-allowed;
    background: var(--gray-50);
    color: var(--gray-300);
    border-color: var(--gray-200);
  }
}

.installed-action {
  background: var(--gray-50);
  color: #15a36e;
  border: 1px solid var(--gray-200);
  cursor: default;
}

.action-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(var(--main-rgb), 0.25);
  border-top-color: var(--main-600);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
</style>
