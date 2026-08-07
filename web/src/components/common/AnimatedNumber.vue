<template>
  <span ref="root" class="t-animated-number">
    <!-- 模式一：数字 pop-in（逐位模糊滑入） -->
    <span v-if="mode === 'pop'" class="t-digit-group" :class="{ 'is-animating': animating }">
      <span v-for="(ch, i) in popChars" :key="i" class="t-digit" :data-stagger="popStagger(i)">{{ ch }}</span>
    </span>
    <!-- 模式二：spinning counter（老虎机翻滚） -->
    <span v-else class="t-reel">
      <template v-for="(seg, i) in reelSegs" :key="i">
        <span v-if="seg.type === 'digit'" class="t-reel-col">
          <span class="t-reel-strip">
            <span v-for="d in 10" :key="d" class="t-reel-digit">{{ d - 1 }}</span>
          </span>
        </span>
        <span v-else class="t-reel-sep">{{ seg.value }}</span>
      </template>
    </span>
  </span>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'

const props = defineProps({
  value: { type: [Number, String], default: 0 },
  // 'pop' | 'reel'
  mode: { type: String, default: 'pop' },
  decimals: { type: Number, default: 0 }
})

const root = ref(null)
const popChars = ref([])
const animating = ref(false)

const reelSegs = computed(() => {
  const s = formatValue(props.value)
  return s.split('').map((ch) => ({ type: /\d/.test(ch) ? 'digit' : 'sep', value: ch }))
})

function formatValue(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return String(v)
  return n.toLocaleString('en-US', {
    minimumFractionDigits: props.decimals,
    maximumFractionDigits: props.decimals
  })
}

function popStagger(i) {
  const last = popChars.value.length
  if (i === last - 2) return '1'
  if (i === last - 1) return '2'
  return undefined
}

function renderPop(animate) {
  popChars.value = formatValue(props.value).split('')
  if (animate) {
    animating.value = false
    nextTick(() => {
      if (!root.value) return
      void root.value.offsetHeight
      animating.value = true
    })
  }
}

function applyReel() {
  nextTick(() => {
    if (!root.value) return
    const cols = root.value.querySelectorAll('.t-reel-col')
    if (!cols.length) return
    const cs = getComputedStyle(document.documentElement)
    const cell = parseFloat(cs.getPropertyValue('--reel-cell')) || 30
    const dur = cs.getPropertyValue('--reel-dur').trim() || '1400ms'
    const ease = cs.getPropertyValue('--reel-ease').trim() || 'cubic-bezier(0.16,1,0.3,1)'
    const stagger = parseFloat(cs.getPropertyValue('--reel-stagger')) || 90
    const digits = formatValue(props.value)
      .split('')
      .filter((c) => /\d/.test(c))
    cols.forEach((col, i) => {
      const d = Number(digits[i] || 0)
      const spins = 2
      const offset = (spins * 10 + d) * cell
      const strip = col.querySelector('.t-reel-strip')
      strip.style.transition = `transform ${dur} ${ease} ${i * stagger}ms, filter ${dur} ${ease} ${i * stagger}ms`
      strip.style.transform = `translateY(${-offset}px)`
      strip.style.filter = 'blur(var(--reel-spin-blur))'
      setTimeout(() => {
        strip.style.filter = 'blur(0)'
      }, i * stagger)
    })
  })
}

onMounted(() => {
  if (props.mode === 'pop') renderPop(false)
  else applyReel()
})

watch(
  () => props.value,
  () => {
    if (props.mode === 'pop') renderPop(true)
    else applyReel()
  }
)
</script>

<style scoped>
.t-animated-number {
  display: inline-flex;
  align-items: baseline;
  font-variant-numeric: tabular-nums;
}
.t-reel-sep {
  display: inline-flex;
  align-items: center;
  padding: 0 1px;
}
</style>
