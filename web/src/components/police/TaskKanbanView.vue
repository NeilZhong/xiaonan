<script setup>
/**
 * ★ 案件内看板视图（Plane 风格）
 * - 借鉴 Plane 的「受控分组 + 通用拖拽」：groupBy 决定分组维度，拖拽落到某列即改写该维度字段。
 * - 分组维度：status（状态）/ priority（优先级）/ assignee（执行人，拖拽即改派）。
 * - 落库走既有 policeTaskApi.update（status/priority）与 assign（改派）。
 */
import { ref, computed } from 'vue'
import { message } from 'ant-design-vue'
import { policeTaskApi } from '@/apis/police_api'

const props = defineProps({
  tasks: { type: Array, default: () => [] },
})

const emit = defineEmits(['open-task', 'assign-task', 'refresh'])

const typeText = {
  transcript_analysis: '笔录分析', fund_analysis: '资金分析', evidence_collection: '调证生成',
  evidence_submission: '证据提交', legal_review: '法制审核', document_generation: '文书生成',
  investigation: '侦查', interrogation: '审讯', arrest: '抓捕', cyber_inquiry: '网警查询',
  knowledge_extraction: '知识抽取',
}
const priorityColor = { urgent: 'red', high: 'orange', medium: 'blue', low: 'default' }

// ── 分组维度（Plane 的 GROUP_FIELD_MAP 思路） ──
const groupBy = ref('status')
const statusColumns = [
  { key: 'pending', title: '待处理', color: '#718096' },
  { key: 'in_progress', title: '进行中', color: '#3182CE' },
  { key: 'review', title: '待审核', color: '#D69E2E' },
  { key: 'completed', title: '已完成', color: '#38A169' },
  { key: 'blocked', title: '已驳回', color: '#E53E3E' },
]
const priorityColumns = [
  { key: 'urgent', title: '紧急', color: '#E53E3E' },
  { key: 'high', title: '高', color: '#ED8936' },
  { key: 'medium', title: '中', color: '#3182CE' },
  { key: 'low', title: '低', color: '#718096' },
]
const assigneeColumns = computed(() => {
  const map = new Map()
  for (const t of props.tasks) {
    for (const a of (t.assignees || [])) {
      const k = `${a.assignee_id}_${a.assignee_type}`
      if (!map.has(k)) {
        map.set(k, { key: k, id: a.assignee_id, name: a.assignee_name, type: a.assignee_type, color: a.assignee_type === 'agent' ? '#9F7AEA' : '#3182CE' })
      }
    }
  }
  return Array.from(map.values())
})

const columns = computed(() => {
  if (groupBy.value === 'status') return statusColumns
  if (groupBy.value === 'priority') return priorityColumns
  return assigneeColumns.value
})

function tasksIn(col) {
  if (groupBy.value === 'status') return props.tasks.filter(t => t.status === col.key)
  if (groupBy.value === 'priority') return props.tasks.filter(t => t.priority === col.key)
  return props.tasks.filter(t => (t.assignees || []).some(a => `${a.assignee_id}_${a.assignee_type}` === col.key))
}

// ── 拖拽 ──
const draggingId = ref(null)
const dragOverCol = ref(null)

function onDragStart(task) { draggingId.value = task.id }
function onDragEnd() { draggingId.value = null; dragOverCol.value = null }

function sameColumn(task, col) {
  if (groupBy.value === 'status') return task.status === col.key
  if (groupBy.value === 'priority') return task.priority === col.key
  return (task.assignees || []).some(a => `${a.assignee_id}_${a.assignee_type}` === col.key)
}

function onDrop(col) {
  const id = draggingId.value
  draggingId.value = null
  dragOverCol.value = null
  if (!id) return
  const task = props.tasks.find(t => t.id === id)
  if (!task || sameColumn(task, col)) return
  applyDrop(id, col)
}

async function applyDrop(id, col) {
  try {
    if (groupBy.value === 'status') {
      await policeTaskApi.update(id, { status: col.key })
    } else if (groupBy.value === 'priority') {
      await policeTaskApi.update(id, { priority: col.key })
    } else {
      await policeTaskApi.assign(id, {
        assignees: [{ assignee_type: col.type, assignee_id: col.id, assignee_name: col.name, role: 'executor' }],
      })
    }
    message.success('任务已更新')
    emit('refresh')
  } catch (e) {
    message.error('更新失败')
  }
}
</script>

<template>
  <div class="kanban-view">
    <div class="kanban-toolbar">
      <span class="group-label">分组</span>
      <a-radio-group v-model:value="groupBy" size="small">
        <a-radio-button value="status">按状态</a-radio-button>
        <a-radio-button value="priority">按优先级</a-radio-button>
        <a-radio-button value="assignee">按执行人</a-radio-button>
      </a-radio-group>
      <span class="group-hint">拖拽卡片到目标列即可改{{ { status: '状态', priority: '优先级', assignee: '执行人' }[groupBy] }}</span>
    </div>

    <div class="kanban-board">
      <div
        v-for="col in columns"
        :key="col.key"
        class="kanban-column"
        :class="{ 'drag-over': dragOverCol === col.key }"
        @dragover.prevent="dragOverCol = col.key"
        @dragleave="dragOverCol = null"
        @drop.prevent="onDrop(col)"
      >
        <div class="kanban-column-header" :style="{ borderTopColor: col.color }">
          <span class="column-title">{{ col.title }}</span>
          <span class="column-count">{{ tasksIn(col).length }}</span>
        </div>
        <div class="kanban-column-body">
          <div
            v-for="task in tasksIn(col)"
            :key="task.id"
            class="kanban-card"
            :class="{ dragging: draggingId === task.id }"
            draggable="true"
            @dragstart="onDragStart(task)"
            @dragend="onDragEnd"
            @click="emit('open-task', task.id)"
          >
            <div class="card-title">{{ task.title }}</div>
            <div class="card-meta">
              <a-tag size="small">{{ typeText[task.type] || task.type }}</a-tag>
              <a-tag :color="priorityColor[task.priority]" size="small">{{ task.priority }}</a-tag>
            </div>
            <div class="card-footer">
              <span class="card-assignee">
                <a-avatar size="small" style="background: var(--main-color, #24839b)">
                  {{ ((task.assignee_name) || (task.assignees && task.assignees[0]?.assignee_name) || '?')[0] }}
                </a-avatar>
                <span>{{ task.assignee_name || (task.assignees && task.assignees[0]?.assignee_name) || '未分配' }}</span>
              </span>
              <a-button type="link" size="small" @click.stop="emit('assign-task', task)">分配</a-button>
            </div>
          </div>
          <div v-if="!tasksIn(col).length" class="kanban-empty">暂无任务</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kanban-view { display: flex; flex-direction: column; }
.kanban-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.group-label { font-size: 13px; color: var(--gray-500, #718096); }
.group-hint { font-size: 12px; color: var(--gray-400, #a0aec0); }

.kanban-board {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 8px;
}
.kanban-column {
  min-width: 240px;
  flex: 1;
  max-width: 300px;
  background: var(--gray-10, #f7fafc);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  transition: box-shadow 0.15s, border-color 0.15s;
}
.kanban-column.drag-over {
  border-color: var(--main-color, #24839b);
  box-shadow: 0 0 0 2px var(--main-color, #24839b)33;
}
.kanban-column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-top: 3px solid;
  border-radius: 10px 10px 0 0;
}
.column-title { font-size: 13px; font-weight: 600; }
.column-count {
  font-size: 11px;
  background: var(--gray-50, #e2e8f0);
  padding: 2px 8px;
  border-radius: 10px;
  color: var(--gray-600, #4a5568);
}
.kanban-column-body { padding: 8px; flex: 1; min-height: 80px; }
.kanban-card {
  background: var(--gray-0, #fff);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
  cursor: grab;
  transition: box-shadow 0.15s, opacity 0.15s;
}
.kanban-card:hover { box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08); }
.kanban-card.dragging { opacity: 0.4; }
.card-title { font-size: 13px; font-weight: 500; margin-bottom: 6px; line-height: 1.4; }
.card-meta { display: flex; gap: 4px; margin-bottom: 6px; flex-wrap: wrap; }
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--gray-500, #718096);
}
.card-assignee { display: flex; align-items: center; gap: 4px; }
.kanban-empty { text-align: center; color: var(--gray-400, #a0aec0); padding: 20px 0; font-size: 12px; }
</style>
