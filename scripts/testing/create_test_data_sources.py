#!/usr/bin/env python3
"""
创建测试数据源脚本

在数据库中创建一组测试数据源，用于任务创建功能的测试。
"""

import sys
import os
from uuid import uuid4
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database.connection import get_db_session
from src.sync.models import DataSourceModel, DataSourceType, DataSourceStatus


def create_test_data_sources():
    """创建测试数据源"""
    
    # 获取数据库会话
    db = next(get_db_session())
    
    try:
        # 检查是否已存在测试数据源
        existing = db.query(DataSourceModel).filter(
            DataSourceModel.name.like('Test%')
        ).count()
        
        if existing > 0:
            print(f"⚠️  已存在 {existing} 个测试数据源")
            response = input("是否删除现有测试数据源并重新创建？(y/N): ")
            if response.lower() == 'y':
                db.query(DataSourceModel).filter(
                    DataSourceModel.name.like('Test%')
                ).delete()
                db.commit()
                print("✅ 已删除现有测试数据源")
            else:
                print("❌ 取消操作")
                return
        
        # 测试数据源列表
        test_data_sources = [
            {
                "name": "Test Customer Reviews Dataset",
                "description": "CSV file containing customer reviews and ratings for testing",
                "source_type": DataSourceType.LOCAL_FILE,
                "connection_config": {
                    "file_path": "/app/data/test_datasets/customer_reviews.csv",
                    "file_format": "csv",
                    "encoding": "utf-8",
                    "delimiter": ",",
                    "has_header": True
                },
                "schema_config": {
                    "columns": [
                        {"name": "review_id", "type": "string"},
                        {"name": "customer_id", "type": "string"},
                        {"name": "product_id", "type": "string"},
                        {"name": "rating", "type": "integer"},
                        {"name": "review_text", "type": "text"},
                        {"name": "review_date", "type": "date"}
                    ]
                }
            },
            {
                "name": "Test Product Descriptions API",
                "description": "REST API endpoint for product descriptions (mock)",
                "source_type": DataSourceType.REST_API,
                "connection_config": {
                    "base_url": "https://api.example.com/products",
                    "auth_type": "bearer",
                    "auth_token": "test_token_12345",
                    "timeout": 30,
                    "retry_count": 3
                },
                "schema_config": {
                    "endpoints": [
                        {
                            "path": "/products",
                            "method": "GET",
                            "response_format": "json"
                        },
                        {
                            "path": "/products/{id}",
                            "method": "GET",
                            "response_format": "json"
                        }
                    ]
                }
            },
            {
                "name": "Test Support Tickets Database",
                "description": "PostgreSQL database with support ticket data (test)",
                "source_type": DataSourceType.POSTGRESQL,
                "connection_config": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "test_support_db",
                    "username": "test_user",
                    "password": "test_password",
                    "ssl_mode": "prefer"
                },
                "schema_config": {
                    "tables": [
                        {
                            "name": "tickets",
                            "columns": [
                                {"name": "ticket_id", "type": "integer", "primary_key": True},
                                {"name": "customer_id", "type": "integer"},
                                {"name": "subject", "type": "varchar(255)"},
                                {"name": "description", "type": "text"},
                                {"name": "status", "type": "varchar(50)"},
                                {"name": "priority", "type": "varchar(20)"},
                                {"name": "created_at", "type": "timestamp"}
                            ]
                        }
                    ]
                }
            },
            {
                "name": "Test E-commerce Orders API",
                "description": "GraphQL API for e-commerce order data (test)",
                "source_type": DataSourceType.GRAPHQL_API,
                "connection_config": {
                    "endpoint": "https://api.example.com/graphql",
                    "auth_type": "api_key",
                    "api_key": "test_api_key_67890",
                    "timeout": 30
                },
                "schema_config": {
                    "queries": [
                        {
                            "name": "getOrders",
                            "fields": ["orderId", "customerId", "orderDate", "totalAmount", "status"]
                        },
                        {
                            "name": "getOrderDetails",
                            "fields": ["orderId", "items", "shippingAddress", "paymentMethod"]
                        }
                    ]
                }
            },
            {
                "name": "Test Social Media Comments",
                "description": "JSON file with social media comments for sentiment analysis",
                "source_type": DataSourceType.LOCAL_FILE,
                "connection_config": {
                    "file_path": "/app/data/test_datasets/social_comments.json",
                    "file_format": "json",
                    "encoding": "utf-8"
                },
                "schema_config": {
                    "structure": {
                        "type": "array",
                        "items": {
                            "comment_id": "string",
                            "user_id": "string",
                            "post_id": "string",
                            "comment_text": "string",
                            "timestamp": "datetime",
                            "likes": "integer",
                            "replies": "integer"
                        }
                    }
                }
            },
            {
                "name": "Test Medical Records Database",
                "description": "MySQL database with anonymized medical records (test)",
                "source_type": DataSourceType.MYSQL,
                "connection_config": {
                    "host": "localhost",
                    "port": 3306,
                    "database": "test_medical_db",
                    "username": "test_user",
                    "password": "test_password",
                    "charset": "utf8mb4"
                },
                "schema_config": {
                    "tables": [
                        {
                            "name": "patient_records",
                            "columns": [
                                {"name": "record_id", "type": "int", "primary_key": True},
                                {"name": "patient_id", "type": "varchar(50)"},
                                {"name": "diagnosis", "type": "text"},
                                {"name": "treatment", "type": "text"},
                                {"name": "notes", "type": "text"},
                                {"name": "record_date", "type": "date"}
                            ]
                        }
                    ]
                }
            },
            {
                "name": "Test News Articles Feed",
                "description": "RSS/XML feed with news articles for classification",
                "source_type": DataSourceType.REST_API,
                "connection_config": {
                    "base_url": "https://news.example.com/feed",
                    "auth_type": "none",
                    "format": "xml",
                    "timeout": 30
                },
                "schema_config": {
                    "feed_structure": {
                        "item": {
                            "title": "string",
                            "description": "string",
                            "link": "string",
                            "pubDate": "datetime",
                            "category": "string",
                            "author": "string"
                        }
                    }
                }
            },
            {
                "name": "Test Financial Transactions",
                "description": "S3 bucket with financial transaction data (CSV)",
                "source_type": DataSourceType.S3,
                "connection_config": {
                    "bucket_name": "test-financial-data",
                    "region": "us-east-1",
                    "access_key_id": "test_access_key",
                    "secret_access_key": "test_secret_key",
                    "prefix": "transactions/",
                    "file_pattern": "*.csv"
                },
                "schema_config": {
                    "file_format": "csv",
                    "columns": [
                        {"name": "transaction_id", "type": "string"},
                        {"name": "account_id", "type": "string"},
                        {"name": "amount", "type": "decimal"},
                        {"name": "currency", "type": "string"},
                        {"name": "transaction_type", "type": "string"},
                        {"name": "timestamp", "type": "datetime"}
                    ]
                }
            }
        ]
        
        # 创建数据源
        created_count = 0
        for ds_data in test_data_sources:
            data_source = DataSourceModel(
                id=uuid4(),
                tenant_id="default_tenant",
                name=ds_data["name"],
                description=ds_data["description"],
                source_type=ds_data["source_type"],
                status=DataSourceStatus.ACTIVE,
                connection_config=ds_data["connection_config"],
                schema_config=ds_data["schema_config"],
                pool_size=5,
                max_overflow=10,
                connection_timeout=30,
                last_health_check=datetime.utcnow(),
                health_check_status="healthy",
                created_by="system",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(data_source)
            created_count += 1
            print(f"✅ 创建数据源: {ds_data['name']}")
        
        # 提交到数据库
        db.commit()
        
        print(f"\n🎉 成功创建 {created_count} 个测试数据源！")
        print("\n数据源列表:")
        print("-" * 80)
        
        # 查询并显示所有测试数据源
        all_sources = db.query(DataSourceModel).filter(
            DataSourceModel.name.like('Test%')
        ).all()
        
        for idx, source in enumerate(all_sources, 1):
            print(f"{idx}. {source.name}")
            print(f"   ID: {source.id}")
            print(f"   类型: {source.source_type.value}")
            print(f"   状态: {source.status.value}")
            print(f"   描述: {source.description}")
            print()
        
        print("=" * 80)
        print("✅ 测试数据源创建完成！")
        print("\n现在可以在任务创建界面中使用这些数据源进行测试。")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 创建测试数据源失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 80)
    print("创建测试数据源")
    print("=" * 80)
    print()
    
    create_test_data_sources()
