# Design Document

## Overview

The i18n (internationalization) system for SuperInsight platform provides comprehensive multi-language support with dynamic language switching capabilities. The system is designed to support Chinese and English languages with Chinese as the default, providing seamless translation services across all API endpoints and user interfaces.

The architecture follows a modular approach with clear separation of concerns: translation storage, language management, API integration, and middleware processing. The system is built for high performance, thread safety, and easy extensibility.

## Architecture

The i18n system consists of four main architectural layers:

### 1. Translation Storage Layer
- **Translation Dictionary**: Centralized storage for all translation key-value pairs
- **Language Registry**: Maintains list of supported languages and their metadata
- **Fallback Mechanism**: Handles missing translations and unsupported languages

### 2. Translation Management Layer
- **Translation Manager**: High-level interface for translation operations
- **Language Context**: Per-request language state management using context variables
- **Validation Engine**: Ensures translation completeness and consistency

### 3. API Integration Layer
- **Language Middleware**: Automatic language detection and context setting
- **API Endpoints**: RESTful endpoints for language management
- **Response Translation**: Automatic translation of API responses

### 4. Client Interface Layer
- **Python API**: Direct programmatic access to translation functions
- **HTTP API**: RESTful interface for external clients
- **Configuration Interface**: System configuration and management

```mermaid
graph TB
    A[Client Request] --> B[Language Middleware]
    B --> C[Language Detection]
    C --> D[Context Setting]
    D --> E[API Endpoint]
    E --> F[Translation Manager]
    F --> G[Translation Dictionary]
    G --> H[Translated Response]
    H --> I[Response Headers]
    I --> J[Client Response]
    
    K[Translation Storage] --> G
    L[Language Registry] --> F
    M[Fallback Mechanism] --> F
```

## Components and Interfaces

### Translation Manager (`TranslationManager`)

The core component responsible for translation operations and language management.

**Interface:**
```python
class TranslationManager:
    def __init__(self, default_language: str = 'zh')
    def set_language(self, language: str) -> None
    def get_language(self) -> str
    def translate(self, key: str, language: Optional[str] = None, **kwargs) -> str
    def t(self, key: str, language: Optional[str] = None, **kwargs) -> str  # shorthand
    def get_all(self, language: Optional[str] = None) -> Dict[str, str]
    def get_supported_languages(self) -> List[str]
    def translate_dict(self, data: Dict, language: Optional[str] = None) -> Dict
    def translate_list(self, items: List[str], language: Optional[str] = None) -> List[str]
```

### Translation Functions

Core functions for translation operations.

**Interface:**
```python
def set_language(language: str) -> None
def get_current_language() -> str
def get_translation(key: str, language: Optional[str] = None, **kwargs) -> str
def get_all_translations(language: Optional[str] = None) -> Dict[str, str]
def get_supported_languages() -> List[str]
```

### Language Middleware

FastAPI middleware for automatic language processing.

**Interface:**
```python
@app.middleware("http")
async def language_middleware(request: Request, call_next: Callable) -> Response
```

**Processing Flow:**
1. Extract language from query parameters (`?language=en`)
2. Extract language from Accept-Language header
3. Validate language code against supported languages
4. Set language context for current request
5. Process request with language context
6. Add Content-Language header to response

### API Endpoints

RESTful endpoints for language management.

**Endpoints:**
- `GET /api/settings/language` - Get current language settings
- `POST /api/settings/language` - Set current language
- `GET /api/i18n/translations` - Get all translations for a language
- `GET /api/i18n/translations?language={code}` - Get translations for specific language

## Data Models

### Translation Dictionary Structure

```python
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'zh': {
        'app_name': 'SuperInsight 平台',
        'login': '登录',
        'logout': '登出',
        # ... 90+ translation keys
    },
    'en': {
        'app_name': 'SuperInsight Platform',
        'login': 'Login',
        'logout': 'Logout',
        # ... 90+ translation keys
    }
}
```

### Language Context Model

```python
# Context variable for per-request language state
_current_language: ContextVar[str] = ContextVar('language', default='zh')
```

### API Response Models

```python
class LanguageSettingsResponse(BaseModel):
    current_language: str
    supported_languages: List[str]
    language_names: Dict[str, str]

class LanguageChangeResponse(BaseModel):
    message: str
    current_language: str

class TranslationsResponse(BaseModel):
    language: str
    translations: Dict[str, str]
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Based on the prework analysis, the following properties have been identified for testing:

### Property 1: Language Support Consistency
*For any* supported language code, the translation system should return translations and include the language in the supported languages list.
**Validates: Requirements 1.1**

### Property 2: Translation Dictionary Completeness
*For any* translation key that exists in one supported language, the same key should exist in all other supported languages.
**Validates: Requirements 1.4, 1.5**

### Property 3: Language Switching Immediacy
*For any* valid language code, when the language is changed, all subsequent translation requests should use the new language immediately.
**Validates: Requirements 2.1**

### Property 4: Invalid Language Validation
*For any* invalid language code, the system should reject the language change request and maintain the current language setting.
**Validates: Requirements 2.2, 2.3**

### Property 5: Multi-method Language Setting
*For any* valid language code, the system should accept language changes through query parameters, headers, and direct API calls with consistent results.
**Validates: Requirements 2.4**

### Property 6: Language Persistence
*For any* language change, all subsequent API responses should use the new language until changed again.
**Validates: Requirements 2.5**

### Property 7: Automatic Language Detection
*For any* request containing language preferences in query parameters or headers, the system should detect and apply the preferred language.
**Validates: Requirements 3.1**

### Property 8: Response Translation Consistency
*For any* API response containing translatable text, the response should be translated according to the current language setting.
**Validates: Requirements 3.2**

### Property 9: Content-Language Header Inclusion
*For any* API response, the response should include a Content-Language header matching the current language.
**Validates: Requirements 3.3, 9.3**

### Property 10: Default Language Fallback
*For any* request without explicit language specification, the system should use Chinese as the default language.
**Validates: Requirements 3.5**

### Property 11: Translation Query Functionality
*For any* valid translation key and language combination, the translation manager should return the appropriate translation.
**Validates: Requirements 4.1**

### Property 12: Batch Translation Consistency
*For any* list of translation keys, batch translation should return the same results as individual translations for each key.
**Validates: Requirements 4.2**

### Property 13: Complete Translation Retrieval
*For any* supported language, requesting all translations should return a complete dictionary of all available translation keys.
**Validates: Requirements 4.4**

### Property 14: Missing Key Fallback
*For any* non-existent translation key, the system should return the key itself as fallback text.
**Validates: Requirements 4.5, 5.1**

### Property 15: Unsupported Language Fallback
*For any* unsupported language code, the system should fallback to Chinese for translations.
**Validates: Requirements 5.2**

### Property 16: Translation Completeness Validation
*For any* supported language, the system should be able to detect if any translation keys are missing compared to other languages.
**Validates: Requirements 7.4**

### Property 17: HTTP Status Code Appropriateness
*For any* language management API request, the system should return appropriate HTTP status codes (200 for success, 400 for bad requests, etc.).
**Validates: Requirements 8.5**

### Property 18: Middleware Language Detection
*For any* request with language indicators, the middleware should correctly detect and set the language context.
**Validates: Requirements 9.1, 9.2**

### Property 19: Detection Method Priority
*For any* request containing both query parameters and headers with different languages, query parameters should take precedence.
**Validates: Requirements 9.5**

### Property 20: Translation Coverage Completeness
*For any* major functional category (authentication, system status, etc.), translations should exist for all relevant text.
**Validates: Requirements 10.1, 10.2**

### Property 21: Translation Consistency Across Modules
*For any* common concept used across different modules, the same translation should be used consistently.
**Validates: Requirements 10.3**

### Property 22: Parameterized Translation Support
*For any* translation with formatting parameters, the system should correctly substitute the parameters in the translated text.
**Validates: Requirements 11.3**

### Property 23: Text Metadata Provision
*For any* translation, the system should be able to provide metadata about text characteristics when requested.
**Validates: Requirements 11.5**

## Error Handling

### Translation Errors
- **Missing Translation Keys**: Return the key itself as fallback text
- **Invalid Language Codes**: Fallback to Chinese and log warning
- **Malformed Translation Requests**: Return appropriate HTTP error codes

### API Errors
- **Invalid Language in Request**: HTTP 400 with descriptive error message
- **Missing Required Parameters**: HTTP 400 with parameter validation errors
- **Internal Translation Errors**: HTTP 500 with generic error message (detailed errors logged)

### Middleware Errors
- **Language Detection Failures**: Fallback to Chinese silently
- **Context Setting Errors**: Continue with default language
- **Response Header Errors**: Continue without Content-Language header

## Testing Strategy

The testing strategy employs a dual approach combining unit tests for specific scenarios and property-based tests for comprehensive validation.

### Unit Testing
Unit tests focus on:
- **Specific Examples**: Test known translation key-value pairs
- **Edge Cases**: Empty strings, special characters, boundary conditions
- **Error Conditions**: Invalid inputs, missing resources, network failures
- **Integration Points**: API endpoints, middleware integration, database connections

### Property-Based Testing
Property-based tests validate universal properties using the fast-check library for JavaScript/TypeScript or Hypothesis for Python:

- **Minimum 100 iterations** per property test to ensure comprehensive coverage
- **Random input generation** for translation keys, language codes, and API parameters
- **Property validation** across all generated inputs
- **Shrinking** to find minimal failing examples when properties fail

Each property test is tagged with the format: **Feature: i18n-support, Property {number}: {property_text}**

### Test Configuration
- **Framework**: pytest for Python unit tests, fast-check/Hypothesis for property tests
- **Coverage Target**: 95% code coverage minimum
- **Performance Tests**: Translation lookup performance validation
- **Load Tests**: Concurrent access and thread safety validation
- **Integration Tests**: End-to-end API workflow testing

### Test Data Management
- **Translation Fixtures**: Predefined translation sets for consistent testing
- **Language Code Generators**: Valid and invalid language code generation
- **API Request Generators**: Comprehensive API request scenario generation
- **Mock Services**: External service mocking for isolated testing