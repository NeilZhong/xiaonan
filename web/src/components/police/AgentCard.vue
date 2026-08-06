<script setup>
/**
 * 数字警员 / 智能体卡片（StaffDeck 风格 v2）
 * - 头像加大，背景块上边缘对齐头像中间
 * - 右上角白色区域放三点菜单（仅编辑/删除）
 * - 背景块右侧白色圆角矩形对话按钮，hover 蓝底白图标
 * - 头像右侧竖排：名称 / 职位 / 在线状态
 * - 底部统计：资料 / 技能 / 工具
 */
import { computed } from 'vue'
import { MessageCircle, MoreHorizontal, Trash2, SquarePen } from 'lucide-vue-next'

import { resolveAgentAvatar } from '@/utils/policeAvatar'

const props = defineProps({
  agent: { type: Object, required: true },
  isOfficer: { type: Boolean, default: false },
  statusText: { type: String, default: '在线' },
  statusColor: { type: String, default: 'green' }
})

const emit = defineEmits(['click', 'chat', 'profile', 'edit', 'delete'])

const officer = computed(() => (props.isOfficer ? props.agent._officer : null))

const avatarUrl = computed(() => resolveAgentAvatar(props.agent))

const agentName = computed(() => props.agent?.name || '未命名智能体')

/** 警号：仅「全局审核通过且已上架(is_global_approved)」的数字警员展示 */
const badgeText = computed(() => {
  const o = officer.value
  if (!o) return ''
  if (!o.is_global_approved || o.approval_status !== 'approved') return ''
  return o.badge_number || ''
})
const showBadge = computed(() => !!badgeText.value)

/** 职位/职务 */
const jobTitle = computed(() => {
  if (officer.value?.rank) return officer.value.rank
  if (officer.value?.department) return officer.value.department
  return props.agent?.backend_id || '通用智能体'
})

const description = computed(
  () =>
    officer.value?.specialty ||
    officer.value?.description ||
    props.agent?.description ||
    '暂无描述'
)

const capabilityTags = computed(() => {
  const raw = officer.value?.capabilities || props.agent?.capabilities
  if (Array.isArray(raw) && raw.length) return raw.slice(0, 4)
  const desc = description.value
  if (!desc) return []
  const phrases = desc.split(/[,，、\s]+/).filter((t) => t.length >= 2 && t.length <= 8)
  return phrases.slice(0, 3)
})

const statItems = computed(() => {
  const stats = officer.value?.work_stats || {}
  const skills = (officer.value?.skills || []).length
  const tools = (props.agent?.tools || props.agent?.tool_ids || []).length
  const positive = stats.feedback_positive
  return [
    { label: '累计对话', value: stats.total_conversations ?? 0 },
    { label: '完成任务', value: stats.total_tasks ?? 0 },
    { label: '好评率', value: positive != null ? `${positive}%` : '—' },
  ]
})

function onCardClick() {
  emit('click', props.agent)
}

function onChat(e) {
  e?.stopPropagation?.()
  emit('chat', props.agent)
}

function onEdit(e) {
  e?.stopPropagation?.()
  emit('edit', props.agent)
}

function onDelete(e) {
  e?.stopPropagation?.()
  emit('delete', props.agent)
}
</script>

<template>
  <div class="police-agent-card" @click="onCardClick">
    <!-- 上半部分：头像 + 背景色块 + 右侧角色信息 -->
    <div class="card-top-area">
      <!-- 右上角三点菜单（白色区域） -->
      <div class="card-header-actions">
        <div class="agent-menu-trigger-wrap" @click.stop>
          <a-dropdown :trigger="['click']" placement="bottomRight">
            <button type="button" class="agent-menu-trigger" aria-label="更多操作">
              <MoreHorizontal :size="18" />
            </button>
            <template #overlay>
              <a-menu>
                <a-menu-item key="edit" @click="onEdit">
                  <span class="menu-item-inner"><SquarePen :size="14" /><span>编辑</span></span>
                </a-menu-item>
                <a-menu-item key="delete" danger @click="onDelete">
                  <span class="menu-item-inner"><Trash2 :size="14" /><span>删除</span></span>
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </div>

      <!-- 头像（浮在背景块之上） -->
      <div class="card-avatar-container">
        <div class="card-avatar">
          <img :src="avatarUrl" :alt="`${agentName}头像`" />
        </div>
      </div>

      <!-- 背景色块 -->
      <div class="card-banner">
        <div class="banner-meta">
          <h3 class="banner-name" :title="agentName">
            {{ agentName }}
            <span v-if="showBadge" class="banner-badge" :title="`警号 ${badgeText}`">警号 {{ badgeText }}</span>
          </h3>
          <p class="banner-job" :title="jobTitle">{{ jobTitle }}</p>
          <div class="banner-status-row">
            <span class="status-dot" :class="`dot-${statusColor}`" />
            <span class="status-label" :class="`label-${statusColor}`">
              {{ statusText }}
            </span>
          </div>
        </div>
        <!-- 对话按钮（背景块右侧，垂直居中） -->
        <button type="button" class="chat-btn" :title="`与 ${agentName} 对话`" @click="onChat">
          <MessageCircle :size="16" />
        </button>
      </div>
    </div>

    <!-- 描述 -->
    <p class="agent-card-desc" :title="description">{{ description }}</p>

    <!-- 功能标签 -->
    <div v-if="capabilityTags.length" class="agent-card-tags">
      <span v-for="(tag, idx) in capabilityTags" :key="idx" class="agent-tag">{{ tag }}</span>
    </div>

    <!-- 底部统计 -->
    <div class="agent-card-stats">
      <div v-for="stat in statItems" :key="stat.label" class="agent-stat-cell">
        <div class="agent-stat-value">{{ stat.value }}</div>
        <div class="agent-stat-label">{{ stat.label }}</div>
      </div>
    </div>
  </div>
</template>

<style lang="less" scoped>
.police-agent-card {
  display: flex;
  flex-direction: column;
  padding: 16px;
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(16, 30, 54, 0.06);
  border: 1px solid var(--gray-150);
  cursor: pointer;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 28px rgba(16, 30, 54, 0.1);
    border-color: var(--main-200);
  }
}

// ============ 上半区 ============
.card-top-area {
  position: relative;
  padding-top: 36px; // 给菜单按钮留空间
}

// ============ 右上角菜单 ============
.card-header-actions {
  position: absolute;
  top: 0;
  right: 0;
  z-index: 3;
}

.agent-menu-trigger-wrap {
  // 透明包裹
}

.agent-menu-trigger {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--gray-500);
  cursor: pointer;
  transition: background 0.16s ease;

  &:hover {
    background: var(--gray-100);
    color: var(--gray-800);
  }
}

// ============ 头像 ============
.card-avatar-container {
  position: absolute;
  left: 0;
  top: 18px; // 放大后保持与背景色块的浮出/底部间隙
  z-index: 2;
}

.card-avatar {
  width: 104px;
  height: 104px;
  border-radius: 22px;
  overflow: hidden;
  background: transparent; // 透明底色，靠 officer-default.png 自身轮廓与背景色块形成层次
  // 与档案页 ap-hero-avatar 保持一致：浮于背景块之上、无描边阴影

  img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

// ============ 背景色块 ============
.card-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 14px 14px 118px; // 左侧给放大的头像留空间，保持与头像 14px 间隙
  min-height: 68px;
  background: linear-gradient(135deg, #f7f8fa 0%, #e8ecf2 100%);
  border-radius: 14px;
  position: relative;
  z-index: 1;
}

.banner-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.banner-name {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #1a365d;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
  display: inline-flex;
  align-items: center;
  gap: 8px;

  .banner-badge {
    flex-shrink: 0;
    padding: 1px 8px;
    border-radius: 999px;
    background: var(--main-700);
    color: #ffffff;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.3px;
    line-height: 1.6;
  }
}

.banner-job {
  margin: 0;
  font-size: 12px;
  color: var(--gray-600);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.3;
}

.banner-status-row {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 1px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;

  &.dot-green { background: #22c55e; }
  &.dot-red { background: #ef4444; }
  &.dot-orange { background: #f97316; }
  &.dot-blue { background: #3b82f6; }
}

.status-label {
  font-size: 11px;
  font-weight: 600;

  &.label-green { color: #15803d; }
  &.label-red { color: #b91c1c; }
  &.label-orange { color: #c2410c; }
  &.label-blue { color: #1d4ed8; }
}

// ============ 对话按钮（背景块右侧） ============
.chat-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid var(--gray-200);
  border-radius: 10px;
  background: #ffffff;
  color: var(--gray-600);
  cursor: pointer;
  flex-shrink: 0;
  transition:
    background 0.2s ease,
    color 0.2s ease,
    border-color 0.2s ease,
    transform 0.15s ease;

  &:hover {
    background: var(--main-700);
    color: #ffffff;
    border-color: var(--main-700);
    transform: scale(1.05);
  }

  &:active {
    transform: scale(0.97);
  }
}

// ============ 描述 & 标签 ============
.agent-card-desc {
  margin: 14px 0 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--gray-600);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  min-height: 2.8em;
}

.agent-card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}

.agent-tag {
  font-size: 11px;
  color: var(--gray-700);
  background: var(--gray-100);
  padding: 4px 10px;
  border-radius: 20px;
  font-weight: 500;
}

// ============ 统计栅格 ============
.agent-card-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 12px;
  margin-top: 14px;
  background: #f8fafc;
  border-radius: 12px;
}

.agent-stat-cell {
  text-align: center;

  & + .agent-stat-cell {
    border-left: 1px solid var(--gray-200);
  }
}

.agent-stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #1a365d;
  line-height: 1.2;
}

.agent-stat-label {
  font-size: 11px;
  color: var(--gray-500);
  margin-top: 2px;
}

.menu-item-inner {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
</style>
