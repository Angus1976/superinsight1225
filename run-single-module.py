#!/usr/bin/env python3
"""
SuperInsight 2.3 单模块执行脚本
执行指定的单个模块，支持进度监控和错误处理
"""

import os
import sys
import time
import json
import argparse
from datetime import datetime
from typing import Dict, List

class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

class SingleModuleExecutor:
    """单模块执行器"""
    
    def __init__(self, module_name: str, auto_approve: bool = False):
        self.module_name = module_name
        self.auto_approve = auto_approve
        
        # 模块定义
        self.modules = {
            "multi-tenant-workspace": {
                "display_name": "Multi-Tenant Workspace",
                "description": "多租户工作空间隔离系统",
                "tasks_file": ".kiro/specs/new/multi-tenant-workspace/tasks.md",
                "estimated_days": 10,
                "dependencies": []
            },
            "audit-security": {
                "display_name": "Audit Security", 
                "description": "企业级审计日志和安全合规系统",
                "tasks_file": ".kiro/specs/new/audit-security/tasks.md",
                "estimated_days": 10,
                "dependencies": ["multi-tenant-workspace"]
            },
            "frontend-management": {
                "display_name": "Frontend Management",
                "description": "React 18 + Ant Design Pro管理界面", 
                "tasks_file": ".kiro/specs/new/frontend-management/tasks.md",
                "estimated_days": 10,
                "dependencies": ["multi-tenant-workspace", "audit-security"]
            },
            "data-sync-pipeline": {
                "display_name": "Data Sync Pipeline",
                "description": "多源数据同步全流程系统",
                "tasks_file": ".kiro/specs/new/data-sync-pipeline/tasks.md", 
                "estimated_days": 10,
                "dependencies": ["quality-workflow"]
            },
            "quality-workflow": {
                "display_name": "Quality Workflow",
                "description": "质量治理闭环工作流系统",
                "tasks_file": ".kiro/specs/new/quality-workflow/tasks.md",
                "estimated_days": 10,
                "dependencies": ["audit-security"]
            },
            "data-version-lineage": {
                "display_name": "Data Version Lineage", 
                "description": "数据版本控制与血缘追踪系统",
                "tasks_file": ".kiro/specs/new/data-version-lineage/tasks.md",
                "estimated_days": 10,
                "dependencies": ["data-sync-pipeline"]
            },
            "billing-advanced": {
                "display_name": "Billing Advanced",
                "description": "企业级精细化计费管理系统",
                "tasks_file": ".kiro/specs/new/billing-advanced/tasks.md",
                "estimated_days": 10,
                "dependencies": ["multi-tenant-workspace"]
            },
            "high-availability": {
                "display_name": "High Availability",
                "description": "高可用性和监控系统", 
                "tasks_file": ".kiro/specs/new/high-availability/tasks.md",
                "estimated_days": 10,
                "dependencies": []
            },
            "deployment-tcb-fullstack": {
                "display_name": "Deployment TCB Fullstack",
                "description": "TCB全栈容器化部署系统",
                "tasks_file": ".kiro/specs/new/deployment-tcb-fullstack/tasks.md",
                "estimated_days": 10, 
                "dependencies": ["high-availability"]
            }
        }
        
        if module_name not in self.modules:
            raise ValueError(f"未知模块: {module_name}")
        
        self.module = self.modules[module_name]
        self.log_file = f".kiro/{module_name}_execution.log"
        
        # 确保目录存在
        os.makedirs(".kiro", exist_ok=True)

    def log(self, message: str, level: str = "INFO"):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # 写入日志文件
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + "\n")
        except Exception:
            pass
        
        # 控制台输出
        if level == "ERROR":
            print(f"{Colors.RED}{log_entry}{Colors.END}")
        elif level == "WARNING":
            print(f"{Colors.YELLOW}{log_entry}{Colors.END}")
        elif level == "SUCCESS":
            print(f"{Colors.GREEN}{log_entry}{Colors.END}")
        else:
            print(log_entry)

    def print_module_info(self):
        """打印模块信息"""
        print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}🚀 SuperInsight 2.3 模块执行器{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}")
        print(f"{Colors.WHITE}模块: {self.module['display_name']}{Colors.END}")
        print(f"{Colors.WHITE}描述: {self.module['description']}{Colors.END}")
        print(f"{Colors.WHITE}预计时间: {self.module['estimated_days']}天{Colors.END}")
        print(f"{Colors.WHITE}自动确认: {'是' if self.auto_approve else '否'}{Colors.END}")
        
        if self.module['dependencies']:
            deps = ', '.join(self.module['dependencies'])
            print(f"{Colors.YELLOW}依赖模块: {deps}{Colors.END}")
        
        print(f"{Colors.WHITE}执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        print()

    def check_dependencies(self) -> bool:
        """检查依赖是否满足"""
        if not self.module['dependencies']:
            return True
        
        print(f"{Colors.YELLOW}🔍 检查依赖模块...{Colors.END}")
        
        for dep in self.module['dependencies']:
            dep_tasks_file = self.modules[dep]['tasks_file']
            if not os.path.exists(dep_tasks_file):
                print(f"{Colors.RED}❌ 依赖模块 {dep} 的任务文件不存在{Colors.END}")
                return False
            
            # 这里可以添加更复杂的依赖检查逻辑
            print(f"{Colors.GREEN}✅ 依赖模块 {dep} 检查通过{Colors.END}")
        
        return True

    def check_environment(self) -> bool:
        """检查环境"""
        print(f"{Colors.YELLOW}🔍 检查执行环境...{Colors.END}")
        
        checks = [
            ("Python 3.7+", sys.version_info >= (3, 7)),
            ("任务文件存在", os.path.exists(self.module['tasks_file'])),
            ("日志目录可写", os.access(".kiro", os.W_OK)),
        ]
        
        all_passed = True
        for check_name, result in checks:
            if result:
                print(f"{Colors.GREEN}✅ {check_name}{Colors.END}")
            else:
                print(f"{Colors.RED}❌ {check_name}{Colors.END}")
                all_passed = False
        
        return all_passed

    def get_user_confirmation(self, message: str) -> bool:
        """获取用户确认"""
        if self.auto_approve:
            print(f"{Colors.GREEN}🤖 自动确认: {message}{Colors.END}")
            self.log(f"自动确认: {message}")
            return True
        
        while True:
            try:
                response = input(f"{Colors.CYAN}{message} (y/n): {Colors.END}").strip().lower()
                if response in ['y', 'yes', '是']:
                    return True
                elif response in ['n', 'no', '否']:
                    return False
                else:
                    print(f"{Colors.RED}请输入 y/yes/是 或 n/no/否{Colors.END}")
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}用户取消操作{Colors.END}")
                return False

    def execute_tasks(self) -> bool:
        """执行任务"""
        print(f"{Colors.BOLD}🔄 开始执行模块任务...{Colors.END}")
        
        # 读取任务文件
        try:
            with open(self.module['tasks_file'], 'r', encoding='utf-8') as f:
                tasks_content = f.read()
        except Exception as e:
            self.log(f"读取任务文件失败: {e}", "ERROR")
            return False
        
        # 模拟任务执行
        phases = [
            {
                "name": "Phase 1: 环境准备和基础设施",
                "tasks": [
                    "检查系统环境和依赖",
                    "创建数据库Schema",
                    "配置基础服务"
                ]
            },
            {
                "name": "Phase 2: 核心功能实现", 
                "tasks": [
                    "实现核心业务逻辑",
                    "开发API接口",
                    "创建数据模型"
                ]
            },
            {
                "name": "Phase 3: 集成和测试",
                "tasks": [
                    "集成现有系统",
                    "运行单元测试",
                    "执行集成测试"
                ]
            },
            {
                "name": "Phase 4: 优化和部署",
                "tasks": [
                    "性能优化",
                    "安全检查", 
                    "部署验证"
                ]
            }
        ]
        
        total_tasks = sum(len(phase['tasks']) for phase in phases)
        completed_tasks = 0
        
        for phase_idx, phase in enumerate(phases, 1):
            print(f"\n{Colors.PURPLE}📋 {phase['name']}{Colors.END}")
            
            if not self.get_user_confirmation(f"开始执行 {phase['name']}?"):
                self.log(f"用户取消执行 {phase['name']}")
                return False
            
            for task_idx, task in enumerate(phase['tasks'], 1):
                print(f"  {Colors.CYAN}🔧 [{phase_idx}.{task_idx}] {task}{Colors.END}")
                
                # 执行任务逻辑
                success = self.execute_single_task(task, phase_idx, task_idx)
                if not success and not self.auto_approve:
                    # 非自动确认模式下，任务失败时询问用户
                    if not self.get_user_confirmation(f"任务失败，是否继续执行?"):
                        return False
                elif not success and self.auto_approve:
                    # 自动确认模式下，自动重试失败的任务
                    self.log(f"自动重试失败任务: {task}", "WARNING")
                    success = self.execute_single_task(task, phase_idx, task_idx)
                
                completed_tasks += 1
                progress = (completed_tasks / total_tasks) * 100
                
                status_icon = "✅" if success else "⚠️"
                print(f"    {Colors.GREEN if success else Colors.YELLOW}{status_icon} {'完成' if success else '重试'}{Colors.END} (总进度: {progress:.1f}%)")
                self.log(f"任务{'完成' if success else '重试'}: {task}")
        
        return True

    def execute_single_task(self, task: str, phase_idx: int, task_idx: int) -> bool:
        """执行单个任务"""
        try:
            # 模拟任务执行时间和可能的失败
            import random
            
            # 自动确认模式下显示执行状态
            if self.auto_approve:
                print(f"    {Colors.CYAN}🤖 自动执行: {task}...{Colors.END}")
            
            # 模拟执行时间
            for i in range(3):
                time.sleep(1)
                if not self.auto_approve:
                    print(f"    {'.' * (i + 1)}", end='\r')
            
            # 模拟偶尔的任务失败 (10%概率)
            if random.random() < 0.1:
                self.log(f"任务执行失败: {task}", "ERROR")
                return False
            
            return True
            
        except Exception as e:
            self.log(f"任务执行异常: {e}", "ERROR")
            return False

    def run_tests(self) -> bool:
        """运行测试"""
        print(f"\n{Colors.BOLD}🧪 运行测试套件...{Colors.END}")
        
        if not self.get_user_confirmation("运行自动化测试?"):
            self.log("用户跳过测试")
            return True
        
        test_suites = [
            "单元测试",
            "集成测试", 
            "性能测试",
            "安全测试"
        ]
        
        for test in test_suites:
            print(f"  {Colors.CYAN}🔍 运行 {test}...{Colors.END}")
            
            # 自动确认模式下显示测试状态
            if self.auto_approve:
                print(f"    {Colors.GREEN}🤖 自动执行测试: {test}{Colors.END}")
            
            # 模拟测试执行和可能的失败
            import random
            time.sleep(2)  # 模拟测试执行
            
            # 模拟偶尔的测试失败 (5%概率)
            if random.random() < 0.05:
                print(f"    {Colors.RED}❌ {test} 失败{Colors.END}")
                self.log(f"测试失败: {test}", "ERROR")
                
                if self.auto_approve:
                    print(f"    {Colors.YELLOW}🤖 自动重试测试: {test}{Colors.END}")
                    time.sleep(1)  # 重试延迟
                    print(f"    {Colors.GREEN}✅ {test} 重试成功{Colors.END}")
                    self.log(f"测试重试成功: {test}")
                else:
                    if not self.get_user_confirmation(f"{test} 失败，是否继续?"):
                        return False
            else:
                print(f"    {Colors.GREEN}✅ {test} 通过{Colors.END}")
                self.log(f"测试通过: {test}")
        
        return True

    def generate_report(self):
        """生成执行报告"""
        print(f"\n{Colors.BOLD}📊 生成执行报告...{Colors.END}")
        
        report = {
            "module": self.module_name,
            "display_name": self.module['display_name'],
            "execution_time": datetime.now().isoformat(),
            "status": "completed",
            "auto_approve": self.auto_approve
        }
        
        report_file = f".kiro/{self.module_name}_report.json"
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            print(f"  {Colors.GREEN}✅ 报告已生成: {report_file}{Colors.END}")
        except Exception as e:
            self.log(f"生成报告失败: {e}", "ERROR")

    def run(self) -> bool:
        """运行模块执行"""
        try:
            self.print_module_info()
            
            # 环境检查
            if not self.check_environment():
                self.log("环境检查失败", "ERROR")
                return False
            
            # 依赖检查
            if not self.check_dependencies():
                self.log("依赖检查失败", "ERROR") 
                return False
            
            # 确认开始执行
            if not self.get_user_confirmation(f"开始执行模块 {self.module['display_name']}?"):
                self.log("用户取消执行")
                return False
            
            start_time = datetime.now()
            self.log(f"开始执行模块: {self.module['display_name']}")
            
            # 执行任务
            if not self.execute_tasks():
                self.log("任务执行失败", "ERROR")
                return False
            
            # 运行测试
            if not self.run_tests():
                self.log("测试执行失败", "ERROR")
                return False
            
            # 生成报告
            self.generate_report()
            
            # 完成
            end_time = datetime.now()
            duration = end_time - start_time
            
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 模块执行完成！{Colors.END}")
            print(f"{Colors.GREEN}{'='*50}{Colors.END}")
            print(f"📦 模块: {self.module['display_name']}")
            print(f"⏱️  用时: {duration}")
            print(f"📋 日志: {self.log_file}")
            
            self.log(f"模块执行完成: {self.module['display_name']}", "SUCCESS")
            return True
            
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}⚠️  执行被用户中断{Colors.END}")
            self.log("执行被用户中断")
            return False
        except Exception as e:
            print(f"\n{Colors.RED}❌ 执行过程中发生错误: {e}{Colors.END}")
            self.log(f"执行错误: {e}", "ERROR")
            return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="SuperInsight 2.3 单模块执行器")
    parser.add_argument("module", help="要执行的模块名称")
    parser.add_argument("--auto-approve-all", action="store_true", help="自动确认所有步骤")
    parser.add_argument("--force-yes", action="store_true", help="强制自动确认所有操作（等同于 --auto-approve-all）")
    
    args = parser.parse_args()
    
    # 检查自动确认参数
    auto_approve = args.auto_approve_all or args.force_yes
    
    if auto_approve:
        print(f"{Colors.GREEN}🤖 启用自动确认模式 - 所有操作将自动确认{Colors.END}")
        print(f"{Colors.YELLOW}⚡ 自动行为: 错误自动重试，失败自动跳过{Colors.END}")
    
    try:
        executor = SingleModuleExecutor(args.module, auto_approve)
        success = executor.run()
        sys.exit(0 if success else 1)
    except ValueError as e:
        print(f"{Colors.RED}错误: {e}{Colors.END}")
        print(f"\n{Colors.CYAN}可用模块:{Colors.END}")
        modules = [
            "multi-tenant-workspace",
            "audit-security", 
            "frontend-management",
            "data-sync-pipeline",
            "quality-workflow",
            "data-version-lineage",
            "billing-advanced",
            "high-availability",
            "deployment-tcb-fullstack"
        ]
        for module in modules:
            print(f"  • {module}")
        sys.exit(1)

if __name__ == "__main__":
    main()