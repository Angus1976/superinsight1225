# 需求文档：AI 智能助手配置方式重构

## 简介

重构 AI 智能助手页面的数据源配置交互方式。将当前位于聊天区域顶部工具栏的数据源选择 Popover 移至右侧边栏底部，并拆分为三个独立的配置入口（配置数据源、配置权限表、输出方式），由管理员统一管理数据源可用性和角色访问权限，普通用户仅可在授权范围内选择数据源和输出方式。

## 术语表

- **AI_Assistant_Page**: AI 智能助手页面（`/ai-assistant`），包含左侧聊天区域和右侧边栏
- **Chat_Area**: 聊天区域，页面左侧 `Col span=16` 区域，包含消息列表和输入框
- **Right_Sidebar**: 右侧边栏，页面右侧 `Col span=8` 区域，包含技能面板、统计和提示
- **Config_Panel**: 配置面板区域，位于 Right_Sidebar 底部，包含三个配置按钮
- **Data_Source**: AI 可访问的数据源（如标注任务、标注效率、用户活跃度等），定义于 `DATA_SOURCE_REGISTRY`
- **Data_Source_Config_Modal**: 配置数据源弹窗，管理员用于启用/禁用数据源
- **Permission_Table_Modal**: 配置权限表弹窗，管理员用于配置角色与数据源的访问映射
- **Output_Mode_Modal**: 输出方式弹窗，用于选择合并输出或对比输出
- **Admin_User**: 角色为 `admin` 的用户，拥有数据源和权限配置权限
- **Regular_User**: 非管理员角色用户（business_expert、annotator、viewer）
- **Output_Mode**: 输出方式，包括 `merge`（合并遍历后一并输出）和 `compare`（分组对比输出）
- **Role_Permission_Mapping**: 角色权限映射表，定义哪些角色可以访问哪些数据源

## 需求

### 需求 1：移除聊天区域数据源工具栏

**用户故事：** 作为用户，我希望聊天区域更简洁，数据源配置不再占用聊天区域空间，以便获得更好的对话体验。

#### 验收标准

1. WHEN AI_Assistant_Page 加载完成, THE Chat_Area SHALL 不再显示数据源选择 Popover 按钮和输出模式 Segmented 控件
2. THE Chat_Area SHALL 仅保留消息列表、输入框和快捷操作区域

### 需求 2：右侧边栏底部配置面板

**用户故事：** 作为用户，我希望在右侧边栏底部看到配置入口，以便快速访问数据源、权限和输出方式的配置。

#### 验收标准

1. THE Config_Panel SHALL 固定显示在 Right_Sidebar 的底部区域
2. THE Config_Panel SHALL 包含三个按钮：「配置数据源」、「配置权限表」、「输出方式」
3. WHILE Admin_User 登录时, THE Config_Panel SHALL 显示全部三个按钮
4. WHILE Regular_User 登录时, THE Config_Panel SHALL 仅显示「输出方式」按钮
5. THE Config_Panel 中的所有按钮文本 SHALL 使用 i18n 的 `t()` 函数包裹

### 需求 3：管理员配置数据源

**用户故事：** 作为管理员，我希望在 AI 助手页面直接配置可用数据源列表，以便控制 AI 助手可以访问哪些数据。

#### 验收标准

1. WHEN Admin_User 点击「配置数据源」按钮, THE Data_Source_Config_Modal SHALL 以弹窗形式展示所有已注册的 Data_Source 列表
2. THE Data_Source_Config_Modal SHALL 为每个 Data_Source 提供启用/禁用开关
3. THE Data_Source_Config_Modal SHALL 为每个 Data_Source 提供访问模式选择（只读/读写）
4. WHEN Admin_User 保存配置, THE Data_Source_Config_Modal SHALL 调用 `POST /api/v1/ai-assistant/data-sources/config` 接口持久化配置
5. IF 保存失败, THEN THE Data_Source_Config_Modal SHALL 显示错误提示信息
6. THE Data_Source_Config_Modal 中的所有文本 SHALL 使用 i18n 的 `t()` 函数包裹

### 需求 4：管理员配置角色权限表

**用户故事：** 作为管理员，我希望配置不同角色可以访问哪些数据源，以便实现细粒度的数据访问控制。

#### 验收标准

1. WHEN Admin_User 点击「配置权限表」按钮, THE Permission_Table_Modal SHALL 以弹窗形式展示角色与数据源的权限映射矩阵
2. THE Permission_Table_Modal SHALL 以表格形式展示：行为角色（admin、business_expert、annotator、viewer），列为已启用的 Data_Source
3. THE Permission_Table_Modal SHALL 为每个角色-数据源组合提供勾选框，表示该角色是否可访问该数据源
4. WHEN Admin_User 保存权限配置, THE Permission_Table_Modal SHALL 调用后端接口持久化角色权限映射
5. IF 保存失败, THEN THE Permission_Table_Modal SHALL 显示错误提示信息
6. THE Permission_Table_Modal 中的所有文本 SHALL 使用 i18n 的 `t()` 函数包裹

### 需求 5：用户选择可用数据源和输出方式

**用户故事：** 作为用户，我希望在配置面板中选择可用的数据源并设置输出方式，以便 AI 助手根据我的选择提供针对性的分析。

#### 验收标准

1. WHEN 用户点击「输出方式」按钮, THE Output_Mode_Modal SHALL 以弹窗形式展示数据源多选列表和输出方式选择
2. THE Output_Mode_Modal SHALL 仅展示当前用户角色有权访问且已启用的 Data_Source 列表
3. THE Output_Mode_Modal SHALL 允许用户多选可用的 Data_Source
4. THE Output_Mode_Modal SHALL 提供两种输出方式选择：合并输出（merge）和对比输出（compare）
5. WHEN 合并输出被选择, THE AI_Assistant_Page SHALL 在对话时遍历所有选中数据源后一并输出分析结果
6. WHEN 对比输出被选择, THE AI_Assistant_Page SHALL 在对话时分别对各数据源进行分析并对比输出
7. THE Output_Mode_Modal 中的所有文本 SHALL 使用 i18n 的 `t()` 函数包裹

### 需求 6：后端角色权限映射接口

**用户故事：** 作为管理员，我希望后端提供角色权限映射的存储和查询接口，以便前端权限表配置能够持久化。

#### 验收标准

1. THE 后端 SHALL 提供 `GET /api/v1/ai-assistant/data-sources/role-permissions` 接口，返回所有角色与数据源的权限映射
2. THE 后端 SHALL 提供 `POST /api/v1/ai-assistant/data-sources/role-permissions` 接口，供管理员更新角色权限映射
3. WHEN Regular_User 调用 `GET /api/v1/ai-assistant/data-sources/available` 接口, THE 后端 SHALL 根据用户角色过滤，仅返回该角色有权访问且已启用的数据源
4. IF 非管理员用户调用权限配置接口, THEN THE 后端 SHALL 返回 403 状态码
5. THE 后端 SHALL 新增 `ai_data_source_role_permission` 数据库表存储角色权限映射

### 需求 7：国际化支持

**用户故事：** 作为用户，我希望所有新增的配置界面文本都支持中英文切换，以便不同语言偏好的用户都能正常使用。

#### 验收标准

1. THE AI_Assistant_Page SHALL 将所有新增的用户可见文本添加到 `frontend/src/locales/zh/aiAssistant.json` 和 `frontend/src/locales/en/aiAssistant.json`
2. THE AI_Assistant_Page SHALL 使用 `useTranslation('aiAssistant')` 命名空间获取翻译函数
3. THE AI_Assistant_Page SHALL 在 HTML/组件属性中使用 `title={t('key')}` 格式，在 JSX 子元素中使用 `{t('key')}` 格式
4. THE AI_Assistant_Page SHALL 为角色名称（admin、business_expert、annotator、viewer）提供中英文翻译
