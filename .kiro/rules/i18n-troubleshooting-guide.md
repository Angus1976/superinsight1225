---
inclusion: manual
---

# i18n 翻译问题诊断与解决指南

**Version**: 1.0  
**Last Updated**: 2026-03-12  
**Priority**: HIGH

---

## 🎯 核心原则

**翻译键路径必须与 JSON 结构完全匹配**

- 代码中 `t('common.status.pending')` → JSON 中必须是 `{ "common": { "status": { "pending": "..." } } }`
- 代码中 `t('created')` → JSON 中必须是 `{ "created": "..." }`（顶级键）
- 路径不匹配 = 显示字面文本（如 "common.status.pending"）

---

## 📋 问题诊断流程（按顺序执行）

### 第 1 步：确认问题现象

**症状识别**：
- ✅ 显示翻译键字面文本（如 "common.status.pending"）→ 键路径问题
- ✅ 显示空白或 undefined → 键不存在
- ✅ 部分翻译正常，部分不正常 → 特定键的问题

### 第 2 步：检查代码中的翻译调用

**检查点**：
```typescript
// 1. 确认使用的命名空间
const { t } = useTranslation('dataLifecycle');  // 单命名空间
const { t } = useTranslation(['dataLifecycle', 'common']);  // 多命名空间

// 2. 确认翻译键的完整路径
t('common.status.pending')  // 期望路径：common.status.pending
t('created')                // 期望路径：created（顶级）
t(`common.${action}`)       // 动态路径：common.created, common.approved 等
```

### 第 3 步：检查 JSON 文件结构

**打开对应的翻译文件**：
- `frontend/src/locales/zh/[namespace].json`
- `frontend/src/locales/en/[namespace].json`

**验证键路径**：
```json
// ✅ 正确：路径匹配
{
  "common": {
    "status": {
      "pending": "待处理"
    },
    "created": "创建"
  }
}
// 代码调用：t('common.status.pending') ✓
// 代码调用：t('common.created') ✓

// ❌ 错误：路径不匹配
{
  "common": {
    "status": {
      "pending": "待处理"
    }
  },
  "created": "创建"  // 这是顶级键，不在 common 下！
}
// 代码调用：t('common.created') ✗ 显示 "common.created"
// 代码调用：t('created') ✓
```

### 第 4 步：修复方案选择

**方案 A：调整 JSON 结构（推荐）**
- 适用场景：键的组织不合理，应该归类到某个对象下
- 操作：将键移到正确的对象层级

```json
// 修复前
{
  "created": "创建",
  "approved": "通过"
}

// 修复后
{
  "common": {
    "created": "创建",
    "approved": "通过"
  }
}
```

**方案 B：调整代码调用（谨慎使用）**
- 适用场景：JSON 结构合理，代码调用路径错误
- 操作：修改 `t()` 调用的键路径

```typescript
// 修复前
t('common.created')  // JSON 中 created 是顶级键

// 修复后
t('created')  // 直接访问顶级键
```

**方案 C：使用多命名空间（特殊场景）**
- 适用场景：需要跨命名空间访问翻译
- 操作：在 `useTranslation` 中声明多个命名空间

```typescript
// 修复前
const { t } = useTranslation('dataLifecycle');
t('common.cancel')  // 尝试访问 common 命名空间的键

// 修复后
const { t } = useTranslation(['dataLifecycle', 'common']);
t('common:cancel')  // 使用命名空间前缀
// 或者在 dataLifecycle.json 中添加该键
```

---

## 🔍 常见错误模式

### 错误 1：键在错误的层级

**问题**：
```typescript
// 代码
t('common.created')

// JSON
{
  "created": "创建"  // 顶级键，不在 common 下
}
```

**解决**：
```json
{
  "common": {
    "created": "创建"  // 移到 common 对象内
  }
}
```

### 错误 2：动态键路径不匹配

**问题**：
```typescript
// 代码
const action = 'created';
t(`common.${action}`)  // 期望 common.created

// JSON
{
  "created": "创建"  // 不在 common 下
}
```

**解决**：
```json
{
  "common": {
    "created": "创建",
    "approved": "通过",
    "started": "开始"
  }
}
```

### 错误 3：命名空间混淆

**问题**：
```typescript
// 代码
const { t } = useTranslation('dataLifecycle');
t('common.cancel')  // 尝试访问 common 命名空间

// dataLifecycle.json
{
  "common": {
    "cancel": "取消"  // 这不是 common 命名空间，只是 dataLifecycle 中的 common 对象
  }
}
```

**理解**：
- `useTranslation('dataLifecycle')` → 只加载 `dataLifecycle.json`
- `t('common.cancel')` → 访问 `dataLifecycle.json` 中的 `common.cancel` 路径
- 如果要访问 `common.json` 命名空间，需要 `useTranslation(['dataLifecycle', 'common'])` 然后 `t('common:cancel')`

### 错误 4：useTranslation 参数类型错误（字符串 vs 数组）

**问题**：
```typescript
// ❌ 错误：传入字符串而不是数组
const { t } = useTranslation('aiProcessing, common');  // 这会被当作单个命名空间名称

// ❌ 错误：数组写成字符串
const { t } = useTranslation("['aiProcessing', 'common']");  // 字符串，不是数组
```

**正确写法**：
```typescript
// ✅ 单命名空间：传字符串
const { t } = useTranslation('aiProcessing');

// ✅ 多命名空间：传数组
const { t } = useTranslation(['aiProcessing', 'common']);
```

**症状识别**：
- 所有翻译都不工作
- 控制台可能报错 "namespace not found"
- i18n 无法加载翻译文件

### 错误 5：翻译键不全（部分键缺失）

**问题**：
```typescript
// 代码中使用了多个状态
const statuses = ['pending', 'success', 'failed', 'cancelled'];
statuses.map(status => t(`common.status.${status}`))

// JSON 中只定义了部分
{
  "common": {
    "status": {
      "pending": "待处理",
      "success": "成功"
      // ❌ 缺少 failed 和 cancelled
    }
  }
}
```

**解决**：
```json
{
  "common": {
    "status": {
      "pending": "待处理",
      "success": "成功",
      "failed": "失败",      // ✅ 补全
      "cancelled": "已取消"  // ✅ 补全
    }
  }
}
```

**预防方法**：
- 使用动态键时，先列出所有可能的值
- 在 JSON 中一次性定义所有键
- 添加代码注释说明可能的值范围

### 错误 6：JSON 语法错误

**问题**：
```json
{
  "common": {
    "status": {
      "pending": "待处理",  // 多余的逗号
    }
  }
}
```

**检查方法**：
```bash
# 验证 JSON 语法
cat frontend/src/locales/zh/dataLifecycle.json | python -m json.tool
```

### 错误 7：中英文翻译键不同步

**问题**：
```json
// zh/dataLifecycle.json
{
  "common": {
    "status": {
      "pending": "待处理",
      "success": "成功",
      "failed": "失败"
    }
  }
}

// en/dataLifecycle.json
{
  "common": {
    "status": {
      "pending": "Pending",
      "success": "Success"
      // ❌ 缺少 failed
    }
  }
}
```

**症状**：
- 切换语言后部分翻译显示为键名
- 英文环境下显示 "common.status.failed"

**解决**：
- 修改翻译时同时更新中英文文件
- 使用工具对比两个文件的键结构
- 建立检查清单确保同步

### 错误 8：对象与字符串混淆

**问题**：
```json
// ❌ 错误：status 应该是对象，却写成了字符串
{
  "common": {
    "status": "状态"  // 这是字符串
  }
}

// 代码期望
t('common.status.pending')  // 期望 common.status 是对象
```

**正确写法**：
```json
{
  "common": {
    "statusLabel": "状态",  // 如果需要 "状态" 这个标签
    "status": {              // status 作为对象包含多个状态值
      "pending": "待处理",
      "success": "成功"
    }
  }
}
```

**识别方法**：
- 错误信息：`Cannot read property 'pending' of undefined`
- 翻译显示为对象：`[object Object]`

### 错误 9：数组与字符串混淆（useTranslation 参数）

**问题**：
```typescript
// ❌ 错误：想用多命名空间，但传了字符串
const { t } = useTranslation('aiProcessing, common');

// ❌ 错误：把数组写成字符串
const { t } = useTranslation("['aiProcessing', 'common']");

// ❌ 错误：单命名空间却传了数组（虽然能工作，但不规范）
const { t } = useTranslation(['aiProcessing']);
```

**正确写法**：
```typescript
// ✅ 单命名空间
const { t } = useTranslation('aiProcessing');

// ✅ 多命名空间
const { t } = useTranslation(['aiProcessing', 'common']);
```

### 错误 10：翻译键拼写错误

**问题**：
```typescript
// 代码
t('common.status.pendding')  // 拼写错误：pendding

// JSON
{
  "common": {
    "status": {
      "pending": "待处理"  // 正确拼写：pending
    }
  }
}
```

**预防**：
- 使用 TypeScript 类型定义翻译键
- 使用常量定义常用的键名
- 代码审查时注意检查

---

## ✅ 标准修复流程

### 步骤 1：定位问题键

```bash
# 在代码中搜索翻译调用
grep -r "t('common.status.pending')" frontend/src/
grep -r "t(\`common.\${" frontend/src/
```

### 步骤 2：检查 JSON 结构

```bash
# 读取翻译文件
cat frontend/src/locales/zh/dataLifecycle.json | grep -A 5 "common"
```

### 步骤 3：修复 JSON 文件

使用 `strReplace` 工具精确修改 JSON 结构：

```typescript
// 确保修改后的 JSON 结构与代码调用匹配
{
  "common": {
    "status": {
      "pending": "待处理",
      "failed": "失败"
    },
    "created": "创建",
    "approved": "通过"
  }
}
```

### 步骤 4：同步中英文翻译

```bash
# 确保中英文文件结构一致
# zh/dataLifecycle.json 和 en/dataLifecycle.json 的键路径必须完全相同
```

### 步骤 5：提交并部署

```bash
git add frontend/src/locales/zh/*.json frontend/src/locales/en/*.json
git commit -m "fix: 修复翻译键路径不匹配问题"
git push origin main
docker compose build frontend
docker compose up -d frontend
```

### 步骤 6：验证修复

```bash
# 等待容器启动（约 10-15 秒）
sleep 15

# 检查容器日志
docker logs superinsight-frontend --tail 50

# 浏览器测试：
# 1. 硬刷新（Cmd+Shift+R 或 Ctrl+Shift+R）
# 2. 清除缓存
# 3. 无痕模式测试
```

---

## 🚫 避免的错误做法

### ❌ 错误 1：盲目添加多命名空间

```typescript
// 不要这样做
const { t } = useTranslation(['dataLifecycle', 'common', 'aiProcessing']);
// 除非真的需要跨命名空间访问
```

**正确做法**：
- 优先在当前命名空间的 JSON 文件中添加需要的键
- 只在确实需要复用其他命名空间的翻译时才使用多命名空间

### ❌ 错误 2：在多个地方重复定义相同的键

```json
// dataLifecycle.json
{
  "common": {
    "cancel": "取消"
  }
}

// common.json
{
  "cancel": "取消"
}
```

**正确做法**：
- 通用的键（如 cancel, confirm, save）放在 `common.json`
- 特定模块的键放在对应的命名空间文件中

### ❌ 错误 3：修改后不重启容器

```bash
# 错误：只修改文件，不重新构建
git commit -m "fix translation"
git push
# 容器还在运行旧代码！
```

**正确做法**：
```bash
git commit && git push
docker compose build frontend
docker compose up -d frontend
```

### ❌ 错误 4：useTranslation 参数写错类型

```typescript
// ❌ 错误：字符串当数组用
const { t } = useTranslation('aiProcessing, common');

// ❌ 错误：数组写成字符串
const { t } = useTranslation("['aiProcessing', 'common']");
```

**正确做法**：
```typescript
// 单命名空间 → 字符串
const { t } = useTranslation('aiProcessing');

// 多命名空间 → 数组
const { t } = useTranslation(['aiProcessing', 'common']);
```

### ❌ 错误 5：只修改中文不修改英文

```bash
# 错误：只提交中文翻译
git add frontend/src/locales/zh/dataLifecycle.json
git commit -m "add translation"
```

**正确做法**：
```bash
# 同时修改中英文
git add frontend/src/locales/zh/dataLifecycle.json frontend/src/locales/en/dataLifecycle.json
git commit -m "fix: 添加翻译键（中英文）"
```

### ❌ 错误 6：JSON 结构与代码不匹配就尝试多命名空间

```typescript
// 代码
const { t } = useTranslation('dataLifecycle');
t('common.created')  // 显示 "common.created"

// 错误的修复：添加多命名空间
const { t } = useTranslation(['dataLifecycle', 'common']);
t('common:created')  // 还是不对
```

**正确做法**：
```json
// 直接修复 JSON 结构
{
  "common": {
    "created": "创建"  // 添加到 dataLifecycle.json 的 common 对象下
  }
}
```

### ❌ 错误 7：不检查 JSON 语法就提交

```json
{
  "common": {
    "status": {
      "pending": "待处理",  // 多余的逗号
    }
  }
}
```

**正确做法**：
```bash
# 提交前验证 JSON
python -m json.tool < frontend/src/locales/zh/dataLifecycle.json
# 或
jq . frontend/src/locales/zh/dataLifecycle.json
```

---

## 📊 实际案例：数据流转页面翻译修复

### 问题描述

页面显示 "common.status.pending" 字面文本，而不是 "待处理"。

### 诊断过程

1. **检查代码**：
```typescript
// RecentActivity 组件
const { t } = useTranslation('dataLifecycle');
description={`${t(`common.${item.action}`)} - ${item.timestamp}`}
// 期望：t('common.created') → "创建"
```

2. **检查 JSON**：
```json
// dataLifecycle.json（修复前）
{
  "common": {
    "status": {
      "pending": "待处理"
    }
  },
  "created": "创建",  // ❌ 顶级键，不在 common 下
  "approved": "通过"
}
```

3. **发现问题**：
- 代码调用 `t('common.created')`
- JSON 中 `created` 是顶级键，路径是 `created` 而不是 `common.created`
- 路径不匹配 → 显示字面文本

### 修复方案

```json
// dataLifecycle.json（修复后）
{
  "common": {
    "status": {
      "pending": "待处理"
    },
    "created": "创建",  // ✅ 移到 common 对象内
    "approved": "通过",
    "started": "开始",
    "added": "添加",
    "completed": "完成"
  }
}
```

### 修复结果

- 提交：`143da77`
- 翻译正常显示："创建"、"通过"、"开始" 等

---

## 🎓 最佳实践

### 1. 翻译键命名规范

```json
{
  "模块名": {
    "子模块": {
      "具体功能": "翻译文本"
    }
  }
}
```

示例：
```json
{
  "tempData": {
    "actions": {
      "create": "创建临时数据",
      "edit": "编辑",
      "delete": "删除"
    },
    "status": {
      "draft": "草稿",
      "ready": "就绪"
    }
  }
}
```

### 2. 通用键的组织

```json
{
  "common": {
    "actions": {
      "save": "保存",
      "cancel": "取消",
      "confirm": "确认"
    },
    "status": {
      "success": "成功",
      "failed": "失败",
      "pending": "待处理"
    }
  }
}
```

### 3. 代码调用规范

```typescript
// 单命名空间（推荐）
const { t } = useTranslation('dataLifecycle');
t('tempData.actions.create')  // 清晰的路径

// 多命名空间（必要时）
const { t } = useTranslation(['dataLifecycle', 'common']);
t('tempData.actions.create')  // dataLifecycle 命名空间
t('common:actions.save')      // common 命名空间（使用前缀）
```

### 4. 动态键的处理

```typescript
// ✅ 推荐：确保所有可能的值都在 JSON 中定义
const status = 'pending';
t(`common.status.${status}`)  // common.status.pending

// JSON 中必须有：
{
  "common": {
    "status": {
      "pending": "待处理",
      "success": "成功",
      "failed": "失败"
    }
  }
}
```

---

## 🔧 调试工具

### 1. 浏览器控制台检查

```javascript
// 在浏览器控制台执行
console.log(i18n.t('common.status.pending'));
// 如果返回 "common.status.pending" → 键不存在或路径错误
// 如果返回 "待处理" → 翻译正常

// 查看当前加载的翻译
console.log(i18n.store.data);
```

### 2. 添加调试日志

```typescript
const { t } = useTranslation('dataLifecycle');

// 临时添加调试
console.log('Translation key:', `common.${action}`);
console.log('Translation result:', t(`common.${action}`));
```

### 3. JSON 验证

```bash
# 验证 JSON 语法
python -m json.tool < frontend/src/locales/zh/dataLifecycle.json

# 或使用 jq
jq . frontend/src/locales/zh/dataLifecycle.json
```

---

## 📝 检查清单

修复翻译问题前，按此清单逐项检查：

- [ ] 确认显示的是翻译键字面文本还是其他问题
- [ ] 找到代码中的 `t()` 调用，记录完整的键路径
- [ ] 打开对应的 JSON 文件，验证键路径是否存在
- [ ] 检查 JSON 结构是否与代码调用匹配
- [ ] 确认中英文 JSON 文件结构一致
- [ ] 验证 JSON 语法无错误
- [ ] 选择合适的修复方案（调整 JSON 或调整代码）
- [ ] 同步修改中英文翻译文件
- [ ] 提交代码并推送
- [ ] 重新构建并部署前端容器
- [ ] 等待容器启动完成（15 秒）
- [ ] 浏览器硬刷新测试

---

**记住：翻译问题 99% 是键路径不匹配。先检查路径，再考虑其他原因。**
