#!/usr/bin/env python3
"""
业务逻辑功能综合测试
测试业务逻辑提炼、模式识别、规则提取、通知系统等完整功能

实现需求 13: 客户业务逻辑提炼与智能化
"""

import asyncio
import json
import time
import requests
import websockets
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BusinessLogicTester:
    """业务逻辑功能测试器"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.project_id = "test_project_001"
        self.test_results = {}
        
    def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始业务逻辑功能综合测试")
        
        # 1. 测试API端点
        self.test_api_endpoints()
        
        # 2. 测试WebSocket连接
        asyncio.run(self.test_websocket_connection())
        
        # 3. 测试通知系统
        self.test_notification_system()
        
        # 4. 测试完整工作流
        self.test_complete_workflow()
        
        # 5. 生成测试报告
        self.generate_test_report()
        
        logger.info("业务逻辑功能综合测试完成")
    
    def test_api_endpoints(self):
        """测试API端点"""
        logger.info("测试业务逻辑API端点...")
        
        api_tests = [
            {
                "name": "模式分析",
                "method": "POST",
                "url": f"{self.base_url}/api/business-logic/analyze",
                "data": {
                    "project_id": self.project_id,
                    "confidence_threshold": 0.8,
                    "min_frequency": 3,
                    "time_range_days": 30
                }
            },
            {
                "name": "规则提取",
                "method": "POST",
                "url": f"{self.base_url}/api/business-logic/rules/extract",
                "data": {
                    "project_id": self.project_id,
                    "threshold": 0.8
                }
            },
            {
                "name": "获取业务规则",
                "method": "GET",
                "url": f"{self.base_url}/api/business-logic/rules/{self.project_id}",
            },
            {
                "name": "获取业务模式",
                "method": "GET",
                "url": f"{self.base_url}/api/business-logic/patterns/{self.project_id}",
            },
            {
                "name": "生成可视化",
                "method": "POST",
                "url": f"{self.base_url}/api/business-logic/visualization",
                "data": {
                    "project_id": self.project_id,
                    "visualization_type": "rule_network"
                }
            },
            {
                "name": "导出业务逻辑",
                "method": "POST",
                "url": f"{self.base_url}/api/business-logic/export",
                "data": {
                    "project_id": self.project_id,
                    "export_format": "json",
                    "include_rules": True,
                    "include_patterns": True,
                    "include_insights": True
                }
            },
            {
                "name": "检测变化",
                "method": "POST",
                "url": f"{self.base_url}/api/business-logic/detect-changes",
                "data": {
                    "project_id": self.project_id,
                    "time_window_days": 7
                }
            },
            {
                "name": "获取业务洞察",
                "method": "GET",
                "url": f"{self.base_url}/api/business-logic/insights/{self.project_id}",
            },
            {
                "name": "获取统计信息",
                "method": "GET",
                "url": f"{self.base_url}/api/business-logic/stats/{self.project_id}",
            },
            {
                "name": "健康检查",
                "method": "GET",
                "url": f"{self.base_url}/api/business-logic/health",
            }
        ]
        
        api_results = []
        
        for test in api_tests:
            try:
                start_time = time.time()
                
                if test["method"] == "GET":
                    response = requests.get(test["url"], timeout=10)
                elif test["method"] == "POST":
                    response = requests.post(
                        test["url"],
                        json=test.get("data", {}),
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # 毫秒
                
                result = {
                    "name": test["name"],
                    "status": "success" if response.status_code == 200 else "error",
                    "status_code": response.status_code,
                    "response_time": f"{response_time:.2f}ms",
                    "response_size": len(response.content),
                }
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        result["data_keys"] = list(response_data.keys()) if isinstance(response_data, dict) else "list"
                    except:
                        result["data_keys"] = "non-json"
                else:
                    result["error"] = response.text[:200]
                
                api_results.append(result)
                logger.info(f"✅ {test['name']}: {result['status']} ({result['response_time']})")
                
            except Exception as e:
                result = {
                    "name": test["name"],
                    "status": "error",
                    "error": str(e),
                    "response_time": "timeout",
                }
                api_results.append(result)
                logger.error(f"❌ {test['name']}: {str(e)}")
        
        self.test_results["api_endpoints"] = api_results
    
    async def test_websocket_connection(self):
        """测试WebSocket连接"""
        logger.info("测试业务逻辑WebSocket连接...")
        
        ws_url = f"ws://localhost:8000/ws/business-logic/{self.project_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                logger.info("WebSocket连接已建立")
                
                # 发送心跳消息
                await websocket.send(json.dumps({
                    "type": "ping",
                    "timestamp": datetime.now().isoformat()
                }))
                
                # 接收响应
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                if response_data.get("type") == "pong":
                    logger.info("✅ WebSocket心跳测试成功")
                    ws_result = {
                        "status": "success",
                        "connection_time": "< 1s",
                        "ping_pong": "success",
                        "message": "WebSocket连接正常"
                    }
                else:
                    logger.warning(f"⚠️ WebSocket响应异常: {response_data}")
                    ws_result = {
                        "status": "warning",
                        "message": f"响应异常: {response_data}"
                    }
                
                # 测试订阅功能
                await websocket.send(json.dumps({
                    "type": "subscribe",
                    "subscription_types": ["business_insight", "pattern_change", "rule_update"]
                }))
                
                # 接收订阅确认
                sub_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                sub_data = json.loads(sub_response)
                
                if sub_data.get("type") == "subscription_confirmed":
                    logger.info("✅ WebSocket订阅测试成功")
                    ws_result["subscription"] = "success"
                else:
                    logger.warning(f"⚠️ WebSocket订阅异常: {sub_data}")
                    ws_result["subscription"] = "warning"
                
        except asyncio.TimeoutError:
            logger.error("❌ WebSocket连接超时")
            ws_result = {
                "status": "error",
                "message": "连接超时"
            }
        except Exception as e:
            logger.error(f"❌ WebSocket连接失败: {e}")
            ws_result = {
                "status": "error",
                "message": str(e)
            }
        
        self.test_results["websocket"] = ws_result
    
    def test_notification_system(self):
        """测试通知系统"""
        logger.info("测试通知系统...")
        
        notification_tests = [
            {
                "name": "邮件通知",
                "method": "POST",
                "url": f"{self.base_url}/api/notifications/email",
                "data": {
                    "type": "business_insight",
                    "project_id": self.project_id,
                    "title": "测试业务洞察",
                    "description": "这是一个测试的业务洞察通知",
                    "impact_score": 0.85,
                    "recipients": ["test@example.com"]
                }
            },
            {
                "name": "短信通知",
                "method": "POST",
                "url": f"{self.base_url}/api/notifications/sms",
                "data": {
                    "type": "business_insight",
                    "project_id": self.project_id,
                    "title": "测试业务洞察",
                    "impact_score": 0.85,
                    "recipients": ["13800138000"]
                }
            },
            {
                "name": "通知历史",
                "method": "GET",
                "url": f"{self.base_url}/api/notifications/history?project_id={self.project_id}",
            }
        ]
        
        notification_results = []
        
        for test in notification_tests:
            try:
                start_time = time.time()
                
                if test["method"] == "GET":
                    response = requests.get(test["url"], timeout=10)
                elif test["method"] == "POST":
                    response = requests.post(
                        test["url"],
                        json=test.get("data", {}),
                        headers={"Content-Type": "application/json"},
                        timeout=10
                    )
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                result = {
                    "name": test["name"],
                    "status": "success" if response.status_code == 200 else "error",
                    "status_code": response.status_code,
                    "response_time": f"{response_time:.2f}ms",
                }
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        result["message"] = response_data.get("message", "成功")
                    except:
                        result["message"] = "响应成功"
                else:
                    result["error"] = response.text[:200]
                
                notification_results.append(result)
                logger.info(f"✅ {test['name']}: {result['status']} ({result['response_time']})")
                
            except Exception as e:
                result = {
                    "name": test["name"],
                    "status": "error",
                    "error": str(e),
                }
                notification_results.append(result)
                logger.error(f"❌ {test['name']}: {str(e)}")
        
        self.test_results["notifications"] = notification_results
    
    def test_complete_workflow(self):
        """测试完整工作流"""
        logger.info("测试完整业务逻辑工作流...")
        
        workflow_steps = [
            {
                "step": "1. 运行模式分析",
                "action": lambda: requests.post(
                    f"{self.base_url}/api/business-logic/analyze",
                    json={
                        "project_id": self.project_id,
                        "confidence_threshold": 0.7,
                        "min_frequency": 2
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=15
                )
            },
            {
                "step": "2. 提取业务规则",
                "action": lambda: requests.post(
                    f"{self.base_url}/api/business-logic/rules/extract",
                    json={
                        "project_id": self.project_id,
                        "threshold": 0.7
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=15
                )
            },
            {
                "step": "3. 生成可视化",
                "action": lambda: requests.post(
                    f"{self.base_url}/api/business-logic/visualization",
                    json={
                        "project_id": self.project_id,
                        "visualization_type": "insight_dashboard"
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
            },
            {
                "step": "4. 检测变化",
                "action": lambda: requests.post(
                    f"{self.base_url}/api/business-logic/detect-changes",
                    json={
                        "project_id": self.project_id,
                        "time_window_days": 7
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
            },
            {
                "step": "5. 导出数据",
                "action": lambda: requests.post(
                    f"{self.base_url}/api/business-logic/export",
                    json={
                        "project_id": self.project_id,
                        "export_format": "json"
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
            }
        ]
        
        workflow_results = []
        total_start_time = time.time()
        
        for step_info in workflow_steps:
            try:
                step_start_time = time.time()
                response = step_info["action"]()
                step_end_time = time.time()
                
                step_time = (step_end_time - step_start_time) * 1000
                
                result = {
                    "step": step_info["step"],
                    "status": "success" if response.status_code == 200 else "error",
                    "status_code": response.status_code,
                    "response_time": f"{step_time:.2f}ms",
                }
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        if isinstance(response_data, dict):
                            result["data_summary"] = {
                                "keys": list(response_data.keys()),
                                "size": len(str(response_data))
                            }
                    except:
                        result["data_summary"] = "non-json"
                else:
                    result["error"] = response.text[:100]
                
                workflow_results.append(result)
                logger.info(f"✅ {step_info['step']}: {result['status']} ({result['response_time']})")
                
                # 步骤间稍作延迟
                time.sleep(0.5)
                
            except Exception as e:
                result = {
                    "step": step_info["step"],
                    "status": "error",
                    "error": str(e),
                }
                workflow_results.append(result)
                logger.error(f"❌ {step_info['step']}: {str(e)}")
        
        total_end_time = time.time()
        total_time = (total_end_time - total_start_time) * 1000
        
        workflow_summary = {
            "total_steps": len(workflow_steps),
            "successful_steps": len([r for r in workflow_results if r["status"] == "success"]),
            "failed_steps": len([r for r in workflow_results if r["status"] == "error"]),
            "total_time": f"{total_time:.2f}ms",
            "steps": workflow_results
        }
        
        self.test_results["workflow"] = workflow_summary
        logger.info(f"工作流测试完成: {workflow_summary['successful_steps']}/{workflow_summary['total_steps']} 步骤成功")
    
    def generate_test_report(self):
        """生成测试报告"""
        logger.info("生成测试报告...")
        
        # 计算总体统计
        total_tests = 0
        successful_tests = 0
        
        for category, results in self.test_results.items():
            if category == "api_endpoints":
                total_tests += len(results)
                successful_tests += len([r for r in results if r["status"] == "success"])
            elif category == "notifications":
                total_tests += len(results)
                successful_tests += len([r for r in results if r["status"] == "success"])
            elif category == "websocket":
                total_tests += 1
                successful_tests += 1 if results["status"] == "success" else 0
            elif category == "workflow":
                total_tests += results["total_steps"]
                successful_tests += results["successful_steps"]
        
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            "test_summary": {
                "project_id": self.project_id,
                "test_time": datetime.now().isoformat(),
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": total_tests - successful_tests,
                "success_rate": f"{success_rate:.1f}%",
            },
            "detailed_results": self.test_results,
            "recommendations": self._generate_recommendations()
        }
        
        # 保存报告到文件
        report_filename = f"business_logic_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # 打印摘要
        print("\n" + "="*60)
        print("业务逻辑功能测试报告")
        print("="*60)
        print(f"项目ID: {self.project_id}")
        print(f"测试时间: {report['test_summary']['test_time']}")
        print(f"总测试数: {total_tests}")
        print(f"成功测试: {successful_tests}")
        print(f"失败测试: {total_tests - successful_tests}")
        print(f"成功率: {success_rate:.1f}%")
        print(f"详细报告: {report_filename}")
        print("="*60)
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 检查API端点测试结果
        api_results = self.test_results.get("api_endpoints", [])
        failed_apis = [r for r in api_results if r["status"] == "error"]
        
        if failed_apis:
            recommendations.append(f"有 {len(failed_apis)} 个API端点测试失败，需要检查服务状态")
        
        # 检查响应时间
        slow_apis = [r for r in api_results if r.get("response_time", "0ms").replace("ms", "").replace("timeout", "999999").isdigit() and float(r["response_time"].replace("ms", "")) > 1000]
        
        if slow_apis:
            recommendations.append(f"有 {len(slow_apis)} 个API响应时间超过1秒，建议优化性能")
        
        # 检查WebSocket连接
        ws_result = self.test_results.get("websocket", {})
        if ws_result.get("status") != "success":
            recommendations.append("WebSocket连接异常，需要检查WebSocket服务")
        
        # 检查通知系统
        notification_results = self.test_results.get("notifications", [])
        failed_notifications = [r for r in notification_results if r["status"] == "error"]
        
        if failed_notifications:
            recommendations.append(f"有 {len(failed_notifications)} 个通知功能测试失败，需要检查通知配置")
        
        # 检查工作流
        workflow_result = self.test_results.get("workflow", {})
        if workflow_result.get("failed_steps", 0) > 0:
            recommendations.append(f"工作流测试有 {workflow_result['failed_steps']} 个步骤失败，需要检查业务逻辑流程")
        
        if not recommendations:
            recommendations.append("所有测试通过，系统运行正常")
        
        return recommendations

def main():
    """主函数"""
    print("SuperInsight 业务逻辑功能综合测试")
    print("="*50)
    
    # 检查服务是否运行
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("❌ 后端服务未运行，请先启动 simple_app.py")
            return
    except:
        print("❌ 无法连接到后端服务，请确保服务在 http://localhost:8000 运行")
        return
    
    print("✅ 后端服务连接正常")
    print()
    
    # 运行测试
    tester = BusinessLogicTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()