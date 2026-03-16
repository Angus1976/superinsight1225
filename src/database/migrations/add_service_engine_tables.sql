-- Migration: Add Smart Service Engine tables
-- Description: Creates user_memories and webhook_configs tables,
--              extends api_keys with service engine fields.

-- ============================================================================
-- 1. Create user_memories table
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    tenant_id VARCHAR(36) NOT NULL,
    memory_type VARCHAR(20) NOT NULL,
    content JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_memories_user_tenant
    ON user_memories (user_id, tenant_id);

COMMENT ON TABLE user_memories IS 'User interaction memory for Smart Service Engine';
COMMENT ON COLUMN user_memories.memory_type IS 'interaction or summary';

-- ============================================================================
-- 2. Create webhook_configs table
-- ============================================================================
CREATE TABLE IF NOT EXISTS webhook_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    webhook_url VARCHAR(500) NOT NULL,
    webhook_secret VARCHAR(255) NOT NULL,
    webhook_events JSONB NOT NULL DEFAULT '[]',
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_webhook_configs_api_key_id
    ON webhook_configs (api_key_id);

COMMENT ON TABLE webhook_configs IS 'Webhook push configuration (MVP reserved)';

-- ============================================================================
-- 3. Extend api_keys table with service engine fields
-- ============================================================================
ALTER TABLE api_keys
    ADD COLUMN IF NOT EXISTS allowed_request_types JSONB NOT NULL DEFAULT '["query","chat","decision","skill"]';

ALTER TABLE api_keys
    ADD COLUMN IF NOT EXISTS skill_whitelist JSONB NOT NULL DEFAULT '[]';

ALTER TABLE api_keys
    ADD COLUMN IF NOT EXISTS webhook_config JSONB DEFAULT NULL;
