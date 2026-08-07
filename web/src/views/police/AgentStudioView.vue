<script setup>
/**
 * ★ 全屏 Agent Studio（P4 前端重构）
 *
 * 替代原 AgentEditModal 弹窗：把「基本信息 / 模型配置 / 工具配置 / 其他配置」
 * 收拢为全屏单页，左侧导航分区，右侧为表单主体。
 *
 * 路由：
 *   /agent-manage/studio?create=1         新建智能体（可选「参考已有智能体」复制草稿）
 *   /agent-manage/studio?id=:slugOrId     编辑已有智能体
 */
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ArrowLeft,
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
import {
  generateRandomPoliceAvatar,
  POLICE_AVATAR_IDS,
  getPoliceAvatarById,
  getOfficerAvatar
} from '@/utils/policeAvatar'
import { MAX_IMAGE_UPLOAD_SIZE_BYTES, MAX_IMAGE_UPLOAD_SIZE_MB } from '@/utils/upload_limits'

const route = useRoute()
const router = useRouter()

const userStore = useUserStore()
const agentStore = useAgentStore()

const DEFAULT_AGENT_BACKEND_ID = 'ChatbotAgent'

const runtimeAgentModalTabs = ['model', 'tools', 'other']

const saving = ref(false)
const loading = ref(false)
const editingAgentId = ref(null)
const agentModalActiveTab = ref('basic')
const agentIconUploading = ref(false)
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
  icon: ''
})

// ── P4-4「基于已有智能体复制草稿」：新建模式下可选来源 ──
const templateOptions = ref([])
const templateLoading = ref(false)
const selectedTemplateId = ref(null)

const normalizeAgent = (agent) => {
  const agentId = agent?.agent_id || agent?.slug || agent?.id
  return agentId
    ? { ...agent, id: agentId, agent_id: agentId, slug: agent?.slug || agentId }
    : agent
}

const agentModalMenuItems = computed(() => [
  { key: 'basic', label: '基本信息', icon: Info },
  { key: 'model', label: '模型配置', icon: SlidersHorizontal },
  { key: 'tools', label: '工具配置', icon: Wrench },
  { key: 'other', label: '其他配置', icon: Settings2 }
])

const runtimeConfigSegment = computed(() =>
  runtimeAgentModalTabs.includes(agentModalActiveTab.value) ? agentModalActiveTab.value : 'model'
)
const isRuntimeAgentModalTab = (key) => runtimeAgentModalTabs.includes(key)

const isEditingBuiltinAgent = computed(() => isBuiltinAgent({ id: editingAgentId.value }))
const pageTitle = computed(() => (editingAgentId.value ? '编辑智能体' : '新增智能体'))
const agentPreviewDefaultIcon = computed(() =>
  editingAgentId.value ? getOfficerAvatar(editingAgentId.value) : ''
)
const agentPreviewName = computed(() => agentForm.name || editingAgentId.value || '智能体')

const resetAgentForm = () => {
  Object.assign(agentForm, {
    slug: '',
    name: '',
    backend_id: getDefaultBackendId(),
    description: '',
    icon: ''
  })
  currentAvatarId.value = ''
}

function getDefaultBackendId() {
  return DEFAULT_AGENT_BACKEND_ID
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

// ── P4-4：加载「参考已有智能体」候选（用户可管理的非模板智能体） ──
const loadTemplateOptions = async () => {
  templateLoading.value = true
  try {
    const [policeRes] = await Promise.all([
      policeAgentApi.list({ page_size: 200 }).catch(() => ({ items: [] })),
      agentStore.fetchAgents()
    ])
    const policeList = (policeRes.items || policeRes.agents || []).filter(
      (p) => !p.is_template && !p.is_subagent
    )
    const yuxiAgents = agentStore.agents || []
    const seen = new Set()
    const merged = []
    for (const p of policeList) {
      seen.add(p.id)
      merged.push({ id: p.id, name: p.name, icon: p.icon, _officer: true, description: p.description })
    }
    for (const a of yuxiAgents) {
      if (a.is_subagent || seen.has(a.id)) continue
      merged.push({ id: a.id, name: a.name, icon: a.icon, _officer: false, description: a.description })
    }
    templateOptions.value = merged
  } catch (error) {
    message.error(error.message || '加载参考智能体列表失败')
  } finally {
    templateLoading.value = false
  }
}

/**
 * 选定参考来源：拉取其全量详情，预填名称/描述/图标与运行配置草稿，
 * 保存时以新智能体创建（来源不受影响）。
 */
const applyTemplateDraft = async (templateId) => {
  if (!templateId) return
  try {
    const detail = await agentStore.fetchAgentDetail(templateId, true)
    if (!detail) return
    Object.assign(agentForm, {
      name: detail.name || '',
      description: detail.description || '',
      icon: detail.icon || ''
    })
    await agentStore.selectAgent(templateId, { allowSubagent: true })
    await agentStore.fetchMentionResources()
    if (!Array.isArray(agentStore.agentConfig?.knowledges)) {
      agentStore.agentConfig.knowledges = []
    }
    message.success('已载入参考配置草稿，可修改后另存为新智能体')
  } catch (error) {
    message.error(error.message || '载入参考配置失败')
  }
}

const buildAgentPayload = () => {
  const payload = {
    name: agentForm.name.trim(),
    description: agentForm.description.trim() || null,
    icon: agentForm.icon.trim() || null,
    is_subagent: false
  }

  if (!editingAgentId.value) {
    payload.slug = agentForm.slug.trim() || undefined
    payload.backend_id = agentForm.backend_id
    // 新建智能体默认个人使用，共享权限在档案页/其他配置单独设置
    payload.share_config = { access_level: 'user', department_ids: [], user_uids: [] }
    // 新建默认不关联任何子智能体（子智能体为内部运行时委派细节，不在 UI 暴露）
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
          const scope = shareConfig.value.access_level
          await policeAgentApi.shareAgent(editingAgentId.value, {
            scope,
            department_ids: shareConfig.value.department_ids,
            user_uids: shareConfig.value.user_uids,
            author_id: null
          })
        }
      }
      message.success('智能体已保存')
    } else {
      // 新建：若选择了参考来源，把已载入的运行配置一并带入新智能体
      if (selectedTemplateId.value && agentStore.agentConfig) {
        payload.config_json = { context: { ...agentStore.agentConfig } }
      }
      const created = await agentStore.createAgent(payload)
      message.success('智能体已创建')
      goBack(normalizeAgent(created))
      return
    }
    goBack()
  } catch (error) {
    message.error(error.message || '保存智能体失败')
  } finally {
    saving.value = false
  }
}

const goBack = (created = null) => {
  if (created) {
    router.push({ name: 'AgentProfileComp', params: { id: created.slug || created.id } })
    return
  }
  // 有来源页则返回，否则回智能体管理列表
  if (window.history.length > 1) router.back()
  else router.push({ path: '/agent-manage' })
}

const initFromRoute = async () => {
  loading.value = true
  try {
    const id = route.query.id
    if (id) {
      editingAgentId.value = String(id)
      agentModalActiveTab.value = 'basic'
      const detail = await agentStore.fetchAgentDetail(editingAgentId.value, true)
      const isOfficer = !!detail?._officer
      const manageable = !!detail?.can_manage || isOfficer || isBuiltinAgent(detail)
      if (!manageable) {
        message.warning('当前智能体不可编辑')
        goBack()
        return
      }
      detail.can_manage = manageable
      Object.assign(agentForm, {
        slug: detail.id || detail.slug || '',
        name: detail.name || '',
        backend_id: detail.backend_id || DEFAULT_AGENT_BACKEND_ID,
        description: detail.description || '',
        icon: detail.icon || ''
      })
      await agentStore.selectAgent(detail.id, { allowSubagent: true })
      await agentStore.fetchMentionResources()
      if (!Array.isArray(agentStore.agentConfig?.knowledges)) {
        agentStore.agentConfig.knowledges = []
      }
      // 初始化共享范围配置（单表化：从 share_config 读取）
      const sc = detail?.share_config || {}
      const scope = sc.access_level || 'user'
      shareConfig.value = {
        access_level: scope === 'global' ? 'global' : scope === 'department' ? 'department' : 'user',
        department_ids: sc.department_ids || [],
        user_uids: sc.user_uids || []
      }
    } else {
      // 新建模式
      editingAgentId.value = null
      agentModalActiveTab.value = 'basic'
      resetAgentForm()
      agentStore.resetAgentConfig()
      if (!Array.isArray(agentStore.agentConfig?.knowledges)) {
        agentStore.agentConfig.knowledges = []
      }
      const avatar = generateRandomPoliceAvatar()
      agentForm.icon = avatar.url
      currentAvatarId.value = avatar.id
      await loadTemplateOptions()
      await nextTick(focusAgentNameInput)
    }
  } catch (error) {
    message.error(error.message || '加载智能体失败')
    goBack()
  } finally {
    loading.value = false
  }
}

onMounted(initFromRoute)
watch(() => route.query.id, (nv, ov) => {
  if (nv !== ov) initFromRoute()
})
</script>

<template>
  <div class="studio-page">
    <!-- ===== 顶部栏 ===== -->
    <header class="studio-topbar">
      <div class="studio-topbar-left">
        <button type="button" class="studio-back-btn" aria-label="返回" @click="goBack()">
          <ArrowLeft :size="16" />
        </button>
        <h1 class="studio-title">{{ pageTitle }}</h1>
        <a-tag v-if="isEditingBuiltinAgent" color="blue">内置</a-tag>
      </div>
      <div class="studio-topbar-actions">
        <a-button :disabled="saving" @click="goBack()">取消</a-button>
        <a-button type="primary" :loading="saving" @click="saveAgent">
          {{ agentStore.hasConfigChanges ? '保存（有修改）' : '保存' }}
        </a-button>
      </div>
    </header>

    <div v-if="loading" class="studio-loading">
      <a-spin tip="加载智能体配置中..." />
    </div>

    <div v-else class="studio-body">
      <!-- ===== 左侧导航 ===== -->
      <aside class="studio-sidebar" aria-label="智能体配置分组">
        <button
          v-for="item in agentModalMenuItems"
          :key="item.key"
          type="button"
          class="studio-nav-item"
          :class="{ active: agentModalActiveTab === item.key }"
          @click="agentModalActiveTab = item.key"
        >
          <span class="nav-item-main">
            <component :is="item.icon" :size="16" />
            <span>{{ item.label }}</span>
          </span>
          <span v-if="item.key === 'model' && agentStore.hasConfigChanges" class="nav-dirty-dot" />
        </button>

        <!-- P4-4：新建模式参考来源 -->
        <div v-if="!editingAgentId" class="studio-template-pick">
          <div class="studio-template-label">参考已有智能体</div>
          <a-select
            v-model:value="selectedTemplateId"
            :loading="templateLoading"
            placeholder="可选，复制其配置为草稿"
            allow-clear
            show-search
            option-filter-prop="label"
            class="studio-template-select"
            @change="applyTemplateDraft"
          >
            <a-select-option v-for="t in templateOptions" :key="t.id" :value="t.id" :label="t.name">
              <span class="template-option">
                <span class="template-option-avatar">{{ t.name?.slice(0, 1) || '?' }}</span>
                <span class="template-option-name">{{ t.name }}</span>
                <a-tag v-if="t._officer" size="small" color="green">数字警员</a-tag>
              </span>
            </a-select-option>
          </a-select>
          <p class="studio-template-hint">选择后将预填基本信息与运行配置，保存时创建独立新智能体。</p>
        </div>
      </aside>

      <!-- ===== 右侧主体 ===== -->
      <div class="studio-main">
        <!-- 基本信息 -->
        <section v-show="agentModalActiveTab === 'basic'" class="studio-section">
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
                  <span v-else class="agent-inline-slug">{{ agentForm.slug || editingAgentId }}</span>
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
                :rows="4"
                placeholder="可选"
              />
            </label>
          </div>
        </section>

        <!-- 其他配置（共享范围） -->
        <section v-show="agentModalActiveTab === 'other'" class="studio-section">
          <div class="agent-share-section">
            <h4 class="section-title">共享范围</h4>
            <p class="section-desc">设置该智能体的访问范围，其他用户将无法在智能体页面看到或使用此智能体。</p>
            <ShareConfigForm ref="shareConfigFormRef" v-model="shareConfig" :auto-select-user-dept="true" />
            <a-alert v-if="shareConfig.access_level === 'global'" type="warning" show-icon
              message="全局共享需超级管理员审核通过后，将出现在所有人的智能体页面并授予警号。" style="margin-top:12px" />
          </div>
        </section>

        <!-- 模型 / 工具 / 其他运行配置 -->
        <section v-show="isRuntimeAgentModalTab(agentModalActiveTab)" class="studio-section runtime-section">
          <AgentRuntimeConfigForm
            ref="runtimeConfigFormRef"
            :segment="runtimeConfigSegment"
            :show-segmented="false"
          />
        </section>
      </div>
    </div>
  </div>
</template>

<style lang="less" scoped>
.studio-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--gray-0);
  color: var(--gray-900);
}

// ============ 顶部栏 ============
.studio-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  gap: 16px;
  padding: 14px 24px;
  border-bottom: 1px solid var(--gray-150);
  background: var(--gray-0);

  .studio-topbar-left {
    display: inline-flex;
    align-items: center;
    min-width: 0;
    gap: 12px;
  }

  .studio-back-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: 1px solid var(--gray-200);
    border-radius: 8px;
    background: var(--gray-10);
    color: var(--gray-700);
    cursor: pointer;
    transition: all 0.16s ease;

    &:hover {
      border-color: var(--main-300);
      background: var(--main-30);
      color: var(--main-700);
    }
  }

  .studio-title {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: var(--gray-900);
  }

  .studio-topbar-actions {
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
}

.studio-loading {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  min-height: 0;
}

// ============ 主体 ============
.studio-body {
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr);
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.studio-sidebar {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 0;
  padding: 16px 12px;
  overflow-y: auto;
  border-right: 1px solid var(--gray-150);
  background: var(--gray-10);
}

.studio-nav-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  min-height: 40px;
  padding: 9px 12px;
  border: 1px solid transparent;
  border-radius: 8px;
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

.studio-nav-item.active .nav-item-main svg {
  color: var(--main-700);
}

.nav-dirty-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-warning-600);
}

// ============ P4-4 参考来源 ============
.studio-template-pick {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px dashed var(--gray-300);
}

.studio-template-label {
  margin-bottom: 8px;
  color: var(--gray-600);
  font-size: 12px;
  font-weight: 500;
}

.studio-template-select {
  width: 100%;
}

.template-option {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;

  .template-option-avatar {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    width: 20px;
    height: 20px;
    border-radius: 6px;
    background: var(--main-30);
    color: var(--main-700);
    font-size: 11px;
    font-weight: 600;
  }

  .template-option-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.studio-template-hint {
  margin: 8px 0 0;
  color: var(--gray-500);
  font-size: 11px;
  line-height: 1.5;
}

// ============ 右侧主体 ============
.studio-main {
  min-width: 0;
  min-height: 0;
  overflow: hidden auto;
  overscroll-behavior: contain;
  padding: 24px 28px 40px;
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

.studio-section {
  max-width: 720px;
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

// ============ 基本信息（沿用弹窗样式，去弹窗外壳） ============
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
  width: 240px;
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
  width: 240px;
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
  min-height: 96px;
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
  .studio-body {
    grid-template-columns: 1fr;
  }

  .studio-sidebar {
    flex-direction: row;
    overflow-x: auto;
    border-right: 0;
    border-bottom: 1px solid var(--gray-150);

    .studio-template-pick {
      display: none;
    }
  }
}
</style>
