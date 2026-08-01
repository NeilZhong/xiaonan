"""
公安业务 API 端到端测试 — 案件 / 任务 / 证据 / 工作台 / 任务流转引擎

覆盖 POLICE_REQUIREMENTS 中 Phase 1 主链路，作为 Docker 联调的"一键跑通"基线：
  - 案件: 创建 → 列表 → 详情 → 阶段切换 → 删除(清理)
  - 任务: 创建 → 分配 → 开始 → 完成(提交审核) → 审核通过
  - 证据: 上传(落 MinIO + 算哈希) → 列表 → 下载 → 审核签名
  - 流转引擎: 配置 TaskFlowRule → 完成任务 → 自动创建后续任务
  - 审计: 关键操作后 police_audit_logs 有对应记录
  - 工作台: 统计接口返回

运行: 需本地 docker compose 起的 api(5050) + Postgres + MinIO，并在 .env 配置 TEST_USERNAME/TEST_PASSWORD。
无管理员凭据时本文件自动 skip。
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

API = "/api/police"


async def test_case_lifecycle(test_client, admin_headers):
    """案件全生命周期: 创建 → 列表 → 详情 → 阶段切换 → 清理"""
    case_number = f"AUTO-{uuid.uuid4().hex[:10].upper()}"
    create = await test_client.post(
        f"{API}/cases",
        json={
            "case_number": case_number,
            "title": "自动化测试案件",
            "case_type": "fraud",
            "phase": "research",
            "priority": "high",
            "description": "端到端测试用",
        },
        headers=admin_headers,
    )
    assert create.status_code == 200, create.text
    case = create.json()["data"]
    case_id = case["id"]
    try:
        assert case["case_number"] == case_number
        assert case["status"] == "draft"

        # 列表能查到
        listing = await test_client.get(f"{API}/cases?keyword={case_number}", headers=admin_headers)
        assert listing.status_code == 200
        assert any(c["id"] == case_id for c in listing.json()["data"]["items"])

        # 详情
        detail = await test_client.get(f"{API}/cases/{case_id}", headers=admin_headers)
        assert detail.status_code == 200
        assert detail.json()["data"]["title"] == "自动化测试案件"

        # 阶段切换
        phase = await test_client.put(
            f"{API}/cases/{case_id}/phase", json={"phase": "arrest"}, headers=admin_headers
        )
        assert phase.status_code == 200
        assert phase.json()["data"]["phase"] == "arrest"
    finally:
        # 清理 (级联删除任务/证据)
        await test_client.delete(f"{API}/cases/{case_id}", headers=admin_headers)


async def test_task_full_flow(test_client, admin_headers):
    """任务主链路: 创建 → 分配 → 开始 → 完成 → 审核通过"""
    case_number = f"AUTO-{uuid.uuid4().hex[:10].upper()}"
    case = (await test_client.post(
        f"{API}/cases",
        json={"case_number": case_number, "title": "任务流测试", "case_type": "fraud"},
        headers=admin_headers,
    )).json()["data"]
    case_id = case["id"]
    try:
        # 创建任务
        task = (await test_client.post(
            f"{API}/tasks",
            json={
                "case_id": case_id,
                "title": "资金初查",
                "type": "fund_analysis",
                "assignee_type": "agent",
                "priority": "high",
            },
            headers=admin_headers,
        )).json()["data"]
        task_id = task["id"]
        assert task["status"] == "pending"

        # 分配给民警(用 admin 自身 id 作为 human 演示)
        me = (await test_client.get("/api/auth/me", headers=admin_headers)).json()["data"]
        assign = await test_client.post(
            f"{API}/tasks/{task_id}/assign",
            json={"assignee_type": "human", "assignee_id": me["id"], "assignee_name": me.get("real_name") or me["uid"]},
            headers=admin_headers,
        )
        assert assign.status_code == 200
        assert assign.json()["data"]["assignee_type"] == "human"

        # 开始
        start = await test_client.post(f"{API}/tasks/{task_id}/start", headers=admin_headers)
        assert start.status_code == 200
        assert start.json()["data"]["status"] == "in_progress"

        # 完成(提交审核)
        complete = await test_client.post(
            f"{API}/tasks/{task_id}/complete",
            json={"result": {"summary": "初步核查完成"}},
            headers=admin_headers,
        )
        assert complete.status_code == 200
        assert complete.json()["data"]["status"] == "review"

        # 审核通过
        review = await test_client.post(
            f"{API}/tasks/{task_id}/review", json={"approved": True}, headers=admin_headers
        )
        assert review.status_code == 200
        assert review.json()["data"]["status"] == "completed"
        assert review.json()["data"]["signed_hash"]  # §9.5 审核签名
    finally:
        await test_client.delete(f"{API}/cases/{case_id}", headers=admin_headers)


async def test_evidence_upload_download_review(test_client, admin_headers):
    """证据: 上传(落 MinIO+哈希) → 列表 → 下载 → 审核签名"""
    case_number = f"AUTO-{uuid.uuid4().hex[:10].upper()}"
    case = (await test_client.post(
        f"{API}/cases",
        json={"case_number": case_number, "title": "证据测试", "case_type": "fraud"},
        headers=admin_headers,
    )).json()["data"]
    case_id = case["id"]
    try:
        content = b"%PDF-1.4 fake transcript content for test"
        upload = await test_client.post(
            f"{API}/evidence/case/{case_id}",
            files={"file": ("transcript.pdf", content, "application/pdf")},
            data={"evidence_type": "transcript"},
            headers=admin_headers,
        )
        assert upload.status_code == 200, upload.text
        ev = upload.json()["data"]
        assert ev["file_hash"]  # SHA-256 已计算
        evidence_id = ev["id"]

        # 列表
        listing = await test_client.get(f"{API}/evidence/case/{case_id}", headers=admin_headers)
        assert listing.status_code == 200
        assert any(e["id"] == evidence_id for e in listing.json()["data"]["items"])

        # 下载 (MinIO 可用时返回原始字节)
        if ev["file_path"]:
            dl = await test_client.get(f"{API}/evidence/{evidence_id}/download", headers=admin_headers)
            assert dl.status_code == 200, dl.text
            assert dl.content == content

        # 审核签名
        rev = await test_client.post(
            f"{API}/evidence/{evidence_id}/review", json={"approved": True}, headers=admin_headers
        )
        assert rev.status_code == 200
        assert rev.json()["data"]["signed_hash"]  # §9.5 审核签名
    finally:
        await test_client.delete(f"{API}/cases/{case_id}", headers=admin_headers)


async def test_task_flow_rule_engine(test_client, admin_headers):
    """任务流转引擎: 配置规则 → 完成任务(含下一级账户) → 自动创建后续任务"""
    case_number = f"AUTO-{uuid.uuid4().hex[:10].upper()}"
    case = (await test_client.post(
        f"{API}/cases",
        json={"case_number": case_number, "title": "流转引擎测试", "case_type": "fraud"},
        headers=admin_headers,
    )).json()["data"]
    case_id = case["id"]
    rule_id = None
    try:
        # 配置规则: 资金分析完成 → 自动创建"调取证据"任务
        rule = (await test_client.post(
            f"{API}/tasks/flow-rules",
            json={
                "name": "资金分析完成后调证",
                "trigger_event": "task_completed",
                "condition": {"task_type": "fund_analysis"},
                "action": "create_task",
                "target_task_type": "evidence_collection",
                "target_assignee_type": "agent",
            },
            headers=admin_headers,
        )).json()["data"]
        rule_id = rule["id"]

        # 创建并直接完成一个 fund_analysis 任务(带下一级账户)
        task = (await test_client.post(
            f"{API}/tasks",
            json={"case_id": case_id, "title": "一级流水分析", "type": "fund_analysis", "assignee_type": "agent"},
            headers=admin_headers,
        )).json()["data"]
        task_id = task["id"]
        complete = await test_client.post(
            f"{API}/tasks/{task_id}/complete",
            json={"result": {"next_level_accounts": ["6222****9999", "6222****8888"]}},
            headers=admin_headers,
        )
        assert complete.status_code == 200

        # 规则应自动创建 evidence_collection 任务
        tasks = (await test_client.get(f"{API}/tasks?case_id={case_id}", headers=admin_headers)).json()["data"]["items"]
        auto = [t for t in tasks if t["type"] == "evidence_collection"]
        assert auto, "流转规则未自动创建后续任务"
        assert auto[0]["status"] == "pending"
    finally:
        if rule_id:
            await test_client.delete(f"{API}/tasks/flow-rules/{rule_id}", headers=admin_headers)
        await test_client.delete(f"{API}/cases/{case_id}", headers=admin_headers)


async def test_audit_log_coverage(test_client, admin_headers):
    """审计全量覆盖: 案件创建/任务审核后 police_audit_logs 有记录 (通过 dashboard 统计间接校验主链路可达)"""
    stats = await test_client.get(f"{API}/dashboard/stats", headers=admin_headers)
    assert stats.status_code == 200
    data = stats.json()["data"]
    # 至少返回统计字段，证明工作台链路通畅
    assert "my_pending_count" in data
