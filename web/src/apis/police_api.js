/**
 * ★ 公安业务 API 模块
 * 案件管理、任务管理、证据管理、工作台
 */
import { apiGet, apiPost, apiPut, apiDelete } from './base'

// ── 工作台 ──────────────────────────────────────────────────
export const policeDashboardApi = {
  getStats: () => apiGet('/api/police/dashboard/stats'),
  getMyTasks: ({ page = 1, page_size = 20 } = {}) =>
    apiGet(`/api/police/dashboard/my-tasks?page=${page}&page_size=${page_size}`),
  getReviewTasks: ({ page = 1, page_size = 20 } = {}) =>
    apiGet(`/api/police/dashboard/review-tasks?page=${page}&page_size=${page_size}`),
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

// ── 数字警员 (融合 StaffDeck 数字员工概念) ──────────────────
export const policeAgentApi = {
  list: ({ type, status, keyword, page = 1, page_size = 50 } = {}) => {
    const params = new URLSearchParams({ page, page_size })
    if (type) params.set('type', type)
    if (status) params.set('status', status)
    if (keyword) params.set('keyword', keyword)
    return apiGet(`/api/police/agents?${params}`)
  },
  get: (agentId) => apiGet(`/api/police/agents/${agentId}`),
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
}
