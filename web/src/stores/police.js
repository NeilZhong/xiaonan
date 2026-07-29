/**
 * ★ 公安业务 Pinia Store
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { policeDashboardApi, policeCaseApi, policeTaskApi } from '@/apis/police_api'

export const usePoliceStore = defineStore('police', () => {
  // ── 工作台统计 ──────────────────────────────────────────
  const stats = ref({ my_pending_count: 0, my_in_progress_count: 0, review_count: 0, my_tasks_total: 0 })
  const myTasks = ref([])
  const reviewTasks = ref([])
  const myTasksTotal = ref(0)
  const reviewTasksTotal = ref(0)

  async function loadStats() {
    try {
      const res = await policeDashboardApi.getStats()
      stats.value = res.data || stats.value
    } catch (e) { console.error('加载统计失败', e) }
  }

  async function loadMyTasks(page = 1, pageSize = 20) {
    try {
      const res = await policeDashboardApi.getMyTasks({ page, page_size: pageSize })
      myTasks.value = res.data?.items || []
      myTasksTotal.value = res.data?.total || 0
    } catch (e) { console.error('加载我的任务失败', e) }
  }

  async function loadReviewTasks(page = 1, pageSize = 20) {
    try {
      const res = await policeDashboardApi.getReviewTasks({ page, page_size: pageSize })
      reviewTasks.value = res.data?.items || []
      reviewTasksTotal.value = res.data?.total || 0
    } catch (e) { console.error('加载审核任务失败', e) }
  }

  // ── 案件 ────────────────────────────────────────────────
  const cases = ref([])
  const casesTotal = ref(0)
  const currentCase = ref(null)

  async function loadCases(params = {}) {
    try {
      const res = await policeCaseApi.list(params)
      cases.value = res.data?.items || []
      casesTotal.value = res.data?.total || 0
    } catch (e) { console.error('加载案件失败', e) }
  }

  async function loadCase(caseId) {
    try {
      const res = await policeCaseApi.get(caseId)
      currentCase.value = res.data
    } catch (e) { console.error('加载案件详情失败', e) }
  }

  async function createCase(data) {
    const res = await policeCaseApi.create(data)
    return res.data
  }

  async function updateCase(caseId, data) {
    const res = await policeCaseApi.update(caseId, data)
    return res.data
  }

  async function updatePhase(caseId, phase) {
    const res = await policeCaseApi.updatePhase(caseId, phase)
    if (currentCase.value?.id === caseId) {
      currentCase.value = res.data
    }
    return res.data
  }

  // ── 任务 ────────────────────────────────────────────────
  const tasks = ref([])
  const tasksTotal = ref(0)
  const currentTask = ref(null)

  async function loadTasks(params = {}) {
    try {
      const res = await policeTaskApi.list(params)
      tasks.value = res.data?.items || []
      tasksTotal.value = res.data?.total || 0
    } catch (e) { console.error('加载任务失败', e) }
  }

  async function loadTask(taskId) {
    try {
      const res = await policeTaskApi.get(taskId)
      currentTask.value = res.data
    } catch (e) { console.error('加载任务详情失败', e) }
  }

  async function createTask(data) {
    const res = await policeTaskApi.create(data)
    return res.data
  }

  async function assignTask(taskId, data) {
    const res = await policeTaskApi.assign(taskId, data)
    return res.data
  }

  async function startTask(taskId) {
    const res = await policeTaskApi.start(taskId)
    return res.data
  }

  async function completeTask(taskId, result) {
    const res = await policeTaskApi.complete(taskId, result)
    return res.data
  }

  async function reviewTask(taskId, approved, comment) {
    const res = await policeTaskApi.review(taskId, approved, comment)
    return res.data
  }

  return {
    stats, myTasks, reviewTasks, myTasksTotal, reviewTasksTotal,
    cases, casesTotal, currentCase, tasks, tasksTotal, currentTask,
    loadStats, loadMyTasks, loadReviewTasks,
    loadCases, loadCase, createCase, updateCase, updatePhase,
    loadTasks, loadTask, createTask, assignTask, startTask, completeTask, reviewTask,
  }
})
