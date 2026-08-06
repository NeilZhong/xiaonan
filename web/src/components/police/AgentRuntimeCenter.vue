<script setup>
/**
 * 数字警员运行中心抽屉（参考悟帆运行中心）
 * - 流动版本 / 受控发布 双模式切换（二次确认）
 * - 版本历史（自动版本化，可回滚）
 * - 资产健康度
 */
import { ref, computed, onMounted, watch } from 'vue'
import { message, Modal, Empty } from 'ant-design-vue'
import { Rocket, History, Activity } from 'lucide-vue-next'
import { policeAgentApi } from '@/apis/police_api'

const props = defineProps({
  open: { type: Boolean, default: false },
  /** 数字警员对象（含 id） */
  agent: { type: Object, required: true }
})
const emit = defineEmits(['update:open'])

const aEmptyImage = Empty.PRESENTED_IMAGE_SIMPLE

const loading = ref(false)
const versions = ref([])
const releaseMode = ref('rolling')
const currentVersionId = ref(null)
const draftVersionId = ref(null)
const health = ref(null)

const currentVersion = computed(() =>
  versions.value.find((v) => v.id === currentVersionId.value) || versions.value[0] || null
)
const draftVersion = computed(() =>
  versions.value.find((v) => v.id === draftVersionId.value) || null
)

async function load() {
  if (!props.agent?.id) return
  loading.value = true
  try {
    const [v, h] = await Promise.all([
      policeAgentApi.listVersions(props.agent.id),
      policeAgentApi.health(props.agent.id)
    ])
    versions.value = v.items || []
    releaseMode.value = v.release_mode || 'rolling'
    currentVersionId.value = v.current_version_id ?? null
    draftVersionId.value = v.draft_version_id ?? null
    health.value = h
  } catch (e) {
    message.error(e.message || '加载运行状态失败')
  } finally {
    loading.value = false
  }
}

async function switchMode(target) {
  if (target === releaseMode.value) return
  const toControlled = target === 'controlled'
  const ok = await new Promise((resolve) => {
    Modal.confirm({
      title: toControlled ? '切换到受控发布？' : '切换到流动版本？',
      content: toControlled
        ? '之后的改动将进入草稿，不会立即影响线上使用。测试无误后需手动点「发布」才会生效。'
        : '之后的改动将自动生效，无需手动发布。',
      okText: '切换', cancelText: '取消',
      onOk: () => resolve(true),
      onCancel: () => resolve(false)
    })
  })
  if (!ok) return
  try {
    const res = await policeAgentApi.switchReleaseMode(props.agent.id, target)
    releaseMode.value = res.release_mode
    message.success('发布模式已切换')
    await load()
  } catch (e) {
    message.error(e.message || '切换失败')
  }
}

async function publishDraft() {
  if (!draftVersionId.value) return
  const ok = await new Promise((resolve) => {
    Modal.confirm({
      title: '发布草稿版本？',
      content: '发布后该版本将立即对线上使用生效，旧版本将进入历史记录。',
      okText: '发布', cancelText: '取消',
      onOk: () => resolve(true),
      onCancel: () => resolve(false)
    })
  })
  if (!ok) return
  try {
    await policeAgentApi.publishVersion(props.agent.id, draftVersionId.value)
    message.success('草稿已发布')
    await load()
  } catch (e) {
    message.error(e.message || '发布失败')
  }
}

async function rollback(v) {
  const ok = await new Promise((resolve) => {
    Modal.confirm({
      title: `回滚到 ${v.version_label}？`,
      content: '回滚将基于该版本快照生成一个新版本并立即生效，原配置会恢复为该版本的内容。',
      okText: '回滚', okType: 'danger', cancelText: '取消',
      onOk: () => resolve(true),
      onCancel: () => resolve(false)
    })
  })
  if (!ok) return
  try {
    await policeAgentApi.rollbackVersion(props.agent.id, v.id)
    message.success(`已回滚到 ${v.version_label}`)
    await load()
  } catch (e) {
    message.error(e.message || '回滚失败')
  }
}

onMounted(load)
watch(() => [props.open, props.agent?.id], ([open]) => {
  if (open) load()
})
</script>

<template>
  <a-drawer
    :open="open"
    title="运行中心"
    :width="520"
    @update:open="(v) => emit('update:open', v)"
  >
    <a-spin :spinning="loading">
      <!-- 运行模式 -->
      <div class="rc-section">
        <h4 class="rc-title">运行模式</h4>
        <p class="rc-desc">决定改动是否需要手动发布才生效。可在这里直接切换。</p>
        <div class="rc-mode-card" :class="`m-${releaseMode}`">
          <div class="rc-mode-head">
            <span class="rc-mode-name">{{ releaseMode === 'rolling' ? '流动版本' : '受控发布' }}</span>
            <a-button v-if="releaseMode === 'rolling'" size="small" @click="switchMode('controlled')">
              切到受控发布
            </a-button>
            <a-button v-else size="small" @click="switchMode('rolling')">切到流动版本</a-button>
          </div>
          <p class="rc-mode-desc">
            {{ releaseMode === 'rolling' ? '改动即生效，无需手动发布。' : '改动进入草稿，手动点「发布」后才生效。' }}
          </p>
        </div>
      </div>

      <!-- 当前运行 -->
      <div class="rc-section">
        <h4 class="rc-title">当前运行</h4>
        <div class="rc-current">
          <div class="rc-current-row">
            <span class="rc-k">版本</span>
            <span class="rc-v rc-ver">{{ currentVersion?.version_label || '—' }}</span>
            <a-tag v-if="currentVersion" color="green">运行中</a-tag>
          </div>
          <div class="rc-current-row">
            <span class="rc-k">改动摘要</span>
            <span class="rc-v">{{ currentVersion?.change_summary || '—' }}</span>
          </div>
          <div class="rc-current-row">
            <span class="rc-k">发布时间</span>
            <span class="rc-v">{{ (currentVersion?.published_at || currentVersion?.created_at || '').substring(0, 16) || '—' }}</span>
          </div>
        </div>
      </div>

      <!-- 资产健康度 -->
      <div class="rc-section">
        <h4 class="rc-title">资产健康度</h4>
        <div class="rc-health">
          <span v-if="health" class="rc-health-status" :class="health.synced ? 'ok' : 'warn'">
            <Activity :size="13" />
            {{ health.synced ? '全部同步' : '存在待发布内容' }}
          </span>
          <span v-if="health" class="rc-health-meta">
            {{ health.release_mode === 'rolling' ? '流动版本模式' : '受控发布模式' }}
            <template v-if="health.draft_count"> · 草稿 {{ health.draft_count }} 份</template>
          </span>
        </div>
      </div>

      <!-- 受控发布草稿区 -->
      <div v-if="releaseMode === 'controlled' && draftVersion" class="rc-section rc-draft">
        <h4 class="rc-title">待发布草稿</h4>
        <div class="rc-draft-card">
          <div class="rc-draft-row">
            <span class="rc-ver">{{ draftVersion.version_label }}</span>
            <span class="rc-draft-summary">{{ draftVersion.change_summary }}</span>
          </div>
          <a-button type="primary" size="small" @click="publishDraft">发布</a-button>
        </div>
      </div>

      <!-- 版本历史 -->
      <div class="rc-section">
        <h4 class="rc-title"><History :size="13" /> 版本历史</h4>
        <p class="rc-desc">每次灵魂或资产改动都会自动产生一次新版本。可以回滚到任意历史版本。</p>
        <div v-if="versions.length" class="rc-versions">
          <div v-for="v in versions" :key="v.id" class="rc-version-item">
            <div class="rc-version-head">
              <span class="rc-ver">{{ v.version_label }}</span>
              <a-tag v-if="v.id === currentVersionId" color="green">最新</a-tag>
              <a-tag v-else-if="v.status === 'draft'" color="orange">草稿</a-tag>
              <a-tag v-else-if="v.status === 'rolled_back'" color="default">已回滚</a-tag>
              <span v-else class="rc-ver-old">历史</span>
            </div>
            <div class="rc-version-summary">{{ v.change_summary || '—' }}</div>
            <div class="rc-version-meta">
              <span>{{ (v.published_at || v.created_at || '').substring(0, 16) }}</span>
              <a-button
                v-if="v.id !== currentVersionId && v.status !== 'draft'"
                type="link" size="small" danger
                @click="rollback(v)"
              >回滚到此版本</a-button>
            </div>
          </div>
        </div>
        <a-empty v-else description="暂无版本记录" :image="aEmptyImage" style="padding: 16px 0" />
      </div>
    </a-spin>
  </a-drawer>
</template>

<style lang="less" scoped>
.rc-section {
  margin-bottom: 22px;
}
.rc-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-900);
}
.rc-desc {
  margin: 0 0 10px 0;
  font-size: 12px;
  color: var(--gray-500);
  line-height: 1.6;
}
.rc-mode-card {
  padding: 14px;
  border: 1px solid var(--gray-150);
  border-radius: 10px;
  &.m-rolling {
    background: var(--color-success-50);
    border-color: var(--color-success-200);
  }
  &.m-controlled {
    background: var(--color-warning-50);
    border-color: var(--color-warning-200);
  }
}
.rc-mode-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.rc-mode-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-900);
}
.rc-mode-desc {
  margin: 6px 0 0 0;
  font-size: 12px;
  color: var(--gray-600);
}
.rc-current {
  padding: 12px 14px;
  border: 1px solid var(--gray-150);
  border-radius: 10px;
  background: var(--gray-25);
}
.rc-current-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 0;
  font-size: 12px;
}
.rc-k {
  width: 64px;
  flex-shrink: 0;
  color: var(--gray-500);
}
.rc-v {
  color: var(--gray-800);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rc-ver {
  font-family: var(--font-mono, monospace);
  font-weight: 600;
  color: var(--main-700);
}
.rc-health {
  display: flex;
  align-items: center;
  gap: 12px;
}
.rc-health-status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  &.ok { color: var(--color-success-600); }
  &.warn { color: var(--color-warning-600); }
}
.rc-health-meta {
  font-size: 12px;
  color: var(--gray-500);
}
.rc-draft-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  border: 1px dashed var(--color-warning-300);
  border-radius: 10px;
  background: var(--color-warning-50);
}
.rc-draft-row {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.rc-draft-summary {
  font-size: 12px;
  color: var(--gray-600);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rc-versions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.rc-version-item {
  padding: 10px 12px;
  border: 1px solid var(--gray-150);
  border-radius: 10px;
  background: var(--gray-0);
}
.rc-version-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.rc-ver-old {
  font-size: 11px;
  color: var(--gray-400);
}
.rc-version-summary {
  margin: 4px 0;
  font-size: 12px;
  color: var(--gray-700);
}
.rc-version-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11px;
  color: var(--gray-400);
}
</style>
