<script setup>
/**
 * ★ 侦查任务模板配置化 (POLICE_REQUIREMENTS §6.7)
 * 把「涉案要素 → 侦查任务」的映射规则开放给民警/管理员维护：
 *  - 模板表格（按要素类型分组、启停开关、内置/自定义标识、链式后继）
 *  - 新建 / 编辑抽屉（全部字段 + 占位符提示）
 *  - 渲染预览（用示例要素值填充占位符，所见即所得）
 *  - 一键植入内置侦查常识模板（幂等）
 */
import { onMounted, ref, computed } from 'vue'
import { usePoliceStore } from '@/stores/police'
import { useUserStore } from '@/stores/user'
import { message, Modal } from 'ant-design-vue'
import {
  PlusOutlined, ReloadOutlined, EyeOutlined, EditOutlined, DeleteOutlined,
  InfoCircleOutlined
} from '@ant-design/icons-vue'

const policeStore = usePoliceStore()
const userStore = useUserStore()

const loading = ref(false)
const filterElementType = ref(undefined)
const enabledOnly = ref(false)
const keyword = ref('')

const meta = computed(() => policeStore.taskTemplateMeta || null)
const elementTypeOptions = computed(() =>
  (meta.value?.element_types || []).map((t) => ({ value: t.value, label: t.label }))
)
const elementTypeMap = computed(() => {
  const m = {}
  for (const t of meta.value?.element_types || []) m[t.value] = t.label
  return m
})
const taskTypeMap = computed(() => {
  const m = {}
  for (const t of meta.value?.task_types || []) m[t.value] = t.label
  return m
})
const agentTypeMap = computed(() => {
  const m = {}
  for (const t of meta.value?.agent_types || []) m[t.value] = t.label
  return m
})
const priorityColor = { urgent: 'red', high: 'orange', medium: 'gold', low: 'green' }
const priorityLabel = { urgent: '紧急', high: '高', medium: '中', low: '低' }
const templateNameByCode = computed(() => {
  const m = {}
  for (const t of meta.value?.templates || []) m[t.code] = t.name
  return m
})

const columns = [
  { title: '模板名称', key: 'name', width: 200, fixed: 'left' },
  { title: '要素类型', dataIndex: 'element_label', key: 'element_label', width: 120 },
  { title: '生成任务', key: 'task', width: 260 },
  { title: '优先级', dataIndex: 'priority', key: 'priority', width: 90 },
  { title: '建议数字警员', key: 'agent', width: 160 },
  { title: '链式后继', key: 'chain', width: 200 },
  { title: '状态', key: 'enabled', width: 90 },
  { title: '来源', key: 'builtin', width: 90 },
  { title: '操作', key: 'action', width: 150, fixed: 'right' },
]

async function loadAll() {
  loading.value = true
  try {
    if (!meta.value) await policeStore.loadTaskTemplateMeta()
    await policeStore.loadTaskTemplates({
      element_type: filterElementType.value,
      enabled_only: enabledOnly.value,
      keyword: keyword.value || undefined,
    })
  } catch (e) {
    message.error('加载模板失败：' + (e?.message || e))
  } finally {
    loading.value = false
  }
}

const filteredRows = computed(() => policeStore.taskTemplates || [])

// ── 新建 / 编辑抽屉 ──────────────────────────────────────
const drawerOpen = ref(false)
const drawerMode = ref('create') // create | edit
const saving = ref(false)
const editingId = ref(null)
const formRef = ref()
const form = ref(emptyForm())

function emptyForm() {
  return {
    name: '',
    description: '',
    element_type: undefined,
    case_types: [],
    phases: [],
    source_task_types: [],
    task_title: '',
    task_type: 'investigation',
    task_description: '',
    instructions: '',
    priority: 'medium',
    suggested_agent_type: undefined,
    due_days: undefined,
    next_template_codes: [],
    enabled: 1,
  }
}

const rules = {
  name: [{ required: true, message: '请填写模板名称', trigger: 'blur' }],
  task_title: [{ required: true, message: '请填写生成任务标题模板', trigger: 'blur' }],
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
}

function openCreate() {
  drawerMode.value = 'create'
  editingId.value = null
  form.value = emptyForm()
  drawerOpen.value = true
}

function openEdit(record) {
  drawerMode.value = 'edit'
  editingId.value = record.id
  form.value = {
    name: record.name,
    description: record.description || '',
    element_type: record.element_type || undefined,
    case_types: record.case_types || [],
    phases: record.phases || [],
    source_task_types: record.source_task_types || [],
    task_title: record.task_title,
    task_type: record.task_type,
    task_description: record.task_description || '',
    instructions: record.instructions || '',
    priority: record.priority || 'medium',
    suggested_agent_type: record.suggested_agent_type || undefined,
    due_days: record.due_days ?? undefined,
    next_template_codes: record.next_template_codes || [],
    enabled: record.enabled ?? 1,
  }
  drawerOpen.value = true
}

async function saveForm() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  saving.value = true
  const payload = {
    ...form.value,
    enabled: form.value.enabled ? 1 : 0,
    case_types: form.value.case_types || [],
    phases: form.value.phases || [],
    source_task_types: form.value.source_task_types || [],
    next_template_codes: form.value.next_template_codes || [],
  }
  try {
    if (drawerMode.value === 'create') {
      await policeStore.createTaskTemplate(payload)
      message.success('模板已创建')
    } else {
      await policeStore.updateTaskTemplate(editingId.value, payload)
      message.success('模板已更新')
    }
    drawerOpen.value = false
    await loadAll()
  } catch (e) {
    message.error('保存失败：' + (e?.message || e))
  } finally {
    saving.value = false
  }
}

// ── 启停 ────────────────────────────────────────────────
async function onToggle(record, val) {
  try {
    await policeStore.toggleTaskTemplate(record.id, val)
    record.enabled = val ? 1 : 0
    message.success(val ? '已启用' : '已停用')
  } catch (e) {
    message.error('操作失败：' + (e?.message || e))
  }
}

// ── 删除 ────────────────────────────────────────────────
function onDelete(record) {
  if (record.is_builtin) {
    message.warning('内置模板只能停用，不能删除')
    return
  }
  Modal.confirm({
    title: '删除自定义模板',
    content: `确认删除模板「${record.name}」？该操作不可恢复。`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        await policeStore.deleteTaskTemplate(record.id)
        message.success('已删除')
        await loadAll()
      } catch (e) {
        message.error('删除失败：' + (e?.message || e))
      }
    },
  })
}

// ── 预览 ────────────────────────────────────────────────
const previewOpen = ref(false)
const previewLoading = ref(false)
const previewSample = ref('6222****1234')
const previewData = ref(null)
const previewName = ref('')
const currentPreviewId = ref(null)

async function openPreview(record) {
  currentPreviewId.value = record.id
  previewName.value = record.name
  previewSample.value = '6222****1234'
  previewData.value = null
  previewOpen.value = true
  await runPreview(record.id, previewSample.value)
}

async function runPreview(id, sample) {
  previewLoading.value = true
  try {
    previewData.value = await policeStore.previewTaskTemplate(id, sample)
  } catch (e) {
    message.error('预览失败：' + (e?.message || e))
  } finally {
    previewLoading.value = false
  }
}

// ── 植入内置模板 ────────────────────────────────────────
function onSeed() {
  Modal.confirm({
    title: '植入内置侦查常识模板',
    content: '将把内置模板（如「发现银行卡→调流水→资金分析→法制审核」等链路）写入库。已存在的模板不会被覆盖，仅补充缺失字段。',
    okText: '确认植入',
    cancelText: '取消',
    onOk: async () => {
      try {
        const res = await policeStore.seedTaskTemplates()
        message.success(`内置模板已就绪：新增 ${res?.created || 0}，保留 ${res?.kept || 0}`)
        await loadAll()
      } catch (e) {
        message.error('植入失败：' + (e?.message || e))
      }
    },
  })
}

onMounted(loadAll)
</script>

<template>
  <div class="tpl-page">
    <!-- 页头 -->
    <div class="tpl-header">
      <div class="tpl-title">
        <h2>侦查任务模板</h2>
        <span class="tpl-subtitle">
          把「涉案要素 → 侦查任务」的侦查常识配置化：推进智能体按模板确定性生成任务，可审计、可改、稳定。
        </span>
      </div>
      <div v-if="userStore.isAdmin" class="tpl-actions">
        <a-button @click="onSeed">
          <ReloadOutlined /> 植入内置模板
        </a-button>
        <a-button type="primary" @click="openCreate">
          <PlusOutlined /> 新建模板
        </a-button>
      </div>
    </div>

    <!-- 过滤器 -->
    <div class="tpl-filter">
      <a-select
        v-model:value="filterElementType"
        placeholder="按要素类型筛选"
        allow-clear
        style="width: 200px"
        :options="elementTypeOptions"
        @change="loadAll"
      />
      <a-input-search
        v-model:value="keyword"
        placeholder="搜索模板名称 / 标题 / 描述"
        allow-clear
        style="width: 260px"
        @search="loadAll"
        @change="(e) => { if (!e.target.value) loadAll() }"
      />
      <label class="tpl-check" style="display:inline-flex;align-items:center;gap:6px;cursor:pointer;">
        <span
          class="t-check"
          role="checkbox"
          :aria-checked="enabledOnly"
          tabindex="0"
          style="--check-len: 16"
          @click="enabledOnly = !enabledOnly; loadAll()"
          @keydown.space.prevent="enabledOnly = !enabledOnly; loadAll()"
        >
          <svg viewBox="0 0 18 18" width="12" height="12" aria-hidden="true"><path d="M4 9 L8 13 L14 5" /></svg>
        </span>
        <span class="tpl-check-label" style="font-size:13px;color:var(--gray-700,#374151);" @click="enabledOnly = !enabledOnly; loadAll()">仅看启用</span>
      </label>
      <span class="tpl-count">共 {{ filteredRows.length }} 条模板</span>
    </div>

    <!-- 表格 -->
    <a-table
      :columns="columns"
      :data-source="filteredRows"
      :loading="loading"
      row-key="id"
      size="middle"
      :scroll="{ x: 1300 }"
      bordered
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          <div class="tpl-name">
            <span class="tpl-name-text">{{ record.name }}</span>
            <a-tag class="tpl-code">{{ record.code }}</a-tag>
          </div>
          <div v-if="record.description" class="tpl-desc">{{ record.description }}</div>
        </template>

        <template v-else-if="column.key === 'task'">
          <div class="tpl-task-title">{{ record.task_title }}</div>
          <a-tag color="blue">{{ taskTypeMap[record.task_type] || record.task_type }}</a-tag>
        </template>

        <template v-else-if="column.key === 'priority'">
          <a-tag :color="priorityColor[record.priority]">
            {{ priorityLabel[record.priority] || record.priority }}
          </a-tag>
        </template>

        <template v-else-if="column.key === 'agent'">
          <span v-if="record.suggested_agent_type">{{ agentTypeMap[record.suggested_agent_type] || record.suggested_agent_type }}</span>
          <span v-else class="tpl-muted">—</span>
        </template>

        <template v-else-if="column.key === 'chain'">
          <template v-if="record.next_template_codes && record.next_template_codes.length">
            <a-tag v-for="code in record.next_template_codes" :key="code" color="purple">
              {{ templateNameByCode[code] || code }}
            </a-tag>
          </template>
          <span v-else class="tpl-muted">末端任务</span>
        </template>

        <template v-else-if="column.key === 'enabled'">
          <a-switch
            :checked="record.enabled === 1"
            size="small"
            :disabled="!userStore.isAdmin"
            @change="(val) => onToggle(record, val)"
          />
        </template>

        <template v-else-if="column.key === 'builtin'">
          <a-tag :color="record.is_builtin ? 'geekblue' : 'default'">
            {{ record.is_builtin ? '内置' : '自定义' }}
          </a-tag>
        </template>

        <template v-else-if="column.key === 'action'">
          <a-space>
            <a-button type="link" size="small" @click="openPreview(record)">
              <EyeOutlined /> 预览
            </a-button>
            <template v-if="userStore.isAdmin">
              <a-button type="link" size="small" @click="openEdit(record)">
                <EditOutlined /> 编辑
              </a-button>
              <a-button
                type="link"
                size="small"
                danger
                :disabled="record.is_builtin"
                @click="onDelete(record)"
              >
                <DeleteOutlined /> 删除
              </a-button>
            </template>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 新建 / 编辑抽屉 -->
    <a-drawer
      :open="drawerOpen"
      :title="drawerMode === 'create' ? '新建侦查任务模板' : '编辑侦查任务模板'"
      width="640"
      :destroy-on-close="true"
      @close="drawerOpen = false"
    >
      <a-form ref="formRef" :model="form" :rules="rules" layout="vertical">
        <a-form-item label="模板名称" name="name">
          <a-input v-model:value="form.name" placeholder="如：银行卡调流水" />
        </a-form-item>

        <a-form-item label="模板说明">
          <a-textarea v-model:value="form.description" :rows="2" placeholder="这条模板的用途 / 适用场景" />
        </a-form-item>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="要素类型（要素触发）">
              <a-select
                v-model:value="form.element_type"
                placeholder="通用（不参与要素触发）"
                allow-clear
                :options="elementTypeOptions"
              />
              <div class="tpl-hint">选填。指定后，推进智能体抽取到该类要素即触发本模板。</div>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="任务类型" name="task_type">
              <a-select
                v-model:value="form.task_type"
                :options="meta?.task_types"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="生成任务标题模板" name="task_title">
          <a-input v-model:value="form.task_title" placeholder="如：调取 {element_value} 的银行流水" />
        </a-form-item>

        <a-form-item label="任务描述模板">
          <a-textarea v-model:value="form.task_description" :rows="2" placeholder="支持占位符，如：针对 {element_value} 开展核查" />
        </a-form-item>

        <a-form-item label="办理指引（草案审查时展示给主办民警）">
          <a-textarea v-model:value="form.instructions" :rows="3" placeholder="如：1. 开具协查；2. 调取近一年流水；3. 标注可疑交易" />
        </a-form-item>

        <!-- 占位符提示 -->
        <a-alert
          v-if="meta?.placeholders?.length"
          class="tpl-ph"
          type="info"
          :show-icon="true"
        >
          <template #message>
            <div class="tpl-ph-title">
              <InfoCircleOutlined /> 可用占位符（在标题/描述/指引中直接书写）
            </div>
            <div class="tpl-ph-list">
              <a-tag v-for="p in meta.placeholders" :key="p.key">{{ p.key }}</a-tag>
            </div>
            <div class="tpl-ph-desc">
              <span v-for="p in meta.placeholders" :key="p.key + '_d'" class="tpl-ph-item">
                <code>{{ p.key }}</code> = {{ p.desc }}
              </span>
            </div>
          </template>
        </a-alert>

        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="优先级">
              <a-select
                v-model:value="form.priority"
                :options="meta?.priorities"
              />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="建议数字警员">
              <a-select
                v-model:value="form.suggested_agent_type"
                placeholder="不指定"
                allow-clear
                :options="meta?.agent_types"
              />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="办理期限（天）">
              <a-input-number v-model:value="form.due_days" :min="0" :max="365" style="width: 100%" placeholder="不限制" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="适用案件类型（不填=不限制）">
          <a-select
            v-model:value="form.case_types"
            mode="tags"
            placeholder="输入案件类型后回车，如：电诈、赌博"
            :token-separators="[',']"
          />
        </a-form-item>

        <a-form-item label="适用侦查阶段（不填=不限制）">
          <a-select
            v-model:value="form.phases"
            mode="tags"
            placeholder="输入阶段后回车，如：初查、侦查"
            :token-separators="[',']"
          />
        </a-form-item>

        <a-form-item label="上游任务类型（链式触发，不填=不参与链式）">
          <a-select
            v-model:value="form.source_task_types"
            mode="tags"
            placeholder="输入上游任务类型后回车"
            :token-separators="[',']"
          />
        </a-form-item>

        <a-form-item label="链式后继模板（本任务完成后接续生成）">
          <a-select
            v-model:value="form.next_template_codes"
            mode="multiple"
            placeholder="选择后继模板"
            :options="meta?.templates"
          />
        </a-form-item>

        <a-form-item label="是否启用">
          <a-switch v-model:checked="form.enabled" />
          <span class="tpl-hint" style="margin-left: 12px">停用后推进智能体不再用它生成任务。</span>
        </a-form-item>
      </a-form>

      <template #footer>
        <a-space>
          <a-button @click="drawerOpen = false">取消</a-button>
          <a-button type="primary" :loading="saving" @click="saveForm">保存</a-button>
        </a-space>
      </template>
    </a-drawer>

    <!-- 预览弹窗 -->
    <a-modal
      v-model:open="previewOpen"
      :title="`模板预览 · ${previewName}`"
      width="680"
      :footer="null"
    >
      <div class="tpl-preview-sample">
        <span>示例要素值：</span>
        <a-input v-model:value="previewSample" style="width: 240px" @press-enter="runPreview(currentPreviewId, previewSample)" />
        <a-button type="primary" :loading="previewLoading" @click="runPreview(currentPreviewId, previewSample)">重新渲染</a-button>
      </div>
      <a-spin :spinning="previewLoading">
        <div v-if="previewData" class="tpl-preview-body">
          <div class="tpl-preview-row">
            <span class="tpl-preview-label">任务标题</span>
            <div class="tpl-preview-value tpl-preview-title">{{ previewData.title }}</div>
          </div>
          <div class="tpl-preview-row">
            <span class="tpl-preview-label">类型</span>
            <div class="tpl-preview-value">
              <a-tag color="blue">{{ previewData.type_label }}</a-tag>
              <a-tag :color="priorityColor[previewData.priority]">{{ priorityLabel[previewData.priority] || previewData.priority }}</a-tag>
            </div>
          </div>
          <div class="tpl-preview-row">
            <span class="tpl-preview-label">任务描述</span>
            <div class="tpl-preview-value">{{ previewData.description || '—' }}</div>
          </div>
          <div class="tpl-preview-row">
            <span class="tpl-preview-label">办理指引</span>
            <div class="tpl-preview-value tpl-preview-pre">{{ previewData.instructions || '—' }}</div>
          </div>
          <div class="tpl-preview-row">
            <span class="tpl-preview-label">链式后继</span>
            <div class="tpl-preview-value">
              <template v-if="previewData.next_template_codes && previewData.next_template_codes.length">
                <a-tag v-for="c in previewData.next_template_codes" :key="c" color="purple">
                  {{ templateNameByCode[c] || c }}
                </a-tag>
              </template>
              <span v-else class="tpl-muted">末端任务</span>
            </div>
          </div>
        </div>
      </a-spin>
    </a-modal>
  </div>
</template>

<style lang="less" scoped>
.tpl-page {
  padding: 20px 24px 40px;
  max-width: 1280px;
  margin: 0 auto;
}
.tpl-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}
.tpl-title h2 {
  margin: 0 0 4px;
  font-size: 20px;
  font-weight: 650;
}
.tpl-subtitle {
  color: var(--gray-600);
  font-size: 13px;
}
.tpl-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.tpl-filter {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.tpl-count {
  color: var(--gray-500);
  font-size: 13px;
}
.tpl-name-text {
  font-weight: 600;
}
.tpl-code {
  margin-left: 6px;
  font-family: monospace;
  font-size: 11px;
}
.tpl-desc {
  color: var(--gray-500);
  font-size: 12px;
  margin-top: 2px;
  max-width: 200px;
}
.tpl-task-title {
  font-weight: 500;
  margin-bottom: 4px;
}
.tpl-muted {
  color: var(--gray-400);
}
.tpl-hint {
  color: var(--gray-500);
  font-size: 12px;
  line-height: 1.5;
  margin-top: 4px;
}
.tpl-ph {
  margin: 4px 0 16px;
}
.tpl-ph-title {
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}
.tpl-ph-list {
  margin: 8px 0 4px;
}
.tpl-ph-desc {
  display: flex;
  flex-direction: column;
  gap: 2px;
  color: var(--gray-600);
  font-size: 12px;
}
.tpl-ph-item code {
  background: var(--gray-100);
  padding: 1px 6px;
  border-radius: 4px;
  margin-right: 4px;
}
.tpl-preview-sample {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}
.tpl-preview-row {
  display: flex;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--gray-100);
}
.tpl-preview-label {
  flex: 0 0 80px;
  color: var(--gray-600);
  font-size: 13px;
}
.tpl-preview-value {
  flex: 1 1 auto;
  min-width: 0;
}
.tpl-preview-title {
  font-weight: 600;
  font-size: 15px;
}
.tpl-preview-pre {
  white-space: pre-wrap;
  line-height: 1.6;
}
</style>
