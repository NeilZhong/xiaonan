<script setup>
/**
 * ★ 任务看板 — Multica 风格多列 Kanban (POLICE_REQUIREMENTS §8.4.10)
 * 六列：待确认 / 待开始 / 进行中 / 审核中 / 已完成 / 已归档
 * 待确认列的任务由推进智能体生成，点击进入「草案审查」抽屉。
 */
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePoliceStore } from '@/stores/police'
import { message } from 'ant-design-vue'
import {
  ArrowLeftOutlined, AppstoreOutlined, UnorderedListOutlined, SettingOutlined
} from '@ant-design/icons-vue'
import TaskCard from '@/components/police/TaskCard.vue'
import TaskDraftReviewDrawer from '@/components/police/TaskDraftReviewDrawer.vue'

const typeText = {
  transcript_analysis: '笔录分析', fund_analysis: '资金分析', evidence_collection: '调证生成',
  evidence_submission: '证据提交', legal_review: '法制审核', document_generation: '文书生成',
  investigation: '侦查', interrogation: '审讯', arrest: '抓捕', cyber_inquiry: '网警查询',
  knowledge_extraction: '知识抽取',
}
const priorityColor = { urgent: 'red', high: 'orange', medium: 'gold', low: 'green' }
const statusText = {
  pending_confirmation: '待确认', pending: '待开始', in_progress: '进行中', review: '审核中',
  completed: '已完成', suspended: '已暂停', terminated: '已终止', cancelled: '已取消', blocked: '已驳回',
}
const statusBadge = {
  pending_confirmation: 'warning', pending: 'default', in_progress: 'processing', review: 'warning',
  completed: 'success', suspended: 'default', terminated: 'default', cancelled: 'default', blocked: 'error',
}
const listColumns = [
  { title: '任务', dataIndex: 'title', key: 'title', ellipsis: true },
  { title: '案件', dataIndex: 'case_id', key: 'case_id', width: 80 },
  { title: '类型', dataIndex: 'type', key: 'type', width: 120 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '创建者', key: 'creator', width: 80 },
  { title: '优先级', dataIndex: 'priority', key: 'priority', width: 80 },
  { title: '操作', key: 'action', width: 80 },
]
const archivedStatuses = ['suspended', 'terminated', 'cancelled', 'blocked']

const route = useRoute()
const router = useRouter()
const policeStore = usePoliceStore()

const viewMode = ref('kanban')
const loading = ref(false)
const filterCaseId = ref(undefined)
const showArchived = ref(true)
const caseOptions = computed(() =>
  (policeStore.cases || []).map((c) => ({ value: c.id, label: `${c.title} #${c.id}` }))
)

const columnsDef = [
  { key: 'pending_confirmation', title: '待确认', color: '#B7791F' },
  { key: 'pending', title: '待开始', color: '#718096' },
  { key: 'in_progress', title: '进行中', color: '#3182CE' },
  { key: 'review', title: '审核中', color: '#DD6B20' },
  { key: 'completed', title: '已完成', color: '#38A169' },
  { key: 'archived', title: '已归档', color: '#A0AEC0' },
]

const statusColumns = computed(() =>
  columnsDef.filter((c) => c.key !== 'archived' || showArchived.value)
)

const tasksByStatus = computed(() => {
  const map = {}
  for (const col of columnsDef) {
    if (col.key === 'archived') {
      map[col.key] = policeStore.tasks.filter((t) => archivedStatuses.includes(t.status))
    } else {
      map[col.key] = policeStore.tasks.filter((t) => t.status === col.key)
    }
  }
  return map
})

async function loadData() {
  loading.value = true
  try {
    await policeStore.loadTasks({ case_id: filterCaseId.value, page_size: 500 })
  } finally {
    loading.value = false
  }
}

function goTask(taskId) {
  router.push(`/police/tasks/${taskId}`)
}
function onClickTask(task) {
  if (task.status === 'pending_confirmation') openDraft(task)
  else goTask(task.id)
}

// ── 草案审查抽屉 ──────────────────────────────────────────
const draftOpen = ref(false)
const currentDraft = ref(null)
function openDraft(task) {
  currentDraft.value = task
  draftOpen.value = true
}
async function onDraftConfirmed() {
  await loadData()
  await policeStore.loadMyDrafts()
}
async function onDraftRejected() {
  await loadData()
  await policeStore.loadMyDrafts()
}

// ── 推进设置（选中具体案件时可用）─────────────────────────
const advanceOpen = ref(false)
const advEnabled = ref(true)
const advDirection = ref('')
async function openAdvance() {
  if (!filterCaseId.value) {
    message.info('请先选择具体案件')
    return
  }
  await policeStore.loadCase(filterCaseId.value)
  advEnabled.value = policeStore.currentCase?.advancement_enabled === 1
  advDirection.value = policeStore.currentCase?.investigation_direction || ''
  advanceOpen.value = true
}
async function saveAdvance() {
  if (!filterCaseId.value) return
  try {
    await policeStore.toggleAdvancement(filterCaseId.value, advEnabled.value)
    if (advDirection.value.trim()) {
      await policeStore.changeDirection(filterCaseId.value, advDirection.value.trim())
      message.success('侦查方向已更新，推进智能体正在重新规划任务')
    } else {
      message.success('推进设置已保存')
    }
    advanceOpen.value = false
    await loadData()
  } catch (e) {
    message.error('保存失败：' + (e.message || e))
  }
}

onMounted(async () => {
  await policeStore.loadCases({ page_size: 200 })
  if (route.query.case_id) filterCaseId.value = Number(route.query.case_id)
  await loadData()
  await policeStore.loadMyDrafts()
  if (route.query.draft_id) {
    const t = policeStore.tasks.find((x) => x.id === Number(route.query.draft_id))
    if (t) openDraft(t)
  }
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
        <h1 class="page-title">任务看板</h1>
        <a-tag v-if="filterCaseId" color="blue">案件 #{{ filterCaseId }}</a-tag>
      </div>
      <div class="header-right">
        <a-button v-if="filterCaseId" type="default" size="small" @click="openAdvance">
          <template #icon><SettingOutlined /></template>
          推进设置
        </a-button>
        <a-radio-group v-model:value="viewMode" button-style="solid" size="small">
          <a-radio-button value="kanban"><AppstoreOutlined /> 看板</a-radio-button>
          <a-radio-button value="list"><UnorderedListOutlined /> 列表</a-radio-button>
        </a-radio-group>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="filter-bar">
      <a-select
        v-model:value="filterCaseId"
        placeholder="全部案件"
        style="width: 240px"
        allow-clear
        :options="caseOptions"
        @change="loadData"
      />
      <a-checkbox v-model:checked="showArchived">显示已归档</a-checkbox>
    </div>

    <!-- 看板视图 -->
    <div v-if="viewMode === 'kanban'" class="kanban-board">
      <div v-for="col in statusColumns" :key="col.key" class="kanban-column">
        <div class="kanban-column-header" :style="{ borderTopColor: col.color }">
          <span class="column-title">{{ col.title }}</span>
          <span class="column-count">{{ tasksByStatus[col.key]?.length || 0 }}</span>
        </div>
        <div class="kanban-column-body">
          <TaskCard
            v-for="task in (tasksByStatus[col.key] || [])"
            :key="task.id"
            :task="task"
            @click="onClickTask"
          />
          <div v-if="!tasksByStatus[col.key]?.length" class="kanban-empty">暂无任务</div>
        </div>
      </div>
    </div>

    <!-- 列表视图 -->
    <div v-else class="table-card">
      <a-table
        :columns="listColumns"
        :data-source="policeStore.tasks"
        :loading="loading"
        row-key="id"
        size="middle"
        :pagination="{ pageSize: 20, showSizeChanger: true }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'title'">
            <a class="task-link" @click="onClickTask(record)">{{ record.title }}</a>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-badge :status="statusBadge[record.status]" :text="statusText[record.status]" />
          </template>
          <template v-else-if="column.key === 'type'">
            {{ typeText[record.type] || record.type }}
          </template>
          <template v-else-if="column.key === 'priority'">
            <a-tag :color="priorityColor[record.priority]">{{ record.priority }}</a-tag>
          </template>
          <template v-else-if="column.key === 'creator'">
            <a-tag v-if="record.creator_type === 'agent'" color="purple">AI</a-tag>
            <span v-else>民警</span>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-button type="link" size="small" @click="onClickTask(record)">详情</a-button>
          </template>
        </template>
      </a-table>
    </div>

    <!-- 草案审查抽屉 -->
    <TaskDraftReviewDrawer
      v-model:open="draftOpen"
      :draft="currentDraft"
      @confirmed="onDraftConfirmed"
      @rejected="onDraftRejected"
    />

    <!-- 推进设置弹窗 -->
    <a-modal v-model:open="advanceOpen" title="案件推进设置" @ok="saveAdvance">
      <a-form layout="vertical">
        <a-form-item label="推进智能体">
          <a-switch v-model:checked="advEnabled" checked-children="启用" un-checked-children="停用" />
          <span class="hint">关闭后为纯手动模式，不再自动生成任务草案</span>
        </a-form-item>
        <a-form-item label="侦查方向">
          <a-textarea v-model:value="advDirection" :rows="2" placeholder="如：电信诈骗资金链条追查" />
          <span class="hint">调整后推进智能体将基于新方向重新规划任务</span>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<style scoped>
.task-board-page {
  padding: 24px 32px;
  max-width: 1700px;
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
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}
.hint {
  display: block;
  font-size: 12px;
  color: var(--gray-400, #a0aec0);
  margin-top: 4px;
}
.kanban-board {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 8px;
  align-items: flex-start;
}
.kanban-column {
  min-width: 270px;
  flex: 1;
  background: var(--gray-10, #f7fafc);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 220px);
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
  overflow-y: auto;
}
.kanban-empty {
  text-align: center;
  color: var(--gray-400, #a0aec0);
  padding: 24px 0;
  font-size: 13px;
}
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
