# Kiro 自动确认配置指南

## 直接实现自动确认的方法

### 方法 1：配置 Trusted Commands（推荐）

在 Kiro IDE 中：

1. 打开 **Settings**（`Cmd + ,`）
2. 搜索 **"Trusted Commands"**
3. 添加你想要自动执行的命令前缀

**推荐添加的命令前缀**：
```
python
pytest
npm
npx
pip
git
cat
ls
mkdir
touch
echo
cd
pwd
head
tail
grep
find
docker
docker-compose
alembic
black
isort
prettier
eslint
vitest
```

### 方法 2：使用 "Run and Trust" 按钮

当 Kiro 提示确认命令时：
- 点击 **"Run and Trust"** 而不是 "Run"
- 该命令前缀会被自动添加到信任列表
- 以后相同前缀的命令会自动执行

### 方法 3：MCP 工具自动批准

在 `.kiro/settings/mcp.json` 中配置 `autoApprove`：

```json
{
  "mcpServers": {
    "server-name": {
      "autoApprove": ["tool_name1", "tool_name2"]
    }
  }
}
```

### 方法 4：CLI 模式 - trust-all

如果使用 Kiro CLI，可以使用：
```bash
/tools trust-all
```

⚠️ **警告**：这会信任所有工具，仅在受信任的环境中使用。

---

## 关于 "N 次后暂停" 的功能

**目前 Kiro 不支持设置"自动确认 N 次后暂停"的功能。**

Kiro 的设计理念是：
- 要么信任某类命令（自动执行）
- 要么不信任（每次确认）

**替代方案**：
1. 配置好 Trusted Commands 后，大部分操作会自动执行
2. 只有未信任的命令才需要手动确认
3. 通过 "Run and Trust" 逐步扩展信任列表

---

## 快速配置步骤

1. `Cmd + ,` 打开设置
2. 搜索 "Trusted Commands"
3. 添加常用命令前缀
4. 切换到 Autopilot 模式
5. 开始开发，遇到新命令时选择 "Run and Trust"
