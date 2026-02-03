---
inclusion: manual
---

# 代码质量标准 (Code Quality Standards)

**Version**: 2.0  
**Status**: ✅ Active  
**Last Updated**: 2026-02-04  
**Priority**: CRITICAL  
**加载方式**: 手动加载（按需引用）

---

## 📌 核心原则（必读）

**可读性 > 可维护性 > 可测试性 > 健壮性 > 性能**

---

## 🎯 10 条核心规则（日常使用）

1. **单一职责** - 函数 20-40 行，类 200-400 行
2. **卫语句** - 提前返回，减少嵌套
3. **显式优于隐式** - 不用魔法，不用可变默认值
4. **防御性编程** - 永远不信任外部输入
5. **DRY 但不过度** - 重复 3 次才抽象
6. **清晰的错误处理** - 明确的业务异常
7. **可测试性** - 依赖注入，纯函数
8. **注释写"为什么"** - 不写"做什么"
9. **删除僵尸代码** - 不注释大段代码
10. **避免魔法值** - 硬编码抽成常量

---

## ⚡ 快速参考（80% 场景够用）

### 命名规范
- **Python**: `snake_case` (函数/变量), `PascalCase` (类), `UPPER_SNAKE_CASE` (常量)
- **TypeScript**: `camelCase` (函数/变量), `PascalCase` (类/组件), `UPPER_SNAKE_CASE` (常量)

### 工具链
- **Python**: Black + Ruff + mypy + Pytest
- **TypeScript**: Prettier + ESLint + tsc + Vitest

### Code Review 检查清单
- [ ] 函数是否超过 40 行？
- [ ] 是否使用了卫语句？
- [ ] 是否有魔法值？
- [ ] 是否有可变默认值？
- [ ] 错误处理是否清晰？
- [ ] 是否有僵尸代码？
- [ ] 注释是否写了"为什么"？
- [ ] 是否易于测试？
- [ ] 命名是否清晰？
- [ ] 缩进是否超过 3 层？

---

## 📚 详细规则（按需查阅）

<details>
<summary><b>1. 单一职责原则</b>（点击展开）</summary>

### 规则
- 一个函数/类只做一件事
- 函数 20-40 行（理想 10-20 行）
- 类 200-400 行

### ❌ 错误示例
```python
def process_user_data(user_id):
    user = db.query(User).filter_by(id=user_id).first()
    if not user.email:
        raise ValueError("Email required")
    user.status = "active"
    send_email(user.email, "Welcome")
    logger.info(f"Processed {user_id}")
    return user
```

### ✅ 正确示例
```python
def get_user(user_id: int) -> User:
    return db.query(User).filter_by(id=user_id).first()

def validate_user(user: User) -> None:
    if not user.email:
        raise ValueError("Email required")

def activate_user(user: User) -> User:
    user.status = "active"
    return user

def notify_user(user: User) -> None:
    send_email(user.email, "Welcome")
    logger.info(f"Notified user {user.id}")

def process_user_data(user_id: int) -> User:
    user = get_user(user_id)
    validate_user(user)
    user = activate_user(user)
    notify_user(user)
    return user
```

</details>

<details>
<summary><b>2. 卫语句</b>（点击展开）</summary>

### 规则
- 提前返回异常/无效情况
- 核心逻辑保持最浅缩进

### ❌ 错误示例
```python
def process_order(order_id):
    order = get_order(order_id)
    if order:
        if order.status == "pending":
            if order.amount > 0:
                # 核心逻辑
                return result
```

### ✅ 正确示例
```python
def process_order(order_id):
    order = get_order(order_id)
    if not order:
        return None
    if order.status != "pending":
        return None
    if order.amount <= 0:
        return None
    
    # 核心逻辑（缩进最浅）
    return result
```

</details>

<details>
<summary><b>3. 显式优于隐式</b>（点击展开）</summary>

### 规则
- 不用可变默认值
- 返回值类型一致
- 配置从环境变量读取

### ❌ 错误示例
```python
def get_users(filters={}):  # 可变默认值！
    return db.query(User).filter_by(**filters).all() or []
```

### ✅ 正确示例
```python
def get_users(filters: Optional[Dict[str, Any]] = None) -> List[User]:
    if filters is None:
        filters = {}
    return db.query(User).filter_by(**filters).all()
```

</details>

<details>
<summary><b>4. 防御性编程</b>（点击展开）</summary>

### 规则
- 永远不信任外部输入
- 函数开头做参数校验

### ✅ 正确示例
```python
def create_user(email: str, age: int) -> User:
    if not email or "@" not in email:
        raise ValueError(f"Invalid email: {email}")
    if not isinstance(age, int) or age < 0 or age > 150:
        raise ValueError(f"Invalid age: {age}")
    
    user = User(email=email, age=age)
    db.add(user)
    db.commit()
    return user
```

</details>

<details>
<summary><b>5. DRY 但不过度抽象</b>（点击展开）</summary>

### 规则
- 重复 3 次才抽象
- 2 次可以接受
- 1 次不抽取

### 流程
1. 第一次：直接写
2. 第二次：复制粘贴 + 小改
3. 第三次：思考是否值得抽象 → 重构

</details>

<details>
<summary><b>6. 清晰的错误处理</b>（点击展开）</summary>

### 规则
- 明确的业务异常
- 在适当层级处理

### ✅ 正确示例
```python
class UserNotFoundError(Exception):
    pass

def get_user(user_id: int) -> User:
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise UserNotFoundError(f"User {user_id} not found")
    return user

@app.route("/users/<int:user_id>")
def user_detail(user_id):
    try:
        user = get_user(user_id)
        return jsonify(user.to_dict())
    except UserNotFoundError as e:
        return jsonify({"error": str(e)}), 404
```

</details>

<details>
<summary><b>7. 可测试性</b>（点击展开）</summary>

### 规则
- 依赖注入
- 纯函数
- 避免静态方法、当前时间、网络请求

### ✅ 正确示例
```python
def process_order(order: Order, current_time: datetime, email_sender: EmailSender):
    if current_time > order.deadline:
        email_sender.send(order.user.email, "Late")

# 测试时注入 mock
def test_process_order():
    order = Order(deadline=datetime(2026, 1, 1))
    current_time = datetime(2026, 1, 2)
    email_sender = MockEmailSender()
    
    process_order(order, current_time, email_sender)
    
    assert email_sender.sent_count == 1
```

</details>

<details>
<summary><b>8. 注释写"为什么"</b>（点击展开）</summary>

### 规则
- 好的代码 + 好的命名 → 注释很少
- 注释写：为什么、业务背景、权衡、坑、临时方案

### ❌ 低级注释
```python
i += 1  # i 加 1
```

### ✅ 高级注释
```python
# HACK: 临时方案，等待上游 API 修复后移除
# 原因：上游 API 返回的时间戳是秒级，但我们需要毫秒级
timestamp = int(response["timestamp"]) * 1000
```

</details>

<details>
<summary><b>9. 删除僵尸代码</b>（点击展开）</summary>

### 规则
- 删除不用的代码
- 不注释大段代码（用 git 历史）
- TODO 设定时限

### ✅ 正确示例
```python
def process_order(order_id):
    # TODO(angus, 2026-02-10): 优化性能，目标 < 100ms
    # Issue: https://github.com/company/project/issues/123
    ...
```

</details>

<details>
<summary><b>10. 其他高频规则</b>（点击展开）</summary>

| 规则 | 检查点 |
|------|--------|
| 避免魔法值 | 硬编码抽成常量 |
| 控制认知复杂度 | 用工具打分 |
| 避免过深嵌套 | 最多 3 层缩进 |
| 结构化日志 | 包含上下文信息 |
| 资源管理 | 用 with / defer |
| 幂等性设计 | 更新操作幂等 |

</details>

---

## 🔗 相关资源

- **AI 开发效率**：`.kiro/steering/ai-development-efficiency.md`
- **异步安全**：`.kiro/steering/async-sync-safety-quick-reference.md`
- **TypeScript 规范**：`.kiro/steering/typescript-export-rules.md`

---

**此规范为强制性规范。违反规范将导致 PR 被拒绝。**
