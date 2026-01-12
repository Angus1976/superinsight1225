"""
TCB Auto-Scaler for Automatic Scaling Configuration.

Provides auto-scaling configuration and management for TCB Cloud Run
deployments based on metrics from Prometheus integration.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class ScalingDirection(Enum):
    """Direction of scaling operation."""
    UP = "up"
    DOWN = "down"
    NONE = "none"


class ScalingMetricType(Enum):
    """Types of metrics used for scaling decisions."""
    CPU = "cpu"
    MEMORY = "memory"
    REQUEST_RATE = "request_rate"
    RESPONSE_TIME = "response_time"
    CUSTOM = "custom"


@dataclass
class ScalingRule:
    """A scaling rule definition."""
    name: str
    metric_type: ScalingMetricType
    threshold_up: float
    threshold_down: float
    scale_up_increment: int = 1
    scale_down_increment: int = 1
    cooldown_seconds: float = 300.0
    evaluation_periods: int = 3
    enabled: bool = True


@dataclass
class ScalingEvent:
    """A scaling event record."""
    timestamp: float
    direction: ScalingDirection
    rule_name: str
    metric_value: float
    previous_instances: int
    new_instances: int
    reason: str


@dataclass
class TCBAutoScalerConfig:
    """Configuration for TCB auto-scaler."""
    min_instances: int = 1
    max_instances: int = 10
    evaluation_interval: float = 60.0
    scale_up_cooldown: float = 300.0
    scale_down_cooldown: float = 600.0
    default_cpu_threshold_up: float = 70.0
    default_cpu_threshold_down: float = 30.0
    default_memory_threshold_up: float = 80.0
    default_memory_threshold_down: float = 40.0
    default_request_rate_threshold_up: float = 100.0
    default_request_rate_threshold_down: float = 20.0


class TCBAutoScaler:
    """
    Auto-scaler for TCB Cloud Run deployments.
    
    Features:
    - CPU-based scaling
    - Memory-based scaling
    - Request rate-based scaling
    - Response time-based scaling
    - Custom metric scaling
    - Cooldown management
    - Scaling event history
    """
    
    def __init__(self, config: Optional[TCBAutoScalerConfig] = None):
        self.config = config or TCBAutoScalerConfig()
        self.rules: Dict[str, ScalingRule] = {}
        self.current_instances: int = self.config.min_instances
        self.last_scale_up_time: float = 0.0
        self.last_scale_down_time: float = 0.0
        self.scaling_history: deque = deque(maxlen=1000)
        self.metric_history: Dict[str, deque] = {}
        self._is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._metrics_callback: Optional[callable] = None
        self._scale_callback: Optional[callable] = None
        
        # Register default rules
        self._register_default_rules()
        
        logger.info("TCBAutoScaler initialized")
    
    def _register_default_rules(self):
        """Register default scaling rules."""
        default_rules = [
            ScalingRule(
                name="cpu_scaling",
                metric_type=ScalingMetricType.CPU,
                threshold_up=self.config.default_cpu_threshold_up,
                threshold_down=self.config.default_cpu_threshold_down,
                scale_up_increment=1,
                scale_down_increment=1,
                cooldown_seconds=self.config.scale_up_cooldown
            ),
            ScalingRule(
                name="memory_scaling",
                metric_type=ScalingMetricType.MEMORY,
                threshold_up=self.config.default_memory_threshold_up,
                threshold_down=self.config.default_memory_threshold_down,
                scale_up_increment=1,
                scale_down_increment=1,
                cooldown_seconds=self.config.scale_up_cooldown
            ),
            ScalingRule(
                name="request_rate_scaling",
                metric_type=ScalingMetricType.REQUEST_RATE,
                threshold_up=self.config.default_request_rate_threshold_up,
                threshold_down=self.config.default_request_rate_threshold_down,
                scale_up_increment=2,
                scale_down_increment=1,
                cooldown_seconds=self.config.scale_up_cooldown
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.name] = rule
            self.metric_history[rule.name] = deque(maxlen=100)
    
    def set_metrics_callback(self, callback: callable):
        """Set callback for fetching current metrics."""
        self._metrics_callback = callback
    
    def set_scale_callback(self, callback: callable):
        """Set callback for executing scaling operations."""
        self._scale_callback = callback
    
    def add_rule(self, rule: ScalingRule):
        """Add a scaling rule."""
        self.rules[rule.name] = rule
        self.metric_history[rule.name] = deque(maxlen=100)
        logger.info(f"Added scaling rule: {rule.name}")
    
    def remove_rule(self, rule_name: str) -> bool:
        """Remove a scaling rule."""
        if rule_name in self.rules:
            del self.rules[rule_name]
            if rule_name in self.metric_history:
                del self.metric_history[rule_name]
            logger.info(f"Removed scaling rule: {rule_name}")
            return True
        return False
    
    def enable_rule(self, rule_name: str) -> bool:
        """Enable a scaling rule."""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = True
            return True
        return False
    
    def disable_rule(self, rule_name: str) -> bool:
        """Disable a scaling rule."""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = False
            return True
        return False
    
    async def start(self):
        """Start the auto-scaler monitoring loop."""
        if self._is_running:
            return
        
        self._is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("TCBAutoScaler started")
    
    async def stop(self):
        """Stop the auto-scaler."""
        self._is_running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("TCBAutoScaler stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop for auto-scaling."""
        while self._is_running:
            try:
                await self._evaluate_scaling()
                await asyncio.sleep(self.config.evaluation_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in auto-scaler monitor loop: {e}")
                await asyncio.sleep(10)
    
    async def _evaluate_scaling(self):
        """Evaluate all scaling rules and make scaling decisions."""
        if not self._metrics_callback:
            return
        
        try:
            # Get current metrics
            metrics = await self._metrics_callback()
            
            # Evaluate each rule
            scale_up_needed = False
            scale_down_possible = True
            scale_up_rule = None
            scale_down_rule = None
            
            for rule_name, rule in self.rules.items():
                if not rule.enabled:
                    continue
                
                metric_value = self._get_metric_value(metrics, rule.metric_type)
                if metric_value is None:
                    continue
                
                # Record metric
                self.metric_history[rule_name].append({
                    "timestamp": time.time(),
                    "value": metric_value
                })
                
                # Check if we have enough data points
                if len(self.metric_history[rule_name]) < rule.evaluation_periods:
                    continue
                
                # Calculate average over evaluation periods
                recent_values = list(self.metric_history[rule_name])[-rule.evaluation_periods:]
                avg_value = sum(v["value"] for v in recent_values) / len(recent_values)
                
                # Check thresholds
                if avg_value >= rule.threshold_up:
                    scale_up_needed = True
                    scale_up_rule = rule
                
                if avg_value > rule.threshold_down:
                    scale_down_possible = False
                else:
                    scale_down_rule = rule
            
            # Execute scaling decision
            current_time = time.time()
            
            if scale_up_needed and scale_up_rule:
                if current_time - self.last_scale_up_time >= self.config.scale_up_cooldown:
                    await self._scale_up(scale_up_rule, metrics)
            elif scale_down_possible and scale_down_rule:
                if current_time - self.last_scale_down_time >= self.config.scale_down_cooldown:
                    await self._scale_down(scale_down_rule, metrics)
                    
        except Exception as e:
            logger.error(f"Error evaluating scaling: {e}")
    
    def _get_metric_value(self, metrics: Dict[str, Any], metric_type: ScalingMetricType) -> Optional[float]:
        """Get metric value from metrics dict."""
        metric_map = {
            ScalingMetricType.CPU: "cpu_usage_percent",
            ScalingMetricType.MEMORY: "memory_usage_percent",
            ScalingMetricType.REQUEST_RATE: "request_rate",
            ScalingMetricType.RESPONSE_TIME: "response_time_p95"
        }
        
        key = metric_map.get(metric_type)
        if key and key in metrics:
            return metrics[key]
        return None
    
    async def _scale_up(self, rule: ScalingRule, metrics: Dict[str, Any]):
        """Execute scale up operation."""
        if self.current_instances >= self.config.max_instances:
            logger.info("Already at max instances, cannot scale up")
            return
        
        new_instances = min(
            self.current_instances + rule.scale_up_increment,
            self.config.max_instances
        )
        
        metric_value = self._get_metric_value(metrics, rule.metric_type)
        
        event = ScalingEvent(
            timestamp=time.time(),
            direction=ScalingDirection.UP,
            rule_name=rule.name,
            metric_value=metric_value or 0,
            previous_instances=self.current_instances,
            new_instances=new_instances,
            reason=f"{rule.metric_type.value} exceeded threshold {rule.threshold_up}"
        )
        
        # Execute scaling
        if self._scale_callback:
            success = await self._scale_callback(new_instances)
            if success:
                self.current_instances = new_instances
                self.last_scale_up_time = time.time()
                self.scaling_history.append(event)
                logger.info(f"Scaled up: {event.previous_instances} -> {event.new_instances}")
        else:
            # Simulate scaling for testing
            self.current_instances = new_instances
            self.last_scale_up_time = time.time()
            self.scaling_history.append(event)
            logger.info(f"Scaled up (simulated): {event.previous_instances} -> {event.new_instances}")
    
    async def _scale_down(self, rule: ScalingRule, metrics: Dict[str, Any]):
        """Execute scale down operation."""
        if self.current_instances <= self.config.min_instances:
            logger.info("Already at min instances, cannot scale down")
            return
        
        new_instances = max(
            self.current_instances - rule.scale_down_increment,
            self.config.min_instances
        )
        
        metric_value = self._get_metric_value(metrics, rule.metric_type)
        
        event = ScalingEvent(
            timestamp=time.time(),
            direction=ScalingDirection.DOWN,
            rule_name=rule.name,
            metric_value=metric_value or 0,
            previous_instances=self.current_instances,
            new_instances=new_instances,
            reason=f"{rule.metric_type.value} below threshold {rule.threshold_down}"
        )
        
        # Execute scaling
        if self._scale_callback:
            success = await self._scale_callback(new_instances)
            if success:
                self.current_instances = new_instances
                self.last_scale_down_time = time.time()
                self.scaling_history.append(event)
                logger.info(f"Scaled down: {event.previous_instances} -> {event.new_instances}")
        else:
            # Simulate scaling for testing
            self.current_instances = new_instances
            self.last_scale_down_time = time.time()
            self.scaling_history.append(event)
            logger.info(f"Scaled down (simulated): {event.previous_instances} -> {event.new_instances}")
    
    async def manual_scale(self, target_instances: int) -> bool:
        """Manually scale to a specific number of instances."""
        if target_instances < self.config.min_instances or target_instances > self.config.max_instances:
            logger.error(f"Target instances {target_instances} out of range [{self.config.min_instances}, {self.config.max_instances}]")
            return False
        
        previous = self.current_instances
        
        if self._scale_callback:
            success = await self._scale_callback(target_instances)
            if not success:
                return False
        
        self.current_instances = target_instances
        
        direction = ScalingDirection.UP if target_instances > previous else ScalingDirection.DOWN
        if target_instances == previous:
            direction = ScalingDirection.NONE
        
        event = ScalingEvent(
            timestamp=time.time(),
            direction=direction,
            rule_name="manual",
            metric_value=0,
            previous_instances=previous,
            new_instances=target_instances,
            reason="Manual scaling operation"
        )
        self.scaling_history.append(event)
        
        logger.info(f"Manual scale: {previous} -> {target_instances}")
        return True
    
    def get_current_state(self) -> Dict[str, Any]:
        """Get current auto-scaler state."""
        return {
            "current_instances": self.current_instances,
            "min_instances": self.config.min_instances,
            "max_instances": self.config.max_instances,
            "is_running": self._is_running,
            "last_scale_up": self.last_scale_up_time,
            "last_scale_down": self.last_scale_down_time,
            "rules": {
                name: {
                    "metric_type": rule.metric_type.value,
                    "threshold_up": rule.threshold_up,
                    "threshold_down": rule.threshold_down,
                    "enabled": rule.enabled
                }
                for name, rule in self.rules.items()
            }
        }
    
    def get_scaling_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get scaling history."""
        history = list(self.scaling_history)[-limit:]
        return [
            {
                "timestamp": e.timestamp,
                "direction": e.direction.value,
                "rule_name": e.rule_name,
                "metric_value": e.metric_value,
                "previous_instances": e.previous_instances,
                "new_instances": e.new_instances,
                "reason": e.reason
            }
            for e in history
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get auto-scaler statistics."""
        history = list(self.scaling_history)
        scale_ups = sum(1 for e in history if e.direction == ScalingDirection.UP)
        scale_downs = sum(1 for e in history if e.direction == ScalingDirection.DOWN)
        
        return {
            "total_scaling_events": len(history),
            "scale_up_events": scale_ups,
            "scale_down_events": scale_downs,
            "current_instances": self.current_instances,
            "min_instances": self.config.min_instances,
            "max_instances": self.config.max_instances,
            "active_rules": sum(1 for r in self.rules.values() if r.enabled),
            "total_rules": len(self.rules)
        }


# Global auto-scaler instance
tcb_auto_scaler: Optional[TCBAutoScaler] = None


def initialize_tcb_auto_scaler(
    config: Optional[TCBAutoScalerConfig] = None
) -> TCBAutoScaler:
    """Initialize the global TCB auto-scaler."""
    global tcb_auto_scaler
    tcb_auto_scaler = TCBAutoScaler(config)
    return tcb_auto_scaler


def get_tcb_auto_scaler() -> Optional[TCBAutoScaler]:
    """Get the global TCB auto-scaler instance."""
    return tcb_auto_scaler
