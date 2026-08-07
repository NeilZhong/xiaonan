<script setup>
/**
 * ★ 创建任务弹窗（与 TaskDetailModal 统一视觉语言）
 * 白底圆角弹窗、语义 token、明暗自适应；两列：左表单 + 右执行方式说明。
 * 支持多执行人（办案民警 + 数字警员），截止日期、任务指引。
 */
import { ref, computed, watch } from 'vue'
import { usePoliceStore } from '@/stores/police'
import { policeAgentApi, policeCaseApi } from '@/apis/police_api'
import { message } from 'ant-design-vue'
import {
  Bot,
  Calendar,
  Flag,
  Sparkles,
  User,
  Users,
  X,
} from 'lucide-vue-next'

const props = defineProps({
  /** 打开时传入案件 ID */
  caseId: { type: [Number, String], default: null },
  visible: { type: Boolean, default: false },
  /** 预填案件阶段 */
  phase: { type: String, default: null },
})
const emit = defineEmits(['close', 'created'])

const policeStore = usePoliceStore()

// ── 任务类型 / 优先级 ──────────────────────────────
const taskTypes = [
  { label: '笔录分析', value: 'transcript_analysis' },
  { label: '资金分析', value: 'fund_analysis' },
  { label: '调证生成', value: 'evidence_collection' },
  { label: '证据提交', value: 'evidence_submission' },
  { label: '法制审核', value: 'legal_review' },
  { label: '文书生成', value: 'document_generation' },
  { label: '侦查', value: 'investigation' },
  { label: '审讯', value: 'interrogation' },
  { label: '抓捕', value: 'arrest' },
  { label: '网警查询', value: 'cyber_inquiry' },
  { label: '知识抽取', value: 'knowledge_extraction' },
]
const priorityOptions = [
  { label: '紧急', value: 'urgent' },
  { label: '高', value: 'high' },
  { label: '中', value: 'medium' },
  { label: '低', value: 'low' },
]
const priorityPill = { urgent: 'rose', high: 'orange', medium: 'blue', low: 'default' }

const form = ref({
  title: '',
  type: 'evidence_collection',
  priority: 'medium',
  due_date: null,
  description: '',
  instructions: '',
  selectedHumans: [],
  selectedAgents: [],
})
const submitting = ref(false)

// ── 分配对象选项 ──────────────────────────────────
const humanOptions = ref([])
const agentOptions = ref([])
const membersLoading = ref(false)
const agentsLoading = ref(false)

const caseMembers = computed(() => policeStore.currentCase?.members || [])

async function loadOptions() {
  membersLoading.value = true
  agentsLoading.value = true
  try {
    humanOptions.value = caseMembers.value.map(m => ({
      label: `${m.username || m.user_name || '未命名'} (${{ commander: '指挥员', handler: '办案人', reviewer: '审核员', observer: '观察员' }[m.role] || m.role})`,
      value: m.user_id,
      name: m.username || m.user_name || '',
    }))
    if (!humanOptions.value.length && props.caseId) {
      // 兜底：直接查案件成员
      const res = await policeCaseApi.get(props.caseId)
      humanOptions.value = (res.members || []).map(m => ({
        label: `${m.username || '未命名'} (${{ commander: '指挥员', handler: '办案人', reviewer: '审核员', observer: '观察员' }[m.role] || m.role})`,
        value: m.user_id,
        name: m.username || '',
      }))
    }
    const res = await policeAgentApi.list({ page_size: 50 })
    agentOptions.value = (res.items || []).map(a => ({
      label: `${a.name || a.display_name || '未命名智能体'} (${a.type || a.agent_type || '-'})`,
      value: a.id,
      name: a.name || a.display_name || '',
    }))
  } catch {
    // 加载失败不阻塞
  } finally {
    membersLoading.value = false
    agentsLoading.value = false
  }
}

/** 执行方式摘要：谁参与、AI 是否参与 */
const execMode = computed(() => {
  const humans = form.value.selectedHumans.length
  const agents = form.value.selectedAgents.length
  if (agents > 0 && humans > 0) return { icon: Users, text: '人机协同执行', desc: `${humans} 名民警 + ${agents} 个数字警员协同完成任务` }
  if (agents > 0) return { icon: Bot, text: '数字警员自动执行', desc: `任务创建后由 ${agents} 个数字警员自动完成，产出经民警审核` }
  if (humans > 0) return { icon: User, text: '民警执行', desc: `${humans} 名民警负责执行，可手动提交结果` }
  return { icon: Sparkles, text: '待分配', desc: '暂不指定执行人，稍后在任务详情中分配' }
})

const selectedCount = computed(() => form.value.selectedHumans.length + form.value.selectedAgents.length)

function resetForm() {
  form.value = {
    title: '', type: 'evidence_collection', priority: 'medium',
    due_date: null, description: '', instructions: '',
    selectedHumans: [], selectedAgents: [],
  }
}

async function submit() {
  if (!form.value.title.trim()) {
    message.warning('请填写任务标题')
    return
  }
  submitting.value = true
  try {
    // 构造 assignees（多执行人）
    const assignees = [
      ...form.value.selectedHumans.map(h => ({
        assignee_type: 'human', assignee_id: h.value,
        assignee_name: h.name || h.label || '', role: 'executor',
      })),
      ...form.value.selectedAgents.map(a => ({
        assignee_type: 'agent', assignee_id: a.value,
        assignee_name: a.name || a.label || '', role: 'executor',
      })),
    ]
    // 兼容后端：单执行人用冗余字段；任何执行人都走 assign 同步 TaskAssignee 表
    const primary = assignees[0] || {}
    const created = await policeStore.createTask({
      case_id: props.caseId,
      title: form.value.title,
      type: form.value.type,
      priority: form.value.priority,
      phase: props.phase || undefined,
      due_date: form.value.due_date || undefined,
      description: form.value.description || undefined,
      instructions: form.value.instructions || undefined,
      assignee_type: primary.assignee_type || 'human',
      assignee_id: primary.assignee_id ?? null,
      assignee_name: primary.assignee_name || '',
    })
    // 统一补充分配（含单执行人）→ 写入 TaskAssignee 表，保证人机分配/审核人解算正确
    if (assignees.length) {
      await policeStore.assignTask(created.id, { assignees })
    }
    message.success('任务创建成功' + (execMode.value.text === '数字警员自动执行' ? '，数字警员即将开始执行' : ''))
    emit('created')
    close()
  } catch {
    message.error('创建失败')
  } finally {
    submitting.value = false
  }
}

function close() {
  resetForm()
  emit('close')
}

watch(() => props.visible, (v) => {
  if (v) { resetForm(); loadOptions() }
})
</script>

<template>
  <a-modal
    :open="props.visible"
    :footer="null"
    :closable="false"
    width="720px"
    wrap-class-name="tdm-wrap tcm-wrap"
    :body-style="{ padding: 0 }"
    @cancel="close"
  >
    <div class="tcm">
      <!-- Header -->
      <header class="tcm-header">
        <h2 class="tcm-title">创建任务</h2>
        <div class="tcm-header-actions">
          <button class="tcm-icon-btn" title="关闭" @click="close">
            <X :size="16" />
          </button>
        </div>
      </header>

      <div class="tcm-body">
        <!-- ══ 左列：表单 ══ -->
        <div class="tcm-main">
          <div class="tcm-field">
            <label class="tcm-label" for="tcm-title">任务标题 <span class="tcm-required">*</span></label>
            <input
              id="tcm-title"
              v-model="form.title"
              class="tcm-input"
              placeholder="如：调取工行账户6222****1234流水"
              @keyup.enter="submit"
            />
          </div>

          <div class="tcm-row">
            <div class="tcm-field">
              <label class="tcm-label">任务类型</label>
              <a-select v-model:value="form.type" size="small" class="tcm-select" :options="taskTypes" />
            </div>
            <div class="tcm-field">
              <label class="tcm-label"><Flag :size="12" /> 优先级</label>
              <a-select v-model:value="form.priority" size="small" class="tcm-select" :options="priorityOptions" />
            </div>
          </div>

          <div class="tcm-row">
            <div class="tcm-field">
              <label class="tcm-label"><Calendar :size="12" /> 截止日期</label>
              <a-date-picker
                v-model:value="form.due_date"
                size="small"
                class="tcm-select"
                placeholder="可选"
                value-format="YYYY-MM-DD"
              />
            </div>
            <div class="tcm-field">
              <label class="tcm-label">案件阶段</label>
              <span class="tcm-static">{{ { research: '前期研判', arrest: '抓捕审讯', handling: '案件办理', prosecution: '移送起诉' }[props.phase] || '未分阶段' }}</span>
            </div>
          </div>

          <div class="tcm-field">
            <label class="tcm-label"><Users :size="12" /> 执行人（可多选）</label>
            <div class="tcm-assignees">
              <div class="tcm-assignee-group">
                <span class="tcm-group-label">办案民警</span>
                <a-select
                  mode="multiple"
                  v-model:value="form.selectedHumans"
                  :options="humanOptions"
                  placeholder="选择办案民警（可选）"
                  size="small"
                  :loading="membersLoading"
                  allow-clear
                  show-search
                  option-filter-prop="label"
                  class="tcm-select"
                />
              </div>
              <div class="tcm-assignee-group">
                <span class="tcm-group-label"><Bot :size="12" /> 数字警员</span>
                <a-select
                  mode="multiple"
                  v-model:value="form.selectedAgents"
                  :options="agentOptions"
                  placeholder="选择数字警员（可选，将自动执行）"
                  size="small"
                  :loading="agentsLoading"
                  allow-clear
                  show-search
                  option-filter-prop="label"
                  class="tcm-select"
                />
              </div>
            </div>
          </div>

          <div class="tcm-field">
            <label class="tcm-label">任务描述</label>
            <a-textarea v-model:value="form.description" :rows="2" placeholder="背景、目标（可选）" />
          </div>

          <div class="tcm-field">
            <label class="tcm-label">任务指引</label>
            <a-textarea v-model:value="form.instructions" :rows="3" placeholder="给执行人的详细要求和注意事项" />
          </div>
        </div>

        <!-- ══ 右列：执行方式说明 ══ -->
        <aside class="tcm-sidebar">
          <div class="tcm-prop">
            <span class="tcm-prop-label">执行方式</span>
            <div class="tcm-mode" :class="{ 'has-agent': form.selectedAgents.length > 0 }">
              <component :is="execMode.icon" :size="16" />
              <span class="tcm-mode-text">{{ execMode.text }}</span>
              <span class="tcm-mode-desc">{{ execMode.desc }}</span>
            </div>
          </div>

          <div class="tcm-prop">
            <span class="tcm-prop-label">优先级</span>
            <span class="tcm-priority" :class="`is-${priorityPill[form.priority] || 'default'}`">
              {{ priorityOptions.find(p => p.value === form.priority)?.label }}
            </span>
          </div>

          <div class="tcm-prop">
            <span class="tcm-prop-label">执行人数</span>
            <span class="tcm-static">{{ selectedCount ? `${selectedCount} 名执行人` : '未分配' }}</span>
          </div>

          <div class="tcm-tip">
            <Sparkles :size="13" />
            提示：分配数字警员后，开始执行时智能体将自动完成任务并产出成果，由你审核后归档。
          </div>

          <button class="tcm-submit" :disabled="submitting" @click="submit">
            {{ submitting ? '创建中...' : '创建任务' }}
          </button>
        </aside>
      </div>
    </div>
  </a-modal>
</template>

<style scoped>
:global(.tcm-wrap .ant-modal-content) {
  border-radius: 16px;
  padding: 0;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
}
:global(.tcm-wrap .ant-modal-body) {
  max-height: 80vh;
  overflow: auto;
}

.tcm {
  background: var(--gray-0, #fff);
  color: var(--gray-1000, #0f172a);
}

.tcm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px 0;
}
.tcm-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--gray-1000, #0f172a);
  margin: 0;
}
.tcm-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-500, #64748b);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.tcm-icon-btn:hover { background: var(--gray-50, #e2e8f0); color: var(--gray-800, #334155); }
.tcm-icon-btn:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 1px;
}

.tcm-body {
  display: flex;
  gap: 24px;
  padding: 16px 22px 22px;
}
.tcm-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 14px; }
.tcm-sidebar {
  flex: 0 0 208px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-left: 20px;
  border-left: 1px solid var(--gray-50, #e2e8f0);
}

.tcm-field { display: flex; flex-direction: column; gap: 6px; }
.tcm-row { display: flex; gap: 12px; }
.tcm-row .tcm-field { flex: 1; }
.tcm-label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 500;
  color: var(--gray-600, #475569);
}
.tcm-required { color: var(--color-error-500, #dc2626); }
.tcm-input {
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 14px;
  color: var(--gray-1000, #0f172a);
  background: var(--gray-0, #fff);
  outline: none;
  transition: border-color 0.15s;
}
.tcm-input:hover { border-color: var(--gray-200, #cbd5e1); }
.tcm-input:focus { border-color: var(--main-color, #24839b); }
.tcm-input:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 1px;
  border-radius: 8px;
}
.tcm-input::placeholder { color: var(--gray-400, #94a3b8); }
.tcm-select { width: 100%; }
.tcm-static {
  font-size: 13px;
  color: var(--gray-700, #334155);
  line-height: 30px;
}

.tcm-assignees { display: flex; flex-direction: column; gap: 8px; }
.tcm-assignee-group { display: flex; flex-direction: column; gap: 4px; }
.tcm-group-label {
  font-size: 12px;
  color: var(--gray-500, #64748b);
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.tcm-prop { display: flex; flex-direction: column; gap: 6px; }
.tcm-prop-label {
  font-size: 12px;
  color: var(--gray-500, #64748b);
}
.tcm-mode {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--gray-10, #f1f5f9);
  color: var(--gray-700, #334155);
}
.tcm-mode.has-agent {
  background: #f5f3ff;
  color: #6d28d9;
}
.tcm-mode-text { font-size: 13px; font-weight: 600; }
.tcm-mode-desc { font-size: 12px; color: var(--gray-500, #64748b); line-height: 1.5; }
.tcm-priority {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 9999px;
  align-self: flex-start;
}
.tcm-priority.is-rose { background: #ffe4e6; color: #e11d48; }
.tcm-priority.is-orange { background: #ffedd5; color: #ea580c; }
.tcm-priority.is-blue { background: #dbeafe; color: #2563eb; }
.tcm-priority.is-default { background: var(--gray-50, #e2e8f0); color: var(--gray-600, #475569); }

.tcm-tip {
  display: flex;
  gap: 6px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--gray-500, #64748b);
  background: var(--gray-10, #f1f5f9);
  border-radius: 8px;
  padding: 10px;
}
.tcm-tip svg { flex-shrink: 0; margin-top: 2px; }

.tcm-submit {
  margin-top: auto;
  border: none;
  border-radius: 8px;
  background: var(--main-color, #24839b);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  padding: 9px 0;
  cursor: pointer;
  transition: opacity 0.15s;
}
.tcm-submit:hover { opacity: 0.88; }
.tcm-submit:disabled { opacity: 0.5; cursor: not-allowed; }
.tcm-submit:focus-visible {
  outline: 2px solid var(--main-color, #24839b);
  outline-offset: 2px;
}

@media (max-width: 640px) {
  .tcm-body { flex-direction: column; }
  .tcm-sidebar {
    flex: 1;
    border-left: none;
    border-top: 1px solid var(--gray-50, #e2e8f0);
    padding-left: 0;
    padding-top: 16px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .tcm-icon-btn, .tcm-input, .tcm-submit { transition: none; }
}
</style>
