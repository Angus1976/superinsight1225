# i18n 快速参考指南

## 快速开始

### 在 Python 代码中使用

```python
from i18n import get_translation, set_language

# 获取中文翻译
text = get_translation('app_name')  # 'SuperInsight 平台'

# 切换到英文
set_language('en')
text = get_translation('app_name')  # 'SuperInsight Platform'
```

### 在 FastAPI 中使用

```python
from fastapi import FastAPI
from i18n import get_translation

app = FastAPI()

@app.get("/")
async def root():
    return {
        "name": get_translation("app_name"),
        "language": "zh"
    }
```

## API 端点

### 获取语言设置
```bash
GET /api/settings/language
```

### 设置语言
```bash
POST /api/settings/language?language=en
```

### 获取翻译字典
```bash
GET /api/i18n/translations?language=en
```

## 常用翻译键

| 键 | 中文 | 英文 |
|----|------|------|
| app_name | SuperInsight 平台 | SuperInsight Platform |
| login | 登录 | Login |
| logout | 登出 | Logout |
| username | 用户名 | Username |
| password | 密码 | Password |
| healthy | 健康 | Healthy |
| error | 错误 | Error |
| success | 成功 | Success |
| pending | 待处理 | Pending |
| in_progress | 进行中 | In Progress |
| completed | 已完成 | Completed |

## 使用翻译管理器

```python
from i18n import get_manager

manager = get_manager()

# 设置语言
manager.set_language('en')

# 获取翻译
text = manager.t('login')  # 'Login'

# 获取所有翻译
all_trans = manager.get_all()

# 获取支持的语言
languages = manager.get_supported_languages()  # ['zh', 'en']
```

## 在请求中指定语言

### 方法 1: 查询参数
```bash
curl "http://localhost:8000/api/info?language=en"
```

### 方法 2: 请求头
```bash
curl -H "Accept-Language: en" "http://localhost:8000/api/info"
```

## 添加新翻译

编辑 `src/i18n/translations.py`：

```python
TRANSLATIONS = {
    'zh': {
        'my_key': '我的翻译',
        ...
    },
    'en': {
        'my_key': 'My Translation',
        ...
    }
}
```

然后在代码中使用：
```python
text = get_translation('my_key')
```

## 添加新语言

编辑 `src/i18n/translations.py`：

```python
TRANSLATIONS['es'] = {
    'app_name': 'Plataforma SuperInsight',
    'login': 'Iniciar sesión',
    # ... 所有 90 个翻译键
}
```

## 测试

运行测试脚本：
```bash
python3 test_i18n.py
```

## 常见问题

**Q: 如何设置默认语言？**
A: 在应用启动时调用 `set_language('zh')`

**Q: 如何处理缺失的翻译？**
A: 系统会返回翻译键作为后备值

**Q: 如何在前端使用？**
A: 调用 `/api/i18n/translations` 获取翻译字典，然后在前端使用

**Q: 支持多少种语言？**
A: 目前支持中文和英文，可轻松扩展

## 文件位置

- 模块: `src/i18n/`
- 应用: `simple_app.py`
- 文档: `I18N_GUIDE.md`
- 测试: `test_i18n.py`

## 相关命令

```bash
# 运行测试
python3 test_i18n.py

# 启动应用
python3 simple_app.py

# 测试 API
curl "http://localhost:8000/api/settings/language"
curl -X POST "http://localhost:8000/api/settings/language?language=en"
curl "http://localhost:8000/api/i18n/translations?language=en"
```

## 支持的语言代码

- `zh` - 中文 (Chinese)
- `en` - 英文 (English)

## 翻译键总数

**90 个翻译键** 覆盖所有功能

## 更多信息

详见 `I18N_GUIDE.md` 和 `I18N_IMPLEMENTATION_SUMMARY.md`
