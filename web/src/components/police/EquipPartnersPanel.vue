<script setup>
/**
 * 数字警员「装备伙伴」子面板（参考悟帆「装备伙伴」截图）
 * - 空间资产：已装备的协助伙伴（subagents 展开），带开关可卸载
 * - 天赋资产：当前空间可装备但未装备的候选协助伙伴，带开关可装备
 * - 权限：仅该警员的创建者或超管可交互开关
 */
import { ref, computed, onMounted, watch } from 'vue'
import { message, Empty } from 'ant-design-vue'
import { HelpCircle, Wrench } from 'lucide-vue-next'
import { policeEquipApi } from '@/apis/police_api'
import { useUserStore } from '@/stores/user'
import FallbackAvatar from '@/components/common/FallbackAvatar.vue'
import { getOfficerAvatar } from '@/utils/policeAvatar'

const props = defineProps({
  /** 数字警员对象（含 id、created_by） */
  agent: { type: Object, required: true }
})

const aEmptyImage = Empty.PRESENTED_IMAGE_SIMPLE

const userStore = useUserStore()

const equipped = ref([])
const available = ref([])
const loading = ref(false)
const activeTab = ref('all')
const keyword = ref('')

/** 当前用户是否可管理该警员的装备（创建者或超管） */
const canManage = computed(() => {
  if (!props.agent) return false
  const owner = props.agent.created_by
  return userStore.isSuperAdmin || (owner != null && String(owner) === String(userStore.uid))
})

const filterKeyword = (list) => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return list
  return list.filter((i) => (i.name || '').toLowerCase().includes(kw))
}

const filteredEquipped = computed(() => filterKeyword(equipped.value))
const filteredAvailable = computed(() => {
  let list = filterKeyword(available.value)
  if (activeTab.value === 'all') return list
  return list // available 只有未开启，无需二次过滤；tab 语义保留
})

async function load() {
  if (!props.agent?.id) return
  loading.value = true
  try {
    const [eq, av] = await Promise.all([
      policeEquipApi.listEquipped(props.agent.id),
      policeEquipApi.listAvailable(props.agent.id)
    ])
    equipped.value = eq.items || []
    available.value = av.items || []
  } catch (e) {
    message.error(e.message || '加载协助伙伴失败')
  } finally {
    loading.value = false
  }
}

async function toggleEquip(partner, targetOn) {
  if (!canManage.value) return
  try {
    if (targetOn) {
      await policeEquipApi.equip(props.agent.id, partner.id)
      message.success(`已装备「${partner.name}」`)
    } else {
      await policeEquipApi.unequip(props.agent.id, partner.id)
      message.success(`已卸载「${partner.name}」`)
    }
    await load()
  } catch (e) {
    message.error(e.message || '操作失败')
  }
}

onMounted(load)
watch(() => props.agent?.id, load)
</script>

<template>
  <div class="equip-partners">
    <div class="ep-hint">
      <HelpCircle :size="14" />
      <span>选择可与本数字警员协作的协助伙伴。协助伙伴被挂载后，数字警员可在办案中调用其专业能力。</span>
    </div>

    <div class="ep-toolbar">
      <a-input-search
        v-model:value="keyword"
        placeholder="搜索协助伙伴…"
        style="width: 240px"
        allow-clear
      />
      <a-tabs v-model:activeKey="activeTab" size="small">
        <a-tab-pane key="all" tab="全部" />
        <a-tab-pane key="available" tab="未开启" />
      </a-tabs>
    </div>

    <a-spin :spinning="loading">
      <!-- 空间资产：已装备 -->
      <div class="ep-section">
        <h4 class="ep-section-title">空间资产 <span class="ep-count">已装备 {{ equipped.length }}</span></h4>
        <div v-if="filteredEquipped.length" class="ep-list">
          <div v-for="p in filteredEquipped" :key="p.id" class="ep-item">
            <FallbackAvatar :src="p.icon" :defaultSrc="getOfficerAvatar(p.id || p.name)" :name="p.name" :seed="p.id" kind="agent" :size="36" shape="rounded" />
            <div class="ep-item-main">
              <div class="ep-item-name">{{ p.name }}</div>
              <div class="ep-item-desc">{{ p.description || '暂无描述' }}</div>
            </div>
            <a-switch
              :checked="true"
              :disabled="!canManage"
              size="small"
              @change="(v) => toggleEquip(p, v)"
            />
          </div>
        </div>
        <a-empty v-else :image="aEmptyImage" description="暂无已装备的协助伙伴" style="padding: 16px 0" />
      </div>

      <!-- 天赋资产：候选可装备 -->
      <div class="ep-section">
        <h4 class="ep-section-title">天赋资产 <span class="ep-count">可装备 {{ available.length }}</span></h4>
        <div v-if="filteredAvailable.length" class="ep-list">
          <div v-for="p in filteredAvailable" :key="p.id" class="ep-item">
            <FallbackAvatar :src="p.icon" :defaultSrc="getOfficerAvatar(p.id || p.name)" :name="p.name" :seed="p.id" kind="agent" :size="36" shape="rounded" />
            <div class="ep-item-main">
              <div class="ep-item-name">{{ p.name }}</div>
              <div class="ep-item-desc">{{ p.description || '暂无描述' }}</div>
            </div>
            <a-switch
              :checked="false"
              :disabled="!canManage"
              size="small"
              @change="(v) => toggleEquip(p, v)"
            />
          </div>
        </div>
        <a-empty v-else :image="aEmptyImage" description="暂无更多可装备的协助伙伴" style="padding: 16px 0">
          <template #description>
            <div class="ep-empty-tip">
              <Wrench :size="18" />
              <span>可先到「协助伙伴」页创建或申请共享的协助伙伴</span>
            </div>
          </template>
        </a-empty>
      </div>
    </a-spin>
  </div>
</template>

<style lang="less" scoped>
.equip-partners {
  padding: 4px 0;
}
.ep-hint {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  background: var(--gray-25);
  color: var(--gray-600);
  font-size: 12px;
  line-height: 1.6;
  svg {
    flex-shrink: 0;
    margin-top: 2px;
    color: var(--main-600);
  }
}
.ep-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}
.ep-section {
  margin-bottom: 16px;
}
.ep-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 8px 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-800);
}
.ep-count {
  font-size: 11px;
  font-weight: 400;
  color: var(--gray-500);
}
.ep-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ep-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--gray-150);
  border-radius: 10px;
  background: var(--gray-0);
  transition: border-color 0.16s ease;
  &:hover {
    border-color: var(--gray-300);
  }
}
.ep-item-main {
  flex: 1;
  min-width: 0;
}
.ep-item-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-900);
}
.ep-item-desc {
  font-size: 11px;
  color: var(--gray-500);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ep-empty-tip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--gray-500);
  font-size: 12px;
}
</style>
