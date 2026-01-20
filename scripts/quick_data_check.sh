#!/bin/bash

# 快速数据检查脚本
# 验证数据库中是否有数据

set -e

# 配置
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-superinsight}"
DB_NAME="${DB_NAME:-superinsight}"
DB_PASSWORD="${DB_PASSWORD:-password}"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}SuperInsight 数据快速检查${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 检查数据库连接
echo -e "${BLUE}检查数据库连接...${NC}"
if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 数据库连接成功${NC}\n"
else
    echo -e "${RED}❌ 数据库连接失败${NC}"
    echo -e "${YELLOW}请确保 PostgreSQL 正在运行${NC}"
    exit 1
fi

# 检查用户表
echo -e "${BLUE}检查用户表...${NC}"
user_count=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ')
if [ "$user_count" -gt 0 ]; then
    echo -e "${GREEN}✅ 用户表中有 $user_count 条记录${NC}"
    echo -e "${BLUE}用户列表:${NC}"
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT username, email FROM users;" 2>/dev/null
else
    echo -e "${YELLOW}⚠️  用户表为空${NC}"
fi
echo ""

# 检查项目表
echo -e "${BLUE}检查项目表...${NC}"
project_count=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM projects;" 2>/dev/null | tr -d ' ')
if [ "$project_count" -gt 0 ]; then
    echo -e "${GREEN}✅ 项目表中有 $project_count 条记录${NC}"
    echo -e "${BLUE}项目列表:${NC}"
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT name, status FROM projects;" 2>/dev/null
else
    echo -e "${YELLOW}⚠️  项目表为空${NC}"
fi
echo ""

# 检查任务表
echo -e "${BLUE}检查标注任务表...${NC}"
task_count=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM annotation_tasks;" 2>/dev/null | tr -d ' ')
if [ "$task_count" -gt 0 ]; then
    echo -e "${GREEN}✅ 标注任务表中有 $task_count 条记录${NC}"
    echo -e "${BLUE}任务列表:${NC}"
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT name, status, total_items, completed_items FROM annotation_tasks;" 2>/dev/null
else
    echo -e "${YELLOW}⚠️  标注任务表为空${NC}"
fi
echo ""

# 检查数据集表
echo -e "${BLUE}检查数据集表...${NC}"
dataset_count=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -t -c "SELECT COUNT(*) FROM datasets;" 2>/dev/null | tr -d ' ')
if [ "$dataset_count" -gt 0 ]; then
    echo -e "${GREEN}✅ 数据集表中有 $dataset_count 条记录${NC}"
    echo -e "${BLUE}数据集列表:${NC}"
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT name, size FROM datasets;" 2>/dev/null
else
    echo -e "${YELLOW}⚠️  数据集表为空${NC}"
fi
echo ""

# 总结
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}数据统计${NC}"
echo -e "${BLUE}========================================${NC}"
echo "用户: $user_count"
echo "项目: $project_count"
echo "任务: $task_count"
echo "数据集: $dataset_count"
echo ""

# 检查是否需要生成数据
if [ "$user_count" -eq 0 ] || [ "$project_count" -eq 0 ] || [ "$task_count" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  数据不完整，需要生成演示数据${NC}"
    echo -e "${BLUE}运行以下命令生成演示数据:${NC}"
    echo "  docker compose exec superinsight-api python scripts/seed_demo_data.py"
    exit 1
else
    echo -e "${GREEN}✅ 所有数据都已入库，可以开始测试${NC}"
    exit 0
fi
