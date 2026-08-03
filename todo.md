# 智案协 — 项目进度与待办

> **最后更新**: 2026-08-03
> **当前里程碑**: M0 ✅ → M1 ✅ → M1.5 ✅ → M2 ✅ (闭环) → M3 ✅ 主体 (推进管线+任务模板) → M4 ⬜ (图谱未启) → M5 ⚠️ (安全部分) → M6 ⬜
> **开发文档**: [POLICE_REQUIREMENTS.md](./POLICE_REQUIREMENTS.md) **v1.5**（文档—代码对齐版，已修正此前与代码不符的描述）

---

## 已完成

### Phase 0: 语析底座接入 ✅

| 任务 | 状态 | 说明 |
|------|------|------|
| Fork xerrors/Yuxi，clone 到本地 | ✅ | `NeilZhong/xiaonan` → `D:\project\xiaonan` |
| 熟悉语析架构 (server + package 分层) | ✅ | server/routers (HTTP) + package/yuxi (核心库) |
| 扩展用户模型 (警号/警衔/真实姓名) | ✅ | `models_business.py` + `manager.py` SQL 迁移 |
| LLM 配置精简为单一 OpenAI 兼容 API | ✅ | `custom-openai` provider，支持 vLLM/Ollama |
| Git 初始化 + 首次提交 + Push GitHub | ✅ | commit `255550b4`，SSH 认证 |
| README.md 重写 | ✅ | 智案协平台说明 |
| 开发文档编写 | ✅ | POLICE_REQUIREMENTS.md v1.2 (11 章 2189 行) |

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
- ✅ 前端 `vite build` 成功 (0 errors, 44.64s)
- ✅ npm 445 packages, 0 vulnerabilities

---

## 待完成

### v1.5 文档—代码对齐（2026-08-03 完成）

- [x] **需求文档对齐代码**: `POLICE_REQUIREMENTS.md` 升到 **v1.5**（文档—代码对齐版）。修正了与代码严重不符的描述：数据模型主键/表名前缀、API 前缀 `/api/v1/*`→`/api/police/*`、推进智能体实现（非 LangGraph 状态机/非 ARQ，而是 `review_task` 后 `asyncio.create_task` 触发的顺序管线）、数字警员表结构、证据签名用 `reviewer_police_id` 而非 `reviewed_by` 等；补写了已实现但文档缺失的模块：侦查任务模板体系(§4.9)、案件工作区文件系统(§4.10)、数字警员市场与共享审批(§4.11)、任务多执行人(§5.2.3)。**换机后 `git pull` 即可看到最新文档。**
- [ ] **补写 DA-006 / DA-007 PRD 小节**: 群聊分析专家、审讯辅助专家已在 `PRESET_AGENTS` 落地，但文档 §6 尚未为其单独成节（当前标「待补写」）。
- [ ] **DA-005 命名冲突**: 代码内 `case_orchestrator`(案件编排官) 同时承担「推进智能体」职责，命名/职责需与文档统一（见文档 §0.2 技术债）。

### 决策待确认

- [ ] **证书类型字段 (evidence_type 补充)**: 证据/证书类型枚举待产品确认（如警官证、立案决定书、银行回执等专用类型），确认后补入 `EVIDENCE_TYPE` 与前端筛选。**⏰ 2026-08-04 前确认**（用户原话：证书类型明天再确认）。

### 已知技术债（来自文档 §0.2，建议排入后续迭代）

- [ ] **推进触发不可靠**: 推进智能体仅靠进程内单例 + 串行 `create_task` 近似幂等，无分布式锁；多副本部署存在并发重复触发风险。
- [ ] **只签名不验证**: `evidence_repository.review()` 与 `review_task()` 写入 `signed_hash`，但无对应的校验端点；诉讼/监察时无法在系统内自证完整性与签名真实性（§9.5.3 验证函数未实现）。
- [ ] **TaskEvent 无消费者**: `police_task_events` 仅用于时间线展示，任务流转规则并不由事件驱动。
- [ ] **图谱/向量未接入**: Neo4j、Milvus 在所有 police 代码中无调用（M4 知识图谱尚未启动）。

### Phase 0 遗留

- [ ] **权限模型扩展**: 实现 admin/chief/officer/legal 四级角色（当前使用 Yuxi 基础权限）
- [ ] **验证语析中间件可用性**: 审批中间件 (checkpoint resume) + SubAgents + 沙盒文件系统
- [ ] **Docker 本地启动联调**: `docker compose up` 验证 PostgreSQL + 后端 + 前端全链路

### Phase 1 遗留 (联调测试)

- [x] **后端端到端测试**: 新增 `test/integration/api/test_police_business_router.py`（案件/任务/证据/流转引擎/审计/工作台主链路，5 个用例），需 `docker compose` 起的 api+PG+MinIO 跑通
- [ ] **前端联调**: 前后端对接，验证案件/任务/证据全流程（待 Docker 联调）
- [x] **证据文件上传**: `upload_evidence` 已调用 `aupload_file` 落 MinIO（之前描述过时）；本轮补全 `download` / `preview` 端点 + 上传审计
- [x] **任务流转规则引擎验证**: 引擎已在 `complete_task` 接线；本轮新增 `flow-rules` 配置 API（增/查/删）+ 端到端测试验证"完成任务自动建后续任务"
- [x] **审计日志全量覆盖**: 案件/智能体原本已有；本轮补齐 **任务全部操作**（创建/分配/开始/完成/审核）+ **证据上传/审核** 审计埋点，统一收敛到 `write_audit_log`

### Phase 1.5: 数字警员平台 (融合 StaffDeck) ✅

融合 StaffDeck 数字员工概念 + 手绘风格 UI，将公安智能体升级为"数字警员"。

#### 后端

| 任务 | 状态 | 文件 | 说明 |
|------|------|------|------|
| 扩展 PoliceAgent 模型为数字警员 | ✅ | `models_police.py` | 新增档案(工号/警衔/专长/头像/部门)、能力矩阵、工作统计、成长记录、SOP 关联 |
| 新增 PoliceSOP 模型 (状态机驱动 SOP) | ✅ | `models_police.py` | SOP 流程技能定义(状态节点/转移规则/输入输出) |
| SQL 迁移 (新列 + 新表) | ✅ | `manager.py` | police_agents 扩展列 + police_sops 建表 |
| 数字警员仓储 | ✅ | `agent_repository.py` | CRUD + 工作统计 + 成长记录 + 运行记录 + SOP 管理 |
| 数字警员服务层 | ✅ | `police_service.py` | PoliceAgentService + 5 名预设数字警员 + seed 接口 |
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
- ✅ 前端 `vite build` 成功 (0 errors, 51.20s)

### Phase 2: 笔录分析智能体 + 案件智能创建 (3周)

> 2026-08-01 推进：已落地「上传笔录 → AI 分析 → 民警确认 → 建案并生成任务」最小闭环（后端 + 前端）。实现方式较原计划的调整见各项说明。

- [x] **笔录信息提取 → 结构化案件信息 JSON**：`police_transcript_service.analyze_transcript` 复用 `load_chat_model(agnes)` 调 LLM，结构化提取案件概览（案由/当事人/时间地点/金额/关键事实）+ 建议任务列表
- [x] **自动创建案件 + 生成初始任务列表**：`POST /police/import/transcript/confirm` 复用 `police_case_service.create_case` + `police_task_service.create_task`（自动走审计埋点）
- [x] **案件导入流程页面**：`web/src/views/police/CaseImportView.vue`（上传/粘贴 → 分析 → 可编辑概览+任务 → 确认建案）+ 路由 `/police/import` + 案件列表「导入笔录」入口按钮
- [x] **集成 Yuxi OCR 引擎（解析 PDF/图片）**：复用 `ocr_service.parse_document`（统一 OCR 网关，内部选 MinerU/PaddleX）；代码已接，best-effort——文本路径无需 OCR 即可跑，PDF/图片需 `docker compose up -d mineru-api paddlex`（当前未启动）
- [~] **开发 `transcript_analysis` Skill（基于 Yuxi Skills 系统）**：实现方式调整——未注册为 Yuxi builtin Skill，而是作为独立 `police_*` 业务服务 + API（Yuxi Skills 偏 agent 工具集，笔录建案是带鉴权/审计/落库的业务流程，更适独立实现）；如需纳入 Skill 体系可后续补注册
- [~] **复用 Yuxi 审批中间件**：以「AI 分析 → 民警确认 → 建案」流程实现「产出需确认」约束；未接入 Yuxi 审批中间件机制（checkpoint resume），需确认是否符合预期

### Phase 3: 专业智能体开发 (4周)

- [ ] **资金分析智能体** (`fund_analysis` Skill)
  - [ ] 银行流水解析工具 (`toolkits/bank_statement.py`)
  - [ ] Python/Pandas/NetworkX 负责解析清洗追踪统计 (LLM 只读 Top 10 异常摘要)
  - [ ] 产出资金流向图 + 下级账户清单
  - [ ] 资金流向可视化 (AntV G6)
- [ ] **调证智能体** (`evidence_collection` Skill)
  - [ ] 法律依据检索 (知识库 RAG)
  - [ ] 调取通知书自动生成 (文书模板)
- [ ] **法制审核智能体** (`legal_review` Skill)
  - [ ] 复用 Yuxi 审批中间件实现人机协作
  - [ ] 程序/证据/定性三维度审核
- [ ] **案件编排智能体** (基于 Yuxi SubAgents)
  - [ ] 主智能体监听案件事件
  - [ ] 调度专业子智能体
  - [ ] 自动创建后续任务 (对接 TaskFlowRule 引擎)
- [ ] **任务自动流转引擎完善**: `task_flow_rules` 条件触发 + 事件监听

### Phase 4: 知识库与知识图谱 (3周)

- [ ] 按案件隔离知识库 (复用 Yuxi 多租户)
- [ ] 定义公安知识图谱 Schema (人员/账户/通讯/事件)
- [ ] 案件材料自动抽取实体关系 → Neo4j + Milvus 图谱
- [ ] 知识图谱可视化 (AntV G6 + Yuxi 图谱探索)
- [ ] 图谱分析: 最短路径 / 社团发现 / 跨案碰撞
- [ ] 法律知识库构建 (法律法规 / 案例 / 文书模板)

### Phase 5: 安全加固与优化 (3周)

- [ ] PII 脱敏中间件 (借鉴 Octop，移植为 Yuxi 中间件)
- [ ] 工具防护层 (智能体外部调用安全控制)
- [ ] 案件级数据隔离强化
- [ ] 审计日志全量覆盖验证
- [ ] 性能优化 (Worker 多副本 / 数据库索引 / 缓存)
- [ ] UI/UX 打磨 (参考 Plane 项目管理交互细节)
- [ ] Docker 生产部署配置 (离线部署 / GPU 支持)

### Phase 6: 测试与交付 (3周)

- [ ] 端到端测试 (模拟完整案件流程: 报案 → 侦查 → 结案 → 移送)
- [ ] 安全测试 (渗透测试 / 权限验证)
- [ ] 压力测试 (多案件并发)
- [ ] 部署文档 + 运维手册
- [ ] 用户培训材料
- [ ] 正式交付

---

## 里程碑追踪

| 里程碑 | 计划时间 | 状态 | 说明 |
|--------|----------|------|------|
| M0: 语析底座跑通 | 第 2 周 | ✅ 完成 | Fork 运行 + 用户模型扩展 + LLM 配置 |
| M1: 案件管理可用 | 第 6 周 | ✅ 代码完成 / ⏳ 待联调 | 案件-任务-证据 + 工作台，需 Docker 联调 |
| M1.5: 数字警员 | 第 7 周 | ✅ 完成 | StaffDeck 融合 + 数字警员 + SOP + 手绘风格 UI |
| M2: 智能创建上线 | 第 9 周 | ✅ 闭环代码完成 / ⏳ 待 OCR 与真实 LLM 联调 | 笔录分析智能体 + 案件智能创建 |
| M3: 多智能体协作 | 第 13 周 | ⬜ 未开始 | 资金分析+调证+法制+编排，任务自动流转 |
| M4: 知识图谱上线 | 第 16 周 | ⬜ 未开始 | 知识库+知识图谱+可视化+图谱分析 |
| M5: 安全加固完成 | 第 19 周 | ⬜ 未开始 | PII 脱敏+审计+隔离+渗透测试 |
| M6: 正式交付 | 第 22 周 | ⬜ 未开始 | 完整平台+部署文档+培训材料 |

---

## 代码统计

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
| LLM | OpenAI 兼容 API (vLLM / Ollama / DashScope / DeepSeek) |
| 部署 | Docker Compose (支持离线部署) |

---

## 关键设计决策

1. **复用 Yuxi Base**: `models_police.py` 导入 `models_business.py` 的 `Base`，确保 `create_tables()` 自动创建 police 表
2. **运行时 SQL 迁移**: 无 Alembic，通过 `manager.py` 的 `ensure_business_schema()` 幂等建表
3. **证据双哈希**: `file_hash` (SHA-256 文件内容) + `signed_hash` (SHA-256 of reviewer_police_id[警号] + reviewed_at.isoformat() + 内容哈希；证据=file_hash，任务=result_hash)
4. **单一 LLM Provider**: 仅保留 `custom-openai`，支持任何 OpenAI 兼容端点
5. **前端 Ant Design Vue**: 使用 Yuxi 原生 UI 库，手绘风格 CSS 主题叠加
6. **任务流转引擎**: `TaskFlowRule` 条件触发自动创建后续任务 (如资金分析完成 → 自动创建调证任务)
7. **数字警员概念** (融合 StaffDeck): 每位 AI 智能体有完整身份档案(工号/警衔/专长)、能力矩阵、工作统计和成长记录
8. **SOP 状态机** (融合 StaffDeck): 将公安办案流程定义为结构化 SOP，状态机保证复杂流程精确执行
9. **手绘风格 UI** (融合 StaffDeck): 纸质感卡片 + 草图线条 + 暖色调 + 不规则圆角
