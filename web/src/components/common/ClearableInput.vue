<template>
  <!-- 清空输入框：文字飞出 + 光晕（input-clear）。
       结构沿用 transitions.css 的 .t-clear / .t-clear-mirror / .t-clear-glow。 -->
  <div class="t-clear" :class="{ 'has-value': !!modelValue, 'is-clearing': clearing }" ref="wrap">
    <input
      ref="inputEl"
      class="t-clear-input"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="onInput"
      @keydown.enter="$emit('enter', $event)"
    />
    <span class="t-clear-placeholder" aria-hidden="true">{{ placeholder }}</span>
    <span class="t-clear-mirror" aria-hidden="true">{{ mirrorText }}</span>
    <span class="t-clear-glow" aria-hidden="true"></span>
    <button
      v-if="modelValue"
      class="t-clear-btn"
      type="button"
      :aria-label="clearLabel"
      @click="clear"
    >
      <X :size="14" />
    </button>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  placeholder: { type: String, default: '搜索...' },
  disabled: { type: Boolean, default: false },
  clearLabel: { type: String, default: '清空' }
})
const emit = defineEmits(['update:modelValue', 'enter', 'clear'])

const wrap = ref(null)
const inputEl = ref(null)
const clearing = ref(false)
const mirrorText = ref('')

function onInput(e) {
  emit('update:modelValue', e.target.value)
}

function clear() {
  if (clearing.value) return
  // 先把当前文字放进镜像层，播放飞出 + 光晕，再真正清空
  mirrorText.value = String(props.modelValue ?? '')
  clearing.value = true
  nextTick(() => {
    window.setTimeout(() => {
      clearing.value = false
      mirrorText.value = ''
      emit('update:modelValue', '')
      emit('clear')
      inputEl.value?.focus()
    }, 420)
  })
}
</script>

<style scoped>
.t-clear-input {
  width: 100%;
  height: 32px;
  border: 1px solid var(--gray-200, #e5e7eb);
  border-radius: 6px;
  padding: 0 30px 0 12px;
  font-size: 13px;
  color: var(--gray-1000, #1f2329);
  background: var(--gray-0, #fff);
  outline: none;
  transition: border-color 0.15s ease-out, box-shadow 0.15s ease-out;
}
.t-clear-input:focus {
  border-color: var(--main-color, #2e6dce);
  box-shadow: 0 0 0 2px var(--color-primary-50, rgba(46, 109, 206, 0.12));
}
.t-clear-btn {
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: 0;
  border-radius: 50%;
  background: var(--gray-200, #e5e7eb);
  color: var(--gray-600, #6b7280);
  cursor: pointer;
  z-index: 4;
}
.t-clear-btn:hover {
  background: var(--gray-300, #d1d5db);
  color: var(--gray-800, #374151);
}
:root.dark .t-clear-input {
  background: var(--gray-900, #161a22);
  border-color: var(--gray-700, #2a2f3a);
  color: var(--gray-100, #e5e7eb);
}
</style>
