# Label Studio 中文支持优化方案

**日期**: 2026-01-26  
**目标**: 实现完全友好的中文支持，同时不影响开源版本的快速升级迭代  
**状态**: ✅ 优化方案

---

## 核心原则

### 1. 不修改 Label Studio 源码 ✅
- 保持与官方版本完全兼容
- 可以随时升级到最新版本
- 不影响开源版本的快速迭代

### 2. 分层优化策略 🎯
- **Layer 1**: 使用官方 Django i18n（后端）
- **Layer 2**: 使用官方 React i18next（前端）
- **Layer 3**: 自定义翻译覆盖（可选）
- **Layer 4**: SuperInsight 集成层优化

---

## 技术架构

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    SuperInsight 平台                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  前端 (React)                                         │  │
│  │  - i18n 语言选择器                                    │  │
│  │  - 语言状态管理 (languageStore)                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  集成层 (LabelStudioEmbed)                           │  │
│  │  - URL 参数注入: ?lang=zh                            │  │
│  │  - 语言同步监听                                       │  │
│  │  - iframe 重载控制                                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                  Label Studio (官方版本)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  后端 (Django)                                        │  │
│  │  - Django i18n 中间件                                 │  │
│  │  - 环境变量: LANGUAGE_CODE=zh-hans                   │  │
│  │  - URL 参数解析: ?lang=zh                            │  │
│  │  - Session 语言存储                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ↓                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  前端 (React + i18next)                               │  │
│  │  - 官方 i18next 配置                                  │  │
│  │  - 中文翻译文件 (内置)                                │  │
│  │  - 动态语言切换                                       │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 实施方案

### Layer 1: Django 后端配置（官方支持）

#### 1.1 环境变量配置

```yaml
# docker-compose.yml
label-studio:
  image: heartexlabs/label-studio:latest
  container_name: superinsight-label-studio
  ports:
    - "8080:8080"
  environment:
    # 基础配置
    - LABEL_STUDIO_USERNAME=admin
    - LABEL_STUDIO_PASSWORD=admin
    
    # 国际化配置
    - LANGUAGE_CODE=zh-hans              # Django 默认语言
    - LABEL_STUDIO_DEFAULT_LANGUAGE=zh   # Label Studio 特定配置
    - DJANGO_SETTINGS_MODULE=label_studio.core.settings.label_studio
    
    # 可选：启用所有支持的语言
    - LABEL_STUDIO_LANGUAGES=zh-hans,en
    
  volumes:
    - label_studio_data:/label-studio/data
```

**说明**:
- `LANGUAGE_CODE=zh-hans`: Django 标准配置，设置默认语言为简体中文
- `LABEL_STUDIO_DEFAULT_LANGUAGE=zh`: Label Studio 特定配置
- 不需要修改任何源码，纯配置方式

#### 1.2 Django i18n 工作原理

```python
# Label Studio 内部实现（无需修改）
# label_studio/core/settings/base.py

LANGUAGE_CODE = os.getenv('LANGUAGE_CODE', 'en')

LANGUAGES = [
    ('en', 'English'),
    ('zh-hans', '简体中文'),
    # 其他语言...
]

MIDDLEWARE = [
    'django.middleware.locale.LocaleMiddleware',  # 语言中间件
    # 其他中间件...
]

# 语言切换逻辑
# 1. URL 参数: ?lang=zh
# 2. Session: django_language cookie
# 3. Accept-Language header
# 4. 默认: LANGUAGE_CODE
```

**优势**:
- ✅ 官方标准实现，稳定可靠
- ✅ 支持多种语言切换方式
- ✅ 自动处理语言回退
- ✅ 不需要修改源码

---

### Layer 2: React 前端配置（官方支持）

#### 2.1 Label Studio Frontend i18next 配置

Label Studio 前端使用 **i18next** 进行国际化，已经内置中文翻译。

```javascript
// Label Studio Frontend 内部实现（无需修改）
// label-studio-frontend/src/i18n.js

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// 翻译资源（内置）
import zhTranslation from './locales/zh/translation.json';
import enTranslation from './locales/en/translation.json';

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: enTranslation },
      'zh-hans': { translation: zhTranslation },
      'zh': { translation: zhTranslation },  // 简化映射
    },
    lng: 'en',  // 默认语言（会被 URL 参数覆盖）
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
```

**说明**:
- Label Studio 前端已经集成 i18next
- 中文翻译文件已经内置（基于 PR #2421）
- 支持通过 URL 参数动态切换语言

#### 2.2 URL 参数语言切换

```javascript
// Label Studio Frontend 内部实现（无需修改）
// 自动检测 URL 参数 ?lang=zh

const urlParams = new URLSearchParams(window.location.search);
const langParam = urlParams.get('lang');

if (langParam) {
  i18n.changeLanguage(langParam);
}
```

**优势**:
- ✅ 官方已实现，无需修改
- ✅ 支持动态语言切换
- ✅ 与 Django 后端协同工作

---

### Layer 3: 自定义翻译覆盖（可选，不修改源码）

如果官方翻译质量不满意，可以通过 **外部配置** 覆盖翻译，而不修改源码。

#### 3.1 Django 翻译覆盖

```yaml
# docker-compose.yml
label-studio:
  volumes:
    # 挂载自定义翻译文件
    - ./custom-translations/locale:/label-studio/locale:ro
```

```bash
# 创建自定义翻译目录
mkdir -p custom-translations/locale/zh_Hans/LC_MESSAGES

# 复制官方翻译文件
docker cp superinsight-label-studio:/label-studio/locale/zh_Hans/LC_MESSAGES/django.po \
  custom-translations/locale/zh_Hans/LC_MESSAGES/

# 编辑翻译文件
vim custom-translations/locale/zh_Hans/LC_MESSAGES/django.po

# 编译翻译文件
msgfmt custom-translations/locale/zh_Hans/LC_MESSAGES/django.po \
  -o custom-translations/locale/zh_Hans/LC_MESSAGES/django.mo

# 重启容器
docker-compose restart label-studio
```

**优势**:
- ✅ 不修改 Label Studio 源码
- ✅ 可以自定义任何翻译
- ✅ 升级时只需重新覆盖
- ✅ 可以版本控制自定义翻译

#### 3.2 React 前端翻译覆盖

```yaml
# docker-compose.yml
label-studio:
  volumes:
    # 挂载自定义前端翻译
    - ./custom-translations/frontend:/label-studio/frontend/locales:ro
```

```json
// custom-translations/frontend/zh/translation.json
{
  "common": {
    "save": "保存",
    "cancel": "取消",
    "delete": "删除"
  },
  "annotation": {
    "start": "开始标注",
    "submit": "提交标注",
    "skip": "跳过"
  }
}
```

**优势**:
- ✅ 不修改源码
- ✅ 可以精细控制翻译
- ✅ 支持专业术语定制

---

### Layer 4: SuperInsight 集成层优化

#### 4.1 语言同步机制

```typescript
// frontend/src/components/LabelStudio/LabelStudioEmbed.tsx

import { useEffect, useRef } from 'react';
import { useLanguageStore } from '@/stores/languageStore';

export const LabelStudioEmbed: React.FC<Props> = ({ projectId, taskId }) => {
  const { language } = useLanguageStore();
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const prevLanguageRef = useRef(language);

  // 生成 Label Studio URL
  const getLabelStudioUrl = () => {
    const params = new URLSearchParams();
    params.append('token', authToken);
    params.append('task', taskId);
    
    // 关键：添加语言参数
    params.append('lang', mapLanguage(language));
    
    return `${baseUrl}/projects/${projectId}/data?${params.toString()}`;
  };

  // 语言映射
  const mapLanguage = (lang: string): string => {
    const mapping: Record<string, string> = {
      'zh': 'zh-hans',
      'zh-CN': 'zh-hans',
      'zh-Hans': 'zh-hans',
      'en': 'en',
      'en-US': 'en',
    };
    return mapping[lang] || 'zh-hans';
  };

  // 监听语言变化
  useEffect(() => {
    if (prevLanguageRef.current !== language) {
      // 语言改变时重新加载 iframe
      if (iframeRef.current) {
        const newUrl = getLabelStudioUrl();
        iframeRef.current.src = newUrl;
      }
      prevLanguageRef.current = language;
    }
  }, [language]);

  return (
    <iframe
      ref={iframeRef}
      src={getLabelStudioUrl()}
      style={{ width: '100%', height: '100%', border: 'none' }}
      title="Label Studio"
    />
  );
};
```

**优势**:
- ✅ 自动同步 SuperInsight 和 Label Studio 语言
- ✅ 无缝切换，用户体验好
- ✅ 不修改 Label Studio 源码

#### 4.2 语言切换优化

```typescript
// frontend/src/stores/languageStore.ts

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface LanguageStore {
  language: 'zh' | 'en';
  setLanguage: (lang: 'zh' | 'en') => void;
}

export const useLanguageStore = create<LanguageStore>()(
  persist(
    (set) => ({
      language: 'zh',  // 默认中文
      setLanguage: (lang) => {
        set({ language: lang });
        
        // 同步到 i18n
        import('i18next').then(({ default: i18n }) => {
          i18n.changeLanguage(lang);
        });
        
        // 触发 Label Studio iframe 重载（通过 useEffect）
      },
    }),
    {
      name: 'language-storage',
    }
  )
);
```

**优势**:
- ✅ 持久化语言选择
- ✅ 自动同步到所有组件
- ✅ 触发 Label Studio 语言更新

---

## 翻译质量优化

### 方案 1: 使用官方翻译（推荐）

**优势**:
- ✅ 官方维护，持续更新
- ✅ 与新功能同步
- ✅ 社区贡献，质量提升

**劣势**:
- ⚠️ 机器翻译，可能不够专业
- ⚠️ 专业术语可能不准确

### 方案 2: 自定义翻译覆盖（可选）

**适用场景**:
- 需要专业术语定制
- 需要符合行业规范
- 需要品牌一致性

**实施步骤**:

1. **提取官方翻译**
   ```bash
   # 从容器中提取翻译文件
   docker cp superinsight-label-studio:/label-studio/locale/zh_Hans/LC_MESSAGES/django.po \
     ./translations/django.po
   
   docker cp superinsight-label-studio:/label-studio/frontend/locales/zh/translation.json \
     ./translations/frontend-zh.json
   ```

2. **编辑翻译**
   ```bash
   # 使用专业翻译工具或人工翻译
   vim ./translations/django.po
   vim ./translations/frontend-zh.json
   ```

3. **编译和部署**
   ```bash
   # 编译 Django 翻译
   msgfmt ./translations/django.po -o ./translations/django.mo
   
   # 挂载到容器
   # 见 Layer 3 配置
   ```

4. **版本控制**
   ```bash
   # 将自定义翻译纳入版本控制
   git add translations/
   git commit -m "Add custom Chinese translations"
   ```

**优势**:
- ✅ 完全控制翻译质量
- ✅ 不修改源码
- ✅ 可以版本控制
- ✅ 升级时只需重新覆盖

---

## 升级兼容性保证

### 升级流程

```bash
# 1. 备份当前配置
docker-compose down
cp docker-compose.yml docker-compose.yml.backup
cp -r custom-translations custom-translations.backup

# 2. 更新 Label Studio 镜像
docker pull heartexlabs/label-studio:latest

# 3. 重启服务
docker-compose up -d

# 4. 验证语言功能
curl -I "http://localhost:8080?lang=zh"

# 5. 如果有自定义翻译，重新应用
# （自定义翻译通过 volume 挂载，自动生效）
```

### 兼容性检查清单

- [ ] 环境变量配置是否生效
- [ ] URL 参数 `?lang=zh` 是否工作
- [ ] 默认语言是否为中文
- [ ] 语言切换是否正常
- [ ] 自定义翻译是否生效（如果有）
- [ ] SuperInsight 集成是否正常

---

## 测试方案

### 1. 后端语言测试

```bash
# 测试默认语言
curl -I http://localhost:8080/
# 检查 Content-Language: zh-hans

# 测试 URL 参数
curl -I "http://localhost:8080?lang=zh"
curl -I "http://localhost:8080?lang=en"

# 测试 Accept-Language header
curl -H "Accept-Language: zh-CN,zh;q=0.9" http://localhost:8080/
```

### 2. 前端语言测试

```typescript
// frontend/e2e/label-studio-language.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Label Studio Language Support', () => {
  test('should display Chinese by default', async ({ page }) => {
    await page.goto('/tasks/1/annotate');
    
    const iframe = page.frameLocator('iframe[data-label-studio]');
    
    // 验证 HTML lang 属性
    const html = iframe.locator('html');
    await expect(html).toHaveAttribute('lang', /zh/);
    
    // 验证中文文本
    await expect(iframe.locator('text=标注')).toBeVisible();
    await expect(iframe.locator('text=提交')).toBeVisible();
  });

  test('should switch to English', async ({ page }) => {
    await page.goto('/tasks/1/annotate');
    
    // 切换语言
    await page.click('[data-testid="language-switcher"]');
    await page.click('text=English');
    
    // 等待 iframe 重新加载
    await page.waitForTimeout(2000);
    
    const iframe = page.frameLocator('iframe[data-label-studio]');
    
    // 验证英文
    await expect(iframe.locator('html')).toHaveAttribute('lang', 'en');
    await expect(iframe.locator('text=Annotation')).toBeVisible();
  });

  test('should persist language choice', async ({ page }) => {
    // 设置中文
    await page.goto('/tasks/1/annotate');
    await page.click('[data-testid="language-switcher"]');
    await page.click('text=中文');
    
    // 刷新页面
    await page.reload();
    
    // 验证语言保持
    const iframe = page.frameLocator('iframe[data-label-studio]');
    await expect(iframe.locator('html')).toHaveAttribute('lang', /zh/);
  });
});
```

### 3. 集成测试

```typescript
// frontend/e2e/annotation-workflow-language.spec.ts

test('complete annotation workflow in Chinese', async ({ page }) => {
  // 1. 设置中文
  await page.goto('/');
  await page.click('[data-testid="language-switcher"]');
  await page.click('text=中文');
  
  // 2. 创建任务
  await page.goto('/tasks');
  await page.click('text=创建任务');
  
  // 3. 开始标注
  await page.click('text=开始标注');
  
  // 4. 验证 Label Studio 显示中文
  const iframe = page.frameLocator('iframe[data-label-studio]');
  await expect(iframe.locator('text=标注')).toBeVisible();
  
  // 5. 完成标注
  await iframe.locator('text=提交').click();
  
  // 6. 验证成功消息为中文
  await expect(page.locator('text=标注已提交')).toBeVisible();
});
```

---

## 性能优化

### 1. 语言切换性能

```typescript
// 优化：避免不必要的 iframe 重载

const LabelStudioEmbed: React.FC = () => {
  const { language } = useLanguageStore();
  const [iframeKey, setIframeKey] = useState(0);
  
  useEffect(() => {
    // 只在语言真正改变时重载
    setIframeKey(prev => prev + 1);
  }, [language]);
  
  return (
    <iframe
      key={iframeKey}  // 使用 key 强制重载
      src={getLabelStudioUrl()}
    />
  );
};
```

### 2. 翻译文件缓存

```yaml
# docker-compose.yml
label-studio:
  volumes:
    # 使用只读挂载提高性能
    - ./custom-translations/locale:/label-studio/locale:ro
```

---

## 监控和日志

### 1. 语言使用统计

```python
# src/monitoring/language_metrics.py

from prometheus_client import Counter

language_usage = Counter(
    'label_studio_language_usage',
    'Language usage statistics',
    ['language']
)

def track_language_usage(request):
    lang = request.GET.get('lang', 'zh-hans')
    language_usage.labels(language=lang).inc()
```

### 2. 翻译错误日志

```python
# 监控翻译缺失

import logging

logger = logging.getLogger('label_studio.i18n')

def log_missing_translation(key, language):
    logger.warning(
        f"Missing translation: key={key}, language={language}"
    )
```

---

## 最佳实践

### 1. 开发环境

```yaml
# docker-compose.dev.yml
label-studio:
  environment:
    - LANGUAGE_CODE=zh-hans
    - DEBUG=True  # 显示翻译键，方便调试
```

### 2. 生产环境

```yaml
# docker-compose.prod.yml
label-studio:
  environment:
    - LANGUAGE_CODE=zh-hans
    - DEBUG=False
    - LABEL_STUDIO_LANGUAGES=zh-hans,en  # 限制支持的语言
```

### 3. 翻译维护

```bash
# 定期更新翻译
# 1. 检查官方更新
git clone https://github.com/HumanSignal/label-studio.git
cd label-studio
git pull

# 2. 提取最新翻译
cp -r label_studio/locale/zh_Hans custom-translations/locale/

# 3. 合并自定义翻译
# 使用 msgmerge 工具合并
```

---

## 总结

### ✅ 优势

1. **不修改源码** - 完全通过配置实现
2. **可升级** - 随时升级到最新版本
3. **灵活** - 可选自定义翻译覆盖
4. **性能好** - 原生支持，无额外开销
5. **维护简单** - 配置清晰，易于管理

### 📋 实施清单

- [ ] 更新 docker-compose.yml 添加语言环境变量
- [ ] 更新 LabelStudioEmbed 组件添加语言参数
- [ ] 实现语言同步机制
- [ ] 编写语言切换测试
- [ ] （可选）创建自定义翻译覆盖
- [ ] 部署和验证

### 🎯 预期效果

- ✅ 默认显示中文界面
- ✅ 支持中英文无缝切换
- ✅ 语言选择持久化
- ✅ 不影响 Label Studio 升级
- ✅ 翻译质量可控

---

**文档版本**: 1.0  
**创建日期**: 2026-01-26  
**维护者**: SuperInsight 开发团队  
**状态**: ✅ 优化方案完成
