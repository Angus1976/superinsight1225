# SuperInsight i18n Troubleshooting Guide

## Overview

This guide provides solutions to common issues encountered when working with the SuperInsight i18n system. It covers debugging techniques, common problems, and their solutions.

## Common Issues and Solutions

### 1. Language Not Changing

**Symptoms:**
- API responses still in the old language after language change request
- Language setting appears to change but content remains the same
- Inconsistent language across different API endpoints

**Possible Causes and Solutions:**

#### A. Context Variable Not Set Properly

**Diagnosis:**
```python
# Add debug logging to check context
from src.i18n.manager import get_current_language

def debug_language_context():
    current_lang = get_current_language()
    print(f"Current language context: {current_lang}")
```

**Solution:**
```python
# Ensure middleware is properly configured
from src.i18n.middleware import I18nMiddleware

# In your FastAPI app setup
app.add_middleware(I18nMiddleware)

# Verify middleware order - i18n middleware should be added early
```

#### B. Caching Issues

**Diagnosis:**
```bash
# Check if responses are cached
curl -H "Cache-Control: no-cache" "http://localhost:8000/api/endpoint?language=en"
```

**Solution:**
```python
# Clear cache or disable caching temporarily
from src.i18n.manager import get_manager

manager = get_manager()
manager.clear_cache()  # If cache is implemented

# Or disable caching in configuration
I18N_CACHE_ENABLED=false
```

#### C. Multiple Language Parameters

**Diagnosis:**
```python
# Check for conflicting language settings
def debug_language_detection(request):
    query_lang = request.query_params.get('language')
    header_lang = request.headers.get('accept-language')
    cookie_lang = request.cookies.get('preferred_language')
    
    print(f"Query: {query_lang}, Header: {header_lang}, Cookie: {cookie_lang}")
```

**Solution:**
- Ensure consistent language parameter across all requests
- Check middleware priority order for language detection
- Clear browser cookies if they contain conflicting language settings

### 2. Missing Translations

**Symptoms:**
- Translation keys returned instead of translated text
- Some text appears in English/Chinese while other text is translated
- Error messages about missing translation keys

**Possible Causes and Solutions:**

#### A. Translation Key Not Found

**Diagnosis:**
```python
# Check if translation key exists
from src.i18n.translations import TRANSLATIONS

def check_translation_key(key, language):
    if language not in TRANSLATIONS:
        print(f"Language {language} not supported")
        return False
    
    if key not in TRANSLATIONS[language]:
        print(f"Key '{key}' not found in {language} translations")
        return False
    
    return True

# Usage
check_translation_key('login', 'en')
```

**Solution:**
```python
# Add missing translation keys
TRANSLATIONS['en']['missing_key'] = 'Missing Translation'
TRANSLATIONS['zh']['missing_key'] = '缺失翻译'

# Or use validation to find all missing keys
from src.i18n.validation import validate_translation_completeness
validate_translation_completeness()
```

#### B. Typo in Translation Key

**Diagnosis:**
```python
# Find similar keys to detect typos
import difflib

def find_similar_keys(target_key, language='zh'):
    available_keys = list(TRANSLATIONS[language].keys())
    similar = difflib.get_close_matches(target_key, available_keys, n=5, cutoff=0.6)
    return similar

# Usage
similar_keys = find_similar_keys('loginn')  # Typo in 'login'
print(f"Did you mean: {similar_keys}")
```

**Solution:**
- Fix the typo in your code
- Add the correct translation key if it's genuinely missing

#### C. Language Not Supported

**Diagnosis:**
```python
# Check supported languages
from src.i18n.manager import get_manager

manager = get_manager()
supported = manager.get_supported_languages()
print(f"Supported languages: {supported}")
```

**Solution:**
- Use a supported language code
- Add support for the new language (see Extension Guide)

### 3. Performance Issues

**Symptoms:**
- Slow API response times
- High memory usage
- Translation lookup timeouts

**Possible Causes and Solutions:**

#### A. Inefficient Translation Lookup

**Diagnosis:**
```python
import time
from src.i18n.manager import get_manager

def benchmark_translation_lookup():
    manager = get_manager()
    
    start_time = time.time()
    for i in range(1000):
        manager.translate('login', 'en')
    end_time = time.time()
    
    print(f"1000 lookups took {end_time - start_time:.4f} seconds")
    print(f"Average: {(end_time - start_time) * 1000:.4f}ms per lookup")

benchmark_translation_lookup()
```

**Solution:**
```python
# Enable caching if not already enabled
I18N_CACHE_ENABLED=true
I18N_CACHE_TTL=300

# Optimize translation dictionary structure
# Ensure O(1) dictionary lookups are being used
```

#### B. Memory Leaks

**Diagnosis:**
```python
import psutil
import os

def monitor_memory_usage():
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    print(f"RSS: {memory_info.rss / 1024 / 1024:.2f} MB")
    print(f"VMS: {memory_info.vms / 1024 / 1024:.2f} MB")

# Monitor before and after translation operations
monitor_memory_usage()
```

**Solution:**
```python
# Check for context variable leaks
from contextvars import copy_context

def clean_context_variables():
    # Ensure context variables are properly cleaned up
    # This should happen automatically, but can be forced if needed
    ctx = copy_context()
    # Context will be cleaned when it goes out of scope
```

#### C. Database Connection Issues (if using external sources)

**Diagnosis:**
```python
# Check database connection pool
def check_db_connections():
    from src.i18n.sources.database_source import DatabaseTranslationSource
    
    source = DatabaseTranslationSource("your_db_url")
    try:
        # Test connection
        source.get_translation('test', 'en')
        print("Database connection OK")
    except Exception as e:
        print(f"Database connection failed: {e}")
```

**Solution:**
- Increase database connection pool size
- Add connection retry logic
- Implement connection health checks

### 4. Thread Safety Issues

**Symptoms:**
- Inconsistent language settings in concurrent requests
- Race conditions in multi-threaded environments
- Context variable corruption

**Possible Causes and Solutions:**

#### A. Context Variable Corruption

**Diagnosis:**
```python
import threading
import time
from src.i18n.manager import set_language, get_current_language

def test_thread_safety():
    def worker(language, worker_id):
        set_language(language)
        time.sleep(0.1)  # Simulate work
        current = get_current_language()
        print(f"Worker {worker_id}: set {language}, got {current}")
        assert current == language, f"Context corruption in worker {worker_id}"
    
    threads = []
    for i in range(10):
        lang = 'en' if i % 2 == 0 else 'zh'
        thread = threading.Thread(target=worker, args=(lang, i))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()

test_thread_safety()
```

**Solution:**
```python
# Ensure proper context variable usage
from contextvars import ContextVar

# Context variables should be module-level
_current_language: ContextVar[str] = ContextVar('language', default='zh')

# Never share context variables between threads manually
# Let the framework handle context propagation
```

#### B. Shared Mutable State

**Diagnosis:**
```python
# Check for shared mutable objects
def check_shared_state():
    from src.i18n.translations import TRANSLATIONS
    
    # TRANSLATIONS should be immutable
    original_login = TRANSLATIONS['en']['login']
    
    # This should not affect other threads
    TRANSLATIONS['en']['login'] = 'Modified'
    
    # Check if change persists (it shouldn't in production)
    print(f"Original: {original_login}")
    print(f"Modified: {TRANSLATIONS['en']['login']}")
```

**Solution:**
```python
# Make translation dictionary immutable
from types import MappingProxyType

# Wrap in immutable proxy
TRANSLATIONS = MappingProxyType({
    'zh': MappingProxyType({...}),
    'en': MappingProxyType({...}),
})
```

### 5. API Integration Issues

**Symptoms:**
- API endpoints not returning translated content
- Missing Content-Language headers
- Inconsistent language detection

**Possible Causes and Solutions:**

#### A. Middleware Not Applied

**Diagnosis:**
```python
# Check middleware registration
from fastapi import FastAPI

app = FastAPI()

# List all middleware
for middleware in app.user_middleware:
    print(f"Middleware: {middleware}")

# Check if I18nMiddleware is present
```

**Solution:**
```python
# Ensure middleware is properly registered
from src.i18n.middleware import I18nMiddleware

app.add_middleware(I18nMiddleware)

# Middleware order matters - add i18n middleware early
```

#### B. Header Detection Issues

**Diagnosis:**
```bash
# Test header detection
curl -H "Accept-Language: en" "http://localhost:8000/api/test"
curl -H "Accept-Language: zh" "http://localhost:8000/api/test"

# Check response headers
curl -I "http://localhost:8000/api/test?language=en"
```

**Solution:**
```python
# Debug header processing in middleware
async def language_middleware(request: Request, call_next):
    # Add debug logging
    accept_lang = request.headers.get('accept-language')
    query_lang = request.query_params.get('language')
    
    logger.debug(f"Accept-Language: {accept_lang}")
    logger.debug(f"Query language: {query_lang}")
    
    # ... rest of middleware logic
```

#### C. Response Header Missing

**Diagnosis:**
```python
# Check if Content-Language header is added
def check_response_headers(response):
    content_lang = response.headers.get('Content-Language')
    if not content_lang:
        print("Warning: Content-Language header missing")
    else:
        print(f"Content-Language: {content_lang}")
```

**Solution:**
```python
# Ensure response headers are added in middleware
async def language_middleware(request: Request, call_next):
    # ... language detection logic
    
    response = await call_next(request)
    
    # Always add Content-Language header
    current_lang = get_current_language()
    response.headers["Content-Language"] = current_lang
    
    return response
```

### 6. Configuration Issues

**Symptoms:**
- Environment variables not being read
- Configuration changes not taking effect
- Default values being used instead of configured values

**Possible Causes and Solutions:**

#### A. Environment Variables Not Loaded

**Diagnosis:**
```python
import os

def check_env_vars():
    env_vars = [
        'I18N_DEFAULT_LANGUAGE',
        'I18N_SUPPORTED_LANGUAGES',
        'I18N_CACHE_ENABLED',
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        print(f"{var}: {value}")

check_env_vars()
```

**Solution:**
```bash
# Ensure environment variables are set
export I18N_DEFAULT_LANGUAGE=zh
export I18N_SUPPORTED_LANGUAGES=zh,en
export I18N_CACHE_ENABLED=true

# Or use .env file
echo "I18N_DEFAULT_LANGUAGE=zh" >> .env
echo "I18N_SUPPORTED_LANGUAGES=zh,en" >> .env
```

#### B. Configuration File Not Found

**Diagnosis:**
```python
import os
from pathlib import Path

def check_config_files():
    config_paths = [
        'config/i18n.yaml',
        '.env',
        'config/languages/zh.yaml',
        'config/languages/en.yaml',
    ]
    
    for path in config_paths:
        if Path(path).exists():
            print(f"✓ {path} exists")
        else:
            print(f"✗ {path} missing")

check_config_files()
```

**Solution:**
- Create missing configuration files
- Check file paths and permissions
- Verify configuration file format (YAML syntax, etc.)

## Debugging Techniques

### 1. Enable Debug Logging

```python
import logging

# Enable debug logging for i18n
logging.getLogger('src.i18n').setLevel(logging.DEBUG)

# Or set environment variable
I18N_LOG_LEVEL=DEBUG
```

### 2. Add Translation Debugging

```python
# Add debug wrapper around translation function
def debug_translate(original_translate):
    def wrapper(key, language=None, **kwargs):
        result = original_translate(key, language, **kwargs)
        print(f"translate('{key}', '{language}') -> '{result}'")
        return result
    return wrapper

# Apply wrapper
from src.i18n.manager import TranslationManager
TranslationManager.translate = debug_translate(TranslationManager.translate)
```

### 3. Context Variable Debugging

```python
from contextvars import copy_context

def debug_context():
    ctx = copy_context()
    print(f"Context variables: {list(ctx.items())}")
    
    from src.i18n.manager import get_current_language
    current_lang = get_current_language()
    print(f"Current language: {current_lang}")
```

### 4. Request Flow Debugging

```python
# Add debugging middleware
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class DebugMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print(f"Request: {request.method} {request.url}")
        print(f"Headers: {dict(request.headers)}")
        print(f"Query params: {dict(request.query_params)}")
        
        response = await call_next(request)
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        return response

# Add before i18n middleware
app.add_middleware(DebugMiddleware)
```

## Performance Monitoring

### 1. Translation Lookup Performance

```python
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        duration = (end_time - start_time) * 1000  # Convert to milliseconds
        if duration > 10:  # Log slow translations (>10ms)
            print(f"Slow translation: {func.__name__} took {duration:.2f}ms")
        
        return result
    return wrapper

# Apply to translation methods
from src.i18n.manager import TranslationManager
TranslationManager.translate = monitor_performance(TranslationManager.translate)
```

### 2. Memory Usage Monitoring

```python
import psutil
import gc

def monitor_memory():
    # Force garbage collection
    gc.collect()
    
    # Get memory usage
    process = psutil.Process()
    memory_info = process.memory_info()
    
    print(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
    print(f"Translation objects: {len(gc.get_objects())}")
```

### 3. Cache Performance

```python
class CacheMonitor:
    def __init__(self):
        self.hits = 0
        self.misses = 0
    
    def record_hit(self):
        self.hits += 1
    
    def record_miss(self):
        self.misses += 1
    
    def get_hit_rate(self):
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0
    
    def print_stats(self):
        print(f"Cache hits: {self.hits}")
        print(f"Cache misses: {self.misses}")
        print(f"Hit rate: {self.get_hit_rate():.2%}")

# Global cache monitor
cache_monitor = CacheMonitor()
```

## Health Checks

### 1. I18n System Health Check

```python
from fastapi import HTTPException

async def i18n_health_check():
    """Comprehensive i18n system health check."""
    health_status = {
        'status': 'healthy',
        'checks': {}
    }
    
    try:
        # Check translation manager
        from src.i18n.manager import get_manager
        manager = get_manager()
        
        # Test basic translation
        test_translation = manager.translate('login', 'en')
        health_status['checks']['translation_lookup'] = 'ok' if test_translation else 'failed'
        
        # Check supported languages
        supported_languages = manager.get_supported_languages()
        health_status['checks']['supported_languages'] = len(supported_languages)
        
        # Check context variables
        from src.i18n.manager import get_current_language
        current_lang = get_current_language()
        health_status['checks']['context_variables'] = 'ok' if current_lang else 'failed'
        
        # Check translation completeness
        from src.i18n.validation import validate_translation_completeness
        completeness_ok = validate_translation_completeness()
        health_status['checks']['translation_completeness'] = 'ok' if completeness_ok else 'warning'
        
    except Exception as e:
        health_status['status'] = 'unhealthy'
        health_status['error'] = str(e)
    
    return health_status

# Add as FastAPI endpoint
@app.get("/health/i18n")
async def health_check_endpoint():
    health = await i18n_health_check()
    if health['status'] != 'healthy':
        raise HTTPException(status_code=503, detail=health)
    return health
```

### 2. Automated Health Monitoring

```python
import asyncio
import logging

async def continuous_health_monitoring():
    """Continuous health monitoring for i18n system."""
    while True:
        try:
            health = await i18n_health_check()
            if health['status'] != 'healthy':
                logging.error(f"I18n health check failed: {health}")
                # Send alert to monitoring system
                await send_alert(health)
            else:
                logging.debug("I18n health check passed")
        
        except Exception as e:
            logging.error(f"Health check error: {e}")
        
        # Check every 60 seconds
        await asyncio.sleep(60)

# Start monitoring in background
asyncio.create_task(continuous_health_monitoring())
```

This troubleshooting guide provides comprehensive solutions for diagnosing and resolving common issues with the SuperInsight i18n system.