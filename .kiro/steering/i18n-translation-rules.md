# i18n 翻译规范

**Version**: 1.0  
**Status**: ✅ Active  
**Last Updated**: 2026-01-25  
**Priority**: HIGH

## 概述

本规范旨在防止 i18n 翻译实现中的常见错误，确保翻译键的正确使用和维护。基于 2026-01-25 修复的实际问题总结而成。

## 问题背景

### 2026-01-25 翻译错误案例

**问题描述**:
- 页面显示 "returned an object instead of string" 错误
- 翻译键 `systemMonitoring` 和 `securityAudit` 无法正确显示

**根本原因**:
1. 代码中使用 `t('systemMonitoring')` 期望返回字符串
2. 但翻译文件中 `systemMonitoring` 是一个对象（包含 `title`、`timeRange` 等子键）
3. 英文翻译文件中存在重复键定义（字符串 + 对象）

**影响范围**:
- 前端页面显示异常
- 用户体验受损
- 需要重建容器才能修复

## 强制规则

### 规则 1: 区分对象和字符串类型

**核心原则**: 翻译键的类型必须与代码中的使用方式一致

#### 1.1 对象类型翻译键

**定义**: 包含多个子键的翻译结构

**❌ 错误使用**:
```typescript
// 翻译文件 (admin.json)
{
  "systemMonitoring": {
    "title": "系统监控",
    "timeRange": "时间范围",
    "refresh": "刷新"
  }
}

// 代码中错误使用
const label = t('systemMonitoring');  // ❌ 返回对象，不是字符串
```

**✅ 正确使用**:
```typescript
// 翻译文件 (admin.json)
{
  "systemMonitoring": {
    "title": "系统监控",
    "timeRange": "时间范围",
    "refresh": "刷新"
  }
}

// 代码中正确使用
const title = t('systemMonitoring.title');      // ✅ 返回 "系统监控"
const timeRange = t('systemMonitoring.timeRange'); // ✅ 返回 "时间范围"
```

#### 1.2 字符串类型翻译键

**定义**: 直接映射到字符串值的翻译键

**✅ 正确定义和使用**:
```typescript
// 翻译文件 (admin.json)
{
  "save": "保存",
  "cancel": "取消",
  "confirm": "确认"
}

// 代码中使用
const saveLabel = t('save');    // ✅ 返回 "保存"
const cancelLabel = t('cancel'); // ✅ 返回 "取消"
```

#### 1.3 类型检查清单

在添加或使用翻译键时，必须确认：

- [ ] 翻译文件中的键是对象还是字符串？
- [ ] 代码中的使用方式是否匹配类型？
- [ ] 如果是对象，是否使用了正确的子键路径？
- [ ] 如果是字符串，是否直接使用键名？

### 规则 2: 避免重复翻译键

**核心原则**: 每个翻译键在同一文件中只能定义一次

#### 2.1 检测重复键

**❌ 错误示例 - 重复定义**:
```json
{
  "systemMonitoring": "系统监控",  // ❌ 第一次定义（字符串）
  "securityAudit": "安全审计",
  "systemMonitoring": {            // ❌ 第二次定义（对象）- 会覆盖第一次
    "title": "系统监控",
    "timeRange": "时间范围"
  }
}
```

**问题**:
- JSON 中后定义的键会覆盖先定义的键
- 导致不可预测的行为
- 难以调试和维护

**✅ 正确示例 - 唯一定义**:
```json
{
  "systemMonitoring": {
    "title": "系统监控",
    "timeRange": "时间范围",
    "refresh": "刷新"
  },
  "securityAudit": {
    "title": "安全审计",
    "auditLogs": "审计日志"
  }
}
```

#### 2.2 添加翻译键前的检查流程

**必须执行的步骤**:

1. **搜索现有键**
   ```bash
   # 在翻译文件中搜索键名
   grep -n '"systemMonitoring"' frontend/src/locales/zh/admin.json
   grep -n '"systemMonitoring"' frontend/src/locales/en/admin.json
   ```

2. **检查键的类型**
   - 如果键已存在，确认是对象还是字符串
   - 如果是对象，考虑添加子键而不是新键
   - 如果是字符串，考虑是否需要转换为对象

3. **验证所有语言文件**
   - 中文文件 (`zh/admin.json`)
   - 英文文件 (`en/admin.json`)
   - 确保结构一致

4. **使用工具检测重复**
   ```bash
   # 检测重复键（简单方法）
   cat frontend/src/locales/zh/admin.json | grep -o '"[^"]*":' | sort | uniq -d
   ```

#### 2.3 重复键的修复策略

**场景 1: 字符串 + 对象重复**

```json
// ❌ 错误
{
  "systemMonitoring": "系统监控",
  "systemMonitoring": {
    "title": "系统监控"
  }
}

// ✅ 修复方案 1: 保留对象，删除字符串
{
  "systemMonitoring": {
    "title": "系统监控",
    "timeRange": "时间范围"
  }
}

// ✅ 修复方案 2: 重命名字符串键
{
  "systemMonitoringLabel": "系统监控",  // 重命名
  "systemMonitoring": {
    "title": "系统监控",
    "timeRange": "时间范围"
  }
}
```

**场景 2: 多个对象重复**

```json
// ❌ 错误
{
  "user": {
    "name": "用户名"
  },
  "user": {  // 重复
    "email": "邮箱"
  }
}

// ✅ 修复: 合并对象
{
  "user": {
    "name": "用户名",
    "email": "邮箱"
  }
}
```

### 规则 3: 翻译键命名规范

#### 3.1 命名约定

**对象类型键** (包含子键):
- 使用 camelCase
- 名称应该是名词或名词短语
- 表示一个功能模块或概念

```json
{
  "systemMonitoring": { ... },
  "securityAudit": { ... },
  "userManagement": { ... }
}
```

**字符串类型键** (直接值):
- 使用 camelCase
- 名称应该清晰表达含义
- 常用于通用操作或标签

```json
{
  "save": "保存",
  "cancel": "取消",
  "delete": "删除",
  "confirmDelete": "确认删除"
}
```

**子键命名**:
- 使用 camelCase
- 应该在父键的上下文中有意义

```json
{
  "systemMonitoring": {
    "title": "系统监控",        // 标题
    "timeRange": "时间范围",    // 时间范围
    "refresh": "刷新",          // 刷新按钮
    "overview": {               // 嵌套对象
      "systemStatus": "系统状态"
    }
  }
}
```

#### 3.2 命名层级建议

**推荐结构** (最多 3-4 层):
```json
{
  "module": {                    // 第 1 层: 模块
    "feature": {                 // 第 2 层: 功能
      "component": {             // 第 3 层: 组件
        "element": "文本"        // 第 4 层: 元素
      }
    }
  }
}
```

**实际示例**:
```json
{
  "admin": {                           // 模块
    "systemMonitoring": {              // 功能
      "services": {                    // 组件
        "title": "服务健康状态",       // 元素
        "name": "服务",
        "status": "状态"
      }
    }
  }
}
```

### 规则 4: 代码中的翻译使用规范

#### 4.1 TypeScript 类型安全

**推荐**: 使用 TypeScript 类型定义确保翻译键的正确性

```typescript
// types/i18n.ts
export type TranslationKeys = 
  | 'save'
  | 'cancel'
  | 'systemMonitoring.title'
  | 'systemMonitoring.timeRange'
  | 'securityAudit.title';

// 使用时有类型提示
const title = t('systemMonitoring.title' as TranslationKeys);
```

#### 4.2 避免动态拼接

**❌ 不推荐**:
```typescript
const section = 'systemMonitoring';
const key = 'title';
const text = t(`${section}.${key}`);  // ❌ 难以追踪和维护
```

**✅ 推荐**:
```typescript
const text = t('systemMonitoring.title');  // ✅ 明确且可追踪
```

#### 4.3 处理缺失的翻译

**使用默认值**:
```typescript
// 提供默认值
const text = t('systemMonitoring.title', { defaultValue: 'System Monitoring' });

// 或使用可选链
const text = t('systemMonitoring.title') || 'System Monitoring';
```

### 规则 5: 翻译文件维护流程

#### 5.1 添加新翻译键

**步骤**:

1. **确定键的类型** (对象 or 字符串)
2. **检查是否已存在**
   ```bash
   grep -rn '"newKey"' frontend/src/locales/
   ```
3. **在所有语言文件中添加**
   - `frontend/src/locales/zh/admin.json`
   - `frontend/src/locales/en/admin.json`
4. **确保结构一致**
5. **验证无重复**
6. **测试翻译效果**

#### 5.2 修改现有翻译键

**步骤**:

1. **搜索所有使用该键的代码**
   ```bash
   grep -rn "t('oldKey')" frontend/src/
   ```
2. **评估影响范围**
3. **同步更新所有语言文件**
4. **更新所有使用该键的代码**
5. **运行测试验证**

#### 5.3 删除翻译键

**步骤**:

1. **确认键未被使用**
   ```bash
   grep -rn "t('keyToDelete')" frontend/src/
   ```
2. **从所有语言文件中删除**
3. **提交时注明删除原因**

### 规则 6: 翻译文件结构规范

#### 6.1 文件组织

**推荐结构**:
```
frontend/src/locales/
├── zh/
│   ├── common.json      # 通用翻译
│   ├── admin.json       # 管理后台翻译
│   ├── user.json        # 用户相关翻译
│   └── errors.json      # 错误消息翻译
└── en/
    ├── common.json
    ├── admin.json
    ├── user.json
    └── errors.json
```

#### 6.2 JSON 格式规范

**必须遵守**:
- 使用 2 空格缩进
- 键名使用双引号
- 最后一个键值对后不加逗号
- 保持合理的嵌套层级（不超过 4 层）

**示例**:
```json
{
  "systemMonitoring": {
    "title": "系统监控",
    "overview": {
      "systemStatus": "系统状态",
      "uptime": "运行时间"
    }
  }
}
```

#### 6.3 保持语言文件同步

**关键点**:
- 所有语言文件必须有相同的键结构
- 键的顺序应该保持一致
- 嵌套层级必须相同

**验证脚本示例**:
```bash
# 比较中英文文件的键结构
diff <(jq -S 'keys' frontend/src/locales/zh/admin.json) \
     <(jq -S 'keys' frontend/src/locales/en/admin.json)
```

## 开发流程检查点

### 添加新功能时

- [ ] 确定需要哪些翻译键
- [ ] 检查是否已存在相关键
- [ ] 决定使用对象还是字符串类型
- [ ] 在所有语言文件中添加翻译
- [ ] 验证无重复键
- [ ] 在代码中正确使用翻译键
- [ ] 测试语言切换功能

### 修改现有功能时

- [ ] 搜索相关翻译键的使用
- [ ] 评估修改影响范围
- [ ] 同步更新所有语言文件
- [ ] 更新所有使用该键的代码
- [ ] 运行测试验证修改

### 代码审查时

- [ ] 检查翻译键类型是否正确
- [ ] 验证无重复键定义
- [ ] 确认所有语言文件已更新
- [ ] 检查代码中的使用方式
- [ ] 验证翻译文本的准确性

## 自动化检查

### 提交前检查

```bash
# 在 frontend 目录运行
npm run i18n:check  # 如果有配置的话

# 或手动检查
# 1. 检查重复键
cat src/locales/zh/admin.json | grep -o '"[^"]*":' | sort | uniq -d

# 2. 检查键结构一致性
diff <(jq -S 'keys' src/locales/zh/admin.json) \
     <(jq -S 'keys' src/locales/en/admin.json)

# 3. 验证 JSON 格式
jq empty src/locales/zh/admin.json
jq empty src/locales/en/admin.json
```

### CI/CD 检查

```yaml
# GitHub Actions 示例
- name: i18n Validation
  run: |
    cd frontend
    # 检查 JSON 格式
    jq empty src/locales/zh/admin.json
    jq empty src/locales/en/admin.json
    
    # 检查键结构一致性
    npm run i18n:validate
```

## 常见错误模式

### 模式 1: 对象当字符串使用

**错误**:
```typescript
// 翻译文件
{ "user": { "name": "用户名" } }

// 代码
const label = t('user');  // ❌ 返回对象
```

**修复**:
```typescript
const label = t('user.name');  // ✅ 返回 "用户名"
```

### 模式 2: 重复键定义

**错误**:
```json
{
  "save": "保存",
  "save": "保存数据"  // ❌ 重复
}
```

**修复**:
```json
{
  "save": "保存",
  "saveData": "保存数据"  // ✅ 使用不同的键名
}
```

### 模式 3: 不一致的嵌套结构

**错误**:
```json
// zh/admin.json
{
  "user": {
    "profile": {
      "name": "姓名"
    }
  }
}

// en/admin.json
{
  "user": {
    "name": "Name"  // ❌ 结构不一致
  }
}
```

**修复**:
```json
// en/admin.json
{
  "user": {
    "profile": {
      "name": "Name"  // ✅ 结构一致
    }
  }
}
```

## 故障排查指南

### 问题: "returned an object instead of string"

**原因**: 翻译键是对象，但代码期望字符串

**排查步骤**:
1. 检查翻译文件中该键的类型
2. 确认代码中的使用方式
3. 修改代码使用正确的子键路径

**示例**:
```typescript
// 如果看到错误
const text = t('systemMonitoring');  // ❌

// 检查翻译文件
// { "systemMonitoring": { "title": "..." } }

// 修复
const text = t('systemMonitoring.title');  // ✅
```

### 问题: 翻译不显示或显示键名

**原因**: 翻译键不存在或路径错误

**排查步骤**:
1. 检查翻译文件中是否存在该键
2. 验证键的路径是否正确
3. 确认所有语言文件都有该键
4. 检查是否有拼写错误

### 问题: 语言切换后翻译不更新

**原因**: 可能是缓存问题或翻译文件未正确加载

**排查步骤**:
1. 清除浏览器缓存
2. 检查翻译文件是否正确加载
3. 验证 i18n 配置是否正确
4. 重启开发服务器

## 工具和脚本

### 检测重复键脚本

```bash
#!/bin/bash
# check-duplicate-keys.sh

echo "Checking for duplicate keys in translation files..."

for file in frontend/src/locales/*/*.json; do
  echo "Checking $file..."
  duplicates=$(cat "$file" | grep -o '"[^"]*":' | sort | uniq -d)
  if [ -n "$duplicates" ]; then
    echo "❌ Found duplicate keys in $file:"
    echo "$duplicates"
  else
    echo "✅ No duplicates in $file"
  fi
done
```

### 验证键结构一致性脚本

```bash
#!/bin/bash
# check-key-consistency.sh

echo "Checking key structure consistency..."

zh_keys=$(jq -r 'paths(scalars) | join(".")' frontend/src/locales/zh/admin.json | sort)
en_keys=$(jq -r 'paths(scalars) | join(".")' frontend/src/locales/en/admin.json | sort)

diff <(echo "$zh_keys") <(echo "$en_keys") > /tmp/key-diff.txt

if [ -s /tmp/key-diff.txt ]; then
  echo "❌ Key structure mismatch found:"
  cat /tmp/key-diff.txt
else
  echo "✅ Key structures are consistent"
fi
```

### 查找未使用的翻译键

```bash
#!/bin/bash
# find-unused-keys.sh

echo "Finding unused translation keys..."

for key in $(jq -r 'paths(scalars) | join(".")' frontend/src/locales/zh/admin.json); do
  if ! grep -rq "t('$key')" frontend/src/; then
    echo "Unused key: $key"
  fi
done
```

## 参考资料

- [react-i18next 文档](https://react.i18next.com/)
- [i18next 最佳实践](https://www.i18next.com/principles/fallback)
- [TypeScript i18n 类型安全](https://react.i18next.com/latest/typescript)

## 历史问题记录

### 2026-01-25: systemMonitoring 和 securityAudit 对象类型错误

**问题**: 代码使用 `t('systemMonitoring')` 但翻译文件中是对象
**影响**: 页面显示 "returned an object instead of string" 错误
**修复**: 修改代码使用 `t('systemMonitoring.title')`
**文档**: `TRANSLATION_FIX_VERIFICATION_GUIDE.md`

---

**此规范为强制性规范，所有前端 i18n 开发必须遵守。**

**违反规范将导致**:
1. PR 被拒绝
2. 需要重新修复
3. 可能需要重建容器

---

**最后更新**: 2026-01-25  
**维护者**: SuperInsight 开发团队  
**反馈**: 如发现规范不完善或有改进建议，请提交 issue
