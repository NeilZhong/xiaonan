<script setup>
/**
 * ★ 案件时间线 Tab
 */
import { onMounted, ref, watch } from 'vue'
import { policeCaseApi } from '@/apis/police_api'
import { ClockCircleOutlined } from '@ant-design/icons-vue'

const props = defineProps({ caseId: { type: Number, required: true } })
const timeline = ref([])
const loading = ref(false)

const eventText = {
  created: '创建', assigned: '分配', started: '开始', completed: '完成',
  reviewed: '审核', blocked: '驳回', file_uploaded: '上传文件', phase_change: '阶段变更',
}

async function loadData() {
  loading.value = true
  try {
    const res = await policeCaseApi.timeline(props.caseId)
    timeline.value = res.data || []
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
watch(() => props.caseId, loadData)
</script>

<template>
  <div class="timeline-tab">
    <a-timeline v-if="timeline.length">
      <a-timeline-item v-for="(item, idx) in timeline" :key="idx">
        <template #dot><ClockCircleOutlined /></template>
        <div class="timeline-content">
          <div class="timeline-title">
            <span class="event-type">{{ eventText[item.event_type] || item.event_type }}</span>
            <span v-if="item.task_title" class="event-task"> — {{ item.task_title }}</span>
          </div>
          <div class="timeline-desc" v-if="item.event_data && Object.keys(item.event_data).length">
            {{ JSON.stringify(item.event_data).substring(0, 200) }}
          </div>
          <div class="timeline-time">{{ item.created_at }}</div>
        </div>
      </a-timeline-item>
    </a-timeline>
    <a-empty v-else description="暂无动态" style="padding: 40px" />
  </div>
</template>

<style scoped>
.timeline-tab { padding: 12px 0; max-height: 600px; overflow-y: auto; }
.timeline-content { padding-bottom: 4px; }
.timeline-title { font-size: 14px; font-weight: 500; }
.event-type { color: var(--main-color, #24839b); }
.event-task { color: var(--gray-600, #4a5568); }
.timeline-desc { font-size: 12px; color: var(--gray-500, #718096); margin: 2px 0; }
.timeline-time { font-size: 12px; color: var(--gray-400, #a0aec0); }
</style>
