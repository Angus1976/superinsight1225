---
inclusion: manual
---

# TDD 工作流 (Test-Driven Development Workflow)

**Version**: 1.0
**Status**: ✅ Active
**Last Updated**: 2026-03-16
**Priority**: HIGH
**来源**: 参考 everything-claude-code tdd-workflow skill，适配本项目
**加载方式**: 手动加载（按需引用）

---

## 📌 核心原则

**RED → GREEN → REFACTOR，覆盖率目标 80%+**

---

## 🔴 RED：先写失败的测试

```python
# 1. 定义接口/行为
def test_annotation_quality_score():
    """标注质量评分应返回 0-1 之间的浮点数"""
    scorer = QualityScorer()
    result = scorer.evaluate(annotation=sample, reference=gold)
    assert 0.0 <= result.score <= 1.0
    assert result.metrics is not None
```

## 🟢 GREEN：写最少的代码让测试通过

```python
class QualityScorer:
    def evaluate(self, annotation, reference) -> QualityResult:
        score = self._calculate_similarity(annotation, reference)
        return QualityResult(score=score, metrics={"similarity": score})
```

## 🔵 REFACTOR：重构，保持测试绿色

- 消除重复代码
- 改善命名
- 提取公共方法
- 确保所有测试仍然通过

---

## 📋 本项目 TDD 实践

### 后端测试（pytest）
```bash
# 运行全部测试
pytest tests/ -v --cov=src --cov-report=term-missing

# 运行特定模块
pytest tests/test_annotation/ -v

# 只运行标记的测试
pytest -m "not slow" tests/
```

### 前端测试（Vitest + Playwright）
```bash
# 单元测试
cd frontend && npx vitest --run

# E2E 测试
cd frontend && npx playwright test
```

### 测试文件组织
```
tests/
├── conftest.py              # 共享 fixtures
├── test_annotation/         # 标注模块测试
│   ├── test_api.py          # API 端点测试
│   ├── test_service.py      # 业务逻辑测试
│   └── test_models.py       # 模型测试
├── test_quality/            # 质量评估测试
├── test_security/           # 安全模块测试
└── test_integration/        # 集成测试

frontend/src/
├── __tests__/               # 前端单元测试
└── e2e/                     # E2E 测试
```

---

## 🎯 TDD 检查清单

### 写测试前
- [ ] 明确要测试的行为（不是实现细节）
- [ ] 准备好测试数据（fixtures）
- [ ] 确定边界条件

### 写代码时
- [ ] 只写让测试通过的最少代码
- [ ] 不提前优化
- [ ] 一次只让一个测试通过

### 重构时
- [ ] 所有测试仍然通过
- [ ] 消除重复
- [ ] 改善可读性
- [ ] 检查覆盖率 >= 80%

---

## ⚠️ 测试反模式

| 反模式 | 正确做法 |
|--------|----------|
| 测试实现细节 | 测试行为和输出 |
| 测试之间有依赖 | 每个测试独立 |
| Mock 过多 | 只 Mock 外部依赖 |
| 测试名称不清晰 | `test_<行为>_when_<条件>_should_<结果>` |
| 忽略边界条件 | 空值、极大值、并发场景 |
| Playwright 中用 `Buffer.from()` | 用 `new Uint8Array(new TextEncoder().encode(...))` — Playwright 测试环境无 Node `Buffer` |
| Playwright `baseURL`/`webServer.url` 写死端口 | 用 `process.env.PLAYWRIGHT_BASE_URL` — Vite 端口被占用会自动递增导致超时 |

---

## 🔗 相关资源

- **代码质量**: `.kiro/rules/coding-quality-standards.md`
- **异步安全**: `.kiro/rules/async-sync-safety-quick-reference.md`
- **Python 模式**: `.kiro/rules/python-fastapi-patterns.md`
