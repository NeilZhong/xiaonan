<template>
  <div class="audit-overview">
    <a-card :loading="loading" class="audit-card" :bordered="false">
      <template #title>
        <div class="audit-title">
          <span>审计概览</span>
          <a-tag color="default" class="audit-badge">合规留痕</a-tag>
        </div>
      </template>
      <template #extra>
        <a @click="emit('open-audit')" class="audit-link">查看全部 ›</a>
      </template>

      <div class="audit-stats">
        <div class="audit-stat">
          <div class="audit-stat-value">{{ stats.today_ops }}</div>
          <div class="audit-stat-label">今日操作</div>
        </div>
        <div class="audit-stat">
          <div class="audit-stat-value warn">{{ stats.anomaly_ops }}</div>
          <div class="audit-stat-label">异常操作</div>
        </div>
      </div>

      <div class="audit-recent">
        <div class="audit-recent-title">最近事件</div>
        <a-empty v-if="!stats.recent_events || stats.recent_events.length === 0" :image="simpleImage" description="暂无审计记录" />
        <ul v-else class="audit-event-list">
          <li v-for="ev in stats.recent_events.slice(0, 4)" :key="ev.id" class="audit-event">
            <a-tag :color="actionColor(ev.action)" size="small">{{ actionLabel(ev.action) }}</a-tag>
            <span class="audit-event-user">{{ ev.user_name || '系统' }}</span>
            <span class="audit-event-time">{{ formatTime(ev.created_at) }}</span>
          </li>
        </ul>
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { Empty } from 'ant-design-vue'
import { dashboardApi } from '@/apis/dashboard_api'

const emit = defineEmits(['open-audit'])

const simpleImage = Empty.PRESENTED_IMAGE_SIMPLE

const stats = ref({ today_ops: 0, anomaly_ops: 0, recent_events: [] })
const loading = ref(false)

const ACTION_LABELS = {
  create: '创建', update: '更新', delete: '删除',
  review: '审核通过', reject: '审核驳回', assign: '分配',
  start: '启动', complete: '完成', phase_change: '阶段变更',
  add_member: '添加成员', share: '发布'
}

const ACTION_COLORS = {
  delete: 'red', reject: 'volcano', create: 'green', review: 'blue',
  update: 'geekblue', assign: 'cyan', start: 'gold', complete: 'green',
  phase_change: 'purple', add_member: 'lime', share: 'blue'
}

const actionLabel = (a) => ACTION_LABELS[a] || a
const actionColor = (a) => ACTION_COLORS[a] || 'default'

const formatTime = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const load = async () => {
  loading.value = true
  try {
    const res = await dashboardApi.getAuditStats()
    stats.value = res.data || { today_ops: 0, anomaly_ops: 0, recent_events: [] }
  } catch (e) {
    console.error('加载审计概览失败:', e)
    message.error('加载审计概览失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style lang="less" scoped>
.audit-overview {
  height: 100%;
}

.audit-card {
  border-radius: 12px;
  border: 1px solid var(--gray-200);
  height: 100%;
}

.audit-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--gray-1000);
}

.audit-badge {
  font-size: 11px;
  line-height: 18px;
  margin: 0;
}

.audit-link {
  color: var(--main-color);
  cursor: pointer;
  font-size: 13px;
  &:hover {
    opacity: 0.8;
  }
}

.audit-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 16px;
}

.audit-stat {
  background: var(--gray-25);
  border-radius: 8px;
  padding: 14px 16px;
  text-align: center;

  .audit-stat-value {
    font-size: 26px;
    font-weight: 700;
    color: var(--gray-1000);
    line-height: 1.1;

    &.warn {
      color: var(--color-warning-700);
    }
  }

  .audit-stat-label {
    font-size: 12px;
    color: var(--gray-600);
    margin-top: 4px;
  }
}

.audit-recent-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-800);
  margin-bottom: 8px;
}

.audit-event-list {
  list-style: none;
  margin: 0;
  padding: 0;

  .audit-event {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 0;
    border-bottom: 1px dashed var(--gray-100);
    font-size: 13px;

    &:last-child {
      border-bottom: none;
    }

    .audit-event-user {
      color: var(--gray-800);
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .audit-event-time {
      color: var(--gray-500);
      font-size: 12px;
    }
  }
}
</style>
