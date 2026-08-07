<template>
  <div class="source-section">
    <div class="section-title">知识库来源 ({{ citedChunks.length }})</div>
    <KbResultGroupedList
      :chunks="citedChunks"
      :show-summary="false"
      :citation-label-map="citationLabelMap"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import KbResultGroupedList from '@/components/sources/KbResultGroupedList.vue'

const props = defineProps({
  chunks: {
    type: Array,
    default: () => []
  },
  citedChunkIds: {
    type: Set,
    default: () => new Set()
  },
  citationLabelMap: {
    type: Map,
    default: () => new Map()
  }
})

// 只展示正文实际引用的片段，未引用的检索结果不出现在来源中。
const citedChunks = computed(() =>
  props.chunks.filter((chunk) =>
    props.citedChunkIds.has(String(chunk?.metadata?.chunk_id || '').trim())
  )
)
</script>

<style scoped lang="less">
.source-section {
  .section-title {
    font-size: 12px;
    color: var(--gray-700);
    margin-bottom: 8px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
  }
}
</style>
