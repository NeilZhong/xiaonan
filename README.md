<div align="center">
<h1>智案协 Xiaonan</h1>

<p><strong>公安多智能体协作平台</strong><br/>基于语析 Yuxi 二次开发，面向公安办案场景的「案件 · 任务 · 数字警员 · 证据」全链路协同工作台</p>

[![Fork](https://img.shields.io/badge/Fork%20from-Yuxi-24839b?style=flat)](https://github.com/xerrors/Yuxi)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat)](LICENSE)
[![Vue](https://img.shields.io/badge/Vue-3.5-42b883?style=flat&logo=vuedotjs&logoColor=fff)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=fff)](https://fastapi.tiangolo.com/)
[![Branch](https://img.shields.io/badge/branch-beta__v1.0.1-c8665cf6-success?style=flat)](https://github.com/NeilZhong/xiaonan)

</div>

---

## 目录

- [一、项目简介](#一项目简介)
- [二、两大支柱与核心能力](#二两大支柱与核心能力)
- [三、技术栈](#三技术栈)
- [四、系统架构](#四系统架构)
- [五、目录结构](#五目录结构)
- [六、数据模型](#六数据模型)
- [七、关键业务流程](#七关键业务流程)
- [八、安全与合规设计](#八安全与合规设计)
- [九、快速开始](#九快速开始)
- [十、开发规范与约束](#十开发规范与约束)
- [十一、配置说明](#十一配置说明)
- [十二、文档索引](#十二文档索引)
- [十三、当前阶段与路线图](#十三当前阶段与路线图)
- [十四、许可证与致谢](#十四许可证与致谢)

---

## 一、项目简介

**智案协（Xiaonan）** 是在 [语析 Yuxi](https://github.com/xerrors/Yuxi)（基于 LangGraph 的 RAG 知识库与多智能体平台）基础上二次开发的**公安多智能体协作平台**。它融合：

- **Yuxi** 的 RAG 知识库、LangGraph 多智能体编排、ARQ 异步任务队列能力；
- **StaffDeck** 的「数字员工」概念（档案 / 能力矩阵 / 工作统计 / 成长记录）；
- **Plane** 的项目管理交互设计（看板 / 列表 / 时间线）；
- 以及**公安办案业务规范**（笔录、证据存证、案件流转、审批留痕）。

平台定位为民警的「AI 协同办案工作台」：以**案件**为主线，由**编排智能体**自动拆解侦查任务并派发给**数字警员**与人类民警协同执行，关键动作由用户审核确认，全程审计溯源。

> 内部代号「智案协」。当前代码分支 `beta_v1.0.1`（详见 [POLICE_REQUIREMENTS.md](POLICE_REQUIREMENTS.md) 产品需求文档 v2.1）。

---

## 二、两大支柱与核心能力

平台围绕**两大支柱**设计（源自需求文档 v2.1「两大核心重新整理」）：

1. **数字警员（AI 数字员工）是一等公民** —— 每位数字警员拥有独立档案（警号 / 警衔 / 专长 / 部门）、能力矩阵、版本与发布控制、工作统计与成长记录，可像真实民警一样被「装备」「派遣」「评价」。
2. **案件驱动的多智能体协作** —— 以案件为中心，编排智能体（案件推进）自动生成任务草案 → 用户确认 / 改方向 → 任务分配（人或 AI）执行 → 用户审核闭环，并配套证据存证与审计。

### 功能模块一览

| 模块 | 说明 | 关键代码 |
| --- | --- | --- |
| **数字警员中心** | 档案页（悟帆 AI 员工风格）、能力区块（灵魂/技能/连接器/协助伙伴/记忆）、版本受控发布（流动版本 / 受控发布 / 回滚）、1–5 星评价 | `views/AgentProfileView.vue`、`AgentSectionView.vue`、`police_agent_router.py`、`police_agent_version_*` |
| **内置数字警员** | 7 名预置警员：DA-001 笔录分析师 / DA-002 资金追踪师 / DA-003 调证生成师 / DA-004 法制审核官 / DA-005 案件编排官 / DA-006 群聊分析专家 / DA-007 审讯辅助专家 | `services/police_prompts.py` |
| **协助伙伴** | 子智能体的独立管理入口，可与数字警员「装备」关联，构成协作网络 | `police_partner_router.py`、`PartnerManageView.vue` |
| **智能体对话** | 日常办公 / 能力演进 / 智能孵化 三 Tab 对话框（悟帆皮肤），承接 AgentRun 流式对话 | `views/AgentView.vue`、`agent_router.py` |
| **案件中心** | 案件列表、详情（多 Tab）、时间线、阶段流转、成员权限、统计驾驶舱 | `views/police/Case*View.vue`、`police_case_router.py` |
| **笔录分析 / 智能建案** | 上传或粘贴讯问/询问笔录 → OCR + LLM 抽取结构化信息 → 民警确认 → 一键建案并自动生成侦查任务 | `views/police/CaseImportView.vue`、`services/police_transcript_service.py` |
| **案件编排智能体** | 多智能体协作核心：分析案情 → 产出任务草案 / 改方向建议 / 阶段总结，交由用户审核 | `services/police_advancement_service.py`、`police_advancement_router.py` |
| **任务板** | 任务 9 态状态机、看板 / 日历 / 树 三视图、详情弹窗（多人/多智能体协同 + 动态审核权限）、任务流规则自动派生 | `components/police/Task*`，`police_task_router.py`（17 端点） |
| **侦查任务模板** | 「涉案要素 → 侦查任务」映射配置化，支持链式 `next_template_codes` 与占位符 | `police_task_template_router.py`、`TaskTemplateView.vue` |
| **案件工作区** | 每案独立存储命名空间 + 树状文件节点（上传/下载/移动/重命名） | `police_workspace_router.py`、`WorkspaceTab.vue` |
| **证据与存证** | 证据上传 + SHA-256 双哈希签名 + 证据关联链（证据链） | `police_evidence_router.py`、`EvidenceTab.vue` |
| **小南市场** | 探索/浏览数字警员与协作资产、申请使用、发布与审核流 | `police_market_router.py`、`ExploreView.vue` |
| **审核工作台** | 推进草案审阅、任务审核、复盘审阅、市场审核聚合 | `police_dashboard_router.py`、`ReflectionReviewView.vue` |
| **运行时控制台** | 系统管理员专属：回收/跳入子会话/终止运行中的 AgentRun | `RuntimeConsoleView.vue` |
| **审计留痕** | 全操作审计日志，可验证、可导查，符合公安信息化规范 | `police_audit_router.py`、`police_audit_logs` 表 |
| **个人工作台** | 待审查 / 待审核 / 待处理 / 通知 四组待办聚合（数据驾驶舱） | `PoliceDashboardView.vue`、`stores/police.js` |

> 后端警务相关路由共 **20 个 `APIRouter`、约 124 个端点**，全部挂载在 `/api/police/*` 与 `/api/agent*` 下。

---

## 三、技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3.5 · Vite 8 · Ant Design Vue 4.2 · Pinia（含持久化插件）· vue-router 5 |
| 图表/图谱 | ECharts 6 · @antv/g6 5 · D3 · Sigma/Graphology（知识图谱可视化） |
| 文件预览 | @file-viewer（Office / 工程格式 CAD·XMind·3D·PSD 等） |
| 后端 | FastAPI · LangGraph · ARQ（异步 worker）· SQLAlchemy(async) |
| 存储 | PostgreSQL 16 · Redis 7 · MinIO · Milvus 2.5（向量）· Neo4j 5.26（图谱） |
| 文档解析 | MinerU · PaddleX · RapidOCR（可选，`profiles: [all]`） |
| LLM | 单一 `custom-openai` 兼容接口（支持 vLLM / Ollama / 云端 API），当前模型 `custom-openai:agnes-2.5-flash` |
| 部署 | Docker Compose（支持离线 / `LITE_MODE` 轻量部署） |

---

## 四、系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          前端 (web/, Vite :5173)                       │
│  /police 公安工作台 · /agent 对话 · /agent-manage 数字警员 ·           │
│  /extensions 扩展 · /dashboard 总览 · /workspace 个人空间              │
│  所有请求经 /api 代理 → 后端                                           │
└───────────────────────────────┬─────────────────────────────────────┘
                                 │  HTTP /api/*   (SSE 流式)
┌───────────────────────────────▼─────────────────────────────────────┐
│                    后端 API (api-dev :5050, FastAPI)                   │
│  server/routers/*  ← 薄路由层                                         │
│  yuxi/services/*   ← 用例层（含 police_service 等业务服务）           │
│  yuxi/repositories/* ← PostgreSQL 访问边界                            │
│  lifespan 启动: ensure_business_schema() 自动建表                      │
└───────┬───────────────────────────┬─────────────────────────────────┘
        │ 派发 AgentRun             │ 业务读写
        ▼                           ▼
┌──────────────────┐   ┌──────────────────────────────────────────────┐
│  ARQ Worker       │   │  存储 / 中间件                                 │
│ (worker-dev)      │   │  PostgreSQL · Redis(队列/事件/缓存) · MinIO    │
│ 执行 LangGraph    │   │  Milvus(向量) · Neo4j(图谱)                    │
│ 任务截止提醒 cron │   └──────────────────────────────────────────────┘
└────────┬─────────┘
         │ 隔离执行代码/工具
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│  sandbox-provisioner (:8002) — 为智能体工具执行提供隔离沙盒            │
└─────────────────────────────────────────────────────────────────────┘
```

**运行链路要点**（详见 [ARCHITECTURE.md](ARCHITECTURE.md)）：

1. 普通智能体请求先落 PostgreSQL（消息 + `AgentRunRequest`），再按用户/智能体/线程做 FIFO 串行派发；
2. 派发后通过 Redis/ARQ 投递到 `worker-dev` 执行 LangGraph，运行事件写入 Redis Stream；
3. 最终状态与业务记录写回 PostgreSQL，前端通过 SSE 消费排队与运行事件；
4. 智能体能力由 context / middleware / toolkits / Skills / MCP / backends 组合，知识库、沙盒等逻辑不硬编码进页面。

**架构不变量**：Docker Compose 是开发环境事实来源；路由保持薄、用例放 `services`、持久化放 `repositories`；先提交 PostgreSQL 事实再投递 ARQ；前端 API 调用集中在 `web/src/apis`。

---

## 五、目录结构

```
xiaonan/
├── POLICE_REQUIREMENTS.md     # 产品需求文档 (v2.1) —— 功能与验收权威来源
├── ARCHITECTURE.md            # Yuxi 代码地图（系统边界 / 运行链路 / 不变量）
├── AGENTS.md / CLAUDE.md      # 开发准则与行为约定
├── docker-compose.yml         # 服务编排（api/worker/web/postgres/redis/minio/...）
├── docker/                    # Dockerfile 与 sandbox-provisioner 等
├── backend/
│   ├── server/                # Web 入口与 HTTP 适配层
│   │   ├── main.py            #   创建 FastAPI app，挂载 /api
│   │   ├── routers/           #   路由边界（含 20 个 police_*_router.py）
│   │   └── utils/lifespan.py  #   启动建表、初始化中间件/知识库/Redis/沙盒
│   └── package/yuxi/          # 业务与基础设施主体（editable install）
│       ├── agents/            #   LangGraph 智能体体系
│       ├── services/          #   用例层（police_service / police_advancement_service / ...）
│       ├── repositories/      #   PostgreSQL 访问（police_agent_repository 等）
│       ├── storage/postgres/  #   ORM 模型（models_business / models_police / manager）
│       ├── models/providers/  #   LLM provider（custom-openai 等）
│       ├── knowledge/         #   知识库 / 解析 / 图谱
│       └── config/            #   系统/用户级配置
├── web/
│   └── src/
│       ├── apis/              # 后端接口封装（police_api.js 等 22 个模块）
│       ├── stores/            # Pinia（police.js / agent.js / user.js / ...）
│       ├── views/             # 页面（police/ 13 个 + agent* + dashboard 等）
│       ├── components/police/ # 任务看板/日历/树、详情弹窗、属性浮层等 16 个
│       ├── router/            # 路由（8 组：police/agent/agent-manage/extensions/...）
│       └── assets/css/base.css# 全局样式与颜色变量（警察蓝主题）
├── docs/                      # VitePress 文档站（intro/agents/advanced/develop-guides）
└── scripts/                   # 初始化与迁移脚本（init.sh / init.ps1 / migrate_*）
```

---

## 六、数据模型

公安业务通过**运行时 SQL 迁移**（`ensure_business_schema()`，无 Alembic）自动建表。当前警务相关表 **20+ 张**，按职责分组：

| 分组 | 表 |
| --- | --- |
| 案件 | `police_cases` · `police_case_members` · `police_case_phases` · `police_case_workspaces` · `police_workspace_nodes` |
| 任务 | `police_tasks` · `police_task_assignees` · `police_task_flow_rules` · `police_task_events` · `police_task_comments` · `police_task_templates` · `police_notifications` |
| 证据 | `police_evidence` · `police_evidence_links` |
| 数字警员 | `police_agent_runs` · `police_agent_comments` · `police_agent_connections` · `police_agent_versions` · `police_agent_release_state` · `police_sops` |
| 协作/治理 | `police_advancement_logs` · `police_reflection_records` · `police_audit_logs` |

> **重要变更（beta_v1 起）**：原 `police_agents` 表已**删除并单表化合并到共享 `agents` 表**（`storage/postgres/models_business.py`）。数字警员现在是 `agents` 表中的一类记录，新增字段包括 `badge_number`（警号，仅全局共享审核通过后授予）、`rank`、`specialty`、`department`、`category`、`agent_type`、`status`、`system_prompt`、`skills`、`sop_ids`、`capabilities`、`approval_status`、`work_stats`、`growth_log` 等。`/api/police/agents` 与 `/api/agent` 读写同一批记录。
>
> `users` 表扩展了 `real_name` / `police_id` / `police_rank` 字段（民警真实身份）。

---

## 七、关键业务流程

**① 笔录分析 → 智能建案**
`CaseImportView` 上传/粘贴笔录 → `police_transcript_service` 调 OCR + LLM 抽取结构化案件信息 → 民警在确认页校正 → 一键创建案件并基于「侦查任务模板」自动派生初始任务。

**② 案件推进（编排智能体）**
`police_advancement_service` 多智能体协作：读取案情/任务进展 → 产出「任务草案 / 改变方向建议 / 阶段总结 / 无动作」四类决策日志（`police_advancement_logs`）→ 用户在审核工作台确认或驳回，确认后真正创建/调整任务。

**③ 任务闭环**
任务 9 态状态机：创建 → 分配（人/AI）→ 开始 →（AI 自动执行）→ 完成 → 审核；审核不通过可打回。任务流规则（`police_task_flow_rules`）可条件触发自动派生后续任务。每日 08:30 由 ARQ cron 推送截止提醒（`police_notifications`）。

**④ 数字警员执行**
对话/任务派发给数字警员 → 走标准 AgentRun 链路（见架构）→ 运行结果回写 `police_agent_runs` 与工作统计；版本受控发布保证线上警员稳定，草稿可回滚。

---

## 八、安全与合规设计

### 证据链双哈希签名
```
file_hash   = SHA-256(file_bytes)                            # 文件内容哈希
signed_hash = SHA-256(police_id + reviewed_at + file_hash)   # 审核签名哈希
```
每次证据审核计算双哈希并落库，确保证据不可篡改、可溯源。

### 审计留痕
所有关键操作写入 `police_audit_logs`，支持按案件查询与验证（`police_audit_router.py`）。

### LLM 离线/可控部署
仅保留 `custom-openai` 单一 provider，支持 vLLM / Ollama 本地推理或云端 API，模型在管理面板可配置；移除多厂商故障转移，避免不可控外部依赖。

### 权限模型
三级前端守卫（`requiresAuth` / `requiresAdmin` / `requiresSuperAdmin`）+ 后端 FastAPI 依赖（`get_required_user` 等）做最终授权；前端守卫只负责体验，后端校验才是边界。

---

## 九、快速开始

### 前置要求

- **Docker Desktop** + Docker Compose（后端依赖容器）
- **Node.js 22+**（前端本地 Vite 进程，不跑在容器内）
- 一个 OpenAI 兼容的 LLM 服务（当前默认 `custom-openai:agnes-2.5-flash`）

### 1. 获取代码

```bash
git clone https://github.com/NeilZhong/xiaonan.git
cd xiaonan
git checkout beta_v1.0.1
```

### 2. 配置环境变量

```bash
cp .env.template .env
```

编辑 `.env` 至少补全：`POSTGRES_PASSWORD`、`MINIO_ACCESS_KEY/SECRET`、`SANDBOX_PROVISIONER_TOKEN`（见 `.env.template` 注释），以及 LLM 配置：

```env
YUXI_DEFAULT_MODEL=custom-openai:agnes-2.5-flash
OPENAI_API_BASE=https://your-llm-endpoint/v1
OPENAI_API_KEY=your-key
```

### 3. 启动后端（Docker）

```bash
# 启动核心后端服务（api / worker / postgres / redis / minio / sandbox-provisioner）
docker compose up -d api worker postgres redis minio sandbox-provisioner

# 如需知识图谱与向量检索，追加 graph milvus etcd：
# docker compose up -d api worker postgres redis minio sandbox-provisioner graph milvus etcd

# 轻量模式（跳过知识库/图谱/评估重依赖）：在 .env 设 LITE_MODE=true
```

> 容器 `api-dev` 启动即执行 `ensure_business_schema()` 自动建表，健康检查 `GET /api/system/health` 返回 200 即就绪。`worker-dev` 的 arq 进程若显示 `<defunct>`，通常是启动期撞上 postgres 未就绪的瞬时竞态——待 postgres Healthy 后 `docker restart worker-dev` 即可恢复。

### 4. 启动前端（本地 Vite）

```bash
cd web
pnpm install        # 或 npm install
VITE_API_URL=http://localhost:5050 pnpm run dev
```

前端默认监听 `http://localhost:5173`，通过 `/api` 代理打到后端 `:5050`。

### 5. 访问平台

浏览器打开 `http://localhost:5173`，使用初始化生成的管理员账户登录（具体账户/密码见 `.env` 与初始化脚本输出）。

登录后可见：工作台（待办聚合）、案件管理、任务板、数字警员、小南市场、扩展中心等。

---

## 十、开发规范与约束

- **禁止覆盖 Yuxi 核心模块**：新增后端功能放独立文件（如 `police_*_repository.py`、`police_*_router.py`、`services/police_*.py`），不要改动 `yuxi` 核心逻辑。
- **数据库迁移走运行时建表**：使用 `ensure_business_schema()` 的 `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`，**无 Alembic**。
- **前端品牌为「小南 / Xiaonan」**：禁止添加 GitHub Star 卡片 / 仓库外链（品牌约束）。
- **代码结构约定**：Router 薄、用例放 `services`、持久化放 `repositories`；前端 API 调用集中在 `web/src/apis`，组件不散落拼接 HTTP。
- **前端技术约定**：Composition API + `<script setup>`；图标优先 `lucide-vue-next`；样式用 Less 并复用 `assets/css/base.css` 颜色变量；API 定义在 `web/src/apis`。
- **测试分层**：`backend/test` 下 `unit` / `integration` / `e2e`；提交前确保相关测试通过。

---

## 十一、配置说明

| 变量 | 说明 | 默认 |
| --- | --- | --- |
| `LITE_MODE` | `true` 时跳过 knowledge/graph/evaluation/external_kb 路由，省掉 neo4j+milvus+etcd | `false` |
| `POSTGRES_URL` / `REDIS_URL` / `MINIO_URI` / `NEO4J_URI` / `MILVUS_URI` | 各存储连接串 | 见 `docker-compose.yml` |
| `SANDBOX_PROVISIONER_TOKEN` | 沙盒调度鉴权令牌（**必填**，否则 api/worker 启动失败） | — |
| `YUXI_DEFAULT_MODEL` | 默认 chat 模型，格式 `custom-openai:<model>` | `custom-openai:agnes-2.5-flash` |
| `OPENAI_API_BASE` / `OPENAI_API_KEY` | LLM 兼容接口地址与密钥 | — |
| `VITE_API_URL` | 前端连后端的地址（本地开发设为 `http://localhost:5050`） | `http://api:5050`（容器内） |

LLM Provider 现状：`agnes` **不是**独立 provider，而是 `custom-openai` 下的模型名 `agnes-2.5-flash`；默认 embedding `text-embedding-3-small`、reranker `qwen3-rerank`，均可在管理面板调整。

---

## 十二、文档索引

- [POLICE_REQUIREMENTS.md](POLICE_REQUIREMENTS.md) —— 产品需求文档（v2.1），功能与验收权威来源，含 14 章（概述/术语/两大支柱/角色权限/架构/功能模块/数据模型/安全合规/部署）。
- [ARCHITECTURE.md](ARCHITECTURE.md) —— 后端/前端代码地图、运行链路与架构不变量。
- [AGENTS.md](AGENTS.md) / [CLAUDE.md](CLAUDE.md) —— 开发准则与行为约定。
- `docs/`（VitePress 文档站）：
  - `docs/intro/` 项目概览、快速开始、模型配置、知识库、评估
  - `docs/agents/` 智能体配置、请求队列、工具系统、中间件、沙盒、MCP、Skills、SubAgents
  - `docs/advanced/` 配置、部署、Langfuse、文档处理、品牌、第三方鉴权
  - `docs/develop-guides/` 贡献规范、路线图、变更日志、设计规范（design.md）、测试规范
  - `docs/vibe/` 需求/设计评审沉淀（如「智能体 × 数字警员合并」PRD）

---

## 十三、当前阶段与路线图

- **当前阶段：Phase 2** —— 笔录分析智能体、案件智能创建（对话/模板一键建案 + 工作区初始化），并持续完善工作区权限、文件版本、证据存证校验、数字警员产物自动落盘。
- 近期已落地能力（beta_v1.0.1）：AI 数字警员协同工作流、任务详情/创建弹窗 + AI 执行闭环、任务时间链与截止提醒、多视图任务看板、智能体单表化与版本受控发布、小南市场、办案复盘、协助伙伴管理、工作台三 Tab（能力演进 / 智能孵化）。
- 路线图详见 `docs/develop-guides/roadmap.md` 与 `todo.md`。

---

## 十四、许可证与致谢

本项目采用 **MIT 许可证**，详见 [LICENSE](LICENSE)。

基于 [语析 Yuxi](https://github.com/xerrors/Yuxi) 二次开发，融合 [StaffDeck](https://github.com/OpenBMB/StaffDeck) 数字员工概念与 [Plane](https://github.com/makeplane/plane) 项目管理交互设计，并借鉴 LangGraph / LightRAG / RAGflow / DeerFlow 等优秀开源项目的设计思想。感谢原作者及所有开源贡献者。

---

> 本文档基于 `beta_v1.0.1` 分支（HEAD `c8665cf6`）实际代码整理。如与代码不符，以代码为准；功能细节以 [POLICE_REQUIREMENTS.md](POLICE_REQUIREMENTS.md) 为准。
