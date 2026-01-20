# SuperInsight i18n User Guide

## Overview

The SuperInsight platform provides comprehensive internationalization (i18n) support, allowing users to switch between Chinese and English languages dynamically. This guide covers how to use the i18n features from a user perspective.

## Supported Languages

The platform currently supports:
- **Chinese (zh)** - Default language
- **English (en)** - Secondary language

## Changing Language

### Method 1: Query Parameters

Add the `language` parameter to any URL:

```
https://your-domain.com/api/endpoint?language=en
https://your-domain.com/api/endpoint?language=zh
```

### Method 2: HTTP Headers

Include the `Accept-Language` header in your requests:

```http
Accept-Language: en
Accept-Language: zh
```

### Method 3: API Endpoints

Use the dedicated language management endpoints:

**Get Current Language:**
```http
GET /api/settings/language
```

**Change Language:**
```http
POST /api/settings/language
Content-Type: application/json

{
  "language": "en"
}
```

## Language Persistence

- Language settings persist for the duration of your session
- Each request can override the language using query parameters or headers
- Query parameters take priority over HTTP headers
- If no language is specified, Chinese is used as default

## API Response Format

All API responses include language information:

```json
{
  "data": {
    "message": "操作成功",
    "status": "success"
  },
  "meta": {
    "language": "zh"
  }
}
```

Response headers also include:
```http
Content-Language: zh
```

## Error Messages

Error messages are automatically translated based on your language preference:

**Chinese (default):**
```json
{
  "error": "无效的语言代码",
  "code": "INVALID_LANGUAGE"
}
```

**English:**
```json
{
  "error": "Invalid language code",
  "code": "INVALID_LANGUAGE"
}
```

## Common Use Cases

### Frontend Integration

For web applications, you can detect and set language preferences:

```javascript
// Detect browser language
const browserLang = navigator.language.startsWith('zh') ? 'zh' : 'en';

// Set language for API calls
fetch('/api/data?language=' + browserLang)
  .then(response => response.json())
  .then(data => console.log(data));
```

### Mobile Applications

Include language headers in your HTTP client:

```javascript
// React Native example
const response = await fetch('/api/data', {
  headers: {
    'Accept-Language': userPreferredLanguage,
    'Content-Type': 'application/json'
  }
});
```

### API Integration

For third-party integrations, use query parameters for simplicity:

```bash
# Get user data in English
curl "https://api.superinsight.com/users?language=en"

# Get system status in Chinese
curl "https://api.superinsight.com/status?language=zh"
```

## Troubleshooting

### Language Not Changing

1. **Check parameter format**: Ensure you're using `language=zh` or `language=en`
2. **Verify headers**: Use `Accept-Language: zh` or `Accept-Language: en`
3. **Clear cache**: Some responses may be cached with the previous language

### Unsupported Language

If you request an unsupported language:
- The system will fallback to Chinese (default)
- You'll receive a warning in the response headers
- The actual content will be in Chinese

### Mixed Language Content

If you see mixed languages:
- Check if you're using consistent language parameters across requests
- Verify that all API calls include the same language preference
- Some cached content may still show the previous language

## Best Practices

1. **Consistent Language Setting**: Use the same language parameter across all API calls in a session
2. **Fallback Handling**: Always handle the case where your preferred language might not be available
3. **User Preference Storage**: Store user language preferences locally and apply them to all requests
4. **Error Handling**: Implement proper error handling for language-related API failures

## Language Coverage

The platform provides translations for:
- Authentication and login flows
- System status and health messages
- Data processing and analysis results
- Error messages and validation feedback
- User interface elements and navigation
- Help text and tooltips

## Getting Help

If you encounter issues with language features:
1. Check the API documentation for endpoint-specific language support
2. Review the error messages for specific guidance
3. Contact support with details about your language preference and the issue encountered