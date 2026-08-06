<script setup>
/**
 * 协助伙伴（子智能体）创建/编辑抽屉
 * is_subagent 固定为 true，由后端强制 SubAgentBackend。
 */
import { reactive, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { Handshake } from 'lucide-vue-next'
import { policePartnerApi } from '@/apis/police_api'

const props = defineProps({
  open: { type: Boolean, default: false },
  /** 编辑对象；null = 新建 */
  partner: { type: Object, default: null }
})
const emit = defineEmits(['update:open', 'saved'])

const AGENT_CATEGORIES = [
  { value: 'case_analysis', label: '案件分析' },
  { value: 'fund_tracking', label: '资金追踪' },
  { value: 'intelligence', label: '情报研判' },
  { value: 'evidence_mgmt', label: '调证取证' },
  { value: 'legal_review', label: '法制审核' },
  { value: 'interrogation', label: '审讯辅助' },
  { value: 'image_recon', label: '图像侦查' },
  { value: 'anti_fraud', label: '反诈劝阻' },
  { value: 'command', label: '指挥调度' },
  { value: 'partner_generic', label: '通用协助' }
]

const saving = ref(false)
const form = reactive({
  name: '',
  description: '',
  category: undefined,
  system_prompt: '',
  model_settings: {}
})

const isEdit = () => !!props.partner

watch(
  () => props.open,
  (open) => {
    if (!open) return
    if (props.partner) {
      form.name = props.partner.name || ''
      form.description = props.partner.description || ''
      form.category = props.partner.category || undefined
      form.system_prompt = props.partner.system_prompt || ''
      form.model_settings = props.partner.model_config || {}
    } else {
      form.name = ''
      form.description = ''
      form.category = undefined
      form.system_prompt = ''
      form.model_settings = {}
    }
  }
)

async function handleSave() {
  if (!form.name.trim()) {
    message.error('请填写协助伙伴名称')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      category: form.category || null,
      system_prompt: form.system_prompt.trim() || null,
      model_settings: Object.keys(form.model_settings).length ? form.model_settings : null
    }
    if (props.partner) {
      await policePartnerApi.update(props.partner.id, payload)
      message.success('协助伙伴已更新')
    } else {
      await policePartnerApi.create(payload)
      message.success('协助伙伴已创建')
    }
    emit('update:open', false)
    emit('saved')
  } catch (e) {
    message.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <a-drawer
    :open="open"
    :title="isEdit() ? '编辑协助伙伴' : '新建协助伙伴'"
    :width="480"
    destroy-on-close
    @update:open="(v) => emit('update:open', v)"
  >
    <div class="partner-edit-drawer">
      <div class="partner-type-hint">
        <Handshake :size="14" />
        <span>协助伙伴是子智能体（SubAgentBackend），被数字警员挂载后在其办案中调用。</span>
      </div>

      <a-form layout="vertical">
        <a-form-item label="名称" required>
          <a-input v-model:value="form.name" placeholder="如：笔录要素抽取助手" />
        </a-form-item>
        <a-form-item label="功能分类">
          <a-select
            v-model:value="form.category"
            :options="AGENT_CATEGORIES"
            placeholder="选择分类"
            allow-clear
          />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="2" placeholder="一句话说明这个协助伙伴擅长什么" />
        </a-form-item>
        <a-form-item label="系统提示词（可选）">
          <a-textarea
            v-model:value="form.system_prompt"
            :rows="6"
            placeholder="定义该协助伙伴的专业行为与输出规范"
          />
        </a-form-item>
      </a-form>
    </div>

    <template #footer>
      <div class="partner-edit-footer">
        <a-button @click="emit('update:open', false)">取消</a-button>
        <a-button type="primary" :loading="saving" @click="handleSave">保存</a-button>
      </div>
    </template>
  </a-drawer>
</template>

<style lang="less" scoped>
.partner-edit-drawer {
  padding: 4px 0;
}
.partner-type-hint {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 16px;
  padding: 10px 12px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-25);
  color: var(--gray-600);
  font-size: 12px;
  line-height: 1.6;
  svg {
    flex-shrink: 0;
    margin-top: 2px;
    color: var(--main-600);
  }
}
.partner-edit-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
