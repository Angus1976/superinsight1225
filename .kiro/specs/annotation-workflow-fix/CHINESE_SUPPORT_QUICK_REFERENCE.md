# Label Studio 中文支持 - 快速参考

**版本**: 1.0  
**日期**: 2026-01-26  
**状态**: ✅ 推荐方案

---

## 核心原则

✅ **不修改 Label Studio 源码**  
✅ **可随时升级官方版本**  
✅ **完全友好的中文支持**  
✅ **分层优化策略**

---

## 快速实施（5 分钟）

### 1. 更新 docker-compose.yml

```yaml
label-studio:
  image: heartexlabs/label-studio:latest
  environment:
    - LANGUAGE_CODE=zh-hans              # Django 默认语言
    - LABEL_STUDIO_DEFAULT_LANGUAGE=zh   # Label Studio 配置
    - LABEL_STUDIO_LANGUAGES=zh-hans,en  # 支持的语言
```

### 2. 更新前端组件

```typescript
// frontend/src/components/LabelStudio/LabelStudioEmbed.tsx

const getLabelStudioUrl = () => {
  const params = new URLSearchParams();
  params.append('token', token);
  params.append('task', taskId);
  params.append('lang', language === 'zh' ? 'zh-hans' : 'en');  // 添加语言参数
  
  return `${baseUrl}/projects/${projectId}/data?${params.toString()}`;
};
```

### 3. 重启服务

```bash
docker-compose restart label-studio
```

### 4. 验证

访问 http://localhost:8080?lang=zh 应该看到中文界面。

---

## 分层架构

```
Layer 4: SuperInsight 集成层
         ↓ (URL 参数: ?lang=zh)
Layer 2: Label Studio React 前端 (i18next)
         ↓
Layer 1: Label Studio Django 后端 (Django i18n)
         ↓
Layer 3: 自定义翻译覆盖 (可选)
```

---

## 语言切换方式

### 方式 1: URL 参数（推荐）

```
http://localhost:8080/projects/1?lang=zh      # 中文
http://localhost:8080/projects/1?lang=en      # 英文
```

### 方式 2: 环境变量（默认语言）

```yaml
environment:
  - LANGUAGE_CODE=zh-hans  # 默认中文
```

### 方式 3: Accept-Language Header

```bash
curl -H "Accept-Language: zh-CN,zh;q=0.9" http://localhost:8080/
```

---

## 常见问题

### Q: 需要下载中文语言包吗？

**A**: ❌ 不需要。Label Studio 内置中文支持（基于 Django 和 i18next）。

### Q: 会影响升级吗？

**A**: ❌ 不会。完全通过配置实现，不修改源码，可随时升级。

### Q: 翻译质量如何？

**A**: 官方翻译基于 Google Translate，质量可接受。如需专业翻译，可使用 Layer 3 自定义覆盖。

### Q: 如何自定义翻译？

**A**: 参考 CHINESE_SUPPORT_OPTIMIZATION.md - Layer 3 部分。

---

## 测试清单

- [ ] 默认语言是中文
- [ ] URL 参数 `?lang=zh` 显示中文
- [ ] URL 参数 `?lang=en` 显示英文
- [ ] SuperInsight 语言切换同步到 Label Studio
- [ ] 刷新页面后语言保持

---

## 相关文档

- **详细方案**: CHINESE_SUPPORT_OPTIMIZATION.md
- **实施任务**: tasks.md - Phase 5
- **研究报告**: LABEL_STUDIO_I18N_RESEARCH.md
- **第三方评估**: THIRD_PARTY_I18N_EVALUATION.md

---

## 技术支持

如有问题，请参考：
1. CHINESE_SUPPORT_OPTIMIZATION.md - 完整技术方案
2. Label Studio 官方文档: https://labelstud.io/
3. Django i18n 文档: https://docs.djangoproject.com/en/stable/topics/i18n/

---

**维护者**: SuperInsight 开发团队  
**最后更新**: 2026-01-26
