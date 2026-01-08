"""
TCB Auto Scaler

Handles automatic scaling during service failures.
"""

from typing import Dict, Any


class AutoScaler:
    """Handles automatic scaling for TCB deployment."""
    
    def get_deployment_state(self) -> Dict[str, Any]:
        """Get current deployment state."""
        return {
            'current_replicas': 3,
            'healthy_replicas': 3,
            'target_replicas': 3,
            'max_replicas': 10,
            'min_replicas': 1
        }
    
    def handle_replica_failure(self, deployment_state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle replica failure by scaling up."""
        if deployment_state['healthy_replicas'] < deployment_state['min_replicas']:
            target_replicas = min(
                deployment_state['current_replicas'] + 2,
                deployment_state['max_replicas']
            )
            
            return {
                'should_scale': True,
                'target_replicas': target_replicas,
                'reason': 'replica_failure_compensation'
            }
        
        return {
            'should_scale': False,
            'reason': 'sufficient_healthy_replicas'
        }