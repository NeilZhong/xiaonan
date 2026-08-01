<script setup>
/**
 * 通用智能体档案页
 *
 * 支持所有智能体（含数字警员和普通智能体）的档案展示。
 * - 数字警员：展示完整档案（能力矩阵 / 工作统计 / 技能列表 / SOP / 成长轨迹）
 * - 普通智能体：展示基本信息（名称 / 描述 / 后端类型 / 共享权限），缺失字段优雅降级
 *
 * 编辑统一使用 AgentEditModal（Yuxi 原版编辑界面）。
 */
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { Share2 } from 'lucide-vue-next'

import { agentApi } from '@/apis/agent_api'
import { policeAgentApi } from '@/apis/police_api'
import AgentEditModal from '@/components/model-management/AgentEditModal.vue'
import ShareConfigForm from '@/components/ShareConfigForm.vue'
import { isBuiltinAgent, useAgentStore } from '@/stores/agent'
import FallbackAvatar from '@/components/common/FallbackAvatar.vue'
import { generatePixelAvatar } from '@/utils/pixelAvatar'

const route = useRoute()
const router = useRouter()
const agentStore = useAgentStore()

/** 基础智能体数据（来自 agents 表） */
const agent = ref(null)
/** 数字警员扩展数据（来自 police_agents 表，可能为 null） */
const officer = ref(null)
const loading = ref(false)

// AgentEditModal 引用
const agentEditModalRef = ref(null)
/** AgentEditModal 需要的后端选项 */
const backendOptions = ref([])

// ── 分享弹窗 ──
const shareModalVisible = ref(false)
const shareSaving = ref(false)
const shareConfig = ref({ access_level: 'user', department_ids: [], user_uids: [] })
const shareConfigFormRef = ref(null)

// ============ 派生状态 ============

/** 是否为数字警员（有对应的 police_agent 记录） */
const isOfficer = computed(() => !!officer.value)

/** 智能体状态文字 */
const statusText = computed(() => {
  if (!agent.value) return '未知'
  if (isOfficer.value) {
    const s = officer.value?.status
    return { active: '在线', training: '训练中', offline: '离线' }[s] || '离线'
  }
  return agent.value.is_builtin ? '内置' : '正常'
})

const statusBadgeType = computed(() => {
  if (isOfficer.value) {
    const s = officer.value?.status
    return { active: 'success', training: 'processing', offline: 'default' }[s] || 'default'
  }
  return 'success'
})

/** 工作统计（仅数字警员） */
const statCards = computed(() => {
  const s = officer.value?.work_stats || {}
  return [
    { label: '完成任务', value: s.tasks_completed ?? 0 },
    { label: '处理案件', value: s.cases_handled ?? 0 },
    { label: '好评率', value: s.feedback_positive != null ? `${s.feedback_positive}%` : '—' },
  ]
})

/** 后端类型显示名 */
const backendLabel = computed(() => {
  const b = agent.value?.backend_id || 'ChatbotAgent'
  const map = { ChatbotAgent: '对话智能体', SubAgentBackend: '子智能体' }
  return map[b] || b
})

/** 默认头像 URL */
const defaultIconSrc = computed(() =>
  agent.value?.id ? generatePixelAvatar(agent.value.id) : ''
)

// ============ 运行记录颜色/文字 ============
function runColor(s) {
  return { queued: 'gray', running: 'blue', completed: 'green', failed: 'red', cancelled: 'gray' }[s] || 'gray'
}
function runText(s) {
  return { queued: '排队中', running: '运行中', completed: '已完成', failed: '失败', cancelled: '已取消' }[s] || s
}

// ============ 操作 ============

function goBack() {
  router.push({ name: 'agent-manage' })
}

function goChat() {
  const slug = agent.value?.slug || agent.value?.id
  if (slug) {
    router.push({ path: '/agent', query: { agent_id: slug } })
  } else {
    router.push('/agent')
  }
}

function openEdit() {
  // openEdit 内部按 yuxi slug 拉取详情，必须传 slug 而非 int 主键
  agentEditModalRef.value?.openEdit(agent.value?.slug || agent.value?.id)
}

async function onEdited() {
  await load()
}

async function handleDelete() {
  const name = agent.value?.name || '该智能体'
  const isOff = isOfficer.value
  Modal.confirm({
    title: `删除 ${name}`,
    content: isOff
      ? '删除后该数字警员及其关联的对话智能体也将一并移除，不可恢复。'
      : '删除后不可恢复，已绑定该智能体的历史对话仍保留原始绑定信息。',
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      try {
        if (isOff) {
          await policeAgentApi.delete(officer.value.id)
        } else {
          await agentApi.deleteAgent(agent.value.id)
        }
        message.success('已删除')
        router.push({ name: 'agent-manage' })
      } catch (e) {
        message.error('删除失败: ' + (e.message || e))
      }
    }
  })
}

// ── 分享操作 ──

function openShareModal() {
  // 初始化为当前共享状态（从 officer 或 agent 的 share_config 读取）
  const current = officer.value?.share_scope
    ? { access_level: officer.value.share_scope === 'global' ? 'global' : officer.value.share_scope === 'department' ? 'department' : 'user', department_ids: [], user_uids: [] }
    : { access_level: 'user', department_ids: [], user_uids: [] }
  shareConfig.value = current
  shareModalVisible.value = true
}

async function handleShare() {
  const validation = shareConfigFormRef.value?.validate?.()
  if (validation && !validation.valid) {
    message.error(validation.message)
    return
  }

  shareSaving.value = true
  try {
    const targetId = officer.value?.id || agent.value?.id
    if (!targetId) return

    await policeAgentApi.shareAgent(targetId, {
      scope: shareConfig.value.access_level,
      department_ids: shareConfig.value.department_ids,
      user_uids: shareConfig.value.user_uids,
      // TODO: 从用户 session 取真实 ID
      author_id: null,
    })

    message.success(
      shareConfig.value.access_level === 'global'
        ? '已提交全局共享申请，等待管理员审批'
        : '分享设置已更新'
    )
    shareModalVisible.value = false
    await load() // 刷新档案数据
  } catch (e) {
    message.error('分享失败: ' + (e.message || e))
  } finally {
    shareSaving.value = false
  }
}

// ============ 数据加载 ============

async function loadBackends() {
  try {
    const res = await agentApi.getAgentBackends()
    backendOptions.value = (res.backends || []).map((b) => ({
      label: b.name || b.backend_id,
      value: b.backend_id
    }))
  } catch (_) {
    // 非阻塞
  }
}

async function load() {
  loading.value = true
  try {
    const id = route.params.id
    // 路由参数可能是数字警员工号（如 DA-AE74CDAF）或 yuxi slug
    // 先尝试按工号查 police 档案，拿到 yuxi agent_id 后再加载 yuxi 详情
    const policeData = await policeAgentApi.getByBadgeNumber(id).catch(() => null)
    if (policeData?.agent_id) {
      // 数字警员路径：用 police 记录的 agent_id（yuxi 外键）加载 yuxi 详情
      officer.value = policeData
      const agentResp = await agentApi.getAgentDetail(policeData.agent_id)
      const agentObj = agentResp?.agent || agentResp
      agent.value = agentObj
    } else {
      // 兼容原有 yuxi 智能体路径（直接传 yuxi slug / id）
      const agentResp = await agentApi.getAgentDetail(id)
      const agentObj = agentResp?.agent || agentResp
      agent.value = agentObj
      const yuxiId = agentObj?.id
      if (yuxiId != null) {
        const pd = await policeAgentApi.getByYuxiId(yuxiId).catch(() => null)
        if (pd && (pd.agent_id === yuxiId || pd.id)) {
          officer.value = pd
        }
      }
    }
  } catch (e) {
    message.error('加载档案失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  loadBackends()
})
</script>

<template>
  <div class="agent-profile" v-if="agent">
    <!-- 返回 + 操作栏 -->
    <div class="profile-bar">
      <a-button type="text" @click="goBack">
        <span class="back-arrow">←</span> 返回列表
      </a-button>
      <div class="bar-actions">
        <a-button v-if="isOfficer" @click="$router.push('/police/cases')">编入专案组</a-button>
        <a-button
          v-if="agent.can_manage || isBuiltinAgent(agent)"
          @click="openEdit"
        >编辑</a-button>
        <a-popconfirm
          v-if="!isBuiltinAgent(agent)"
          title="确认删除？"
          :description="isOfficer ? '关联的对话智能体也将一并移除' : '删除后不可恢复'"
          ok-text="删除"
          cancel-text="取消"
          :ok-button-props="{ danger: true }"
          @confirm="handleDelete"
        >
          <a-button danger>删除</a-button>
        </a-popconfirm>
        <a-button
          v-if="!isBuiltinAgent(agent)"
          @click="openShareModal"
        >
          <Share2 :size="14" :stroke-width="2" /> 分享
        </a-button>
        <a-button type="primary" @click="goChat">发起对话</a-button>
      </div>
    </div>

    <!-- 头部档案卡 -->
    <div class="profile-head" :class="`theme-${officer?.color_theme || 'blue'}`">
      <div class="head-avatar" :class="`bg-${officer?.color_theme || 'blue'}`">
        <FallbackAvatar
          :src="agent.icon"
          :default-src="defaultIconSrc"
          :name="agent.name || agent.id"
          :seed="agent.id"
          kind="agent"
          :size="48"
          shape="rounded"
        />
      </div>
      <div class="head-main">
        <div class="head-line1">
          <h2>{{ agent.name }}</h2>
          <a-badge :status="statusBadgeType" :text="statusText" />
          <span v-if="isOfficer" class="officer-label">数字警员</span>
        </div>
        <div class="head-line2">
          <span class="tag-pill">{{ agent.slug || agent.id }}</span>
          <span v-if="isOfficer" class="tag-pill">工号 {{ officer.badge_number }}</span>
          <span v-if="isOfficer && officer.rank" class="tag-pill">{{ officer.rank }}</span>
          <span v-if="isOfficer && officer.department" class="tag-pill">{{ officer.department }}</span>
          <span class="tag-pill">{{ backendLabel }}</span>
        </div>
        <div class="head-specialty">
          <template v-if="isOfficer">{{ officer.specialty || officer.description || agent.description || '—' }}</template>
          <template v-else>{{ agent.description || '暂无描述' }}</template>
        </div>
      </div>
      <div v-if="isOfficer" class="head-exp">
        <div class="exp-num">Lv.{{ officer.experience_level || 1 }}</div>
        <div class="exp-label">经验等级</div>
      </div>
    </div>

    <a-row :gutter="16" class="profile-body">
      <!-- 左列 -->
      <a-col :xs="24" :lg="14">
        <!-- 能力矩阵：仅数字警员 -->
        <a-card v-if="isOfficer" class="block" title="能力矩阵">
          <div class="cap-matrix">
            <div v-for="cap in (officer.capabilities || [])" :key="cap" class="cap-item">
              <span class="cap-dot" />{{ cap }}
            </div>
            <a-empty v-if="!(officer.capabilities || []).length" description="暂无能力标签" />
          </div>
        </a-card>

        <!-- 技能列表：仅数字警员 -->
        <a-card v-if="isOfficer" class="block" title="技能列表">
          <a-tag v-for="s in (officer.skills || [])" :key="s" class="skill-tag">{{ s }}</a-tag>
          <div v-if="!(officer.skills || []).length" class="muted">暂未挂载技能</div>
        </a-card>

        <!-- 关联 SOP：仅数字警员 -->
        <a-card v-if="isOfficer" class="block" title="关联 SOP / 办案规程">
          <div v-for="sop in (officer.sops || [])" :key="sop.id" class="sop-item">
            <div class="sop-name">{{ sop.name }}</div>
            <div class="sop-desc">{{ sop.description || '—' }}</div>
          </div>
          <a-empty v-if="!(officer.sops || []).length" description="暂无关联 SOP" />
        </a-card>

        <!-- 基本信息：普通智能体展示 -->
        <a-card v-if="!isOfficer" class="block" title="基本信息">
          <div class="info-grid">
            <div class="info-row">
              <span class="info-label">标识</span>
              <span class="info-value">{{ agent.slug || agent.id }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">后端类型</span>
              <span class="info-value">{{ backendLabel }}（{{ agent.backend_id }}）</span>
            </div>
            <div class="info-row">
              <span class="info-label">共享范围</span>
              <span class="info-value">
                {{ agent.share_config?.access_level === 'global' ? '全局可见' :
                   agent.share_config?.access_level === 'department' ? '部门内可见' : '仅自己' }}
              </span>
            </div>
            <div class="info-row" v-if="agent.created_at">
              <span class="info-label">创建时间</span>
              <span class="info-value">{{ agent.created_at }}</span>
            </div>
          </div>
        </a-card>
      </a-col>

      <!-- 右列 -->
      <a-col :xs="24" :lg="10">
        <!-- 工作统计：仅数字警员 -->
        <a-card v-if="isOfficer" class="block" title="工作统计">
          <a-row :gutter="12">
            <a-col :span="8" v-for="stat in statCards" :key="stat.label" class="stat-cell">
              <div class="stat-num">{{ stat.value }}</div>
              <div class="stat-label">{{ stat.label }}</div>
            </a-col>
          </a-row>
        </a-card>

        <!-- 工作记录：仅数字警员 -->
        <a-card v-if="isOfficer" class="block" title="工作记录">
          <a-timeline v-if="(officer.recent_runs || []).length">
            <a-timeline-item
              v-for="run in officer.recent_runs"
              :key="run.id"
              :color="runColor(run.status)"
            >
              <div class="run-row">
                <span class="run-title">运行 #{{ run.id }}</span>
                <a-tag :color="runColor(run.status)" class="run-status">{{ runText(run.status) }}</a-tag>
              </div>
              <div class="run-meta">
                案件 #{{ run.case_id }} · {{ run.tokens_used || 0 }} tokens
                <span v-if="run.started_at"> · {{ run.started_at }}</span>
              </div>
            </a-timeline-item>
          </a-timeline>
          <a-empty v-else description="暂无运行记录" />
        </a-card>

        <!-- 成长轨迹：仅数字警员 -->
        <a-card v-if="isOfficer" class="block" title="成长轨迹">
          <a-timeline v-if="(officer.growth_log || []).length">
            <a-timeline-item
              v-for="(g, i) in officer.growth_log"
              :key="i"
              color="#1A365D"
            >
              <div class="growth-event">{{ g.event }}</div>
              <div class="growth-desc">{{ g.description }}</div>
              <div class="growth-date" v-if="g.date">{{ g.date }}</div>
            </a-timeline-item>
          </a-timeline>
          <a-empty v-else description="暂无成长事件" />
        </a-card>

        <!-- 快捷操作：普通智能体 -->
        <a-card v-if="!isOfficer" class="block" title="快捷操作">
          <div class="quick-actions">
            <a-button type="primary" block @click="goChat">
              发起对话
            </a-button>
            <a-button
              v-if="agent.can_manage || isBuiltinAgent(agent)"
              block
              style="margin-top: 8px"
              @click="openEdit"
            >
              编辑配置
            </a-button>
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>

  <div v-else class="profile-loading">
    <a-spin tip="加载智能体档案中..." />
  </div>

  <!-- 统一编辑弹窗（AgentEditModal） -->
  <AgentEditModal
    ref="agentEditModalRef"
    :backend-options="backendOptions"
    @saved="onEdited"
  />

  <!-- 分享弹窗 -->
  <a-modal
    v-model:open="shareModalVisible"
    title="分享智能体"
    :confirm-loading="shareSaving"
    ok-text="确认分享"
    cancel-text="取消"
    @ok="handleShare"
  >
    <div class="share-modal-body">
      <p class="share-tip">设置共享范围后，其他用户可在「智能体市场」中看到并下载此智能体。</p>
      <ShareConfigForm
        ref="shareConfigFormRef"
        v-model="shareConfig"
        :auto-select-user-dept="true"
      />
      <a-alert
        v-if="shareConfig.access_level === 'global'"
        type="warning"
        show-icon
        message="全局共享需要系统管理员审批通过后才会上架到市场。"
        style="margin-top: 12px"
      />
    </div>
  </a-modal>
</template>

<style scoped>
.agent-profile {
  padding: var(--page-padding);
  max-width: 1180px;
  margin: 0 auto;
}

/* 分享弹窗 */
.share-modal-body { padding: 4px 0; }
.share-tip {
  font-size: 13px;
  color: var(--gray-600);
  margin-bottom: 12px;
}

.profile-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.back-arrow { font-size: 16px; margin-right: 4px; }
.bar-actions { display: flex; gap: 10px; }

/* ====== 头部档案卡 ====== */
.profile-head {
  position: relative;
  display: flex;
  align-items: center;
  gap: 18px;
  background: #fff;
  border-radius: 18px;
  padding: 22px 24px;
  box-shadow: 0 6px 18px var(--shadow-1);
  border: 1px solid var(--gray-150);
  overflow: hidden;
  margin-bottom: 18px;
}
.profile-head::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 6px;
}
.theme-blue::before { background: #2B6CB0; }
.theme-green::before { background: #2F855A; }
.theme-amber::before { background: #B7791F; }
.theme-coral::before { background: #C53030; }
.theme-purple::before { background: #6B46C1; }

.head-avatar {
  width: 72px; height: 72px;
  border-radius: 18px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}
.bg-blue { background: #2B6CB0; }
.bg-green { background: #2F855A; }
.bg-amber { background: #B7791F; }
.bg-coral { background: #C53030; }
.bg-purple { background: #6B46C1; }

.head-main { flex: 1; min-width: 0; }
.head-line1 { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.head-line1 h2 { margin: 0; font-size: 22px; color: #1A365D; font-weight: 700; }

.officer-label {
  font-size: 11px;
  color: #fff;
  background: var(--main-700);
  padding: 1px 8px;
  border-radius: 6px;
  font-weight: 600;
}

.head-line2 { display: flex; gap: 8px; margin: 8px 0; flex-wrap: wrap; }
.tag-pill {
  font-size: 12px; color: #1A365D; background: #EBF2FA;
  border-radius: 10px; padding: 2px 10px;
}
.head-specialty { font-size: 13px; color: var(--gray-700); line-height: 1.5; }

.head-exp {
  text-align: center; flex-shrink: 0;
  background: #F7FAFC; border-radius: 14px; padding: 10px 16px;
}
.exp-num { font-size: 20px; font-weight: 700; color: #1A365D; }
.exp-label { font-size: 11px; color: var(--gray-500); }

/* ====== 内容区 ====== */
.profile-body { margin: 0 !important; }
.block {
  border-radius: 16px;
  margin-bottom: 16px;
  border: 1px solid var(--gray-150);
  box-shadow: 0 4px 12px var(--shadow-1);
}
.block :deep(.ant-card-head-title) { font-weight: 600; color: #1A365D; }

/* 能力矩阵 */
.cap-matrix {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
}
.cap-item {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; color: var(--gray-800);
  background: var(--gray-50); border-radius: 10px; padding: 8px 12px;
}
.cap-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #2B6CB0; flex-shrink: 0;
}

/* 技能标签 */
.skill-tag {
  font-size: 12px; margin: 0 6px 6px 0;
  border-radius: 8px; background: #EBF2FA; color: #1A365D; border: none;
}
.muted { color: var(--gray-500); font-size: 13px; }

/* SOP */
.sop-item {
  padding: 10px 0;
  border-bottom: 1px dashed var(--gray-200);
}
.sop-item:last-child { border-bottom: none; }
.sop-name { font-size: 14px; font-weight: 600; color: #1A202C; }
.sop-desc { font-size: 12px; color: var(--gray-600); margin-top: 2px; }

/* 统计 */
.stat-cell { text-align: center; margin-bottom: 8px; }
.stat-num { font-size: 20px; font-weight: 700; color: #1A365D; }
.stat-label { font-size: 11px; color: var(--gray-500); margin-top: 2px; }

/* 运行记录 */
.run-row { display: flex; align-items: center; gap: 8px; }
.run-title { font-size: 13px; font-weight: 600; color: var(--gray-900); }
.run-status { font-size: 11px; }
.run-meta { font-size: 12px; color: var(--gray-500); margin-top: 2px; }

/* 成长轨迹 */
.growth-event { font-size: 13px; font-weight: 600; color: #1A202C; }
.growth-desc { font-size: 12px; color: var(--gray-600); margin-top: 2px; }
.growth-date { font-size: 11px; color: var(--gray-400); margin-top: 2px; }

/* 基本信息（普通智能体） */
.info-grid { display: flex; flex-direction: column; gap: 10px; }
.info-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px dashed var(--gray-150);
}
.info-row:last-child { border-bottom: none; }
.info-label {
  font-size: 12px; color: var(--gray-500);
  min-width: 72px; flex-shrink: 0;
}
.info-value { font-size: 13px; color: var(--gray-900); }

.quick-actions { padding: 4px 0; }

.profile-loading {
  display: flex; justify-content: center; padding: 120px 0;
}
</style>
