"""★ 公安证据管理 API 路由"""

import hashlib
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_required_user
from yuxi.repositories.evidence_repository import evidence_repository
from yuxi.services.police_service import police_workspace_service, write_audit_log
from yuxi.storage.minio.client import get_minio_client
from yuxi.storage.postgres.models_business import User
from yuxi.utils import logger

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
    """上传证据材料 — 自动计算 SHA-256 file_hash，并统一落入案件工作区"""
    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    # 存储到 MinIO — 统一落入案件工作区 cases/{case_number}/evidence/
    object_name = ""
    try:
        ws = await police_workspace_service.get_or_create(case_id)
        object_name = f"{ws['storage_prefix']}evidence/{file.filename}"
        await get_minio_client().aupload_file(
            ws["storage_bucket"], object_name, content,
            file.content_type or "application/octet-stream",
        )
    except Exception as e:
        # 如果 MinIO 不可用,记录告警并保留哈希 (best-effort, 不阻断上传记录)
        logger.warning(f"Evidence upload to MinIO failed: {e}")

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
    # 同步到案件工作区「证据」文件夹
    try:
        await police_workspace_service.sync_evidence_node(case_id, evidence)
    except Exception as e:
        logger.warning(f"Sync evidence to workspace failed: {e}")
    # 审计日志: 证据上传 (POLICE_REQUIREMENTS §9.4)
    await write_audit_log(
        action="upload", resource_type="evidence", resource_id=evidence.id,
        case_id=case_id, user_id=current_user.id,
        user_name=getattr(current_user, "real_name", None),
        details={"name": file.filename, "type": evidence_type, "file_hash": file_hash},
    )
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
    # 审计日志: 证据审核确认 (POLICE_REQUIREMENTS §9.4/§9.5)
    await write_audit_log(
        action="review", resource_type="evidence", resource_id=evidence_id,
        case_id=evidence.case_id, user_id=current_user.id,
        user_name=getattr(current_user, "real_name", None),
        details={"approved": body.approved, "signed_hash": evidence.signed_hash},
    )
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


@evidence_router.get("/{evidence_id}/download")
async def download_evidence(
    evidence_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """下载证据材料 — 从 MinIO 取回原始文件流"""
    evidence = await evidence_repository.get_by_id(evidence_id)
    if not evidence or not evidence.file_path:
        raise HTTPException(status_code=404, detail="证据材料或存储路径不存在")
    try:
        bucket = police_workspace_service.WORKSPACE_BUCKET
        data = await get_minio_client().adownload_file(bucket, evidence.file_path)
    except Exception as e:
        logger.warning(f"Download evidence {evidence_id} from MinIO failed: {e}")
        raise HTTPException(status_code=502, detail="证据文件读取失败，存储服务不可用")
    return Response(
        content=data,
        media_type=evidence.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename=\"{evidence.name}\""},
    )


@evidence_router.get("/{evidence_id}/preview")
async def preview_evidence(
    evidence_id: int,
    current_user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    """在线预览证据材料 — 与下载相同文件流，但以内联方式展示（浏览器直接打开）"""
    evidence = await evidence_repository.get_by_id(evidence_id)
    if not evidence or not evidence.file_path:
        raise HTTPException(status_code=404, detail="证据材料或存储路径不存在")
    try:
        bucket = police_workspace_service.WORKSPACE_BUCKET
        data = await get_minio_client().adownload_file(bucket, evidence.file_path)
    except Exception as e:
        logger.warning(f"Preview evidence {evidence_id} from MinIO failed: {e}")
        raise HTTPException(status_code=502, detail="证据文件读取失败，存储服务不可用")
    return Response(content=data, media_type=evidence.mime_type or "application/octet-stream")
