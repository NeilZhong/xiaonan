/**
 * ★ 公安业务 API 模块
 * 案件管理、任务管理、证据管理、工作台
 */
import { apiGet, apiPost, apiPut, apiDelete } from './base'

// ── 工作台 ──────────────────────────────────────────────────
export const policeDashboardApi = {
  getStats: (silent = false) =>
    apiGet('/api/police/dashboard/stats', silent ? { silent: true } : {}),
  getMyTasks: ({ page = 1, page_size = 20 } = {}, silent = false) =>
    apiGet(`/api/police/dashboard/my-tasks?page=${page}&page_size=${page_size}`, silent ? { silent: true } : {}),
  getReviewTasks: ({ page = 1, page_size = 20 } = {}, silent = false) =>
    apiGet(`/api/police/dashboard/review-tasks?page=${page}&page_size=${page_size}`, silent ? { silent: true } : {}),
}

// ── 案件管理 ────────────────────────────────────────────────
export const policeCaseApi = {
  list: ({ page = 1, page_size = 20, status, phase, case_type, keyword, mine } = {}) => {
    const params = new URLSearchParams({ page, page_size })
    if (status) params.set('status', status)
    if (phase) params.set('phase', phase)
    if (case_type) params.set('case_type', case_type)
    if (keyword) params.set('keyword', keyword)
    if (mine) params.set('mine', 'true')
    return apiGet(`/api/police/cases?${params}`)
  },
  get: (caseId) => apiGet(`/api/police/cases/${caseId}`),
  create: (data) => apiPost('/api/police/cases', data),
  update: (caseId, data) => apiPut(`/api/police/cases/${caseId}`, data),
  delete: (caseId) => apiDelete(`/api/police/cases/${caseId}`),
  addMember: (caseId, data) => apiPost(`/api/police/cases/${caseId}/members`, data),
  updatePhase: (caseId, phase) => apiPut(`/api/police/cases/${caseId}/phase`, { phase }),
  timeline: (caseId) => apiGet(`/api/police/cases/${caseId}/timeline`),
}

// ── 任务管理 ────────────────────────────────────────────────
export const policeTaskApi = {
  list: ({ page = 1, page_size = 20, case_id, status, assignee_type, task_type, keyword } = {}) => {
    const params = new URLSearchParams({ page, page_size })
    if (case_id) params.set('case_id', case_id)
    if (status) params.set('status', status)
    if (assignee_type) params.set('assignee_type', assignee_type)
    if (task_type) params.set('task_type', task_type)
    if (keyword) params.set('keyword', keyword)
    return apiGet(`/api/police/tasks?${params}`)
  },
  myTasks: ({ page = 1, page_size = 20 } = {}) =>
    apiGet(`/api/police/tasks/my?page=${page}&page_size=${page_size}`),
  reviewTasks: ({ page = 1, page_size = 20 } = {}) =>
    apiGet(`/api/police/tasks/review?page=${page}&page_size=${page_size}`),
  get: (taskId) => apiGet(`/api/police/tasks/${taskId}`),
  create: (data) => apiPost('/api/police/tasks', data),
  update: (taskId, data) => apiPut(`/api/police/tasks/${taskId}`, data),
  assign: (taskId, data) => apiPost(`/api/police/tasks/${taskId}/assign`, data),
  start: (taskId) => apiPost(`/api/police/tasks/${taskId}/start`),
  complete: (taskId, result) => apiPost(`/api/police/tasks/${taskId}/complete`, { result }),
  review: (taskId, approved, comment) => apiPost(`/api/police/tasks/${taskId}/review`, { approved, comment }),
  events: (taskId) => apiGet(`/api/police/tasks/${taskId}/events`),
}

// ── 证据管理 ────────────────────────────────────────────────
export const policeEvidenceApi = {
  list: (caseId, { page = 1, page_size = 50, evidence_type, task_id } = {}) => {
    const params = new URLSearchParams({ page, page_size })
    if (evidence_type) params.set('evidence_type', evidence_type)
    if (task_id) params.set('task_id', task_id)
    return apiGet(`/api/police/evidence/case/${caseId}?${params}`)
  },
  upload: (caseId, file, { evidence_type = 'document', task_id } = {}) => {
    const formData = new FormData()
    formData.append('file', file)
    const url = `/api/police/evidence/case/${caseId}?evidence_type=${evidence_type}${task_id ? `&task_id=${task_id}` : ''}`
    return apiPost(url, formData)
  },
  get: (evidenceId) => apiGet(`/api/police/evidence/${evidenceId}`),
  review: (evidenceId) => apiPost(`/api/police/evidence/${evidenceId}/review`, { approved: true }),
  chain: (caseId) => apiGet(`/api/police/evidence/case/${caseId}/chain`),
}

// ── 智能体 / 流程技能 (SOP) ────────────────────────────────
export const policeAgentApi = {
  list: ({ type, status, keyword, page = 1, page_size = 50 } = {}) => {
    const params = new URLSearchParams({ page, page_size })
    if (type) params.set('type', type)
    if (status) params.set('status', status)
    if (keyword) params.set('keyword', keyword)
    return apiGet(`/api/police/agents?${params}`)
  },
  get: (agentId) => apiGet(`/api/police/agents/${agentId}`),
  /** 按 yuxi 智能体主键 id 查询关联的数字警员档案（无关联返回 null） */
  getByYuxiId: (yuxiAgentId) => apiGet(`/api/police/agents/by-yuxi/${yuxiAgentId}`),
  /** 按数字警员工号查询档案（档案页路由 /agent-manage/:badge_number 使用） */
  getByBadgeNumber: (badgeNumber) => apiGet(`/api/police/agents/by-badge/${badgeNumber}`),
  create: (data) => apiPost('/api/police/agents', data),
  update: (agentId, data) => apiPut(`/api/police/agents/${agentId}`, data),
  delete: (agentId) => apiDelete(`/api/police/agents/${agentId}`),
  runs: (agentId, { page = 1, page_size = 20 } = {}) =>
    apiGet(`/api/police/agents/${agentId}/runs?page=${page}&page_size=${page_size}`),
  listSops: ({ agent_type, category } = {}) => {
    const params = new URLSearchParams()
    if (agent_type) params.set('agent_type', agent_type)
    if (category) params.set('category', category)
    return apiGet(`/api/police/agents/sops/list?${params}`)
  },
  getSop: (sopId) => apiGet(`/api/police/agents/sops/${sopId}`),
  createSop: (data) => apiPost('/api/police/agents/sops', data),
  updateSop: (sopId, data) => apiPut(`/api/police/agents/sops/${sopId}`, data),
  seed: () => apiPost('/api/police/agents/seed'),
  // ── 市场模板 ────────────────────────────────────────
  listTemplates: ({ category, keyword, page = 1, page_size = 50 } = {}) => {
    const params = new URLSearchParams({ page, page_size })
    if (category) params.set('category', category)
    if (keyword) params.set('keyword', keyword)
    return apiGet(`/api/police/agents/templates?${params}`)
  },
  installTemplate: (templateId) => apiPost(`/api/police/agents/templates/${templateId}/install`),
  shareAgent: (agentId, { scope, department_ids, user_uids, author_id }) =>
    apiPost(`/api/police/agents/${agentId}/share`, { scope, department_ids, user_uids, author_id }),
  approveAgent: (agentId, { approved, reviewer_id }) =>
    apiPost(`/api/police/agents/${agentId}/approve`, { approved, reviewer_id }),
}

// ── 案件独立工作区（树状节点）────────────────────────────────
export const policeWorkspaceApi = {
  get: (caseId) => apiGet(`/api/police/workspaces/${caseId}`),
  init: (caseId) => apiPost(`/api/police/workspaces/${caseId}/init`),
  createFolder: (caseId, { name, parent_id }) =>
    apiPost(`/api/police/workspaces/${caseId}/folders`, { name, parent_id }),
  upload: (caseId, parentId, file) => {
    const formData = new FormData()
    formData.append('file', file)
    const qs = parentId ? `?parent_id=${parentId}` : ''
    return apiPost(`/api/police/workspaces/${caseId}/upload${qs}`, formData)
  },
  download: (caseId, nodeId) =>
    `/api/police/workspaces/${caseId}/download?node_id=${nodeId}`,
  move: (caseId, { node_id, target_parent_id }) =>
    apiPost(`/api/police/workspaces/${caseId}/move`, { node_id, target_parent_id }),
  rename: (caseId, { node_id, name }) =>
    apiPost(`/api/police/workspaces/${caseId}/rename`, { node_id, name }),
  remove: (caseId, nodeId) =>
    apiDelete(`/api/police/workspaces/${caseId}/nodes`, { body: JSON.stringify({ node_id: nodeId }) }),
}

// ── 案件推进智能体 (POLICE_REQUIREMENTS §6.7) ──────────────
export const policeAdvancementApi = {
  // 某案件待确认任务草案
  listDrafts: (caseId) => apiGet(`/api/police/advancement/${caseId}/drafts`),
  // 当前用户跨案件待确认草案（个人工作台「待审查」）
  myDrafts: (silent = false) =>
    apiGet('/api/police/advancement/my-drafts', silent ? { silent: true } : {}),
  // 主办民警确认草案 → pending（可附带编辑）
  confirmDraft: (taskId, edits) =>
    apiPost(`/api/police/advancement/tasks/${taskId}/confirm`, { edits: edits || null }),
  // 主办民警驳回草案 → cancelled
  rejectDraft: (taskId, reason) =>
    apiPost(`/api/police/advancement/tasks/${taskId}/reject`, { reason: reason || null }),
  // 侦查方向变更（重新规划）
  changeDirection: (caseId, direction) =>
    apiPost(`/api/police/advancement/${caseId}/direction`, { direction }),
  // 推进决策日志（可解释性）
  listLogs: (caseId, limit = 50) => apiGet(`/api/police/advancement/${caseId}/logs?limit=${limit}`),
  // 启用 / 停用推进智能体
  toggle: (caseId, enabled) => apiPost(`/api/police/advancement/${caseId}/toggle`, { enabled }),
}

// ── 侦查任务模板 (POLICE_REQUIREMENTS §6.7 任务模板配置化) ──
export const policeTaskTemplateApi = {
  // 模板列表（首次访问且库为空会自动植入内置模板）
  list: ({ element_type, enabled_only, keyword } = {}) => {
    const params = new URLSearchParams()
    if (element_type) params.set('element_type', element_type)
    if (enabled_only) params.set('enabled_only', 'true')
    if (keyword) params.set('keyword', keyword)
    const qs = params.toString()
    return apiGet(`/api/police/task-templates${qs ? `?${qs}` : ''}`)
  },
  // 表单元数据：要素类型 / 任务类型 / 优先级 / 数字警员 / 占位符 / 模板（用于链式后继选择）
  meta: () => apiGet('/api/police/task-templates/meta'),
  // 重新植入内置模板（幂等）
  seed: () => apiPost('/api/police/task-templates/seed'),
  // 新建自定义模板
  create: (data) => apiPost('/api/police/task-templates', data),
  // 模板详情
  get: (id) => apiGet(`/api/police/task-templates/${id}`),
  // 更新模板
  update: (id, data) => apiPut(`/api/police/task-templates/${id}`, data),
  // 删除自定义模板（内置模板只能停用）
  remove: (id) => apiDelete(`/api/police/task-templates/${id}`),
  // 启用 / 停用
  toggle: (id, enabled) => apiPost(`/api/police/task-templates/${id}/toggle`, { enabled }),
  // 预览渲染效果（用示例要素值填充占位符）
  preview: (id, sampleValue = '示例值') =>
    apiPost(`/api/police/task-templates/${id}/preview`, { sample_value: sampleValue }),
}
