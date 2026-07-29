"""★ 公安任务管理 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user
from yuxi.services.police_service import police_task_service
from yuxi.storage.postgres.models_business import User

task_router = APIRouter(prefix="/police/tasks", tags=["police-tasks"])


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


class TaskAssign(BaseModel):
    assignee_type: str  # human/agent
    assignee_id: int
    assignee_name: str


class TaskComplete(BaseModel):
    result: dict | None = None


class TaskReview(BaseModel):
    approved: bool
    comment: str | None = None


@task_router.get("")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
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
    """分配任务"""
    result = await police_task_service.assign_task(
        task_id, body.assignee_type, body.assignee_id, body.assignee_name, current_user.id
    )
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
    """审核任务 (通过/驳回) — 通过时自动计算 signed_hash"""
    police_id = getattr(current_user, "police_id", None) or str(current_user.id)
    result = await police_task_service.review_task(
        task_id, body.approved, current_user.id, police_id
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
