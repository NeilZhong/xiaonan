# 小南 / Xiaonan 产品需求文档

> 内部代号：智案协  
> 版本：v2.1（基于两大核心重新整理）  
> 日期：2026-08-04  
> 编写：产品需求协同助手  

---

## 文档信息

| 项目 | 内容 |
|---|---|
| 产品名称 | 小南 / Xiaonan |
| 定位 | 公安多智能体协作平台 |
| 核心用户 | 公安民警、案件指挥员、系统管理员 |
| 当前阶段 | Phase 2（案件智能创建 + 笔录分析 + 多智能体协作） |
| 技术底座 | fork 自 xerrors/Yuxi，后端 FastAPI + SQLAlchemy(async) + LangGraph + ARQ；前端 Vue 3.5 + Vite + Ant Design Vue 4.2.6 + Pinia |
| 存储 | PostgreSQL + Redis + MinIO + Milvus + Neo4j |
| LLM | OpenAI 兼容接口，当前模型 `agnes:agnes-2.5-flash`（公安内网自建） |
| 品牌约束 | 前端统一使用「小南 / Xiaonan」，禁止 GitHub 链接/Star 卡片 |
| 代码约束 | 禁止覆盖 yuxi 核心模块；新增后端功能放独立文件 `police_*_repository.py` / `police_*_router.py`；数据库迁移走 `ensure_business_schema()` 运行时 CREATE TABLE IF NOT EXISTS |

---

## 修订记录

| 版本 | 日期 | 修订人 | 修订内容 |
|---|---|---|---|
| v1.0 | 2026-07 | 产品 | 初始需求，覆盖笔录分析、案件创建、工作区、存证 |
| v1.2 | 2026-07 | 产品 | 补充数字警员、证据链、部署方案 |
| v2.0 | 2026-08-04 | 产品协同助手 | 对照 MateClaw 取长补短，补强审批 RBAC、审计查询、产物可观测、运行时控制台、Workflow DSL |
| **v2.1** | **2026-08-04** | **产品协同助手** | **按两大核心重新整理：① 数字警察是一等公民；② 案件驱动 + 编排智能体 + 任务分配 + 用户审核。移除多厂商故障转移，明确角色权限与审核人判定规则。** |

---

## 1. 项目概述

### 1.1 一句话定位

**小南是面向公安场景的多智能体协作平台：数字警察与普通用户一样是一等公民，既可被直接对话，也可被纳入案件执行任务；案件由用户发起后，由案件编排智能体自动拆解任务、推进阶段，用户将任务分配给其他用户或数字警察执行，数字警察的产出必须由指定用户审核后方可进入下一环节。**

### 1.2 两大核心支柱

| 支柱 | 说明 | 对应 MateClaw 概念 |
|---|---|---|
| **支柱一：数字警察是一等公民** | 数字警察不是聊天框附属物，而是与普通用户并列的实体：有唯一身份、可登录可见、可被@、可被分配任务、可被加入案件、可产出成果。 | 数字员工（Digital Employee） |
| **支柱二：案件驱动协作** | 平台的核心工作流以「案件」为中心。用户发起案件 → 编排智能体生成任务板 → 用户/指挥员把任务分给人或数字警察 → 执行者产出 → 审核人确认 → 编排智能体推进阶段。 | Agent Teams / 任务板 / 审批链 |

### 1.3 解决的核心问题

- **重复性劳动重**：笔录阅卷、证据整理、法律文书初稿占用基层民警大量时间。
- **多人协作乱**：一个案件涉及多个警种、多份材料，任务谁来做、做到哪、谁审核不清楚。
- **AI 产出不敢用**：大模型生成的分析/结论没有审核链路、无法追溯、无法担责。
- **过程不可见**：数字警察跑在哪、卡在哪、产出是否被篡改，管理员和指挥员看不到。

### 1.4 产品目标

| 目标 | 验收标准 |
|---|---|
| 数字警察可独立履职 | 可被创建、配置、加入案件、分配任务、产出成果、被用户审核 |
| 案件流程可编排 | 一个案件从创建到结案，任务依赖、阶段推进、审核卡点自动运转 |
| AI 产出可追责 | 每条结论都有「谁产生、谁审核、基于什么证据、何时签名」的完整记录 |
| 平台可管控 | 系统管理员可查看所有运行中数字警察；指挥员可查看自己案件的实时状态 |

---

## 2. 术语表

| 术语 | 定义 |
|---|---|
| **数字警察** | 平台中的一等公民智能体，具有唯一身份、角色卡、能力矩阵，可被执行任务、产出成果、接受审核。对应 MateClaw 的 Digital Employee。 |
| **普通用户** | 公安民警账号，可在平台中发起案件、参与案件、与数字警察对话、审核任务。 |
| **系统管理员** | 平台级管理员，负责数字警察管理、运行时监控、审计查看、全局配置。 |
| **案件（Case）** | 由用户发起的协作单元，如「XX 盗窃案」「XX 诈骗案」。未来可扩展为「事件」（如个人极端事件）。 |
| **案件指挥员（Commander）** | 案件的发起人，拥有该案件的最终管理权：添加成员/数字警察、指定审核人、推进/中止案件。 |
| **案件编排智能体（Orchestrator）** | 负责根据案件信息自动创建任务、维护任务依赖、推进案件阶段、在卡点处暂停等待人工介入。 |
| **任务（Task）** | 案件下的最小执行单元，可分配给单个用户、单个数字警察，或「用户 + 数字警察」组合。 |
| **审核人（Reviewer）** | 对任务产出进行确认的用户。规则见 §9.2。 |
| **任务板（Task Board）** | 案件内所有任务的可视化看板，含状态、负责人、依赖、审核链。 |
| **审核工作台** | 参考 MateClaw 设计的三栏页面：左为待审列表、中为详情与审批链、右为证据与引用。 |
| **运行时控制台** | 系统管理员查看所有运行中数字警察的实时状态、执行流、工具调用，并可进行干预。 |
| **产物（Artifact）** | 任务执行后生成的成果，如分析报告、法律文书、证据摘要、结构化数据。 |
| **密级（Classification）** | 数据/任务/案件的敏感等级，如公开、内部、机密、绝密，驱动审批强度和访问范围。 |
| **证据链哈希** | 对证据内容和元数据分别计算 SHA-256，再合成 `signed_hash`，用于诉讼合规与防篡改。 |

---

## 3. 核心概念：两大支柱详解

### 3.1 支柱一：数字警察是一等公民

#### 3.1.1 与普通用户并列的实体

- 数字警察拥有独立的身份档案，不是某个对话框里的配置项。
- 数字警察可以被@、被搜索、被加入案件成员列表、被分配任务。
- 数字警察执行任务时，其产出（artifact）以该数字警察的 ID 署名。

#### 3.1.2 数字警察的角色卡

每个数字警察必须有一张结构化角色卡，至少包含：

| 字段 | 说明 | 示例 |
|---|---|---|
| `id` | 全局唯一标识 | `agent-forensic-001` |
| `name` | 显示名称 | 「法医助手小南」 |
| `role` | 职责角色 | 「法医鉴定辅助」 |
| `goal` | 目标 | 「基于尸检报告与现场照片，生成死因分析初稿」 |
| `backstory` | 背景/职权边界 | 「具备法医学知识，不做最终司法鉴定结论，只输出辅助分析」 |
| `police_rank` | 警衔/等级 | 「高级技术顾问」 |
| `specialty` | 专业领域 | 「法医病理 / 痕迹分析 / 笔录摘要」 |
| `clearance_level` | 密级授权 | 「机密」 |
| `capability_matrix` | 能力矩阵 | 可使用的工具、可读的数据类型、可产出的文书类型 |
| `system_prompt` | 渲染后的系统提示 | 由角色卡字段自动合成，禁止直接手写大段文本 |

> **EARS 需求**：The system shall generate a digital police officer's `system_prompt` from its structured role card, and shall not allow a raw hand-written system prompt to override the role card without an audit record.

#### 3.1.3 用户与数字警察的对话

- 用户可在「智能体对话」页面选择任意可见的数字警察进行 1 对 1 对话。
- 对话内容按用户-数字警察维度存储，支持后续作为案件材料引用。
- 数字警察在对话中可调用工具，但工具调用三级裁决（ALLOW / NEEDS_APPROVAL / BLOCK）同样生效。

#### 3.1.4 运行时控制台（系统管理员专用）

- 仅系统管理员可见、可进入。
- 展示当前平台所有处于运行态的数字警察：所属案件、当前任务、已运行时长、当前工具调用、子代理树。
- 支持四档干预：友好停止、强制回收、中断指定子代理、批量清扫 stuck 运行。
- 所有干预写审计日志。

> **EARS 需求**：When a system administrator accesses the runtime console, the system shall display only running digital police officers and shall permit intervention actions only after writing an audit record.

---

### 3.2 支柱二：案件驱动协作

#### 3.2.1 案件生命周期

```
发起案件 → 编排智能体拆解任务 → 任务板生成 → 分配执行者 → 执行/协作 → 产出待审 → 审核通过 → 推进阶段 → … → 结案
```

#### 3.2.2 案件发起

- 任何普通用户均可发起案件。
- 发起者自动成为该案件的 **案件指挥员（Commander）**。
- 发起时填写：案件名称、案件类型、案情摘要、初始材料、密级。
- 编排智能体根据案情自动推荐任务模板，指挥员可调整。

#### 3.2.3 案件成员

案件成员包括两类：

| 成员类型 | 说明 | 权限 |
|---|---|---|
| **用户成员** | 被指挥员加入的公安民警 | 按角色：指挥员 / 审核人 / 执行人 / 观察者 |
| **数字警察成员** | 被指挥员加入的数字警察 | 可被分配任务、产出成果、被查看运行状态 |

> **EARS 需求**：When a commander adds a member to a case, the system shall support adding both human users and digital police officers as first-class case members.

#### 3.2.4 任务分配

- 任务可分配给：单个用户、单个数字警察、或「用户 + 数字警察」组合。
- 当任务为「用户 + 数字警察」组合时：数字警察负责生成初稿/分析，用户负责复核、确认或修订。
- 当任务仅分配给数字警察时：由案件指挥员作为默认审核人（除非指挥员另行指定）。
- 当任务仅分配给用户时：按普通任务执行，无需 AI 产出审核流程。

> **EARS 需求**：When a task is assigned to both a user and a digital police officer, the system shall designate the assigned user as the reviewer of the digital police officer's output.

> **EARS 需求**：When a task is assigned only to a digital police officer, the system shall designate the case commander as the default reviewer, unless the commander explicitly assigns another reviewer.

#### 3.2.5 审核卡点

- 数字警察产出的任务，必须经审核人确认后才能标记为完成。
- 审核操作：通过 / 驳回 / 要求修订。
- 驳回时必须填写理由；要求修订时可标注具体段落或字段。
- 审核记录含审核人警号、时间、结论、数字签名，不可删除。

> **EARS 需求**：When a digital police officer completes a task, the system shall transition the task to `pending_review` and shall block downstream tasks until the reviewer approves it.

#### 3.2.6 协作模型对比：小南 vs MateClaw（重要）

MateClaw 的团队协作模型与小南存在**本质差异**，需求设计与实现时不可混淆：

| 维度 | MateClaw | 小南（Xiaonan） |
|---|---|---|
| 任务板归属 | 一个**团队（Team）**：1 个 Lead 数字员工 + 若干成员数字员工 | 一个**案件（Case）**：由真实用户发起 |
| 板上的执行主体 | **全部是数字员工**（agent） | **多个真实用户 + 多个数字警察**，二者都是板上的执行者 |
| 人类的角色 | **板外的指挥/旁观者**：对 Lead 下目标、往板上投任务、旁观进度；人类本身不在板上执行任务 | **板内的案件成员**：可直接认领并执行任务、审核产出 |
| 关系模型 | **1 个人类指挥 ↔ 1 个 agent 团队** 围着一块板 | **多个用户 + 多个 agent ↔ 1 个案件任务板**，多对多协作 |
| 编排者 | Lead 是**团队内**的一个数字员工（Plan-Execute 或 ReAct） | 案件编排智能体是**系统级后台服务**（非板成员），不占成员席位 |
| 多人类协同 | 不直接支持（人类是外部 boss） | **原生支持**（多个民警是板上的 peers，各有 executor/reviewer 角色） |

**小南模型的核心特征**：案件任务板是「多对多协作平面」——多个公安民警（指挥员/执行人/审核人）与多个数字警察（执行人）共同围着同一块板工作。用户既是任务的发起者，也是任务的执行者和审核者；数字警察是并列的执行主体，而非"代替人类团队干活的 agent 群"。

> **EARS 需求**：When a case is created, the system shall treat the case as a multi-party collaboration board where both human users and digital police officers are first-class executors, and shall not restrict task execution to digital police officers only.

> **EARS 需求**：When the orchestrator decomposes a case into tasks, the system shall assign tasks to either human users, digital police officers, or both, according to the case commander's instructions.

---

## 4. 用户角色与权限体系

### 4.1 角色分层

小南的权限模型分两层：**平台层** 和 **案件层**。

#### 4.1.1 平台层角色

| 角色 | 说明 | 典型人员 |
|---|---|---|
| **系统管理员（System Admin）** | 平台级超级管理员 | 科信/技术管理员 |
| **普通用户（User）** | 平台普通民警账号 | 办案民警 |

#### 4.1.2 案件层角色

案件层角色仅在案件范围内生效，由案件指挥员分配：

| 角色 | 说明 | 权限 |
|---|---|---|
| **指挥员（Commander）** | 案件发起人 | 增删成员、分配任务、指定审核人、推进/中止案件、查看全案 |
| **执行人（Executor）** | 被分配任务的用户 | 查看自己被分配的任务、上传材料、提交执行结果 |
| **审核人（Reviewer）** | 被指定为某任务审核人的用户 | 查看待审任务、执行通过/驳回/要求修订 |
| **观察者（Observer）** | 仅查看案件进展的成员 | 只读访问案件看板 |

### 4.2 功能可见性矩阵

| 功能 | 系统管理员 | 指挥员 | 执行人 | 审核人 | 观察者 | 数字警察 |
|---|---|---|---|---|---|---|
| 数字警察管理 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 运行时控制台 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 全局审计台 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 发起案件 | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| 管理案件成员 | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 分配任务 | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 执行任务 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 审核任务产出 | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| 查看案件任务板 | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| 与数字警察对话 | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| 下载产物/证据 | ✅ | ✅ | ✅ | ✅ | ✅ | 按授权 |
| 提交证据/材料 | ✅ | ✅ | ✅ | ✅ | ❌ | 按授权 |

> 说明：系统管理员在功能矩阵中通常拥有全部权限，但 **运行时控制台、全局审计台、数字警察管理** 是系统管理员独占功能，普通用户（包括案件指挥员）不可见。

### 4.3 审核人判定规则（核心规则）

这是任务审核权限的核心算法，必须在代码层严格实现：

```
IF 任务仅分配给用户:
    该任务无 AI 产出审核流程（用户自己负责质量）
ELIF 任务同时分配给用户 + 数字警察:
    审核人 = 该任务指定的用户（若多个用户，取第一个；指挥员可改）
ELIF 任务仅分配给数字警察:
    审核人 = 案件指挥员（默认）
    指挥员可在任务创建后另行指定其他案件成员为审核人
END
```

> **EARS 需求**：When determining the reviewer of a task, the system shall apply the reviewer resolution rules in §4.3, and shall reject any review attempt by a user who is not the designated reviewer.

> **EARS 需求**：If the commander reassigns the reviewer of a task, the system shall write an audit record containing the old reviewer, the new reviewer, the time, and the commander's identity.

---

## 5. 产品架构

### 5.1 架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        小南 / Xiaonan 平台                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │ 智能体对话   │  │ 案件中心     │  │ 审核工作台（参考 MateClaw）│  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                      │                │
│  ┌──────▼────────────────▼──────────────────────▼──────┐         │
│  │              案件编排引擎（LangGraph）                │         │
│  │  - 任务拆解 / 依赖编排 / 阶段推进 / 审核卡点           │         │
│  └──────┬───────────────────────────────────────┬──────┘         │
│         │                                        │                │
│  ┌──────▼──────┐  ┌─────────────┐  ┌───────────▼────────┐       │
│  │ 数字警察引擎 │  │ 证据/存证    │  │ 运行时控制台（admin） │       │
│  │ role/goal/  │  │ 双哈希签名   │  │ 运行态 / 干预 / 审计  │       │
│  │ backstory   │  │ 验证接口     │  │                      │       │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬────────┘       │
│         │                │                      │                │
│  ┌──────▼────────────────▼──────────────────────▼──────┐         │
│  │ 接入层 (FastAPI + RBAC 注解 + 审计中间件 + 密级拦截)   │         │
│  └─────────────────────────────────────────────────────┘         │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────┐       │
│  │  PostgreSQL  │  Redis  │  MinIO  │  Milvus  │  Neo4j  │       │
│  └───────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 关键组件

| 组件 | 职责 | 技术约束 |
|---|---|---|
| 数字警察引擎 | 角色卡渲染、智能体实例化、任务执行、产物生成 | 新增文件 `police_agent_repository.py`、`police_agent_router.py` |
| 案件编排引擎 | 案件生命周期、任务板、依赖调度、审核卡点 | 基于 LangGraph StateGraph，新增 `police_case_repository.py`、`police_case_router.py` |
| 审核工作台 | 三栏式审核页面（参考 MateClaw） | 前端页面，新增 `AuditWorkbench.vue` |
| 运行时控制台 | 系统管理员监控所有运行中数字警察 | 状态落 Redis，新增 `police_runtime_router.py` |
| 审计中间件 | 自动捕获所有资源 CRUD、模型调用、审批行为 | 新增 `police_audit_middleware.py`，覆盖 `ip_address` / `user_agent` |
| 证据存证 | 双哈希 + 签名 + 验证接口 | 新增 `police_evidence_router.py` |

### 5.3 与 MateClaw 的借鉴关系

| MateClaw 能力 | 小南如何借鉴 | 是否采纳 |
|---|---|---|
| 数字员工角色卡 | 映射为「数字警察角色卡」，增加警衔、专业、密级授权等公安字段 | ✅ 采纳 |
| Agent Teams 任务板 | 映射为「案件任务板」，以案件为单位组织；**但小南的板是「多用户 + 多数字警察」多对多协作平面，人类是板内执行者，而非 MateClaw 那种「1 人类指挥 1 个纯 agent 团队」模型**（详见 §3.2.6） | ✅ 采纳（模型有本质差异） |
| 审批链 | 映射为「任务审核工作台」，参考其三栏设计 | ✅ 采纳 |
| 审计事件流 | 补查询接口 + 前端审计台 + 哈希链防篡改 | ✅ 采纳 |
| 运行时控制台 | 系统管理员专用，状态落 Redis | ✅ 采纳 |
| Workflow DSL + Trigger | 作为后续阶段扩展（案件模板可 DSL 化） | ✅ 采纳（P2） |
| 技能自进化 / MCP | 数字警察能力矩阵 + 工作区归属绑定 | ✅ 采纳（P2） |
| 多厂商故障转移 | 公安内网仅自建模型，不适用 | ❌ 不采纳 |

---

## 6. 功能模块

### 6.1 数字警察中心

#### 6.1.1 数字警察列表

- 系统管理员可查看、创建、编辑、停用所有数字警察。
- 普通用户仅能看到自己被授权可见的数字警察（按密级/警种授权）。
- 列表展示：头像、名称、角色、专业领域、状态（在线/离线/运行中/异常）。

#### 6.1.2 数字警察创建

- 必填：name、role、goal、backstory、clearance_level。
- 选填：police_rank、specialty、capability_matrix、avatar。
- 系统自动生成 `system_prompt`，可预览但不可直接编辑；如需覆盖必须走审批并留审计。

#### 6.1.3 数字警察详情

- 展示角色卡全字段。
- 展示历史执行任务列表、审核通过率、平均耗时。
- 展示当前运行状态（仅系统管理员可见完整运行时流）。

> **EARS 需求**：When creating a digital police officer, the system shall require `role`, `goal`, `backstory`, and `clearance_level`, and shall generate the `system_prompt` from these fields.

---

### 6.2 智能体对话

#### 6.2.1 对话入口

- 左侧导航有「智能体对话」入口。
- 用户可选择一个数字警察开始 1 对 1 对话。

#### 6.2.2 对话能力

- 支持文本、图片、文件上传。
- 数字警察可调用的工具受限于其 `capability_matrix`。
- 每次工具调用均写审计日志。
- 用户可将对话中的某条消息「加入案件材料」。

#### 6.2.3 对话与案件的关联

- 对话本身不绑定案件。
- 但对话中的关键信息可手动引用到案件中，作为证据/材料。

---

### 6.3 案件中心

#### 6.3.1 案件列表

- 展示我发起的、我参与的、我可见的案件。
- 支持按状态（进行中/待审/已结案/已中止）、类型、时间筛选。
- 指挥员视角可看到案件的「整体进度条」和「当前卡点」。

#### 6.3.2 发起案件

- 入口：案件中心右上角「发起案件」。
- 表单：案件名称、案件类型（盗窃/诈骗/伤害/自定义）、案情摘要、密级、初始材料上传。
- 提交后，案件编排智能体自动推荐任务模板，指挥员确认或调整。

#### 6.3.3 案件详情页

- 顶部：案件名称、密级标签、指挥员、创建时间、当前阶段。
- Tab 切换：任务板 / 成员 / 材料 / 时间线 / 设置。

---

### 6.4 案件编排智能体

#### 6.4.1 任务拆解

- 接收案件信息后，编排智能体根据案件类型调用对应模板。
- 生成初始任务列表，每个任务含：名称、描述、预计输入、预计输出、建议执行者类型、是否需审核。
- 指挥员可增删改任务、调整依赖关系。

#### 6.4.2 阶段推进

- 案件划分为若干阶段，如：受案 → 初查 → 侦查 → 取证 → 结案。
- 每个阶段由一组任务驱动，当前阶段所有关键任务完成后，编排智能体自动推进到下一阶段。
- 阶段推进前如存在 `in_review` 任务，则暂停并通知审核人。

#### 6.4.3 依赖调度

- 任务支持 `blocked_by` 依赖。
- 依赖任务未完成时，下游任务不可开始。
- 编排智能体负责在依赖满足后自动触发下游任务（对数字警察任务）或通知执行人（对用户任务）。

> **EARS 需求**：When all blocking tasks of a downstream task are completed, the system shall automatically transition the downstream task to `pending_execution` and notify or trigger the assigned executor.

---

### 6.5 任务板

#### 6.5.1 看板视图

- 以案件为维度展示任务。
- 列：待执行 / 执行中 / 待审核 / 已完成 / 已驳回。
- 每个任务卡片展示：任务名、执行者头像（用户或数字警察）、密级标签、截止时间、阻塞标识。

#### 6.5.2 任务分配

- 指挥员可在任务板上拖拽或点击分配执行者。
- 执行者可从「案件成员」中选择，包括用户和数字警察。
- 分配时系统根据 §4.3 自动提示/设定审核人。

#### 6.5.3 任务详情抽屉

- 点击任务卡片弹出抽屉。
- 展示：任务描述、输入材料、执行者、审核人、产出物、时间线、评论。

---

### 6.6 审核工作台（参考 MateClaw 三栏设计）

这是数字警察产出的核心消费页面，设计参考用户提供的 MateClaw 截图。

#### 6.6.1 页面布局

```
┌─────────────────┬─────────────────────────────┬─────────────────┐
│   左栏：待审列表   │       中栏：任务详情与审批链    │   右栏：证据与引用  │
├─────────────────┼─────────────────────────────┼─────────────────┤
│ 按状态/风险筛选   │ 任务元信息                    │ 原始证据片段      │
│ 待审任务卡片      │ AI 产出内容（可高亮）          │ Playbook/规范条款 │
│ 显示任务名/来源   │ 审批链（已完成/进行中/待审）    │ 历史先例         │
│ 执行者/密级/时间  │ 操作按钮：驳回/要求修订/通过    │ 置信度/模型信息   │
└─────────────────┴─────────────────────────────┴─────────────────┘
```

#### 6.6.2 左栏：待审列表

- 展示当前审核人所有待审任务。
- 可按案件、密级、风险等级、等待时长筛选。
- 每个任务显示：来源案件、任务名、执行数字警察、风险标签、等待时长。

#### 6.6.3 中栏：任务详情与审批链

- 顶部：任务名称、所属案件、执行者、密级、产出时间。
- AI 产出区：结构化展示数字警察产出的内容（支持段落级批注）。
- 审批链：以步骤条形式展示：数字警察执行完成 → 当前审核人（我）→ 下一级（如有）→ 完成。
- 底部操作按钮：
  - **驳回**：必须填写驳回理由，任务回到执行者/数字警察。
  - **要求修订**：可勾选具体段落或字段，附修订意见。
  - **通过**：任务完成，解锁下游任务；生成审核签名。

#### 6.6.4 右栏：证据与引用

- **原始证据**：数字警察产出所引用的证据片段，带出处（文件名、页码、段落）。
- **规范条款**：平台内置的法律/业务规范条文，如「刑事诉讼法第 X 条」「笔录制作规范」。
- **历史先例**：相似案件的过往分析或结论，供审核人参考。
- **置信度与模型**：展示该产出的置信度评分、使用模型、耗时。

> **EARS 需求**：When displaying a digital police officer's output for review, the system shall present the output together with its source evidence, applicable rules, historical precedents, confidence score, and model information.

> **EARS 需求**：When a reviewer rejects a task, the system shall require a rejection reason and shall transition the task back to `pending_revision`.

---

### 6.7 运行时控制台（系统管理员专用）

#### 6.7.1 可见性

- **仅系统管理员可见**。
- 普通用户、案件指挥员、审核人均不可见入口。

#### 6.7.2 功能

- 列表视图：所有运行中数字警察的摘要（名称、所属案件、当前任务、运行时长、状态）。
- 详情视图：选中数字警察的实时执行流（打字机式输出、当前节点、工具调用参数、子代理树）。
- 四档干预：
  1. **友好停止**：在下一检查点优雅收尾。
  2. **强制回收**：立即释放运行态，丢弃未完成的流式输出。
  3. **中断指定子代理**：终止某个子任务/子代理。
  4. **批量清扫 stuck 运行**：一键清理超过阈值的卡死运行。
- stuck 判定：空闲无事件 >150s（非工具调用中）/ 工具调用中 >600s / 硬上限 1800s。

> **EARS 需求**：When a system administrator triggers an intervention in the runtime console, the system shall write an audit record containing the intervention type, target digital police officer, target task, time, and administrator identity.

---

### 6.8 审计台

#### 6.8.1 可见性

- **全局审计台：系统管理员独占**。
- **案件审计视图：案件指挥员可在案件内查看本案件审计记录**。
- 普通用户不可见审计入口。

#### 6.8.2 审计内容

- 所有资源 CRUD（案件、任务、成员、数字警察、证据）。
- 所有模型调用（prompt、completion、token、工具入参出参）。
- 所有审批行为（通过/驳回/要求修订/改派审核人）。
- 运行时控制台的所有干预操作。
- 自动捕获 `ip_address` / `user_agent`。

#### 6.8.3 防篡改

- 审计记录形成哈希链：每条记录含前一条记录的哈希值。
- 提供审计校验接口，可验证某条记录是否被篡改。

> **EARS 需求**：When writing an audit record, the system shall capture the user's IP address and user agent, and shall link the record into a tamper-evident hash chain.

---

### 6.9 证据与存证

#### 6.9.1 证据上传

- 案件成员可在案件内上传证据/材料。
- 上传后自动计算双哈希（内容哈希 + 元数据哈希），合成 `signed_hash`。

#### 6.9.2 证据引用

- 数字警察产出中引用的证据，必须保留证据 ID 与引用位置。
- 审核工作台右栏展示引用证据片段。

#### 6.9.3 证据验证

- 提供 `GET /evidence/{id}/verify` 接口，重算哈希并与 `signed_hash` 比对。
- 返回校验结果、原始时间戳、签名者警号。

---

## 7. 数据模型

### 7.1 实体清单

| 实体 | 说明 | v2.1 变化 |
|---|---|---|
| `police_users` | 普通用户/民警 | 增加 `platform_role`（system_admin / user） |
| `police_agents` | 数字警察 | 增加 `role`/`goal`/`backstory`/`clearance_level` 等结构化字段 |
| `police_cases` | 案件 | 新增核心实体 |
| `police_case_members` | 案件成员（用户或数字警察） | 新增核心实体 |
| `police_tasks` | 任务 | 增加 `case_id`/`assignee_type`/`assignee_id`/`reviewer_id`/`require_approval`/`blocked_by` |
| `police_task_outputs` | 任务产出 | 新增，关联 source_task_id |
| `police_artifacts` | 产物（结构化报告/文书） | 新增，含版本、状态、签名 |
| `police_evidence` | 证据/材料 | 保留双哈希签名 |
| `police_audit_logs` | 审计日志 | 增加哈希链字段，补查询能力 |
| `police_runtime_sessions` | 运行时会话 | 新增，落 Redis 或 PG |
| `police_workflows` | 案件模板/Workflow DSL | 新增（P2） |

### 7.2 核心表结构

```sql
-- 7.2.1 用户表（增量字段）
CREATE TABLE IF NOT EXISTS police_users (
    id              UUID PRIMARY KEY,
    police_id       VARCHAR(32) UNIQUE NOT NULL,   -- 警号
    name            VARCHAR(128) NOT NULL,
    platform_role   VARCHAR(32) DEFAULT 'user',    -- system_admin / user
    department      VARCHAR(128),
    clearance_level VARCHAR(32) DEFAULT '内部',
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 7.2.2 数字警察表（角色卡结构化）
CREATE TABLE IF NOT EXISTS police_agents (
    id                UUID PRIMARY KEY,
    agent_code        VARCHAR(64) UNIQUE NOT NULL,   -- 唯一智能体编号
    name              VARCHAR(128) NOT NULL,
    avatar_url        TEXT,
    role              VARCHAR(256) NOT NULL,         -- 职责角色
    goal              TEXT NOT NULL,                  -- 目标
    backstory         TEXT NOT NULL,                  -- 背景/职权边界
    police_rank       VARCHAR(64),                    -- 警衔/等级
    specialty         VARCHAR(256),                   -- 专业领域
    clearance_level   VARCHAR(32) DEFAULT '内部',      -- 密级授权
    capability_matrix JSONB DEFAULT '{}',             -- 能力矩阵
    system_prompt     TEXT,                           -- 由角色卡渲染
    status            VARCHAR(32) DEFAULT 'offline',  -- offline/online/running/error
    created_by        UUID REFERENCES police_users(id),
    created_at        TIMESTAMP DEFAULT NOW()
);

-- 7.2.3 案件表
CREATE TABLE IF NOT EXISTS police_cases (
    id                UUID PRIMARY KEY,
    case_no           VARCHAR(128) UNIQUE NOT NULL,   -- 案件编号
    title             VARCHAR(512) NOT NULL,
    case_type         VARCHAR(64) NOT NULL,           -- 盗窃/诈骗/伤害/自定义/事件
    summary           TEXT,
    commander_id      UUID NOT NULL REFERENCES police_users(id),
    current_stage     VARCHAR(64) DEFAULT '受案',
    status            VARCHAR(32) DEFAULT 'active',   -- active/paused/closed/aborted
    classification    VARCHAR(32) DEFAULT '内部',      -- 密级
    workflow_id       UUID,                            -- 关联模板
    created_at        TIMESTAMP DEFAULT NOW(),
    updated_at        TIMESTAMP DEFAULT NOW()
);

-- 7.2.4 案件成员表
CREATE TABLE IF NOT EXISTS police_case_members (
    id          UUID PRIMARY KEY,
    case_id     UUID NOT NULL REFERENCES police_cases(id) ON DELETE CASCADE,
    member_type VARCHAR(16) NOT NULL,                  -- 'user' / 'agent'
    member_id   UUID NOT NULL,                         -- user_id 或 agent_id
    case_role   VARCHAR(32) DEFAULT 'observer',        -- commander/executor/reviewer/observer
    joined_at   TIMESTAMP DEFAULT NOW(),
    UNIQUE(case_id, member_type, member_id)
);

-- 7.2.5 任务表
CREATE TABLE IF NOT EXISTS police_tasks (
    id                  UUID PRIMARY KEY,
    case_id             UUID NOT NULL REFERENCES police_cases(id) ON DELETE CASCADE,
    name                VARCHAR(512) NOT NULL,
    description         TEXT,
    stage               VARCHAR(64),                   -- 所属阶段
    assignee_type       VARCHAR(16),                   -- 'user' / 'agent' / 'both'
    assignee_user_id    UUID REFERENCES police_users(id),
    assignee_agent_id   UUID REFERENCES police_agents(id),
    reviewer_id         UUID REFERENCES police_users(id),
    status              VARCHAR(32) DEFAULT 'pending', -- pending/executing/pending_review/rejected/completed/revision
    require_approval    BOOLEAN DEFAULT TRUE,          -- 数字警察产出是否需审核
    blocked_by          UUID[] DEFAULT '{}',           -- 依赖任务ID数组
    priority            VARCHAR(16) DEFAULT 'normal',
    due_at              TIMESTAMP,
    output_id           UUID,                          -- 关联 task_outputs
    approved_by         UUID REFERENCES police_users(id),
    approved_at         TIMESTAMP,
    approval_signature  TEXT,                          -- 审核人数字签名
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- 7.2.6 任务产出表
CREATE TABLE IF NOT EXISTS police_task_outputs (
    id              UUID PRIMARY KEY,
    task_id         UUID NOT NULL REFERENCES police_tasks(id) ON DELETE CASCADE,
    agent_id        UUID REFERENCES police_agents(id),
    content_type    VARCHAR(64),                       -- json/markdown/docx/html
    content         JSONB,                             -- 结构化内容
    raw_text        TEXT,                              -- 原始文本
    evidence_refs   JSONB DEFAULT '[]',                -- 引用的证据ID与位置
    confidence      FLOAT,
    model_name      VARCHAR(128),
    token_used      INT,
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    status          VARCHAR(32) DEFAULT 'draft',       -- draft/final/rejected
    version         INT DEFAULT 1
);

-- 7.2.7 产物表（更正式的归档产物）
CREATE TABLE IF NOT EXISTS police_artifacts (
    id              UUID PRIMARY KEY,
    case_id         UUID NOT NULL REFERENCES police_cases(id) ON DELETE CASCADE,
    task_id         UUID REFERENCES police_tasks(id),
    name            VARCHAR(512) NOT NULL,
    file_type       VARCHAR(64),
    minio_path      VARCHAR(1024),
    content_hash    VARCHAR(128),
    metadata_hash   VARCHAR(128),
    signed_hash     VARCHAR(256),
    signed_by       UUID REFERENCES police_users(id),
    signed_at       TIMESTAMP,
    status          VARCHAR(32) DEFAULT 'draft',
    version         INT DEFAULT 1,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 7.2.8 证据表（沿用 v1.x 双哈希）
CREATE TABLE IF NOT EXISTS police_evidence (
    id              UUID PRIMARY KEY,
    case_id         UUID NOT NULL REFERENCES police_cases(id) ON DELETE CASCADE,
    uploader_id     UUID NOT NULL REFERENCES police_users(id),
    file_name       VARCHAR(512),
    file_type       VARCHAR(64),
    minio_path      VARCHAR(1024),
    content_hash    VARCHAR(128),
    metadata_hash   VARCHAR(128),
    signed_hash     VARCHAR(256),
    signed_by       UUID REFERENCES police_users(id),
    signed_at       TIMESTAMP,
    classification  VARCHAR(32) DEFAULT '内部',
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 7.2.9 审计日志表（v2.1 哈希链）
CREATE TABLE IF NOT EXISTS police_audit_logs (
    id              UUID PRIMARY KEY,
    action          VARCHAR(64) NOT NULL,
    resource_type   VARCHAR(64) NOT NULL,              -- case/task/agent/evidence/...
    resource_id     UUID,
    actor_type      VARCHAR(16) NOT NULL,              -- user/agent/system
    actor_id        UUID NOT NULL,
    payload         JSONB,
    ip_address      INET,
    user_agent      TEXT,
    prev_hash       VARCHAR(256),                      -- 前一条审计记录哈希
    record_hash     VARCHAR(256) NOT NULL,             -- 本记录哈希
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 7.2.10 运行时会话表（落 PG，热点查 Redis）
CREATE TABLE IF NOT EXISTS police_runtime_sessions (
    id              UUID PRIMARY KEY,
    agent_id        UUID NOT NULL REFERENCES police_agents(id),
    case_id         UUID REFERENCES police_cases(id),
    task_id         UUID REFERENCES police_tasks(id),
    status          VARCHAR(32) DEFAULT 'running',     -- running/paused/stopped/error/stuck
    current_node    VARCHAR(256),
    current_tool    VARCHAR(256),
    started_at      TIMESTAMP DEFAULT NOW(),
    last_event_at   TIMESTAMP DEFAULT NOW(),
    events          JSONB DEFAULT '[]'
);
```

### 7.3 实体关系

```
police_users (1) ──< police_cases (commander_id)
police_cases (1) ──< police_case_members (N) >── police_users / police_agents
police_cases (1) ──< police_tasks (N) >── police_users (assignee/reviewer) / police_agents
police_tasks (1) ──< police_task_outputs (N) >── police_agents
police_tasks (1) ──< police_artifacts (N)
police_cases (1) ──< police_evidence (N)
all ──< police_audit_logs
police_agents (1) ──< police_runtime_sessions (N)
```

---

## 8. 数字警员详解

### 8.1 数字警员与普通用户的并列关系

- 在 `police_case_members` 中，`member_type` 区分 `user` 和 `agent`，但二者都是案件的合法成员。
- 在任务分配时，`assignee_type` 支持 `user`、`agent`、`both`。
- 数字警察没有密码，不通过常规登录接口；其身份通过 API Key / 内部服务身份认证。

### 8.2 角色卡渲染为 system_prompt

系统不允许直接写死 `system_prompt`，必须从角色卡渲染：

```jinja2
你是 {{ name }}，一名 {{ police_rank }}，专业领域为 {{ specialty }}。
你的职责角色是：{{ role }}。
你的目标是：{{ goal }}。
你的背景与职权边界：{{ backstory }}。
你的能力矩阵：{{ capability_matrix }}。
你的密级授权为 {{ clearance_level }}，不得访问高于该密级的数据。
```

> **EARS 需求**：When updating a digital police officer's role card, the system shall regenerate the `system_prompt` and shall version the previous role card for audit purposes.

### 8.3 数字警察与案件编排智能体的区别

| | 数字警察 | 案件编排智能体 |
|---|---|---|
| 职责 | 执行具体任务，产出分析/文书 | 拆解任务、维护依赖、推进阶段、处理卡点 |
| 是否可见为一等公民 | ✅ 是 | ❌ 否（系统级后台服务） |
| 是否可被加入案件 | ✅ 是 | ❌ 否 |
| 是否可被用户直接对话 | ✅ 是 | ❌ 否 |

### 8.4 数字警察生命周期状态

- `offline`：未启用或已停用。
- `online`：可用，未被分配任务。
- `running`：正在执行任务。
- `stuck`：运行超过阈值无响应。
- `error`：运行异常。

---

## 9. 案件与任务协作

### 9.1 案件创建流程

1. 用户点击「发起案件」。
2. 填写案件基础信息并上传初始材料。
3. 系统创建案件，发起人自动成为指挥员。
4. 案件编排智能体读取案情，推荐任务模板。
5. 指挥员确认/调整任务列表与依赖。
6. 任务板生成，案件进入「受案」阶段。

### 9.2 审核人判定规则（再次强调，必须代码层实现）

```
IF assignee_type == 'user':
    reviewer_id = NULL
    require_approval = FALSE
ELIF assignee_type == 'both':
    reviewer_id = assignee_user_id（第一个用户；指挥员可改）
    require_approval = TRUE
ELIF assignee_type == 'agent':
    reviewer_id = commander_id（默认）
    指挥员可另行指定 reviewer_id
    require_approval = TRUE
END
```

> **EARS 需求**：When the commander assigns a task, the system shall automatically resolve the reviewer according to the above rules and shall allow the commander to override the reviewer before the task starts.

### 9.3 任务状态机

```
              ┌─────────────────────────────────────┐
              │                                     ▼
pending ──▶ executing ──▶ pending_review ──▶ completed
              │                │                  ▲
              ▼                ▼                  │
           rejected  ◀──  revision ───────────────┘
```

| 状态 | 说明 |
|---|---|
| `pending` | 等待依赖满足或等待执行者开始 |
| `executing` | 执行中（用户处理 / 数字警察运行） |
| `pending_review` | 数字警察产出完成，等待审核 |
| `revision` | 被驳回后进入修订状态 |
| `rejected` | 最终被驳回，不再继续 |
| `completed` | 审核通过，可解锁下游任务 |

### 9.4 数字警察任务执行流程

1. 依赖满足后，任务进入 `executing`。
2. 系统为数字警察创建运行时会话。
3. 数字警察读取任务输入、相关证据、角色卡。
4. 数字警察调用 LLM 与工具，生成结构化产出。
5. 产出写入 `police_task_outputs`，任务进入 `pending_review`。
6. 系统通知审核人。
7. 审核人在审核工作台处理。
8. 通过后，任务 `completed`，编排智能体检查阶段推进条件。

### 9.5 阶段推进规则

- 每个阶段有一组「关键任务」。
- 当该阶段所有关键任务均 `completed` 后，编排智能体自动推进到下一阶段。
- 推进时生成阶段小结，写入案件时间线。
- 如推进前发现未审核的关键任务，暂停并高亮提示指挥员。

---

## 10. API 设计

### 10.1 API 设计原则

- 遵循 RESTful 风格。
- 所有接口返回统一包装：`{ code, message, data }`。
- 所有写操作强制写审计日志。
- 权限校验在路由层完成，失败返回 403。

### 10.2 数字警察 API

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/v1/agents` | 列表（按可见性过滤） | 登录用户 |
| POST | `/api/v1/agents` | 创建数字警察 | 系统管理员 |
| GET | `/api/v1/agents/{id}` | 详情（含角色卡全字段） | 登录用户 |
| PUT | `/api/v1/agents/{id}` | 编辑角色卡 | 系统管理员 |
| DELETE | `/api/v1/agents/{id}` | 停用 | 系统管理员 |
| POST | `/api/v1/agents/{id}/chat` | 与数字警察对话 | 登录用户 |
| GET | `/api/v1/agents/{id}/runs` | 历史运行记录 | 系统管理员 |

### 10.3 案件 API

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| POST | `/api/v1/cases` | 发起案件 | 登录用户 |
| GET | `/api/v1/cases` | 我的案件列表 | 登录用户 |
| GET | `/api/v1/cases/{id}` | 案件详情 | 案件成员 / 系统管理员 |
| PUT | `/api/v1/cases/{id}` | 修改案件基础信息 | 指挥员 / 系统管理员 |
| POST | `/api/v1/cases/{id}/members` | 添加成员（用户或数字警察） | 指挥员 / 系统管理员 |
| DELETE | `/api/v1/cases/{id}/members/{mid}` | 移除成员 | 指挥员 / 系统管理员 |
| POST | `/api/v1/cases/{id}/advance` | 手动推进阶段 | 指挥员 / 系统管理员 |
| POST | `/api/v1/cases/{id}/abort` | 中止案件 | 指挥员 / 系统管理员 |

### 10.4 任务 API

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/v1/cases/{id}/tasks` | 案件任务板 | 案件成员 |
| POST | `/api/v1/cases/{id}/tasks` | 创建任务 | 指挥员 / 系统管理员 |
| PUT | `/api/v1/tasks/{tid}` | 编辑任务 | 指挥员 / 系统管理员 |
| POST | `/api/v1/tasks/{tid}/assign` | 分配执行者 | 指挥员 / 系统管理员 |
| POST | `/api/v1/tasks/{tid}/start` | 开始执行 | 执行者 |
| POST | `/api/v1/tasks/{tid}/submit` | 提交产出（用户） | 执行者 |
| POST | `/api/v1/tasks/{tid}/review` | 审核任务 | 审核人 / 指挥员 / 系统管理员 |
| POST | `/api/v1/tasks/{tid}/reclaim` | 强制回收（运行时控制台调用） | 系统管理员 |

> **重点**：`/tasks/{tid}/review` 必须严格校验调用者是否为该任务的 `reviewer_id`，否则 403。这是 P0 安全修复。

### 10.5 审核工作台 API

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/v1/reviews/pending` | 当前用户的待审列表 | 登录用户 |
| GET | `/api/v1/reviews/{task_id}` | 某任务的审核详情（含产出、证据、引用） | 审核人 / 指挥员 / 系统管理员 |
| POST | `/api/v1/reviews/{task_id}/approve` | 通过 | 审核人 / 指挥员 / 系统管理员 |
| POST | `/api/v1/reviews/{task_id}/reject` | 驳回 | 审核人 / 指挥员 / 系统管理员 |
| POST | `/api/v1/reviews/{task_id}/revise` | 要求修订 | 审核人 / 指挥员 / 系统管理员 |

### 10.6 运行时控制台 API（系统管理员专用）

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/v1/admin/runtime/sessions` | 所有运行中会话 | 系统管理员 |
| GET | `/api/v1/admin/runtime/sessions/{id}` | 会话详情 | 系统管理员 |
| POST | `/api/v1/admin/runtime/sessions/{id}/stop` | 友好停止 | 系统管理员 |
| POST | `/api/v1/admin/runtime/sessions/{id}/reclaim` | 强制回收 | 系统管理员 |
| POST | `/api/v1/admin/runtime/sessions/{id}/interrupt` | 中断子代理 | 系统管理员 |
| POST | `/api/v1/admin/runtime/sweep-stuck` | 批量清扫 stuck | 系统管理员 |

### 10.7 审计 API

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/v1/admin/audit/logs` | 全局审计查询 | 系统管理员 |
| GET | `/api/v1/cases/{id}/audit/logs` | 案件审计视图 | 指挥员 / 系统管理员 |
| POST | `/api/v1/admin/audit/verify` | 审计哈希链校验 | 系统管理员 |

### 10.8 证据 API

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| POST | `/api/v1/cases/{id}/evidence` | 上传证据 | 案件成员 |
| GET | `/api/v1/evidence/{id}` | 证据详情 | 案件成员 / 系统管理员 |
| GET | `/api/v1/evidence/{id}/verify` | 验证证据哈希 | 案件成员 / 系统管理员 |
| GET | `/api/v1/evidence/{id}/download` | 下载证据 | 案件成员 / 系统管理员 |

---

## 11. 前端规范

### 11.1 页面清单

| 页面 | 路由 | 说明 |
|---|---|---|
| 智能体对话 | `/agents/chat` | 选择数字警察进行 1 对 1 对话 |
| 数字警察管理 | `/admin/agents` | 系统管理员管理角色卡 |
| 案件中心 | `/cases` | 案件列表 |
| 案件详情 | `/cases/{id}` | 任务板 / 成员 / 材料 / 时间线 |
| 审核工作台 | `/reviews` | 参考 MateClaw 三栏设计 |
| 运行时控制台 | `/admin/runtime` | 系统管理员专用 |
| 审计台 | `/admin/audit` | 系统管理员专用 |

### 11.2 审核工作台交互设计

参考用户提供的 MateClaw 截图，设计为三栏布局：

- **左栏**：待审列表
  - 顶部标签切换：全部 / 高风险 / 待审 / 已驳回
  - 列表项：任务名、来源案件、执行数字警察、风险标签、等待时长
  - 选中态高亮

- **中栏**：任务详情与审批链
  - 顶部：案件名 + 任务名 + 密级标签
  - AI 产出区：结构化展示，支持段落高亮与批注
  - 审批链：步骤条，显示「数字警察执行完成 → 当前审核人 → 下一级 → 完成」
  - 底部：驳回 / 要求修订 / 通过 三个主按钮

- **右栏**：证据与引用
  - 原始证据片段（带出处）
  - 规范条款
  - 历史先例
  - 置信度、模型、耗时

### 11.3 品牌与组件

- 品牌统一使用「小南 / Xiaonan」。
- 组件库：Ant Design Vue 4.2.6。
- 禁止出现 GitHub 链接/Star 卡片。
- 密级标签使用统一色板：公开（绿）、内部（蓝）、机密（橙）、绝密（红）。

---

## 12. 安全合规

### 12.1 权限体系

- 平台层角色：`system_admin` / `user`。
- 案件层角色：`commander` / `executor` / `reviewer` / `observer`。
- 运行时控制台、全局审计台、数字警察管理 **仅 system_admin 可见**。
- 案件指挥员在自己案件中拥有最高权限，但不可跨案。

### 12.2 审批越权修复（P0）

- `/tasks/{tid}/review` 必须校验调用者 == `reviewer_id`。
- 若调用者为 `system_admin`，允许审核但写特殊审计标记。
- 若调用者为 `commander` 且 `reviewer_id` 为空，允许指定自己为审核人后审核。

### 12.3 密级控制

- 所有案件、任务、证据、数字警察均有 `classification`。
- 用户只能访问不高于自身 `clearance_level` 的数据。
- 数字警察只能访问不高于其 `clearance_level` 的数据。
- 机密级以上任务强制多级会签（可配置）。

### 12.4 审计合规

- 审计中间件覆盖所有资源 CRUD、模型调用、审批行为、运行时干预。
- 自动捕获 `ip_address` / `user_agent`。
- 审计记录哈希链防篡改。
- 提供审计查询接口与校验接口。

### 12.5 证据链哈希

- 证据上传时计算 `content_hash`（文件内容）和 `metadata_hash`（文件名、大小、上传人、时间）。
- 合成 `signed_hash`，由上传人数字签名。
- 提供 `GET /evidence/{id}/verify` 重算校验。

### 12.6 智能体安全

- 工具调用三级裁决：ALLOW / NEEDS_APPROVAL / BLOCK。
- BLOCK 级工具不可被审批覆盖。
- ACP/MCP 按工作区归属绑定，禁止跨工作区调用敏感内部系统。
- 数字警察的 `capability_matrix` 限制其可调用的工具范围。

---

## 13. 部署方案

### 13.1 私有化部署

- 部署于公安内网。
- Docker 服务名使用 `api`。
- 前端 Vite 为本地进程，重启使用 `npm run dev`。
- 模型使用内网自建 `agnes:agnes-2.5-flash`，无多厂商故障转移。

### 13.2 存储用法

- MinIO：`get_minio_client().aupload_file` / `adownload_file`。
- 证据、产物、运行时事件均落 MinIO。
- 审计哈希链、证据哈希落 PostgreSQL。
- 运行时会话热点数据落 Redis，持久化快照落 PostgreSQL。

### 13.3 数据库迁移

- 使用 `ensure_business_schema()` 运行时 `CREATE TABLE IF NOT EXISTS`。
- 无 Alembic 迁移。
- 新增表通过独立的 `police_*` 文件定义，不修改 yuxi 核心表。

---

## 14. 开发计划与里程碑

### 14.1 阶段划分

| 阶段 | 内容 | 重点 |
|---|---|---|
| **Phase 1（已完成）** | 基础工作区、文件上传、MinIO 对接 | 底座就绪 |
| **Phase 2（进行中）** | 数字警察角色卡、案件中心、任务板、审核工作台、运行时控制台 | **P0 审批越权修复 + 审计查询/前端/防篡改** |
| **Phase 3（规划中）** | 笔录分析智能体、案件智能创建、产物自动落盘、证据验证 | P1 依赖编排消费 + 产物结构化 |
| **Phase 4（规划中）** | Workflow DSL、技能自进化、MCP 工作区归属、知识引用溯源 | P2 扩展能力 |

### 14.2 P0/P1/P2 需求清单

| 优先级 | 事项 | 归属角色 | 说明 |
|---|---|---|---|
| **P0** | 用户 platform_role + 系统管理员权限体系 | 后端 | 区分 system_admin 与普通用户 |
| **P0** | 案件成员模型（支持用户 + 数字警察） | 后端 | 案件层角色：commander/executor/reviewer/observer |
| **P0** | 任务审核人判定规则代码实现 | 后端 | §4.3 与 §9.2 规则 |
| **P0** | 审批端点补 reviewer RBAC 校验 | 后端 | `/tasks/{tid}/review` 严格校验 |
| **P0** | 审计中间件自动捕获 ip/ua + 查询接口 | 后端+前端 | 替换当前手写调用点 |
| **P0** | 审计哈希链 | 后端 | 每条记录含前一条哈希 |
| **P0** | 运行时控制台仅 system_admin 可见 | 后端+前端 | 接口与入口均需鉴权 |
| **P1** | 案件编排智能体自动拆解任务 | AI 智能体专家 | 基于案情推荐任务模板 |
| **P1** | 任务依赖 `blocked_by` 真正消费 | 后端 | 阻塞校验 + 拓扑触发 |
| **P1** | 审核工作台三栏页面 | 前端 | 参考 MateClaw 设计 |
| **P1** | 产物结构化报告 + 版本/状态/签名 | 后端+前端 | 生成 Office/PDF 导出 |
| **P1** | 证据验证端点 `GET /evidence/{id}/verify` | 后端 | 闭环 v1.x 只写未读 |
| **P2** | 数字警察角色卡结构化字段 + 前端表单 | 后端+前端 | role/goal/backstory 独立 |
| **P2** | Workflow DSL + 案件模板 | 后端 | 可发布/可重放的案件流程 |
| **P2** | 技能 manifest 解析 + MCP 工作区归属 | 后端 | 数字警察能力扩展 |
| **P2** | 知识引用溯源（LLM Wiki） | AI 智能体专家 | 带 `[[链接]]` 的可点引用 |

---

## 15. 附录

### 15.1 参考项目

- **Yuxi**（xerrors/Yuxi）：小南的技术底座，提供 FastAPI/LangGraph/工作区基础。
- **MateClaw（太一）**（mateaix/mateclaw，Apache 2.0）：团队多智能体 harness，Java/Spring Boot。经源码级对照，其在数字员工角色卡、任务板、审批链、运行时控制台、审计事件流上成熟，作为理念参考；其缺失的密级/涉密分级、审计防篡改、内网私有化由小南公安特化补齐。

### 15.2 关键文件命名约定

- 新增后端功能：`police_<module>_repository.py`、`police_<module>_router.py`、`police_<module>_service.py`
- 新增前端页面：`Police<Page>View.vue`
- 新增数据表：`police_<name>`

### 15.3 审核人规则速查表

| 任务分配 | 默认审核人 | 可改派？ |
|---|---|---|
| 仅用户 | 无（无 AI 产出） | 不适用 |
| 用户 + 数字警察 | 该用户 | 指挥员可改 |
| 仅数字警察 | 案件指挥员 | 指挥员可改 |

---

*本文档为 Xiaonan v2.1 基线需求，后续版本迭代以此为基础。*
