# 自定义算法开发指南

## 概述

SuperInsight 平台支持开发和集成自定义业务逻辑分析算法。本指南将详细介绍如何开发、测试和部署自定义算法，以满足特定的业务需求。

## 算法架构

### 基础算法接口

所有自定义算法都需要实现 `BaseAlgorithm` 接口：

```python
# src/business_logic/base_algorithm.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from pydantic import BaseModel

class AlgorithmResult(BaseModel):
    """算法结果基类"""
    algorithm_name: str
    confidence: float
    patterns: List[Dict[str, Any]]
    metadata: Dict[str, Any]

class BaseAlgorithm(ABC):
    """算法基类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
        
    @abstractmethod
    async def analyze(self, data: List[Dict[str, Any]]) -> AlgorithmResult:
        """分析数据并返回结果"""
        pass
        
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置参数"""
        pass
        
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """获取必需的数据字段"""
        pass
```

## 开发自定义算法

### 1. 创建算法类

```python
# algorithms/custom_sentiment_analyzer.py
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from src.business_logic.base_algorithm import BaseAlgorithm, AlgorithmResult

class CustomSentimentAnalyzer(BaseAlgorithm):
    """自定义情感分析算法"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.min_cluster_size = config.get('min_cluster_size', 5)
        self.max_clusters = config.get('max_clusters', 10)
        self.vectorizer = TfidfVectorizer(
            max_features=config.get('max_features', 1000),
            stop_words='english'
        )
        
    async def analyze(self, data: List[Dict[str, Any]]) -> AlgorithmResult:
        """执行自定义情感分析"""
        try:
            # 数据预处理
            texts = [item.get('content', '') for item in data]
            sentiments = [item.get('sentiment', 'neutral') for item in data]
            
            # 特征提取
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            
            # 聚类分析
            n_clusters = min(self.max_clusters, len(texts) // self.min_cluster_size)
            if n_clusters < 2:
                n_clusters = 2
                
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            clusters = kmeans.fit_predict(tfidf_matrix)
            
            # 分析每个聚类的情感分布
            patterns = []
            for cluster_id in range(n_clusters):
                cluster_mask = clusters == cluster_id
                cluster_sentiments = [s for i, s in enumerate(sentiments) if cluster_mask[i]]
                
                if len(cluster_sentiments) >= self.min_cluster_size:
                    sentiment_dist = self._calculate_sentiment_distribution(cluster_sentiments)
                    dominant_sentiment = max(sentiment_dist, key=sentiment_dist.get)
                    
                    # 提取关键词
                    cluster_texts = [t for i, t in enumerate(texts) if cluster_mask[i]]
                    keywords = self._extract_keywords(cluster_texts)
                    
                    pattern = {
                        'cluster_id': cluster_id,
                        'size': len(cluster_sentiments),
                        'dominant_sentiment': dominant_sentiment,
                        'sentiment_distribution': sentiment_dist,
                        'keywords': keywords,
                        'confidence': sentiment_dist[dominant_sentiment]
                    }
                    patterns.append(pattern)
            
            # 计算整体置信度
            overall_confidence = np.mean([p['confidence'] for p in patterns])
            
            return AlgorithmResult(
                algorithm_name=self.name,
                confidence=overall_confidence,
                patterns=patterns,
                metadata={
                    'total_clusters': n_clusters,
                    'total_documents': len(texts),
                    'feature_count': tfidf_matrix.shape[1]
                }
            )
            
        except Exception as e:
            raise RuntimeError(f"算法执行失败: {str(e)}")
    
    def _calculate_sentiment_distribution(self, sentiments: List[str]) -> Dict[str, float]:
        """计算情感分布"""
        from collections import Counter
        counts = Counter(sentiments)
        total = len(sentiments)
        return {sentiment: count / total for sentiment, count in counts.items()}
    
    def _extract_keywords(self, texts: List[str]) -> List[str]:
        """提取关键词"""
        if not texts:
            return []
            
        # 重新训练向量化器用于关键词提取
        vectorizer = TfidfVectorizer(max_features=10, stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(texts)
        
        # 获取特征名称（关键词）
        feature_names = vectorizer.get_feature_names_out()
        
        # 计算平均 TF-IDF 分数
        mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)
        
        # 按分数排序并返回前 10 个关键词
        keyword_scores = list(zip(feature_names, mean_scores))
        keyword_scores.sort(key=lambda x: x[1], reverse=True)
        
        return [keyword for keyword, score in keyword_scores[:10]]
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置参数"""
        required_keys = ['min_cluster_size', 'max_clusters']
        for key in required_keys:
            if key not in config:
                return False
                
        if config['min_cluster_size'] < 1:
            return False
            
        if config['max_clusters'] < 2:
            return False
            
        return True
    
    def get_required_fields(self) -> List[str]:
        """获取必需的数据字段"""
        return ['content', 'sentiment']
```

### 2. 注册算法

```python
# src/business_logic/algorithm_registry.py
from typing import Dict, Type
from src.business_logic.base_algorithm import BaseAlgorithm

class AlgorithmRegistry:
    """算法注册表"""
    
    def __init__(self):
        self._algorithms: Dict[str, Type[BaseAlgorithm]] = {}
    
    def register(self, name: str, algorithm_class: Type[BaseAlgorithm]):
        """注册算法"""
        self._algorithms[name] = algorithm_class
    
    def get_algorithm(self, name: str) -> Type[BaseAlgorithm]:
        """获取算法类"""
        if name not in self._algorithms:
            raise ValueError(f"未找到算法: {name}")
        return self._algorithms[name]
    
    def list_algorithms(self) -> List[str]:
        """列出所有已注册的算法"""
        return list(self._algorithms.keys())

# 全局注册表实例
algorithm_registry = AlgorithmRegistry()

# 注册自定义算法
from algorithms.custom_sentiment_analyzer import CustomSentimentAnalyzer
algorithm_registry.register('custom_sentiment_analyzer', CustomSentimentAnalyzer)
```

### 3. 算法配置

```python
# config/algorithm_configs.py
ALGORITHM_CONFIGS = {
    'custom_sentiment_analyzer': {
        'min_cluster_size': 5,
        'max_clusters': 8,
        'max_features': 1000,
        'description': '自定义情感聚类分析算法',
        'version': '1.0.0',
        'author': 'SuperInsight Team'
    }
}
```

## 算法测试

### 1. 单元测试

```python
# tests/test_custom_sentiment_analyzer.py
import pytest
import asyncio
from algorithms.custom_sentiment_analyzer import CustomSentimentAnalyzer

class TestCustomSentimentAnalyzer:
    
    @pytest.fixture
    def algorithm(self):
        config = {
            'min_cluster_size': 3,
            'max_clusters': 5,
            'max_features': 100
        }
        return CustomSentimentAnalyzer(config)
    
    @pytest.fixture
    def sample_data(self):
        return [
            {'content': 'I love this product', 'sentiment': 'positive'},
            {'content': 'This is amazing', 'sentiment': 'positive'},
            {'content': 'Great quality', 'sentiment': 'positive'},
            {'content': 'I hate this', 'sentiment': 'negative'},
            {'content': 'Terrible experience', 'sentiment': 'negative'},
            {'content': 'Bad quality', 'sentiment': 'negative'},
            {'content': 'It is okay', 'sentiment': 'neutral'},
            {'content': 'Average product', 'sentiment': 'neutral'},
        ]
    
    @pytest.mark.asyncio
    async def test_analyze_basic(self, algorithm, sample_data):
        """测试基本分析功能"""
        result = await algorithm.analyze(sample_data)
        
        assert result.algorithm_name == 'CustomSentimentAnalyzer'
        assert 0 <= result.confidence <= 1
        assert len(result.patterns) > 0
        assert 'total_clusters' in result.metadata
    
    @pytest.mark.asyncio
    async def test_analyze_empty_data(self, algorithm):
        """测试空数据处理"""
        with pytest.raises(RuntimeError):
            await algorithm.analyze([])
    
    def test_validate_config_valid(self, algorithm):
        """测试有效配置验证"""
        valid_config = {
            'min_cluster_size': 5,
            'max_clusters': 10
        }
        assert algorithm.validate_config(valid_config) == True
    
    def test_validate_config_invalid(self, algorithm):
        """测试无效配置验证"""
        invalid_config = {
            'min_cluster_size': 0,
            'max_clusters': 1
        }
        assert algorithm.validate_config(invalid_config) == False
    
    def test_get_required_fields(self, algorithm):
        """测试必需字段获取"""
        fields = algorithm.get_required_fields()
        assert 'content' in fields
        assert 'sentiment' in fields
```

### 2. 集成测试

```python
# tests/test_algorithm_integration.py
import pytest
from src.business_logic.algorithm_manager import AlgorithmManager
from src.business_logic.algorithm_registry import algorithm_registry

class TestAlgorithmIntegration:
    
    @pytest.fixture
    def algorithm_manager(self):
        return AlgorithmManager()
    
    @pytest.mark.asyncio
    async def test_custom_algorithm_execution(self, algorithm_manager):
        """测试自定义算法执行"""
        # 准备测试数据
        project_data = {
            'project_id': 'test_project',
            'data': [
                {'content': 'Great product', 'sentiment': 'positive'},
                {'content': 'Love it', 'sentiment': 'positive'},
                {'content': 'Hate this', 'sentiment': 'negative'},
                {'content': 'Bad quality', 'sentiment': 'negative'},
            ]
        }
        
        # 执行算法
        result = await algorithm_manager.run_algorithm(
            'custom_sentiment_analyzer',
            project_data['data']
        )
        
        assert result is not None
        assert result.algorithm_name == 'CustomSentimentAnalyzer'
        assert len(result.patterns) > 0
    
    def test_algorithm_registry(self):
        """测试算法注册表"""
        algorithms = algorithm_registry.list_algorithms()
        assert 'custom_sentiment_analyzer' in algorithms
        
        algorithm_class = algorithm_registry.get_algorithm('custom_sentiment_analyzer')
        assert algorithm_class is not None
```

## 性能优化

### 1. 并行处理

```python
# algorithms/parallel_processor.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

class ParallelAlgorithmProcessor:
    """并行算法处理器"""
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def process_in_parallel(
        self, 
        algorithm: BaseAlgorithm, 
        data_chunks: List[List[Dict[str, Any]]]
    ) -> List[AlgorithmResult]:
        """并行处理数据块"""
        tasks = []
        
        for chunk in data_chunks:
            task = asyncio.create_task(
                self._process_chunk(algorithm, chunk)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return results
    
    async def _process_chunk(
        self, 
        algorithm: BaseAlgorithm, 
        chunk: List[Dict[str, Any]]
    ) -> AlgorithmResult:
        """处理单个数据块"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            lambda: asyncio.run(algorithm.analyze(chunk))
        )
```

### 2. 缓存机制

```python
# algorithms/cached_algorithm.py
import hashlib
import json
from typing import Dict, Any, Optional
from src.business_logic.base_algorithm import BaseAlgorithm, AlgorithmResult

class CachedAlgorithm(BaseAlgorithm):
    """带缓存的算法包装器"""
    
    def __init__(self, algorithm: BaseAlgorithm, cache_manager):
        self.algorithm = algorithm
        self.cache_manager = cache_manager
        self.cache_ttl = 3600  # 1小时
    
    async def analyze(self, data: List[Dict[str, Any]]) -> AlgorithmResult:
        """带缓存的分析"""
        # 生成缓存键
        cache_key = self._generate_cache_key(data)
        
        # 尝试从缓存获取结果
        cached_result = await self.cache_manager.get(cache_key)
        if cached_result:
            return AlgorithmResult.parse_obj(cached_result)
        
        # 执行算法
        result = await self.algorithm.analyze(data)
        
        # 缓存结果
        await self.cache_manager.set(
            cache_key, 
            result.dict(), 
            ttl=self.cache_ttl
        )
        
        return result
    
    def _generate_cache_key(self, data: List[Dict[str, Any]]) -> str:
        """生成缓存键"""
        # 创建数据的哈希值
        data_str = json.dumps(data, sort_keys=True)
        data_hash = hashlib.md5(data_str.encode()).hexdigest()
        
        # 包含算法名称和配置
        config_str = json.dumps(self.algorithm.config, sort_keys=True)
        config_hash = hashlib.md5(config_str.encode()).hexdigest()
        
        return f"algorithm:{self.algorithm.name}:{config_hash}:{data_hash}"
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        return self.algorithm.validate_config(config)
    
    def get_required_fields(self) -> List[str]:
        return self.algorithm.get_required_fields()
```

## 部署和监控

### 1. 算法部署

```python
# deployment/algorithm_deployer.py
import importlib
import os
from typing import Dict, Any
from src.business_logic.algorithm_registry import algorithm_registry

class AlgorithmDeployer:
    """算法部署器"""
    
    def __init__(self, algorithms_dir: str = "algorithms"):
        self.algorithms_dir = algorithms_dir
    
    def deploy_algorithm(self, algorithm_file: str, config: Dict[str, Any]):
        """部署算法"""
        try:
            # 动态导入算法模块
            module_name = algorithm_file.replace('.py', '')
            module_path = f"{self.algorithms_dir}.{module_name}"
            
            module = importlib.import_module(module_path)
            
            # 查找算法类
            algorithm_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BaseAlgorithm) and 
                    attr != BaseAlgorithm):
                    algorithm_class = attr
                    break
            
            if not algorithm_class:
                raise ValueError(f"未找到算法类: {algorithm_file}")
            
            # 验证配置
            temp_instance = algorithm_class(config)
            if not temp_instance.validate_config(config):
                raise ValueError("算法配置验证失败")
            
            # 注册算法
            algorithm_name = config.get('name', algorithm_class.__name__)
            algorithm_registry.register(algorithm_name, algorithm_class)
            
            return {
                'status': 'success',
                'algorithm_name': algorithm_name,
                'class_name': algorithm_class.__name__
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def list_available_algorithms(self) -> List[str]:
        """列出可用的算法文件"""
        algorithms = []
        
        if os.path.exists(self.algorithms_dir):
            for file in os.listdir(self.algorithms_dir):
                if file.endswith('.py') and not file.startswith('__'):
                    algorithms.append(file)
        
        return algorithms
```

### 2. 算法监控

```python
# monitoring/algorithm_monitor.py
import time
import logging
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge

# 监控指标
algorithm_executions = Counter(
    'algorithm_executions_total', 
    'Total algorithm executions',
    ['algorithm_name', 'status']
)

algorithm_duration = Histogram(
    'algorithm_duration_seconds',
    'Algorithm execution duration',
    ['algorithm_name']
)

algorithm_data_size = Histogram(
    'algorithm_data_size',
    'Size of data processed by algorithm',
    ['algorithm_name']
)

class AlgorithmMonitor:
    """算法监控器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def track_execution(self, algorithm_name: str, data_size: int):
        """跟踪算法执行"""
        algorithm_data_size.labels(algorithm_name=algorithm_name).observe(data_size)
        
        return AlgorithmExecutionContext(algorithm_name, self.logger)

class AlgorithmExecutionContext:
    """算法执行上下文"""
    
    def __init__(self, algorithm_name: str, logger):
        self.algorithm_name = algorithm_name
        self.logger = logger
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"开始执行算法: {self.algorithm_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type is None:
            status = 'success'
            self.logger.info(f"算法执行成功: {self.algorithm_name}, 耗时: {duration:.2f}s")
        else:
            status = 'error'
            self.logger.error(f"算法执行失败: {self.algorithm_name}, 错误: {exc_val}")
        
        algorithm_executions.labels(
            algorithm_name=self.algorithm_name,
            status=status
        ).inc()
        
        algorithm_duration.labels(
            algorithm_name=self.algorithm_name
        ).observe(duration)
```

## 最佳实践

### 1. 算法设计原则
- **单一职责**: 每个算法只负责一个特定的分析任务
- **可配置性**: 通过配置参数调整算法行为
- **错误处理**: 优雅处理异常情况
- **性能考虑**: 对大数据集进行优化

### 2. 代码质量
- **类型注解**: 使用 Python 类型注解提高代码可读性
- **文档字符串**: 为所有公共方法添加详细的文档
- **单元测试**: 确保算法的正确性和稳定性
- **代码审查**: 通过代码审查保证质量

### 3. 部署建议
- **版本控制**: 为算法版本进行标记和管理
- **渐进部署**: 先在测试环境验证再部署到生产环境
- **监控告警**: 设置关键指标的监控和告警
- **回滚机制**: 准备算法回滚方案

## 示例：完整的自定义算法

```python
# algorithms/keyword_trend_analyzer.py
"""
关键词趋势分析算法
分析关键词在时间序列中的变化趋势
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any
from sklearn.preprocessing import StandardScaler
from scipy import stats
from src.business_logic.base_algorithm import BaseAlgorithm, AlgorithmResult

class KeywordTrendAnalyzer(BaseAlgorithm):
    """关键词趋势分析算法"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.time_window = config.get('time_window', 30)  # 天
        self.min_occurrences = config.get('min_occurrences', 5)
        self.trend_threshold = config.get('trend_threshold', 0.1)
    
    async def analyze(self, data: List[Dict[str, Any]]) -> AlgorithmResult:
        """分析关键词趋势"""
        try:
            # 数据预处理
            df = pd.DataFrame(data)
            df['created_at'] = pd.to_datetime(df['created_at'])
            df = df.sort_values('created_at')
            
            # 提取关键词
            keywords = self._extract_keywords(df)
            
            # 分析每个关键词的趋势
            patterns = []
            for keyword in keywords:
                trend_data = self._analyze_keyword_trend(df, keyword)
                if trend_data['significance'] > self.trend_threshold:
                    patterns.append(trend_data)
            
            # 计算整体置信度
            confidence = np.mean([p['significance'] for p in patterns]) if patterns else 0
            
            return AlgorithmResult(
                algorithm_name=self.name,
                confidence=confidence,
                patterns=patterns,
                metadata={
                    'total_keywords': len(keywords),
                    'significant_trends': len(patterns),
                    'time_range': {
                        'start': df['created_at'].min().isoformat(),
                        'end': df['created_at'].max().isoformat()
                    }
                }
            )
            
        except Exception as e:
            raise RuntimeError(f"关键词趋势分析失败: {str(e)}")
    
    def _extract_keywords(self, df: pd.DataFrame) -> List[str]:
        """提取关键词"""
        from collections import Counter
        import re
        
        all_words = []
        for content in df['content']:
            words = re.findall(r'\b\w+\b', content.lower())
            all_words.extend(words)
        
        # 过滤高频词
        word_counts = Counter(all_words)
        keywords = [word for word, count in word_counts.items() 
                   if count >= self.min_occurrences and len(word) > 2]
        
        return keywords[:50]  # 限制关键词数量
    
    def _analyze_keyword_trend(self, df: pd.DataFrame, keyword: str) -> Dict[str, Any]:
        """分析单个关键词的趋势"""
        # 创建时间序列
        df_keyword = df[df['content'].str.contains(keyword, case=False, na=False)]
        
        # 按天聚合
        daily_counts = df_keyword.groupby(df_keyword['created_at'].dt.date).size()
        
        # 填充缺失日期
        date_range = pd.date_range(
            start=df['created_at'].min().date(),
            end=df['created_at'].max().date(),
            freq='D'
        )
        daily_counts = daily_counts.reindex(date_range.date, fill_value=0)
        
        # 计算趋势
        x = np.arange(len(daily_counts))
        y = daily_counts.values
        
        # 线性回归
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # 计算趋势方向和强度
        trend_direction = 'increasing' if slope > 0 else 'decreasing'
        trend_strength = abs(r_value)
        
        return {
            'keyword': keyword,
            'trend_direction': trend_direction,
            'slope': slope,
            'r_squared': r_value ** 2,
            'p_value': p_value,
            'significance': trend_strength,
            'total_occurrences': len(df_keyword),
            'daily_average': daily_counts.mean(),
            'peak_date': daily_counts.idxmax().isoformat() if len(daily_counts) > 0 else None
        }
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        required_keys = ['time_window', 'min_occurrences', 'trend_threshold']
        
        for key in required_keys:
            if key not in config:
                return False
        
        if config['time_window'] < 1:
            return False
            
        if config['min_occurrences'] < 1:
            return False
            
        if not 0 <= config['trend_threshold'] <= 1:
            return False
        
        return True
    
    def get_required_fields(self) -> List[str]:
        """获取必需字段"""
        return ['content', 'created_at']
```

## 总结

通过本指南，您可以：

1. **理解算法架构**: 掌握 SuperInsight 平台的算法设计模式
2. **开发自定义算法**: 创建满足特定需求的分析算法
3. **测试和验证**: 确保算法的正确性和性能
4. **部署和监控**: 将算法安全地部署到生产环境

自定义算法开发让您能够扩展平台的分析能力，满足独特的业务需求。记住遵循最佳实践，确保算法的质量和可维护性。

---

**SuperInsight 自定义算法开发指南** - 释放无限分析潜能