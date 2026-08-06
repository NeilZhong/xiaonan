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

    <!-- 其它类型占位 -->
    <div v-else-if="selectedType && selectedType !== 'agent'" class="mp-coming">
      「{{ currentTypeName }}」发布即将支持，敬请期待。
    </div>
  </a-drawer>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import { policeMarketApi, policeAgentApi } from '@/apis/police_api'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['update:open', 'published'])

const publishTypes = [
  { key: 'agent', icon: '🧑‍✈️', name: '数字民警', desc: '发布完整数字民警配置', available: true },
  { key: 'skill', icon: '📦', name: '技能', desc: '发布内化的知识手册', available: false, soon: true },
  { key: 'tool', icon: '🛠️', name: '工具', desc: '发布自定义工具', available: false, soon: true },
  { key: 'mcp', icon: '🔌', name: 'MCP 服务', desc: '发布 MCP 服务连接', available: false, soon: true },
  { key: 'card', icon: '🃏', name: '卡片', desc: '发布交互卡片', available: false, soon: true },
  { key: 'partner', icon: '🤝', name: '协助伙伴', desc: '发布子智能体', available: false, soon: true },
]

const selectedType = ref('')
const currentTypeName = computed(
  () => publishTypes.find((t) => t.key === selectedType.value)?.name || ''
)

const agentKeyword = ref('')
const myAgents = ref([])
const selectedAgentId = ref(null)
const reason = ref('')
const submitting = ref(false)

function selectType(t) {
  if (t.key === 'agent') {
    selectedType.value = t.key
    loadMyAgents()
  } else {
    selectedType.value = t.key // 展示「即将支持」占位
  }
}

async function loadMyAgents() {
  try {
    const res = await policeAgentApi.list({ keyword: agentKeyword.value || undefined, page_size: 100 })
    myAgents.value = res.items || []
  } catch (e) {
    message.error('加载数字民警失败: ' + (e.message || e))
  }
}

async function submit() {
  if (!selectedAgentId.value) return
  submitting.value = true
  try {
    const res = await policeMarketApi.publish({
      type: 'agent',
      asset_id: selectedAgentId.value,
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
  reason.value = ''
  agentKeyword.value = ''
  myAgents.value = []
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
