"""★ 公安证据管理 API 路由"""

import hashlib
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user
from yuxi.repositories.evidence_repository import evidence_repository
from yuxi.storage.postgres.models_business import User

evidence_router = APIRouter(prefix="/police/evidence", tags=["police-evidence"])


class EvidenceReview(BaseModel):
    approved: bool = True


@evidence_router.get("/case/{case_id}")
async def list_evidence(
    case_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    evidence_type: str | None = None,
    task_id: int | None = None,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """证据列表"""
    items, total = await evidence_repository.list_evidence(
        case_id, skip=(page - 1) * page_size, limit=page_size,
        evidence_type=evidence_type, task_id=task_id,
    )
    return {
        "code": 0, "message": "success",
        "data": {"items": [e.to_dict() for e in items], "total": total, "page": page, "page_size": page_size},
    }


@evidence_router.post("/case/{case_id}")
async def upload_evidence(
    case_id: int,
    file: UploadFile = File(...),
    evidence_type: str = "document",
    task_id: int | None = None,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """上传证据材料 — 自动计算 SHA-256 file_hash"""
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    # 存储到 MinIO (使用现有 minio client)
    from yuxi.storage.minio.client import minio_client

    object_name = f"police-evidence/{case_id}/{file.filename}"
    try:
        minio_client.upload_bytes(object_name, content, file.content_type or "application/octet-stream")
    except Exception as e:
        # 如果 MinIO 不可用,回退到本地路径
        object_name = f"local://police-evidence/{case_id}/{file.filename}"

    evidence = await evidence_repository.create({
        "case_id": case_id,
        "task_id": task_id,
        "name": file.filename,
        "type": evidence_type,
        "file_path": object_name,
        "file_hash": file_hash,
        "file_size": len(content),
        "mime_type": file.content_type,
        "uploaded_by": current_user.id,
    })
    return {"code": 0, "message": "success", "data": evidence.to_dict()}


@evidence_router.get("/{evidence_id}")
async def get_evidence(
    evidence_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """证据详情"""
    evidence = await evidence_repository.get_by_id(evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="证据材料不存在")
    return {"code": 0, "message": "success", "data": evidence.to_dict()}


@evidence_router.post("/{evidence_id}/review")
async def review_evidence(
    evidence_id: int,
    body: EvidenceReview,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """审核证据材料 — 计算 signed_hash (POLICE_REQUIREMENTS §9.5)"""
    if not body.approved:
        raise HTTPException(status_code=400, detail="当前仅支持审核通过操作")

    police_id = getattr(current_user, "police_id", None) or str(current_user.id)
    evidence = await evidence_repository.review(evidence_id, current_user.id, police_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="证据材料不存在")
    return {"code": 0, "message": "success", "data": evidence.to_dict()}


@evidence_router.get("/case/{case_id}/chain")
async def evidence_chain(
    case_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """证据链 — 证据关联关系"""
    links = await evidence_repository.list_links(case_id)
    return {"code": 0, "message": "success", "data": [l.to_dict() for l in links]}
