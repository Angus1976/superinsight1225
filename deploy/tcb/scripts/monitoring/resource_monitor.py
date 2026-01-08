"""
TCB Resource Monitor

Monitors system resource usage for TCB deployment.
"""

import psutil
from typing import Dict, Any


class ResourceMonitor:
    """Monitors system resource usage."""
    
    def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect comprehensive system metrics."""
        return {
            'cpu_usage': psutil.cpu_percent(interval=1),
            'memory_usage': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'network_io': {
                'bytes_sent': psutil.net_io_counters().bytes_sent,
                'bytes_recv': psutil.net_io_counters().bytes_recv
            },
            'disk_io': {
                'read_bytes': psutil.disk_io_counters().read_bytes,
                'write_bytes': psutil.disk_io_counters().write_bytes
            }
        }