# SuperInsight Frontend

SuperInsight 前端应用，基于 React + TypeScript + Vite 构建。

## 国际化 (i18n)

SuperInsight 支持多语言界面，目前支持以下语言：

- **中文 (zh)** - 默认语言
- **English (en)**

### 语言切换

用户可以通过界面右上角的语言切换器切换语言。语言偏好会自动保存到 localStorage，下次访问时自动恢复。

### 开发指南

在开发新功能时，请确保所有用户可见文本都使用翻译函数 `t()`：

```typescript
import { useTranslation } from 'react-i18next';

const MyComponent = () => {
  const { t } = useTranslation('tasks');
  return <h1>{t('title')}</h1>;
};
```

### 翻译文件结构

翻译文件按命名空间组织，位于 `src/locales/` 目录：

| 命名空间 | 用途 |
|---------|------|
| `common` | 通用文本、菜单、操作按钮 |
| `auth` | 登录、注册、密码重置 |
| `tasks` | 任务管理、标注、审核 |
| `billing` | 账单、工时、计费规则 |
| `quality` | 质量管理、改进任务 |
| `security` | 权限、角色、审计 |
| `admin` | 管理控制台 |

📖 **详细文档**: 请参阅 [国际化开发指南](./docs/i18n-guidelines.md) 获取完整的开发规范和最佳实践。

---

## 技术栈

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
