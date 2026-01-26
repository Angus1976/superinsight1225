# 第三方 i18n Fork 决策总结

**日期**: 2026-01-26  
**问题**: 是否使用 https://github.com/Keekuun/label-studio-i18n  
**决策**: ❌ 不使用，继续使用官方 Label Studio

---

## 快速结论

**不使用第三方 fork，原因如下**:

1. ✅ **官方已支持** - Label Studio 官方通过 PR #2421 已经添加了完整的中英文 i18n 支持
2. ✅ **符合要求** - 用户要求"尽量不改开源 Label Studio 的源码（未来会升级）"
3. ✅ **更安全** - 官方版本更稳定，有持续维护和支持
4. ✅ **可升级** - 不会被锁定在旧版本，可以随时升级

---

## 详细对比

| 维度 | 官方 Label Studio | 第三方 Fork |
|------|------------------|------------|
| **i18n 支持** | ✅ 内置支持（PR #2421） | ✅ 支持 |
| **中文翻译** | ✅ 有（Google Translate） | ✅ 有 |
| **修改源码** | ❌ 不需要 | ✅ 使用修改版 |
| **可升级性** | ✅ 随时升级 | ❌ 升级困难 |
| **维护支持** | ✅ 官方维护 | ⚠️ 依赖第三方 |
| **安全更新** | ✅ 及时 | ⚠️ 可能延迟 |
| **社区支持** | ✅ 活跃 | ⚠️ 有限 |
| **兼容性** | ✅ 官方 API | ⚠️ 可能不兼容 |

---

## 实施方案

### 使用官方 Label Studio + 配置

```yaml
# docker-compose.yml
label-studio:
  image: heartexlabs/label-studio:latest  # 官方镜像
  environment:
    - LANGUAGE_CODE=zh-hans  # 设置默认中文
    - LABEL_STUDIO_DEFAULT_LANGUAGE=zh
```

```typescript
// frontend/src/components/LabelStudio/LabelStudioEmbed.tsx
const url = `${baseUrl}/projects/${projectId}?token=${token}&lang=${language}`;
// language: 'zh' 或 'en'
```

---

## 关键证据

### 官方 PR #2421

- **标题**: "I18n label-studio-frontend based on #1409"
- **内容**: "Chinese added by google translate"
- **状态**: ✅ 已合并
- **链接**: https://github.com/heartexlabs/label-studio/pull/2421

这证明官方已经实现了完整的 i18n 支持，包括中文翻译。

---

## 风险评估

### 使用官方方案的风险: 低 ✅

- 中文翻译质量可能不完美（可以自定义）
- 官方 i18n 功能已经成熟稳定

### 使用第三方 Fork 的风险: 高 ⚠️

- Fork 可能停止维护
- 无法升级到官方新版本
- 可能与官方 API 不兼容
- 安全漏洞无法及时修复

---

## 相关文档

- **详细评估**: `THIRD_PARTY_I18N_EVALUATION.md`
- **i18n 研究**: `LABEL_STUDIO_I18N_RESEARCH.md`
- **实施计划**: `tasks.md` - Phase 5

---

## 下一步行动

- [x] 评估第三方 fork
- [x] 确认使用官方方案
- [ ] 更新 docker-compose.yml
- [ ] 更新前端代码
- [ ] 测试语言切换功能

---

**决策人**: Kiro AI Assistant  
**批准**: 待用户确认  
**状态**: ✅ 推荐使用官方方案
