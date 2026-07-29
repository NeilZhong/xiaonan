# 智案协 — 公安多智能体协作平台开发文档

> **版本**: v1.2  
> **日期**: 2026-07-30  
> **状态**: 补充生产落地关键坑点（前端技术栈/资金分析性能/证据防篡改/离线部署）  
> **基础底座**: 语析 Yuxi v0.7.1 (https://github.com/xerrors/Yuxi, MIT 协议)

---

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 开源项目选型分析](#2-开源项目选型分析)
- [3. 系统架构设计](#3-系统架构设计)
- [4. 核心功能模块设计](#4-核心功能模块设计)
- [5. 数据模型设计](#5-数据模型设计)
- [6. 智能体设计](#6-智能体设计)
- [7. API 接口设计](#7-api-接口设计)
- [8. 前端 UI 设计规范](#8-前端-ui-设计规范)
- [9. 安全与合规设计](#9-安全与合规设计)
- [10. 部署方案](#10-部署方案)
- [11. 开发计划与里程碑](#11-开发计划与里程碑)

---

## 1. 项目概述

### 1.1 背景与问题

当前公安专案侦办过程中存在以下痛点：

- **协同效率低**：专案涉及研判、抓捕、审讯、办理、移送起诉等多个阶段，参与人员多、流转环节多，信息同步靠口头和纸质，容易出现信息断层。
- **重复劳动多**：资金流分析、文书生成、证据整理等工作高度重复，消耗大量警力。
- **知识难沉淀**：每个案件的研判过程、资金流向、人员关系等知识散落在个人脑中和零散文档中，无法复用。
- **线索易遗漏**：海量证据材料人工梳理，关键线索容易遗漏，缺乏系统化的辅助分析手段。

### 1.2 项目目标

构建一个面向公安机关的 **多智能体协作平台**，以 **项目管理** 为蓝本，将案件作为项目进行全生命周期管理，通过 **AI 智能体** 协助民警完成资金分析、文书生成、法制审核等工作，实现：

1. **案件项目化**：案件即项目，侦查/办理各阶段的工作即为项目任务，可分配给民警或智能体。
2. **智能体协作**：资金分析、调证生成、法制审核等专业智能体参与案件办理，与民警形成人机协作。
3. **任务自动流转**：智能体根据案件进展自动创建、派发新任务（如一级流水到账后自动创建资金分析任务）。
4. **知识图谱化**：案件资料结构化为知识图谱，支持实体关系查询与推理。
5. **全程可追溯**：所有操作、智能体产出、民警审核均有审计记录。

### 1.3 核心价值主张

| 角色 | 价值 |
|------|------|
| **案件指挥员** | 全局掌控案件进展，任务自动流转，智能体辅助决策 |
| **办案民警** | 工作台看到分配给自己的任务，按指引完成即可，无需从零分析 |
| **智能体** | 承担重复性、专业性工作（资金分析、文书生成等），产出供民警审核 |
| **法制部门** | 法制智能体前置审核，减少程序性错误 |

### 1.4 典型工作流

```
受害人报案 → 上传报案笔录
    → 笔录分析智能体提取关键信息（涉案银行卡、微信号、嫌疑人信息等）
    → 自动创建案件项目 + 生成初始任务列表
        ├─ 任务1: 调取银行卡X流水 → 分配给调证智能体 → 生成调取通知书
        ├─ 任务2: 微信号查询 → 分配给网警民警
        └─ 任务3: 资金初查 → 分配给资金分析智能体
    → 一级流水到账（民警上传）
        → 资金分析智能体自动触发分析
        → 产出: 涉案资金追踪报告 + 需调取的二级账户清单
        → 自动创建新任务: 调取二级账户Y流水
    → ... 持续迭代直到资金链路完整 ...
    → 法制智能体审核全案证据链
    → 移送起诉
```

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

---

## 3. 系统架构设计

### 3.1 整体架构

平台采用 **分层架构 + 模块化设计**，自底向上分为五层：

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端展示层 (Frontend)                      │
│  Vue 3 + Vite + Pinia + Element Plus / Naive UI                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │ 工作台    │ │ 案件管理  │ │ 任务管理  │ │ 智能体中心│ │知识图谱 ││
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘│
├─────────────────────────────────────────────────────────────────┤
│                     API 网关层 (API Gateway)                      │
│  FastAPI + JWT Auth + RBAC + Rate Limit + Audit Log              │
├─────────────────────────────────────────────────────────────────┤
│                     业务服务层 (Business Services)                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │ 案件服务  │ │ 任务服务  │ │ 智能体调度│ │ 文书服务  │ │知识服务 ││
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

#### 4.1.2 案件创建流程（智能创建）

1. **上传报案笔录**：用户上传受害人报案笔录（PDF/Word/图片）
2. **笔录分析智能体**自动：
   - 提取案件类型、涉案金额、案发时间地点
   - 提取涉案人员信息（嫌疑人、受害人、证人）
   - 提取涉案账户（银行卡、支付宝、微信）
   - 提取涉案通讯信息（微信号、QQ号、手机号）
3. **自动创建案件项目**：生成案件编号、标题、描述
4. **自动生成初始任务列表**：根据提取的信息生成需要执行的任务
5. **用户确认**：用户审核智能体提取的信息和生成的任务，可修改后确认

#### 4.1.3 案件信息结构

```
案件 (Case)
├── 基本信息: 编号、标题、类型、状态、创建时间
├── 案情描述: 案发经过、涉案金额、受害人信息
├── 涉案人员: 嫌疑人、受害人、证人 (人员关系图谱)
├── 涉案账户: 银行卡、第三方支付 (资金网络图谱)
├── 涉案通讯: 微信、QQ、手机号 (通讯网络图谱)
├── 证据材料: 笔录、流水、截图、录音录像
├── 法律文书: 立案决定书、调取通知书、起诉意见书
├── 案件阶段: 研判 → 抓捕 → 办理 → 移送
├── 任务列表: 各阶段的具体任务
├── 案件团队: 指挥员、办案民警、法制审核员
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

### 4.3 智能体中心

#### 4.3.1 智能体管理

- **智能体注册**：每个智能体有名称、描述、能力标签、系统提示词
- **智能体配置**：绑定的大模型、工具列表、知识库
- **智能体模板**：预设的专业智能体模板（资金分析、调证生成等）
- **运行监控**：查看智能体运行状态、历史执行记录
- **能力扩展**：通过 Skills / MCP / Tools 扩展智能体能力

#### 4.3.2 智能体调度模式

| 模式 | 说明 | 示例 |
|------|------|------|
| **直接指派** | 任务直接分配给指定智能体 | 资金分析任务→资金分析智能体 |
| **编排调度** | 案件编排智能体根据上下文决定调用哪个智能体 | 案件编排智能体分析后决定先调笔录分析 |
| **链式协作** | 多个智能体按链式顺序协作 | 笔录分析→资金分析→调证生成→法制审核 |
| **人机协作** | 智能体完成初稿，民警审核确认 | 资金分析智能体产出报告，民警审核后采纳 |

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

- **我的待办任务**：分配给我的待处理/进行中任务
- **待审核任务**：智能体完成、需要我审核的任务
- **案件动态**：我参与的案件的最新进展
- **智能体动态**：智能体的运行状态和产出通知
- **快捷操作**：创建案件、上传材料、查看图谱等

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

#### 5.2.1 用户与权限

```sql
-- 用户表
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username    VARCHAR(50) UNIQUE NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    real_name   VARCHAR(50) NOT NULL,
    police_id   VARCHAR(20) UNIQUE,        -- 警号
    rank        VARCHAR(20),                -- 警衔
    department  VARCHAR(100),               -- 所属部门
    phone       VARCHAR(20),
    role        VARCHAR(20) NOT NULL DEFAULT 'officer',  -- admin/chief/officer/legal
    status      VARCHAR(20) DEFAULT 'active',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 案件成员表 (多对多)
CREATE TABLE case_members (
    case_id     UUID REFERENCES cases(id) ON DELETE CASCADE,
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    role        VARCHAR(20) NOT NULL,  -- commander/handler/reviewer/observer
    joined_at   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (case_id, user_id)
);
```

#### 5.2.2 案件

```sql
CREATE TABLE cases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_number     VARCHAR(50) UNIQUE NOT NULL,    -- 案件编号
    title           VARCHAR(200) NOT NULL,
    case_type       VARCHAR(50),                     -- 案件类型: fraud/theft/etc
    description     TEXT,
    status          VARCHAR(20) DEFAULT 'draft',     -- draft/investigation/arrest/handling/prosecution/closed
    phase           VARCHAR(30) DEFAULT 'research',  -- research/arrest/handling/prosecution
    priority        VARCHAR(10) DEFAULT 'medium',
    incident_date   TIMESTAMPTZ,                      -- 案发时间
    incident_location   TEXT,                         -- 案发地点
    total_amount    DECIMAL(15,2),                    -- 涉案金额
    victim_info     JSONB,                            -- 受害人信息
    suspect_info    JSONB,                            -- 嫌疑人信息 (动态)
    metadata        JSONB DEFAULT '{}',               -- 扩展字段
    knowledge_base_id  VARCHAR(100),                  -- 关联知识库ID
    graph_id        VARCHAR(100),                     -- 关联知识图谱ID
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 案件阶段记录
CREATE TABLE case_phases (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     UUID REFERENCES cases(id) ON DELETE CASCADE,
    phase       VARCHAR(30) NOT NULL,
    status      VARCHAR(20) DEFAULT 'active',  -- active/completed/skipped
    started_at  TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    summary     TEXT,
    metadata    JSONB DEFAULT '{}'
);
```

#### 5.2.3 任务

```sql
CREATE TABLE tasks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         UUID REFERENCES cases(id) ON DELETE CASCADE,
    title           VARCHAR(200) NOT NULL,
    description     TEXT,
    type            VARCHAR(50) NOT NULL,              -- 任务类型
    status          VARCHAR(20) DEFAULT 'pending',     -- pending/in_progress/review/completed/blocked
    assignee_type   VARCHAR(10) NOT NULL,              -- human/agent
    assignee_id     UUID,                               -- 用户ID或智能体ID
    assignee_name   VARCHAR(100),                       -- 冗余字段，显示用
    creator_id      UUID,                               -- 创建者(用户或智能体)
    creator_type    VARCHAR(10) DEFAULT 'human',        -- human/agent/system
    priority        VARCHAR(10) DEFAULT 'medium',
    phase           VARCHAR(30),                         -- 案件阶段
    parent_task_id  UUID REFERENCES tasks(id),
    dependencies    UUID[] DEFAULT '{}',                 -- 依赖任务ID列表
    attachments     JSONB DEFAULT '[]',                  -- 附件列表
    result          JSONB,                               -- 任务结果
    instructions    TEXT,                                -- 任务指引说明
    due_date        TIMESTAMPTZ,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    reviewed_by     UUID REFERENCES users(id),           -- 审核民警 (完成任务审核时填入)
    reviewed_at     TIMESTAMPTZ,                          -- 审核时间
    signed_hash     VARCHAR(128),                         -- 民警审核签名哈希 (SHA-256: police_id + reviewed_at + result_hash)
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 任务流转规则表
CREATE TABLE task_flow_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         UUID REFERENCES cases(id) ON DELETE CASCADE,  -- NULL=全局规则
    name            VARCHAR(100) NOT NULL,
    trigger_event   VARCHAR(50) NOT NULL,     -- task_completed/file_uploaded/phase_changed
    condition       JSONB NOT NULL,            -- 触发条件 (JSON规则)
    action          VARCHAR(50) NOT NULL,      -- create_task/notify/auto_approve
    target_task_type VARCHAR(50),              -- 创建的新任务类型
    target_assignee_type VARCHAR(10),          -- human/agent
    target_assignee_id UUID,                   -- 具体分配对象
    enabled         BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 任务事件日志 (用于触发流转规则)
CREATE TABLE task_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     UUID REFERENCES cases(id) ON DELETE CASCADE,
    task_id     UUID REFERENCES tasks(id) ON DELETE CASCADE,
    event_type  VARCHAR(50) NOT NULL,          -- created/assigned/started/completed/blocked/file_uploaded
    event_data  JSONB DEFAULT '{}',
    created_by  UUID,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

#### 5.2.4 智能体

```sql
-- 智能体定义
CREATE TABLE agents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    type            VARCHAR(50) NOT NULL,          -- transcript_analyst/fund_analyst/etc
    system_prompt   TEXT NOT NULL,                  -- 系统提示词
    model_config    JSONB NOT NULL,                 -- 模型配置 (provider/model/temperature)
    tools           JSONB DEFAULT '[]',             -- 工具列表
    skills          JSONB DEFAULT '[]',             -- 技能列表
    knowledge_base_ids  JSONB DEFAULT '[]',         -- 关联知识库
    capabilities    JSONB DEFAULT '[]',             -- 能力标签
    icon            VARCHAR(50),                    -- 图标
    status          VARCHAR(20) DEFAULT 'active',
    is_template     BOOLEAN DEFAULT FALSE,          -- 是否为模板
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 智能体运行记录
CREATE TABLE agent_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        UUID REFERENCES agents(id),
    task_id         UUID REFERENCES tasks(id),
    case_id         UUID REFERENCES cases(id),
    status          VARCHAR(20) DEFAULT 'queued',   -- queued/running/completed/failed/cancelled
    input           JSONB,                           -- 输入参数
    output          JSONB,                           -- 输出结果
    artifacts       JSONB DEFAULT '[]',              -- 产出文件列表
    error           TEXT,
    tokens_used     INTEGER DEFAULT 0,
    duration_ms     INTEGER,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 智能体消息记录 (LangGraph 对话历史)
CREATE TABLE agent_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID REFERENCES agent_runs(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL,            -- user/assistant/tool/system
    content         TEXT,
    tool_calls      JSONB,                           -- 工具调用记录
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### 5.2.5 证据与文档

```sql
-- 证据材料
CREATE TABLE evidence (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         UUID REFERENCES cases(id) ON DELETE CASCADE,
    task_id         UUID REFERENCES tasks(id),        -- 关联任务 (可空)
    name            VARCHAR(200) NOT NULL,
    type            VARCHAR(50) NOT NULL,              -- transcript/bank_flow/screenshot/audio/video/document
    file_path       VARCHAR(500) NOT NULL,             -- MinIO 存储路径
    file_hash       VARCHAR(64),                       -- SHA-256 完整性校验
    file_size       BIGINT,
    mime_type       VARCHAR(100),
    ocr_text        TEXT,                              -- OCR 提取的文本
    parsed_content  JSONB,                             -- 结构化解析结果
    metadata        JSONB DEFAULT '{}',
    uploaded_by     UUID REFERENCES users(id),
    version         INTEGER DEFAULT 1,
    parent_id       UUID REFERENCES evidence(id),      -- 上一版本
    reviewed_by     UUID REFERENCES users(id),          -- 审核民警 (AI生成的证据材料需民警审核确认)
    reviewed_at     TIMESTAMPTZ,                         -- 审核时间
    signed_hash     VARCHAR(128),                        -- 民警审核签名 (SHA-256: police_id + reviewed_at + file_hash)
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 证据关联关系 (证据链)
CREATE TABLE evidence_links (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         UUID REFERENCES cases(id) ON DELETE CASCADE,
    source_evidence_id  UUID REFERENCES evidence(id) ON DELETE CASCADE,
    target_evidence_id  UUID REFERENCES evidence(id) ON DELETE CASCADE,
    relation_type   VARCHAR(50),                      -- derives_from/supports/contradicts
    description     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### 5.2.6 知识图谱 (Neo4j)

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

#### 5.2.7 审计日志

```sql
CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID,
    user_name       VARCHAR(100),
    action          VARCHAR(50) NOT NULL,    -- create/update/delete/login/assign/approve/reject
    resource_type   VARCHAR(50),             -- case/task/agent/evidence/document
    resource_id     UUID,
    case_id         UUID,                    -- 关联案件
    details         JSONB,                   -- 操作详情
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 6. 智能体设计

### 6.1 智能体概览

| 智能体 | 职责 | 输入 | 输出 | 关联任务类型 |
|--------|------|------|------|-------------|
| 笔录分析智能体 | 分析报案笔录，提取关键信息 | 笔录文档 | 结构化案件信息 + 初始任务列表 | transcript_analysis |
| 资金分析智能体 | 分析银行流水，追踪涉案资金 | 流水文件 | 资金追踪报告 + 下级账户清单 | fund_analysis |
| 调证智能体 | 生成调取通知书等法律文书 | 调证需求 | 法律文书文档 | evidence_collection |
| 法制审核智能体 | 审核案件程序合规性 | 案件材料 | 审核意见 + 整改建议 | legal_review |
| 文书生成智能体 | 生成各类法律文书 | 案件信息 | 法律文书文档 | document_generation |
| 证据梳理智能体 | 梳理证据链，生成证据清单 | 证据材料 | 证据链报告 | knowledge_extraction |
| 案件编排智能体 | 分析案件进展，决策任务流转 | 案件上下文 | 新任务创建指令 | (编排层，不直接接任务) |

### 6.2 笔录分析智能体

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

### 6.3 资金分析智能体

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

### 6.4 调证智能体

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

### 6.5 法制审核智能体

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

### 6.6 案件编排智能体

```
职责: 全局视角的案件编排者，分析案件进展，决策任务流转

这不是一个直接接任务的智能体，而是作为"调度中心"运行:
  - 监听案件事件 (任务完成、文件上传、阶段变更)
  - 评估当前案件进展
  - 决定是否需要创建新任务
  - 决定新任务分配给哪个智能体或民警

编排逻辑 (LangGraph StateGraph):

  ┌─────────────┐
  │ 事件监听     │
  └──────┬──────┘
         ▼
  ┌─────────────┐     ┌──────────────┐
  │ 上下文分析   │────→│ 是否需要新任务?│
  └─────────────┘     └──────┬───────┘
                             │
                    ┌────────┴────────┐
                    │ 是               │ 否
                    ▼                  ▼
             ┌─────────────┐   ┌─────────────┐
             │ 规划任务     │   │ 继续监听     │
             │ (类型/内容)  │   └─────────────┘
             └──────┬──────┘
                    ▼
             ┌─────────────┐
             │ 决定分配对象 │
             │ (Agent/Human)│
             └──────┬──────┘
                    ▼
             ┌─────────────┐
             │ 创建任务     │
             │ + 通知      │
             └─────────────┘
```

### 6.7 智能体开发规范

每个智能体遵循统一接口规范：

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
    """智能体基类"""
    name: str
    description: str
    tools: list
    
    def build_graph(self) -> StateGraph:
        """构建 LangGraph 工作流"""
        graph = StateGraph(AgentInput)
        # ... 定义节点和边 ...
        return graph.compile()
    
    async def run(self, input: AgentInput) -> AgentOutput:
        """执行智能体"""
        graph = self.build_graph()
        result = await graph.ainvoke(input)
        return self.format_output(result)
    
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
- 版本: `/api/v1/`
- 分页: `?page=1&page_size=20`
- 排序: `?sort=-created_at` (负号=降序)
- 筛选: `?status=pending&assignee_type=agent`

### 7.2 核心 API 列表

#### 7.2.1 认证

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/auth/login` | 用户登录 |
| POST | `/api/v1/auth/refresh` | 刷新 Token |
| GET  | `/api/v1/auth/me` | 获取当前用户信息 |

#### 7.2.2 案件管理

| Method | Path | 说明 |
|--------|------|------|
| GET  | `/api/v1/cases` | 案件列表 (支持筛选/排序/分页) |
| POST | `/api/v1/cases` | 创建案件 |
| GET  | `/api/v1/cases/{id}` | 案件详情 |
| PUT  | `/api/v1/cases/{id}` | 更新案件 |
| DELETE | `/api/v1/cases/{id}` | 删除案件 |
| POST | `/api/v1/cases/import` | 上传笔录智能创建案件 |
| GET  | `/api/v1/cases/{id}/tasks` | 案件下的任务列表 |
| GET  | `/api/v1/cases/{id}/evidence` | 案件证据列表 |
| GET  | `/api/v1/cases/{id}/timeline` | 案件时间线 |
| GET  | `/api/v1/cases/{id}/graph` | 案件知识图谱数据 |
| POST | `/api/v1/cases/{id}/members` | 添加案件成员 |
| PUT  | `/api/v1/cases/{id}/phase` | 切换案件阶段 |

#### 7.2.3 任务管理

| Method | Path | 说明 |
|--------|------|------|
| GET  | `/api/v1/tasks` | 任务列表 (支持筛选) |
| GET  | `/api/v1/tasks/my` | 我的任务 |
| GET  | `/api/v1/tasks/my/review` | 待我审核的任务 |
| POST | `/api/v1/cases/{case_id}/tasks` | 创建任务 |
| GET  | `/api/v1/tasks/{id}` | 任务详情 |
| PUT  | `/api/v1/tasks/{id}` | 更新任务 |
| POST | `/api/v1/tasks/{id}/assign` | 分配任务 |
| POST | `/api/v1/tasks/{id}/start` | 开始任务 |
| POST | `/api/v1/tasks/{id}/complete` | 完成任务 |
| POST | `/api/v1/tasks/{id}/review` | 审核任务 (通过/驳回) |
| POST | `/api/v1/tasks/{id}/attachments` | 上传任务附件 |
| GET  | `/api/v1/tasks/{id}/events` | 任务事件日志 |

#### 7.2.4 智能体

| Method | Path | 说明 |
|--------|------|------|
| GET  | `/api/v1/agents` | 智能体列表 |
| POST | `/api/v1/agents` | 注册智能体 |
| GET  | `/api/v1/agents/{id}` | 智能体详情 |
| PUT  | `/api/v1/agents/{id}` | 更新智能体配置 |
| GET  | `/api/v1/agents/{id}/runs` | 智能体运行记录 |
| POST | `/api/v1/tasks/{task_id}/agent-run` | 触发智能体执行任务 |
| GET  | `/api/v1/agent-runs/{id}` | 运行详情 |
| GET  | `/api/v1/agent-runs/{id}/stream` | 运行流式输出 (SSE) |
| POST | `/api/v1/agent-runs/{id}/cancel` | 取消运行 |

#### 7.2.5 证据与文档

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/cases/{case_id}/evidence` | 上传证据材料 |
| GET  | `/api/v1/cases/{case_id}/evidence` | 证据列表 |
| GET  | `/api/v1/evidence/{id}` | 证据详情 |
| GET  | `/api/v1/evidence/{id}/download` | 下载证据文件 |
| GET  | `/api/v1/evidence/{id}/preview` | 在线预览 |
| POST | `/api/v1/evidence/{id}/ocr` | 触发OCR识别 |
| GET  | `/api/v1/cases/{case_id}/evidence-chain` | 证据链 |

#### 7.2.6 知识库与图谱

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/v1/cases/{case_id}/knowledge/search` | 案件知识库检索 |
| GET  | `/api/v1/cases/{case_id}/graph` | 获取知识图谱 |
| GET  | `/api/v1/cases/{case_id}/graph/entities` | 图谱实体列表 |
| GET  | `/api/v1/cases/{case_id}/graph/relations` | 图谱关系列表 |
| POST | `/api/v1/cases/{case_id}/graph/query` | Cypher/路径查询 |
| POST | `/api/v1/cases/{case_id}/graph/extract` | 触发知识抽取 |

#### 7.2.7 工作台

| Method | Path | 说明 |
|--------|------|------|
| GET  | `/api/v1/dashboard/stats` | 工作台统计数据 |
| GET  | `/api/v1/dashboard/my-tasks` | 我的待办任务 |
| GET  | `/api/v1/dashboard/review-tasks` | 待审核任务 |
| GET  | `/api/v1/dashboard/case-updates` | 案件动态 |
| GET  | `/api/v1/dashboard/agent-updates` | 智能体动态 |

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

**关键词**: 现代、简洁、流畅、专业

参考 Plane 的设计语言：

- **极简主义**：大量留白，去除冗余装饰，信息层次清晰
- **卡片化布局**：内容以卡片形式组织，边界柔和
- **流畅交互**：拖拽、动画过渡自然，操作反馈即时
- **专业配色**：以深蓝/藏青为主色调（公安行业属性），辅以灰白底色
- **信息密度适中**：不过度堆砌信息，也不过于空旷

> **⚠️ 前端技术栈统一警告（重要）**
>
> Plane 的前端基于 **React / Next.js**，而基础底座语析（Yuxi）的前端完全是 **Vue 3 + Vite**。
> **切勿尝试迁移 React 组件代码到 Vue 项目中**——Vue 的响应式系统（Proxy + ref/reactive）与 React 的状态更新机制（不可变状态 + hooks）在底层完全不同，混用会导致 50% 以上的开发时间浪费在数据响应机制适配上。
>
> **正确做法**：
> 1. 前端**全面采用 Vue 3 生态**（Naive UI 组件库 + Pinia 状态管理 + Vue Router）。
> 2. 参考 Plane 的 **UI 布局截图和交互逻辑**（看板拖拽、列表筛选、Command-K 搜索等），但用 Vue 3 重新实现。
> 3. 给 AI 开发工具发 Prompt 时，必须明确指定技术栈：
>    > "参照 Plane 的 UI 布局和交互逻辑，使用 **Vue 3 + Naive UI + Pinia** 生成页面组件。不要使用 React/JSX 语法，不要使用 Tailwind CSS（语析使用原生 CSS + scoped styles）。"
> 4. 如果需要参考 Plane 的具体组件实现，只看其 **DOM 结构和 CSS 类名设计**，不看其 React 组件代码。

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
- 工作台 (Dashboard)
- 案件管理 (Cases)
  - 全部案件
  - 我参与的
  - 按阶段筛选
- 任务管理 (Tasks)
  - 我的任务
  - 待审核
  - 全部任务
- 智能体中心 (Agents)
  - 智能体列表
  - 运行监控
  - 智能体模板
- 知识库 (Knowledge)
  - 案件知识库
  - 知识图谱
  - 法律知识库
- 统计分析 (Analytics)
- 系统管理 (Admin) [仅管理员]

### 8.4 核心页面设计

#### 8.4.1 工作台

```
┌─────────────────────────────────────────────────────┐
│  工作台                                              │
│  早班好，张警官 | 2026-07-30 周四                    │
├─────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐│
│  │ 待办任务  │ │ 待审核   │ │ 进行中   │ │ 今日新增 ││
│  │    12    │ │    5     │ │    8     │ │    3    ││
│  └──────────┘ └──────────┘ └──────────┘ └─────────┘│
├──────────────────────┬──────────────────────────────┤
│  我的待办任务 (12)    │  案件动态                     │
│  ┌─────────────────┐ │  ┌────────────────────────┐ │
│  │⚠ 调取工行流水    │ │  │ 「电信诈骗案」资金分析  │ │
│  │  案件: 张某诈骗案 │ │  │ 智能体已完成分析        │ │
│  │  截止: 今天       │ │  │ 2分钟前                │ │
│  └─────────────────┘ │  └────────────────────────┘ │
│  ┌─────────────────┐ │  ┌────────────────────────┐ │
│  │📋 审核资金分析报告│ │  │ 「盗窃案」新证据已上传  │ │
│  │  案件: 李某盗窃案 │ │  │ 王警官 10分钟前         │ │
│  │  截止: 明天       │ │  └────────────────────────┘ │
│  └─────────────────┘ │                              │
└──────────────────────┴──────────────────────────────┘
```

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

#### 8.4.4 任务详情

```
┌─────────────────────────────────────────────────────┐
│  ← 返回    资金分析 - 工行账户流水分析               │
│                                                       │
│  状态: [进行中]  优先级: [高]  分配给: [资金分析智能体]│
│  创建者: 案件编排智能体    创建时间: 2026-07-30 10:00│
├─────────────────────────────────────────────────────┤
│  任务描述                                             │
│  请分析以下工行账户的银行流水，追踪涉案资金流向：      │
│  账户: 6222****1234, 户名: 王某                      │
│  分析重点:                                            │
│  1. 资金转入来源                                      │
│  2. 资金转出去向                                      │
│  3. 异常交易模式                                      │
│                                                       │
│  附件: [工行流水_202607.xlsx] [受害人笔录摘要.pdf]   │
├─────────────────────────────────────────────────────┤
│  智能体运行状态                                       │
│  ┌─────────────────────────────────────────────┐    │
│  │ 资金分析智能体 正在运行...                    │    │
│  │ ████████████████░░░░ 75%                     │    │
│  │ [实时日志输出区域]                            │    │
│  │ > 正在解析流水文件...                          │    │
│  │ > 识别到 156 条交易记录                        │    │
│  │ > 追踪资金流向...                              │    │
│  │ > 发现 3 个可疑转入账户                        │    │
│  └─────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────┤
│  审核操作 (任务完成后显示)                            │
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
```

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
| `signed_hash` (SHA-256) | 民警审核确认时 | `SHA-256(police_id + reviewed_at + file_hash)` | evidence.signed_hash / tasks.signed_hash | 证明"该民警在该时间确认了该文件" |

#### 9.5.2 签名流程

```
智能体生成文书/分析结果
    │
    ▼
文件上传至 MinIO → 计算 file_hash (SHA-256) → 落库 evidence.file_hash
    │
    ▼
民警在工作台审核 → 点击"审核通过"
    │
    ▼
系统自动计算 signed_hash = SHA-256(民警警号 + 审核时间戳ISO + file_hash)
    │
    ▼
落库: evidence.reviewed_by = 民警ID
      evidence.reviewed_at = 审核时间
      evidence.signed_hash = 签名哈希
    │
    ▼
审计日志记录: "民警XXX于YYYY-MM-DD HH:MM:SS 审核确认文件YYY (hash:zzz)"
```

#### 9.5.3 验证流程（诉讼阶段/监督检查）

```python
import hashlib

def verify_evidence_integrity(evidence_record, original_file_bytes):
    """验证证据完整性"""
    # 1. 验证文件哈希（文件未被篡改）
    current_hash = hashlib.sha256(original_file_bytes).hexdigest()
    if current_hash != evidence_record.file_hash:
        return False, "文件已被篡改: file_hash 不匹配"

    # 2. 验证签名哈希（审核记录未被伪造）
    expected_signed = hashlib.sha256(
        f"{evidence_record.reviewed_by}"
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

Phase 3: 专业智能体开发 (4周)
├── 资金分析智能体 (fund_analysis Skill)
│   ├── 银行流水解析工具 (toolkits/bank_statement.py)
│   ├── 资金追踪 + 异常检测逻辑
│   └── 产出资金流向图 + 下级账户清单
├── 调证智能体 (evidence_collection Skill)
│   ├── 法律依据检索 (知识库 RAG)
│   └── 调取通知书自动生成
├── 法制审核智能体 (legal_review Skill)
│   ├── 复用语析审批中间件实现人机协作
│   └── 程序/证据/定性三维度审核
├── 案件编排智能体 (基于语析 SubAgents)
│   ├── 主智能体监听案件事件
│   ├── 调度专业子智能体
│   └── 自动创建后续任务
└── 任务自动流转引擎 (task_flow_rules + 事件监听)

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
├── UI/UX 打磨 (参考 Plane 项目管理交互)
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

| 里程碑 | 时间 | 交付物 |
|--------|------|--------|
| M0: 语析底座跑通 | 第 2 周 | Fork 语析成功运行，用户/权限模型扩展完成 |
| M1: 案件管理可用 | 第 6 周 | 案件-任务-证据管理 + 工作台 |
| M2: 智能创建上线 | 第 9 周 | 笔录分析智能体 + 案件智能创建流程 |
| M3: 多智能体协作 | 第 13 周 | 资金分析+调证+法制+编排，任务自动流转 |
| M4: 知识图谱上线 | 第 16 周 | 知识库+知识图谱+可视化+图谱分析 |
| M5: 安全加固完成 | 第 19 周 | PII 脱敏+审计+隔离+渗透测试 |
| M6: 正式交付 | 第 22 周 | 完整平台 + 部署文档 + 培训材料 |

### 11.3 项目目录结构

基于语析 Yuxi 的架构分层（server HTTP 适配层 + package 业务逻辑层）进行扩展：

```
police-agent-platform/          # Fork from xerrors/Yuxi v0.7.1
├── web/                          # 前端 (Vue 3 + Vite + Pinia)
│   ├── src/
│   │   ├── apis/                 # API 请求层 (复用语析，新增公安接口)
│   │   ├── assets/               # 静态资源 + 全局样式
│   │   ├── components/           # 公共组件
│   │   ├── composables/          # 组合式函数 (请求排队/Run SSE/审批等)
│   │   ├── layouts/              # 布局组件 (公安专用侧边导航)
│   │   ├── router/               # 路由 (增加案件/任务/工作台路由)
│   │   ├── stores/               # Pinia 状态管理
│   │   ├── views/                # 页面
│   │   │   ├── dashboard/        # 工作台 (民警待办/案件动态/智能体动态)
│   │   │   ├── cases/            # 案件管理 (列表/详情/创建/导入笔录)
│   │   │   ├── tasks/            # 任务管理 (看板/列表/详情/审核)
│   │   │   ├── agents/           # 智能体中心 (列表/配置/运行监控)
│   │   │   ├── knowledge/        # 知识库与图谱 (检索/可视化/法律库)
│   │   │   ├── evidence/         # 证据材料管理
│   │   │   └── admin/            # 系统管理 (用户/部门/智能体/模型)
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
3. **前端统一 Vue 3，禁止引入 React**：语析前端是 Vue 3 + Vite，参考 Plane 的 UI 时**只看设计不看代码**。给 AI 的 Prompt 必须包含约束："使用 Vue 3 + Naive UI + Pinia + Vue Router，使用 `<script setup>` 语法，不要使用 React/JSX/Tailwind"。如果 AI 误生成 React 代码，立即纠正而非适配。
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
| 案件 | 公安办理的具体案件，在平台中作为项目进行管理 |
| 任务 | 案件中需要完成的具体工作项，可分配给民警或智能体 |
| 智能体 | AI 驱动的自动化助手，负责特定专业领域的工作 |
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
| Octop | https://github.com/TencentCloud/Octop | 多智能体管理 + PII 脱敏参考 |
| Plane | https://github.com/makeplane/plane | 项目管理 UI/UX 参考（AGPL，仅设计参考） |
| LangGraph | https://github.com/langchain-ai/langgraph | 智能体编排框架 |
| DeepAgents | https://github.com/langchain-ai/deepagents | 深度智能体框架 |
| AntV G6 | https://github.com/antvis/G6 | 知识图谱可视化 |
| Naive UI | https://github.com/tusen-ai/naive-ui | 前端 UI 组件库 |
