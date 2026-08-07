<script setup>
/**
 * 任务视图切换器（借鉴 Plane 的 LayoutSelection 受控范式）
 * - 自身零状态：当前视图由 v-model 外部持有，layouts 白名单由调用方传入
 * - 切换仅 emit update:modelValue，不持有业务数据
 */
import { Table, KanbanSquare, ListTree, GanttChartSquare, CalendarDays } from 'lucide-vue-next'

const props = defineProps({
  modelValue: { type: String, required: true },
  layouts: {
    type: Array,
    default: () => ['table', 'kanban', 'tree', 'gantt', 'calendar'],
  },
})
const emit = defineEmits(['update:modelValue'])

// 视图元数据表（类比 Plane 的 ISSUE_LAYOUT_MAP）
const LAYOUT_MAP = {
  table: { label: '表格', icon: Table },
  kanban: { label: '看板', icon: KanbanSquare },
  tree: { label: '树状', icon: ListTree },
  gantt: { label: '甘特', icon: GanttChartSquare },
  calendar: { label: '日历', icon: CalendarDays },
}

function select(key) {
  if (key !== props.modelValue) emit('update:modelValue', key)
}
</script>

<template>
  <div class="task-view-switcher">
    <button
      v-for="key in layouts"
      :key="key"
      type="button"
      class="switcher-btn"
      :class="{ active: key === modelValue }"
      :title="LAYOUT_MAP[key].label"
      @click="select(key)"
    >
      <component :is="LAYOUT_MAP[key].icon" :size="15" />
      <span class="switcher-label">{{ LAYOUT_MAP[key].label }}</span>
    </button>
  </div>
</template>

<style scoped>
.task-view-switcher {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  border-radius: 8px;
  background: var(--gray-50, #f5f7f7);
  border: 1px solid var(--gray-200, #e4e6e6);
}
:root.dark .task-view-switcher {
  background: var(--gray-900, #1d1f1f);
  border-color: var(--gray-800, #2a2c2c);
}
.switcher-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 30px;
  padding: 0 10px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-600, #8a8d8d);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.18s ease, color 0.18s ease;
}
.switcher-btn:hover {
  color: var(--gray-800, #323333);
  background: var(--gray-100, #eef0f0);
}
:root.dark .switcher-btn:hover {
  color: var(--gray-100, #eef0f0);
  background: var(--gray-800, #2a2c2c);
}
.switcher-btn.active {
  background: var(--main-color, #24839b);
  color: #fff;
}
.switcher-btn.active:hover {
  color: #fff;
}
@media (prefers-reduced-motion: reduce) {
  .switcher-btn {
    transition: none;
  }
}
@media (max-width: 768px) {
  .switcher-label {
    display: none;
  }
  .switcher-btn {
    padding: 0 8px;
  }
}
</style>
