<template>
  <!-- 双页滑动（page-side-by-side）：同一容器内 list ↔ detail 平滑切换。
       动画变量沿用 transitions.css 的 --page-*。page 取值 1|2。 -->
  <div class="t-page-slide" :data-page="page">
    <div class="t-page" data-page-id="1">
      <slot name="page1" />
    </div>
    <div class="t-page" data-page-id="2">
      <slot name="page2" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  // 当前页：1=列表，2=详情
  page: { type: Number, default: 1 }
})
</script>

<style scoped>
.t-page-slide {
  position: relative;
  height: 100%;
}
.t-page-slide .t-page {
  position: absolute;
  inset: 0;
  height: 100%;
}
@media (prefers-reduced-motion: reduce) {
  .t-page-slide .t-page {
    transition: none !important;
  }
}
</style>
