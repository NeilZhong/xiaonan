"""数字警员版本与运行模式集成测试（P2b）。

通过真实前端路径 /api/agent 验证：
- 运行模式默认受控发布（controlled）；
- 保存（创建/更新）自动生成版本快照；
- 受控模式下更新进入草稿（draft），初始版本发布为当前版本（active/current）。

依赖 standard_user fixture（需要 TEST_USERNAME/TEST_PASSWORD 配置，未配置时整体跳过）。
"""
from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def test_digital_officer_default_controlled_and_autosnapshot(
    test_client, standard_user,
):
    headers = standard_user["headers"]
    unique = uuid.uuid4().hex[:8]
    name = f"pytest_version_officer_{unique}"

    # 1) 创建数字警员（真实前端路径 /api/agent）
    create = await test_client.post(
        "/api/agent",
        json={"name": name, "type": "test_officer", "system_prompt": "初始提示词"},
        headers=headers,
    )
    assert create.status_code == 200, create.text
    agent = create.json()["agent"]
    aid, slug = agent["id"], agent["slug"]

    try:
        # 2) 初始版本应已发布为当前版本，且运行模式默认受控
        ver = await test_client.get(f"/api/police/agents/{aid}/versions")
        assert ver.status_code == 200, ver.text
        body = ver.json()
        assert body["release_mode"] == "controlled", "默认运行模式应为受控发布"
        assert body["total"] >= 1, "创建后应生成初始版本基线"
        assert body["current_version_id"] is not None, "初始版本应发布为当前版本"

        # 3) 更新提示词 → 受控模式下生成 draft 版本（current 不变，直至发布）
        upd = await test_client.put(
            f"/api/agent/{slug}",
            json={"system_prompt": "更新后的提示词"},
            headers=headers,
        )
        assert upd.status_code == 200, upd.text
        ver2 = await test_client.get(f"/api/police/agents/{aid}/versions")
        body2 = ver2.json()
        assert body2["total"] >= 2, "更新后应再生成一个版本"
        drafts = [v for v in body2["items"] if v["status"] == "draft"]
        assert drafts, "受控模式下更新应生成 draft 版本"

        # 4) 运行模式开关自检
        sw = await test_client.post(
            f"/api/police/agents/{aid}/switch-mode",
            json={"mode": "rolling"},
            headers=headers,
        )
        assert sw.status_code == 200 and sw.json()["release_mode"] == "rolling"
        sw2 = await test_client.post(
            f"/api/police/agents/{aid}/switch-mode",
            json={"mode": "controlled"},
            headers=headers,
        )
        assert sw2.status_code == 200 and sw2.json()["release_mode"] == "controlled"
    finally:
        # 清理临时数字警员
        await test_client.delete(f"/api/agent/{slug}", headers=headers)
