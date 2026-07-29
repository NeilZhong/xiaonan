# 智案协 — 项目进度与待办

> **最后更新**: 2026-07-30
> **当前里程碑**: M0 ✅ → M1 ✅ (待联调) → M2 ⏳
> **开发文档**: [POLICE_REQUIREMENTS.md](./POLICE_REQUIREMENTS.md) v1.2

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

### Phase 0 遗留

- [ ] **权限模型扩展**: 实现 admin/chief/officer/legal 四级角色（当前使用 Yuxi 基础权限）
- [ ] **验证语析中间件可用性**: 审批中间件 (checkpoint resume) + SubAgents + 沙盒文件系统
- [ ] **Docker 本地启动联调**: `docker compose up` 验证 PostgreSQL + 后端 + 前端全链路

### Phase 1 遗留 (联调测试)

- [ ] **后端端到端测试**: 启动服务后测试所有 27 个 API endpoints
- [ ] **前端联调**: 前后端对接，验证案件/任务/证据全流程
- [ ] **证据文件上传**: 对接 Yuxi MinIO 文件存储，当前仅计算哈希未实际上传
- [ ] **任务流转规则引擎验证**: 配置 TaskFlowRule 后测试自动创建后续任务
- [ ] **审计日志全量覆盖**: 验证所有操作均写入 audit_logs

### Phase 2: 笔录分析智能体 + 案件智能创建 (3周)

- [ ] 开发 `transcript_analysis` Skill (基于 Yuxi Skills 系统)
- [ ] 集成 Yuxi OCR 引擎 (MinerU/PaddleX) 解析笔录 PDF/图片
- [ ] 笔录信息提取 → 结构化案件信息 JSON (涉案银行卡/微信号/嫌疑人等)
- [ ] 自动创建案件 + 生成初始任务列表
- [ ] 复用 Yuxi 审批中间件: 智能体产出需民警确认
- [ ] 案件导入流程页面 (上传笔录 → AI 分析 → 确认 → 创建案件)

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
| M2: 智能创建上线 | 第 9 周 | ⬜ 未开始 | 笔录分析智能体 + 案件智能创建 |
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
3. **证据双哈希**: `file_hash` (SHA-256 文件内容) + `signed_hash` (SHA-256 of police_id + reviewed_at + file_hash)
4. **单一 LLM Provider**: 仅保留 `custom-openai`，支持任何 OpenAI 兼容端点
5. **前端 Ant Design Vue**: 使用 Yuxi 原生 UI 库 (非 Naive UI)，Plane 视觉风格
6. **任务流转引擎**: `TaskFlowRule` 条件触发自动创建后续任务 (如资金分析完成 → 自动创建调证任务)
