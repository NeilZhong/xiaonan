<script setup>
/**
 * 协助伙伴（子智能体）管理页
 * - 独立入口（/police/partners），与数字警员列表平级
 * - 权限边界：编辑/删除/分享仅创建者本人或超管可见；非创建者只显示查看
 */
import { ref, reactive, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { Plus, Handshake, Users, ShieldCheck } from 'lucide-vue-next'
import { policePartnerApi } from '@/apis/police_api'
import { useUserStore } from '@/stores/user'
import FallbackAvatar from '@/components/common/FallbackAvatar.vue'
import { getOfficerAvatar } from '@/utils/policeAvatar'
import ShareConfigForm from '@/components/ShareConfigForm.vue'
import PartnerEditDrawer from '@/components/police/PartnerEditDrawer.vue'

const userStore = useUserStore()

const loading = ref(false)
const partners = ref([])
const total = ref(0)
const keyword = ref('')
const activeStatus = ref('all')

const editDrawerOpen = ref(false)
const editingPartner = ref(null)
const shareDrawerOpen = ref(false)
const shareTarget = ref(null)
const shareConfig = reactive({ access_level: 'user', department_ids: [], user_uids: [] })

const tabs = [
  { key: 'all', label: '全部' },
  { key: 'mine', label: '我创建的' }
]

const canManage = (p) => {
  const isOwner = String(p.created_by) === String(userStore.uid)
  return isOwner || userStore.isSuperAdmin
}

const statusTag = (p) => {
  const scope = p.share_config?.access_level
  if (scope === 'global') {
    return p.approval_status === 'approved'
      ? { text: '全局·已审批', color: 'green' }
      : p.approval_status === 'pending'
        ? { text: '全局·待审批', color: 'orange' }
        : { text: '全局·被驳回', color: 'red' }
  }
  if (scope === 'department') return { text: '部门共享', color: 'blue' }
  if (scope === 'user') return { text: '指定人', color: 'default' }
  return { text: '仅自己', color: 'default' }
}

async function load() {
  loading.value = true
  try {
    const res = await policePartnerApi.list({
      keyword: keyword.value || undefined,
      status: activeStatus.value === 'mine' ? 'mine' : undefined
    })
    partners.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    message.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingPartner.value = null
  editDrawerOpen.value = true
}
function openEdit(p) {
  editingPartner.value = p
  editDrawerOpen.value = true
}
async function onSaved() {
  await load()
}

function openShare(p) {
  shareTarget.value = p
  const sc = p.share_config || {}
  shareConfig.access_level = sc.access_level === 'global' ? 'global' : sc.access_level === 'department' ? 'department' : 'user'
  shareConfig.department_ids = sc.department_ids || []
  shareConfig.user_uids = sc.user_uids || []
  shareDrawerOpen.value = true
}
async function handleShare() {
  if (!shareTarget.value) return
  try {
    await policePartnerApi.share(shareTarget.value.id, {
      scope: shareConfig.access_level,
      department_ids: shareConfig.department_ids,
      user_uids: shareConfig.user_uids
    })
    message.success('共享设置已保存')
    shareDrawerOpen.value = false
    await load()
  } catch (e) {
    message.error(e.message || '共享设置失败')
  }
}

function handleDelete(p) {
  Modal.confirm({
    title: `删除协助伙伴「${p.name}」`,
    content: '删除后不可恢复；若仍有数字警员挂载该协助伙伴，将被拒绝删除。',
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      try {
        await policePartnerApi.remove(p.id)
        message.success('已删除')
        await load()
      } catch (e) {
        message.error(e.message || '删除失败')
      }
    }
  })
}

onMounted(load)
</script>

<template>
  <div class="partner-manage">
    <!-- 页头 -->
    <div class="pm-header">
      <div class="pm-title-row">
        <div class="pm-title">
          <Handshake :size="18" />
          <h2>协助伙伴</h2>
          <span class="pm-sub">被数字警员挂载的专业能力（子智能体）</span>
        </div>
        <a-button type="primary" @click="openCreate">
          <Plus :size="14" />
          新建协助伙伴
        </a-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="pm-toolbar">
      <a-input-search
        v-model:value="keyword"
        placeholder="搜索协助伙伴名称…"
        style="width: 280px"
        @search="load"
      />
      <a-tabs v-model:activeKey="activeStatus" size="small" @change="load">
        <a-tab-pane v-for="t in tabs" :key="t.key" :tab="t.label" />
      </a-tabs>
    </div>

    <!-- 列表 -->
    <a-spin :spinning="loading">
      <div v-if="partners.length" class="pm-grid">
        <div v-for="p in partners" :key="p.id" class="pm-card">
          <div class="pm-card-head">
            <FallbackAvatar
              :src="p.icon"
              :defaultSrc="getOfficerAvatar(p.id || p.slug || p.name)"
              :name="p.name"
              :seed="p.id || p.slug"
              kind="agent"
              :size="44"
              shape="rounded"
            />
            <div class="pm-card-title">
              <div class="pm-card-name">{{ p.name }}</div>
              <div class="pm-card-meta">
                <a-tag :color="statusTag(p).color" style="margin-right: 4px">{{ statusTag(p).text }}</a-tag>
                <span v-if="p.category" class="pm-cat">{{ p.category }}</span>
              </div>
            </div>
          </div>
          <div class="pm-card-desc">{{ p.description || '暂无描述' }}</div>
          <div class="pm-card-foot">
            <span class="pm-card-time">
              <ShieldCheck :size="12" /> 创建于 {{ (p.created_at || '').substring(0, 10) }}
            </span>
            <div class="pm-card-actions">
              <a-button v-if="canManage(p)" size="small" @click="openEdit(p)">编辑</a-button>
              <a-button v-if="canManage(p)" size="small" @click="openShare(p)">共享</a-button>
              <a-button v-if="canManage(p)" size="small" danger @click="handleDelete(p)">删除</a-button>
            </div>
          </div>
        </div>
      </div>
      <a-empty v-else description="暂无协助伙伴" style="padding: 48px 0">
        <template #description>
          <div class="pm-empty">
            <Users :size="28" />
            <p>还没有协助伙伴，创建第一个专业能力吧</p>
          </div>
        </template>
        <a-button type="primary" @click="openCreate">
          <Plus :size="14" /> 新建协助伙伴
        </a-button>
      </a-empty>
    </a-spin>

    <!-- 创建/编辑抽屉 -->
    <PartnerEditDrawer
      v-model:open="editDrawerOpen"
      :partner="editingPartner"
      @saved="onSaved"
    />

    <!-- 共享范围抽屉 -->
    <a-drawer
      :open="shareDrawerOpen"
      title="共享协助伙伴"
      :width="420"
      @update:open="(v) => (shareDrawerOpen = v)"
    >
      <ShareConfigForm v-model="shareConfig" :auto-select-user-dept="true" />
      <a-alert
        v-if="shareConfig.access_level === 'global'"
        type="warning"
        show-icon
        message="全局共享需超级管理员审核通过后，对所有用户可见。"
        style="margin-top: 12px"
      />
      <template #footer>
        <div style="display: flex; justify-content: flex-end; gap: 8px">
          <a-button @click="shareDrawerOpen = false">取消</a-button>
          <a-button type="primary" @click="handleShare">保存</a-button>
        </div>
      </template>
    </a-drawer>
  </div>
</template>

<style lang="less" scoped>
.partner-manage {
  padding: 20px 24px;
  max-width: 1280px;
  margin: 0 auto;
}
.pm-header {
  margin-bottom: 16px;
}
.pm-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.pm-title {
  display: flex;
  align-items: center;
  gap: 8px;
  h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: var(--gray-900);
  }
  svg {
    color: var(--main-600);
  }
}
.pm-sub {
  color: var(--gray-500);
  font-size: 12px;
}
.pm-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}
.pm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
}
.pm-card {
  padding: 16px;
  border: 1px solid var(--gray-150);
  border-radius: 12px;
  background: var(--gray-0);
  transition: box-shadow 0.16s ease, border-color 0.16s ease;
  &:hover {
    border-color: var(--gray-300);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  }
}
.pm-card-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}
.pm-card-title {
  min-width: 0;
}
.pm-card-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--gray-900);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pm-card-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
}
.pm-cat {
  font-size: 11px;
  color: var(--gray-500);
}
.pm-card-desc {
  min-height: 40px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--gray-600);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.pm-card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--gray-100);
}
.pm-card-time {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--gray-500);
}
.pm-card-actions {
  display: flex;
  gap: 6px;
}
.pm-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--gray-500);
  p {
    margin: 0;
  }
}
</style>
