# Label Studio iframe 无缝集成 - 需求文档

## 介绍

Label Studio iframe 无缝集成功能旨在将 Label Studio 标注界面无缝嵌入到 SuperInsight 前端管理系统中，实现标注与管理的统一体验。通过 iframe 和 PostMessage 通信机制，实现前后端的完整集成，支持权限控制、实时同步和用户体验优化。

## 术语表

- **Label_Studio_Iframe**: 嵌入的 Label Studio 标注界面容器
- **PostMessage_Bridge**: iframe 与主窗口的通信桥梁
- **Annotation_Context**: 标注上下文信息（项目、任务、用户）
- **Sync_Manager**: 数据同步管理器
- **Permission_Controller**: 权限控制器
- **UI_Coordinator**: UI 协调器，管理 iframe 与主窗口的交互
- **Event_Emitter**: 事件发射器，处理标注事件
- **Data_Transformer**: 数据转换器，处理数据格式转换

## 需求

### 需求 1: iframe 容器和生命周期管理

**用户故事:** 作为前端开发者，我希望能够灵活地管理 Label Studio iframe 的生命周期，以便实现高效的资源管理和错误恢复。

#### 验收标准

1. THE Label_Studio_Iframe SHALL 支持动态创建和销毁
2. WHEN iframe 加载时，THE Label_Studio_Iframe SHALL 显示加载进度条
3. WHEN iframe 加载失败时，THE Label_Studio_Iframe SHALL 显示错误提示和重试按钮
4. THE Label_Studio_Iframe SHALL 支持刷新和重新加载功能
5. WHEN 用户离开标注页面时，THE Label_Studio_Iframe SHALL 自动清理资源

### 需求 2: PostMessage 通信机制

**用户故事:** 作为系统架构师，我希望建立安全可靠的 iframe 与主窗口通信机制，以便实现数据同步和事件处理。

#### 验收标准

1. THE PostMessage_Bridge SHALL 支持双向通信（主窗口 ↔ iframe）
2. WHEN 主窗口发送消息时，THE PostMessage_Bridge SHALL 验证消息来源和格式
3. THE PostMessage_Bridge SHALL 支持消息队列和重试机制
4. WHEN 通信失败时，THE PostMessage_Bridge SHALL 记录错误日志并触发错误处理
5. THE PostMessage_Bridge SHALL 支持超时控制和连接状态监控

### 需求 3: 权限和上下文传递

**用户故事:** 作为安全管理员，我希望能够安全地将用户权限和上下文信息传递给 iframe，以便确保标注操作的安全性和合规性。

#### 验收标准

1. THE Annotation_Context SHALL 包含用户信息、项目信息、任务信息和权限信息
2. WHEN iframe 加载时，THE Annotation_Context SHALL 通过 PostMessage 传递给 iframe
3. THE Permission_Controller SHALL 验证用户权限并限制标注操作
4. WHEN 用户权限变更时，THE Permission_Controller SHALL 实时更新 iframe 中的权限
5. THE Annotation_Context SHALL 支持加密传输和签名验证

### 需求 4: 标注数据同步

**用户故事:** 作为数据管理员，我希望能够实时同步标注数据，以便确保数据的一致性和完整性。

#### 验收标准

1. WHEN 用户在 iframe 中完成标注时，THE Sync_Manager SHALL 自动保存标注数据
2. THE Sync_Manager SHALL 支持增量同步和全量同步两种模式
3. WHEN 网络连接中断时，THE Sync_Manager SHALL 缓存标注数据并在恢复后同步
4. THE Sync_Manager SHALL 支持冲突检测和解决机制
5. WHEN 标注数据同步完成时，THE Sync_Manager SHALL 触发相应的事件通知

### 需求 5: 事件处理和回调

**用户故事:** 作为前端开发者，我希望能够监听和处理标注事件，以便实现自定义的业务逻辑。

#### 验收标准

1. THE Event_Emitter SHALL 支持标注开始、进行中、完成等事件
2. THE Event_Emitter SHALL 支持事件监听和取消监听
3. WHEN 标注事件发生时，THE Event_Emitter SHALL 触发相应的回调函数
4. THE Event_Emitter SHALL 支持事件优先级和事件链
5. THE Event_Emitter SHALL 提供事件历史记录和调试工具

### 需求 6: UI 协调和交互

**用户故事:** 作为用户体验设计师，我希望能够协调 iframe 与主窗口的 UI 交互，以便提供流畅的用户体验。

#### 验收标准

1. THE UI_Coordinator SHALL 支持 iframe 全屏和窗口模式切换
2. WHEN 用户调整窗口大小时，THE UI_Coordinator SHALL 自动调整 iframe 大小
3. THE UI_Coordinator SHALL 支持快捷键传递和事件冒泡控制
4. WHEN iframe 获得焦点时，THE UI_Coordinator SHALL 隐藏主窗口的导航栏
5. THE UI_Coordinator SHALL 支持拖拽和缩放操作

### 需求 7: 数据格式转换和验证

**用户故事:** 作为数据工程师，我希望能够灵活地转换和验证标注数据格式，以便支持多种标注类型和数据源。

#### 验收标准

1. THE Data_Transformer SHALL 支持 JSON、CSV、XML 等多种数据格式
2. THE Data_Transformer SHALL 支持自定义转换规则和映射
3. WHEN 数据格式不匹配时，THE Data_Transformer SHALL 自动进行格式转换
4. THE Data_Transformer SHALL 验证转换后的数据完整性和正确性
5. THE Data_Transformer SHALL 提供转换日志和错误报告

### 需求 8: 错误处理和恢复

**用户故事:** 作为系统管理员，我希望能够处理 iframe 集成中的各种错误，以便确保系统的稳定性和可靠性。

#### 验收标准

1. THE Label_Studio_Iframe SHALL 支持自动重连和故障转移
2. WHEN iframe 崩溃时，THE Label_Studio_Iframe SHALL 自动重新加载
3. THE Label_Studio_Iframe SHALL 记录详细的错误日志和堆栈跟踪
4. WHEN 发生严重错误时，THE Label_Studio_Iframe SHALL 触发告警通知
5. THE Label_Studio_Iframe SHALL 支持手动恢复和回滚操作

### 需求 9: 性能优化和监控

**用户故事:** 作为性能工程师，我希望能够优化 iframe 的加载性能和运行效率，以便提供更好的用户体验。

#### 验收标准

1. THE Label_Studio_Iframe SHALL 支持懒加载和预加载
2. THE Label_Studio_Iframe SHALL 监控加载时间、内存占用和 CPU 使用率
3. WHEN 性能指标超过阈值时，THE Label_Studio_Iframe SHALL 触发性能告警
4. THE Label_Studio_Iframe SHALL 支持性能分析和优化建议
5. THE Label_Studio_Iframe SHALL 提供性能报表和趋势分析

### 需求 10: 安全性和隐私保护

**用户故事:** 作为安全管理员，我希望能够确保 iframe 集成的安全性和隐私保护，以便防止数据泄露和恶意攻击。

#### 验收标准

1. THE Label_Studio_Iframe SHALL 支持 CSP（内容安全策略）和 CORS 配置
2. THE Label_Studio_Iframe SHALL 对敏感数据进行加密和脱敏处理
3. WHEN 检测到安全威胁时，THE Label_Studio_Iframe SHALL 立即中断操作并记录事件
4. THE Label_Studio_Iframe SHALL 支持审计日志和合规性检查
5. THE Label_Studio_Iframe SHALL 定期进行安全扫描和漏洞修复
