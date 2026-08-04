# 智案协 / 小南 — 项目进度与待办

> **最后更新**: 2026-08-04
> **当前里程碑**: M0 ✅ → M1 ✅ → M1.5 ✅ → M2 ✅ (闭环) → **当前聚焦：v2.1 安全与权限地基（P0）+ 协作深化（P1）**
> **开发文档**: [POLICE_REQUIREMENTS.md](./POLICE_REQUIREMENTS.md) **v2.1**（两大核心：①数字警察为一等公民 ②案件驱动协作；对照 MateClaw 取长补短重写）
> **当前开发秩序**: 先 P0（权限/审批越权/审计防篡改——合规硬缺口），再 P1（依赖编排/审核工作台/产物/证据验证），后 P2（角色卡结构化/Workflow DSL/技能/MCP/知识溯源）

---

## 已完成

### Phase 0: 语析底座接入 ✅

| 任务 | 状态 | 说明 |
|------|------|------|
| Fork xerrors/Yuxi，clone 到本地 | ✅ | `NeilZhong/xiaonan` → 本地仓库 |
| 熟悉语析架构 (server + package 分层) | ✅ | server/routers (HTTP) + package/yuxi (核心库) |
| 扩展用户模型 (警号/警衔/真实姓名) | ✅ | `models_business.py` + `manager.py` SQL 迁移 |
| LLM 配置精简为单一 OpenAI 兼容 API | ✅ | `custom-openai` provider，仅自建 `agnes` 模型 |
| Git 初始化 + 首次提交 + Push GitHub | ✅ | commit `255550b4`，SSH 认证 |
| README.md 重写 | ✅ | 智案协平台说明 |
| 开发文档编写 | ✅ | POLICE_REQUIREMENTS.md v1.2 → v1.5 → v1.6 → **v2.1** |

### Phase 1: 案件与任务管理 ✅

#### 后端

| 任务 | 状态 | 文件 | 行数 |
|------|------|------|------|
| 公安业务 ORM 模型 (11 张表) | ✅ | `models_police.py` | 459 |
| 案件 Repository (CRUD + 成员 + 阶段) | ✅ | `case_repository.py` | 160 |
| 任务 Repository (CRUD + 状态流转 + 事件 + 流转规则) | ✅ | `task_repository.py` | 183 |
| 证据 Repository (CRUD + SHA-256 双哈希签名 + 关联链) | ✅ | `evidence_repository.py` | 102 |
| 公安业务 Service 层 (案件 + 任务流转引擎 + 仪表盘) | ✅ | `police_service.py` | 265 |
| 案件 API Router (8 endpoints) | ✅ | `police_case_router.py` | 169 |
| 任务 API Router (11 endpoints) | ✅ | `police_task_router.py` | 215 |
| 证据 API Router (5 endpoints) | ✅ | `police_evidence_router.py` | 118 |
| 仪表盘 API Router (3 endpoints) | ✅ | `police_dashboard_router.py` | 48 |
| 运行时 SQL 迁移 (建表 + 索引) | ✅ | `manager.py` 扩展 | +227 |
| 路由注册 | ✅ | `routers/__init__.py` | +12 |

#### 前端

| 任务 | 状态 | 文件 | 行数 |
|------|------|------|------|
| API 请求层 | ✅ | `police_api.js` | 78 |
| Pinia 状态管理 | ✅ | `stores/police.js` | 129 |
| 工作台仪表盘 (统计卡片 + 待办 + 审核 + 快捷操作) | ✅ | `PoliceDashboardView.vue` | 367 |
| 案件列表 (搜索 + 筛选 + 分页 + 创建弹窗) | ✅ | `CaseListView.vue` | 284 |
| 案件详情 (阶段步骤条 + 多 Tab) | ✅ | `CaseDetailView.vue` | 571 |
| 任务看板 (看板/列表双视图 + 5 状态列) | ✅ | `TaskBoardView.vue` | 318 |
| 任务详情 (操作按钮 + 事件时间线 + 审核弹窗) | ✅ | `TaskDetailView.vue` | 701 |
| 证据管理 Tab (上传 + 哈希展示 + 审核签名) | ✅ | `EvidenceTab.vue` | 129 |
| 案件时间线 | ✅ | `CaseTimeline.vue` | 61 |
| 路由配置 (5 条 /police/* 路由) | ✅ | `router/index.js` | +37 |
| 侧边导航菜单 (工作台/案件管理/任务管理) | ✅ | `AppLayout.vue` | +30 |

#### 构建验证

- ✅ Python AST 语法检查全部通过
- ✅ 前端 `vite build` 成功 (0 errors)
- ✅ npm 445 packages, 0 vulnerabilities

### Phase 1.5: 数字警员平台 (融合 StaffDeck) ✅

融合 StaffDeck 数字员工概念 + 手绘风格 UI，将公安智能体升级为"数字警员"。

#### 后端

| 任务 | 状态 | 文件 | 说明 |
|------|------|------|------|
| 扩展 PoliceAgent 模型为数字警员 | ✅ | `models_police.py` | 新增档案(工号/警衔/专长/头像/部门)、能力矩阵、工作统计、成长记录、SOP 关联 |
| 新增 PoliceSOP 模型 (状态机驱动 SOP) | ✅ | `models_police.py` | SOP 流程技能定义(状态节点/转移规则/输入输出) |
| SQL 迁移 (新列 + 新表) | ✅ | `manager.py` | police_agents 扩展列 + police_sops 建表 |
| 数字警员仓储 | ✅ | `agent_repository.py` | CRUD + 工作统计 + 成长记录 + 运行记录 + SOP 管理 |
| 数字警员服务层 | ✅ | `police_service.py` | PoliceAgentService + 7 名预设数字警员 + seed 接口 |
| 数字警员 API 路由 (13 endpoints) | ✅ | `police_agent_router.py` | 列表/详情/CRUD/运行记录/SOP/初始化 |

#### 前端

| 任务 | 状态 | 文件 | 说明 |
|------|------|------|------|
| 手绘线条美术风格 CSS 主题 | ✅ | `police-sketch-theme.css` | 纸质感卡片/手绘边框/暖色调/不规则圆角/手绘标签/时间线 |
| 数字警员 API 扩展 | ✅ | `police_api.js` | policeAgentApi (list/get/create/update/delete/runs/sops/seed) |
| Pinia Store 扩展 | ✅ | `police.js` | agents/currentAgent/sops 状态 + loadAgents/loadAgent/seedAgents |
| 数字警员列表页 (画廊式卡片) | ✅ | `DigitalOfficerListView.vue` | StaffDeck 风格画廊 + 搜索/筛选/初始化预设 |
| 数字警员详情页 (档案/能力/记录/SOP/成长) | ✅ | `DigitalOfficerDetailView.vue` | 4 Tab(档案/工作记录/SOP/成长) + 侧边栏统计 |
| 路由 + 导航 | ✅ | `router/index.js` + `AppLayout.vue` | /police/agents + /police/agents/:agentId + 侧边栏菜单 |

#### 7 名预设数字警员（PRESET_AGENTS，DA-001~DA-007）

| 工号 | 名称 | 类型 | 专长 | 色系 |
|------|------|------|------|------|
| DA-001 | 笔录分析师 | transcript_analyst | 笔录解析 · 实体识别 · 信息提取 | blue |
| DA-002 | 资金追踪师 | fund_analyst | 银行流水解析 · 资金追踪 · 异常检测 | green |
| DA-003 | 调证生成师 | evidence_collector | 法律依据检索 · 调取通知书生成 | amber |
| DA-004 | 法制审核官 | legal_reviewer | 程序审核 · 证据审核 · 定性审核 | coral |
| DA-005 | 案件编排官 | case_orchestrator | 案件编排 · 子智能体调度 · 任务流转 | purple |
| DA-006 | 群聊分析专家 | chat_analyst | 聊天记录/电子数据关联分析 | blue |
| DA-007 | 审讯辅助专家 | interrogation_advisor | 基于笔录与证据的审讯策略 | green |

#### 构建验证

- ✅ Python AST 语法检查全部通过
- ✅ 前端 `vite build` 成功 (0 errors)

### Phase 2: 笔录分析智能体 + 案件智能创建 ✅ (最小闭环)

- [x] **笔录信息提取 → 结构化案件信息 JSON**：`police_transcript_service.analyze_transcript`
- [x] **自动创建案件 + 生成初始任务列表**：`POST /police/import/transcript/confirm`
- [x] **案件导入流程页面**：`web/src/views/police/CaseImportView.vue`
- [x] **集成 Yuxi OCR 引擎（解析 PDF/图片）**：复用 `ocr_service.parse_document`
- [~] **开发 `transcript_analysis` Skill**：当前作为独立 `police_*` 业务服务 + API
- [~] **复用 Yuxi 审批中间件**：以「AI 分析 → 民警确认 → 建案」实现「产出需确认」约束

---

## 当前开发任务（v2.1 路线图落地）

> 来源：[POLICE_REQUIREMENTS.md](./POLICE_REQUIREMENTS.md) §14「开发计划与里程碑」P0/P1/P2 清单 + §4 权限体系 + §9 审核人规则。
> 命名约定：新增后端功能放独立文件 `police_*_repository.py` / `police_*_router.py`；DB 迁移走 `ensure_business_schema()`（CREATE TABLE IF NOT EXISTS，无 Alembic）。
> **执行顺序**：P0（合规硬缺口，必须先做）→ P1 → P2。

### 🔴 P0：权限与安全地基（合规硬缺口，优先排期）

**P0-1 平台角色体系 `system_admin` / `user`**
- [~] 后端：**决策：复用 yuxi 既有 `users.role`（`admin`/`superadmin`=系统管理员）＋ 既有 `get_admin_user` 依赖作为 `require_admin`**，不新增 `platform_role` 列（避免改动 yuxi 核心 User 模型；如确需独立 `system_admin/user` 枚举再补）。运行时控制台/审计台入口将挂载此依赖。
- [~] 后端：`require_admin` 已就绪（= `get_admin_user`，`role in [admin, superadmin]`）
- [x] 前端：管理员专属入口（运行时控制台 / 审计台 / 数字警员管理）按 `role` 显隐；普通用户不可见

**P0-2 案件成员模型（用户 + 数字警察并列为一等成员）**
- [ ] 后端：确认 `police_case_members` 的 `member_type`(`user`/`agent`) + `case_role`(`commander`/`executor`/`reviewer`/`observer`) 在创建/查询/鉴权链路生效
- [ ] 后端：「添加成员」接口支持加入用户或数字警察，写审计
- [ ] 前端：案件成员管理面板（区分人/警，显示案件角色与状态）

**P0-3 任务审核人判定规则代码化**（§4.3 / §9.2，必须代码层实现）
- [x] 后端：`create_task` / `assign_task_multi` 时按规则自动解算 `reviewer_id` + `require_approval`（`task_repository.resolve_reviewer` + `set_reviewer`）：both→首个人类执行人；agent→案件指挥员；user→NULL / 无需审核
- [ ] 后端：指挥员改派审核人必须写审计记录（后续增强）

**P0-4 审批端点补 reviewer RBAC 校验**（修复越权安全硬伤 ✅ 已落地）
- [x] 后端：`POST /tasks/{tid}/review` 严格校验（`require_approval=1` 时仅 `reviewer_id` 或 `admin/superadmin`，否则 403）；纯人类任务仅执行人或管理员可标记完成
- [x] 后端：签名 `signed_hash` 用真实审核人警号签署（`current_user.police_id`），禁止任意账号冒充审核人
- [ ] 后端（可选）：`GET /tasks/{tid}/verify-signature` 校验签名真实性（待 P0-6 后做）
- [x] 前端：审核页 `canReview` 按 `reviewer_id` 前置显隐通过/驳回按钮 + 403 友好提示（TaskDetailView.vue）
- [x] 后端（关键修复）：`ensure_business_schema` 共享 stmts 事务无 per-stmt try，任一 stmt 失败回滚整个事务，导致偏后的 `reviewer_id`/`require_approval` 加列被回滚、列始终不存在；改为独立事务+独立 try/except 加列（manager.py），api 现已正常启动并加载新列

**P0-5 审计中间件自动捕获 ip/ua + 查询接口**
- [ ] 后端：统一 `write_audit_log` 中间件/依赖自动捕获 `ip_address`、`user_agent`（替换当前手写调用点，消除永远 NULL）
- [ ] 后端：补审计查询接口 `GET /audit/logs`（按 resource_type/action/时间/actor 过滤），鉴权 `system_admin`
- [ ] 前端：审计台页面（admin-only），时间线 + 过滤 + 哈希链校验入口

**P0-6 审计哈希链（防篡改）**
- [ ] 后端：`police_audit_logs` 增 `prev_hash` + `record_hash`（设计见 §7.2.9）；每条记录写入时链接前一条哈希
- [ ] 后端：`GET /audit/{id}/verify` 重算哈希验证完整性，返回是否被篡改

**P0-7 运行时控制台仅 `system_admin` 可见**
- [ ] 后端：`/runtime/*` 全部接口加 `require_admin`
- [ ] 后端：`police_runtime_sessions` 落库（运行态轮询数字警察当前节点/工具/状态）
- [x] 前端：运行时控制台入口仅 `system_admin` 显示；四档干预（暂停/回收/跳子会话/终止）均鉴权

### 🟠 P1：协作深化（P0 完成后）

**P1-1 案件编排智能体自动拆解任务**（AI 智能体专家）
- [ ] 监听案件创建/材料上传事件，基于案情推荐任务模板与依赖
- [ ] 指挥员确认/调整后批量建任务（复用 `police_task_service.create_task`，走审计）

**P1-2 任务依赖 `blocked_by` 真正消费**（后端）
- [ ] 任务开始前校验依赖是否全部 `completed`，未满足则阻塞
- [ ] 依赖任务完成时触发下游任务（拓扑触发，替代当前串行 `for` 派发）
- [ ] 智能体并行派发（多 agent 任务可并发，带执行租约）

**P1-3 审核工作台三栏页面**（前端，参考 MateClaw 设计）
- [ ] 左栏：待审列表（按状态/风险/等待时长筛选）
- [ ] 中栏：AI 产出 + 审批链 + 驳回/要求修订/通过
- [ ] 右栏：原始证据、规范条款、历史先例、置信度、模型信息

**P1-4 产物结构化报告 + 版本/状态/签名**（后端+前端）
- [ ] 后端：`police_artifacts` 支持版本、状态、签名；任务产出可生成 Office/PDF 结构化文书
- [ ] 前端：产物查看/导出/版本对比

**P1-5 证据验证端点**（后端，闭环 v1.x「只写未读」）
- [ ] 后端：`GET /evidence/{id}/verify` 重算 `file_hash` + `signed_hash` 校验完整性与签名真实性
- [ ] 前端：证据详情页「验证」按钮 + 校验结果展示

### 🟢 P2：扩展能力（中长期）

**P2-1 数字警察角色卡结构化字段 + 前端表单**（后端+前端）
- [ ] 后端：`police_agents` 的 `role`/`goal`/`backstory` 独立字段（替代塞进 `system_prompt` 大文本）；角色卡渲染为 `system_prompt` 并版本化（见 §8.2）
- [ ] 前端：数字警员创建/编辑表单（角色卡结构化输入）

**P2-2 Workflow DSL + 案件模板**（后端）
- [ ] 可发布/可重放的案件流程（step 编排 + trigger），复用 `task_flow_rules`

**P2-3 技能 manifest 解析 + MCP 工作区归属**（后端）
- [ ] 数字警察能力以 SKILL.md manifest 解析 + 安全扫描；MCP 按案件工作区归属隔离

**P2-4 知识引用溯源（LLM Wiki）**（AI 智能体专家）
- [ ] 案件材料消化为带 `[[链接]]`、可点引用溯源的结构化页面（复用 Milvus 向量 + 证据关联）

---

## 规划中（待排期）

### 案件记忆 Case Memory（M3.5，v1.6 已规划）
- [ ] T1 数据模型 `police_case_memory_blocks` + `ensure_business_schema()` 建表
- [ ] T2 案件记忆服务：共享层/个案层双层读写 + provenance 可逆白盒
- [ ] T3 事件抽取管线：建案+笔录分析→共享层；任务完成→个案层
- [ ] T4 人工确认落盘（`pending_confirmation` 模式）
- [ ] T5 召回：BM25+向量+RRF 检索替换「单文件全量注入」
- [ ] T6 权限隔离：仅参案角色可见
- [ ] T7 结案归档：转只读归入案卷，可审计/可导出
- [ ] T8 跨案反哺：可泛化经验沉淀为智能体长期记忆/已学 SOP
- [ ] T9 案件维度记忆开关 + 确认/编辑 UI
- [ ] T10 与 `task_templates` / `advancement` 管线耦合对齐

### 专业智能体（原 Phase 3，待排期）
- [ ] 资金分析智能体、调证智能体、法制审核智能体、案件编排智能体深化
- [ ] 任务自动流转引擎完善（`task_flow_rules` 条件触发 + 事件监听）

### 知识库与图谱（原 Phase 4，待排期）
- [ ] 按案件隔离知识库、公安知识图谱 Schema、材料实体抽取 → Neo4j + Milvus、图谱可视化与碰撞分析

### 安全加固与交付（原 Phase 5/6，待排期）
- [ ] PII 脱敏中间件、工具防护层、案件级数据隔离强化、性能优化、Docker 离线部署、端到端/安全/压力测试、培训交付

---

## 决策待确认

- [ ] **证书类型字段 (evidence_type 补充)**: 证据/证书类型枚举待产品确认（如警官证、立案决定书、银行回执等专用类型），确认后补入 `EVIDENCE_TYPE` 与前端筛选。

## 已知技术债（来自文档 §0.2，建议排入后续迭代）

- [ ] **推进触发不可靠**: 推进智能体仅靠进程内单例 + 串行 `create_task` 近似幂等，无分布式锁；多副本部署存在并发重复触发风险。
- [ ] **只签名不验证**: `evidence_repository.review()` 与 `review_task()` 写入 `signed_hash`，但无对应校验端点（P1-5 闭环）。
- [ ] **TaskEvent 无消费者**: `police_task_events` 仅用于时间线展示，任务流转规则并不由事件驱动。
- [ ] **图谱/向量未接入**: Neo4j、Milvus 在所有 police 代码中无调用（知识图谱尚未启动）。

## Phase 0 / 1 遗留 (联调测试)

- [x] **后端端到端测试**: 新增 `test/integration/api/test_police_business_router.py`
- [ ] **前端联调**: 前后端对接，验证案件/任务/证据全流程（待 Docker 联调）
- [x] **证据文件上传**: `upload_evidence` 已调用 `aupload_file` 落 MinIO；补全 `download` / `preview` 端点 + 上传审计
- [x] **任务流转规则引擎验证**: 引擎已在 `complete_task` 接线；`flow-rules` 配置 API + 端到端测试
- [x] **审计日志全量覆盖**: 案件/智能体/任务全部操作 + 证据上传/审核 审计埋点，统一收敛到 `write_audit_log`
- [ ] **Docker 本地启动联调**: `docker compose up` 验证 PostgreSQL + 后端 + 前端全链路
- [ ] **权限模型扩展**: 实现 `system_admin`/`user` 平台角色 + 案件层四角色（见 P0-1/P0-2）

---

## 里程碑追踪

| 里程碑 | 状态 | 说明 |
|--------|------|------|
| M0: 语析底座跑通 | ✅ 完成 | Fork 运行 + 用户模型扩展 + LLM 配置 |
| M1: 案件管理可用 | ✅ 代码完成 / ⏳ 待联调 | 案件-任务-证据 + 工作台 |
| M1.5: 数字警员 | ✅ 完成 | StaffDeck 融合 + 数字警员 + SOP + 手绘风格 UI |
| M2: 智能创建上线 | ✅ 闭环代码完成 / ⏳ 待 OCR 与真实 LLM 联调 | 笔录分析智能体 + 案件智能创建 |
| **M2.1: 权限与安全地基（v2.1 P0）** | 🔴 **进行中** | 平台角色 + 案件成员 + 审核人规则 + 审批 RBAC + 审计中间件/查询/哈希链 + 运行时控制台 admin 独占 |
| M2.2: 协作深化（v2.1 P1） | ⬜ 待 P0 | 编排拆解 + 依赖消费 + 审核工作台 + 产物结构化 + 证据验证 |
| M3: 专业智能体 | ⬜ 未开始 | 资金/调证/法制/编排深化 |
| M3.5: 案件记忆 | 📋 规划中 | 双层案件记忆 + 事件抽取 + 结案归档 |
| M4: 知识图谱 | ⬜ 未开始 | 知识库 + 知识图谱 + 可视化 |
| M5: 安全加固 | ⬜ 未开始 | PII 脱敏 + 隔离 + 渗透测试 |
| M6: 正式交付 | ⬜ 未开始 | 完整平台 + 部署文档 + 培训 |

---

## 代码统计（末次统计 v1.6，Phase 1.5 后）

| 模块 | 文件数 | 代码行 |
|------|--------|--------|
| 后端 - 数据模型 | 2 (1新+1改) | ~466 |
| 后端 - Repository | 3 | ~445 |
| 后端 - Service | 1 | 265 |
| 后端 - Router | 4 (新) + 1 (改) | ~550 |
| 后端 - 配置/迁移 | 3 改 | ~260 |
| 前端 - API/Store | 2 (新) + 1 (改) | ~207 |
| 前端 - 视图组件 | 7 | ~2,431 |
| 前端 - 路由/布局 | 2 改 | ~67 |
| 文档 | 2 (1新+1改) | ~2,400 |
| **合计** | **29 文件** | **~7,091 行** |

---

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3.5 · Vite 8 · Ant Design Vue 4.2 · Pinia · vue-router |
| 后端 | FastAPI · LangGraph · ARQ · SQLAlchemy (async) |
| 存储 | PostgreSQL · Redis · MinIO · Milvus · Neo4j |
| LLM | OpenAI 兼容 API（**仅自建 `agnes:agnes-2.5-flash` 内网接口，无多厂商故障转移**） |
| 部署 | Docker Compose（支持离线部署） |

---

## 关键设计决策

1. **复用 Yuxi Base**: `models_police.py` 导入 `models_business.py` 的 `Base`，确保 `create_tables()` 自动创建 police 表
2. **运行时 SQL 迁移**: 无 Alembic，通过 `manager.py` 的 `ensure_business_schema()` 幂等建表
3. **证据双哈希**: `file_hash` (SHA-256 文件内容) + `signed_hash` (SHA-256 of reviewer_police_id[警号] + reviewed_at + 内容哈希)
4. **单一 LLM Provider**: 仅保留 `custom-openai`，仅绑内网自建 `agnes`（**不采纳多厂商故障转移/厂商健康**）
5. **前端 Ant Design Vue**: 使用 Yuxi 原生 UI 库，手绘风格 CSS 主题叠加
6. **任务流转引擎**: `TaskFlowRule` 条件触发自动创建后续任务
7. **数字警员概念** (融合 StaffDeck): 每位 AI 智能体有完整身份档案、能力矩阵、工作统计和成长记录
8. **SOP 状态机** (融合 StaffDeck): 将公安办案流程定义为结构化 SOP
9. **手绘风格 UI** (融合 StaffDeck): 纸质感卡片 + 草图线条 + 暖色调 + 不规则圆角

### v2.1 新增决策（2026-08-04）

10. **两大核心支柱**: ①数字警察为一等公民（与普通用户并列，可对话/可加入案件/可被审核）；②案件驱动协作（用户发起 → 编排智能体拆解 → 分配给人或数字警察 → 产出 → 用户审核 → 推进阶段）
11. **协作模型本质差异**: 小南是「多个用户 + 多个数字警察共同围着一块案件任务板」，不同于 MateClaw「1 人类指挥 ↔ 1 纯 agent 团队」
12. **权限分层**: 平台层 `system_admin` / `user` + 案件层 `commander`/`executor`/`reviewer`/`observer`；运行时控制台 / 全局审计台 / 数字警员管理 **仅 system_admin 可见**
13. **审核人判定规则**: `both`→指定用户；`agent`→指挥员(可改派)；`user`→无需审核；改派必写审计
14. **对照 MateClaw 取长补短**: 借鉴其团队编排/审批卡点/审计/运行时/工作流表达，保留小南公安特化（存证哈希/密级/内网私有化）
