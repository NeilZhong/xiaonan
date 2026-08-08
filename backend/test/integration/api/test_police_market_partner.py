"""协助伙伴一等实体集成测试（P5：市场单独添加=建立 binding）。

通过真实前端路径验证：
- 创建协助伙伴 → 市场 apply（partner）应建立 active 绑定（而非仅 equip_guided 引导）；
- 重复 apply 幂等（复用同一连接，不重复插入）；
- /mine 富视图可见该伙伴绑定，且标记 is_subagent=true。

依赖 admin_headers（TEST_USERNAME/TEST_PASSWORD），未配置凭据时由 conftest 自动跳过。
"""
from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def test_market_partner_apply_creates_binding(
    test_client, admin_headers, standard_user,
):
    """市场单独添加协助伙伴应建立 active 绑定（P5 产品模型：添加=绑定）。"""
    unique = uuid.uuid4().hex[:8]
    user_headers = standard_user["headers"]

    partner = await test_client.post(
        "/api/police/partners",
        json={
            "name": f"pytest_p5_partner_{unique}",
            "category": "文书生成",
            "description": "P5 集成测试用协助伙伴",
            "system_prompt": "x",
        },
        headers=admin_headers,
    )
    assert partner.status_code == 200, partner.text
    partner_body = partner.json()
    pid = partner_body["id"]
    partner_slug = partner_body["slug"]

    try:
        # 市场 apply（partner）：应返回 bind 模式并建立连接
        apply = await test_client.post(
            f"/api/police/market/partner/{pid}/apply",
            headers=user_headers,
        )
        assert apply.status_code == 200, apply.text
        body = apply.json()
        assert body.get("mode") == "bind", body
        assert body.get("agent_id") == pid, body

        # /mine 富视图可见该伙伴绑定
        mine = await test_client.get(
            "/api/police/agent-connections/mine", headers=user_headers,
        )
        assert mine.status_code == 200, mine.text
        items = mine.json()["items"]
        conn = next((i for i in items if i["agent_id"] == pid), None)
        assert conn is not None, mine.json()
        assert conn["status"] == "active", conn
        assert conn.get("agent", {}).get("is_subagent") is True, conn

        # 重复 apply 幂等：仍只一条连接
        again = await test_client.post(
            f"/api/police/market/partner/{pid}/apply",
            headers=user_headers,
        )
        assert again.status_code == 200, again.text
        mine2 = await test_client.get(
            "/api/police/agent-connections/mine", headers=user_headers,
        )
        assert mine2.status_code == 200, mine2.text
        same = [i for i in mine2.json()["items"] if i["agent_id"] == pid]
        assert len(same) == 1, mine2.json()

        # 市场 explore 中该伙伴 apply_mode 为 connect（可添加，非 equip_guided 引导）
        # 说明：伙伴为 admin 创建、私有（user 级共享），仅创建者可见，故用 admin_headers 查询
        explore = await test_client.get(
            f"/api/police/market/explore?type=partner&keyword={partner_body['name']}",
            headers=admin_headers,
        )
        assert explore.status_code == 200, explore.text
        hit = next(
            (it for it in explore.json().get("items", []) if it.get("id") == pid), None,
        )
        assert hit is not None, explore.json()
        assert hit.get("apply_mode") == "connect", hit
    finally:
        # 清理：移除用户绑定 → 删除伙伴
        mine = await test_client.get(
            "/api/police/agent-connections/mine", headers=user_headers,
        )
        for it in mine.json().get("items", []):
            if it["agent_id"] == pid:
                await test_client.delete(
                    f"/api/police/agent-connections/{it['id']}", headers=user_headers,
                )
        await test_client.delete(
            f"/api/police/partners/{partner_slug}", headers=admin_headers,
        )
