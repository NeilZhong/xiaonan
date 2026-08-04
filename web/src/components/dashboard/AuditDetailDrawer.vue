<template>
  <a-drawer
    :open="open"
    title="审计日志"
    width="920"
    @close="emit('update:open', false)"
  >
    <template #extra>
      <a-button type="primary" ghost size="small" :loading="verifying" @click="verifyChain">
        <template #icon><SafetyCertificateOutlined /></template>
        校验哈希链
      </a-button>
    </template>

    <a-form layout="inline" class="audit-filters">
      <a-form-item label="操作">
        <a-select
          v-model:value="filters.action"
          placeholder="全部"
          allow-clear
          style="width: 130px"
          :options="actionOptions"
        />
      </a-form-item>
      <a-form-item label="操作人ID">
        <a-input-number v-model:value="filters.user_id" :min="1" placeholder="全部" style="width: 110px" />
      </a-form-item>
      <a-form-item label="案件ID">
        <a-input-number v-model:value="filters.case_id" :min="1" placeholder="全部" style="width: 110px" />
      </a-form-item>
      <a-form-item label="起始">
        <a-date-picker v-model:value="filters.from" value-format="YYYY-MM-DD" />
      </a-form-item>
      <a-form-item label="截止">
        <a-date-picker v-model:value="filters.to" value-format="YYYY-MM-DD" />
      </a-form-item>
      <a-form-item>
        <a-button type="primary" :loading="loading" @click="loadLogs">查询</a-button>
      </a-form-item>
    </a-form>

    <a-table
      :columns="columns"
      :data-source="items"
      :loading="loading"
      :pagination="{ pageSize: 20, total, showTotal: (t) => `共 ${t} 条` }"
      size="small"
      row-key="id"
      class="audit-table"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <a-tag :color="actionColor(record.action)" size="small">{{ actionLabel(record.action) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'created_at'">
          {{ formatTime(record.created_at) }}
        </template>
        <template v-else-if="column.key === 'record_hash'">
          <span class="hash">{{ (record.record_hash || '—').slice(0, 12) }}</span>
        </template>
        <template v-else-if="column.key === 'details'">
          <span class="details">{{ summarize(record.details) }}</span>
        </template>
      </template>
    </a-table>
  </a-drawer>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { message } from 'ant-design-vue'
import { SafetyCertificateOutlined } from '@ant-design/icons-vue'
import { dashboardApi } from '@/apis/dashboard_api'

const props = defineProps({ open: Boolean })
const emit = defineEmits(['update:open'])

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
const actionOptions = Object.entries(ACTION_LABELS).map(([value, label]) => ({ value, label }))

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 70 },
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 140 },
  { title: '操作', dataIndex: 'action', key: 'action', width: 90 },
  { title: '资源', dataIndex: 'resource_type', key: 'resource_type', width: 90 },
  { title: '操作人', dataIndex: 'user_name', key: 'user_name', width: 90 },
  { title: '案件', dataIndex: 'case_id', key: 'case_id', width: 70 },
  { title: 'IP', dataIndex: 'ip_address', key: 'ip_address', width: 120 },
  { title: '摘要', dataIndex: 'details', key: 'details' },
  { title: '哈希', dataIndex: 'record_hash', key: 'record_hash', width: 110 }
]

const filters = reactive({ action: undefined, user_id: undefined, case_id: undefined, from: undefined, to: undefined })
const items = ref([])
const total = ref(0)
const loading = ref(false)
const verifying = ref(false)

const formatTime = (iso) => {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

const summarize = (details) => {
  if (!details) return '—'
  try {
    const s = typeof details === 'string' ? details : JSON.stringify(details)
    return s.length > 40 ? s.slice(0, 40) + '…' : s
  } catch {
    return '—'
  }
}

const loadLogs = async () => {
  loading.value = true
  try {
    const params = {}
    if (filters.action) params.action = filters.action
    if (filters.user_id) params.user_id = filters.user_id
    if (filters.case_id) params.case_id = filters.case_id
    if (filters.from) params.from = filters.from
    if (filters.to) params.to = filters.to
    params.limit = 50
    params.offset = 0
    const res = await dashboardApi.getAuditLogs(params)
    items.value = res.data?.items || []
    total.value = res.data?.total || 0
  } catch (e) {
    console.error('查询审计日志失败:', e)
    message.error('查询审计日志失败')
  } finally {
    loading.value = false
  }
}

const verifyChain = async () => {
  verifying.value = true
  try {
    const res = await dashboardApi.verifyAuditChain(5000)
    const d = res.data || {}
    if (d.ok) {
      message.success(`哈希链完整：已校验 ${d.checked} 条${d.legacy_count ? `，遗留 ${d.legacy_count} 条未上链` : ''}`)
    } else {
      message.error(`哈希链在记录 #${d.broken_at} 处断裂（已校验 ${d.checked} 条）`)
    }
  } catch (e) {
    console.error('校验哈希链失败:', e)
    message.error('校验哈希链失败')
  } finally {
    verifying.value = false
  }
}
</script>

<style lang="less" scoped>
.audit-filters {
  margin-bottom: 16px;
  row-gap: 12px;
}

.audit-table {
  .hash {
    font-family: monospace;
    font-size: 12px;
    color: var(--gray-600);
  }
  .details {
    color: var(--gray-700);
    font-size: 12px;
  }
}
</style>
