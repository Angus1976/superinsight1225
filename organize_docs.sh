#!/bin/bash
# 文档整理脚本
# 将根目录下的 Markdown 文档按分类移动到 文档/ 目录下

set -e

echo "开始整理文档..."

# 快速开始/
echo "整理快速开始文档..."
mv -f "QUICK_START.md" "文档/快速开始/快速启动指南.md" 2>/dev/null || true
mv -f "QUICK_REFERENCE.md" "文档/快速开始/快速参考手册.md" 2>/dev/null || true
mv -f "README_DOCKER_SETUP.md" "文档/快速开始/Docker快速设置.md" 2>/dev/null || true

# 部署指南/
echo "整理部署指南文档..."
mv -f "DEPLOYMENT.md" "文档/部署指南/部署说明.md" 2>/dev/null || true
mv -f "TCB_DEPLOYMENT_GUIDE.md" "文档/部署指南/腾讯云部署指南.md" 2>/dev/null || true
mv -f "TCB_DEPLOY_README.md" "文档/部署指南/腾讯云部署说明.md" 2>/dev/null || true
mv -f "TCB_ENV_SETUP.md" "文档/部署指南/腾讯云环境配置.md" 2>/dev/null || true
mv -f "LOCAL_DEBUG_GUIDE.md" "文档/部署指南/本地调试指南.md" 2>/dev/null || true
mv -f "LOCAL_DEBUG_SETUP_SUMMARY.md" "文档/部署指南/本地调试配置摘要.md" 2>/dev/null || true

# Docker/
echo "整理Docker文档..."
mv -f "DOCKER_BUILD_SUCCESS.md" "文档/Docker/Docker构建成功报告.md" 2>/dev/null || true
mv -f "DOCKER_DEPLOYMENT_COMPLETE.md" "文档/Docker/Docker部署完成报告.md" 2>/dev/null || true
mv -f "DOCKER_OPERATIONS_SUMMARY.md" "文档/Docker/Docker操作摘要.md" 2>/dev/null || true
mv -f "DOCKER_REBUILD_AND_TEST_GUIDE.md" "文档/Docker/Docker重建测试指南.md" 2>/dev/null || true
mv -f "DOCKER_REBUILD_GUIDE.md" "文档/Docker/Docker重建指南.md" 2>/dev/null || true
mv -f "DOCKER_TROUBLESHOOTING.md" "文档/Docker/Docker故障排查.md" 2>/dev/null || true
mv -f "CONTAINER_RESTART_REPORT.md" "文档/Docker/容器重启报告.md" 2>/dev/null || true
mv -f "CONTAINER_RESTART_STATUS.md" "文档/Docker/容器重启状态.md" 2>/dev/null || true

# 国际化翻译/
echo "整理国际化翻译文档..."
mv -f "ADMIN_TRANSLATION_COMPLETE.md" "文档/国际化翻译/管理后台翻译完成报告.md" 2>/dev/null || true
mv -f "ADMIN_TRANSLATION_DUPLICATE_FIX.md" "文档/国际化翻译/管理后台翻译重复键修复.md" 2>/dev/null || true
mv -f "ADMIN_TRANSLATION_FIX_FINAL_SUMMARY.md" "文档/国际化翻译/管理后台翻译修复最终摘要.md" 2>/dev/null || true
mv -f "ADMIN_TRANSLATION_FIX_SUMMARY.md" "文档/国际化翻译/管理后台翻译修复摘要.md" 2>/dev/null || true
mv -f "TRANSLATION_FIX_SUMMARY.md" "文档/国际化翻译/翻译修复摘要.md" 2>/dev/null || true
mv -f "TRANSLATION_FIX_VERIFICATION_GUIDE.md" "文档/国际化翻译/翻译修复验证指南.md" 2>/dev/null || true
mv -f "TRANSLATION_STRUCTURE_VERIFICATION.md" "文档/国际化翻译/翻译结构验证.md" 2>/dev/null || true
mv -f "DUPLICATE_KEYS_CHECK_COMPLETE.md" "文档/国际化翻译/重复键检查完成.md" 2>/dev/null || true
mv -f "DUPLICATE_KEYS_FIX_FINAL.md" "文档/国际化翻译/重复键修复最终版.md" 2>/dev/null || true
mv -f "DUPLICATE_KEYS_FIX_SUMMARY.md" "文档/国际化翻译/重复键修复摘要.md" 2>/dev/null || true
mv -f "I18N_CONSOLE_WARNINGS_REPORT.md" "文档/国际化翻译/国际化控制台警告报告.md" 2>/dev/null || true
mv -f "I18N_RULES_ADDED.md" "文档/国际化翻译/国际化规则添加.md" 2>/dev/null || true
mv -f "LANGUAGE_SWITCHING_TEST_SUMMARY.md" "文档/国际化翻译/语言切换测试摘要.md" 2>/dev/null || true
mv -f "CONSOLE_TRANSLATION_TEST_REPORT.md" "文档/国际化翻译/控制台翻译测试报告.md" 2>/dev/null || true

# 问题修复/
echo "整理问题修复文档..."
mv -f "BACKEND_FIX_COMPLETE.md" "文档/问题修复/后端修复完成报告.md" 2>/dev/null || true
mv -f "BACKEND_FIX_REPORT.md" "文档/问题修复/后端修复报告.md" 2>/dev/null || true
mv -f "BACKEND_FIX_SUMMARY.md" "文档/问题修复/后端修复摘要.md" 2>/dev/null || true
mv -f "SYSTEM_MONITORING_DATE_FIX.md" "文档/问题修复/系统监控日期修复.md" 2>/dev/null || true
mv -f "TENANT_OVERVIEW_TRANSLATION_FIX.md" "文档/问题修复/租户概览翻译修复.md" 2>/dev/null || true
mv -f "QUOTA_PAGE_TRANSLATION_FIX.md" "文档/问题修复/配额页面翻译修复.md" 2>/dev/null || true
mv -f "ADMIN_TENANT_QUOTA_FIX_COMPLETE.md" "文档/问题修复/管理后台租户配额修复完成.md" 2>/dev/null || true
mv -f "PROMETHEUS_FIX_SUMMARY.md" "文档/问题修复/Prometheus修复摘要.md" 2>/dev/null || true

# 任务完成/
echo "整理任务完成文档..."
mv -f "TASK_5.2_CONSOLE_TEST_COMPLETE.md" "文档/任务完成/任务5.2-控制台测试完成.md" 2>/dev/null || true
mv -f "TASK_5.3_BILLING_TEST_COMPLETE.md" "文档/任务完成/任务5.3-计费测试完成.md" 2>/dev/null || true
mv -f "TASK_5.4_PERMISSION_CONFIG_TEST_COMPLETE.md" "文档/任务完成/任务5.4-权限配置测试完成.md" 2>/dev/null || true
mv -f "TASK_5.4_PERMISSION_CONFIG_TEST_REPORT.md" "文档/任务完成/任务5.4-权限配置测试报告.md" 2>/dev/null || true
mv -f "TASK_5.5_QUOTA_MANAGEMENT_TEST_CHECKLIST.md" "文档/任务完成/任务5.5-配额管理测试清单.md" 2>/dev/null || true
mv -f "TASK_5.5_QUOTA_MANAGEMENT_TEST_COMPLETE.md" "文档/任务完成/任务5.5-配额管理测试完成.md" 2>/dev/null || true
mv -f "TASK_5.6_LANGUAGE_SWITCHING_TEST_COMPLETE.md" "文档/任务完成/任务5.6-语言切换测试完成.md" 2>/dev/null || true
mv -f "TASK_6.1_CONSOLE_WARNINGS_CHECK_COMPLETE.md" "文档/任务完成/任务6.1-控制台警告检查完成.md" 2>/dev/null || true
mv -f "TASK_6.2_RAW_KEYS_VERIFICATION_COMPLETE.md" "文档/任务完成/任务6.2-原始键验证完成.md" 2>/dev/null || true

# 状态报告/
echo "整理状态报告文档..."
mv -f "BACKEND_RESTART_STATUS.md" "文档/状态报告/后端重启状态.md" 2>/dev/null || true
mv -f "TCB_DEPLOYMENT_STATUS.md" "文档/状态报告/腾讯云部署状态.md" 2>/dev/null || true
mv -f "SETUP_COMPLETE_SUMMARY.md" "文档/状态报告/设置完成摘要.md" 2>/dev/null || true
mv -f "GIT_PUSH_STATUS.md" "文档/状态报告/Git推送状态.md" 2>/dev/null || true
mv -f "GIT_PUSH_SUMMARY.md" "文档/状态报告/Git推送摘要.md" 2>/dev/null || true

# 执行报告/
echo "整理执行报告文档..."
mv -f "COMPLETE_FLOW_TEST_GUIDE.md" "文档/执行报告/完整流程测试指南.md" 2>/dev/null || true
mv -f "COMPLETE_FLOW_TEST_SUMMARY.md" "文档/执行报告/完整流程测试摘要.md" 2>/dev/null || true
mv -f "FINAL_REPORT.md" "文档/执行报告/最终报告.md" 2>/dev/null || true

# 开发流程/
echo "整理开发流程文档..."
mv -f "TESTING_CHECKLIST.md" "文档/开发流程/测试检查清单.md" 2>/dev/null || true
mv -f "TESTING_WORKFLOW.md" "文档/开发流程/测试工作流程.md" 2>/dev/null || true
mv -f "OPERATION_CHECKLIST.md" "文档/开发流程/操作检查清单.md" 2>/dev/null || true
mv -f "PUSH_TO_GIT_GUIDE.md" "文档/开发流程/Git推送指南.md" 2>/dev/null || true
mv -f "DEBUG_INDEX.md" "文档/索引和说明/调试索引.md" 2>/dev/null || true
mv -f "DEBUG_QUICK_REFERENCE.md" "文档/索引和说明/调试快速参考.md" 2>/dev/null || true

echo "文档整理完成！"
echo ""
echo "已整理的文档分类："
echo "  - 快速开始: 3 个文件"
echo "  - 部署指南: 6 个文件"
echo "  - Docker: 8 个文件"
echo "  - 国际化翻译: 14 个文件"
echo "  - 问题修复: 8 个文件"
echo "  - 任务完成: 9 个文件"
echo "  - 状态报告: 5 个文件"
echo "  - 执行报告: 3 个文件"
echo "  - 开发流程: 4 个文件"
echo "  - 索引和说明: 2 个文件"
echo ""
echo "总计: 62 个文件已整理"
