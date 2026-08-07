<template>
  <!-- 成功对勾：淡入 + 旋转 + 下沉 + SVG 描边；show=true 触发，replayKey 变化可重播 -->
  <span
    ref="root"
    class="t-success-check"
    :data-state="state"
    :style="{ width: size + 'px', height: size + 'px' }"
    aria-hidden="true"
  >
    <svg viewBox="0 0 48 48" :width="size" :height="size" fill="none">
      <path ref="pathEl" d="M14 25 L21 32 L34 16" />
    </svg>
  </span>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'

const props = defineProps({
  // 是否展示（true 时播放一次）
  show: { type: Boolean, default: false },
  // 尺寸 px
  size: { type: Number, default: 48 },
  // 改变此值可在 show 已为 true 时强制重播
  replayKey: { type: [Number, String], default: 0 }
})

const root = ref(null)
const pathEl = ref(null)
const state = ref('out')

// 按真实路径长度校准描边，避免过绘/欠绘
function calibrate() {
  if (!pathEl.value) return
  const len = Math.ceil(pathEl.value.getTotalLength())
  pathEl.value.style.strokeDasharray = String(len)
  pathEl.value.style.strokeDashoffset = String(len)
  root.value.style.setProperty('--check-len', String(len))
}

function play() {
  if (!root.value) return
  state.value = 'out'
  void root.value.offsetWidth // 强制 reflow，保证 keyframes 从头重放
  state.value = 'in'
}

onMounted(() => {
  calibrate()
  if (props.show) nextTick(play)
})

watch(
  () => props.show,
  (v) => {
    if (v) play()
  }
)
watch(
  () => props.replayKey,
  () => {
    if (props.show) play()
  }
)

defineExpose({ play })
</script>
