"""
Billing Rule Engine for SuperInsight Platform.

Provides flexible billing rule configuration and execution:
- Rule definition and management
- Condition evaluation
- Action execution
- Rule priority and conflict resolution
"""

from datetime import datetime, date, time
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from uuid import uuid4
import logging
import operator
import re

logger = logging.getLogger(__name__)


class RuleType(str, Enum):
    """Rule type enumeration."""
    PRICING = "pricing"
    DISCOUNT = "discount"
    TAX = "tax"
    SURCHARGE = "surcharge"
    VALIDATION = "validation"
    NOTIFICATION = "notification"


class ConditionOperator(str, Enum):
    """Condition operator enumeration."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCHES = "matches"  # regex
    BETWEEN = "between"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class ActionType(str, Enum):
    """Action type enumeration."""
    SET_RATE = "set_rate"
    MULTIPLY_RATE = "multiply_rate"
    ADD_AMOUNT = "add_amount"
    SUBTRACT_AMOUNT = "subtract_amount"
    APPLY_DISCOUNT = "apply_discount"
    APPLY_TAX = "apply_tax"
    SET_FLAG = "set_flag"
    SEND_NOTIFICATION = "send_notification"
    REJECT = "reject"
    APPROVE = "approve"


class RuleStatus(str, Enum):
    """Rule status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ARCHIVED = "archived"


class LogicOperator(str, Enum):
    """Logic operator for combining conditions."""
    AND = "and"
    OR = "or"


@dataclass
class RuleCondition:
    """Rule condition definition."""
    condition_id: str
    field: str
    operator: ConditionOperator
    value: Any
    value_type: str = "string"  # string, number, date, boolean, list


@dataclass
class RuleConditionGroup:
    """Group of conditions with logic operator."""
    group_id: str
    conditions: List[RuleCondition]
    logic: LogicOperator = LogicOperator.AND
    nested_groups: List['RuleConditionGroup'] = field(default_factory=list)


@dataclass
class RuleAction:
    """Rule action definition."""
    action_id: str
    action_type: ActionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    order: int = 0


@dataclass
class BillingRule:
    """Billing rule definition."""
    rule_id: str
    name: str
    description: str
    rule_type: RuleType
    condition_group: RuleConditionGroup
    actions: List[RuleAction]
    priority: int = 100  # Lower number = higher priority
    status: RuleStatus = RuleStatus.ACTIVE
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuleExecutionResult:
    """Result of rule execution."""
    rule_id: str
    rule_name: str
    matched: bool
    actions_executed: List[str]
    modifications: Dict[str, Any]
    execution_time_ms: float
    error: Optional[str] = None


@dataclass
class RuleEngineResult:
    """Result of rule engine execution."""
    context_id: str
    rules_evaluated: int
    rules_matched: int
    results: List[RuleExecutionResult]
    final_values: Dict[str, Any]
    total_execution_time_ms: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ConditionEvaluator:
    """
    Evaluates rule conditions against context data.
    """
    
    OPERATORS: Dict[ConditionOperator, Callable] = {
        ConditionOperator.EQUALS: operator.eq,
        ConditionOperator.NOT_EQUALS: operator.ne,
        ConditionOperator.GREATER_THAN: operator.gt,
        ConditionOperator.GREATER_THAN_OR_EQUAL: operator.ge,
        ConditionOperator.LESS_THAN: operator.lt,
        ConditionOperator.LESS_THAN_OR_EQUAL: operator.le,
    }
    
    def evaluate_condition(
        self,
        condition: RuleCondition,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate a single condition."""
        field_value = self._get_field_value(condition.field, context)
        condition_value = self._convert_value(condition.value, condition.value_type)
        
        op = condition.operator
        
        # Handle null checks
        if op == ConditionOperator.IS_NULL:
            return field_value is None
        if op == ConditionOperator.IS_NOT_NULL:
            return field_value is not None
        
        # If field value is None, condition fails (except null checks)
        if field_value is None:
            return False
        
        # Standard operators
        if op in self.OPERATORS:
            return self.OPERATORS[op](field_value, condition_value)
        
        # Collection operators
        if op == ConditionOperator.IN:
            return field_value in condition_value
        if op == ConditionOperator.NOT_IN:
            return field_value not in condition_value
        
        # String operators
        if op == ConditionOperator.CONTAINS:
            return str(condition_value) in str(field_value)
        if op == ConditionOperator.STARTS_WITH:
            return str(field_value).startswith(str(condition_value))
        if op == ConditionOperator.ENDS_WITH:
            return str(field_value).endswith(str(condition_value))
        if op == ConditionOperator.MATCHES:
            return bool(re.match(str(condition_value), str(field_value)))
        
        # Range operator
        if op == ConditionOperator.BETWEEN:
            if isinstance(condition_value, (list, tuple)) and len(condition_value) == 2:
                return condition_value[0] <= field_value <= condition_value[1]
            return False
        
        return False
    
    def evaluate_condition_group(
        self,
        group: RuleConditionGroup,
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate a group of conditions."""
        results = []
        
        # Evaluate direct conditions
        for condition in group.conditions:
            results.append(self.evaluate_condition(condition, context))
        
        # Evaluate nested groups
        for nested in group.nested_groups:
            results.append(self.evaluate_condition_group(nested, context))
        
        if not results:
            return True  # Empty group matches everything
        
        if group.logic == LogicOperator.AND:
            return all(results)
        else:  # OR
            return any(results)
    
    def _get_field_value(self, field: str, context: Dict[str, Any]) -> Any:
        """Get field value from context using dot notation."""
        parts = field.split(".")
        value = context
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        
        return value
    
    def _convert_value(self, value: Any, value_type: str) -> Any:
        """Convert value to specified type."""
        if value is None:
            return None
        
        try:
            if value_type == "number":
                return Decimal(str(value))
            elif value_type == "date":
                if isinstance(value, date):
                    return value
                return datetime.fromisoformat(str(value)).date()
            elif value_type == "boolean":
                return bool(value)
            elif value_type == "list":
                if isinstance(value, list):
                    return value
                return [value]
            else:
                return str(value)
        except (ValueError, TypeError):
            return value


class ActionExecutor:
    """
    Executes rule actions and modifies context.
    """
    
    def execute_action(
        self,
        action: RuleAction,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single action and return modifications."""
        modifications = {}
        params = action.parameters
        
        if action.action_type == ActionType.SET_RATE:
            field = params.get("field", "rate")
            value = Decimal(str(params.get("value", 0)))
            modifications[field] = value
            self._set_context_value(context, field, value)
        
        elif action.action_type == ActionType.MULTIPLY_RATE:
            field = params.get("field", "rate")
            multiplier = Decimal(str(params.get("multiplier", 1)))
            current = self._get_context_value(context, field) or Decimal("0")
            new_value = current * multiplier
            modifications[field] = new_value
            self._set_context_value(context, field, new_value)
        
        elif action.action_type == ActionType.ADD_AMOUNT:
            field = params.get("field", "amount")
            amount = Decimal(str(params.get("amount", 0)))
            current = self._get_context_value(context, field) or Decimal("0")
            new_value = current + amount
            modifications[field] = new_value
            self._set_context_value(context, field, new_value)
        
        elif action.action_type == ActionType.SUBTRACT_AMOUNT:
            field = params.get("field", "amount")
            amount = Decimal(str(params.get("amount", 0)))
            current = self._get_context_value(context, field) or Decimal("0")
            new_value = current - amount
            modifications[field] = new_value
            self._set_context_value(context, field, new_value)
        
        elif action.action_type == ActionType.APPLY_DISCOUNT:
            discount_type = params.get("discount_type", "percentage")
            discount_value = Decimal(str(params.get("value", 0)))
            amount_field = params.get("amount_field", "amount")
            current_amount = self._get_context_value(context, amount_field) or Decimal("0")
            
            if discount_type == "percentage":
                discount_amount = current_amount * (discount_value / 100)
            else:
                discount_amount = discount_value
            
            new_amount = current_amount - discount_amount
            modifications["discount_amount"] = discount_amount
            modifications[amount_field] = new_amount
            self._set_context_value(context, amount_field, new_amount)
            self._set_context_value(context, "discount_amount", discount_amount)
        
        elif action.action_type == ActionType.APPLY_TAX:
            tax_rate = Decimal(str(params.get("rate", 0)))
            amount_field = params.get("amount_field", "amount")
            current_amount = self._get_context_value(context, amount_field) or Decimal("0")
            
            tax_amount = current_amount * (tax_rate / 100)
            modifications["tax_amount"] = tax_amount
            modifications["total_with_tax"] = current_amount + tax_amount
            self._set_context_value(context, "tax_amount", tax_amount)
            self._set_context_value(context, "total_with_tax", current_amount + tax_amount)
        
        elif action.action_type == ActionType.SET_FLAG:
            flag_name = params.get("flag")
            flag_value = params.get("value", True)
            if flag_name:
                modifications[flag_name] = flag_value
                self._set_context_value(context, flag_name, flag_value)
        
        elif action.action_type == ActionType.REJECT:
            modifications["rejected"] = True
            modifications["rejection_reason"] = params.get("reason", "Rule rejection")
            self._set_context_value(context, "rejected", True)
        
        elif action.action_type == ActionType.APPROVE:
            modifications["approved"] = True
            self._set_context_value(context, "approved", True)
        
        return modifications
    
    def _get_context_value(self, context: Dict[str, Any], field: str) -> Any:
        """Get value from context using dot notation."""
        parts = field.split(".")
        value = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value
    
    def _set_context_value(self, context: Dict[str, Any], field: str, value: Any):
        """Set value in context using dot notation."""
        parts = field.split(".")
        target = context
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value


class BillingRuleEngine:
    """
    Main billing rule engine.
    
    Manages rules and executes them against billing contexts.
    """
    
    def __init__(self):
        self.rules: Dict[str, BillingRule] = {}
        self.condition_evaluator = ConditionEvaluator()
        self.action_executor = ActionExecutor()
    
    def create_rule(
        self,
        name: str,
        description: str,
        rule_type: RuleType,
        conditions: List[Dict[str, Any]],
        actions: List[Dict[str, Any]],
        priority: int = 100,
        **kwargs
    ) -> BillingRule:
        """Create a new billing rule."""
        rule_id = str(uuid4())
        
        # Build condition group
        condition_group = self._build_condition_group(conditions)
        
        # Build actions
        rule_actions = self._build_actions(actions)
        
        rule = BillingRule(
            rule_id=rule_id,
            name=name,
            description=description,
            rule_type=rule_type,
            condition_group=condition_group,
            actions=rule_actions,
            priority=priority,
            **kwargs
        )
        
        self.rules[rule_id] = rule
        logger.info(f"Created billing rule: {rule_id} - {name}")
        
        return rule
    
    def _build_condition_group(
        self,
        conditions: List[Dict[str, Any]],
        logic: LogicOperator = LogicOperator.AND
    ) -> RuleConditionGroup:
        """Build condition group from dict list."""
        group_id = str(uuid4())
        rule_conditions = []
        
        for cond in conditions:
            condition = RuleCondition(
                condition_id=str(uuid4()),
                field=cond.get("field", ""),
                operator=ConditionOperator(cond.get("operator", "eq")),
                value=cond.get("value"),
                value_type=cond.get("value_type", "string"),
            )
            rule_conditions.append(condition)
        
        return RuleConditionGroup(
            group_id=group_id,
            conditions=rule_conditions,
            logic=logic,
        )
    
    def _build_actions(self, actions: List[Dict[str, Any]]) -> List[RuleAction]:
        """Build actions from dict list."""
        rule_actions = []
        
        for i, act in enumerate(actions):
            action = RuleAction(
                action_id=str(uuid4()),
                action_type=ActionType(act.get("action_type", "set_flag")),
                parameters=act.get("parameters", {}),
                order=act.get("order", i),
            )
            rule_actions.append(action)
        
        return rule_actions
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> Optional[BillingRule]:
        """Update an existing rule."""
        if rule_id not in self.rules:
            return None
        
        rule = self.rules[rule_id]
        
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        rule.updated_at = datetime.utcnow()
        logger.info(f"Updated billing rule: {rule_id}")
        
        return rule
    
    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Deleted billing rule: {rule_id}")
            return True
        return False
    
    def get_rule(self, rule_id: str) -> Optional[BillingRule]:
        """Get a rule by ID."""
        return self.rules.get(rule_id)
    
    def list_rules(
        self,
        rule_type: RuleType = None,
        status: RuleStatus = None,
        tenant_id: str = None
    ) -> List[BillingRule]:
        """List rules with optional filters."""
        rules = list(self.rules.values())
        
        if rule_type:
            rules = [r for r in rules if r.rule_type == rule_type]
        
        if status:
            rules = [r for r in rules if r.status == status]
        
        if tenant_id:
            rules = [r for r in rules if r.tenant_id == tenant_id or r.tenant_id is None]
        
        # Sort by priority
        rules.sort(key=lambda r: r.priority)
        
        return rules
    
    def execute_rules(
        self,
        context: Dict[str, Any],
        rule_type: RuleType = None,
        tenant_id: str = None,
        stop_on_first_match: bool = False
    ) -> RuleEngineResult:
        """Execute applicable rules against context."""
        import time
        start_time = time.time()
        
        context_id = str(uuid4())
        results = []
        rules_matched = 0
        
        # Get applicable rules
        applicable_rules = self._get_applicable_rules(rule_type, tenant_id)
        
        for rule in applicable_rules:
            rule_start = time.time()
            
            # Check if rule is effective
            if not self._is_rule_effective(rule):
                continue
            
            # Evaluate conditions
            matched = self.condition_evaluator.evaluate_condition_group(
                rule.condition_group, context
            )
            
            actions_executed = []
            modifications = {}
            
            if matched:
                rules_matched += 1
                
                # Execute actions in order
                sorted_actions = sorted(rule.actions, key=lambda a: a.order)
                for action in sorted_actions:
                    try:
                        mods = self.action_executor.execute_action(action, context)
                        modifications.update(mods)
                        actions_executed.append(action.action_type.value)
                    except Exception as e:
                        logger.error(f"Action execution error: {e}")
            
            rule_time = (time.time() - rule_start) * 1000
            
            result = RuleExecutionResult(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                matched=matched,
                actions_executed=actions_executed,
                modifications=modifications,
                execution_time_ms=rule_time,
            )
            results.append(result)
            
            if matched and stop_on_first_match:
                break
        
        total_time = (time.time() - start_time) * 1000
        
        return RuleEngineResult(
            context_id=context_id,
            rules_evaluated=len(applicable_rules),
            rules_matched=rules_matched,
            results=results,
            final_values=context,
            total_execution_time_ms=total_time,
        )
    
    def _get_applicable_rules(
        self,
        rule_type: RuleType = None,
        tenant_id: str = None
    ) -> List[BillingRule]:
        """Get applicable rules sorted by priority."""
        rules = [r for r in self.rules.values() if r.status == RuleStatus.ACTIVE]
        
        if rule_type:
            rules = [r for r in rules if r.rule_type == rule_type]
        
        if tenant_id:
            rules = [r for r in rules if r.tenant_id == tenant_id or r.tenant_id is None]
        
        # Sort by priority (lower number = higher priority)
        rules.sort(key=lambda r: r.priority)
        
        return rules
    
    def _is_rule_effective(self, rule: BillingRule) -> bool:
        """Check if rule is currently effective."""
        today = date.today()
        
        if rule.effective_from and today < rule.effective_from:
            return False
        
        if rule.effective_to and today > rule.effective_to:
            return False
        
        return True
    
    def validate_rule(self, rule: BillingRule) -> List[str]:
        """Validate a rule configuration."""
        errors = []
        
        if not rule.name:
            errors.append("Rule name is required")
        
        if not rule.condition_group.conditions and not rule.condition_group.nested_groups:
            errors.append("At least one condition is required")
        
        if not rule.actions:
            errors.append("At least one action is required")
        
        # Validate conditions
        for condition in rule.condition_group.conditions:
            if not condition.field:
                errors.append(f"Condition {condition.condition_id}: field is required")
        
        # Validate actions
        for action in rule.actions:
            if action.action_type in [ActionType.SET_RATE, ActionType.MULTIPLY_RATE]:
                if "value" not in action.parameters and "multiplier" not in action.parameters:
                    errors.append(f"Action {action.action_id}: value or multiplier required")
        
        return errors
    
    def export_rules(self, rule_ids: List[str] = None) -> List[Dict[str, Any]]:
        """Export rules to JSON-serializable format."""
        rules_to_export = []
        
        for rule_id, rule in self.rules.items():
            if rule_ids and rule_id not in rule_ids:
                continue
            
            rules_to_export.append({
                "rule_id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "rule_type": rule.rule_type.value,
                "priority": rule.priority,
                "status": rule.status.value,
                "conditions": [
                    {
                        "field": c.field,
                        "operator": c.operator.value,
                        "value": c.value,
                        "value_type": c.value_type,
                    }
                    for c in rule.condition_group.conditions
                ],
                "actions": [
                    {
                        "action_type": a.action_type.value,
                        "parameters": a.parameters,
                        "order": a.order,
                    }
                    for a in rule.actions
                ],
                "effective_from": rule.effective_from.isoformat() if rule.effective_from else None,
                "effective_to": rule.effective_to.isoformat() if rule.effective_to else None,
                "tenant_id": rule.tenant_id,
                "metadata": rule.metadata,
            })
        
        return rules_to_export
    
    def import_rules(self, rules_data: List[Dict[str, Any]]) -> List[BillingRule]:
        """Import rules from JSON data."""
        imported = []
        
        for data in rules_data:
            rule = self.create_rule(
                name=data.get("name", "Imported Rule"),
                description=data.get("description", ""),
                rule_type=RuleType(data.get("rule_type", "pricing")),
                conditions=[
                    {
                        "field": c.get("field"),
                        "operator": c.get("operator"),
                        "value": c.get("value"),
                        "value_type": c.get("value_type", "string"),
                    }
                    for c in data.get("conditions", [])
                ],
                actions=data.get("actions", []),
                priority=data.get("priority", 100),
                status=RuleStatus(data.get("status", "active")),
                tenant_id=data.get("tenant_id"),
                metadata=data.get("metadata", {}),
            )
            
            if data.get("effective_from"):
                rule.effective_from = date.fromisoformat(data["effective_from"])
            if data.get("effective_to"):
                rule.effective_to = date.fromisoformat(data["effective_to"])
            
            imported.append(rule)
        
        return imported


# Convenience function
def get_billing_rule_engine() -> BillingRuleEngine:
    """Get BillingRuleEngine instance."""
    return BillingRuleEngine()
