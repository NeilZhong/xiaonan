<script setup>
/**
 * 任务日历视图（借鉴 Plane calendar layout）
 * 基于现有 PoliceTask.due_date 渲染月历网格，任务卡片按日期归入对应日格。
 */
import { ref, computed } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'

const props = defineProps({
  tasks: { type: Array, required: true },
})
const emit = defineEmits(['open-task', 'assign-task'])

const today = new Date()
const viewYear = ref(today.getFullYear())
const viewMonth = ref(today.getMonth()) // 0-11

// 按 due_date(YYYY-MM-DD) 分组
const monthTasks = computed(() => {
  const map = {}
  for (const t of props.tasks) {
    if (!t.due_date) continue
    const d = (t.due_date || '').slice(0, 10)
    if (!map[d]) map[d] = []
    map[d].push(t)
  }
  return map
})

const firstDay = computed(() => new Date(viewYear.value, viewMonth.value, 1).getDay()) // 0=周日
const daysInMonth = computed(() => new Date(viewYear.value, viewMonth.value + 1, 0).getDate())
const weeks = computed(() => {
  const cells = []
  for (let i = 0; i < firstDay.value; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth.value; d++) cells.push(d)
  while (cells.length % 7 !== 0) cells.push(null)
  const rows = []
  for (let i = 0; i < cells.length; i += 7) rows.push(cells.slice(i, i + 7))
  return rows
})
const monthLabel = computed(() => `${viewYear.value}年${viewMonth.value + 1}月`)
const weekHeaders = ['日', '一', '二', '三', '四', '五', '六']

const statusColor = { pending: 'default', in_progress: 'processing', review: 'warning', completed: 'success', paused: 'default' }

function prevMonth() {
  if (viewMonth.value === 0) { viewMonth.value = 11; viewYear.value-- } else viewMonth.value--
}
function nextMonth() {
  if (viewMonth.value === 11) { viewMonth.value = 0; viewYear.value++ } else viewMonth.value++
}
function cellDate(d) {
  return d ? `${viewYear.value}-${String(viewMonth.value + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}` : null
}
function isToday(d) {
  const t = new Date()
  return d === t.getDate() && viewMonth.value === t.getMonth() && viewYear.value === t.getFullYear()
}
function goTask(id) { emit('open-task', id) }
</script>

<template>
  <div class="task-calendar">
    <div class="calendar-header">
      <div class="cal-nav">
        <button type="button" class="cal-btn" @click="prevMonth"><ChevronLeft :size="16" /></button>
        <span class="cal-label">{{ monthLabel }}</span>
        <button type="button" class="cal-btn" @click="nextMonth"><ChevronRight :size="16" /></button>
      </div>
    </div>

    <div class="calendar-grid">
      <div v-for="w in weekHeaders" :key="w" class="cal-weekday">{{ w }}</div>
      <template v-for="(row, ri) in weeks" :key="ri">
        <div
          v-for="(d, ci) in row"
          :key="ri + '-' + ci"
          class="cal-cell"
          :class="{ 'cal-cell--empty': !d, 'cal-cell--today': d && isToday(d) }"
        >
          <template v-if="d">
            <div class="cal-date">{{ d }}</div>
            <div class="cal-tasks">
              <div
                v-for="t in (monthTasks[cellDate(d)] || [])"
                :key="t.id"
                class="cal-task"
                @click="goTask(t.id)"
              >
                <span class="cal-dot" :class="'dot-' + (t.status || 'pending')" />
                <span class="cal-task-title">{{ t.title }}</span>
              </div>
            </div>
          </template>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.task-calendar {
  border: 1px solid var(--gray-200, #e4e6e6);
  border-radius: 8px;
  padding: 12px;
}
:root.dark .task-calendar {
  border-color: var(--gray-800, #2a2c2c);
}
.calendar-header {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 10px;
}
.cal-nav {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.cal-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--gray-200, #e4e6e6);
  border-radius: 6px;
  background: transparent;
  color: var(--gray-600, #8a8d8d);
  cursor: pointer;
}
.cal-btn:hover {
  background: var(--gray-100, #eef0f0);
}
:root.dark .cal-btn {
  border-color: var(--gray-800, #2a2c2c);
}
:root.dark .cal-btn:hover {
  background: var(--gray-900, #1d1f1f);
}
.cal-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-800, #323333);
  min-width: 84px;
  text-align: center;
}
:root.dark .cal-label {
  color: var(--gray-100, #eef0f0);
}
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}
.cal-weekday {
  text-align: center;
  font-size: 12px;
  color: var(--gray-500, #a7aaaa);
  padding: 4px 0;
}
.cal-cell {
  min-height: 84px;
  border: 1px solid var(--gray-100, #eef0f0);
  border-radius: 6px;
  padding: 4px;
  background: var(--gray-50, #f5f7f7);
}
:root.dark .cal-cell {
  border-color: var(--gray-800, #2a2c2c);
  background: var(--gray-900, #1d1f1f);
}
.cal-cell--empty {
  background: transparent;
  border-color: transparent;
}
.cal-cell--today {
  border-color: var(--main-color, #24839b);
  box-shadow: inset 0 0 0 1px var(--main-color, #24839b);
}
.cal-date {
  font-size: 12px;
  color: var(--gray-600, #8a8d8d);
  margin-bottom: 2px;
}
.cal-task {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 4px;
  margin-bottom: 2px;
  border-radius: 4px;
  background: var(--gray-100, #eef0f0);
  cursor: pointer;
  overflow: hidden;
}
.cal-task:hover {
  background: var(--gray-200, #e4e6e6);
}
:root.dark .cal-task {
  background: var(--gray-800, #2a2c2c);
}
:root.dark .cal-task:hover {
  background: var(--gray-700, #3a3d3d);
}
.cal-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--gray-400, #bdbfbf);
}
.dot-pending { background: var(--gray-400, #bdbfbf); }
.dot-in_progress { background: #24839b; }
.dot-review { background: #faad14; }
.dot-completed { background: #52c41a; }
.dot-paused { background: #bfbfbf; }
.cal-task-title {
  font-size: 11px;
  color: var(--gray-800, #323333);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
:root.dark .cal-task-title {
  color: var(--gray-100, #eef0f0);
}
</style>
