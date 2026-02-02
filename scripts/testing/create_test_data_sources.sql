-- 创建测试数据源表和数据
-- 用于任务创建功能的测试

-- 创建 data_sources 表（如果不存在）
CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    source_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    connection_config JSONB NOT NULL DEFAULT '{}',
    schema_config JSONB DEFAULT '{}',
    pool_size INTEGER DEFAULT 5,
    max_overflow INTEGER DEFAULT 10,
    connection_timeout INTEGER DEFAULT 30,
    last_health_check TIMESTAMP WITH TIME ZONE,
    health_check_status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(100)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_data_sources_tenant_type ON data_sources(tenant_id, source_type);

-- 删除现有测试数据（如果存在）
DELETE FROM data_sources WHERE name LIKE 'Test%';

-- 插入测试数据源
INSERT INTO data_sources (
    id, tenant_id, name, description, source_type, status,
    connection_config, schema_config, pool_size, max_overflow,
    connection_timeout, last_health_check, health_check_status,
    created_by, created_at, updated_at
) VALUES
-- 1. Customer Reviews Dataset (CSV)
(
    'a0000001-0000-4000-8000-000000000001'::UUID,
    'default_tenant',
    'Test Customer Reviews Dataset',
    'CSV file containing customer reviews and ratings for testing',
    'local_file',
    'active',
    '{"file_path": "/app/data/test_datasets/customer_reviews.csv", "file_format": "csv", "encoding": "utf-8", "delimiter": ",", "has_header": true}'::JSONB,
    '{"columns": [{"name": "review_id", "type": "string"}, {"name": "customer_id", "type": "string"}, {"name": "product_id", "type": "string"}, {"name": "rating", "type": "integer"}, {"name": "review_text", "type": "text"}, {"name": "review_date", "type": "date"}]}'::JSONB,
    5, 10, 30,
    NOW(), 'healthy',
    'system', NOW(), NOW()
),

-- 2. Product Descriptions API (REST)
(
    'a0000002-0000-4000-8000-000000000002'::UUID,
    'default_tenant',
    'Test Product Descriptions API',
    'REST API endpoint for product descriptions (mock)',
    'rest_api',
    'active',
    '{"base_url": "https://api.example.com/products", "auth_type": "bearer", "auth_token": "test_token_12345", "timeout": 30, "retry_count": 3}'::JSONB,
    '{"endpoints": [{"path": "/products", "method": "GET", "response_format": "json"}, {"path": "/products/{id}", "method": "GET", "response_format": "json"}]}'::JSONB,
    5, 10, 30,
    NOW(), 'healthy',
    'system', NOW(), NOW()
),

-- 3. Support Tickets Database (PostgreSQL)
(
    'a0000003-0000-4000-8000-000000000003'::UUID,
    'default_tenant',
    'Test Support Tickets Database',
    'PostgreSQL database with support ticket data (test)',
    'postgresql',
    'active',
    '{"host": "localhost", "port": 5432, "database": "test_support_db", "username": "test_user", "password": "test_password", "ssl_mode": "prefer"}'::JSONB,
    '{"tables": [{"name": "tickets", "columns": [{"name": "ticket_id", "type": "integer", "primary_key": true}, {"name": "customer_id", "type": "integer"}, {"name": "subject", "type": "varchar(255)"}, {"name": "description", "type": "text"}, {"name": "status", "type": "varchar(50)"}, {"name": "priority", "type": "varchar(20)"}, {"name": "created_at", "type": "timestamp"}]}]}'::JSONB,
    5, 10, 30,
    NOW(), 'healthy',
    'system', NOW(), NOW()
),

-- 4. E-commerce Orders API (GraphQL)
(
    'a0000004-0000-4000-8000-000000000004'::UUID,
    'default_tenant',
    'Test E-commerce Orders API',
    'GraphQL API for e-commerce order data (test)',
    'graphql_api',
    'active',
    '{"endpoint": "https://api.example.com/graphql", "auth_type": "api_key", "api_key": "test_api_key_67890", "timeout": 30}'::JSONB,
    '{"queries": [{"name": "getOrders", "fields": ["orderId", "customerId", "orderDate", "totalAmount", "status"]}, {"name": "getOrderDetails", "fields": ["orderId", "items", "shippingAddress", "paymentMethod"]}]}'::JSONB,
    5, 10, 30,
    NOW(), 'healthy',
    'system', NOW(), NOW()
),

-- 5. Social Media Comments (JSON)
(
    'a0000005-0000-4000-8000-000000000005'::UUID,
    'default_tenant',
    'Test Social Media Comments',
    'JSON file with social media comments for sentiment analysis',
    'local_file',
    'active',
    '{"file_path": "/app/data/test_datasets/social_comments.json", "file_format": "json", "encoding": "utf-8"}'::JSONB,
    '{"structure": {"type": "array", "items": {"comment_id": "string", "user_id": "string", "post_id": "string", "comment_text": "string", "timestamp": "datetime", "likes": "integer", "replies": "integer"}}}'::JSONB,
    5, 10, 30,
    NOW(), 'healthy',
    'system', NOW(), NOW()
),

-- 6. Medical Records Database (MySQL)
(
    'a0000006-0000-4000-8000-000000000006'::UUID,
    'default_tenant',
    'Test Medical Records Database',
    'MySQL database with anonymized medical records (test)',
    'mysql',
    'active',
    '{"host": "localhost", "port": 3306, "database": "test_medical_db", "username": "test_user", "password": "test_password", "charset": "utf8mb4"}'::JSONB,
    '{"tables": [{"name": "patient_records", "columns": [{"name": "record_id", "type": "int", "primary_key": true}, {"name": "patient_id", "type": "varchar(50)"}, {"name": "diagnosis", "type": "text"}, {"name": "treatment", "type": "text"}, {"name": "notes", "type": "text"}, {"name": "record_date", "type": "date"}]}]}'::JSONB,
    5, 10, 30,
    NOW(), 'healthy',
    'system', NOW(), NOW()
),

-- 7. News Articles Feed (RSS/XML)
(
    'a0000007-0000-4000-8000-000000000007'::UUID,
    'default_tenant',
    'Test News Articles Feed',
    'RSS/XML feed with news articles for classification',
    'rest_api',
    'active',
    '{"base_url": "https://news.example.com/feed", "auth_type": "none", "format": "xml", "timeout": 30}'::JSONB,
    '{"feed_structure": {"item": {"title": "string", "description": "string", "link": "string", "pubDate": "datetime", "category": "string", "author": "string"}}}'::JSONB,
    5, 10, 30,
    NOW(), 'healthy',
    'system', NOW(), NOW()
),

-- 8. Financial Transactions (S3)
(
    'a0000008-0000-4000-8000-000000000008'::UUID,
    'default_tenant',
    'Test Financial Transactions',
    'S3 bucket with financial transaction data (CSV)',
    's3',
    'active',
    '{"bucket_name": "test-financial-data", "region": "us-east-1", "access_key_id": "test_access_key", "secret_access_key": "test_secret_key", "prefix": "transactions/", "file_pattern": "*.csv"}'::JSONB,
    '{"file_format": "csv", "columns": [{"name": "transaction_id", "type": "string"}, {"name": "account_id", "type": "string"}, {"name": "amount", "type": "decimal"}, {"name": "currency", "type": "string"}, {"name": "transaction_type", "type": "string"}, {"name": "timestamp", "type": "datetime"}]}'::JSONB,
    5, 10, 30,
    NOW(), 'healthy',
    'system', NOW(), NOW()
);

-- 查询插入的数据
SELECT 
    id,
    name,
    source_type,
    status,
    description
FROM data_sources
WHERE name LIKE 'Test%'
ORDER BY name;

-- 显示统计信息
SELECT 
    source_type,
    COUNT(*) as count
FROM data_sources
WHERE name LIKE 'Test%'
GROUP BY source_type
ORDER BY count DESC;
