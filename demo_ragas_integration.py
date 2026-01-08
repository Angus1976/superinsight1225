#!/usr/bin/env python3
"""
Ragas Integration Demo Script.

Demonstrates the comprehensive Ragas evaluation system integration
including evaluation, trend analysis, and quality monitoring.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import Ragas integration components
from src.ragas_integration import (
    RagasEvaluator,
    RagasEvaluationResult,
    QualityTrendAnalyzer,
    QualityMonitor,
    MonitoringConfig
)
from src.models.annotation import Annotation
from uuid import uuid4


class RagasIntegrationDemo:
    """Demo class for Ragas integration functionality."""
    
    def __init__(self):
        """Initialize demo components."""
        self.evaluator = RagasEvaluator()
        self.trend_analyzer = QualityTrendAnalyzer()
        self.quality_monitor = QualityMonitor()
        
        # Demo data
        self.sample_annotations = self._create_sample_annotations()
    
    def _create_sample_annotations(self) -> List[Annotation]:
        """Create sample annotations for demonstration."""
        annotations = []
        
        # Sample Q&A data for different quality levels
        qa_samples = [
            {
                "question": "什么是机器学习？",
                "answer": "机器学习是人工智能的一个分支，它使计算机能够在没有明确编程的情况下学习和改进。通过算法和统计模型，机器学习系统可以从数据中识别模式并做出预测。",
                "context": "机器学习是一种数据分析方法，它自动化分析模型的构建。它是人工智能（AI）的一个分支，基于系统可以从数据中学习、识别模式并在最少人工干预的情况下做出决策的想法。",
                "ground_truth": "机器学习是人工智能的一个子领域，专注于开发能够从数据中学习的算法。",
                "quality_level": "high"
            },
            {
                "question": "深度学习和机器学习有什么区别？",
                "answer": "深度学习是机器学习的一个子集，使用多层神经网络来模拟人脑的工作方式。它特别适合处理大量数据和复杂模式识别任务。",
                "context": "深度学习是机器学习的一个特殊分支，它使用人工神经网络，特别是深度神经网络来学习数据表示。深度学习在图像识别、自然语言处理等领域取得了突破性进展。",
                "ground_truth": "深度学习是机器学习的一个子集，使用深度神经网络进行学习。",
                "quality_level": "high"
            },
            {
                "question": "什么是自然语言处理？",
                "answer": "NLP是计算机科学的一个领域。",
                "context": "自然语言处理（NLP）是人工智能和语言学的交叉领域，专注于使计算机能够理解、解释和生成人类语言。NLP结合了计算语言学、机器学习和深度学习模型，使计算机能够以有意义的方式处理人类语言。",
                "ground_truth": "自然语言处理是人工智能的一个分支，专注于计算机与人类语言之间的交互。",
                "quality_level": "low"
            },
            {
                "question": "什么是监督学习？",
                "answer": "监督学习是一种机器学习方法，使用标记的训练数据来学习输入和输出之间的映射关系。算法通过分析训练样本来学习，然后对新的未见过的数据进行预测。常见的监督学习任务包括分类和回归。",
                "context": "监督学习是机器学习的一种类型，其中算法从标记的训练数据中学习。训练数据包含输入-输出对，算法的目标是学习一个函数，该函数可以将输入映射到正确的输出。",
                "ground_truth": "监督学习是使用标记数据训练模型的机器学习方法。",
                "quality_level": "medium"
            },
            {
                "question": "什么是无监督学习？",
                "answer": "无监督学习处理没有标签的数据，试图发现数据中的隐藏模式。主要任务包括聚类、降维和关联规则学习。",
                "context": "无监督学习是机器学习的一种方法，其中算法试图从没有标记的数据中找到隐藏的模式或结构。与监督学习不同，无监督学习没有目标变量或正确答案来指导学习过程。",
                "ground_truth": "无监督学习是从未标记数据中发现模式的机器学习方法。",
                "quality_level": "medium"
            }
        ]
        
        for i, sample in enumerate(qa_samples):
            # Simulate different confidence levels based on quality
            if sample["quality_level"] == "high":
                confidence = random.uniform(0.85, 0.95)
            elif sample["quality_level"] == "medium":
                confidence = random.uniform(0.70, 0.85)
            else:
                confidence = random.uniform(0.50, 0.70)
            
            annotation = Annotation(
                id=uuid4(),
                task_id=uuid4(),
                annotator_id=f"demo_user_{i+1}",
                annotation_data=sample,
                confidence=confidence
            )
            annotations.append(annotation)
        
        return annotations
    
    async def demo_basic_evaluation(self):
        """Demonstrate basic Ragas evaluation."""
        print("\n" + "="*60)
        print("🔍 基础 Ragas 评估演示")
        print("="*60)
        
        # Check if Ragas is available
        if self.evaluator.is_available():
            print("✅ Ragas 库可用，将进行完整评估")
        else:
            print("⚠️  Ragas 库不可用，将进行基础评估")
        
        # Evaluate a subset of annotations
        test_annotations = self.sample_annotations[:3]
        
        print(f"\n📊 评估 {len(test_annotations)} 个标注样本...")
        
        result = await self.evaluator.evaluate_annotations(
            annotations=test_annotations,
            task_id="demo_task_001"
        )
        
        print(f"\n📈 评估结果:")
        print(f"  评估ID: {result.evaluation_id}")
        print(f"  整体分数: {result.overall_score:.3f}")
        
        if result.metrics:
            print(f"  详细指标:")
            for metric, score in result.metrics.items():
                print(f"    {metric}: {score:.3f}")
        
        # Add to trend analyzer for later demos
        self.trend_analyzer.add_evaluation_result(result)
        
        return result
    
    async def demo_batch_evaluation(self):
        """Demonstrate batch evaluation with trend tracking."""
        print("\n" + "="*60)
        print("📦 批量评估与趋势跟踪演示")
        print("="*60)
        
        # Simulate multiple evaluation sessions over time
        print("\n🔄 模拟多次评估会话...")
        
        for session in range(5):
            print(f"\n  会话 {session + 1}/5")
            
            # Select random annotations for each session
            session_annotations = random.sample(self.sample_annotations, 3)
            
            result = await self.evaluator.evaluate_annotations(
                annotations=session_annotations,
                task_id=f"demo_session_{session + 1}"
            )
            
            print(f"    整体分数: {result.overall_score:.3f}")
            
            # Add to trend analyzer
            self.trend_analyzer.add_evaluation_result(result)
            
            # Simulate time passage
            await asyncio.sleep(0.1)
        
        print("\n✅ 批量评估完成")
    
    def demo_trend_analysis(self):
        """Demonstrate trend analysis functionality."""
        print("\n" + "="*60)
        print("📈 质量趋势分析演示")
        print("="*60)
        
        # Analyze trends for all metrics
        trends = self.trend_analyzer.analyze_all_metrics()
        
        print(f"\n📊 发现 {len(trends)} 个指标的趋势:")
        
        for metric_name, trend in trends.items():
            print(f"\n  📌 {metric_name}:")
            print(f"    趋势方向: {trend.direction.value}")
            print(f"    当前值: {trend.current_value:.3f}")
            print(f"    置信度: {trend.confidence:.3f}")
            print(f"    数据点数: {trend.data_points}")
            
            if trend.predicted_value is not None:
                print(f"    预测值: {trend.predicted_value:.3f}")
        
        # Demonstrate forecasting
        print(f"\n🔮 质量预测演示:")
        
        for metric_name in list(trends.keys())[:2]:  # Forecast first 2 metrics
            forecast = self.trend_analyzer.forecast_quality(metric_name, forecast_days=7)
            
            if forecast:
                print(f"\n  📊 {metric_name} 7天预测:")
                print(f"    预测准确度: {forecast.forecast_accuracy:.3f}")
                print(f"    风险评估: {forecast.risk_assessment}")
                print(f"    预测值范围: {min(forecast.predicted_values):.3f} - {max(forecast.predicted_values):.3f}")
                
                if forecast.recommendations:
                    print(f"    建议:")
                    for rec in forecast.recommendations[:2]:  # Show first 2 recommendations
                        print(f"      • {rec}")
    
    def demo_alert_system(self):
        """Demonstrate alert system functionality."""
        print("\n" + "="*60)
        print("🚨 质量警报系统演示")
        print("="*60)
        
        # Get active alerts
        alerts = self.trend_analyzer.get_active_alerts()
        
        print(f"\n📢 当前活跃警报: {len(alerts)} 个")
        
        if alerts:
            # Group alerts by severity
            severity_counts = {}
            for alert in alerts:
                severity = alert.severity.value
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            print(f"\n  按严重程度分类:")
            for severity, count in severity_counts.items():
                emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
                print(f"    {emoji} {severity}: {count} 个")
            
            # Show details of first few alerts
            print(f"\n  警报详情:")
            for alert in alerts[:3]:  # Show first 3 alerts
                print(f"\n    🚨 {alert.alert_id}")
                print(f"      严重程度: {alert.severity.value}")
                print(f"      指标: {alert.metric_name}")
                print(f"      消息: {alert.message}")
                print(f"      当前值: {alert.current_value:.3f}")
                print(f"      阈值: {alert.threshold_value:.3f}")
        else:
            print("  ✅ 当前没有活跃警报")
        
        # Demonstrate alert acknowledgment
        if alerts:
            print(f"\n🔧 演示警报确认...")
            first_alert = alerts[0]
            success = self.trend_analyzer.acknowledge_alert(first_alert.alert_id)
            if success:
                print(f"  ✅ 警报 {first_alert.alert_id} 已确认")
    
    async def demo_quality_monitoring(self):
        """Demonstrate quality monitoring functionality."""
        print("\n" + "="*60)
        print("🔍 质量监控系统演示")
        print("="*60)
        
        # Configure monitoring
        config = MonitoringConfig(
            evaluation_interval=60,  # 1 minute for demo
            min_overall_quality=0.8,
            enable_auto_retraining=True,
            enable_notifications=True
        )
        
        self.quality_monitor.update_config(config)
        
        print(f"\n⚙️  监控配置:")
        print(f"  评估间隔: {config.evaluation_interval} 秒")
        print(f"  最低质量阈值: {config.min_overall_quality}")
        print(f"  自动重训练: {'启用' if config.enable_auto_retraining else '禁用'}")
        
        # Get monitoring status
        status = self.quality_monitor.get_monitoring_status()
        
        print(f"\n📊 监控状态:")
        print(f"  状态: {status['status']}")
        print(f"  总评估数: {status['statistics']['total_evaluations']}")
        print(f"  活跃警报: {status['statistics']['active_alerts']}")
        print(f"  重训练事件: {status['statistics']['retraining_events']}")
        
        # Demonstrate manual retraining trigger
        print(f"\n🔄 演示手动触发重训练...")
        await self.quality_monitor.manual_retraining("演示目的")
        
        # Get retraining history
        history = self.quality_monitor.get_retraining_history(limit=3)
        
        if history:
            print(f"\n📜 重训练历史 (最近 {len(history)} 次):")
            for event in history:
                print(f"\n  🔄 {event.event_id}")
                print(f"    触发器: {event.trigger.value}")
                print(f"    时间: {event.triggered_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"    原因: {event.trigger_reason}")
                print(f"    完成状态: {'✅' if event.retraining_completed else '⏳'}")
    
    def demo_quality_summary(self):
        """Demonstrate comprehensive quality summary."""
        print("\n" + "="*60)
        print("📋 综合质量报告演示")
        print("="*60)
        
        # Generate quality summary
        summary = self.trend_analyzer.get_quality_summary(timedelta(days=7))
        
        print(f"\n🏥 整体健康评分: {summary['overall_health_score']:.3f}")
        
        # Show trend summary
        trends = summary['trends']
        if trends:
            print(f"\n📈 趋势摘要:")
            
            improving = [name for name, trend in trends.items() if trend['direction'] == 'improving']
            declining = [name for name, trend in trends.items() if trend['direction'] == 'declining']
            stable = [name for name, trend in trends.items() if trend['direction'] == 'stable']
            
            if improving:
                print(f"  📈 改善中: {', '.join(improving)}")
            if declining:
                print(f"  📉 下降中: {', '.join(declining)}")
            if stable:
                print(f"  📊 稳定: {', '.join(stable)}")
        
        # Show alert summary
        alert_summary = summary['active_alerts']
        print(f"\n🚨 警报摘要:")
        print(f"  总计: {alert_summary['total']}")
        
        for severity, count in alert_summary['by_severity'].items():
            if count > 0:
                emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
                print(f"  {emoji} {severity}: {count}")
        
        # Show recommendations
        recommendations = summary.get('recommendations', [])
        if recommendations:
            print(f"\n💡 系统建议:")
            for rec in recommendations:
                print(f"  • {rec}")
    
    def demo_metric_descriptions(self):
        """Demonstrate available metrics and their descriptions."""
        print("\n" + "="*60)
        print("📚 可用指标说明")
        print("="*60)
        
        descriptions = self.evaluator.get_metric_descriptions()
        
        print(f"\n📊 Ragas 评估指标:")
        
        for metric, description in descriptions.items():
            print(f"\n  📌 {metric}:")
            print(f"    {description}")
    
    async def run_full_demo(self):
        """Run the complete demonstration."""
        print("🚀 Ragas 集成系统完整演示")
        print("="*80)
        
        try:
            # 1. Basic evaluation
            await self.demo_basic_evaluation()
            
            # 2. Batch evaluation
            await self.demo_batch_evaluation()
            
            # 3. Trend analysis
            self.demo_trend_analysis()
            
            # 4. Alert system
            self.demo_alert_system()
            
            # 5. Quality monitoring
            await self.demo_quality_monitoring()
            
            # 6. Quality summary
            self.demo_quality_summary()
            
            # 7. Metric descriptions
            self.demo_metric_descriptions()
            
            print("\n" + "="*80)
            print("✅ Ragas 集成系统演示完成!")
            print("="*80)
            
        except Exception as e:
            logger.error(f"演示过程中发生错误: {e}")
            print(f"\n❌ 演示失败: {e}")


async def main():
    """Main demo function."""
    demo = RagasIntegrationDemo()
    await demo.run_full_demo()


if __name__ == "__main__":
    asyncio.run(main())