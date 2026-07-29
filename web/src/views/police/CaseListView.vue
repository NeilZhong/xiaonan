<script setup>
/**
 * ★ 案件列表 — Plane 风格表格视图
 * POLICE_REQUIREMENTS §8.4.2
 */
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePoliceStore } from '@/stores/police'
import { message, Modal } from 'ant-design-vue'
import { PlusOutlined, SearchOutlined } from '@ant-design/icons-vue'

const router = useRouter()
const policeStore = usePoliceStore()

const loading = ref(false)
const keyword = ref('')
const statusFilter = ref(undefined)
const phaseFilter = ref(undefined)
const typeFilter = ref(undefined)
const showCreateModal = ref(false)

const statusOptions = [
  { label: '全部', value: undefined },
  { label: '草稿', value: 'draft' },
  { label: '侦查中', value: 'investigation' },
  { label: '抓捕阶段', value: 'arrest' },
  { label: '办理中', value: 'handling' },
  { label: '待移送', value: 'prosecution' },
  { label: '已结案', value: 'closed' },
]

const phaseOptions = [
  { label: '全部', value: undefined },
  { label: '研判', value: 'research' },
  { label: '抓捕', value: 'arrest' },
  { label: '办理', value: 'handling' },
  { label: '移送', value: 'prosecution' },
]

const statusText = { draft: '草稿', investigation: '侦查中', arrest: '抓捕', handling: '办理中', prosecution: '待移送', closed: '已结案' }
const statusColor = { draft: 'default', investigation: 'processing', arrest: 'warning', handling: 'blue', prosecution: 'orange', closed: 'success' }
const phaseText = { research: '研判', arrest: '抓捕', handling: '办理', prosecution: '移送' }

const columns = [
  { title: '案件编号', dataIndex: 'case_number', key: 'case_number', width: 140 },
  { title: '案件名称', dataIndex: 'title', key: 'title', ellipsis: true },
  { title: '类型', dataIndex: 'case_type', key: 'case_type', width: 100 },
  { title: '阶段', dataIndex: 'phase', key: 'phase', width: 100 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '涉案金额', dataIndex: 'total_amount', key: 'total_amount', width: 120, align: 'right' },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 120 },
  { title: '操作', key: 'action', width: 100, fixed: 'right' },
]

async function loadData(page = 1, pageSize = 20) {
  loading.value = true
  try {
    await policeStore.loadCases({
      page, page_size: pageSize,
      status: statusFilter.value,
      phase: phaseFilter.value,
      case_type: typeFilter.value,
      keyword: keyword.value || undefined,
    })
  } finally {
    loading.value = false
  }
}

function onSearch() {
  loadData(1)
}

function goDetail(record) {
  router.push(`/police/cases/${record.id}`)
}

// ── 创建案件 ──────────────────────────────────────────────
const createForm = ref({
  case_number: '',
  title: '',
  case_type: 'fraud',
  description: '',
  priority: 'medium',
  total_amount: null,
})

async function handleCreate() {
  if (!createForm.value.case_number || !createForm.value.title) {
    message.warning('请填写案件编号和名称')
    return
  }
  try {
    const data = await policeStore.createCase(createForm.value)
    message.success('案件创建成功')
    showCreateModal.value = false
    createForm.value = { case_number: '', title: '', case_type: 'fraud', description: '', priority: 'medium', total_amount: null }
    router.push(`/police/cases/${data.id}`)
  } catch (e) {
    message.error('创建失败: ' + (e.message || '未知错误'))
  }
}

onMounted(() => loadData(1))
</script>

<template>
  <div class="case-list-page">
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">案件管理</h1>
        <p class="page-subtitle">共 {{ policeStore.casesTotal }} 件案件</p>
      </div>
      <div class="header-actions">
        <a-button @click="router.push('/police')">
          <template #icon><PlusOutlined /></template>
          导入笔录
        </a-button>
        <a-button type="primary" @click="showCreateModal = true">
          <template #icon><PlusOutlined /></template>
          创建案件
        </a-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <a-input-search
        v-model:value="keyword"
        placeholder="搜索案件编号或名称"
        style="width: 280px"
        allow-clear
        @search="onSearch"
      />
      <a-select v-model:value="statusFilter" placeholder="状态" style="width: 120px" allow-clear @change="onSearch">
        <a-select-option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</a-select-option>
      </a-select>
      <a-select v-model:value="phaseFilter" placeholder="阶段" style="width: 120px" allow-clear @change="onSearch">
        <a-select-option v-for="opt in phaseOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</a-select-option>
      </a-select>
    </div>

    <!-- 案件表格 -->
    <div class="table-card">
      <a-table
        :columns="columns"
        :data-source="policeStore.cases"
        :loading="loading"
        :pagination="{
          current: 1,
          pageSize: 20,
          total: policeStore.casesTotal,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => loadData(p, ps),
        }"
        row-key="id"
        :scroll="{ x: 900 }"
        size="middle"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'case_number'">
            <a class="case-link" @click="goDetail(record)">{{ record.case_number }}</a>
          </template>
          <template v-else-if="column.key === 'title'">
            <a class="case-link" @click="goDetail(record)">{{ record.title }}</a>
          </template>
          <template v-else-if="column.key === 'phase'">
            <a-tag>{{ phaseText[record.phase] || record.phase }}</a-tag>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-badge :status="statusColor[record.status]" :text="statusText[record.status]" />
          </template>
          <template v-else-if="column.key === 'total_amount'">
            {{ record.total_amount ? '¥' + Number(record.total_amount).toLocaleString() : '—' }}
          </template>
          <template v-else-if="column.key === 'created_at'">
            {{ record.created_at?.substring(0, 10) }}
          </template>
          <template v-else-if="column.key === 'action'">
            <a-button type="link" size="small" @click="goDetail(record)">详情</a-button>
          </template>
        </template>
      </a-table>
    </div>

    <!-- 创建案件弹窗 -->
    <a-modal v-model:open="showCreateModal" title="创建案件" @ok="handleCreate" width="560px">
      <a-form layout="vertical" style="margin-top: 16px">
        <a-form-item label="案件编号" required>
          <a-input v-model:value="createForm.case_number" placeholder="如: A2026-001" />
        </a-form-item>
        <a-form-item label="案件名称" required>
          <a-input v-model:value="createForm.title" placeholder="如: 张某电信诈骗案" />
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="案件类型">
              <a-select v-model:value="createForm.case_type">
                <a-select-option value="fraud">诈骗</a-select-option>
                <a-select-option value="theft">盗窃</a-select-option>
                <a-select-option value="drug">毒品</a-select-option>
                <a-select-option value="economic">经济犯罪</a-select-option>
                <a-select-option value="other">其他</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="优先级">
              <a-select v-model:value="createForm.priority">
                <a-select-option value="urgent">紧急</a-select-option>
                <a-select-option value="high">高</a-select-option>
                <a-select-option value="medium">中</a-select-option>
                <a-select-option value="low">低</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="涉案金额">
          <a-input-number v-model:value="createForm.total_amount" style="width: 100%" :min="0" :precision="2" placeholder="0.00" />
        </a-form-item>
        <a-form-item label="案件描述">
          <a-textarea v-model:value="createForm.description" :rows="3" placeholder="简要描述案件情况" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<style scoped>
.case-list-page {
  padding: 24px 32px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 20px;
}

.page-title {
  font-size: 22px;
  font-weight: 600;
  margin: 0 0 4px 0;
}

.page-subtitle {
  font-size: 13px;
  color: var(--gray-500, #718096);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.table-card {
  background: var(--gray-0, #fff);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 12px;
  overflow: hidden;
}

.case-link {
  color: var(--main-color, #24839b);
  cursor: pointer;
  font-weight: 500;
}

.case-link:hover {
  text-decoration: underline;
}
</style>
