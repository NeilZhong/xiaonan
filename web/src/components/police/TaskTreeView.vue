<script setup>
/**
 * 任务树状视图（借鉴 Plane 的嵌套 block 递归呈现）
 * 基于现有 PoliceTask.parent_task_id 构建层级，采用「DFS 扁平化 + 展开态」渲染，
 * 避免递归组件，逻辑更直观。
 */
import { ref, computed } from 'vue'
import { ChevronRight, ChevronDown } from 'lucide-vue-next'

const props = defineProps({
  tasks: { type: Array, required: true },
})
const emit = defineEmits(['open-task', 'assign-task'])

// 按 parent_task_id 分组构建 childrenMap（null 视为根）
const childrenMap = computed(() => {
  const map = {}
  for (const t of props.tasks) {
    const pid = t.parent_task_id || null
    if (!map[pid]) map[pid] = []
    map[pid].push(t)
  }
  return map
})
const rootTasks = computed(() => childrenMap.value[null] || [])

// 展开态（仅记录已展开节点的 id）
const expanded = ref(new Set())
function toggle(id) {
  const s = new Set(expanded.value)
  s.has(id) ? s.delete(id) : s.add(id)
  expanded.value = s
}
const isExpanded = (id) => expanded.value.has(id)
const hasChildren = (task) => (childrenMap.value[task.id] || []).length > 0

// DFS 扁平化（尊重展开态），每行带 depth
const flatList = computed(() => {
  const result = []
  const walk = (list, depth) => {
    for (const t of list) {
      result.push({ task: t, depth })
      if (isExpanded(t.id)) {
        const kids = childrenMap.value[t.id] || []
        if (kids.length) walk(kids, depth + 1)
      }
    }
  }
  walk(rootTasks.value, 0)
  return result
})

const priorityColor = { urgent: 'red', high: 'orange', medium: 'blue', low: 'default' }
const statusColor = { pending: 'default', in_progress: 'processing', review: 'warning', completed: 'success', paused: 'default' }
const statusText = { pending: '待开始', in_progress: '进行中', review: '待审查', completed: '已完成', paused: '已暂停' }

function goTask(id) { emit('open-task', id) }
function assign(task) { emit('assign-task', task) }
</script>

<template>
  <div class="task-tree">
    <div
      v-for="row in flatList"
      :key="row.task.id"
      class="tree-row"
      :style="{ paddingLeft: row.depth * 22 + 8 + 'px' }"
    >
      <button
        v-if="hasChildren(row.task)"
        type="button"
        class="tree-toggle"
        @click="toggle(row.task.id)"
      >
        <component :is="isExpanded(row.task.id) ? ChevronDown : ChevronRight" :size="14" />
      </button>
      <span v-else class="tree-toggle tree-toggle--leaf" />

      <span class="tree-title" @click="goTask(row.task.id)">{{ row.task.title }}</span>

      <a-tag :color="priorityColor[row.task.priority]" size="small">{{ row.task.priority }}</a-tag>
      <a-badge
        v-if="row.task.status"
        :status="statusColor[row.task.status]"
        :text="statusText[row.task.status]"
      />
      <span v-if="row.task.assignee_name" class="tree-assignee">{{ row.task.assignee_name }}</span>
      <span v-if="row.task.due_date" class="tree-due">{{ (row.task.due_date || '').slice(0, 10) }}</span>

      <a-button type="link" size="small" class="tree-assign-btn" @click="assign(row.task)">分配</a-button>
    </div>

    <div v-if="!flatList.length" class="tree-empty">暂无任务</div>
  </div>
</template>

<style scoped>
.task-tree {
  border: 1px solid var(--gray-200, #e4e6e6);
  border-radius: 8px;
  overflow: hidden;
}
:root.dark .task-tree {
  border-color: var(--gray-800, #2a2c2c);
}
.tree-row {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 38px;
  padding-right: 12px;
  border-bottom: 1px solid var(--gray-100, #eef0f0);
  border-left: 2px solid transparent;
  transition: background 0.15s ease;
}
.tree-row:last-child {
  border-bottom: none;
}
.tree-row:hover {
  background: var(--gray-50, #f5f7f7);
}
:root.dark .tree-row {
  border-bottom-color: var(--gray-800, #2a2c2c);
}
:root.dark .tree-row:hover {
  background: var(--gray-900, #1d1f1f);
}
.tree-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border: none;
  background: transparent;
  color: var(--gray-500, #a7aaaa);
  cursor: pointer;
  flex-shrink: 0;
}
.tree-toggle--leaf {
  cursor: default;
}
.tree-title {
  flex: 1;
  font-size: 13px;
  color: var(--gray-800, #323333);
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
:root.dark .tree-title {
  color: var(--gray-100, #eef0f0);
}
.tree-title:hover {
  color: var(--main-color, #24839b);
  text-decoration: underline;
}
.tree-assignee,
.tree-due {
  font-size: 12px;
  color: var(--gray-500, #a7aaaa);
  flex-shrink: 0;
}
.tree-assign-btn {
  flex-shrink: 0;
}
.tree-empty {
  padding: 40px;
  text-align: center;
  color: var(--gray-500, #a7aaaa);
}
@media (prefers-reduced-motion: reduce) {
  .tree-row {
    transition: none;
  }
}
</style>
