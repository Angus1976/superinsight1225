-- ============================================================
-- SuperInsight Sealos 种子数据
-- 在 schema.sql 执行完成后执行
-- ============================================================

-- Alembic 版本记录（防止后端启动时重复迁移）
INSERT INTO public.alembic_version VALUES ('033_add_api_key_and_call_log_tables');
INSERT INTO public.alembic_version VALUES ('011_add_progress_info');
INSERT INTO public.alembic_version VALUES ('009_llm_app_binding');
INSERT INTO public.alembic_version VALUES ('037_add_ai_workflows');

-- Demo 用户数据
-- 密码: admin@superinsight.local → admin123
-- 密码: 其他账号 → Demo@2026
INSERT INTO public.users VALUES ('9a5d8773-5fcd-4c02-9abd-33fbc5ca138a', 'admin@superinsight.local', 'admin', 'Administrator', NULL, NULL, true, true, true, '$2b$12$8m2tGLdZL9d.N6QFvaof7u4Z7C1ubJoQXu9we/D0zjzdHc.o8zlua', NULL, NULL, NULL, NULL, 'UTC', 'en', '2026-01-27 12:37:23.930518', '2026-03-20 01:36:20.98025', '2026-03-20 02:21:16.474783', NULL, NULL, 'admin', 'default_tenant', NULL);
INSERT INTO public.users VALUES ('73d83204-a6f8-4edc-ab2f-958ce68a7ce1', 'manager@superinsight.local', 'data_manager', '数据管理员', NULL, NULL, true, true, false, '$2b$12$ikP.px4ISbxZt/VZBMszdOMFfH1/nDw.rLKI6AsMVabLrAthNFhGy', NULL, NULL, NULL, NULL, 'Asia/Shanghai', 'zh', '2026-03-20 00:42:59.02018', '2026-03-20 01:34:45.373227', '2026-03-20 01:34:44.843238', NULL, NULL, 'data_manager', 'default_tenant', NULL);
INSERT INTO public.users VALUES ('8e1cf683-e66a-4b6a-bd9f-2a5872a12f8f', 'expert@superinsight.local', 'business_expert', '业务专家', NULL, NULL, true, true, false, '$2b$12$U4dGghOf/uvhGxuaKoLDKeriPQNIu9Sul70cp3e2RiPFr0GSzEeJ2', NULL, NULL, NULL, NULL, 'Asia/Shanghai', 'zh', '2026-03-20 00:42:59.02018', '2026-03-20 00:42:59.02018', NULL, NULL, NULL, 'business_expert', 'default_tenant', NULL);
INSERT INTO public.users VALUES ('822d0c38-5f0d-4edb-8779-dd44d3d5a479', 'editor@superinsight.local', 'editor', '编辑员', NULL, NULL, true, true, false, '$2b$12$U4dGghOf/uvhGxuaKoLDKeriPQNIu9Sul70cp3e2RiPFr0GSzEeJ2', NULL, NULL, NULL, NULL, 'Asia/Shanghai', 'zh', '2026-03-20 00:42:59.02018', '2026-03-20 00:42:59.02018', NULL, NULL, NULL, 'editor', 'default_tenant', NULL);
INSERT INTO public.users VALUES ('b45be49d-b067-4396-bc21-278004f376e8', 'viewer@superinsight.local', 'viewer', '只读用户', NULL, NULL, true, true, false, '$2b$12$U4dGghOf/uvhGxuaKoLDKeriPQNIu9Sul70cp3e2RiPFr0GSzEeJ2', NULL, NULL, NULL, NULL, 'Asia/Shanghai', 'zh', '2026-03-20 00:42:59.02018', '2026-03-20 00:42:59.02018', NULL, NULL, NULL, 'viewer', 'default_tenant', NULL);
