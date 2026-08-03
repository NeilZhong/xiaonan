"""★ 侦查任务模板服务 — 把「涉案要素 → 侦查任务」的映射规则配置化

原先推进智能体把「发现银行卡就该调流水」这类侦查常识写死在 prompt 里，带来三个问题：
  1. 民警无法干预 —— 本单位的办案习惯改不了
  2. 结果不稳定  —— 同样的要素，LLM 每次生成的任务标题/类型/优先级都可能不同
  3. 无法审计    —— 说不清这条任务建议到底依据什么规则产生

本服务将映射规则外置为数据库中的模板：推进智能体只用 LLM 做「要素抽取」，
任务生成走模板匹配（确定性 + 可配置 + 可解释）。模板未覆盖的要素才回落到 LLM 兜底。
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from yuxi.repositories.task_template_repository import task_template_repository
from yuxi.storage.postgres.models_police import (
    ELEMENT_TYPE,
    ELEMENT_TYPE_LABELS,
    TASK_PRIORITY,
)
from yuxi.utils import logger
from yuxi.utils.datetime_utils import utc_now_naive

# 任务类型标签（与前端 typeText 保持一致，供模板表单下拉使用）
TASK_TYPE_LABELS = {
    "transcript_analysis": "笔录分析",
    "fund_analysis": "资金分析",
    "evidence_collection": "调证生成",
    "evidence_submission": "证据提交",
    "legal_review": "法制审核",
    "document_generation": "文书生成",
    "investigation": "侦查",
    "interrogation": "审讯",
    "arrest": "抓捕",
    "cyber_inquiry": "网警查询",
    "knowledge_extraction": "知识抽取",
}

# 建议召唤的数字警员（对应 police_prompts.PRESET_AGENTS 的 type）
AGENT_TYPE_LABELS = {
    "transcript_analyst": "笔录分析师 DA-001",
    "fund_analyst": "资金追踪师 DA-002",
    "evidence_collector": "调证生成师 DA-003",
    "legal_reviewer": "法制审核官 DA-004",
    "case_orchestrator": "案件编排官 DA-005",
    "chat_analyst": "群聊分析专家 DA-006",
    "interrogation_advisor": "审讯辅助专家 DA-007",
}

PLACEHOLDERS = [
    {"key": "{element}", "desc": "要素中文名，如「银行卡/账户」"},
    {"key": "{element_value}", "desc": "要素值，如「6222***1234」"},
    {"key": "{case_title}", "desc": "案件名称"},
    {"key": "{case_number}", "desc": "案件编号"},
    {"key": "{source_task}", "desc": "触发本模板的上游任务标题"},
]


# ── 内置模板：公安侦查常识链 ──────────────────────────────────
# 设计原则：
#   - 要素触发（element_type 非空）：新提取到该类要素时生成任务
#   - 链式触发（element_type 为空）：由上游模板的 next_template_codes 接续
#   - 每条都附「办理指引」，让主办民警审查草案时知道这任务具体怎么落地
BUILTIN_TEMPLATES: list[dict[str, Any]] = [
    # ── 资金链 ──
    {
        "code": "bank_card_flow",
        "name": "银行卡 → 调取账户流水",
        "description": "发现涉案银行卡/账户后，生成调取该账户交易流水的调证任务。",
        "element_type": "bank_card",
        "task_title": "调取涉案银行卡流水（{element_value}）",
        "task_type": "evidence_collection",
        "task_description": "针对涉案账户 {element_value} 调取开户资料及全量交易流水。",
        "instructions": (
            "1. 生成《调取证据通知书》，载明账户号、调取时间区间、调取内容；\n"
            "2. 通过反诈平台/银行专线提交调证；\n"
            "3. 流水回执与电子数据上传至本任务附件，完成后提交审核。"
        ),
        "priority": "high",
        "suggested_agent_type": "evidence_collector",
        "due_days": 3,
        "next_template_codes": ["fund_flow_analysis"],
        "sort_order": 10,
    },
    {
        "code": "fund_flow_analysis",
        "name": "流水到位 → 资金流向分析",
        "description": "银行流水调取完成后，接续生成资金穿透分析任务。",
        "element_type": None,
        "task_title": "资金流水分析（来源：{source_task}）",
        "task_type": "fund_analysis",
        "task_description": "对已调取的账户流水做多层穿透，还原资金真实走向，标记异常交易。",
        "instructions": (
            "1. 召唤「资金追踪师 DA-002」导入流水做穿透分析；\n"
            "2. 重点关注多层嵌套、跨境对敲、虚拟货币混币、空壳通道；\n"
            "3. 输出资金流向图谱与异常交易清单。"
        ),
        "priority": "high",
        "suggested_agent_type": "fund_analyst",
        "due_days": 5,
        "next_template_codes": ["fund_evidence_review"],
        "sort_order": 11,
    },
    {
        "code": "fund_evidence_review",
        "name": "资金分析完成 → 证据链法制审核",
        "description": "资金分析报告出具后，接续生成法制审核任务，把关证据链完整性。",
        "element_type": None,
        "task_title": "资金证据链法制审核（{case_title}）",
        "task_type": "legal_review",
        "task_description": "审核资金证据的合法性、关联性、充分性，识别证据瑕疵。",
        "instructions": (
            "1. 召唤「法制审核官 DA-004」做程序/证据/定性三维审核；\n"
            "2. 逐项核对调证手续是否完备；\n"
            "3. 输出瑕疵清单与整改建议。"
        ),
        "priority": "medium",
        "suggested_agent_type": "legal_reviewer",
        "due_days": 3,
        "next_template_codes": [],
        "sort_order": 12,
    },
    {
        "code": "virtual_currency_trace",
        "name": "虚拟货币地址 → 链上资金追踪",
        "description": "发现虚拟货币钱包地址后，生成链上追踪任务。",
        "element_type": "virtual_currency",
        "task_title": "虚拟货币地址链上追踪（{element_value}）",
        "task_type": "fund_analysis",
        "task_description": "对钱包地址 {element_value} 做链上资金追踪，定位出入金交易所。",
        "instructions": (
            "1. 通过链上分析工具还原资金路径；\n"
            "2. 定位落地交易所并固定 KYC 信息；\n"
            "3. 形成可作为证据的追踪报告。"
        ),
        "priority": "high",
        "suggested_agent_type": "fund_analyst",
        "due_days": 5,
        "next_template_codes": [],
        "sort_order": 13,
    },
    # ── 通联链 ──
    {
        "code": "phone_cdr",
        "name": "手机号 → 调取通话详单",
        "description": "发现涉案手机号后，生成调取通话详单/短信记录的调证任务。",
        "element_type": "phone",
        "task_title": "调取通话详单（{element_value}）",
        "task_type": "evidence_collection",
        "task_description": "调取号码 {element_value} 的机主信息、通话详单与基站定位数据。",
        "instructions": (
            "1. 生成《调取证据通知书》向运营商调证；\n"
            "2. 调取范围含机主实名、通话详单、短信记录、基站轨迹；\n"
            "3. 回执与数据上传本任务附件。"
        ),
        "priority": "high",
        "suggested_agent_type": "evidence_collector",
        "due_days": 3,
        "next_template_codes": ["phone_cdr_analysis"],
        "sort_order": 20,
    },
    {
        "code": "phone_cdr_analysis",
        "name": "详单到位 → 通联关系研判",
        "description": "通话详单调取完成后，接续生成通联关系分析任务。",
        "element_type": None,
        "task_title": "通联关系研判（来源：{source_task}）",
        "task_type": "investigation",
        "task_description": "分析通联频次与时空伴随关系，识别核心关系人与团伙结构。",
        "instructions": (
            "1. 统计高频联系人、异常时段通联；\n"
            "2. 结合基站轨迹做时空伴随分析；\n"
            "3. 输出关系网络图与重点人员清单。"
        ),
        "priority": "medium",
        "suggested_agent_type": None,
        "due_days": 3,
        "next_template_codes": [],
        "sort_order": 21,
    },
    {
        "code": "phone_identity",
        "name": "手机号 → 实名与关联账号核查",
        "description": "对涉案号码做实名核查及互联网账号关联查询。",
        "element_type": "phone",
        "task_title": "手机号实名与关联账号核查（{element_value}）",
        "task_type": "cyber_inquiry",
        "task_description": "核查号码 {element_value} 的实名信息及注册的互联网账号。",
        "instructions": "通过大数据平台发起协查，核实机主身份及名下互联网账号注册情况。",
        "priority": "medium",
        "suggested_agent_type": None,
        "due_days": 2,
        "next_template_codes": [],
        "sort_order": 22,
    },
    # ── 网络账号链 ──
    {
        "code": "social_account_inquiry",
        "name": "社交账号 → 调取注册与登录日志",
        "description": "发现涉案微信/QQ 等社交账号后，生成平台调证任务。",
        "element_type": "wechat",
        "task_title": "调取社交账号注册及登录信息（{element_value}）",
        "task_type": "cyber_inquiry",
        "task_description": "向平台调取账号 {element_value} 的注册资料、绑定手机、登录 IP 日志。",
        "instructions": (
            "1. 通过网安渠道向平台发起调证；\n"
            "2. 调取范围含注册信息、绑定关系、登录 IP/设备指纹；\n"
            "3. 结果上传本任务附件。"
        ),
        "priority": "high",
        "suggested_agent_type": "evidence_collector",
        "due_days": 3,
        "next_template_codes": ["chat_record_analysis"],
        "sort_order": 30,
    },
    {
        "code": "chat_record_analysis",
        "name": "账号信息到位 → 聊天记录研判",
        "description": "社交账号数据到位后，接续生成聊天记录分析任务。",
        "element_type": None,
        "task_title": "聊天记录研判分析（来源：{source_task}）",
        "task_type": "investigation",
        "task_description": "对已获取的聊天记录做实体提取、时间轴重建与暗语识别。",
        "instructions": (
            "1. 召唤「群聊分析专家 DA-006」导入聊天数据；\n"
            "2. 提取人员/时间/地点/物品/行为五要素；\n"
            "3. 识别暗语与角色分工，输出研判报告。"
        ),
        "priority": "medium",
        "suggested_agent_type": "chat_analyst",
        "due_days": 3,
        "next_template_codes": [],
        "sort_order": 31,
    },
    {
        "code": "platform_account_inquiry",
        "name": "平台账号 → 平台数据调取",
        "description": "针对电商/直播/游戏等平台账号发起调证。",
        "element_type": "platform_account",
        "task_title": "调取平台账号数据（{element_value}）",
        "task_type": "cyber_inquiry",
        "task_description": "调取账号 {element_value} 的注册信息、交易记录与资金结算数据。",
        "instructions": "向平台运营方发函调取账号注册、交易、提现结算等数据。",
        "priority": "medium",
        "suggested_agent_type": None,
        "due_days": 3,
        "next_template_codes": [],
        "sort_order": 32,
    },
    {
        "code": "ip_locate",
        "name": "IP 地址 → IP 落地与上网日志",
        "description": "对涉案 IP 做落地查询并调取上网日志。",
        "element_type": "ip",
        "task_title": "IP 落地查询（{element_value}）",
        "task_type": "cyber_inquiry",
        "task_description": "查询 IP {element_value} 的归属地、宽带账号及对应上网日志。",
        "instructions": "通过网安平台落地 IP 归属，调取对应时段的宽带账号与上网日志。",
        "priority": "medium",
        "suggested_agent_type": None,
        "due_days": 3,
        "next_template_codes": [],
        "sort_order": 33,
    },
    # ── 人员链 ──
    {
        "code": "person_control",
        "name": "涉案人员 → 落地查控",
        "description": "发现新的涉案人员后，生成人员落地查控任务。",
        "element_type": "person",
        "task_title": "涉案人员落地查控（{element_value}）",
        "task_type": "investigation",
        "task_description": "核实 {element_value} 的身份信息与实时活动轨迹，具备条件时实施抓捕。",
        "instructions": (
            "1. 核查户籍与常住地信息；\n"
            "2. 通过技侦/大数据平台掌握活动轨迹；\n"
            "3. 具备条件报请审批后实施传唤或抓捕。"
        ),
        "priority": "urgent",
        "suggested_agent_type": None,
        "due_days": 2,
        "next_template_codes": ["person_interrogation"],
        "sort_order": 40,
    },
    {
        "code": "person_interrogation",
        "name": "人员到案 → 讯问并制作笔录",
        "description": "人员落地到案后，接续生成讯问/询问任务。",
        "element_type": None,
        "task_title": "讯问并制作笔录（来源：{source_task}）",
        "task_type": "interrogation",
        "task_description": "依法讯问到案人员，制作笔录并固定关键供述。",
        "instructions": (
            "1. 召唤「审讯辅助专家 DA-007」生成审讯策略与质询问题；\n"
            "2. 依法定程序讯问，全程同步录音录像；\n"
            "3. 笔录扫描件上传本任务附件。"
        ),
        "priority": "high",
        "suggested_agent_type": "interrogation_advisor",
        "due_days": 2,
        "next_template_codes": ["transcript_analysis_followup"],
        "sort_order": 41,
    },
    {
        "code": "transcript_analysis_followup",
        "name": "笔录制作完成 → 笔录分析",
        "description": "笔录到位后，接续生成笔录分析任务，从中挖掘新的涉案要素。",
        "element_type": None,
        "task_title": "笔录分析（来源：{source_task}）",
        "task_type": "transcript_analysis",
        "task_description": "对新制作的笔录做实体提取与矛盾点分析，挖掘新的侦查线索。",
        "instructions": (
            "1. 召唤「笔录分析师 DA-001」导入笔录；\n"
            "2. 多轮笔录交叉比对，标记供述矛盾；\n"
            "3. 输出结构化分析报告（推进智能体将据此继续生成任务）。"
        ),
        "priority": "medium",
        "suggested_agent_type": "transcript_analyst",
        "due_days": 1,
        "next_template_codes": [],
        "sort_order": 42,
    },
    # ── 物证 / 现场链 ──
    {
        "code": "address_surveillance",
        "name": "涉案地址 → 现场核查与监控调取",
        "description": "发现涉案地址/落脚点后，生成现场核查与周边监控调取任务。",
        "element_type": "address",
        "task_title": "现场核查与周边监控调取（{element_value}）",
        "task_type": "investigation",
        "task_description": "对 {element_value} 开展实地核查，调取周边视频监控。",
        "instructions": (
            "1. 实地走访核查该地址的实际使用人；\n"
            "2. 调取案发时段周边监控（注意保存期限，优先处理）；\n"
            "3. 监控截取片段上传本任务附件。"
        ),
        "priority": "high",
        "suggested_agent_type": None,
        "due_days": 3,
        "next_template_codes": [],
        "sort_order": 50,
    },
    {
        "code": "vehicle_track",
        "name": "涉案车辆 → 卡口轨迹调取",
        "description": "发现涉案车辆后，生成车辆轨迹与登记信息调取任务。",
        "element_type": "vehicle",
        "task_title": "涉案车辆轨迹调取（{element_value}）",
        "task_type": "cyber_inquiry",
        "task_description": "调取车辆 {element_value} 的登记信息与卡口过车轨迹。",
        "instructions": "通过交管/卡口系统调取车辆登记信息与案发前后过车记录。",
        "priority": "medium",
        "suggested_agent_type": None,
        "due_days": 3,
        "next_template_codes": [],
        "sort_order": 51,
    },
    {
        "code": "device_forensics",
        "name": "涉案设备 → 电子数据勘验",
        "description": "扣押涉案手机/电脑等设备后，生成电子数据勘验取证任务。",
        "element_type": "device",
        "task_title": "电子数据勘验取证（{element_value}）",
        "task_type": "evidence_collection",
        "task_description": "对扣押设备 {element_value} 依法开展电子数据勘验，固定证据。",
        "instructions": (
            "1. 依法定程序制作《电子数据检查工作记录》；\n"
            "2. 镜像固定后再做分析，保证原始性；\n"
            "3. 计算哈希值并记入证据存证。"
        ),
        "priority": "high",
        "suggested_agent_type": None,
        "due_days": 5,
        "next_template_codes": [],
        "sort_order": 52,
    },
    {
        "code": "company_registry",
        "name": "涉案公司 → 工商与账户信息调取",
        "description": "发现涉案公司/商户后，生成工商登记与对公账户调取任务。",
        "element_type": "company",
        "task_title": "调取涉案公司工商及账户信息（{element_value}）",
        "task_type": "evidence_collection",
        "task_description": "调取 {element_value} 的工商登记资料、股东信息与对公账户流水。",
        "instructions": "向市场监管部门调取工商档案，向开户行调取对公账户开户资料及流水。",
        "priority": "medium",
        "suggested_agent_type": "evidence_collector",
        "due_days": 3,
        "next_template_codes": ["fund_flow_analysis"],
        "sort_order": 53,
    },
    {
        "code": "express_trace",
        "name": "快递单号 → 面单与揽收信息调取",
        "description": "发现涉案快递单号后，生成物流信息调取任务。",
        "element_type": "express",
        "task_title": "调取快递面单及揽收信息（{element_value}）",
        "task_type": "evidence_collection",
        "task_description": "调取快递 {element_value} 的寄递人信息、揽收网点与派送记录。",
        "instructions": "向快递企业调取面单原始信息、揽收网点监控与派件签收记录。",
        "priority": "medium",
        "suggested_agent_type": None,
        "due_days": 3,
        "next_template_codes": [],
        "sort_order": 54,
    },
]


class PoliceTaskTemplateService:
    """侦查任务模板服务"""

    def __init__(self) -> None:
        self._seed_checked = False

    async def _ensure_seeded(self) -> None:
        """首次访问时若模板库为空则自动植入内置模板（进程内只检查一次）。

        与预设数字警员一致，也提供显式 seed 接口供管理员重新植入。
        """
        if self._seed_checked:
            return
        self._seed_checked = True
        try:
            if await task_template_repository.count() == 0:
                await self.ensure_builtin()
        except Exception as e:
            logger.warning(f"Auto-seed task templates failed: {e}")

    # ── 内置模板植入 ────────────────────────────────────────
    async def ensure_builtin(self) -> dict[str, Any]:
        """幂等植入内置模板。

        已存在的模板只补齐空字段，不覆盖民警的定制内容。
        """
        created, kept = 0, 0
        for tpl in BUILTIN_TEMPLATES:
            try:
                existing = await task_template_repository.get_by_code(tpl["code"])
                await task_template_repository.upsert_by_code(tpl["code"], tpl)
                if existing:
                    kept += 1
                else:
                    created += 1
            except Exception as e:
                logger.warning(f"Seed builtin template {tpl['code']} failed: {e}")
        logger.info(f"Task templates seeded: {created} created, {kept} kept")
        return {"created": created, "kept": kept, "total": len(BUILTIN_TEMPLATES)}

    # ── CRUD ────────────────────────────────────────────────
    async def list_templates(
        self,
        element_type: str | None = None,
        enabled_only: bool = False,
        keyword: str | None = None,
    ) -> list[dict[str, Any]]:
        await self._ensure_seeded()
        rows = await task_template_repository.list_templates(
            element_type=element_type, enabled_only=enabled_only, keyword=keyword
        )
        return [r.to_dict() for r in rows]

    async def get(self, template_id: int) -> dict[str, Any] | None:
        row = await task_template_repository.get_by_id(template_id)
        return row.to_dict() if row else None

    async def create(self, data: dict[str, Any], user_id: int | None = None) -> dict[str, Any]:
        payload = dict(data)
        payload.setdefault("code", self._gen_code(payload.get("name", "custom")))
        payload["is_builtin"] = 0
        payload["created_by"] = user_id
        row = await task_template_repository.create(payload)
        return row.to_dict()

    async def update(self, template_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        # code 是内置模板链式引用的锚点，禁止改动
        data = {k: v for k, v in data.items() if k != "code"}
        row = await task_template_repository.update(template_id, data)
        return row.to_dict() if row else None

    async def delete(self, template_id: int) -> tuple[bool, str]:
        row = await task_template_repository.get_by_id(template_id)
        if not row:
            return False, "模板不存在"
        if row.is_builtin == 1:
            return False, "内置模板不可删除，可将其停用"
        ok = await task_template_repository.delete(template_id)
        return ok, "" if ok else "删除失败"

    async def toggle(self, template_id: int, enabled: bool) -> dict[str, Any] | None:
        row = await task_template_repository.update(template_id, {"enabled": 1 if enabled else 0})
        return row.to_dict() if row else None

    # ── 匹配 ────────────────────────────────────────────────
    async def match_by_element(
        self, element_type: str, case=None, source_task=None
    ) -> list[Any]:
        """按要素类型匹配启用中的模板（并过滤案件类型/阶段/触发源任务类型）。"""
        await self._ensure_seeded()
        rows = await task_template_repository.list_templates(
            element_type=element_type, enabled_only=True
        )
        return [r for r in rows if self.is_applicable(r, case, source_task)]

    async def chain_templates(self, codes: list[str], case=None, source_task=None) -> list[Any]:
        """取链式后继模板（上游任务完成后接续）。"""
        rows = await task_template_repository.get_by_codes(codes)
        return [
            r for r in rows if r.enabled == 1 and self.is_applicable(r, case, source_task)
        ]

    def is_applicable(self, template, case=None, source_task=None) -> bool:
        """判断模板在当前案件 / 触发源下是否适用。空列表表示不限制。"""
        case_types = template.case_types or []
        if case_types and case is not None:
            if (getattr(case, "case_type", None) or "") not in case_types:
                return False
        phases = template.phases or []
        if phases and case is not None:
            if (getattr(case, "phase", None) or "") not in phases:
                return False
        source_types = template.source_task_types or []
        if source_types and source_task is not None:
            if (getattr(source_task, "type", None) or "") not in source_types:
                return False
        return True

    # ── 渲染 ────────────────────────────────────────────────
    def build_context(
        self, case=None, source_task=None, element: dict[str, Any] | None = None
    ) -> dict[str, str]:
        element = element or {}
        el_type = element.get("type") or ""
        return {
            "element": element.get("label") or ELEMENT_TYPE_LABELS.get(el_type, el_type) or "线索",
            "element_value": str(element.get("value") or "").strip() or "未标注",
            "case_title": getattr(case, "title", "") or "",
            "case_number": getattr(case, "case_number", "") or "",
            "source_task": getattr(source_task, "title", "") or "",
        }

    def render(self, text: str | None, ctx: dict[str, str]) -> str:
        """占位符渲染；未知占位符原样保留，不因 KeyError 中断。"""
        if not text:
            return ""
        out = text
        for k, v in ctx.items():
            out = out.replace("{" + k + "}", v)
        return out

    def build_task_payload(
        self,
        template,
        *,
        case,
        source_task=None,
        element: dict[str, Any] | None = None,
        origin: str = "template",
    ) -> dict[str, Any]:
        """把模板 + 要素渲染为可直接写库的任务草案 payload。"""
        ctx = self.build_context(case, source_task, element)
        element = element or {}
        basis = (element.get("basis") or "").strip()
        guide = self.render(template.instructions, ctx)
        parts = []
        if basis:
            parts.append(f"【推进依据】{basis}")
        else:
            parts.append(f"【推进依据】依据《{ctx['source_task'] or '上游任务'}》成果，命中模板「{template.name}」")
        if guide:
            parts.append(f"【办理指引】\n{guide}")
        due_date = None
        if template.due_days:
            due_date = utc_now_naive() + timedelta(days=int(template.due_days))
        return {
            "case_id": case.id,
            "title": self.render(template.task_title, ctx)[:200],
            "description": self.render(template.task_description, ctx) or None,
            "type": template.task_type or "investigation",
            "status": "pending_confirmation",
            "creator_type": "agent",
            "creator_id": None,
            "assignee_type": "human",
            "assignee_id": None,
            "priority": template.priority or "medium",
            "phase": getattr(case, "phase", None) or getattr(source_task, "phase", None),
            "instructions": "\n\n".join(parts),
            "due_date": due_date,
            "parent_task_id": getattr(source_task, "id", None),
            "extra": {
                "advancement": {
                    "origin": origin,
                    "template_id": template.id,
                    "template_code": template.code,
                    "template_name": template.name,
                    "element_type": element.get("type"),
                    "element_value": element.get("value"),
                    "source_task_id": getattr(source_task, "id", None),
                    "suggested_agent_type": template.suggested_agent_type,
                    "next_template_codes": template.next_template_codes or [],
                }
            },
        }

    async def preview(self, template_id: int, sample_value: str = "示例值") -> dict[str, Any] | None:
        """模板预览：用示例要素渲染出任务草案，方便民警配置时所见即所得。"""
        row = await task_template_repository.get_by_id(template_id)
        if not row:
            return None
        el_type = row.element_type or "other"
        ctx = self.build_context(
            case=None,
            source_task=None,
            element={"type": el_type, "value": sample_value},
        )
        ctx["case_title"] = ctx["case_title"] or "示例案件"
        ctx["case_number"] = ctx["case_number"] or "XA20260001"
        ctx["source_task"] = ctx["source_task"] or "上游任务"
        return {
            "title": self.render(row.task_title, ctx),
            "description": self.render(row.task_description, ctx),
            "instructions": self.render(row.instructions, ctx),
            "type": row.task_type,
            "type_label": TASK_TYPE_LABELS.get(row.task_type, row.task_type),
            "priority": row.priority,
            "due_days": row.due_days,
            "suggested_agent_type": row.suggested_agent_type,
            "next_template_codes": row.next_template_codes or [],
        }

    # ── 元数据（前端表单用）────────────────────────────────
    async def meta(self) -> dict[str, Any]:
        all_templates = await task_template_repository.list_templates()
        return {
            "element_types": [
                {"value": t, "label": ELEMENT_TYPE_LABELS.get(t, t)} for t in ELEMENT_TYPE
            ],
            "task_types": [
                {"value": k, "label": v} for k, v in TASK_TYPE_LABELS.items()
            ],
            "priorities": [
                {"value": p, "label": {"urgent": "紧急", "high": "高", "medium": "中", "low": "低"}[p]}
                for p in TASK_PRIORITY
            ],
            "agent_types": [
                {"value": k, "label": v} for k, v in AGENT_TYPE_LABELS.items()
            ],
            "placeholders": PLACEHOLDERS,
            "templates": [
                {"code": t.code, "name": t.name} for t in all_templates
            ],
        }

    # ── 工具 ────────────────────────────────────────────────
    @staticmethod
    def _gen_code(name: str) -> str:
        import re
        import uuid

        slug = re.sub(r"[^a-zA-Z0-9_]+", "_", (name or "custom").strip().lower())[:32].strip("_")
        return f"{slug or 'custom'}_{uuid.uuid4().hex[:6]}"


police_task_template_service = PoliceTaskTemplateService()
