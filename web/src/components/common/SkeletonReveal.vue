<template>
  <!-- 骨架屏 → 内容交叉淡入（skeleton-reveal）。
       用 grid 同格堆叠避免原 absolute 方案容器塌陷；动画变量沿用 transitions.css 的 --reveal-* / --pulse-*。 -->
  <div class="sk-reveal" :class="{ 'is-revealed': !loading }">
    <div class="sk-reveal-skeleton" :class="{ 'is-pulsing': pulse }" aria-hidden="true">
      <slot name="skeleton">
        <div v-for="n in rows" :key="n" class="sk-bar" :style="{ width: barWidth(n) }" />
      </slot>
    </div>
    <div class="sk-reveal-content">
      <slot />
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  // true=显示骨架，false=显示内容（已加载）
  loading: { type: Boolean, default: false },
  // 默认骨架条数
  rows: { type: Number, default: 3 },
  // 是否脉冲呼吸
  pulse: { type: Boolean, default: true }
})

// 让骨架条长短不一，更贴近真实内容
function barWidth(n) {
  const widths = ['92%', '78%', '85%', '70%', '88%', '64%']
  return widths[(n - 1) % widths.length]
}
</script>

<style scoped>
.sk-reveal {
  display: grid;
}
.sk-reveal-skeleton,
.sk-reveal-content {
  grid-area: 1 / 1;
}
.sk-reveal-skeleton {
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  opacity: 1;
  filter: blur(0);
  transition:
    opacity var(--reveal-dur, 420ms) var(--reveal-ease, ease),
    filter  var(--reveal-dur, 420ms) var(--reveal-ease, ease);
}
.sk-reveal-content {
  z-index: 2;
  opacity: 0;
  filter: blur(var(--reveal-blur, 6px));
  transition:
    opacity var(--reveal-dur, 420ms) var(--reveal-ease, ease),
    filter  var(--reveal-dur, 420ms) var(--reveal-ease, ease);
}
.sk-reveal.is-revealed .sk-reveal-skeleton {
  opacity: 0;
  filter: blur(var(--reveal-blur, 6px));
}
.sk-reveal.is-revealed .sk-reveal-content {
  opacity: 1;
  filter: blur(0);
}
.sk-reveal-skeleton.is-pulsing > .sk-bar {
  animation: t-skel-pulse var(--pulse-dur, 1.4s) ease-in-out infinite;
}
.sk-bar {
  height: 16px;
  border-radius: 6px;
  background: var(--gray-200, #eef0f3);
}
:root.dark .sk-bar {
  background: var(--gray-800, #2a2f3a);
}
@media (prefers-reduced-motion: reduce) {
  .sk-reveal-skeleton,
  .sk-reveal-content {
    transition: none !important;
  }
  .sk-reveal-skeleton.is-pulsing > .sk-bar {
    animation: none !important;
  }
  .sk-reveal-content {
    opacity: 1;
    filter: none;
  }
}
</style>
