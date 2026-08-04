/**
 * ★ 公安业务 Pinia Store
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { policeDashboardApi, policeCaseApi, policeTaskApi, policeAgentApi, policeWorkspaceApi, policeAdvancementApi, policeTaskTemplateApi } from '@/apis/police_api'

export const usePoliceStore = defineStore('police', () => {
  // ── 工作台统计 ──────────────────────────────────────────
  const stats = ref({ my_pending_count: 0, my_in_progress_count: 0, review_count: 0, my_tasks_total: 0 })
  const myTasks = ref([])
  const reviewTasks = ref([])
  const myTasksTotal = ref(0)
  const reviewTasksTotal = ref(0)
  const myDrafts = ref([])
  const advancementLogs = ref([])

  async function loadStats(silent = false) {
    try {
      const res = await policeDashboardApi.getStats(silent)
      stats.value = res.data || stats.value
    } catch (e) { console.error('加载统计失败', e) }
  }

  async function loadMyTasks(page = 1, pageSize = 20, silent = false) {
    try {
      const res = await policeDashboardApi.getMyTasks({ page, page_size: pageSize }, silent)
      myTasks.value = res.data?.items || []
      myTasksTotal.value = res.data?.total || 0
    } catch (e) { console.error('加载我的任务失败', e) }
  }

  async function loadReviewTasks(page = 1, pageSize = 20, silent = false) {
    try {
      const res = await policeDashboardApi.getReviewTasks({ page, page_size: pageSize }, silent)
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

  // ── 案件推进智能体 ──────────────────────────────────────
  async function loadMyDrafts(silent = false) {
    try {
      const res = await policeAdvancementApi.myDrafts(silent)
      myDrafts.value = res.data || []
    } catch (e) { console.error('加载待审查草案失败', e) }
  }

  async function loadDrafts(caseId) {
    try {
      const res = await policeAdvancementApi.listDrafts(caseId)
      myDrafts.value = res.data || []
    } catch (e) { console.error('加载草案失败', e) }
  }

  async function confirmDraft(taskId, edits) {
    const res = await policeAdvancementApi.confirmDraft(taskId, edits)
    return res.data
  }

  async function rejectDraft(taskId, reason) {
    const res = await policeAdvancementApi.rejectDraft(taskId, reason)
    return res.data
  }

  async function changeDirection(caseId, direction) {
    const res = await policeAdvancementApi.changeDirection(caseId, direction)
    return res.data
  }

  async function loadAdvancementLogs(caseId) {
    try {
      const res = await policeAdvancementApi.listLogs(caseId)
      advancementLogs.value = res.data || []
    } catch (e) { console.error('加载推进日志失败', e) }
  }

  async function toggleAdvancement(caseId, enabled) {
    const res = await policeAdvancementApi.toggle(caseId, enabled)
    return res.data
  }

  // ── 侦查任务模板 ────────────────────────────────────────
  const taskTemplates = ref([])
  const taskTemplateMeta = ref(null)

  async function loadTaskTemplates(params = {}) {
    try {
      const res = await policeTaskTemplateApi.list(params)
      taskTemplates.value = res.data || []
    } catch (e) { console.error('加载任务模板失败', e) }
    return taskTemplates.value
  }

  async function loadTaskTemplateMeta() {
    try {
      const res = await policeTaskTemplateApi.meta()
      taskTemplateMeta.value = res.data
    } catch (e) { console.error('加载模板元数据失败', e) }
    return taskTemplateMeta.value
  }

  async function createTaskTemplate(data) {
    const res = await policeTaskTemplateApi.create(data)
    return res.data
  }

  async function updateTaskTemplate(id, data) {
    const res = await policeTaskTemplateApi.update(id, data)
    return res.data
  }

  async function deleteTaskTemplate(id) {
    const res = await policeTaskTemplateApi.remove(id)
    return res.data
  }

  async function toggleTaskTemplate(id, enabled) {
    const res = await policeTaskTemplateApi.toggle(id, enabled)
    return res.data
  }

  async function seedTaskTemplates() {
    const res = await policeTaskTemplateApi.seed()
    return res.data
  }

  async function previewTaskTemplate(id, sampleValue) {
    const res = await policeTaskTemplateApi.preview(id, sampleValue)
    return res.data
  }

  // ── 流程技能 (SOP) ─────────────────────────────────────
  const sops = ref([])

  async function loadSops(params = {}) {
    try {
      const res = await policeAgentApi.listSops(params)
      sops.value = res.data || []
    } catch (e) { console.error('加载SOP失败', e) }
  }

  // ── 案件工作区 ──────────────────────────────────────────
  const workspace = ref(null)

  async function loadWorkspace(caseId) {
    try {
      const res = await policeWorkspaceApi.get(caseId)
      workspace.value = res.data
    } catch (e) { console.error('加载工作区失败', e) }
    return workspace.value
  }

  return {
    stats, myTasks, reviewTasks, myTasksTotal, reviewTasksTotal, myDrafts, advancementLogs,
    cases, casesTotal, currentCase, tasks, tasksTotal, currentTask,
    sops, workspace, taskTemplates, taskTemplateMeta,
    loadStats, loadMyTasks, loadReviewTasks,
    loadCases, loadCase, createCase, updateCase, updatePhase,
    loadTasks, loadTask, createTask, assignTask, startTask, completeTask, reviewTask,
    loadMyDrafts, loadDrafts, confirmDraft, rejectDraft, changeDirection, loadAdvancementLogs, toggleAdvancement,
    loadTaskTemplates, loadTaskTemplateMeta, createTaskTemplate, updateTaskTemplate,
    deleteTaskTemplate, toggleTaskTemplate, seedTaskTemplates, previewTaskTemplate,
    loadSops,
    loadWorkspace,
  }
})
