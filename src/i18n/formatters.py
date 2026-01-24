"""
i18n Formatters Module

Provides locale-aware formatting for dates, numbers, currencies, and other data types.
Supports Chinese (zh) and English (en) locales.
"""

from typing import Optional, Union
from datetime import datetime, date, time
from decimal import Decimal
import logging

from .translations import get_current_language

logger = logging.getLogger(__name__)


# ============================================================================
# Date and Time Formatting
# ============================================================================

class DateTimeFormatter:
    """Locale-aware date and time formatter."""

    # 日期格式模板
    DATE_FORMATS = {
        'zh': {
            'short': '%Y-%m-%d',  # 2024-01-24
            'medium': '%Y年%m月%d日',  # 2024年01月24日
            'long': '%Y年%m月%d日 %A',  # 2024年01月24日 星期三
            'full': '%Y年%m月%d日 %A %H:%M:%S',  # 2024年01月24日 星期三 14:30:00
        },
        'en': {
            'short': '%Y-%m-%d',  # 2024-01-24
            'medium': '%b %d, %Y',  # Jan 24, 2024
            'long': '%B %d, %Y',  # January 24, 2024
            'full': '%A, %B %d, %Y %I:%M:%S %p',  # Wednesday, January 24, 2024 02:30:00 PM
        }
    }

    # 时间格式模板
    TIME_FORMATS = {
        'zh': {
            'short': '%H:%M',  # 14:30
            'medium': '%H:%M:%S',  # 14:30:45
            'long': '%H时%M分%S秒',  # 14时30分45秒
        },
        'en': {
            'short': '%I:%M %p',  # 02:30 PM
            'medium': '%I:%M:%S %p',  # 02:30:45 PM
            'long': '%I:%M:%S %p %Z',  # 02:30:45 PM UTC
        }
    }

    # 星期名称
    WEEKDAY_NAMES = {
        'zh': ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'],
        'en': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    }

    # 月份名称
    MONTH_NAMES = {
        'zh': ['一月', '二月', '三月', '四月', '五月', '六月',
               '七月', '八月', '九月', '十月', '十一月', '十二月'],
        'en': ['January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']
    }

    @classmethod
    def format_date(
        cls,
        dt: Union[datetime, date],
        format_style: str = 'medium',
        language: Optional[str] = None
    ) -> str:
        """
        Format a date according to locale.

        Args:
            dt: Date or datetime to format
            format_style: Format style ('short', 'medium', 'long', 'full')
            language: Language code (defaults to current language)

        Returns:
            Formatted date string
        """
        if language is None:
            language = get_current_language()

        try:
            format_str = cls.DATE_FORMATS.get(language, cls.DATE_FORMATS['en']).get(
                format_style, cls.DATE_FORMATS['en']['medium']
            )
            return dt.strftime(format_str)
        except Exception as e:
            logger.warning(f"Date formatting failed: {e}")
            return str(dt)

    @classmethod
    def format_time(
        cls,
        tm: Union[datetime, time],
        format_style: str = 'medium',
        language: Optional[str] = None
    ) -> str:
        """
        Format a time according to locale.

        Args:
            tm: Time or datetime to format
            format_style: Format style ('short', 'medium', 'long')
            language: Language code (defaults to current language)

        Returns:
            Formatted time string
        """
        if language is None:
            language = get_current_language()

        try:
            format_str = cls.TIME_FORMATS.get(language, cls.TIME_FORMATS['en']).get(
                format_style, cls.TIME_FORMATS['en']['medium']
            )
            return tm.strftime(format_str)
        except Exception as e:
            logger.warning(f"Time formatting failed: {e}")
            return str(tm)

    @classmethod
    def format_datetime(
        cls,
        dt: datetime,
        format_style: str = 'medium',
        language: Optional[str] = None
    ) -> str:
        """
        Format a datetime according to locale.

        Args:
            dt: Datetime to format
            format_style: Format style ('short', 'medium', 'long', 'full')
            language: Language code (defaults to current language)

        Returns:
            Formatted datetime string
        """
        if language is None:
            language = get_current_language()

        try:
            date_format = cls.DATE_FORMATS.get(language, cls.DATE_FORMATS['en']).get(
                format_style, cls.DATE_FORMATS['en']['medium']
            )
            time_format = cls.TIME_FORMATS.get(language, cls.TIME_FORMATS['en']).get(
                'medium', cls.TIME_FORMATS['en']['medium']
            )

            if language == 'zh':
                return f"{dt.strftime(date_format)} {dt.strftime(time_format)}"
            else:
                return f"{dt.strftime(date_format)} {dt.strftime(time_format)}"
        except Exception as e:
            logger.warning(f"Datetime formatting failed: {e}")
            return str(dt)

    @classmethod
    def format_relative_time(
        cls,
        dt: datetime,
        now: Optional[datetime] = None,
        language: Optional[str] = None
    ) -> str:
        """
        Format relative time (e.g., "2 hours ago", "in 3 days").

        Args:
            dt: Datetime to format
            now: Reference datetime (defaults to current time)
            language: Language code (defaults to current language)

        Returns:
            Relative time string
        """
        if language is None:
            language = get_current_language()

        if now is None:
            now = datetime.now()

        delta = now - dt
        seconds = abs(delta.total_seconds())

        if language == 'zh':
            if delta.total_seconds() > 0:  # Past
                if seconds < 60:
                    return f"{int(seconds)}秒前"
                elif seconds < 3600:
                    return f"{int(seconds / 60)}分钟前"
                elif seconds < 86400:
                    return f"{int(seconds / 3600)}小时前"
                elif seconds < 2592000:  # 30 days
                    return f"{int(seconds / 86400)}天前"
                elif seconds < 31536000:  # 365 days
                    return f"{int(seconds / 2592000)}个月前"
                else:
                    return f"{int(seconds / 31536000)}年前"
            else:  # Future
                if seconds < 60:
                    return f"{int(seconds)}秒后"
                elif seconds < 3600:
                    return f"{int(seconds / 60)}分钟后"
                elif seconds < 86400:
                    return f"{int(seconds / 3600)}小时后"
                elif seconds < 2592000:
                    return f"{int(seconds / 86400)}天后"
                elif seconds < 31536000:
                    return f"{int(seconds / 2592000)}个月后"
                else:
                    return f"{int(seconds / 31536000)}年后"
        else:  # English
            if delta.total_seconds() > 0:  # Past
                if seconds < 60:
                    return f"{int(seconds)} seconds ago"
                elif seconds < 3600:
                    mins = int(seconds / 60)
                    return f"{mins} minute ago" if mins == 1 else f"{mins} minutes ago"
                elif seconds < 86400:
                    hours = int(seconds / 3600)
                    return f"{hours} hour ago" if hours == 1 else f"{hours} hours ago"
                elif seconds < 2592000:
                    days = int(seconds / 86400)
                    return f"{days} day ago" if days == 1 else f"{days} days ago"
                elif seconds < 31536000:
                    months = int(seconds / 2592000)
                    return f"{months} month ago" if months == 1 else f"{months} months ago"
                else:
                    years = int(seconds / 31536000)
                    return f"{years} year ago" if years == 1 else f"{years} years ago"
            else:  # Future
                if seconds < 60:
                    return f"in {int(seconds)} seconds"
                elif seconds < 3600:
                    mins = int(seconds / 60)
                    return f"in {mins} minute" if mins == 1 else f"in {mins} minutes"
                elif seconds < 86400:
                    hours = int(seconds / 3600)
                    return f"in {hours} hour" if hours == 1 else f"in {hours} hours"
                elif seconds < 2592000:
                    days = int(seconds / 86400)
                    return f"in {days} day" if days == 1 else f"in {days} days"
                elif seconds < 31536000:
                    months = int(seconds / 2592000)
                    return f"in {months} month" if months == 1 else f"in {months} months"
                else:
                    years = int(seconds / 31536000)
                    return f"in {years} year" if years == 1 else f"in {years} years"


# ============================================================================
# Number Formatting
# ============================================================================

class NumberFormatter:
    """Locale-aware number formatter."""

    # 千位分隔符
    THOUSAND_SEPARATOR = {
        'zh': ',',
        'en': ','
    }

    # 小数点符号
    DECIMAL_SEPARATOR = {
        'zh': '.',
        'en': '.'
    }

    @classmethod
    def format_number(
        cls,
        value: Union[int, float, Decimal],
        decimals: Optional[int] = None,
        use_grouping: bool = True,
        language: Optional[str] = None
    ) -> str:
        """
        Format a number according to locale.

        Args:
            value: Number to format
            decimals: Number of decimal places (None = auto)
            use_grouping: Whether to use thousand separators
            language: Language code (defaults to current language)

        Returns:
            Formatted number string
        """
        if language is None:
            language = get_current_language()

        try:
            thousand_sep = cls.THOUSAND_SEPARATOR.get(language, ',')
            decimal_sep = cls.DECIMAL_SEPARATOR.get(language, '.')

            if decimals is not None:
                formatted = f"{value:.{decimals}f}"
            else:
                formatted = str(value)

            # Split into integer and decimal parts
            if '.' in formatted:
                integer_part, decimal_part = formatted.split('.')
            else:
                integer_part = formatted
                decimal_part = None

            # Add thousand separators
            if use_grouping and len(integer_part) > 3:
                # Handle negative numbers
                if integer_part.startswith('-'):
                    sign = '-'
                    integer_part = integer_part[1:]
                else:
                    sign = ''

                # Add separators
                parts = []
                for i, digit in enumerate(reversed(integer_part)):
                    if i > 0 and i % 3 == 0:
                        parts.append(thousand_sep)
                    parts.append(digit)
                integer_part = sign + ''.join(reversed(parts))

            # Combine parts
            if decimal_part is not None:
                return f"{integer_part}{decimal_sep}{decimal_part}"
            else:
                return integer_part

        except Exception as e:
            logger.warning(f"Number formatting failed: {e}")
            return str(value)

    @classmethod
    def format_percent(
        cls,
        value: Union[float, Decimal],
        decimals: int = 2,
        language: Optional[str] = None
    ) -> str:
        """
        Format a number as percentage.

        Args:
            value: Number to format (0.5 = 50%)
            decimals: Number of decimal places
            language: Language code (defaults to current language)

        Returns:
            Formatted percentage string
        """
        percent_value = value * 100
        formatted = cls.format_number(percent_value, decimals=decimals, use_grouping=False, language=language)
        return f"{formatted}%"


# ============================================================================
# Currency Formatting
# ============================================================================

class CurrencyFormatter:
    """Locale-aware currency formatter."""

    # 货币符号
    CURRENCY_SYMBOLS = {
        'CNY': {'symbol': '¥', 'position': 'prefix', 'name_zh': '人民币', 'name_en': 'Chinese Yuan'},
        'USD': {'symbol': '$', 'position': 'prefix', 'name_zh': '美元', 'name_en': 'US Dollar'},
        'EUR': {'symbol': '€', 'position': 'prefix', 'name_zh': '欧元', 'name_en': 'Euro'},
        'GBP': {'symbol': '£', 'position': 'prefix', 'name_zh': '英镑', 'name_en': 'British Pound'},
        'JPY': {'symbol': '¥', 'position': 'prefix', 'name_zh': '日元', 'name_en': 'Japanese Yen'},
    }

    @classmethod
    def format_currency(
        cls,
        value: Union[int, float, Decimal],
        currency: str = 'CNY',
        show_symbol: bool = True,
        language: Optional[str] = None
    ) -> str:
        """
        Format a number as currency.

        Args:
            value: Amount to format
            currency: Currency code (CNY, USD, EUR, etc.)
            show_symbol: Whether to show currency symbol
            language: Language code (defaults to current language)

        Returns:
            Formatted currency string
        """
        if language is None:
            language = get_current_language()

        try:
            # Get currency info
            currency_info = cls.CURRENCY_SYMBOLS.get(currency.upper(), {
                'symbol': currency,
                'position': 'prefix',
                'name_zh': currency,
                'name_en': currency
            })

            # Format number
            formatted_value = NumberFormatter.format_number(
                value,
                decimals=2,
                use_grouping=True,
                language=language
            )

            # Add currency symbol
            if show_symbol:
                symbol = currency_info['symbol']
                position = currency_info['position']

                if position == 'prefix':
                    return f"{symbol}{formatted_value}"
                else:
                    return f"{formatted_value} {symbol}"
            else:
                return formatted_value

        except Exception as e:
            logger.warning(f"Currency formatting failed: {e}")
            return f"{value} {currency}"

    @classmethod
    def get_currency_name(
        cls,
        currency: str,
        language: Optional[str] = None
    ) -> str:
        """
        Get localized currency name.

        Args:
            currency: Currency code
            language: Language code (defaults to current language)

        Returns:
            Localized currency name
        """
        if language is None:
            language = get_current_language()

        currency_info = cls.CURRENCY_SYMBOLS.get(currency.upper())
        if currency_info:
            if language == 'zh':
                return currency_info['name_zh']
            else:
                return currency_info['name_en']
        else:
            return currency


# ============================================================================
# Convenience Functions
# ============================================================================

def format_date(
    dt: Union[datetime, date],
    format_style: str = 'medium',
    language: Optional[str] = None
) -> str:
    """Shortcut for DateTimeFormatter.format_date."""
    return DateTimeFormatter.format_date(dt, format_style, language)


def format_time(
    tm: Union[datetime, time],
    format_style: str = 'medium',
    language: Optional[str] = None
) -> str:
    """Shortcut for DateTimeFormatter.format_time."""
    return DateTimeFormatter.format_time(tm, format_style, language)


def format_datetime(
    dt: datetime,
    format_style: str = 'medium',
    language: Optional[str] = None
) -> str:
    """Shortcut for DateTimeFormatter.format_datetime."""
    return DateTimeFormatter.format_datetime(dt, format_style, language)


def format_relative_time(
    dt: datetime,
    now: Optional[datetime] = None,
    language: Optional[str] = None
) -> str:
    """Shortcut for DateTimeFormatter.format_relative_time."""
    return DateTimeFormatter.format_relative_time(dt, now, language)


def format_number(
    value: Union[int, float, Decimal],
    decimals: Optional[int] = None,
    use_grouping: bool = True,
    language: Optional[str] = None
) -> str:
    """Shortcut for NumberFormatter.format_number."""
    return NumberFormatter.format_number(value, decimals, use_grouping, language)


def format_percent(
    value: Union[float, Decimal],
    decimals: int = 2,
    language: Optional[str] = None
) -> str:
    """Shortcut for NumberFormatter.format_percent."""
    return NumberFormatter.format_percent(value, decimals, language)


def format_currency(
    value: Union[int, float, Decimal],
    currency: str = 'CNY',
    show_symbol: bool = True,
    language: Optional[str] = None
) -> str:
    """Shortcut for CurrencyFormatter.format_currency."""
    return CurrencyFormatter.format_currency(value, currency, show_symbol, language)


# ============================================================================
# Export
# ============================================================================

__all__ = [
    # Classes
    'DateTimeFormatter',
    'NumberFormatter',
    'CurrencyFormatter',

    # Convenience functions
    'format_date',
    'format_time',
    'format_datetime',
    'format_relative_time',
    'format_number',
    'format_percent',
    'format_currency',
]
