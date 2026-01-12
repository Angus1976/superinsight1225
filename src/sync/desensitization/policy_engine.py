"""
脱敏策略引擎
将策略集成到脱敏流程，基于租户和数据类型应用不同策略
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import logging

from src.models.desensitization import SensitivityPolicy
from src.sync.desensitization.presidio_engine import PresidioEngine
from src.sync.desensitization.models import DesensitizationRequest, DesensitizationResult

logger = logging.getLogger(__name__)

class PolicyEngine:
    """策略引擎"""
    
    def __init__(self, db: Session):
        self.db = db
        self.presidio_engine = PresidioEngine()
        self._policy_cache = {}
    
    async def apply_policies(
        self, 
        request: DesensitizationRequest
    ) -> DesensitizationResult:
        """应用脱敏策略"""
        try:
            # 获取租户策略
            policies = await self.get_tenant_policies(request.tenant_id)
            
            if not policies:
                # 使用默认策略
                return await self.presidio_engine.process_request(request)
            
            # 应用策略
            result = await self.process_with_policies(request, policies)
            
            # 记录策略应用日志
            await self.log_policy_application(request, policies, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Policy application failed: {e}")
            # 降级到默认处理
            return await self.presidio_engine.process_request(request)
    
    async def get_tenant_policies(self, tenant_id: str) -> List[SensitivityPolicy]:
        """获取租户策略"""
        # 检查缓存
        cache_key = f"tenant_policies:{tenant_id}"
        if cache_key in self._policy_cache:
            return self._policy_cache[cache_key]
        
        # 从数据库查询
        policies = self.db.query(SensitivityPolicy).filter(
            SensitivityPolicy.tenant_id == tenant_id,
            SensitivityPolicy.is_active == True
        ).all()
        
        # 缓存结果
        self._policy_cache[cache_key] = policies
        
        return policies
    
    async def process_with_policies(
        self, 
        request: DesensitizationRequest, 
        policies: List[SensitivityPolicy]
    ) -> DesensitizationResult:
        """使用策略处理请求"""
        
        # 合并所有策略的模式和规则
        all_patterns = []
        all_rules = []
        
        for policy in policies:
            all_patterns.extend(policy.patterns)
            all_rules.extend(policy.masking_rules)
        
        # 创建增强的请求
        enhanced_request = DesensitizationRequest(
            text=request.text,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            data_type=request.data_type,
            context=request.context,
            custom_patterns=all_patterns,
            custom_rules=all_rules
        )
        
        # 使用Presidio引擎处理
        return await self.presidio_engine.process_request(enhanced_request)
    
    async def evaluate_policy_conditions(
        self, 
        conditions: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> bool:
        """评估策略条件"""
        if not conditions:
            return True
        
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")
            
            if not self.evaluate_single_condition(field, operator, value, context):
                return False
        
        return True
    
    def evaluate_single_condition(
        self, 
        field: str, 
        operator: str, 
        value: Any, 
        context: Dict[str, Any]
    ) -> bool:
        """评估单个条件"""
        context_value = context.get(field)
        
        if operator == "equals":
            return context_value == value
        elif operator == "not_equals":
            return context_value != value
        elif operator == "in":
            return context_value in value if isinstance(value, list) else False
        elif operator == "not_in":
            return context_value not in value if isinstance(value, list) else True
        elif operator == "greater_than":
            return context_value > value if context_value is not None else False
        elif operator == "less_than":
            return context_value < value if context_value is not None else False
        elif operator == "contains":
            return value in str(context_value) if context_value is not None else False
        elif operator == "regex":
            import re
            return bool(re.search(value, str(context_value))) if context_value is not None else False
        
        return False
    
    async def log_policy_application(
        self, 
        request: DesensitizationRequest, 
        policies: List[SensitivityPolicy], 
        result: DesensitizationResult
    ):
        """记录策略应用日志"""
        try:
            from src.security.audit_service import EnhancedAuditService
            audit_service = EnhancedAuditService()
            
            await audit_service.log_event(
                event_type="desensitization_policy_applied",
                user_id=request.user_id,
                resource="desensitization_policy",
                action="apply",
                details={
                    "tenant_id": request.tenant_id,
                    "data_type": request.data_type,
                    "policies_applied": [p.id for p in policies],
                    "entities_detected": len(result.entities),
                    "masking_applied": result.masked_text != request.text
                }
            )
        except Exception as e:
            logger.error(f"Failed to log policy application: {e}")
    
    def invalidate_cache(self, tenant_id: str = None):
        """失效缓存"""
        if tenant_id:
            cache_key = f"tenant_policies:{tenant_id}"
            self._policy_cache.pop(cache_key, None)
        else:
            self._policy_cache.clear()
    
    async def validate_policy(self, policy: SensitivityPolicy) -> Dict[str, Any]:
        """验证策略配置"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # 验证模式
        for pattern in policy.patterns:
            if pattern.get("pattern_type") == "regex":
                try:
                    import re
                    re.compile(pattern.get("pattern", ""))
                except re.error as e:
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Invalid regex pattern: {e}")
        
        # 验证脱敏规则
        for rule in policy.masking_rules:
            masking_type = rule.get("masking_type")
            if masking_type not in ["redact", "replace", "hash", "encrypt", "partial"]:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Invalid masking type: {masking_type}")
        
        return validation_result