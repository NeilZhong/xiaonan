"""★ 案件独立工作区 API 路由（树状节点版）

工作区以树状节点组织文件/文件夹，支持：
  - 工作区信息 + 树状列表
  - 创建文件夹
  - 上传文件到指定文件夹
  - 下载文件
  - 删除节点（递归删除文件夹）
  - 移动 / 重命名节点
"""

import io
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user
from yuxi.services.police_service import police_workspace_service
from yuxi.storage.postgres.models_business import User

workspace_router = APIRouter(prefix="/police/workspaces", tags=["police-workspaces"])


class CreateFolderBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: int | None = None


class MoveNodeBody(BaseModel):
    node_id: int
    target_parent_id: int | None = None


class RenameNodeBody(BaseModel):
    node_id: int
    name: str = Field(..., min_length=1, max_length=255)


class DeleteNodeBody(BaseModel):
    node_id: int


@workspace_router.get("/{case_id}")
async def get_workspace(
    case_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取案件工作区信息 + 树状节点 + 统计（自动初始化不存在的工作区）"""
    result = await police_workspace_service.get_workspace(case_id)
    if not result:
        raise HTTPException(status_code=404, detail="案件工作区不存在")
    return {"code": 0, "message": "success", "data": result}


@workspace_router.post("/{case_id}/init")
async def init_workspace(
    case_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """强制初始化案件工作区及默认文件夹"""
    ws = await police_workspace_service.get_or_create(case_id)
    return {"code": 0, "message": "success", "data": ws}


@workspace_router.post("/{case_id}/folders")
async def create_folder(
    case_id: int,
    body: CreateFolderBody,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """在工作区创建文件夹"""
    try:
        folder = await police_workspace_service.create_folder(
            case_id, body.name, body.parent_id, current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": folder}


@workspace_router.post("/{case_id}/upload")
async def upload_workspace_file(
    case_id: int,
    file: UploadFile = File(...),
    parent_id: int | None = Query(None, description="目标文件夹节点 ID"),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """上传文件到工作区指定文件夹"""
    try:
        result = await police_workspace_service.upload(case_id, parent_id, file, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": result}


@workspace_router.get("/{case_id}/download")
async def download_workspace_file(
    case_id: int,
    node_id: int = Query(..., description="要下载的文件节点 ID"),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """下载工作区文件（后端流式转发，避免 MinIO 直接暴露）"""
    try:
        data, content_type, filename = await police_workspace_service.download(case_id, node_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"文件不存在: {e}")
    return StreamingResponse(
        io.BytesIO(data),
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@workspace_router.post("/{case_id}/move")
async def move_node(
    case_id: int,
    body: MoveNodeBody,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """移动节点到目标文件夹"""
    try:
        result = await police_workspace_service.move_node(case_id, body.node_id, body.target_parent_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": result}


@workspace_router.post("/{case_id}/rename")
async def rename_node(
    case_id: int,
    body: RenameNodeBody,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """重命名节点"""
    try:
        result = await police_workspace_service.rename_node(case_id, body.node_id, body.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": result}


@workspace_router.delete("/{case_id}/nodes")
async def delete_node(
    case_id: int,
    body: DeleteNodeBody,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """删除节点（文件夹会递归删除）"""
    try:
        ok = await police_workspace_service.delete_node(case_id, body.node_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="节点不存在")
    return {"code": 0, "message": "success"}
