---
description: 从对话生成产品需求文档 / Create a Product Requirements Document from conversation
argument-hint: [output-filename]
---

# 创建 PRD / Create PRD: Generate Product Requirements Document

## 概述 / Overview

基于当前对话上下文和讨论的需求生成全面的产品需求文档 (PRD)。使用下面定义的结构和章节创建一个完整、专业的 PRD。

## 输出文件 / Output File

将 PRD 写入: `$ARGUMENTS` (默认: `PRD.md`)

**或者（如果使用 Kiro Spec）**: `.kiro/specs/[feature-name]/requirements.md`

## PRD 结构 / PRD Structure

创建具有以下章节的结构良好的 PRD。根据可用信息调整深度和细节：

### 必需章节 / Required Sections

**1. 执行摘要 / Executive Summary**
- 简洁的产品概述（2-3 段）
- 核心价值主张
- MVP 目标声明

**2. 使命 / Mission**
- 产品使命声明
- 核心原则（3-5 个关键原则）

**3. 目标用户 / Target Users**
- 主要用户画像
- 技术熟练程度
- 关键用户需求和痛点

**4. MVP 范围 / MVP Scope**
- **范围内 / In Scope:** MVP 的核心功能（使用 ✅ 复选框）
- **范围外 / Out of Scope:** 推迟到未来阶段的功能（使用 ❌ 复选框）
- 按类别分组（核心功能、技术、集成、部署）

**5. 用户故事 / User Stories**
- 主要用户故事（5-8 个故事），格式："作为 [用户]，我想要 [操作]，以便 [收益]"
- 为每个故事包含具体示例
- 如相关，添加技术用户故事

**使用 EARS 表示法 / Use EARS Notation:**
- WHEN [条件], THEN [预期结果]
- IF [条件], THEN [预期结果]
- WHERE [条件], THEN [预期结果]

**6. 核心架构与模式 / Core Architecture & Patterns**
- 高级架构方案
- 目录结构（如适用）
- 关键设计模式和原则
- 技术特定模式

**SuperInsight 架构参考:**
```
superinsight-platform/
├── src/                    # 后端 Python 代码
│   ├── api/               # FastAPI 路由
│   ├── models/            # SQLAlchemy 模型
│   ├── schemas/           # Pydantic 模式
│   ├── security/          # 安全和认证
│   └── ...
├── frontend/              # React TypeScript 前端
│   ├── src/components/    # UI 组件
│   ├── src/hooks/         # React Hooks
│   ├── src/services/      # API 服务
│   └── ...
└── tests/                 # 测试套件
```

**7. 工具/功能 / Tools/Features**
- 详细的功能规格
- 如果构建代理：工具设计，包括目的、操作和关键功能
- 如果构建应用：核心功能分解

**8. 技术栈 / Technology Stack**

**SuperInsight 标准技术栈:**

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | Python 3.11+ |
| 数据库 | PostgreSQL | 15+ |
| 缓存 | Redis | 7+ |
| 图数据库 | Neo4j | 5+ |
| ORM | SQLAlchemy | 2.0+ |
| 前端框架 | React | 19 |
| 构建工具 | Vite | 7+ |
| UI 库 | Ant Design | 5+ |
| 状态管理 | Zustand | - |
| 数据获取 | TanStack Query | - |
| 测试 | Pytest / Vitest | - |

**9. 安全与配置 / Security & Configuration**
- 认证/授权方案
- 配置管理（环境变量、设置）
- 安全范围（范围内和范围外）
- 部署考虑

**SuperInsight 安全要求:**
- JWT 认证
- RBAC 权限控制
- 多租户数据隔离
- 审计日志
- 数据脱敏

**10. API 规格 / API Specification** (如适用)
- 端点定义
- 请求/响应格式
- 认证要求
- 示例负载

**11. 成功标准 / Success Criteria**
- MVP 成功定义
- 功能要求（使用 ✅ 复选框）
- 质量指标
- 用户体验目标

**12. 实现阶段 / Implementation Phases**
- 分解为 3-4 个阶段
- 每个阶段包括：目标、交付物（✅ 复选框）、验证标准
- 现实的时间估计

**13. 未来考虑 / Future Considerations**
- MVP 后增强
- 集成机会
- 后续阶段的高级功能

**14. 风险与缓解 / Risks & Mitigations**
- 3-5 个关键风险及具体缓解策略

**15. 附录 / Appendix** (如适用)
- 相关文档
- 关键依赖及链接
- 仓库/项目结构

## 指令 / Instructions

### 1. 提取需求 / Extract Requirements
- 审查整个对话历史
- 识别明确需求和隐含需求
- 记录技术约束和偏好
- 捕获用户目标和成功标准

### 2. 综合信息 / Synthesize Information
- 将需求组织到适当的章节
- 在缺少细节的地方填入合理假设
- 保持章节间的一致性
- 确保技术可行性

### 3. 编写 PRD / Write the PRD
- 使用清晰、专业的语言
- 包含具体示例和细节
- 使用 markdown 格式（标题、列表、代码块、复选框）
- 在技术章节适当添加代码片段
- 保持执行摘要简洁但全面

### 4. 质量检查 / Quality Checks
- ✅ 所有必需章节都存在
- ✅ 用户故事有明确的收益
- ✅ MVP 范围现实且定义明确
- ✅ 技术选择有理由
- ✅ 实现阶段可操作
- ✅ 成功标准可衡量
- ✅ 全文术语一致

## 风格指南 / Style Guidelines

- **语气**: 专业、清晰、行动导向
- **格式**: 广泛使用 markdown（标题、列表、代码块、表格）
- **复选框**: 使用 ✅ 表示范围内项目，❌ 表示范围外
- **具体性**: 优先使用具体示例而非抽象描述
- **长度**: 全面但可扫描（通常 30-60 个章节的内容）

## 与 Kiro Spec 的集成 / Integration with Kiro Spec

如果使用 Kiro Spec 工作流，PRD 应该：

1. **保存位置**: `.kiro/specs/[feature-name]/requirements.md`
2. **遵循 Doc-First 工作流**: 参见 `.kiro/steering/doc-first-workflow.md`
3. **使用 EARS 表示法**: 用于验收标准
4. **包含正确性属性**: 用于属性基测试

**示例 Kiro Spec 结构:**
```
.kiro/specs/[feature-name]/
├── requirements.md    ← 此 PRD
├── design.md          ← 技术设计
└── tasks.md           ← 实现任务
```

## 输出确认 / Output Confirmation

创建 PRD 后：
1. 确认写入的文件路径
2. 提供 PRD 内容的简要摘要
3. 突出显示因信息缺失而做出的任何假设
4. 建议后续步骤（例如，审查、细化、规划）

## 注意事项 / Notes

- 如果缺少关键信息，在生成前询问澄清问题
- 根据可用细节调整章节深度
- 对于高度技术性的产品，强调架构和技术栈
- 对于面向用户的产品，强调用户故事和体验
- 此命令包含完整的 PRD 模板结构，无需外部引用
- 考虑与现有 SuperInsight 功能的集成点

## 参考文档 / Reference Documents

- `.kiro/steering/doc-first-workflow.md` - 文档优先工作流
- `.kiro/steering/tech.md` - 技术栈参考
- `.kiro/steering/structure.md` - 项目结构参考
- `.kiro/steering/product.md` - 产品信息
- `CLAUDE.md` - 项目配置
