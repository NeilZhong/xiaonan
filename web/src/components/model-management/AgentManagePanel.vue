<script setup>
import { computed, onMounted, ref } from 'vue'
import { message, Modal } from 'ant-design-vue'
import {
  Plus,
  RefreshCw,
  Trash2,
  SquarePen,
  Bot,
  MessageCirclePlus,
  UserCircle,
  Eye
} from 'lucide-vue-next'
import { useRouter } from 'vue-router'

import { agentApi } from '@/apis/agent_api'
import { policeAgentApi } from '@/apis/police_api'
import AgentEditModal from '@/components/model-management/AgentEditModal.vue'
import { isBuiltinAgent, useAgentStore } from '@/stores/agent'
import PageShoulder from '@/components/shared/PageShoulder.vue'
import InfoCard from '@/components/shared/InfoCard.vue'
import FallbackAvatar from '@/components/common/FallbackAvatar.vue'
import ExtensionCardGrid from '@/components/extensions/ExtensionCardGrid.vue'
import { generatePixelAvatar } from '@/utils/pixelAvatar'

const agentStore = useAgentStore()
const router = useRouter()
const agentLoading = ref(false)
const searchQuery = ref('')

const agentBackendOptions = ref([])
const managedAgents = ref([])
/** 数字警员原始列表（用于与 agents 表数据合并） */
const policeAgentsRaw = ref([])
const agentEditModalRef = ref(null)

const normalizeAgent = (agent) => {
  const rawId = agent?.id            // yuxi 智能体 int 主键（关联 police_agents.agent_id）
  const agentId = agent?.agent_id || agent?.slug || rawId
  return agentId
    ? { ...agent, id: agentId, agent_id: agentId, slug: agent?.slug || agentId, yuxi_id: rawId }
    : agent
}

/**
 * 将数字警员（police_agents）数据合并到智能体（agents）列表上。
 * 匹配键：police_agent.agent_id（int 外键）=== agent.yuxi_id（yuxi 智能体 int 主键）。
 * 合并后每条 agent 记录会携带 _officer 附加字段（含 badge_number / rank / department 等）。
 */
const mergePoliceData = (agents, policeList) => {
  const policeMap = new Map()
  for (const p of policeList || []) {
    if (p.agent_id != null) policeMap.set(p.agent_id, p)
  }
  return (agents || []).map((a) => {
    const officer = policeMap.get(a.yuxi_id)
    return officer ? { ...a, _officer: officer } : a
  })
}

const filteredAgents = computed(() => {
  const keyword = searchQuery.value.trim().toLowerCase()
  const list = managedAgents.value || []
  const filtered = keyword
    ? list.filter(
        (agent) =>
          String(agent.name || '')
            .toLowerCase()
            .includes(keyword) ||
          String(agent.id || '')
            .toLowerCase()
            .includes(keyword) ||
          String(agent.backend_id || '')
            .toLowerCase()
            .includes(keyword) ||
          String(agent._officer?.badge_number || '').toLowerCase().includes(keyword)
      )
    : list
  return [...filtered].sort((a, b) => {
    // 内置智能体排最前，其次数字警员，最后普通智能体
    const aBuiltin = isBuiltinAgent(a)
    const bBuiltin = isBuiltinAgent(b)
    if (aBuiltin !== bBuiltin) return aBuiltin ? -1 : 1
    const aOfficer = !!a._officer
    const bOfficer = !!b._officer
    if (aOfficer !== bOfficer) return aOfficer ? -1 : 1
    return String(a.name || a.id).localeCompare(String(b.name || b.id), 'zh-CN')
  })
})

const groupedAgents = computed(() => {
  const agents = filteredAgents.value.filter((agent) => !agent.is_subagent)
  const subagents = filteredAgents.value.filter((agent) => agent.is_subagent)
  return [
    { key: 'agents', title: '智能体', agents },
    { key: 'subagents', title: '子智能体', agents: subagents }
  ].filter((group) => group.agents.length > 0)
})

const agentStats = computed(() => ({
  total: managedAgents.value.length,
  builtin: managedAgents.value.filter(isBuiltinAgent).length,
  officers: managedAgents.value.filter((a) => !!a._officer).length,
  manageable: managedAgents.value.filter((agent) => agent.can_manage).length,
  global: managedAgents.value.filter((agent) => agent.share_config?.access_level === 'global')
    .length
}))

const canManageAgent = (agent) => {
  // 内置智能助手、有 _officer（数字警员/自建智能体）或后端标记可管理 → 显示操作菜单
  return !!agent?.can_manage || !!agent?._officer || isBuiltinAgent(agent)
}
const isOfficer = (agent) => !!agent?._officer
const getAgentDefaultIconSrc = (agent) => (agent.id ? generatePixelAvatar(agent.id) : '')

// ============ 导航操作 ============

/** 点击卡片 → 进入档案页 */
const openProfile = (agent) => {
  router.push({ name: 'AgentProfileComp', params: { id: agent.id } })
}

const openAgentChat = (agent) => {
  if (!agent?.id || agent.is_subagent) return
  router.push({ name: 'AgentComp', query: { agent_id: agent.id } })
}

// ============ 编辑 / 删除（统一使用 AgentEditModal） ============

const openCreateAgentModal = () => {
  agentEditModalRef.value?.openCreate()
}

const openEditAgentModal = (agent) => {
  if (!canManageAgent(agent)) return
  agentEditModalRef.value?.openEdit(agent)
}

const refreshAgentLists = async () => {
  await Promise.all([loadAgents(), agentStore.fetchAgents()])
}

const deleteAgent = async (agent) => {
  if (isBuiltinAgent(agent)) {
    message.warning('内置智能体不能删除')
    return
  }
  // 安全检查：防止误删市场模板（is_template=1）
  if (agent._officer?.is_template) {
    message.warning('市场模板不能在智能体管理页删除')
    return
  }
  const officer = agent._officer
  Modal.confirm({
    title: `删除 ${agent.name}`,
    content: officer
      ? '删除后该数字警员及其关联的对话智能体也将一并移除，不可恢复。'
      : '删除后不可恢复，已绑定该智能体的历史对话仍保留原始绑定信息。',
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      try {
        // 数字警员优先走 police 删除（级联清理 yuxi 智能体）
        if (officer) {
          await policeAgentApi.delete(officer.id)
        } else {
          await agentApi.deleteAgent(agent.id)
        }
        await refreshAgentLists()
        message.success('已删除')
      } catch (error) {
        message.error(error.message || '删除失败')
      }
    }
  })
}

// ============ 数据加载 ============

const loadAgentBackends = async () => {
  try {
    const response = await agentApi.getAgentBackends()
    agentBackendOptions.value = (response.backends || []).map((backend) => ({
      label: backend.name || backend.backend_id,
      value: backend.backend_id
    }))
  } catch (error) {
    message.error(error.message || '加载智能体后端失败')
  }
}

const loadAgents = async () => {
  agentLoading.value = true
  try {
    const [agentRes, policeRes] = await Promise.all([
      agentApi.getAgents({ includeSubagents: true }),
      policeAgentApi.list({ page_size: 200 }).catch(() => ({ items: [] }))
    ])
    const policeList = (policeRes.items || policeRes.agents || [])
      // 过滤市场模板（is_template=1），模板不应出现在智能体管理列表中
      .filter((p) => !p.is_template)
    policeAgentsRaw.value = policeList
    managedAgents.value = mergePoliceData(
      (agentRes.agents || []).map(normalizeAgent),
      policeList
    )
  } catch (error) {
    message.error(error.message || '加载智能体失败')
  } finally {
    agentLoading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadAgentBackends(), loadAgents()])
})

defineExpose({
  loading: agentLoading,
  stats: agentStats,
  refresh: refreshAgentLists
})
</script>

<template>
  <div class="agent-manage-panel">
    <PageShoulder v-model:search="searchQuery" search-placeholder="搜索智能体或数字警员...">
      <template #actions>
        <a-button type="primary" class="lucide-icon-btn" @click="openCreateAgentModal">
          <Plus :size="14" />
          新增智能体
        </a-button>
        <a-button class="lucide-icon-btn" @click="loadAgents" :loading="agentLoading">
          <RefreshCw :size="14" :class="{ spinning: agentLoading }" />
        </a-button>
      </template>
    </PageShoulder>

    <div v-if="groupedAgents.length === 0" class="agent-empty-state">
      <a-empty
        :image="false"
        :description="searchQuery ? '没有匹配的智能体' : '暂无智能体，点击右上角新增'"
      />
    </div>

    <template v-else>
      <section v-for="group in groupedAgents" :key="group.key" class="agent-group-section">
        <div class="agent-group-header">
          <span>{{ group.title }}</span>
          <span v-if="group.key === 'agents'" class="group-count">
            共 {{ group.agents.length }} 个
            <template v-if="agentStats.officers">（{{ agentStats.officers }} 名数字警员）</template>
          </span>
        </div>
        <ExtensionCardGrid :min-width="320">
          <InfoCard
            v-for="agent in group.agents"
            :key="agent.id"
            :title="agent.name"
            :subtitle="agent._officer ? `${agent.slug || agent.id} · 工号 ${agent._officer.badge_number}` : (agent.slug || agent.id)"
            :description="agent.description || '暂无描述'"
            :default-icon="isOfficer(agent) ? UserCircle : Bot"
            :tags="[]"
            class="config-card agent-card"
            @click="openProfile(agent)"
          >
            <template #icon>
              <div class="agent-card-icon-wrapper">
                <FallbackAvatar
                  class="agent-card-icon-image"
                  :src="agent.icon"
                  :default-src="getAgentDefaultIconSrc(agent)"
                  :name="agent.name || agent.id"
                  :seed="agent.id || agent.name"
                  kind="agent"
                  :size="40"
                  shape="rounded"
                  :alt="`${agent.name || '智能体'}图标`"
                />
                <!-- 数字警员角标 -->
                <span v-if="isOfficer(agent)" class="officer-badge" title="数字警员">
                  <UserCircle :size="10" />
                </span>
              </div>
            </template>

            <template v-if="canManageAgent(agent)" #card-more-action-corner>
              <a-menu>
                <a-menu-item key="profile" @click.stop="openProfile(agent)">
                  <span class="lucide-menu-item">
                    <Eye :size="14" />
                    <span>查看档案</span>
                  </span>
                </a-menu-item>
                <a-menu-item key="edit" @click.stop="openEditAgentModal(agent)">
                  <span class="lucide-menu-item">
                    <SquarePen :size="14" />
                    <span>编辑</span>
                  </span>
                </a-menu-item>
                <a-menu-item
                  key="delete"
                  :disabled="isBuiltinAgent(agent)"
                  :danger="!isBuiltinAgent(agent)"
                  @click.stop="deleteAgent(agent)"
                >
                  <span class="lucide-menu-item">
                    <Trash2 :size="14" />
                    <span>删除</span>
                  </span>
                </a-menu-item>
              </a-menu>
            </template>

            <template v-if="group.key === 'agents'" #tags>
              <div class="agent-card-actions">
                <a-button
                  type="text"
                  size="small"
                  class="lucide-icon-btn agent-profile-entry"
                  @click.stop="openProfile(agent)"
                >
                  <Eye :size="14" />
                  档案
                </a-button>
                <a-button
                  type="text"
                  size="small"
                  class="lucide-icon-btn agent-chat-entry"
                  @click.stop="openAgentChat(agent)"
                >
                  <MessageCirclePlus :size="14" />
                  对话
                </a-button>
              </div>
            </template>
          </InfoCard>
        </ExtensionCardGrid>
      </section>
    </template>

    <AgentEditModal
      ref="agentEditModalRef"
      :backend-options="agentBackendOptions"
      @saved="refreshAgentLists"
    />
  </div>
</template>

<style lang="less" scoped>
.agent-manage-panel {
  height: 100%;
  min-height: 0;
}

.agent-empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 100px 20px;
  text-align: center;
}

.agent-group-section + .agent-group-section {
  padding-top: 2px;
}

.agent-group-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px var(--page-padding) 0;
  color: var(--gray-500);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.4px;
  line-height: 18px;
}

.group-count {
  font-weight: 400;
  opacity: 0.7;
}

.agent-card-icon-image {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
}

.agent-card-icon-wrapper {
  position: relative;
  display: block;
  width: 100%;
  height: 100%;
}

/* 数字警员角标：右下角小圆点 */
.officer-badge {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 18px;
  height: 18px;
  background: var(--main-700);
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}

.officer-hint {
  font-size: 11px;
  color: var(--main-700);
  background: var(--main-30);
  padding: 1px 8px;
  border-radius: 6px;
  margin-left: 6px;
}

.agent-card {
  cursor: pointer;

  &:hover {
    border-color: var(--main-200);
    box-shadow: 0 4px 14px var(--shadow-2);
  }
}

.agent-card :deep(.info-card-tags) {
  justify-content: flex-start;
  margin-top: auto;
}

.agent-card-actions {
  display: flex;
  justify-content: flex-start;
  gap: 4px;
  width: 100%;
  margin-top: auto;
}

.agent-profile-entry,
.agent-chat-entry {
  min-width: 64px;
  height: 32px;
  padding: 2px 10px;
  border: 0;
  border-radius: 8px;
  background: var(--gray-100);
  box-shadow: none;
  color: var(--gray-800);
  font-size: 12px;

  &:hover {
    border: 0;
    background: var(--gray-700);
    box-shadow: none;
    color: var(--gray-0);
  }

  &:focus:not(:focus-visible) {
    outline: none;
  }

  &:focus-visible {
    outline: 2px solid var(--main-200);
    outline-offset: 2px;
  }
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
</style>
