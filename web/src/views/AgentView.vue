<template>
  <div class="agent-view">
    <div class="agent-view-body">
      <!-- 中间内容区域：三 Tab 均为对话框，仅「皮肤」不同（对齐悟帆：日常办公/能力演进/智能孵化 都是对话框） -->
      <div class="content">
        <!-- 新建对话 hero（对齐悟帆：欢迎语 + 三 Tab 位于输入框上方）；历史对话页不展示 -->
        <div v-if="isNewConversation" class="chat-hero">
          <div class="chat-hero-inner">
            <template v-if="isNewConversation">
              <p class="chat-hero-sub">{{ heroSub }}</p>
              <h1 class="chat-hero-title">{{ heroTitle }}</h1>
            </template>
            <div class="chat-tab-group">
              <SlidingTabs v-model="activeTab" :options="tabOptions" />
            </div>
          </div>
        </div>

        <div class="chat-host">
          <AgentChatComponent
            ref="chatComponentRef"
            :single-mode="false"
            :hide-greeting="true"
            :placeholder="currentPlaceholder"
            @thread-change="handleThreadChange"
          >
            <template #input-actions-left="{ hasActiveThread }">
              <a-dropdown
                v-if="selectedAgentId"
                v-model:open="agentDropdownOpen"
                :trigger="['click']"
                placement="topLeft"
                overlay-class-name="config-dropdown-overlay"
              >
                <button
                  ref="agentDropdownTriggerRef"
                  type="button"
                  class="input-action-btn config-dropdown-trigger"
                  :class="{ disabled: isLoadingConfig }"
                  :aria-label="currentAgentLabel"
                >
                  <FallbackAvatar
                    v-if="currentAgentOption"
                    class="config-dropdown-compact-icon"
                    :src="currentAgentOption.icon"
                    :default-src="currentAgentOption.defaultIcon"
                    :name="currentAgentOption.label"
                    :seed="currentAgentOption.value || currentAgentOption.label"
                    kind="agent"
                    :size="18"
                    shape="rounded"
                    alt=""
                  />
                  <span class="hide-text config-dropdown-text">{{ currentAgentLabel }}</span>
                  <ChevronDown size="15" class="config-dropdown-chevron" />
                </button>

                <template #overlay>
                  <div ref="agentDropdownPanelRef" class="config-dropdown-panel">
                    <button
                      v-for="agent in agentQuickSwitchOptions"
                      :key="agent.value"
                      type="button"
                      class="config-dropdown-item"
                      :class="{
                        selected: agent.value === selectedAgentId,
                        disabled: hasActiveThread && agent.value !== selectedAgentId
                      }"
                      @click="handleAgentSwitch(agent.value, hasActiveThread)"
                    >
                      <FallbackAvatar
                        class="config-dropdown-item-icon-image"
                        :src="agent.icon"
                        :default-src="agent.defaultIcon"
                        :name="agent.label"
                        :seed="agent.value || agent.label"
                        kind="agent"
                        :size="24"
                        shape="rounded"
                        :alt="`${agent.label}图标`"
                      />
                      <span class="config-dropdown-item-label">{{ agent.label }}</span>
                      <span v-if="agent.isBuiltin" class="config-dropdown-item-badge">内置</span>
                      <Check
                        v-if="agent.value === selectedAgentId"
                        :size="14"
                        class="config-dropdown-item-check"
                      />
                    </button>

                    <div v-if="hasActiveThread" class="config-dropdown-hint">
                      当前对话已绑定智能体，新对话可切换。
                    </div>

                    <div class="config-dropdown-divider"></div>

                    <button
                      type="button"
                      class="config-dropdown-item action-item"
                      @click="openAgentManagement"
                    >
                      <Settings2 :size="15" class="config-dropdown-item-icon" />
                      <span class="config-dropdown-item-label">管理智能体</span>
                    </button>
                  </div>
                </template>
              </a-dropdown>
            </template>

            <!-- 能力演进：输入框上方的子切换条（技能/连接器/协助伙伴 + 打造/诊断优化），仅新建对话页 -->
            <template #before-input>
              <div v-if="isNewConversation && activeTab === 'evolution'" class="evo-subtabs">
                <div class="evo-seg">
                  <SlidingTabs v-model="evoCategory" :options="evoCategories" />
                </div>
                <div class="evo-seg">
                  <SlidingTabs v-model="evoAction" :options="evoActions" />
                </div>
              </div>
            </template>

            <!-- 输入框下方推荐语胶囊（按 Tab 不同而不同），仅新建对话页 -->
            <template #after-input>
              <div v-if="isNewConversation" class="usecase-row">
                <button
                  v-for="uc in currentUseCases"
                  :key="uc"
                  type="button"
                  class="usecase-chip"
                  @click="applyUseCase(uc)"
                >
                  <span class="usecase-text">{{ uc }}</span>
                  <span class="usecase-icon">
                    <svg width="11.5" height="11.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 7h10v10"></path><path d="M7 17 17 7"></path></svg>
                  </span>
                </button>
              </div>
            </template>
          </AgentChatComponent>
        </div>
      </div>
    </div>

    <AgentEditModal
      ref="agentEditModalRef"
      :backend-options="agentBackendOptions"
      @saved="handleAgentSaved"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { Settings2, ChevronDown, Check } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { agentApi } from '@/apis/agent_api'
import { useOutsidePointerdown } from '@/composables/useOutsidePointerdown'
import AgentChatComponent from '@/components/AgentChatComponent.vue'
import AgentEditModal from '@/components/model-management/AgentEditModal.vue'
import { isBuiltinAgent, useAgentStore } from '@/stores/agent'
import { handleChatError } from '@/utils/errorHandler'
import FallbackAvatar from '@/components/common/FallbackAvatar.vue'
import SlidingTabs from '@/components/common/SlidingTabs.vue'
import { getOfficerAvatar } from '@/utils/policeAvatar'

import { storeToRefs } from 'pinia'

// ═══════ 新建对话页三 Tab：日常办公 / 能力演进 / 智能孵化（均为对话框，仅皮肤不同，对齐悟帆） ═══════
const activeTab = ref('office')
const tabOptions = [
  { label: '日常办公', value: 'office' },
  { label: '能力演进', value: 'evolution' },
  { label: '智能孵化', value: 'incubation' }
]

// 仅空状态（无选中对话线程）视为「新建对话页」：展示欢迎语、三 Tab、推荐语；
// 进入具体对话（历史对话）后隐藏，历史对话页回归纯聊天界面
const isNewConversation = computed(() => !getRouteThreadId())

// 各 Tab 的欢迎语（对齐悟帆 hero copy）
const heroCopyMap = {
  office: { sub: '嗨，我是小南👋', title: '今天我们做些什么？' },
  evolution: { sub: '连接万物、沉淀方法、召集伙伴', title: '只要你想，我还能变得更强大💪' },
  incubation: { sub: '从零孵化、持续打磨数字民警', title: '打造专属你的 AI 警员' }
}
const heroSub = computed(() => heroCopyMap[activeTab.value]?.sub || heroCopyMap.office.sub)
const heroTitle = computed(() => heroCopyMap[activeTab.value]?.title || heroCopyMap.office.title)

// 各 Tab 输入框占位符
const placeholderMap = {
  office: '想要做些什么？@ 引用文件、技能、协助伙伴，/ 调用强大指令',
  evolution: '描述要沉淀的方法论，或说「把刚才的做法沉淀成技能」',
  incubation: '描述想孵化的数字民警：服务谁、负责什么、在哪里用'
}
const currentPlaceholder = computed(
  () => placeholderMap[activeTab.value] || placeholderMap.office
)

// 各 Tab 的推荐语胶囊
const useCaseMap = {
  office: [
    '帮我把本周笔录整理成结构化摘要',
    '起草一份讯问提纲',
    '分析这起案件的证据链是否完整'
  ],
  evolution: [
    '把我常用的工作流程沉淀成一个技能',
    '帮我接入新的业务数据源',
    '创建一个前端质量把控专家伙伴'
  ],
  incubation: [
    '帮我孵化一个笔录分析数字民警',
    '帮我孵化一个资金追踪助手',
    '帮我孵化一个法制审核专家'
  ]
}
const currentUseCases = computed(() => useCaseMap[activeTab.value] || useCaseMap.office)

// 能力演进子切换条（对齐悟帆：技能/连接器/协助伙伴 + 打造/诊断优化）
const evoCategories = [
  { label: '技能', value: 'skill' },
  { label: '连接器', value: 'connector' },
  { label: '协助伙伴', value: 'partner' }
]
const evoActions = [
  { label: '打造', value: 'build' },
  { label: '诊断优化', value: 'optimize' }
]
const evoCategory = ref('skill')
const evoAction = ref('build')

// 点击推荐语胶囊：预填输入框（不直接发送，由用户确认）
const applyUseCase = (text) => {
  chatComponentRef.value?.prefillInput?.(text)
}

// 组件引用
const chatComponentRef = ref(null)
const agentEditModalRef = ref(null)

// Stores
const agentStore = useAgentStore()
const route = useRoute()
const router = useRouter()

// 从 agentStore 中获取响应式状态
const { agents, selectedAgentId, isLoadingConfig } = storeToRefs(agentStore)

const syncingRouteThread = ref(false)

const getRouteThreadId = () => {
  const value = route.params.thread_id
  return typeof value === 'string' ? value : ''
}

const getRouteAgentId = () => {
  const value = route.query.agent_id
  return typeof value === 'string' ? value : ''
}

const syncSelectedThreadFromRoute = async () => {
  const chatComponent = chatComponentRef.value
  if (!chatComponent?.selectThreadFromRoute) return

  const threadId = getRouteThreadId()
  syncingRouteThread.value = true
  try {
    if (!threadId && !agentStore.isInitialized) {
      await agentStore.initialize()
    }

    const ok = await chatComponent.selectThreadFromRoute(threadId)
    if (threadId && !ok) {
      await router.replace({ name: 'AgentComp' })
    }
  } catch (error) {
    handleChatError(error, 'load')
  } finally {
    syncingRouteThread.value = false
  }
}

const consumeRouteAgentSelection = async () => {
  const targetAgentId = getRouteAgentId()
  if (!targetAgentId || getRouteThreadId()) return

  try {
    if (!agentStore.isInitialized) {
      await agentStore.initialize()
    }

    await nextTick()
    await chatComponentRef.value?.selectThreadFromRoute?.('')
    await agentStore.selectAgent(targetAgentId)
  } catch (error) {
    handleChatError(error, 'load')
  } finally {
    const nextQuery = { ...route.query }
    delete nextQuery.agent_id
    await router.replace({ name: 'AgentComp', query: nextQuery })
  }
}

watch(
  () => route.params.thread_id,
  () => {
    syncSelectedThreadFromRoute()
  },
  { immediate: true }
)

watch(
  () => route.query.agent_id,
  () => {
    consumeRouteAgentSelection()
  },
  { immediate: true }
)

watch(chatComponentRef, (instance) => {
  if (!instance) return
  syncSelectedThreadFromRoute()
})

const handleThreadChange = (threadId) => {
  if (syncingRouteThread.value) return
  const currentRouteThreadId = getRouteThreadId()
  const nextThreadId = threadId || ''
  if (currentRouteThreadId === nextThreadId) return

  if (nextThreadId) {
    router.replace({ name: 'AgentCompWithThreadId', params: { thread_id: nextThreadId } })
  } else {
    router.replace({ name: 'AgentComp' })
  }
}

const agentQuickSwitchOptions = computed(() =>
  (agents.value || [])
    .filter((agent) => !agent.is_subagent)
    .map((agent) => ({
      label: agent.name || agent.id,
      value: agent.id,
      icon: agent.icon || '',
      defaultIcon: agent.id ? getOfficerAvatar(agent.id) : '',
      isBuiltin: isBuiltinAgent(agent)
    }))
)

const currentAgentOption = computed(() =>
  agentQuickSwitchOptions.value.find((agent) => agent.value === selectedAgentId.value)
)

const currentAgentLabel = computed(() => {
  if (isLoadingConfig.value) return '加载中...'
  return currentAgentOption.value?.label || '智能体'
})

const agentDropdownOpen = ref(false)
const agentDropdownTriggerRef = ref(null)
const agentDropdownPanelRef = ref(null)
const agentBackendOptions = ref([])
const agentBackendsLoaded = ref(false)

const loadAgentBackends = async () => {
  if (agentBackendsLoaded.value) return
  const response = await agentApi.getAgentBackends()
  agentBackendOptions.value = (response.backends || []).map((backend) => ({
    label: backend.name || backend.backend_id,
    value: backend.backend_id
  }))
  agentBackendsLoaded.value = true
}

const handleAgentSwitch = async (agentId, hasActiveThread) => {
  if (!agentId || agentId === selectedAgentId.value) return
  if (hasActiveThread) {
    message.info('当前对话已绑定智能体，请新建对话后切换')
    return
  }
  try {
    await agentStore.selectAgent(agentId)
    agentDropdownOpen.value = false
  } catch (error) {
    console.error('切换智能体出错:', error)
    message.error('切换智能体失败')
  }
}

const handleAgentSaved = async () => {
  await agentStore.fetchAgents()
  if (selectedAgentId.value) {
    await agentStore.fetchAgentDetail(selectedAgentId.value, true)
  }
}

const openAgentManagement = async () => {
  agentDropdownOpen.value = false
  if (!selectedAgentId.value) {
    message.warning('请先选择智能体')
    return
  }
  try {
    await loadAgentBackends()
    await agentEditModalRef.value?.openEdit(selectedAgentId.value)
  } catch (error) {
    message.error(error.message || '打开智能体配置失败')
  }
}

useOutsidePointerdown(agentDropdownOpen, [agentDropdownTriggerRef, agentDropdownPanelRef])
</script>

<style lang="less" scoped>
.agent-view {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100vh;
  overflow: hidden;
}

.agent-view-body {
  --gap-radius: 6px;
  display: flex;
  flex-direction: row;
  width: 100%;
  flex: 1;
  height: 100%;
  overflow: hidden;
  position: relative;

.content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* 聊天宿主：占据 hero 以下剩余空间，确保 .chat-container(height:100%) 正确撑满 */
.chat-host {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
}

/* ═══════ 新建对话 hero（日常办公 Tab 内，对齐悟帆：欢迎语 + 三 Tab 位于输入框上方） ═══════ */
.chat-hero {
  flex-shrink: 0;
  display: flex;
  justify-content: center;
  padding: clamp(48px, 9vh, 110px) 24px 8px;
}
.chat-hero-inner {
  width: 100%;
  max-width: 760px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}
.chat-hero-sub {
  margin: 0;
  font-size: 14px;
  font-weight: 450;
  line-height: 1.4;
  color: var(--gray-500, #718096);
  letter-spacing: -0.01em;
}
.chat-hero-title {
  margin: 0 0 14px;
  font-size: clamp(21px, 2.4vw, 28px);
  font-weight: 650;
  line-height: 1.3;
  color: var(--gray-900, #1a202c);
  letter-spacing: -0.02em;
}
.chat-tab-group {
  margin-top: 20px;
}

/* ═══════ 能力演进子切换条（对齐悟帆：技能/连接器/协助伙伴 + 打造/诊断优化） ═══════ */
.evo-subtabs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 0 6px 2px;
  max-width: 760px;
  margin: 0 auto;
  width: 100%;
}
.evo-seg {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}

/* ═══════ 推荐语胶囊（输入框下方，按 Tab 不同） ═══════ */
.usecase-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  max-width: 760px;
  margin: 0 auto;
  width: 100%;
  padding: 2px 24px 10px;
}
.usecase-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 9px 7px 14px;
  font-size: 12.5px;
  line-height: 1.4;
  border-radius: 999px;
  cursor: pointer;
  background: transparent;
  border: 1px solid var(--gray-200, #e2e8f0);
  color: var(--gray-600, #4a5568);
  transition: color 0.15s, border-color 0.15s, background 0.15s;
  white-space: nowrap;
}
.usecase-chip:hover {
  color: var(--gray-900, #1a202c);
  border-color: var(--gray-300, #cbd5e0);
  background: var(--gray-50, #f7fafc);
}
.usecase-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--gray-100, #edf2f7);
  color: var(--gray-500, #718096);
  flex-shrink: 0;
}
.usecase-chip:hover .usecase-icon {
  background: var(--gray-200, #e2e8f0);
  color: var(--gray-700, #4a5568);
}

.config-dropdown-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 0;
  max-width: min(240px, calc(100vw - 160px));
  gap: 4px;
}

.config-dropdown-trigger :deep(svg) {
  color: currentColor;
}

.config-dropdown-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: currentColor;
}

.config-dropdown-chevron {
  flex-shrink: 0;
  color: currentColor;
}

.config-dropdown-compact-icon {
  display: none;
  flex-shrink: 0;
}

@container (max-width: 640px) {
  .config-dropdown-trigger {
    width: 30px;
    padding-inline: 0;
  }

  .config-dropdown-compact-icon {
    display: block;
  }

  .config-dropdown-text,
  .config-dropdown-chevron {
    display: none;
  }
}

// 响应式优化
@media (max-width: 520px) {
  .config-dropdown-trigger {
    max-width: calc(100vw - 112px);
  }
}
</style>

<style lang="less">
.config-dropdown-overlay .config-dropdown-panel {
  min-width: 188px;
  max-width: min(260px, calc(100vw - 24px));
  padding: 4px;
  background: var(--gray-0);
  border: 1px solid var(--gray-100);
  border-radius: 8px;
  box-shadow:
    0 8px 24px rgba(0, 0, 0, 0.08),
    0 2px 8px rgba(0, 0, 0, 0.04);
}

.config-dropdown-overlay .config-dropdown-item {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  width: 100%;
  padding: 6px 8px;
  border: none;
  border-radius: 6px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.config-dropdown-overlay .config-dropdown-item:hover {
  background: var(--gray-50);
}

.config-dropdown-overlay .config-dropdown-item.disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.config-dropdown-overlay .config-dropdown-item.selected {
  background: var(--gray-50);
}

.config-dropdown-overlay .config-dropdown-item.action-item {
  color: var(--gray-800);
}

.config-dropdown-overlay .config-dropdown-item-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  line-height: 1.35;
  color: var(--gray-800);
}

.config-dropdown-overlay .config-dropdown-item-icon,
.config-dropdown-overlay .config-dropdown-item-icon-image,
.config-dropdown-overlay .config-dropdown-item-icon-empty {
  flex-shrink: 0;
}

.config-dropdown-overlay .config-dropdown-item-icon {
  color: var(--gray-500);
}

.config-dropdown-overlay .config-dropdown-item-icon-image,
.config-dropdown-overlay .config-dropdown-item-icon-empty {
  width: 24px;
  height: 24px;
  border-radius: 4px;
}

.config-dropdown-overlay .config-dropdown-item-icon-image {
  object-fit: cover;
}

.config-dropdown-overlay .config-dropdown-item-badge {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--gray-100);
  color: var(--gray-600);
  font-size: 11px;
  line-height: 1.4;
}

.config-dropdown-overlay .config-dropdown-item-check {
  flex-shrink: 0;
  color: var(--main-600);
}

.config-dropdown-overlay .config-dropdown-hint {
  padding: 6px 8px;
  color: var(--gray-500);
  font-size: 12px;
  line-height: 1.4;
}

.config-dropdown-overlay .config-dropdown-divider {
  height: 1px;
  margin: 4px 4px;
  background: var(--gray-100);
}
</style>
