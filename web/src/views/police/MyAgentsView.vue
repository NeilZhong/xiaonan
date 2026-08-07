<script setup>
/**
 * ★ 我的数字警员（P4 前端重构）
 *
 * 展示当前用户全部绑定（GET /api/police/agent-connections/mine 富视图），
 * 每个绑定卡片支持：
 *   - 版本状态：跟随最新 / 钉住某版本，新版角标（源有更新版本且未跟随）
 *   - 套用最新（pin current_version_id）／ 回退到某版本（版本选择器）／ 跟随最新（unpin）
 *   - 偏好：昵称、新版通知开关（PATCH /{id}）
 */
import { computed, onMounted, ref } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { ArrowUp, GitBranch, Pin, RefreshCw, RotateCcw, Settings2, UserRound } from 'lucide-vue-next'

import { policeConnectionApi, policeAgentApi } from '@/apis/police_api'
import { resolveAgentAvatar } from '@/utils/policeAvatar'

const loading = ref(false)
const bindings = ref([])
const errorMsg = ref('')

// 每卡独立状态（版本列表 / 操作中）
const versionMap = ref({}) // connId -> { items, current_version_id, draft_version_id, release_mode }
const loadingVersions = ref({}) // connId -> bool
const busyAction = ref('') // `${connId}:${action}` 防重入

// 回退弹窗状态
const rollbackTarget = ref(null) // { conn, versions }
const rollbackVersionId = ref(null)
const rollbackOpen = computed(() => !!rollbackTarget.value)

// 昵称编辑状态
const editingPrefsId = ref(null)
const editNickname = ref('')
const editNotify = ref(true)
const savingPrefs = ref(false)

const hasBindings = computed(() => bindings.value.length > 0)

const versionInfoOf = (conn) => {
  const info = versionMap.value[conn.id]
  return info || { items: [], current_version_id: null, draft_version_id: null, release_mode: null }
}

/** 某绑定是否「有新版可套用」：源当前版本 ≠ 绑定钉住版本，且未跟随最新 */
const hasNewVersion = (conn) => {
  const info = versionInfoOf(conn)
  if (!info.current_version_id) return false
  if (!conn.pinned_version_id) return false
  return info.current_version_id !== conn.pinned_version_id
}

const runningLabel = (conn) => {
  if (conn.pinned_version_id) {
    const v = conn.pinned_version
    return v ? `已钉住 ${v.version_label || `#${v.id}`}` : `已钉住 #${conn.pinned_version_id}`
  }
  return '跟随最新'
}

const releaseModeText = (mode) => (mode === 'controlled' ? '受控发布' : '流动版本')

const isBusy = (connId, action) => busyAction.value === `${connId}:${action}`

async function loadVersionsFor(conn) {
  loadingVersions.value = { ...loadingVersions.value, [conn.id]: true }
  try {
    const res = await policeAgentApi.listVersions(conn.agent_id)
    versionMap.value = { ...versionMap.value, [conn.id]: res }
  } catch (e) {
    message.error(e.message || '加载版本失败')
  } finally {
    loadingVersions.value = { ...loadingVersions.value, [conn.id]: false }
  }
}

async function load() {
  loading.value = true
  errorMsg.value = ''
  try {
    const res = await policeConnectionApi.mine()
    bindings.value = (res.items || []).filter((b) => b.status === 'active' || !b.status)
    // 并行预取每个绑定的版本信息（用于角标判断与套用最新）
    await Promise.all(bindings.value.map((b) => loadVersionsFor(b)))
  } catch (e) {
    errorMsg.value = e.message || '加载失败'
    message.error(errorMsg.value)
  } finally {
    loading.value = false
  }
}

const runAction = async (conn, action, fn) => {
  if (busyAction.value) return
  busyAction.value = `${conn.id}:${action}`
  try {
    await fn()
    await load()
    message.success(action === 'pin' ? '已套用该版本' : action === 'unpin' ? '已恢复跟随最新' : '操作成功')
  } catch (e) {
    message.error(e.message || '操作失败')
  } finally {
    busyAction.value = ''
  }
}

/** 套用最新版本 */
const applyLatest = (conn) => {
  const info = versionInfoOf(conn)
  if (!info.current_version_id) {
    message.warning('暂无可套用的最新版本')
    return
  }
  runAction(conn, 'pin', () =>
    policeConnectionApi.pin(conn.id, info.current_version_id)
  )
}

/** 打开回退弹窗（列出全部历史版本） */
const openRollback = async (conn) => {
  await loadVersionsFor(conn)
  const info = versionInfoOf(conn)
  if (!info.items?.length) {
    message.info('该智能体暂无历史版本')
    return
  }
  rollbackTarget.value = conn
  rollbackVersionId.value = info.current_version_id || info.items[0]?.id || null
}

const confirmRollback = () => {
  const conn = rollbackTarget.value
  if (!conn || !rollbackVersionId.value) return
  runAction(conn, 'pin', () =>
    policeConnectionApi.pin(conn.id, rollbackVersionId.value)
  ).then(() => {
    rollbackTarget.value = null
  })
}

/** 跟随最新（取消钉住） */
const followLatest = (conn) => {
  Modal.confirm({
    title: '恢复跟随最新版本？',
    content: '取消钉住后，该数字警员将自动跟随源智能体的最新版本。',
    okText: '跟随最新',
    cancelText: '取消',
    async onOk() {
      await runAction(conn, 'unpin', () => policeConnectionApi.unpin(conn.id))
    }
  })
}

/** 移除绑定（外层已用 a-popconfirm 确认） */
const removeBinding = async (conn) => {
  try {
    await policeConnectionApi.remove(conn.id)
    message.success('已移除')
    await load()
  } catch (e) {
    message.error(e.message || '移除失败')
  }
}

// ── 偏好编辑 ──
const openPrefs = (conn) => {
  editingPrefsId.value = conn.id
  editNickname.value = conn.nickname || ''
  editNotify.value = conn.notify_new_version !== false
}

const savePrefs = async () => {
  const conn = bindings.value.find((b) => b.id === editingPrefsId.value)
  if (!conn) return
  savingPrefs.value = true
  try {
    await policeConnectionApi.setPrefs(conn.id, {
      nickname: editNickname.value.trim() || null,
      notify_new_version: editNotify.value
    })
    message.success('偏好已保存')
    editingPrefsId.value = null
    await load()
  } catch (e) {
    message.error(e.message || '保存失败')
  } finally {
    savingPrefs.value = false
  }
}

const displayName = (conn) => conn.nickname || conn.agent?.name || `数字警员 #${conn.agent_id}`
const displayAvatar = (conn) => resolveAgentAvatar(conn.agent) || ''
const initial = (name) => (name || '?').slice(0, 1).toUpperCase()

onMounted(load)
</script>

<template>
  <div class="my-agents">
    <!-- ===== 头部 ===== -->
    <header class="my-agents-header">
      <div class="my-agents-title-wrap">
        <h2 class="my-agents-title">我的数字警员</h2>
        <p class="my-agents-sub">从市场添加的数字警员都集中在这里，可随时套用新版本或回退到旧版本。</p>
      </div>
      <a-button class="lucide-icon-btn" :loading="loading" @click="load">
        <RefreshCw :size="14" :class="{ spinning: loading }" />
        刷新
      </a-button>
    </header>

    <!-- ===== 加载 / 空态 / 错误 ===== -->
    <div v-if="loading" class="my-agents-loading">
      <a-spin tip="加载绑定中..." />
    </div>

    <a-empty
      v-else-if="!hasBindings"
      :description="errorMsg || '还没有添加数字警员，去探索市场看看吧'"
      style="margin-top: 80px"
    >
      <template #image>
        <UserRound :size="48" style="color: var(--gray-300)" />
      </template>
      <a-button type="primary" @click="$router.push('/police/explore')">去探索市场</a-button>
    </a-empty>

    <!-- ===== 绑定卡片列表 ===== -->
    <div v-else class="my-agents-list">
      <div v-for="conn in bindings" :key="conn.id" class="binding-card">
        <div class="binding-avatar">
          <img v-if="displayAvatar(conn)" :src="displayAvatar(conn)" :alt="displayName(conn)" />
          <span v-else>{{ initial(displayName(conn)) }}</span>
        </div>

        <div class="binding-main">
          <div class="binding-head">
            <span class="binding-name" :title="displayName(conn)">{{ displayName(conn) }}</span>
            <span v-if="conn.nickname" class="binding-origin-name" :title="conn.agent?.name">
              原名：{{ conn.agent?.name }}
            </span>
            <a-tag v-if="conn.agent?.department" color="blue">{{ conn.agent.department }}</a-tag>
            <a-tag v-if="conn.agent?.is_subagent" color="purple">协助伙伴</a-tag>
          </div>

          <div class="binding-version-line">
            <span class="binding-version-label">
              <Pin v-if="conn.pinned_version_id" :size="12" />
              <GitBranch v-else :size="12" />
              {{ runningLabel(conn) }}
            </span>
            <span class="binding-release-mode">{{ releaseModeText(versionInfoOf(conn).release_mode) }}</span>
            <a-tag v-if="hasNewVersion(conn)" color="orange" class="new-version-badge">
              有新版本可套用
            </a-tag>
          </div>

          <div class="binding-meta">
            <span v-if="conn.associated_partners?.length">
              关联协助伙伴 {{ conn.associated_partners.length }} 个
            </span>
            <span v-else>无关联协助伙伴</span>
          </div>
        </div>

        <div class="binding-actions">
          <a-button
            size="small"
            type="primary"
            :loading="isBusy(conn.id, 'pin')"
            :disabled="!versionInfoOf(conn).current_version_id || !hasNewVersion(conn)"
            @click="applyLatest(conn)"
          >
            <ArrowUp :size="13" />
            套用最新
          </a-button>
          <a-button
            size="small"
            :loading="loadingVersions[conn.id]"
            @click="openRollback(conn)"
          >
            <RotateCcw :size="13" />
            回退版本
          </a-button>
          <a-button
            v-if="conn.pinned_version_id"
            size="small"
            :loading="isBusy(conn.id, 'unpin')"
            @click="followLatest(conn)"
          >
            跟随最新
          </a-button>
          <a-button size="small" class="binding-prefs-btn" @click="openPrefs(conn)">
            <Settings2 :size="13" />
          </a-button>
          <a-popconfirm
            title="确认移除该数字警员？"
            ok-text="移除"
            cancel-text="取消"
            ok-type="danger"
            @confirm="removeBinding(conn)"
          >
            <a-button size="small" type="text" danger>移除</a-button>
          </a-popconfirm>
        </div>

        <!-- 偏好编辑行（行内展开） -->
        <div v-if="editingPrefsId === conn.id" class="binding-prefs">
          <a-input
            v-model:value="editNickname"
            placeholder="自定义昵称（可选）"
            :maxlength="80"
            allow-clear
            class="binding-nickname-input"
          />
          <a-switch v-model:checked="editNotify" checked-children="新版通知开" un-checked-children="关" />
          <a-button type="primary" size="small" :loading="savingPrefs" @click="savePrefs">保存</a-button>
          <a-button size="small" @click="editingPrefsId = null">取消</a-button>
        </div>
      </div>
    </div>

    <!-- ===== 回退版本弹窗 ===== -->
    <a-modal
      v-model:open="rollbackOpen"
      title="回退到某个版本"
      :footer="null"
      width="520"
      @cancel="rollbackTarget = null"
    >
      <template v-if="rollbackTarget">
        <p class="rollback-desc">
          选择要套用的版本。套用后「{{ displayName(rollbackTarget) }}」将钉在该版本，直到你手动「跟随最新」。
        </p>
        <div class="rollback-list">
          <button
            v-for="v in versionInfoOf(rollbackTarget).items"
            :key="v.id"
            type="button"
            class="rollback-item"
            :class="{ active: rollbackVersionId === v.id }"
            @click="rollbackVersionId = v.id"
          >
            <span class="rollback-item-label">{{ v.version_label || `版本 #${v.id}` }}</span>
            <span class="rollback-item-meta">
              <a-tag v-if="v.status === 'published'" color="green">已发布</a-tag>
              <a-tag v-else-if="v.status === 'draft'" color="orange">草稿</a-tag>
              <a-tag v-else>{{ v.status }}</a-tag>
              {{ v.created_at || '' }}
            </span>
          </button>
        </div>
        <div class="rollback-footer">
          <a-button @click="rollbackTarget = null">取消</a-button>
          <a-button type="primary" :loading="isBusy(rollbackTarget.id, 'pin')" @click="confirmRollback">
            套用该版本
          </a-button>
        </div>
      </template>
    </a-modal>
  </div>
</template>

<style lang="less" scoped>
.my-agents {
  padding: 24px var(--page-padding) 48px;
  max-width: 1080px;
  margin: 0 auto;
  color: var(--gray-900);
}

.my-agents-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;

  .my-agents-title-wrap {
    min-width: 0;
  }

  .my-agents-title {
    margin: 0 0 6px;
    font-size: 22px;
    font-weight: 700;
    color: #1a365d;
    line-height: 1.25;
  }

  .my-agents-sub {
    margin: 0;
    color: var(--gray-600);
    font-size: 13px;
    line-height: 1.6;
  }
}

.my-agents-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 100px 0;
}

.my-agents-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.binding-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 18px 20px;
  border: 1px solid var(--gray-150);
  border-radius: 14px;
  background: #ffffff;
  box-shadow: 0 2px 10px rgba(16, 30, 54, 0.05);
  transition: box-shadow 0.16s ease;

  &:hover {
    box-shadow: 0 6px 18px rgba(16, 30, 54, 0.09);
  }
}

.binding-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 56px;
  height: 56px;
  border-radius: 14px;
  overflow: hidden;
  background: var(--main-30);
  color: var(--main-700);
  font-size: 20px;
  font-weight: 600;

  img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.binding-main {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  gap: 8px;
}

.binding-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;

  .binding-name {
    font-size: 15px;
    font-weight: 600;
    color: var(--gray-900);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .binding-origin-name {
    color: var(--gray-500);
    font-size: 12px;
  }
}

.binding-version-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;

  .binding-version-label {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    border-radius: 6px;
    background: var(--gray-25);
    color: var(--gray-700);
    font-size: 12px;
    font-weight: 500;
  }

  .binding-release-mode {
    color: var(--gray-500);
    font-size: 12px;
  }

  .new-version-badge {
    animation: badge-pulse 2s ease-in-out infinite;
  }
}

@keyframes badge-pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.75;
  }
}

.binding-meta {
  color: var(--gray-500);
  font-size: 12px;
}

.binding-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 6px;

  .binding-prefs-btn {
    color: var(--gray-600);
  }
}

.binding-prefs {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding-top: 12px;
  border-top: 1px dashed var(--gray-200);

  .binding-nickname-input {
    max-width: 260px;
  }
}

// ============ 回退弹窗 ============
.rollback-desc {
  color: var(--gray-600);
  font-size: 13px;
  line-height: 1.6;
  margin: 0 0 14px;
}

.rollback-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 320px;
  overflow-y: auto;
  margin-bottom: 16px;
}

.rollback-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  background: var(--gray-0);
  color: var(--gray-800);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition: all 0.16s ease;

  &:hover {
    border-color: var(--main-300);
    background: var(--main-30);
  }

  &.active {
    border-color: var(--main-500);
    background: var(--main-30);
    box-shadow: 0 0 0 2px var(--main-50);
  }

  .rollback-item-label {
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .rollback-item-meta {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--gray-500);
    font-size: 12px;
    flex-shrink: 0;
  }
}

.rollback-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
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
