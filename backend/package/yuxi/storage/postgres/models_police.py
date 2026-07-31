"""★ 公安业务数据模型 — 案件、任务、证据、审计等表

所有表复用 models_business 的 Base，遵循 yuxi 的模型规范：
  - Integer 自增主键
  - utc_now_naive 时间戳
  - to_dict() 序列化
  - JSON 字段存储灵活数据
"""

from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from yuxi.storage.postgres.models_business import Base
from yuxi.utils.datetime_utils import format_utc_datetime, utc_now_naive

# ── 案件状态枚举 ──────────────────────────────────────────────
CASE_STATUS = ("draft", "investigation", "arrest", "handling", "prosecution", "closed")
CASE_PHASE = ("research", "arrest", "handling", "prosecution")
TASK_STATUS = ("pending", "in_progress", "review", "completed", "blocked")
TASK_PRIORITY = ("urgent", "high", "medium", "low")
ASSIGNEE_TYPE = ("human", "agent")
EVIDENCE_TYPE = ("transcript", "bank_flow", "screenshot", "audio", "video", "document", "report", "other")


class PoliceCase(Base):
    """★ 案件表"""

    __tablename__ = "police_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_number = Column(String(50), unique=True, nullable=False, index=True)  # 案件编号
    title = Column(String(200), nullable=False)
    case_type = Column(String(50), index=True)  # fraud/theft/drug/etc
    description = Column(Text)
    status = Column(String(20), default="draft", index=True)
    phase = Column(String(30), default="research", index=True)
    priority = Column(String(10), default="medium")
    incident_date = Column(DateTime, nullable=True)
    incident_location = Column(Text, nullable=True)
    total_amount = Column(Float, nullable=True)  # 涉案金额
    victim_info = Column(JSON, default=dict)  # 受害人信息
    suspect_info = Column(JSON, default=list)  # 嫌疑人信息 (动态列表)
    extra = Column(JSON, default=dict)  # 扩展字段 (对应 requirements 的 metadata)
    knowledge_base_id = Column(String(100), nullable=True)
    graph_id = Column(String(100), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    # 关联
    members = relationship("CaseMember", back_populates="case", cascade="all, delete-orphan")
    phases = relationship("CasePhase", back_populates="case", cascade="all, delete-orphan")
    tasks = relationship("PoliceTask", back_populates="case", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "case_number": self.case_number,
            "title": self.title,
            "case_type": self.case_type,
            "description": self.description,
            "status": self.status,
            "phase": self.phase,
            "priority": self.priority,
            "incident_date": format_utc_datetime(self.incident_date),
            "incident_location": self.incident_location,
            "total_amount": self.total_amount,
            "victim_info": self.victim_info,
            "suspect_info": self.suspect_info,
            "extra": self.extra,
            "knowledge_base_id": self.knowledge_base_id,
            "graph_id": self.graph_id,
            "created_by": self.created_by,
            "created_at": format_utc_datetime(self.created_at),
            "updated_at": format_utc_datetime(self.updated_at),
        }


class CaseMember(Base):
    """★ 案件成员表 (多对多)"""

    __tablename__ = "police_case_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("police_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # commander/handler/reviewer/observer
    joined_at = Column(DateTime, default=utc_now_naive)

    case = relationship("PoliceCase", back_populates="members")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "user_id": self.user_id,
            "role": self.role,
            "joined_at": format_utc_datetime(self.joined_at),
        }


class CasePhase(Base):
    """★ 案件阶段记录"""

    __tablename__ = "police_case_phases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("police_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    phase = Column(String(30), nullable=False)
    status = Column(String(20), default="active")  # active/completed/skipped
    started_at = Column(DateTime, default=utc_now_naive)
    completed_at = Column(DateTime, nullable=True)
    summary = Column(Text, nullable=True)
    extra = Column(JSON, default=dict)

    case = relationship("PoliceCase", back_populates="phases")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "phase": self.phase,
            "status": self.status,
            "started_at": format_utc_datetime(self.started_at),
            "completed_at": format_utc_datetime(self.completed_at),
            "summary": self.summary,
            "extra": self.extra,
        }


class PoliceTask(Base):
    """★ 任务表"""

    __tablename__ = "police_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("police_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50), nullable=False, index=True)  # transcript_analysis/fund_analysis/etc
    status = Column(String(20), default="pending", index=True)
    assignee_type = Column(String(10), nullable=False)  # human/agent
    assignee_id = Column(Integer, nullable=True)  # 用户ID或智能体ID
    assignee_name = Column(String(100), nullable=True)  # 冗余字段
    creator_id = Column(Integer, nullable=True)
    creator_type = Column(String(10), default="human")  # human/agent/system
    priority = Column(String(10), default="medium")
    phase = Column(String(30), nullable=True)
    parent_task_id = Column(Integer, ForeignKey("police_tasks.id"), nullable=True)
    dependencies = Column(JSON, default=list)  # 依赖任务ID列表
    attachments = Column(JSON, default=list)
    result = Column(JSON, nullable=True)
    instructions = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    # 证据链防篡改签名 (POLICE_REQUIREMENTS §9.5)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    signed_hash = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    case = relationship("PoliceCase", back_populates="tasks")
    events = relationship("TaskEvent", back_populates="task", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "title": self.title,
            "description": self.description,
            "type": self.type,
            "status": self.status,
            "assignee_type": self.assignee_type,
            "assignee_id": self.assignee_id,
            "assignee_name": self.assignee_name,
            "creator_id": self.creator_id,
            "creator_type": self.creator_type,
            "priority": self.priority,
            "phase": self.phase,
            "parent_task_id": self.parent_task_id,
            "dependencies": self.dependencies or [],
            "attachments": self.attachments or [],
            "result": self.result,
            "instructions": self.instructions,
            "due_date": format_utc_datetime(self.due_date),
            "started_at": format_utc_datetime(self.started_at),
            "completed_at": format_utc_datetime(self.completed_at),
            "reviewed_by": self.reviewed_by,
            "reviewed_at": format_utc_datetime(self.reviewed_at),
            "signed_hash": self.signed_hash,
            "created_at": format_utc_datetime(self.created_at),
            "updated_at": format_utc_datetime(self.updated_at),
        }


class TaskFlowRule(Base):
    """★ 任务流转规则表"""

    __tablename__ = "police_task_flow_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("police_cases.id", ondelete="CASCADE"), nullable=True, index=True)  # NULL=全局
    name = Column(String(100), nullable=False)
    trigger_event = Column(String(50), nullable=False)  # task_completed/file_uploaded/phase_changed
    condition = Column(JSON, nullable=False)  # 触发条件 (JSON规则)
    action = Column(String(50), nullable=False)  # create_task/notify/auto_approve
    target_task_type = Column(String(50), nullable=True)
    target_assignee_type = Column(String(10), nullable=True)
    target_assignee_id = Column(Integer, nullable=True)
    enabled = Column(Integer, default=1)  # 1=启用 0=禁用
    created_at = Column(DateTime, default=utc_now_naive)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "name": self.name,
            "trigger_event": self.trigger_event,
            "condition": self.condition,
            "action": self.action,
            "target_task_type": self.target_task_type,
            "target_assignee_type": self.target_assignee_type,
            "target_assignee_id": self.target_assignee_id,
            "enabled": self.enabled,
            "created_at": format_utc_datetime(self.created_at),
        }


class TaskEvent(Base):
    """★ 任务事件日志 (用于触发流转规则)"""

    __tablename__ = "police_task_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("police_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("police_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # created/assigned/started/completed/blocked/file_uploaded
    event_data = Column(JSON, default=dict)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)

    task = relationship("PoliceTask", back_populates="events")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "event_data": self.event_data,
            "created_by": self.created_by,
            "created_at": format_utc_datetime(self.created_at),
        }


class Evidence(Base):
    """★ 证据材料表"""

    __tablename__ = "police_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("police_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("police_tasks.id"), nullable=True, index=True)
    name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False, index=True)  # transcript/bank_flow/screenshot/audio/video/document/report
    file_path = Column(String(500), nullable=False)  # MinIO 存储路径
    file_hash = Column(String(64), nullable=True)  # SHA-256
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    ocr_text = Column(Text, nullable=True)
    parsed_content = Column(JSON, nullable=True)  # 结构化解析结果
    extra = Column(JSON, default=dict)  # metadata
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    version = Column(Integer, default=1)
    parent_id = Column(Integer, ForeignKey("police_evidence.id"), nullable=True)
    # 证据链防篡改签名 (POLICE_REQUIREMENTS §9.5)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    signed_hash = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "task_id": self.task_id,
            "name": self.name,
            "type": self.type,
            "file_path": self.file_path,
            "file_hash": self.file_hash,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "ocr_text": self.ocr_text,
            "parsed_content": self.parsed_content,
            "extra": self.extra,
            "uploaded_by": self.uploaded_by,
            "version": self.version,
            "parent_id": self.parent_id,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": format_utc_datetime(self.reviewed_at),
            "signed_hash": self.signed_hash,
            "created_at": format_utc_datetime(self.created_at),
        }


class EvidenceLink(Base):
    """★ 证据关联关系 (证据链)"""

    __tablename__ = "police_evidence_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("police_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    source_evidence_id = Column(Integer, ForeignKey("police_evidence.id", ondelete="CASCADE"), nullable=False)
    target_evidence_id = Column(Integer, ForeignKey("police_evidence.id", ondelete="CASCADE"), nullable=False)
    relation_type = Column(String(50), nullable=True)  # derives_from/supports/contradicts
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "case_id": self.case_id,
            "source_evidence_id": self.source_evidence_id,
            "target_evidence_id": self.target_evidence_id,
            "relation_type": self.relation_type,
            "description": self.description,
            "created_at": format_utc_datetime(self.created_at),
        }


class PoliceAgent(Base):
    """★ 数字警员定义表 (融合 StaffDeck 数字员工概念)

    将公安智能体升级为"数字警员"——每位数字警员拥有完整身份档案、
    能力矩阵、工作统计和成长记录，像管理真实员工一样管理 AI。

    与 yuxi 原生的 agents 表互补：此表存储公安专用智能体的业务配置，
    运行时仍走 yuxi 的 LangGraph 引擎。
    """

    __tablename__ = "police_agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50), nullable=False, index=True)  # transcript_analyst/fund_analyst/legal_reviewer/case_orchestrator
    system_prompt = Column(Text, nullable=False)
    model_config = Column(JSON, nullable=False)  # {provider, model, temperature}

    # ── 数字警员档案 (StaffDeck 数字员工概念) ──────────────────
    badge_number = Column(String(20), nullable=True, index=True)  # 数字警员工号 (如 DA-001)
    rank = Column(String(30), nullable=True)  # 警衔: 一级/二级/三级警员
    specialty = Column(String(100), nullable=True)  # 专业领域: 资金追踪/笔录分析/法制审核
    avatar = Column(String(200), nullable=True)  # 头像 URL 或 emoji
    department = Column(String(100), nullable=True)  # 所属部门
    color_theme = Column(String(20), nullable=True)  # 主题色: blue/green/coral/purple/amber

    # ── 能力矩阵 ──────────────────────────────────────────────
    tools = Column(JSON, default=list)
    skills = Column(JSON, default=list)
    knowledge_base_ids = Column(JSON, default=list)
    capabilities = Column(JSON, default=list)  # 能力标签: ["笔录解析","实体识别","OCR"]
    sop_ids = Column(JSON, default=list)  # 关联的 SOP 流程技能 ID

    # ── 工作统计 (由系统聚合，非手动维护) ─────────────────────
    work_stats = Column(JSON, default=dict)  # {tasks_completed, tasks_total, success_rate, cases_handled, feedback_positive, feedback_negative}

    # ── 成长记录 ──────────────────────────────────────────────
    growth_log = Column(JSON, default=list)  # [{date, event, description}] 能力成长事件
    experience_level = Column(Integer, default=1)  # 经验等级 1-5

    icon = Column(String(50), nullable=True)
    status = Column(String(20), default="active")  # active/offline/training
    is_template = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    runs = relationship("PoliceAgentRun", back_populates="agent")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "system_prompt": self.system_prompt,
            "model_config": self.model_config,
            "badge_number": self.badge_number,
            "rank": self.rank,
            "specialty": self.specialty,
            "avatar": self.avatar,
            "department": self.department,
            "color_theme": self.color_theme,
            "tools": self.tools or [],
            "skills": self.skills or [],
            "knowledge_base_ids": self.knowledge_base_ids or [],
            "capabilities": self.capabilities or [],
            "sop_ids": self.sop_ids or [],
            "work_stats": self.work_stats or {},
            "growth_log": self.growth_log or [],
            "experience_level": self.experience_level,
            "icon": self.icon,
            "status": self.status,
            "is_template": self.is_template,
            "created_at": format_utc_datetime(self.created_at),
            "updated_at": format_utc_datetime(self.updated_at),
        }


class PoliceAgentRun(Base):
    """★ 数字警员运行记录 (公安专用)"""

    __tablename__ = "police_agent_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("police_agents.id"), nullable=True, index=True)
    task_id = Column(Integer, ForeignKey("police_tasks.id"), nullable=True, index=True)
    case_id = Column(Integer, ForeignKey("police_cases.id", ondelete="CASCADE"), nullable=True, index=True)
    status = Column(String(20), default="queued", index=True)  # queued/running/completed/failed/cancelled
    input = Column(JSON, nullable=True)
    output = Column(JSON, nullable=True)
    artifacts = Column(JSON, default=list)
    error = Column(Text, nullable=True)
    tokens_used = Column(Integer, default=0)
    duration_ms = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)

    agent = relationship("PoliceAgent", back_populates="runs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "case_id": self.case_id,
            "status": self.status,
            "input": self.input,
            "output": self.output,
            "artifacts": self.artifacts or [],
            "error": self.error,
            "tokens_used": self.tokens_used,
            "duration_ms": self.duration_ms,
            "started_at": format_utc_datetime(self.started_at),
            "completed_at": format_utc_datetime(self.completed_at),
            "created_at": format_utc_datetime(self.created_at),
        }


class PoliceSOP(Base):
    """★ SOP 流程技能定义表 (融合 StaffDeck 状态机驱动 SOP 概念)

    将公安办案流程定义为结构化 SOP（Standard Operating Procedure），
    使用状态机保证复杂流程精确执行。每个 SOP 包含多个步骤节点，
    步骤间有条件转移规则，支持中途插问、上下文恢复。
    """

    __tablename__ = "police_sops"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    agent_type = Column(String(50), nullable=True, index=True)  # 关联的数字警员类型
    category = Column(String(50), nullable=True)  # transcript/fund_analysis/legal_review/evidence_collection
    version = Column(Integer, default=1)  # 版本管理
    # 状态机定义: [{id, name, description, actions, transitions: [{to, condition}]}]
    states = Column(JSON, nullable=False)  # 状态机节点列表
    initial_state = Column(String(50), nullable=False)  # 初始状态ID
    terminal_states = Column(JSON, default=list)  # 终止状态ID列表
    input_schema = Column(JSON, default=dict)  # 输入参数定义
    output_template = Column(Text, nullable=True)  # 产出模板
    is_published = Column(Integer, default=0)  # 0=草稿 1=已发布
    created_at = Column(DateTime, default=utc_now_naive)
    updated_at = Column(DateTime, default=utc_now_naive, onupdate=utc_now_naive)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type,
            "category": self.category,
            "version": self.version,
            "states": self.states or [],
            "initial_state": self.initial_state,
            "terminal_states": self.terminal_states or [],
            "input_schema": self.input_schema or {},
            "output_template": self.output_template,
            "is_published": self.is_published,
            "created_at": format_utc_datetime(self.created_at),
            "updated_at": format_utc_datetime(self.updated_at),
        }


class PoliceAuditLog(Base):
    """★ 审计日志表"""

    __tablename__ = "police_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    user_name = Column(String(100), nullable=True)
    action = Column(String(50), nullable=False)  # create/update/delete/login/assign/approve/reject
    resource_type = Column(String(50), nullable=True)  # case/task/agent/evidence/document
    resource_id = Column(Integer, nullable=True)
    case_id = Column(Integer, nullable=True, index=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now_naive)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "case_id": self.case_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "created_at": format_utc_datetime(self.created_at),
        }
