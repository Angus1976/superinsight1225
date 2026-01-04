# SuperInsight i18n Extension and Customization Guide

## Overview

This guide provides comprehensive instructions for extending and customizing the SuperInsight i18n system. Whether you need to add new languages, integrate external translation services, or customize behavior, this document covers all extension points.

## Adding New Languages

### Step 1: Define Translation Dictionary

Add translations for your new language to the main translation dictionary:

```python
# src/i18n/translations.py

# Add your language translations
TRANSLATIONS['ja'] = {  # Japanese example
    'app_name': 'SuperInsight プラットフォーム',
    'login': 'ログイン',
    'logout': 'ログアウト',
    'dashboard': 'ダッシュボード',
    'settings': '設定',
    'profile': 'プロフィール',
    'help': 'ヘルプ',
    'search': '検索',
    'save': '保存',
    'cancel': 'キャンセル',
    'delete': '削除',
    'edit': '編集',
    'create': '作成',
    'update': '更新',
    'success': '成功',
    'error': 'エラー',
    'warning': '警告',
    'info': '情報',
    # ... add all required keys
}

TRANSLATIONS['fr'] = {  # French example
    'app_name': 'Plateforme SuperInsight',
    'login': 'Connexion',
    'logout': 'Déconnexion',
    'dashboard': 'Tableau de bord',
    'settings': 'Paramètres',
    'profile': 'Profil',
    'help': 'Aide',
    'search': 'Rechercher',
    'save': 'Enregistrer',
    'cancel': 'Annuler',
    'delete': 'Supprimer',
    'edit': 'Modifier',
    'create': 'Créer',
    'update': 'Mettre à jour',
    'success': 'Succès',
    'error': 'Erreur',
    'warning': 'Avertissement',
    'info': 'Information',
    # ... add all required keys
}
```

### Step 2: Update Supported Languages List

```python
# src/i18n/manager.py

class TranslationManager:
    def __init__(self, default_language: str = 'zh'):
        # Add new languages to supported list
        self._supported_languages = ['zh', 'en', 'ja', 'fr']  # Add your languages
        # ... rest of initialization
```

### Step 3: Add Language Metadata

Create language-specific configuration:

```python
# src/i18n/language_config.py

LANGUAGE_METADATA = {
    'ja': {
        'name': 'Japanese',
        'native_name': '日本語',
        'direction': 'ltr',
        'locale': 'ja-JP',
        'font_family': 'Noto Sans JP, sans-serif',
        'text_expansion_factor': 1.2,  # Japanese text is typically longer
    },
    'fr': {
        'name': 'French',
        'native_name': 'Français',
        'direction': 'ltr',
        'locale': 'fr-FR',
        'font_family': 'Arial, sans-serif',
        'text_expansion_factor': 1.15,  # French text is typically longer
    },
    'ar': {
        'name': 'Arabic',
        'native_name': 'العربية',
        'direction': 'rtl',  # Right-to-left
        'locale': 'ar-SA',
        'font_family': 'Noto Sans Arabic, sans-serif',
        'text_expansion_factor': 0.9,  # Arabic text is typically shorter
    }
}
```

### Step 4: Add Validation Rules

```python
# src/i18n/validation.py

def validate_language_completeness():
    """Validate that all languages have complete translations."""
    base_keys = set(TRANSLATIONS['zh'].keys())  # Use Chinese as reference
    
    for language, translations in TRANSLATIONS.items():
        language_keys = set(translations.keys())
        missing_keys = base_keys - language_keys
        extra_keys = language_keys - base_keys
        
        if missing_keys:
            logger.warning(f"Language {language} missing keys: {missing_keys}")
        
        if extra_keys:
            logger.info(f"Language {language} has extra keys: {extra_keys}")
    
    return True

# Add language-specific validators
class LanguageValidator:
    def __init__(self, language_code: str):
        self.language_code = language_code
        self.metadata = LANGUAGE_METADATA.get(language_code, {})
    
    def validate_text_length(self, text: str, max_length: int) -> bool:
        """Validate text length considering language expansion factor."""
        expansion_factor = self.metadata.get('text_expansion_factor', 1.0)
        effective_length = len(text) * expansion_factor
        return effective_length <= max_length
    
    def validate_direction(self, text: str) -> bool:
        """Validate text direction for RTL languages."""
        if self.metadata.get('direction') == 'rtl':
            # Add RTL-specific validation logic
            return self._validate_rtl_text(text)
        return True
```

### Step 5: Update API Endpoints

The API endpoints will automatically support new languages once they're added to the supported languages list. No additional changes needed.

### Step 6: Add Tests

```python
# tests/test_new_languages.py

import pytest
from src.i18n.manager import get_manager

class TestNewLanguages:
    def test_japanese_translations(self):
        """Test Japanese language support."""
        manager = get_manager()
        manager.set_language('ja')
        
        assert manager.translate('login') == 'ログイン'
        assert manager.translate('app_name') == 'SuperInsight プラットフォーム'
    
    def test_french_translations(self):
        """Test French language support."""
        manager = get_manager()
        manager.set_language('fr')
        
        assert manager.translate('login') == 'Connexion'
        assert manager.translate('app_name') == 'Plateforme SuperInsight'
    
    @pytest.mark.parametrize('language', ['ja', 'fr'])
    def test_translation_completeness(self, language):
        """Test that new languages have complete translations."""
        manager = get_manager()
        base_keys = set(manager.get_all('zh').keys())
        language_keys = set(manager.get_all(language).keys())
        
        # Should have same keys as base language
        assert base_keys == language_keys
```

## Custom Translation Sources

### Database-Backed Translations

Create a custom translation source that loads from a database:

```python
# src/i18n/sources/database_source.py

from abc import ABC, abstractmethod
from typing import Dict, Optional
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

class TranslationSource(ABC):
    """Abstract base class for translation sources."""
    
    @abstractmethod
    def get_translation(self, key: str, language: str) -> Optional[str]:
        pass
    
    @abstractmethod
    def get_all_translations(self, language: str) -> Dict[str, str]:
        pass
    
    @abstractmethod
    def reload(self) -> None:
        """Reload translations from source."""
        pass

class DatabaseTranslationSource(TranslationSource):
    """Database-backed translation source."""
    
    def __init__(self, database_url: str):
        self.engine = sa.create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        self._last_reload = 0
    
    def get_translation(self, key: str, language: str) -> Optional[str]:
        """Get single translation from database."""
        self._ensure_cache_fresh()
        return self._cache.get(language, {}).get(key)
    
    def get_all_translations(self, language: str) -> Dict[str, str]:
        """Get all translations for a language from database."""
        self._ensure_cache_fresh()
        return self._cache.get(language, {})
    
    def reload(self) -> None:
        """Reload translations from database."""
        with self.Session() as session:
            # Query translations table
            query = """
                SELECT language_code, translation_key, translation_value
                FROM translations
                WHERE active = true
            """
            
            results = session.execute(sa.text(query))
            
            # Rebuild cache
            new_cache = {}
            for row in results:
                language = row.language_code
                key = row.translation_key
                value = row.translation_value
                
                if language not in new_cache:
                    new_cache[language] = {}
                
                new_cache[language][key] = value
            
            self._cache = new_cache
            self._last_reload = time.time()
    
    def _ensure_cache_fresh(self):
        """Ensure cache is fresh, reload if needed."""
        if time.time() - self._last_reload > self._cache_ttl:
            self.reload()

# Integration with Translation Manager
class ExtendedTranslationManager(TranslationManager):
    def __init__(self, default_language: str = 'zh'):
        super().__init__(default_language)
        self.sources = []
    
    def add_source(self, source: TranslationSource, priority: int = 0):
        """Add a translation source with priority."""
        self.sources.append((priority, source))
        self.sources.sort(key=lambda x: x[0], reverse=True)  # Higher priority first
    
    def translate(self, key: str, language: Optional[str] = None, **kwargs) -> str:
        """Enhanced translate with multiple sources."""
        target_language = language or get_current_language()
        
        # Try each source in priority order
        for priority, source in self.sources:
            translation = source.get_translation(key, target_language)
            if translation:
                return self._format_translation(translation, **kwargs)
        
        # Fallback to built-in translations
        return super().translate(key, language, **kwargs)
```

### File-Based Translation Source

```python
# src/i18n/sources/file_source.py

import json
import yaml
import os
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileTranslationSource(TranslationSource):
    """File-based translation source with hot reload."""
    
    def __init__(self, translations_dir: str, format: str = 'json'):
        self.translations_dir = Path(translations_dir)
        self.format = format
        self._cache = {}
        self._observer = None
        
        # Load initial translations
        self.reload()
        
        # Set up file watching for hot reload
        self._setup_file_watcher()
    
    def get_translation(self, key: str, language: str) -> Optional[str]:
        return self._cache.get(language, {}).get(key)
    
    def get_all_translations(self, language: str) -> Dict[str, str]:
        return self._cache.get(language, {})
    
    def reload(self) -> None:
        """Reload translations from files."""
        new_cache = {}
        
        for file_path in self.translations_dir.glob(f'*.{self.format}'):
            language = file_path.stem
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    if self.format == 'json':
                        translations = json.load(f)
                    elif self.format == 'yaml':
                        translations = yaml.safe_load(f)
                    else:
                        raise ValueError(f"Unsupported format: {self.format}")
                
                new_cache[language] = translations
                
            except Exception as e:
                logger.error(f"Failed to load translations from {file_path}: {e}")
        
        self._cache = new_cache
        logger.info(f"Reloaded translations for languages: {list(new_cache.keys())}")
    
    def _setup_file_watcher(self):
        """Set up file system watcher for hot reload."""
        class TranslationFileHandler(FileSystemEventHandler):
            def __init__(self, source):
                self.source = source
            
            def on_modified(self, event):
                if not event.is_directory and event.src_path.endswith(f'.{self.source.format}'):
                    logger.info(f"Translation file changed: {event.src_path}")
                    self.source.reload()
        
        self._observer = Observer()
        self._observer.schedule(
            TranslationFileHandler(self),
            str(self.translations_dir),
            recursive=False
        )
        self._observer.start()
    
    def __del__(self):
        if self._observer:
            self._observer.stop()
            self._observer.join()
```

### External API Translation Source

```python
# src/i18n/sources/api_source.py

import httpx
import asyncio
from typing import Dict, Optional

class APITranslationSource(TranslationSource):
    """External API-based translation source."""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url
        self.api_key = api_key
        self._cache = {}
        self._cache_ttl = 3600  # 1 hour
        self._last_fetch = {}
    
    def get_translation(self, key: str, language: str) -> Optional[str]:
        """Get translation from external API."""
        # Check cache first
        cache_key = f"{language}:{key}"
        if self._is_cached_fresh(cache_key):
            return self._cache.get(cache_key)
        
        # Fetch from API
        translation = self._fetch_translation(key, language)
        if translation:
            self._cache[cache_key] = translation
            self._last_fetch[cache_key] = time.time()
        
        return translation
    
    def get_all_translations(self, language: str) -> Dict[str, str]:
        """Get all translations for a language from API."""
        # This would typically batch fetch all translations
        return self._fetch_all_translations(language)
    
    def _fetch_translation(self, key: str, language: str) -> Optional[str]:
        """Fetch single translation from API."""
        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{self.api_url}/translate",
                    params={
                        'key': key,
                        'language': language,
                        'api_key': self.api_key
                    },
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get('translation')
                
        except Exception as e:
            logger.error(f"Failed to fetch translation from API: {e}")
        
        return None
    
    def _fetch_all_translations(self, language: str) -> Dict[str, str]:
        """Fetch all translations for a language from API."""
        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{self.api_url}/translations/{language}",
                    params={'api_key': self.api_key},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json().get('translations', {})
                
        except Exception as e:
            logger.error(f"Failed to fetch all translations from API: {e}")
        
        return {}
    
    def _is_cached_fresh(self, cache_key: str) -> bool:
        """Check if cached translation is still fresh."""
        last_fetch = self._last_fetch.get(cache_key, 0)
        return time.time() - last_fetch < self._cache_ttl
```

## Custom Middleware Extensions

### Language Detection Middleware

```python
# src/i18n/middleware/custom_detection.py

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import geoip2.database
import user_agents

class AdvancedLanguageDetectionMiddleware(BaseHTTPMiddleware):
    """Advanced language detection with multiple strategies."""
    
    def __init__(self, app, geoip_db_path: str = None):
        super().__init__(app)
        self.geoip_reader = None
        if geoip_db_path:
            self.geoip_reader = geoip2.database.Reader(geoip_db_path)
    
    async def dispatch(self, request: Request, call_next):
        # Multiple detection strategies
        language = (
            self._detect_from_query(request) or
            self._detect_from_header(request) or
            self._detect_from_cookie(request) or
            self._detect_from_user_agent(request) or
            self._detect_from_geoip(request) or
            'zh'  # Default fallback
        )
        
        # Set language context
        set_language(language)
        
        # Process request
        response = await call_next(request)
        
        # Add response headers
        response.headers["Content-Language"] = language
        response.set_cookie("preferred_language", language, max_age=86400 * 30)  # 30 days
        
        return response
    
    def _detect_from_query(self, request: Request) -> Optional[str]:
        """Detect language from query parameter."""
        return request.query_params.get('language')
    
    def _detect_from_header(self, request: Request) -> Optional[str]:
        """Detect language from Accept-Language header."""
        accept_language = request.headers.get('accept-language', '')
        
        # Parse Accept-Language header
        languages = []
        for lang_range in accept_language.split(','):
            parts = lang_range.strip().split(';')
            lang = parts[0].strip()
            quality = 1.0
            
            if len(parts) > 1 and parts[1].startswith('q='):
                try:
                    quality = float(parts[1][2:])
                except ValueError:
                    quality = 1.0
            
            languages.append((lang, quality))
        
        # Sort by quality and find supported language
        languages.sort(key=lambda x: x[1], reverse=True)
        
        for lang, _ in languages:
            # Extract primary language code
            primary_lang = lang.split('-')[0].lower()
            if primary_lang in ['zh', 'en', 'ja', 'fr']:  # Your supported languages
                return primary_lang
        
        return None
    
    def _detect_from_cookie(self, request: Request) -> Optional[str]:
        """Detect language from cookie."""
        return request.cookies.get('preferred_language')
    
    def _detect_from_user_agent(self, request: Request) -> Optional[str]:
        """Detect language from User-Agent string."""
        user_agent_string = request.headers.get('user-agent', '')
        user_agent = user_agents.parse(user_agent_string)
        
        # Simple heuristics based on browser/OS
        if 'zh' in user_agent_string.lower():
            return 'zh'
        elif 'ja' in user_agent_string.lower():
            return 'ja'
        
        return None
    
    def _detect_from_geoip(self, request: Request) -> Optional[str]:
        """Detect language from IP geolocation."""
        if not self.geoip_reader:
            return None
        
        # Get client IP
        client_ip = request.client.host
        if client_ip in ['127.0.0.1', 'localhost']:
            return None
        
        try:
            response = self.geoip_reader.country(client_ip)
            country_code = response.country.iso_code
            
            # Map countries to languages
            country_language_map = {
                'CN': 'zh',  # China
                'TW': 'zh',  # Taiwan
                'HK': 'zh',  # Hong Kong
                'JP': 'ja',  # Japan
                'FR': 'fr',  # France
                'CA': 'fr',  # Canada (could be French)
                # Add more mappings as needed
            }
            
            return country_language_map.get(country_code)
            
        except Exception as e:
            logger.debug(f"GeoIP lookup failed: {e}")
            return None
```

### Caching Middleware

```python
# src/i18n/middleware/caching.py

import hashlib
import json
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class TranslationCachingMiddleware(BaseHTTPMiddleware):
    """Middleware for caching translated responses."""
    
    def __init__(self, app, cache_backend=None):
        super().__init__(app)
        self.cache = cache_backend or {}  # Simple dict cache
        self.cache_ttl = 300  # 5 minutes
    
    async def dispatch(self, request: Request, call_next):
        # Generate cache key based on URL, method, and language
        language = get_current_language()
        cache_key = self._generate_cache_key(request, language)
        
        # Check cache
        cached_response = self._get_cached_response(cache_key)
        if cached_response:
            return cached_response
        
        # Process request
        response = await call_next(request)
        
        # Cache response if appropriate
        if self._should_cache_response(request, response):
            self._cache_response(cache_key, response)
        
        return response
    
    def _generate_cache_key(self, request: Request, language: str) -> str:
        """Generate cache key for request."""
        key_data = {
            'method': request.method,
            'url': str(request.url),
            'language': language,
            'query_params': dict(request.query_params)
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _should_cache_response(self, request: Request, response: Response) -> bool:
        """Determine if response should be cached."""
        # Only cache GET requests with 200 status
        return (
            request.method == 'GET' and
            response.status_code == 200 and
            'application/json' in response.headers.get('content-type', '')
        )
```

## Custom Formatters and Validators

### Language-Specific Formatters

```python
# src/i18n/formatters.py

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any

class LanguageFormatter(ABC):
    """Abstract base class for language-specific formatting."""
    
    @abstractmethod
    def format_date(self, date: datetime) -> str:
        pass
    
    @abstractmethod
    def format_number(self, number: float) -> str:
        pass
    
    @abstractmethod
    def format_currency(self, amount: Decimal, currency: str) -> str:
        pass

class ChineseFormatter(LanguageFormatter):
    """Chinese language formatter."""
    
    def format_date(self, date: datetime) -> str:
        return date.strftime('%Y年%m月%d日')
    
    def format_number(self, number: float) -> str:
        # Chinese number formatting
        return f"{number:,.2f}".replace(',', '，')
    
    def format_currency(self, amount: Decimal, currency: str = 'CNY') -> str:
        if currency == 'CNY':
            return f"¥{self.format_number(float(amount))}"
        return f"{amount} {currency}"

class JapaneseFormatter(LanguageFormatter):
    """Japanese language formatter."""
    
    def format_date(self, date: datetime) -> str:
        return date.strftime('%Y年%m月%d日')
    
    def format_number(self, number: float) -> str:
        return f"{number:,.2f}"
    
    def format_currency(self, amount: Decimal, currency: str = 'JPY') -> str:
        if currency == 'JPY':
            return f"¥{int(amount):,}"  # JPY doesn't use decimals
        return f"{amount} {currency}"

class ArabicFormatter(LanguageFormatter):
    """Arabic language formatter with RTL support."""
    
    def format_date(self, date: datetime) -> str:
        # Arabic date formatting
        return date.strftime('%d/%m/%Y')
    
    def format_number(self, number: float) -> str:
        # Arabic-Indic numerals
        arabic_numerals = str.maketrans('0123456789', '٠١٢٣٤٥٦٧٨٩')
        return f"{number:,.2f}".translate(arabic_numerals)
    
    def format_currency(self, amount: Decimal, currency: str = 'SAR') -> str:
        formatted_amount = self.format_number(float(amount))
        return f"{formatted_amount} {currency}"

# Formatter registry
FORMATTERS = {
    'zh': ChineseFormatter(),
    'en': EnglishFormatter(),
    'ja': JapaneseFormatter(),
    'ar': ArabicFormatter(),
}

def get_formatter(language: str) -> LanguageFormatter:
    """Get formatter for language."""
    return FORMATTERS.get(language, FORMATTERS['en'])  # Default to English
```

### Custom Validators

```python
# src/i18n/validators.py

class TranslationValidator:
    """Custom validation for translations."""
    
    def __init__(self, language: str):
        self.language = language
        self.metadata = LANGUAGE_METADATA.get(language, {})
    
    def validate_translation_quality(self, key: str, translation: str) -> List[str]:
        """Validate translation quality and return issues."""
        issues = []
        
        # Check for empty translations
        if not translation.strip():
            issues.append("Translation is empty")
        
        # Check for untranslated content (still in English/Chinese)
        if self._contains_untranslated_content(translation):
            issues.append("Contains untranslated content")
        
        # Check for proper parameter placeholders
        if not self._validate_parameters(key, translation):
            issues.append("Parameter placeholders don't match")
        
        # Check text length for UI compatibility
        if not self._validate_ui_length(translation):
            issues.append("Translation may be too long for UI")
        
        # Language-specific validations
        issues.extend(self._validate_language_specific(translation))
        
        return issues
    
    def _contains_untranslated_content(self, translation: str) -> bool:
        """Check if translation contains untranslated content."""
        # Simple heuristic: check for common English/Chinese words
        english_indicators = ['the', 'and', 'or', 'in', 'on', 'at', 'to', 'for']
        chinese_indicators = ['的', '和', '或', '在', '到', '为']
        
        if self.language not in ['en', 'zh']:
            for indicator in english_indicators + chinese_indicators:
                if indicator in translation.lower():
                    return True
        
        return False
    
    def _validate_parameters(self, key: str, translation: str) -> bool:
        """Validate parameter placeholders in translation."""
        import re
        
        # Find all parameter placeholders
        params_in_translation = set(re.findall(r'\{(\w+)\}', translation))
        
        # Get expected parameters from base translation
        base_translation = TRANSLATIONS.get('zh', {}).get(key, '')
        expected_params = set(re.findall(r'\{(\w+)\}', base_translation))
        
        return params_in_translation == expected_params
    
    def _validate_ui_length(self, translation: str) -> bool:
        """Validate translation length for UI compatibility."""
        expansion_factor = self.metadata.get('text_expansion_factor', 1.0)
        effective_length = len(translation) * expansion_factor
        
        # Reasonable UI limits
        return effective_length <= 200  # Adjust based on your UI needs
    
    def _validate_language_specific(self, translation: str) -> List[str]:
        """Language-specific validation rules."""
        issues = []
        
        if self.language == 'ar':
            # Arabic-specific validations
            if not self._is_proper_rtl_text(translation):
                issues.append("Text may not display properly in RTL")
        
        elif self.language == 'ja':
            # Japanese-specific validations
            if not self._has_proper_japanese_characters(translation):
                issues.append("Should use appropriate Japanese characters")
        
        return issues
    
    def _is_proper_rtl_text(self, text: str) -> bool:
        """Check if text is proper RTL."""
        # Simple check for Arabic characters
        arabic_range = range(0x0600, 0x06FF)
        return any(ord(char) in arabic_range for char in text)
    
    def _has_proper_japanese_characters(self, text: str) -> bool:
        """Check if text uses appropriate Japanese characters."""
        # Check for Hiragana, Katakana, or Kanji
        hiragana_range = range(0x3040, 0x309F)
        katakana_range = range(0x30A0, 0x30FF)
        kanji_range = range(0x4E00, 0x9FAF)
        
        return any(
            ord(char) in hiragana_range or
            ord(char) in katakana_range or
            ord(char) in kanji_range
            for char in text
        )
```

## Plugin System

### Plugin Interface

```python
# src/i18n/plugins/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class I18nPlugin(ABC):
    """Base class for i18n plugins."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('enabled', True)
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the plugin."""
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get plugin name."""
        pass
    
    def pre_translate(self, key: str, language: str, **kwargs) -> Optional[str]:
        """Hook called before translation lookup."""
        return None
    
    def post_translate(self, key: str, language: str, translation: str, **kwargs) -> str:
        """Hook called after translation lookup."""
        return translation
    
    def on_language_change(self, old_language: str, new_language: str) -> None:
        """Hook called when language changes."""
        pass

class PluginManager:
    """Manager for i18n plugins."""
    
    def __init__(self):
        self.plugins = []
    
    def register_plugin(self, plugin: I18nPlugin) -> None:
        """Register a plugin."""
        if plugin.enabled:
            plugin.initialize()
            self.plugins.append(plugin)
    
    def pre_translate_hooks(self, key: str, language: str, **kwargs) -> Optional[str]:
        """Execute pre-translate hooks."""
        for plugin in self.plugins:
            result = plugin.pre_translate(key, language, **kwargs)
            if result is not None:
                return result
        return None
    
    def post_translate_hooks(self, key: str, language: str, translation: str, **kwargs) -> str:
        """Execute post-translate hooks."""
        for plugin in self.plugins:
            translation = plugin.post_translate(key, language, translation, **kwargs)
        return translation
    
    def language_change_hooks(self, old_language: str, new_language: str) -> None:
        """Execute language change hooks."""
        for plugin in self.plugins:
            plugin.on_language_change(old_language, new_language)
```

### Example Plugins

```python
# src/i18n/plugins/analytics.py

class AnalyticsPlugin(I18nPlugin):
    """Plugin for tracking translation usage analytics."""
    
    def get_name(self) -> str:
        return "analytics"
    
    def initialize(self) -> None:
        self.usage_stats = {}
        self.language_stats = {}
    
    def post_translate(self, key: str, language: str, translation: str, **kwargs) -> str:
        """Track translation usage."""
        # Update usage statistics
        self.usage_stats[key] = self.usage_stats.get(key, 0) + 1
        self.language_stats[language] = self.language_stats.get(language, 0) + 1
        
        # Send to analytics service (async)
        self._send_analytics_event(key, language)
        
        return translation
    
    def _send_analytics_event(self, key: str, language: str) -> None:
        """Send analytics event (implement based on your analytics service)."""
        pass

# src/i18n/plugins/fallback.py

class SmartFallbackPlugin(I18nPlugin):
    """Plugin for intelligent translation fallbacks."""
    
    def get_name(self) -> str:
        return "smart_fallback"
    
    def initialize(self) -> None:
        # Language similarity mapping
        self.language_similarity = {
            'zh-TW': 'zh',  # Traditional Chinese -> Simplified Chinese
            'zh-HK': 'zh',  # Hong Kong Chinese -> Simplified Chinese
            'en-GB': 'en',  # British English -> American English
            'en-AU': 'en',  # Australian English -> American English
        }
    
    def pre_translate(self, key: str, language: str, **kwargs) -> Optional[str]:
        """Provide smart fallback for similar languages."""
        # If exact language not found, try similar language
        if language in self.language_similarity:
            fallback_language = self.language_similarity[language]
            fallback_translation = TRANSLATIONS.get(fallback_language, {}).get(key)
            if fallback_translation:
                return fallback_translation
        
        return None
```

This extension guide provides comprehensive examples for customizing and extending the SuperInsight i18n system to meet specific requirements and use cases.