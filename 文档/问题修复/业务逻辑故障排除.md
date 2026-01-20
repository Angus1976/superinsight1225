# 业务逻辑功能故障排查指南

## 概述

本指南帮助您快速诊断和解决 SuperInsight 业务逻辑提炼与智能化功能中可能遇到的问题。按照问题类型分类，提供详细的排查步骤和解决方案。

## 快速诊断工具

### 系统健康检查

首先运行系统健康检查来快速识别问题：

```bash
# 检查业务逻辑服务状态
curl -X GET "http://localhost:8000/api/business-logic/health"

# 预期响应
{
  "status": "healthy",
  "service": "business-logic",
  "timestamp": "2026-01-05T10:30:00Z",
  "version": "1.0.0"
}
```

### 服务依赖检查

```bash
# 检查数据库连接
python -c "
from src.database import get_db_connection
try:
    conn = get_db_connection()
    print('✅ 数据库连接正常')
except Exception as e:
    print(f'❌ 数据库连接失败: {e}')
"

# 检查 Redis 缓存
python -c "
import redis
try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.ping()
    print('✅ Redis 连接正常')
except Exception as e:
    print(f'❌ Redis 连接失败: {e}')
"

# 检查 NLP 模型
python -c "
import spacy
try:
    nlp = spacy.load('en_core_web_sm')
    print('✅ spaCy 模型加载正常')
except Exception as e:
    print(f'❌ spaCy 模型加载失败: {e}')
"
```

## 常见问题分类

### 1. 分析性能问题

#### 问题症状
- 分析任务执行时间过长 (>5分钟)
- 系统响应缓慢或超时
- 内存使用率过高

#### 排查步骤

**步骤 1: 检查数据量**
```python
# 检查项目数据量
import pandas as pd
from src.database import get_annotations

def check_data_size(project_id):
    annotations = get_annotations(project_id)
    data_size = len(annotations)
    
    print(f"项目 {project_id} 数据量: {data_size} 条")
    
    if data_size > 50000:
        print("⚠️  数据量过大，建议分批处理")
    elif data_size < 100:
        print("⚠️  数据量过小，可能影响分析质量")
    else:
        print("✅ 数据量适中")
    
    return data_size

# 使用示例
check_data_size("your_project_id")
```

**步骤 2: 检查系统资源**
```bash
# 检查 CPU 使用率
top -p $(pgrep -f "business_logic")

# 检查内存使用
ps aux | grep business_logic | awk '{print $4, $6}'

# 检查磁盘空间
df -h /tmp  # 检查临时文件空间
```

**步骤 3: 优化分析参数**
```python
# 推荐的参数设置
optimization_params = {
    "small_dataset": {  # < 1000 条
        "min_confidence": 0.6,
        "min_support": 3,
        "max_features": 500,
        "batch_size": 100
    },
    "medium_dataset": {  # 1000-10000 条
        "min_confidence": 0.7,
        "min_support": 5,
        "max_features": 1000,
        "batch_size": 500
    },
    "large_dataset": {  # > 10000 条
        "min_confidence": 0.8,
        "min_support": 10,
        "max_features": 1500,
        "batch_size": 1000
    }
}
```

#### 解决方案

**方案 1: 启用批处理模式**
```python
# 修改分析请求，启用批处理
analysis_request = {
    "project_id": "your_project_id",
    "analysis_types": ["sentiment_correlation"],
    "batch_processing": True,
    "batch_size": 1000,
    "parallel_workers": 4
}
```

**方案 2: 使用缓存**
```python
# 启用结果缓存
analysis_request = {
    "project_id": "your_project_id",
    "use_cache": True,
    "cache_ttl": 3600  # 1小时缓存
}
```

**方案 3: 分时段分析**
```python
# 分时段分析大数据集
import datetime

def analyze_by_time_periods(project_id, days_per_batch=7):
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=30)
    
    current_date = start_date
    results = []
    
    while current_date < end_date:
        batch_end = current_date + datetime.timedelta(days=days_per_batch)
        
        batch_request = {
            "project_id": project_id,
            "time_range": {
                "start_date": current_date.isoformat(),
                "end_date": batch_end.isoformat()
            }
        }
        
        batch_result = analyze_patterns(batch_request)
        results.append(batch_result)
        
        current_date = batch_end
    
    return merge_analysis_results(results)
```

### 2. 分析结果异常

#### 问题症状
- 分析结果为空或数量异常少
- 置信度异常低或异常高
- 规则逻辑不合理

#### 排查步骤

**步骤 1: 数据质量检查**
```python
def diagnose_data_quality(project_id):
    annotations = get_annotations(project_id)
    df = pd.DataFrame(annotations)
    
    print("=== 数据质量诊断 ===")
    
    # 基本统计
    print(f"总记录数: {len(df)}")
    print(f"字段数: {len(df.columns)}")
    
    # 缺失值检查
    missing_data = df.isnull().sum()
    print("\n缺失值统计:")
    for col, missing_count in missing_data.items():
        if missing_count > 0:
            percentage = (missing_count / len(df)) * 100
            print(f"  {col}: {missing_count} ({percentage:.1f}%)")
    
    # 数据分布检查
    if 'sentiment' in df.columns:
        sentiment_dist = df['sentiment'].value_counts()
        print(f"\n情感分布:")
        for sentiment, count in sentiment_dist.items():
            percentage = (count / len(df)) * 100
            print(f"  {sentiment}: {count} ({percentage:.1f}%)")
        
        # 检查数据倾斜
        max_percentage = max(sentiment_dist.values) / len(df) * 100
        if max_percentage > 80:
            print("⚠️  数据严重倾斜，可能影响分析质量")
    
    # 文本质量检查
    if 'text' in df.columns:
        text_lengths = df['text'].str.len()
        print(f"\n文本长度统计:")
        print(f"  平均长度: {text_lengths.mean():.1f}")
        print(f"  最短: {text_lengths.min()}")
        print(f"  最长: {text_lengths.max()}")
        
        # 检查空文本
        empty_texts = (text_lengths == 0).sum()
        if empty_texts > 0:
            print(f"⚠️  发现 {empty_texts} 条空文本")
    
    return df

# 使用示例
diagnose_data_quality("your_project_id")
```

**步骤 2: 参数合理性检查**
```python
def validate_analysis_parameters(params):
    issues = []
    
    # 检查置信度阈值
    if params.get('min_confidence', 0) > 0.9:
        issues.append("置信度阈值过高，可能导致结果过少")
    elif params.get('min_confidence', 0) < 0.5:
        issues.append("置信度阈值过低，可能产生噪音结果")
    
    # 检查支持度阈值
    if params.get('min_support', 0) > 50:
        issues.append("支持度阈值过高，可能错过重要模式")
    elif params.get('min_support', 0) < 2:
        issues.append("支持度阈值过低，可能产生偶然模式")
    
    # 检查时间范围
    if 'time_range' in params:
        start = datetime.datetime.fromisoformat(params['time_range']['start_date'])
        end = datetime.datetime.fromisoformat(params['time_range']['end_date'])
        days_diff = (end - start).days
        
        if days_diff > 365:
            issues.append("时间范围过长，建议分段分析")
        elif days_diff < 7:
            issues.append("时间范围过短，可能数据不足")
    
    if issues:
        print("参数问题:")
        for issue in issues:
            print(f"  ⚠️  {issue}")
    else:
        print("✅ 参数设置合理")
    
    return len(issues) == 0
```

#### 解决方案

**方案 1: 数据预处理**
```python
def preprocess_data_for_analysis(df):
    """数据预处理以提高分析质量"""
    
    # 1. 清理空值
    df = df.dropna(subset=['text', 'sentiment'])
    
    # 2. 文本清理
    df['text'] = df['text'].str.strip()
    df = df[df['text'].str.len() > 0]  # 移除空文本
    
    # 3. 标准化情感标签
    sentiment_mapping = {
        'pos': 'positive',
        'neg': 'negative',
        'neu': 'neutral',
        '1': 'positive',
        '0': 'neutral',
        '-1': 'negative'
    }
    df['sentiment'] = df['sentiment'].map(sentiment_mapping).fillna(df['sentiment'])
    
    # 4. 过滤异常长度文本
    text_lengths = df['text'].str.len()
    q1, q3 = text_lengths.quantile([0.25, 0.75])
    iqr = q3 - q1
    lower_bound = max(10, q1 - 1.5 * iqr)  # 最少10个字符
    upper_bound = q3 + 1.5 * iqr
    
    df = df[(text_lengths >= lower_bound) & (text_lengths <= upper_bound)]
    
    print(f"预处理后数据量: {len(df)}")
    return df
```

**方案 2: 调整分析策略**
```python
def adaptive_analysis_strategy(data_size, data_quality_score):
    """根据数据特征自适应调整分析策略"""
    
    if data_size < 100:
        return {
            "min_confidence": 0.5,
            "min_support": 2,
            "analysis_types": ["sentiment_correlation"],  # 简化分析
            "use_advanced_nlp": False
        }
    elif data_size < 1000:
        return {
            "min_confidence": 0.6,
            "min_support": 3,
            "analysis_types": ["sentiment_correlation", "keyword_cooccurrence"],
            "use_advanced_nlp": True
        }
    else:
        return {
            "min_confidence": 0.7,
            "min_support": 5,
            "analysis_types": ["sentiment_correlation", "keyword_cooccurrence", 
                             "temporal_trends", "user_behavior"],
            "use_advanced_nlp": True,
            "enable_caching": True
        }
```

### 3. API 调用问题

#### 问题症状
- API 请求超时
- 返回 500 内部服务器错误
- 认证失败

#### 排查步骤

**步骤 1: 检查 API 服务状态**
```bash
# 检查服务是否运行
curl -X GET "http://localhost:8000/api/business-logic/health"

# 检查服务日志
tail -f logs/app.log | grep "business-logic"

# 检查错误日志
tail -f logs/errors.log | grep "ERROR"
```

**步骤 2: 验证请求格式**
```python
import requests
import json

def test_api_request():
    url = "http://localhost:8000/api/business-logic/analyze"
    headers = {
        "Authorization": "Bearer your_jwt_token",
        "Content-Type": "application/json"
    }
    
    # 最小化测试请求
    test_data = {
        "project_id": "test_project",
        "analysis_types": ["sentiment_correlation"],
        "min_confidence": 0.7
    }
    
    try:
        response = requests.post(url, json=test_data, headers=headers, timeout=30)
        
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API 调用成功")
            print(f"返回数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ API 调用失败: {response.text}")
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except requests.exceptions.ConnectionError:
        print("❌ 连接错误")
    except Exception as e:
        print(f"❌ 其他错误: {e}")

test_api_request()
```

#### 解决方案

**方案 1: 重启服务**
```bash
# 停止服务
pkill -f "business_logic"

# 清理临时文件
rm -rf /tmp/business_logic_*

# 重启服务
python -m src.business_logic.api &

# 验证服务启动
sleep 5
curl -X GET "http://localhost:8000/api/business-logic/health"
```

**方案 2: 检查和修复配置**
```python
# 检查配置文件
import os
from src.config import settings

def validate_configuration():
    required_settings = [
        'DATABASE_URL',
        'REDIS_URL',
        'JWT_SECRET_KEY'
    ]
    
    missing_settings = []
    for setting in required_settings:
        if not getattr(settings, setting, None):
            missing_settings.append(setting)
    
    if missing_settings:
        print("❌ 缺少必要配置:")
        for setting in missing_settings:
            print(f"  - {setting}")
        return False
    
    print("✅ 配置检查通过")
    return True

validate_configuration()
```

### 4. 前端界面问题

#### 问题症状
- 页面加载失败或白屏
- 图表显示异常
- 数据更新不及时

#### 排查步骤

**步骤 1: 检查浏览器控制台**
```javascript
// 在浏览器控制台中运行
console.log("检查 JavaScript 错误:");
console.log(window.errors || "无错误");

// 检查网络请求
console.log("检查网络请求:");
performance.getEntriesByType("navigation").forEach(entry => {
    console.log(`页面加载时间: ${entry.loadEventEnd - entry.loadEventStart}ms`);
});

// 检查 API 调用
fetch('/api/business-logic/health')
    .then(response => response.json())
    .then(data => console.log('API 健康检查:', data))
    .catch(error => console.error('API 调用失败:', error));
```

**步骤 2: 检查前端服务**
```bash
# 检查前端服务状态
curl -X GET "http://localhost:3000"

# 检查前端构建
cd frontend
npm run build

# 检查依赖
npm audit
```

#### 解决方案

**方案 1: 清理缓存并重启**
```bash
# 清理浏览器缓存
# Chrome: Ctrl+Shift+Delete
# Firefox: Ctrl+Shift+Delete

# 清理前端缓存
cd frontend
rm -rf node_modules/.cache
rm -rf dist/

# 重新安装依赖
npm install

# 重启前端服务
npm run dev
```

**方案 2: 检查和修复前端配置**
```javascript
// 检查前端配置 (frontend/src/config.js)
const config = {
    API_BASE_URL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000',
    WS_URL: process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws',
    TIMEOUT: 30000
};

// 验证配置
console.log('前端配置:', config);

// 测试 API 连接
fetch(`${config.API_BASE_URL}/api/business-logic/health`)
    .then(response => {
        if (response.ok) {
            console.log('✅ API 连接正常');
        } else {
            console.log('❌ API 连接异常:', response.status);
        }
    })
    .catch(error => {
        console.log('❌ API 连接失败:', error);
    });
```

### 5. 数据库相关问题

#### 问题症状
- 数据库连接失败
- 查询超时
- 数据不一致

#### 排查步骤

**步骤 1: 检查数据库连接**
```python
import psycopg2
from src.config import settings

def test_database_connection():
    try:
        conn = psycopg2.connect(settings.DATABASE_URL)
        cursor = conn.cursor()
        
        # 测试基本查询
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ 数据库连接成功: {version[0]}")
        
        # 检查业务逻辑相关表
        tables = ['business_rules', 'business_patterns', 'business_insights']
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} 条记录")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")

test_database_connection()
```

**步骤 2: 检查数据库性能**
```sql
-- 检查慢查询
SELECT query, mean_time, calls, total_time
FROM pg_stat_statements
WHERE query LIKE '%business_%'
ORDER BY mean_time DESC
LIMIT 10;

-- 检查表大小
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE tablename LIKE 'business_%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 检查索引使用情况
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename LIKE 'business_%'
ORDER BY idx_scan DESC;
```

#### 解决方案

**方案 1: 优化数据库查询**
```python
# 添加查询优化
def optimized_rule_query(project_id, limit=100):
    query = """
    SELECT id, name, description, confidence, support, created_at
    FROM business_rules 
    WHERE project_id = %s 
    AND is_active = true
    ORDER BY confidence DESC, support DESC
    LIMIT %s
    """
    
    # 使用连接池
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (project_id, limit))
            return cursor.fetchall()
```

**方案 2: 数据库维护**
```sql
-- 更新表统计信息
ANALYZE business_rules;
ANALYZE business_patterns;
ANALYZE business_insights;

-- 重建索引
REINDEX TABLE business_rules;

-- 清理无用数据
DELETE FROM business_rules 
WHERE created_at < NOW() - INTERVAL '1 year' 
AND is_active = false;

-- 优化表空间
VACUUM FULL business_rules;
```

## 监控和预防

### 1. 设置监控告警

```python
# 监控脚本示例
import time
import requests
import smtplib
from email.mime.text import MIMEText

def monitor_business_logic_service():
    """监控业务逻辑服务健康状态"""
    
    while True:
        try:
            # 健康检查
            response = requests.get(
                "http://localhost:8000/api/business-logic/health",
                timeout=10
            )
            
            if response.status_code != 200:
                send_alert(f"业务逻辑服务异常: HTTP {response.status_code}")
            
            # 检查响应时间
            if response.elapsed.total_seconds() > 5:
                send_alert(f"业务逻辑服务响应缓慢: {response.elapsed.total_seconds()}s")
            
            print(f"✅ 服务正常 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            send_alert(f"业务逻辑服务不可用: {e}")
        
        time.sleep(60)  # 每分钟检查一次

def send_alert(message):
    """发送告警邮件"""
    # 实现邮件发送逻辑
    print(f"🚨 告警: {message}")

# 启动监控
if __name__ == "__main__":
    monitor_business_logic_service()
```

### 2. 日志配置

```python
# 配置详细日志
import logging
import sys

def setup_logging():
    """配置业务逻辑模块日志"""
    
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # 文件处理器
    file_handler = logging.FileHandler('logs/business_logic.log')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)
    
    # 配置根日志器
    logger = logging.getLogger('business_logic')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 使用示例
logger = setup_logging()
logger.info("业务逻辑服务启动")
```

### 3. 性能基准测试

```python
import time
import statistics
from concurrent.futures import ThreadPoolExecutor

def benchmark_analysis_performance():
    """业务逻辑分析性能基准测试"""
    
    test_cases = [
        {"data_size": 100, "expected_time": 5},
        {"data_size": 1000, "expected_time": 30},
        {"data_size": 5000, "expected_time": 120}
    ]
    
    results = []
    
    for case in test_cases:
        print(f"测试数据量: {case['data_size']} 条")
        
        # 生成测试数据
        test_data = generate_test_data(case['data_size'])
        
        # 执行多次测试
        times = []
        for i in range(3):
            start_time = time.time()
            result = analyze_patterns(test_data)
            end_time = time.time()
            
            execution_time = end_time - start_time
            times.append(execution_time)
            print(f"  第 {i+1} 次: {execution_time:.2f}s")
        
        avg_time = statistics.mean(times)
        std_time = statistics.stdev(times) if len(times) > 1 else 0
        
        results.append({
            "data_size": case['data_size'],
            "avg_time": avg_time,
            "std_time": std_time,
            "expected_time": case['expected_time'],
            "performance_ratio": case['expected_time'] / avg_time
        })
        
        # 性能评估
        if avg_time <= case['expected_time']:
            print(f"  ✅ 性能达标: {avg_time:.2f}s <= {case['expected_time']}s")
        else:
            print(f"  ❌ 性能不达标: {avg_time:.2f}s > {case['expected_time']}s")
    
    return results

# 运行基准测试
benchmark_results = benchmark_analysis_performance()
```

## 联系支持

如果按照本指南仍无法解决问题，请联系技术支持：

### 收集诊断信息

在联系支持前，请收集以下信息：

```bash
# 生成诊断报告
python -c "
import sys
import platform
import psutil
import pkg_resources

print('=== 系统信息 ===')
print(f'操作系统: {platform.system()} {platform.release()}')
print(f'Python 版本: {sys.version}')
print(f'CPU 核数: {psutil.cpu_count()}')
print(f'内存总量: {psutil.virtual_memory().total / 1024**3:.1f} GB')

print('\n=== 依赖版本 ===')
packages = ['fastapi', 'pandas', 'numpy', 'scikit-learn', 'spacy', 'nltk']
for package in packages:
    try:
        version = pkg_resources.get_distribution(package).version
        print(f'{package}: {version}')
    except:
        print(f'{package}: 未安装')

print('\n=== 服务状态 ===')
# 添加服务状态检查代码
"

# 收集日志
tail -n 100 logs/business_logic.log > diagnostic_logs.txt
tail -n 100 logs/errors.log >> diagnostic_logs.txt
```

### 支持渠道

1. **技术文档**: 查看 [API 参考文档](api-reference.md)
2. **用户指南**: 查看 [业务分析师指南](user-guides/business-analyst-guide.md)
3. **GitHub Issues**: 提交问题到项目仓库
4. **技术支持邮箱**: support@superinsight.ai

### 问题报告模板

```
问题标题: [简短描述问题]

环境信息:
- 操作系统: 
- Python 版本: 
- SuperInsight 版本: 
- 浏览器 (如适用): 

问题描述:
[详细描述遇到的问题]

重现步骤:
1. 
2. 
3. 

预期结果:
[描述期望的正常行为]

实际结果:
[描述实际发生的情况]

错误信息:
[粘贴相关的错误日志]

已尝试的解决方案:
[列出已经尝试过的解决方法]

附件:
- 诊断日志文件
- 截图 (如适用)
- 配置文件 (如适用)
```

---

通过本故障排查指南，您应该能够快速诊断和解决大部分常见问题。如果问题持续存在，请不要犹豫联系我们的技术支持团队。