-- ============================================================================
-- 单表化迁移：police_agents 并入 agents，之后删除 police_agents
--
-- 背景：智能体在平台内具有唯一性，agents 表成为唯一数据源。
--   - 可见性统一由 agents.share_config.access_level 决定（user/department/global）
--   - 全局共享需超级管理员审核：approval_status = pending -> approved
--   - 警号 badge_number 仅在全局审核通过时授予，普通创建/部门共享一律留空
--
-- 幂等性：脚本可重复执行。若 police_agents 已不存在则整体跳过。
-- 事务性：全程单事务，任一步失败自动回滚。
-- ============================================================================

BEGIN;

DO $$
DECLARE
    v_preset_pattern CONSTANT text := '^DA-[0-9]{3}$';  -- 平台预设警号格式，如 DA-001
    v_merged   int := 0;
    v_inserted int := 0;
    v_runs     int := 0;
    v_comments int := 0;
BEGIN
    IF to_regclass('public.police_agents') IS NULL THEN
        RAISE NOTICE '[skip] police_agents 不存在，迁移已完成过';
        RETURN;
    END IF;

    -- ── 1. 已关联的数字警员：档案字段合并进对应 agents 行 ──────────────
    -- 平台预设（警号形如 DA-001）视为官方智能体：全局可见 + 已审核 + 保留警号。
    -- 其余记录按新规则不授予警号，可见性收敛为私有，由用户重新分享。
    UPDATE agents a SET
        badge_number       = CASE WHEN p.badge_number ~ v_preset_pattern THEN p.badge_number END,
        rank               = p.rank,
        specialty          = p.specialty,
        department         = p.department,
        color_theme        = p.color_theme,
        icon_key           = p.icon,
        category           = p.category,
        agent_type         = p.type,
        status             = COALESCE(p.status, 'active'),
        experience_level   = COALESCE(p.experience_level, 1),
        system_prompt      = p.system_prompt,
        model_config       = p.model_config,
        tools              = COALESCE(p.tools, '[]'::json),
        skills             = COALESCE(p.skills, '[]'::json),
        knowledge_base_ids = COALESCE(p.knowledge_base_ids, '[]'::json),
        sop_ids            = COALESCE(p.sop_ids, '[]'::json),
        capabilities       = COALESCE(p.capabilities, '[]'::json),
        work_stats         = COALESCE(p.work_stats, '{}'::json),
        growth_log         = COALESCE(p.growth_log, '[]'::json),
        icon               = COALESCE(p.avatar, a.icon),
        approval_status    = CASE WHEN p.badge_number ~ v_preset_pattern THEN 'approved' END,
        share_config       = CASE
                                WHEN p.badge_number ~ v_preset_pattern
                                THEN '{"access_level":"global","department_ids":[],"user_uids":[]}'::json
                                ELSE a.share_config
                             END,
        updated_at         = NOW()
    FROM police_agents p
    WHERE p.agent_id = a.id;
    GET DIAGNOSTICS v_merged = ROW_COUNT;

    -- ── 2. 未关联 yuxi 智能体的孤儿记录：新建 agents 行，不丢数据 ────────
    -- slug 用 officer-legacy-{旧id}，便于第 3 步反解出映射关系。
    INSERT INTO agents (
        slug, backend_id, name, description, icon, pics, config_json, share_config,
        is_default, is_subagent,
        badge_number, rank, specialty, department, color_theme, icon_key,
        category, agent_type, status, experience_level,
        system_prompt, model_config, tools, skills, knowledge_base_ids, sop_ids, capabilities,
        work_stats, growth_log, created_at, updated_at
    )
    SELECT
        'officer-legacy-' || p.id,
        COALESCE(NULLIF(p.backend_id, ''), 'ChatbotAgent'),
        p.name,
        p.description,
        p.avatar,
        '[]'::json,
        json_build_object('context', json_build_object(
            'system_prompt', COALESCE(p.system_prompt, ''),
            'model',       COALESCE(p.model_config ->> 'model', 'gpt-4o'),
            'temperature', COALESCE((p.model_config ->> 'temperature')::float, 0.3)
        )),
        -- 新规则：未经分享的智能体仅创建者可见；此处无可靠 uid，先收敛为空白名单
        '{"access_level":"user","department_ids":[],"user_uids":[]}'::json,
        false, false,
        NULL,                                   -- 警号：未经全局审核不授予
        p.rank, p.specialty, p.department, p.color_theme, p.icon,
        p.category, p.type, COALESCE(p.status, 'active'), COALESCE(p.experience_level, 1),
        p.system_prompt, p.model_config,
        COALESCE(p.tools, '[]'::json), COALESCE(p.skills, '[]'::json),
        COALESCE(p.knowledge_base_ids, '[]'::json), COALESCE(p.sop_ids, '[]'::json),
        COALESCE(p.capabilities, '[]'::json),
        COALESCE(p.work_stats, '{}'::json), COALESCE(p.growth_log, '[]'::json),
        p.created_at, p.updated_at
    FROM police_agents p
    WHERE p.agent_id IS NULL
      AND NOT EXISTS (SELECT 1 FROM agents x WHERE x.slug = 'officer-legacy-' || p.id);
    GET DIAGNOSTICS v_inserted = ROW_COUNT;

    -- ── 3. 建立 旧 police_agents.id -> 新 agents.id 映射 ────────────────
    CREATE TEMP TABLE _pa_map ON COMMIT DROP AS
        SELECT p.id AS old_id, p.agent_id AS new_id
        FROM police_agents p
        WHERE p.agent_id IS NOT NULL
        UNION ALL
        SELECT split_part(a.slug, '-', 3)::int AS old_id, a.id AS new_id
        FROM agents a
        WHERE a.slug LIKE 'officer-legacy-%';

    -- ── 4. 关联表外键改指 agents.id ─────────────────────────────────────
    ALTER TABLE police_agent_runs     DROP CONSTRAINT IF EXISTS police_agent_runs_agent_id_fkey;
    ALTER TABLE police_agent_comments DROP CONSTRAINT IF EXISTS police_agent_comments_agent_id_fkey;

    UPDATE police_agent_runs r SET agent_id = m.new_id
    FROM _pa_map m WHERE r.agent_id = m.old_id;
    GET DIAGNOSTICS v_runs = ROW_COUNT;

    UPDATE police_agent_comments c SET agent_id = m.new_id
    FROM _pa_map m WHERE c.agent_id = m.old_id;
    GET DIAGNOSTICS v_comments = ROW_COUNT;

    -- 清理无法映射的残留引用，避免加外键时失败
    DELETE FROM police_agent_comments c
    WHERE NOT EXISTS (SELECT 1 FROM agents a WHERE a.id = c.agent_id);
    UPDATE police_agent_runs r SET agent_id = NULL
    WHERE r.agent_id IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM agents a WHERE a.id = r.agent_id);

    ALTER TABLE police_agent_runs
        ADD CONSTRAINT police_agent_runs_agent_id_fkey
        FOREIGN KEY (agent_id) REFERENCES agents(id);
    ALTER TABLE police_agent_comments
        ADD CONSTRAINT police_agent_comments_agent_id_fkey
        FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE;

    -- ── 5. 删除旧表 ─────────────────────────────────────────────────────
    DROP TABLE police_agents CASCADE;

    RAISE NOTICE '[done] 合并 % 行 / 新建 % 行 / runs 改指 % 行 / comments 改指 % 行',
        v_merged, v_inserted, v_runs, v_comments;
END $$;

COMMIT;
