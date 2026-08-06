"""★ 数字民警办案复盘服务（模块 I.1，借鉴悟帆自进化闭环·改造为待审流）

模式A 任务后反思三环节（顺序 1→2→3，每环节独立判断无产出则跳过）：
  - memory 记忆审计：只记该数字民警对该民警的专属记忆，遵守「不记什么」清单
  - skill  技能沉淀：四条件同满足才生成模板草稿（5+步骤/关键步骤/高复现/未覆盖）
  - profile 用户画像：辩证更新法（观察→质疑→综合），防草率改写
模式B 技能自修复（source=template_audit）：生成修订建议，绝不直接改线上版本

合规红线：所有沉淀产物默认 draft / pending_review，民警确认后才入册（技能沉淀→模板库、
修订建议→新版本+changelog），绝不自动上线。所有写入走审计链路。
"""

from typing import Any

from sqlalchemy import select, func

from yuxi.services.police_service import write_audit_log
from yuxi.services.police_task_template_service import police_task_template_service
from yuxi.storage.postgres.manager import pg_manager
from yuxi.storage.postgres.models_business import User
from yuxi.storage.postgres.models_police import PoliceReflectionRecord
from yuxi.utils.datetime_utils import utc_now_naive

# 记录状态机
STATUS_DRAFT = "draft"
STATUS_PENDING = "pending_review"
STATUS_APPLIED = "applied"
STATUS_REJECTED = "rejected"

# 环节标识
PHASE_MEMORY = "memory"     # 记忆审计
PHASE_SKILL = "skill"       # 技能沉淀
PHASE_PROFILE = "profile"   # 用户画像
PHASE_REPAIR = "repair"     # 技能自修复（修订建议）

# 「不记什么」清单（容量治理/记忆审计红线）
DO_NOT_REMEMBER_KEYWORDS = (
    "临时", "中间过程", "草稿", "待定", "可能", "大概",
)


class PoliceReflectionService:
    """办案复盘：触发 → 待审 → 审阅落库（全程可审计）。"""

    # ── 创建与触发 ─────────────────────────────────────────

    async def create_record(
        self, *, agent_id: int | None, case_id: int | None,
        trigger_type: str, phase: str, source: str,
        payload: dict[str, Any] | None, current_user: User,
    ) -> dict[str, Any]:
        """显式创建一条复盘记录（draft）。触发方（对话/模板审计）调用。"""
        record = PoliceReflectionRecord(
            agent_id=agent_id,
            case_id=case_id,
            trigger_type=trigger_type,
            phase=phase,
            source=source,
            payload=payload or {},
            status=STATUS_DRAFT,
            created_by=current_user.id,
        )
        async with pg_manager.get_async_session_context() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
        await write_audit_log(
            action="reflection.create", resource_type="reflection", resource_id=record.id,
            user_id=current_user.id, user_name=getattr(current_user, "name", None),
            details={"agent_id": agent_id, "case_id": case_id,
                     "trigger_type": trigger_type, "phase": phase},
        )
        return record.to_dict()

    async def trigger_reflection(
        self, *, agent_id: int | None, case_id: int | None,
        conversation_summary: str, current_user: User,
    ) -> dict[str, Any]:
        """任务后反思触发（模式A，MVP 规则化判定）。

        对对话摘要做轻量结构化判定，按需产出 1-3 条记录（memory/skill/profile），
        全部 draft 待民警审阅；LLM 深度抽取为未来扩展（接 police_reflection_repository 时替换）。
        """
        summary = (conversation_summary or "").strip()
        if len(summary) < 20:
            return {"ok": True, "created": 0, "message": "对话过短，跳过复盘"}

        created = 0
        reasons: list[str] = []

        # 环节1 记忆审计：排除「不记什么」后，摘要本身作为候选记忆条目
        if not any(kw in summary for kw in DO_NOT_REMEMBER_KEYWORDS):
            await self.create_record(
                agent_id=agent_id, case_id=case_id, trigger_type="A", phase=PHASE_MEMORY,
                source="conversation",
                payload={
                    "candidate_memory": {
                        "content": summary[:500],
                        "category": "case_note",
                        "action": "add",
                    }
                },
                current_user=current_user,
            )
            created += 1
            reasons.append("记忆审计")

        # 环节2 技能沉淀：满足「含流程/步骤 + 长度足够」才生成模板草稿
        has_process = any(kw in summary for kw in ("步骤", "流程", "先", "再", "最后"))
        if has_process and len(summary) >= 60:
            await self.create_record(
                agent_id=agent_id, case_id=case_id, trigger_type="A", phase=PHASE_SKILL,
                source="conversation",
                payload={
                    "template_draft": {
                        "name": f"复盘沉淀模板 #{utc_now_naive().strftime('%m%d')}",
                        "description": summary[:200],
                        "task_title": summary[:80] or "复盘沉淀任务",
                        "task_type": "review",
                        "instructions": summary[:500],
                        "source_summary": summary,
                    }
                },
                current_user=current_user,
            )
            created += 1
            reasons.append("技能沉淀")

        # 环节3 用户画像：无结构化新观察时跳过（MVP 留接口）
        return {
            "ok": True,
            "created": created,
            "message": f"已沉淀 {created} 条复盘记录（{'、'.join(reasons) or '无'}），待审阅" if created
            else "本次无新沉淀",
        }

    # ── 查询 ─────────────────────────────────────────────

    async def list_records(
        self, *, current_user: User, trigger_type: str | None = None,
        status: str | None = None, page: int = 1, page_size: int = 50,
    ) -> dict[str, Any]:
        """复盘记录列表：本人创建的记录 + 超管可见全部。"""
        async with pg_manager.get_async_session_context() as session:
            stmt = select(PoliceReflectionRecord)
            if current_user.role not in ("admin", "superadmin"):
                stmt = stmt.where(PoliceReflectionRecord.created_by == current_user.id)
            if trigger_type:
                stmt = stmt.where(PoliceReflectionRecord.trigger_type == trigger_type)
            if status:
                stmt = stmt.where(PoliceReflectionRecord.status == status)
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = (await session.execute(count_stmt)).scalar() or 0
            stmt = stmt.order_by(PoliceReflectionRecord.id.desc())
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
            rows = list((await session.execute(stmt)).scalars().all())
        return {"items": [r.to_dict() for r in rows], "total": total, "page": page}

    async def get_record(self, record_id: int) -> dict[str, Any] | None:
        async with pg_manager.get_async_session_context() as session:
            record = await session.get(PoliceReflectionRecord, record_id)
        return record.to_dict() if record else None

    # ── 审阅 ─────────────────────────────────────────────

    async def review_record(
        self, *, record_id: int, action: str, current_user: User,
    ) -> dict[str, Any]:
        """民警审阅：approve→applied（技能沉淀/修订建议落库）；reject→rejected。

        权限：仅该记录的创建者或超管。
        落库规则：
        - phase=skill 且 payload 含 template_draft → 调用模板服务 create 正式入册
        - phase=repair → 修订建议通过后生成新版本（当前 MVP 仅记录，版本落库在模板更新时执行）
        - phase=memory/profile → 仅状态流转（记忆/画像落库走 Memory L1/L2 层，另行接入）
        """
        async with pg_manager.get_async_session_context() as session:
            record = await session.get(PoliceReflectionRecord, record_id)
            if not record:
                raise ValueError("复盘记录不存在")
            if record.created_by != current_user.id and current_user.role not in ("admin", "superadmin"):
                raise PermissionError("仅该记录的创建者或超管可审阅")
            if record.status in (STATUS_APPLIED, STATUS_REJECTED):
                raise ValueError(f"该记录已审阅（{record.status}），不可重复操作")

            approved = action in ("approve", "apply")
            record.status = STATUS_APPLIED if approved else STATUS_REJECTED
            record.reviewed_by = current_user.id
            record.reviewed_at = utc_now_naive()
            await session.commit()
            await session.refresh(record)

        # 审阅通过后的落库动作（在事务外调用其它服务，避免跨表死锁）
        applied_template = None
        if approved and record.phase == PHASE_SKILL:
            draft = (record.payload or {}).get("template_draft")
            if draft:
                applied_template = await police_task_template_service.create(
                    {
                        "name": draft.get("name") or "复盘沉淀模板",
                        "description": draft.get("description"),
                        "task_title": draft.get("task_title") or "复盘沉淀任务",
                        "task_type": draft.get("task_type") or "review",
                        "instructions": draft.get("instructions"),
                        "element_type": draft.get("element_type"),
                    },
                    user_id=current_user.id,
                )

        await write_audit_log(
            action="reflection.review", resource_type="reflection", resource_id=record.id,
            user_id=current_user.id, user_name=getattr(current_user, "name", None),
            details={"action": action, "result_status": record.status,
                     "applied_template_id": applied_template.get("id") if applied_template else None},
        )
        return {
            "ok": True,
            "status": record.status,
            "applied_template": applied_template,
            "message": "已应用并入册" if approved else "已驳回",
        }


police_reflection_service = PoliceReflectionService()
