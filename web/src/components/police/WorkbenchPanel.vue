<script setup>
/**
 * ★ 工作台可拖拽面板外壳
 *  - 统一标题栏（图标 + 标题 + 计数 + 操作）
 *  - 支持拖拽排序（HTML5 DnD）：面板头部可拖、可自定义拖拽手柄
 *  - 支持移除（触发父级 remove 事件，父级管理布局持久化）
 */
import { GripVertical, X } from 'lucide-vue-next'

defineProps({
  title: { type: String, default: '' },
  icon: { type: [Object, Function], default: null },
  count: { type: [Number, String], default: 0 },
  showCount: { type: Boolean, default: true },
  removable: { type: Boolean, default: true },
  draggable: { type: Boolean, default: true },
  full: { type: Boolean, default: false },
  // 面板唯一 key（用于 DnD 排序）
  panelKey: { type: String, default: '' },
})
const emit = defineEmits(['remove', 'dragstart', 'dragover', 'drop', 'dragend'])

function onDragStart(e) {
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/panel-key', String(panelKey))
  emit('dragstart', panelKey)
}
function onDragOver(e) {
  e.preventDefault()
  e.dataTransfer.dropEffect = 'move'
  emit('dragover', panelKey)
}
function onDrop(e) {
  e.preventDefault()
  emit('drop', panelKey)
}
</script>

<template>
  <section
    class="wb-panel"
    :class="full ? 'wb-panel--full' : ''"
    @dragover="onDragOver"
    @drop="onDrop"
  >
    <header
      class="wb-panel-head"
      :draggable="draggable"
      :title="draggable ? '拖拽调整位置' : ''"
      @dragstart="onDragStart"
      @dragend="emit('dragend')"
    >
      <span v-if="draggable" class="wb-panel-grip" :title="'拖拽调整位置'">
        <GripVertical :size="14" />
      </span>
      <component :is="icon" v-if="icon" class="wb-panel-icon" :size="16" />
      <h3 class="wb-panel-title">{{ title }}</h3>
      <span v-if="showCount" class="wb-panel-count">{{ count }}</span>
      <div class="wb-panel-actions">
        <slot name="actions" />
        <button
          v-if="removable"
          type="button"
          class="wb-panel-remove"
          :title="'从工作台移除'"
          @click="emit('remove')"
        >
          <X :size="14" />
        </button>
      </div>
    </header>
    <div class="wb-panel-body">
      <slot />
    </div>
  </section>
</template>

<style lang="less" scoped>
.wb-panel {
  display: flex;
  flex-direction: column;
  background: var(--gray-0, #fff);
  border: 1px solid var(--main-20, #e8eff3);
  border-radius: 14px;
  box-shadow: 0 2px 12px rgba(16, 30, 54, 0.05);
  overflow: hidden;
  min-width: 0;
  transition: box-shadow 0.18s ease, border-color 0.18s ease, transform 0.18s ease;

  &:hover {
    border-color: var(--main-100, #cfe3e8);
    box-shadow: 0 6px 20px rgba(16, 30, 54, 0.09);
  }

  &.wb-dragging {
    opacity: 0.5;
    transform: scale(0.99);
  }
&.wb-panel--full {
    grid-column: 1 / -1;
  }
}

.wb-panel-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--gray-50, #e9eef2);
  cursor: grab;
  user-select: none;

  &:active {
    cursor: grabbing;
  }
}

.wb-panel-grip {
  display: inline-flex;
  align-items: center;
  color: var(--gray-400, #a0aec0);
  cursor: grab;
}

.wb-panel-icon {
  color: var(--main-color, #24839b);
  flex-shrink: 0;
}

.wb-panel-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-1000, #1a1a1a);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.wb-panel-count {
  min-width: 20px;
  height: 20px;
  padding: 0 7px;
  border-radius: 999px;
  background: var(--main-color, #24839b);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  line-height: 20px;
  text-align: center;
}

.wb-panel-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
}

.wb-panel-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-400, #a0aec0);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;

  &:hover {
    background: var(--color-danger-50, #fdecec);
    color: var(--color-danger-600, #d64545);
  }
}

.wb-panel-body {
  padding: 12px;
  min-height: 0;
  overflow-y: auto;
  flex: 1;
}
</style>