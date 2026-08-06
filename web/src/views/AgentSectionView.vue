<script setup>
/**
 * 智能体档案 - 区块子页（悟帆 AI 员工页风格）
 *
 * 顶部：返回按钮 + 标签页（灵魂 / 技能 / 连接器 / 协助伙伴 / 记忆 图标切换，就地切换内容）
 * 左侧：智能体简明信息（头像 / 名称 / 状态 / 介绍，只读）
 * 右侧：当前区块详情
 *   soul       灵魂        → system_prompt
 *   skills     技能        → skills 表（装备技能控制台）
 *   connectors 连接器与工具 → config_json.context.mcps / tools（装备连接器控制台）
 *   partners   协助伙伴    → 数字警员装备区（已装备=空间资产 / 可装备=天赋资产，开关接 equip/unequip）
 *   memory     记忆        → 当前用户工作区 MEMORY.md
 */
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  Sparkles, Wrench, Users, Brain, ArrowLeft, BookOpen, CircleHelp, Search, WandSparkles,
  Cable, PenLine
} from 'lucide-vue-next'

import { agentApi } from '@/apis/agent_api'
import { policeAgentApi, policeEquipApi } from '@/apis/police_api'
import { skillApi } from '@/apis/skill_api'
import { getMcpServers } from '@/apis/mcp_api'
import { getWorkspaceFileContent, saveWorkspaceFileContent } from '@/apis/workspace_api'
import { resolveAgentAvatar } from '@/utils/policeAvatar'

const route = useRoute()
const router = useRouter()

const TABS = [
  { key: 'soul', title: '灵魂', subtitle: '系统提示词 · 智能体人格', icon: Sparkles },
  { key: 'skills', title: '技能', subtitle: '能力标签与工具', icon: Wrench },
  { key: 'connectors', title: '连接器与工具', subtitle: 'MCP 服务与平台内置工具', icon: Cable },
  { key: 'partners', title: '协助伙伴', subtitle: '协作的数字警员', icon: Users },
  { key: 'memory', title: '记忆', subtitle: '对当前用户的记忆', icon: Brain },
]

const agent = ref(null)
const officer = ref(null)
const loading = ref(false)
const baseLoaded = ref(false)
const contentRef = ref(null)

const section = computed(() => route.params.section)
const activeTab = computed(() => TABS.find((t) => t.key === section.value) || TABS[0])

const avatarUrl = computed(() => resolveAgentAvatar(agent.value))
const isOfficer = computed(() => !!officer.value)
const statusText = computed(() => {
  if (!agent.value) return '未知'
  if (isOfficer.value) {
    const s = officer.value?.status
    return { active: '在线', training: '训练中', offline: '离线' }[s] || '离线'
  }
  return '正常'
})
const statusColor = computed(() => {
  if (isOfficer.value) return { active: 'green', training: 'orange', offline: 'red' }[officer.value?.status] || 'red'
  return 'green'
})

// 连接器与工具（装备控制台，直接读写 config_json.context.mcps / tools）
const MCP_TRANSPORT_LABEL = { sse: 'SSE', streamable_http: 'HTTP', stdio: 'STDIO' }

const mcpServers = ref([])
const connectorSearch = ref('')
const connectorFilter = ref('all') // all | on | off
const savingResource = ref([])

const agentContext = computed(() => agent.value?.config_json?.context || {})
const canManageAgent = computed(() => agent.value?.can_manage !== false)
const mcpOptions = computed(() => agent.value?.configurable_items?.mcps?.options || [])
const toolOptions = computed(() => agent.value?.configurable_items?.tools?.options || [])

/** context.mcps / context.tools 为 null 表示「默认全部启用」，数组则是显式白名单 */
const isResourceOn = (kind, key) => {
  const selected = agentContext.value[kind]
  return selected == null ? true : selected.includes(key)
}
/** 集合状态：all=默认全部 / none=全部关闭 / custom=显式挑选 */
const groupMode = (kind) => {
  const selected = agentContext.value[kind]
  if (selected == null) return 'all'
  return selected.length === 0 ? 'none' : 'custom'
}

const matchesConnectorSearch = (item) => {
  const q = connectorSearch.value.trim().toLowerCase()
  if (!q) return true
  return [item.name, item.key, item.description].filter(Boolean).join(' ').toLowerCase().includes(q)
}
const matchesConnectorFilter = (kind, key) => {
  if (connectorFilter.value === 'on') return isResourceOn(kind, key)
  if (connectorFilter.value === 'off') return !isResourceOn(kind, key)
  return true
}

const mcpCards = computed(() =>
  mcpOptions.value
    .map((o) => {
      const server = mcpServers.value.find((s) => s.slug === o.key) || {}
      const transport = MCP_TRANSPORT_LABEL[server.transport] || 'MCP'
      return { ...o, badge: 'MCP', meta: `${transport} · ${server.enabled === false ? '平台已停用' : '平台已上线'}` }
    })
    .filter((o) => matchesConnectorSearch(o) && matchesConnectorFilter('mcps', o.key))
)
const toolCards = computed(() =>
  toolOptions.value
    .map((o) => ({ ...o, badge: '内置工具', meta: o.key }))
    .filter((o) => matchesConnectorSearch(o) && matchesConnectorFilter('tools', o.key))
)

const mcpEnabledCount = computed(() => mcpOptions.value.filter((o) => isResourceOn('mcps', o.key)).length)
const toolEnabledCount = computed(() => toolOptions.value.filter((o) => isResourceOn('tools', o.key)).length)
const percent = (part, total) => (total ? `${Math.round((part / total) * 100)}%` : '0%')

async function saveContextPatch(patch) {
  const slug = agent.value?.slug
  if (!slug) return
  const resp = await agentApi.updateAgent(slug, {
    config_json: { context: { ...agentContext.value, ...patch } }
  })
  const updated = resp?.agent || resp
  if (updated) agent.value = { ...agent.value, ...updated }
}

async function toggleResource(kind, key) {
  if (!canManageAgent.value || savingResource.value.includes(key)) return
  const options = kind === 'mcps' ? mcpOptions.value : toolOptions.value
  const selected = agentContext.value[kind]
  // 从「默认全部」改动单项时，先固化为显式列表再增删
  const base = selected == null ? options.map((o) => o.key) : [...selected]
  const next = base.includes(key) ? base.filter((k) => k !== key) : [...base, key]

  savingResource.value.push(key)
  try {
    await saveContextPatch({ [kind]: next })
  } catch (e) {
    message.error('保存失败: ' + (e.message || e))
  } finally {
    savingResource.value = savingResource.value.filter((k) => k !== key)
  }
}

async function setGroupMode(kind, mode) {
  if (!canManageAgent.value || groupMode(kind) === mode) return
  const options = kind === 'mcps' ? mcpOptions.value : toolOptions.value
  const selected = agentContext.value[kind]
  // all 交回平台默认（后续新增的资源自动获得），none 全部关闭，custom 固化当前有效选择
  const value = mode === 'all' ? null : mode === 'none' ? [] : selected ?? options.map((o) => o.key)
  try {
    await saveContextPatch({ [kind]: value })
  } catch (e) {
    message.error('保存失败: ' + (e.message || e))
  }
}

async function loadConnectors() {
  // 警号入口拿到的是档案数据，不含 configurable_items，需补一次 yuxi 详情
  const slug = agent.value?.slug
  if (slug && !agent.value?.configurable_items) {
    const resp = await agentApi.getAgentDetail(slug)
    agent.value = { ...agent.value, ...(resp?.agent || resp) }
  }
  try {
    const res = await getMcpServers()
    mcpServers.value = res?.data || []
  } catch (e) {
    console.warn('加载 MCP 服务失败', e)
  }
}

// 记忆（当前用户工作区 MEMORY.md：查看 / 搜索 / 按类型筛选 / 编辑写回）
const memoryText = ref('')
const memoryMissing = ref(false)
const memoryLoading = ref(false)
const memoryEditing = ref(false)
const memoryDraft = ref('')
const memorySearch = ref('')
const memoryTypeFilter = ref('all') // all | fact | context | procedure | 其他标题
const savingMemory = ref(false)

// 将 MEMORY.md 按二级/三级标题切分为记忆条目，标题文本作为类型
function parseMemoryEntries(text) {
  const lines = (text || '').split('\n')
  const entries = []
  let current = null
  const push = () => {
    if (current && (current.content.trim() || current.type !== '未分类')) entries.push(current)
  }
  for (const line of lines) {
    const m = line.match(/^#{2,3}\s+(.+?)\s*$/)
    if (m) {
      push()
      current = { type: m[1].trim(), content: '' }
    } else {
      if (!current) current = { type: '未分类', content: '' }
      current.content += line + '\n'
    }
  }
  push()
  return entries
}

const MEMORY_STANDARD_TYPES = ['fact', 'context', 'procedure']
const memoryEntries = computed(() => parseMemoryEntries(memoryText.value))
// 过滤按钮：全部 + 标准三类（与悟帆一致，始终展示）+ 实际存在的额外类型
const memoryTypes = computed(() => {
  const present = new Set(memoryEntries.value.map((e) => e.type))
  const types = [...MEMORY_STANDARD_TYPES]
  for (const t of present) if (!MEMORY_STANDARD_TYPES.includes(t)) types.push(t)
  return types
})
const memoryFiltered = computed(() => {
  const q = memorySearch.value.trim().toLowerCase()
  return memoryEntries.value.filter((e) => {
    if (memoryTypeFilter.value !== 'all' && e.type !== memoryTypeFilter.value) return false
    if (q && !`${e.type} ${e.content}`.toLowerCase().includes(q)) return false
    return true
  })
})

async function loadMemory() {
  memoryLoading.value = true
  try {
    const blob = await getWorkspaceFileContent('MEMORY.md')
    const raw = await blob.text()
    try {
      const j = JSON.parse(raw)
      memoryText.value = j.content || raw
    } catch {
      memoryText.value = raw
    }
    memoryMissing.value = false
  } catch (e) {
    memoryMissing.value = true
    memoryText.value = ''
  } finally {
    memoryLoading.value = false
  }
}

function startEditMemory() {
  memoryDraft.value = memoryText.value
  memoryEditing.value = true
}
async function saveMemory() {
  if (savingMemory.value) return
  savingMemory.value = true
  try {
    await saveWorkspaceFileContent('MEMORY.md', memoryDraft.value)
    memoryText.value = memoryDraft.value
    memoryEditing.value = false
    message.success('记忆已保存')
  } catch (e) {
    message.error('保存失败: ' + (e.message || e))
  } finally {
    savingMemory.value = false
  }
}
function cancelEditMemory() {
  memoryEditing.value = false
  memoryDraft.value = ''
}

// 技能（装备技能控制台，复用 /api/system/skills 真实数据）
const allSkills = ref([])
const skillsLoading = ref(false)
const skillSearch = ref('')
const skillFilter = ref('all') // all | enabled | disabled
const skillToggling = ref([])
const isSkillToggling = (slug) => skillToggling.value.includes(slug)
const canManageSkill = (s) => s?.can_manage !== false

async function loadSkills() {
  skillsLoading.value = true
  try {
    const r = await skillApi.listSkills()
    allSkills.value = r?.data || []
  } catch (e) {
    message.error('加载技能失败: ' + (e.message || e))
  } finally {
    skillsLoading.value = false
  }
}

const skillMatches = (s) => {
  if (!skillSearch.value) return true
  const q = skillSearch.value.toLowerCase()
  return [s.name, s.slug, s.description].filter(Boolean).join(' ').toLowerCase().includes(q)
}
const skillByStatus = (s) => {
  if (skillFilter.value === 'enabled') return s.enabled !== false
  if (skillFilter.value === 'disabled') return s.enabled === false
  return true
}
const spaceSkills = computed(() =>
  allSkills.value.filter((s) => s.source_type !== 'builtin' && skillMatches(s) && skillByStatus(s))
)
const innateSkills = computed(() =>
  allSkills.value.filter((s) => s.source_type === 'builtin' && skillMatches(s) && skillByStatus(s))
)

async function toggleSkill(s) {
  if (!canManageSkill(s) || isSkillToggling(s.slug)) return
  const next = s.enabled === false
  skillToggling.value.push(s.slug)
  try {
    const r = await skillApi.updateSkillEnabled(s.slug, next)
    const updated = r?.data
    const idx = allSkills.value.findIndex((x) => x.slug === s.slug)
    if (updated && idx > -1) allSkills.value[idx] = updated
    else s.enabled = next
    message.success(`技能「${s.name || s.slug}」已${next ? '启用' : '禁用'}`)
  } catch (e) {
    message.error('更新技能状态失败: ' + (e.message || e))
  } finally {
    skillToggling.value = skillToggling.value.filter((x) => x !== s.slug)
  }
}

// 协助伙伴（数字警员装备区：已装备=空间资产，可装备候选=天赋资产）
const partnerSearch = ref('')
const partnerFilter = ref('all') // all | on | off
const equippedPartners = ref([])
const availablePartners = ref([])
const savingPartner = ref([])
const partnerAgentId = computed(() => agent.value?.id)

const matchesPartnerSearch = (p) => {
  const q = partnerSearch.value.trim().toLowerCase()
  if (!q) return true
  return [p.name, p.slug, p.description].filter(Boolean).join(' ').toLowerCase().includes(q)
}
// 空间资产（已装备）随「开启/全部」出现；天赋资产（可装备）随「未开启/全部」出现
const equippedView = computed(() => {
  if (partnerFilter.value === 'off') return []
  return equippedPartners.value.filter(matchesPartnerSearch)
})
const availableView = computed(() => {
  if (partnerFilter.value === 'on') return []
  return availablePartners.value.filter(matchesPartnerSearch)
})

async function loadPartners() {
  const id = partnerAgentId.value
  if (!id) return
  try {
    const [eq, av] = await Promise.all([
      policeEquipApi.listEquipped(id),
      policeEquipApi.listAvailable(id),
    ])
    equippedPartners.value = eq?.items || []
    availablePartners.value = av?.items || []
  } catch (e) {
    console.warn('加载协助伙伴失败', e)
  }
}

async function togglePartner(p, equip) {
  const id = partnerAgentId.value
  if (!id || !canManageAgent.value || savingPartner.value.includes(p.id)) return
  savingPartner.value.push(p.id)
  try {
    if (equip) await policeEquipApi.equip(id, p.id)
    else await policeEquipApi.unequip(id, p.id)
    await loadPartners()
  } catch (e) {
    message.error('操作失败: ' + (e.message || e))
  } finally {
    savingPartner.value = savingPartner.value.filter((x) => x !== p.id)
  }
}

function showPartnerHelp() {
  message.info('协助伙伴（子智能体）可由本智能体在运行时委派协作，例如代码探索、资料检索、验证等专用助手。')
}

// ============ 数据加载 ============
async function loadBase() {
  const id = route.params.id
  const isBadge = /^DA-[\w-]+$/.test(id || '')
  const policeData = isBadge ? await policeAgentApi.getByBadgeNumber(id).catch(() => null) : null
  if (policeData?.id) {
    officer.value = policeData
    agent.value = policeData
  } else {
    const agentResp = await agentApi.getAgentDetail(id)
    const agentObj = agentResp?.agent || agentResp
    agent.value = agentObj
    const yuxiId = agentObj?.id
    if (yuxiId != null) {
      const pd = await policeAgentApi.getByYuxiId(yuxiId).catch(() => null)
      if (pd && (pd.id || pd.agent_id)) officer.value = pd
    }
  }
  baseLoaded.value = true
}

async function loadSectionData() {
  if (!baseLoaded.value) return
  const sec = section.value
  mcpServers.value = []
  memoryText.value = ''
  memoryMissing.value = false
  memoryEditing.value = false
  memoryDraft.value = ''
  if (sec === 'connectors') {
    await loadConnectors()
  } else if (sec === 'skills') {
    await loadSkills()
  } else if (sec === 'partners') {
    await loadPartners()
  } else if (sec === 'memory') {
    await loadMemory()
  }
  nextTick(() => {
    if (contentRef.value) contentRef.value.scrollTop = 0
  })
}

async function load() {
  loading.value = true
  try {
    await loadBase()
    await loadSectionData()
  } catch (e) {
    message.error('加载失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

function switchSection(key) {
  const id = route.params.id
  router.push({ path: `/agent-manage/${encodeURIComponent(id)}/section/${key}` })
}
function goBack() {
  const id = route.params.id
  router.push({ path: `/agent-manage/${encodeURIComponent(id)}` })
}

// 切换标签页时只重载区块数据，不重复拉取 agent
watch(() => route.params.section, () => { loadSectionData() })

onMounted(load)
</script>

<template>
  <div class="sec-container">
    <!-- ===== 顶部：返回 + 标签页 ===== -->
    <div class="sec-topbar">
      <button type="button" class="sec-back" @click="goBack">
        <ArrowLeft :size="15" /> 返回档案
      </button>
      <div class="sec-tabbar">
        <button
          v-for="t in TABS"
          :key="t.key"
          type="button"
          class="sec-tab"
          :class="{ active: section === t.key }"
          :aria-label="t.title"
          :title="t.title"
          @click="switchSection(t.key)"
        >
          <component :is="t.icon" :size="15" />
        </button>
      </div>
      <div class="sec-active-title">
        <component :is="activeTab.icon" :size="16" class="sec-active-icon" />
        <span>{{ activeTab.title }}</span>
        <span class="sec-active-sub">{{ activeTab.subtitle }}</span>
      </div>
    </div>

    <div v-if="loading" class="sec-loading"><a-spin tip="加载中…" /></div>

    <div v-else class="sec-body">
      <!-- ===== 左侧：智能体简明信息（只读） ===== -->
      <aside class="sec-aside">
        <div class="sec-aside-avatar">
          <img :src="avatarUrl" :alt="`${agent?.name || ''}头像`" />
        </div>
        <div class="sec-aside-name">{{ agent?.name || '智能体' }}</div>
        <span class="sec-aside-status" :class="`s-${statusColor}`">
          <span class="s-dot" /><span>{{ statusText }}</span>
        </span>
        <p class="sec-aside-desc">{{ agent?.description || officer?.description || '暂无介绍' }}</p>
      </aside>

      <!-- ===== 右侧：当前区块内容 ===== -->
      <div ref="contentRef" class="sec-content">
        <!-- 灵魂 -->
        <div v-if="section === 'soul'" class="sec-block">
          <p class="sec-desc">{{ activeTab.subtitle }}</p>
          <div v-if="agent?.system_prompt" class="sec-prompt">
            <pre class="sec-pre">{{ agent.system_prompt }}</pre>
          </div>
          <a-empty v-else description="该智能体尚未配置系统提示词" />
        </div>

        <!-- 技能：装备技能控制台（悟帆风格） -->
        <div v-else-if="section === 'skills'" class="sec-block sec-skills">
          <div class="sk-head">
            <div class="sk-head-title">
              <span class="sk-head-icon"><BookOpen :size="18" /></span>
              <div class="sk-head-text">
                <div class="sk-title-row">
                  <h2>装备技能</h2>
                  <button type="button" class="sk-help" aria-label="什么是技能？">
                    <CircleHelp :size="13" /><span>什么是技能？</span>
                  </button>
                </div>
                <p>为AI员工装备可复用的方法论和专业流程</p>
              </div>
            </div>
            <label class="sk-search">
              <Search :size="15" />
              <input v-model="skillSearch" placeholder="搜索技能…" />
            </label>
          </div>

          <div class="sk-filter" role="group" aria-label="按装备状态筛选">
            <button type="button" :class="{ active: skillFilter === 'all' }" @click="skillFilter = 'all'">全部</button>
            <button type="button" :class="{ active: skillFilter === 'enabled' }" @click="skillFilter = 'enabled'">开启</button>
            <button type="button" :class="{ active: skillFilter === 'disabled' }" @click="skillFilter = 'disabled'">未开启</button>
          </div>

          <div v-if="skillsLoading" class="sk-loading"><a-spin /></div>
          <template v-else>
            <section class="sk-section">
              <div class="sk-section-title"><h3>空间资产</h3><span>{{ spaceSkills.length }}</span></div>
              <div v-if="spaceSkills.length" class="sk-grid">
                <article v-for="s in spaceSkills" :key="s.slug" class="sk-card" :class="{ off: s.enabled === false }">
                  <div class="sk-card-top">
                    <span class="sk-card-icon"><WandSparkles :size="18" /></span>
                    <span class="sk-card-ctrl">
                      <button type="button" class="sk-switch" :class="{ on: s.enabled !== false }" :disabled="!canManageSkill(s) || isSkillToggling(s.slug)" :aria-label="(s.enabled === false ? '启用' : '禁用') + ' ' + (s.name || s.slug)" @click="toggleSkill(s)">
                        <span class="sk-switch-track"><span></span></span>
                      </button>
                    </span>
                  </div>
                  <div class="sk-card-body">
                    <div class="sk-card-title-row"><h4>{{ s.name || s.slug }}</h4></div>
                    <p>{{ s.description || '暂无描述' }}</p>
                    <div class="sk-card-meta">{{ s.slug }}</div>
                  </div>
                </article>
              </div>
              <a-empty v-else :description="skillSearch || skillFilter !== 'all' ? '没有匹配的技能' : '暂无空间技能'" />
            </section>

            <section class="sk-section is-divided">
              <div class="sk-section-title"><h3>天赋资产</h3><span>{{ innateSkills.length }}</span></div>
              <div v-if="innateSkills.length" class="sk-grid">
                <article v-for="s in innateSkills" :key="s.slug" class="sk-card" :class="{ off: s.enabled === false }">
                  <div class="sk-card-top">
                    <span class="sk-card-icon"><WandSparkles :size="18" /></span>
                    <span class="sk-card-ctrl">
                      <button type="button" class="sk-switch" :class="{ on: s.enabled !== false }" :disabled="!canManageSkill(s) || isSkillToggling(s.slug)" :aria-label="(s.enabled === false ? '启用' : '禁用') + ' ' + (s.name || s.slug)" @click="toggleSkill(s)">
                        <span class="sk-switch-track"><span></span></span>
                      </button>
                    </span>
                  </div>
                  <div class="sk-card-body">
                    <div class="sk-card-title-row"><h4>{{ s.name || s.slug }}</h4></div>
                    <p>{{ s.description || '暂无描述' }}</p>
                    <div class="sk-card-meta">{{ s.slug }}</div>
                  </div>
                </article>
              </div>
              <a-empty v-else :description="skillSearch || skillFilter !== 'all' ? '没有匹配的技能' : '暂无天赋技能'" />
            </section>
          </template>
        </div>

        <!-- 连接器与工具：装备控制台（悟帆风格） -->
        <div v-else-if="section === 'connectors'" class="sec-block sec-connectors">
          <div class="ct-head">
            <div class="ct-head-title">
              <span class="ct-head-icon"><Cable :size="18" /></span>
              <div class="ct-head-text">
                <div class="ct-title-row">
                  <h2>装备连接器 &amp; 工具</h2>
                  <button type="button" class="ct-help" aria-label="什么是连接器与工具？">
                    <CircleHelp :size="13" /><span>什么是连接器与工具？</span>
                  </button>
                </div>
                <p>为 AI 员工装备连接外部系统的工具、MCP，以及用于数据处理与复杂编排的工作流</p>
              </div>
            </div>
            <label class="ct-search">
              <Search :size="15" />
              <input v-model="connectorSearch" placeholder="搜索连接器、工具包或工具…" />
            </label>
          </div>

          <div class="ct-filter" role="group" aria-label="按装备状态筛选">
            <button type="button" :class="{ active: connectorFilter === 'all' }" @click="connectorFilter = 'all'">全部</button>
            <button type="button" :class="{ active: connectorFilter === 'on' }" @click="connectorFilter = 'on'" title="含开启与按需">开启</button>
            <button type="button" :class="{ active: connectorFilter === 'off' }" @click="connectorFilter = 'off'">未开启</button>
          </div>

          <template v-if="mcpOptions.length || toolOptions.length">
            <!-- 空间资产：MCP 连接器 -->
            <section class="ct-section">
              <div class="ct-section-head">
                <div class="ct-section-title"><h3>空间资产</h3><span>{{ mcpOptions.length }}</span></div>
                <div class="ct-group-ctrl">
                  <button type="button" :class="{ on: groupMode('mcps') === 'none' }" :disabled="!canManageAgent" @click="setGroupMode('mcps', 'none')">全部关闭</button>
                  <button type="button" :class="{ on: groupMode('mcps') === 'custom' }" :disabled="!canManageAgent" @click="setGroupMode('mcps', 'custom')">自由配置</button>
                  <button type="button" :class="{ on: groupMode('mcps') === 'all' }" :disabled="!canManageAgent" @click="setGroupMode('mcps', 'all')">全部开启</button>
                </div>
              </div>
              <div class="ct-progress">
                <div class="ct-progress-bar"><span :style="{ width: percent(mcpEnabledCount, mcpOptions.length) }"></span></div>
                <span class="ct-progress-text">{{ mcpEnabledCount }}/{{ mcpOptions.length }} 已开启</span>
              </div>
              <div v-if="mcpCards.length" class="ct-grid">
                <article v-for="c in mcpCards" :key="c.key" class="ct-card" :class="{ off: !isResourceOn('mcps', c.key) }">
                  <div class="ct-card-top">
                    <span class="ct-card-badge">{{ c.badge }}</span>
                    <button type="button" class="ct-switch" :class="{ on: isResourceOn('mcps', c.key) }" :disabled="!canManageAgent || savingResource.includes(c.key)" :aria-label="(isResourceOn('mcps', c.key) ? '关闭' : '开启') + ' ' + (c.name || c.key)" @click="toggleResource('mcps', c.key)">
                      <span class="ct-switch-track"><span></span></span>
                    </button>
                  </div>
                  <div class="ct-card-body">
                    <div class="ct-card-title-row"><h4>{{ c.name || c.key }}</h4></div>
                    <p>{{ c.description || '暂无描述' }}</p>
                    <div class="ct-card-meta">{{ c.meta }}</div>
                  </div>
                </article>
              </div>
              <a-empty v-else :description="connectorSearch || connectorFilter !== 'all' ? '没有匹配的连接器' : '暂无可装备的 MCP 连接器'" />
            </section>

            <!-- 天赋资产：平台内置工具 -->
            <section class="ct-section is-divided">
              <div class="ct-section-head">
                <div class="ct-section-title"><h3>天赋资产</h3><span>{{ toolOptions.length }}</span></div>
                <div class="ct-group-ctrl">
                  <button type="button" :class="{ on: groupMode('tools') === 'none' }" :disabled="!canManageAgent" @click="setGroupMode('tools', 'none')">全部关闭</button>
                  <button type="button" :class="{ on: groupMode('tools') === 'custom' }" :disabled="!canManageAgent" @click="setGroupMode('tools', 'custom')">自由配置</button>
                  <button type="button" :class="{ on: groupMode('tools') === 'all' }" :disabled="!canManageAgent" @click="setGroupMode('tools', 'all')">全部开启</button>
                </div>
              </div>
              <div class="ct-progress">
                <div class="ct-progress-bar"><span :style="{ width: percent(toolEnabledCount, toolOptions.length) }"></span></div>
                <span class="ct-progress-text">{{ toolEnabledCount }}/{{ toolOptions.length }} 已开启</span>
              </div>
              <div v-if="toolCards.length" class="ct-grid">
                <article v-for="c in toolCards" :key="c.key" class="ct-card" :class="{ off: !isResourceOn('tools', c.key) }">
                  <div class="ct-card-top">
                    <span class="ct-card-badge soft">{{ c.badge }}</span>
                    <button type="button" class="ct-switch" :class="{ on: isResourceOn('tools', c.key) }" :disabled="!canManageAgent || savingResource.includes(c.key)" :aria-label="(isResourceOn('tools', c.key) ? '关闭' : '开启') + ' ' + (c.name || c.key)" @click="toggleResource('tools', c.key)">
                      <span class="ct-switch-track"><span></span></span>
                    </button>
                  </div>
                  <div class="ct-card-body">
                    <div class="ct-card-title-row"><h4>{{ c.name || c.key }}</h4></div>
                    <p>{{ c.description || '暂无描述' }}</p>
                    <div class="ct-card-meta">{{ c.meta }}</div>
                  </div>
                </article>
              </div>
              <a-empty v-else :description="connectorSearch || connectorFilter !== 'all' ? '没有匹配的工具' : '暂无可装备的内置工具'" />
            </section>
          </template>
          <a-empty v-else description="该智能体暂无可装备的连接器与工具" />
        </div>

        <!-- 协助伙伴 -->
        <div v-else-if="section === 'partners'" class="sec-block">
          <div class="ct-head">
            <div class="ct-head-title">
              <span class="ct-head-icon"><Users :size="18" /></span>
              <div class="ct-head-text">
                <div class="ct-title-row">
                  <h2>装备伙伴</h2>
                  <button type="button" class="ct-help" @click="showPartnerHelp">
                    <CircleHelp :size="14" /><span>什么是协助伙伴？</span>
                  </button>
                </div>
                <p>选择可与当前 AI 员工协作的同事与专业伙伴</p>
              </div>
            </div>
            <label class="ct-search">
              <Search :size="15" />
              <input v-model="partnerSearch" placeholder="搜索协助伙伴…" />
            </label>
          </div>

          <div class="ct-filter" role="group" aria-label="按装备状态筛选">
            <button type="button" :class="{ active: partnerFilter === 'all' }" @click="partnerFilter = 'all'">全部</button>
            <button type="button" :class="{ active: partnerFilter === 'on' }" @click="partnerFilter = 'on'" title="含开启与按需">开启</button>
            <button type="button" :class="{ active: partnerFilter === 'off' }" @click="partnerFilter = 'off'">未开启</button>
          </div>

          <div v-if="partnerAgentId" class="sec-connectors">
            <!-- 空间资产：已装备 -->
            <section class="ct-section">
              <div class="ct-section-head">
                <div class="ct-section-title"><h3>空间资产</h3><span>{{ equippedView.length }}</span></div>
              </div>
              <div v-if="equippedView.length" class="ct-grid">
                <article v-for="p in equippedView" :key="p.id" class="ct-card">
                  <div class="ct-card-top">
                    <span class="ct-card-avatar"><img v-if="p.icon" :src="p.icon" :alt="p.name" /><span v-else>{{ (p.name || '?').slice(0, 1) }}</span></span>
                    <button type="button" class="ct-switch on" :disabled="!canManageAgent || savingPartner.includes(p.id)" :aria-label="'卸载 ' + (p.name || p.slug)" @click="togglePartner(p, false)">
                      <span class="ct-switch-track"><span></span></span>
                    </button>
                  </div>
                  <div class="ct-card-body">
                    <div class="ct-card-title-row"><h4>{{ p.name || p.slug }}</h4></div>
                    <p>{{ p.description || '暂无描述' }}</p>
                    <div class="ct-card-meta">已装备</div>
                  </div>
                </article>
              </div>
              <a-empty v-else :description="partnerSearch || partnerFilter !== 'all' ? '没有匹配的已装备伙伴' : '暂无已装备的协助伙伴'" />
            </section>

            <!-- 天赋资产：可装备候选 -->
            <section class="ct-section is-divided">
              <div class="ct-section-head">
                <div class="ct-section-title"><h3>天赋资产</h3><span>{{ availableView.length }}</span></div>
              </div>
              <div v-if="availableView.length" class="ct-grid">
                <article v-for="p in availableView" :key="p.id" class="ct-card off">
                  <div class="ct-card-top">
                    <span class="ct-card-avatar"><img v-if="p.icon" :src="p.icon" :alt="p.name" /><span v-else>{{ (p.name || '?').slice(0, 1) }}</span></span>
                    <button type="button" class="ct-switch" :disabled="!canManageAgent || savingPartner.includes(p.id)" :aria-label="'装备 ' + (p.name || p.slug)" @click="togglePartner(p, true)">
                      <span class="ct-switch-track"><span></span></span>
                    </button>
                  </div>
                  <div class="ct-card-body">
                    <div class="ct-card-title-row"><h4>{{ p.name || p.slug }}</h4></div>
                    <p>{{ p.description || '暂无描述' }}</p>
                    <div class="ct-card-meta">可装备</div>
                  </div>
                </article>
              </div>
              <a-empty v-else :description="partnerSearch || partnerFilter !== 'all' ? '没有匹配的可装备伙伴' : '暂无可装备的协助伙伴'" />
            </section>
          </div>
          <a-empty v-else description="无法识别当前智能体" />
        </div>

        <!-- 记忆 -->
        <div v-else-if="section === 'memory'" class="sec-block">
          <div v-if="memoryMissing && !memoryEditing" class="mem-empty">
            <Brain :size="30" />
            <p class="mem-empty-text">当前用户工作区暂无 MEMORY.md（智能体还没有关于你的记忆）</p>
            <button class="mem-edit-btn" @click="startEditMemory"><PenLine :size="12" /> 新建记忆</button>
          </div>
          <template v-else>
            <div class="mem-toolbar">
              <div class="mem-title-row">
                <Brain :size="18" class="mem-title-icon" />
                <span class="mem-title">记忆管理</span>
                <span class="mem-count">{{ memoryEntries.length }} 条记忆</span>
                <div class="mem-spacer" />
                <label class="mem-search">
                  <Search :size="15" />
                  <input v-model="memorySearch" placeholder="搜索记忆..." />
                </label>
                <template v-if="memoryEditing">
                  <button class="mem-edit-btn" :disabled="savingMemory" @click="saveMemory">保存</button>
                  <button class="mem-edit-btn mem-ghost" :disabled="savingMemory" @click="cancelEditMemory">取消</button>
                </template>
                <button v-else class="mem-edit-btn" @click="startEditMemory"><PenLine :size="12" /> 编辑</button>
              </div>
              <div v-if="!memoryEditing" class="mem-filter" role="group" aria-label="按记忆类型筛选">
                <button :class="{ 'is-active': memoryTypeFilter === 'all' }" @click="memoryTypeFilter = 'all'">全部</button>
                <button
                  v-for="t in memoryTypes"
                  :key="t"
                  :class="{ 'is-active': memoryTypeFilter === t }"
                  @click="memoryTypeFilter = t"
                >{{ t }}</button>
              </div>
            </div>

            <div v-if="memoryEditing" class="mem-editor">
              <textarea
                v-model="memoryDraft"
                class="mem-textarea"
                placeholder="用 Markdown 记录智能体需要记住的关于你的信息（以 ## 标题 区分不同类别的记忆，例如 ## fact / ## context / ## procedure）…"
              ></textarea>
            </div>

            <div v-else class="mem-list">
              <div v-if="memoryFiltered.length" class="mem-entries">
                <div v-for="(e, i) in memoryFiltered" :key="i" class="mem-entry">
                  <div v-if="e.type !== '未分类'" class="mem-entry-type">{{ e.type }}</div>
                  <pre class="mem-entry-body">{{ e.content.trim() }}</pre>
                </div>
              </div>
              <div v-else class="mem-empty-list">暂无记忆条目</div>
            </div>
          </template>
        </div>

        <a-empty v-else description="未知区块" />
      </div>
    </div>
  </div>
</template>

<style lang="less" scoped>
.sec-container {
  padding: 24px var(--page-padding) 48px;
  max-width: 1200px;
  margin: 0 auto;
}

// ============ 顶部栏 ============
.sec-topbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--gray-150);
  margin-bottom: 20px;
}
.sec-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--gray-600);
  font-size: 13px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 8px;
  flex-shrink: 0;
  &:hover { color: var(--main-700); background: var(--gray-50); }
}
.sec-tabbar {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.sec-tab {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 1px solid var(--gray-200);
  background: #f8fafc;
  color: var(--gray-400);
  cursor: pointer;
  transition: background 0.18s, border-color 0.18s, color 0.18s;
  &:hover {
    background: var(--gray-100);
    color: var(--gray-600);
    border-color: var(--gray-300);
  }
  &.active {
    background: #eef2ff;
    border-color: var(--main-300);
    color: var(--main-700);
    position: relative;
    &::after {
      content: '';
      position: absolute;
      left: 18%;
      right: 18%;
      bottom: -1px;
      height: 2px;
      border-radius: 1px;
      background: var(--main-700);
    }
  }
}
.sec-active-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 700;
  color: #1a365d;
  min-width: 0;
  overflow: hidden;
}
.sec-active-icon { color: var(--main-700); flex-shrink: 0; }
.sec-active-sub {
  font-size: 12px;
  font-weight: 400;
  color: var(--gray-500);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sec-loading { display: flex; justify-content: center; padding: 80px 0; }

// ============ 主体两栏 ============
.sec-body {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 24px;
  align-items: start;
}

// ============ 左侧简明信息 ============
.sec-aside {
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid var(--gray-150);
  box-shadow: 0 2px 10px rgba(16,30,54,.05);
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 10px;
  position: sticky;
  top: 16px;
}
.sec-aside-avatar {
  width: 72px;
  height: 72px;
  border-radius: 18px;
  overflow: hidden;
  background: transparent;
  flex-shrink: 0;
  img { display: block; width: 100%; height: 100%; object-fit: cover; }
}
.sec-aside-name {
  font-size: 16px;
  font-weight: 700;
  color: #1a365d;
}
.sec-aside-status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid transparent;
  &.s-green { background: #f0fdf4; color: #15803d; border-color: #bbf7d0; }
  &.s-red { background: #fef2f2; color: #b91c1c; border-color: #fecaca; }
  &.s-orange { background: #fff7ed; color: #c2410c; border-color: #fed7aa; }
}
.s-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: currentColor;
}
.sec-aside-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--gray-500);
  line-height: 1.6;
  text-align: left;
}

// ============ 右侧内容 ============
.sec-content { min-height: 240px; max-height: calc(100vh - 150px); overflow-y: auto; }

.sec-block {
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid var(--gray-150);
  box-shadow: 0 2px 10px rgba(16,30,54,.05);
  padding: 20px 24px;
}
.sec-desc {
  margin: 0 0 16px;
  font-size: 12px;
  color: var(--gray-500);
}

.sec-pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.7;
  color: #334155;
  font-family: inherit;
}

// ============ 技能：装备技能控制台 ============
.sec-skills { display: flex; flex-direction: column; gap: 16px; }
.sk-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.sk-head-title { display: flex; gap: 12px; align-items: flex-start; }
.sk-head-icon {
  width: 36px; height: 36px; border-radius: 10px;
  background: var(--main-50, #eef2ff); color: var(--main-700);
  display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.sk-head-text { min-width: 0; }
.sk-title-row { display: flex; align-items: center; gap: 8px; }
.sk-title-row h2 { margin: 0; font-size: 17px; font-weight: 700; color: #1a365d; }
.sk-help {
  display: inline-flex; align-items: center; gap: 3px;
  font-size: 12px; color: var(--gray-500); background: none; border: none; cursor: pointer;
  padding: 2px 4px; border-radius: 6px;
  &:hover { color: var(--main-700); background: var(--gray-50); }
}
.sk-head-text p { margin: 2px 0 0; font-size: 12px; color: var(--gray-500); }
.sk-search {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--gray-50, #f8fafc); border: 1px solid var(--gray-200);
  border-radius: 999px; padding: 6px 12px; color: var(--gray-500); flex-shrink: 0;
  input { border: none; outline: none; background: transparent; font-size: 13px; color: var(--gray-800); width: 160px; }
}
.sk-filter {
  display: inline-flex; gap: 4px; align-self: flex-start;
  background: var(--gray-50, #f8fafc); border: 1px solid var(--gray-200); border-radius: 10px; padding: 3px;
  button {
    font-size: 12px; padding: 5px 14px; border-radius: 8px; border: none; background: transparent;
    color: var(--gray-500); cursor: pointer; transition: .15s;
    &:hover { color: var(--gray-700); }
    &.active { background: #fff; color: var(--main-700); font-weight: 600; box-shadow: 0 1px 3px rgba(16,30,54,.08); }
  }
}
.sk-loading { display: flex; justify-content: center; padding: 48px 0; }
.sk-section {
  display: flex; flex-direction: column; gap: 10px;
  &.is-divided { margin-top: 4px; padding-top: 16px; border-top: 1px dashed var(--gray-150); }
}
.sk-section-title { display: flex; align-items: center; gap: 6px; }
.sk-section-title h3 { margin: 0; font-size: 13px; font-weight: 700; color: var(--gray-700); }
.sk-section-title span {
  font-size: 11px; font-weight: 600; color: var(--gray-500);
  background: var(--gray-100, #f1f5f9); border-radius: 999px; padding: 1px 8px;
}
.sk-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
.sk-card {
  border: 1px solid var(--gray-150); border-radius: 12px; padding: 14px; background: #fff;
  display: flex; flex-direction: column; gap: 10px;
  transition: border-color .18s, box-shadow .18s;
  &:hover { border-color: var(--main-200, #c7d2fe); box-shadow: 0 2px 8px rgba(16,30,54,.06); }
  &.off { opacity: .82; }
}
.sk-card-top { display: flex; align-items: center; justify-content: space-between; }
.sk-card-icon {
  width: 36px; height: 36px; border-radius: 10px;
  background: var(--gray-100, #f4f4f5); color: #18181b;
  display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.sk-switch {
  width: 40px; height: 22px; border-radius: 999px; border: none; cursor: pointer; padding: 0;
  background: var(--gray-300, #cbd5e1); position: relative; transition: background .2s; flex-shrink: 0;
  &:disabled { opacity: .5; cursor: not-allowed; }
  .sk-switch-track { position: absolute; inset: 0; }
  .sk-switch-track > span {
    position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; border-radius: 50%;
    background: #fff; box-shadow: 0 1px 2px rgba(0,0,0,.25); transition: transform .2s;
  }
  &.on { background: var(--main-500, #6366f1); }
  &.on .sk-switch-track > span { transform: translateX(18px); }
}
.sk-card-body { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.sk-card-title-row h4 { margin: 0; font-size: 14px; font-weight: 600; color: #1a365d; }
.sk-card-body p {
  margin: 0; font-size: 12px; color: var(--gray-500); line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.sk-card-meta { font-size: 11px; color: var(--gray-400); }

.sec-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.sec-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: #f8fafc;
  border: 1px solid var(--gray-150);
  border-radius: 12px;
}
.sec-item-icon {
  width: 36px; height: 36px;
  border-radius: 10px;
  background: #eef2ff;
  color: var(--main-700);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.sec-item-avatar {
  width: 36px; height: 36px;
  border-radius: 10px;
  overflow: hidden;
  background: var(--main-100);
  color: var(--main-700);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
  img { width: 100%; height: 100%; object-fit: cover; }
}
.sec-item-body { flex: 1; min-width: 0; }
.sec-item-title { font-size: 14px; font-weight: 600; color: #1a365d; }
.sec-item-sub { font-size: 12px; color: var(--gray-500); margin-top: 2px; }
.sec-item-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 999px;
  flex-shrink: 0;
  &.on { background: #dcfce7; color: #15803d; }
  &.off { background: #f1f5f9; color: #94a3b8; }
}
// ============ 记忆 ============
.mem-empty {
  display: flex; flex-direction: column; align-items: center; gap: 14px;
  padding: 48px 0; color: var(--gray-400); text-align: center;
  .mem-empty-text { font-size: 13px; max-width: 360px; }
}
.mem-toolbar {
  position: sticky; top: 0; z-index: 10;
  background: var(--color-bg-elevated, var(--gray-0, #fff));
  padding: 4px 0 14px; margin-bottom: 14px;
  display: flex; flex-direction: column; gap: 14px;
  border-bottom: 1px solid var(--gray-150, #eef0f0);
}
.mem-title-row {
  display: flex; align-items: center; gap: 10px;
  .mem-title-icon { color: var(--gray-500, #979999); }
  .mem-title { font-size: 16px; font-weight: 700; color: var(--gray-900, #1e1f1f); }
  .mem-count {
    font-size: 10px; color: var(--gray-500, #979999);
    background: var(--gray-100, #eff2f2); padding: 3px 8px; border-radius: 999px;
  }
  .mem-spacer { flex: 1 1 0; }
}
.mem-search {
  display: inline-flex; align-items: center; gap: 6px;
  width: 280px; max-width: 32vw;
  background: var(--gray-50, #f5f7f7);
  border: 1px solid var(--gray-200, #e4e6e6);
  border-radius: 10px; padding: 0 10px; height: 36px;
  color: var(--gray-400, #bdbfbf);
  input {
    border: none; outline: none; background: transparent;
    flex: 1; font-size: 13px; color: var(--gray-800, #323333); min-width: 0;
  }
}
.mem-edit-btn {
  display: inline-flex; align-items: center; gap: 5px;
  height: 36px; padding: 0 14px; border-radius: 11px;
  background: var(--gray-100, #eff2f2);
  border: 1px solid var(--gray-200, #e4e6e6);
  cursor: pointer; color: var(--gray-600, #697070);
  font-size: 12px; font-weight: 500; flex-shrink: 0;
  &:hover { background: var(--gray-150, #eef0f0); }
  &:disabled { opacity: 0.6; cursor: not-allowed; }
  &.mem-ghost { background: transparent; }
}
.mem-filter {
  align-self: flex-start; display: inline-flex; gap: 6px; flex-wrap: wrap;
  button {
    height: 30px; padding: 0 14px; border-radius: 8px;
    background: var(--gray-50, #f5f7f7);
    border: 1px solid var(--gray-200, #e4e6e6);
    cursor: pointer; color: var(--gray-600, #697070); font-size: 12px;
    &.is-active {
      background: var(--brand, #3b82f6); border-color: var(--brand, #3b82f6); color: #fff;
    }
    &:hover:not(.is-active) { background: var(--gray-100, #eff2f2); }
  }
}
.mem-editor { margin-top: 4px; }
.mem-textarea {
  width: 100%; min-height: 320px; resize: vertical;
  border: 1px solid var(--gray-200, #e4e6e6); border-radius: 12px;
  padding: 14px; font-size: 13px; line-height: 1.6;
  font-family: var(--font-mono, monospace);
  color: var(--gray-800, #323333); background: var(--gray-50, #f5f7f7);
  outline: none;
  &:focus { border-color: var(--brand, #3b82f6); }
}
.mem-list { display: flex; flex-direction: column; gap: 10px; }
.mem-entries { display: flex; flex-direction: column; gap: 10px; }
.mem-entry {
  border: 1px solid var(--gray-150, #eef0f0); border-radius: 12px;
  padding: 14px 16px; background: var(--gray-50, #f5f7f7);
  .mem-entry-type {
    display: inline-block; font-size: 11px; font-weight: 600;
    color: var(--brand, #3b82f6);
    background: var(--brand-50, #eff4ff); padding: 2px 8px; border-radius: 6px;
    margin-bottom: 8px;
  }
  .mem-entry-body {
    margin: 0; white-space: pre-wrap; word-break: break-word;
    font-size: 13px; line-height: 1.6; color: var(--gray-700, #4c4d4d);
    font-family: inherit;
  }
}
.mem-empty-list {
  display: flex; align-items: center; justify-content: center;
  padding: 40px; color: var(--gray-400, #bdbfbf); font-size: 12px;
}

// ============ 连接器与工具：装备控制台 ============
.sec-connectors { display: flex; flex-direction: column; gap: 16px; }
.ct-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.ct-head-title { display: flex; gap: 12px; align-items: flex-start; }
.ct-head-icon {
  width: 36px; height: 36px; border-radius: 10px;
  background: var(--main-50, #eef2ff); color: var(--main-700);
  display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.ct-head-text { min-width: 0; }
.ct-title-row { display: flex; align-items: center; gap: 8px; }
.ct-title-row h2 { margin: 0; font-size: 17px; font-weight: 700; color: #1a365d; }
.ct-help {
  display: inline-flex; align-items: center; gap: 3px;
  font-size: 12px; color: var(--gray-500); background: none; border: none; cursor: pointer;
  padding: 2px 4px; border-radius: 6px;
  &:hover { color: var(--main-700); background: var(--gray-50); }
}
.ct-head-text p { margin: 2px 0 0; font-size: 12px; color: var(--gray-500); }
.ct-search {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--gray-50, #f8fafc); border: 1px solid var(--gray-200);
  border-radius: 999px; padding: 6px 12px; color: var(--gray-500); flex-shrink: 0;
  input { border: none; outline: none; background: transparent; font-size: 13px; color: var(--gray-800); width: 180px; }
}
.ct-filter {
  display: inline-flex; gap: 4px; align-self: flex-start;
  background: var(--gray-50, #f8fafc); border: 1px solid var(--gray-200); border-radius: 10px; padding: 3px;
  button {
    font-size: 12px; padding: 5px 14px; border-radius: 8px; border: none; background: transparent;
    color: var(--gray-500); cursor: pointer; transition: .15s;
    &:hover { color: var(--gray-700); }
    &.active { background: #fff; color: var(--main-700); font-weight: 600; box-shadow: 0 1px 3px rgba(16,30,54,.08); }
  }
}
.ct-section {
  display: flex; flex-direction: column; gap: 10px;
  &.is-divided { margin-top: 4px; padding-top: 16px; border-top: 1px dashed var(--gray-150); }
}
.ct-section-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.ct-section-title { display: flex; align-items: center; gap: 6px; }
.ct-section-title h3 { margin: 0; font-size: 13px; font-weight: 700; color: var(--gray-700); }
.ct-section-title span {
  font-size: 11px; font-weight: 600; color: var(--gray-500);
  background: var(--gray-100, #f1f5f9); border-radius: 999px; padding: 1px 8px;
}
.ct-group-ctrl { display: inline-flex; gap: 6px; }
.ct-group-ctrl button {
  font-size: 12px; padding: 4px 12px; border-radius: 8px;
  border: 1px solid var(--gray-200); background: #fff; color: var(--gray-500); cursor: pointer;
  transition: .15s;
  &:hover:not(:disabled) { color: var(--main-700); border-color: var(--main-300); }
  &:disabled { opacity: .5; cursor: not-allowed; }
  &.on { background: #eef2ff; color: var(--main-700); border-color: var(--main-300); font-weight: 600; }
}
.ct-progress { display: flex; align-items: center; gap: 10px; }
.ct-progress-bar {
  flex: 1; height: 6px; border-radius: 999px; background: var(--gray-100, #f1f5f9); overflow: hidden;
  span { display: block; height: 100%; border-radius: 999px; background: var(--main-500, #6366f1); transition: width .25s; }
}
.ct-progress-text { font-size: 11px; color: var(--gray-500); white-space: nowrap; }
.ct-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
.ct-card {
  border: 1px solid var(--gray-150); border-radius: 12px; padding: 14px; background: #fff;
  display: flex; flex-direction: column; gap: 10px;
  transition: border-color .18s, box-shadow .18s;
  &:hover { border-color: var(--main-200, #c7d2fe); box-shadow: 0 2px 8px rgba(16,30,54,.06); }
  &.off { opacity: .82; }
}
.ct-card-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.ct-card-avatar {
  width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0; overflow: hidden;
  background: var(--gray-100, #f1f5f9); color: var(--gray-500);
  display: inline-flex; align-items: center; justify-content: center; font-weight: 600; font-size: 14px;
  img { width: 100%; height: 100%; object-fit: cover; display: block; }
}
.ct-card-badge {
  font-size: 10px; font-weight: 700; letter-spacing: .02em;
  color: var(--main-700); background: #eef2ff; border-radius: 6px; padding: 2px 7px;
  &.soft { color: #475569; background: var(--gray-100, #f1f5f9); }
}
.ct-switch {
  width: 40px; height: 22px; border-radius: 999px; border: none; cursor: pointer; padding: 0;
  background: var(--gray-300, #cbd5e1); position: relative; transition: background .2s; flex-shrink: 0;
  &:disabled { opacity: .5; cursor: not-allowed; }
  .ct-switch-track { position: absolute; inset: 0; }
  .ct-switch-track > span {
    position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; border-radius: 50%;
    background: #fff; box-shadow: 0 1px 2px rgba(0,0,0,.25); transition: transform .2s;
  }
  &.on { background: var(--main-500, #6366f1); }
  &.on .ct-switch-track > span { transform: translateX(18px); }
}
.ct-card-body { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.ct-card-title-row h4 { margin: 0; font-size: 14px; font-weight: 600; color: #1a365d; }
.ct-card-body p {
  margin: 0; font-size: 12px; color: var(--gray-500); line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.ct-card-meta { font-size: 11px; color: var(--gray-400); }

// ============ 响应式 ============
@media (max-width: 900px) {
  .sec-body { grid-template-columns: 1fr; }
  .sec-aside { position: static; flex-direction: row; text-align: left; align-items: center; }
  .sec-aside-desc { margin-top: 0; }
}
@media (max-width: 640px) {
  .sec-active-sub { display: none; }
  .sec-aside { flex-direction: column; text-align: center; }
}
</style>
