<template>
  <div class="reflection-view">
    <!-- 头部：标题 + 触发入口 + 筛选 -->
    <div class="rv-header">
      <div class="rv-title">
        <span class="rv-emoji">📋</span>
        <div>
          <h2>办案复盘</h2>
          <p class="rv-sub">数字民警任务后反思 / 技能自修复产物，民警确认后才入册，绝不自动改线上</p>
        </div>
      </div>
      <div class="rv-actions">
        <a-button @click="openTrigger">手动触发复盘</a-button>
      </div>
    </div>

    <div class="rv-filters">
      <a-segmented
        v-model:value="statusFilter"
        :options="statusOptions"
        @change="onFilterChange"
      />
      <a-segmented
        v-model:value="typeFilter"
        :options="typeOptions"
        @change="onFilterChange"
      />
    </div>

    <!-- 列表 -->
    <a-spin :spinning="loading">
      <div v-if="items.length" class="rv-list">
        <div v-for="r in items" :key="r.id" class="rv-card">
          <div class="rv-card-head">
            <a-tag :color="phaseTag(r).color" class="rv-phase">{{ phaseTag(r).text }}</a-tag>
            <a-tag :color="statusTag(r.status).color">{{ statusTag(r.status).text }}</a-tag>
            <span class="rv-time">{{ (r.created_at || '').substring(0, 19).replace('T', ' ') }}</span>
          </div>
          <div class="rv-card-body">
            <div v-if="r.phase === 'skill' && r.payload.template_draft" class="rv-summary">
              技能沉淀：{{ r.payload.template_draft.name }}
            </div>
            <div v-else-if="r.phase === 'memory' && r.payload.candidate_memory" class="rv-summary">
              记忆审计：{{ (r.payload.candidate_memory.content || '').slice(0, 80) }}…
            </div>
            <div v-else-if="r.phase === 'repair'" class="rv-summary">技能自修复：修订建议待审</div>
            <div v-else class="rv-summary">复盘记录 #{{ r.id }}</div>
          </div>
          <div class="rv-card-foot">
            <span class="rv-source">{{ sourceLabel(r.source) }} · 触发{{ r.trigger_type === 'A' ? '任务后反思' : '技能自修复' }}</span>
            <div v-if="r.status === 'pending_review' || r.status === 'draft'" class="rv-ops">
              <a-button size="small" type="primary" @click="review(r, 'approve')">确认入册</a-button>
              <a-button size="small" danger @click="review(r, 'reject')">驳回</a-button>
            </div>
          </div>
        </div>
      </div>
      <a-empty v-else-if="!loading" description="暂无复盘记录" />
    </a-spin>

    <!-- 手动触发弹窗 -->
    <a-modal
      v-model:open="triggerOpen"
      title="手动触发办案复盘"
      ok-text="触发"
      cancel-text="取消"
      @ok="doTrigger"
    >
      <p style="font-size: 12px; color: var(--gray-500)">
        把一段办案过程/对话摘要交给数字民警做任务后反思：满足条件会自动生成记忆审计 / 技能沉淀记录（draft，待你审阅）。
      </p>
      <a-input-number
        v-model:value="triggerForm.agent_id"
        placeholder="数字民警 ID（可选）"
        style="width: 100%; margin-bottom: 10px"
      />
      <a-input-number
        v-model:value="triggerForm.case_id"
        placeholder="案件 ID（可选）"
        style="width: 100%; margin-bottom: 10px"
      />
      <a-textarea
        v-model:value="triggerForm.conversation_summary"
        :rows="5"
        maxlength="800"
        show-count
        placeholder="粘贴办案过程 / 对话摘要，例如：办理电信诈骗案件时，先调取银行流水固定资金链，再交叉比对群聊记录确认涉案人员…"
      />
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { policeReflectionApi } from '@/apis/police_api'

const items = ref([])
const total = ref(0)
const loading = ref(false)
const statusFilter = ref('')
const typeFilter = ref('')
const triggerOpen = ref(false)
const triggerForm = ref({ agent_id: null, case_id: null, conversation_summary: '' })

const statusOptions = [
  { label: '全部', value: '' },
  { label: '待审', value: 'pending_review' },
  { label: '草稿', value: 'draft' },
  { label: '已应用', value: 'applied' },
  { label: '已驳回', value: 'rejected' },
]
const typeOptions = [
  { label: '全部类型', value: '' },
  { label: '任务后反思', value: 'A' },
  { label: '技能自修复', value: 'B' },
]

const phaseTag = (r) =>
  ({
    memory: { text: '记忆审计', color: 'blue' },
    skill: { text: '技能沉淀', color: 'green' },
    profile: { text: '用户画像', color: 'purple' },
    repair: { text: '修订建议', color: 'orange' },
  })[r.phase] || { text: r.phase, color: 'default' }

const statusTag = (s) =>
  ({
    draft: { text: '草稿', color: 'default' },
    pending_review: { text: '待审', color: 'processing' },
    applied: { text: '已应用', color: 'success' },
    rejected: { text: '已驳回', color: 'error' },
  })[s] || { text: s, color: 'default' }

const sourceLabel = (s) => (s === 'template_audit' ? '模板审计' : '对话')

async function load() {
  loading.value = true
  try {
    const res = await policeReflectionApi.list({
      trigger_type: typeFilter.value || undefined,
      status: statusFilter.value || undefined,
    })
    items.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    message.error('加载复盘记录失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

function onFilterChange() {
  load()
}

async function review(record, action) {
  try {
    const res = await policeReflectionApi.review(record.id, action)
    message.success(res?.message || (action === 'approve' ? '已应用并入册' : '已驳回'))
    load()
  } catch (e) {
    message.error('操作失败: ' + (e.message || e))
  }
}

function openTrigger() {
  triggerOpen.value = true
}

async function doTrigger() {
  if (!triggerForm.value.conversation_summary?.trim()) {
    message.warning('请先粘贴办案过程/对话摘要')
    return
  }
  try {
    const res = await policeReflectionApi.trigger({
      agent_id: triggerForm.value.agent_id || null,
      case_id: triggerForm.value.case_id || null,
      conversation_summary: triggerForm.value.conversation_summary.trim(),
    })
    message.success(res?.message || '已触发')
    triggerOpen.value = false
    triggerForm.value = { agent_id: null, case_id: null, conversation_summary: '' }
    load()
  } catch (e) {
    message.error('触发失败: ' + (e.message || e))
  }
}

onMounted(load)
</script>

<style scoped>
.reflection-view {
  padding: var(--page-padding);
  max-width: 1080px;
  margin: 0 auto;
}
.rv-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 18px;
}
.rv-title {
  display: flex;
  gap: 14px;
  align-items: center;
}
.rv-emoji {
  font-size: 34px;
  filter: drop-shadow(0 2px 4px var(--shadow-1));
}
.rv-title h2 {
  margin: 0;
  font-size: 22px;
  color: #1a365d;
  font-weight: 700;
}
.rv-sub {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--gray-600);
}
.rv-filters {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}
.rv-filters :deep(.ant-segmented) {
  background: var(--gray-100);
  border-radius: 8px;
}
.rv-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rv-card {
  background: #fff;
  border-radius: 14px;
  padding: 14px 16px;
  box-shadow: 0 4px 16px rgba(16, 30, 54, 0.06);
  border: 1px solid var(--gray-150);
}
.rv-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.rv-phase {
  margin: 0;
}
.rv-time {
  margin-left: auto;
  font-size: 12px;
  color: var(--gray-500);
}
.rv-card-body {
  margin: 10px 0;
}
.rv-summary {
  font-size: 13px;
  color: var(--gray-800);
  line-height: 1.6;
}
.rv-card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px dashed var(--gray-200);
  padding-top: 10px;
}
.rv-source {
  font-size: 12px;
  color: var(--gray-500);
}
.rv-ops {
  display: flex;
  gap: 8px;
}
</style>
