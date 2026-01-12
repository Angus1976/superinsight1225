#!/usr/bin/env python3
"""
SuperInsight 2.3 执行控制脚本
提供启动、停止、暂停、恢复等执行控制功能
"""

import os
import sys
import json
import signal
import subprocess
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

class ExecutionController:
    """执行控制器"""
    
    def __init__(self):
        self.status_file = ".kiro/execution_status.json"
        self.pid_file = ".kiro/execution.pid"
        self.log_file = ".kiro/execution.log"
        
        # 确保目录存在
        os.makedirs(".kiro", exist_ok=True)

    def load_status(self) -> Optional[Dict]:
        """加载执行状态"""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"{Colors.RED}加载状态失败: {e}{Colors.END}")
        return None

    def save_control_signal(self, signal_type: str):
        """保存控制信号"""
        signal_file = ".kiro/control_signal.json"
        signal_data = {
            "signal": signal_type,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            with open(signal_file, 'w', encoding='utf-8') as f:
                json.dump(signal_data, f, indent=2)
        except Exception as e:
            print(f"{Colors.RED}保存控制信号失败: {e}{Colors.END}")

    def get_execution_pid(self) -> Optional[int]:
        """获取执行进程PID"""
        try:
            if os.path.exists(self.pid_file):
                with open(self.pid_file, 'r') as f:
                    return int(f.read().strip())
        except Exception:
            pass
        return None

    def is_execution_running(self) -> bool:
        """检查执行是否正在运行"""
        pid = self.get_execution_pid()
        if pid:
            try:
                # 检查进程是否存在
                os.kill(pid, 0)
                return True
            except OSError:
                # 进程不存在，清理PID文件
                if os.path.exists(self.pid_file):
                    os.remove(self.pid_file)
        return False

    def print_status_summary(self):
        """打印状态摘要"""
        status = self.load_status()
        
        print(f"{Colors.CYAN}{Colors.BOLD}📊 SuperInsight 2.3 执行状态{Colors.END}")
        print(f"{Colors.CYAN}{'='*50}{Colors.END}")
        
        if not status:
            print(f"{Colors.YELLOW}⚠️  未找到执行状态文件{Colors.END}")
            return
        
        # 总体统计
        modules = status.get('modules', {})
        total = len(modules)
        completed = len([m for m in modules.values() if m.get('status') == 'completed'])
        running = len([m for m in modules.values() if m.get('status') == 'running'])
        failed = len([m for m in modules.values() if m.get('status') == 'failed'])
        
        print(f"📈 总体进度: {completed}/{total} 模块完成 ({completed/total*100:.1f}%)")
        print(f"🔄 正在执行: {running} 个模块")
        print(f"❌ 执行失败: {failed} 个模块")
        
        if status.get('start_time'):
            start_time = datetime.fromisoformat(status['start_time'])
            elapsed = datetime.now() - start_time
            print(f"⏱️  总用时: {int(elapsed.total_seconds() // 60)}分钟")
        
        # 当前执行模块
        current_module = status.get('current_module')
        if current_module and current_module in modules:
            module_info = modules[current_module]
            if module_info.get('status') == 'running':
                print(f"\n🔄 当前执行: {current_module}")
                print(f"📈 进度: {module_info.get('progress', 0)}%")
                print(f"🔧 任务: {module_info.get('current_task', '未知')}")
        
        print()

    def start_execution(self, auto_approve: bool = False, follow_sequence: bool = True, force_yes: bool = False):
        """启动执行"""
        if self.is_execution_running():
            print(f"{Colors.YELLOW}⚠️  执行已在运行中{Colors.END}")
            return False
        
        print(f"{Colors.GREEN}🚀 启动 SuperInsight 2.3 全自动执行...{Colors.END}")
        
        # 构建命令
        cmd = ["python3", "run-all-modules.py"]
        if auto_approve or force_yes:
            cmd.append("--auto-approve-all")
        if follow_sequence:
            cmd.append("--follow-sequence")
        
        if auto_approve or force_yes:
            print(f"{Colors.GREEN}🤖 自动确认模式已启用{Colors.END}")
        
        try:
            # 启动后台进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            # 保存PID
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))
            
            print(f"{Colors.GREEN}✅ 执行已启动 (PID: {process.pid}){Colors.END}")
            if auto_approve or force_yes:
                print(f"{Colors.YELLOW}⚡ 自动确认: 错误重试 → 暂停继续 → 失败跳过{Colors.END}")
            print(f"{Colors.CYAN}💡 使用以下命令监控进度:{Colors.END}")
            print(f"  python3 monitor-execution.py")
            print(f"  python3 execution-control.py status")
            
            return True
            
        except Exception as e:
            print(f"{Colors.RED}❌ 启动失败: {e}{Colors.END}")
            return False

    def stop_execution(self):
        """停止执行"""
        pid = self.get_execution_pid()
        
        if not pid:
            print(f"{Colors.YELLOW}⚠️  未找到运行中的执行进程{Colors.END}")
            return False
        
        try:
            print(f"{Colors.YELLOW}🛑 正在停止执行 (PID: {pid})...{Colors.END}")
            
            # 发送SIGTERM信号
            os.kill(pid, signal.SIGTERM)
            
            # 等待进程结束
            import time
            for i in range(10):  # 等待最多10秒
                try:
                    os.kill(pid, 0)
                    time.sleep(1)
                except OSError:
                    break
            else:
                # 如果进程仍在运行，强制终止
                print(f"{Colors.RED}强制终止进程...{Colors.END}")
                os.kill(pid, signal.SIGKILL)
            
            # 清理PID文件
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
            
            print(f"{Colors.GREEN}✅ 执行已停止{Colors.END}")
            return True
            
        except Exception as e:
            print(f"{Colors.RED}❌ 停止失败: {e}{Colors.END}")
            return False

    def pause_execution(self):
        """暂停执行"""
        if not self.is_execution_running():
            print(f"{Colors.YELLOW}⚠️  没有运行中的执行进程{Colors.END}")
            return False
        
        self.save_control_signal("pause")
        print(f"{Colors.YELLOW}⏸️  已发送暂停信号{Colors.END}")
        print(f"{Colors.CYAN}💡 执行将在当前任务完成后暂停{Colors.END}")
        return True

    def resume_execution(self):
        """恢复执行"""
        if not self.is_execution_running():
            print(f"{Colors.YELLOW}⚠️  没有运行中的执行进程{Colors.END}")
            return False
        
        self.save_control_signal("resume")
        print(f"{Colors.GREEN}▶️  已发送恢复信号{Colors.END}")
        return True

    def restart_execution(self, auto_approve: bool = False, force_yes: bool = False):
        """重启执行"""
        print(f"{Colors.CYAN}🔄 重启执行...{Colors.END}")
        
        # 先停止
        if self.is_execution_running():
            self.stop_execution()
        
        # 等待一秒
        import time
        time.sleep(1)
        
        # 再启动
        return self.start_execution(auto_approve or force_yes, force_yes=force_yes)

    def show_logs(self, lines: int = 50, follow: bool = False):
        """显示日志"""
        if not os.path.exists(self.log_file):
            print(f"{Colors.YELLOW}⚠️  日志文件不存在{Colors.END}")
            return
        
        try:
            if follow:
                # 实时跟踪日志
                print(f"{Colors.CYAN}📝 实时跟踪日志 (按 Ctrl+C 停止):{Colors.END}")
                subprocess.run(["tail", "-f", self.log_file])
            else:
                # 显示最后N行
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    log_lines = f.readlines()
                
                print(f"{Colors.CYAN}📝 最近 {min(lines, len(log_lines))} 行日志:{Colors.END}")
                for line in log_lines[-lines:]:
                    line = line.strip()
                    if '[ERROR]' in line:
                        print(f"{Colors.RED}{line}{Colors.END}")
                    elif '[SUCCESS]' in line:
                        print(f"{Colors.GREEN}{line}{Colors.END}")
                    elif '[WARNING]' in line:
                        print(f"{Colors.YELLOW}{line}{Colors.END}")
                    else:
                        print(line)
                        
        except Exception as e:
            print(f"{Colors.RED}❌ 读取日志失败: {e}{Colors.END}")

    def clean_execution_data(self):
        """清理执行数据"""
        files_to_clean = [
            self.status_file,
            self.pid_file,
            self.log_file,
            ".kiro/control_signal.json"
        ]
        
        cleaned = 0
        for file_path in files_to_clean:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    cleaned += 1
                    print(f"{Colors.GREEN}✅ 已清理: {file_path}{Colors.END}")
                except Exception as e:
                    print(f"{Colors.RED}❌ 清理失败 {file_path}: {e}{Colors.END}")
        
        if cleaned > 0:
            print(f"{Colors.GREEN}🧹 已清理 {cleaned} 个文件{Colors.END}")
        else:
            print(f"{Colors.YELLOW}⚠️  没有需要清理的文件{Colors.END}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SuperInsight 2.3 执行控制器")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 启动命令
    start_parser = subparsers.add_parser('start', help='启动执行')
    start_parser.add_argument('--auto-approve-all', action='store_true', help='自动确认所有步骤')
    start_parser.add_argument('--force-yes', action='store_true', help='强制自动确认所有操作（等同于 --auto-approve-all）')
    start_parser.add_argument('--no-sequence', action='store_true', help='不按推荐顺序执行')
    
    # 停止命令
    subparsers.add_parser('stop', help='停止执行')
    
    # 暂停命令
    subparsers.add_parser('pause', help='暂停执行')
    
    # 恢复命令
    subparsers.add_parser('resume', help='恢复执行')
    
    # 重启命令
    restart_parser = subparsers.add_parser('restart', help='重启执行')
    restart_parser.add_argument('--auto-approve-all', action='store_true', help='自动确认所有步骤')
    restart_parser.add_argument('--force-yes', action='store_true', help='强制自动确认所有操作（等同于 --auto-approve-all）')
    
    # 状态命令
    subparsers.add_parser('status', help='显示执行状态')
    
    # 日志命令
    logs_parser = subparsers.add_parser('logs', help='显示日志')
    logs_parser.add_argument('--lines', '-n', type=int, default=50, help='显示行数')
    logs_parser.add_argument('--follow', '-f', action='store_true', help='实时跟踪日志')
    
    # 清理命令
    subparsers.add_parser('clean', help='清理执行数据')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    controller = ExecutionController()
    
    if args.command == 'start':
        auto_approve = args.auto_approve_all or args.force_yes
        controller.start_execution(
            auto_approve=auto_approve,
            follow_sequence=not args.no_sequence,
            force_yes=args.force_yes
        )
    elif args.command == 'stop':
        controller.stop_execution()
    elif args.command == 'pause':
        controller.pause_execution()
    elif args.command == 'resume':
        controller.resume_execution()
    elif args.command == 'restart':
        auto_approve = args.auto_approve_all or args.force_yes
        controller.restart_execution(auto_approve=auto_approve, force_yes=args.force_yes)
    elif args.command == 'status':
        controller.print_status_summary()
    elif args.command == 'logs':
        controller.show_logs(lines=args.lines, follow=args.follow)
    elif args.command == 'clean':
        controller.clean_execution_data()

if __name__ == "__main__":
    main()