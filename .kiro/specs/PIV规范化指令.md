规划与执行
命令	描述
/core_piv_loop:prime	加载项目上下文和代码库理解
/core_piv_loop:plan-feature	通过代码库分析制定全面的实施计划。
/core_piv_loop:execute	逐步执行实施计划

验证
命令	描述
/validation:validate	运行完整验证：测试、代码检查、代码覆盖率、前端构建
/validation:code-review	对已更改文件进行技术代码审查
/validation:code-review-fix	修复代码审查中发现的问题
/validation:execution-report	功能实施后生成报告
/validation:system-review	分析流程改进的实施情况与计划的差异

漏洞修复
命令	描述
/github_bug_fix:rca	为 GitHub 问题创建根本原因分析文档
/github_bug_fix:implement-fix	根据根本原因分析 (RCA) 文件实施修复

杂项
命令	描述
/commit	创建带有适当标签（feat、fix、docs 等）的原子提交
/init-project	安装依赖项，启动后端和前端服务器
/create-prd	根据对话生成产品需求文档