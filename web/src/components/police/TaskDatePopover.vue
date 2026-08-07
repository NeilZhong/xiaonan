<script setup>
/**
 * ★ 日期选择浮层（Notion 风格日历网格）
 * 用于任务详情弹窗「开始日期 / 截止日期」。
 * 支持：月份切换、点击选中、今天、清除；外点/Esc 关闭。
 */
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { Calendar, ChevronLeft, ChevronRight, X } from 'lucide-vue-next'

const props = defineProps({
  /** 当前值（YYYY-MM-DD 或 null） */
  modelValue: { type: String, default: null },
  placeholder: { type: String, default: '选择日期' },
})
const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const rootRef = ref(null)
// 日历视图锚点（YYYY-MM）
const viewYear = ref(new Date().getFullYear())
const viewMonth = ref(new Date().getMonth() + 1)

const WEEK_HEAD = ['一', '二', '三', '四', '五', '六', '日']

const selected = computed(() => props.modelValue)

/** 视图月份的天数 */
const daysInView = computed(() => new Date(viewYear.value, viewMonth.value, 0).getDate())

/** 视图首日星期几（0=周日）→ 转为周一开始（0=周一） */
const firstWeekday = computed(() => {
  const d = new Date(viewYear.value, viewMonth.value - 1, 1).getDay()
  return d === 0 ? 6 : d - 1
})

/** 生成网格：6x7 固定，含前后月补位 */
const grid = computed(() => {
  const cells = []
  const prevMonthDays = new Date(viewYear.value, viewMonth.value - 1, 0).getDate()
  for (let i = 0; i < firstWeekday.value; i++) {
    const d = prevMonthDays - firstWeekday.value + 1 + i
    cells.push({ day: d, inView: false })
  }
  for (let d = 1; d <= daysInView.value; d++) {
    cells.push({ day: d, inView: true })
  }
  while (cells.length % 7 !== 0) {
    cells.push({ day: cells.length % 7 === 0 ? 1 : (cells.length % 7), inView: false })
  }
  return cells
})

function fmt(v) {
  return `${viewYear.value}-${String(viewMonth.value).padStart(2, '0')}-${String(v).padStart(2, '0')}`
}

function isToday(day, inView) {
  if (!inView) return false
  const now = new Date()
  return now.getFullYear() === viewYear.value && now.getMonth() + 1 === viewMonth.value && now.getDate() === day
}

function isSelected(day, inView) {
  if (!inView || !selected.value) return false
  return selected.value === fmt(day)
}

function pick(day, inView) {
  if (!inView) return
  const v = fmt(day)
  emit('update:modelValue', v)
  close()
}

function today() {
  const now = new Date()
  emit('update:modelValue', `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`)
  close()
}

function clear() {
  emit('update:modelValue', null)
  close()
}

function prevMonth() {
  if (viewMonth.value === 1) { viewMonth.value = 12; viewYear.value-- }
  else viewMonth.value--
}
function nextMonth() {
  if (viewMonth.value === 12) { viewMonth.value = 1; viewYear.value++ }
  else viewMonth.value++
}

function toggle() {
  open.value = !open.value
  // 打开时锚定到当前选中月份
  if (open.value && selected.value) {
    const [y, m] = selected.value.split('-').map(Number)
    if (y && m) { viewYear.value = y; viewMonth.value = m }
  }
}
function close() { open.value = false }

function onDocClick(e) {
  if (open.value && rootRef.value && !rootRef.value.contains(e.target)) close()
}
watch(open, (v) => {
  if (v) document.addEventListener('mousedown', onDocClick)
  else document.removeEventListener('mousedown', onDocClick)
})
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocClick))
</script>

<template>
  <div ref="rootRef" class="tdp" @keydown.esc="close">
    <!-- 触发器 -->
    <div class="tdp-trigger" role="button" :tabindex="0" :aria-expanded="open" @click="toggle">
      <Calendar :size="13" class="tdp-trigger-icon" />
      <span class="tdp-trigger-text" :class="{ 'is-empty': !modelValue }">
        {{ modelValue || placeholder }}
      </span>
      <button v-if="modelValue" class="tdp-clear" @click.stop="clear">
        <X :size="12" />
      </button>
    </div>

    <!-- 日历浮层 -->
    <transition name="tdp-fade">
      <div v-if="open" class="tdp-popover" @click.stop>
        <!-- 头部：月份切换 -->
        <div class="tdp-head">
          <button class="tdp-nav" title="上个月" @click="prevMonth"><ChevronLeft :size="14" /></button>
          <span class="tdp-title">{{ viewYear }} 年 {{ viewMonth }} 月</span>
          <button class="tdp-nav" title="下个月" @click="nextMonth"><ChevronRight :size="14" /></button>
        </div>

        <!-- 星期表头 -->
        <div class="tdp-week">
          <span v-for="w in WEEK_HEAD" :key="w" class="tdp-week-cell">{{ w }}</span>
        </div>

        <!-- 日期网格 -->
        <div class="tdp-grid">
          <button
            v-for="(cell, i) in grid"
            :key="i"
            class="tdp-cell"
            :class="{
              'is-out': !cell.inView,
              'is-today': isToday(cell.day, cell.inView),
              'is-selected': isSelected(cell.day, cell.inView),
            }"
            :disabled="!cell.inView"
            @click="pick(cell.day, cell.inView)"
          >{{ cell.day }}</button>
        </div>

        <!-- 快捷操作 -->
        <div class="tdp-footer">
          <button class="tdp-foot-btn" @click="today">今天</button>
          <button class="tdp-foot-btn is-clear" @click="clear">清除</button>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.tdp { position: relative; width: 100%; }
.tdp-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  font-size: 13px;
  color: var(--gray-800, #1e293b);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.tdp-trigger:hover { background: var(--gray-10, #f1f5f9); border-color: var(--gray-50, #e2e8f0); }
.tdp-trigger:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 1px;
}
.tdp-trigger-icon { color: var(--gray-400, #94a3b8); flex-shrink: 0; }
.tdp-trigger-text { flex: 1; text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tdp-trigger-text.is-empty { color: var(--gray-400, #94a3b8); }
.tdp-clear {
  display: inline-flex;
  border: none;
  background: transparent;
  color: var(--gray-400, #94a3b8);
  cursor: pointer;
  padding: 2px;
}
.tdp-clear:hover { color: var(--gray-600, #475569); }

.tdp-popover {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 1080;
  width: 248px;
  background: var(--gray-0, #fff);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12), 0 2px 6px rgba(15, 23, 42, 0.06);
  padding: 8px;
}
.tdp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.tdp-nav {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-500, #64748b);
  cursor: pointer;
}
.tdp-nav:hover { background: var(--gray-10, #f1f5f9); color: var(--gray-800, #1e293b); }
.tdp-nav:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 1px;
}
.tdp-title { font-size: 13px; font-weight: 600; color: var(--gray-800, #1e293b); }

.tdp-week {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  margin-bottom: 2px;
}
.tdp-week-cell {
  text-align: center;
  font-size: 11px;
  color: var(--gray-400, #94a3b8);
  padding: 3px 0;
}
.tdp-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 1px; }
.tdp-cell {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 27px;
  border: none;
  border-radius: 6px;
  background: transparent;
  font-size: 12px;
  color: var(--gray-700, #334155);
  cursor: pointer;
}
.tdp-cell:hover { background: var(--gray-10, #f1f5f9); }
.tdp-cell:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: -1px;
}
.tdp-cell.is-out { color: var(--gray-200, #cbd5e1); cursor: default; }
.tdp-cell.is-out:disabled { background: transparent; }
.tdp-cell.is-today { font-weight: 700; color: var(--main-color, #24839b); }
.tdp-cell.is-selected { background: var(--main-color, #24839b); color: #fff; font-weight: 600; }
.tdp-cell.is-selected:hover { background: var(--main-color, #24839b); opacity: 0.9; }

.tdp-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid var(--gray-50, #e2e8f0);
}
.tdp-foot-btn {
  border: none;
  background: transparent;
  font-size: 12px;
  color: var(--main-color, #24839b);
  cursor: pointer;
  padding: 2px 8px;
  border-radius: 6px;
}
.tdp-foot-btn:hover { background: var(--gray-10, #f1f5f9); }
.tdp-foot-btn.is-clear { color: var(--gray-400, #94a3b8); }
.tdp-foot-btn:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 1px;
}

.tdp-fade-enter-active, .tdp-fade-leave-active { transition: opacity 0.12s, transform 0.12s; }
.tdp-fade-enter-from, .tdp-fade-leave-to { opacity: 0; transform: translateY(-3px); }

@media (prefers-reduced-motion: reduce) {
  .tdp-fade-enter-active, .tdp-fade-leave-active { transition: none; }
}
</style>
