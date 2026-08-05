"""★ 侦查任务模板 API 路由 (POLICE_REQUIREMENTS §6.7 任务模板配置化)

把「涉案要素 → 侦查任务」的映射规则开放给民警配置：
  - 模板增删改查 / 启停
  - 内置模板重新植入
  - 表单元数据（要素类型 / 任务类型 / 优先级 / 数字警员 / 占位符）
  - 模板效果预览（所见即所得）
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_admin_user, get_db, get_required_user, get_admin_user
from yuxi.services.police_task_template_service import police_task_template_service
from yuxi.storage.postgres.models_business import User

task_template_router = APIRouter(prefix="/police/task-templates", tags=["police-task-templates"])


class TemplateCreate(BaseModel):
    name: str
    description: str | None = None
    element_type: str | None = None
    case_types: list[str] = []
    phases: list[str] = []
    source_task_types: list[str] = []
    task_title: str
    task_type: str
    task_description: str | None = None
    instructions: str | None = None
    priority: str = "medium"
    suggested_agent_type: str | None = None
    due_days: int | None = None
    next_template_codes: list[str] = []
    enabled: int = 1
    sort_order: int = 100


class TemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    element_type: str | None = None
    case_types: list[str] | None = None
    phases: list[str] | None = None
    source_task_types: list[str] | None = None
    task_title: str | None = None
    task_type: str | None = None
    task_description: str | None = None
    instructions: str | None = None
    priority: str | None = None
    suggested_agent_type: str | None = None
    due_days: int | None = None
    next_template_codes: list[str] | None = None
    enabled: int | None = None
    sort_order: int | None = None


class TemplateToggle(BaseModel):
    enabled: bool


class TemplatePreview(BaseModel):
    sample_value: str = "示例值"


@task_template_router.get("/meta")
async def template_meta(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """模板表单元数据：要素类型、任务类型、优先级、数字警员、占位符说明。"""
    return {"code": 0, "message": "success", "data": await police_task_template_service.meta()}


@task_template_router.post("/seed")
async def seed_templates(
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """重新植入内置模板（幂等：已存在的只补空字段，不覆盖民警的定制）。"""
    result = await police_task_template_service.ensure_builtin()
    return {"code": 0, "message": "success", "data": result}


@task_template_router.get("")
async def list_templates(
    element_type: str | None = None,
    enabled_only: bool = False,
    keyword: str | None = None,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """模板列表（首次访问且库为空时自动植入内置模板）。"""
    data = await police_task_template_service.list_templates(
        element_type=element_type, enabled_only=enabled_only, keyword=keyword
    )
    return {"code": 0, "message": "success", "data": data, "total": len(data)}


@task_template_router.post("")
async def create_template(
    body: TemplateCreate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """新建自定义模板。"""
    if not body.task_title.strip():
        raise HTTPException(status_code=422, detail="任务标题模板不能为空")
    data = await police_task_template_service.create(body.model_dump(), current_user.id)
    return {"code": 0, "message": "success", "data": data}


@task_template_router.get("/{template_id}")
async def get_template(
    template_id: int,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    data = await police_task_template_service.get(template_id)
    if not data:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"code": 0, "message": "success", "data": data}


@task_template_router.put("/{template_id}")
async def update_template(
    template_id: int,
    body: TemplateUpdate,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """更新模板（内置模板可改内容，但 code 不可变，以免破坏链式引用）。"""
    payload = {k: v for k, v in body.model_dump().items() if v is not None}
    if not payload:
        raise HTTPException(status_code=422, detail="没有需要更新的字段")
    data = await police_task_template_service.update(template_id, payload)
    if not data:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"code": 0, "message": "success", "data": data}


@task_template_router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """删除自定义模板（内置模板只能停用，不能删除）。"""
    ok, err = await police_task_template_service.delete(template_id)
    if not ok:
        raise HTTPException(status_code=400 if err else 404, detail=err or "模板不存在")
    return {"code": 0, "message": "success", "data": {"id": template_id}}


@task_template_router.post("/{template_id}/toggle")
async def toggle_template(
    template_id: int,
    body: TemplateToggle,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """启用 / 停用模板。停用后推进智能体不再用它生成任务。"""
    data = await police_task_template_service.toggle(template_id, body.enabled)
    if not data:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"code": 0, "message": "success", "data": data}


@task_template_router.post("/{template_id}/preview")
async def preview_template(
    template_id: int,
    body: TemplatePreview,
    current_user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """预览模板渲染效果（用示例要素值填充占位符）。"""
    data = await police_task_template_service.preview(template_id, body.sample_value)
    if not data:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"code": 0, "message": "success", "data": data}
