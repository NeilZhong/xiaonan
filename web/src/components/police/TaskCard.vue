<script setup>
/**
 * ★ 任务卡片 — Multica 风格
 * 区分人类 / 智能体创建，优先级彩色标签，显示类型、依据、创建者、截止日期。
 * 复用于任务看板与个人工作台。
 */
import { computed } from 'vue'
import { RobotOutlined } from '@ant-design/icons-vue'

const props = defineProps({
  task: { type: Object, required: true },
})
const emit = defineEmits(['click'])

const typeText = {
  transcript_analysis: '笔录分析',
  fund_analysis: '资金分析',
  evidence_collection: '调证生成',
  evidence_submission: '证据提交',
  legal_review: '法制审核',
  document_generation: '文书生成',
  investigation: '侦查',
  interrogation: '审讯',
  arrest: '抓捕',
  cyber_inquiry: '网警查询',
  knowledge_extraction: '知识抽取',
}

const priorityMeta = {
  urgent: { color: 'red', text: '紧急' },
  high: { color: 'orange', text: '高' },
  medium: { color: 'gold', text: '中' },
  low: { color: 'green', text: '低' },
}

const isAgent = computed(() => props.task.creator_type === 'agent')
const isDraft = computed(() => props.task.status === 'pending_confirmation')
const priority = computed(() => priorityMeta[props.task.priority] || priorityMeta.medium)
const typeLabel = computed(() => typeText[props.task.type] || props.task.type || '任务')
const assigneeName = computed(() =>
  props.task.assignee_name || (isAgent.value ? 'AI 待分配' : '未分配')
)
const dueText = computed(() =>
  props.task.due_date ? String(props.task.due_date).substring(0, 10) : ''
)

/** 键盘可达：Enter / Space 触发点击（DESIGN.md 键盘优先） */
function onKeydown(e) {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault()
    emit('click', props.task)
  }
}
</script>

<template>
  <div
    class="task-card"
    :class="{ 'is-draft': isDraft, 'is-agent': isAgent }"
    role="button"
    :tabindex="0"
    :aria-label="`打开任务：${task.title}`"
    @click="emit('click', task)"
    @keydown="onKeydown"
  >
    <div class="card-top">
      <a-tag size="small" class="type-tag">{{ typeLabel }}</a-tag>
      <a-tag :color="priority.color" size="small">{{ priority.text }}</a-tag>
      <span v-if="isAgent" class="agent-badge"><RobotOutlined /> AI</span>
      <span v-if="isDraft" class="draft-badge">待审查</span>
    </div>

    <div class="card-title">{{ task.title }}</div>

    <div v-if="task.instructions" class="card-basis" :title="task.instructions">
      <span class="basis-label">依据</span>{{ task.instructions }}
    </div>

    <div class="card-footer">
      <span class="card-assignee">
        <a-avatar
          v-if="!isAgent"
          size="small"
          :style="{ background: 'var(--main-color, #24839b)' }"
        >{{ (assigneeName[0] || '?') }}</a-avatar>
        <a-avatar v-else size="small" style="background: #6b7280"><RobotOutlined /></a-avatar>
        <span class="assignee-name">{{ assigneeName }}</span>
      </span>
      <span class="card-meta">
        <span v-if="dueText" class="due">{{ dueText }}</span>
        <span class="case-id">#{{ task.case_id }}</span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.task-card {
  background: var(--task-card-bg, #fff);
  border: 1px solid var(--task-card-border, #e4e6e6);
  border-left: 3px solid var(--task-card-border, #e4e6e6);
  border-radius: var(--radius-md, 8px);
  padding: 12px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: box-shadow var(--motion-instant, 150ms) ease, border-color var(--motion-instant, 150ms) ease;
}
.task-card:hover {
  box-shadow: var(--shadow-2, rgba(0, 0, 0, 0.08));
  border-color: var(--main-color, #24839b);
}
.task-card:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 2px;
  box-shadow: var(--shadow-2, rgba(0, 0, 0, 0.08));
}
.task-card.is-draft {
  border-left-color: var(--task-status-review, #d69e2e);
  background: var(--color-warning-10, #fffdf5);
}
.task-card.is-agent {
  border-left-color: var(--task-agent, #8b5cf6);
}

.card-top {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.type-tag {
  background: var(--gray-10, #f7fafc);
  color: var(--gray-700, #4a5568);
  border-color: var(--gray-50, #e2e8f0);
}
.agent-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: var(--task-font-size-xs, 11px);
  font-weight: 600;
  color: var(--task-agent, #8b5cf6);
  background: var(--color-accent-10, #f5f3ff);
  border: 1px solid var(--color-accent-50, #ede9fe);
  border-radius: var(--radius-xs, 4px);
  padding: 0 5px;
  line-height: 18px;
}
.draft-badge {
  font-size: var(--task-font-size-xs, 11px);
  font-weight: 600;
  color: var(--task-status-review, #b45309);
  background: var(--color-warning-50, #fef3c7);
  border-radius: var(--radius-xs, 4px);
  padding: 0 5px;
  line-height: 18px;
}

.card-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 8px;
  line-height: 1.4;
  color: var(--gray-900, #1a202c);
}

.card-basis {
  font-size: 12px;
  color: var(--gray-600, #718096);
  background: var(--gray-10, #f7fafc);
  border-radius: 6px;
  padding: 6px 8px;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}
.basis-label {
  display: inline-block;
  font-weight: 600;
  color: var(--gray-500, #a0aec0);
  margin-right: 4px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--gray-500, #718096);
}
.card-assignee {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}
.assignee-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 110px;
}
.card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}
.due {
  color: var(--gray-500, #718096);
}
.case-id {
  color: var(--gray-400, #a0aec0);
}
@media (prefers-reduced-motion: reduce) {
  .task-card {
    transition: none;
  }
}
</style>
