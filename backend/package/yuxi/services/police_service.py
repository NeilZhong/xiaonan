"""★ 公安业务服务层 — 案件 + 任务流转引擎 + 数字警员"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any

from yuxi.repositories.police_agent_repository import police_agent_repository
from yuxi.repositories.police_workspace_repository import police_workspace_repository
from yuxi.repositories.case_repository import case_repository
from yuxi.repositories.evidence_repository import evidence_repository
from yuxi.repositories.task_repository import task_repository
from yuxi.storage.minio.client import get_minio_client
from yuxi.storage.postgres.models_police import Evidence
from yuxi.utils.datetime_utils import utc_now_naive
from yuxi.utils import logger


class PoliceCaseService:
    """案件服务 — 编排案件创建、阶段切换、统计等业务逻辑"""

    async def create_case(self, data: dict[str, Any], creator_id: int) -> dict[str, Any]:
        """创建案件 + 自动添加创建者为 commander"""
        case = await case_repository.create(data)
        # 创建者为案件指挥员
        await case_repository.add_member(case.id, creator_id, "commander")
        # 创建初始阶段记录
        initial_phase = case.phase or "research"
        await case_repository.update_phase(case.id, initial_phase)
        # ★ 自动创建案件独立工作区 (证据/材料/产物统一存储命名空间)
        try:
            await police_workspace_service.get_or_create(case.id, case_number=case.case_number)
        except Exception as e:
            logger.warning(f"Auto-create workspace failed for case {case.id}: {e}")
        # 记录审计日志
        await self._audit(action="create", resource_type="case", resource_id=case.id, case_id=case.id, user_id=creator_id, details={"title": case.title})
        return case.to_dict()

    async def get_case_detail(self, case_id: int) -> dict[str, Any] | None:
        case = await case_repository.get_by_id(case_id)
        if not case:
            return None
        result = case.to_dict()
        members = await case_repository.list_members(case_id)
        result["members"] = [m.to_dict() for m in members]
        phases = await case_repository.list_phases(case_id)
        result["phases"] = [p.to_dict() for p in phases]
        return result

    async def list_cases(self, **kwargs) -> dict[str, Any]:
        cases, total = await case_repository.list_cases(**kwargs)
        return {
            "items": [c.to_dict() for c in cases],
            "total": total,
            "page": (kwargs.get("skip", 0) // kwargs.get("limit", 20)) + 1,
            "page_size": kwargs.get("limit", 20),
        }

    async def update_case(self, case_id: int, data: dict[str, Any], user_id: int) -> dict[str, Any] | None:
        case = await case_repository.update(case_id, data)
        if case:
            await self._audit(action="update", resource_type="case", resource_id=case_id, case_id=case_id, user_id=user_id, details=data)
        return case.to_dict() if case else None

    async def delete_case(self, case_id: int, user_id: int) -> bool:
        ok = await case_repository.delete(case_id)
        if ok:
            await self._audit(action="delete", resource_type="case", resource_id=case_id, case_id=case_id, user_id=user_id)
        return ok

    async def update_phase(self, case_id: int, phase: str, user_id: int) -> dict[str, Any] | None:
        case = await case_repository.update_phase(case_id, phase)
        if case:
            await self._audit(action="phase_change", resource_type="case", resource_id=case_id, case_id=case_id, user_id=user_id, details={"phase": phase})
        return case.to_dict() if case else None

    async def add_member(self, case_id: int, user_id: int, role: str, operator_id: int) -> dict[str, Any]:
        member = await case_repository.add_member(case_id, user_id, role)
        await self._audit(action="add_member", resource_type="case", resource_id=case_id, case_id=case_id, user_id=operator_id, details={"member_user_id": user_id, "role": role})
        return member.to_dict()

    async def case_timeline(self, case_id: int) -> list[dict[str, Any]]:
        """案件时间线 — 合并任务事件和阶段记录"""
        tasks, _ = await task_repository.list_tasks(case_id=case_id, limit=1000)
        timeline = []
        for task in tasks:
            task_events = await task_repository.list_events(task.id)
            for ev in task_events:
                timeline.append({**ev.to_dict(), "task_title": task.title})
        phases = await case_repository.list_phases(case_id)
        for ph in phases:
            timeline.append({
                "event_type": "phase_change",
                "event_data": {"phase": ph.phase, "status": ph.status},
                "created_at": ph.started_at.isoformat() if ph.started_at else None,
            })
        timeline.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return timeline

    async def _audit(self, action: str, resource_type: str, resource_id: int, case_id: int | None, user_id: int, details: dict | None = None):
        """记录审计日志 (best-effort, 不阻塞主流程)"""
        try:
            from yuxi.storage.postgres.models_police import PoliceAuditLog
            from yuxi.storage.postgres.manager import pg_manager

            async with pg_manager.get_async_session_context() as session:
                log = PoliceAuditLog(
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    case_id=case_id,
                    details=details,
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")


class PoliceTaskService:
    """任务服务 — 编排任务创建、分配、状态流转、自动触发规则"""

    async def create_task(self, data: dict[str, Any], creator_id: int, creator_type: str = "human") -> dict[str, Any]:
        data["creator_id"] = creator_id
        data["creator_type"] = creator_type
        task = await task_repository.create(data)
        # 记录事件
        await task_repository.create_event({
            "case_id": task.case_id,
            "task_id": task.id,
            "event_type": "created",
            "event_data": {"title": task.title, "type": task.type},
            "created_by": creator_id,
        })
        return task.to_dict()

    async def list_tasks(self, **kwargs) -> dict[str, Any]:
        tasks, total = await task_repository.list_tasks(**kwargs)
        return {
            "items": [t.to_dict() for t in tasks],
            "total": total,
            "page": (kwargs.get("skip", 0) // kwargs.get("limit", 20)) + 1,
            "page_size": kwargs.get("limit", 20),
        }

    async def get_task(self, task_id: int) -> dict[str, Any] | None:
        task = await task_repository.get_by_id(task_id)
        if not task:
            return None
        result = task.to_dict()
        events = await task_repository.list_events(task_id)
        result["events"] = [e.to_dict() for e in events]
        return result

    async def update_task(self, task_id: int, data: dict[str, Any], user_id: int) -> dict[str, Any] | None:
        task = await task_repository.update(task_id, data)
        return task.to_dict() if task else None

    async def assign_task(self, task_id: int, assignee_type: str, assignee_id: int, assignee_name: str, user_id: int) -> dict[str, Any] | None:
        task = await task_repository.assign(task_id, assignee_type, assignee_id, assignee_name)
        if task:
            await task_repository.create_event({
                "case_id": task.case_id, "task_id": task_id, "event_type": "assigned",
                "event_data": {"assignee_type": assignee_type, "assignee_id": assignee_id, "assignee_name": assignee_name},
                "created_by": user_id,
            })
        return task.to_dict() if task else None

    async def start_task(self, task_id: int, user_id: int) -> dict[str, Any] | None:
        task = await task_repository.start(task_id)
        if task:
            await task_repository.create_event({
                "case_id": task.case_id, "task_id": task_id, "event_type": "started", "event_data": {}, "created_by": user_id,
            })
        return task.to_dict() if task else None

    async def complete_task(self, task_id: int, result: dict | None, user_id: int) -> dict[str, Any] | None:
        task = await task_repository.complete(task_id, result)
        if task:
            await task_repository.create_event({
                "case_id": task.case_id, "task_id": task_id, "event_type": "completed",
                "event_data": {"result": result}, "created_by": user_id,
            })
            # ★ 把任务阶段性成果写入案件工作区
            await self._write_task_artifact(task, result, user_id)
            # ★ 触发任务流转规则
            await self._trigger_flow_rules(task)
        return task.to_dict() if task else None

    async def _write_task_artifact(self, task, result: dict | None, user_id: int) -> None:
        """任务完成后将结果写入工作区「03-阶段性成果」"""
        if not result:
            return
        try:
            import json
            content = json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8")
            filename = f"{task.type}-{task.id}-result.json"
            await police_workspace_service.upload_task_artifact(
                case_id=task.case_id,
                task_id=task.id,
                filename=filename,
                content=content,
                mime_type="application/json",
                created_by=user_id,
            )
        except Exception as e:
            logger.warning(f"Write task artifact to workspace failed: {e}")

    async def review_task(self, task_id: int, approved: bool, reviewer_id: int, reviewer_police_id: str) -> dict[str, Any] | None:
        """审核任务 — 通过时计算 signed_hash"""
        # 获取任务结果哈希
        task = await task_repository.get_by_id(task_id)
        if not task:
            return None
        result_str = str(task.result) if task.result else ""
        result_hash = hashlib.sha256(result_str.encode()).hexdigest()
        signed_hash = None
        if approved:
            hash_input = f"{reviewer_police_id}{utc_now_naive().isoformat()}{result_hash}"
            signed_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        task = await task_repository.review(task_id, approved, reviewer_id, signed_hash)
        if task:
            await task_repository.create_event({
                "case_id": task.case_id, "task_id": task_id, "event_type": "reviewed",
                "event_data": {"approved": approved, "reviewer_id": reviewer_id}, "created_by": reviewer_id,
            })
        return task.to_dict() if task else None

    async def _trigger_flow_rules(self, task) -> None:
        """★ 任务流转规则引擎 — 根据已完成任务自动创建后续任务"""
        try:
            rules = await task_repository.list_flow_rules(task.case_id)
            for rule in rules:
                if rule.trigger_event != "task_completed":
                    continue
                # 简单条件匹配: condition.task_type == task.type
                condition = rule.condition or {}
                if condition.get("task_type") and condition["task_type"] != task.type:
                    continue
                if rule.action == "create_task":
                    # 检查 result 中是否有下一级账户等数据
                    result = task.result or {}
                    next_accounts = result.get("next_level_accounts", [])
                    if condition.get("has_next_level") and not next_accounts:
                        continue
                    new_task_data = {
                        "case_id": task.case_id,
                        "title": f"{rule.target_task_type} — 自动生成",
                        "type": rule.target_task_type,
                        "status": "pending",
                        "assignee_type": rule.target_assignee_type or "agent",
                        "assignee_id": rule.target_assignee_id,
                        "priority": task.priority,
                        "phase": task.phase,
                        "parent_task_id": task.id,
                        "instructions": f"由任务「{task.title}」完成后自动创建。关联数据: {next_accounts}",
                    }
                    new_task = await task_repository.create(new_task_data)
                    await task_repository.create_event({
                        "case_id": task.case_id, "task_id": new_task.id, "event_type": "created",
                        "event_data": {"auto_created": True, "parent_task_id": task.id, "rule_id": rule.id},
                        "created_by": None,
                    })
                    logger.info(f"Flow rule triggered: created task {new_task.id} from task {task.id}")
        except Exception as e:
            logger.warning(f"Flow rule trigger failed: {e}")


class PoliceAgentService:
    """数字警员服务 — 管理数字警员档案、能力、工作记录、SOP

    融合 StaffDeck 数字员工概念：每位数字警员有完整身份档案、
    能力矩阵、工作统计和成长记录，像管理真实员工一样管理 AI。
    """

    PRESET_AGENTS = [
        {
            "name": "笔录分析师",
            "type": "transcript_analyst",
            "badge_number": "DA-001",
            "rank": "一级警员",
            "specialty": "笔录解析 · 实体识别 · 信息提取",
            "avatar": "pencil",
            "department": "情报分析科",
            "color_theme": "blue",
            "capabilities": ["笔录解析", "OCR", "实体识别", "信息提取", "结构化输出"],
            "system_prompt": "你是一位专业的公安笔录分析师。你的任务是解析报案笔录，提取关键信息（涉案银行卡、微信号、嫌疑人信息等），并生成结构化的案件信息。",
            "model_config": {"provider": "custom-openai", "model": "gpt-4o", "temperature": 0.3},
        },
        {
            "name": "资金追踪师",
            "type": "fund_analyst",
            "badge_number": "DA-002",
            "rank": "一级警员",
            "specialty": "银行流水解析 · 资金追踪 · 异常检测",
            "avatar": "chart",
            "department": "经侦科",
            "color_theme": "green",
            "capabilities": ["银行流水解析", "资金链路追踪", "异常交易检测", "可视化报告", "NetworkX"],
            "system_prompt": "你是一位专业的资金分析智能体。你的任务是解析银行流水数据，追踪资金链路，发现异常交易模式，生成资金流向报告。记住：你只负责读摘要写报告，不做算数字。",
            "model_config": {"provider": "custom-openai", "model": "gpt-4o", "temperature": 0.2},
        },
        {
            "name": "调证生成师",
            "type": "evidence_collector",
            "badge_number": "DA-003",
            "rank": "二级警员",
            "specialty": "法律依据检索 · 调取通知书生成",
            "avatar": "file",
            "department": "法制科",
            "color_theme": "amber",
            "capabilities": ["法律检索", "RAG", "文书生成", "调取通知书", "模板填充"],
            "system_prompt": "你是一位专业的调证智能体。你的任务是根据案件信息检索法律依据，生成调取证据通知书。确保文书格式规范、法律引用准确。",
            "model_config": {"provider": "custom-openai", "model": "gpt-4o", "temperature": 0.2},
        },
        {
            "name": "法制审核官",
            "type": "legal_reviewer",
            "badge_number": "DA-004",
            "rank": "三级警员",
            "specialty": "程序审核 · 证据审核 · 定性审核",
            "avatar": "shield",
            "department": "法制科",
            "color_theme": "coral",
            "capabilities": ["程序审核", "证据审核", "定性审核", "法律适用", "审批流程"],
            "system_prompt": "你是一位专业的法制审核智能体。你的任务是从程序、证据、定性三个维度审核案件，确保办案程序合法、证据链完整、定性准确。",
            "model_config": {"provider": "custom-openai", "model": "gpt-4o", "temperature": 0.1},
        },
        {
            "name": "案件编排官",
            "type": "case_orchestrator",
            "badge_number": "DA-005",
            "rank": "三级警员",
            "specialty": "案件编排 · 子智能体调度 · 任务流转",
            "avatar": "network",
            "department": "指挥中心",
            "color_theme": "purple",
            "capabilities": ["案件编排", "子智能体调度", "任务流转", "事件监听", "自动决策"],
            "system_prompt": "你是案件编排智能体。你的任务是监听案件事件，根据案件进展调度专业子智能体，自动创建后续任务。你是整个多智能体协作的大脑。",
            "model_config": {"provider": "custom-openai", "model": "gpt-4o", "temperature": 0.3},
        },
    ]

    async def list_agents(
        self, *, type: str | None = None, status: str | None = None,
        keyword: str | None = None, page: int = 1, page_size: int = 50,
    ) -> dict[str, Any]:
        agents, total = await police_agent_repository.list_agents(
            type=type, status=status, keyword=keyword,
            page=page, page_size=page_size,
        )
        return {"items": [a.to_dict() for a in agents], "total": total}

    async def get_agent(self, agent_id: int) -> dict[str, Any] | None:
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            return None
        d = agent.to_dict()
        # 聚合运行记录
        runs, run_total = await police_agent_repository.list_runs(agent_id=agent_id, page=1, page_size=5)
        d["recent_runs"] = [r.to_dict() for r in runs]
        d["run_total"] = run_total
        # 获取关联 SOP
        sops = await police_agent_repository.list_sops(agent_type=agent.type)
        d["sops"] = [s.to_dict() for s in sops]
        return d

    async def create_agent(self, data: dict[str, Any]) -> dict[str, Any]:
        agent = await police_agent_repository.create(data)
        await self._audit_agent(agent.id, "create", data)
        return agent.to_dict()

    async def update_agent(self, agent_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        agent = await police_agent_repository.update(agent_id, data)
        if not agent:
            return None
        await self._audit_agent(agent_id, "update", data)
        return agent.to_dict()

    async def delete_agent(self, agent_id: int) -> bool:
        ok = await police_agent_repository.delete(agent_id)
        if ok:
            await self._audit_agent(agent_id, "delete", {})
        return ok

    async def get_agent_runs(
        self, *, agent_id: int | None = None, case_id: int | None = None,
        page: int = 1, page_size: int = 20,
    ) -> dict[str, Any]:
        runs, total = await police_agent_repository.list_runs(
            agent_id=agent_id, case_id=case_id, page=page, page_size=page_size,
        )
        return {"items": [r.to_dict() for r in runs], "total": total}

    async def list_sops(self, *, agent_type: str | None = None, category: str | None = None) -> list[dict[str, Any]]:
        sops = await police_agent_repository.list_sops(agent_type=agent_type, category=category)
        return [s.to_dict() for s in sops]

    async def get_sop(self, sop_id: int) -> dict[str, Any] | None:
        sop = await police_agent_repository.get_sop(sop_id)
        return sop.to_dict() if sop else None

    async def create_sop(self, data: dict[str, Any]) -> dict[str, Any]:
        sop = await police_agent_repository.create_sop(data)
        return sop.to_dict()

    async def update_sop(self, sop_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        sop = await police_agent_repository.update_sop(sop_id, data)
        return sop.to_dict() if sop else None

    async def seed_preset_agents(self) -> dict[str, Any]:
        """初始化预设数字警员，并与 yuxi 原生智能体体系打通（幂等）

        - 按 badge_number（警号）去重，已存在的数字警员跳过创建
        - 每个数字警员在 yuxi.agents 表同步创建一条子智能体记录 (backend=SubAgentBackend)
        - 回填 PoliceAgent.agent_id，建立双向关联，使其可被 yuxi 工作流调度
        """
        created = []
        synced = []
        for preset in self.PRESET_AGENTS:
            # 查找已存在的同警号数字警员
            existing_list, _ = await police_agent_repository.list_agents(
                type=preset["type"], page=1, page_size=20,
            )
            agent = next(
                (a for a in existing_list if a.badge_number == preset["badge_number"]), None
            )
            if not agent:
                agent = await police_agent_repository.create(
                    {**preset, "backend_id": "SubAgentBackend"}
                )
                await police_agent_repository.add_growth_event(
                    agent.id, "created", f"数字警员 {agent.name} 初始化完成"
                )
                created.append(agent.to_dict())
            # 若尚未关联 yuxi 智能体（agent_id 或 backend_id 缺失），则创建并回填
            if not agent.agent_id or not agent.backend_id:
                yuxi_agent = await self._ensure_yuxi_agent(agent)
                if yuxi_agent:
                    await police_agent_repository.update(
                        agent.id, {"agent_id": yuxi_agent.id, "backend_id": "SubAgentBackend"}
                    )
                    synced.append(agent.id)
        return {"created": len(created), "synced": len(synced), "agents": created}

    async def _ensure_yuxi_agent(self, agent: "PoliceAgent"):
        """在 yuxi.agents 表为数字警员创建对应子智能体记录，返回该 Agent。

        数字警员本质上是 yuxi 的专业子智能体：用 SubAgentBackend 后端，
        slug 直接使用数字警员工号（全局唯一），权限默认为 global（所有民警可见）。
        """
        from yuxi.repositories.agent_repository import AgentRepository
        from yuxi.storage.postgres.manager import pg_manager

        async with pg_manager.get_async_session_context() as session:
            repo = AgentRepository(session)
            # 已通过 agent_id 关联则直接取回，避免按 slug 大小写差异重复创建
            if agent.agent_id:
                from yuxi.storage.postgres.models_business import Agent
                existing_by_id = await session.get(Agent, agent.agent_id)
                if existing_by_id:
                    return existing_by_id
            # 已存在相同 slug (工号) 的智能体则直接复用
            existing = await repo.get_by_slug(agent.badge_number)
            if existing:
                return existing
            model_cfg = agent.model_config or {}
            config_json = {
                "context": {
                    "system_prompt": agent.system_prompt,
                    "model": model_cfg.get("model", "gpt-4o"),
                    "temperature": model_cfg.get("temperature", 0.3),
                }
            }
            return await repo.create(
                name=agent.name,
                backend_id="SubAgentBackend",
                slug=agent.badge_number,
                description=agent.description or agent.specialty or "",
                icon=agent.avatar,
                pics=[],
                config_json=config_json,
                share_config=None,  # 默认 global，所有民警可见
                is_subagent=True,
                created_by="system-police",
            )

    async def _audit_agent(self, agent_id: int, action: str, details: dict):
        try:
            from yuxi.storage.postgres.models_police import PoliceAuditLog
            from yuxi.storage.postgres.manager import pg_manager

            async with pg_manager.get_async_session_context() as session:
                log = PoliceAuditLog(
                    action=action,
                    resource_type="agent",
                    resource_id=agent_id,
                    details=details,
                )
                session.add(log)
                await session.commit()
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")


class PoliceDashboardService:
    """工作台统计服务"""

    async def get_stats(self, user_id: int) -> dict[str, Any]:
        """工作台统计数据"""
        my_tasks, my_count = await task_repository.list_tasks(my_tasks_user_id=user_id, limit=1000)
        review_tasks, review_count = await task_repository.list_tasks(review_user_id=user_id, limit=1000)
        in_progress = [t for t in my_tasks if t.status == "in_progress"]
        pending = [t for t in my_tasks if t.status == "pending"]
        return {
            "my_pending_count": len(pending),
            "my_in_progress_count": len(in_progress),
            "review_count": review_count,
            "my_tasks_total": my_count,
        }

    async def get_my_tasks(self, user_id: int, skip: int = 0, limit: int = 20) -> dict[str, Any]:
        tasks, total = await task_repository.list_tasks(my_tasks_user_id=user_id, skip=skip, limit=limit)
        return {"items": [t.to_dict() for t in tasks], "total": total}

    async def get_review_tasks(self, user_id: int, skip: int = 0, limit: int = 20) -> dict[str, Any]:
        tasks, total = await task_repository.list_tasks(review_user_id=user_id, skip=skip, limit=limit)
        return {"items": [t.to_dict() for t in tasks], "total": total}


class PoliceWorkspaceService:
    """★ 案件独立工作区服务（树状节点版）

    为每个案件维护一个 MinIO 存储命名空间 (cases/{case_number}/)，
    并以 PoliceWorkspaceNode 树状节点组织文件/文件夹：
      - 01-证据     证据材料（与 evidence 表同步）
      - 02-材料     民警手动上传的办案材料
      - 03-阶段性成果 任务完成后自动生成的产物
    支持文件夹嵌套、文件上传/下载/删除/移动。
    """

    WORKSPACE_BUCKET = "police-workspace"
    DEFAULT_FOLDERS = [
        ("01-证据", "evidence"),
        ("02-材料", "materials"),
        ("03-阶段性成果", "artifacts"),
    ]
    FOLDER_CATEGORY = {
        "evidence": "证据",
        "materials": "材料",
        "artifacts": "阶段性成果",
    }

    async def get_or_create(self, case_id: int, case_number: str | None = None) -> dict[str, Any]:
        """获取或创建案件工作区；自动初始化默认文件夹"""
        if case_number is None:
            case = await case_repository.get_by_id(case_id)
            if not case:
                raise ValueError(f"案件 {case_id} 不存在")
            case_number = case.case_number
        prefix = f"cases/{case_number}/"
        workspace = await police_workspace_repository.upsert({
            "case_id": case_id,
            "case_number": case_number,
            "storage_bucket": self.WORKSPACE_BUCKET,
            "storage_prefix": prefix,
            "status": "ready",
        })
        await self._ensure_default_folders(workspace)
        return workspace.to_dict()

    async def _ensure_default_folders(self, workspace: PoliceCaseWorkspace) -> None:
        """幂等初始化默认根文件夹"""
        for name, category in self.DEFAULT_FOLDERS:
            existing = await police_workspace_repository.get_node_by_name(workspace.id, name, parent_id=None)
            if existing:
                continue
            await police_workspace_repository.create_node({
                "workspace_id": workspace.id,
                "parent_id": None,
                "node_type": "folder",
                "name": name,
                "storage_path": None,
                "source_type": "system",
                "extra": {"category": category},
            })

    async def get_workspace(self, case_id: int) -> dict[str, Any] | None:
        """返回工作区信息 + 树状节点 + 统计"""
        workspace = await police_workspace_repository.get_by_case_id(case_id)
        if not workspace:
            return None
        await self._ensure_default_folders(workspace)
        nodes = await police_workspace_repository.list_nodes_by_workspace(workspace.id)
        tree = self._build_tree(nodes)
        stats = self._calc_stats(nodes)
        return {
            "workspace": workspace.to_dict(),
            "tree": tree,
            "nodes": [n.to_dict() for n in nodes],
            "stats": stats,
        }

    def _build_tree(self, nodes: list[PoliceWorkspaceNode]) -> list[dict[str, Any]]:
        """把扁平节点列表构建成嵌套树"""
        by_id: dict[int, dict] = {}
        roots: list[dict] = []
        for n in nodes:
            d = {**n.to_dict(), "children": []}
            by_id[n.id] = d
        for n in nodes:
            d = by_id[n.id]
            if n.parent_id is not None and n.parent_id in by_id:
                by_id[n.parent_id]["children"].append(d)
            else:
                roots.append(d)
        # 文件夹在前，按名称排序
        roots.sort(key=lambda x: (0 if x["node_type"] == "folder" else 1, x["name"]))
        return roots

    def _calc_stats(self, nodes: list[PoliceWorkspaceNode]) -> dict[str, Any]:
        evidence_count = material_count = artifact_count = file_count = total_size = 0
        for n in nodes:
            if n.node_type != "file":
                continue
            file_count += 1
            total_size += n.size or 0
            cat = (n.extra or {}).get("category")
            if cat == "evidence":
                evidence_count += 1
            elif cat == "materials":
                material_count += 1
            elif cat == "artifacts":
                artifact_count += 1
        return {
            "evidence_count": evidence_count,
            "material_count": material_count,
            "artifact_count": artifact_count,
            "file_count": file_count,
            "total_size": total_size,
        }

    async def create_folder(
        self, case_id: int, name: str, parent_id: int | None = None, created_by: int | None = None
    ) -> dict[str, Any]:
        """在工作区创建文件夹"""
        ws = await self.get_or_create(case_id)
        parent = await self._require_folder(ws["id"], parent_id)
        existing = await police_workspace_repository.get_node_by_name(ws["id"], name, parent_id=parent.id if parent else None)
        if existing:
            raise ValueError("同目录下已存在同名文件夹")
        folder = await police_workspace_repository.create_node({
            "workspace_id": ws["id"],
            "parent_id": parent.id if parent else None,
            "node_type": "folder",
            "name": name,
            "source_type": "manual",
            "created_by": created_by,
            "extra": {"category": (parent.extra or {}).get("category") if parent else None},
        })
        return folder.to_dict()

    async def upload(
        self, case_id: int, parent_id: int | None, file, uploaded_by: int | None = None
    ) -> dict[str, Any]:
        """上传文件到工作区指定文件夹下"""
        ws = await self.get_or_create(case_id)
        parent = await self._require_folder(ws["id"], parent_id)
        content = await file.read()
        if not content:
            raise ValueError("空文件")
        filename = file.filename or "unnamed"

        # 构造 MinIO 路径：cases/{case_number}/{category}/{parent_path?}/filename
        category = (parent.extra or {}).get("category") or "materials"
        folder_path = await self._folder_storage_path(parent)
        object_name = f"{ws['storage_prefix']}{category}/{folder_path}{filename}".replace("//", "/")

        existing = await police_workspace_repository.get_node_by_name(
            ws["id"], filename, parent_id=parent.id if parent else None
        )
        if existing and existing.node_type == "file":
            raise ValueError("同目录下已存在同名文件")

        client = get_minio_client()
        await client.aupload_file(
            ws["storage_bucket"], object_name, content,
            file.content_type or "application/octet-stream",
        )

        node = await police_workspace_repository.create_node({
            "workspace_id": ws["id"],
            "parent_id": parent.id if parent else None,
            "node_type": "file",
            "name": filename,
            "storage_path": object_name,
            "mime_type": file.content_type or "application/octet-stream",
            "size": len(content),
            "source_type": "manual",
            "created_by": uploaded_by,
            "extra": {"category": category},
        })
        await self._update_stats(ws["id"])
        return node.to_dict()

    async def upload_task_artifact(
        self, case_id: int, task_id: int, filename: str, content: bytes,
        mime_type: str = "text/plain", created_by: int | None = None,
    ) -> dict[str, Any]:
        """任务完成后把产物写入工作区（放入 03-阶段性成果）"""
        ws = await self.get_or_create(case_id)
        # 找到「03-阶段性成果」文件夹
        root_nodes = await police_workspace_repository.list_nodes(ws["id"], parent_id=None)
        artifact_folder = next(
            (n for n in root_nodes if n.node_type == "folder" and (n.extra or {}).get("category") == "artifacts"),
            None,
        )
        if not artifact_folder:
            artifact_folder = await police_workspace_repository.create_node({
                "workspace_id": ws["id"],
                "parent_id": None,
                "node_type": "folder",
                "name": "03-阶段性成果",
                "source_type": "system",
                "extra": {"category": "artifacts"},
            })
        # 在成果文件夹下按任务 ID 再建一个子文件夹
        task_folder_name = f"task-{task_id}"
        task_folder = await police_workspace_repository.get_node_by_name(
            ws["id"], task_folder_name, parent_id=artifact_folder.id
        )
        if not task_folder:
            task_folder = await police_workspace_repository.create_node({
                "workspace_id": ws["id"],
                "parent_id": artifact_folder.id,
                "node_type": "folder",
                "name": task_folder_name,
                "source_type": "task",
                "source_task_id": task_id,
                "extra": {"category": "artifacts", "task_id": task_id},
            })

        object_name = f"{ws['storage_prefix']}artifacts/task-{task_id}/{filename}".replace("//", "/")
        client = get_minio_client()
        await client.aupload_file(ws["storage_bucket"], object_name, content, mime_type)

        existing = await police_workspace_repository.get_node_by_name(
            ws["id"], filename, parent_id=task_folder.id
        )
        if existing:
            await police_workspace_repository.update_node(existing.id, {
                "storage_path": object_name,
                "mime_type": mime_type,
                "size": len(content),
                "source_task_id": task_id,
            })
            node = existing
        else:
            node = await police_workspace_repository.create_node({
                "workspace_id": ws["id"],
                "parent_id": task_folder.id,
                "node_type": "file",
                "name": filename,
                "storage_path": object_name,
                "mime_type": mime_type,
                "size": len(content),
                "source_type": "task",
                "source_task_id": task_id,
                "created_by": created_by,
                "extra": {"category": "artifacts", "task_id": task_id},
            })
        await self._update_stats(ws["id"])
        return node.to_dict()

    async def sync_evidence_node(self, case_id: int, evidence: Evidence) -> dict[str, Any]:
        """证据上传后同步到工作区「01-证据」文件夹"""
        ws = await self.get_or_create(case_id)
        root_nodes = await police_workspace_repository.list_nodes(ws["id"], parent_id=None)
        evidence_folder = next(
            (n for n in root_nodes if n.node_type == "folder" and (n.extra or {}).get("category") == "evidence"),
            None,
        )
        if not evidence_folder:
            evidence_folder = await police_workspace_repository.create_node({
                "workspace_id": ws["id"],
                "parent_id": None,
                "node_type": "folder",
                "name": "01-证据",
                "source_type": "system",
                "extra": {"category": "evidence"},
            })
        filename = evidence.name or evidence.file_path.split("/")[-1] or f"evidence-{evidence.id}"
        existing = await police_workspace_repository.get_node_by_name(
            ws["id"], filename, parent_id=evidence_folder.id
        )
        data = {
            "workspace_id": ws["id"],
            "parent_id": evidence_folder.id,
            "node_type": "file",
            "name": filename,
            "storage_path": evidence.file_path,
            "mime_type": evidence.mime_type,
            "size": evidence.file_size,
            "source_type": "evidence",
            "source_task_id": evidence.task_id,
            "created_by": evidence.uploaded_by,
            "extra": {"category": "evidence", "evidence_id": evidence.id, "evidence_type": evidence.type},
        }
        if existing:
            node = await police_workspace_repository.update_node(existing.id, data)
        else:
            node = await police_workspace_repository.create_node(data)
        await self._update_stats(ws["id"])
        return node.to_dict()

    async def move_node(self, case_id: int, node_id: int, target_parent_id: int | None) -> dict[str, Any]:
        """移动节点到目标文件夹"""
        ws = await self.get_or_create(case_id)
        node = await police_workspace_repository.get_node(node_id)
        if not node or node.workspace_id != ws["id"]:
            raise ValueError("节点不存在")
        if target_parent_id is not None:
            target = await police_workspace_repository.get_node(target_parent_id)
            if not target or target.workspace_id != ws["id"] or target.node_type != "folder":
                raise ValueError("目标文件夹不存在")
            # 禁止把自己移入自己的后代
            if await self._is_descendant(node_id, target_parent_id):
                raise ValueError("不能将文件夹移入自己的子文件夹")
        # 重名校验
        sibling = await police_workspace_repository.get_node_by_name(
            ws["id"], node.name, parent_id=target_parent_id
        )
        if sibling and sibling.id != node_id:
            raise ValueError("目标目录下已存在同名节点")
        updated = await police_workspace_repository.update_node(node_id, {"parent_id": target_parent_id})
        return updated.to_dict()

    async def rename_node(self, case_id: int, node_id: int, new_name: str) -> dict[str, Any]:
        """重命名节点"""
        ws = await self.get_or_create(case_id)
        node = await police_workspace_repository.get_node(node_id)
        if not node or node.workspace_id != ws["id"]:
            raise ValueError("节点不存在")
        sibling = await police_workspace_repository.get_node_by_name(
            ws["id"], new_name, parent_id=node.parent_id
        )
        if sibling and sibling.id != node_id:
            raise ValueError("同目录下已存在同名节点")
        updated = await police_workspace_repository.update_node(node_id, {"name": new_name})
        return updated.to_dict()

    async def delete_node(self, case_id: int, node_id: int) -> bool:
        """删除节点：文件同步删 MinIO；文件夹递归删除"""
        ws = await self.get_or_create(case_id)
        node = await police_workspace_repository.get_node(node_id)
        if not node or node.workspace_id != ws["id"]:
            raise ValueError("节点不存在")
        # 先删子节点
        children = await police_workspace_repository.list_nodes(ws["id"], parent_id=node_id)
        for child in children:
            await self.delete_node(case_id, child.id)
        # 再删 MinIO 对象
        if node.node_type == "file" and node.storage_path:
            try:
                await get_minio_client().adelete_file(ws["storage_bucket"], node.storage_path)
            except Exception as e:
                logger.warning(f"Delete minio object failed: {e}")
        ok = await police_workspace_repository.delete_node(node_id)
        await self._update_stats(ws["id"])
        return ok

    async def download(self, case_id: int, node_id: int) -> tuple[bytes, str, str]:
        """根据节点 ID 下载文件"""
        ws = await self.get_or_create(case_id)
        node = await police_workspace_repository.get_node(node_id)
        if not node or node.workspace_id != ws["id"]:
            raise ValueError("节点不存在")
        if node.node_type != "file" or not node.storage_path:
            raise ValueError("该节点不是可下载文件")
        bucket = ws["storage_bucket"]

        def _stat():
            return get_minio_client().client.stat_object(bucket, node.storage_path)

        try:
            stat = await asyncio.to_thread(_stat)
            content_type = stat.content_type or node.mime_type or "application/octet-stream"
        except Exception:
            content_type = node.mime_type or "application/octet-stream"

        data = await get_minio_client().adownload_file(bucket, node.storage_path)
        return data, content_type, node.name

    async def _require_folder(
        self, workspace_id: int, parent_id: int | None
    ) -> PoliceWorkspaceNode | None:
        """校验 parent_id 是有效的文件夹；None 表示根目录"""
        if parent_id is None:
            return None
        parent = await police_workspace_repository.get_node(parent_id)
        if not parent or parent.workspace_id != workspace_id or parent.node_type != "folder":
            raise ValueError("目标文件夹不存在")
        return parent

    async def _folder_storage_path(self, folder: PoliceWorkspaceNode | None) -> str:
        """从 folder 向上回溯构造相对存储路径"""
        if folder is None:
            return ""
        parts = []
        current = folder
        # 避免循环，最多 20 层
        for _ in range(20):
            parts.append(current.name)
            if current.parent_id is None:
                break
            parent = await police_workspace_repository.get_node(current.parent_id)
            if not parent:
                break
            current = parent
        # 排除根分类文件夹名，因为它已经体现在 category 中
        if parts and any(parts[-1].startswith(prefix) for prefix in ("01-", "02-", "03-")):
            parts.pop()
        return "/".join(reversed(parts)) + "/" if parts else ""

    async def _is_descendant(self, ancestor_id: int, node_id: int) -> bool:
        """判断 node_id 是否是 ancestor_id 的后代"""
        current = await police_workspace_repository.get_node(node_id)
        visited = set()
        while current and current.parent_id is not None:
            if current.parent_id in visited:
                break
            visited.add(current.parent_id)
            if current.parent_id == ancestor_id:
                return True
            current = await police_workspace_repository.get_node(current.parent_id)
        return False

    async def _update_stats(self, workspace_id: int) -> None:
        """重新计算并缓存工作区统计"""
        try:
            nodes = await police_workspace_repository.list_nodes_by_workspace(workspace_id)
            stats = self._calc_stats(nodes)
            await police_workspace_repository.update(workspace_id, {"stats": stats})
        except Exception as e:
            logger.warning(f"Update workspace stats failed: {e}")


police_case_service = PoliceCaseService()
police_task_service = PoliceTaskService()
police_dashboard_service = PoliceDashboardService()
police_agent_service = PoliceAgentService()
police_workspace_service = PoliceWorkspaceService()


police_case_service = PoliceCaseService()
police_task_service = PoliceTaskService()
police_dashboard_service = PoliceDashboardService()
police_agent_service = PoliceAgentService()
police_workspace_service = PoliceWorkspaceService()
