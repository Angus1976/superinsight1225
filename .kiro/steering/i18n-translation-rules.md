# i18n 翻译规范

**Version**: 2.0  
**Last Updated**: 2026-02-03  
**Priority**: HIGH

## 核心原则

翻译键的类型必须与代码中的使用方式一致。

## 关键规则

### 规则 1: 区分对象和字符串类型

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

### 规则 2: 避免重复翻译键

每个翻译键在同一文件中只能定义一次。

**检查方法**:
```bash
cat frontend/src/locales/zh/admin.json | grep -o '"[^"]*":' | sort | uniq -d
```

### 规则 3: 保持语言文件同步

所有语言文件必须有相同的键结构。

**验证**:
```bash
diff <(jq -S 'keys' frontend/src/locales/zh/admin.json) \
     <(jq -S 'keys' frontend/src/locales/en/admin.json)
```

## 常见错误

| 错误 | 原因 | 修复 |
|------|------|------|
| "returned an object instead of string" | 翻译键是对象，代码期望字符串 | 使用子键路径 `t('key.subkey')` |
| 翻译不显示 | 键不存在或路径错误 | 检查翻译文件和键路径 |
| 重复键 | JSON 中同一键定义多次 | 删除重复定义 |

## 开发流程

### 添加新翻译键
1. 确定键的类型（对象 or 字符串）
2. 检查是否已存在
3. 在所有语言文件中添加
4. 验证无重复

### 修改现有翻译键
1. 搜索所有使用该键的代码
2. 同步更新所有语言文件
3. 更新所有使用该键的代码
4. 运行测试验证

## 参考

- [react-i18next 文档](https://react.i18next.com/)
- [i18next 最佳实践](https://www.i18next.com/principles/fallback)

---

**此规范为强制性规范。违反规范将导致 PR 被拒绝。**
