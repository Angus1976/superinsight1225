"""
企业本体模块单元测试

测试本体实体、关系、合规验证和 AI 数据转换功能。

Validates: 设计文档 - 本体模型设计
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

from src.ontology.enterprise_ontology import (
    ChineseEntityType,
    ChineseRelationType,
    DataClassification,
    SensitivityLevel,
    OntologyEntity,
    OntologyRelation,
    DataLineageNode,
    EnterpriseOntologyManager,
    ComplianceIssue,
    ComplianceResult,
)
from src.ontology.ai_data_converter import (
    AIDataFormat,
    AIDataConverter,
    ConversionResult,
)


# ============================================================================
# 实体类型测试
# ============================================================================

class TestChineseEntityType:
    """中国企业特色实体类型测试"""
    
    def test_basic_entity_types_exist(self):
        """基础实体类型应存在"""
        assert ChineseEntityType.PERSON.value == "person"
        assert ChineseEntityType.ORGANIZATION.value == "organization"
        assert ChineseEntityType.DOCUMENT.value == "document"
    
    def test_chinese_enterprise_entity_types_exist(self):
        """中国企业特色实体类型应存在"""
        assert ChineseEntityType.DEPARTMENT.value == "department"
        assert ChineseEntityType.BUSINESS_UNIT.value == "business_unit"
        assert ChineseEntityType.REGULATION.value == "regulation"
        assert ChineseEntityType.CONTRACT.value == "contract"
        assert ChineseEntityType.APPROVAL.value == "approval"
        assert ChineseEntityType.SEAL.value == "seal"
        assert ChineseEntityType.INVOICE.value == "invoice"
        assert ChineseEntityType.CERTIFICATE.value == "certificate"
    
    def test_get_display_name_chinese(self):
        """应返回中文显示名称"""
        assert ChineseEntityType.get_display_name(ChineseEntityType.DEPARTMENT, "zh") == "部门"
        assert ChineseEntityType.get_display_name(ChineseEntityType.CONTRACT, "zh") == "合同"
        assert ChineseEntityType.get_display_name(ChineseEntityType.SEAL, "zh") == "印章"
    
    def test_get_display_name_english(self):
        """应返回英文显示名称"""
        assert ChineseEntityType.get_display_name(ChineseEntityType.DEPARTMENT, "en") == "Department"
        assert ChineseEntityType.get_display_name(ChineseEntityType.CONTRACT, "en") == "Contract"
        assert ChineseEntityType.get_display_name(ChineseEntityType.SEAL, "en") == "Seal"


class TestChineseRelationType:
    """中国企业特色关系类型测试"""
    
    def test_basic_relation_types_exist(self):
        """基础关系类型应存在"""
        assert ChineseRelationType.BELONGS_TO.value == "belongs_to"
        assert ChineseRelationType.CREATED_BY.value == "created_by"
        assert ChineseRelationType.RELATED_TO.value == "related_to"
    
    def test_chinese_enterprise_relation_types_exist(self):
        """中国企业特色关系类型应存在"""
        assert ChineseRelationType.REPORTS_TO.value == "reports_to"
        assert ChineseRelationType.APPROVES.value == "approves"
        assert ChineseRelationType.SEALS.value == "seals"
        assert ChineseRelationType.COMPLIES_WITH.value == "complies_with"
        assert ChineseRelationType.SUPERVISES.value == "supervises"
        assert ChineseRelationType.DELEGATES_TO.value == "delegates_to"
    
    def test_get_display_name_chinese(self):
        """应返回中文显示名称"""
        assert ChineseRelationType.get_display_name(ChineseRelationType.REPORTS_TO, "zh") == "汇报给"
        assert ChineseRelationType.get_display_name(ChineseRelationType.APPROVES, "zh") == "审批"
        assert ChineseRelationType.get_display_name(ChineseRelationType.SEALS, "zh") == "用印"


# ============================================================================
# 本体实体测试
# ============================================================================

class TestOntologyEntity:
    """本体实体测试"""
    
    def test_create_entity_with_required_fields(self):
        """应能创建包含必需字段的实体"""
        entity = OntologyEntity(
            entity_type=ChineseEntityType.DEPARTMENT,
            name="Engineering",
            name_zh="工程部"
        )
        
        assert entity.id is not None
        assert entity.entity_type == ChineseEntityType.DEPARTMENT
        assert entity.name == "Engineering"
        assert entity.name_zh == "工程部"
        assert entity.is_active is True
    
    def test_create_entity_with_all_fields(self):
        """应能创建包含所有字段的实体"""
        entity = OntologyEntity(
            entity_type=ChineseEntityType.CONTRACT,
            name="Sales Contract",
            name_zh="销售合同",
            description="Annual sales contract",
            description_zh="年度销售合同",
            business_domain="Sales",
            data_classification=DataClassification.CONFIDENTIAL,
            sensitivity_level=SensitivityLevel.HIGH,
            retention_period_days=365 * 7,
            cross_border_allowed=False,
            pii_fields=["customer_name", "customer_phone"],
            tenant_id="tenant_001"
        )
        
        assert entity.data_classification == DataClassification.CONFIDENTIAL
        assert entity.sensitivity_level == SensitivityLevel.HIGH
        assert entity.retention_period_days == 365 * 7
        assert entity.cross_border_allowed is False
        assert "customer_name" in entity.pii_fields
    
    def test_to_knowledge_graph_entity(self):
        """应能转换为知识图谱实体"""
        entity = OntologyEntity(
            entity_type=ChineseEntityType.PERSON,
            name="John Doe",
            name_zh="张三",
            description_zh="测试用户",
            business_domain="HR"
        )
        
        kg_entity = entity.to_knowledge_graph_entity()
        
        assert kg_entity.id == entity.id
        assert kg_entity.name == "John Doe"
        assert kg_entity.properties.get("name_zh") == "张三"
        assert kg_entity.properties.get("business_domain") == "HR"
    
    def test_to_dict(self):
        """应能转换为字典"""
        entity = OntologyEntity(
            entity_type=ChineseEntityType.INVOICE,
            name="INV-2026-001",
            name_zh="发票-2026-001",
            data_classification=DataClassification.INTERNAL
        )
        
        entity_dict = entity.to_dict()
        
        assert entity_dict["entity_type"] == "invoice"
        assert entity_dict["name"] == "INV-2026-001"
        assert entity_dict["name_zh"] == "发票-2026-001"
        assert entity_dict["data_classification"] == "internal"


# ============================================================================
# 本体关系测试
# ============================================================================

class TestOntologyRelation:
    """本体关系测试"""
    
    def test_create_relation(self):
        """应能创建关系"""
        source_id = uuid4()
        target_id = uuid4()
        
        relation = OntologyRelation(
            source_id=source_id,
            target_id=target_id,
            relation_type=ChineseRelationType.REPORTS_TO,
            name_zh="汇报关系"
        )
        
        assert relation.id is not None
        assert relation.source_id == source_id
        assert relation.target_id == target_id
        assert relation.relation_type == ChineseRelationType.REPORTS_TO
    
    def test_relation_with_business_attributes(self):
        """应能创建包含业务属性的关系"""
        relation = OntologyRelation(
            source_id=uuid4(),
            target_id=uuid4(),
            relation_type=ChineseRelationType.APPROVES,
            name_zh="审批关系",
            business_rule="RULE_001",
            approval_required=True,
            audit_required=True,
            effective_date=datetime.now(),
            expiry_date=datetime.now() + timedelta(days=365)
        )
        
        assert relation.business_rule == "RULE_001"
        assert relation.approval_required is True
        assert relation.audit_required is True
        assert relation.effective_date is not None
        assert relation.expiry_date is not None
    
    def test_is_valid_within_period(self):
        """在有效期内应返回 True"""
        relation = OntologyRelation(
            source_id=uuid4(),
            target_id=uuid4(),
            relation_type=ChineseRelationType.DELEGATES_TO,
            effective_date=datetime.now() - timedelta(days=1),
            expiry_date=datetime.now() + timedelta(days=30)
        )
        
        assert relation.is_valid() is True
    
    def test_is_valid_expired(self):
        """过期后应返回 False"""
        relation = OntologyRelation(
            source_id=uuid4(),
            target_id=uuid4(),
            relation_type=ChineseRelationType.DELEGATES_TO,
            effective_date=datetime.now() - timedelta(days=60),
            expiry_date=datetime.now() - timedelta(days=30)
        )
        
        assert relation.is_valid() is False
    
    def test_to_knowledge_graph_relation(self):
        """应能转换为知识图谱关系"""
        relation = OntologyRelation(
            source_id=uuid4(),
            target_id=uuid4(),
            relation_type=ChineseRelationType.BELONGS_TO,
            name_zh="属于关系",
            weight=0.8
        )
        
        kg_relation = relation.to_knowledge_graph_relation()
        
        assert kg_relation.id == relation.id
        assert kg_relation.weight == 0.8


# ============================================================================
# 合规验证测试
# ============================================================================

class TestComplianceValidation:
    """合规验证测试"""
    
    @pytest.fixture
    def manager(self):
        return EnterpriseOntologyManager()
    
    @pytest.mark.asyncio
    async def test_compliant_entity(self, manager):
        """合规实体应通过验证"""
        entity = OntologyEntity(
            entity_type=ChineseEntityType.DOCUMENT,
            name="Public Report",
            name_zh="公开报告",
            data_classification=DataClassification.PUBLIC,
            sensitivity_level=SensitivityLevel.LOW
        )
        
        result = await manager.validate_compliance(entity)
        
        assert result.compliant is True
        assert result.error_count == 0
    
    @pytest.mark.asyncio
    async def test_missing_classification_warning(self, manager):
        """缺少数据分类应产生警告"""
        entity = OntologyEntity(
            entity_type=ChineseEntityType.DOCUMENT,
            name="Test Document",
            name_zh="测试文档"
        )
        
        result = await manager.validate_compliance(entity)
        
        assert result.warning_count >= 1
        assert any(i.issue_type == "missing_classification" for i in result.issues)
    
    @pytest.mark.asyncio
    async def test_cross_border_violation(self, manager):
        """跨境传输违规应产生错误"""
        entity = OntologyEntity(
            entity_type=ChineseEntityType.DOCUMENT,
            name="Sensitive Data",
            name_zh="敏感数据",
            cross_border_allowed=False,
            downstream_targets=["aws-s3-bucket", "azure-blob"]
        )
        
        result = await manager.validate_compliance(entity)
        
        assert result.compliant is False
        assert result.error_count >= 1
        assert any(i.issue_type == "cross_border_violation" for i in result.issues)
    
    @pytest.mark.asyncio
    async def test_pii_sensitivity_mismatch(self, manager):
        """PII 敏感度不匹配应产生警告"""
        entity = OntologyEntity(
            entity_type=ChineseEntityType.DOCUMENT,
            name="Customer Data",
            name_zh="客户数据",
            pii_fields=["name", "phone", "email"],
            sensitivity_level=SensitivityLevel.LOW,
            data_classification=DataClassification.CONFIDENTIAL
        )
        
        result = await manager.validate_compliance(entity)
        
        assert any(i.issue_type == "pii_sensitivity_mismatch" for i in result.issues)
    
    @pytest.mark.asyncio
    async def test_pii_classification_mismatch(self, manager):
        """PII 分类不匹配应产生错误"""
        entity = OntologyEntity(
            entity_type=ChineseEntityType.DOCUMENT,
            name="Customer Data",
            name_zh="客户数据",
            pii_fields=["name", "phone"],
            data_classification=DataClassification.PUBLIC
        )
        
        result = await manager.validate_compliance(entity)
        
        assert result.compliant is False
        assert any(i.issue_type == "pii_classification_mismatch" for i in result.issues)


# ============================================================================
# AI 数据转换器测试
# ============================================================================

class TestAIDataConverter:
    """AI 数据转换器测试"""
    
    @pytest.fixture
    def converter(self):
        return AIDataConverter()
    
    @pytest.fixture
    def sample_annotations(self):
        return [
            {
                "id": "ann_001",
                "question": "什么是机器学习？",
                "answer": "机器学习是人工智能的一个分支...",
                "context": "",
                "quality_score": 0.95
            },
            {
                "id": "ann_002",
                "question": "如何训练神经网络？",
                "answer": "训练神经网络需要以下步骤...",
                "context": "深度学习基础",
                "quality_score": 0.88
            }
        ]
    
    @pytest.mark.asyncio
    async def test_convert_to_alpaca_format(self, converter, sample_annotations):
        """应能转换为 Alpaca 格式"""
        result = await converter.convert_annotations_to_training_data(
            sample_annotations,
            AIDataFormat.ALPACA
        )
        
        assert result.success is True
        assert result.converted_records == 2
        assert len(result.data) == 2
        
        # 验证格式
        item = result.data[0]
        assert "instruction" in item
        assert "input" in item
        assert "output" in item
        assert item["instruction"] == "什么是机器学习？"
    
    @pytest.mark.asyncio
    async def test_convert_to_sharegpt_format(self, converter, sample_annotations):
        """应能转换为 ShareGPT 格式"""
        result = await converter.convert_annotations_to_training_data(
            sample_annotations,
            AIDataFormat.SHAREGPT
        )
        
        assert result.success is True
        assert len(result.data) == 2
        
        # 验证格式
        item = result.data[0]
        assert "conversations" in item
        assert len(item["conversations"]) == 2
        assert item["conversations"][0]["from"] == "human"
        assert item["conversations"][1]["from"] == "gpt"
    
    @pytest.mark.asyncio
    async def test_convert_to_openai_format(self, converter, sample_annotations):
        """应能转换为 OpenAI 格式"""
        result = await converter.convert_annotations_to_training_data(
            sample_annotations,
            AIDataFormat.OPENAI,
            system_prompt="你是一个有帮助的助手。"
        )
        
        assert result.success is True
        
        # 验证格式
        item = result.data[0]
        assert "messages" in item
        assert item["messages"][0]["role"] == "system"
        assert item["messages"][1]["role"] == "user"
        assert item["messages"][2]["role"] == "assistant"
    
    @pytest.mark.asyncio
    async def test_convert_to_llama_factory_format(self, converter, sample_annotations):
        """应能转换为 LLaMA-Factory 格式"""
        result = await converter.convert_annotations_to_training_data(
            sample_annotations,
            AIDataFormat.LLAMA_FACTORY
        )
        
        assert result.success is True
        
        # 验证格式
        item = result.data[0]
        assert "instruction" in item
        assert "input" in item
        assert "output" in item
    
    @pytest.mark.asyncio
    async def test_convert_with_history(self, converter):
        """应能处理多轮对话历史"""
        annotations = [{
            "id": "ann_003",
            "question": "继续解释",
            "answer": "好的，让我继续...",
            "history": [
                {"question": "什么是 AI？", "answer": "AI 是人工智能..."},
                {"question": "有哪些应用？", "answer": "AI 有很多应用..."}
            ]
        }]
        
        result = await converter.convert_annotations_to_training_data(
            annotations,
            AIDataFormat.SHAREGPT
        )
        
        assert result.success is True
        # ShareGPT 格式应包含历史对话
        item = result.data[0]
        assert len(item["conversations"]) > 2
    
    @pytest.mark.asyncio
    async def test_validate_annotations_valid(self, converter, sample_annotations):
        """有效标注应通过验证"""
        result = await converter.validate_annotations(sample_annotations)
        
        assert result["valid"] == 2
        assert result["invalid"] == 0
        assert result["can_convert"] is True
    
    @pytest.mark.asyncio
    async def test_validate_annotations_missing_question(self, converter):
        """缺少问题的标注应验证失败"""
        annotations = [
            {"id": "ann_001", "answer": "Some answer"}
        ]
        
        result = await converter.validate_annotations(annotations)
        
        assert result["invalid"] == 1
        assert result["can_convert"] is False
        assert any(i["issue"] == "missing_question" for i in result["issues"])
    
    @pytest.mark.asyncio
    async def test_validate_annotations_missing_answer(self, converter):
        """缺少回答的标注应验证失败"""
        annotations = [
            {"id": "ann_001", "question": "Some question"}
        ]
        
        result = await converter.validate_annotations(annotations)
        
        assert result["invalid"] == 1
        assert any(i["issue"] == "missing_answer" for i in result["issues"])
    
    def test_get_supported_formats(self, converter):
        """应返回支持的格式列表"""
        formats = converter.get_supported_formats("zh")
        
        assert len(formats) > 0
        assert any(f["value"] == "alpaca" for f in formats)
        assert any(f["value"] == "openai" for f in formats)
        
        # 验证中文标签
        alpaca_format = next(f for f in formats if f["value"] == "alpaca")
        assert "Alpaca" in alpaca_format["label"]


# ============================================================================
# 企业本体管理器测试
# ============================================================================

class TestEnterpriseOntologyManager:
    """企业本体管理器测试"""
    
    @pytest.fixture
    def manager(self):
        return EnterpriseOntologyManager()
    
    @pytest.mark.asyncio
    async def test_create_entity(self, manager):
        """应能创建实体"""
        entity = OntologyEntity(
            entity_type=ChineseEntityType.DEPARTMENT,
            name="Engineering",
            name_zh="工程部"
        )
        
        created = await manager.create_entity(entity)
        
        assert created.id == entity.id
        assert created.name_zh == "工程部"
    
    @pytest.mark.asyncio
    async def test_get_entity_from_cache(self, manager):
        """应能从缓存获取实体"""
        entity = OntologyEntity(
            entity_type=ChineseEntityType.PROJECT,
            name="Project Alpha",
            name_zh="阿尔法项目"
        )
        
        await manager.create_entity(entity)
        retrieved = await manager.get_entity(entity.id)
        
        assert retrieved is not None
        assert retrieved.id == entity.id
        assert retrieved.name_zh == "阿尔法项目"
    
    @pytest.mark.asyncio
    async def test_update_entity(self, manager):
        """应能更新实体"""
        entity = OntologyEntity(
            entity_type=ChineseEntityType.DOCUMENT,
            name="Draft",
            name_zh="草稿"
        )
        
        await manager.create_entity(entity)
        
        updated = await manager.update_entity(
            entity.id,
            {"name": "Final", "name_zh": "最终版"}
        )
        
        assert updated is not None
        assert updated.name == "Final"
        assert updated.name_zh == "最终版"
        assert updated.version == 2
    
    @pytest.mark.asyncio
    async def test_delete_entity(self, manager):
        """应能删除实体"""
        entity = OntologyEntity(
            entity_type=ChineseEntityType.MEETING,
            name="Weekly Meeting",
            name_zh="周会"
        )
        
        await manager.create_entity(entity)
        result = await manager.delete_entity(entity.id)
        
        assert result is True
        
        # 验证已从缓存删除
        retrieved = await manager.get_entity(entity.id)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_create_relation(self, manager):
        """应能创建关系"""
        relation = OntologyRelation(
            source_id=uuid4(),
            target_id=uuid4(),
            relation_type=ChineseRelationType.MANAGES,
            name_zh="管理关系"
        )
        
        created = await manager.create_relation(relation)
        
        assert created.id == relation.id
        assert created.relation_type == ChineseRelationType.MANAGES
    
    @pytest.mark.asyncio
    async def test_get_stats(self, manager):
        """应能获取统计信息"""
        # 创建一些实体
        for i in range(3):
            entity = OntologyEntity(
                entity_type=ChineseEntityType.DOCUMENT,
                name=f"Doc {i}",
                name_zh=f"文档 {i}"
            )
            await manager.create_entity(entity)
        
        stats = await manager.get_stats()
        
        assert stats["cached_entities"] == 3
        assert stats["kg_connected"] is False
        assert stats["lineage_connected"] is False
    
    def test_clear_cache(self, manager):
        """应能清除缓存"""
        # 手动添加到缓存
        entity = OntologyEntity(
            entity_type=ChineseEntityType.POLICY,
            name="Policy",
            name_zh="政策"
        )
        manager._entity_cache[entity.id] = entity
        
        manager.clear_cache()
        
        assert len(manager._entity_cache) == 0
        assert len(manager._relation_cache) == 0


# ============================================================================
# 数据血缘节点测试
# ============================================================================

class TestDataLineageNode:
    """数据血缘节点测试"""
    
    def test_create_lineage_node(self):
        """应能创建血缘节点"""
        entity_id = uuid4()
        node = DataLineageNode(
            entity_id=entity_id,
            node_type="source",
            source_system="ERP",
            source_table="customers",
            source_column="customer_id"
        )
        
        assert node.id is not None
        assert node.entity_id == entity_id
        assert node.node_type == "source"
        assert node.source_system == "ERP"
    
    def test_lineage_node_with_transformation(self):
        """应能创建包含转换信息的血缘节点"""
        node = DataLineageNode(
            entity_id=uuid4(),
            node_type="transform",
            transformation_type="aggregation",
            transformation_logic="SUM(amount) GROUP BY customer_id"
        )
        
        assert node.transformation_type == "aggregation"
        assert "SUM" in node.transformation_logic
    
    def test_lineage_node_with_quality(self):
        """应能创建包含质量信息的血缘节点"""
        node = DataLineageNode(
            entity_id=uuid4(),
            node_type="target",
            quality_score=0.95,
            last_quality_check=datetime.now()
        )
        
        assert node.quality_score == 0.95
        assert node.last_quality_check is not None
    
    def test_to_dict(self):
        """应能转换为字典"""
        node = DataLineageNode(
            entity_id=uuid4(),
            node_type="source",
            source_system="CRM"
        )
        
        node_dict = node.to_dict()
        
        assert "id" in node_dict
        assert "entity_id" in node_dict
        assert node_dict["node_type"] == "source"
        assert node_dict["source_system"] == "CRM"


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
