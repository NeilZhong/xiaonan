<div align="center">
<h1>智案协 Xiaonan</h1>

<p><strong>公安多智能体协作平台</strong><br/>基于语析 Yuxi 二次开发，面向公安办案场景的案件 · 任务 · 证据全链路协同</p>

[![Fork](https://img.shields.io/badge/Fork%20from-Yuxi-24839b?style=flat&logo=github)](https://github.com/xerrors/Yuxi)
[![License](https://img.shields.io/github/license/xerrors/Yuxi?logo=github)](LICENSE)
[![Vue](https://img.shields.io/badge/Vue-3.5-42b883?style=flat&logo=vuedotjs&logoColor=fff)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=fff)](https://fastapi.tiangolo.com/)

</div>

---

## 项目简介

**智案协（Xiaonan）** 是在 [语析 Yuxi](https://github.com/xerrors/Yuxi) 基础上二次开发的公安多智能体协作平台。它融合了 [StaffDeck](https://github.com/OpenBMB/StaffDeck) 的数字员工概念、Yuxi 的 RAG 知识库与 LangGraph 多智能体编排能力、[Plane](https://github.com/makeplane/plane) 的项目管理交互设计，以及公安办案业务规范，提供 **案件管理 → 任务流转 → 证据链管理 → 数字警员协作 → 审计溯源** 的全链路数字化协同工作台。

### 核心能力

| 模块 | 说明 |
| --- | --- |
| 案件管理 | 案件创建/归档、多阶段流转（受理 → 侦查 → 结案）、成员权限管理、案件时间线 |
| 任务引擎 | 任务分配/领取/完成/审核闭环、任务流规则引擎（自动派生后续任务）、事件追踪 |
| 证据链管理 | 证据上传 + SHA-256 文件哈希 + 签名哈希（police_id + reviewed_at + file_hash）、证据关联链 |
| 数字警员 | 融合 StaffDeck 数字员工概念 — 每位 AI 有档案(工号/警衔/专长)、能力矩阵、工作统计、成长记录 |
| SOP 流程技能 | 状态机驱动的流程技能，将公安办案流程定义为可执行的结构化步骤 |
| 仪表盘 | 案件/任务/证据统计、个人待办、待审核任务一览 |
| 审计日志 | 全操作审计溯源，符合公安信息化规范 |
| LLM 接入 | 仅保留 OpenAI 兼容 API 接口，支持 vLLM / Ollama 等离线部署方案 |
| 手绘风格 UI | 融合 StaffDeck 手绘风格 — 纸质感卡片、草稿线条、暖色调 |

---

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3.5 · Vite 8 · Ant Design Vue 4.2 · Pinia · vue-router |
| 后端 | FastAPI · LangGraph · ARQ (异步 worker) · SQLAlchemy (async) |
| 存储 | PostgreSQL · Redis · MinIO · Milvus · Neo4j |
| 文档解析 | MinerU · PaddleX · RapidOCR |
| LLM | OpenAI 兼容 API（vLLM / Ollama / DashScope / DeepSeek 等） |
| 部署 | Docker Compose（支持离线部署） |

---

## 架构概览

```
xiaonan/
├── POLICE_REQUIREMENTS.md          # 公安业务开发文档 (v1.2)
├── backend/
│   ├── package/yuxi/               # 核心库（editable install）
│   │   ├── storage/postgres/
│   │   │   ├── models_business.py  # 基础业务模型（扩展 police 字段）
│   │   │   ├── models_police.py    # ★ 公安业务 ORM 模型 (11 张表)
│   │   │   └── manager.py          # 运行时 SQL 迁移（含 police 建表）
│   │   ├── repositories/
│   │   │   ├── case_repository.py  # ★ 案件仓储
│   │   │   ├── task_repository.py  # ★ 任务仓储
│   │   │   └── evidence_repository.py # ★ 证据仓储（含哈希签名）
│   │   ├── services/
│   │   │   └── police_service.py   # ★ 公安业务服务层 (案件+任务+仪表盘)
│   │   ├── config/app.py           # LLM 默认配置 (custom-openai)
│   │   └── models/providers/builtin.py # 自定义 OpenAI 兼容 provider
│   └── server/routers/
│       ├── police_case_router.py   # ★ 案件 API (8 endpoints)
│       ├── police_task_router.py   # ★ 任务 API (11 endpoints)
│       ├── police_evidence_router.py # ★ 证据 API (5 endpoints)
│       └── police_dashboard_router.py # ★ 仪表盘 API (3 endpoints)
└── web/src/
    ├── apis/police_api.js          # 公安业务 API 模块
    ├── stores/police.js            # Pinia 状态管理
    ├── layouts/AppLayout.vue       # 侧边导航（含公安菜单）
    ├── router/index.js             # 路由配置（含 /police/* 路由）
    └── views/police/               # 公安业务页面 (7 个 Vue 组件)
        ├── PoliceDashboardView.vue # 工作台仪表盘
        ├── CaseListView.vue        # 案件列表
        ├── CaseDetailView.vue      # 案件详情 (多 Tab)
        ├── TaskBoardView.vue       # 任务看板 (看板/列表双视图)
        ├── TaskDetailView.vue      # 任务详情 + 审核
        ├── EvidenceTab.vue         # 证据管理 Tab
        └── CaseTimeline.vue        # 案件时间线
```

---

## 数据模型

公安业务新增 11 张数据表（均通过运行时 SQL 迁移自动创建）：

| 表 | 说明 |
| --- | --- |
| `police_cases` | 案件主表（编号、标题、类型、阶段、状态） |
| `police_case_members` | 案件成员（user_id, role: commander/investigator/analyst） |
| `police_case_phases` | 案件阶段记录（research/investigation/closing/archive） |
| `police_tasks` | 任务表（类型、优先级、状态、分配、审核签名） |
| `police_task_flow_rules` | 任务流规则（条件触发自动创建后续任务） |
| `police_task_events` | 任务事件日志 |
| `police_evidence` | 证据表（file_hash + signed_hash 双哈希） |
| `police_evidence_links` | 证据关联关系 |
| `police_agents` | 公安智能体配置 |
| `police_agent_runs` | 智能体执行记录 |
| `police_audit_logs` | 审计日志 |

> `users` 表扩展了 `real_name`、`police_id`、`police_rank` 字段。

---

## 安全设计

### 证据链哈希签名（§9.5）

```
file_hash   = SHA-256(file_bytes)                           # 文件内容哈希
signed_hash = SHA-256(police_id + reviewed_at + file_hash)  # 审核签名哈希
```

每次证据审核时计算双哈希并写入数据库，确保证据链不可篡改、可溯源。

### LLM 离线部署

仅保留 `custom-openai` 单一 provider，支持：

- **vLLM**：本地 GPU 推理，兼容 OpenAI API
- **Ollama**：本地 CPU/GPU 推理
- **DashScope / DeepSeek**：云端 API（需外网）

---

## 快速开始

### 前置要求

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose
- 一个兼容 OpenAI 接口的 LLM 服务（vLLM / Ollama / 云端 API）

### 1. 克隆代码

```bash
git clone https://github.com/NeilZhong/xiaonan.git
cd xiaonan
```

### 2. 配置环境变量

```bash
cp .env.template .env
```

编辑 `.env`，填入 LLM 配置：

```env
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=http://localhost:8000/v1    # vLLM / Ollama / 云端
YUXI_DEFAULT_MODEL=custom-openai:gpt-4o
```

### 3. 启动服务

```bash
# 初始化
./scripts/init.sh        # Linux/macOS
.\scripts\init.ps1       # Windows PowerShell

# Docker 启动
docker compose up --build
```

### 4. 访问平台

浏览器打开 `http://localhost:5173`，使用初始化生成的管理员账户登录。

登录后侧边栏可见：
- **工作台** — 仪表盘、待办、待审核
- **案件管理** — 案件列表与详情
- **任务管理** — 任务看板与详情

---

## 开发说明

### 前端开发

```bash
cd web
npm install
npm run dev      # 开发服务器 (http://localhost:5173)
npm run build    # 生产构建
```

### 后端开发

```bash
cd backend
uv sync                  # 安装依赖
uv run python main.py    # 启动后端
```

### 代码结构约定

- **Repository 模式**：`repositories/` 层使用 `pg_manager.get_async_session_context()` 管理会话
- **Service 层**：`services/police_service.py` 封装业务逻辑，调用 repository + 审计日志
- **Router 层**：`server/routers/` 下的 FastAPI 路由，使用 `get_required_user` / `get_db` 依赖注入
- **ORM 约定**：Integer 自增主键、`utc_now_naive()` 时间戳、`to_dict()` 序列化、JSON 列存储灵活数据
- **前端约定**：Composition API + `<script setup>`、Ant Design Vue 组件、Pinia Composition store

---

## 致谢

本项目基于 [语析 Yuxi](https://github.com/xerrors/Yuxi) 二次开发，融合 [StaffDeck](https://github.com/OpenBMB/StaffDeck) 数字员工概念与 [Plane](https://github.com/makeplane/plane) 项目管理交互设计。感谢原作者及所有开源贡献者。

Yuxi 参考引用的优秀项目：
- [LangGraph](https://github.com/langchain-ai/langgraph) — 多智能体编排框架
- [DeepAgents](https://github.com/langchain-ai/deepagents) — 深度智能体框架
- [DeerFlow](https://github.com/bytedance/deer-flow) — Sandbox 智能体架构
- [RAGflow](https://github.com/infiniflow/ragflow) — 文档分块策略
- [LightRAG](https://github.com/HKUDS/LightRAG) — 图谱构建与检索思路

StaffDeck 参考引用的概念：
- 数字员工身份档案、能力矩阵、工作统计、成长记录
- SOP 状态机驱动的流程型技能
- 文档结构感知的知识检索

---

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。
