<script setup>
import { ref, onMounted, onBeforeUnmount, computed, provide, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import {
  Activity,
  BarChart3,
  ClipboardList,
  LibraryBig,
  Box,
  FolderKanban,
  PanelLeftClose,
  PanelLeftOpen,
  MessageCirclePlus,
  MessageSquare,
  Search,
  Shield,
  Briefcase,
  SlidersHorizontal,
  Handshake,
  Store,
  ShieldCheck,
  Gauge
} from 'lucide-vue-next'
import { CheckSquareOutlined } from '@ant-design/icons-vue'

import { useConfigStore } from '@/stores/config'
import { useAgentStore } from '@/stores/agent'
import { useChatThreadsStore } from '@/stores/chatThreads'
import { useDatabaseStore } from '@/stores/database'
import { useInfoStore } from '@/stores/info'
import { useTaskerStore } from '@/stores/tasker'
import { usePoliceStore } from '@/stores/police'
import { useUserStore } from '@/stores/user'
import { storeToRefs } from 'pinia'
import UserInfoComponent from '@/components/UserInfoComponent.vue'
import DebugComponent from '@/components/DebugComponent.vue'
import TaskCenterDrawer from '@/components/TaskCenterDrawer.vue'
import SettingsModal from '@/components/SettingsModal.vue'
import ConversationNavSection from '@/components/ConversationNavSection.vue'
import ConversationSearchModal from '@/components/ConversationSearchModal.vue'

const configStore = useConfigStore()
const agentStore = useAgentStore()
const chatThreadsStore = useChatThreadsStore()
const databaseStore = useDatabaseStore()
const infoStore = useInfoStore()
const taskerStore = useTaskerStore()
const policeStore = usePoliceStore()
const userStore = useUserStore()
const { activeCount: activeCountRef, isDrawerOpen } = storeToRefs(taskerStore)
const { threads, currentThreadId, hasMoreThreads, isLoadingMoreThreads } =
  storeToRefs(chatThreadsStore)

// 三态侧边栏（同款悟帆）：
//  桌面端常驻，分 展开(240px) / 收起(56px 纯图标栏) 两态
//  窄屏完全隐藏，汉堡展开为 240px 浮层
const isExpanded = ref(typeof window !== 'undefined' ? window.innerWidth >= 900 : true)
const isMobileOpen = ref(false)
const isMobile = ref(typeof window !== 'undefined' ? window.innerWidth < 900 : false)

// 桌面：展开 / 收起
const expandSidebar = () => {
  isExpanded.value = true
}
const collapseSidebar = () => {
  isExpanded.value = false
}
// 窄屏浮层：打开 / 关闭
const openMobileSidebar = () => {
  isMobileOpen.value = true
}
const closeMobileSidebar = () => {
  isMobileOpen.value = false
}

// 派生显示状态
const showWideSidebar = computed(
  () => (isMobile.value && isMobileOpen.value) || (!isMobile.value && isExpanded.value)
)
const showNarrowSidebar = computed(() => !isMobile.value && !isExpanded.value)
const showHamburger = computed(() => isMobile.value && !isMobileOpen.value)
const showBackdrop = computed(() => isMobile.value && isMobileOpen.value)

// 点击导航项：窄屏浮层下关闭浮层；桌面无副作用
const onNavClick = () => {
  if (isMobile.value) {
    isMobileOpen.value = false
  }
}
// 窄栏历史/通知等图标：桌面展开宽栏；窄屏浮层下关闭
const openWideFromNarrow = () => {
  if (isMobile.value) {
    isMobileOpen.value = false
  } else {
    isExpanded.value = true
  }
}

const mobileMq = typeof window !== 'undefined' ? window.matchMedia('(max-width: 900px)') : null
const onMqChange = (e) => {
  isMobile.value = e.matches
  // 跨断点：进入窄屏则收起浮层；宽屏保留用户展开/收起偏好
  if (e.matches) {
    isMobileOpen.value = false
  }
}
onMounted(() => {
  mobileMq?.addEventListener?.('change', onMqChange)
})
onBeforeUnmount(() => {
  mobileMq?.removeEventListener?.('change', onMqChange)
})

// Add state for debug modal
const showDebugModal = ref(false)

// Add state for settings modal
const showSettingsModal = ref(false)
const settingsInitialTab = ref('')

const conversationSearchOpen = ref(false)

// Provide settings modal methods to child components
const openSettingsModal = (tab) => {
  settingsInitialTab.value = tab || (userStore.isAdmin ? 'base' : 'account')
  showSettingsModal.value = true
}

// Handle debug modal close
const handleDebugModalClose = () => {
  showDebugModal.value = false
}

const getRemoteConfig = async () => {
  try {
    await configStore.refreshConfig()
  } catch (error) {
    console.warn('加载系统配置失败:', error)
  }
}

const getRemoteDatabase = async () => {
  try {
    await databaseStore.loadDatabases()
  } catch (error) {
    console.warn('加载知识库列表失败:', error)
  }
}

onMounted(async () => {
  // 加载信息配置与知识库数据无依赖，可并行
  await Promise.all([infoStore.loadInfoConfig(), getRemoteDatabase()])
  await initAgentNavigation()
  await getRemoteConfig()
  // 仅管理员加载任务中心数据
  if (userStore.isAdmin) {
    taskerStore.loadTasks()
  }
  // 加载工作台统计（我的待办 / 待审核），用于侧边栏红色数字指示器
  policeStore.loadStats()
})

const route = useRoute()
const router = useRouter()

const activeTaskCount = computed(() => activeCountRef.value || 0)

// 工作台红点指示器：我的待办任务(my_pending_count) + 待审核事项(review_count)
const workbenchBadge = computed(
  () => (policeStore.stats?.my_pending_count || 0) + (policeStore.stats?.review_count || 0)
)
const activeConversationThreadId = computed(() => {
  return route.path.startsWith('/agent') ? currentThreadId.value : null
})
const organizationName = computed(() => {
  return infoStore.organization.name || infoStore.branding.name || 'Xiaonan'
})

// 下面是导航菜单部分，添加智能体项
const mainList = computed(() => {
  const items = [
    {
      name: '新建对话',
      path: '/agent',
      icon: MessageCirclePlus,
      activeIcon: MessageCirclePlus,
      action: true,
      exactActive: true
    }
  ]

  // ★ 公安业务导航
  items.push({
    name: '工作台',
    path: '/police',
    icon: Shield,
    activeIcon: Shield,
    exactActive: true
  })

  items.push({
    name: '案件管理',
    path: '/police/cases',
    icon: Briefcase,
    activeIcon: Briefcase,
    activePaths: ['/police/cases']
  })

  if (userStore.isAdmin) {
    items.push({
      name: '任务模板',
      path: '/police/task-templates',
      icon: SlidersHorizontal,
      activeIcon: SlidersHorizontal,
      activePaths: ['/police/task-templates']
    })
  }

  items.push({
    name: '智能体',
    path: '/agent-manage',
    icon: Box,
    activeIcon: Box,
    activePaths: ['/agent-manage']
  })

  items.push({
    name: '协助伙伴',
    path: '/police/partners',
    icon: Handshake,
    activeIcon: Handshake,
    activePaths: ['/police/partners']
  })

  items.push({
    name: '探索市场',
    path: '/police/explore',
    icon: Store,
    activeIcon: Store,
    activePaths: ['/police/explore']
  })

  items.push({
    name: '办案复盘',
    path: '/police/reflections',
    icon: ClipboardList,
    activeIcon: ClipboardList,
    activePaths: ['/police/reflections']
  })

  items.push({
    name: '工作区',
    path: '/workspace',
    icon: FolderKanban,
    activeIcon: FolderKanban
  })

  items.push({
    name: '知识库 · 技能',
    path: '/extensions',
    activePaths: ['/extensions'],
    icon: LibraryBig,
    activeIcon: LibraryBig
  })

  if (userStore.isSuperAdmin) {
    items.push({
      name: '数据总览',
      path: '/dashboard',
      icon: BarChart3,
      activeIcon: BarChart3
    })
    items.push({
      name: '审核台',
      path: '/police/governance/review',
      icon: ShieldCheck,
      activeIcon: ShieldCheck,
      activePaths: ['/police/governance/review']
    })
    items.push({
      name: '运行中心',
      path: '/police/governance/runtime',
      icon: Gauge,
      activeIcon: Gauge,
      activePaths: ['/police/governance/runtime']
    })
  }

  // ★ 管理员专属入口：仅系统管理员可见，普通用户不可见（v2.1 §9.2）
  if (userStore.isAdmin) {
    items.push({
      name: '运行时控制台',
      path: '/police/runtime-console',
      icon: Activity,
      activeIcon: Activity,
      activePaths: ['/police/runtime-console']
    })
  }

  return items
})

const primaryNavItem = computed(() => mainList.value[0] || null)
const secondaryNavItems = computed(() => mainList.value.slice(1))

const isNavItemActive = (item) => {
  const activePaths = item.activePaths || [item.path]
  if (item.exactActive) {
    return activePaths.some((path) => route.path === path)
  }
  return activePaths.some((path) => route.path === path || route.path.startsWith(`${path}/`))
}

const openConversationSearch = () => {
  conversationSearchOpen.value = true
}

const initAgentNavigation = async () => {
  try {
    if (!agentStore.isInitialized) {
      await agentStore.initialize()
    }
    await chatThreadsStore.loadThreads()
  } catch (error) {
    console.warn('加载对话导航失败:', error)
  }
}

const handleSelectChat = (threadId) => {
  if (!threadId) return
  chatThreadsStore.setCurrentThreadId(threadId)
  router.push({ name: 'AgentCompWithThreadId', params: { thread_id: threadId } })
}

const handleSearchThreadFound = (thread) => {
  chatThreadsStore.upsertThread(thread)
}

const handleSearchSelectThread = (thread) => {
  if (!thread?.id) return
  chatThreadsStore.upsertThread(thread)
  handleSelectChat(thread.id)
}

const handleCreateConversationFromSearch = () => {
  chatThreadsStore.setCurrentThreadId(null)
  router.push({ name: 'AgentComp' })
}

const handleDeleteChat = async (threadId) => {
  if (!threadId) return
  try {
    await chatThreadsStore.deleteThread(threadId)
    if (route.params.thread_id === threadId) {
      await router.replace({ name: 'AgentComp' })
    }
  } catch (error) {
    console.warn('删除对话失败:', error)
  }
}

const handleRenameChat = async ({ chatId, title }) => {
  try {
    await chatThreadsStore.updateThread(chatId, title)
  } catch (error) {
    console.warn('重命名对话失败:', error)
  }
}

const handleTogglePinChat = async (threadId) => {
  const thread = threads.value.find((item) => item.id === threadId)
  if (!thread) return
  try {
    await chatThreadsStore.updateThread(threadId, null, !thread.is_pinned)
    await chatThreadsStore.loadThreads()
    if (currentThreadId.value) {
      chatThreadsStore.setCurrentThreadId(currentThreadId.value)
    }
  } catch (error) {
    console.warn('更新置顶状态失败:', error)
  }
}

watch(
  () => [route.path, route.params.thread_id],
  () => {
    if (!route.path.startsWith('/agent')) return
    const threadId = typeof route.params.thread_id === 'string' ? route.params.thread_id : null
    chatThreadsStore.setCurrentThreadId(threadId)
  },
  { immediate: true }
)

// Provide settings modal methods to child components
provide('settingsModal', {
  openSettingsModal
})
</script>

<template>
  <div class="app-layout" :class="{ 'is-mobile': isMobile, 'is-collapsed': !isExpanded && !isMobile }">
    <!-- 窄屏遮罩：侧边栏浮层展开时点击关闭 -->
    <div
      v-if="showBackdrop"
      class="xn-sidebar-backdrop"
      @click="closeMobileSidebar"
    ></div>

    <!-- 同款悟帆 cvo-sidebar：fixed 浮层 + 毛玻璃圆角（桌面常驻 / 窄屏浮层） -->
    <aside
      v-show="showWideSidebar"
      class="xn-sidebar"
      data-cvo-id="cvo-sidebar"
    >
      <div class="xn-sidebar-inner" data-cvo-id="cvo-sidebar-inner">
        <!-- 顶部品牌栏 -->
        <div class="xn-sb-header">
          <router-link to="/" class="xn-brand" @click="onNavClick">
            <img :src="infoStore.organization.avatar" class="xn-brand-avatar" />
            <span class="xn-brand-name">{{ organizationName }}</span>
          </router-link>
          <button
            type="button"
            class="xn-sb-collapse"
            aria-label="收起侧边栏"
            title="收起侧边栏"
            @click="collapseSidebar"
          >
            <PanelLeftClose :size="18" />
          </button>
        </div>
        <div class="xn-sb-spacer"></div>

        <!-- 主导航 -->
        <nav class="xn-primary-nav">
          <RouterLink
            v-if="primaryNavItem"
            :to="primaryNavItem.path"
            class="xn-nav-entry xn-nav-new"
            :class="{ active: isNavItemActive(primaryNavItem) }"
            :active-class="''"
            @click="onNavClick"
          >
            <span class="xn-nav-icon">
              <component
                :is="isNavItemActive(primaryNavItem) ? primaryNavItem.activeIcon : primaryNavItem.icon"
                :size="16"
              />
            </span>
            <span class="xn-nav-text">{{ primaryNavItem.name }}</span>
          </RouterLink>

          <RouterLink
            v-for="(item, index) in secondaryNavItems"
            :key="index"
            :to="item.path"
            v-show="!item.hidden"
            class="xn-nav-entry"
            :class="{ active: isNavItemActive(item) }"
            :active-class="''"
            @click="onNavClick"
          >
            <span class="xn-nav-icon">
              <component
                :is="isNavItemActive(item) ? item.activeIcon : item.icon"
                :size="16"
              />
            </span>
            <span class="xn-nav-text">{{ item.name }}</span>
            <span
              v-if="item.path === '/police' && workbenchBadge > 0"
              class="xn-nav-badge"
            >{{ workbenchBadge > 99 ? '99+' : workbenchBadge }}</span>
          </RouterLink>
        </nav>

        <div class="xn-divider"></div>

        <!-- 对话历史区 -->
        <section class="xn-history">
          <div class="xn-history-header">
            <h2 class="xn-history-title">对话</h2>
            <button
              type="button"
              class="xn-history-action"
              aria-label="搜索对话"
              title="搜索对话"
              @click="openConversationSearch"
            >
              <Search :size="14" />
            </button>
          </div>
          <div class="xn-history-scroll">
            <ConversationNavSection
              :current-chat-id="activeConversationThreadId"
              :chats-list="threads"
              :has-more-chats="hasMoreThreads"
              :is-loading-more="isLoadingMoreThreads"
              @select-chat="handleSelectChat"
              @delete-chat="handleDeleteChat"
              @rename-chat="handleRenameChat"
              @toggle-pin="handleTogglePinChat"
              @load-more-chats="() => chatThreadsStore.loadMoreThreads()"
            />
          </div>
        </section>

        <!-- 底部用户区 -->
        <div class="xn-footer">
          <UserInfoComponent :show-role="true">
            <template v-if="userStore.isAdmin" #actions>
              <button
                class="xn-user-task-center"
                :class="{ active: isDrawerOpen }"
                type="button"
                aria-label="任务中心"
                @click.stop="taskerStore.openDrawer()"
              >
                <a-badge
                  :count="activeTaskCount"
                  :overflow-count="99"
                  size="small"
                >
                  <ClipboardList :size="16" />
                </a-badge>
              </button>
            </template>
          </UserInfoComponent>
        </div>
      </div>
    </aside>

    <!-- 窄栏（56px 纯图标栏）：桌面收起态常驻显示，同款悟帆 cvo-sidebar-collapsed -->
    <aside
      v-show="showNarrowSidebar"
      class="xn-sidebar-narrow"
      data-cvo-id="cvo-sidebar-collapsed"
    >
      <div class="xn-narrow-inner">
        <button
          type="button"
          class="xn-narrow-logo"
          title="展开侧边栏"
          aria-label="展开侧边栏"
          @click="expandSidebar"
        >
          <img :src="infoStore.organization.avatar" class="xn-narrow-brand-img" />
        </button>
        <div class="xn-narrow-spacer"></div>

        <RouterLink
          v-if="primaryNavItem"
          :to="primaryNavItem.path"
          class="xn-narrow-btn xn-narrow-new"
          :class="{ active: isNavItemActive(primaryNavItem) }"
          :active-class="''"
          :title="primaryNavItem.name"
          @click="onNavClick"
        >
          <component
            :is="isNavItemActive(primaryNavItem) ? primaryNavItem.activeIcon : primaryNavItem.icon"
            :size="18"
          />
        </RouterLink>

        <RouterLink
          v-for="(item, index) in secondaryNavItems"
          :key="index"
          :to="item.path"
          v-show="!item.hidden"
          class="xn-narrow-btn"
          :class="{ active: isNavItemActive(item) }"
          :active-class="''"
          :title="item.name"
          @click="onNavClick"
        >
          <component
            :is="isNavItemActive(item) ? item.activeIcon : item.icon"
            :size="18"
          />
          <span
            v-if="item.path === '/police' && workbenchBadge > 0"
            class="xn-narrow-nav-dot"
          ></span>
        </RouterLink>

        <div class="xn-narrow-divider"></div>

        <button
          type="button"
          class="xn-narrow-btn"
          title="对话历史"
          aria-label="对话历史"
          @click="openWideFromNarrow"
        >
          <MessageSquare :size="16" />
        </button>

        <div class="xn-narrow-flex"></div>

        <div class="xn-narrow-spacer"></div>
        <button
          type="button"
          class="xn-narrow-avatar"
          title="账户设置"
          aria-label="账户设置"
          @click="openSettingsModal('account')"
        >
          {{ (userStore.username || '?').charAt(0).toUpperCase() }}
        </button>
      </div>
    </aside>

    <!-- 汉堡按钮：窄屏完全隐藏侧边栏时显示，用于弹出浮层 -->
    <button
      v-if="showHamburger"
      type="button"
      class="xn-hamburger"
      aria-label="打开侧边栏"
      @click="openMobileSidebar"
    >
      <PanelLeftOpen :size="18" />
    </button>

    <div id="app-router-view">
      <router-view v-slot="{ Component, route }">
        <keep-alive v-if="route.meta.keepAlive !== false">
          <component :is="Component" />
        </keep-alive>
        <component :is="Component" v-else />
      </router-view>
    </div>

    <ConversationSearchModal
      v-model:open="conversationSearchOpen"
      :recent-threads="threads"
      @select-thread="handleSearchSelectThread"
      @create-thread="handleCreateConversationFromSearch"
      @thread-found="handleSearchThreadFound"
    />

    <!-- Debug Modal -->
    <a-modal
      v-model:open="showDebugModal"
      title="调试面板"
      width="90%"
      :footer="null"
      @cancel="handleDebugModalClose"
      :maskClosable="true"
      :destroyOnClose="true"
      class="debug-modal"
    >
      <DebugComponent />
    </a-modal>
    <TaskCenterDrawer v-if="userStore.isAdmin" />
    <SettingsModal
      v-model:visible="showSettingsModal"
      :initial-tab="settingsInitialTab"
      @close="() => (showSettingsModal = false)"
    />
  </div>
</template>

<style lang="less" scoped>
// ===== 同款悟帆侧边栏主题变量（映射小南浅/深主题）=====
.app-layout {
  // 侧边栏宽度（与悟帆宽栏一致：240px，外层即卡片，无额外背板）
  --xn-sidebar-w: 240px;
  // 收起态窄栏宽度（同款悟帆 56px 纯图标栏）
  --xn-sidebar-collapsed-w: 56px;
  // 侧边栏浮起间距：卡片与视口上/左/下边缘的留白，越大悬浮感越强
  --xn-sidebar-gap: 14px;

  // 浅色主题（默认）
  --xn-sidebar-bg: rgba(255, 255, 255, 0.82);
  --xn-sidebar-border: rgba(15, 23, 42, 0.08);
  --xn-sidebar-shadow: 0 14px 34px rgba(15, 23, 42, 0.16), 0 2px 8px rgba(15, 23, 42, 0.06);
  --xn-sidebar-blur: 14px;
  --xn-text-primary: var(--gray-1000);
  --xn-text-secondary: var(--gray-700);
  --xn-text-muted: var(--gray-500);
  --xn-nav-active-bg: color-mix(in srgb, var(--main-color) 8%, #ffffff);
  --xn-nav-hover-bg: var(--main-20);
  --xn-bg-secondary: var(--gray-50);
  --xn-hover-bg: var(--main-20);
  --xn-logo-text: var(--main-color);
  --xn-user-avatar-bg: var(--main-100);
  --xn-user-avatar-text: var(--main-900);
  --xn-user-avatar-ring: var(--main-200);
  --xn-divider: var(--gray-200);
  --xn-panel-shadow: 0 8px 30px rgba(15, 23, 42, 0.12);

  display: flex;
  flex-direction: row;
  width: 100%;
  height: 100vh;
  min-width: var(--min-width);
  position: relative;
}

// 深色主题（document.documentElement 带 .dark）
:global(html.dark) .app-layout {
  --xn-sidebar-bg: rgba(28, 28, 36, 0.72);
  --xn-sidebar-border: rgba(255, 255, 255, 0.09);
  --xn-sidebar-shadow: 0 14px 34px rgba(0, 0, 0, 0.5), 0 2px 8px rgba(0, 0, 0, 0.3);
  --xn-sidebar-blur: 16px;
  --xn-text-primary: rgba(255, 255, 255, 0.92);
  --xn-text-secondary: rgba(255, 255, 255, 0.66);
  --xn-text-muted: rgba(255, 255, 255, 0.42);
  --xn-nav-active-bg: rgba(255, 255, 255, 0.12);
  --xn-nav-hover-bg: rgba(255, 255, 255, 0.08);
  --xn-bg-secondary: rgba(255, 255, 255, 0.06);
  --xn-hover-bg: rgba(255, 255, 255, 0.08);
  --xn-logo-text: #ffffff;
  --xn-user-avatar-bg: rgba(255, 255, 255, 0.16);
  --xn-user-avatar-text: #ffffff;
  --xn-user-avatar-ring: rgba(255, 255, 255, 0.2);
  --xn-divider: rgba(255, 255, 255, 0.1);
  --xn-panel-shadow: 0 8px 30px rgba(0, 0, 0, 0.45);
}

#app-router-view {
  flex: 1 1 auto;
  height: 100%;
  overflow-y: auto;
  transition: margin-left 0.22s ease;
}

// 桌面端：内容跟随侧边栏宽度（展开 240px / 收起 56px）+ 浮起间距
.app-layout:not(.is-mobile) #app-router-view {
  margin-left: calc(var(--xn-sidebar-w) + var(--xn-sidebar-gap));
}

.app-layout:not(.is-mobile).is-collapsed #app-router-view {
  margin-left: calc(var(--xn-sidebar-collapsed-w) + var(--xn-sidebar-gap));
}

// ===== 侧边栏浮层（宽栏：桌面常驻 / 窄屏浮层，显隐由 v-show 控制）=====
// 外层即悬浮卡片：与视口上/左/下边缘留出 --xn-sidebar-gap，营造明显浮起感（同款悟帆 cvo-sidebar）
.xn-sidebar {
  position: fixed;
  top: var(--xn-sidebar-gap);
  bottom: var(--xn-sidebar-gap);
  left: var(--xn-sidebar-gap);
  width: var(--xn-sidebar-w);
  z-index: 31;
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  background: var(--xn-sidebar-bg);
  backdrop-filter: blur(var(--xn-sidebar-blur));
  -webkit-backdrop-filter: blur(var(--xn-sidebar-blur));
  border: 1px solid var(--xn-sidebar-border);
  box-shadow: var(--xn-sidebar-shadow);
  overflow: hidden;
}

.xn-sidebar-backdrop {
  position: fixed;
  inset: 0;
  z-index: 30;
  background: rgba(0, 0, 0, 0.32);
}

.xn-sidebar-inner {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

// ===== 顶部品牌栏 =====
.xn-sb-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 14px 14px 14px 18px;
  flex-shrink: 0;
}

.xn-brand {
  display: flex;
  align-items: center;
  min-width: 0;
  gap: 8px;
  text-decoration: none;
  color: var(--xn-logo-text);
  cursor: pointer;
}

.xn-brand-avatar {
  flex: 0 0 24px;
  width: 24px;
  height: 24px;
  border-radius: 7px;
  object-fit: cover;
}

.xn-brand-name {
  min-width: 0;
  overflow: hidden;
  font-size: 16px;
  font-weight: 650;
  line-height: 20px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.xn-sb-collapse {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--xn-text-muted);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;

  &:hover {
    background: var(--xn-nav-hover-bg);
    color: var(--xn-text-primary);
  }
}

.xn-sb-spacer {
  height: 6px;
  flex-shrink: 0;
}

// ===== 主导航 =====
.xn-primary-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 8px 8px;
  flex-shrink: 0;
}

.xn-nav-entry {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  min-height: 36px;
  padding: 0 14px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--xn-text-secondary);
  font-size: 13px;
  font-weight: 400;
  text-decoration: none;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
  outline: none;

  .xn-nav-icon {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    color: var(--xn-text-muted);
  }

  .xn-nav-text {
    min-width: 0;
    overflow: hidden;
    font-weight: 400;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &:hover {
    background: var(--xn-nav-hover-bg);
    color: var(--xn-text-primary);

    .xn-nav-icon {
      color: var(--xn-text-primary);
    }
  }

  &.active {
    background: var(--xn-nav-active-bg);
    color: var(--xn-text-primary);
    font-weight: 500;

    .xn-nav-icon {
      color: var(--xn-text-primary);
    }
  }

  // 新建对话：与普通导航项一致，透明背景，仅 hover/active 时显示底色
  &.xn-nav-new {
    color: var(--xn-text-primary);
    font-weight: 500;
    margin-bottom: 2px;

    .xn-nav-icon {
      color: var(--xn-text-primary);
    }

    &:hover {
      background: var(--xn-nav-hover-bg);
      color: var(--xn-text-primary);
    }
  }

  &:focus-visible {
    outline: 2px solid var(--xn-text-muted);
    outline-offset: 1px;
  }
}

// 工作台红色数字指示器（我的待办 + 待审核）
.xn-nav-badge {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 6px;
  border-radius: 999px;
  background: linear-gradient(180deg, #ff6b6b, #e54848);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  line-height: 18px;
  letter-spacing: 0.01em;
  box-shadow: 0 1px 3px rgba(229, 72, 77, 0.45);
  animation: t-badge-slide-in var(--badge-slide-dur) var(--badge-slide-ease);
}

/* xn-badge-pop 已弃用：工作台红点改用 transitions.css 的 t-badge-slide-in 入场动画 */

.xn-divider {
  margin: 0 12px;
  height: 1px;
  background: var(--xn-divider);
  flex-shrink: 0;
}

// ===== 对话历史区 =====
.xn-history {
  display: flex;
  flex-direction: column;
  flex: 1 1 0;
  min-height: 0;
  padding: 0;
}

.xn-history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 34px;
  padding: 2px 10px 0 14px;
  flex-shrink: 0;
}

.xn-history-title {
  margin: 0;
  font-size: 12px;
  font-weight: 500;
  color: var(--xn-text-muted);
  opacity: 0.82;
  letter-spacing: 0.01em;
}

.xn-history-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  padding: 0;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--xn-text-muted);
  opacity: 0.6;
  cursor: pointer;
  transition: background-color 0.12s ease, color 0.12s ease, opacity 0.12s ease;

  &:hover {
    background: var(--xn-nav-hover-bg);
    color: var(--xn-text-primary);
    opacity: 1;
  }
}

.xn-history-scroll {
  flex: 1 1 0;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-top: 2px;
  scrollbar-gutter: stable;
}

// 让内嵌的对话列表适配侧边栏配色
.xn-history :deep(.conversation-nav-section) {
  margin-top: 0;
}

.xn-history :deep(.history-label) {
  padding: 4px 6px 4px 14px;
  color: var(--xn-text-muted);
}

.xn-history :deep(.conversation-item) {
  margin: 0 8px;
  color: var(--xn-text-secondary);

  &:hover {
    background: var(--xn-nav-hover-bg);
    color: var(--xn-text-primary);

    .actions-mask {
      background: linear-gradient(to right, transparent, var(--xn-nav-hover-bg));
    }
  }

  &.active {
    background-color: var(--xn-nav-active-bg);
    color: var(--xn-text-primary);

    .actions-mask {
      background: linear-gradient(to right, transparent, var(--xn-nav-active-bg) 20px);
    }
  }
}

// ===== 底部用户区 =====
.xn-footer {
  flex-shrink: 0;
  padding: 10px 12px;
}

.xn-footer :deep(.user-info-component) {
  width: 100%;
}

.xn-user-task-center {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--xn-text-secondary);
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    color 0.2s ease,
    transform 0.1s ease,
    box-shadow 0.2s ease;

  &:hover,
  &.active {
    background: var(--xn-nav-hover-bg);
    color: var(--xn-text-primary);
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.1);
  }

  &:active {
    transform: scale(0.9);
  }

  &:focus-visible {
    outline: 2px solid var(--xn-text-muted);
    outline-offset: 1px;
  }

  :deep(.ant-badge) {
    display: flex;
    align-items: center;
  }

  :deep(svg) {
    display: block;
    width: 16px;
    height: 16px;
  }
}

// 底部用户区整体交互（用户名片 / 头像）
.xn-footer :deep(.user-info-dropdown) {
  padding: 8px 10px;
  border-radius: 10px;
  cursor: pointer;
  transition:
    background-color 0.18s ease,
    transform 0.12s ease,
    box-shadow 0.18s ease;

  &:hover {
    background: var(--xn-nav-hover-bg);
  }

  &:active {
    transform: scale(0.975);
  }

  &:focus-visible {
    outline: 2px solid var(--xn-text-muted);
    outline-offset: 1px;
  }
}

.xn-footer :deep(.user-avatar) {
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.xn-footer :deep(.user-info-dropdown):hover .user-avatar {
  transform: scale(1.06);
  box-shadow: 0 4px 12px var(--shadow-1);
}

// ===== 汉堡按钮 =====
.xn-hamburger {
  position: fixed;
  top: 12px;
  left: 12px;
  z-index: 32;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 8px;
  background: var(--xn-sidebar-bg);
  backdrop-filter: blur(var(--xn-sidebar-blur));
  -webkit-backdrop-filter: blur(var(--xn-sidebar-blur));
  border: 1px solid var(--xn-sidebar-border);
  color: var(--xn-text-secondary);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;

  &:hover {
    color: var(--xn-text-primary);
    background: var(--xn-nav-hover-bg);
  }
}

// ===== 窄栏（56px 纯图标栏，同款悟帆 cvo-sidebar-collapsed）=====
.xn-sidebar-narrow {
  position: fixed;
  top: var(--xn-sidebar-gap);
  bottom: var(--xn-sidebar-gap);
  left: var(--xn-sidebar-gap);
  width: var(--xn-sidebar-collapsed-w);
  z-index: 31;
  overflow: hidden;
  pointer-events: none;
}

.xn-narrow-inner {
  position: absolute;
  inset: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 0;
  border-radius: 16px;
  background: var(--xn-sidebar-bg);
  backdrop-filter: blur(var(--xn-sidebar-blur));
  -webkit-backdrop-filter: blur(var(--xn-sidebar-blur));
  border: 1px solid var(--xn-sidebar-border);
  box-shadow: var(--xn-sidebar-shadow);
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-width: none;
  pointer-events: auto;

  &::-webkit-scrollbar {
    display: none;
  }
}

.xn-narrow-logo {
  width: 32px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 0 4px;
  border: 0;
  background: transparent;
  cursor: pointer;
}

.xn-narrow-brand-img {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  object-fit: cover;
}

.xn-narrow-spacer {
  height: 16px;
  flex-shrink: 0;
}

.xn-narrow-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  margin: 2px 0;
  padding: 0;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--xn-text-muted);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
  text-decoration: none;

  &:hover {
    background: var(--xn-nav-hover-bg);
    color: var(--xn-text-primary);
  }

  &.active {
    background: var(--xn-nav-active-bg);
    color: var(--xn-text-primary);
  }

  // 新建对话：与普通按钮一致，hover 才显示底色
  &.xn-narrow-new {
    color: var(--xn-text-primary);

    &:hover {
      background: var(--xn-nav-hover-bg);
      color: var(--xn-text-primary);
    }
  }
}

.xn-narrow-divider {
  width: 24px;
  height: 1px;
  background: var(--xn-divider);
  margin: 10px 0;
  flex-shrink: 0;
}

.xn-narrow-flex {
  flex: 1 1 auto;
  min-height: 8px;
}

// 窄栏工作台红点（收起态下无文字，仅以红点提示）
.xn-narrow-nav-dot {
  position: absolute;
  top: 5px;
  right: 6px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: linear-gradient(180deg, #ff6b6b, #e54848);
  box-shadow: 0 0 0 1.5px var(--xn-sidebar-bg);
  pointer-events: none;
  animation: t-badge-slide-in var(--badge-slide-dur) var(--badge-slide-ease);
}

.xn-narrow-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 0;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  background: var(--xn-user-avatar-bg);
  color: var(--xn-user-avatar-text);
  box-shadow: inset 0 0 0 1px var(--xn-user-avatar-ring);
}
@media (prefers-reduced-motion: reduce) {
  .xn-nav-badge,
  .xn-narrow-nav-dot {
    animation: none !important;
  }
}
</style>
