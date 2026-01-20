#!/usr/bin/env python3
"""
API 诊断脚本 - 分步测试找出卡住的原因
"""

import requests
import time
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

def test_endpoint(name, url, timeout=3):
    """测试单个端点"""
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"URL: {url}")
    print(f"超时: {timeout}秒")
    print(f"{'='*60}")
    
    start_time = time.time()
    try:
        response = requests.get(url, timeout=timeout)
        elapsed = time.time() - start_time
        
        print(f"✓ 状态码: {response.status_code}")
        print(f"✓ 响应时间: {elapsed:.2f}秒")
        print(f"✓ 内容长度: {len(response.content)} bytes")
        
        # 尝试解析 JSON
        try:
            data = response.json()
            print(f"✓ JSON 解析成功")
            if isinstance(data, dict):
                print(f"  键: {list(data.keys())[:5]}")
        except:
            print(f"  响应不是 JSON 格式")
            print(f"  前100字符: {response.text[:100]}")
        
        return True, elapsed
        
    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"✗ 超时 ({elapsed:.2f}秒)")
        return False, elapsed
        
    except requests.exceptions.ConnectionError as e:
        elapsed = time.time() - start_time
        print(f"✗ 连接错误: {e}")
        return False, elapsed
        
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"✗ 错误: {type(e).__name__}: {e}")
        return False, elapsed

def main():
    print("="*60)
    print("SuperInsight API 诊断工具")
    print("="*60)
    
    base_url = "http://localhost:8000"
    
    # 定义测试端点（从简单到复杂）
    endpoints = [
        ("根路径", "/", 3),
        ("健康检查", "/health", 3),
        ("OpenAPI 文档", "/openapi.json", 5),
        ("Swagger UI", "/docs", 5),
        ("系统状态（简化）", "/api/v1/system/health", 5),
        ("系统状态（完整）", "/system/status", 10),
    ]
    
    results = []
    
    for name, path, timeout in endpoints:
        url = f"{base_url}{path}"
        success, elapsed = test_endpoint(name, url, timeout)
        results.append((name, success, elapsed))
        
        # 如果失败，不继续测试更复杂的端点
        if not success and elapsed >= timeout - 0.5:
            print(f"\n⚠️  {name} 超时，跳过后续测试")
            break
        
        # 短暂延迟
        time.sleep(0.5)
    
    # 总结
    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}")
    
    for name, success, elapsed in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{status:8} {name:30} {elapsed:6.2f}秒")
    
    # 分析
    print(f"\n{'='*60}")
    print("问题分析")
    print(f"{'='*60}")
    
    if not results:
        print("❌ 无法执行任何测试")
        return 1
    
    # 找出第一个失败的端点
    first_failure = None
    for name, success, elapsed in results:
        if not success:
            first_failure = name
            break
    
    if first_failure:
        print(f"❌ 第一个失败的端点: {first_failure}")
        print(f"\n可能的原因:")
        
        if first_failure in ["根路径", "健康检查"]:
            print("  1. API 服务未正常启动")
            print("  2. 端口映射问题")
            print("  3. 应用启动时卡在某个初始化步骤")
            print("\n建议:")
            print("  - 检查容器日志: docker compose logs superinsight-api")
            print("  - 检查容器状态: docker compose ps")
            print("  - 进入容器检查: docker exec -it superinsight-api sh")
            
        elif first_failure in ["系统状态（简化）", "系统状态（完整）"]:
            print("  1. 系统状态检查涉及多个服务连接")
            print("  2. 某个服务连接超时或卡住")
            print("  3. 数据库查询过慢")
            print("\n建议:")
            print("  - 检查 Redis 连接")
            print("  - 检查 PostgreSQL 连接")
            print("  - 检查 Neo4j 连接")
            print("  - 检查 Label Studio 连接")
            
        else:
            print(f"  端点 {first_failure} 存在问题")
            print("\n建议:")
            print("  - 查看应用日志获取详细错误信息")
            print("  - 检查该端点的代码实现")
    else:
        print("✓ 所有测试通过！")
        return 0
    
    return 1

if __name__ == "__main__":
    sys.exit(main())
