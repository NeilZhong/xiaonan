<script setup>
/**
 * ★ 数字警员（智能体统一管理入口）
 *  - 智能体模块统一命名「数字警员」
 *  - 内置 / 市场中添加 / 自建的数字警员全部在此看到（卡片样式）
 *  - 协助伙伴以 tab 融合：数字警员 / 协助伙伴
 */
import { computed, ref, watch } from 'vue'

import PageHeader from '@/components/shared/PageHeader.vue'
import AgentManagePanel from '@/components/model-management/AgentManagePanel.vue'
import PartnerManageView from '@/views/police/PartnerManageView.vue'

const activeTab = ref('agents')
const agentPanelRef = ref(null)

const modelManageTabs = computed(() => [
  { key: 'agents', label: '数字警员' },
  { key: 'partners', label: '协助伙伴' },
])

const activeLoading = computed(() => (activeTab.value === 'agents' ? agentPanelRef.value?.loading || false : false))
const activeStats = computed(() => (activeTab.value === 'agents' ? agentPanelRef.value?.stats || {} : {}))

// 切换到数字警员面板时刷新数据
watch(activeTab, () => {
  if (activeTab.value === 'agents') {
    agentPanelRef.value?.refresh?.()
  }
})
</script>

<template>
  <div class="agent-manage-view">
    <PageHeader
      v-model:active-key="activeTab"
      title="数字警员"
      :tabs="modelManageTabs"
      :loading="activeLoading"
      :show-border="true"
      aria-label="数字警员管理视图切换"
    >
      <template #info>
        <div v-if="activeTab === 'agents'" class="summary-strip">
          <span>{{ activeStats.total || 0 }} 个智能体</span>
          <span v-if="activeStats.officers">{{ activeStats.officers }} 名数字警员</span>
          <span v-if="activeStats.builtin">{{ activeStats.builtin }} 个内置</span>
          <span>{{ activeStats.manageable || 0 }} 个可管理</span>
          <span>{{ activeStats.global || 0 }} 个全局</span>
        </div>
        <div v-else class="summary-strip">
          <span>协助伙伴 = 被数字警员挂载的专业能力（子智能体）</span>
        </div>
      </template>
    </PageHeader>

    <div class="agent-manage-content">
      <div v-show="activeTab === 'agents'" class="tab-panel">
        <AgentManagePanel ref="agentPanelRef" />
      </div>
      <div v-show="activeTab === 'partners'" class="tab-panel">
        <PartnerManageView />
      </div>
    </div>
  </div>
</template>

<style lang="less" scoped>
.agent-manage-view {
  display: flex;
  flex-direction: column;
  min-height: 100%;
  background: var(--gray-0);
  color: var(--gray-1000);
}

.agent-manage-content {
  flex: 1;
  min-height: 0;
  overflow: hidden;

  .tab-panel {
    height: 100%;
    min-height: 0;
    overflow-y: auto;
  }
}

.summary-strip {
  display: flex;
  gap: 8px;

  span {
    padding: 6px 10px;
    border: 1px solid var(--gray-100);
    border-radius: 7px;
    background: var(--gray-10);
    color: var(--gray-700);
    font-size: 12px;
    line-height: 18px;
  }

  .warning-count {
    background: var(--color-warning-50);
    border-color: var(--color-warning-100);
    color: var(--color-warning-700);
  }
}
</style>