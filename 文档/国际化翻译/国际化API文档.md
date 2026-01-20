# SuperInsight i18n API Documentation

## Overview

This document provides comprehensive API documentation for the SuperInsight internationalization (i18n) system. All endpoints support dynamic language switching and return localized content.

## Base URL

```
https://api.superinsight.com
```

## Authentication

All i18n endpoints follow the same authentication requirements as other platform APIs. Include your API key in the Authorization header:

```http
Authorization: Bearer YOUR_API_KEY
```

## Language Management Endpoints

### Get Current Language Settings

Retrieve the current language configuration and supported languages.

**Endpoint:** `GET /api/settings/language`

**Parameters:** None

**Response:**
```json
{
  "current_language": "zh",
  "supported_languages": ["zh", "en"],
  "language_names": {
    "zh": "中文",
    "en": "English"
  }
}
```

**Status Codes:**
- `200 OK` - Success
- `401 Unauthorized` - Invalid authentication
- `500 Internal Server Error` - Server error

**Example:**
```bash
curl -X GET "https://api.superinsight.com/api/settings/language" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Change Language Settings

Update the current language preference for the session.

**Endpoint:** `POST /api/settings/language`

**Content-Type:** `application/json`

**Request Body:**
```json
{
  "language": "en"
}
```

**Parameters:**
- `language` (string, required): Language code ("zh" or "en")

**Response:**
```json
{
  "message": "Language updated successfully",
  "current_language": "en"
}
```

**Status Codes:**
- `200 OK` - Language updated successfully
- `400 Bad Request` - Invalid language code or malformed request
- `401 Unauthorized` - Invalid authentication
- `500 Internal Server Error` - Server error

**Example:**
```bash
curl -X POST "https://api.superinsight.com/api/settings/language" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"language": "en"}'
```

## Translation Endpoints

### Get All Translations

Retrieve all available translations for a specific language.

**Endpoint:** `GET /api/i18n/translations`

**Parameters:**
- `language` (string, optional): Language code ("zh" or "en"). Defaults to current language.

**Response:**
```json
{
  "language": "zh",
  "translations": {
    "app_name": "SuperInsight 平台",
    "login": "登录",
    "logout": "登出",
    "dashboard": "仪表板",
    "settings": "设置",
    "profile": "个人资料",
    "help": "帮助",
    "search": "搜索",
    "save": "保存",
    "cancel": "取消",
    "delete": "删除",
    "edit": "编辑",
    "create": "创建",
    "update": "更新",
    "success": "成功",
    "error": "错误",
    "warning": "警告",
    "info": "信息"
  }
}
```

**Status Codes:**
- `200 OK` - Success
- `400 Bad Request` - Invalid language parameter
- `401 Unauthorized` - Invalid authentication
- `500 Internal Server Error` - Server error

**Example:**
```bash
# Get Chinese translations
curl -X GET "https://api.superinsight.com/api/i18n/translations?language=zh" \
  -H "Authorization: Bearer YOUR_API_KEY"

# Get English translations
curl -X GET "https://api.superinsight.com/api/i18n/translations?language=en" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Get Supported Languages

Retrieve the list of all supported languages.

**Endpoint:** `GET /api/i18n/languages`

**Parameters:** None

**Response:**
```json
{
  "supported_languages": ["zh", "en"],
  "default_language": "zh",
  "language_names": {
    "zh": "中文",
    "en": "English"
  }
}
```

**Status Codes:**
- `200 OK` - Success
- `401 Unauthorized` - Invalid authentication
- `500 Internal Server Error` - Server error

**Example:**
```bash
curl -X GET "https://api.superinsight.com/api/i18n/languages" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Language Detection

### Query Parameters

Add the `language` parameter to any API endpoint:

```
GET /api/users?language=en
POST /api/data?language=zh
```

### HTTP Headers

Include the `Accept-Language` header:

```http
Accept-Language: en
Accept-Language: zh
```

### Priority Order

Language detection follows this priority:
1. Query parameter (`?language=en`)
2. Accept-Language header
3. Session language setting
4. Default language (Chinese)

## Response Headers

All API responses include language information:

```http
Content-Language: zh
Content-Type: application/json; charset=utf-8
```

## Error Responses

Error responses are localized based on the current language:

**Chinese:**
```json
{
  "error": {
    "message": "无效的语言代码",
    "code": "INVALID_LANGUAGE",
    "details": "支持的语言: zh, en"
  }
}
```

**English:**
```json
{
  "error": {
    "message": "Invalid language code",
    "code": "INVALID_LANGUAGE", 
    "details": "Supported languages: zh, en"
  }
}
```

## Common Error Codes

| Code | Chinese Message | English Message | HTTP Status |
|------|----------------|-----------------|-------------|
| `INVALID_LANGUAGE` | 无效的语言代码 | Invalid language code | 400 |
| `MISSING_TRANSLATION` | 翻译缺失 | Missing translation | 500 |
| `LANGUAGE_NOT_SUPPORTED` | 不支持的语言 | Language not supported | 400 |
| `TRANSLATION_ERROR` | 翻译错误 | Translation error | 500 |

## Rate Limiting

Language management endpoints are subject to rate limiting:
- 100 requests per minute per API key
- 1000 requests per hour per API key

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## SDK Examples

### JavaScript/Node.js

```javascript
const SuperInsightAPI = require('superinsight-api');

const client = new SuperInsightAPI({
  apiKey: 'YOUR_API_KEY',
  language: 'en' // Optional default language
});

// Get current language settings
const settings = await client.language.getSettings();

// Change language
await client.language.setLanguage('zh');

// Get all translations
const translations = await client.i18n.getTranslations('en');
```

### Python

```python
from superinsight import SuperInsightClient

client = SuperInsightClient(
    api_key='YOUR_API_KEY',
    language='zh'  # Optional default language
)

# Get current language settings
settings = client.language.get_settings()

# Change language
client.language.set_language('en')

# Get all translations
translations = client.i18n.get_translations('zh')
```

### cURL Examples

```bash
# Set language to English
curl -X POST "https://api.superinsight.com/api/settings/language" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"language": "en"}'

# Get data with Chinese language
curl -X GET "https://api.superinsight.com/api/data?language=zh" \
  -H "Authorization: Bearer YOUR_API_KEY"

# Get translations for English
curl -X GET "https://api.superinsight.com/api/i18n/translations?language=en" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Best Practices

1. **Cache Translations**: Cache translation responses to reduce API calls
2. **Handle Fallbacks**: Always handle cases where translations might be missing
3. **Consistent Language**: Use the same language across related API calls
4. **Error Handling**: Implement proper error handling for language-related failures
5. **Performance**: Use batch operations when possible to reduce API calls

## Changelog

### Version 1.0.0
- Initial release with Chinese and English support
- Basic language management endpoints
- Translation retrieval endpoints
- Automatic language detection middleware