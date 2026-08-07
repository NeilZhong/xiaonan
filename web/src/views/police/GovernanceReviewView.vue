<template>
  <div class="gov-view">
    <!-- 头部：标题 + 副标题 -->
    <div class="gv-header">
      <div class="gv-title">
        <span class="gv-emoji">🛡️</span>
        <div>
          <h2>审核台</h2>
          <p class="gv-sub">数字警员与协助伙伴的上架审核：查看全量配置、对话试跑，再决定是否通过</p>
        </div>
      </div>
    </div>

    <!-- 类型筛选 -->
    <div class="gv-filters">
      <a-segmented v-model:value="typeFilter" :options="typeOptions" @change="load" />
    </div>

    <!-- 待审列表 -->
    <a-spin :spinning="loading">
      <div v-if="items.length" class="gv-list">
        <div
          v-for="it in items"
          :key="it.id"
          class="gv-card"
          @click="openDetail(it)"
        >
          <div class="gv-card-head">
            <a-tag :color="it.request_type === 'partner' ? 'purple' : 'blue'">
              {{ it.request_type === 'partner' ? '协助伙伴' : '数字警员' }}
            </a-tag>
            <a-tag :color="shareTag(it.share_level).color">{{ shareTag(it.share_level).text }}</a-tag>
            <span class="gv-time">{{ (it.requested_at || '').substring(0, 19).replace('T', ' ') }}</span>
          </div>
          <div class="gv-card-name">{{ it.name }}</div>
          <div class="gv-card-desc">{{ it.description || '暂无描述' }}</div>
          <div class="gv-card-foot">
            <span class="gv-meta">分类：{{ it.category || '—' }}</span>
            <span class="gv-arrow">查看详情 ›</span>
          </div>
        </div>
      </div>
      <a-empty v-else-if="!loading" description="暂无待审核项" />
    </a-spin>

    <!-- 详情抽屉 -->
    <a-drawer
      v-model:open="detailOpen"
      :title="detail?.agent?.name ? `审核 · ${detail.agent.name}` : '审核详情'"
      width="760"
    >
      <div v-if="detail" class="gd-body">
        <!-- 基本信息 -->
        <section class="gd-section">
          <h3>基本信息</h3>
          <a-descriptions :column="1" size="small" bordered>
            <a-descriptions-item label="类型">
              {{ currentItem?.request_type === 'partner' ? '协助伙伴' : '数字警员' }}
            </a-descriptions-item>
            <a-descriptions-item label="描述">{{ detail.agent?.description || '—' }}</a-descriptions-item>
            <a-descriptions-item label="分类">{{ detail.agent?.category || '—' }}</a-descriptions-item>
            <a-descriptions-item label="共享范围">
              {{ shareTag(detail.agent?.share_config?.access_level).text }}
            </a-descriptions-item>
            <a-descriptions-item label="工号">{{ detail.agent?.badge_number || '—' }}</a-descriptions-item>
            <a-descriptions-item label="当前运行模式">{{ modeTag(detail.release_mode).text }}</a-descriptions-item>
          </a-descriptions>
        </section>

        <!-- 关联伙伴 -->
        <section v-if="detail.associated_partners?.length" class="gd-section">
          <h3>关联协助伙伴</h3>
          <a-space wrap>
            <a-tag v-for="p in detail.associated_partners" :key="p.id" color="purple">
              {{ p.name }}（{{ p.approval_status }}）
            </a-tag>
          </a-space>
        </section>

        <!-- 全量配置 -->
        <section class="gd-section">
          <h3>全量配置</h3>
          <a-collapse :active-key="['sp']">
            <a-collapse-panel key="sp" header="系统提示词 (system_prompt)">
              <pre class="gd-pre">{{ detail.runtime?.system_prompt || '（空）' }}</pre>
            </a-collapse-panel>
            <a-collapse-panel key="mc" header="模型配置 (model_config)">
              <pre class="gd-pre">{{ pretty(detail.runtime?.model_config) }}</pre>
            </a-collapse-panel>
            <a-collapse-panel key="tools" header="工具 / 技能 / 知识库">
              <div class="gd-kv"><b>工具：</b>{{ (detail.runtime?.tools || []).join('、') || '—' }}</div>
              <div class="gd-kv"><b>技能：</b>{{ (detail.runtime?.skills || []).join('、') || '—' }}</div>
              <div class="gd-kv"><b>知识库：</b>{{ (detail.runtime?.knowledge_base_ids || []).join('、') || '—' }}</div>
            </a-collapse-panel>
            <a-collapse-panel key="ver" header="版本基线">
              <div class="gd-kv">当前版本 ID：{{ detail.current_version_id ?? '—' }}</div>
              <div class="gd-kv">草稿版本 ID：{{ detail.draft_version_id ?? '—' }}</div>
              <div class="gd-kv">版本数：{{ detail.versions?.length || 0 }}</div>
            </a-collapse-panel>
          </a-collapse>
        </section>

        <!-- 试跑 -->
        <section class="gd-section">
          <h3>对话试跑（草稿配置）</h3>
          <a-textarea
            v-model:value="previewMsg"
            :rows="2"
            placeholder="输入一句测试对话，例如：帮我把这段笔录整理成案件概要"
            style="margin-bottom: 8px"
          />
          <a-button :loading="previewLoading" @click="runPreview">试跑</a-button>
          <div v-if="previewResult" class="gd-preview">
            <a-alert
              v-if="previewResult.warning"
              type="warning"
              :message="previewResult.warning"
              show-icon
              style="margin-bottom: 8px"
            />
            <div class="gd-kv">
              <b>生效模型：</b>{{ previewResult.model }}（来源：{{ previewResult.config_source }}）
            </div>
            <pre class="gd-pre">{{ previewResult.reply }}</pre>
          </div>
        </section>
      </div>

      <template #footer>
        <div class="gd-footer">
          <a-button :loading="decideLoading" danger @click="openReject">驳回</a-button>
          <a-button :loading="decideLoading" type="primary" @click="approve">通过并上架</a-button>
        </div>
      </template>
    </a-drawer>

    <!-- 驳回理由 -->
    <a-modal
      v-model:open="rejectOpen"
      title="驳回理由"
      ok-text="确认驳回"
      cancel-text="取消"
      @ok="reject"
    >
      <a-textarea v-model:value="rejectReason" :rows="3" placeholder="请填写驳回原因（将记入审计）" />
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { policeGovernanceApi } from '@/apis/police_api'

const items = ref([])
const loading = ref(false)
const typeFilter = ref('')

const detailOpen = ref(false)
const detail = ref(null)
const currentItem = ref(null)

const previewMsg = ref('帮我把这段笔录整理成案件概要')
const previewLoading = ref(false)
const previewResult = ref(null)

const decideLoading = ref(false)
const rejectOpen = ref(false)
const rejectReason = ref('')

const typeOptions = [
  { label: '全部', value: '' },
  { label: '数字警员', value: 'agent' },
  { label: '协助伙伴', value: 'partner' },
]

const shareTag = (lv) =>
  ({
    personal: { text: '个人', color: 'default' },
    department: { text: '部门', color: 'blue' },
    user: { text: '指定用户', color: 'cyan' },
    global: { text: '全局', color: 'gold' },
  })[lv] || { text: lv || '—', color: 'default' }

const modeTag = (m) =>
  m === 'rolling'
    ? { text: '流动发布', color: 'green' }
    : { text: '受控发布', color: 'orange' }

const pretty = (v) => (v == null ? '—' : JSON.stringify(v, null, 2))

async function load() {
  loading.value = true
  try {
    const res = await policeGovernanceApi.reviewPending({ page: 1, page_size: 50 })
    const all = res.items || []
    items.value = typeFilter.value
      ? all.filter((it) => it.request_type === typeFilter.value)
      : all
  } catch (e) {
    message.error('加载待审列表失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

async function openDetail(it) {
  currentItem.value = it
  detailOpen.value = true
  detail.value = null
  previewResult.value = null
  loading.value = true
  try {
    const res = await policeGovernanceApi.reviewDetail(it.id)
    detail.value = res
  } catch (e) {
    message.error('加载详情失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

async function runPreview() {
  if (!previewMsg.value?.trim()) {
    message.warning('请先输入试跑内容')
    return
  }
  previewLoading.value = true
  previewResult.value = null
  try {
    const res = await policeGovernanceApi.preview(currentItem.value.id, {
      message: previewMsg.value.trim(),
      use_draft: true,
    })
    previewResult.value = res
  } catch (e) {
    message.error('试跑失败: ' + (e.message || e))
  } finally {
    previewLoading.value = false
  }
}

async function approve() {
  await decide(true)
}
function openReject() {
  rejectOpen.value = true
}
async function reject() {
  if (!rejectReason.value?.trim()) {
    message.warning('请填写驳回原因')
    return
  }
  await decide(false, rejectReason.value.trim())
}

async function decide(approved, reason = null) {
  const it = currentItem.value
  if (!it) return
  decideLoading.value = true
  try {
    await policeGovernanceApi.decide(it.request_type, it.id, { approved, reason })
    message.success(approved ? '已通过并上架' : '已驳回')
    rejectOpen.value = false
    rejectReason.value = ''
    detailOpen.value = false
    load()
  } catch (e) {
    message.error('操作失败: ' + (e.message || e))
  } finally {
    decideLoading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.gov-view { padding: var(--page-padding); max-width: 1080px; margin: 0 auto; }
.gv-header { margin-bottom: 18px; }
.gv-title { display: flex; gap: 14px; align-items: center; }
.gv-emoji { font-size: 34px; }
.gv-title h2 { margin: 0; font-size: 22px; color: #1a365d; font-weight: 700; }
.gv-sub { margin: 4px 0 0; font-size: 13px; color: var(--gray-600); }
.gv-filters { margin-bottom: 18px; }
.gv-filters :deep(.ant-segmented) { background: var(--gray-100); border-radius: 8px; }
.gv-list { display: flex; flex-direction: column; gap: 12px; }
.gv-card { background: #fff; border-radius: 14px; padding: 14px 16px; box-shadow: 0 4px 16px rgba(16,30,54,0.06); border: 1px solid var(--gray-150); cursor: pointer; transition: box-shadow .15s; }
.gv-card:hover { box-shadow: 0 6px 22px rgba(16,30,54,0.12); }
.gv-card-head { display: flex; align-items: center; gap: 8px; }
.gv-time { margin-left: auto; font-size: 12px; color: var(--gray-500); }
.gv-card-name { font-size: 15px; font-weight: 600; color: #1a365d; margin: 10px 0 4px; }
.gv-card-desc { font-size: 13px; color: var(--gray-700); line-height: 1.6; max-height: 42px; overflow: hidden; }
.gv-card-foot { display: flex; align-items: center; justify-content: space-between; border-top: 1px dashed var(--gray-200); padding-top: 10px; margin-top: 10px; }
.gv-meta { font-size: 12px; color: var(--gray-500); }
.gv-arrow { font-size: 12px; color: var(--gray-500); }
.gd-body { padding: 4px 4px 12px; }
.gd-section { margin-bottom: 18px; }
.gd-section h3 { font-size: 14px; color: #1a365d; margin: 0 0 10px; font-weight: 600; }
.gd-pre { background: var(--gray-50); border: 1px solid var(--gray-150); border-radius: 8px; padding: 10px; font-size: 12px; white-space: pre-wrap; word-break: break-all; max-height: 240px; overflow: auto; margin: 0; }
.gd-kv { font-size: 13px; color: var(--gray-800); margin-bottom: 6px; }
.gd-preview { margin-top: 12px; }
.gd-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 10px 16px; }
</style>
