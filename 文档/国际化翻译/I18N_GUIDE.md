# 多语言支持 (i18n) 使用指南

## 概述

SuperInsight 平台现已支持多语言界面，支持中文和英文的动态切换。默认语言为中文。

## 功能特性

- ✅ 支持中文 (zh) 和英文 (en) 两种语言
- ✅ 默认语言为中文
- ✅ 动态语言切换，无需重启应用
- ✅ 通过请求头或查询参数设置语言
- ✅ 完整的翻译字典覆盖所有 API 响应
- ✅ 易于扩展，支持添加新语言

## 架构

### 模块结构

```
src/i18n/
├── __init__.py           # 模块入口
├── translations.py       # 翻译字典和基础函数
└── manager.py           # 翻译管理器类
```

### 核心组件

1. **translations.py** - 翻译管理
   - `TRANSLATIONS` - 翻译字典
   - `set_language()` - 设置当前语言
   - `get_current_language()` - 获取当前语言
   - `get_translation()` - 获取翻译文本
   - `get_all_translations()` - 获取所有翻译
   - `get_supported_languages()` - 获取支持的语言列表

2. **manager.py** - 翻译管理器
   - `TranslationManager` - 翻译管理器类
   - `get_manager()` - 获取全局管理器实例

3. **simple_app.py** - FastAPI 应用集成
   - 语言中间件 - 自动处理语言设置
   - 语言管理端点 - 获取和设置语言
   - 翻译端点 - 获取翻译字典

## 使用方法

### 1. 在 Python 代码中使用

#### 基础用法

```python
from i18n import get_translation, set_language, get_current_language

# 获取当前语言
current_lang = get_current_language()  # 返回 'zh'

# 设置语言
set_language('en')

# 获取翻译
text = get_translation('app_name')  # 返回 'SuperInsight Platform'
text = get_translation('app_name', 'zh')  # 返回 'SuperInsight 平台'
```

#### 使用翻译管理器

```python
from i18n import get_manager

# 获取管理器实例
manager = get_manager()

# 设置语言
manager.set_language('en')

# 获取翻译
text = manager.translate('login')  # 返回 'Login'
text = manager.t('login')  # 简写方法

# 获取所有翻译
all_translations = manager.get_all()

# 获取支持的语言
languages = manager.get_supported_languages()  # ['zh', 'en']
```

### 2. 在 API 请求中使用

#### 方法 1: 使用查询参数

```bash
# 获取中文响应
curl "http://localhost:8000/api/info?language=zh"

# 获取英文响应
curl "http://localhost:8000/api/info?language=en"
```

#### 方法 2: 使用请求头

```bash
# 使用 Accept-Language 请求头
curl -H "Accept-Language: en" "http://localhost:8000/api/info"
```

### 3. 语言管理端点

#### 获取当前语言设置

```bash
GET /api/settings/language
```

响应示例：
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

#### 设置语言

```bash
POST /api/settings/language?language=en
```

响应示例：
```json
{
  "message": "Language changed",
  "current_language": "en"
}
```

#### 获取翻译字典

```bash
GET /api/i18n/translations
GET /api/i18n/translations?language=en
```

响应示例：
```json
{
  "language": "zh",
  "translations": {
    "app_name": "SuperInsight 平台",
    "login": "登录",
    "logout": "登出",
    ...
  }
}
```

## 翻译键列表

### 通用

- `app_name` - 应用名称
- `app_description` - 应用描述
- `version` - 版本
- `status` - 状态
- `error` - 错误
- `success` - 成功
- `warning` - 警告
- `info` - 信息

### 认证相关

- `login` - 登录
- `logout` - 登出
- `username` - 用户名
- `password` - 密码
- `email` - 邮箱
- `full_name` - 全名
- `role` - 角色
- `invalid_credentials` - 无效的凭证
- `user_created` - 用户已创建
- `user_exists` - 用户已存在
- `login_success` - 登录成功
- `logout_success` - 登出成功

### 用户角色

- `admin` - 系统管理员
- `business_expert` - 业务专家
- `annotator` - 数据标注员
- `viewer` - 报表查看者

### 系统状态

- `healthy` - 健康
- `unhealthy` - 不健康
- `system_status` - 系统状态
- `services` - 服务
- `metrics` - 指标
- `uptime` - 运行时间
- `cpu_usage` - CPU 使用率
- `memory_usage` - 内存使用率
- `disk_usage` - 磁盘使用率

### 数据提取

- `extraction` - 数据提取
- `extract_data` - 提取数据
- `extraction_started` - 数据提取已启动
- `extraction_completed` - 数据提取已完成
- `source_type` - 源类型
- `task_id` - 任务 ID

### 质量管理

- `quality` - 质量
- `evaluate_quality` - 评估质量
- `completeness` - 完整性
- `accuracy` - 准确性
- `consistency` - 一致性
- `overall_score` - 总体评分

### AI 预标注

- `ai_annotation` - AI 预标注
- `preannotate` - 预标注
- `confidence` - 置信度
- `label` - 标签

### 计费

- `billing` - 计费
- `usage` - 使用情况
- `cost` - 成本
- `currency` - 货币
- `total` - 总计
- `extraction_tasks` - 提取任务
- `annotations` - 标注数
- `ai_predictions` - AI 预测
- `storage` - 存储

### 知识图谱

- `knowledge_graph` - 知识图谱
- `entities` - 实体
- `entity` - 实体
- `entity_type` - 实体类型
- `person` - 人物
- `organization` - 组织
- `location` - 地点

### 任务管理

- `tasks` - 任务
- `task` - 任务
- `task_title` - 任务标题
- `pending` - 待处理
- `in_progress` - 进行中
- `completed` - 已完成
- `failed` - 失败
- `created_at` - 创建时间
- `updated_at` - 更新时间

### 错误消息

- `not_found` - 未找到
- `unauthorized` - 未授权
- `forbidden` - 禁止访问
- `bad_request` - 请求错误
- `internal_error` - 内部错误
- `service_unavailable` - 服务不可用

### 语言设置

- `language` - 语言
- `language_changed` - 语言已更改
- `chinese` - 中文
- `english` - 英文

## 添加新语言

### 步骤 1: 添加翻译字典

编辑 `src/i18n/translations.py`，在 `TRANSLATIONS` 字典中添加新语言：

```python
TRANSLATIONS: Dict[str, Dict[str, Any]] = {
    'zh': { ... },
    'en': { ... },
    'es': {  # 西班牙语
        'app_name': 'Plataforma SuperInsight',
        'login': 'Iniciar sesión',
        # ... 其他翻译
    }
}
```

### 步骤 2: 使用新语言

```python
from i18n import set_language, get_translation

set_language('es')
text = get_translation('app_name')  # 返回 'Plataforma SuperInsight'
```

## 测试示例

### 使用 curl 测试

```bash
# 1. 获取中文响应
curl "http://localhost:8000/?language=zh"

# 2. 获取英文响应
curl "http://localhost:8000/?language=en"

# 3. 登录（中文）
curl -X POST "http://localhost:8000/api/security/login?language=zh" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin_test", "password": "admin123"}'

# 4. 登录（英文）
curl -X POST "http://localhost:8000/api/security/login?language=en" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin_test", "password": "admin123"}'

# 5. 获取语言设置
curl "http://localhost:8000/api/settings/language"

# 6. 设置语言为英文
curl -X POST "http://localhost:8000/api/settings/language?language=en"

# 7. 获取翻译字典
curl "http://localhost:8000/api/i18n/translations?language=en"
```

### 使用 Python 测试

```python
import requests

# 获取中文响应
response = requests.get("http://localhost:8000/api/info?language=zh")
print(response.json())

# 获取英文响应
response = requests.get("http://localhost:8000/api/info?language=en")
print(response.json())

# 登录
response = requests.post(
    "http://localhost:8000/api/security/login?language=en",
    json={"username": "admin_test", "password": "admin123"}
)
print(response.json())
```

## 最佳实践

1. **始终使用翻译键** - 不要在代码中硬编码文本
2. **保持翻译同步** - 添加新翻译键时，同时更新所有语言
3. **使用有意义的键名** - 使用清晰的、描述性的键名
4. **测试所有语言** - 确保所有语言的翻译都正确显示
5. **处理缺失翻译** - 如果翻译不存在，系统会返回键名作为后备

## 故障排除

### 问题：翻译不显示

**解决方案**：
1. 检查语言代码是否正确（'zh' 或 'en'）
2. 确认翻译键存在于 `TRANSLATIONS` 字典中
3. 检查是否正确调用了 `set_language()`

### 问题：语言设置不生效

**解决方案**：
1. 确保使用了正确的查询参数或请求头
2. 检查中间件是否正确处理了语言设置
3. 验证语言代码是否在支持的语言列表中

### 问题：新语言不工作

**解决方案**：
1. 确认已在 `TRANSLATIONS` 字典中添加了新语言
2. 检查所有翻译键是否都已定义
3. 重启应用以加载新的翻译

## 相关文件

- `src/i18n/__init__.py` - 模块入口
- `src/i18n/translations.py` - 翻译字典和基础函数
- `src/i18n/manager.py` - 翻译管理器类
- `simple_app.py` - FastAPI 应用集成

## 总结

SuperInsight 平台的多语言支持提供了灵活、易用的国际化解决方案。通过简单的 API 和中间件，用户可以轻松地在中文和英文之间切换，并且系统可以轻松扩展以支持更多语言。
