#!/usr/bin/env python3
"""
SuperInsight 2.3 执行监控脚本
实时监控模块执行进度，支持人工干预
"""

import os
import sys
import time
import json
import signal
from datetime import datetime
from typing import Dict, Optional

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

class ExecutionMonitor:
    """执行监控器"""
    
    def __init__(self):
        self.status_file = ".kiro/execution_status.json"
        self.log_file = ".kiro/execution.log"
        self.running = True
        
        # 设置信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """处理中断信号"""
        print(f"\n{Colors.YELLOW}监控已停止{Colors.END}")
        self.running = False

    def load_status(self) -> Optional[Dict]:
        """加载执行状态"""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"{Colors.RED}加载状态失败: {e}{Colors.END}")
        return None

    def get_status_icon(self, status: str) -> str:
        """获取状态图标"""
        icons = {
            'pending': '⏳',
            'running': '🔄',
            'completed': '✅',
            'failed': '❌',
            'paused': '⏸️'
        }
        return icons.get(status, '❓')

    def format_duration(self, start_time: str, end_time: Optional[str] = None) -> str:
        """格式化持续时间"""
        try:
            start = datetime.fromisoformat(start_time)
            end = datetime.fromisoformat(end_time) if end_time else datetime.now()
            duration = end - start
            
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        except:
            return "未知"

    def print_status_dashboard(self, status: Dict):
        """打印状态仪表盘"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}📊 SuperInsight 2.3 执行监控仪表盘{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.END}")
        print(f"{Colors.WHITE}更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        
        # 检查是否启用了自动确认模式
        auto_approve_enabled = self.check_auto_approve_mode()
        if auto_approve_enabled:
            print(f"{Colors.GREEN}🤖 自动确认模式: 已启用{Colors.END}")
        else:
            print(f"{Colors.YELLOW}👤 手动确认模式: 需要人工干预{Colors.END}")
        print()
        
        # 总体统计
        modules = status.get('modules', {})
        total_modules = len(modules)
        completed_modules = len([m for m in modules.values() if m.get('status') == 'completed'])
        running_modules = len([m for m in modules.values() if m.get('status') == 'running'])
        failed_modules = len([m for m in modules.values() if m.get('status') == 'failed'])
        
        overall_progress = (completed_modules / total_modules * 100) if total_modules > 0 else 0
        
        print(f"{Colors.BOLD}📈 总体进度:{Colors.END}")
        print(f"  🎯 完成进度: {overall_progress:.1f}% ({completed_modules}/{total_modules})")
        print(f"  🔄 正在执行: {running_modules} 个模块")
        print(f"  ❌ 执行失败: {failed_modules} 个模块")
        
        # 执行时间统计
        if status.get('start_time'):
            start_time = datetime.fromisoformat(status['start_time'])
            elapsed = datetime.now() - start_time
            print(f"  ⏱️  总用时: {self.format_duration(status['start_time'])}")
            
            if completed_modules > 0:
                avg_time = elapsed / completed_modules
                remaining = total_modules - completed_modules
                estimated_remaining = avg_time * remaining
                print(f"  ⏱️  预计剩余: {int(estimated_remaining.total_seconds() // 60)}分钟")
        
        print()
        
        # 当前执行模块详情
        current_module = status.get('current_module')
        if current_module and current_module in modules:
            module_info = modules[current_module]
            if module_info.get('status') == 'running':
                print(f"{Colors.BOLD}🔄 当前执行模块:{Colors.END}")
                print(f"  📦 模块名称: {current_module}")
                print(f"  📈 执行进度: {module_info.get('progress', 0)}%")
                print(f"  🔧 当前任务: {module_info.get('current_task', '未知')}")
                if module_info.get('start_time'):
                    print(f"  ⏱️  执行时间: {self.format_duration(module_info['start_time'])}")
                print()
        
        # 模块状态列表
        print(f"{Colors.BOLD}📋 模块状态列表:{Colors.END}")
        
        module_names = [
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
        
        display_names = {
            "multi-tenant-workspace": "Multi-Tenant Workspace",
            "audit-security": "Audit Security",
            "frontend-management": "Frontend Management",
            "data-sync-pipeline": "Data Sync Pipeline",
            "quality-workflow": "Quality Workflow",
            "data-version-lineage": "Data Version Lineage",
            "billing-advanced": "Billing Advanced",
            "high-availability": "High Availability",
            "deployment-tcb-fullstack": "Deployment TCB Fullstack"
        }
        
        for i, module_name in enumerate(module_names, 1):
            module_info = modules.get(module_name, {})
            status_icon = self.get_status_icon(module_info.get('status', 'pending'))
            progress = module_info.get('progress', 0)
            
            print(f"  {i:2d}. {status_icon} {display_names.get(module_name, module_name)} - {progress}%")
            
            if module_info.get('status') == 'running':
                current_task = module_info.get('current_task', '执行中...')
                print(f"      🔧 {current_task}")
                if module_info.get('start_time'):
                    duration = self.format_duration(module_info['start_time'])
                    print(f"      ⏱️  {duration}")
            elif module_info.get('status') == 'completed':
                if module_info.get('start_time') and module_info.get('end_time'):
                    duration = self.format_duration(module_info['start_time'], module_info['end_time'])
                    print(f"      ✅ 完成用时: {duration}")
            elif module_info.get('status') == 'failed':
                if auto_approve_enabled:
                    print(f"      🤖 自动重试中...")
                else:
                    print(f"      ❌ 执行失败，需要人工干预")
        
        print()
        
        # 控制提示
        print(f"{Colors.YELLOW}💡 监控控制:{Colors.END}")
        print(f"  • 按 Ctrl+C 停止监控")
        print(f"  • 查看详细日志: tail -f {self.log_file}")
        print(f"  • 状态文件位置: {self.status_file}")
        if auto_approve_enabled:
            print(f"  • 自动确认模式: 错误自动重试，失败自动跳过")
        
        # 最近日志
        self.print_recent_logs()

    def check_auto_approve_mode(self) -> bool:
        """检查是否启用了自动确认模式"""
        try:
            # 检查是否有运行中的进程使用了自动确认参数
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'python3' and proc.info['cmdline']:
                        cmdline = ' '.join(proc.info['cmdline'])
                        if 'run-all-modules.py' in cmdline and ('--auto-approve-all' in cmdline or '--force-yes' in cmdline):
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except ImportError:
            # 如果没有psutil，通过其他方式检查
            pass
        
        return False

    def print_recent_logs(self, lines: int = 5):
        """打印最近的日志"""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    log_lines = f.readlines()
                
                if log_lines:
                    print(f"{Colors.BOLD}📝 最近日志 (最后{min(lines, len(log_lines))}行):{Colors.END}")
                    for line in log_lines[-lines:]:
                        line = line.strip()
                        if line:
                            if '[ERROR]' in line:
                                print(f"  {Colors.RED}{line}{Colors.END}")
                            elif '[SUCCESS]' in line:
                                print(f"  {Colors.GREEN}{line}{Colors.END}")
                            elif '[WARNING]' in line:
                                print(f"  {Colors.YELLOW}{line}{Colors.END}")
                            else:
                                print(f"  {line}")
        except Exception:
            pass

    def check_execution_health(self, status: Dict) -> bool:
        """检查执行健康状态"""
        modules = status.get('modules', {})
        
        # 检查是否有失败的模块
        failed_modules = [name for name, info in modules.items() if info.get('status') == 'failed']
        if failed_modules:
            print(f"\n{Colors.RED}⚠️  发现失败模块: {', '.join(failed_modules)}{Colors.END}")
            return False
        
        # 检查是否有长时间运行的模块
        for name, info in modules.items():
            if info.get('status') == 'running' and info.get('start_time'):
                start_time = datetime.fromisoformat(info['start_time'])
                duration = datetime.now() - start_time
                
                # 如果单个模块运行超过30分钟，发出警告
                if duration.total_seconds() > 1800:  # 30分钟
                    print(f"\n{Colors.YELLOW}⚠️  模块 {name} 运行时间过长: {self.format_duration(info['start_time'])}{Colors.END}")
        
        return True

    def run(self, refresh_interval: int = 5):
        """运行监控"""
        print(f"{Colors.CYAN}🚀 启动 SuperInsight 2.3 执行监控器{Colors.END}")
        print(f"{Colors.WHITE}刷新间隔: {refresh_interval}秒{Colors.END}")
        print(f"{Colors.WHITE}按 Ctrl+C 停止监控{Colors.END}")
        print()
        
        while self.running:
            try:
                status = self.load_status()
                
                if status:
                    self.print_status_dashboard(status)
                    self.check_execution_health(status)
                else:
                    print(f"{Colors.YELLOW}⚠️  未找到执行状态文件，等待执行开始...{Colors.END}")
                
                # 等待刷新间隔
                for i in range(refresh_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"{Colors.RED}监控错误: {e}{Colors.END}")
                time.sleep(refresh_interval)
        
        print(f"\n{Colors.CYAN}监控已停止{Colors.END}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SuperInsight 2.3 执行监控器")
    parser.add_argument("--interval", "-i", type=int, default=5, help="刷新间隔(秒)")
    
    args = parser.parse_args()
    
    monitor = ExecutionMonitor()
    monitor.run(args.interval)

if __name__ == "__main__":
    main()