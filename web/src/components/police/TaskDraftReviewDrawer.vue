<script setup>
/**
 * ★ 任务草案审查抽屉 — Human-in-the-Loop
 * 主办民警审查推进智能体生成的任务草案：可编辑字段后「确认」，或填写原因「驳回」。
 */
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { usePoliceStore } from '@/stores/police'

const props = defineProps({
  open: { type: Boolean, default: false },
  draft: { type: Object, default: null },
})
const emit = defineEmits(['update:open', 'confirmed', 'rejected'])

const policeStore = usePoliceStore()
const router = useRouter()

const typeOptions = [
  { value: 'transcript_analysis', label: '笔录分析' },
  { value: 'fund_analysis', label: '资金分析' },
  { value: 'evidence_collection', label: '调证生成' },
  { value: 'evidence_submission', label: '证据提交' },
  { value: 'legal_review', label: '法制审核' },
  { value: 'document_generation', label: '文书生成' },
  { value: 'investigation', label: '侦查' },
  { value: 'interrogation', label: '审讯' },
  { value: 'arrest', label: '抓捕' },
  { value: 'cyber_inquiry', label: '网警查询' },
  { value: 'knowledge_extraction', label: '知识抽取' },
]
const priorityOptions = [
  { value: 'urgent', label: '紧急' },
  { value: 'high', label: '高' },
  { value: 'medium', label: '中' },
  { value: 'low', label: '低' },
]

const form = ref({ title: '', type: 'investigation', priority: 'medium', instructions: '', due_date: '' })
const rejectReason = ref('')
const submitting = ref(false)

watch(
  () => props.draft,
  (d) => {
    if (d) {
      form.value = {
        title: d.title || '',
        type: d.type || 'investigation',
        priority: d.priority || 'medium',
        instructions: d.instructions || '',
        due_date: d.due_date || '',
      }
      rejectReason.value = ''
    }
  },
  { immediate: true }
)

async function handleConfirm() {
  if (!form.value.title.trim()) {
    message.warning('任务标题不能为空')
    return
  }
  submitting.value = true
  try {
    const edits = {
      title: form.value.title.trim(),
      type: form.value.type,
      priority: form.value.priority,
      instructions: form.value.instructions,
      due_date: form.value.due_date || null,
    }
    await policeStore.confirmDraft(props.draft.id, edits)
    message.success('已确认任务草案，进入待分配状态')
    emit('confirmed', props.draft.id)
    emit('update:open', false)
  } catch (e) {
    message.error('确认失败：' + (e.message || e))
  } finally {
    submitting.value = false
  }
}

async function handleReject() {
  submitting.value = true
  try {
    await policeStore.rejectDraft(props.draft.id, rejectReason.value || null)
    message.success('已驳回任务草案')
    emit('rejected', props.draft.id)
    emit('update:open', false)
  } catch (e) {
    message.error('驳回失败：' + (e.message || e))
  } finally {
    submitting.value = false
  }
}

function goSource() {
  if (props.draft?.parent_task_id) {
    router.push(`/police/tasks/${props.draft.parent_task_id}`)
    emit('update:open', false)
  }
}
</script>

<template>
  <a-drawer
    :open="open"
    title="审查任务草案"
    width="480"
    :footer="null"
    @close="emit('update:open', false)"
  >
    <template v-if="draft">
      <a-alert type="info" class="mb-16" show-icon>
        <template #message>该任务由案件推进智能体生成</template>
        <template #description>
          <span>来源任务 #{{ draft.parent_task_id || '—' }}</span>
          <a v-if="draft.parent_task_id" @click="goSource"> 查看来源</a>
        </template>
      </a-alert>

      <a-form layout="vertical">
        <a-form-item label="任务标题">
          <a-input v-model:value="form.title" placeholder="任务标题" />
        </a-form-item>
        <a-form-item label="任务类型">
          <a-select v-model:value="form.type" :options="typeOptions" />
        </a-form-item>
        <a-form-item label="优先级">
          <a-select v-model:value="form.priority" :options="priorityOptions" />
        </a-form-item>
        <a-form-item label="截止日期（可选，格式 YYYY-MM-DD）">
          <a-input v-model:value="form.due_date" placeholder="如 2026-08-20" />
        </a-form-item>
        <a-form-item label="推进智能体依据">
          <div class="basis-box">{{ form.instructions || '（无依据说明）' }}</div>
        </a-form-item>
        <a-form-item label="驳回原因（驳回时填写）">
          <a-textarea
            v-model:value="rejectReason"
            :rows="2"
            placeholder="如：暂不急需 / 与当前侦查方向不符"
          />
        </a-form-item>
      </a-form>

      <div class="drawer-footer">
        <a-button danger :loading="submitting" @click="handleReject">驳回</a-button>
        <a-button type="primary" :loading="submitting" @click="handleConfirm">确认任务</a-button>
      </div>
    </template>
  </a-drawer>
</template>

<style scoped>
.mb-16 {
  margin-bottom: 16px;
}
.basis-box {
  font-size: 13px;
  color: var(--gray-700, #4a5568);
  background: var(--gray-10, #f7fafc);
  border: 1px solid var(--gray-50, #e2e8f0);
  border-radius: 6px;
  padding: 8px 10px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
  padding-top: 16px;
  border-top: 1px solid var(--gray-50, #e2e8f0);
}
</style>
