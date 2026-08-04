<script setup>
/**
 * ★ 运行时控制台 — 仅系统管理员可见（v2.1 §4.13 / §9.2）
 * 查看运行中数字警员状态，支持回收 / 跳入子会话 / 终止等干预。
 * 后端运行时接口（P0-7）就绪后通过 police_api 接入。
 */
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
</script>

<template>
  <div class="runtime-console">
    <a-page-header title="运行时控制台" sub-title="系统管理员专属">
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
      description="后端运行时接口（P0-7）就绪后，此处将展示各数字警员实时运行状态、当前执行任务、执行轨迹，并提供回收 / 跳入子会话 / 终止等四档干预能力。当前页面仅作为权限验证入口：系统管理员可见，普通用户菜单中不会出现此入口、直访也会被路由守卫拦截。"
    />
  </div>
</template>

<style scoped>
.runtime-console {
  padding: 8px 16px;
}
</style>
