<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { Plus, RefreshCw } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

import { agentApi } from '@/apis/agent_api'
import { policeAgentApi } from '@/apis/police_api'
import AgentEditModal from '@/components/model-management/AgentEditModal.vue'
import { isBuiltinAgent, useAgentStore } from '@/stores/agent'
import PageShoulder from '@/components/shared/PageShoulder.vue'
import AgentCard from '@/components/police/AgentCard.vue'
import ExtensionCardGrid from '@/components/extensions/ExtensionCardGrid.vue'

const agentStore = useAgentStore()
const router = useRouter()
const agentLoading = ref(false)
const searchQuery = ref('')

/** 9 大功能分类（用于列表顶部筛选，直接映射到 police_agents.category） */
const AGENT_CATEGORIES = [
  { key: '', label: '全部' },
  { key: 'case_analysis', label: '案件分析' },
  { key: 'fund_tracking', label: '资金追踪' },
  { key: 'intelligence', label: '情报研判' },
  { key: 'evidence_mgmt', label: '调证取证' },
  { key: 'legal_review', label: '法制审核' },
  { key: 'interrogation', label: '审讯辅助' },
  { key: 'image_recon', label: '图像侦查' },
  { key: 'anti_fraud', label: '反诈劝阻' },
  { key: 'command', label: '指挥调度' }
]
const activeCategory = ref('')

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
 * 以 police_agents（数字警员）为列表主源：后端已按当前用户做可见性过滤，
 * 并按 category 做功能分类筛选。每条记录携带 _officer（police 档案）与对话侧字段。
 * 为保证不遗漏通过对话系统新建的普通智能体（非 police 档案），再联合未被 police 覆盖的 yuxi 智能体。
 */
const buildManagedAgents = (policeList, yuxiAgents) => {
  const yuxiById = new Map()
  for (const a of yuxiAgents || []) {
    const na = normalizeAgent(a)
    if (na.yuxi_id != null) yuxiById.set(na.yuxi_id, na)
  }
  // 单表化：policeList 即 agents 表中带 category 的数字警员（完整 Agent 记录）。
  // 后端 police_agent_repository.list_agents 已按当前用户做可见性过滤并按 category 筛选。
  const policeIds = new Set(
    (policeList || []).map((p) => p.id).filter((v) => v != null)
  )

  const fromPolice = (policeList || []).map((p) => {
    const yuxi = yuxiById.get(p.id) || {}
    const sc = p.share_config || {}
    return {
      ...yuxi,
      // 单表化后直接用 Agent 记录字段（agents 表为唯一数据源）
      id: p.slug || `officer-${p.id}`,
      yuxi_id: p.id,
      agent_id: p.id,
      police_id: p.id,
      slug: p.slug,
      icon: p.icon || yuxi.icon || '',
      avatar: p.icon,
      name: p.name,
      description: p.description,
      category: p.category,
      type: p.type,
      capabilities: p.capabilities,
      tools: p.tools,
      status: p.status,
      // 派生兼容别名：AgentCard / AgentProfileView / 统计 仍引用旧字段名，
      // 这里从 share_config.access_level / badge_number / created_by 推导。
      share_scope: sc.access_level,
      is_public: sc.access_level === 'global',
      approval_status: p.approval_status,
      is_global_approved: p.is_global_approved,
      badge_number: p.badge_number,
      author_id: p.created_by,
      created_by: p.created_by,
      rank: p.rank,
      specialty: p.specialty,
      department: p.department,
      color_theme: p.color_theme,
      _officer: p
    }
  })

  const fromYuxi = (yuxiAgents || [])
    .map(normalizeAgent)
    .filter((a) => a.yuxi_id != null && !policeIds.has(a.yuxi_id))

  return [...fromPolice, ...fromYuxi]
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
  return [
    { key: 'agents', title: '智能体', agents }
  ].filter((group) => group.agents.length > 0)
})

const agentStats = computed(() => ({
  total: managedAgents.value.length,
  builtin: managedAgents.value.filter(isBuiltinAgent).length,
  officers: managedAgents.value.filter((a) => !!a._officer).length,
  manageable: managedAgents.value.filter((agent) => agent.can_manage || !!agent._officer).length,
  global: managedAgents.value.filter((agent) => agent.share_scope === 'global').length
}))

const canManageAgent = (agent) => {
  // 内置智能助手、有 _officer（数字警员/自建智能体）或后端标记可管理 → 显示操作菜单
  return !!agent?.can_manage || !!agent?._officer || isBuiltinAgent(agent)
}
const isOfficer = (agent) => !!agent?._officer
const getAgentStatus = (agent) => {
  if (!isOfficer(agent)) return { text: '内置', color: 'blue' }
  const s = agent._officer?.status
  const map = {
    active: { text: '在线', color: 'green' },
    training: { text: '训练中', color: 'orange' },
    offline: { text: '离线', color: 'red' }
  }
  return map[s] || { text: '离线', color: 'red' }
}

// ============ 导航操作 ============

/** 点击卡片 → 进入档案页 */
const openProfile = (agent) => {
  router.push({ name: 'AgentProfileComp', params: { id: agent.id } })
}

const openAgentChat = (agent) => {
  const chatId = agent?.yuxi_id || agent?.agent_id || agent?.id
  if (!chatId || agent.is_subagent) return
  router.push({ name: 'AgentComp', query: { agent_id: chatId } })
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
      agentApi.getAgents({ includeSubagents: false }),
      policeAgentApi
        .list({ page_size: 200, category: activeCategory.value || undefined })
        .catch(() => ({ items: [] }))
    ])
    const policeList = (policeRes.items || policeRes.agents || [])
      // 过滤市场模板（is_template=1），模板不应出现在智能体管理列表中
      .filter((p) => !p.is_template)
    policeAgentsRaw.value = policeList
    managedAgents.value = buildManagedAgents(policeList, agentRes.agents || [])
  } catch (error) {
    message.error(error.message || '加载智能体失败')
  } finally {
    agentLoading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadAgentBackends(), loadAgents()])
})

watch(activeCategory, () => {
  loadAgents()
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

    <!-- 功能维度筛选（9 大类） -->
    <div class="agent-category-filter">
      <button
        v-for="cat in AGENT_CATEGORIES"
        :key="cat.key"
        type="button"
        class="category-chip"
        :class="{ active: activeCategory === cat.key }"
        @click="activeCategory = cat.key"
      >
        {{ cat.label }}
      </button>
    </div>

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
        <ExtensionCardGrid :min-width="340">
          <AgentCard
            v-for="agent in group.agents"
            :key="agent.id"
            :agent="agent"
            :is-officer="isOfficer(agent)"
            :status-text="getAgentStatus(agent).text"
            :status-color="getAgentStatus(agent).color"
            @click="openProfile(agent)"
            @chat="openAgentChat"
            @edit="openEditAgentModal"
            @delete="deleteAgent"
          />
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

.agent-category-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px var(--page-padding) 4px;
}

.category-chip {
  padding: 5px 14px;
  border: 1px solid var(--gray-200);
  border-radius: 999px;
  background: var(--gray-0);
  color: var(--gray-700);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
  cursor: pointer;
  transition:
    background 0.16s ease,
    border-color 0.16s ease,
    color 0.16s ease;

  &:hover {
    border-color: var(--main-300);
    color: var(--main-800);
  }

  &.active {
    border-color: var(--main-700);
    background: var(--main-700);
    color: #ffffff;
    font-weight: 600;
  }
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
