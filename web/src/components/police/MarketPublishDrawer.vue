<template>
  <a-drawer
    :open="open"
    :width="520"
    title="发布到市场"
    @close="emit('update:open', false)"
  >
    <p class="mp-sub">将你的创作与小南社区分享</p>

    <!-- 类型选择 -->
    <div class="mp-types">
      <div
        v-for="t in publishTypes"
        :key="t.key"
        class="mp-type-card"
        :class="{ active: selectedType === t.key, soon: !t.available }"
        @click="selectType(t)"
      >
        <span class="mp-type-icon">{{ t.icon }}</span>
        <div class="mp-type-main">
          <div class="mp-type-name">{{ t.name }}</div>
          <div class="mp-type-desc">{{ t.desc }}</div>
        </div>
        <span class="mp-type-arrow">
          {{ t.available ? '→' : (t.soon ? '即将支持' : '') }}
        </span>
      </div>
    </div>

    <!-- 数字民警发布表单 -->
    <template v-if="selectedType === 'agent'">
      <a-divider style="margin: 12px 0" />
      <div class="mp-form">
        <div class="mp-field">
          <div class="mp-label">选择要发布的数字民警</div>
          <a-input-search
            v-model:value="agentKeyword"
            placeholder="搜索数字民警"
            allow-clear
            size="small"
            @search="loadMyAgents"
          />
        </div>
        <div v-if="myAgents.length" class="mp-agent-list">
          <div
            v-for="a in myAgents"
            :key="a.id"
            class="mp-agent-item"
            :class="{ selected: selectedAgentId === a.id }"
            @click="selectedAgentId = a.id"
          >
            <span class="mp-agent-name">{{ a.name }}</span>
            <span class="mp-agent-meta">{{ a.badge_number || '未授警号' }}</span>
          </div>
        </div>
        <div v-else class="mp-empty">暂无可选数字民警（仅创建者或超管可发布）</div>

        <div class="mp-field" style="margin-top: 12px">
          <div class="mp-label">发布说明</div>
          <a-textarea
            v-model:value="reason"
            :rows="3"
            maxlength="200"
            show-count
            placeholder="说明这个数字民警的用途与亮点（提交审核时可见）"
          />
        </div>

        <a-button
          type="primary"
          block
          class="mp-submit"
          :disabled="!selectedAgentId"
          :loading="submitting"
          @click="submit"
        >
          提交审核
        </a-button>
      </div>
    </template>

    <!-- 协助伙伴发布表单（P5） -->
    <template v-else-if="selectedType === 'partner'">
      <a-divider style="margin: 12px 0" />
      <div class="mp-form">
        <div class="mp-field">
          <div class="mp-label">选择要发布的协助伙伴</div>
          <a-input-search
            v-model:value="partnerKeyword"
            placeholder="搜索协助伙伴"
            allow-clear
            size="small"
            @search="loadMyPartners"
          />
        </div>
        <div v-if="myPartners.length" class="mp-agent-list">
          <div
            v-for="p in myPartners"
            :key="p.id"
            class="mp-agent-item"
            :class="{ selected: selectedPartnerId === p.id }"
            @click="selectedPartnerId = p.id"
          >
            <span class="mp-agent-name">{{ p.name }}</span>
            <span class="mp-agent-meta">{{ categoryLabel(p.category) }}</span>
          </div>
        </div>
        <div v-else class="mp-empty">暂无可选协助伙伴（仅创建者或超管可发布）</div>

        <div class="mp-field" style="margin-top: 12px">
          <div class="mp-label">发布说明</div>
          <a-textarea
            v-model:value="reason"
            :rows="3"
            maxlength="200"
            show-count
            placeholder="说明这个协助伙伴的用途与亮点（提交审核时可见）"
          />
        </div>

        <a-button
          type="primary"
          block
          class="mp-submit"
          :disabled="!selectedPartnerId"
          :loading="submitting"
          @click="submit"
        >
          提交审核
        </a-button>
      </div>
    </template>

    <!-- 其它类型占位 -->
    <div v-else-if="selectedType && selectedType !== 'agent'" class="mp-coming">
      「{{ currentTypeName }}」发布即将支持，敬请期待。
    </div>
  </a-drawer>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import { policeMarketApi, policeAgentApi, policePartnerApi } from '@/apis/police_api'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['update:open', 'published'])

const CATEGORY_LABELS = {
  case_analysis: '案件分析',
  fund_tracking: '资金追踪',
  intelligence: '情报研判',
  evidence_mgmt: '调证取证',
  legal_review: '法制审核',
  interrogation: '审讯辅助',
  image_recon: '图像侦查',
  anti_fraud: '反诈劝阻',
  command: '指挥调度',
  partner_generic: '通用协助',
}
const categoryLabel = (c) => CATEGORY_LABELS[c] || c || '未分类'

const publishTypes = [
  { key: 'agent', icon: '🧑‍✈️', name: '数字民警', desc: '发布完整数字民警配置', available: true },
  { key: 'skill', icon: '📦', name: '技能', desc: '发布内化的知识手册', available: false, soon: true },
  { key: 'tool', icon: '🛠️', name: '工具', desc: '发布自定义工具', available: false, soon: true },
  { key: 'mcp', icon: '🔌', name: 'MCP 服务', desc: '发布 MCP 服务连接', available: false, soon: true },
  { key: 'card', icon: '🃏', name: '卡片', desc: '发布交互卡片', available: false, soon: true },
  { key: 'partner', icon: '🤝', name: '协助伙伴', desc: '发布子智能体', available: true },
]

const selectedType = ref('')
const currentTypeName = computed(
  () => publishTypes.find((t) => t.key === selectedType.value)?.name || ''
)

const agentKeyword = ref('')
const myAgents = ref([])
const selectedAgentId = ref(null)
const partnerKeyword = ref('')
const myPartners = ref([])
const selectedPartnerId = ref(null)
const reason = ref('')
const submitting = ref(false)

function selectType(t) {
  selectedType.value = t.key
  if (t.key === 'agent') loadMyAgents()
  if (t.key === 'partner') loadMyPartners()
}

async function loadMyAgents() {
  try {
    const res = await policeAgentApi.list({ keyword: agentKeyword.value || undefined, page_size: 100 })
    myAgents.value = res.items || []
  } catch (e) {
    message.error('加载数字民警失败: ' + (e.message || e))
  }
}

async function loadMyPartners() {
  try {
    const res = await policePartnerApi.list({
      keyword: partnerKeyword.value || undefined,
      status: 'mine',
      page_size: 100,
    })
    myPartners.value = res.items || []
  } catch (e) {
    message.error('加载协助伙伴失败: ' + (e.message || e))
  }
}

async function submit() {
  if (selectedType.value === 'agent' && !selectedAgentId.value) return
  if (selectedType.value === 'partner' && !selectedPartnerId.value) return
  submitting.value = true
  try {
    const asset_id = selectedType.value === 'partner' ? selectedPartnerId.value : selectedAgentId.value
    const res = await policeMarketApi.publish({
      type: selectedType.value,
      asset_id,
      reason: reason.value || null,
    })
    message.success(res?.message || '已提交审核')
    emit('published')
    emit('update:open', false)
    resetForm()
  } catch (e) {
    message.error('发布失败: ' + (e.message || e))
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  selectedType.value = ''
  selectedAgentId.value = null
  selectedPartnerId.value = null
  reason.value = ''
  agentKeyword.value = ''
  partnerKeyword.value = ''
  myAgents.value = []
  myPartners.value = []
}

watch(
  () => props.open,
  (v) => {
    if (v) resetForm()
  }
)
</script>

<style scoped>
.mp-sub {
  color: var(--gray-600);
  font-size: 13px;
  margin: 0 0 14px;
}
.mp-types {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.mp-type-card {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 12px;
  border: 1px solid var(--gray-200);
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.16s ease, background 0.16s ease;
}
.mp-type-card:hover {
  border-color: var(--main-400);
}
.mp-type-card.active {
  border-color: #1a365d;
  background: #ebf2fa;
}
.mp-type-card.soon {
  opacity: 0.55;
}
.mp-type-icon {
  font-size: 22px;
}
.mp-type-main {
  flex: 1;
  min-width: 0;
}
.mp-type-name {
  font-size: 13px;
  font-weight: 600;
  color: #1a202c;
}
.mp-type-desc {
  font-size: 11px;
  color: var(--gray-500);
  margin-top: 2px;
}
.mp-type-arrow {
  font-size: 12px;
  color: var(--gray-400);
  flex-shrink: 0;
}
.mp-form {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.mp-label {
  font-size: 12px;
  color: var(--gray-600);
  margin-bottom: 6px;
}
.mp-agent-list {
  max-height: 220px;
  overflow-y: auto;
  border: 1px solid var(--gray-200);
  border-radius: 10px;
  margin-top: 8px;
}
.mp-agent-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  cursor: pointer;
}
.mp-agent-item:hover {
  background: var(--gray-100);
}
.mp-agent-item.selected {
  background: #ebf2fa;
}
.mp-agent-name {
  font-size: 13px;
  color: #1a202c;
}
.mp-agent-meta {
  font-size: 11px;
  color: var(--gray-500);
}
.mp-empty {
  font-size: 12px;
  color: var(--gray-500);
  padding: 12px 0;
}
.mp-submit {
  margin-top: 16px;
  background: #1a365d;
  border-color: #1a365d;
}
.mp-coming {
  margin-top: 24px;
  text-align: center;
  color: var(--gray-500);
  font-size: 13px;
  padding: 30px 0;
}
</style>
