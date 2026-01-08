"""
Intelligent Operations System for SuperInsight Platform.

Provides AI-driven operations capabilities including:
- Machine learning-based anomaly detection and prediction
- System failure prediction using time series analysis
- Capacity planning and resource forecasting
- Intelligent operational recommendations
- Predictive maintenance scheduling
"""

import asyncio
import logging
import time
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import json
import pickle
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error

from src.monitoring.advanced_anomaly_detection import AdvancedAnomalyDetector, AnomalyType, AnomalySeverity
from src.system.monitoring import MetricsCollector, PerformanceMonitor
from src.system.fault_detection_system import FaultDetectionSystem, FaultType, FaultSeverity

logger = logging.getLogger(__name__)


class PredictionType(Enum):
    """Types of predictions the system can make."""
    FAILURE_PREDICTION = "failure_prediction"
    CAPACITY_PLANNING = "capacity_planning"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    MAINTENANCE_SCHEDULING = "maintenance_scheduling"


class RecommendationType(Enum):
    """Types of operational recommendations."""
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    OPTIMIZE_PERFORMANCE = "optimize_performance"
    PREVENTIVE_MAINTENANCE = "preventive_maintenance"
    CONFIGURATION_CHANGE = "configuration_change"
    RESOURCE_REALLOCATION = "resource_reallocation"


@dataclass
class Prediction:
    """Prediction result with confidence and timeline."""
    prediction_id: str
    prediction_type: PredictionType
    target_metric: str
    predicted_value: float
    confidence: float
    prediction_horizon: int  # hours
    created_at: datetime
    features_used: List[str]
    model_accuracy: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationalRecommendation:
    """Operational recommendation with impact analysis."""
    recommendation_id: str
    recommendation_type: RecommendationType
    title: str
    description: str
    priority: str  # low, medium, high, critical
    estimated_impact: Dict[str, float]  # performance, cost, reliability
    implementation_effort: str  # low, medium, high
    timeline: str  # immediate, short_term, long_term
    prerequisites: List[str]
    risks: List[str]
    created_at: datetime
    expires_at: Optional[datetime] = None


@dataclass
class CapacityForecast:
    """Capacity planning forecast."""
    resource_type: str
    current_usage: float
    predicted_usage: List[float]  # Next 24 hours
    capacity_limit: float
    time_to_exhaustion: Optional[int]  # hours
    recommended_action: str
    confidence: float
    created_at: datetime


class MLPredictor:
    """
    Machine learning predictor for system metrics and failures.
    
    Uses ensemble methods to predict system behavior and potential issues.
    """
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.feature_importance: Dict[str, Dict[str, float]] = {}
        self.model_accuracy: Dict[str, float] = {}
        self.training_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self.last_training: Dict[str, datetime] = {}
        
        # Model configuration
        self.min_training_samples = 100
        self.retrain_interval_hours = 24
        self.feature_window = 24  # hours of features to use
        
    def add_training_data(self, metric_name: str, features: Dict[str, float], target: float):
        """Add training data for a metric."""
        data_point = {
            'timestamp': time.time(),
            'features': features.copy(),
            'target': target
        }
        self.training_data[metric_name].append(data_point)
    
    async def train_model(self, metric_name: str) -> bool:
        """Train prediction model for a metric."""
        try:
            if len(self.training_data[metric_name]) < self.min_training_samples:
                logger.debug(f"Insufficient training data for {metric_name}: {len(self.training_data[metric_name])}")
                return False
            
            # Prepare training data
            data = list(self.training_data[metric_name])
            
            # Extract features and targets
            feature_names = list(data[0]['features'].keys())
            X = np.array([[point['features'][fname] for fname in feature_names] for point in data])
            y = np.array([point['target'] for point in data])
            
            # Handle missing values
            X = np.nan_to_num(X, nan=0.0)
            y = np.nan_to_num(y, nan=0.0)
            
            if len(np.unique(y)) < 2:
                logger.warning(f"Insufficient target variance for {metric_name}")
                return False
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            
            # Calculate R² score
            ss_res = np.sum((y_test - y_pred) ** 2)
            ss_tot = np.sum((y_test - np.mean(y_test)) ** 2)
            r2_score = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            # Store model and metadata
            self.models[metric_name] = model
            self.scalers[metric_name] = scaler
            self.model_accuracy[metric_name] = max(0, r2_score)
            self.last_training[metric_name] = datetime.utcnow()
            
            # Store feature importance
            self.feature_importance[metric_name] = dict(zip(feature_names, model.feature_importances_))
            
            logger.info(f"Trained model for {metric_name}: R²={r2_score:.3f}, MSE={mse:.3f}, MAE={mae:.3f}")
            return True
            
        except Exception as e:
            logger.error(f"Error training model for {metric_name}: {e}")
            return False
    
    async def predict(self, metric_name: str, features: Dict[str, float]) -> Optional[Tuple[float, float]]:
        """Make prediction for a metric."""
        try:
            if metric_name not in self.models:
                return None
            
            model = self.models[metric_name]
            scaler = self.scalers[metric_name]
            
            # Prepare features
            feature_names = list(self.feature_importance[metric_name].keys())
            X = np.array([[features.get(fname, 0.0) for fname in feature_names]])
            X = np.nan_to_num(X, nan=0.0)
            
            # Scale and predict
            X_scaled = scaler.transform(X)
            prediction = model.predict(X_scaled)[0]
            
            # Estimate confidence based on model accuracy
            confidence = self.model_accuracy.get(metric_name, 0.5)
            
            return prediction, confidence
            
        except Exception as e:
            logger.error(f"Error making prediction for {metric_name}: {e}")
            return None
    
    def needs_retraining(self, metric_name: str) -> bool:
        """Check if model needs retraining."""
        if metric_name not in self.last_training:
            return True
        
        last_train = self.last_training[metric_name]
        hours_since_training = (datetime.utcnow() - last_train).total_seconds() / 3600
        
        return hours_since_training >= self.retrain_interval_hours


class CapacityPlanner:
    """
    Capacity planning system with predictive analytics.
    
    Forecasts resource usage and provides capacity recommendations.
    """
    
    def __init__(self, ml_predictor: MLPredictor):
        self.ml_predictor = ml_predictor
        self.resource_limits = {
            'cpu_usage_percent': 80.0,
            'memory_usage_percent': 85.0,
            'disk_usage_percent': 90.0,
            'network_bandwidth_mbps': 1000.0
        }
        self.growth_rates = {}  # Historical growth rates
        self.seasonal_patterns = {}  # Seasonal usage patterns
        
    async def generate_capacity_forecast(self, resource_type: str, current_metrics: Dict[str, float]) -> CapacityForecast:
        """Generate capacity forecast for a resource."""
        try:
            current_usage = current_metrics.get(resource_type, 0.0)
            capacity_limit = self.resource_limits.get(resource_type, 100.0)
            
            # Generate hourly predictions for next 24 hours
            predicted_usage = []
            confidence_sum = 0.0
            
            for hour in range(24):
                # Create features for prediction
                features = current_metrics.copy()
                features['hour_of_day'] = (datetime.utcnow().hour + hour) % 24
                features['day_of_week'] = datetime.utcnow().weekday()
                features['time_offset'] = hour
                
                # Get prediction
                prediction_result = await self.ml_predictor.predict(resource_type, features)
                
                if prediction_result:
                    predicted_value, confidence = prediction_result
                    predicted_usage.append(max(0, predicted_value))
                    confidence_sum += confidence
                else:
                    # Fallback to trend-based prediction
                    growth_rate = self.growth_rates.get(resource_type, 0.01)  # 1% per hour default
                    predicted_value = current_usage * (1 + growth_rate * hour)
                    predicted_usage.append(predicted_value)
                    confidence_sum += 0.5
            
            avg_confidence = confidence_sum / 24
            
            # Calculate time to exhaustion
            time_to_exhaustion = None
            for i, usage in enumerate(predicted_usage):
                if usage >= capacity_limit:
                    time_to_exhaustion = i + 1
                    break
            
            # Generate recommendation
            max_predicted = max(predicted_usage)
            if time_to_exhaustion and time_to_exhaustion <= 8:  # Within 8 hours
                recommended_action = f"URGENT: Scale up {resource_type} immediately"
            elif max_predicted >= capacity_limit * 0.9:  # 90% of limit
                recommended_action = f"Scale up {resource_type} within 24 hours"
            elif max_predicted >= capacity_limit * 0.8:  # 80% of limit
                recommended_action = f"Plan to scale up {resource_type} within 48 hours"
            else:
                recommended_action = f"No immediate action needed for {resource_type}"
            
            return CapacityForecast(
                resource_type=resource_type,
                current_usage=current_usage,
                predicted_usage=predicted_usage,
                capacity_limit=capacity_limit,
                time_to_exhaustion=time_to_exhaustion,
                recommended_action=recommended_action,
                confidence=avg_confidence,
                created_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error generating capacity forecast for {resource_type}: {e}")
            return CapacityForecast(
                resource_type=resource_type,
                current_usage=0.0,
                predicted_usage=[0.0] * 24,
                capacity_limit=100.0,
                time_to_exhaustion=None,
                recommended_action="Error generating forecast",
                confidence=0.0,
                created_at=datetime.utcnow()
            )
    
    def update_growth_rate(self, resource_type: str, historical_data: List[Tuple[float, float]]):
        """Update growth rate based on historical data."""
        try:
            if len(historical_data) < 2:
                return
            
            # Calculate growth rate using linear regression
            timestamps = np.array([t for t, _ in historical_data])
            values = np.array([v for _, v in historical_data])
            
            # Normalize timestamps to hours
            timestamps = (timestamps - timestamps[0]) / 3600
            
            # Calculate slope (growth rate per hour)
            if len(timestamps) > 1:
                slope = np.polyfit(timestamps, values, 1)[0]
                # Convert to percentage growth rate
                avg_value = np.mean(values)
                if avg_value > 0:
                    growth_rate = slope / avg_value
                    self.growth_rates[resource_type] = max(-0.1, min(0.1, growth_rate))  # Clamp to ±10%
            
        except Exception as e:
            logger.error(f"Error updating growth rate for {resource_type}: {e}")


class IntelligentRecommendationEngine:
    """
    Intelligent recommendation engine for operational improvements.
    
    Analyzes system state and generates actionable recommendations.
    """
    
    def __init__(self, ml_predictor: MLPredictor, capacity_planner: CapacityPlanner):
        self.ml_predictor = ml_predictor
        self.capacity_planner = capacity_planner
        self.recommendation_history: deque = deque(maxlen=1000)
        self.recommendation_effectiveness: Dict[str, float] = {}
        
    async def generate_recommendations(self, system_metrics: Dict[str, float], 
                                    anomalies: List[Dict[str, Any]],
                                    capacity_forecasts: List[CapacityForecast]) -> List[OperationalRecommendation]:
        """Generate intelligent operational recommendations."""
        recommendations = []
        
        try:
            # Performance optimization recommendations
            perf_recommendations = await self._generate_performance_recommendations(system_metrics)
            recommendations.extend(perf_recommendations)
            
            # Capacity planning recommendations
            capacity_recommendations = await self._generate_capacity_recommendations(capacity_forecasts)
            recommendations.extend(capacity_recommendations)
            
            # Anomaly-based recommendations
            anomaly_recommendations = await self._generate_anomaly_recommendations(anomalies)
            recommendations.extend(anomaly_recommendations)
            
            # Preventive maintenance recommendations
            maintenance_recommendations = await self._generate_maintenance_recommendations(system_metrics)
            recommendations.extend(maintenance_recommendations)
            
            # Sort by priority and impact
            recommendations.sort(key=lambda r: self._calculate_recommendation_score(r), reverse=True)
            
            # Store recommendations
            for rec in recommendations:
                self.recommendation_history.append(rec)
            
            return recommendations[:10]  # Return top 10 recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    async def _generate_performance_recommendations(self, metrics: Dict[str, float]) -> List[OperationalRecommendation]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        try:
            cpu_usage = metrics.get('system.cpu.usage_percent', 0)
            memory_usage = metrics.get('system.memory.usage_percent', 0)
            response_time = metrics.get('requests.duration', 0)
            
            # High CPU usage recommendation
            if cpu_usage > 80:
                recommendations.append(OperationalRecommendation(
                    recommendation_id=f"perf_cpu_{int(time.time())}",
                    recommendation_type=RecommendationType.OPTIMIZE_PERFORMANCE,
                    title="Optimize CPU Usage",
                    description=f"CPU usage is high at {cpu_usage:.1f}%. Consider optimizing CPU-intensive operations or scaling up.",
                    priority="high" if cpu_usage > 90 else "medium",
                    estimated_impact={"performance": 0.3, "cost": -0.1, "reliability": 0.2},
                    implementation_effort="medium",
                    timeline="short_term",
                    prerequisites=["Performance profiling", "Resource analysis"],
                    risks=["Temporary service disruption during optimization"],
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(hours=24)
                ))
            
            # High memory usage recommendation
            if memory_usage > 85:
                recommendations.append(OperationalRecommendation(
                    recommendation_id=f"perf_mem_{int(time.time())}",
                    recommendation_type=RecommendationType.OPTIMIZE_PERFORMANCE,
                    title="Optimize Memory Usage",
                    description=f"Memory usage is high at {memory_usage:.1f}%. Review memory leaks and optimize data structures.",
                    priority="high" if memory_usage > 95 else "medium",
                    estimated_impact={"performance": 0.4, "cost": 0.0, "reliability": 0.3},
                    implementation_effort="medium",
                    timeline="short_term",
                    prerequisites=["Memory profiling", "Application analysis"],
                    risks=["Potential memory-related crashes"],
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(hours=12)
                ))
            
            # Slow response time recommendation
            if response_time > 2.0:
                recommendations.append(OperationalRecommendation(
                    recommendation_id=f"perf_resp_{int(time.time())}",
                    recommendation_type=RecommendationType.OPTIMIZE_PERFORMANCE,
                    title="Improve Response Time",
                    description=f"Average response time is {response_time:.2f}s. Optimize database queries and implement caching.",
                    priority="medium",
                    estimated_impact={"performance": 0.5, "cost": -0.05, "reliability": 0.1},
                    implementation_effort="high",
                    timeline="long_term",
                    prerequisites=["Performance analysis", "Database optimization"],
                    risks=["Complexity increase", "Potential cache inconsistency"],
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=7)
                ))
            
        except Exception as e:
            logger.error(f"Error generating performance recommendations: {e}")
        
        return recommendations
    
    async def _generate_capacity_recommendations(self, forecasts: List[CapacityForecast]) -> List[OperationalRecommendation]:
        """Generate capacity planning recommendations."""
        recommendations = []
        
        try:
            for forecast in forecasts:
                if forecast.time_to_exhaustion and forecast.time_to_exhaustion <= 24:
                    priority = "critical" if forecast.time_to_exhaustion <= 8 else "high"
                    
                    recommendations.append(OperationalRecommendation(
                        recommendation_id=f"capacity_{forecast.resource_type}_{int(time.time())}",
                        recommendation_type=RecommendationType.SCALE_UP,
                        title=f"Scale Up {forecast.resource_type.replace('_', ' ').title()}",
                        description=f"Resource will reach capacity in {forecast.time_to_exhaustion} hours. {forecast.recommended_action}",
                        priority=priority,
                        estimated_impact={"performance": 0.4, "cost": -0.3, "reliability": 0.5},
                        implementation_effort="low" if "cpu" in forecast.resource_type or "memory" in forecast.resource_type else "medium",
                        timeline="immediate" if forecast.time_to_exhaustion <= 4 else "short_term",
                        prerequisites=["Resource availability check", "Budget approval"],
                        risks=["Increased operational costs", "Potential over-provisioning"],
                        created_at=datetime.utcnow(),
                        expires_at=datetime.utcnow() + timedelta(hours=forecast.time_to_exhaustion or 24)
                    ))
                
                elif max(forecast.predicted_usage) < forecast.capacity_limit * 0.5:
                    # Over-provisioned resource
                    recommendations.append(OperationalRecommendation(
                        recommendation_id=f"downscale_{forecast.resource_type}_{int(time.time())}",
                        recommendation_type=RecommendationType.SCALE_DOWN,
                        title=f"Consider Scaling Down {forecast.resource_type.replace('_', ' ').title()}",
                        description=f"Resource utilization is consistently low. Consider scaling down to optimize costs.",
                        priority="low",
                        estimated_impact={"performance": -0.1, "cost": 0.3, "reliability": -0.05},
                        implementation_effort="low",
                        timeline="long_term",
                        prerequisites=["Usage pattern analysis", "Performance impact assessment"],
                        risks=["Potential performance degradation", "Insufficient capacity during peaks"],
                        created_at=datetime.utcnow(),
                        expires_at=datetime.utcnow() + timedelta(days=30)
                    ))
            
        except Exception as e:
            logger.error(f"Error generating capacity recommendations: {e}")
        
        return recommendations
    
    async def _generate_anomaly_recommendations(self, anomalies: List[Dict[str, Any]]) -> List[OperationalRecommendation]:
        """Generate recommendations based on detected anomalies."""
        recommendations = []
        
        try:
            for anomaly in anomalies:
                anomaly_type = anomaly.get('anomaly_type', 'unknown')
                severity = anomaly.get('severity', 'low')
                metric_name = anomaly.get('metric_name', 'unknown')
                
                if severity in ['high', 'critical']:
                    recommendations.append(OperationalRecommendation(
                        recommendation_id=f"anomaly_{anomaly.get('id', int(time.time()))}",
                        recommendation_type=RecommendationType.OPTIMIZE_PERFORMANCE,
                        title=f"Investigate {anomaly_type.replace('_', ' ').title()} Anomaly",
                        description=f"Anomaly detected in {metric_name}. Investigate root cause and implement corrective measures.",
                        priority=severity,
                        estimated_impact={"performance": 0.3, "cost": 0.0, "reliability": 0.4},
                        implementation_effort="medium",
                        timeline="immediate" if severity == "critical" else "short_term",
                        prerequisites=["Anomaly investigation", "Root cause analysis"],
                        risks=["Potential system instability", "Service degradation"],
                        created_at=datetime.utcnow(),
                        expires_at=datetime.utcnow() + timedelta(hours=4 if severity == "critical" else 24)
                    ))
            
        except Exception as e:
            logger.error(f"Error generating anomaly recommendations: {e}")
        
        return recommendations
    
    async def _generate_maintenance_recommendations(self, metrics: Dict[str, float]) -> List[OperationalRecommendation]:
        """Generate preventive maintenance recommendations."""
        recommendations = []
        
        try:
            # Database maintenance
            db_query_time = metrics.get('database.query.duration', 0)
            if db_query_time > 1.0:
                recommendations.append(OperationalRecommendation(
                    recommendation_id=f"maint_db_{int(time.time())}",
                    recommendation_type=RecommendationType.PREVENTIVE_MAINTENANCE,
                    title="Database Maintenance Required",
                    description=f"Database query time is {db_query_time:.2f}s. Schedule maintenance to optimize performance.",
                    priority="medium",
                    estimated_impact={"performance": 0.3, "cost": -0.1, "reliability": 0.2},
                    implementation_effort="high",
                    timeline="long_term",
                    prerequisites=["Maintenance window scheduling", "Database backup"],
                    risks=["Service downtime during maintenance", "Potential data corruption"],
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=7)
                ))
            
            # Log cleanup
            disk_usage = metrics.get('system.disk.usage_percent', 0)
            if disk_usage > 80:
                recommendations.append(OperationalRecommendation(
                    recommendation_id=f"maint_logs_{int(time.time())}",
                    recommendation_type=RecommendationType.PREVENTIVE_MAINTENANCE,
                    title="Log Cleanup Required",
                    description=f"Disk usage is {disk_usage:.1f}%. Clean up old logs and temporary files.",
                    priority="medium" if disk_usage > 90 else "low",
                    estimated_impact={"performance": 0.1, "cost": 0.0, "reliability": 0.2},
                    implementation_effort="low",
                    timeline="short_term",
                    prerequisites=["Log retention policy review"],
                    risks=["Loss of historical data"],
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=3)
                ))
            
        except Exception as e:
            logger.error(f"Error generating maintenance recommendations: {e}")
        
        return recommendations
    
    def _calculate_recommendation_score(self, recommendation: OperationalRecommendation) -> float:
        """Calculate priority score for recommendation ranking."""
        try:
            # Priority weights
            priority_weights = {"critical": 1.0, "high": 0.8, "medium": 0.6, "low": 0.4}
            priority_score = priority_weights.get(recommendation.priority, 0.5)
            
            # Impact score (average of positive impacts)
            impact_values = [v for v in recommendation.estimated_impact.values() if v > 0]
            impact_score = sum(impact_values) / len(impact_values) if impact_values else 0
            
            # Effort penalty (lower effort = higher score)
            effort_weights = {"low": 1.0, "medium": 0.7, "high": 0.4}
            effort_score = effort_weights.get(recommendation.implementation_effort, 0.5)
            
            # Timeline urgency
            timeline_weights = {"immediate": 1.0, "short_term": 0.8, "long_term": 0.6}
            timeline_score = timeline_weights.get(recommendation.timeline, 0.5)
            
            # Calculate weighted score
            total_score = (priority_score * 0.4 + impact_score * 0.3 + 
                          effort_score * 0.2 + timeline_score * 0.1)
            
            return total_score
            
        except Exception as e:
            logger.error(f"Error calculating recommendation score: {e}")
            return 0.0


class IntelligentOperationsSystem:
    """
    Main intelligent operations system coordinating all AI-driven operations.
    
    Integrates anomaly detection, prediction, capacity planning, and recommendations.
    """
    
    def __init__(self, metrics_collector: MetricsCollector, 
                 anomaly_detector: AdvancedAnomalyDetector,
                 fault_detector: FaultDetectionSystem):
        self.metrics_collector = metrics_collector
        self.anomaly_detector = anomaly_detector
        self.fault_detector = fault_detector
        
        # AI components
        self.ml_predictor = MLPredictor()
        self.capacity_planner = CapacityPlanner(self.ml_predictor)
        self.recommendation_engine = IntelligentRecommendationEngine(
            self.ml_predictor, self.capacity_planner
        )
        
        # System state
        self.is_running = False
        self.analysis_task: Optional[asyncio.Task] = None
        self.predictions: Dict[str, Prediction] = {}
        self.capacity_forecasts: Dict[str, CapacityForecast] = {}
        self.recommendations: List[OperationalRecommendation] = []
        
        # Configuration
        self.analysis_interval = 300  # 5 minutes
        self.prediction_metrics = [
            'system.cpu.usage_percent',
            'system.memory.usage_percent',
            'system.disk.usage_percent',
            'requests.duration',
            'database.query.duration'
        ]
    
    async def start(self):
        """Start the intelligent operations system."""
        if self.is_running:
            logger.warning("Intelligent operations system is already running")
            return
        
        self.is_running = True
        self.analysis_task = asyncio.create_task(self._analysis_loop())
        
        logger.info("Intelligent operations system started")
    
    async def stop(self):
        """Stop the intelligent operations system."""
        self.is_running = False
        
        if self.analysis_task:
            self.analysis_task.cancel()
            try:
                await self.analysis_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Intelligent operations system stopped")
    
    async def _analysis_loop(self):
        """Main analysis loop for intelligent operations."""
        while self.is_running:
            try:
                # Collect current metrics
                current_metrics = self.metrics_collector.get_all_metrics_summary()
                
                # Update ML models with training data
                await self._update_ml_models(current_metrics)
                
                # Generate predictions
                await self._generate_predictions(current_metrics)
                
                # Generate capacity forecasts
                await self._generate_capacity_forecasts(current_metrics)
                
                # Get current anomalies
                active_anomalies = self.anomaly_detector.get_active_anomalies()
                
                # Generate recommendations
                self.recommendations = await self.recommendation_engine.generate_recommendations(
                    system_metrics=self._flatten_metrics(current_metrics),
                    anomalies=active_anomalies,
                    capacity_forecasts=list(self.capacity_forecasts.values())
                )
                
                # Log insights
                await self._log_insights()
                
                # Sleep until next analysis
                await asyncio.sleep(self.analysis_interval)
                
            except Exception as e:
                logger.error(f"Error in intelligent operations analysis loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _update_ml_models(self, metrics_summary: Dict[str, Dict[str, Any]]):
        """Update ML models with new training data."""
        try:
            flat_metrics = self._flatten_metrics(metrics_summary)
            
            for metric_name in self.prediction_metrics:
                if metric_name in flat_metrics:
                    # Create features from other metrics
                    features = {k: v for k, v in flat_metrics.items() if k != metric_name}
                    features['hour_of_day'] = datetime.utcnow().hour
                    features['day_of_week'] = datetime.utcnow().weekday()
                    
                    target_value = flat_metrics[metric_name]
                    
                    # Add training data
                    self.ml_predictor.add_training_data(metric_name, features, target_value)
                    
                    # Retrain if needed
                    if self.ml_predictor.needs_retraining(metric_name):
                        await self.ml_predictor.train_model(metric_name)
            
        except Exception as e:
            logger.error(f"Error updating ML models: {e}")
    
    async def _generate_predictions(self, metrics_summary: Dict[str, Dict[str, Any]]):
        """Generate predictions for key metrics."""
        try:
            flat_metrics = self._flatten_metrics(metrics_summary)
            
            for metric_name in self.prediction_metrics:
                # Create features for prediction
                features = {k: v for k, v in flat_metrics.items() if k != metric_name}
                features['hour_of_day'] = (datetime.utcnow().hour + 1) % 24  # Next hour
                features['day_of_week'] = datetime.utcnow().weekday()
                
                # Get prediction
                prediction_result = await self.ml_predictor.predict(metric_name, features)
                
                if prediction_result:
                    predicted_value, confidence = prediction_result
                    
                    prediction = Prediction(
                        prediction_id=f"pred_{metric_name}_{int(time.time())}",
                        prediction_type=PredictionType.PERFORMANCE_DEGRADATION,
                        target_metric=metric_name,
                        predicted_value=predicted_value,
                        confidence=confidence,
                        prediction_horizon=1,  # 1 hour
                        created_at=datetime.utcnow(),
                        features_used=list(features.keys()),
                        model_accuracy=self.ml_predictor.model_accuracy.get(metric_name, 0.0)
                    )
                    
                    self.predictions[metric_name] = prediction
            
        except Exception as e:
            logger.error(f"Error generating predictions: {e}")
    
    async def _generate_capacity_forecasts(self, metrics_summary: Dict[str, Dict[str, Any]]):
        """Generate capacity forecasts for resources."""
        try:
            flat_metrics = self._flatten_metrics(metrics_summary)
            
            resource_types = [
                'system.cpu.usage_percent',
                'system.memory.usage_percent',
                'system.disk.usage_percent'
            ]
            
            for resource_type in resource_types:
                if resource_type in flat_metrics:
                    forecast = await self.capacity_planner.generate_capacity_forecast(
                        resource_type, flat_metrics
                    )
                    self.capacity_forecasts[resource_type] = forecast
            
        except Exception as e:
            logger.error(f"Error generating capacity forecasts: {e}")
    
    def _flatten_metrics(self, metrics_summary: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Flatten metrics summary to simple key-value pairs."""
        flat_metrics = {}
        
        for metric_name, metric_data in metrics_summary.items():
            if isinstance(metric_data, dict) and 'latest' in metric_data:
                flat_metrics[metric_name] = metric_data['latest'] or 0.0
        
        return flat_metrics
    
    async def _log_insights(self):
        """Log intelligent operations insights."""
        try:
            # Count predictions by type
            prediction_count = len(self.predictions)
            
            # Count forecasts with warnings
            warning_forecasts = sum(1 for f in self.capacity_forecasts.values() 
                                  if f.time_to_exhaustion and f.time_to_exhaustion <= 24)
            
            # Count high-priority recommendations
            high_priority_recs = sum(1 for r in self.recommendations 
                                   if r.priority in ['high', 'critical'])
            
            logger.info(f"Intelligent Operations Insights: "
                       f"Predictions={prediction_count}, "
                       f"Capacity Warnings={warning_forecasts}, "
                       f"High Priority Recommendations={high_priority_recs}")
            
        except Exception as e:
            logger.error(f"Error logging insights: {e}")
    
    def get_system_insights(self) -> Dict[str, Any]:
        """Get comprehensive system insights."""
        try:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "predictions": {
                    metric: {
                        "predicted_value": pred.predicted_value,
                        "confidence": pred.confidence,
                        "model_accuracy": pred.model_accuracy
                    }
                    for metric, pred in self.predictions.items()
                },
                "capacity_forecasts": {
                    resource: {
                        "current_usage": forecast.current_usage,
                        "time_to_exhaustion": forecast.time_to_exhaustion,
                        "recommended_action": forecast.recommended_action,
                        "confidence": forecast.confidence
                    }
                    for resource, forecast in self.capacity_forecasts.items()
                },
                "recommendations": [
                    {
                        "id": rec.recommendation_id,
                        "type": rec.recommendation_type.value,
                        "title": rec.title,
                        "priority": rec.priority,
                        "timeline": rec.timeline,
                        "estimated_impact": rec.estimated_impact
                    }
                    for rec in self.recommendations[:5]  # Top 5 recommendations
                ],
                "model_status": {
                    metric: {
                        "trained": metric in self.ml_predictor.models,
                        "accuracy": self.ml_predictor.model_accuracy.get(metric, 0.0),
                        "last_training": self.ml_predictor.last_training.get(metric, datetime.min).isoformat()
                    }
                    for metric in self.prediction_metrics
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting system insights: {e}")
            return {"error": str(e)}


# Global instance
intelligent_operations = None

def get_intelligent_operations() -> IntelligentOperationsSystem:
    """Get the global intelligent operations instance."""
    global intelligent_operations
    if intelligent_operations is None:
        from src.system.monitoring import MetricsCollector
        from src.monitoring.advanced_anomaly_detection import advanced_anomaly_detector
        from src.system.fault_detection_system import FaultDetectionSystem
        
        metrics_collector = MetricsCollector()
        fault_detector = FaultDetectionSystem()
        
        intelligent_operations = IntelligentOperationsSystem(
            metrics_collector=metrics_collector,
            anomaly_detector=advanced_anomaly_detector,
            fault_detector=fault_detector
        )
    
    return intelligent_operations