<template>
  <!-- 滑动药丸分段控件：v-model 绑定选中值，JS 仅写 pill 位置，CSS 拥有补间 -->
  <div ref="root" class="t-tabs" role="tablist">
    <span ref="pill" class="t-tabs-pill" aria-hidden="true"></span>
    <button
      v-for="opt in options"
      :key="opt.value"
      class="t-tab"
      type="button"
      role="tab"
      :aria-selected="String(modelValue === opt.value)"
      @click="select(opt.value)"
    >
      {{ opt.label }}
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] } // [{ label, value }]
})
const emit = defineEmits(['update:modelValue'])

const root = ref(null)
const pill = ref(null)

function activeTab() {
  if (!root.value) return null
  return (
    [...root.value.querySelectorAll('.t-tab')].find(
      (t) => t.getAttribute('aria-selected') === 'true'
    ) || null
  )
}

function moveTo(tab, animate) {
  if (!tab || !pill.value) return
  if (!animate) {
    const prev = pill.value.style.transition
    pill.value.style.transition = 'none'
    pill.value.style.transform = `translateX(${tab.offsetLeft}px)`
    pill.value.style.width = `${tab.offsetWidth}px`
    void pill.value.offsetWidth
    pill.value.style.transition = prev
  } else {
    pill.value.style.transform = `translateX(${tab.offsetLeft}px)`
    pill.value.style.width = `${tab.offsetWidth}px`
  }
}

function select(val) {
  emit('update:modelValue', val)
}

function onResize() {
  moveTo(activeTab(), false)
}

onMounted(() => {
  nextTick(() => moveTo(activeTab(), false))
  window.addEventListener('resize', onResize)
})
onUnmounted(() => window.removeEventListener('resize', onResize))

watch(
  () => props.modelValue,
  () => nextTick(() => moveTo(activeTab(), true))
)
</script>
