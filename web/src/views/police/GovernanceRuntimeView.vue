<template>
  <div class="gov-view">
    <div class="gv-header">
      <div class="gv-title">
        <span class="gv-emoji">🎛️</span>
        <div>
          <h2>运行中心</h2>
          <p class="gv-sub">平台默认运行模式与全部智能体的在线状态、发布模式与绑定规模</p>
        </div>
      </div>
    </div>

    <!-- 平台默认运行模式 -->
    <a-card class="rc-mode-card" :bordered="false">
      <div class="rc-mode">
        <div>
          <div class="rc-mode-title">平台默认运行模式</div>
          <div class="rc-mode-sub">仅影响此后新建智能体的初始发布状态；已存在智能体不受影响</div>
        </div>
        <a-segmented v-model:value="defaultMode" :options="modeOptions" @change="saveDefaultMode" />
      </div>
    </a-card>

    <!-- 总览表格 -->
    <a-spin :spinning="loading">
      <a-table
        :columns="columns"
        :data-source="items"
        :pagination="false"
        row-key="id"
        class="rc-table"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'type'">
            <a-tag :color="record.is_system ? 'default' : record.is_subagent ? 'purple' : 'blue'">
              {{ record.is_system ? '系统内置' : record.is_subagent ? '协助伙伴' : '数字警员' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-badge :status="isOnline(record) ? 'success' : 'default'" :text="isOnline(record) ? '在线' : '下线'" />
          </template>
          <template v-else-if="column.key === 'release_mode'">
            <a-tag :color="record.release_mode === 'rolling' ? 'green' : 'orange'">
              {{ record.release_mode === 'rolling' ? '流动发布' : '受控发布' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'draft_pending'">
            <a-tag v-if="record.draft_pending" color="orange">草稿待发布</a-tag>
            <span v-else class="rc-muted">—</span>
          </template>
          <template v-else-if="column.key === 'badge_number'">
            {{ record.badge_number || '—' }}
          </template>
          <template v-else-if="column.key === 'action'">
            <a-button
              v-if="!record.is_system"
              size="small"
              :loading="switchingId === record.id"
              @click="switchMode(record)"
            >
              {{ record.release_mode === 'rolling' ? '切为受控' : '切为流动' }}
            </a-button>
            <span v-else class="rc-muted">系统内置</span>
          </template>
        </template>
      </a-table>
      <div class="rc-pager" v-if="total > pageSize">
        <a-pagination
          v-model:current="page"
          :total="total"
          :page-size="pageSize"
          show-less-items
          @change="load"
        />
      </div>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { policeGovernanceApi, policeAgentApi } from '@/apis/police_api'

const items = ref([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const defaultMode = ref('controlled')
const switchingId = ref(null)

const modeOptions = [
  { label: '受控发布', value: 'controlled' },
  { label: '流动发布', value: 'rolling' },
]

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '工号', dataIndex: 'badge_number', key: 'badge_number' },
  { title: '类型', key: 'type' },
  { title: '状态', key: 'status' },
  { title: '运行模式', key: 'release_mode' },
  { title: '草稿待发布', key: 'draft_pending' },
  { title: '绑定数', dataIndex: 'binding_count', key: 'binding_count' },
  { title: '操作', key: 'action' },
]

const isOnline = (r) => r.status === 'active' || r.status === 'online'

async function load() {
  loading.value = true
  try {
    const res = await policeGovernanceApi.runtimeOverview({ page: page.value, page_size: pageSize.value })
    items.value = res.items || []
    total.value = res.total || 0
    if (res.default_release_mode) defaultMode.value = res.default_release_mode
  } catch (e) {
    message.error('加载运行总览失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

async function saveDefaultMode(mode) {
  try {
    await policeGovernanceApi.setRuntimeConfig(mode)
    message.success('平台默认运行模式已更新为：' + (mode === 'rolling' ? '流动发布' : '受控发布'))
  } catch (e) {
    message.error('保存失败: ' + (e.message || e))
    load() // 回滚显示
  }
}

async function switchMode(record) {
  const target = record.release_mode === 'rolling' ? 'controlled' : 'rolling'
  switchingId.value = record.id
  try {
    await policeAgentApi.switchReleaseMode(record.id, target)
    message.success(`已切换为${target === 'rolling' ? '流动发布' : '受控发布'}`)
    load()
  } catch (e) {
    message.error('切换失败: ' + (e.message || e))
  } finally {
    switchingId.value = null
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
.rc-mode-card { border-radius: 14px; box-shadow: 0 4px 16px rgba(16,30,54,0.06); border: 1px solid var(--gray-150); margin-bottom: 18px; }
.rc-mode { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.rc-mode-title { font-size: 15px; font-weight: 600; color: #1a365d; }
.rc-mode-sub { font-size: 12px; color: var(--gray-500); margin-top: 2px; }
.rc-table { background: #fff; border-radius: 14px; padding: 8px 12px; box-shadow: 0 4px 16px rgba(16,30,54,0.06); border: 1px solid var(--gray-150); }
.rc-pager { display: flex; justify-content: flex-end; margin-top: 14px; }
.rc-muted { color: var(--gray-400); }
</style>
