#!/usr/bin/env python3
"""
Performance Optimization System Demo

Demonstrates the comprehensive performance optimization capabilities including:
- Application Performance Monitoring (APM)
- Resource Usage Optimization
- Cache and Database Optimization
"""

import asyncio
import logging
import time
import random
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our performance optimization modules
from src.system.apm_monitor import (
    apm_monitor,
    trace_api_request,
    trace_database_query,
    BusinessTransactionTracker,
    UserExperienceMetrics
)
from src.system.resource_optimizer import (
    resource_monitor,
    resource_predictor,
    resource_optimizer
)
from src.system.cache_db_optimizer import (
    cache_db_optimizer,
    get_cached_data
)


async def demo_apm_monitoring():
    """Demonstrate Application Performance Monitoring capabilities."""
    print("\n" + "="*60)
    print("🔍 APPLICATION PERFORMANCE MONITORING (APM) DEMO")
    print("="*60)
    
    # Simulate API requests with tracing
    print("\n1. Simulating API requests with distributed tracing...")
    
    @trace_api_request("/api/users", "GET")
    async def get_users():
        await asyncio.sleep(0.1)  # Simulate processing time
        return {"users": ["user1", "user2", "user3"]}
    
    @trace_api_request("/api/annotations", "POST")
    async def create_annotation():
        await asyncio.sleep(0.2)  # Simulate processing time
        return {"annotation_id": "ann_123", "status": "created"}
    
    # Execute traced requests
    for i in range(5):
        await get_users()
        await create_annotation()
    
    # Simulate database queries with tracing
    print("2. Simulating database queries with performance tracking...")
    
    async with trace_database_query("SELECT", "users"):
        await asyncio.sleep(0.05)  # Simulate query time
    
    async with trace_database_query("INSERT", "annotations"):
        await asyncio.sleep(0.08)  # Simulate query time
    
    # Simulate business transaction tracking
    print("3. Tracking business transactions...")
    
    with BusinessTransactionTracker("user_annotation_workflow", "user_123") as transaction:
        # Step 1: User authentication
        await asyncio.sleep(0.02)
        transaction.add_step("authentication", 0.02, True)
        
        # Step 2: Load annotation task
        await asyncio.sleep(0.05)
        transaction.add_step("load_task", 0.05, True)
        
        # Step 3: Save annotation
        await asyncio.sleep(0.1)
        transaction.add_step("save_annotation", 0.1, True)
    
    # Record user experience metrics
    print("4. Recording user experience metrics...")
    
    ux_metrics = UserExperienceMetrics(
        page_url="/annotation-interface",
        user_agent="Mozilla/5.0 (Chrome/91.0)",
        page_load_time=2.1,
        dom_content_loaded=1.5,
        first_contentful_paint=1.2,
        largest_contentful_paint=2.0,
        cumulative_layout_shift=0.05,
        first_input_delay=50,
        time_to_interactive=2.5,
        session_duration=300,
        error_count=0
    )
    
    apm_monitor.record_user_experience(ux_metrics)
    
    # Display APM summary
    print("\n📊 APM Performance Summary:")
    api_summary = apm_monitor.get_api_performance_summary()
    db_summary = apm_monitor.get_database_performance_summary()
    ux_summary = apm_monitor.get_user_experience_summary()
    transaction_summary = apm_monitor.get_business_transaction_summary()
    
    print(f"  • API Endpoints Tracked: {api_summary['total_endpoints']}")
    print(f"  • Database Query Types: {db_summary['total_query_types']}")
    print(f"  • User Sessions: {ux_summary['total_sessions']}")
    print(f"  • Business Transactions: {transaction_summary['total_transactions']}")
    print(f"  • Core Web Vitals Score: {ux_summary.get('core_web_vitals_score', 0):.1f}/100")


async def demo_resource_optimization():
    """Demonstrate Resource Usage Optimization capabilities."""
    print("\n" + "="*60)
    print("📈 RESOURCE USAGE OPTIMIZATION DEMO")
    print("="*60)
    
    # Start resource monitoring
    print("\n1. Starting resource monitoring...")
    await resource_monitor.start_monitoring()
    
    # Wait for some metrics to be collected
    await asyncio.sleep(2)
    
    # Get current resource metrics
    print("2. Analyzing current resource usage...")
    current_metrics = resource_monitor.get_current_metrics()
    
    if current_metrics:
        print(f"  • CPU Usage: {current_metrics.cpu_percent:.1f}%")
        print(f"  • Memory Usage: {current_metrics.memory_percent:.1f}%")
        print(f"  • Disk Usage: {current_metrics.disk_percent:.1f}%")
        print(f"  • Process Count: {current_metrics.process_count}")
    
    # Generate resource predictions
    print("3. Generating resource usage predictions...")
    
    cpu_prediction = resource_predictor.predict_resource_usage("cpu", 24)
    memory_prediction = resource_predictor.predict_resource_usage("memory", 24)
    
    if cpu_prediction:
        print(f"  • CPU Prediction (24h): {cpu_prediction.predicted_24h:.1f}% (trend: {cpu_prediction.trend})")
        print(f"    Recommendation: {cpu_prediction.recommendation}")
    
    if memory_prediction:
        print(f"  • Memory Prediction (24h): {memory_prediction.predicted_24h:.1f}% (trend: {memory_prediction.trend})")
        print(f"    Recommendation: {memory_prediction.recommendation}")
    
    # Analyze bottlenecks
    print("4. Analyzing performance bottlenecks...")
    bottlenecks = resource_optimizer.analyze_bottlenecks()
    
    if bottlenecks:
        for bottleneck in bottlenecks:
            print(f"  • {bottleneck.resource_type.upper()} Bottleneck ({bottleneck.severity})")
            print(f"    Current Usage: {bottleneck.current_usage:.1f}%")
            print(f"    Impact: {bottleneck.impact}")
            print(f"    Top Recommendation: {bottleneck.recommendations[0] if bottleneck.recommendations else 'None'}")
    else:
        print("  • No critical bottlenecks detected")
    
    # Generate scaling recommendations
    print("5. Generating scaling recommendations...")
    scaling_recommendations = resource_optimizer.generate_scaling_recommendations()
    
    if scaling_recommendations:
        for rec in scaling_recommendations:
            print(f"  • {rec.resource_type.upper()} Scaling ({rec.priority} priority)")
            print(f"    Current: {rec.current_allocation:.1f} → Recommended: {rec.recommended_allocation:.1f}")
            print(f"    Reason: {rec.reason}")
            print(f"    Cost Impact: {rec.estimated_cost_impact:+.1f}%")
    else:
        print("  • No scaling recommendations at this time")
    
    # Cost optimization analysis
    print("6. Analyzing cost optimization opportunities...")
    cost_analysis = resource_optimizer.get_cost_optimization_analysis()
    
    if "error" not in cost_analysis:
        print(f"  • Total Opportunities: {cost_analysis['total_opportunities']}")
        print(f"  • Potential Savings: {cost_analysis['total_potential_savings']:.1f} cost units")
        
        for opportunity in cost_analysis.get('opportunities', [])[:2]:  # Show top 2
            print(f"    - {opportunity['opportunity']}: {opportunity['potential_savings_percent']}% savings")
    
    # Stop monitoring
    await resource_monitor.stop_monitoring()


async def demo_cache_db_optimization():
    """Demonstrate Cache and Database Optimization capabilities."""
    print("\n" + "="*60)
    print("💾 CACHE & DATABASE OPTIMIZATION DEMO")
    print("="*60)
    
    # Create intelligent cache
    print("\n1. Creating intelligent cache with adaptive TTL...")
    cache = cache_db_optimizer.create_cache(
        name="demo_cache",
        default_ttl=300,  # 5 minutes
        max_memory_mb=50
    )
    
    print(f"  • Cache '{cache.name}' created with {cache.backend} backend")
    
    # Simulate cache operations
    print("2. Simulating cache operations...")
    
    # Set some values
    await cache.set("user:123", {"name": "John Doe", "role": "annotator"})
    await cache.set("task:456", {"title": "Image Classification", "status": "pending"})
    await cache.set("project:789", {"name": "Medical Images", "type": "classification"})
    
    # Simulate cache hits and misses
    for i in range(10):
        key = f"user:{random.choice([123, 124, 125])}"
        value = await cache.get(key)
        if value is None:
            # Cache miss - simulate loading from database
            await cache.set(key, {"name": f"User {key.split(':')[1]}", "role": "annotator"})
    
    # Demonstrate cached data loading
    print("3. Demonstrating intelligent data caching...")
    
    async def load_user_data(user_id):
        """Simulate loading user data from database."""
        await asyncio.sleep(0.1)  # Simulate database query time
        return {"id": user_id, "name": f"User {user_id}", "annotations": random.randint(10, 100)}
    
    # Load data with caching
    start_time = time.time()
    user_data = await get_cached_data(
        cache_name="demo_cache",
        key="user_data:123",
        data_loader=lambda: load_user_data("123"),
        ttl=600
    )
    first_load_time = time.time() - start_time
    
    # Load same data again (should be cached)
    start_time = time.time()
    cached_user_data = await get_cached_data(
        cache_name="demo_cache",
        key="user_data:123",
        data_loader=lambda: load_user_data("123"),
        ttl=600
    )
    cached_load_time = time.time() - start_time
    
    print(f"  • First load time: {first_load_time*1000:.1f}ms")
    print(f"  • Cached load time: {cached_load_time*1000:.1f}ms")
    print(f"  • Speed improvement: {(first_load_time/cached_load_time):.1f}x faster")
    
    # Create database pool (simulated)
    print("4. Creating optimized database connection pool...")
    
    try:
        # This would normally connect to a real database
        db_pool = cache_db_optimizer.create_db_pool(
            name="demo_pool",
            database_url="postgresql://demo:demo@localhost/demo",
            min_connections=2,
            max_connections=10
        )
        print(f"  • Database pool '{db_pool.name}' created (simulated)")
    except Exception as e:
        print(f"  • Database pool creation skipped (no database available): {str(e)[:50]}...")
    
    # Get cache statistics
    print("5. Analyzing cache performance...")
    cache_stats = cache.get_cache_statistics()
    
    print(f"  • Total Requests: {cache_stats['total_requests']}")
    print(f"  • Cache Hit Rate: {cache_stats['hit_rate']:.1%}")
    print(f"  • Average Response Time: {cache_stats['avg_response_time']*1000:.1f}ms")
    print(f"  • Popular Keys: {len(cache_stats['popular_keys'])}")
    
    # Get comprehensive optimization recommendations
    print("6. Generating optimization recommendations...")
    recommendations = cache_db_optimizer.get_optimization_recommendations()
    
    total_recommendations = (
        len(recommendations['cache_recommendations']) +
        len(recommendations['database_recommendations']) +
        len(recommendations['integration_recommendations'])
    )
    
    print(f"  • Total Recommendations: {total_recommendations}")
    
    if recommendations['cache_recommendations']:
        print("  • Cache Recommendations:")
        for rec in recommendations['cache_recommendations'][:2]:
            print(f"    - {rec['title']} ({rec['priority']} priority)")
    
    if recommendations['integration_recommendations']:
        print("  • Integration Recommendations:")
        for rec in recommendations['integration_recommendations'][:2]:
            print(f"    - {rec['title']} ({rec['priority']} priority)")


async def demo_integrated_performance_analysis():
    """Demonstrate integrated performance analysis across all systems."""
    print("\n" + "="*60)
    print("🎯 INTEGRATED PERFORMANCE ANALYSIS")
    print("="*60)
    
    print("\n1. Collecting comprehensive performance metrics...")
    
    # Simulate some load to generate metrics
    await asyncio.sleep(1)
    
    # Get APM insights
    api_summary = apm_monitor.get_api_performance_summary()
    ux_summary = apm_monitor.get_user_experience_summary()
    
    # Get resource statistics
    resource_stats = resource_monitor.get_resource_statistics(hours=1)
    
    # Get cache/DB statistics
    cache_db_stats = cache_db_optimizer.get_comprehensive_statistics()
    
    print("2. Performance Analysis Summary:")
    print(f"  • API Endpoints Monitored: {api_summary.get('total_endpoints', 0)}")
    print(f"  • Average Page Load Time: {ux_summary.get('avg_page_load_time', 0):.2f}s")
    
    if "error" not in resource_stats:
        print(f"  • CPU Usage (avg): {resource_stats['cpu']['average']:.1f}%")
        print(f"  • Memory Usage (avg): {resource_stats['memory']['average']:.1f}%")
        print(f"  • CPU Trend: {resource_stats['cpu']['trend']}")
    
    print(f"  • Cache Hit Rate: {cache_db_stats['summary']['overall_cache_hit_rate']:.1%}")
    
    print("\n3. Performance Optimization Opportunities:")
    
    # Identify optimization opportunities
    opportunities = []
    
    # Check API performance
    for endpoint, metrics in api_summary.get('endpoints', {}).items():
        if metrics['avg_response_time'] > 1.0:
            opportunities.append(f"Optimize slow API endpoint: {endpoint} ({metrics['avg_response_time']:.2f}s)")
    
    # Check resource usage
    if "error" not in resource_stats:
        if resource_stats['cpu']['average'] > 70:
            opportunities.append(f"High CPU usage detected: {resource_stats['cpu']['average']:.1f}%")
        
        if resource_stats['memory']['average'] > 80:
            opportunities.append(f"High memory usage detected: {resource_stats['memory']['average']:.1f}%")
    
    # Check cache performance
    if cache_db_stats['summary']['overall_cache_hit_rate'] < 0.8:
        opportunities.append(f"Low cache hit rate: {cache_db_stats['summary']['overall_cache_hit_rate']:.1%}")
    
    if opportunities:
        for i, opportunity in enumerate(opportunities[:5], 1):
            print(f"  {i}. {opportunity}")
    else:
        print("  • No critical optimization opportunities detected")
    
    print("\n4. Recommended Actions:")
    print("  • Implement proactive monitoring alerts")
    print("  • Set up automated scaling policies")
    print("  • Optimize cache warming strategies")
    print("  • Regular performance review cycles")
    print("  • Continuous query optimization")


async def main():
    """Run the complete performance optimization demo."""
    print("🚀 SuperInsight Performance Optimization System Demo")
    print("=" * 60)
    print("This demo showcases comprehensive performance optimization capabilities")
    print("including APM, resource optimization, and cache/database optimization.")
    
    try:
        # Run all demo sections
        await demo_apm_monitoring()
        await demo_resource_optimization()
        await demo_cache_db_optimization()
        await demo_integrated_performance_analysis()
        
        print("\n" + "="*60)
        print("✅ DEMO COMPLETED SUCCESSFULLY")
        print("="*60)
        print("\nKey Features Demonstrated:")
        print("• 🔍 Application Performance Monitoring (APM)")
        print("  - Distributed request tracing")
        print("  - Database query performance tracking")
        print("  - Business transaction monitoring")
        print("  - User experience metrics (Core Web Vitals)")
        print("\n• 📈 Resource Usage Optimization")
        print("  - Real-time resource monitoring")
        print("  - Predictive capacity planning")
        print("  - Intelligent scaling recommendations")
        print("  - Cost optimization analysis")
        print("\n• 💾 Cache & Database Optimization")
        print("  - Intelligent caching with adaptive TTL")
        print("  - Database connection pool optimization")
        print("  - Query performance analysis")
        print("  - Automated optimization suggestions")
        print("\n• 🎯 Integrated Performance Analysis")
        print("  - Cross-system performance correlation")
        print("  - Comprehensive optimization recommendations")
        print("  - Proactive bottleneck detection")
        
        print(f"\n📊 Performance Metrics Summary:")
        print(f"• Total API requests traced: {apm_monitor.get_api_performance_summary().get('total_endpoints', 0)}")
        print(f"• Resource monitoring data points: {len(resource_monitor.metrics_history)}")
        print(f"• Cache operations: {sum(cache.metrics.total_requests for cache in cache_db_optimizer.caches.values())}")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        print(f"\n❌ Demo failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)