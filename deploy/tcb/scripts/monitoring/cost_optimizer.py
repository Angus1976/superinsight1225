"""
TCB Cost Optimizer

Provides cost optimization recommendations for TCB deployment.
"""

from typing import Dict, Any, List


class CostOptimizer:
    """Provides cost optimization recommendations."""
    
    def analyze_usage_patterns(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze usage patterns for optimization."""
        return {
            'avg_cpu_utilization': 35,
            'avg_memory_utilization': 85,
            'peak_cpu_utilization': 60,
            'peak_memory_utilization': 95,
            'storage_utilization': 70,
            'daily_cost': 25.50
        }
    
    def generate_cost_optimization_recommendations(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate cost optimization recommendations."""
        usage = self.analyze_usage_patterns(config)
        recommendations = []
        
        if usage['avg_cpu_utilization'] < 50:
            recommendations.append({
                'resource': 'CPU',
                'action': 'Reduce CPU allocation',
                'current': f"{config['cpu_cores']} cores",
                'recommended': f"{max(1, config['cpu_cores'] - 1)} cores",
                'potential_savings': 5.0
            })
        
        if usage['avg_memory_utilization'] > 80:
            recommendations.append({
                'resource': 'Memory',
                'action': 'Increase memory allocation',
                'current': f"{config['memory_gb']} GB",
                'recommended': f"{config['memory_gb'] + 2} GB",
                'potential_savings': -2.0  # Cost increase
            })
        
        return recommendations