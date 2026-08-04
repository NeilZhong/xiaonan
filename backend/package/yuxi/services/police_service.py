"""★ 公安业务服务层 — 案件 + 任务流转引擎 + 数字警员"""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select

from yuxi.repositories.agent_repository import DEFAULT_AGENT_BACKEND_ID
from yuxi.services.police_prompts import PRESET_AGENTS as _PRESET_AGENTS_UPGRADED
from yuxi.repositories.police_agent_repository import police_agent_repository
from yuxi.repositories.police_workspace_repository import police_workspace_repository
from yuxi.repositories.case_repository import case_repository
from yuxi.repositories.evidence_repository import evidence_repository
from yuxi.repositories.task_repository import task_repository
from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.minio.client import get_minio_client
from yuxi.storage.postgres.models_business import User
from yuxi.storage.postgres.models_police import Evidence
from yuxi.utils.datetime_utils import utc_now_naive
from yuxi.utils import logger


async def write_audit_log(
    *,
    action: str,
    resource_type: str,
    resource_id: int | None,
    case_id: int | None = None,
    user_id: int | None = None,
    user_name: str | None = None,
    details: dict | None = None,
) -> None:
    """记录审计日志 (best-effort, 不阻塞主流程)。

    供案件、任务、证据、智能体等各业务操作统一调用，确保关键操作均可
    追溯到 (操作人, 动作, 资源, 案件, 时间)，满足 POLICE_REQUIREMENTS §9.4 全量覆盖要求。
    """
    try:
        from yuxi.storage.postgres.manager import pg_manager
        from yuxi.storage.postgres.models_police import PoliceAuditLog

        async with pg_manager.get_async_session_context() as session:
            log = PoliceAuditLog(
                user_id=user_id,
                user_name=user_name,
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
        # 补充成员的用户名（CaseMember.to_dict() 不含 username）
        if members:
            user_ids = list({m.user_id for m in members})
            async with pg_manager.get_async_session_context() as db:
                users_rows = (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
                user_map = {u.id: u.username for u in users_rows}
            result["members"] = [{**m.to_dict(), "username": user_map.get(m.user_id, "")} for m in members]
        else:
            result["members"] = []
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
        await write_audit_log(
            action=action, resource_type=resource_type, resource_id=resource_id,
            case_id=case_id, user_id=user_id, details=details,
        )


class PoliceTaskService:
    """任务服务 — 编排任务创建、分配、状态流转、自动触发规则"""

    async def _audit(self, action: str, resource_id: int, user_id: int, case_id: int | None, details: dict | None = None) -> None:
        """任务操作审计 (best-effort) — 补充 POLICE_REQUIREMENTS §9.4 全量覆盖"""
        await write_audit_log(
            action=action, resource_type="task", resource_id=resource_id,
            case_id=case_id, user_id=user_id, details=details,
        )

    async def create_task(self, data: dict[str, Any], creator_id: int, creator_type: str = "human") -> dict[str, Any]:
        data["creator_id"] = creator_id
        data["creator_type"] = creator_type
        task = await task_repository.create(data)
        # 若创建时即带执行人（向后兼容单执行人字段），解算并落审核人
        await self._resolve_and_store_reviewer(task.id)
        # 记录事件
        await task_repository.create_event({
            "case_id": task.case_id,
            "task_id": task.id,
            "event_type": "created",
            "event_data": {"title": task.title, "type": task.type},
            "created_by": creator_id,
        })
        await self._audit("create", task.id, creator_id, task.case_id, {"title": task.title, "type": task.type})
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
        """获取任务详情（含执行人列表）"""
        task = await task_repository.get_task_with_assignees(task_id)
        if not task:
            return None
        result = task.to_dict()  # to_dict 已包含 assignees
        events = await task_repository.list_events(task_id)
        result["events"] = [e.to_dict() for e in events]
        return result

    async def update_task(self, task_id: int, data: dict[str, Any], user_id: int) -> dict[str, Any] | None:
        task = await task_repository.update(task_id, data)
        return task.to_dict() if task else None

    async def assign_task(self, task_id: int, assignee_type: str, assignee_id: int, assignee_name: str, user_id: int) -> dict[str, Any] | None:
        """向后兼容的单执行人分配（内部转为多执行人调用）"""
        return await self.assign_task_multi(task_id, [
            {"assignee_type": assignee_type, "assignee_id": assignee_id, "assignee_name": assignee_name, "role": "executor"}
        ], user_id)

    async def assign_task_multi(self, task_id: int, assignees: list[dict], user_id: int) -> dict[str, Any] | None:
        """多执行人分配（核心方法）。

        assignees 每项: {assignee_type, assignee_id, assignee_name, role?}
        同时更新 PoliceTask 冗余字段（向后兼容），并写入 TaskAssignee 关联表。
        """
        task = await task_repository.get_by_id(task_id)
        if not task:
            return None
        # 写入多执行人关联表
        await task_repository.set_assignees(task_id, assignees)
        # 重新解算并落审核人（v2.1 §4.3）
        await self._resolve_and_store_reviewer(task_id)
        # 同步冗余字段（取第一个执行人作为主显示）
        first = assignees[0] if assignees else {}
        task = await task_repository.assign(
            task_id,
            first.get("assignee_type", "human"),
            first.get("assignee_id"),
            first.get("assignee_name", ""),
        )
        # 记录事件
        await task_repository.create_event({
            "case_id": task.case_id, "task_id": task_id, "event_type": "assigned",
            "event_data": {"assignees": assignees, "count": len(assignees)},
            "created_by": user_id,
        })
        await self._audit("assign", task_id, user_id, task.case_id, {"assignees": assignees})
        # 重新加载含执行人的完整数据
        full = await task_repository.get_task_with_assignees(task_id)
        return full.to_dict() if full else task.to_dict()

    async def start_task(self, task_id: int, user_id: int) -> dict[str, Any] | None:
        """开始任务 — 若有智能体执行人则自动触发 AI 执行"""
        task = await task_repository.start(task_id)
        if not task:
            return None
        await task_repository.create_event({
            "case_id": task.case_id, "task_id": task_id, "event_type": "started",
            "event_data": {}, "created_by": user_id,
        })
        await self._audit("start", task_id, user_id, task.case_id, {})

        # ★ 智能体自动执行：检测是否有 agent 类型执行人
        summary = await task_repository.get_assignee_summary(task_id)
        if summary["has_agent"]:
            # 异步触发智能体执行，不阻塞响应
            asyncio.create_task(self._execute_agents(task_id, summary["agents"], user_id))

        full = await task_repository.get_task_with_assignees(task_id)
        return full.to_dict() if full else task.to_dict()

    async def _execute_agents(self, task_id: int, agents: list[dict], trigger_user_id: int) -> None:
        """异步执行智能体任务（后台运行）。

        根据任务描述和各智能体的 system_prompt 调用 LLM 自动完成任务，
        完成后将结果写入 task.result 并将状态推进到 review。
        """
        try:
            task = await task_repository.get_by_id(task_id)
            if not task or task.status != "in_progress":
                return

            from yuxi.agents.models import load_chat_model

            # 加载案件上下文
            case_detail = None
            if task.case_id:
                case_detail = await police_case_service.get_case_detail(task.case_id)

            # 逐个执行智能体，聚合结果
            all_results = []
            for agent_info in agents:
                agent = await police_agent_repository.get_by_id(agent_info["assignee_id"])
                if not agent:
                    continue
                try:
                    cfg = agent.model_config or {}
                    provider = cfg.get("provider")
                    model_name = cfg.get("model") or ""
                    model_spec = (
                        f"{provider}:{model_name}" if provider and model_name
                        else (model_name or None)
                    )
                    model = load_chat_model(
                        model_spec, temperature=cfg.get("temperature", 0.3)
                    )
                    # 构造执行 prompt
                    system_prompt = agent.system_prompt
                    user_prompt = (
                        f"请完成以下公安办案任务。\n\n"
                        f"【任务】{task.title}\n"
                        f"【描述】{task.description or '无'}\n"
                        f"【类型】{task.type}\n"
                    )
                    if case_detail:
                        user_prompt += (
                            f"\n【案件】{case_detail.get('title', '')} (#{case_detail.get('id')})\n"
                            f"【案情摘要】{(case_detail.get('description') or '')[:500]}"
                        )
                    if task.instructions:
                        user_prompt += f"\n【具体指示】{task.instructions}"
                    user_prompt += "\n\n请直接输出任务执行结果（结构化 JSON 或文本）。"

                    response = await model.ainvoke([
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ])
                    result_text = getattr(response, "content", str(response))
                    all_results.append({
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "result": result_text,
                    })

                    # 记录智能体运行
                    await self._record_agent_run(agent.id, task_id, task.case_id, result_text)
                except Exception as e:
                    logger.error(f"Agent {agent_info['assignee_name']} execution failed: {e}")
                    all_results.append({
                        "agent_id": agent_info["assignee_id"],
                        "agent_name": agent_info["assignee_name"],
                        "error": str(e),
                    })

            # 汇总结果并推进到审核状态
            final_result = {
                "agent_results": all_results,
                "summary": "\n".join(
                    r.get("result", r.get("error", "无结果")) for r in all_results
                ),
                "executed_by": "agent_auto",
            }
            # 自动完成 → 进入待审核
            await self.complete_task(task_id, final_result, trigger_user_id)

        except Exception as e:
            logger.error(f"Agent auto-execution for task {task_id} failed: {e}")
            # 标记任务异常
            await task_repository.update(task_id, {"status": "blocked"})

    async def _record_agent_run(self, agent_id: int, task_id: int, case_id: int | None, output: str) -> None:
        """记录数字警员运行实例（best-effort）"""
        try:
            from yuxi.storage.postgres.models_police import PoliceAgentRun
            async with pg_manager.get_async_session_context() as session:
                run = PoliceAgentRun(
                    agent_id=agent_id, task_id=task_id, case_id=case_id,
                    status="completed", output={"result": output}, tokens_used=0,
                    started_at=utc_now_naive(), completed_at=utc_now_naive(),
                )
                session.add(run)
                await session.commit()
        except Exception as e:
            logger.warning(f"Record agent run failed: {e}")

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
            await self._audit("complete", task_id, user_id, task.case_id, {"has_result": bool(result)})
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

    async def _resolve_and_store_reviewer(self, task_id: int) -> None:
        """解算并落盘任务的审核人（v2.1 §4.3）。幂等，失败 best-effort 不阻断主流程。"""
        try:
            reviewer_id, require_approval = await task_repository.resolve_reviewer(task_id)
            await task_repository.set_reviewer(task_id, reviewer_id, require_approval)
        except Exception as e:
            logger.warning(f"Resolve reviewer for task {task_id} failed: {e}")

    async def review_task(
        self,
        task_id: int,
        approved: bool,
        current_user_id: int,
        current_user_role: str,
        reviewer_police_id: str,
        comment: str | None = None,
    ) -> dict[str, Any] | None:
        """审核任务（v2.1 权限加固）

        - 审核前确保审核人已解算；若未解算（历史数据/分配前创建）则即时解算。
        - 权限：require_approval=1 时，仅指定审核人(reviewer_id)或系统管理员(admin/superadmin)
                可审核；其余账号返回 403（修复越权安全硬伤）。
        - require_approval=0（仅人类执行、无 AI 产出）时，任务的执行人(人类)或管理员可标记完成。
        - 通过时以真实审核人的警号签署 signed_hash，禁止冒充。
        """
        task = await task_repository.get_by_id(task_id)
        if not task:
            return None
        # 确保审核人已解算
        if task.reviewer_id is None and task.require_approval is None:
            await self._resolve_and_store_reviewer(task_id)
            task = await task_repository.get_by_id(task_id)
            if not task:
                return None

        is_admin = current_user_role in ("admin", "superadmin")
        if task.require_approval:
            # 需审核：仅指定审核人或管理员
            if not is_admin and task.reviewer_id != current_user_id:
                raise HTTPException(
                    status_code=403,
                    detail="无审核权限：仅指定审核人或系统管理员可审核该任务",
                )
        else:
            # 无需审核（纯人类任务）：仅执行人或管理员可标记完成
            summary = await task_repository.get_assignee_summary(task_id)
            human_ids = [h["assignee_id"] for h in summary["humans"]]
            if not is_admin and current_user_id not in human_ids:
                raise HTTPException(
                    status_code=403,
                    detail="无权限：仅任务执行人或系统管理员可操作该任务",
                )

        # 真实审核人（用于署名与签名）
        reviewer_id = current_user_id
        # 获取任务结果哈希
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
                "event_data": {"approved": approved, "reviewer_id": reviewer_id, "comment": comment},
                "created_by": reviewer_id,
            })
            await self._audit(
                "review" if approved else "reject", task_id, reviewer_id, task.case_id,
                {"approved": approved, "comment": comment},
            )
            # 审核通过 → 任务真正完成 → 异步触发推进智能体（事件驱动，不阻塞响应）
            if approved:
                asyncio.create_task(self._trigger_advancement(task.case_id, task_id, reviewer_id))
        return task.to_dict() if task else None

    async def _trigger_advancement(self, case_id: int, task_id: int, reviewer_id: int) -> None:
        """懒加载推进智能体并触发推进（隔离导入，避免循环依赖）。"""
        try:
            from yuxi.services.police_advancement_service import police_advancement_service

            await police_advancement_service.advance_after_task_completed(case_id, task_id, reviewer_id)
        except Exception as e:
            logger.error(f"Trigger advancement failed: {e}")

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
                    await write_audit_log(
                        action="auto_create", resource_type="task", resource_id=new_task.id,
                        case_id=task.case_id, user_id=None,
                        details={"parent_task_id": task.id, "rule_id": rule.id, "trigger": "flow_rule"},
                    )
        except Exception as e:
            logger.warning(f"Flow rule trigger failed: {e}")


class PoliceAgentService:
    """数字警员服务 — 管理数字警员档案、能力、工作记录、SOP

    融合 StaffDeck 数字员工概念：每位数字警员有完整身份档案、
    能力矩阵、工作统计和成长记录，像管理真实员工一样管理 AI。
    """

    # 数字警员预设定义已抽到 yuxi.services.police_prompts（吸收 Hunter 猎人系列设计理念，
    # 升级 DA-001~DA-005 并新增 DA-006/DA-007，模型统一 agnes-2.5-flash）。
    PRESET_AGENTS = _PRESET_AGENTS_UPGRADED

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

    async def get_agent_by_yuxi(self, yuxi_agent_id: int) -> dict[str, Any] | None:
        """按 yuxi 智能体主键 id 查询关联的数字警员档案（无关联返回 None）。

        供统一智能体档案页使用：档案页路由携带 yuxi agent slug，先经 yuxi 接口
        解析为 int 主键后再调用本方法，避免把 slug 当作 police 表 int 主键传入。
        """
        agent = await police_agent_repository.get_by_yuxi_agent_id(yuxi_agent_id)
        if not agent:
            return None
        d = agent.to_dict()
        runs, run_total = await police_agent_repository.list_runs(agent_id=agent.id, page=1, page_size=5)
        d["recent_runs"] = [r.to_dict() for r in runs]
        d["run_total"] = run_total
        sops = await police_agent_repository.list_sops(agent_type=agent.type)
        d["sops"] = [s.to_dict() for s in sops]
        return d

    async def get_agent_by_badge(self, badge_number: str) -> dict[str, Any] | None:
        """按数字警员工号查询档案（供档案页路由 /agent-manage/:badge_number 使用）。

        返回 police 档案含 agent_id（yuxi 外键），无记录返回 None。
        """
        agent = await police_agent_repository.get_by_badge_number(badge_number)
        if not agent:
            return None
        d = agent.to_dict()
        runs, run_total = await police_agent_repository.list_runs(agent_id=agent.id, page=1, page_size=5)
        d["recent_runs"] = [r.to_dict() for r in runs]
        d["run_total"] = run_total
        sops = await police_agent_repository.list_sops(agent_type=agent.type)
        d["sops"] = [s.to_dict() for s in sops]
        return d

    async def list_templates(
        self, *, category: str | None = None, keyword: str | None = None,
        page: int = 1, page_size: int = 50, source: str | None = None,
    ) -> dict[str, Any]:
        """市场模板列表。

        source='builtin' → 仅内置模板（is_template=1）
        source='shared'  → 仅用户分享的智能体（is_public=1, is_template=0）
        source=None      → 仅内置模板（向后兼容）
        """
        if source == "shared":
            return await self.list_shared_agents(
                keyword=keyword, page=page, page_size=page_size,
            )

        # 默认：内置模板
        agents, total = await police_agent_repository.list_templates(
            category=category, keyword=keyword, page=page, page_size=page_size,
        )
        installed_ids = await police_agent_repository.get_installed_template_ids()
        return {
            "items": [a.to_dict() for a in agents],
            "total": total,
            "installed_template_ids": installed_ids,
        }

    async def install_template(self, template_id: int) -> dict[str, Any] | None:
        """一键安装模板：复制模板配置为新数字警员实例（自动生成工号并桥接 yuxi）。

        失败时回滚 police 记录并返回 None。
        """
        template = await police_agent_repository.get_by_id(template_id)
        if not template or not template.is_template:
            return None
        # 从模板复制核心配置（不继承 is_template/template 身份、badge_number/install_count）
        new_data = {
            "name": template.name,
            "description": template.description,
            "type": template.type,
            "category": template.category,
            "system_prompt": template.system_prompt,
            "model_config": template.model_config or {},
            "specialty": template.specialty,
            "avatar": template.avatar,
            "color_theme": template.color_theme,
            "capabilities": template.capabilities or [],
            "skills": template.skills or [],
            "tools": template.tools or [],
            "icon": template.icon,
            "source_template_id": template_id,  # 记录来源模板，用于市场"已安装"状态判断
            # 以下字段由 create_agent 自动处理：badge_number / backend_id / agent_id
        }
        try:
            new_agent = await self.create_agent(new_data)
            # 更新模板安装计数
            await police_agent_repository.increment_install_count(template_id)
            return new_agent
        except Exception as e:
            logger.error(f"安装模板 {template_id} 失败: {e}")
            return None

    async def create_agent(self, data: dict[str, Any]) -> dict[str, Any]:
        # 工号(badge_number)是 yuxi 桥接的 slug 来源，用户未提供时自动生成全局唯一值
        if not data.get("badge_number"):
            data["badge_number"] = await self._next_badge_number()
        agent = await police_agent_repository.create(data)
        # 桥接为 yuxi 一等可对话智能体（ChatbotAgent 后端），使新建数字警员可直接对话
        yuxi_agent = await self._sync_yuxi_agent(agent)
        await police_agent_repository.update(
            agent.id,
            {"backend_id": DEFAULT_AGENT_BACKEND_ID, "agent_id": yuxi_agent.id},
        )
        agent = await police_agent_repository.get_by_id(agent.id)
        await self._audit_agent(agent.id, "create", data)
        return agent.to_dict()

    async def _next_badge_number(self) -> str:
        """生成未占用的数字警员工号（作为 yuxi slug，须全局唯一）。

        预设警员使用 DA-001~005；用户自建采用 DA-{8 位大写十六进制} 形式，
        冲突概率极低且保证 slug 合法（字母数字连字符）。
        """
        import uuid

        for _ in range(5):
            candidate = f"DA-{uuid.uuid4().hex[:8].upper()}"
            existing = await police_agent_repository.get_by_badge_number(candidate)
            if not existing:
                return candidate
        return f"DA-{uuid.uuid4().hex[:12].upper()}"

    async def update_agent(self, agent_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        agent = await police_agent_repository.update(agent_id, data)
        if not agent:
            return None
        # 同步对话智能体：system_prompt / 模型参数 / 名称等编辑实时反映到 yuxi 侧
        yuxi_agent = await self._sync_yuxi_agent(agent)
        if yuxi_agent and agent.agent_id != yuxi_agent.id:
            await police_agent_repository.update(
                agent.id, {"backend_id": DEFAULT_AGENT_BACKEND_ID, "agent_id": yuxi_agent.id}
            )
        await self._audit_agent(agent_id, "update", data)
        agent = await police_agent_repository.get_by_id(agent_id)
        return agent.to_dict() if agent else None

    async def delete_agent(self, agent_id: int) -> bool:
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            return False
        yuxi_id = agent.agent_id
        ok = await police_agent_repository.delete(agent_id)
        if ok and yuxi_id:
            # 一并移除桥接的 yuxi 对话智能体，避免 /agent 列表中遗留孤儿智能体
            try:
                from yuxi.repositories.agent_repository import AgentRepository
                from yuxi.storage.postgres.manager import pg_manager
                from yuxi.storage.postgres.models_business import Agent

                async with pg_manager.get_async_session_context() as session:
                    repo = AgentRepository(session)
                    yuxi_agent = await session.get(Agent, yuxi_id)
                    if yuxi_agent:
                        await repo.delete(agent=yuxi_agent)
            except Exception as e:
                logger.warning(f"删除数字警员关联的 yuxi 智能体失败（已保留 police 记录删除）: {e}")
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
                    {**preset, "backend_id": DEFAULT_AGENT_BACKEND_ID}
                )
                await police_agent_repository.add_growth_event(
                    agent.id, "created", f"数字警员 {agent.name} 初始化完成"
                )
                created.append(agent.to_dict())
            else:
                # 存量预设警员：同步最新预设定义（system_prompt/模型/能力/档案字段），
                # 使 Hunter 猎人系列升级方案在重新 seed 时可靠生效。
                # 仅覆盖预设字段，保留用户新增的运行记录等非预设数据。
                await police_agent_repository.update(
                    agent.id,
                    {
                        "name": preset["name"],
                        "description": preset.get("description", ""),
                        "type": preset["type"],
                        "category": preset.get("category"),
                        "specialty": preset.get("specialty", ""),
                        "rank": preset.get("rank", ""),
                        "department": preset.get("department", ""),
                        "avatar": preset.get("avatar", ""),
                        "color_theme": preset.get("color_theme", "blue"),
                        "capabilities": preset.get("capabilities", []),
                        "system_prompt": preset["system_prompt"],
                        "model_config": preset.get("model_config", {}),
                        "is_template": preset.get("is_template", 0),
                    },
                )
                # 重新读取，确保下面同步到 yuxi 时拿到最新字段
                agent = await police_agent_repository.get_by_id(agent.id)
            # 始终同步到 yuxi 主对话智能体（含升级后的 system_prompt/模型参数），
            # 保证前端对话行为反映最新预设定义。
            yuxi_agent = await self._sync_yuxi_agent(agent)
            if yuxi_agent:
                await police_agent_repository.update(
                    agent.id, {"agent_id": yuxi_agent.id, "backend_id": DEFAULT_AGENT_BACKEND_ID}
                )
                synced.append(agent.id)
        return {"created": len(created), "synced": len(synced), "agents": created}

    async def _sync_yuxi_agent(self, agent: "PoliceAgent"):
        """为数字警员创建/更新对应的 yuxi 主对话智能体记录，保持双向字段同步，返回该 Agent。

        数字警员即一等智能体：使用 ChatbotAgent 主对话后端（is_subagent=False），
        slug 直接使用数字警员工号（全局唯一），权限默认为 global（所有民警可见）。
        新建时创建记录；已关联时同步桥接字段与对话配置（system_prompt / model / temperature），
        使前端的编辑操作能实时反映到对话行为。
        """
        from yuxi.repositories.agent_repository import AgentRepository
        from yuxi.storage.postgres.manager import pg_manager
        from yuxi.storage.postgres.models_business import Agent

        model_cfg = agent.model_config or {}
        config_json = {
            "context": {
                "system_prompt": agent.system_prompt or "",
                "model": model_cfg.get("model", "gpt-4o"),
                "temperature": model_cfg.get("temperature", 0.3),
            }
        }
        async with pg_manager.get_async_session_context() as session:
            repo = AgentRepository(session)
            yuxi_agent = None
            # 已通过 agent_id 关联则直接取回，避免按 slug 大小写差异重复创建
            if agent.agent_id:
                yuxi_agent = await session.get(Agent, agent.agent_id)
            # 已存在相同 slug (工号) 的智能体则直接复用
            if not yuxi_agent:
                yuxi_agent = await repo.get_by_slug(agent.badge_number)
            if not yuxi_agent:
                yuxi_agent = await repo.create(
                    name=agent.name,
                    backend_id=DEFAULT_AGENT_BACKEND_ID,
                    slug=agent.badge_number,
                    description=agent.description or agent.specialty or "",
                    icon=agent.avatar,
                    pics=[],
                    config_json=config_json,
                    share_config=None,  # 默认 global，所有民警可见
                    is_subagent=False,
                    created_by="system-police",
                )
            else:
                # 已存在则同步桥接字段与对话配置（含编辑后的 system_prompt / 模型参数）
                yuxi_agent.backend_id = DEFAULT_AGENT_BACKEND_ID
                yuxi_agent.is_subagent = False
                yuxi_agent.name = agent.name
                yuxi_agent.description = agent.description or agent.specialty or ""
                yuxi_agent.icon = agent.avatar
                yuxi_agent.config_json = config_json
                await session.commit()
                await session.refresh(yuxi_agent)
            return yuxi_agent

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

    # ── 共享与市场发布 ─────────────────────────────────────

    async def share_agent(
        self, agent_id: int, *,
        scope: str,  # personal / department / global
        author_id: int | None = None,
        department_ids: list[int] | None = None,
        user_uids: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """设置智能体共享范围。

        - department / global: 标记 is_public=1，使其在市场中可见
        - global: 额外设置 approval_status=pending，需管理员审批后上架
        - personal: 取消公开，从市场撤回
        """
        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent:
            return None

        update_data: dict[str, Any] = {"share_scope": scope}

        if scope in ("department", "global"):
            update_data["is_public"] = 1
            if author_id and not agent.author_id:
                update_data["author_id"] = author_id
            if scope == "global":
                # 全局共享需审批
                update_data["approval_status"] = "pending"
            else:
                # 部门分享直接生效
                update_data["approval_status"] = None
        else:
            # personal → 撤回公开
            update_data["is_public"] = 0
            update_data["approval_status"] = None

        ok = await police_agent_repository.update_share(agent_id, **update_data)
        if not ok:
            return None

        updated = await police_agent_repository.get_by_id(agent_id)
        return updated.to_dict() if updated else None

    async def approve_agent(
        self, agent_id: int, *, approved: bool, reviewer_id: int,
    ) -> dict[str, Any] | None:
        """管理员审批全局共享申请。

        approved=True → approval_status=approved, 正式上架市场
        approved=False → approval_status=rejected, 不上架
        """
        from datetime import datetime as _dt

        agent = await police_agent_repository.get_by_id(agent_id)
        if not agent or agent.approval_status != "pending":
            return None

        status = "approved" if approved else "rejected"
        ok = await police_agent_repository.update_share(
            agent_id,
            approval_status=status,
            approved_by=reviewer_id,
            approved_at=_dt.utcnow() if approved else None,
        )
        if not ok:
            return None

        updated = await police_agent_repository.get_by_id(agent_id)
        return updated.to_dict() if updated else None

    async def list_shared_agents(
        self, *, keyword: str | None = None, page: int = 1, page_size: int = 50,
    ) -> dict[str, Any]:
        """查询「来自分享」的市场智能体列表"""
        agents, total = await police_agent_repository.list_public_shared(
            keyword=keyword, page=page, page_size=page_size,
        )
        installed_ids = await police_agent_repository.get_installed_template_ids()
        return {
            "items": [a.to_dict() for a in agents],
            "total": total,
            "installed_template_ids": installed_ids,
        }


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
