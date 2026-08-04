<script setup>
/**
 * ★ 审计台 — 仅系统管理员可见（v2.1 §9.4）
 * 查询与核验全量审计事件（含防篡改哈希链）。
 * 后端审计查询接口（P0-5）就绪后通过 police_api 接入。
 */
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
</script>

<template>
  <div class="audit-console">
    <a-page-header title="审计台" sub-title="系统管理员专属">
      <template #tags>
        <a-tag color="red">仅系统管理员可见</a-tag>
        <a-tag v-if="userStore.isSuperAdmin" color="gold">超级管理员</a-tag>
      </template>
    </a-page-header>

    <a-alert
      type="info"
      show-icon
      style="margin: 16px;"
      message="功能建设中"
      description="后端审计查询接口（P0-5）就绪后，此处将提供全量审计事件检索、按案件/用户/操作类型筛选、以及证据哈希 / 审计哈希链的防篡改核验。当前页面仅作为权限验证入口：系统管理员可见，普通用户菜单中不会出现此入口、直访也会被路由守卫拦截。"
    />
  </div>
</template>

<style scoped>
.audit-console {
  padding: 8px 16px;
}
</style>
