<script setup>
import { computed, nextTick, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  Bot,
  Dices,
  Info,
  Microscope,
  RefreshCw,
  Settings2,
  SlidersHorizontal,
  Upload,
  Wrench
} from 'lucide-vue-next'

import { userApi } from '@/apis/user_api'
import { policeAgentApi } from '@/apis/police_api'
import AgentRuntimeConfigForm from '@/components/AgentRuntimeConfigForm.vue'
import FallbackAvatar from '@/components/common/FallbackAvatar.vue'
import ShareConfigForm from '@/components/ShareConfigForm.vue'
import { isBuiltinAgent, useAgentStore } from '@/stores/agent'
import { useUserStore } from '@/stores/user'
import { generatePixelAvatar } from '@/utils/pixelAvatar'
import {
  generateRandomPoliceAvatar,
  POLICE_AVATAR_IDS,
  getPoliceAvatarById
} from '@/utils/policeAvatar'
import { MAX_IMAGE_UPLOAD_SIZE_BYTES, MAX_IMAGE_UPLOAD_SIZE_MB } from '@/utils/upload_limits'

const props = defineProps({
  backendOptions: { type: Array, default: () => [] }
})

const emit = defineEmits(['saved'])

const userStore = useUserStore()
const agentStore = useAgentStore()

const DEFAULT_AGENT_BACKEND_ID = 'ChatbotAgent'

/** 9 大功能分类（新增数字警员时下拉选择，对应 agents.category） */
const AGENT_CATEGORIES = [
  { value: 'case_analysis', label: '案件分析' },
  { value: 'fund_tracking', label: '资金追踪' },
  { value: 'intelligence', label: '情报研判' },
  { value: 'evidence_mgmt', label: '调证取证' },
  { value: 'legal_review', label: '法制审核' },
  { value: 'interrogation', label: '审讯辅助' },
  { value: 'image_recon', label: '图像侦查' },
  { value: 'anti_fraud', label: '反诈劝阻' },
  { value: 'command', label: '指挥调度' }
]
const runtimeAgentModalTabs = ['model', 'tools', 'other']

const showAgentModal = ref(false)
const editingAgentId = ref(null)
const agentModalActiveTab = ref('basic')
const agentIconUploading = ref(false)
const saving = ref(false)
const runtimeConfigFormRef = ref(null)
const shareConfigFormRef = ref(null)
const shareConfig = ref({ access_level: 'user', department_ids: [], user_uids: [] })
const agentNameInputRef = ref(null)
const isGeneratingAvatar = ref(false)
const currentAvatarId = ref('')
const agentForm = reactive({
  slug: '',
  name: '',
  backend_id: DEFAULT_AGENT_BACKEND_ID,
  description: '',
  icon: '',
  category: ''
})

const normalizeAgent = (agent) => {
  const agentId = agent?.agent_id || agent?.slug || agent?.id
  return agentId
    ? { ...agent, id: agentId, agent_id: agentId, slug: agent?.slug || agentId }
    : agent
}

const agentModalMenuItems = computed(() => {
  return [
    { key: 'basic', label: '基本信息', icon: Info },
    { key: 'model', label: '模型配置', icon: SlidersHorizontal },
    { key: 'tools', label: '工具配置', icon: Wrench },
    { key: 'other', label: '其他配置', icon: Settings2 }
  ]
})

const showAgentModalSidebar = computed(() => true)
const runtimeConfigSegment = computed(() =>
  runtimeAgentModalTabs.includes(agentModalActiveTab.value) ? agentModalActiveTab.value : 'model'
)
const isRuntimeAgentModalTab = (key) => runtimeAgentModalTabs.includes(key)
const getDefaultBackendId = () => DEFAULT_AGENT_BACKEND_ID

const isEditingBuiltinAgent = computed(() => isBuiltinAgent({ id: editingAgentId.value }))

const agentModalTitle = computed(() => (editingAgentId.value ? '编辑智能体' : '新增智能体'))
const agentPreviewDefaultIcon = computed(() =>
  editingAgentId.value ? generatePixelAvatar(editingAgentId.value) : ''
)
const agentPreviewName = computed(() => agentForm.name || editingAgentId.value || '智能体')
const selectedBackendOption = computed(() =>
  props.backendOptions.find((backend) => backend.value === agentForm.backend_id)
)
const selectedBackendLabel = computed(
  () => selectedBackendOption.value?.label || agentForm.backend_id || '未选择'
)
const selectedBackendIcon = computed(() => {
  const backendText = `${agentForm.backend_id} ${selectedBackendLabel.value}`.toLowerCase()
  return backendText.includes('deep') || backendText.includes('search') ? Microscope : Bot
})

const resetAgentForm = () => {
  Object.assign(agentForm, {
    slug: '',
    name: '',
    backend_id: getDefaultBackendId(),
    description: '',
    icon: '',
    category: ''
  })
  currentAvatarId.value = ''
}

/**
 * 随机生成数字警员漫画形象：卡牌翻转/快速切换动画，最后落定。
 */
const generatePoliceAvatar = () => {
  if (isGeneratingAvatar.value) return
  isGeneratingAvatar.value = true
  const cycles = 8
  const interval = 120
  let step = 0
  const timer = setInterval(() => {
    const avatarId = POLICE_AVATAR_IDS[step % POLICE_AVATAR_IDS.length]
    const avatar = getPoliceAvatarById(avatarId)
    if (avatar) {
      agentForm.icon = avatar.url
      currentAvatarId.value = avatar.id
    }
    step += 1
    if (step >= cycles) {
      clearInterval(timer)
      const final = generateRandomPoliceAvatar()
      agentForm.icon = final.url
      currentAvatarId.value = final.id
      isGeneratingAvatar.value = false
    }
  }, interval)
}

const focusAgentNameInput = async () => {
  await nextTick()
  agentNameInputRef.value?.focus?.()
}

const handleAgentModalAfterOpenChange = (open) => {
  if (open && !editingAgentId.value) focusAgentNameInput()
}

const openCreate = () => {
  editingAgentId.value = null
  agentModalActiveTab.value = 'basic'
  resetAgentForm()
  agentStore.resetAgentConfig()
  // 确保知识库配置初始化为数组（避免未定义）
  if (!Array.isArray(agentStore.agentConfig?.knowledges)) {
    agentStore.agentConfig.knowledges = []
  }
  // 新建数字警员时默认随机分配一个漫画警察形象
  const avatar = generateRandomPoliceAvatar()
  agentForm.icon = avatar.url
  currentAvatarId.value = avatar.id
  showAgentModal.value = true
}

const openEdit = async (agent) => {
  const agentId = typeof agent === 'string' ? agent : agent?.id
  if (!agentId) return

  const detail = await agentStore.fetchAgentDetail(agentId, true)
  // 数字警员（police agent）通过 _officer 标记识别；内置智能助手、数字警员
  // 默认可管理，不依赖 yuxi 的 can_manage（其桥接记录 created_by 不匹配当前用户）
  const isOfficer = !!agent?._officer || !!detail?._officer
  const manageable = !!detail?.can_manage || isOfficer || isBuiltinAgent(detail)
  if (!manageable) {
    message.warning('当前智能体不可编辑')
    return
  }
  // 同步给下游配置表单（模型/工具/其他配置依赖 selectedAgent.can_manage 判定只读）
  detail.can_manage = manageable

  editingAgentId.value = detail.id
  agentModalActiveTab.value = 'basic'
  Object.assign(agentForm, {
    slug: detail.id || detail.slug || '',
    name: detail.name || '',
    backend_id: detail.backend_id || DEFAULT_AGENT_BACKEND_ID,
    description: detail.description || '',
    icon: detail.icon || '',
    category: detail.category || ''
  })
  await agentStore.selectAgent(detail.id, { allowSubagent: true })
  await agentStore.fetchMentionResources()
  if (!Array.isArray(agentStore.agentConfig?.knowledges)) {
    agentStore.agentConfig.knowledges = []
  }
  // 初始化共享范围配置（单表化：从 share_config 读取，而非已废弃的顶层 share_scope）
  const sc = detail?.share_config || {}
  const scope = sc.access_level || 'user'
  shareConfig.value = {
    access_level: scope === 'global' ? 'global' : scope === 'department' ? 'department' : 'user',
    department_ids: sc.department_ids || [],
    user_uids: sc.user_uids || []
  }
  showAgentModal.value = true
}

const restoreChatAgentSelectionIfNeeded = async () => {
  if (!agentStore.selectedAgent?.is_subagent) return
  const fallbackAgentId = (agentStore.agents || []).find((agent) => !agent.is_subagent)?.id
  if (fallbackAgentId) await agentStore.selectAgent(fallbackAgentId)
}

const closeAgentModal = async () => {
  if (saving.value || agentIconUploading.value) return
  showAgentModal.value = false
  await restoreChatAgentSelectionIfNeeded()
}

const beforeAgentIconUpload = (file) => {
  if (!file.type.startsWith('image/')) {
    message.error('只能上传图片文件')
    return false
  }

  if (file.size > MAX_IMAGE_UPLOAD_SIZE_BYTES) {
    message.error(`图片大小不能超过 ${MAX_IMAGE_UPLOAD_SIZE_MB}MB`)
    return false
  }

  uploadAgentIcon(file)
  return false
}

const uploadAgentIcon = async (file) => {
  agentIconUploading.value = true
  try {
    const data = await userApi.uploadImage(file)
    agentForm.icon = data.image_url || data.url || ''
    message.success('图标上传成功')
  } catch (error) {
    message.error(error.message || '图标上传失败')
  } finally {
    agentIconUploading.value = false
  }
}

const buildAgentPayload = () => {
  const payload = {
    name: agentForm.name.trim(),
    description: agentForm.description.trim() || null,
    icon: agentForm.icon.trim() || null,
    is_subagent: false,
    // 单表化：功能分类写入 agents.category，使其归入数字警员列表
    category: agentForm.category || null
  }

  if (!editingAgentId.value) {
    payload.slug = agentForm.slug.trim() || undefined
    payload.backend_id = agentForm.backend_id
    // 新建智能体默认个人使用，共享权限在档案页单独设置
    payload.share_config = { access_level: 'user', department_ids: [], user_uids: [] }
    // 新建智能体默认不关联任何子智能体（子智能体为内部运行时委派细节，不在 UI 暴露）
    payload.config_json = { context: { subagents: [] } }
  }

  return payload
}

const saveAgent = async () => {
  if (!agentForm.name.trim()) {
    agentModalActiveTab.value = 'basic'
    message.error('请填写智能体名称')
    return
  }

  saving.value = true
  try {
    const payload = buildAgentPayload()
    if (editingAgentId.value) {
      const validatedConfig = runtimeConfigFormRef.value?.validateAndFilterConfig?.()
      if (
        validatedConfig &&
        JSON.stringify(validatedConfig) !== JSON.stringify(agentStore.agentConfig)
      ) {
        agentStore.updateAgentConfig(validatedConfig)
      }
      if (agentStore.hasConfigChanges) {
        payload.config_json = { context: agentStore.agentConfig }
      }
      const updated = await agentStore.updateAgentProfile(editingAgentId.value, payload)
      agentStore.originalAgentConfig = { ...agentStore.agentConfig }
      // 保存共享范围配置
      const configForm = shareConfigFormRef.value
      if (configForm && configForm.validate) {
        const validate = configForm.validate()
        if (validate.valid) {
          // 后端支持 personal / department / user / global 四种共享范围；
          // 「指定人」(user) 会持久化 shared_user_uids，被分享用户即可在智能体页面看到该智能体。
          const scope = shareConfig.value.access_level
          await policeAgentApi.shareAgent(editingAgentId.value, {
            scope,
            department_ids: shareConfig.value.department_ids,
            user_uids: shareConfig.value.user_uids,
            author_id: null
          })
        }
      }
      emit('saved', { mode: 'edit', agent: updated })
      message.success('智能体已保存')
    } else {
      const created = await agentStore.createAgent(payload)
      emit('saved', { mode: 'create', agent: normalizeAgent(created) })
      message.success('智能体已创建')
    }
    showAgentModal.value = false
    await restoreChatAgentSelectionIfNeeded()
  } catch (error) {
    message.error(error.message || '保存智能体失败')
  } finally {
    saving.value = false
  }
}

defineExpose({
  openCreate,
  openEdit,
  close: closeAgentModal
})
</script>

<template>
  <a-modal
    v-model:open="showAgentModal"
    class="agent-edit-modal"
    :width="820"
    :footer="null"
    :closable="false"
    @cancel="closeAgentModal"
    @after-open-change="handleAgentModalAfterOpenChange"
  >
    <template #title>
      <div class="agent-modal-titlebar">
        <span class="agent-modal-title">{{ agentModalTitle }}</span>
        <div class="agent-modal-actions">
          <a-button :disabled="saving" @click="closeAgentModal">取消</a-button>
          <a-button type="primary" :loading="saving" @click="saveAgent">
            {{ agentStore.hasConfigChanges ? '保存（有修改）' : '保存' }}
          </a-button>
        </div>
      </div>
    </template>
    <div
      class="agent-modal-content"
    >
      <aside v-if="showAgentModalSidebar" class="agent-modal-sidebar" aria-label="智能体配置分组">
        <button
          v-for="item in agentModalMenuItems"
          :key="item.key"
          type="button"
          class="agent-modal-nav-item"
          :class="{ active: agentModalActiveTab === item.key }"
          @click="agentModalActiveTab = item.key"
        >
          <span class="nav-item-main">
            <component :is="item.icon" :size="16" />
            <span>{{ item.label }}</span>
          </span>
          <span v-if="item.key === 'model' && agentStore.hasConfigChanges" class="nav-dirty-dot" />
        </button>
      </aside>

      <div class="agent-modal-main">
        <section v-show="agentModalActiveTab === 'basic'" class="agent-modal-section">
          <div class="agent-profile-header">
            <div class="agent-icon-preview" aria-label="智能体图标、名称与类型">
              <div class="agent-profile-main">
                <div class="agent-icon-preview-area">
                  <a-upload
                    :show-upload-list="false"
                    :before-upload="beforeAgentIconUpload"
                    :disabled="agentIconUploading || isGeneratingAvatar"
                    accept="image/*"
                  >
                    <div
                      class="agent-icon-upload"
                      :class="{
                        uploading: agentIconUploading,
                        'is-empty': !agentForm.icon && !editingAgentId,
                        'avatar-shuffling': isGeneratingAvatar
                      }"
                    >
                      <FallbackAvatar
                        v-if="agentForm.icon || editingAgentId"
                        :src="agentForm.icon"
                        :default-src="agentPreviewDefaultIcon"
                        :name="agentPreviewName"
                        :seed="editingAgentId || agentForm.slug || agentForm.name"
                        kind="agent"
                        :size="56"
                        shape="rounded"
                        :alt="`${agentForm.name || '智能体'}图标`"
                        class="agent-icon-preview-avatar"
                      />
                      <div class="agent-icon-mask">
                        <RefreshCw v-if="agentIconUploading" :size="16" class="spinning" />
                        <Upload v-else :size="16" />
                        <span>{{ agentForm.icon ? '更换图标' : '上传图标' }}</span>
                      </div>
                    </div>
                  </a-upload>

                  <!-- 新建模式：随机生成漫画警察形象 -->
                  <button
                    v-if="!editingAgentId"
                    type="button"
                    class="agent-avatar-dice-btn"
                    :disabled="isGeneratingAvatar"
                    @click="generatePoliceAvatar"
                  >
                    <Dices :size="14" :class="{ spinning: isGeneratingAvatar }" />
                    <span>{{ isGeneratingAvatar ? '生成中…' : '随机形象' }}</span>
                  </button>
                </div>
                <div class="agent-icon-preview-text">
                  <input
                    ref="agentNameInputRef"
                    v-model="agentForm.name"
                    class="agent-inline-name-input"
                    type="text"
                    placeholder="点击输入智能体名称"
                    aria-label="智能体名称"
                  />
                  <input
                    v-if="!editingAgentId"
                    v-model="agentForm.slug"
                    class="agent-inline-slug-input"
                    type="text"
                    placeholder="标识可选，留空自动生成"
                    aria-label="智能体标识"
                  />
                  <span v-else class="agent-inline-slug">{{
                    agentForm.slug || editingAgentId
                  }}</span>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-form">
            <label class="form-label full-width">
              <span>描述</span>
              <a-textarea
                v-model:value="agentForm.description"
                class="agent-description-textarea"
                :rows="3"
                placeholder="可选"
              />
            </label>
            <label class="form-label full-width">
              <span>功能分类</span>
              <a-select
                v-model:value="agentForm.category"
                class="agent-category-select"
                placeholder="选择该数字警员的功能分类"
                :options="AGENT_CATEGORIES"
                allow-clear
              />
            </label>
          </div>
        </section>

        <section v-show="agentModalActiveTab === 'other'" class="agent-modal-section">
          <div class="agent-share-section">
            <h4 class="section-title">共享范围</h4>
            <p class="section-desc">设置该智能体的访问范围，其他用户将无法在智能体页面看到或使用此智能体。</p>
            <ShareConfigForm ref="shareConfigFormRef" v-model="shareConfig" :auto-select-user-dept="true" />
            <a-alert v-if="shareConfig.access_level === 'global'" type="warning" show-icon
              message="全局共享需超级管理员审核通过后，将出现在所有人的智能体页面并授予警号。" style="margin-top:12px" />
          </div>
        </section>

        <section v-show="isRuntimeAgentModalTab(agentModalActiveTab)" class="agent-modal-section runtime-section">
          <AgentRuntimeConfigForm
            ref="runtimeConfigFormRef"
            :segment="runtimeConfigSegment"
            :show-segmented="false"
          />
        </section>
      </div>
    </div>
  </a-modal>
</template>

<style lang="less" scoped>
.agent-modal-titlebar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
}

.agent-modal-title {
  color: var(--gray-900);
  font-size: 16px;
  font-weight: 600;
}

.agent-modal-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;

  :deep(.ant-btn) {
    min-width: 70px;
    height: 36px;
    border-radius: 8px;
    font-weight: 500;
  }

  :deep(.ant-btn-primary) {
    border-color: var(--main-700);
    background: var(--main-700);

    &:hover,
    &:focus {
      border-color: var(--main-800);
      background: var(--main-800);
    }
  }
}

.agent-modal-content {
  display: grid;
  grid-template-columns: 144px minmax(0, 1fr);
  height: min(72vh, 640px);
  min-height: 0;
  overflow: hidden;
  background: var(--gray-0);

  &.without-sidebar {
    grid-template-columns: minmax(0, 1fr);
  }

  &.create-mode {
    height: auto;
    min-height: 360px;
  }
}

.agent-modal-sidebar {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 0;
  padding: 14px 10px;
  overflow-y: auto;
  border-right: 1px solid var(--gray-150);
  background: transparent;
}

.agent-modal-nav-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 38px;
  padding: 8px 10px;
  border: 1px solid transparent;
  border-radius: 7px;
  background: transparent;
  color: var(--gray-800);
  font-size: 13px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition:
    background 0.16s ease,
    border-color 0.16s ease,
    color 0.16s ease;

  &:hover {
    background: var(--gray-50);
    color: var(--gray-900);
  }

  &:focus-visible {
    outline: 2px solid var(--main-100);
    outline-offset: 1px;
    border-color: var(--main-200);
  }

  &.active {
    background: var(--main-30);
    color: var(--main-800);

    span {
      font-weight: 600;
    }
  }
}

.nav-item-main {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  gap: 8px;

  svg {
    flex-shrink: 0;
    color: var(--gray-600);
  }
}

.agent-modal-nav-item.active .nav-item-main svg {
  color: var(--main-700);
}

.nav-dirty-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-warning-600);
}

.agent-modal-main {
  min-width: 0;
  min-height: 0;
  overflow: hidden auto;
  overscroll-behavior: contain;
  padding: 22px 18px 24px 24px;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
  scrollbar-color: var(--gray-300) transparent;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    border: 2px solid transparent;
    border-radius: 999px;
    background: var(--gray-300);
    background-clip: content-box;
  }

  &::-webkit-scrollbar-thumb:hover {
    background: var(--gray-400);
    background-clip: content-box;
  }
}

.agent-modal-section {
  min-height: 0;
  background: var(--gray-0);
}

.agent-share-section {
  padding: 16px;
  border: 1px solid var(--gray-100);
  border-radius: 8px;
  background: var(--gray-25);
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--gray-900);
  line-height: 1.4;
  margin: 0 0 4px 0;
}

.section-desc {
  font-size: 13px;
  color: var(--gray-600);
  line-height: 1.5;
  margin: 0 0 14px 0;
}

.runtime-section {
  display: flex;
  flex-direction: column;
  min-height: 100%;

  :deep(.agent-runtime-config-form) {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-height: 0;
    background: transparent;
  }

  :deep(.runtime-config-content) {
    flex: 1;
    min-width: 0;
    min-height: 0;
    padding: 0;
    overflow: visible;
  }
}

.section-heading {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  color: var(--gray-900);
  font-size: 14px;
  font-weight: 600;
}

.agent-profile-header {
  margin-bottom: 16px;
}

.agent-icon-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-width: 0;
  gap: 16px;

  :deep(.ant-upload) {
    display: block;
  }
}

.agent-profile-main {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  gap: 10px;
}

.agent-icon-upload {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  overflow: hidden;
  border: 1px solid var(--gray-200);
  border-radius: 12px;
  background: var(--main-30);
  cursor: pointer;
  transition:
    border-color 0.16s ease,
    box-shadow 0.16s ease;

  .agent-icon-preview-avatar {
    width: 100%;
    height: 100%;
    border: 0;
  }

  &:hover,
  &:focus-within,
  &.uploading {
    border-color: var(--main-300);
    box-shadow: 0 0 0 3px var(--main-50);
  }

  &:hover .agent-icon-mask,
  &:focus-within .agent-icon-mask,
  &.uploading .agent-icon-mask,
  &.is-empty .agent-icon-mask {
    opacity: 1;
  }

  &.is-empty {
    border-style: dashed;
    background: var(--gray-0);
  }
}

.agent-icon-mask {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  background: color-mix(in srgb, var(--gray-900) 62%, transparent);
  color: var(--gray-0);
  font-size: 11px;
  font-weight: 600;
  opacity: 0;
  transition: opacity 0.16s ease;
}

.agent-icon-upload.is-empty .agent-icon-mask {
  background: transparent;
  color: var(--gray-600);
}

.agent-icon-preview-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 4px;
  line-height: 1.25;
}

.agent-inline-name-input {
  width: 200px;
  max-width: 100%;
  padding: 1px 4px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-900);
  caret-color: var(--main-700);
  font-size: 14px;
  font-weight: 600;
  line-height: 1.35;
  transition:
    border-color 0.16s ease,
    background 0.16s ease,
    box-shadow 0.16s ease;

  &::placeholder {
    color: var(--gray-400);
  }

  &:hover {
    border-color: var(--gray-300);
    background: var(--gray-0);
  }

  &:focus {
    border-color: var(--main-300);
    background: var(--gray-0);
    box-shadow: 0 0 0 3px var(--main-50);
    outline: none;
  }
}

.agent-inline-slug,
.agent-inline-slug-input {
  padding: 1px 4px;
  width: 200px;
  max-width: 100%;
  overflow: hidden;
  color: var(--gray-500);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-inline-slug-input {
  border: 1px solid transparent;
  border-radius: 2px;
  background: transparent;

  &::placeholder {
    color: var(--gray-400);
  }

  &:hover,
  &:focus {
    border-color: var(--gray-300);
    background: var(--gray-0);
    outline: none;
  }
}

.agent-backend-summary {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
  gap: 10px;
  width: 190px;
  min-height: 56px;
  padding: 10px 12px;
  border: 1px solid var(--gray-200);
  border-radius: 12px;
  background: var(--gray-10);
  color: var(--gray-700);

  &.editable {
    padding-right: 8px;
  }
}

.agent-backend-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: var(--gray-100);
  color: var(--gray-700);
}

.agent-backend-text {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  gap: 3px;
  line-height: 1.2;
}

.agent-backend-label {
  color: var(--gray-500);
  font-size: 11px;
}

.agent-backend-name {
  max-width: 128px;
  overflow: hidden;
  color: var(--gray-900);
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-backend-select {
  width: 128px;
  margin: -3px 0 -5px -11px;

  :deep(.ant-select-selector) {
    background: transparent !important;
    box-shadow: none !important;
  }

  :deep(.ant-select-selection-item) {
    color: var(--gray-900);
    font-size: 13px;
    font-weight: 600;
  }

  :deep(.ant-select-arrow) {
    color: var(--gray-500);
  }
}

.share-config-block {
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid var(--gray-150);
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-label {
  display: flex;
  flex-direction: column;
  gap: 6px;

  > span {
    color: var(--gray-700);
    font-size: 12px;
    font-weight: 500;
  }
}

.agent-description-textarea {
  min-height: 80px;
  padding: 10px 12px;
  border-color: var(--gray-200);
  border-radius: 8px;
  background: var(--gray-10);
  color: var(--gray-900);
  font-size: 13px;
  line-height: 1.6;
  resize: vertical;
  transition:
    border-color 0.16s ease,
    background 0.16s ease,
    box-shadow 0.16s ease;

  &::placeholder {
    color: var(--gray-400);
  }

  &:hover {
    border-color: var(--gray-300);
    background: var(--gray-0);
  }

  &:focus {
    border-color: var(--main-300);
    background: var(--gray-0);
    box-shadow: 0 0 0 3px var(--main-50);
  }
}

.full-width {
  grid-column: 1 / -1;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.agent-icon-preview-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.agent-avatar-dice-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 12px;
  border: 1px dashed var(--main-300);
  border-radius: 8px;
  background: var(--main-30);
  color: var(--main-700);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.16s ease;

  &:hover:not(:disabled) {
    background: var(--main-50);
    border-style: solid;
  }

  &:disabled {
    opacity: 0.7;
    cursor: wait;
  }
}

.agent-icon-upload.avatar-shuffling {
  animation: avatar-flip 0.12s ease-in-out;
}

@keyframes avatar-flip {
  0% {
    transform: scaleX(1);
  }
  50% {
    transform: scaleX(0);
  }
  100% {
    transform: scaleX(1);
  }
}

@media (max-width: 768px) {
  .agent-modal-content {
    grid-template-columns: 1fr;
    height: min(78vh, 680px);
  }

  .agent-modal-sidebar {
    flex-direction: row;
    overflow-x: auto;
    border-right: 0;
    border-bottom: 1px solid var(--gray-150);
  }
}

:global(.agent-edit-modal .ant-modal-content) {
  overflow: hidden;
  padding: 0;
  border-radius: 12px;
}

:global(.agent-edit-modal .ant-modal-header) {
  margin: 0;
  padding: 18px 24px;
  border-bottom: 1px solid var(--gray-150);
  background: var(--gray-0);
}

:global(.agent-edit-modal .ant-modal-title) {
  width: 100%;
}

:global(.agent-edit-modal .ant-modal-body) {
  padding: 0;
}
</style>
