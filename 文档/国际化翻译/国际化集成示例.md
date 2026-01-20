# SuperInsight i18n Integration Examples

## Overview

This document provides practical integration examples for implementing i18n support in various application types and frameworks.

## Frontend Integration Examples

### React Application

#### Basic Setup

```jsx
// i18n/i18nProvider.js
import React, { createContext, useContext, useState, useEffect } from 'react';

const I18nContext = createContext();

export const useI18n = () => {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within I18nProvider');
  }
  return context;
};

export const I18nProvider = ({ children }) => {
  const [language, setLanguage] = useState('zh');
  const [translations, setTranslations] = useState({});

  const changeLanguage = async (newLanguage) => {
    try {
      // Update language setting
      await fetch('/api/settings/language', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getApiKey()}`
        },
        body: JSON.stringify({ language: newLanguage })
      });

      // Fetch new translations
      const response = await fetch(`/api/i18n/translations?language=${newLanguage}`, {
        headers: {
          'Authorization': `Bearer ${getApiKey()}`
        }
      });
      const data = await response.json();
      
      setLanguage(newLanguage);
      setTranslations(data.translations);
      localStorage.setItem('preferred-language', newLanguage);
    } catch (error) {
      console.error('Failed to change language:', error);
    }
  };

  const t = (key, params = {}) => {
    let translation = translations[key] || key;
    
    // Handle parameterized translations
    Object.keys(params).forEach(param => {
      translation = translation.replace(`{${param}}`, params[param]);
    });
    
    return translation;
  };

  useEffect(() => {
    // Initialize language from localStorage or browser preference
    const savedLanguage = localStorage.getItem('preferred-language');
    const browserLanguage = navigator.language.startsWith('zh') ? 'zh' : 'en';
    const initialLanguage = savedLanguage || browserLanguage;
    
    changeLanguage(initialLanguage);
  }, []);

  return (
    <I18nContext.Provider value={{ language, changeLanguage, t }}>
      {children}
    </I18nContext.Provider>
  );
};
```

#### Component Usage

```jsx
// components/Dashboard.jsx
import React from 'react';
import { useI18n } from '../i18n/i18nProvider';

const Dashboard = () => {
  const { t, language, changeLanguage } = useI18n();

  return (
    <div className="dashboard">
      <header>
        <h1>{t('dashboard')}</h1>
        <div className="language-selector">
          <button 
            onClick={() => changeLanguage('zh')}
            className={language === 'zh' ? 'active' : ''}
          >
            中文
          </button>
          <button 
            onClick={() => changeLanguage('en')}
            className={language === 'en' ? 'active' : ''}
          >
            English
          </button>
        </div>
      </header>
      
      <main>
        <div className="welcome-message">
          {t('welcome_message', { name: 'SuperInsight' })}
        </div>
        
        <nav>
          <a href="/profile">{t('profile')}</a>
          <a href="/settings">{t('settings')}</a>
          <a href="/help">{t('help')}</a>
        </nav>
      </main>
    </div>
  );
};

export default Dashboard;
```

### Vue.js Application

#### Plugin Setup

```javascript
// plugins/i18n.js
import { ref, reactive } from 'vue';

const language = ref('zh');
const translations = reactive({});

const i18n = {
  install(app) {
    const changeLanguage = async (newLanguage) => {
      try {
        await fetch('/api/settings/language', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getApiKey()}`
          },
          body: JSON.stringify({ language: newLanguage })
        });

        const response = await fetch(`/api/i18n/translations?language=${newLanguage}`);
        const data = await response.json();
        
        language.value = newLanguage;
        Object.assign(translations, data.translations);
      } catch (error) {
        console.error('Failed to change language:', error);
      }
    };

    const t = (key, params = {}) => {
      let translation = translations[key] || key;
      Object.keys(params).forEach(param => {
        translation = translation.replace(`{${param}}`, params[param]);
      });
      return translation;
    };

    app.config.globalProperties.$t = t;
    app.config.globalProperties.$language = language;
    app.config.globalProperties.$changeLanguage = changeLanguage;
    
    app.provide('i18n', { t, language, changeLanguage });
  }
};

export default i18n;
```

#### Component Usage

```vue
<!-- components/UserProfile.vue -->
<template>
  <div class="user-profile">
    <h2>{{ $t('profile') }}</h2>
    
    <form @submit.prevent="saveProfile">
      <div class="form-group">
        <label>{{ $t('username') }}</label>
        <input v-model="profile.username" type="text" />
      </div>
      
      <div class="form-group">
        <label>{{ $t('email') }}</label>
        <input v-model="profile.email" type="email" />
      </div>
      
      <button type="submit">{{ $t('save') }}</button>
      <button type="button" @click="cancel">{{ $t('cancel') }}</button>
    </form>
  </div>
</template>

<script>
import { inject, ref } from 'vue';

export default {
  name: 'UserProfile',
  setup() {
    const { t } = inject('i18n');
    const profile = ref({
      username: '',
      email: ''
    });

    const saveProfile = async () => {
      try {
        const response = await fetch('/api/profile', {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Accept-Language': language.value
          },
          body: JSON.stringify(profile.value)
        });
        
        if (response.ok) {
          alert(t('profile_saved_successfully'));
        }
      } catch (error) {
        alert(t('save_failed'));
      }
    };

    return { profile, saveProfile, t };
  }
};
</script>
```

## Backend Integration Examples

### Express.js Middleware

```javascript
// middleware/i18n.js
const i18nMiddleware = (req, res, next) => {
  // Detect language from query parameter or header
  const queryLang = req.query.language;
  const headerLang = req.headers['accept-language'];
  
  // Priority: query > header > default
  let language = 'zh'; // default
  if (queryLang && ['zh', 'en'].includes(queryLang)) {
    language = queryLang;
  } else if (headerLang && headerLang.startsWith('en')) {
    language = 'en';
  }
  
  // Set language in request context
  req.language = language;
  
  // Add Content-Language header to response
  res.set('Content-Language', language);
  
  next();
};

module.exports = i18nMiddleware;
```

### FastAPI Integration

```python
# middleware/i18n_middleware.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class I18nMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Detect language
        language = self.detect_language(request)
        
        # Set language context (assuming you have a context manager)
        from src.i18n.manager import set_language
        set_language(language)
        
        # Process request
        response = await call_next(request)
        
        # Add Content-Language header
        response.headers["Content-Language"] = language
        
        return response
    
    def detect_language(self, request: Request) -> str:
        # Check query parameter first
        query_lang = request.query_params.get('language')
        if query_lang in ['zh', 'en']:
            return query_lang
        
        # Check Accept-Language header
        accept_lang = request.headers.get('accept-language', '')
        if accept_lang.startswith('en'):
            return 'en'
        
        # Default to Chinese
        return 'zh'
```

### Django Integration

```python
# middleware/i18n_middleware.py
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
import logging

logger = logging.getLogger(__name__)

class I18nMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Detect language
        language = self.detect_language(request)
        
        # Set language in request
        request.language = language
        
        # Activate language for Django's i18n
        from django.utils import translation
        translation.activate(language)
    
    def process_response(self, request, response):
        # Add Content-Language header
        if hasattr(request, 'language'):
            response['Content-Language'] = request.language
        
        return response
    
    def detect_language(self, request):
        # Check query parameter
        query_lang = request.GET.get('language')
        if query_lang in ['zh', 'en']:
            return query_lang
        
        # Check Accept-Language header
        accept_lang = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        if accept_lang.startswith('en'):
            return 'en'
        
        return 'zh'  # default
```

## Mobile Application Examples

### React Native

```javascript
// services/i18nService.js
import AsyncStorage from '@react-native-async-storage/async-storage';

class I18nService {
  constructor() {
    this.language = 'zh';
    this.translations = {};
    this.apiKey = null;
  }

  async initialize(apiKey) {
    this.apiKey = apiKey;
    
    // Load saved language preference
    const savedLanguage = await AsyncStorage.getItem('language');
    if (savedLanguage) {
      await this.setLanguage(savedLanguage);
    } else {
      // Detect device language
      const deviceLanguage = Platform.OS === 'ios' 
        ? NativeModules.SettingsManager.settings.AppleLocale
        : NativeModules.I18nManager.localeIdentifier;
      
      const language = deviceLanguage.startsWith('zh') ? 'zh' : 'en';
      await this.setLanguage(language);
    }
  }

  async setLanguage(language) {
    try {
      // Update server-side language setting
      await fetch('https://api.superinsight.com/api/settings/language', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`
        },
        body: JSON.stringify({ language })
      });

      // Fetch translations
      const response = await fetch(
        `https://api.superinsight.com/api/i18n/translations?language=${language}`,
        {
          headers: {
            'Authorization': `Bearer ${this.apiKey}`
          }
        }
      );
      
      const data = await response.json();
      this.language = language;
      this.translations = data.translations;
      
      // Save preference locally
      await AsyncStorage.setItem('language', language);
      
    } catch (error) {
      console.error('Failed to set language:', error);
    }
  }

  t(key, params = {}) {
    let translation = this.translations[key] || key;
    
    Object.keys(params).forEach(param => {
      translation = translation.replace(`{${param}}`, params[param]);
    });
    
    return translation;
  }

  getCurrentLanguage() {
    return this.language;
  }
}

export default new I18nService();
```

### Flutter/Dart

```dart
// services/i18n_service.dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class I18nService {
  static final I18nService _instance = I18nService._internal();
  factory I18nService() => _instance;
  I18nService._internal();

  String _language = 'zh';
  Map<String, String> _translations = {};
  String? _apiKey;

  String get language => _language;
  
  Future<void> initialize(String apiKey) async {
    _apiKey = apiKey;
    
    // Load saved language preference
    final prefs = await SharedPreferences.getInstance();
    final savedLanguage = prefs.getString('language');
    
    if (savedLanguage != null) {
      await setLanguage(savedLanguage);
    } else {
      // Use system locale
      final systemLocale = Platform.localeName;
      final language = systemLocale.startsWith('zh') ? 'zh' : 'en';
      await setLanguage(language);
    }
  }

  Future<void> setLanguage(String language) async {
    try {
      // Update server-side language setting
      final response = await http.post(
        Uri.parse('https://api.superinsight.com/api/settings/language'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_apiKey',
        },
        body: jsonEncode({'language': language}),
      );

      if (response.statusCode == 200) {
        // Fetch translations
        final translationsResponse = await http.get(
          Uri.parse('https://api.superinsight.com/api/i18n/translations?language=$language'),
          headers: {
            'Authorization': 'Bearer $_apiKey',
          },
        );

        if (translationsResponse.statusCode == 200) {
          final data = jsonDecode(translationsResponse.body);
          _language = language;
          _translations = Map<String, String>.from(data['translations']);
          
          // Save preference locally
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString('language', language);
        }
      }
    } catch (error) {
      print('Failed to set language: $error');
    }
  }

  String t(String key, [Map<String, String>? params]) {
    String translation = _translations[key] ?? key;
    
    if (params != null) {
      params.forEach((param, value) {
        translation = translation.replaceAll('{$param}', value);
      });
    }
    
    return translation;
  }
}
```

## API Client Examples

### Python SDK

```python
# superinsight_sdk/i18n.py
import requests
from typing import Dict, Optional, List

class I18nClient:
    def __init__(self, api_key: str, base_url: str = "https://api.superinsight.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        })
        self._current_language = 'zh'
    
    def set_language(self, language: str) -> Dict:
        """Set the current language preference."""
        response = self.session.post(
            f"{self.base_url}/api/settings/language",
            json={'language': language}
        )
        response.raise_for_status()
        self._current_language = language
        return response.json()
    
    def get_language_settings(self) -> Dict:
        """Get current language settings."""
        response = self.session.get(f"{self.base_url}/api/settings/language")
        response.raise_for_status()
        return response.json()
    
    def get_translations(self, language: Optional[str] = None) -> Dict:
        """Get all translations for a language."""
        lang = language or self._current_language
        response = self.session.get(
            f"{self.base_url}/api/i18n/translations",
            params={'language': lang}
        )
        response.raise_for_status()
        return response.json()
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        response = self.session.get(f"{self.base_url}/api/i18n/languages")
        response.raise_for_status()
        return response.json()['supported_languages']
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an API request with current language preference."""
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['Accept-Language'] = self._current_language
        
        url = f"{self.base_url}{endpoint}"
        return self.session.request(method, url, **kwargs)

# Usage example
client = I18nClient('your-api-key')

# Set language to English
client.set_language('en')

# Get user data with English responses
response = client.make_request('GET', '/api/users')
data = response.json()
```

### JavaScript SDK

```javascript
// superinsight-sdk/i18n.js
class SuperInsightI18n {
  constructor(apiKey, baseUrl = 'https://api.superinsight.com') {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
    this.currentLanguage = 'zh';
  }

  async setLanguage(language) {
    const response = await fetch(`${this.baseUrl}/api/settings/language`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ language })
    });

    if (!response.ok) {
      throw new Error(`Failed to set language: ${response.statusText}`);
    }

    this.currentLanguage = language;
    return response.json();
  }

  async getLanguageSettings() {
    const response = await fetch(`${this.baseUrl}/api/settings/language`, {
      headers: {
        'Authorization': `Bearer ${this.apiKey}`
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to get language settings: ${response.statusText}`);
    }

    return response.json();
  }

  async getTranslations(language = null) {
    const lang = language || this.currentLanguage;
    const response = await fetch(`${this.baseUrl}/api/i18n/translations?language=${lang}`, {
      headers: {
        'Authorization': `Bearer ${this.apiKey}`
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to get translations: ${response.statusText}`);
    }

    return response.json();
  }

  async request(method, endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Authorization': `Bearer ${this.apiKey}`,
      'Accept-Language': this.currentLanguage,
      ...options.headers
    };

    return fetch(url, {
      method,
      headers,
      ...options
    });
  }
}

// Usage
const i18n = new SuperInsightI18n('your-api-key');

// Set language and make requests
await i18n.setLanguage('en');
const response = await i18n.request('GET', '/api/dashboard');
```

## Testing Integration

### Frontend Testing

```javascript
// tests/i18n.test.js
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { I18nProvider, useI18n } from '../src/i18n/i18nProvider';

// Mock fetch
global.fetch = jest.fn();

const TestComponent = () => {
  const { t, changeLanguage, language } = useI18n();
  
  return (
    <div>
      <span data-testid="language">{language}</span>
      <span data-testid="greeting">{t('greeting')}</span>
      <button onClick={() => changeLanguage('en')}>English</button>
      <button onClick={() => changeLanguage('zh')}>中文</button>
    </div>
  );
};

describe('I18n Integration', () => {
  beforeEach(() => {
    fetch.mockClear();
  });

  test('changes language and updates translations', async () => {
    // Mock API responses
    fetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ message: 'Language updated' })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          language: 'en',
          translations: { greeting: 'Hello' }
        })
      });

    render(
      <I18nProvider>
        <TestComponent />
      </I18nProvider>
    );

    // Click English button
    fireEvent.click(screen.getByText('English'));

    // Wait for language change
    await waitFor(() => {
      expect(screen.getByTestId('language')).toHaveTextContent('en');
      expect(screen.getByTestId('greeting')).toHaveTextContent('Hello');
    });

    // Verify API calls
    expect(fetch).toHaveBeenCalledWith('/api/settings/language', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer undefined'
      },
      body: JSON.stringify({ language: 'en' })
    });
  });
});
```

## Performance Optimization

### Caching Strategy

```javascript
// utils/i18nCache.js
class I18nCache {
  constructor(maxAge = 5 * 60 * 1000) { // 5 minutes default
    this.cache = new Map();
    this.maxAge = maxAge;
  }

  set(key, value) {
    this.cache.set(key, {
      value,
      timestamp: Date.now()
    });
  }

  get(key) {
    const item = this.cache.get(key);
    if (!item) return null;

    if (Date.now() - item.timestamp > this.maxAge) {
      this.cache.delete(key);
      return null;
    }

    return item.value;
  }

  clear() {
    this.cache.clear();
  }
}

const translationCache = new I18nCache();

// Enhanced translation fetching with cache
async function fetchTranslations(language) {
  const cacheKey = `translations_${language}`;
  const cached = translationCache.get(cacheKey);
  
  if (cached) {
    return cached;
  }

  const response = await fetch(`/api/i18n/translations?language=${language}`);
  const data = await response.json();
  
  translationCache.set(cacheKey, data);
  return data;
}
```

This comprehensive integration guide provides practical examples for implementing i18n support across different platforms and frameworks, ensuring consistent multilingual experiences for users.