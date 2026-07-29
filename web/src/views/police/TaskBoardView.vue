<script setup>
/**
 * ★ 任务看板 — Plane 风格 Kanban
 * POLICE_REQUIREMENTS §4.2.4 §8.4.4
 */
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePoliceStore } from '@/stores/police'
import { message } from 'ant-design-vue'
import {
  ArrowLeftOutlined, AppstoreOutlined, UnorderedListOutlined
} from '@ant-design/icons-vue'

const route = useRoute()
const router = useRouter()
const policeStore = usePoliceStore()

const viewMode = ref('kanban') // kanban / list
const loading = ref(false)
const filterCaseId = ref(undefined)
const filterStatus = ref(undefined)

const statusColumns = [
  { key: 'pending', title: '待处理', color: '#718096' },
  { key: 'in_progress', title: '进行中', color: '#3182CE' },
  { key: 'review', title: '待审核', color: '#D69E2E' },
  { key: 'completed', title: '已完成', color: '#38A169' },
  { key: 'blocked', title: '已驳回', color: '#E53E3E' },
]

const typeText = {
  transcript_analysis: '笔录分析', fund_analysis: '资金分析', evidence_collection: '调证生成',
  evidence_submission: '证据提交', legal_review: '法制审核', document_generation: '文书生成',
  investigation: '侦查', interrogation: '审讯', arrest: '抓捕', cyber_inquiry: '网警查询',
  knowledge_extraction: '知识抽取',
}

const priorityColor = { urgent: 'red', high: 'orange', medium: 'blue', low: 'default' }

const columns = [
  { title: '任务', dataIndex: 'title', key: 'title', ellipsis: true },
  { title: '案件', dataIndex: 'case_id', key: 'case_id', width: 80 },
  { title: '类型', dataIndex: 'type', key: 'type', width: 120 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '分配给', dataIndex: 'assignee_name', key: 'assignee_name', width: 120 },
  { title: '优先级', dataIndex: 'priority', key: 'priority', width: 80 },
  { title: '操作', key: 'action', width: 80 },
]

const tasksByStatus = computed(() => {
  const map = {}
  for (const col of statusColumns) {
    map[col.key] = policeStore.tasks.filter(t => t.status === col.key)
  }
  return map
})

async function loadData() {
  loading.value = true
  try {
    await policeStore.loadTasks({
      case_id: filterCaseId.value,
      status: filterStatus.value,
      page_size: 200,
    })
  } finally {
    loading.value = false
  }
}

function goTask(taskId) {
  router.push(`/police/tasks/${taskId}`)
}

const statusText = { pending: '待处理', in_progress: '进行中', review: '待审核', completed: '已完成', blocked: '已驳回' }
const statusColor = { pending: 'default', in_progress: 'processing', review: 'warning', completed: 'success', blocked: 'error' }

onMounted(() => {
  // 支持 URL 参数 ?status=review
  if (route.query.status) filterStatus.value = route.query.status
  loadData()
})
</script>

<template>
  <div class="task-board-page">
    <!-- 页头 -->
    <div class="page-header">
      <div class="header-left">
        <a-button type="text" @click="router.push('/police')">
          <template #icon><ArrowLeftOutlined /></template>
          返回
        </a-button>
        <h1 class="page-title">任务管理</h1>
      </div>
      <div class="header-right">
        <a-radio-group v-model:value="viewMode" button-style="solid" size="small">
          <a-radio-button value="kanban"><AppstoreOutlined /> 看板</a-radio-button>
          <a-radio-button value="list"><UnorderedListOutlined /> 列表</a-radio-button>
        </a-radio-group>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="filter-bar">
      <a-input-number v-model:value="filterCaseId" placeholder="案件ID" style="width: 120px" allow-clear @change="loadData" />
      <a-select v-model:value="filterStatus" placeholder="状态" style="width: 140px" allow-clear @change="loadData">
        <a-select-option v-for="col in statusColumns" :key="col.key" :value="col.key">{{ col.title }}</a-select-option>
      </a-select>
    </div>

    <!-- 看板视图 -->
    <div v-if="viewMode === 'kanban'" class="kanban-board">
      <div v-for="col in statusColumns" :key="col.key" class="kanban-column">
        <div class="kanban-column-header" :style="{ borderTopColor: col.color }">
          <span class="column-title">{{ col.title }}</span>
          <span class="column-count">{{ tasksByStatus[col.key]?.length || 0 }}</span>
        </div>
        <div class="kanban-column-body">
          <div
            v-for="task in (tasksByStatus[col.key] || [])"
            :key="task.id"
            class="kanban-card"
            @click="goTask(task.id)"
          >
            <div class="card-title">{{ task.title }}</div>
            <div class="card-meta">
              <a-tag size="small">{{ typeText[task.type] || task.type }}</a-tag>
              <a-tag :color="priorityColor[task.priority]" size="small">{{ task.priority }}</a-tag>
            </div>
            <div class="card-footer">
              <span class="card-assignee">
                <a-avatar size="small" style="background: var(--main-color, #24839b)">
                  {{ (task.assignee_name || '?')[0] }}
                </a-avatar>
                <span>{{ task.assignee_name || '未分配' }}</span>
              </span>
              <span class="card-case">#{{ task.case_id }}</span>
            </div>
          </div>
          <div v-if="!tasksByStatus[col.key]?.length" class="kanban-empty">暂无任务</div>
        </div>
      </div>
    </div>

    <!-- 列表视图 -->
    <div v-else class="table-card">
      <a-table
        :columns="columns"
        :data-source="policeStore.tasks"
        :loading="loading"
        row-key="id"
        size="middle"
        :pagination="{ pageSize: 20, showSizeChanger: true }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'title'">
            <a class="task-link" @click="goTask(record.id)">{{ record.title }}</a>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-badge :status="statusColor[record.status]" :text="statusText[record.status]" />
          </template>
          <template v-else-if="column.key === 'type'">
            {{ typeText[record.type] || record.type }}
          </template>
          <template v-else-if="column.key === 'priority'">
            <a-tag :color="priorityColor[record.priority]">{{ record.priority }}</a-tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-button type="link" size="small" @click="goTask(record.id)">详情</a-button>
          </template>
        </template>
      </a-table>
    </div>
  </div>
</template>

<style scoped>
.task-board-page {
  padding: 24px 32px;
  max-width: 1600px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-title {
  font-size: 22px;
  font-weight: 600;
  margin: 0;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

/* 看板 */
.kanban-board {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 8px;
}

.kanban-column {
  min-width: 260px;
  flex: 1;
  background: var(--gray-10, #f7fafc);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
}

.kanban-column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-top: 3px solid;
  border-radius: 10px 10px 0 0;
}

.column-title {
  font-size: 14px;
  font-weight: 600;
}

.column-count {
  font-size: 12px;
  background: var(--gray-50, #e2e8f0);
  padding: 2px 8px;
  border-radius: 10px;
  color: var(--gray-600, #4a5568);
}

.kanban-column-body {
  padding: 8px;
  flex: 1;
  min-height: 100px;
}

.kanban-card {
  background: var(--gray-0, #fff);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: box-shadow 0.15s;
}

.kanban-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}

.card-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 8px;
  line-height: 1.4;
}

.card-meta {
  display: flex;
  gap: 4px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--gray-500, #718096);
}

.card-assignee {
  display: flex;
  align-items: center;
  gap: 4px;
}

.kanban-empty {
  text-align: center;
  color: var(--gray-400, #a0aec0);
  padding: 24px 0;
  font-size: 13px;
}

/* 列表 */
.table-card {
  background: var(--gray-0, #fff);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 12px;
  overflow: hidden;
}

.task-link {
  color: var(--main-color, #24839b);
  cursor: pointer;
  font-weight: 500;
}
</style>
