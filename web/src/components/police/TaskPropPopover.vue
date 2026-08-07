<script setup>
/**
 * ★ 通用 Click-to-Open 属性下拉浮层（Notion/Linear 风格）
 * 用于任务详情弹窗右侧属性栏：状态/优先级/标签/日期等字段。
 *
 * 特性：
 *  - 触发器任意插槽；点击开合，外点/Esc 关闭（direction 控制浮层方向）
 *  - 选项列表：选中对勾、搜索过滤、单选/多选、分组
 *  - 键盘可达：Enter/Space 开合、↑↓ 导航、Esc 关闭
 *  - 语义 token + 明暗自适应（项目无 Tailwind，scoped CSS 实现同等视觉）
 */
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { Check, ChevronDown, Search, X } from 'lucide-vue-next'

const props = defineProps({
  /** 浮层方向：下方对齐（属性栏用）或上方弹出（底部按钮用） */
  direction: { type: String, default: 'down' },
  /** 浮层宽度（px） */
  width: { type: Number, default: 220 },
  /** 是否显示搜索框 */
  searchable: { type: Boolean, default: false },
  /** 搜索占位 */
  searchPlaceholder: { type: String, default: '搜索' },
  /** 选项：[{ value, label, dot?, pill?, disabled?, group? }] */
  options: { type: Array, default: () => [] },
  /** 当前选中值（单选 String / 多选 Array） */
  modelValue: { type: [String, Array, Number], default: null },
  /** 多选模式 */
  multiple: { type: Boolean, default: false },
  /** 空态文案 */
  emptyText: { type: String, default: '无匹配项' },
})
const emit = defineEmits(['update:modelValue', 'select'])

const open = ref(false)
const keyword = ref('')
const highlightIndex = ref(-1)
const rootRef = ref(null)
const listRef = ref(null)

/** 按分组聚合过滤后的选项 */
const grouped = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  const filtered = props.options.filter(o =>
    !kw || String(o.label || '').toLowerCase().includes(kw)
  )
  const groups = []
  for (const o of filtered) {
    const g = o.group || ''
    let cur = groups.find(x => x.label === g)
    if (!cur) { cur = { label: g, items: [] }; groups.push(cur) }
    cur.items.push(o)
  }
  return groups
})

const flatItems = computed(() => grouped.value.flatMap(g => g.items))

/** 是否已选中（多选数组 / 单选值） */
function isSelected(opt) {
  if (props.multiple) {
    return Array.isArray(props.modelValue) && props.modelValue.includes(opt.value)
  }
  return props.modelValue === opt.value
}

function toggle() {
  open.value = !open.value
  if (open.value) {
    keyword.value = ''
    highlightIndex.value = -1
    nextTickFocus()
  }
}

function pick(opt) {
  if (opt.disabled) return
  if (props.multiple) {
    const cur = Array.isArray(props.modelValue) ? [...props.modelValue] : []
    const idx = cur.indexOf(opt.value)
    if (idx >= 0) cur.splice(idx, 1)
    else cur.push(opt.value)
    emit('update:modelValue', cur)
    emit('select', opt.value, cur)
  } else {
    emit('update:modelValue', opt.value)
    emit('select', opt.value)
    close()
  }
}

function close() {
  open.value = false
  keyword.value = ''
  highlightIndex.value = -1
}

/** 键盘导航：↑↓ 移动高亮、Enter 选中、Esc 关闭 */
function onKeydown(e) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    open.value = true
    highlightIndex.value = (highlightIndex.value + 1) % Math.max(flatItems.value.length, 1)
    scrollHighlight()
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    open.value = true
    highlightIndex.value = (highlightIndex.value - 1 + Math.max(flatItems.value.length, 1)) % Math.max(flatItems.value.length, 1)
    scrollHighlight()
  } else if (e.key === 'Enter') {
    if (open.value && highlightIndex.value >= 0 && flatItems.value[highlightIndex.value]) {
      e.preventDefault()
      pick(flatItems.value[highlightIndex.value])
    } else {
      toggle()
    }
  } else if (e.key === 'Escape') {
    if (open.value) { e.preventDefault(); close() }
  } else if (e.key === ' ') {
    // Space 在输入框内不拦截
    if (e.target.tagName !== 'INPUT') { e.preventDefault(); toggle() }
  }
}

function scrollHighlight() {
  nextTick(() => {
    listRef.value?.querySelector('[data-highlight="true"]')?.scrollIntoView({ block: 'nearest' })
  })
}

function nextTickFocus() {
  nextTick(() => {
    rootRef.value?.querySelector('input')?.focus()
  })
}

/** 外点关闭 */
function onDocClick(e) {
  if (open.value && rootRef.value && !rootRef.value.contains(e.target)) {
    close()
  }
}

watch(open, (v) => {
  if (v) document.addEventListener('mousedown', onDocClick)
  else document.removeEventListener('mousedown', onDocClick)
})
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocClick))
</script>

<template>
  <div ref="rootRef" class="tpp" @keydown="onKeydown">
    <!-- 触发器插槽 -->
    <div class="tpp-trigger" role="button" :tabindex="0" :aria-expanded="open" @click="toggle">
      <slot name="trigger">
        <span class="tpp-trigger-text">{{ modelValue || '选择' }}</span>
        <ChevronDown :size="13" class="tpp-chevron" :class="{ 'is-open': open }" />
      </slot>
    </div>

    <!-- 浮层 -->
    <transition name="tpp-fade">
      <div
        v-if="open"
        class="tpp-popover"
        :class="`is-${direction}`"
        :style="{ width: width + 'px' }"
        role="listbox"
        @click.stop
      >
        <!-- 搜索框 -->
        <div v-if="searchable" class="tpp-search">
          <Search :size="13" class="tpp-search-icon" />
          <input
            v-model="keyword"
            class="tpp-search-input"
            :placeholder="searchPlaceholder"
            @keydown.stop
          />
          <button v-if="keyword" class="tpp-search-clear" @click="keyword = ''">
            <X :size="12" />
          </button>
        </div>

        <!-- 选项列表 -->
        <div ref="listRef" class="tpp-list">
          <template v-for="g in grouped" :key="g.label || 'default'">
            <div v-if="g.label" class="tpp-group-label">{{ g.label }}</div>
            <button
              v-for="opt in g.items"
              :key="opt.value"
              class="tpp-option"
              :class="{
                'is-selected': isSelected(opt),
                'is-highlight': flatItems.indexOf(opt) === highlightIndex,
              }"
              :data-highlight="flatItems.indexOf(opt) === highlightIndex"
              :disabled="opt.disabled"
              role="option"
              :aria-selected="isSelected(opt)"
              @click="pick(opt)"
              @mouseenter="highlightIndex = flatItems.indexOf(opt)"
            >
              <span v-if="opt.dot" class="tpp-opt-dot" :style="{ background: opt.dot }"></span>
              <span v-else-if="opt.icon" class="tpp-opt-icon">
                <component :is="opt.icon" :size="13" />
              </span>
              <span class="tpp-opt-label">{{ opt.label }}</span>
              <span v-if="opt.pill" class="tpp-opt-pill" :class="`is-${opt.pill}`"></span>
              <Check v-if="isSelected(opt)" :size="14" class="tpp-opt-check" />
            </button>
          </template>
          <div v-if="!flatItems.length" class="tpp-empty">{{ emptyText }}</div>
        </div>

        <!-- 多选操作栏 -->
        <div v-if="multiple" class="tpp-footer">
          <span class="tpp-footer-count">
            已选 {{ Array.isArray(modelValue) ? modelValue.length : 0 }}
          </span>
          <button class="tpp-footer-done" @click="close">完成</button>
        </div>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.tpp { position: relative; display: inline-block; width: 100%; }
.tpp-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  width: 100%;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--gray-800, #1e293b);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.tpp-trigger:hover { background: var(--gray-10, #f1f5f9); border-color: var(--gray-50, #e2e8f0); }
.tpp-trigger:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 1px;
}
.tpp-trigger-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; text-align: left; }
.tpp-chevron { color: var(--gray-400, #94a3b8); transition: transform 0.15s; flex-shrink: 0; }
.tpp-chevron.is-open { transform: rotate(180deg); }

.tpp-popover {
  position: absolute;
  z-index: 1080;
  background: var(--gray-0, #fff);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12), 0 2px 6px rgba(15, 23, 42, 0.06);
  padding: 6px;
}
.tpp-popover.is-down { top: calc(100% + 4px); left: 0; }
.tpp-popover.is-up { bottom: calc(100% + 4px); left: 0; }

.tpp-search {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  margin-bottom: 4px;
  border-radius: 6px;
  background: var(--gray-10, #f1f5f9);
}
.tpp-search-icon { color: var(--gray-400, #94a3b8); flex-shrink: 0; }
.tpp-search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 13px;
  color: var(--gray-800, #1e293b);
  padding: 2px 0;
}
.tpp-search-input::placeholder { color: var(--gray-400, #94a3b8); }
.tpp-search-clear {
  display: inline-flex;
  border: none;
  background: transparent;
  color: var(--gray-400, #94a3b8);
  cursor: pointer;
  padding: 2px;
}
.tpp-search-clear:hover { color: var(--gray-600, #475569); }

.tpp-list { max-height: 240px; overflow: auto; }
.tpp-group-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--gray-400, #94a3b8);
  padding: 6px 8px 2px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.tpp-option {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  padding: 6px 8px;
  border: none;
  border-radius: 6px;
  background: transparent;
  font-size: 13px;
  color: var(--gray-700, #334155);
  cursor: pointer;
  text-align: left;
  transition: background 0.1s;
}
.tpp-option:hover, .tpp-option.is-highlight { background: var(--gray-10, #f1f5f9); }
.tpp-option.is-selected { color: var(--gray-900, #0f172a); font-weight: 500; }
.tpp-option:disabled { opacity: 0.4; cursor: not-allowed; }
.tpp-option:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: -2px;
}
.tpp-opt-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.tpp-opt-icon { color: var(--gray-500, #64748b); display: inline-flex; flex-shrink: 0; }
.tpp-opt-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tpp-opt-pill {
  width: 22px;
  height: 10px;
  border-radius: 9999px;
  flex-shrink: 0;
}
.tpp-opt-pill.is-rose { background: #f43f5e; }
.tpp-opt-pill.is-orange { background: #f97316; }
.tpp-opt-pill.is-blue { background: #3b82f6; }
.tpp-opt-pill.is-green { background: #22c55e; }
.tpp-opt-pill.is-gray { background: #94a3b8; }
.tpp-opt-check { color: var(--main-color, #24839b); flex-shrink: 0; }
.tpp-empty { padding: 14px 8px; text-align: center; font-size: 12px; color: var(--gray-400, #94a3b8); }

.tpp-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 4px 2px;
  border-top: 1px solid var(--gray-50, #e2e8f0);
  margin-top: 4px;
}
.tpp-footer-count { font-size: 12px; color: var(--gray-400, #94a3b8); }
.tpp-footer-done {
  border: none;
  background: var(--main-color, #24839b);
  color: #fff;
  font-size: 12px;
  padding: 3px 14px;
  border-radius: 6px;
  cursor: pointer;
}
.tpp-footer-done:hover { opacity: 0.88; }
.tpp-footer-done:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 1px;
}

.tpp-fade-enter-active, .tpp-fade-leave-active { transition: opacity 0.12s, transform 0.12s; }
.tpp-fade-enter-from, .tpp-fade-leave-to { opacity: 0; transform: translateY(-3px); }
.tpp-popover.is-up.tpp-fade-enter-from, .tpp-popover.is-up.tpp-fade-leave-to { transform: translateY(3px); }

@media (prefers-reduced-motion: reduce) {
  .tpp-fade-enter-active, .tpp-fade-leave-active, .tpp-chevron, .tpp-option { transition: none; }
}
</style>
