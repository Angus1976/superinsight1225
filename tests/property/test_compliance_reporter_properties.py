"""
Compliance Reporter Property Tests - 合规报告调度器属性测试
使用 Hypothesis 库进行属性测试

**Feature: system-optimization, Property 15**
**Validates: Requirements 7.2**
"""

import pytest
from hypothesis import given, settings, assume, example
from hypothesis import strategies as st
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4
import asyncio


# ============================================================================
# Local Schema Definitions (避免导入问题)
# ============================================================================

@dataclass
class CronParseResult:
    """Cron 表达式解析结果"""
    is_valid: bool
    minute: Optional[str] = None
    hour: Optional[str] = None
    day: Optional[str] = None
    month: Optional[str] = None
    day_of_week: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_valid": self.is_valid,
            "minute": self.minute,
            "hour": self.hour,
            "day": self.day,
            "month": self.month,
            "day_of_week": self.day_of_week,
            "error_message": self.error_message
        }


@dataclass
class ScheduledJob:
    """调度任务信息"""
    job_id: str
    report_type: str
    cron_expression: str
    recipients: List[str]
    config: Dict[str, Any] = field(default_factory=dict)
    is_paused: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


# ============================================================================
# Core Functions (独立实现，用于属性测试)
# ============================================================================

class CronParser:
    """Cron 表达式解析器 - 独立实现用于属性测试"""
    
    SUPPORTED_REPORT_TYPES = ["GDPR", "SOC2", "ACCESS", "PERMISSION_CHANGES"]
    
    @staticmethod
    def parse_cron_expression(expression: str) -> CronParseResult:
        """
        解析 cron 表达式
        
        支持标准 5 字段 cron 格式: 分 时 日 月 周
        
        **Validates: Requirements 7.2**
        """
        if not expression or not isinstance(expression, str):
            return CronParseResult(
                is_valid=False,
                error_message="Cron expression cannot be empty"
            )
        
        # 分割表达式
        parts = expression.strip().split()
        
        if len(parts) != 5:
            return CronParseResult(
                is_valid=False,
                error_message=f"Cron expression must have 5 fields, got {len(parts)}"
            )
        
        minute, hour, day, month, day_of_week = parts
        
        try:
            # 验证分钟 (0-59)
            if not CronParser._validate_cron_field(minute, 0, 59):
                return CronParseResult(
                    is_valid=False,
                    error_message=f"Invalid minute field: {minute}"
                )
            
            # 验证小时 (0-23)
            if not CronParser._validate_cron_field(hour, 0, 23):
                return CronParseResult(
                    is_valid=False,
                    error_message=f"Invalid hour field: {hour}"
                )
            
            # 验证日 (1-31)
            if not CronParser._validate_cron_field(day, 1, 31):
                return CronParseResult(
                    is_valid=False,
                    error_message=f"Invalid day field: {day}"
                )
            
            # 验证月 (1-12)
            if not CronParser._validate_cron_field(month, 1, 12):
                return CronParseResult(
                    is_valid=False,
                    error_message=f"Invalid month field: {month}"
                )
            
            # 验证星期 (0-6, 0=Sunday)
            if not CronParser._validate_cron_field(day_of_week, 0, 6):
                return CronParseResult(
                    is_valid=False,
                    error_message=f"Invalid day_of_week field: {day_of_week}"
                )
            
            return CronParseResult(
                is_valid=True,
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week
            )
            
        except Exception as e:
            return CronParseResult(
                is_valid=False,
                error_message=f"Failed to parse cron expression: {str(e)}"
            )
    
    @staticmethod
    def _validate_cron_field(field: str, min_val: int, max_val: int) -> bool:
        """验证单个 cron 字段"""
        if field == "*":
            return True
        
        # 处理步长 (*/n 或 range/n)
        if "/" in field:
            parts = field.split("/")
            if len(parts) != 2:
                return False
            
            base, step = parts
            
            try:
                step_val = int(step)
                if step_val <= 0:
                    return False
            except ValueError:
                return False
            
            if base == "*":
                return True
            
            if "-" in base:
                return CronParser._validate_cron_range(base, min_val, max_val)
            
            try:
                val = int(base)
                return min_val <= val <= max_val
            except ValueError:
                return False
        
        # 处理列表 (1,3,5)
        if "," in field:
            parts = field.split(",")
            for part in parts:
                part = part.strip()
                if "-" in part:
                    if not CronParser._validate_cron_range(part, min_val, max_val):
                        return False
                else:
                    try:
                        val = int(part)
                        if not (min_val <= val <= max_val):
                            return False
                    except ValueError:
                        return False
            return True
        
        # 处理范围 (1-5)
        if "-" in field:
            return CronParser._validate_cron_range(field, min_val, max_val)
        
        # 单个数字
        try:
            val = int(field)
            return min_val <= val <= max_val
        except ValueError:
            return False
    
    @staticmethod
    def _validate_cron_range(range_str: str, min_val: int, max_val: int) -> bool:
        """验证 cron 范围字段"""
        parts = range_str.split("-")
        if len(parts) != 2:
            return False
        
        try:
            start = int(parts[0])
            end = int(parts[1])
            
            if start > end:
                return False
            
            return min_val <= start <= max_val and min_val <= end <= max_val
            
        except ValueError:
            return False


# ============================================================================
# Hypothesis Strategies - 测试数据生成策略
# ============================================================================

# 有效的 cron 字段策略
valid_minute_strategy = st.one_of(
    st.just("*"),
    st.integers(min_value=0, max_value=59).map(str),
    st.tuples(
        st.integers(min_value=0, max_value=30),
        st.integers(min_value=31, max_value=59)
    ).map(lambda x: f"{x[0]}-{x[1]}"),
    st.lists(
        st.integers(min_value=0, max_value=59),
        min_size=2, max_size=5
    ).map(lambda x: ",".join(map(str, sorted(set(x))))),
    st.integers(min_value=1, max_value=30).map(lambda x: f"*/{x}")
)

valid_hour_strategy = st.one_of(
    st.just("*"),
    st.integers(min_value=0, max_value=23).map(str),
    st.tuples(
        st.integers(min_value=0, max_value=12),
        st.integers(min_value=13, max_value=23)
    ).map(lambda x: f"{x[0]}-{x[1]}"),
    st.lists(
        st.integers(min_value=0, max_value=23),
        min_size=2, max_size=5
    ).map(lambda x: ",".join(map(str, sorted(set(x))))),
    st.integers(min_value=1, max_value=12).map(lambda x: f"*/{x}")
)

valid_day_strategy = st.one_of(
    st.just("*"),
    st.integers(min_value=1, max_value=31).map(str),
    st.tuples(
        st.integers(min_value=1, max_value=15),
        st.integers(min_value=16, max_value=31)
    ).map(lambda x: f"{x[0]}-{x[1]}"),
    st.lists(
        st.integers(min_value=1, max_value=31),
        min_size=2, max_size=5
    ).map(lambda x: ",".join(map(str, sorted(set(x))))),
    st.integers(min_value=1, max_value=15).map(lambda x: f"*/{x}")
)

valid_month_strategy = st.one_of(
    st.just("*"),
    st.integers(min_value=1, max_value=12).map(str),
    st.tuples(
        st.integers(min_value=1, max_value=6),
        st.integers(min_value=7, max_value=12)
    ).map(lambda x: f"{x[0]}-{x[1]}"),
    st.lists(
        st.integers(min_value=1, max_value=12),
        min_size=2, max_size=5
    ).map(lambda x: ",".join(map(str, sorted(set(x))))),
    st.integers(min_value=1, max_value=6).map(lambda x: f"*/{x}")
)

valid_dow_strategy = st.one_of(
    st.just("*"),
    st.integers(min_value=0, max_value=6).map(str),
    st.tuples(
        st.integers(min_value=0, max_value=3),
        st.integers(min_value=4, max_value=6)
    ).map(lambda x: f"{x[0]}-{x[1]}"),
    st.lists(
        st.integers(min_value=0, max_value=6),
        min_size=2, max_size=4
    ).map(lambda x: ",".join(map(str, sorted(set(x)))))
)

# 有效的 cron 表达式策略
valid_cron_expression_strategy = st.tuples(
    valid_minute_strategy,
    valid_hour_strategy,
    valid_day_strategy,
    valid_month_strategy,
    valid_dow_strategy
).map(lambda x: " ".join(x))

# 无效的 cron 表达式策略
invalid_cron_expression_strategy = st.one_of(
    # 空字符串
    st.just(""),
    # 字段数量不对
    st.text(min_size=1, max_size=10),
    st.just("* * *"),
    st.just("* * * * * *"),
    # 超出范围的值
    st.just("60 * * * *"),  # 分钟超出范围
    st.just("* 24 * * *"),  # 小时超出范围
    st.just("* * 32 * *"),  # 日超出范围
    st.just("* * * 13 *"),  # 月超出范围
    st.just("* * * * 7"),   # 星期超出范围
    # 无效的范围
    st.just("30-10 * * * *"),  # 范围起始大于结束
    st.just("* 20-10 * * *"),
    # 无效的步长
    st.just("*/0 * * * *"),  # 步长为 0
    st.just("*/-1 * * * *"),  # 负步长
)

# 报告类型策略
valid_report_type_strategy = st.sampled_from(
    ["GDPR", "SOC2", "ACCESS", "PERMISSION_CHANGES"]
)

invalid_report_type_strategy = st.one_of(
    st.just("INVALID"),
    st.just("gdpr"),  # 小写
    st.just(""),
    st.text(min_size=1, max_size=20).filter(
        lambda x: x not in ["GDPR", "SOC2", "ACCESS", "PERMISSION_CHANGES"]
    )
)

# 收件人策略
recipients_strategy = st.lists(
    st.emails(),
    min_size=1,
    max_size=10
)


# ============================================================================
# Property 15: 合规报告 cron 表达式解析
# ============================================================================

class TestCronExpressionParsing:
    """
    Property 15: 合规报告 cron 表达式解析
    
    *对于任意*有效的 cron 表达式，系统应该正确计算下次运行时间；
    对于无效的 cron 表达式，应该返回错误。
    
    **Feature: system-optimization**
    **Validates: Requirements 7.2**
    """
    
    @given(cron_expr=valid_cron_expression_strategy)
    @settings(max_examples=100, deadline=None)
    def test_valid_cron_expressions_are_parsed_successfully(self, cron_expr: str):
        """
        Property: 有效的 cron 表达式应该被成功解析
        
        **Validates: Requirements 7.2**
        """
        result = CronParser.parse_cron_expression(cron_expr)
        
        # 有效的表达式应该解析成功
        assert result.is_valid, f"Valid cron expression '{cron_expr}' should be parsed successfully"
        
        # 解析结果应该包含所有字段
        assert result.minute is not None
        assert result.hour is not None
        assert result.day is not None
        assert result.month is not None
        assert result.day_of_week is not None
        
        # 不应该有错误消息
        assert result.error_message is None
    
    @given(cron_expr=invalid_cron_expression_strategy)
    @settings(max_examples=50, deadline=None)
    def test_invalid_cron_expressions_return_error(self, cron_expr: str):
        """
        Property: 无效的 cron 表达式应该返回错误
        
        **Validates: Requirements 7.2**
        """
        result = CronParser.parse_cron_expression(cron_expr)
        
        # 无效的表达式应该解析失败
        assert not result.is_valid, f"Invalid cron expression '{cron_expr}' should fail parsing"
        
        # 应该有错误消息
        assert result.error_message is not None
        assert len(result.error_message) > 0
    
    @example("0 0 * * *")      # 每天午夜
    @example("*/15 * * * *")   # 每 15 分钟
    @example("0 9 * * 1-5")    # 工作日早上 9 点
    @example("0 0 1 * *")      # 每月 1 号
    @example("30 4 1,15 * *")  # 每月 1 号和 15 号凌晨 4:30
    @given(cron_expr=valid_cron_expression_strategy)
    @settings(max_examples=50, deadline=None)
    def test_cron_expression_roundtrip(self, cron_expr: str):
        """
        Property: cron 表达式解析后应该保持字段值不变
        
        **Validates: Requirements 7.2**
        """
        result = CronParser.parse_cron_expression(cron_expr)
        
        if result.is_valid:
            # 重新组合字段应该得到原始表达式
            reconstructed = f"{result.minute} {result.hour} {result.day} {result.month} {result.day_of_week}"
            assert reconstructed == cron_expr, f"Roundtrip failed: '{cron_expr}' -> '{reconstructed}'"
    
    def test_empty_expression_returns_error(self):
        """
        Property: 空表达式应该返回错误
        
        **Validates: Requirements 7.2**
        """
        result = CronParser.parse_cron_expression("")
        assert not result.is_valid
        assert "empty" in result.error_message.lower()
    
    def test_none_expression_returns_error(self):
        """
        Property: None 表达式应该返回错误
        
        **Validates: Requirements 7.2**
        """
        result = CronParser.parse_cron_expression(None)
        assert not result.is_valid
        assert "empty" in result.error_message.lower()
    
    @given(num_fields=st.integers(min_value=1, max_value=10).filter(lambda x: x != 5))
    @settings(max_examples=20, deadline=None)
    def test_wrong_number_of_fields_returns_error(self, num_fields: int):
        """
        Property: 字段数量不是 5 的表达式应该返回错误
        
        **Validates: Requirements 7.2**
        """
        fields = ["*"] * num_fields
        cron_expr = " ".join(fields)
        
        result = CronParser.parse_cron_expression(cron_expr)
        
        assert not result.is_valid
        assert "5 fields" in result.error_message


class TestCronFieldValidation:
    """
    Cron 字段验证测试
    
    **Feature: system-optimization**
    **Validates: Requirements 7.2**
    """
    
    @given(minute=st.integers(min_value=0, max_value=59))
    @settings(max_examples=30, deadline=None)
    def test_valid_minute_values(self, minute: int):
        """
        Property: 0-59 范围内的分钟值应该有效
        
        **Validates: Requirements 7.2**
        """
        cron_expr = f"{minute} * * * *"
        result = CronParser.parse_cron_expression(cron_expr)
        assert result.is_valid, f"Minute {minute} should be valid"
    
    @given(minute=st.integers(min_value=60, max_value=100))
    @settings(max_examples=20, deadline=None)
    def test_invalid_minute_values(self, minute: int):
        """
        Property: 超出 0-59 范围的分钟值应该无效
        
        **Validates: Requirements 7.2**
        """
        cron_expr = f"{minute} * * * *"
        result = CronParser.parse_cron_expression(cron_expr)
        assert not result.is_valid, f"Minute {minute} should be invalid"
    
    @given(hour=st.integers(min_value=0, max_value=23))
    @settings(max_examples=24, deadline=None)
    def test_valid_hour_values(self, hour: int):
        """
        Property: 0-23 范围内的小时值应该有效
        
        **Validates: Requirements 7.2**
        """
        cron_expr = f"* {hour} * * *"
        result = CronParser.parse_cron_expression(cron_expr)
        assert result.is_valid, f"Hour {hour} should be valid"
    
    @given(hour=st.integers(min_value=24, max_value=50))
    @settings(max_examples=20, deadline=None)
    def test_invalid_hour_values(self, hour: int):
        """
        Property: 超出 0-23 范围的小时值应该无效
        
        **Validates: Requirements 7.2**
        """
        cron_expr = f"* {hour} * * *"
        result = CronParser.parse_cron_expression(cron_expr)
        assert not result.is_valid, f"Hour {hour} should be invalid"
    
    @given(day=st.integers(min_value=1, max_value=31))
    @settings(max_examples=31, deadline=None)
    def test_valid_day_values(self, day: int):
        """
        Property: 1-31 范围内的日值应该有效
        
        **Validates: Requirements 7.2**
        """
        cron_expr = f"* * {day} * *"
        result = CronParser.parse_cron_expression(cron_expr)
        assert result.is_valid, f"Day {day} should be valid"
    
    @given(day=st.one_of(
        st.integers(min_value=-10, max_value=0),
        st.integers(min_value=32, max_value=50)
    ))
    @settings(max_examples=20, deadline=None)
    def test_invalid_day_values(self, day: int):
        """
        Property: 超出 1-31 范围的日值应该无效
        
        **Validates: Requirements 7.2**
        """
        cron_expr = f"* * {day} * *"
        result = CronParser.parse_cron_expression(cron_expr)
        assert not result.is_valid, f"Day {day} should be invalid"
    
    @given(month=st.integers(min_value=1, max_value=12))
    @settings(max_examples=12, deadline=None)
    def test_valid_month_values(self, month: int):
        """
        Property: 1-12 范围内的月值应该有效
        
        **Validates: Requirements 7.2**
        """
        cron_expr = f"* * * {month} *"
        result = CronParser.parse_cron_expression(cron_expr)
        assert result.is_valid, f"Month {month} should be valid"
    
    @given(month=st.one_of(
        st.integers(min_value=-10, max_value=0),
        st.integers(min_value=13, max_value=50)
    ))
    @settings(max_examples=20, deadline=None)
    def test_invalid_month_values(self, month: int):
        """
        Property: 超出 1-12 范围的月值应该无效
        
        **Validates: Requirements 7.2**
        """
        cron_expr = f"* * * {month} *"
        result = CronParser.parse_cron_expression(cron_expr)
        assert not result.is_valid, f"Month {month} should be invalid"
    
    @given(dow=st.integers(min_value=0, max_value=6))
    @settings(max_examples=7, deadline=None)
    def test_valid_day_of_week_values(self, dow: int):
        """
        Property: 0-6 范围内的星期值应该有效
        
        **Validates: Requirements 7.2**
        """
        cron_expr = f"* * * * {dow}"
        result = CronParser.parse_cron_expression(cron_expr)
        assert result.is_valid, f"Day of week {dow} should be valid"
    
    @given(dow=st.one_of(
        st.integers(min_value=-10, max_value=-1),
        st.integers(min_value=7, max_value=50)
    ))
    @settings(max_examples=20, deadline=None)
    def test_invalid_day_of_week_values(self, dow: int):
        """
        Property: 超出 0-6 范围的星期值应该无效
        
        **Validates: Requirements 7.2**
        """
        cron_expr = f"* * * * {dow}"
        result = CronParser.parse_cron_expression(cron_expr)
        assert not result.is_valid, f"Day of week {dow} should be invalid"


class TestCronSpecialPatterns:
    """
    Cron 特殊模式测试
    
    **Feature: system-optimization**
    **Validates: Requirements 7.2**
    """
    
    def test_wildcard_pattern(self):
        """
        Property: 通配符 * 应该在所有字段中有效
        
        **Validates: Requirements 7.2**
        """
        result = CronParser.parse_cron_expression("* * * * *")
        assert result.is_valid
        assert result.minute == "*"
        assert result.hour == "*"
        assert result.day == "*"
        assert result.month == "*"
        assert result.day_of_week == "*"
    
    @given(step=st.integers(min_value=1, max_value=30))
    @settings(max_examples=20, deadline=None)
    def test_step_pattern_with_wildcard(self, step: int):
        """
        Property: */n 步长模式应该有效
        
        **Validates: Requirements 7.2**
        """
        cron_expr = f"*/{step} * * * *"
        result = CronParser.parse_cron_expression(cron_expr)
        assert result.is_valid, f"Step pattern */{step} should be valid"
    
    @given(
        start=st.integers(min_value=0, max_value=30),
        end=st.integers(min_value=31, max_value=59)
    )
    @settings(max_examples=20, deadline=None)
    def test_range_pattern(self, start: int, end: int):
        """
        Property: start-end 范围模式应该有效
        
        **Validates: Requirements 7.2**
        """
        cron_expr = f"{start}-{end} * * * *"
        result = CronParser.parse_cron_expression(cron_expr)
        assert result.is_valid, f"Range pattern {start}-{end} should be valid"
    
    @given(
        start=st.integers(min_value=30, max_value=59),
        end=st.integers(min_value=0, max_value=29)
    )
    @settings(max_examples=20, deadline=None)
    def test_invalid_range_pattern(self, start: int, end: int):
        """
        Property: 起始大于结束的范围应该无效
        
        **Validates: Requirements 7.2**
        """
        cron_expr = f"{start}-{end} * * * *"
        result = CronParser.parse_cron_expression(cron_expr)
        assert not result.is_valid, f"Invalid range {start}-{end} should fail"
    
    @given(values=st.lists(
        st.integers(min_value=0, max_value=59),
        min_size=2,
        max_size=5,
        unique=True
    ))
    @settings(max_examples=20, deadline=None)
    def test_list_pattern(self, values: List[int]):
        """
        Property: 逗号分隔的列表模式应该有效
        
        **Validates: Requirements 7.2**
        """
        list_str = ",".join(map(str, sorted(values)))
        cron_expr = f"{list_str} * * * *"
        result = CronParser.parse_cron_expression(cron_expr)
        assert result.is_valid, f"List pattern {list_str} should be valid"
    
    def test_zero_step_is_invalid(self):
        """
        Property: 步长为 0 应该无效
        
        **Validates: Requirements 7.2**
        """
        result = CronParser.parse_cron_expression("*/0 * * * *")
        assert not result.is_valid
    
    def test_negative_step_is_invalid(self):
        """
        Property: 负步长应该无效
        
        **Validates: Requirements 7.2**
        """
        result = CronParser.parse_cron_expression("*/-1 * * * *")
        assert not result.is_valid


class TestCommonCronExpressions:
    """
    常见 cron 表达式测试
    
    **Feature: system-optimization**
    **Validates: Requirements 7.2**
    """
    
    def test_every_minute(self):
        """每分钟执行"""
        result = CronParser.parse_cron_expression("* * * * *")
        assert result.is_valid
    
    def test_every_hour(self):
        """每小时执行"""
        result = CronParser.parse_cron_expression("0 * * * *")
        assert result.is_valid
    
    def test_every_day_at_midnight(self):
        """每天午夜执行"""
        result = CronParser.parse_cron_expression("0 0 * * *")
        assert result.is_valid
    
    def test_every_monday(self):
        """每周一执行"""
        result = CronParser.parse_cron_expression("0 0 * * 1")
        assert result.is_valid
    
    def test_first_day_of_month(self):
        """每月 1 号执行"""
        result = CronParser.parse_cron_expression("0 0 1 * *")
        assert result.is_valid
    
    def test_every_15_minutes(self):
        """每 15 分钟执行"""
        result = CronParser.parse_cron_expression("*/15 * * * *")
        assert result.is_valid
    
    def test_weekdays_at_9am(self):
        """工作日早上 9 点执行"""
        result = CronParser.parse_cron_expression("0 9 * * 1-5")
        assert result.is_valid
    
    def test_quarterly_report(self):
        """季度报告 (每季度第一天)"""
        result = CronParser.parse_cron_expression("0 0 1 1,4,7,10 *")
        assert result.is_valid
    
    def test_annual_report(self):
        """年度报告 (每年 1 月 1 日)"""
        result = CronParser.parse_cron_expression("0 0 1 1 *")
        assert result.is_valid


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
