"""★ 案件独立工作区 API 路由

证据 / 材料 / 研判报告等产物统一存储到案件专属 MinIO 命名空间
(cases/{case_number}/)，本路由提供工作区信息查询、文件浏览、上传、下载、删除。
"""

import io
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user
from yuxi.services.police_service import police_workspace_service
from yuxi.storage.postgres.models_business import User

workspace_router = APIRouter(prefix="/police/workspaces", tags=["police-workspaces"])


class DeleteFileBody(BaseModel):
    object_name: str


@workspace_router.get("/{case_id}")
async def get_workspace(
    case_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """获取案件工作区信息 + 文件清单 + 统计 (自动初始化不存在的工作区)"""
    # 确保工作区存在 (兼容历史案件)
    await police_workspace_service.get_or_create(case_id)
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
    """强制初始化案件工作区"""
    ws = await police_workspace_service.get_or_create(case_id)
    return {"code": 0, "message": "success", "data": ws}


@workspace_router.post("/{case_id}/upload")
async def upload_workspace_file(
    case_id: int,
    file: UploadFile = File(...),
    category: str = Query("materials", description="文件分类: evidence/materials/reports"),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """上传文件到工作区指定分类目录 (材料 / 报告)"""
    try:
        result = await police_workspace_service.upload(case_id, category, file, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "message": "success", "data": result}


@workspace_router.get("/{case_id}/download")
async def download_workspace_file(
    case_id: int,
    object_name: str = Query(..., description="工作区对象路径"),
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """下载工作区文件 (后端流式转发，避免 MinIO 直接暴露)"""
    try:
        data, content_type, filename = await police_workspace_service.download(case_id, object_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"文件不存在: {e}")
    return StreamingResponse(
        io.BytesIO(data),
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@workspace_router.delete("/{case_id}/files")
async def delete_workspace_file(
    case_id: int,
    body: DeleteFileBody,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """删除工作区文件"""
    try:
        ok = await police_workspace_service.delete_file(case_id, body.object_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail="文件不存在")
    return {"code": 0, "message": "success"}
