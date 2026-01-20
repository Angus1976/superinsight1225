#!/usr/bin/env python3
"""
Demo script for Intelligent Operations System.

Demonstrates AI-driven operations capabilities including:
- Machine learning-based anomaly detection and prediction
- Automated operations and self-healing
- Operations knowledge base and decision support
"""

import asyncio
import logging
import math
import time
import random
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_intelligent_operations():
    """Demonstrate intelligent operations capabilities."""
    print("=" * 80)
    print("INTELLIGENT OPERATIONS SYSTEM DEMO")
    print("=" * 80)
    
    try:
        # Import components
        from src.system.intelligent_operations import get_intelligent_operations
        from src.system.automated_operations import get_automated_operations
        from src.system.operations_knowledge_base import get_operations_knowledge
        from src.system.monitoring import MetricsCollector
        from src.monitoring.advanced_anomaly_detection import advanced_anomaly_detector
        
        # Initialize systems
        print("\n1. Initializing Intelligent Operations Systems...")
        intelligent_ops = get_intelligent_operations()
        automated_ops = get_automated_operations()
        knowledge_system = get_operations_knowledge()
        metrics_collector = MetricsCollector()
        
        # Start systems
        print("   Starting intelligent operations...")
        await intelligent_ops.start()
        
        print("   Starting automated operations...")
        await automated_ops.start()
        
        print("   Starting metrics collection...")
        await metrics_collector.start_collection()
        
        print("   ✓ All systems started successfully")
        
        # Demo 1: ML-based Anomaly Detection and Prediction
        print("\n2. Demonstrating ML-based Anomaly Detection and Prediction...")
        
        # Simulate metrics with anomalies
        print("   Simulating system metrics with anomalies...")
        for i in range(20):
            # Normal metrics
            cpu_usage = 45 + random.uniform(-10, 10)
            memory_usage = 60 + random.uniform(-15, 15)
            response_time = 0.8 + random.uniform(-0.3, 0.3)
            
            # Inject anomalies
            if i == 15:  # CPU spike
                cpu_usage = 95
                print(f"   🚨 Injecting CPU anomaly: {cpu_usage:.1f}%")
            elif i == 17:  # Memory spike
                memory_usage = 92
                print(f"   🚨 Injecting Memory anomaly: {memory_usage:.1f}%")
            elif i == 18:  # Response time spike
                response_time = 3.5
                print(f"   🚨 Injecting Response Time anomaly: {response_time:.2f}s")
            
            # Record metrics
            metrics_collector.record_metric("system.cpu.usage_percent", cpu_usage)
            metrics_collector.record_metric("system.memory.usage_percent", memory_usage)
            metrics_collector.record_metric("requests.duration", response_time)
            
            # Analyze for anomalies
            anomalies = await advanced_anomaly_detector.analyze_metric(
                "system.cpu.usage_percent", cpu_usage
            )
            
            if anomalies:
                for anomaly in anomalies:
                    print(f"   🔍 Anomaly detected: {anomaly.metric_name} - {anomaly.anomaly_type.value}")
            
            await asyncio.sleep(0.5)  # Simulate time passage
        
        # Show detection statistics
        stats = advanced_anomaly_detector.get_detection_statistics()
        print(f"   📊 Detection Statistics:")
        print(f"      - Total points analyzed: {stats['total_points_analyzed']}")
        print(f"      - Anomalies detected: {stats['anomalies_detected']}")
        print(f"      - Detection rate: {stats['detection_rate']:.2%}")
        
        # Demo 2: Capacity Planning and Predictions
        print("\n3. Demonstrating Capacity Planning and Predictions...")
        
        # Generate capacity forecasts
        current_metrics = metrics_collector.get_all_metrics_summary()
        flat_metrics = {}
        for name, data in current_metrics.items():
            if 'latest' in data:
                flat_metrics[name] = data['latest'] or 0.0
        
        print("   Generating capacity forecasts...")
        capacity_planner = intelligent_ops.capacity_planner
        
        for resource in ['system.cpu.usage_percent', 'system.memory.usage_percent']:
            if resource in flat_metrics:
                forecast = await capacity_planner.generate_capacity_forecast(resource, flat_metrics)
                print(f"   📈 {resource}:")
                print(f"      - Current usage: {forecast.current_usage:.1f}%")
                print(f"      - Time to exhaustion: {forecast.time_to_exhaustion or 'N/A'} hours")
                print(f"      - Recommendation: {forecast.recommended_action}")
                print(f"      - Confidence: {forecast.confidence:.2f}")
        
        # Demo 3: Intelligent Recommendations
        print("\n4. Demonstrating Intelligent Recommendations...")
        
        # Wait for recommendations to be generated
        await asyncio.sleep(2)
        
        recommendations = intelligent_ops.recommendations
        print(f"   Generated {len(recommendations)} operational recommendations:")
        
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"   {i}. {rec.title}")
            print(f"      Priority: {rec.priority}")
            print(f"      Type: {rec.recommendation_type.value}")
            print(f"      Impact: Performance {rec.estimated_impact.get('performance', 0):+.1f}, "
                  f"Cost {rec.estimated_impact.get('cost', 0):+.1f}")
            print(f"      Timeline: {rec.timeline}")
        
        # Demo 4: Automated Operations
        print("\n5. Demonstrating Automated Operations...")
        
        # Show automation status
        automation_status = automated_ops.get_automation_status()
        print(f"   Automation Status:")
        print(f"   - Running: {automation_status['is_running']}")
        print(f"   - Active operations: {automation_status['active_operations']}")
        print(f"   - Automation rules: {len(automation_status['automation_rules'])}")
        
        # Show recent executions
        recent_executions = automation_status.get('recent_executions', [])
        if recent_executions:
            print(f"   Recent Automation Executions:")
            for exec in recent_executions[-3:]:
                status_icon = "✅" if exec['success'] else "❌"
                print(f"   {status_icon} {exec['operation_type']} - {exec['rule_id']}")
        
        # Demo 5: Operations Knowledge Base
        print("\n6. Demonstrating Operations Knowledge Base...")
        
        # Create a sample case from recent anomalies
        from src.system.operations_knowledge_base import OperationalCase, CaseType, CaseSeverity, CaseStatus
        
        sample_case = OperationalCase(
            case_id=f"demo_case_{int(time.time())}",
            case_type=CaseType.PERFORMANCE_OPTIMIZATION,
            severity=CaseSeverity.HIGH,
            status=CaseStatus.RESOLVED,
            title="High CPU Usage Resolution",
            description="System experienced high CPU usage due to inefficient query processing",
            symptoms=["CPU usage > 90%", "Slow response times", "High database load"],
            root_cause="Inefficient database queries without proper indexing",
            resolution_steps=[
                "Identified slow queries using performance monitoring",
                "Added database indexes for frequently accessed columns",
                "Optimized query structure to reduce CPU overhead",
                "Implemented query result caching"
            ],
            resolution_time_minutes=45,
            tags={"cpu", "performance", "database", "optimization"},
            related_metrics={"cpu_usage_percent": 95.0, "response_time_ms": 3500},
            effectiveness_score=0.9
        )
        
        # Add case to knowledge base
        knowledge_system.case_library.add_case(sample_case)
        print(f"   ✓ Added sample case: {sample_case.title}")
        
        # Search for similar cases
        similar_cases = knowledge_system.case_library.find_similar_cases(
            symptoms=["High CPU usage", "Performance issues"],
            metrics={"cpu_usage_percent": 88.0},
            limit=3
        )
        
        print(f"   🔍 Found {len(similar_cases)} similar cases:")
        for case, similarity in similar_cases:
            print(f"      - {case.title} (similarity: {similarity:.2f})")
        
        # Demo 6: Decision Support System
        print("\n7. Demonstrating Decision Support System...")
        
        from src.system.operations_knowledge_base import DecisionContext
        
        # Create decision context
        decision_context = DecisionContext(
            situation_id=f"decision_{int(time.time())}",
            description="System experiencing high resource usage and slow response times",
            current_metrics={
                "cpu_usage_percent": 85.0,
                "memory_usage_percent": 78.0,
                "response_time_ms": 2500
            },
            symptoms=["High CPU usage", "Slow response times", "Increased error rate"],
            constraints={"budget": "limited", "maintenance_window": "weekend_only"},
            objectives=["Improve performance", "Reduce response time", "Maintain availability"],
            time_pressure="high",
            risk_tolerance="medium"
        )
        
        # Get decision recommendations
        decision_recommendations = await knowledge_system.decision_support.get_decision_recommendations(decision_context)
        
        print(f"   🎯 Generated {len(decision_recommendations)} decision recommendations:")
        for i, rec in enumerate(decision_recommendations[:3], 1):
            print(f"   {i}. {rec.recommended_action}")
            print(f"      Confidence: {rec.confidence:.2f}")
            print(f"      Success Probability: {rec.success_probability:.2f}")
            print(f"      Rationale: {rec.rationale}")
        
        # Demo 7: System Insights and Analytics
        print("\n8. Demonstrating System Insights and Analytics...")
        
        # Get comprehensive insights
        insights = intelligent_ops.get_system_insights()
        
        print(f"   📊 System Insights:")
        print(f"   Predictions:")
        for metric, pred in insights.get('predictions', {}).items():
            print(f"      - {metric}: {pred['predicted_value']:.2f} (confidence: {pred['confidence']:.2f})")
        
        print(f"   Capacity Forecasts:")
        for resource, forecast in insights.get('capacity_forecasts', {}).items():
            print(f"      - {resource}: {forecast['current_usage']:.1f}% usage")
            if forecast['time_to_exhaustion']:
                print(f"        Time to exhaustion: {forecast['time_to_exhaustion']} hours")
        
        print(f"   Model Status:")
        for metric, status in insights.get('model_status', {}).items():
            trained_icon = "✅" if status['trained'] else "❌"
            print(f"      - {metric}: {trained_icon} (accuracy: {status['accuracy']:.2f})")
        
        # Demo 8: Knowledge System Statistics
        print("\n9. Knowledge System Statistics...")
        
        kb_insights = knowledge_system.get_system_insights()
        case_stats = kb_insights.get('case_library', {})
        
        print(f"   📚 Knowledge Base Statistics:")
        print(f"   - Total cases: {case_stats.get('total_cases', 0)}")
        print(f"   - Cases by type: {case_stats.get('by_type', {})}")
        print(f"   - Average resolution time: {case_stats.get('avg_resolution_time', 0):.1f} minutes")
        print(f"   - Average effectiveness: {case_stats.get('avg_effectiveness', 0):.2f}")
        
        kb_stats = kb_insights.get('knowledge_base', {})
        print(f"   - Knowledge articles: {kb_stats.get('total_articles', 0)}")
        print(f"   - Categories: {len(kb_stats.get('categories', []))}")
        
        # Demo 9: Real-time Monitoring Integration
        print("\n10. Real-time Monitoring Integration...")
        
        print("    Simulating real-time operations for 30 seconds...")
        start_time = time.time()
        
        while time.time() - start_time < 30:
            # Simulate varying system load
            current_time = time.time() - start_time
            
            # Create realistic patterns
            cpu_base = 50 + 20 * abs(math.sin(current_time / 10))  # Sine wave pattern
            memory_base = 60 + 15 * random.uniform(-1, 1)  # Random variation
            
            # Add occasional spikes
            if random.random() < 0.1:  # 10% chance of spike
                cpu_base += random.uniform(20, 40)
                print(f"    🚨 Simulated load spike: CPU {cpu_base:.1f}%")
            
            # Record metrics
            metrics_collector.record_metric("system.cpu.usage_percent", cpu_base)
            metrics_collector.record_metric("system.memory.usage_percent", memory_base)
            
            # Check for anomalies
            anomalies = await advanced_anomaly_detector.analyze_metric(
                "system.cpu.usage_percent", cpu_base
            )
            
            if anomalies:
                print(f"    🔍 Real-time anomaly: {anomalies[0].anomaly_type.value}")
            
            await asyncio.sleep(2)
        
        print("    ✓ Real-time monitoring simulation completed")
        
        # Final Summary
        print("\n" + "=" * 80)
        print("DEMO SUMMARY")
        print("=" * 80)
        
        final_stats = advanced_anomaly_detector.get_detection_statistics()
        final_insights = intelligent_ops.get_system_insights()
        
        print(f"✅ Anomaly Detection:")
        print(f"   - Total metrics analyzed: {final_stats['total_points_analyzed']}")
        print(f"   - Anomalies detected: {final_stats['anomalies_detected']}")
        print(f"   - Detection methods used: {len(final_stats['by_method'])}")
        
        print(f"✅ Predictions Generated:")
        print(f"   - Active predictions: {len(final_insights.get('predictions', {}))}")
        print(f"   - Capacity forecasts: {len(final_insights.get('capacity_forecasts', {}))}")
        
        print(f"✅ Recommendations:")
        print(f"   - Operational recommendations: {len(intelligent_ops.recommendations)}")
        print(f"   - Decision support recommendations: {len(decision_recommendations)}")
        
        print(f"✅ Knowledge Base:")
        print(f"   - Cases in library: {case_stats.get('total_cases', 0)}")
        print(f"   - Knowledge articles: {kb_stats.get('total_articles', 0)}")
        
        print(f"✅ Automation:")
        print(f"   - Automation rules: {len(automation_status['automation_rules'])}")
        print(f"   - Recent executions: {len(automation_status.get('recent_executions', []))}")
        
        print("\n🎉 Intelligent Operations System Demo Completed Successfully!")
        print("\nKey Features Demonstrated:")
        print("• ML-based anomaly detection with multiple algorithms")
        print("• Predictive analytics for capacity planning")
        print("• Intelligent operational recommendations")
        print("• Automated operations and self-healing")
        print("• Operations knowledge base with case-based reasoning")
        print("• Decision support system with contextual recommendations")
        print("• Real-time monitoring and alerting integration")
        
    except Exception as e:
        logger.error(f"Demo error: {e}")
        print(f"\n❌ Demo failed with error: {e}")
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        try:
            if 'intelligent_ops' in locals():
                await intelligent_ops.stop()
            if 'automated_ops' in locals():
                await automated_ops.stop()
            if 'metrics_collector' in locals():
                await metrics_collector.stop_collection()
            print("✓ Cleanup completed")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")


if __name__ == "__main__":
    import math
    asyncio.run(demo_intelligent_operations())