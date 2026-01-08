"""
TCB Cost Calculator

Calculates TCB deployment costs based on resource usage.
"""

from typing import Dict, Any


class TCBCostCalculator:
    """Calculates TCB costs based on usage."""
    
    def get_pricing_config(self) -> Dict[str, float]:
        """Get TCB pricing configuration."""
        return {
            'cpu_core_hour': 0.05,
            'memory_gb_hour': 0.02,
            'storage_gb_month': 0.10,
            'network_gb': 0.08,
            'request_million': 0.20
        }
    
    def calculate_daily_cost(self, usage_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate daily cost based on usage."""
        pricing = self.get_pricing_config()
        
        cpu_cost = usage_data['cpu_core_hours'] * pricing['cpu_core_hour']
        memory_cost = usage_data['memory_gb_hours'] * pricing['memory_gb_hour']
        storage_cost = usage_data['storage_gb'] * pricing['storage_gb_month'] / 30
        network_cost = usage_data['network_gb'] * pricing['network_gb']
        request_cost = (usage_data['total_requests'] / 1000000) * pricing['request_million']
        
        return {
            'cpu_cost': cpu_cost,
            'memory_cost': memory_cost,
            'storage_cost': storage_cost,
            'network_cost': network_cost,
            'request_cost': request_cost,
            'total_cost': cpu_cost + memory_cost + storage_cost + network_cost + request_cost
        }