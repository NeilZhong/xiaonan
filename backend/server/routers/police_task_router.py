"""★ 公安任务管理 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user
from yuxi.repositories.task_repository import task_repository
from yuxi.services.police_service import police_task_service
from yuxi.storage.postgres.models_business import User

task_router = APIRouter(prefix="/police/tasks", tags=["police-tasks"])


class FlowRuleCreate(BaseModel):
    name: str = Field(..., max_length=100)
    trigger_event: str  # task_completed / file_uploaded / phase_changed
    condition: dict = Field(default_factory=dict)  # 触发条件 (JSON规则)
    action: str = "create_task"  # create_task / notify / auto_approve
    target_task_type: str | None = None
    target_assignee_type: str | None = None
    target_assignee_id: int | None = None
    case_id: int | None = None  # NULL=全局规则
    enabled: int = 1


class TaskCreate(BaseModel):
    case_id: int
    title: str = Field(..., max_length=200)
    description: str | None = None
    type: str
    assignee_type: str = "human"
    assignee_id: int | None = None
    assignee_name: str | None = None
    priority: str = "medium"
    phase: str | None = None
    instructions: str | None = None
    due_date: str | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None
    phase: str | None = None
    instructions: str | None = None
    due_date: str | None = None
    status: str | None = None  # 看板拖拽改状态（需为 TASK_STATUS 合法值）


class TaskAssign(BaseModel):
    """任务分配请求（支持多执行人）

    向后兼容：若直接传 assignee_type/assignee_id/assignee_name（单执行人），
    内部自动转为 assignees 数组；新调用方应优先使用 assignees 数组。
    """
    assignees: list[dict] | None = Field(default=None, description="执行人列表，每项 {assignee_type, assignee_id, assignee_name, role?}")
    # 向后兼容单执行人字段
    assignee_type: str | None = Field(default=None, description="单执行人类型（向后兼容）")
    assignee_id: int | None = Field(default=None, description="单执行人ID（向后兼容）")
    assignee_name: str | None = Field(default=None, description="单执行人名称（向后兼容）")


class TaskComplete(BaseModel):
    result: dict | None = None


class TaskReview(BaseModel):
    approved: bool
    comment: str | None = None


@task_router.get("")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    case_id: int | None = None,
    status: str | None = None,
    assignee_type: str | None = None,
    task_type: str | None = None,
    keyword: str | None = None,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """任务列表"""
    result = await police_task_service.list_tasks(
        skip=(page - 1) * page_size,
        limit=page_size,
        case_id=case_id,
        status=status,
        assignee_type=assignee_type,
        task_type=task_type,
        keyword=keyword,
    )
    return {"code": 0, "message": "success", "data": result}


@task_router.get("/my")
async def my_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """我的任务"""
    result = await police_task_service.list_tasks(
        skip=(page - 1) * page_size, limit=page_size, my_tasks_user_id=current_user.id
    )
    return {"code": 0, "message": "success", "data": result}


@task_router.get("/review")
async def review_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """待审核任务"""
    result = await police_task_service.list_tasks(
        skip=(page - 1) * page_size, limit=page_size, review_user_id=current_user.id
    )
    return {"code": 0, "message": "success", "data": result}


@task_router.post("")
async def create_task(
    body: TaskCreate,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """创建任务"""
    data = body.model_dump(exclude_none=True)
    result = await police_task_service.create_task(data, current_user.id)
    return {"code": 0, "message": "success", "data": result}


@task_router.get("/{task_id}")
async def get_task(
    task_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """任务详情"""
    result = await police_task_service.get_task(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"code": 0, "message": "success", "data": result}


@task_router.put("/{task_id}")
async def update_task(
    task_id: int,
    body: TaskUpdate,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """更新任务"""
    data = body.model_dump(exclude_none=True)
    result = await police_task_service.update_task(task_id, data, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"code": 0, "message": "success", "data": result}


@task_router.post("/{task_id}/assign")
async def assign_task(
    task_id: int,
    body: TaskAssign,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """分配任务（支持多人/多智能体协同）"""
    # 统一转为多执行人数组
    if body.assignees is not None:
        assignees = body.assignees
    else:
        # 向后兼容：单执行人字段转数组
        if not body.assignee_type or body.assignee_id is None:
            raise HTTPException(status_code=422, detail="需提供 assignees 数组或单执行人字段")
        assignees = [{
            "assignee_type": body.assignee_type,
            "assignee_id": body.assignee_id,
            "assignee_name": body.assignee_name or "",
            "role": "executor",
        }]
    result = await police_task_service.assign_task_multi(task_id, assignees, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"code": 0, "message": "success", "data": result}


@task_router.post("/{task_id}/start")
async def start_task(
    task_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """开始任务"""
    result = await police_task_service.start_task(task_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"code": 0, "message": "success", "data": result}


@task_router.post("/{task_id}/complete")
async def complete_task(
    task_id: int,
    body: TaskComplete,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """完成任务 (提交审核)"""
    result = await police_task_service.complete_task(task_id, body.result, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"code": 0, "message": "success", "data": result}


@task_router.post("/{task_id}/review")
async def review_task(
    task_id: int,
    body: TaskReview,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """审核任务 (通过/驳回) — 权限校验：仅指定审核人或系统管理员；通过时以真实警号签署"""
    police_id = getattr(current_user, "police_id", None) or str(current_user.id)
    result = await police_task_service.review_task(
        task_id, body.approved, current_user.id, current_user.role, police_id, body.comment
    )
    if not result:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"code": 0, "message": "success", "data": result}


@task_router.get("/{task_id}/events")
async def task_events(
    task_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """任务事件日志"""
    task = await police_task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"code": 0, "message": "success", "data": task.get("events", [])}


# ── 任务流转规则管理 (POLICE_REQUIREMENTS §3.4 / §6 自动流转) ──

@task_router.get("/flow-rules/list")
async def list_flow_rules(
    case_id: int | None = None,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """列出任务流转规则 (含全局规则)"""
    rules = await task_repository.list_flow_rules(case_id)
    return {"code": 0, "message": "success", "data": [r.to_dict() for r in rules]}


@task_router.post("/flow-rules")
async def create_flow_rule(
    body: FlowRuleCreate,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """创建任务流转规则 — 配置完成后，满足条件的任务完成时会自动创建后续任务"""
    rule = await task_repository.create_flow_rule(body.model_dump(exclude_none=True))
    return {"code": 0, "message": "success", "data": rule.to_dict()}


@task_router.delete("/flow-rules/{rule_id}")
async def delete_flow_rule(
    rule_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """删除任务流转规则"""
    ok = await task_repository.delete_flow_rule(rule_id)
    if not ok:
        raise HTTPException(status_code=404, detail="流转规则不存在")
    return {"code": 0, "message": "success", "data": {"deleted": True}}
