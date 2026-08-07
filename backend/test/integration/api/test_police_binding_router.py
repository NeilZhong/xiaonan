"""授权绑定与伙伴关联集成测试（P2c）。

通过真实前端路径验证：
- 非共享（私有）数字警员：用户「添加」建立连接后即通过授权可见（绑定非复制）；
- 市场「添加」= 申请使用（apply），已关联协助伙伴的数字警员会级联把伙伴一并加入用户空间；
- 绑定支持版本 pin / unpin、昵称与通知偏好；
- 创建者侧可设置/查看关联协助伙伴。

依赖 admin_headers（TEST_USERNAME/TEST_PASSWORD）与 standard_user fixture，
未配置凭据时由 conftest 的 _require_admin_credentials 自动跳过。
"""
from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def test_connection_grants_visibility_to_private_agent(
    test_client, admin_headers, standard_user,
):
    """私有数字警员在用户「添加」建立连接前不可见，连接后通过授权可见。"""
    unique = uuid.uuid4().hex[:8]
    create = await test_client.post(
        "/api/agent",
        json={"name": f"pytest_bind_officer_{unique}", "system_prompt": "初始提示词"},
        headers=admin_headers,
    )
    assert create.status_code == 200, create.text
    agent = create.json()["agent"]
    aid, slug = agent["id"], agent["slug"]
    user_headers = standard_user["headers"]

    try:
        # 连接前：私有警员对 standard_user 不可见
        before = await test_client.get("/api/agent", headers=user_headers)
        ids_before = [a["id"] for a in before.json().get("agents", [])]
        assert aid not in ids_before, ("私有警员连接前不应可见", ids_before)

        # 申请使用（添加）
        apply = await test_client.post(
            "/api/police/agent-connections",
            json={"agent_id": aid},
            headers=user_headers,
        )
        assert apply.status_code == 200, apply.text
        assert apply.json().get("status") == "active", apply.json()
        assert apply.json().get("agent_id") == aid, apply.json()

        # 连接后：通过授权可见
        after = await test_client.get("/api/agent", headers=user_headers)
        ids_after = [a["id"] for a in after.json().get("agents", [])]
        assert aid in ids_after, ("连接后应通过授权可见", ids_after)

        # /mine 可见该绑定
        mine = await test_client.get("/api/police/agent-connections/mine", headers=user_headers)
        assert mine.status_code == 200, mine.text
        assert any(i["agent_id"] == aid for i in mine.json()["items"]), mine.json()
    finally:
        # 清理：移除用户绑定，再删除警员
        mine = await test_client.get("/api/police/agent-connections/mine", headers=user_headers)
        for it in mine.json().get("items", []):
            if it["agent_id"] == aid:
                await test_client.delete(
                    f"/api/police/agent-connections/{it['id']}", headers=user_headers,
                )
        await test_client.delete(f"/api/agent/{slug}", headers=admin_headers)


async def test_associate_partners_cascade_and_pin(
    test_client, admin_headers,
):
    """关联协助伙伴后申请使用应级联添加伙伴；绑定支持 pin/unpin 与偏好设置。"""
    unique = uuid.uuid4().hex[:8]
    officer = await test_client.post(
        "/api/agent",
        json={"name": f"pytest_cascade_officer_{unique}", "system_prompt": "x"},
        headers=admin_headers,
    )
    assert officer.status_code == 200, officer.text
    officer_body = officer.json()["agent"]
    aid, officer_slug = officer_body["id"], officer_body["slug"]

    partner = await test_client.post(
        "/api/police/partners",
        json={"name": f"pytest_partner_{unique}", "category": "文书生成", "system_prompt": "x"},
        headers=admin_headers,
    )
    assert partner.status_code == 200, partner.text
    partner_body = partner.json()
    pid, partner_id = partner_body["id"], partner_body["id"]
    partner_slug = partner_body["slug"]

    try:
        # 设置关联伙伴
        assoc = await test_client.put(
            f"/api/police/agents/{aid}/associate-partners",
            json={"partner_ids": [pid]},
            headers=admin_headers,
        )
        assert assoc.status_code == 200, assoc.text
        assert set(assoc.json()["partner_ids"]) == {pid}, assoc.json()

        # 查看关联伙伴
        listed = await test_client.get(
            f"/api/police/agents/{aid}/associate-partners", headers=admin_headers,
        )
        assert listed.status_code == 200 and listed.json()["total"] == 1, listed.json()

        # 申请使用（级联伙伴）
        apply = await test_client.post(
            "/api/police/agent-connections",
            json={"agent_id": aid},
            headers=admin_headers,
        )
        assert apply.status_code == 200, apply.text
        assert pid in apply.json().get("cascaded_partner_ids", []), apply.json()

        # /mine 应含两条（警员 + 级联伙伴）
        mine = await test_client.get("/api/police/agent-connections/mine", headers=admin_headers)
        assert mine.status_code == 200, mine.text
        assert len(mine.json()["items"]) == 2, mine.json()

        conn_id = next(i["id"] for i in mine.json()["items"] if i["agent_id"] == aid)

        # 版本 pin / unpin
        ver = await test_client.get(f"/api/police/agents/{aid}/versions", headers=admin_headers)
        assert ver.status_code == 200, ver.text
        cur = ver.json()["current_version_id"]
        assert cur, ("无当前版本", ver.json())
        pin = await test_client.post(
            f"/api/police/agent-connections/{conn_id}/pin",
            json={"version_id": cur},
            headers=admin_headers,
        )
        assert pin.status_code == 200 and pin.json()["pinned_version_id"] == cur, pin.text
        unpin = await test_client.delete(
            f"/api/police/agent-connections/{conn_id}/pin", headers=admin_headers,
        )
        assert unpin.status_code == 200 and unpin.json()["pinned_version_id"] is None, unpin.text

        # 偏好设置
        prefs = await test_client.patch(
            f"/api/police/agent-connections/{conn_id}",
            json={"nickname": "我的测试警员", "notify_new_version": False},
            headers=admin_headers,
        )
        assert prefs.status_code == 200, prefs.text
        assert prefs.json()["nickname"] == "我的测试警员", prefs.json()
        assert prefs.json()["notify_new_version"] is False, prefs.json()
    finally:
        # 清理：移除全部连接 → 清空关联伙伴 → 删除警员与伙伴
        mine = await test_client.get("/api/police/agent-connections/mine", headers=admin_headers)
        for it in mine.json().get("items", []):
            await test_client.delete(
                f"/api/police/agent-connections/{it['id']}", headers=admin_headers,
            )
        await test_client.put(
            f"/api/police/agents/{aid}/associate-partners",
            json={"partner_ids": []},
            headers=admin_headers,
        )
        await test_client.delete(f"/api/agent/{officer_slug}", headers=admin_headers)
        await test_client.delete(f"/api/police/partners/{partner_id}", headers=admin_headers)
