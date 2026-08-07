"""治理后台集成测试（P3：审核台 + 运行中心）。

覆盖 /api/police/admin/* 全部端点：
- 运行中心：平台默认运行模式读写、非法值拒绝、状态总览字段完整；
- 审核台：全局共享申请进入待审列表、详情含全量配置、通过后授警号、重复审核被拒；
- 预览试跑：空内容拒绝；模型环境不可用时不阻断审核（接口可达即通过）；
- 权限：普通用户访问治理接口一律被拒。

依赖 admin_headers（TEST_USERNAME/TEST_PASSWORD，须为超级管理员）与 standard_user fixture，
未配置凭据时由 conftest 的 _require_admin_credentials 自动跳过。
"""
from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

RUNTIME_CONFIG = "/api/police/admin/runtime-config"


async def _create_officer(test_client, admin_headers) -> tuple[int, str]:
    """建一个数字警员，返回 (id, slug)。"""
    unique = uuid.uuid4().hex[:8]
    resp = await test_client.post(
        "/api/agent",
        json={"name": f"pytest_gov_officer_{unique}", "system_prompt": "你是一名笔录分析警员。"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    agent = resp.json()["agent"]
    return agent["id"], agent["slug"]


async def _find_in_overview(test_client, admin_headers, agent_id: int) -> dict | None:
    """状态总览按 id 升序分页（page_size 上限 100），逐页找到目标警员那一行。"""
    page, page_size = 1, 100
    while True:
        resp = await test_client.get(
            "/api/police/admin/runtime-overview",
            params={"page": page, "page_size": page_size},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        hit = next((i for i in body["items"] if i["id"] == agent_id), None)
        if hit or page * page_size >= body["total"]:
            return hit
        page += 1


async def test_runtime_config_read_write_and_validation(test_client, admin_headers):
    """平台默认运行模式可读可写，非法值被拒，读回一致。"""
    read = await test_client.get(RUNTIME_CONFIG, headers=admin_headers)
    assert read.status_code == 200, read.text
    original = read.json()["default_release_mode"]
    assert original in ("rolling", "controlled"), read.json()

    try:
        bad = await test_client.put(
            RUNTIME_CONFIG, json={"default_release_mode": "bogus"}, headers=admin_headers,
        )
        assert bad.status_code == 400, ("非法运行模式应被拒", bad.status_code, bad.text)

        target = "rolling" if original == "controlled" else "controlled"
        ok = await test_client.put(
            RUNTIME_CONFIG, json={"default_release_mode": target}, headers=admin_headers,
        )
        assert ok.status_code == 200, ok.text
        assert ok.json()["default_release_mode"] == target, ok.json()

        again = await test_client.get(RUNTIME_CONFIG, headers=admin_headers)
        assert again.json()["default_release_mode"] == target, again.json()
    finally:
        await test_client.put(
            RUNTIME_CONFIG, json={"default_release_mode": original}, headers=admin_headers,
        )


async def test_review_pipeline_and_runtime_overview(test_client, admin_headers):
    """全局共享申请 → 待审列表 → 详情 → 试跑 → 通过授警号 → 幂等；总览含该警员。"""
    aid, slug = await _create_officer(test_client, admin_headers)

    try:
        share = await test_client.post(
            f"/api/police/agents/{aid}/share", json={"scope": "global"}, headers=admin_headers,
        )
        assert share.status_code == 200, share.text

        pending = await test_client.get(
            "/api/police/admin/review/pending", params={"page_size": 100}, headers=admin_headers,
        )
        assert pending.status_code == 200, pending.text
        item = next((i for i in pending.json()["items"] if i["id"] == aid), None)
        assert item is not None, ("待审列表应包含该警员", pending.json())
        assert item["request_type"] == "agent", item
        assert item["share_level"] == "global", item

        detail = await test_client.get(f"/api/police/admin/review/{aid}", headers=admin_headers)
        assert detail.status_code == 200, detail.text
        body = detail.json()
        assert body["agent"]["id"] == aid, body["agent"]
        assert body["runtime"]["system_prompt"], ("详情应含系统提示词", body["runtime"])
        assert body["release_mode"] in ("rolling", "controlled"), body

        # 试跑：空内容必须拒绝；正常内容在模型不可用时允许 502（不阻断审核）
        empty = await test_client.post(
            f"/api/police/admin/review/{aid}/preview", json={"message": "   "}, headers=admin_headers,
        )
        assert empty.status_code == 400, ("空试跑内容应被拒", empty.status_code, empty.text)

        preview = await test_client.post(
            f"/api/police/admin/review/{aid}/preview",
            json={"message": "请用一句话自我介绍。"},
            headers=admin_headers,
        )
        assert preview.status_code in (200, 502), preview.text
        if preview.status_code == 200:
            assert preview.json()["config_source"] in ("draft", "current"), preview.json()
            assert preview.json()["model"], ("应回显真实生效模型", preview.json())

        decide = await test_client.post(
            f"/api/police/admin/review/agent/{aid}/decide",
            json={"approved": True, "reason": "配置合规，准予上架"},
            headers=admin_headers,
        )
        assert decide.status_code == 200, decide.text
        assert decide.json()["status"] == "approved", decide.json()

        after = await test_client.get(f"/api/police/admin/review/{aid}", headers=admin_headers)
        assert after.json()["agent"]["approval_status"] == "approved", after.json()["agent"]
        assert after.json()["agent"]["badge_number"], ("通过后应授警号", after.json()["agent"])

        repeat = await test_client.post(
            f"/api/police/admin/review/agent/{aid}/decide",
            json={"approved": True}, headers=admin_headers,
        )
        assert repeat.status_code == 400, ("重复审核应被拒", repeat.status_code, repeat.text)

        row = await _find_in_overview(test_client, admin_headers, aid)
        assert row is not None, "总览应包含该警员"
        assert row["release_mode"] in ("rolling", "controlled"), row
        assert row["binding_count"] >= 0 and "draft_pending" in row, row
    finally:
        await test_client.delete(f"/api/agent/{slug}", headers=admin_headers)


async def test_review_detail_404_for_missing_agent(test_client, admin_headers):
    """不存在的智能体详情应 404，而非 500。"""
    resp = await test_client.get("/api/police/admin/review/99999999", headers=admin_headers)
    assert resp.status_code == 404, (resp.status_code, resp.text)


async def test_governance_requires_superadmin(test_client, standard_user):
    """普通用户访问治理后台任一端点都应被拒。"""
    headers = standard_user["headers"]
    cases = [
        ("GET", "/api/police/admin/review/pending", None),
        ("GET", RUNTIME_CONFIG, None),
        ("GET", "/api/police/admin/runtime-overview", None),
        ("PUT", RUNTIME_CONFIG, {"default_release_mode": "rolling"}),
    ]
    for method, path, body in cases:
        resp = await test_client.request(method, path, headers=headers, json=body)
        assert resp.status_code in (401, 403), (path, resp.status_code, resp.text)
