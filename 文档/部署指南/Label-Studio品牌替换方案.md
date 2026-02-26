# Label Studio 品牌替换方案

**最后更新**: 2026-02-26  
**品牌名**: 问视间  
**适用版本**: Label Studio latest (heartexlabs/label-studio:latest)

---

## 概述

将 Label Studio 的品牌（Logo、标题、UI 文本）替换为"问视间"，同时提供中文翻译。方案在容器启动时通过 entrypoint 脚本注入，不修改 LS 源码，升级时只需重建容器。

## 文件清单

| 文件 | 作用 | 升级影响 |
|------|------|----------|
| `deploy/label-studio/branding.css` | CSS 隐藏 SVG logo + 注入品牌文字 + 隐藏外部链接 | 低 |
| `deploy/label-studio/i18n-inject.js` | JS 文本节点翻译 + MutationObserver 动态替换 | 低 |
| `deploy/label-studio/entrypoint-sso.sh` | 容器启动时注入 CSS/JS 到模板 + sed 替换 HTML 中的文本 | 中 |
| `deploy/label-studio/Dockerfile` | 构建镜像，COPY 自定义文件到 `/label-studio/custom/` | 低 |

## 替换策略

### 1. SVG Logo 替换（CSS）

Logo 位于侧边栏 `div.lsf-menu-header__trigger` 内，是一个 `<svg viewBox="0 0 194 30">` 元素。

```css
/* 隐藏 SVG */
svg[alt*="Label Studio" i],
svg[viewBox="0 0 194 30"] { display: none !important; }

/* 注入品牌文字 */
.lsf-menu-header__trigger::before {
  content: "问视间" !important;
  font-size: 20px; font-weight: 700;
  color: var(--ls-brand-primary, #1890ff);
}
```

升级检查点：如果 LS 更改了 SVG 的 `viewBox` 尺寸或父容器类名，需要更新选择器。

### 2. HTML 模板文本替换（entrypoint sed）

在 entrypoint 中用 `find + sed` 替换所有 HTML 模板中的 "Label Studio"：

```bash
find /label-studio/label_studio -name "*.html" -exec \
    sed -i 's|Label Studio|问视间|g' {} \;
```

这会替换 `<title>`、静态文本等。只在首次启动时执行（通过 marker 标记）。

### 3. React SPA 动态内容替换（JS）

React 渲染的内容通过 `i18n-inject.js` 处理：
- TreeWalker 遍历所有文本节点，匹配翻译词典
- MutationObserver 监听 DOM 变化，实时翻译新渲染的内容
- `replaceBrand()` 专门处理 SVG logo 隐藏（JS 兜底）

### 4. 外部链接隐藏（CSS + JS）

基于 `href` 属性隐藏 HumanSignal 相关链接：

```css
a[href*="labelstud.io"],
a[href*="humansignal"],
a[href*="github.com/HumanSignal"] { display: none !important; }
```

### 5. 静态文件部署路径

entrypoint 将自定义文件复制到两个目录：
- `/label-studio/label_studio/core/static/` — Django 源静态目录
- `/label-studio/label_studio/core/static_build/` — Django collectstatic 输出目录（实际服务目录）

## LS 升级检查清单

升级 Label Studio 版本后，按以下顺序检查：

1. **容器能否正常启动？**
   - `docker compose build --no-cache label-studio && docker compose up -d label-studio`
   - 查看日志：`docker logs superinsight-label-studio`

2. **模板路径是否变化？**
   - base.html 预期位置：`/label-studio/label_studio/templates/base.html`
   - 如果路径变了，更新 `entrypoint-sso.sh` 中的 `LS_TEMPLATE_DIR`

3. **静态文件目录是否变化？**
   - 预期：`/label-studio/label_studio/core/static/` 和 `static_build/`
   - 验证：`curl http://localhost:8080/static/branding.css` 应返回 200

4. **SVG Logo 结构是否变化？**
   - 打开浏览器 DevTools 检查侧边栏 logo 元素
   - 确认 `viewBox="0 0 194 30"` 是否仍然匹配
   - 确认父容器是否仍是 `.lsf-menu-header__trigger`
   - 如有变化，更新 `branding.css` 中的选择器

5. **React bundle 路径是否变化？**
   - 当前从 `/react-app/main.js` 加载
   - JS 翻译不依赖 bundle 路径，无需修改

6. **Python 版本是否变化？**
   - SSO patch 依赖 `/label-studio/.venv/lib/python3.13/`
   - 如果 Python 版本升级，更新 `entrypoint-sso.sh` 中的路径

## 已知限制

- **不能 sed 替换 React bundle**：压缩的 JS 文件中 "Label Studio"(12字节) 替换为 "问视间"(9字节) 会改变文件大小，破坏 source map 和可能的完整性校验，导致 LS 启动失败
- **SVG Logo 是路径图形**：HeartexLogo 是 SVG path 绘制的，不是文字，只能隐藏不能修改
- **CSS 类名依赖**：`.lsf-menu-header__trigger` 是 LS 内部类名，升级可能变化

## 快速调试

```bash
# 查看容器日志
docker logs superinsight-label-studio 2>&1 | grep -E "(patch|brand|i18n|ERROR)"

# 验证静态文件
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/static/branding.css
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/static/i18n-inject.js

# 验证 HTML 注入
curl -s -L http://localhost:8080/ | grep -E "(branding\.css|i18n-inject|问视间)"

# 进入容器调试
docker exec -it superinsight-label-studio bash
```
