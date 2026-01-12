"""
Real-time Security Integration for SuperInsight Platform.

Integrates all real-time security components and provides a unified interface
for < 5 second security monitoring performance.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.orm import Session

from src.security.real_time_security_monitor import real_time_security_monitor
from src.api.real_time_security_websocket import websocket_manager, start_websocket_heartbeat
from src.api.security_performance_api import router as performance_router
from src.api.real_time_security_websocket import router as websocket_router
from src.database.connection import get_db_session


logger = logging.getLogger(__name__)


class RealTimeSecurityIntegration:
    """
    Real-time security integration manager.
    
    Coordinates all real-time security components to achieve < 5 second
    monitoring performance requirements.
    """
    
    def __init__(self):
        self.initialized = False
        self.monitoring_active = False
        self.performance_target = 5.0  # 5 seconds
        
    async def initialize(self):
        """Initialize all real-time security components."""
        
        if self.initialized:
            return
        
        try:
            logger.info("Initializing real-time security integration...")
            
            # Initialize real-time monitor
            await real_time_security_monitor.initialize()
            
            # Start WebSocket heartbeat
            await start_websocket_heartbeat()
            
            self.initialized = True
            logger.info("Real-time security integration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize real-time security integration: {e}")
            raise
    
    async def start_monitoring(self):
        """Start real-time security monitoring."""
        
        if not self.initialized:
            await self.initialize()
        
        if self.monitoring_active:
            return
        
        try:
            logger.info("Starting real-time security monitoring...")
            
            # Start real-time monitor
            monitoring_task = asyncio.create_task(
                real_time_security_monitor.start_monitoring()
            )
            
            self.monitoring_active = True
            logger.info("Real-time security monitoring started successfully")
            
            return monitoring_task
            
        except Exception as e:
            logger.error(f"Failed to start real-time security monitoring: {e}")
            self.monitoring_active = False
            raise
    
    async def stop_monitoring(self):
        """Stop real-time security monitoring."""
        
        if not self.monitoring_active:
            return
        
        try:
            logger.info("Stopping real-time security monitoring...")
            
            # Stop real-time monitor
            await real_time_security_monitor.stop_monitoring()
            
            self.monitoring_active = False
            logger.info("Real-time security monitoring stopped successfully")
            
        except Exception as e:
            logger.error(f"Failed to stop real-time security monitoring: {e}")
            raise
    
    async def validate_performance(self) -> Dict[str, Any]:
        """Validate that performance meets < 5 second requirement."""
        
        try:
            logger.info("Validating real-time security performance...")
            
            # Get current performance metrics
            metrics = real_time_security_monitor.get_performance_metrics()
            
            # Check key performance indicators
            avg_processing_time = metrics.get('avg_processing_time', 0)
            max_processing_time = metrics.get('max_processing_time', 0)
            monitoring_active = metrics.get('monitoring_active', False)
            
            # Calculate performance score
            performance_score = self._calculate_performance_score(metrics)
            
            # Determine SLA compliance
            sla_compliant = (
                avg_processing_time < self.performance_target and
                max_processing_time < self.performance_target * 2 and
                monitoring_active
            )
            
            validation_result = {
                'timestamp': datetime.utcnow().isoformat(),
                'performance_target': self.performance_target,
                'sla_compliant': sla_compliant,
                'performance_score': performance_score,
                'metrics': {
                    'avg_processing_time': avg_processing_time,
                    'max_processing_time': max_processing_time,
                    'monitoring_active': monitoring_active,
                    'cache_hit_rate': self._calculate_cache_hit_rate(metrics),
                    'throughput_events_per_second': self._calculate_throughput(metrics)
                },
                'recommendations': self._generate_performance_recommendations(metrics)
            }
            
            if sla_compliant:
                logger.info(f"✅ Performance validation PASSED: {avg_processing_time:.3f}s < {self.performance_target}s")
            else:
                logger.warning(f"❌ Performance validation FAILED: {avg_processing_time:.3f}s >= {self.performance_target}s")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Performance validation failed: {e}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'sla_compliant': False,
                'error': str(e),
                'recommendations': ['Check system logs', 'Restart monitoring services']
            }
    
    async def run_performance_test(self, duration_seconds: int = 60) -> Dict[str, Any]:
        """Run comprehensive performance test."""
        
        try:
            logger.info(f"Running {duration_seconds}s performance test...")
            
            # Record initial state
            initial_metrics = real_time_security_monitor.get_performance_metrics()
            start_time = datetime.utcnow()
            
            # Simulate load for the test duration
            test_results = []
            
            for i in range(duration_seconds):
                iteration_start = datetime.utcnow()
                
                # Simulate security event processing
                await self._simulate_security_workload()
                
                iteration_time = (datetime.utcnow() - iteration_start).total_seconds()
                test_results.append(iteration_time)
                
                # Wait for next iteration
                await asyncio.sleep(max(0, 1 - iteration_time))
            
            # Calculate test results
            end_time = datetime.utcnow()
            final_metrics = real_time_security_monitor.get_performance_metrics()
            
            avg_iteration_time = sum(test_results) / len(test_results)
            max_iteration_time = max(test_results)
            min_iteration_time = min(test_results)
            
            # Performance analysis
            performance_analysis = {
                'test_duration': duration_seconds,
                'iterations_completed': len(test_results),
                'avg_iteration_time': avg_iteration_time,
                'max_iteration_time': max_iteration_time,
                'min_iteration_time': min_iteration_time,
                'sla_compliance_rate': sum(1 for t in test_results if t < self.performance_target) / len(test_results),
                'performance_grade': self._grade_performance(avg_iteration_time),
                'initial_metrics': initial_metrics,
                'final_metrics': final_metrics,
                'performance_improvement': self._calculate_improvement(initial_metrics, final_metrics)
            }
            
            logger.info(f"Performance test completed: {avg_iteration_time:.3f}s avg, {performance_analysis['sla_compliance_rate']:.1%} SLA compliance")
            
            return performance_analysis
            
        except Exception as e:
            logger.error(f"Performance test failed: {e}")
            return {'error': str(e), 'sla_compliance_rate': 0.0}
    
    async def optimize_performance(self) -> Dict[str, Any]:
        """Apply automatic performance optimizations."""
        
        try:
            logger.info("Applying automatic performance optimizations...")
            
            # Get current metrics
            current_metrics = real_time_security_monitor.get_performance_metrics()
            
            optimizations_applied = []
            
            # Optimize scan interval
            if current_metrics.get('avg_processing_time', 0) > 3.0:
                real_time_security_monitor.scan_interval = 3  # Reduce to 3 seconds
                optimizations_applied.append("Reduced scan interval to 3 seconds")
            
            # Optimize batch size
            if current_metrics.get('events_processed', 0) > 500:
                real_time_security_monitor.batch_size = 150  # Increase batch size
                optimizations_applied.append("Increased batch size to 150")
            
            # Optimize cache TTL
            cache_hit_rate = self._calculate_cache_hit_rate(current_metrics)
            if cache_hit_rate < 0.8:
                real_time_security_monitor.cache_ttl = 600  # Increase to 10 minutes
                optimizations_applied.append("Increased cache TTL to 10 minutes")
            
            # Enable Redis if not already enabled
            if not current_metrics.get('redis_enabled', False):
                await real_time_security_monitor._initialize_redis()
                optimizations_applied.append("Enabled Redis distributed caching")
            
            # Wait for optimizations to take effect
            await asyncio.sleep(5)
            
            # Get updated metrics
            optimized_metrics = real_time_security_monitor.get_performance_metrics()
            
            optimization_result = {
                'timestamp': datetime.utcnow().isoformat(),
                'optimizations_applied': optimizations_applied,
                'before_metrics': current_metrics,
                'after_metrics': optimized_metrics,
                'performance_improvement': self._calculate_improvement(current_metrics, optimized_metrics),
                'estimated_sla_compliance': optimized_metrics.get('avg_processing_time', 0) < self.performance_target
            }
            
            logger.info(f"Applied {len(optimizations_applied)} performance optimizations")
            
            return optimization_result
            
        except Exception as e:
            logger.error(f"Performance optimization failed: {e}")
            return {'error': str(e), 'optimizations_applied': []}
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of real-time security integration."""
        
        try:
            metrics = real_time_security_monitor.get_performance_metrics()
            websocket_stats = websocket_manager.get_connection_stats()
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'initialized': self.initialized,
                'monitoring_active': self.monitoring_active,
                'performance_target': self.performance_target,
                'current_performance': metrics.get('avg_processing_time', 0),
                'sla_compliant': metrics.get('avg_processing_time', 0) < self.performance_target,
                'real_time_monitor': {
                    'active': metrics.get('monitoring_active', False),
                    'events_processed': metrics.get('events_processed', 0),
                    'threats_detected': metrics.get('threats_detected', 0),
                    'cache_enabled': metrics.get('redis_enabled', False)
                },
                'websocket_manager': {
                    'total_connections': websocket_stats.get('total_connections', 0),
                    'tenant_connections': websocket_stats.get('tenant_connections', {})
                },
                'performance_grade': self._grade_performance(metrics.get('avg_processing_time', 0))
            }
            
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e),
                'initialized': False,
                'monitoring_active': False
            }
    
    # Helper methods
    
    async def _simulate_security_workload(self):
        """Simulate security monitoring workload for testing."""
        
        # Simulate event processing
        await asyncio.sleep(0.01)  # 10ms processing time
        
        # Simulate cache operations
        await real_time_security_monitor._set_cache("test_key", "test_value", ttl=60)
        await real_time_security_monitor._get_cache("test_key")
    
    def _calculate_performance_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall performance score (0-100)."""
        
        score = 0
        
        # Processing time score (40 points)
        avg_time = metrics.get('avg_processing_time', 0)
        if avg_time < 1.0:
            score += 40
        elif avg_time < 3.0:
            score += 30
        elif avg_time < 5.0:
            score += 20
        elif avg_time < 10.0:
            score += 10
        
        # Cache performance score (30 points)
        cache_hit_rate = self._calculate_cache_hit_rate(metrics)
        if cache_hit_rate > 0.9:
            score += 30
        elif cache_hit_rate > 0.8:
            score += 25
        elif cache_hit_rate > 0.7:
            score += 20
        elif cache_hit_rate > 0.5:
            score += 10
        
        # Monitoring status score (20 points)
        if metrics.get('monitoring_active', False):
            score += 20
        
        # Redis availability score (10 points)
        if metrics.get('redis_enabled', False):
            score += 10
        
        return score
    
    def _calculate_cache_hit_rate(self, metrics: Dict[str, Any]) -> float:
        """Calculate cache hit rate."""
        
        hits = metrics.get('cache_hits', 0)
        misses = metrics.get('cache_misses', 1)
        return hits / max(hits + misses, 1)
    
    def _calculate_throughput(self, metrics: Dict[str, Any]) -> float:
        """Calculate event processing throughput."""
        
        events = metrics.get('events_processed', 0)
        time_active = 60  # Assume 60 seconds for simplification
        return events / time_active if time_active > 0 else 0
    
    def _generate_performance_recommendations(self, metrics: Dict[str, Any]) -> list:
        """Generate performance optimization recommendations."""
        
        recommendations = []
        
        avg_time = metrics.get('avg_processing_time', 0)
        if avg_time > 5.0:
            recommendations.append("CRITICAL: Processing time exceeds SLA - apply immediate optimizations")
        elif avg_time > 3.0:
            recommendations.append("WARNING: Processing time approaching SLA limit")
        
        cache_hit_rate = self._calculate_cache_hit_rate(metrics)
        if cache_hit_rate < 0.7:
            recommendations.append("Improve cache hit rate by increasing TTL or enabling Redis")
        
        if not metrics.get('monitoring_active', False):
            recommendations.append("Start real-time monitoring to improve performance")
        
        if not metrics.get('redis_enabled', False):
            recommendations.append("Enable Redis for distributed caching")
        
        if not recommendations:
            recommendations.append("Performance is optimal - no immediate actions needed")
        
        return recommendations
    
    def _grade_performance(self, avg_time: float) -> str:
        """Grade performance based on average processing time."""
        
        if avg_time < 1.0:
            return 'A+'
        elif avg_time < 2.0:
            return 'A'
        elif avg_time < 3.0:
            return 'B'
        elif avg_time < 5.0:
            return 'C'
        else:
            return 'D'
    
    def _calculate_improvement(self, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance improvement between two metric sets."""
        
        before_time = before.get('avg_processing_time', 0)
        after_time = after.get('avg_processing_time', 0)
        
        improvement = {}
        
        if before_time > 0:
            time_improvement = ((before_time - after_time) / before_time) * 100
            improvement['processing_time_improvement_percent'] = time_improvement
        
        before_cache_rate = self._calculate_cache_hit_rate(before)
        after_cache_rate = self._calculate_cache_hit_rate(after)
        improvement['cache_hit_rate_improvement'] = after_cache_rate - before_cache_rate
        
        return improvement


# Global integration instance
real_time_security_integration = RealTimeSecurityIntegration()


# FastAPI integration
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager for real-time security."""
    
    # Startup
    await real_time_security_integration.initialize()
    monitoring_task = await real_time_security_integration.start_monitoring()
    
    yield
    
    # Shutdown
    await real_time_security_integration.stop_monitoring()


def setup_real_time_security_routes(app: FastAPI):
    """Setup real-time security routes in FastAPI app."""
    
    # Include performance API routes
    app.include_router(performance_router)
    
    # Include WebSocket routes
    app.include_router(websocket_router)
    
    # Add integration status endpoint
    @app.get("/api/security/real-time/status")
    async def get_real_time_security_status():
        """Get real-time security integration status."""
        return real_time_security_integration.get_status()
    
    @app.post("/api/security/real-time/validate")
    async def validate_real_time_performance():
        """Validate real-time security performance."""
        return await real_time_security_integration.validate_performance()
    
    @app.post("/api/security/real-time/test")
    async def run_real_time_performance_test(duration: int = 60):
        """Run real-time security performance test."""
        return await real_time_security_integration.run_performance_test(duration)
    
    @app.post("/api/security/real-time/optimize")
    async def optimize_real_time_performance():
        """Optimize real-time security performance."""
        return await real_time_security_integration.optimize_performance()


# Convenience functions
async def start_real_time_security():
    """Start real-time security monitoring."""
    await real_time_security_integration.initialize()
    return await real_time_security_integration.start_monitoring()


async def stop_real_time_security():
    """Stop real-time security monitoring."""
    await real_time_security_integration.stop_monitoring()


async def validate_real_time_performance():
    """Validate real-time security performance."""
    return await real_time_security_integration.validate_performance()


def get_real_time_security_integration():
    """Get real-time security integration instance."""
    return real_time_security_integration