# 小南 (Xiaonan) — 公安数字警员协同平台开发文档

> **产品品牌**: 小南 / Xiaonan（前端 UI 与对外物料统一使用此品牌名）  
> **内部代号**: 智案协  
> **版本**: v1.5  
> **日期**: 2026-08-03  
> **状态**: **文档—代码对齐版**。本次修订不新增设计，只做三件事：①把与代码不符的描述改成代码实际的样子（数据模型主键/表名、API 路径、事件驱动实现方式）；②把已实现但文档缺失的功能补写进来（侦查任务模板体系、案件工作区文件系统、数字警员市场与共享审批、任务多执行人）；③为每一节标注实现状态，区分「已实现」与「规划中」  
> **基础底座**: 语析 Yuxi v0.7.1 (https://github.com/xerrors/Yuxi, MIT 协议)  
> **产品形态参考**: StaffDeck (https://github.com/OpenBMB/StaffDeck，数字员工广场 / 员工档案 / SOP / 工作记录交互语言)  
> **看板交互参考**: Multica (https://github.com/multica-ai/multica，卡片式看板 / 优先级标签 / 多列拖拽 / Agent 队友呈现)  
> **安全能力参考**: Octop (https://github.com/TencentCloud/Octop，PII 脱敏 / 工具防护)

---

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 开源项目选型分析](#2-开源项目选型分析)
- [3. 系统架构设计](#3-系统架构设计)
- [4. 核心功能模块设计](#4-核心功能模块设计)
- [5. 数据模型设计](#5-数据模型设计)
- [6. 数字警员设计](#6-数字警员设计)
- [7. API 接口设计](#7-api-接口设计)
- [8. 前端 UI 设计规范](#8-前端-ui-设计规范)
- [9. 安全与合规设计](#9-安全与合规设计)
- [10. 部署方案](#10-部署方案)
- [11. 开发计划与里程碑](#11-开发计划与里程碑)

---

## 0. 实现状态说明（v1.5 新增，阅读本文档前必读）

本文档同时承载「已建成的系统说明」与「未来规划」两种内容。为避免把规划当成已实现来验收，全文使用统一状态标记：

| 标记 | 含义 | 阅读方式 |
|---|---|---|
| ✅ **已实现** | 代码已落地，描述与代码一致，可直接用于联调 | 可信，以本文档为准 |
| ⚠️ **部分实现** | 主链路已通，但存在文档描述的能力缺口 | 需看该节的「实现差异」说明 |
| 📋 **规划中** | 仅为设计意图，**代码 0 行**，不可用于联调或验收 | 不要照此写调用 |
| 🔀 **实现方式不同** | 功能存在，但实现手段与文档原描述不一致，已按代码修正 | 以本文档修订后的描述为准 |

### 0.1 分章实现状态总览

| 章节 | 主题 | 状态 | 说明 |
|---|---|---|---|
| §1–§3 | 概述 / 选型 / 架构 | ✅ 已实现 | 技术栈与分层与代码一致 |
| §3.4 | 任务自动流转机制 | ⚠️ 部分实现 | `police_task_flow_rules` 表与 CRUD 已实现，条件规则引擎为简化版 |
| §4.1–§4.3 | 案件 / 任务 / 数字警员中心 | ✅ 已实现 | — |
| §4.4 | 知识库与知识图谱 | 📋 规划中 | `knowledge_base_id` / `graph_id` 为**空壳字段**，police 侧无任何读写；Neo4j / Milvus 未接入公安业务 |
| §4.5 | 证据材料管理 | ✅ 已实现 | 上传 / 下载 / 预览 / 审核签名 / 证据链均已实现 |
| §4.6 | 法律文书生成 | 📋 规划中 | 仅有 DA-003 提示词，无文书模板引擎 |
| §4.7 | 工作台 | ✅ 已实现 | — |
| §4.8 | SOP / 办案规程管理 | ⚠️ 部分实现 | `police_sops` 表 + CRUD 已实现；**无 SOP 执行器、无实例表**，状态机不会真正运行 |
| §4.9 | 侦查任务模板配置体系 | ✅ 已实现 | **v1.5 补写**，此前文档完全未记录 |
| §4.10 | 案件工作区文件系统 | ✅ 已实现 | **v1.5 补写**，此前文档完全未记录 |
| §4.11 | 数字警员市场与共享审批 | ✅ 已实现 | **v1.5 补写**，此前文档完全未记录 |
| §5.2 | 核心表结构 | 🔀 已按代码重写 | 原文用 UUID 主键 / 无前缀表名，**与代码完全不符**；v1.5 已全量替换为真实 17 张表 |
| §6.1–§6.5 | 各执行智能体 | ⚠️ 部分实现 | 预设警员已扩到 **DA-001~DA-007**；执行为单轮 LLM 调用，`tools`/`skills`/`knowledge_base_ids` 字段暂未参与执行 |
| §6.6 | 案件推进智能体 | 🔀 已按代码修正 | 实际为**顺序管线**而非 LangGraph StateGraph；任务模板已配置化落库 |
| §6.7.6 | 事件驱动机制 | 🔀 已按代码修正 | 实际用 `asyncio.create_task()` 进程内直调，**未走 ARQ 队列**；触发点在 `review_task` 而非 `complete_task` |
| §6.7.7 | 数据库变更 | 📋 部分作废 | `police_case_advancement_agents` 表与三个 PoliceTask 字段**未实现**；实际以 `police_advancement_logs` + `PoliceTask.extra` 承载 |
| §7 | API 接口设计 | 🔀 已按代码重写 | 真实前缀为 `/api/police/*`，**原文 `/api/v1/*` 路径全部不可用** |
| §8.4.5 | 知识图谱可视化 | 📋 规划中 | 无对应前端页面 |
| §8.4.6 | 数字警员广场 | 🔀 已按代码修正 | 已合并进统一智能体管理页，`/police/officers` 为重定向 |
| §8.4.8 | SOP 管理页 | 📋 规划中 | 无对应前端页面 |
| §9.1 / §9.3 | PII 脱敏中间件 / 智能体安全 | 📋 规划中 | 无脱敏中间件代码，仅在提示词中约束 |
| §9.5.1 / §9.5.2 | 证据双哈希与签名 | ✅ 已实现 | — |
| §9.5.3 | 完整性校验 | 📋 规划中 | **只签不验**：无任何校验函数；原文伪代码字段有误，v1.5 已修正 |
| §10 | 部署方案 | ⚠️ 部分实现 | 开发态 compose 可用，生产态离线部署配置待验证 |

### 0.2 已知的高优先级技术债

以下问题在本次对齐中被识别出来，属于**代码侧隐患**，不通过改文档解决：

1. **推进智能体触发不可靠** — `police_service.py:420` 用 `asyncio.create_task()` 进程内直调，**进程重启即丢事件**，无重试、无幂等锁；而 §6.6 要求「同一案件同时只运行一个实例」。应改为 ARQ 投递。
2. **证据只签不验** — `verify_evidence_integrity` 全库未实现，签名链无法在诉讼阶段被校验，§9.5 的合规目标尚未闭环。
3. **`TaskEvent` 无自动化消费者** — 该表仅用于任务详情页时间线展示，任务流转规则并不由它驱动。
4. **DA-005 命名冲突** — 代码中该警员仍名为「案件编排官 / case_orchestrator」，职责写作"多Agent调度"，与 §6.6 重定位后的「案件推进智能体（建议者，非指挥者）」定位不一致，需统一。

---

## 1. 项目概述

### 1.1 背景与问题

当前公安专案侦办过程中存在以下痛点：

- **协同效率低**：专案涉及研判、抓捕、审讯、办理、移送起诉等多个阶段，参与人员多、流转环节多，信息同步靠口头和纸质，容易出现信息断层。
- **重复劳动多**：资金流分析、文书生成、证据整理等工作高度重复，消耗大量警力。
- **知识难沉淀**：每个案件的研判过程、资金流向、人员关系等知识散落在个人脑中和零散文档中，无法复用。
- **线索易遗漏**：海量证据材料人工梳理，关键线索容易遗漏，缺乏系统化的辅助分析手段。

### 1.2 项目目标

构建一个面向公安机关的 **数字警员协同平台**：将公安内部各警种同事抽象为「数字警员」，以 **案事件** 为核心，由 **民警与数字警员组成专案组** 共同完成案件全流程办理。数字警员以 Yuxi Agent 为技术底座，每个数字警员拥有多项独特 **技能（Yuxi Skill）**，既能与民警 **直接对话**（如法制民警给出法律建议、审查笔录），也能被编入 **复杂专案** 由「案件编排官」按 **SOP/办案规程** 调度，与民警及其他数字警员协同作战。平台实现：

1. **民警+数字警员组队办案**：每个案件 = 一个由主办民警与若干数字警员（如笔录分析师、资金追踪师、法制审核官）组成的专案组。
2. **数字警员可直接对话**：民警可就具体事项与单个数字警员一对一对话，直接调用其专业技能（如「帮我审查这份笔录」「给出本案法律适用建议」）。
3. **数字警员参与专案协同**：复杂专案中，案件编排官按 SOP 把多个数字警员/技能编排串联，自动提示需开具的文书、待办工作项。
4. **人机协作审核（默认流程）**：数字警员产出为「草稿」，必须经民警审核签字（signed_hash）后才具法律效力、进入正式卷宗。
5. **知识图谱化**：案件资料结构化为知识图谱，支持实体关系查询与推理。
6. **全程可追溯**：所有对话、数字警员产出、民警审核均有审计记录。

### 1.3 核心价值主张

| 角色 | 价值 |
|------|------|
| **案件指挥员** | 全局掌控专案组成立与进展，调度数字警员，审核关键产出 |
| **办案民警** | 与数字警员组队，直接对话调用技能；工作台看到分配给自己的任务，按指引完成即可，无需从零分析 |
| **数字警员** | 即 Yuxi Agent，承担重复性、专业性工作（资金分析、文书生成、法制审核等），拥有多项技能，产出供民警审核 |
| **法制部门** | 法制数字警员前置审核，减少程序性错误 |

### 1.4 两种协同模式

平台中数字警员以两种模式参与工作，二者共用同一套「数字警员 = Yuxi Agent、技能 = Yuxi Skill」底座：

**模式 A：直接对话（点对点）**
民警就具体事项与单个数字警员一对一对话，直接调用其技能，无需进入专案流程。
```
民警: "帮我审查这份讯问笔录，看程序是否合规"
    → 对话路由到「法制审核官」数字警员
    → 调用其「笔录审查」技能
    → 产出: 合规审查意见（草稿）
    → 民警审核签字 → 进入卷宗
```

**模式 B：专案协同（一对多）**
围绕案事件成立专案组，由「案件编排官」按 SOP 调度多个数字警员与民警协同。
```
受害人报案 → 上传报案笔录
    → 组建专案组：主办民警 + 笔录分析师 + 资金追踪师 + 法制审核官
    → 笔录分析师（调用「笔录分析」技能）提取关键信息（涉案银行卡、微信号、嫌疑人等）
    → 自动创建案件工作区 + 生成初始工作项
        ├─ 工作项1: 调取银行卡X流水 → 分配给「调证生成师」→ 生成调取通知书
        ├─ 工作项2: 微信号查询 → 分配给网警民警
        └─ 工作项3: 资金初查 → 分配给「资金追踪师」
    → 一级流水到账（民警上传）
        → 资金追踪师自动触发分析
        → 产出: 涉案资金追踪报告 + 需调取的二级账户清单
        → 案件编排官按 SOP 自动创建新工作项: 调取二级账户Y流水
    → ... 持续迭代直到资金链路完整 ...
    → 法制审核官审核全案证据链（提示需补正的文书/程序）
    → 移送起诉 → 专案组解散，工作记录沉淀为知识资产
```

> **说明**：模式 A 是轻量、随用随走的咨询/审查；模式 B 是重度的全流程协同。两种模式的数字警员产出都必须经民警审核签字（见 9.5 节）后才具法律效力。

---

## 2. 开源项目选型分析

### 2.1 候选项目概览

| 维度 | Octop (腾讯云) | 语析 Yuxi | Plane |
|------|----------------|-----------|-------|
| **定位** | 自托管 AI 助手，多用户多智能体 | 多租户 Harness + 企业知识库（RAG+知识图谱+智能体编排） | 开源项目管理工具 (Jira 替代) |
| **GitHub** | TencentCloud/Octop | **xerrors/Yuxi** | makeplane/plane |
| **License** | MIT | **MIT** | AGPL-3.0 |
| **版本** | — | v0.7.1（2368+ commits，持续活跃维护） | — |
| **后端** | Python / FastAPI / SQLite or PostgreSQL | Python / FastAPI / **LangGraph** / **ARQ** | Python / Django / Node.js |
| **前端** | React 18 / TypeScript / Vite / Ant Design | Vue 3 / Vite / Pinia | React / Next.js |
| **存储** | SQLite (WAL) 或 PostgreSQL | PostgreSQL + Redis + MinIO + Milvus + Neo4j | PostgreSQL + Redis |
| **智能体** | harness-agent 运行时，每用户多智能体 | **LangGraph + DeepAgents**，SubAgents/Skills/MCP/沙盒/中间件 | 无 |
| **知识库** | 无 | **Agentic RAG**（自主检索+Rerank+引用溯源）+ 检索评估 | 无 |
| **知识图谱** | 无 | Milvus 内知识图谱 + Neo4j（实体关系抽取+子图检索+可视化） | 无 |
| **审批工作流** | 无 | ✅ 内置审批中间件（人机协作 resume/checkpoint） | 无 |
| **沙盒** | 浏览器/终端/远程桌面 | ✅ 每会话独立虚拟文件系统（workspace/uploads/outputs） | 无 |
| **多租户** | JWT 多用户隔离 | **多租户 + 用户/部门级权限**（全局/部门/指定人三档共享） | 项目级成员管理 |
| **异步任务** | APScheduler (cron) | **ARQ 异步 Worker**（支持取消/流式/跨进程恢复） | Celery |
| **文档解析** | 无 | MinerU / PaddleX / RapidOCR（OCR 引擎配置中心） | 无 |
| **外部集成** | IM 连接器 | **MCP 标准协议 + API Key**（供外部系统调用） | Webhooks |
| **部署** | Docker / pip / 系统服务 | Docker Compose（支持 LITE 轻量模式） | Docker / Kubernetes |
| **CLI 工具** | 无 | ✅ yuxi-cli（知识库文件上传等） | 无 |

### 2.2 Octop vs 语析：深度对比分析

#### 2.2.1 知识管理能力（权重: 高）

公安场景的核心需求是将海量案件资料结构化、可检索、可推理。语析（xerrors/Yuxi）在此维度具有压倒性优势。

| 能力 | Octop | 语析 | 评价 |
|------|-------|------|------|
| Agentic RAG | ❌ 无 | ✅ 智能体自主决定检索时机与查询，多轮向量检索 + Rerank | 语析完胜 |
| 知识图谱 | ❌ 无 | ✅ 实体关系抽取 + 子图检索参与增强 + 可视化探索（Milvus + Neo4j 双图谱） | 语析完胜 |
| 文档解析 | ❌ 无 | ✅ MinerU/PaddleX/RapidOCR OCR 引擎配置中心，PDF/Office/图片 → 结构化 Markdown | 语析完胜 |
| 引用溯源 | ❌ 无 | ✅ 回答带可溯源引用来源 | 语析完胜 |
| 检索评估 | ❌ 无 | ✅ 内置检索质量评估，支持命名运行与指标对比 | 语析完胜 |
| 多知识源 | ❌ 无 | ✅ Dify/Notion/飞书(规划中) 外部知识源统一检索 | 语析完胜 |

> **结论**: 知识管理是公安平台的核心刚需（案件资料、证据链、人员关系网），语析的 Agentic RAG + 双图谱（Milvus 向量图谱 + Neo4j 关系图谱）+ 检索评估构成完整的知识引擎，Octop 完全不具备。

#### 2.2.2 多智能体编排能力（权重: 高）

| 能力 | Octop | 语析 | 评价 |
|------|-------|------|------|
| 编排框架 | harness-agent (自研运行时) | **LangGraph + DeepAgents**（业界标准+深度智能体） | 语析更通用 |
| 子智能体 | 路线图中的 AgentTeams (未实现) | ✅ **SubAgents** 已实现，主智能体编排隔离子线程 | 语析更成熟 |
| 深度智能体 | ❌ 无 | ✅ **DeepAgents** 框架直接引入，支持复杂多步任务 | 语析独有 |
| A2A 协作 | ✅ Channel/Thread 中 Bot 互相对话 | ✅ LangGraph 图编排 + SubAgent 隔离 child thread | 各有特色 |
| 工具系统 | ✅ Skills + MCP 网关 + 连接器 | ✅ **Skills + MCP + Tools + 中间件**（可组合编排） | 语析更灵活 |
| 沙盒执行 | ✅ 浏览器/终端/远程桌面 | ✅ **每会话独立虚拟文件系统**（workspace/uploads/outputs） | 各有侧重 |
| **审批工作流** | ❌ 无 | ✅ **内置审批中间件**（LangGraph checkpoint resume） | **语析独有，公安刚需** |
| Skills 管理 | 基础 | ✅ **上传+远程安装**，「解析草稿 → 确认安装」流程 | 语析更完善 |
| 中间件编排 | ❌ 无 | ✅ 知识库注入/附件处理/历史摘要/动态工具注入/审批 | 语析独有 |
| 异步长任务 | ⚠️ APScheduler (单进程) | ✅ ARQ Worker (可取消/流式/跨进程恢复) | 语析更适合 |
| 请求排队 | ❌ 无 | ✅ 用户/智能体/线程级 FIFO 队列 | 语析独有 |

> **结论**: 语析的智能体引擎远比 Octop 成熟。**审批工作流中间件**是公安场景的刚需——法制审核、人机协作审核都需要「智能体产出 → 暂停等待人工确认 → resume 继续」的能力，语析通过 LangGraph checkpoint 原生支持这一模式。SubAgents 子智能体编排完美契合案件编排智能体的需求（主智能体调度各专业子智能体）。DeepAgents 框架则适合资金追踪这类需要多轮推理+工具调用的复杂任务。

#### 2.2.3 企业级部署能力（权重: 高）

| 能力 | Octop | 语析 | 评价 |
|------|-------|------|------|
| 数据库 | SQLite (默认) / PostgreSQL (可选) | PostgreSQL (默认，含 LangGraph checkpoint) | 语析更企业级 |
| 向量数据库 | 无 | Milvus + etcd | 语析必需 |
| 图数据库 | 无 | Neo4j | 语析必需 |
| 对象存储 | 本地/Docker/PG/COS | MinIO (S3 兼容) | 相当 |
| 缓存 | 无 | Redis（投递/事件/取消/缓存/跨进程配置同步） | 语析更完善 |
| 多租户 | JWT 用户隔离 | **用户/部门级权限**（全局/部门/指定人三档共享） | 语析更细粒度 |
| 外部集成 | IM 连接器 | **API Key 签发**（供外部系统 API 方式调用） | 语析更企业级 |
| 轻量启动 | ❌ 无 | ✅ **LITE 模式**（跳过知识库/图谱等重依赖） | 语析更灵活 |
| CLI 工具 | ❌ 无 | ✅ yuxi-cli（知识库文件上传等） | 语析独有 |
| 单进程限制 | ✅ 单进程架构 | ❌ 多服务架构（API/Worker/Sandbox 分离） | Octop 更简单 |
| 架构清晰度 | — | ✅ server(HTTP适配) / package(业务逻辑) 清晰分层 | 语析更规范 |

> **结论**: 公安平台需要支撑多部门、多案件并发。语析的多服务架构（API + Worker + Sandbox Provisioner 分离）天然适合横向扩展。API Key 集成能力让平台可作为「内部 AI 能力底座」被其他公安系统调用。LITE 模式加速开发迭代。Octop 的 SQLite 单进程架构在并发场景下会成为瓶颈。

#### 2.2.4 安全合规能力（权重: 高）

| 能力 | Octop | 语析 | 评价 |
|------|-------|------|------|
| 用户隔离 | ✅ JWT 每用户隔离 | ✅ 多租户隔离 + 案件级权限 | 语析更细粒度 |
| 沙盒隔离 | ❌ 无 | ✅ **每会话独立虚拟文件系统** + 网络隔离 | 语析更强 |
| 审批控制 | ❌ 无 | ✅ **审批中间件**（智能体操作需人工确认后 resume） | 语析独有，公安刚需 |
| 工具防护 | ✅ Shell 命令白名单/黑名单 | ⚠️ 沙盒网络隔离 + Skill 门控 | Octop 更细粒度 |
| PII 脱敏 | ✅ 内置 PII 过滤 | ❌ 无 | Octop 有优势 |
| 数据本地化 | ✅ 全部本地 | ✅ 全部本地（私有化部署） | 相当 |
| 请求排队 | ❌ 无 | ✅ FIFO 队列防止单用户资源独占 | 语析更安全 |
| 用量管控 | ❌ 无 | ✅ Token 用量统计（中间件层） | 语析更可控 |

> **结论**: 语析的**沙盒隔离**和**审批工作流**对公安场景至关重要：沙盒确保智能体操作的文件不会污染系统；审批中间件让智能体的关键操作（如生成调取通知书）必须经民警确认后才继续执行。Octop 在 PII 脱敏和工具防护上有优势，这些能力可作为独立模块移植到语析平台上。

#### 2.2.5 综合评分

| 维度 | 权重 | Octop | 语析 |
|------|------|-------|------|
| 知识管理 | 25% | 2/10 | **9.5/10** |
| 智能体编排 | 20% | 7/10 | **9/10** |
| 企业级部署 | 20% | 5/10 | **9/10** |
| 安全合规 | 15% | 8/10 | **8/10** |
| 项目管理 | 10% | 2/10 | 2/10 |
| 社区活跃度 | 10% | 7/10 | **8/10**（2368+ commits，持续活跃） |
| **加权总分** | 100% | **4.65** | **8.23** |

### 2.3 选型结论

#### 推荐方案：以语析 Yuxi (xerrors/Yuxi) 为基础底座

**核心理由**：

1. **知识图谱是公安场景的灵魂**：案件涉及人员关系、资金流向、账户网络，天然适合图结构。语析内置 **Milvus 向量图谱 + Neo4j 关系图谱**双图谱能力（实体关系抽取 + 子图检索 + 可视化探索），是 Octop 完全不具备的。

2. **Agentic RAG 是案件资料管理的基石**：报案笔录、证据材料、法律文书需要结构化存储和智能检索。语析的 **Agentic RAG**（智能体自主决定检索时机 + 多轮向量检索 + Rerank + 引用溯源 + 检索评估）直接可用。

3. **审批工作流中间件是公安人机协作的刚需**：法制审核、智能体产出审核都需要「智能体执行 → 暂停等待人工确认 → resume 继续」的模式。语析通过 **LangGraph checkpoint + 审批中间件**原生支持这一模式，无需从零开发。

4. **SubAgents + DeepAgents 契合案件编排**：案件编排智能体需要调度多个专业子智能体，语析的 **SubAgents**（主智能体编排隔离子线程）和 **DeepAgents**（深度智能体框架）天然契合。

5. **沙盒文件系统保障安全**：每个会话/任务拥有独立虚拟文件系统，智能体操作的文件与系统隔离，符合公安数据安全要求。

6. **企业级存储栈 + API Key 集成**：PostgreSQL + Redis + Milvus + Neo4j + MinIO 是成熟的企业级组合。API Key 签发能力让平台可作为公安内部 AI 能力底座被其他系统调用。

7. **MIT 协议无商用限制**：可自由修改、分发、闭源使用，无协议传染风险（对比 Plane 的 AGPL-3.0）。

8. **架构清晰可直接扩展**：语析的代码分层（server HTTP 适配层 / package 业务逻辑层 / agents 智能体层 / knowledge 知识引擎层）规范清晰，新增公安业务逻辑可干净地落在对应层级。

#### 语析架构与公安平台的映射关系

| 语析原生能力 | 公安平台应用 | 扩展方式 |
|-------------|-------------|----------|
| 多租户 + 部门级权限 | 公安部门/专案组隔离 | 直接复用，增加警号/警衔字段 |
| LangGraph + ARQ Worker | 智能体异步执行（资金分析等长任务） | 直接复用 |
| 审批中间件 | 法制审核 + 智能体产出审核 | 直接复用，增加审核角色规则 |
| SubAgents | 案件编排智能体调度专业子智能体 | 直接复用 |
| Skills 技能系统 | 资金分析/笔录分析/调证生成等专业技能 | 开发公安专属 Skills |
| MCP 标准协议 | 接入公安内部系统（网警查询/银行接口等） | 开发公安 MCP 连接器 |
| 沙盒文件系统 | 证据材料安全处理 | 直接复用 |
| Agentic RAG | 案件知识库检索 | 直接复用，按案件隔离知识库 |
| 知识图谱（Milvus+Neo4j） | 人员/资金/通讯关系图谱 | 定义公安专属实体与关系类型 |
| OCR 引擎配置中心 | 笔录/流水/截图 OCR 识别 | 直接复用 |
| API Key 集成 | 供公安其他系统调用平台能力 | 直接复用 |
| LITE 模式 | 开发期快速迭代 | 直接复用 |
| 中间件编排 | 知识库注入/附件处理/历史摘要 | 直接复用 + 自定义公安中间件 |

#### 同时借鉴 Octop 的以下能力：

| 借鉴能力 | 用途 | 集成方式 |
|----------|------|----------|
| PII 脱敏模块 | 案件数据中的身份证号、手机号等脱敏 | 移植为语析中间件 |
| 工具防护 (Tool Guard) | 智能体调用外部工具时的安全控制 | 移植为智能体安全层 |
| Channel/Thread 协作模型 | 案件讨论区的设计参考 | UI/UX 借鉴，不直接使用代码 |
| 专家库 (Expert Catalog) | 智能体模板管理的设计参考 | 架构借鉴 |

#### Plane 的定位：

Plane **不作为代码基础**（AGPL-3.0 协议有传染性），但作为 **UI/UX 设计蓝本**：

| 借鉴要素 | 说明 |
|----------|------|
| 项目-工作项-迭代 三层结构 | 映射为 案件-任务-阶段 |
| 看板/列表/日历多视图 | 任务的多视角查看 |
| 自定义视图与过滤器 | 按案件类型、阶段、负责人筛选 |
| 富文本编辑器 + 文件附件 | 任务描述与证据材料上传 |
| Command-K 全局搜索 | 快速跳转案件/任务/人员 |

> **UI 参考调整（v1.3）**：以上 Plane 借鉴项聚焦于「任务/看板」类协作视图，仍保留参考价值。但平台的一级产品隐喻（数字警员广场、数字警员档案、技能/SOP、工作记录）改为参考 **StaffDeck** 的「数字员工」交互语言（详见 8.1 节）。

### 2.4 StaffDeck 产品形态参考

StaffDeck（OpenBMB）是「企业数字员工平台」，其产品形态与公安「数字警员」定位高度契合，作为 **前端 UI / 交互语言** 的参考（不作为代码基础）：

| StaffDeck 概念 | 小南映射 | 借鉴要点 |
|----------------|----------|----------|
| 数字员工广场 | 数字警员广场 | 卡片化画廊展示可用数字警员，显示状态/专长/工作统计 |
| 员工档案 | 数字警员档案 | 头像、基本资料、能力矩阵、技能列表、工作记录、成长轨迹、对话日志 |
| SOP / 技能 | 办案规程 / 技能 | 状态机驱动的流程 + 原子技能，可版本管理、调用统计、好评率 |
| 工作记录 | 数字警员工作记录 | 每次对话/任务/产出的时间线沉淀 |
| 成长轨迹 | 数字警员成长记录 | 使用频次、好评差评、能力演进 |

**结论**：以语析 Yuxi 为技术底座、以 StaffDeck 为产品形态与 UI 语言、以 Multica 为看板交互参考、以 Octop 为安全能力参考，构成小南 v1.4 的「四位一体」选型框架。

### 2.5 Multica 看板交互参考

Multica（multica-ai）是开源的 Managed Agents 平台，定位"将 Agent 变成真正的队友"。其理念与小南高度一致（Agent 作为一等公民），但其技术栈（Go/Next.js）和场景（软件开发）与小南完全不匹配。**仅吸收 UI 设计语言和看板交互模式，不迁移技术实现**。

| Multica 借鉴要素 | 小南映射 | 借鉴要点 |
|---|---|---|
| 多列看板视图 | 任务看板 | 待确认→待开始→进行中→审核中→已完成，每列独立滚动 |
| 卡片式设计 | 任务卡片 | 白色圆角卡片 + 灰色细边框 + 优先级彩色标签 + 负责人头像 |
| 优先级标签 | 优先级色标 | Low/绿、Medium/黄、High/橙、Urgent/红，圆角彩色 background |
| Agent 队友呈现 | 智能体创建的任务 | 卡片左侧蓝色竖线 + 🤖 标记 + 依据引用，与人类任务视觉区分 |
| 列计数徽标 | 列标题 | 每列顶部显示任务数（如"进行中 (3)"） |
| 导航视角 | 侧边栏 | 按"我是民警"而非"系统功能"组织：个人工作台/我的任务/全部任务/案件中心/数字警员 |

**核心理念对齐——Agent 作为一等公民**：
- Agent 生成的任务与人类创建的任务在同一个看板上平等呈现
- 人机协作不是"人给 AI 发指令"，而是"民警带着 AI 队友组队办案"
- 每一步生成、每一次决策都可追溯到具体人或 Agent

> **技术栈坚守**：Multica 使用 Go/Next.js，小南使用 Python/FastAPI + Vue 3。仅吸收其 UI 设计，不迁移任何代码。

---

## 3. 系统架构设计

### 3.1 整体架构

平台采用 **分层架构 + 模块化设计**，自底向上分为五层：

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端展示层 (Frontend)                      │
│  Vue 3 + Vite + Pinia + Element Plus / Naive UI                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │ 工作台    │ │ 案件管理  │ │ 任务管理  │ │数字警员中心│ │知识图谱 ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘│
├─────────────────────────────────────────────────────────────────┤
│                     API 网关层 (API Gateway)                      │
│  FastAPI + JWT Auth + RBAC + Rate Limit + Audit Log              │
├─────────────────────────────────────────────────────────────────┤
│                     业务服务层 (Business Services)                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │ 案件服务  │ │ 任务服务  │ │数字警员调度│ │ 文书服务  │ │知识服务 ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘│
├─────────────────────────────────────────────────────────────────┤
│                     智能体引擎层 (Agent Engine)                    │
│  LangGraph 多智能体编排 + ARQ 异步 Worker                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │ 笔录分析  │ │ 资金分析  │ │ 调证生成  │ │ 法制审核  │ │案件编排 ││
│  │ 智能体    │ │ 智能体    │ │ 智能体    │ │ 智能体    │ │智能体  ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘│
├─────────────────────────────────────────────────────────────────┤
│                     数据存储层 (Data Storage)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │PostgreSQL│ │  Redis   │ │  MinIO   │ │  Milvus  │ │ Neo4j  ││
│  │ 业务数据  │ │ 缓存/队列 │ │ 文件存储  │ │ 向量检索  │ │知识图谱 ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 技术栈选型

| 层级 | 技术 | 选型理由 |
|------|------|----------|
| **前端框架** | Vue 3 + TypeScript | 语析同栈，生态成熟，团队学习成本低 |
| **构建工具** | Vite 6 | 极速 HMR，语析同栈 |
| **状态管理** | Pinia | Vue 3 官方推荐 |
| **UI 组件库** | Naive UI | 现代简洁风格，TypeScript 原生，暗色模式完善 |
| **图表库** | ECharts 5 | 知识图谱可视化、资金流向图、统计图表 |
| **图谱可视化** | AntV G6 | 专用的图分析可视化，适合人员关系/资金网络 |
| **富文本编辑器** | Tiptap | 任务描述、案件报告编辑 |
| **后端框架** | FastAPI (Python 3.11+) | 语析同栈，异步高性能，自动 OpenAPI 文档 |
| **智能体编排** | LangGraph | 语析同栈，图式编排，支持复杂工作流 |
| **异步任务** | ARQ (Redis-based) | 语析同栈，支持取消/流式/重试 |
| **关系数据库** | PostgreSQL 16 | 语析同栈，企业级，JSONB 支持灵活字段 |
| **缓存/队列** | Redis 7 | 语析同栈，缓存 + ARQ 任务队列 |
| **对象存储** | MinIO | 语析同栈，S3 兼容，私有化部署 |
| **向量数据库** | Milvus 2 | 语析同栈，大规模向量检索 |
| **图数据库** | Neo4j 5 | 语析同栈，知识图谱存储与查询 |
| **文档解析** | MinerU + PaddleX | 语析同栈，PDF/Office/图片 OCR |
| **大模型接入** | OpenAI 兼容接口 | 支持通义千问/DeepSeek/智谱等国产模型 |
| **容器化** | Docker + Docker Compose | 语析同栈，简化部署 |

### 3.3 智能体调度架构

```
                    ┌─────────────────────┐
                    │   案件编排智能体      │
                    │ (Case Orchestrator)  │
                    │  - 分析案件上下文     │
                    │  - 决定任务流转       │
                    │  - 创建新任务         │
                    └──────────┬──────────┘
                               │ 编排调度
                    ┌──────────┴──────────┐
                    │                      │
          ┌─────────┴─────────┐  ┌────────┴─────────┐
          │   专业智能体池      │  │   人工任务池      │
          │                    │  │                    │
          │ ┌─── 笔录分析 ───┐ │  │ ┌── 网警查询 ────┐│
          │ ├─── 资金分析 ───┤ │  │ ├── 银行调证 ────┤│
          │ ├─── 调证生成 ───┤ │  │ ├── 实地取证 ────┤│
          │ ├─── 法制审核 ───┤ │  │ ├── 审讯讯问 ────┤│
          │ └─── 证据梳理 ───┘ │  │ └── ... ─────────┘│
          └────────────────────┘  └────────────────────┘
                    │
                    ▼
          ┌────────────────────┐
          │   ARQ 异步 Worker   │
          │  - 长任务异步执行    │
          │  - 流式输出          │
          │  - 可取消            │
          └────────────────────┘
```

### 3.4 任务自动流转机制

平台的核心创新在于 **任务自动流转**——智能体根据事件触发自动创建新任务：

```python
# 伪代码：任务流转规则引擎
class TaskFlowRule:
    """任务流转规则"""
    trigger_event: str          # 触发事件 (如: task_completed, file_uploaded)
    condition: Callable         # 触发条件 (如: task_type == "fund_analysis")
    action: str                 # 动作 (如: create_task, notify, approve)
    target_task_type: str       # 创建的新任务类型
    target_assignee_type: str   # 分配对象类型 (agent / human)

# 示例规则：资金分析完成 → 创建调取下一级流水任务
rule_fund_analysis_followup = TaskFlowRule(
    trigger_event="task_completed",
    condition=lambda ctx: ctx.task_type == "fund_analysis" 
                          and ctx.result.get("next_level_accounts"),
    action="create_task",
    target_task_type="evidence_collection",
    target_assignee_type="agent",  # 分配给调证智能体
    task_payload_builder=lambda ctx: {
        "accounts": ctx.result["next_level_accounts"],
        "document_type": "bank_flow_requisition",
    }
)
```

---

## 4. 核心功能模块设计

### 4.1 案件项目管理

#### 4.1.1 案件全生命周期

```
立案登记 → 前期研判 → 抓捕审讯 → 案件办理 → 移送起诉 → 结案归档
   │          │          │          │          │          │
   │    笔录分析    审讯记录    证据整理    法制审核    归档封存
   │    资金初查    抓捕方案    文书生成    移送材料    知识沉淀
   │    线索排查    人员控制    羁押审查    ─────────→
   │    串并案                                              │
```

#### 4.1.2 专案组组建流程（智能创建）

案件创建即「组建专案组」——在生成案件工作区的同时，确定参与本案的民警与数字警员：

1. **上传报案笔录**：主办民警上传受害人报案笔录（PDF/Word/图片）
2. **笔录分析数字警员**自动：
   - 提取案件类型、涉案金额、案发时间地点
   - 提取涉案人员信息（嫌疑人、受害人、证人）
   - 提取涉案账户（银行卡、支付宝、微信）
   - 提取涉案通讯信息（微信号、QQ号、手机号）
3. **组建专案组**：系统根据案件类型推荐数字警员组合（如电信诈骗案 → 笔录分析师 + 资金追踪师 + 法制审核官），由主办民警确认/调整，同时指定参与民警
4. **自动创建案件工作区**：生成案件编号、标题、描述，并初始化专案组成员关系
5. **自动生成初始工作项**：根据提取的信息生成需要执行的工作项，分配给对应数字警员或民警
6. **主办民警确认**：审核数字警员提取的信息、专案组构成与工作项，可修改后确认

#### 4.1.3 案件信息结构

```
案件 (Case)
├── 基本信息: 编号、标题、类型、状态、创建时间
├── 案情描述: 案发经过、涉案金额、受害人信息
├── 专案组: 主办民警 + 参与民警 + 数字警员（含各成员在案中的角色）
├── 涉案人员: 嫌疑人、受害人、证人 (人员关系图谱)
├── 涉案账户: 银行卡、第三方支付 (资金网络图谱)
├── 涉案通讯: 微信、QQ、手机号 (通讯网络图谱)
├── 证据材料: 笔录、流水、截图、录音录像
├── 法律文书: 立案决定书、调取通知书、起诉意见书
├── 案件阶段: 研判 → 抓捕 → 办理 → 移送
├── 工作项列表: 各阶段的具体工作项（分配对象 = 民警 或 数字警员）
├── SOP 执行轨迹: 案件编排官按办案规程调度的历史
└── 知识图谱: 人员/资金/通讯关系图
```

### 4.2 任务管理

#### 4.2.1 任务属性

| 属性 | 类型 | 说明 |
|------|------|------|
| id | UUID | 任务唯一标识 |
| case_id | UUID | 所属案件 |
| title | String | 任务标题 |
| description | Text | 任务详细描述（富文本） |
| type | Enum | 任务类型（见下表） |
| status | Enum | pending / in_progress / review / completed / blocked |
| assignee_type | Enum | human / agent |
| assignee_id | UUID | 分配给的用户ID或智能体ID |
| creator_id | UUID | 创建者（用户或智能体） |
| priority | Enum | urgent / high / medium / low |
| phase | Enum | 案件阶段 |
| parent_task_id | UUID | 父任务（支持子任务） |
| dependencies | List[UUID] | 前置依赖任务 |
| attachments | List[File] | 附件 |
| result | JSON | 任务结果（智能体产出） |
| due_date | DateTime | 截止时间 |
| created_at | DateTime | 创建时间 |
| completed_at | DateTime | 完成时间 |

#### 4.2.2 任务类型

| 任务类型 | 分配对象 | 说明 |
|----------|----------|------|
| `transcript_analysis` | Agent | 笔录分析，提取关键信息 |
| `fund_analysis` | Agent | 资金流水分析，追踪涉案资金 |
| `evidence_collection` | Agent | 生成调取通知书等法律文书 |
| `evidence_submission` | Human | 民警上传调取回来的证据材料 |
| `legal_review` | Agent | 法制审核，检查程序合规性 |
| `document_generation` | Agent | 生成法律文书（起诉意见书等） |
| `investigation` | Human | 实地侦查、走访调查 |
| `interrogation` | Human | 审讯讯问 |
| `arrest` | Human | 抓捕行动 |
| `cyber_inquiry` | Human | 网警查询（微信号、IP等） |
| `knowledge_extraction` | Agent | 从案件材料中提取知识图谱 |

#### 4.2.3 任务状态流转

```
                    ┌──────────┐
                    │ pending  │ (待分配/待开始)
                    └────┬─────┘
                         │ 分配/开始
                    ┌────▼─────┐
              ┌─────│in_progress│─────┐
              │     └──────────┘     │
              │ 需审核               │ 直接完成
         ┌────▼─────┐          ┌────▼─────┐
         │  review  │          │ completed│
         └────┬─────┘          └──────────┘
              │ 审核通过              ▲
              ├───────────────────────┘
              │ 审核驳回
         ┌────▼─────┐
         │  blocked │ (退回重做)
         └──────────┘
```

#### 4.2.4 任务视图

参考 Plane，提供多种任务视图：

- **看板视图**：按状态分列拖拽，直观查看任务流转
- **列表视图**：紧凑列表，支持排序/筛选/批量操作
- **时间线视图**：甘特图式展示任务时间安排
- **案件视图**：按案件分组查看任务
- **我的任务**：工作台个人任务列表

### 4.3 数字警员中心

> 数字警员即 Yuxi Agent，是平台的一等公民。前端参考 StaffDeck 的「数字员工广场 + 员工档案」交互语言（详见 8.1 节）。

#### 4.3.1 数字警员管理

- **数字警员注册/建档**：每个数字警员有工号、警衔、部门、专长标签、头像、系统提示词（对应 `police_agents` 表）
- **数字警员配置**：绑定的大模型、技能列表（Yuxi Skill）、MCP/工具、知识库
- **预设数字警员**：笔录分析师、资金追踪师、调证生成师、法制审核官、案件编排官等
- **运行监控**：查看数字警员在线/忙碌状态、历史执行记录与工作统计
- **能力扩展**：通过 Skills / MCP / Tools 扩展数字警员能力

#### 4.3.2 协同模式

| 模式 | 说明 | 示例 |
|------|------|------|
| **直接对话** | 民警与单个数字警员一对一对话，直接调用其技能 | 民警：「审查这份笔录」→ 法制审核官调用「笔录审查」技能 |
| **编排调度** | 案件编排官根据案件上下文决定调用哪个数字警员/技能 | 案件编排官分析后决定先调笔录分析 |
| **链式协作** | 多个数字警员按链式顺序协作（由 SOP 定义） | 笔录分析→资金分析→调证生成→法制审核 |
| **人机协作** | 数字警员完成初稿，民警审核签字确认 | 资金追踪师产出报告，民警审核后采纳 |

#### 4.3.3 技能（Yuxi Skill）

每个数字警员拥有多项独特技能，技能是可在对话中直接调用的原子能力：

- **技能定义**：名称、描述、触发语、关联工具/知识库、输入输出 schema
- **技能调用**：民警在对话中直接点名或自然语言触发（如「帮我审查笔录」「给出法律建议」）
- **技能与数字警员的关系**：一个技能可被多个数字警员共享，一个数字警员拥有多个技能；数字警员是技能的「人格化载体」
- **技能管理**：复用 Yuxi Skills 的「解析草稿 → 确认安装」机制，支持版本管理与调用统计

#### 4.3.4 工作记录与成长

- **工作记录**：每次对话、任务执行、产出文件均沉淀为数字警员的工作记录时间线
- **成长轨迹**：使用频次、好评/差评、能力演进，形成数字警员的成长档案（参考 StaffDeck 成长轨迹）
- **评价机制**：民警对数字警员产出可打分/评价，计入其技能好评率

### 4.4 知识库与知识图谱

#### 4.4.1 案件知识库

每个案件自动构建独立知识库：

- **文档入库**：报案笔录、银行流水、聊天记录、证据截图等自动入库
- **智能分块**：文档自动分块，生成向量索引
- **语义检索**：自然语言查询案件相关内容
- **引用溯源**：检索结果标注来源文档和位置

#### 4.4.2 案件知识图谱

从案件材料中自动抽取实体和关系，构建知识图谱：

**实体类型**：
- 人员（嫌疑人、受害人、证人）
- 账户（银行卡、支付宝、微信支付）
- 通讯账号（微信号、QQ号、手机号）
- 地址（居住地、活动地、作案地）
- 组织（公司、团伙）
- 案件事件（报案、转账、通话、见面）

**关系类型**：
- 转账关系：A → 转账 → B（金额、时间、次数）
- 通话关系：A → 通话 → B（时间、次数）
- 亲属关系：A → 亲属 → B
- 同伙关系：A → 同伙 → B
- 归属关系：A → 持有 → 账户/手机号
- 位置关系：A → 出现于 → 地址（时间）

**图谱应用**：
- 可视化展示人员/资金/通讯关系网络
- 最短路径分析（资金追踪）
- 社团发现（识别犯罪团伙）
- 实体碰撞（跨案件关联分析）

### 4.5 证据材料管理

| 功能 | 说明 |
|------|------|
| 文件上传 | 支持批量上传，自动分类（笔录/流水/截图/录音录像） |
| OCR 识别 | 图片/扫描件自动 OCR 转文本 |
| 文档预览 | 在线预览 PDF/Word/图片 |
| 版本管理 | 同一证据材料的多次提交版本 |
| 证据链管理 | 证据之间的关联关系，形成完整证据链 |
| 完整性校验 | 文件哈希值记录，防止篡改 |

### 4.6 法律文书生成

| 文书类型 | 生成方式 | 说明 |
|----------|----------|------|
| 调取通知书 | 智能体自动生成 | 根据需调取的账户/信息自动生成 |
| 立案决定书 | 智能体辅助生成 | 基于笔录分析结果填充模板 |
| 询问/讯问提纲 | 智能体辅助生成 | 基于案件分析生成提问要点 |
| 资金分析报告 | 智能体自动生成 | 资金流水分析结果的结构化报告 |
| 起诉意见书 | 智能体辅助生成 | 案件办理完成后生成 |
| 法律审核意见 | 智能体自动生成 | 法制审核结果 |

### 4.7 工作台

民警登录后的主页，展示：

- **我的待办工作项**：分配给我的待处理/进行中工作项
- **待审核任务**：数字警员完成、需要我审核的工作项
- **案件动态**：我参与的案件的最新进展
- **数字警员动态**：数字警员的运行状态和产出通知
- **快捷操作**：组建专案组、上传材料、查看图谱等

### 4.8 SOP / 办案规程管理

SOP（办案规程）是连接「数字警员技能」与「复杂专案协同」的编排层：由「案件编排官」按预设规程，把多个数字警员的技能串联为跨步骤流程，由案件事件触发。

- **SOP 定义**：业务域（如电诈/盗窃）、步骤序列、每步调用的数字警员/技能、触发条件、分支与异常处理
- **SOP 与任务流转的关系**：⚠️ SOP 的**表结构与 CRUD 已落地**（`police_sops`，含 `states`/`initial_state`/`terminal_states` 状态机三件套），但**尚无执行器、无实例表**，状态机不会真正运行；`task_flow_rules` 规则表存在，但任务流转并不由 `police_task_events` 事件驱动（见 §5.2.6 / §6.7.2）。v1.4 描述的「LangGraph 状态机驱动」目前未实现。
- **SOP 管理功能**（参考 StaffDeck 的 SOP 页）：
  - 本地 SOP 列表：业务域、状态、版本、调用次数、好评率/差评率
  - 版本管理：SOP 可迭代升级，旧版本归档可追溯
  - 调用统计：每次专案触发的 SOP 实例、各步执行时长与产出
- **典型 SOP 示例**：「电诈案初查规程」→ 笔录分析 → 资金初查 → 生成调取文书 → 提示需补正文书清单 → 法制审核

> SOP 是 v1.3 新增的一等概念。它让「数字警员参与复杂专案、提示需开具的文书」有了标准化的承载形式，而不是散落在硬编码的任务规则里。

---

### 4.9 侦查任务模板配置体系（v1.5 补写，✅ 已实现）

> v1.4 将「涉案要素 → 侦查任务」的映射规则硬编码在 prompt 中。v1.5 将其外置为可配置数据（`police_task_templates` 表，详见 §5.2.9），由推进智能体在管线第②步匹配。

- **模板核心字段**：`code`（唯一标识，内置模板幂等植入）、`element_type`（触发要素，对应 `ELEMENT_TYPE`）、`case_types` / `phases` / `source_task_types`（适用约束）、`task_title` / `task_type` / `instructions`（生成的任务）、`suggested_agent_type`（建议召唤的数字警员）、`next_template_codes`（链式推进）、`enabled` / `is_builtin`（启用与内置保护）。
- **占位符**：`task_title` / `task_description` / `instructions` 支持 `{element}` `{element_value}` `{case_title}` `{case_number}` `{source_task}` 动态填充。
- **触发逻辑**：推进智能体提取涉案要素后，按 `element_type` + 案件类型/阶段/源任务类型 命中模板；生成的任务草案进入 `pending_confirmation`，由主办民警审查（§6.7.3）。
- **管理接口**：`/api/police/task-templates`（列表/新建/更新/删除/启用停用/预览）+ `/seed` 植入内置模板（见 §7.2.8）。
- **权限控制**：配置类接口（新建 `POST`、更新 `PUT`、删除 `DELETE`、启用停用 `POST /toggle`、`/seed` 植入内置模板）**仅限超级管理员**（`role=superadmin`）调用，普通民警调用返回 `403 Forbidden`；列表/详情/元数据/预览为只读，登录即可访问。前端「任务模板」菜单对所有登录用户可见，但非超管执行配置操作会被后端拦截。

### 4.10 案件工作区文件系统（v1.5 补写，✅ 已实现）

> 每个案件一个独立 MinIO 存储命名空间，承载证据材料、任务产物与系统生成报告，替代 v1.4 散落在各处的文件引用。

- **数据模型**：`police_case_workspaces`（每案件一条，含 `storage_bucket` / `storage_prefix` = `cases/{case_number}/` / `stats`）+ `police_workspace_nodes`（可嵌套文件树，`node_type` = folder/file，`source_type` = manual/task/evidence/system）（详见 §5.2.7）。
- **多来源落盘**：民警手动上传、任务执行产物、证据、系统生成报告均可写入工作区节点；产物经审核后自动落盘（呼应 §6.7 人机协作）。
- **管理接口**：`/api/police/workspaces/{case_id}/*`（init / nodes / folders / upload / download / move / rename）（见 §7.2.7）。

### 4.11 数字警员市场与共享审批（v1.5 补写，✅ 已实现）

> v1.4 未记录数字警员的共享/市场能力。v1.5 在 `police_agents` 中补齐了发布与审批字段，并提供了从市场安装、共享发布、管理员审批的完整链路（详见 §5.2.4）。

- **发布字段**：`author_id`（创建者，NULL=系统预设）、`is_public`、`share_scope`（personal/department/global）、`approval_status`（pending/approved/rejected）、`approved_by` / `approved_at`。
- **共享链路**：民警将自有数字警员 `POST /agents/{agent_id}/share` 发布到市场 → 状态 `pending` → 管理员 `POST /agents/{agent_id}/approve` 审批 → `approved` 后可被他人 `POST /agents/templates/{template_id}/install` 安装（详见 §7.2.5）。
- **系统预设 vs 用户创建**：`PRESET_AGENTS`（DA-001~DA-007）由 `POST /agents/seed` 幂等植入，`is_builtin=1` 不可删除（可停用/修改）；用户自建模板 `is_builtin=0`。

---


## 5. 数据模型设计

### 5.1 核心实体关系

```
┌─────────┐     ┌──────────┐     ┌──────────┐
│  User   │────→│  Case    │────→│  Task    │
│  用户    │  N:M │  案件    │  1:N │  任务    │
└─────────┘     └──────────┘     └──────────┘
     │               │                  │
     │               │                  │
     ▼               ▼                  ▼
┌─────────┐     ┌──────────┐     ┌──────────┐
│  Role   │     │ Evidence │     │  Agent   │
│  角色    │     │  证据    │     │ 智能体   │
└─────────┘     └──────────┘     └──────────┘
                     │                  │
                     ▼                  ▼
                ┌──────────┐     ┌──────────┐
                │Document  │     │AgentRun  │
                │ 文档     │     │ 运行记录 │
                └──────────┘     └──────────┘
```

### 5.2 核心表结构

> ✅ **已实现 — 本节为代码真实结构（v1.5 全量重写）**
>
> **重要修订说明**：v1.4 及之前版本本节使用 `UUID PRIMARY KEY DEFAULT gen_random_uuid()` 主键、无前缀表名（`cases` / `tasks` / `evidence`），**与代码完全不符**，照此建表会全部对不上。真实实现遵循 yuxi 底座规范：
>
> - **主键统一为 `Integer autoincrement`**，不使用 UUID
> - **所有公安业务表统一带 `police_` 前缀**
> - 时间戳为 `DateTime`（`utc_now_naive`，naive UTC），不是 `TIMESTAMPTZ`
> - JSON 字段使用 SQLAlchemy `JSON` 类型（不是 `JSONB`）
> - 保留字规避：`metadata` 为 SQLAlchemy 保留名，业务扩展字段统一命名为 **`extra`**
> - 模型定义位置：`backend/package/yuxi/storage/postgres/models_police.py`（共 17 张表）
> - 建表方式：**无 Alembic**，由 `ensure_business_schema()` 在运行时幂等 `CREATE TABLE IF NOT EXISTS` + 增量补列

#### 5.2.0 表清单总览

| # | 模型类 | 表名 | 职责 |
|---|---|---|---|
| 1 | `PoliceCase` | `police_cases` | 案件主表 |
| 2 | `CaseMember` | `police_case_members` | 案件成员（民警） |
| 3 | `CasePhase` | `police_case_phases` | 案件阶段记录 |
| 4 | `PoliceTask` | `police_tasks` | 任务主表 |
| 5 | `TaskAssignee` | `police_task_assignees` | 任务多执行人（人机协作） |
| 6 | `TaskFlowRule` | `police_task_flow_rules` | 任务流转规则 |
| 7 | `TaskEvent` | `police_task_events` | 任务事件日志 |
| 8 | `Evidence` | `police_evidence` | 证据材料 |
| 9 | `EvidenceLink` | `police_evidence_links` | 证据关联关系（证据链） |
| 10 | `PoliceAgent` | `police_agents` | 数字警员定义 |
| 11 | `PoliceAgentRun` | `police_agent_runs` | 数字警员运行记录 |
| 12 | `PoliceSOP` | `police_sops` | SOP 流程技能定义 |
| 13 | `PoliceAuditLog` | `police_audit_logs` | 审计日志 |
| 14 | `PoliceCaseWorkspace` | `police_case_workspaces` | 案件工作区 |
| 15 | `PoliceWorkspaceNode` | `police_workspace_nodes` | 工作区文件树节点 |
| 16 | `PoliceAdvancementLog` | `police_advancement_logs` | 推进智能体决策日志 |
| 17 | `PoliceTaskTemplate` | `police_task_templates` | 侦查任务模板 |

> **用户表 `users` 属于 yuxi 底座**（`models_business.py`），公安侧仅扩展了警号/警衔/真实姓名等字段，不在本节展开。所有指向用户的外键均为 `users.id`（Integer）。

#### 5.2.1 枚举常量

全部定义于 `models_police.py` 头部，前后端应以此为唯一口径：

```python
CASE_STATUS   = ("draft", "investigation", "arrest", "handling", "prosecution", "closed")
CASE_PHASE    = ("research", "arrest", "handling", "prosecution")

TASK_STATUS = (
    "pending_confirmation",  # 推进智能体生成的任务草案，等待主办民警审查确认
    "pending",               # 已确认通过，等待分配/领取
    "in_progress",           # 进行中
    "review",                # 已提交，等待主办民警审核
    "completed",             # 审核通过，已完成
    "suspended",             # 主办民警主动暂停（可恢复）
    "terminated",            # 侦查方向调整导致终止（保留为历史记录）
    "cancelled",             # 待确认/待开始阶段被驳回或方向调整取消
    "blocked",               # 异常阻塞
)
TASK_PRIORITY = ("urgent", "high", "medium", "low")
ASSIGNEE_TYPE = ("human", "agent")
ASSIGNEE_ROLE = ("executor", "reviewer")      # executor=执行人, reviewer=审核人
EVIDENCE_TYPE = ("transcript", "bank_flow", "screenshot", "audio",
                 "video", "document", "report", "other")

# 涉案要素类型 — 侦查任务模板的触发键（详见 §4.9）
ELEMENT_TYPE = (
    "bank_card",         # 涉案银行卡 / 账户
    "phone",             # 手机号 / 固话
    "wechat",            # 微信号 / QQ 号等社交账号
    "person",            # 涉案人员（嫌疑人 / 关系人 / 受害人）
    "address",           # 涉案地址 / 落脚点 / 案发地
    "vehicle",           # 涉案车辆
    "ip",                # IP 地址 / 设备指纹
    "virtual_currency",  # 虚拟货币地址
    "company",           # 涉案公司 / 商户
    "express",           # 快递单号 / 物流信息
    "device",            # 涉案手机 / 电脑等物证
    "platform_account",  # 平台账号（电商 / 直播 / 游戏）
    "other",
)
```

#### 5.2.2 案件

```sql
-- 案件主表
CREATE TABLE police_cases (
    id                      SERIAL PRIMARY KEY,
    case_number             VARCHAR(50) UNIQUE NOT NULL,          -- 案件编号（索引）
    title                   VARCHAR(200) NOT NULL,
    case_type               VARCHAR(50),                          -- fraud/theft/drug/...（索引）
    description             TEXT,
    status                  VARCHAR(20) DEFAULT 'draft',          -- CASE_STATUS（索引）
    phase                   VARCHAR(30) DEFAULT 'research',       -- CASE_PHASE（索引）
    priority                VARCHAR(10) DEFAULT 'medium',
    advancement_enabled     INTEGER DEFAULT 1,                    -- 1=启用推进智能体 0=手动模式
    investigation_direction TEXT,                                 -- 当前侦查方向（主办民警可调整）
    incident_date           TIMESTAMP,
    incident_location       TEXT,
    total_amount            FLOAT,                                -- 涉案金额（Float，非 DECIMAL）
    victim_info             JSON DEFAULT '{}',
    suspect_info            JSON DEFAULT '[]',
    extra                   JSON DEFAULT '{}',                    -- 扩展字段（原文档写作 metadata）
    knowledge_base_id       VARCHAR(100),                         -- 📋 空壳字段，police 侧暂无读写
    graph_id                VARCHAR(100),                         -- 📋 空壳字段，police 侧暂无读写
    created_by              INTEGER REFERENCES users(id),
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);

-- 案件成员（仅民警；数字警员通过任务执行人关联，不入本表）
CREATE TABLE police_case_members (
    id          SERIAL PRIMARY KEY,
    case_id     INTEGER NOT NULL REFERENCES police_cases(id) ON DELETE CASCADE,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        VARCHAR(20) NOT NULL,        -- commander/handler/reviewer/observer
    joined_at   TIMESTAMP DEFAULT NOW()
);

-- 案件阶段记录
CREATE TABLE police_case_phases (
    id           SERIAL PRIMARY KEY,
    case_id      INTEGER NOT NULL REFERENCES police_cases(id) ON DELETE CASCADE,
    phase        VARCHAR(30) NOT NULL,
    status       VARCHAR(20) DEFAULT 'active',   -- active/completed/skipped
    started_at   TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    summary      TEXT,
    extra        JSON DEFAULT '{}'
);
```

> **与 v1.4 的差异**：原文档 `case_members` 设计为「民警 + 数字警员」多态成员表（`member_type` + 复合主键）。**代码未采用该设计** —— 本表只存民警，数字警员通过 `police_task_assignees`（§5.2.3）以执行人身份参与案件。

#### 5.2.3 任务

```sql
-- 任务主表
CREATE TABLE police_tasks (
    id             SERIAL PRIMARY KEY,
    case_id        INTEGER NOT NULL REFERENCES police_cases(id) ON DELETE CASCADE,
    title          VARCHAR(200) NOT NULL,
    description    TEXT,
    type           VARCHAR(50) NOT NULL,               -- 任务类型（索引）
    status         VARCHAR(20) DEFAULT 'pending',      -- TASK_STATUS（索引）
    assignee_type  VARCHAR(10) NOT NULL,               -- human/agent（主执行人，冗余）
    assignee_id    INTEGER,                            -- users.id 或 police_agents.id
    assignee_name  VARCHAR(100),
    creator_id     INTEGER,
    creator_type   VARCHAR(10) DEFAULT 'human',        -- human/agent/system
    priority       VARCHAR(10) DEFAULT 'medium',
    phase          VARCHAR(30),
    parent_task_id INTEGER REFERENCES police_tasks(id),
    dependencies   JSON DEFAULT '[]',                  -- 依赖任务 ID 列表（JSON，非 UUID[]）
    attachments    JSON DEFAULT '[]',
    result         JSON,
    instructions   TEXT,
    due_date       TIMESTAMP,
    started_at     TIMESTAMP,
    completed_at   TIMESTAMP,
    -- 证据链防篡改签名（§9.5）
    reviewed_by    INTEGER REFERENCES users(id),
    reviewed_at    TIMESTAMP,
    signed_hash    VARCHAR(128),
    -- 关闭原因（cancelled/terminated 时填写：驳回意见 / 方向调整说明）
    close_reason   TEXT,
    -- 推进智能体溯源信息（见下方结构说明）
    extra          JSON DEFAULT '{}',
    created_at     TIMESTAMP DEFAULT NOW(),
    updated_at     TIMESTAMP DEFAULT NOW()
);
```

**`police_tasks.extra` 的推进溯源结构**（替代 v1.4 规划但未实现的 `source_event_id` / `draft_reasoning` / `evidence_refs` 三个独立字段）：

```json
{
  "advancement": {
    "source_task_id":     123,
    "template_id":        7,
    "template_code":      "bank_card_to_flow_query",
    "element_type":       "bank_card",
    "element_value":      "6222***1234",
    "origin":             "template | llm | chain",
    "suggested_assignee": "fund_analyst",
    "direction_change":   false
  }
}
```

```sql
-- ✅ 任务多执行人（v1.5 补写，此前文档完全未记录）
-- 支持一个任务分配给多名民警和/或多个数字警员协同执行，实现「人机协作」。
-- police_tasks 上的 assignee_* 字段保留用于向后兼容，冗余存储主执行人。
CREATE TABLE police_task_assignees (
    id            SERIAL PRIMARY KEY,
    task_id       INTEGER NOT NULL REFERENCES police_tasks(id) ON DELETE CASCADE,
    assignee_type VARCHAR(10) NOT NULL,        -- human / agent
    assignee_id   INTEGER,                     -- users.id 或 police_agents.id
    assignee_name VARCHAR(100),
    role          VARCHAR(20) DEFAULT 'executor',  -- executor=执行人 / reviewer=审核人
    created_at    TIMESTAMP DEFAULT NOW()
);

-- 任务流转规则
CREATE TABLE police_task_flow_rules (
    id                   SERIAL PRIMARY KEY,
    case_id              INTEGER REFERENCES police_cases(id) ON DELETE CASCADE,  -- NULL=全局规则
    name                 VARCHAR(100) NOT NULL,
    trigger_event        VARCHAR(50) NOT NULL,   -- task_completed/file_uploaded/phase_changed
    condition            JSON NOT NULL,
    action               VARCHAR(50) NOT NULL,   -- create_task/notify/auto_approve
    target_task_type     VARCHAR(50),
    target_assignee_type VARCHAR(10),
    target_assignee_id   INTEGER,
    enabled              INTEGER DEFAULT 1,      -- 1=启用 0=禁用（Integer，非 BOOLEAN）
    created_at           TIMESTAMP DEFAULT NOW()
);

-- 任务事件日志
-- ⚠️ 现状：本表用于任务详情页时间线展示（police_service.py 会读取），
--    但**没有任何自动化消费者**，任务流转规则并不由本表驱动。
CREATE TABLE police_task_events (
    id         SERIAL PRIMARY KEY,
    case_id    INTEGER NOT NULL REFERENCES police_cases(id) ON DELETE CASCADE,
    task_id    INTEGER NOT NULL REFERENCES police_tasks(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,   -- created/assigned/started/completed/blocked/file_uploaded
    event_data JSON DEFAULT '{}',
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 5.2.4 数字警员

```sql
-- 数字警员定义（公安专用业务配置；与 yuxi 原生 agents 表互补）
CREATE TABLE police_agents (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(100) NOT NULL,
    description         TEXT,
    type                VARCHAR(50) NOT NULL,     -- transcript_analyst/fund_analyst/...（索引）
    system_prompt       TEXT NOT NULL,
    model_config        JSON NOT NULL,            -- {provider, model, temperature}

    -- 数字警员档案
    badge_number        VARCHAR(20),              -- 工号，如 DA-001（索引）
    rank                VARCHAR(30),              -- 警衔
    specialty           VARCHAR(100),             -- 专业领域
    avatar              VARCHAR(200),
    department          VARCHAR(100),
    color_theme         VARCHAR(20),              -- blue/green/coral/purple/amber

    -- 与 yuxi 原生智能体体系的双向关联
    backend_id          VARCHAR(64),              -- yuxi agents.backend_id（索引）
    agent_id            INTEGER,                  -- yuxi agents 主键（索引）

    -- 能力矩阵
    tools               JSON DEFAULT '[]',        -- ⚠️ 当前执行路径未读取
    skills              JSON DEFAULT '[]',        -- ⚠️ 当前执行路径未读取
    knowledge_base_ids  JSON DEFAULT '[]',        -- ⚠️ 当前执行路径未读取
    capabilities        JSON DEFAULT '[]',        -- 能力标签
    sop_ids             JSON DEFAULT '[]',

    -- 工作统计（系统聚合）
    work_stats          JSON DEFAULT '{}',        -- {tasks_completed, tasks_total, success_rate, ...}

    -- 成长记录
    growth_log          JSON DEFAULT '[]',        -- [{date, event, description}]
    experience_level    INTEGER DEFAULT 1,        -- 1-5

    icon                VARCHAR(50),
    status              VARCHAR(20) DEFAULT 'active',  -- active/offline/training
    is_template         INTEGER DEFAULT 0,
    category            VARCHAR(50),              -- 市场分类（索引）
    install_count       INTEGER DEFAULT 0,
    source_template_id  INTEGER,                  -- 安装来源模板 ID（索引）

    -- 共享与市场发布（v1.5 补写，详见 §4.11）
    author_id           INTEGER,                  -- 创建者 users.id，NULL=系统预设（索引）
    is_public           INTEGER DEFAULT 0,
    share_scope         VARCHAR(20) DEFAULT 'personal',  -- personal/department/global
    approval_status     VARCHAR(20),              -- NULL/pending/approved/rejected
    approved_by         INTEGER,
    approved_at         TIMESTAMP,

    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- 数字警员运行记录
CREATE TABLE police_agent_runs (
    id           SERIAL PRIMARY KEY,
    agent_id     INTEGER REFERENCES police_agents(id),
    task_id      INTEGER REFERENCES police_tasks(id),
    case_id      INTEGER REFERENCES police_cases(id) ON DELETE CASCADE,
    status       VARCHAR(20) DEFAULT 'queued',   -- queued/running/completed/failed/cancelled
    input        JSON,
    output       JSON,
    artifacts    JSON DEFAULT '[]',
    error        TEXT,
    tokens_used  INTEGER DEFAULT 0,
    duration_ms  INTEGER,
    started_at   TIMESTAMP,
    completed_at TIMESTAMP,
    created_at   TIMESTAMP DEFAULT NOW()
);
```

> **v1.4 规划的 `agent_messages` 表未实现**（全库 0 命中）。对话历史由 yuxi 底座的会话体系承载，公安侧不再单独建表。

#### 5.2.5 证据

```sql
-- 证据材料
CREATE TABLE police_evidence (
    id             SERIAL PRIMARY KEY,
    case_id        INTEGER NOT NULL REFERENCES police_cases(id) ON DELETE CASCADE,
    task_id        INTEGER REFERENCES police_tasks(id),
    name           VARCHAR(200) NOT NULL,
    type           VARCHAR(50) NOT NULL,        -- EVIDENCE_TYPE（索引）
    file_path      VARCHAR(500) NOT NULL,       -- MinIO 存储路径
    file_hash      VARCHAR(64),                 -- SHA-256 文件内容哈希
    file_size      INTEGER,
    mime_type      VARCHAR(100),
    ocr_text       TEXT,
    parsed_content JSON,
    extra          JSON DEFAULT '{}',
    uploaded_by    INTEGER REFERENCES users(id),
    version        INTEGER DEFAULT 1,
    parent_id      INTEGER REFERENCES police_evidence(id),   -- 上一版本
    -- 防篡改签名（§9.5）
    reviewed_by    INTEGER REFERENCES users(id),
    reviewed_at    TIMESTAMP,
    signed_hash    VARCHAR(128),
    created_at     TIMESTAMP DEFAULT NOW()
);

-- 证据关联关系（证据链）
CREATE TABLE police_evidence_links (
    id                 SERIAL PRIMARY KEY,
    case_id            INTEGER NOT NULL REFERENCES police_cases(id) ON DELETE CASCADE,
    source_evidence_id INTEGER NOT NULL REFERENCES police_evidence(id) ON DELETE CASCADE,
    target_evidence_id INTEGER NOT NULL REFERENCES police_evidence(id) ON DELETE CASCADE,
    relation_type      VARCHAR(50),      -- derives_from / supports / contradicts
    description        TEXT,
    created_at         TIMESTAMP DEFAULT NOW()
);
```

> `relation_type = 'contradicts'`（矛盾关系）已在模型层预留，但当前业务流程中尚无写入方，属可用于后续「反证 / 矛盾清单」能力的埋点。

#### 5.2.6 SOP / 办案规程

```sql
-- ⚠️ 部分实现：表与 CRUD 已实现，但**无执行器、无实例表**，状态机不会真正运行
CREATE TABLE police_sops (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    agent_type      VARCHAR(50),           -- 关联的数字警员类型（索引）
    category        VARCHAR(50),           -- transcript/fund_analysis/legal_review/evidence_collection
    version         INTEGER DEFAULT 1,
    states          JSON NOT NULL,         -- 状态机节点：[{id,name,description,actions,transitions:[{to,condition}]}]
    initial_state   VARCHAR(50) NOT NULL,
    terminal_states JSON DEFAULT '[]',
    input_schema    JSON DEFAULT '{}',
    output_template TEXT,
    is_published    INTEGER DEFAULT 0,     -- 0=草稿 1=已发布
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
```

> **与 v1.4 的差异**：原文档设计的 `business_domain` / `steps` / `trigger_event` / `call_count` / `good_rate` / `bad_rate` / `created_by` 字段**均未实现**；实际采用 `agent_type` + `category` + 状态机三件套（`states` / `initial_state` / `terminal_states`）。
> **v1.4 规划的 `sop_instances`（SOP 执行实例表）与 `officer_feedback`（警员评价表）全库 0 命中，均未实现**，对应的「SOP 调用统计」「好评率 / 成长轨迹」功能目前无数据支撑。

#### 5.2.7 案件工作区（v1.5 补写）

```sql
-- 案件独立工作区：每个案件一个 MinIO 存储命名空间
CREATE TABLE police_case_workspaces (
    id                SERIAL PRIMARY KEY,
    case_id           INTEGER NOT NULL UNIQUE REFERENCES police_cases(id) ON DELETE CASCADE,
    case_number       VARCHAR(50) NOT NULL,      -- 冗余，用于构造存储路径
    storage_bucket    VARCHAR(64) NOT NULL DEFAULT 'police-workspace',
    storage_prefix    VARCHAR(255) NOT NULL,     -- cases/{case_number}/
    knowledge_base_id VARCHAR(100),              -- 📋 预留：案件专属知识库（Milvus collection）
    graph_id          VARCHAR(100),              -- 📋 预留：案件专属图谱（Neo4j）
    status            VARCHAR(20) DEFAULT 'ready',  -- ready / initializing
    stats             JSON DEFAULT '{}',         -- {evidence_count, material_count, report_count, total_size}
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW()
);

-- 工作区文件树节点（可嵌套）
CREATE TABLE police_workspace_nodes (
    id             SERIAL PRIMARY KEY,
    workspace_id   INTEGER NOT NULL REFERENCES police_case_workspaces(id) ON DELETE CASCADE,
    parent_id      INTEGER REFERENCES police_workspace_nodes(id) ON DELETE CASCADE,
    node_type      VARCHAR(20) NOT NULL DEFAULT 'file',   -- folder / file
    name           VARCHAR(255) NOT NULL,
    storage_path   VARCHAR(1024),                -- MinIO 对象路径（文件夹为空）
    mime_type      VARCHAR(100),
    size           INTEGER,                      -- 字节
    source_type    VARCHAR(20),                  -- manual / task / evidence / system
    source_task_id INTEGER REFERENCES police_tasks(id),
    created_by     INTEGER REFERENCES users(id),
    extra          JSON DEFAULT '{}',
    created_at     TIMESTAMP DEFAULT NOW(),
    updated_at     TIMESTAMP DEFAULT NOW()
);
```

#### 5.2.8 推进决策日志（v1.5 补写）

```sql
-- 案件推进智能体每一次决策的完整上下文（满足 §6.7 可审计、可解释要求）
CREATE TABLE police_advancement_logs (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER NOT NULL REFERENCES police_cases(id) ON DELETE CASCADE,
    trigger_task_id INTEGER REFERENCES police_tasks(id),
    decision_type   VARCHAR(30) NOT NULL,   -- 见下表（索引）
    summary         TEXT,                   -- 决策摘要（一句话）
    details         JSON DEFAULT '{}',      -- {source_task, direction, generated_tasks, reasoning, model, duration_ms}
    created_by      INTEGER REFERENCES users(id),  -- 触发人；后台自动触发为 NULL
    created_at      TIMESTAMP DEFAULT NOW()
);
```

| `decision_type` | 含义 |
|---|---|
| `task_draft` | 根据完成任务生成任务草案 |
| `direction_change` | 侦查方向调整，重新规划任务 |
| `phase_summary` | 阶段全部完成，生成阶段小结与下一阶段建议 |
| `no_action` | 评估后认为暂不需要新任务（附 reasoning） |

> 本表是 v1.4 规划的 `police_case_advancement_agents`（每案件一个推进智能体实例表）的**实际替代方案**。代码未采用"每案件实例"模型，推进服务为**模块级单例**，决策上下文改为按次落 log。

#### 5.2.9 侦查任务模板（v1.5 补写）

```sql
-- 把「涉案要素 → 侦查任务」的映射规则从 prompt 中外置为可配置数据（详见 §4.9）
CREATE TABLE police_task_templates (
    id                  SERIAL PRIMARY KEY,
    code                VARCHAR(64) UNIQUE NOT NULL,   -- 唯一标识，内置模板幂等植入用（索引）
    name                VARCHAR(120) NOT NULL,         -- 如「银行卡 → 调取流水」
    description         TEXT,
    -- 触发条件
    element_type        VARCHAR(30),        -- ELEMENT_TYPE；NULL=仅链式触发（索引）
    case_types          JSON DEFAULT '[]',  -- 适用案件类型；空=全部
    phases              JSON DEFAULT '[]',  -- 适用案件阶段；空=全部
    source_task_types   JSON DEFAULT '[]',  -- 限定触发源任务类型；空=任意
    -- 生成的任务
    task_title          VARCHAR(200) NOT NULL,   -- 支持占位符
    task_type           VARCHAR(50) NOT NULL,
    task_description    TEXT,
    instructions        TEXT,               -- 依据/办理指引（展示在草案审查界面）
    priority            VARCHAR(10) DEFAULT 'medium',
    suggested_agent_type VARCHAR(50),       -- 建议召唤的数字警员 type
    due_days            INTEGER,            -- 相对期限（天）；NULL=不设期限
    -- 链式推进
    next_template_codes JSON DEFAULT '[]',  -- 本模板生成的任务完成后接续触发的模板 code
    -- 管理字段
    enabled             INTEGER DEFAULT 1,  -- 1=启用 0=停用（索引）
    is_builtin          INTEGER DEFAULT 0,  -- 1=内置模板（不可删除，可停用/修改）
    sort_order          INTEGER DEFAULT 100,
    created_by          INTEGER REFERENCES users(id),
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);
```

**模板占位符**（可用于 `task_title` / `task_description` / `instructions`）：

| 占位符 | 含义 |
|---|---|
| `{element}` | 要素中文名（如「银行卡」） |
| `{element_value}` | 要素值（如「6222***1234」） |
| `{case_title}` | 案件名称 |
| `{case_number}` | 案件编号 |
| `{source_task}` | 触发源任务标题 |

#### 5.2.10 审计日志

```sql
CREATE TABLE police_audit_logs (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER,                  -- 索引
    user_name     VARCHAR(100),
    action        VARCHAR(50) NOT NULL,     -- create/update/delete/login/assign/approve/reject
    resource_type VARCHAR(50),              -- case/task/agent/evidence/document
    resource_id   INTEGER,
    case_id       INTEGER,                  -- 索引
    details       JSON,
    ip_address    VARCHAR(45),              -- VARCHAR，非 INET
    user_agent    TEXT,
    created_at    TIMESTAMP DEFAULT NOW()
);
```

#### 5.2.11 知识图谱 Schema（Neo4j）

> 📋 **规划中** — 以下 Schema 尚未在公安业务侧落地，Neo4j / Milvus 在所有 `police_*` 代码中均无调用。保留作为 §4.4 的设计目标。

```cypher
// 节点
(:Person {id, name, id_card, phone, role: 'suspect|victim|witness'})
(:Account {id, account_number, bank, type: 'bank|alipay|wechat'})
(:Communication {id, platform: 'wechat|qq|phone', account_id})
(:Location {id, address, type})
(:Organization {id, name, type})
(:Event {id, type, timestamp, description})

// 关系
(:Person)-[:OWNS {since}]->(:Account)
(:Person)-[:USES {since}]->(:Communication)
(:Person)-[:TRANSFERRED {amount, time, count}]->(:Account)
(:Person)-[:CONTACTED {platform, count, last_time}]->(:Person)
(:Person)-[:APPEARED_AT {time}]->(:Location)
(:Person)-[:MEMBER_OF {role}]->(:Organization)
(:Person)-[:RELATED_TO {type: 'family|accomplice|friend'}]->(:Person)
```
---

## 6. 数字警员设计

> **概念映射（v1.3 关键）**：数字警员 = Yuxi Agent；数字警员的原子能力 = Yuxi Skill；数字警员在专案中的编排 = LangGraph 状态机 + SOP（见 4.8 节）。
> 数字警员有两种参与方式：**直接对话模式**（民警点对点调用其技能，见 1.4 模式 A）与 **专案协同模式**（被编入专案组、由案件编排官按 SOP 调度，见 1.4 模式 B）。

### 6.1 数字警员概览

| 数字警员 | 职责 | 输入 | 输出 | 关联技能/任务类型 |
|--------|------|------|------|-------------|
| 笔录分析师 | 分析报案笔录，提取关键信息 | 笔录文档 | 结构化案件信息 + 初始工作项 | transcript_analysis |
| 资金追踪师 | 分析银行流水，追踪涉案资金 | 流水文件 | 资金追踪报告 + 下级账户清单 | fund_analysis |
| 调证生成师 | 生成调取通知书等法律文书 | 调证需求 | 法律文书文档 | evidence_collection |
| 法制审核官 | 审核案件程序合规性 | 案件材料 | 审核意见 + 整改建议 | legal_review |
| 文书生成师 | 生成各类法律文书 | 案件信息 | 法律文书文档 | document_generation |
| 证据梳理员 | 梳理证据链，生成证据清单 | 证据材料 | 证据链报告 | knowledge_extraction |
| 案件编排官 | 分析案件进展，按 SOP 调度各数字警员 | 案件上下文 | SOP 实例推进 / 新工作项创建指令 | (编排层，不直接接任务) |

> 🔀 **v1.5 修订**：v1.4 本节列出的「文书生成师 / 证据梳理员」**在代码中不存在**（`PRESET_AGENTS` 全库仅 7 个，无此二者）；而代码中实际存在的 **DA-006 群聊分析专家、DA-007 审讯辅助专家** 本节原未列出。下表已按 `backend/package/yuxi/services/police_prompts.py` 的 `PRESET_AGENTS` 修正。

| 工号 | 数字警员 | `type` | 职责 | 输入 | 输出 | 专用 PRD 小节 |
|------|----------|--------|------|------|------|--------------|
| DA-001 | 笔录分析师 | `transcript_analyst` | 分析报案笔录，提取关键信息 | 笔录文档 | 结构化案件信息 + 初始工作项 | §6.2 |
| DA-002 | 资金追踪师 | `fund_analyst` | 分析银行流水，追踪涉案资金 | 流水文件 | 资金追踪报告 + 下级账户清单 | §6.3 |
| DA-003 | 调证生成师 | `evidence_collector` | 生成调取通知书等法律文书 | 调证需求 | 法律文书文档 | §6.4 |
| DA-004 | 法制审核官 | `legal_reviewer` | 审核案件程序合规性 | 案件材料 | 审核意见 + 整改建议 | §6.5 |
| DA-005 | 案件编排官（推进智能体） | `case_orchestrator` | 读分析结果、提取要素、生成任务草案、推阶段 | 案件上下文 | 推进决策 / 任务草案 | §6.6 |
| DA-006 | 群聊分析专家 | `chat_analyst` | 分析聊天记录等电子数据中关联关系 | 聊天记录 + 案件背景 | 群聊研判报告 | 📋 待补写 |
| DA-007 | 审讯辅助专家 | `interrogation_advisor` | 基于笔录与证据给出审讯策略 | 笔录 + 证据 + 案件背景 | 审讯策略报告 | 📋 待补写 |

> DA-006 / DA-007 已在 `PRESET_AGENTS` 中落地（prompt + 档案字段齐全），但本文档尚未为其单独撰写 PRD 小节，标记为「待补写」。

### 6.2 笔录分析师（数字警员）

```
职责: 分析报案笔录，提取案件关键信息，自动创建案件和初始任务

输入:
  - 笔录文档 (PDF/Word/图片，经OCR转文本)

处理流程:
  1. 文档解析: OCR → 纯文本
  2. 信息提取:
     - 案件基本信息: 类型、时间、地点、涉案金额
     - 当事人信息: 受害人、嫌疑人、证人
     - 涉案账户: 银行卡号、支付宝账号、微信账号
     - 涉案通讯: 微信号、QQ号、手机号
     - 作案手法: 诈骗方式、转账路径
  3. 结构化输出: 生成案件信息 JSON
  4. 任务规划: 根据提取的信息，生成初始任务列表

输出:
  - 案件结构化信息 (JSON)
  - 初始任务列表 (按优先级排序)
  - 涉案实体清单 (供知识图谱构建)

系统提示词 (核心):
  你是一个专业的公安笔录分析助手。请仔细阅读报案笔录，提取以下信息：
  1. 案件基本信息（类型、时间、地点、金额）
  2. 所有提及的人员（姓名、身份证号、角色）
  3. 所有提及的账户（账号、开户行、类型）
  4. 所有提及的通讯方式（微信号、QQ号、手机号）
  5. 案件经过描述
  6. 需要进一步调查的事项
  请以结构化 JSON 格式输出，并标注每条信息的来源原文。
```

### 6.3 资金追踪师（数字警员）

```
职责: 分析银行/第三方支付流水，追踪涉案资金流向

输入:
  - 流水文件 (Excel/CSV/PDF)
  - 已知涉案账户列表
  - 案件背景信息

处理流程:
  1. 流水解析 (Python/Pandas):
     - 解析银行流水格式，标准化为统一 DataFrame
     - 字段映射: 交易时间/金额/对方账号/对方户名/摘要/余额
     - 去重: 同一笔交易可能跨多次导入，按交易流水号去重
  2. 资金追踪 (Python/Pandas + NetworkX):
     - 从受害人转出点开始，逐级追踪资金流向，构建转账拓扑图
     - 识别资金归集账户（多个账户转入同一账户）
     - 识别资金分散账户（一个账户转出至多个账户）
     - 识别快进快出模式（资金快速转入转出，间隔 < 1小时）
  3. 异常分析 (Python/Pandas):
     - 大额异常交易（金额 > 阈值或 > 均值 3σ）
     - 频繁小额交易（疑似拆分转移，单日同向 > 10 笔且金额接近）
     - 深夜/凌晨交易（00:00-06:00）
     - 跨境转账
  4. 统计摘要生成 (Python/Pandas):
     - 涉案账户资金总量汇总表
     - 账户间转账次数与金额矩阵
     - Top 10 异常交易节点清单（含金额/时间/对手方）
     - 账户活跃时段分布直方图数据
     - 资金流向拓扑图节点-边数据（JSON，供前端 G6 渲染）
  5. 报告生成 (LLM):
     - 输入: 仅 Python 步骤产出的统计摘要 + Top 10 异常节点
     - 输出: 人可读的《资金分析总结报告》(Markdown)
     - 报告内容: 涉案资金总体情况/主要资金流向/异常交易分析/可疑账户研判/下一步建议

输出:
  - 资金分析报告 (Markdown, LLM 生成)
  - 资金流向图数据 (JSON, Python 生成, 供前端 G6 渲染)
  - 下级账户调取清单 (JSON, Python 生成, 自动创建调证任务)
  - 异常交易明细表 (Excel, Python 生成)

工具:
  - parse_bank_statement (Python): 解析银行流水文件 → DataFrame
  - calculate_flow (Python): 计算资金流向拓扑 → NetworkX Graph
  - detect_anomaly (Python): 异常交易检测 → 异常交易列表
  - generate_summary (Python): 生成统计摘要 → JSON
  - generate_report (LLM): 基于摘要生成人可读报告 → Markdown
  - create_task: 创建下级调证任务
```

> **⚠️ Token 与性能瓶颈防范（关键设计约束）**
>
> 一份银行流水往往有 **数万条交易记录**，直接扔给 LLM 即使有大上下文窗口也会出现：
> - **幻觉**：LLM 在超长上下文中遗漏或编造交易记录
> - **爆 Token / 超时**：数万条记录轻易超过模型上下文限制
> - **成本失控**：每次分析消耗数十万 Token
> - **不可复现**：LLM 对数值计算结果不可靠
>
> **必须遵守的分治原则**：
>
> | 环节 | 执行者 | 输入 | 输出 | 说明 |
> |------|--------|------|------|------|
> | 流水解析 | Python / Pandas | 原始流水文件 | 标准化 DataFrame | 不同银行格式适配 |
> | 数据清洗 | Python / Pandas | DataFrame | 去重后的 DataFrame | 按交易流水号去重 |
> | 资金追踪 | Python / NetworkX | DataFrame | 转账拓扑图 (Graph) | 逐级追踪资金流向 |
> | 异常检测 | Python / Pandas | DataFrame | 异常交易列表 | 统计规则 + 阈值 |
> | 统计摘要 | Python / Pandas | DataFrame + Graph | 摘要 JSON (Top 10 + 统计表) | **压缩到 < 2000 Token** |
> | 报告生成 | **LLM** | **仅摘要 JSON** | Markdown 报告 | 只做"阅读理解+文字组织" |
> | 下级账户筛选 | Python / Pandas | Graph + 异常列表 | 账户清单 JSON | 规则驱动，非 LLM |
>
> **核心原则：LLM 只负责"读摘要、写报告"，不负责"算数字"。所有数值计算必须由 Python 确定性完成。**
>
> 开发时的 AI Prompt 示例：
> > "开发资金分析智能体的 Python 工具函数。要求：使用 Pandas 读取银行流水 Excel，按交易流水号去重，用 NetworkX 构建转账拓扑图，输出 Top 10 异常交易节点的 JSON 摘要（控制在 2000 Token 以内）。摘要格式为：{total_amount, account_summary[], top_anomalies[], next_level_accounts[]}。这个摘要后续会作为 LLM 的输入生成报告。"

### 6.4 调证生成师（数字警员）

```
职责: 根据调证需求生成法律文书（调取通知书等）

输入:
  - 调证需求 (账户列表、查询事项)
  - 案件基本信息
  - 法律依据库 (知识库)

处理流程:
  1. 需求解析: 确定需要调取的内容类型（银行流水/微信信息/通话记录等）
  2. 法律依据匹配: 从法律知识库中检索对应的法律条款
  3. 文书生成: 基于文书模板 + 案件信息 + 法律依据生成文书
  4. 格式校验: 检查文书格式是否符合规范

输出:
  - 调取通知书 (Word/PDF)
  - 文书元数据 (调取对象、事项、法律依据)

工具:
  - search_legal_basis: 检索法律依据
  - generate_document: 生成法律文书
  - validate_format: 格式校验
```

### 6.5 法制审核官（数字警员）

```
职责: 审核案件办理程序的合法合规性

输入:
  - 案件全量材料
  - 证据清单
  - 办案流程记录

处理流程:
  1. 程序审查:
     - 立案手续是否完备
     - 强制措施是否合法
     - 侦查活动是否规范
     - 期限是否符合规定
  2. 证据审查:
     - 证据收集程序是否合法
     - 证据是否确实充分
     - 证据链是否完整
  3. 定性审查:
     - 案件定性是否准确
     - 适用法律是否正确
  4. 输出审核意见:
     - 合规项 / 不合规项 / 风险提示
     - 整改建议

输出:
  - 法制审核意见书 (Markdown)
  - 整改任务清单 (JSON, 自动创建整改任务)

工具:
  - search_legal_knowledge: 检索法律知识库
  - check_procedure: 程序合规检查
  - check_evidence: 证据链检查
  - create_task: 创建整改任务
```

### 6.6 案件推进智能体（数字警员）

> **v1.4 重定位**：原「案件编排官」从模糊的"调度中枢"升级为职责清晰的「案件推进智能体」。不再直接执行任何分析任务，纯粹做推进决策——读取分析结果、生成任务草案、盯进度、推阶段。所有决策必须经主办民警审查确认后方可生效。

```
职责: 案件的 AI 推进者，不是决策者

推进智能体是"建议者"而非"指挥者":
  - 读取分析结果（笔录分析、资金追踪等），提取涉案要素
  - 将涉案要素映射为侦查任务草案，标注依据来源
  - 感知任务审核通过事件（`review_task` 后以 `asyncio.create_task` 进程内触发，非轮询、非队列），判断阶段是否闭环
  - 根据模板生成下一阶段任务草案，推给主办民警审查
  - 侦查方向变更时，分析受影响任务并生成处理建议

推进智能体不做:
  - 不判断涉案要素的侦查价值（留给主办民警）
  - 不决定侦查方向是否调整（留给主办民警）
  - 不对案件做定性判断（留给主办民警）
  - 不越过主办民警做任何决策

🔀 **实现方式不同（v1.5 修订）**：v1.4 计划为「每案件实例化一个推进智能体 + LangGraph StateGraph 状态机 + ARQ 队列驱动」。**代码实际未采用**，真实实现为：

- **进程内单例**：`PoliceAdvancementService` 为模块级单例，不按案件实例化；`police_case_advancement_agents` 表全库 0 命中（不存在）。
- **线性管线，非状态机**：`advance_after_task_completed()` 是一条**顺序执行的管线**——① 提取涉案要素 → ② 匹配侦查任务模板 → ③ 生成任务草案。无 LangGraph `StateGraph`、无 `while/for` 循环迭代 LLM、无终止条件判断。
- **进程内触发，非 ARQ**：由 `PoliceTaskService.review_task()` 在审核通过后以 `asyncio.create_task(self._trigger_advancement(...))` 进程内异步触发，**不经过任何 ARQ 队列**（项目虽引入 ARQ，但推进智能体未使用）。

推进管线（线性顺序执行，非循环状态机）：

  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │ 1. 提取要素   │───▶│ 2. 匹配模板   │───▶│ 3. 生成草案   │
  │ 读取审核通过  │    │ 涉案要素 →    │    │ 组装任务草案  │
  │ 任务的产出    │    │ 命中模板规则  │    │ 等待民警审查  │
  └──────────────┘    └──────────────┘    └──────────────┘
        (review_task 后 asyncio.create_task 进程内触发，非 ARQ 推送)
```

**触发条件（EARS 格式）**：

- **[Event-driven]** **When** 任务状态变更为 `completed`，推进智能体 **shall** 接收完成事件，读取任务执行结果。
- **[Event-driven]** **When** 案件阶段变化，推进智能体 **shall** 基于新阶段模板重新规划任务草案。
- **[Event-driven]** **When** 主办民警提交侦查方向调整，推进智能体 **shall** 列出受影响任务清单并生成处理建议，待确认后执行。
- **[State-driven]** **While** 案件处于特定阶段，推进智能体 **shall** 仅生成该阶段范畴内的任务类型。
- **[Optional]** **Where** 主办民警启用了推进智能体（`advancement_enabled=1`），推进智能体 **shall** 主动生成推进建议；**Where** 未启用，主办民警手动管理所有任务。

**任务草案生成示例**：

```
【场景】笔录分析智能体完成分析，输出包含涉案银行卡要素

推进智能体感知到「笔录分析」任务完成
  │
  ▼
读取结果 → 提取要素: 银行卡 6222****1234（涉案收款卡）
  │
  ▼
匹配模板: "涉案银行卡" → task_type: bank_flow_query
  │
  ▼
生成任务草案:
  ┌─────────────────────────────────────────┐
  │ 任务: 调取银行卡 6222****1234 交易流水     │
  │ 类型: bank_flow_query                    │
  │ 阶段: 立案侦查                            │
  │ 优先级: high                              │
  │ 依据: 笔录分析报告 §三 关键实体 —          │
  │       "嫌疑人供述该卡用于收取赃款"            │
  │ 建议执行人: DA-002 资金追踪师               │
  │ 前置条件: 无                               │
  │ 产出要求: 银行流水文件 + 资金分析初报        │
  └─────────────────────────────────────────┘
  │
  ▼
推送给主办民警审查 → 状态: pending_confirmation
```

**任务模板映射（初始版本，Phase 3.1 扩展为可配置规则引擎）**：

| 涉案要素 | 任务类型 | 建议执行人 | 阶段 |
|---|---|---|---|
| 银行卡号 | bank_flow_query | DA-002 资金追踪师 | 立案侦查 |
| 手机号 | call_record_query | agent(协查) | 立案侦查 |
| 微信号 | wechat_record_query | agent(协查) | 立案侦查 |
| 关系人（姓名+身份证号） | summons | agent(文书生成) | 立案侦查 |
| 关系人（无身份证号） | identity_verification | agent(协查) | 初查 |
| 涉案公司 | company_info_query | agent(协查) | 初查 |
| 涉案金额 ≥ 阈值 | freeze_approval | 主办民警 | 立案侦查 |
| 资金链路完整 | fund_analysis | DA-002 资金追踪师 | 立案侦查 |
| 证据链完整 | legal_review | DA-004 法制审核官 | 移送起诉 |
| 嫌疑人到案 | interrogation | DA-007 审讯辅助 | 收网 |
| 上游银行卡流水已调取 | fund_analysis | DA-002 | 立案侦查 |

**技术实现要点（v1.5 按代码修正）**：

- 🔀 推进由 `review_task()` 审核通过后以 `asyncio.create_task()` **进程内**异步触发，**没有 ARQ `case_advancement` 队列**
- ⚠️ 幂等仅靠进程内单例 + 串行 `create_task` 近似保证，**无分布式锁**；多副本部署存在并发重复触发风险（见 §0.2 技术债）
- LLM 调用走 `custom-openai:agnes-2.5-flash`（两次 `ainvoke`：要素提取、草案生成）
- 🔀 **不存在** `police_case_advancement_agents` 表；每次推进决策写入 `police_advancement_logs`（`decision_type` ∈ task_draft / direction_change / phase_summary / no_action），详见 §5.2.8
- 推进决策同时写入审计日志（`police_audit_logs`）

### 6.7 多智能体协作架构

> **v1.4 新增**：定义数字警员之间的协作层级、人机协作协议、任务生命周期和侦查方向变更机制。

#### 6.7.1 三层智能体模型

```
┌─────────────────────────────────────────────────────┐
│                    主办民警 (Human)                    │
│   · 对案件全局负责                                     │
│   · 审查任务草案、确认/驳回/追加                          │
│   · 决定侦查方向、做复杂判断                             │
│   · 审核智能体产出成果                                  │
└──────────────────────┬──────────────────────────────┘
                       │ 审查确认、方向决策
┌──────────────────────▼──────────────────────────────┐
│              案件推进智能体 (Advancement Agent)         │
│   · 每个案件一个实例，跟随案件生命周期                      │
│   · 读取分析结果，提取涉案要素                            │
│   · 根据要素生成任务草案，推给主办民警审查                   │
│   · 感知任务完成事件，判断阶段是否闭环                      │
│   · 根据模板生成下一阶段任务草案                           │
│   · 不越过主办民警做任何决策                              │
└──────────────────────┬──────────────────────────────┘
                       │ 召唤、分配执行任务
┌──────────────────────▼──────────────────────────────┐
│           执行智能体 (Execution Agents)                 │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│   │ 笔录分析  │ │ 资金追踪  │ │ 调证生成  │  ...       │
│   │ DA-001   │ │ DA-002   │ │ DA-003   │            │
│   └──────────┘ └──────────┘ └──────────┘            │
│   可复用工具型 Agent，民警在任务中按需召唤                   │
│   · 接受任务输入，产出结构化结果                            │
│   · 不感知案件全局，不主动推进                              │
└─────────────────────────────────────────────────────┘
```

| 角色 | 命名 | 职责 | 决策权限 |
|---|---|---|---|
| 人类 | **主办民警** | 案件全局负责、复杂决策、成果审核 | 最终决策权 |
| AI | **案件推进智能体** | 要素→任务草案、盯进度、推阶段 | 建议权，无决策权 |
| AI | **执行智能体** | 具体分析/生成/查询 | 执行权（在分配范围内） |

#### 6.7.2 任务状态机（扩展）

在现有状态基础上扩展，支持推进智能体生成任务草案和侦查方向变更：

```
                     推进智能体生成
                          │
                          ▼
                    ┌──────────┐
                    │  待确认   │ ← pending_confirmation [新增]
                    └────┬─────┘     主办民警审查任务草案
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         确认通过     驳回       修改后确认
              │       (已取消)       │
              ▼                     │
         ┌──────────┐              │
         │  待开始   │ ← pending   │
         └────┬─────┘
              │ 民警领取/分配
              ▼
         ┌──────────┐
         │  进行中   │ ← in_progress
         └────┬─────┘   民警可召唤执行智能体
              │
    ┌─────────┼─────────┐
    ▼         ▼         ▼
┌────────┐ ┌────────┐ ┌────────┐
│ 已完成  │ │ 已暂停  │ │ 已终止  │
│completed│ │suspended│ │terminated│
│        │ │[新增]   │ │[新增]   │
└───┬────┘ └────────┘ └────────┘
    │
    ▼
  审核通过
    │
    ▼
 事件推送 → 推进智能体感知
```

**新增状态说明**：

| 状态 | 常量 | 说明 | 触发者 |
|---|---|---|---|
| 待确认 | `pending_confirmation` | 推进智能体生成的任务草案，等待主办民警审查 | 推进智能体 |
| 已暂停 | `suspended` | 主办民警手动暂停 | 主办民警 |
| 已终止 | `terminated` | 因侦查方向调整而终止 | 主办民警（确认方向调整后系统标记） |
| 已取消 | `cancelled` | 待确认阶段被驳回或方向调整前被取消 | 主办民警 |

**任务类型**：

| 类型 | 说明 | 示例 |
|---|---|---|
| 常规侦查任务 | 推进智能体根据涉案要素生成的侦查任务 | "调取银行卡 6222****1234 流水" |
| 子任务 | 民警将大任务拆分为可执行的小步骤 | "生成调取文书"、"通过大数据平台发协查" |
| 核查任务 | 推进智能体感知上下游数据就绪后生成的复核任务 | "资金分析"（前置条件：银行流水已调取） |
| 审批任务 | 需要主办民警或审核人审批的人工任务 | "审核逮捕申请书" |

#### 6.7.3 主办民警审查任务草案

推进智能体生成的任务草案进入 `pending_confirmation` 状态后，主办民警在个人工作台审查：

```
┌─────────────────────────────────────────────────┐
│  📋 推进智能体建议新增 3 个侦查任务                  │
│                                                   │
│  ☑ 调取银行卡 6222****1234 交易流水   [high]       │
│    依据: 笔录分析报告 §三 — 嫌疑人供述该卡用于收款    │
│    建议: DA-002 资金追踪师                          │
│                                                   │
│  ☑ 调取手机号 138****8888 通话记录   [medium]      │
│    依据: 笔录分析报告 §三 — 涉案通联记录未调取       │
│    建议: agent(大数据协查)                          │
│                                                   │
│  ☐ 传唤关系人 张三   [urgent]                      │
│    依据: 笔录分析报告 §五 — 张三参与分赃             │
│    驳回原因: [主办民警填写]                          │
│                                                   │
│  [+ 手动追加任务]                                  │
│                                                   │
│  [确认通过]  [全部驳回]                             │
└─────────────────────────────────────────────────┘
```

- **[Ubiquitous]** 推进智能体 **shall** 为每一条任务草案标注「建议依据」，引用原始分析材料的具体章节。
- **[Event-driven]** **When** 主办民警确认任务草案，已确认的任务 **shall** 自动转入 `pending` 状态。
- **[Event-driven]** **When** 主办民警驳回某项建议，该草案 **shall** 记录驳回原因后转入 `cancelled` 状态。
- **[Event-driven]** **When** 主办民警手动追加任务，该任务 **shall** 直接进入 `pending` 状态。

#### 6.7.4 民警在任务中召唤执行智能体

```
民警领取任务 "调取银行卡 6222****1234 交易流水"
  │
  ├─ 拆分子任务:
  │    1. 生成调取证据通知书 → 召唤 DA-003 调证生成师
  │    2. 通过大数据平台发协查 → 手动执行
  │    3. 上传调证结果 → 手动上传
  │
  └─ 子任务完成、结果审核通过后
       → 主任务标记为 completed
       → 事件推送 → 推进智能体感知
```

- **[Event-driven]** **When** 民警召唤执行智能体，系统 **shall** 创建子任务并关联该智能体作为执行人，自动填充任务上下文。
- **[Ubiquitous]** 执行智能体的产出 **shall** 经民警审核确认后方可写入任务成果；未经审核的产出仅标记为"草稿"。
- **[Ubiquitous]** 民警 **shall** 对所有经由智能体产出的成果负责。

#### 6.7.5 侦查方向变更

当主办民警决定调整侦查方向时，不删除已有工作记录，而是做增量处理：

```
主办民警决定调整侦查方向
  │
  ▼
推进智能体分析当前任务清单:
  ┌────────────────────────────────────────┐
  │ 已完成 (5) → 保留，打标签 [侦查阶段一]    │
  │ 进行中 (2) → 高亮，请主办民警逐条决定:    │
  │   · [继续] 方向调整不冲突               │
  │   · [终止] 立即中止                     │
  │   · [暂停] 暂时挂起                     │
  │ 待开始 (3) → 建议批量取消                │
  └────────────────────────────────────────┘
  │
  ▼
主办民警确认后 → 推进智能体基于新方向重新规划任务草案
  │
  ▼
案件时间线记录: "2026-08-03 14:30 主办民警调整侦查方向
  原方向: 电信诈骗 → 新方向: 洗钱下游追查"
```

- **[Event-driven]** **When** 主办民警发起侦查方向调整，推进智能体 **shall** 读取当前全部任务状态，生成受影响任务清单及处理建议。
- **[Ubiquitous]** 已完成任务 **shall** 永久保留，不受方向调整影响。
- **[Event-driven]** **When** 主办民警确认方向调整，推进智能体 **shall** 基于新方向重新生成任务草案。
- **[Ubiquitous]** 方向变更事件 **shall** 写入案件时间线。

#### 6.7.6 事件驱动机制（后端，v1.5 按代码修正）

🔀 v1.4 描述为「`complete_task` 投递事件到 ARQ 队列 → `CaseAdvancementService.handle_task_completed()` 经 LangGraph 调用 LLM」。**代码实际实现不同**：

```
推进触发流程（进程内，非队列）：

民警在任务详情审核通过 (review_task)
       │
       ▼
PoliceTaskService.review_task()
       ├─ 校验审核人，写入 reviewed_by / reviewed_at / signed_hash（§9.5）
       ├─ 任务状态置为 completed
       ├─ 写入 TaskEvent (completed)
       ├─ 写入工作区产物（若有）
       └─ asyncio.create_task(
            self._trigger_advancement(case_id, task_id, reviewer_id))
              │
              ▼  (进程内异步，不经过 ARQ)
       PoliceAdvancementService.advance_after_task_completed()
              ├─ 读取该任务产出，提取涉案要素
              ├─ 匹配 police_task_templates 规则
              ├─ 调用 LLM（agnes-2.5-flash）生成任务草案
              ├─ 写入 police_advancement_logs（decision_type=task_draft）
              └─ 输出: 生成 pending_confirmation 任务草案 / 阶段小结 / 无操作
```

> **关键差异**：① 触发点是 `review_task`（审核通过），不是 `complete_task`；② 走 `asyncio.create_task` 进程内调用，**无 ARQ 队列**；③ 推进服务是**线性管线**，无 LangGraph 状态机。

#### 6.7.7 数据库变更（v1.5 按代码修正）

🔀 v1.4 规划的 `police_case_advancement_agents` 表，以及 `police_tasks` 的 `source_event_id` / `draft_reasoning` / `evidence_refs` 三字段**均未实现**（全库 0 命中）。实际落地如下：

**推进决策日志表 `police_advancement_logs`（已实现，详见 §5.2.8）** —— 替代原「每案件推进智能体实例表」：

```sql
CREATE TABLE police_advancement_logs (
    id              SERIAL PRIMARY KEY,
    case_id         INTEGER NOT NULL REFERENCES police_cases(id) ON DELETE CASCADE,
    trigger_task_id INTEGER REFERENCES police_tasks(id),
    decision_type   VARCHAR(30) NOT NULL,   -- task_draft / direction_change / phase_summary / no_action
    summary         TEXT,
    details         JSON DEFAULT '{}',      -- {source_task, direction, generated_tasks, reasoning, model, duration_ms}
    created_by      INTEGER REFERENCES users(id),
    created_at      TIMESTAMP DEFAULT NOW()
);
```

**police_tasks 溯源信息（已实现，存于 `extra.advancement` JSON，非独立字段）**：

```json
{
  "advancement": {
    "source_task_id":    123,
    "template_id":       7,
    "template_code":     "bank_card_to_flow_query",
    "element_type":      "bank_card",
    "element_value":     "6222***1234",
    "origin":            "template | llm | chain",
    "suggested_assignee":"fund_analyst",
    "direction_change":  false
  }
}
```

**police_cases 已落地字段（详见 §5.2.2）**：
- `investigation_direction` TEXT — 当前侦查方向描述 ✅ 已实现
- `advancement_enabled` INTEGER DEFAULT 1 — 是否启用推进智能体 ✅ 已实现

**任务状态枚举（已实现，与 §5.2.1 一致）**：
```python
TASK_STATUS = (
    "pending_confirmation",  # 推进智能体生成的任务草案，待主办民警审查
    "pending",
    "in_progress",
    "review",
    "completed",
    "suspended",
    "terminated",
    "cancelled",
    "blocked",
)
```

### 6.8 数字警员开发规范

每个数字警员遵循统一接口规范（即 Yuxi Agent 接口，扩展公安业务字段）：

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Any

class AgentInput(TypedDict):
    task_id: str
    case_id: str
    case_context: dict        # 案件上下文
    task_input: dict          # 任务特定输入
    attachments: list[dict]   # 附件列表

class AgentOutput(TypedDict):
    status: str               # success / failed / needs_review
    result: dict              # 结构化结果
    artifacts: list[dict]     # 产出文件 [{name, path, type}]
    next_tasks: list[dict]    # 建议创建的后续任务
    summary: str              # 人可读的摘要

class CaseAgent:
    """数字警员基类（= Yuxi Agent）"""
    name: str
    police_id: str            # 数字警员工号
    rank: str                 # 警衔
    skills: list              # 拥有的 Yuxi Skill 列表
    tools: list
    
    def build_graph(self) -> StateGraph:
        """构建 LangGraph 工作流"""
        graph = StateGraph(AgentInput)
        # ... 定义节点和边 ...
        return graph.compile()
    
    async def run(self, input: AgentInput) -> AgentOutput:
        """执行数字警员（专案协同模式）"""
        graph = self.build_graph()
        result = await graph.ainvoke(input)
        return self.format_output(result)
    
    async def chat(self, message: str, history: list) -> str:
        """直接对话模式：民警点对点调用技能"""
        ...
    
    def format_output(self, raw: dict) -> AgentOutput:
        """格式化输出"""
        ...
```

---

## 7. API 接口设计

### 7.1 API 规范

- 风格: RESTful
- 认证: JWT Bearer Token
- 格式: JSON
- 前缀: 公安业务接口统一为 `/api/police/<resource>`（由 `app.include_router(router, prefix="/api")` + 各 `police_*` 路由器的 `/police/...` 前缀组成）；鉴权/用户等底座接口属 yuxi 原生，前缀为 `/api/auth`、`/api/user` 等，**不存在 `/api/v1/`**
- 分页: `?page=1&page_size=20`
- 排序: `?sort=-created_at` (负号=降序)
- 筛选: `?status=pending&assignee_type=agent`

### 7.2 核心 API 列表

> 🔀 **v1.5 修订**：v1.4 本节所有路径写作 `/api/v1/...`，**与代码不符**。真实前缀为 `/api/police/<resource>`（见 §7.1）。下方路径均为代码真实存在的端点（✅ 已实现）；标注 📋 者为规划中、代码中尚无对应路由。

#### 7.2.1 认证（yuxi 底座，非 police 前缀）

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/refresh` | 刷新 Token |
| GET  | `/api/auth/me` | 获取当前用户信息 |

#### 7.2.2 案件管理 `/api/police/cases`

| Method | Path | 说明 |
|--------|------|------|
| GET  | `/api/police/cases` | 案件列表 (分页/筛选/排序) |
| POST | `/api/police/cases` | 创建案件 |
| GET  | `/api/police/cases/{case_id}` | 案件详情 |
| PUT  | `/api/police/cases/{case_id}` | 更新案件 |
| DELETE | `/api/police/cases/{case_id}` | 删除案件 |
| POST | `/api/police/cases/{case_id}/members` | 添加案件成员 |
| PUT  | `/api/police/cases/{case_id}/phase` | 切换案件阶段 |
| GET  | `/api/police/cases/{case_id}/timeline` | 案件时间线 |
| POST | `/api/police/import/transcript` | 上传笔录智能创建案件 |
| POST | `/api/police/import/transcript/confirm` | 确认创建案件 |

#### 7.2.3 任务管理 `/api/police/tasks`

| Method | Path | 说明 |
|--------|------|------|
| GET  | `/api/police/tasks` | 任务列表 (支持筛选) |
| GET  | `/api/police/tasks/my` | 我的任务 |
| GET  | `/api/police/tasks/review` | 待我审核的任务 |
| POST | `/api/police/tasks` | 创建任务 |
| GET  | `/api/police/tasks/{task_id}` | 任务详情 |
| PUT  | `/api/police/tasks/{task_id}` | 更新任务 |
| POST | `/api/police/tasks/{task_id}/assign` | 分配任务（多执行人见 §5.2.3）|
| POST | `/api/police/tasks/{task_id}/start` | 开始任务 |
| POST | `/api/police/tasks/{task_id}/complete` | 完成任务（民警）|
| POST | `/api/police/tasks/{task_id}/review` | 审核任务（通过→触发推进，见 §6.7.6）|
| GET  | `/api/police/tasks/{task_id}/events` | 任务事件日志 |
| GET  | `/api/police/tasks/flow-rules/list` | 任务流转规则列表 |
| POST | `/api/police/tasks/flow-rules` | 新建流转规则 |
| PUT  | `/api/police/tasks/flow-rules/{rule_id}` | 更新流转规则 |
| DELETE | `/api/police/tasks/flow-rules/{rule_id}` | 删除流转规则 |

#### 7.2.4 推进智能体 `/api/police/advancement`

| Method | Path | 说明 |
|--------|------|------|
| GET  | `/api/police/advancement/{case_id}/drafts` | 推进智能体生成的待确认任务草案 |
| POST | `/api/police/advancement/tasks/{task_id}/confirm` | 主办民警确认任务草案 |
| POST | `/api/police/advancement/tasks/{task_id}/reject` | 驳回任务草案 |
| POST | `/api/police/advancement/{case_id}/direction` | 侦查方向调整 |
| GET  | `/api/police/advancement/my-drafts` | 我收到的任务草案 |
| GET  | `/api/police/advancement/{case_id}/logs` | 推进决策日志 (police_advancement_logs) |
| POST | `/api/police/advancement/{case_id}/toggle` | 启用/停用推进智能体 |

#### 7.2.5 数字警员与 SOP `/api/police/agents`

| Method | Path | 说明 |
|--------|------|------|
| GET  | `/api/police/agents` | 数字警员列表 |
| GET  | `/api/police/agents/by-badge/{badge_number}` | 按工号查 (DA-xxx) |
| GET  | `/api/police/agents/by-yuxi/{yuxi_agent_id}` | 按 yuxi agent 查 |
| GET  | `/api/police/agents/templates` | 数字警员市场模板列表 |
| POST | `/api/police/agents/templates/{template_id}/install` | 从市场安装数字警员 |
| POST | `/api/police/agents/{agent_id}/share` | 共享/发布到市场 |
| POST | `/api/police/agents/{agent_id}/approve` | 共享审批（见 §4.11）|
| GET  | `/api/police/agents/{agent_id}` | 详情 |
| PUT  | `/api/police/agents/{agent_id}` | 更新配置 |
| DELETE | `/api/police/agents/{agent_id}` | 删除 |
| GET  | `/api/police/agents/{agent_id}/runs` | 运行记录 |
| GET  | `/api/police/agents/sops/list` | SOP 列表 |
| POST | `/api/police/agents/sops` | 新建 SOP |
| GET  | `/api/police/agents/sops/{sop_id}` | SOP 详情 |
| PUT  | `/api/police/agents/sops/{sop_id}` | 更新 SOP |
| DELETE | `/api/police/agents/sops/{sop_id}` | 删除 SOP |
| POST | `/api/police/agents/seed` | 植入预设数字警员/模板 |

#### 7.2.6 证据与文档 `/api/police/evidence`

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/police/evidence/case/{case_id}` | 上传证据材料 |
| GET  | `/api/police/evidence/case/{case_id}` | 证据列表 |
| GET  | `/api/police/evidence/{evidence_id}` | 证据详情 |
| POST | `/api/police/evidence/{evidence_id}/review` | 审核证据（计算 signed_hash，见 §9.5）|
| GET  | `/api/police/evidence/case/{case_id}/chain` | 证据链 |
| GET  | `/api/police/evidence/{evidence_id}/download` | 下载证据文件 |
| GET  | `/api/police/evidence/{evidence_id}/preview` | 在线预览 |
| 📋 POST | `/api/police/evidence/{evidence_id}/ocr` | 触发 OCR 识别（规划中，代码暂无路由）|

#### 7.2.7 案件工作区 `/api/police/workspaces`

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/police/workspaces/{case_id}/init` | 初始化案件工作区 |
| GET  | `/api/police/workspaces/{case_id}` | 工作区信息 |
| GET  | `/api/police/workspaces/{case_id}/nodes` | 文件树节点 |
| GET  | `/api/police/workspaces/{case_id}/folders` | 文件夹列表 |
| POST | `/api/police/workspaces/{case_id}/upload` | 上传文件到工作区 |
| GET  | `/api/police/workspaces/{case_id}/download` | 下载 |
| POST | `/api/police/workspaces/{case_id}/move` | 移动 |
| POST | `/api/police/workspaces/{case_id}/rename` | 重命名 |

#### 7.2.8 侦查任务模板 `/api/police/task-templates`

| Method | Path | 说明 |
|--------|------|------|
| GET  | `/api/police/task-templates/meta` | 元数据（枚举等）|
| POST | `/api/police/task-templates/seed` | 植入内置模板 |
| GET  | `/api/police/task-templates` | 模板列表 |
| POST | `/api/police/task-templates` | 新建模板 |
| GET  | `/api/police/task-templates/{template_id}` | 模板详情 |
| PUT  | `/api/police/task-templates/{template_id}` | 更新模板 |
| DELETE | `/api/police/task-templates/{template_id}` | 删除模板 |
| POST | `/api/police/task-templates/{template_id}/toggle` | 启用/停用 |
| GET  | `/api/police/task-templates/{template_id}/preview` | 预览 |

> **权限**：配置类接口（`POST` 新建、`/seed` 植入、`PUT` 更新、`DELETE` 删除、`POST /toggle` 启用停用）仅超级管理员（`role=superadmin`）可调用，普通民警返回 `403`；`GET` 列表/详情/元数据/预览为只读，登录即可访问。

#### 7.2.9 工作台 `/api/police/dashboard`

| Method | Path | 说明 |
|--------|------|------|
| GET  | `/api/police/dashboard/stats` | 工作台统计数据 |
| GET  | `/api/police/dashboard/my-tasks` | 我的待办任务 |
| GET  | `/api/police/dashboard/review-tasks` | 待审核任务 |

#### 7.2.10 知识库与图谱 📋 规划中

> Neo4j / Milvus 在所有 `police_*` 代码中**均无调用**，知识图谱与图谱检索接口目前**不存在**。v1.4 列出的 `/api/v1/cases/{id}/graph/*` 与 `/knowledge/search` 端点代码暂无对应路由，保留为 §4.4 设计目标。
### 7.3 API 响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": "uuid...",
    "title": "..."
  },
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total": 100
  }
}
```

错误响应：
```json
{
  "code": 40001,
  "message": "案件不存在",
  "details": {
    "case_id": "uuid..."
  }
}
```

---

## 8. 前端 UI 设计规范

### 8.1 设计风格

**关键词**: 数字员工广场、手绘温度、卡片化看板、清晰专业

**v1.4 UI 参考体系**：
- **产品形态 + 数字员工交互语言** → **StaffDeck**（数字员工广场 / 员工档案 / SOP / 工作记录）
- **看板视图 + 任务卡片设计** → **Multica**（多列看板 / 卡片式任务 / 优先级标签 / Agent 队友视觉区分）
- **任务/看板协作布局交互** → **Plane**（看板拖拽、列表筛选、Command-K 搜索）

> **技术栈统一**：前端全面采用 **Vue 3 + Vite + Pinia + Ant Design Vue 4**（语析技术栈），仅参考上述项目的 UI 布局和交互逻辑，不迁移任何代码。

### 8.2 色彩系统

| 色彩 | 色值 | 用途 |
|------|------|------|
| 主色 | #1A365D (深藏青) | 导航栏、标题、主按钮 |
| 辅助色 | #2B6CB0 (警蓝) | 链接、强调 |
| 成功 | #38A169 (绿) | 完成、通过 |
| 警告 | #D69E2E (橙) | 待处理、提醒 |
| 危险 | #E53E3E (红) | 驳回、错误、紧急 |
| 信息 | #3182CE (蓝) | 进行中、提示 |
| 背景色 | #F7FAFC (浅灰白) | 页面背景 |
| 卡片色 | #FFFFFF (白) | 卡片背景 |
| 文字主色 | #1A202C | 正文 |
| 文字次色 | #718096 | 辅助文字 |
| 边框色 | #E2E8F0 | 分割线、边框 |

### 8.3 页面结构

```
┌─────────────────────────────────────────────────────┐
│  顶部导航栏 (Logo + 全局搜索 + 用户菜单)             │
├───────┬─────────────────────────────────────────────┤
│       │                                             │
│ 侧    │                                             │
│ 边    │              主内容区                        │
│ 导    │                                             │
│ 航    │                                             │
│ 栏    │                                             │
│       │                                             │
├───────┴─────────────────────────────────────────────┤
│  (可选) 底部状态栏                                    │
└─────────────────────────────────────────────────────┘
```

侧边导航菜单：
- 个人工作台 (My Workspace) ★ 民警个人待办中枢
  - 待审查（推进智能体任务草案）
  - 待审核（智能体产出）
  - 待处理（已分配给我的任务）
  - 通知（系统动态）
- 我的任务 (My Tasks) ★ 我领取/负责的所有任务
- 数字警员广场 (Officers) ★ 一级入口
  - 全部数字警员
  - 我的数字警员（已激活/常用）
  - 数字警员档案
- SOP 管理 (SOPs) ★ 一级入口
  - 本地 SOP 列表
  - 版本与调用统计
- 案件管理 (Cases)
  - 全部案件（专案组）
  - 我参与的
  - 按阶段筛选
- 全部任务 (All Tasks) — 看板视图
- 知识库 (Knowledge)
  - 案件知识库
  - 知识图谱
  - 法律知识库
- 统计分析 (Analytics)
- 系统管理 (Admin) [仅管理员]

### 8.4 核心页面设计

#### 8.4.1 个人工作台（民警待办中枢）

> **v1.4 重定位**：不再使用独立的"统一收件箱"。民警的个人工作台即待办中枢，聚合「待审查/待审核/待处理/通知」四类待办分组。

```
┌─────────────────────────────────────────────────────────────┐
│  个人工作台 — 张警官                                         │
│  早班好 | 2026-08-03 周一                                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ 待审查   │ │ 待审核   │ │ 待处理   │ │ 未读通知 │           │
│  │   3     │ │   2     │ │   8     │ │   5     │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ▼ 待审查 — 推进智能体任务草案 (3)                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 🤖 建议新增 | 调取银行卡 6222****1234 交易流水        │    │
│  │ 依据: 笔录分析报告 §三 — 嫌疑人供述该卡用于收款         │    │
│  │ 优先级: 🔴 紧急   建议执行: 🤖 DA-002 资金追踪师       │    │
│  │ 案件: 张某电信诈骗案 | 2 分钟前                [审查] │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 🤖 建议新增 | 调取手机号 138****8888 通话记录          │    │
│  │ ...                                             [审查]│    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ▼ 待审核 — 智能体产出 (2)                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 🤖 DA-002 | 资金分析初报                              │    │
│  │ 关联任务: T-0005 资金分析 | 案件: 张某电信诈骗案        │    │
│  │ 10 分钟前                                      [审核]│    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ▼ 待处理 — 分配给我的任务 (8)                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ⚠ 传唤关系人 张三                    🔴 紧急          │    │
│  │ 案件: 张某电信诈骗案 | 截止: 2026-08-04         [处理]│    │
│  └─────────────────────────────────────────────────────┘    │
│  ...更多待处理任务                                            │
│                                                             │
│  ▼ 通知 — 系统动态 (5)                                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 任务 T-0003 审核通过，案件可进入下一阶段                │    │
│  │ 系统通知 | 30 分钟前                                  │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 推进智能体建议: 当前阶段 5 个任务全部完成，建议进入     │    │
│  │ 下一阶段「收网」                                      │    │
│  │ 系统通知 | 1 小时前                                   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**分组规则**：

| 分组 | 内容 | 数据来源 |
|---|---|---|
| 待审查 | 推进智能体生成的任务草案（`pending_confirmation`） | 当前民警为主办民警的案件的待确认任务 |
| 待审核 | 执行智能体产出待审核（`review` 状态中 assigned 给当前民警的） | 任务表中的 review 状态任务 |
| 待处理 | 分配给当前民警且未完成的任务 | 任务表中 assigned_to 当前民警的非完成任务 |
| 通知 | 系统通知（阶段推进建议、方向调整提醒、任务状态变更等） | Notification 表 |

**个人工作台设计原则**：
- 以"我"为中心，而非"系统功能"为中心
- 待审查和待审核是民警必须关注的核心 AI 协作入口
- 红点计数由 WebSocket 实时推送 + API 拉取同步
- 分组可折叠，默认全部展开

#### 8.4.2 案件列表

```
┌─────────────────────────────────────────────────────┐
│  案件管理                    [+ 创建案件] [导入笔录] │
├─────────────────────────────────────────────────────┤
│  [全部] [研判中] [抓捕阶段] [办理中] [待移送] [已结案]│
│  搜索: [___________]  筛选: [类型▼] [负责人▼]       │
├─────────────────────────────────────────────────────┤
│  案件编号    │ 案件名称      │ 类型  │ 阶段   │ 负责人│
│  A2026-001  │ 张某电信诈骗案 │ 诈骗  │ 研判中 │ 张警官│
│  A2026-002  │ 李某盗窃案     │ 盗窃  │ 办理中 │ 王警官│
│  A2026-003  │ 跨省贩毒案     │ 毒品  │ 抓捕中 │ 李警官│
│  ...                                                  │
└─────────────────────────────────────────────────────┘
```

#### 8.4.3 案件详情

```
┌─────────────────────────────────────────────────────┐
│  ← 返回    A2026-001 张某电信诈骗案                  │
│  [概览] [任务] [证据] [知识图谱] [文书] [动态] [成员]│
├─────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌────────────────────────────┐  │
│  │ 案件信息      │  │ 任务看板                     │  │
│  │ 编号: A2026..│  │ ┌──────┬──────┬──────┬────┐│  │
│  │ 类型: 诈骗    │  │ │待处理 │进行中 │待审核 │完成 ││  │
│  │ 阶段: 研判中  │  │ ├──────┼──────┼──────┼────┤│  │
│  │ 金额: ¥50万   │  │ │调取流 │资金分 │审核报 │笔录 ││  │
│  │ 受害人: 张某  │  │ │水(人) │析(机) │告(人) │分析 ││  │
│  │ 创建: 07-28   │  │ │微信查 │      │      │(完成)│  │
│  │ 负责人: 张警官│  │ │询(人) │      │      │     │  │
│  └──────────────┘  │ └──────┴──────┴──────┴────┘│  │
│                     └────────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐  │
│  │ 案件知识图谱 (缩略)                            │  │
│  │   [人]──转账──→[账户]──转账──→[账户]          │  │
│  │    │            │                             │  │
│  │   通话         归属                            │  │
│  │    ↓            ↓                             │  │
│  │   [人]        [人]                             │  │
│  │                          [查看完整图谱 →]     │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

#### 8.4.4 工作项详情

```
┌─────────────────────────────────────────────────────┐
│  ← 返回    资金追踪 - 工行账户流水分析               │
│                                                       │
│  状态: [进行中]  优先级: [高]  分配给: [资金追踪师] │
│  创建者: 案件编排官      创建时间: 2026-07-30 10:00│
├─────────────────────────────────────────────────────┤
│  工作项描述                                           │
│  请分析以下工行账户的银行流水，追踪涉案资金流向：      │
│  账户: 6222****1234, 户名: 王某                      │
│  分析重点:                                            │
│  1. 资金转入来源                                      │
│  2. 资金转出去向                                      │
│  3. 异常交易模式                                      │
│                                                       │
│  附件: [工行流水_202607.xlsx] [受害人笔录摘要.pdf]   │
├─────────────────────────────────────────────────────┤
│  数字警员运行状态                                     │
│  ┌─────────────────────────────────────────────┐    │
│  │ 资金追踪师 正在运行...                        │    │
│  │ ████████████████░░░░ 75%                     │    │
│  │ [实时日志输出区域]                            │    │
│  │ > 正在解析流水文件...                          │    │
│  │ > 识别到 156 条交易记录                        │    │
│  │ > 追踪资金流向...                              │    │
│  │ > 发现 3 个可疑转入账户                        │    │
│  └─────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────┤
│  审核操作 (工作项完成后显示)                          │
│  [✓ 审核通过]  [✗ 驳回重做]  [查看完整报告]          │
└─────────────────────────────────────────────────────┘
```

#### 8.4.5 知识图谱可视化

```
┌─────────────────────────────────────────────────────┐
│  案件知识图谱 - 张某电信诈骗案                        │
├──────────┬──────────────────────────────────────────┤
│ 实体筛选  │                                          │
│ ☑ 人员    │        [受害人张某]                      │
│ ☑ 账户    │            │                            │
│ ☑ 通讯    │          转账                            │
│ ☐ 地址    │            ↓                            │
│ ☐ 组织    │     [账户A 工行****1234]                 │
│           │       │            │                    │
│ 关系筛选  │     转账          转账                    │
│ ☑ 转账    │       ↓            ↓                    │
│ ☑ 通话    │  [账户B 农行]   [账户C 建行]              │
│ ☑ 亲属    │       │                                 │
│ ☐ 同伙    │     归属                                 │
│           │       ↓                                 │
│ 查询:     │   [嫌疑人王某]──通话──[嫌疑人李某]       │
│ [______]  │                                          │
│ [最短路径]│     (可拖拽/缩放/点击节点查看详情)        │
└──────────┴──────────────────────────────────────────┘

#### 8.4.6 数字警员（统一智能体管理页，🔀 已按代码修正）

> v1.4 规划的独立「一级入口：数字警员广场 `/police/officers`」**代码未采用**。真实路由中 `/police/officers` 与 `/police/officers/:id` 均为**重定向**，实际承载数字警员画廊/档案/技能/成长的是 yuxi 原生「智能体管理」页（`/agent-manage`）。前端 `web/src/router/index.js` 中 `officers` 路由 `redirect → /agent-manage`。

数字警员画廊与档案（统一在 `/agent-manage` 呈现，StaffDeck 风格）：

```
┌─────────────────────────────────────────────────────┐
│  智能体管理 (/agent-manage)            [搜索] [筛选▼] │
├──────┬──────┬──────┬──────┬──────┬──────────────────┤
│ 🧑 笔录│ 🕵 资金│ ⚖ 法制│ 📝 调证│ 🗂 编排│  ...(DA-006/007)│
│ 分析师│ 追踪师│ 审核官│ 生成师│ 官    │                 │
│ 在线  │ 忙碌  │ 在线  │ 在线  │ 在线  │                 │
│ 本月12│ 本月8 │ 本月5 │ 本月6 │ 本月3 │                 │
│ 次工作│ 次工作│ 次工作│ 次工作│ 次工作│                 │
└──────┴──────┴──────┴──────┴──────┴──────────────────┘
  [点击卡片 → 进入数字警员档案]
```

> 注：§8.4.7「数字警员档案」的卡片字段（`工号 PO-001`、`好评率/差评率`）中，「好评率/差评率」依赖 `officer_feedback` 表，**该表未实现**（见 §5.2.4 / §5.2.6），目前无数据支撑；工号字段实际为 `badge_number`（如 `DA-001`），非 `PO-001`。

#### 8.4.7 数字警员档案

```
┌─────────────────────────────────────────────────────┐
│  ← 返回   笔录分析师                                  │
│  [头像]  工号: PO-001  警衔: 一级警司  部门: 刑侦     │
├──────────┬──────────────────────────────────────────┤
│ 能力矩阵 │ 技能列表                                  │
│ 笔录提取 │ • 笔录分析 (本月调用 12)                  │
│ 信息抽取 │ • 案件初查摘要 (本月调用 8)               │
│ 任务规划 │ • 初始工作项生成 (本月调用 12)            │
├──────────┼──────────────────────────────────────────┤
│ 工作记录 │ 成长轨迹                                  │
│ 日历视图 │ 好评率 95%  差评率 2%                    │
│ (每日产出)│ 使用频次趋势图                           │
├──────────┼──────────────────────────────────────────┤
│ 对话日志 │ 最近与民警的对话 / 任务执行记录           │
└──────────┴──────────────────────────────────────────┘
  [发起对话]  [编入专案组]
```

#### 8.4.8 SOP 管理

```
┌─────────────────────────────────────────────────────┐
│  SOP 管理                              [+ 新建 SOP]   │
├──────────────────────────────────────────────────────┤
│  名称          业务域   版本  状态   调用  好评率     │
│  电诈案初查     fraud    v3   active  156   94%      │
│  盗窃案办理     theft    v1   active   42   91%      │
│  ...                                                  │
├──────────────────────────────────────────────────────┤
│  选中 SOP 详情：                                      │
│  步骤1 笔录分析 → 步骤2 资金初查 → 步骤3 生成调取文书 │
│  → 步骤4 提示需补正文书 → 步骤5 法制审核             │
│  分支/异常: 若资金链路不完整 → 回退步骤2             │
└──────────────────────────────────────────────────────┘
```

#### 8.4.9 专案组工作台（案件详情升级）

案件详情页强化「专案组」视图——左侧展示参与本案的民警与数字警员，右侧为工作项流（原 8.4.3 案件详情的「成员」标签升级为「专案组」）：

```
┌─────────────────────────────────────────────────────┐
│  ← 返回   A2026-001 张某电信诈骗案   [专案组 5人]    │
├──────────────────────────┬──────────────────────────┤
│  专案组成员               │  工作项看板              │
│  👮 张警官(主办)          │ ┌────┬────┬────┬────┐   │
│  👮 王警官(参办)          │ │待处│进行│待审│完成│   │
│  🧑 笔录分析师            │ ├────┼────┼────┼────┤   │
│  🕵 资金追踪师(忙碌)      │ │调流│资金│审报│笔录│   │
│  ⚖ 法制审核官            │ │水(人│分析│告(人│分析│   │
│                          │ │微信│(机)│(人)│(完)│   │
│  [+ 编入数字警员]         │ │查询│    │    │    │   │
│                          │ │(人) │    │    │    │   │
├──────────────────────────┤ └────┴────┴────┴────┘   │
│  SOP 执行轨迹             │                           │
│  电诈案初查 v3: 步骤2/5  │                           │
└──────────────────────────┴──────────────────────────┘
```
```

#### 8.4.10 多列看板视图（参考 Multica）

> **v1.4 新增**：参考 Multica 的卡片式看板设计，提升任务管理的视觉密度和信息层级。在 8.4.3 中原有简易看板基础上升级。

**整体布局**：多列独立滚动看板，每列顶部显示列名 + 任务计数，列间用细边框分隔。

```
┌──────────────────────────────────────────────────────────────────────┐
│ [案件: 张某诈骗案 (A2026-001)]         [搜索任务]  [筛选▼]  [+ 新建] │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────┤
│ 待确认    │ 待开始    │ 进行中    │ 审核中    │ 已完成    │ 已取消        │
│  (3)     │  (5)     │  (3)     │  (2)     │  (7)     │  (1)         │
│          │          │          │          │          │              │
│ ┌──────┐ │ ┌──────┐ │ ┌──────┐ │ ┌──────┐ │ ┌──────┐ │              │
│ │T-0012│ │ │T-0008│ │ │T-0005│ │ │T-0003│ │ │T-0001│ │              │
│ │调取银 │ │ │传唤关 │ │ │资金分 │ │ │笔录分 │ │ │立案审 │ │              │
│ │行卡流 │ │ │系人张 │ │ │析    │ │ │析报告 │ │ │批    │ │              │
│ │水    │ │ │三    │ │ │      │ │ │审核  │ │ │      │ │              │
│ │🔴紧急 │ │ │🟡中  │ │ │🔴紧急 │ │ │🟢普通 │ │ │      │ │              │
│ │👤李警 │ │ │👤王警 │ │ │🤖DA-0│ │ │👤张警 │ │ │      │ │              │
│ └──────┘ │ └──────┘ │ └──────┘ │ └──────┘ │ └──────┘ │              │
│          │          │          │          │          │              │
│ ┌──────┐ │          │          │          │          │              │
│ │🤖蓝边│ │          │          │          │          │              │
│ │T-0010│ │          │          │          │          │              │
│ │调取微 │ │          │          │          │          │              │
│ │信流水 │ │          │          │          │          │              │
│ │依据:笔│ │          │          │          │          │              │
│ │录分析 │ │          │          │          │          │              │
│ │🟡中  │ │          │          │          │          │              │
│ │🤖DA-0│ │          │          │          │          │              │
│ └──────┘ │          │          │          │          │              │
│          │          │          │          │          │              │
│[+ 添加]  │ [+ 添加] │ [+ 添加] │          │          │              │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────────────┘
```

**列定义与状态映射**：

| 列名 | 对应状态 | 说明 |
|---|---|---|
| 待确认 | `pending_confirmation` | 推进智能体生成的任务草案（🤖 标记 + 蓝边） |
| 待开始 | `pending` | 已确认，等待民警领取 |
| 进行中 | `in_progress` | 执行中 |
| 审核中 | `review` | 已提交结果，等待审核 |
| 已完成 | `completed` | 审核通过 |
| 已暂停 | `suspended` | 手动暂停 |
| 已取消 | `cancelled` / `terminated` | 驳回/方向调整取消 |

**任务卡片设计规范**（`<TaskCard>` 可复用组件）：

| 卡片区域 | 内容 | 样式 |
|---|---|---|
| 顶部 | 任务编号（如 `T-0012`）| 灰色小字，等宽字体 |
| 标题行 | 任务标题 | 14px 加粗，深色文字 |
| 描述区 | 任务描述摘要（1-2 行截断）| 12px 灰色文字 |
| 依据区 | 建议依据引用（仅推进智能体生成的任务）| 12px 浅蓝色文字，左侧竖线标记 |
| 标签区 | 优先级 + 任务类型标签 | 圆角彩色标签 |
| 底部 | 负责人头像 + 名称（或智能体图标 + 名称）| 12px |

**优先级标签色标**：

| 优先级 | 边框色 | 背景色 | 说明 |
|---|---|---|---|
| Urgent 紧急 | `#DC2626` | `#FEE2E2` | 需立即处理 |
| High 高 | `#EA580C` | `#FFF7ED` | 优先处理 |
| Medium 中 | `#CA8A04` | `#FEF9C3` | 正常排期 |
| Low 低 | `#16A34A` | `#F0FDF4` | 可延后 |

**卡片视觉区分——人类 vs 智能体**：

| 区分维度 | 人类创建的任务 | 推进智能体生成的任务 |
|---|---|---|
| 来源标记 | 无特殊标记 | 卡片左上角 🤖 图标 + "建议" 标签 |
| 依据引用 | 无 | 标题下方显示依据来源（如"依据: 笔录分析报告 §三"） |
| 左侧色条 | 无 | 蓝色细竖线（`border-left: 3px solid #1A5FEB`） |
| 底部负责人 | 民警头像 + 姓名 | Agent 图标 + 名称 |

**交互行为**：
- 支持拖拽卡片改变任务状态（仅在合法状态转换范围内）
- 点击卡片展开任务详情侧面板（不跳转页面）
- 列顶 [+ 添加] 按钮手动创建任务
- 看板支持快捷键（n 新建任务、/ 搜索、←→ 切换列）

---

## 9. 安全与合规设计

### 9.1 数据安全

| 安全措施 | 说明 |
|----------|------|
| **传输加密** | 全站 HTTPS (TLS 1.3) |
| **存储加密** | 敏感字段数据库加密 (AES-256) |
| **文件加密** | MinIO 服务端加密 |
| **密码安全** | bcrypt 哈希 + 盐值 |
| **JWT 安全** | 短期 Access Token (30min) + 长期 Refresh Token (7天) |
| **PII 脱敏** | 身份证号、手机号、银行卡号在展示时自动脱敏 |
| **数据隔离** | 案件级数据隔离，非案件成员无法访问 |
| **文件完整性** | 所有上传文件计算 SHA-256 哈希 |
| **数据库备份** | 每日自动备份，保留 30 天 |

### 9.2 权限体系

```
角色层级:
├── 系统管理员 (admin)
│   └── 用户管理、系统配置、智能体管理
├── 案件指挥员 (chief)
│   └── 创建案件、分配任务、审核结果、阶段管理
├── 办案民警 (officer)
│   └── 接受任务、执行任务、上传证据、提交结果
└── 法制审核员 (legal)
    └── 法制审核、程序监督

权限矩阵:
┌──────────┬────────┬────────┬────────┬────────┐
│  操作     │ admin  │ chief  │ officer│ legal  │
├──────────┼────────┼────────┼────────┼────────┤
│ 用户管理  │   ✓    │        │        │        │
│ 系统配置  │   ✓    │        │        │        │
│ 创建案件  │   ✓    │   ✓    │        │        │
│ 分配任务  │   ✓    │   ✓    │        │        │
│ 执行任务  │   ✓    │   ✓    │   ✓    │        │
│ 审核结果  │   ✓    │   ✓    │        │   ✓    │
│ 法制审核  │   ✓    │        │        │   ✓    │
│ 阶段管理  │   ✓    │   ✓    │        │        │
│ 查看案件  │   ✓    │   ✓    │ (参与的)│ (参与的)│
└──────────┴────────┴────────┴────────┴────────┘
```

### 9.3 智能体安全

| 安全措施 | 说明 |
|----------|------|
| **工具白名单** | 智能体只能调用预注册的工具，Shell 命令需白名单 |
| **操作审批** | 智能体的关键操作（创建任务、生成文书）需人工审核 |
| **沙盒执行** | 智能体在沙盒环境中运行，文件系统隔离 |
| **输出过滤** | 智能体输出经过 PII 脱敏后才展示 |
| **用量限制** | 每个智能体的 Token 用量和调用频率限制 |
| **运行日志** | 完整记录智能体的每次运行输入/输出/工具调用 |

### 9.4 审计合规

- **全操作审计**：所有用户操作和智能体操作记录审计日志
- **不可篡改**：审计日志追加写入，不支持修改删除
- **操作溯源**：每条任务结果可追溯到创建者（人或智能体）和审核者
- **导出归档**：支持按案件导出完整操作记录，用于归档和监督

### 9.5 证据链哈希与防篡改签名（诉讼合规关键）

> **背景**：公安卷宗具有极高的法律严肃性。AI 智能体生成的文书或分析结果，如果在审核后被恶意篡改，将直接导致证据被排除，甚至案件被发回重审。辩护律师可能质疑"AI 生成材料是否被篡改过"。因此必须建立**可验证的证据完整性链**。

#### 9.5.1 双重哈希机制

| 哈希字段 | 计算时机 | 计算内容 | 存储位置 | 用途 |
|----------|----------|----------|----------|------|
| `file_hash` (SHA-256) | 文件上传/生成时 | 文件二进制内容 | evidence.file_hash | 证明文件本身未被篡改 |
| `signed_hash` (SHA-256) | 民警审核确认时 | `SHA-256(reviewer_police_id + 审核时间戳ISO + 内容哈希)`，三者直接拼接无分隔符（证据=file_hash，任务=result_hash） | evidence.signed_hash / tasks.signed_hash | 证明"该民警（警号）在该时间确认了该文件/成果" |

#### 9.5.2 签名流程

```
智能体生成文书/分析结果
    │
    ▼
文件上传至 MinIO → 计算 file_hash (SHA-256) → 落库 evidence.file_hash
    │
    ▼
民警在工作台审核证据 → 点击"审核通过"
    │
    ▼
系统自动计算:
  hash_input = f"{reviewer_police_id}{reviewed_at.isoformat()}{file_hash}"
  signed_hash = SHA-256(hash_input)   # 注意：用警号(reviewer_police_id)，非 users.id
    │
    ▼
落库 (evidence_repository.review):
  evidence.reviewed_by   = reviewer_id       # users.id（冗余展示用）
  evidence.reviewed_at   = reviewed_at
  evidence.signed_hash   = signed_hash
    │
    ▼
审计日志记录: "民警XXX于YYYY-MM-DD HH:MM:SS 审核确认文件YYY (hash:zzz)"
```

> ⚠️ **只签名、不验证**：代码中只有"写入 signed_hash"的 `evidence_repository.review()` 与 `police_service.review_task()`，**没有**对应的"读取并校验 signed_hash"的验证函数（§9.5.3 的 `verify_evidence_integrity` 当前仅存在于本文档，代码未实现）。这是 §0.2 列明的技术债——诉讼阶段/监督检查时无法在系统内自证完整性与签名真实性，需补一个验证端点。


#### 9.5.3 验证流程（📋 规划中 — 代码未实现，见 §0.2 技术债）

```python
# ⚠️ 以下为"规划中"的验证函数（v1.5 标注）：代码目前只有写入 signed_hash 的
#    evidence_repository.review() 与 police_service.review_task()，但没有读取并校验的
#    等价实现。下方伪代码仅作为未来验证端点的设计参考，且已按代码修正为使用
#    reviewer_police_id（警号），而非 reviewed_by（users.id）。
def verify_evidence_integrity(evidence_record, reviewer_police_id, original_file_bytes):
    """验证证据完整性（规划中，代码未实现）"""
    # 1. 验证文件哈希（文件未被篡改）
    current_hash = hashlib.sha256(original_file_bytes).hexdigest()
    if current_hash != evidence_record.file_hash:
        return False, "文件已被篡改: file_hash 不匹配"

    # 2. 验证签名哈希（审核记录未被伪造）
    #    注意：签名时用的是 reviewer_police_id（警号），不是 reviewed_by（users.id）
    expected_signed = hashlib.sha256(
        f"{reviewer_police_id}"
        f"{evidence_record.reviewed_at.isoformat()}"
        f"{evidence_record.file_hash}".encode()
    ).hexdigest()
    if expected_signed != evidence_record.signed_hash:
        return False, "审核签名不匹配: signed_hash 验证失败"

    return True, "证据完整性验证通过"
```

#### 9.5.4 适用范围

| 场景 | 是否需要签名 | 说明 |
|------|-------------|------|
| 智能体生成的调取通知书 | ✅ 必须 | 民警审核后签名，证明文书经人工确认 |
| 智能体生成的资金分析报告 | ✅ 必须 | 民警审核后签名，证明分析结论经人工确认 |
| 智能体生成的法制审核意见 | ✅ 必须 | 法制民警审核后签名 |
| 民警手动上传的银行流水 | ⚠️ 可选 | 原始证据，file_hash 即可，但建议民警上传时即签名 |
| 民警手动上传的笔录扫描件 | ⚠️ 可选 | 原始证据，file_hash 即可 |
| 智能体产出的所有任务结果 | ✅ 必须 | tasks.signed_hash 记录审核民警确认 |

> **设计原则**：所有 AI 智能体产出的材料，必须经民警审核确认并生成 `signed_hash` 后，才能进入正式卷宗。未经签名的智能体产出仅标记为"草稿"状态，不具法律效力。

---

## 10. 部署方案

### 10.1 部署架构

```
┌───────────────────────────────────────────────┐
│                 负载均衡 (Nginx)                │
│            SSL 终止 + 静态资源                  │
├───────────────┬───────────────────────────────┤
│   前端服务     │        后端 API 服务            │
│  (Vue 静态)   │    (FastAPI + Uvicorn)         │
│               │    ┌──────────────────┐       │
│               │    │  ARQ Worker x N   │       │
│               │    └──────────────────┘       │
├───────────────┴───────────────────────────────┤
│                  基础设施层                     │
│  ┌────────┐ ┌───────┐ ┌───────┐ ┌──────┐     │
│  │Postgre │ │ Redis │ │MinIO  │ │Milvus│     │
│  │  SQL   │ │       │ │       │ │      │     │
│  └────────┘ └───────┘ └───────┘ └──────┘     │
│  ┌────────┐                                   │
│  │ Neo4j  │                                   │
│  └────────┘                                   │
└───────────────────────────────────────────────┘
```

### 10.2 Docker Compose 部署

```yaml
# docker-compose.yml (核心服务)
version: '3.8'

services:
  # 前端
  web:
    build: ./web
    ports:
      - "80:80"
    depends_on:
      - api

  # 后端 API
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://police:password@postgres:5432/police
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - MILVUS_HOST=milvus
      - NEO4J_URI=bolt://neo4j:7687
    depends_on:
      - postgres
      - redis
      - minio
      - milvus
      - neo4j

  # ARQ Worker (智能体异步执行)
  worker:
    build: ./backend
    command: arq worker.WorkerSettings
    environment:
      - DATABASE_URL=postgresql://police:password@postgres:5432/police
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
      - MILVUS_HOST=milvus
      - NEO4J_URI=bolt://neo4j:7687
    depends_on:
      - redis
      - postgres
    deploy:
      replicas: 3  # 多副本并行处理

  # PostgreSQL
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: police
      POSTGRES_USER: police
      POSTGRES_PASSWORD: password
    volumes:
      - pg_data:/var/lib/postgresql/data

  # Redis
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  # MinIO
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data

  # Milvus
  milvus:
    image: milvusdb/milvus:latest
    ports:
      - "19530:19530"
    volumes:
      - milvus_data:/var/lib/milvus

  # Neo4j
  neo4j:
    image: neo4j:5
    environment:
      NEO4J_AUTH: neo4j/password
    volumes:
      - neo4j_data:/data

volumes:
  pg_data:
  redis_data:
  minio_data:
  milvus_data:
  neo4j_data:
```

### 10.3 环境配置

```env
# .env
# 数据库
DATABASE_URL=postgresql://police:password@localhost:5432/police
REDIS_URL=redis://localhost:6379/0

# 对象存储
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=police-evidence

# 向量数据库
MILVUS_HOST=localhost
MILVUS_PORT=19530

# 图数据库
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# 大模型
LLM_PROVIDER=openai  # openai / dashscope / deepseek / vllm / ollama
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-max

# Embedding 模型
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_API_KEY=sk-xxx

# 安全
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=7

# 应用
APP_NAME=智案协
APP_ENV=production
APP_PORT=8000
CORS_ORIGINS=https://police.example.gov.cn
```

#### 10.3.1 私有化离线部署模型配置（公安内网必需）

> **⚠️ 公安网环境约束**
>
> 公安网通常处于极高密级的内网/局域网，**无法访问外网 API**（如 OpenAI / Dashscope / DeepSeek API）。必须部署本地私有化大模型。以下配置适用于完全离线的公安内网环境。

**方案 A：vLLM 部署（推荐，高性能推理）**

vLLM 提供 OpenAI 兼容 API，语析和本平台无需修改代码即可对接。

```env
# .env (vLLM 私有化部署)
LLM_PROVIDER=openai  # vLLM 兼容 OpenAI 接口，provider 填 openai
LLM_API_KEY=EMPTY    # vLLM 默认不校验，填 EMPTY 即可
LLM_BASE_URL=http://192.168.1.100:8000/v1  # vLLM 服务地址
LLM_MODEL=Qwen2.5-72B-Instruct  # 本地加载的模型名

# Embedding (vLLM 也可托管 Embedding 模型)
EMBEDDING_MODEL=bge-large-zh-v1.5
EMBEDDING_API_KEY=EMPTY
EMBEDDING_BASE_URL=http://192.168.1.100:8001/v1
```

```bash
# vLLM 启动命令 (对话模型)
python -m vllm.entrypoints.openai.api_server \
  --model Qwen2.5-72B-Instruct \
  --served-model-name Qwen2.5-72B-Instruct \
  --tensor-parallel-size 2 \    # 双 GPU 并行
  --gpu-memory-utilization 0.9 \
  --max-model-len 32768 \
  --port 8000

# vLLM 启动命令 (Embedding 模型)
python -m vllm.entrypoints.openai.api_server \
  --model BAAI/bge-large-zh-v1.5 \
  --port 8001
```

**方案 B：Ollama 部署（轻量级，适合小规模/开发环境）**

```env
# .env (Ollama 私有化部署)
LLM_PROVIDER=ollama
LLM_API_KEY=EMPTY
LLM_BASE_URL=http://192.168.1.100:11434/v1  # Ollama OpenAI 兼容端点
LLM_MODEL=deepseek-r1:70b  # 或 qwen2.5:72b

EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_API_KEY=EMPTY
EMBEDDING_BASE_URL=http://192.168.1.100:11434/v1
```

```bash
# Ollama 拉取模型 (需在有网环境预先拉取，再离线迁移)
ollama pull deepseek-r1:70b
ollama pull qwen2.5:72b
ollama pull nomic-embed-text

# 离线迁移: 将 ~/.ollama/models 打包拷贝到公安网服务器
```

**推荐模型选型（按场景）**

| 场景 | 推荐模型 | 参数量 | 显存需求 | 说明 |
|------|----------|--------|----------|------|
| 主力对话/推理 | Qwen2.5-72B-Instruct | 72B | 2×A100 80G 或 4×RTX 4090 | 中文能力强，工具调用稳定 |
| 深度推理/资金分析 | DeepSeek-R1-Distill-70B | 70B | 2×A100 80G | 推理能力强，适合复杂分析 |
| 轻量对话/开发调试 | Qwen2.5-14B-Instruct | 14B | 1×RTX 4090 24G | 开发期快速迭代 |
| Embedding | BAAI/bge-large-zh-v1.5 | 326M | 1×RTX 3060 | 中文向量检索效果好 |
| OCR | PaddleOCR / MinerU | — | CPU 可用 | 语析内置 OCR 引擎配置中心 |

**docker-compose.yml 扩展（含本地模型服务）**

```yaml
# docker-compose.prod.yml (公安内网完整部署)
services:
  # ... 前面的 api / worker / postgres / redis 等服务不变 ...

  # vLLM 对话模型服务 (需 GPU 节点)
  vllm-chat:
    image: vllm/vllm-openai:latest
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=0,1
    volumes:
      - /data/models:/models  # 模型文件挂载
    command: >
      --model /models/Qwen2.5-72B-Instruct
      --tensor-parallel-size 2
      --max-model-len 32768
      --port 8000
    ports:
      - "8000:8000"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 2
              capabilities: [gpu]

  # vLLM Embedding 服务
  vllm-embed:
    image: vllm/vllm-openai:latest
    runtime: nvidia
    volumes:
      - /data/models:/models
    command: >
      --model /models/bge-large-zh-v1.5
      --port 8001
    ports:
      - "8001:8001"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

> **部署要点**：
> 1. 模型文件需在**有网环境预先下载**，通过安全介质（光盘/加密U盘）导入公安网。
> 2. 语析的模型适配层已支持 OpenAI 兼容接口，vLLM/Ollama 无需修改业务代码。
> 3. OCR 引擎（PaddleOCR/MinerU）可完全离线运行，无需外网。
> 4. 开发阶段建议先用 Ollama + Qwen2.5-14B 快速迭代，生产环境再切换 vLLM + 72B 模型。
> 5. 如有条件，建议部署模型缓存层（如 vLLM 的 prefix caching），加速重复推理。

### 10.4 私有化部署要求

| 项目 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 8 核 | 16 核+ |
| 内存 | 16 GB | 32 GB+ |
| 存储 | 500 GB SSD | 2 TB SSD+ |
| GPU | 1× RTX 4090 24GB (Qwen2.5-14B) | 2× A100 80GB (Qwen2.5-72B) 或 4× RTX 4090 |
| 操作系统 | CentOS 7+ / Ubuntu 20+ | Ubuntu 22.04 LTS |
| Docker | 24+ | 24+ |
| 网络 | 内网隔离 | 内网隔离 + 专网 |
| 模型存储 | 100 GB (14B 模型) | 300 GB+ (72B 模型 + Embedding) |

> **GPU 说明**：公安网无法调用外网 API，必须本地部署大模型。14B 模型可用单卡 RTX 4090 运行（开发/小规模）；72B 模型需要 2×A100 80GB 或 4×RTX 4090（生产环境）。模型文件需在有网环境预下载后通过安全介质导入。

---

## 11. 开发计划与里程碑

### 11.1 开发阶段划分

> **核心策略**: Fork 语析 Yuxi v0.7.1 作为起点，保留其智能体引擎/知识引擎/存储层/中间件系统，在其上扩展公安业务层。这大幅减少底层基础设施的开发量，将精力集中在公安业务逻辑和专业智能体上。

```
Phase 0: 语析底座接入 (2周)
├── Fork xerrors/Yuxi v0.7.1，本地运行 (docker compose up)
├── 熟悉语析架构：server/routers + package/yuxi 分层
├── 体验语析智能体对话 + 知识库 + 知识图谱功能
├── 扩展用户模型：增加警号/警衔/部门字段
├── 扩展权限模型：admin/chief/officer/legal 四级角色
└── 验证语析的审批中间件 + SubAgents + 沙盒可用

Phase 1: 案件与任务管理 (4周)
├── 案件数据模型 + CRUD + 列表/详情页
├── 任务数据模型 + CRUD + 看板/列表视图
├── 任务分配与状态流转
├── 证据材料上传与管理 (复用语析 MinIO + 文档解析)
├── 工作台页面 (民警待办/案件动态)
└── 公安专用侧边导航 + 主题配色

Phase 2: 笔录分析智能体 + 案件智能创建 (3周)
├── 开发 transcript_analysis Skill (基于语析 Skills 系统)
├── 集成语析 OCR 引擎 (MinerU/PaddleX) 解析笔录
├── 笔录信息提取 → 结构化案件信息 JSON
├── 自动创建案件 + 生成初始任务列表
├── 复用语析审批中间件：智能体产出需民警确认
└── 案件导入流程 (上传笔录 → AI 分析 → 确认 → 创建)

Phase 2.5: 数字警员平台（StaffDeck 融合）(进行中)
├── 数字警员实体化：PoliceAgent 扩展工号/警衔/部门/头像/成长记录（police_agents）
├── 数字警员画廊/档案（统一在 yuxi 原生 /agent-manage 呈现；/police/officers 为重定向，非独立广场）
├── 技能体系：把各专业能力沉淀为 Yuxi Skill，支持民警对话直接调用
├── SOP / 办案规程框架：police_sops（状态机三件套已落地，但无执行器、无 sop_instances 表，LangGraph 状态机未实现）
├── 专案组模型：case_members 仅存民警；数字警员经 police_task_assignees 以执行人身份参与（人机协作）
└── 人机协作审核默认化：数字警员产出经民警签字(signed_hash)入卷

Phase 3: 多智能体协作与看板重构 (5周)
├── 案件推进智能体（原案件编排官，重定位）
│   ├── 审核通过事件触发（review_task 后 asyncio.create_task 进程内触发，非 ARQ 队列）
│   ├── 推进智能体顺序管线实现（extract → match template → generate draft，非 LangGraph、非循环决策）
│   ├── 任务草案生成（读取分析产出 → 提取要素 → 匹配模板 → 生成草案）
│   ├── 主办民警审查确认流程（确认/驳回/修改/追加）
│   └── 推进服务为模块级单例（无每案件实例、无 police_case_advancement_agents 表，决策落 police_advancement_logs）
├── 任务状态机扩展
│   ├── 新增 pending_confirmation / suspended / terminated / cancelled 状态
│   ├── police_tasks 溯源信息存于 extra.advancement JSON（source_event_id/draft_reasoning/evidence_refs 三字段未实现）
│   └── police_cases 表补充 investigation_direction / advancement_enabled 字段
├── 侦查方向变更机制
│   ├── 方向调整 → 受影响任务清单生成 → 主办民警逐条确认
│   ├── 已完成任务保留（打标签）+ 推进智能体重新规划
│   └── 方向变更事件写入案件时间线
├── 执行智能体（资金/调证/法制）
│   ├── 资金追踪师: 银行流水解析 + 资金追踪 + 异常检测（fund_analysis Skill）
│   ├── 调证生成师: 法律依据检索 + 调取通知书自动生成（evidence_collection Skill）
│   ├── 法制审核官: 程序/证据/定性三维度审核（legal_review Skill，复用语析审批中间件）
│   └── 民警在任务中召唤执行智能体 + 产出审核确认流程
├── 前端看板升级（参考 Multica 卡片式设计）
│   ├── 多列看板视图（待确认→待开始→进行中→审核中→已完成→已取消）
│   ├── 任务卡片组件（`<TaskCard>`）: 编号/标题/描述/优先级标签/依据引用/负责人
│   ├── 智能体任务视觉区分（🤖 标记 + 蓝边 + 依据引用）
│   ├── 优先级色标系统（紧急红/高橙/中黄/低绿）
│   └── 看板拖拽 + 列计数徽标 + 筛选器
├── 个人工作台升级
│   ├── 「待审查/待审核/待处理/通知」四组待办聚合展示
│   ├── 红点计数 WebSocket 推送
│   └── 导航新增「个人工作台」「我的任务」入口
└── SOP 驱动的任务自动流转（police_sops + task_flow_rules 降级为基础规则，推进智能体作为智能规则引擎）

Phase 4: 知识库与知识图谱 (3周)
├── 按案件隔离知识库 (复用语析多租户)
├── 定义公安知识图谱 Schema (人员/账户/通讯/事件)
├── 案件材料自动抽取实体关系 → Neo4j + Milvus 图谱
├── 知识图谱可视化 (AntV G6 + 语析图谱探索)
├── 图谱分析：最短路径/社团发现/跨案碰撞
└── 法律知识库构建 (法律法规/案例/文书模板)

Phase 5: 安全加固与优化 (3周)
├── PII 脱敏中间件 (借鉴 Octop，移植为语析中间件)
├── 工具防护层 (智能体外部调用安全控制)
├── 案件级数据隔离强化
├── 审计日志全量覆盖
├── 性能优化 (Worker 多副本/数据库索引/缓存)
├── UI/UX 打磨 (参考 Multica 看板交互 + Plane 项目管理交互)
└── Docker 生产部署配置

Phase 6: 测试与交付 (3周)
├── 端到端测试 (模拟完整案件流程)
├── 安全测试 (渗透测试/权限验证)
├── 压力测试 (多案件并发)
├── 部署文档 + 运维手册
├── 用户培训材料
└── 正式交付
```

### 11.2 里程碑

| 里程碑 | 原定时间 | 交付物 | 当前状态（v1.5） |
|--------|----------|--------|------------------|
| M0: 语析底座跑通 | 第 2 周 | Fork 语析成功运行，用户/权限模型扩展完成 | ✅ 已完成 |
| M1: 案件管理可用 | 第 6 周 | 案件-任务-证据管理 + 工作台 | ✅ 已完成 |
| M1.5: 数字警员平台 | 第 8 周 | 数字警员广场/档案/技能体系/SOP框架/专案组模型 | ⚠️ 部分实现（数字警员/档案/SOP 表结构已落地，但 SOP 无执行器、档案好评率无数据；广场已并入 /agent-manage）|
| M2: 智能创建上线 | 第 10 周 | 笔录分析师 + 专案组智能创建流程 | ✅ 已完成（笔录分析 + 导入建案）|
| M3: 多智能体协作 + 看板升级 | 第 15 周 | 推进智能体 + 任务模板 + 任务草案审查 + 工作台聚合 | ✅ 主体完成（推进管线+任务模板已落地，见 §4.9；非 LangGraph/ARQ 实现，见 §6.7）|
| M4: 知识图谱上线 | 第 18 周 | 知识库+知识图谱+可视化+图谱分析 | 📋 未启动（Neo4j/Milvus 在 police 代码中无调用）|
| M5: 安全加固完成 | 第 21 周 | PII 脱敏+审计+隔离+渗透测试 | ⚠️ 部分实现（审计/签名写入已落地；签名验证未实现、PII 脱敏待确认）|
| M6: 正式交付 | 第 24 周 | 完整平台 + 部署文档 + 培训材料 | 📋 待启动 |

> 📌 **v1.5 状态快照（截至 2026-08-03，仓库 HEAD = `41ba1555` "feat(police): 侦查任务模板配置化 + 推进智能体管线改造"）**：周数仍为规划排期，不代表实际日历。

### 11.3 项目目录结构

基于语析 Yuxi 的架构分层（server HTTP 适配层 + package 业务逻辑层）进行扩展：

```
police-agent-platform/          # Fork from xerrors/Yuxi v0.7.1
├── web/                          # 前端 (Vue 3 + Vite + Pinia)
│   ├── src/
│   │   ├── apis/                 # API 请求层 (复用语析，新增公安接口)
│   │   ├── assets/               # 静态资源 + 全局样式
│   │   ├── components/           # 公共组件
│   │   ├── composables/          # 组合式函数 (请求排队/Run SSE/审批/WebSocket ★ v1.4)
│   │   ├── layouts/              # 布局组件 (公安专用侧边导航)
│   │   ├── router/               # 路由 (增加案件/任务/工作台路由)
│   │   ├── stores/               # Pinia 状态管理
│   │   ├── views/                # 页面
│   │   │   ├── dashboard/        # 个人工作台 (待审查/待审核/待处理/通知) ★ v1.4 重定位
│   │   │   ├── my-tasks/          # 我的任务 (我领取/负责的所有任务) ★ v1.4 新增
│   │   │   ├── officers/         # 数字警员广场 + 档案 (画廊/详情/技能/成长) ★StaffDeck 风格
│   │   │   ├── sops/             # SOP 管理 (列表/版本/调用统计) ★
│   │   │   ├── cases/            # 案件管理/专案组 (列表/详情/组建/导入笔录)
│   │   │   ├── tasks/            # 工作项管理 (看板/列表/详情/审核)
│   │   │   ├── knowledge/        # 知识库与图谱 (检索/可视化/法律库)
│   │   │   ├── evidence/         # 证据材料管理
│   │   │   └── admin/            # 系统管理 (用户/部门/数字警员/模型)
│   │   ├── App.vue
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
│
├── backend/                      # 后端
│   ├── server/                   # HTTP 适配层 (语析原构)
│   │   ├── main.py               # FastAPI 应用入口
│   │   ├── routers/              # 路由边界
│   │   │   ├── __init__.py       # 路由注册
│   │   │   ├── auth_router.py    # 认证 (增加警号/角色)
│   │   │   ├── case_router.py    # ★ 案件管理 (新增)
│   │   │   ├── task_router.py    # ★ 任务管理 (新增)
│   │   │   ├── agent_router.py   # 智能体 (扩展语析)
│   │   │   ├── evidence_router.py # ★ 证据管理 (新增)
│   │   │   ├── knowledge_router.py # 知识库 (扩展语析)
│   │   │   ├── graph_router.py   # 知识图谱 (扩展语析)
│   │   │   └── dashboard_router.py # ★ 工作台 (新增)
│   │   │   └── ws_router.py         # ★ WebSocket 路由 (v1.4 新增, 任务状态推送)
│   │   ├── utils/
│   │   │   └── lifespan.py       # 生命周期管理
│   │   └── worker_main.py        # ARQ Worker 入口
│   │
│   ├── package/                  # 业务逻辑层
│   │   └── yuxi/                 # ★ 公安扩展包 (基于语析 yuxi 包扩展)
│   │       ├── agents/           # 智能体体系
│   │       │   ├── base.py       # 智能体基类 (复用语析 BaseAgent)
│   │       │   ├── buildin/      # 内置智能体
│   │       │   ├── middlewares/  # 中间件 (复用语析 + 新增公安中间件)
│   │       │   │   ├── pii_filter.py      # ★ PII 脱敏中间件 (借鉴 Octop)
│   │       │   │   ├── legal_review.py    # ★ 法制审核中间件
│   │       │   │   └── audit_log.py       # ★ 审计日志中间件
│   │       │   ├── toolkits/     # 工具集
│   │       │   │   ├── bank_statement.py  # ★ 银行流水解析
│   │       │   │   ├── document_gen.py    # ★ 法律文书生成
│   │       │   │   ├── legal_search.py    # ★ 法律依据检索
│   │       │   │   └── graph_builder.py   # ★ 知识图谱构建
│   │       │   ├── skills/       # ★ 公安专业技能
│   │       │   │   ├── transcript_analysis/  # 笔录分析 Skill
│   │       │   │   ├── fund_analysis/        # 资金分析 Skill
│   │       │   │   ├── evidence_collection/  # 调证生成 Skill
│   │       │   │   └── legal_review/         # 法制审核 Skill
│   │       │   ├── mcp/          # MCP 连接器
│   │       │   │   ├── police_query.py      # ★ 公安内部查询 MCP
│   │       │   │   └── bank_api.py          # ★ 银行接口 MCP
│   │       │   └── backends/     # 后端对接 (沙盒/知识库/文件系统)
│   │       │
│   │       ├── services/         # 用例层 (语析原构 + 公安扩展)
│   │       │   ├── case_service.py          # ★ 案件服务
│   │       │   ├── task_service.py          # ★ 任务服务
│   │       │   ├── flow_engine.py           # ★ 任务流转引擎
│   │       │   ├── advancement_service.py    # ★ 案件推进服务 (v1.4 新增)
│   │       │   ├── advancement_graph.py      # ★ 推进智能体 LangGraph (v1.4 新增)
│   │       │   ├── evidence_service.py      # ★ 证据服务
│   │       │   ├── agent_run_service.py     # 智能体运行 (扩展语析)
│   │       │   └── dashboard_service.py     # ★ 工作台服务
│   │       │
│   │       ├── repositories/     # PostgreSQL 访问边界
│   │       │   ├── case_repository.py       # ★ 案件仓储
│   │       │   ├── task_repository.py       # ★ 任务仓储
│   │       │   ├── evidence_repository.py   # ★ 证据仓储
│   │       │   └── audit_repository.py      # ★ 审计仓储
│   │       │
│   │       ├── storage/          # 存储层
│   │       │   ├── postgres/     # SQLAlchemy 模型 (扩展语析)
│   │       │   │   ├── models.py             # ★ 公安业务模型
│   │       │   │   └── ...                   # 语析原有模型
│   │       │   ├── redis/        # Redis 客户端 (复用语析)
│   │       │   ├── minio/        # 对象存储 (复用语析)
│   │       │   └── neo4j/        # 图数据库 (复用语析)
│   │       │
│   │       ├── knowledge/        # 知识引擎 (复用语析 + 公安扩展)
│   │       │   ├── graphs/       # 图谱能力
│   │       │   │   └── police_schema.py     # ★ 公安图谱 Schema
│   │       │   ├── parser/       # 文档解析 (复用语析 OCR 配置中心)
│   │       │   └── chunking/     # 分块策略 (复用语析)
│   │       │
│   │       ├── models/           # 模型适配 (复用语析 15+ 供应商)
│   │       ├── config/           # 配置管理 (复用语析)
│   │       └── utils/            # 通用工具 (复用语析)
│   │
│   ├── test/                     # 测试 (unit/integration/e2e 分层)
│   ├── alembic/                  # 数据库迁移
│   ├── requirements.txt
│   └── pyproject.toml
│
├── docker/                       # Docker 配置
│   ├── Dockerfile.web
│   ├── Dockerfile.api
│   └── Dockerfile.worker
│
├── scripts/                      # 初始化脚本 (复用语析)
│   ├── init.sh
│   └── init.ps1
│
├── docker-compose.yml            # 开发环境 (复用语析 + 公安扩展)
├── docker-compose.prod.yml       # 生产环境
├── .env.template
├── Makefile                      # 复用语析 Makefile (up/up-lite等)
└── README.md
```

> **说明**: 标 ★ 的为公安平台新增模块，其余为复用语析 Yuxi 原有模块。开发时先 Fork 语析 v0.7.1，保留其核心架构（智能体引擎/知识引擎/存储层/中间件系统），在 `package/yuxi` 包内新增公安业务逻辑，在 `server/routers` 内新增公安 API 路由。

### 11.4 开发工具建议

使用 AI 开发工具（如 WorkBuddy / Claude Code / Cursor）进行开发时的建议：

1. **先 Fork 语析再扩展**：不要从零搭建，先 `git clone --branch v0.7.1 https://github.com/xerrors/Yuxi.git`，让 AI 工具阅读语析的 `ARCHITECTURE.md` 和 `CLAUDE.md`/`AGENTS.md`，理解其分层架构后再开始扩展。
2. **遵循语析架构分层**：新增公安业务逻辑放在 `package/yuxi/services/` 和 `package/yuxi/repositories/`，新增 HTTP 路由放在 `server/routers/`，新增智能体 Skill 放在 `package/yuxi/agents/skills/`。不要破坏语析的分层边界。
3. **前端统一 Vue 3，禁止引入 React**：语析前端是 Vue 3 + Vite，参考 **StaffDeck 的数字员工广场/档案交互语言**（只看设计不看代码），任务/看板类视图可参考 Plane 布局。给 AI 的 Prompt 必须包含约束："使用 Vue 3 + Naive UI + Pinia + Vue Router，使用 `<script setup>` 语法，不要使用 React/JSX/Tailwind"。如果 AI 误生成 React 代码，立即纠正而非适配。
4. **复用语析中间件系统**：公安场景需要的审批工作流、PII 脱敏、审计日志等都应实现为语析中间件（`package/yuxi/agents/middlewares/`），而非硬编码进路由或页面。
5. **智能体开发为 Skills**：资金分析、笔录分析等专业智能体应开发为语析 Skills（`package/yuxi/agents/skills/`），利用语析的「解析草稿 → 确认安装」机制管理。
6. **先数据模型后业务逻辑**：先确定 PostgreSQL 表结构（在 `package/yuxi/storage/postgres/models.py` 中扩展），再生成业务逻辑和 API，最后生成前端页面。
7. **智能体迭代开发**：先让智能体跑通基本流程（利用语析对话工作台测试），再逐步增加工具和优化提示词。
8. **利用 LITE 模式加速迭代**：开发期用 `make up-lite` 跳过 Milvus/Neo4j 等重依赖，快速验证智能体和业务逻辑；需要测试知识库/图谱功能时再完整启动。
9. **测试驱动**：语析的测试按 `unit/integration/e2e` 分层，新增功能应放在对应层级测试。
10. **资金分析等大数据场景必须分治**：涉及银行流水等大批量数据的智能体，**禁止将原始数据直接喂给 LLM**。必须先用 Python/Pandas 完成数据清洗、统计、筛选，仅将 Top N 异常摘要交给 LLM 生成报告（详见 6.3 节）。
11. **私有化模型优先**：公安网通常无法访问外网 API，开发时即应配置本地模型（vLLM/Ollama），不要等到部署阶段才适配（详见 10.3 节）。

---

## 附录 A: 术语表

| 术语 | 说明 |
|------|------|
| 案件 / 案事件 | 公安办理的具体案件，在平台中作为项目进行管理，是协同的主线 |
| 专案组 | 围绕一个案件成立的「主办民警 + 若干数字警员」协同单元 |
| 数字警员 | 平台对公安各警种同事的抽象，技术映射为 **Yuxi Agent**。有工号、警衔、部门、专长、头像、工作记录，可对话、可被编入专案 |
| 技能 | 数字警员拥有的原子能力，技术映射为 **Yuxi Skill**。可在对话中直接调用（如「审查笔录」「法律建议」） |
| SOP / 办案规程 | 由「案件编排官」驱动的跨步骤流程，把多个数字警员/技能编排串联，由案件事件触发；技术映射为 LangGraph 状态机 + 任务流转规则 |
| 工作项 | 案件中需要完成的具体工作项（原「任务」），可分配给民警或数字警员 |
| 工作记录 | 数字警员每次对话/任务/产出的时间线沉淀，计入其成长轨迹 |
| 智能体 | 技术层概念，等价于数字警员（Yuxi Agent）。文档中「智能体」一词统一理解为「数字警员」 |
| 研判 | 案件前期分析研究阶段 |
| 调证 | 调取证据（如银行流水、通信记录等） |
| 资金流 | 涉案资金的流转路径 |
| 知识图谱 | 案件中人物、账户、通讯等实体及其关系的图结构表示 |
| PII | 个人身份信息 (Personally Identifiable Information) |
| RAG | 检索增强生成 (Retrieval-Augmented Generation) |
| LangGraph | 基于图的多智能体编排框架 |
| ARQ | 基于 Redis 的 Python 异步任务队列 |

## 附录 B: 参考项目

| 项目 | 仓库 | 用途 |
|------|------|------|
| 语析 Yuxi | https://github.com/xerrors/Yuxi | **基础底座（MIT 协议，直接 Fork 扩展）** |
| StaffDeck | https://github.com/OpenBMB/StaffDeck | **产品形态 / UI 交互语言参考**（数字员工广场、员工档案、SOP、工作记录） |
| Octop | https://github.com/TencentCloud/Octop | 多智能体管理 + PII 脱敏参考 |
| Plane | https://github.com/makeplane/plane | 项目管理 UI/UX 参考（AGPL，仅设计参考） |
| LangGraph | https://github.com/langchain-ai/langgraph | 智能体编排框架 |
| DeepAgents | https://github.com/langchain-ai/deepagents | 深度智能体框架 |
| AntV G6 | https://github.com/antvis/G6 | 知识图谱可视化 |
| Naive UI | https://github.com/tusen-ai/naive-ui | 前端 UI 组件库 |
