---
inclusion: manual
---

# i18n 翻译规范

**Version**: 2.0  
**Last Updated**: 2026-02-04  
**Priority**: HIGH  
**加载方式**: 手动加载（按需引用）

---

## 📌 核心原则（必读）

**类型一致 > 无重复 > 同步更新**

翻译键的类型必须与代码中的使用方式一致。

---

## 🎯 3 条核心规则（日常使用）

1. **区分对象和字符串** - 对象用 `t('key.subkey')`，字符串用 `t('key')`
2. **避免重复键** - 每个键只定义一次
3. **保持同步** - 所有语言文件有相同的键结构

---

## ⚡ 快速参考（80% 场景够用）

### 类型区分

| 类型 | JSON 定义 | 使用方式 |
|------|----------|---------|
| 对象 | `{"menu": {"home": "首页"}}` | `t('menu.home')` |
| 字符串 | `{"save": "保存"}` | `t('save')` |

### 常见错误

| 错误 | 原因 | 修复 |
|------|------|------|
| "returned an object" | 翻译键是对象，代码期望字符串 | 使用子键 `t('key.subkey')` |
| 翻译不显示 | 键不存在或路径错误 | 检查翻译文件和键路径 |
| 重复键 | JSON 中同一键定义多次 | 删除重复定义 |

### 快速检查命令

```bash
# 检查重复键
cat frontend/src/locales/zh/admin.json | grep -o '"[^"]*":' | sort | uniq -d

# 验证语言文件同步
diff <(jq -S 'keys' frontend/src/locales/zh/admin.json) \
     <(jq -S 'keys' frontend/src/locales/en/admin.json)
```

### 开发流程

**添加新键**：
1. 确定类型（对象 or 字符串）
2. 检查是否已存在
3. 在所有语言文件中添加
4. 验证无重复

**修改现有键**：
1. 搜索所有使用该键的代码
2. 同步更新所有语言文件
3. 更新代码
4. 运行测试

---

## 📚 详细规则（按需查阅）

<details>
<summary><b>规则 1: 区分对象和字符串类型</b>（点击展开）</summary>

**对象类型** - 包含子键:
```json
{
  "systemMonitoring": {
    "title": "系统监控",
    "timeRange": "时间范围"
  }
}
```
使用: `t('systemMonitoring.title')`

**字符串类型** - 直接值:
```json
{
  "save": "保存",
  "cancel": "取消"
}
```
使用: `t('save')`

</details>

<details>
<summary><b>规则 2: 避免重复翻译键</b>（点击展开）</summary>

每个翻译键在同一文件中只能定义一次。

**检查方法**:
```bash
cat frontend/src/locales/zh/admin.json | grep -o '"[^"]*":' | sort | uniq -d
```

</details>

<details>
<summary><b>规则 3: 保持语言文件同步</b>（点击展开）</summary>

所有语言文件必须有相同的键结构。

**验证**:
```bash
diff <(jq -S 'keys' frontend/src/locales/zh/admin.json) \
     <(jq -S 'keys' frontend/src/locales/en/admin.json)
```

</details>

---

## 🔗 相关资源

- **代码质量标准**：`.kiro/steering/coding-quality-standards.md`
- **前端项目结构**：`.kiro/steering/structure.md`
- [react-i18next 文档](https://react.i18next.com/)
- [i18next 最佳实践](https://www.i18next.com/principles/fallback)

---

**此规范为强制性规范。违反规范将导致 PR 被拒绝。**
