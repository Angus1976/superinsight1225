---
inclusion: manual
---

# Kiro 自动确认配置指南

**类型**: 工具指南  
**优先级**: INFO  
**加载方式**: 手动加载（按需引用）

---

## 快速配置（推荐）

### 方法 1：配置 Trusted Commands

1. 打开 Settings (`Cmd + ,`)
2. 搜索 "Trusted Commands"
3. 添加常用命令前缀

**推荐命令前缀**：
```
python pytest npm npx pip git
cat ls mkdir touch echo cd pwd
grep find docker docker-compose
alembic black isort prettier eslint vitest
```

### 方法 2：使用 "Run and Trust"

- 点击 "Run and Trust" 而不是 "Run"
- 该命令前缀会自动添加到信任列表

---

## 其他方法

### MCP 工具自动批准

在 `.kiro/settings/mcp.json` 中：

```json
{
  "mcpServers": {
    "server-name": {
      "autoApprove": ["tool_name1", "tool_name2"]
    }
  }
}
```

### CLI 模式

```bash
/tools trust-all  # ⚠️ 仅在受信任环境使用
```

---

## 注意事项

**Kiro 不支持"自动确认 N 次后暂停"功能**

设计理念：
- 要么信任某类命令（自动执行）
- 要么不信任（每次确认）

**替代方案**：
1. 配置 Trusted Commands 后大部分操作自动执行
2. 只有未信任的命令需要手动确认
3. 通过 "Run and Trust" 逐步扩展信任列表

---

## 快速配置步骤

1. `Cmd + ,` 打开设置
2. 搜索 "Trusted Commands"
3. 添加常用命令前缀
4. 切换到 Autopilot 模式
5. 遇到新命令时选择 "Run and Trust"
