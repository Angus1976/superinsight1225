"""
Deployment configuration for high availability setup.

This module provides deployment configurations for:
- Docker Compose multi-node setup
- Kubernetes cluster deployment
- Load balancer configuration
- Service mesh integration
"""

import yaml
from typing import Dict, List, Any
from pathlib import Path


class DeploymentConfigGenerator:
    """Generator for deployment configurations."""
    
    def __init__(self, cluster_name: str = "superinsight-sync"):
        self.cluster_name = cluster_name
    
    def generate_docker_compose(self, replicas: Dict[str, int] = None) -> str:
        """
        Generate Docker Compose configuration for multi-node deployment.
        
        Args:
            replicas: Number of replicas per service
            
        Returns:
            Docker Compose YAML configuration
        """
        if replicas is None:
            replicas = {
                'sync-gateway': 3,
                'pull-service': 2,
                'push-receiver': 2,
                'data-transformer': 2,
                'conflict-resolver': 1
            }
        
        config = {
            'version': '3.8',
            'services': {},
            'networks': {
                'sync-network': {
                    'driver': 'overlay',
                    'attachable': True
                }
            },
            'volumes': {
                'postgres-data': {},
                'redis-data': {}
            }
        }
        
        # Add infrastructure services
        config['services'].update({
            'postgres': {
                'image': 'postgres:15',
                'environment': {
                    'POSTGRES_DB': 'superinsight',
                    'POSTGRES_USER': 'postgres',
                    'POSTGRES_PASSWORD': 'password'
                },
                'volumes': ['postgres-data:/var/lib/postgresql/data'],
                'networks': ['sync-network'],
                'deploy': {
                    'replicas': 1,
                    'placement': {
                        'constraints': ['node.role == manager']
                    }
                }
            },
            'redis': {
                'image': 'redis:7-alpine',
                'volumes': ['redis-data:/data'],
                'networks': ['sync-network'],
                'deploy': {
                    'replicas': 1,
                    'placement': {
                        'constraints': ['node.role == manager']
                    }
                }
            },
            'nginx-lb': {
                'image': 'nginx:alpine',
                'ports': ['80:80', '443:443'],
                'volumes': ['./nginx.conf:/etc/nginx/nginx.conf:ro'],
                'networks': ['sync-network'],
                'depends_on': ['sync-gateway'],
                'deploy': {
                    'replicas': 2,
                    'update_config': {
                        'parallelism': 1,
                        'delay': '10s'
                    }
                }
            }
        })
        
        # Add application services
        for service_name, replica_count in replicas.items():
            config['services'][service_name] = {
                'image': f'superinsight/{service_name}:latest',
                'environment': {
                    'REDIS_URL': 'redis://redis:6379',
                    'POSTGRES_URL': 'postgresql://postgres:password@postgres:5432/superinsight',
                    'SERVICE_NAME': service_name,
                    'CLUSTER_NAME': self.cluster_name
                },
                'networks': ['sync-network'],
                'depends_on': ['postgres', 'redis'],
                'deploy': {
                    'replicas': replica_count,
                    'update_config': {
                        'parallelism': 1,
                        'delay': '10s',
                        'failure_action': 'rollback'
                    },
                    'restart_policy': {
                        'condition': 'on-failure',
                        'delay': '5s',
                        'max_attempts': 3
                    },
                    'resources': {
                        'limits': {
                            'cpus': '0.5',
                            'memory': '512M'
                        },
                        'reservations': {
                            'cpus': '0.25',
                            'memory': '256M'
                        }
                    }
                },
                'healthcheck': {
                    'test': ['CMD', 'curl', '-f', 'http://localhost:8080/health'],
                    'interval': '30s',
                    'timeout': '10s',
                    'retries': 3,
                    'start_period': '40s'
                }
            }
        
        return yaml.dump(config, default_flow_style=False)
    
    def generate_kubernetes_manifests(self, namespace: str = "superinsight") -> Dict[str, str]:
        """
        Generate Kubernetes manifests for cluster deployment.
        
        Args:
            namespace: Kubernetes namespace
            
        Returns:
            Dictionary of manifest files
        """
        manifests = {}
        
        # Namespace
        manifests['namespace.yaml'] = yaml.dump({
            'apiVersion': 'v1',
            'kind': 'Namespace',
            'metadata': {
                'name': namespace
            }
        })
        
        # ConfigMap
        manifests['configmap.yaml'] = yaml.dump({
            'apiVersion': 'v1',
            'kind': 'ConfigMap',
            'metadata': {
                'name': 'sync-config',
                'namespace': namespace
            },
            'data': {
                'REDIS_URL': 'redis://redis-service:6379',
                'POSTGRES_URL': 'postgresql://postgres:password@postgres-service:5432/superinsight',
                'CLUSTER_NAME': self.cluster_name
            }
        })
        
        # PostgreSQL
        manifests['postgres.yaml'] = yaml.dump_all([
            {
                'apiVersion': 'apps/v1',
                'kind': 'StatefulSet',
                'metadata': {
                    'name': 'postgres',
                    'namespace': namespace
                },
                'spec': {
                    'serviceName': 'postgres-service',
                    'replicas': 1,
                    'selector': {
                        'matchLabels': {
                            'app': 'postgres'
                        }
                    },
                    'template': {
                        'metadata': {
                            'labels': {
                                'app': 'postgres'
                            }
                        },
                        'spec': {
                            'containers': [{
                                'name': 'postgres',
                                'image': 'postgres:15',
                                'env': [
                                    {'name': 'POSTGRES_DB', 'value': 'superinsight'},
                                    {'name': 'POSTGRES_USER', 'value': 'postgres'},
                                    {'name': 'POSTGRES_PASSWORD', 'value': 'password'}
                                ],
                                'ports': [{'containerPort': 5432}],
                                'volumeMounts': [{
                                    'name': 'postgres-storage',
                                    'mountPath': '/var/lib/postgresql/data'
                                }]
                            }]
                        }
                    },
                    'volumeClaimTemplates': [{
                        'metadata': {
                            'name': 'postgres-storage'
                        },
                        'spec': {
                            'accessModes': ['ReadWriteOnce'],
                            'resources': {
                                'requests': {
                                    'storage': '10Gi'
                                }
                            }
                        }
                    }]
                }
            },
            {
                'apiVersion': 'v1',
                'kind': 'Service',
                'metadata': {
                    'name': 'postgres-service',
                    'namespace': namespace
                },
                'spec': {
                    'selector': {
                        'app': 'postgres'
                    },
                    'ports': [{
                        'port': 5432,
                        'targetPort': 5432
                    }]
                }
            }
        ])
        
        # Redis
        manifests['redis.yaml'] = yaml.dump_all([
            {
                'apiVersion': 'apps/v1',
                'kind': 'Deployment',
                'metadata': {
                    'name': 'redis',
                    'namespace': namespace
                },
                'spec': {
                    'replicas': 1,
                    'selector': {
                        'matchLabels': {
                            'app': 'redis'
                        }
                    },
                    'template': {
                        'metadata': {
                            'labels': {
                                'app': 'redis'
                            }
                        },
                        'spec': {
                            'containers': [{
                                'name': 'redis',
                                'image': 'redis:7-alpine',
                                'ports': [{'containerPort': 6379}]
                            }]
                        }
                    }
                }
            },
            {
                'apiVersion': 'v1',
                'kind': 'Service',
                'metadata': {
                    'name': 'redis-service',
                    'namespace': namespace
                },
                'spec': {
                    'selector': {
                        'app': 'redis'
                    },
                    'ports': [{
                        'port': 6379,
                        'targetPort': 6379
                    }]
                }
            }
        ])
        
        # Application services
        services = {
            'sync-gateway': {'replicas': 3, 'port': 8080},
            'pull-service': {'replicas': 2, 'port': 8081},
            'push-receiver': {'replicas': 2, 'port': 8082},
            'data-transformer': {'replicas': 2, 'port': 8083},
            'conflict-resolver': {'replicas': 1, 'port': 8084}
        }
        
        for service_name, config in services.items():
            manifests[f'{service_name}.yaml'] = yaml.dump_all([
                {
                    'apiVersion': 'apps/v1',
                    'kind': 'Deployment',
                    'metadata': {
                        'name': service_name,
                        'namespace': namespace
                    },
                    'spec': {
                        'replicas': config['replicas'],
                        'selector': {
                            'matchLabels': {
                                'app': service_name
                            }
                        },
                        'template': {
                            'metadata': {
                                'labels': {
                                    'app': service_name
                                }
                            },
                            'spec': {
                                'containers': [{
                                    'name': service_name,
                                    'image': f'superinsight/{service_name}:latest',
                                    'ports': [{'containerPort': config['port']}],
                                    'envFrom': [{
                                        'configMapRef': {
                                            'name': 'sync-config'
                                        }
                                    }],
                                    'env': [{
                                        'name': 'SERVICE_NAME',
                                        'value': service_name
                                    }],
                                    'resources': {
                                        'requests': {
                                            'cpu': '250m',
                                            'memory': '256Mi'
                                        },
                                        'limits': {
                                            'cpu': '500m',
                                            'memory': '512Mi'
                                        }
                                    },
                                    'livenessProbe': {
                                        'httpGet': {
                                            'path': '/health',
                                            'port': config['port']
                                        },
                                        'initialDelaySeconds': 30,
                                        'periodSeconds': 10
                                    },
                                    'readinessProbe': {
                                        'httpGet': {
                                            'path': '/ready',
                                            'port': config['port']
                                        },
                                        'initialDelaySeconds': 5,
                                        'periodSeconds': 5
                                    }
                                }]
                            }
                        }
                    }
                },
                {
                    'apiVersion': 'v1',
                    'kind': 'Service',
                    'metadata': {
                        'name': f'{service_name}-service',
                        'namespace': namespace
                    },
                    'spec': {
                        'selector': {
                            'app': service_name
                        },
                        'ports': [{
                            'port': config['port'],
                            'targetPort': config['port']
                        }]
                    }
                }
            ])
        
        # Ingress for external access
        manifests['ingress.yaml'] = yaml.dump({
            'apiVersion': 'networking.k8s.io/v1',
            'kind': 'Ingress',
            'metadata': {
                'name': 'sync-ingress',
                'namespace': namespace,
                'annotations': {
                    'nginx.ingress.kubernetes.io/rewrite-target': '/',
                    'nginx.ingress.kubernetes.io/load-balance': 'round_robin'
                }
            },
            'spec': {
                'rules': [{
                    'host': f'{self.cluster_name}.local',
                    'http': {
                        'paths': [{
                            'path': '/',
                            'pathType': 'Prefix',
                            'backend': {
                                'service': {
                                    'name': 'sync-gateway-service',
                                    'port': {
                                        'number': 8080
                                    }
                                }
                            }
                        }]
                    }
                }]
            }
        })
        
        # HorizontalPodAutoscaler
        for service_name in ['sync-gateway', 'pull-service', 'push-receiver']:
            manifests[f'{service_name}-hpa.yaml'] = yaml.dump({
                'apiVersion': 'autoscaling/v2',
                'kind': 'HorizontalPodAutoscaler',
                'metadata': {
                    'name': f'{service_name}-hpa',
                    'namespace': namespace
                },
                'spec': {
                    'scaleTargetRef': {
                        'apiVersion': 'apps/v1',
                        'kind': 'Deployment',
                        'name': service_name
                    },
                    'minReplicas': 1,
                    'maxReplicas': 10,
                    'metrics': [
                        {
                            'type': 'Resource',
                            'resource': {
                                'name': 'cpu',
                                'target': {
                                    'type': 'Utilization',
                                    'averageUtilization': 70
                                }
                            }
                        },
                        {
                            'type': 'Resource',
                            'resource': {
                                'name': 'memory',
                                'target': {
                                    'type': 'Utilization',
                                    'averageUtilization': 80
                                }
                            }
                        }
                    ]
                }
            })
        
        return manifests
    
    def generate_nginx_config(self, services: List[str] = None) -> str:
        """
        Generate Nginx load balancer configuration.
        
        Args:
            services: List of service names to load balance
            
        Returns:
            Nginx configuration
        """
        if services is None:
            services = ['sync-gateway']
        
        config = """
events {
    worker_connections 1024;
}

http {
    upstream sync_backend {
        least_conn;
        server sync-gateway-1:8080 max_fails=3 fail_timeout=30s;
        server sync-gateway-2:8080 max_fails=3 fail_timeout=30s;
        server sync-gateway-3:8080 max_fails=3 fail_timeout=30s;
    }
    
    server {
        listen 80;
        server_name _;
        
        location /health {
            access_log off;
            return 200 "healthy\\n";
            add_header Content-Type text/plain;
        }
        
        location / {
            proxy_pass http://sync_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Health check
            proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
            proxy_connect_timeout 5s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
    }
}
"""
        return config
    
    def generate_prometheus_config(self) -> str:
        """Generate Prometheus monitoring configuration."""
        config = {
            'global': {
                'scrape_interval': '15s',
                'evaluation_interval': '15s'
            },
            'scrape_configs': [
                {
                    'job_name': 'sync-services',
                    'static_configs': [{
                        'targets': [
                            'sync-gateway:8080',
                            'pull-service:8081',
                            'push-receiver:8082',
                            'data-transformer:8083',
                            'conflict-resolver:8084'
                        ]
                    }],
                    'metrics_path': '/metrics',
                    'scrape_interval': '10s'
                },
                {
                    'job_name': 'infrastructure',
                    'static_configs': [{
                        'targets': [
                            'postgres:5432',
                            'redis:6379'
                        ]
                    }],
                    'scrape_interval': '30s'
                }
            ]
        }
        
        return yaml.dump(config, default_flow_style=False)
    
    def save_configurations(self, output_dir: str = "./deploy") -> None:
        """
        Save all deployment configurations to files.
        
        Args:
            output_dir: Output directory for configuration files
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Docker Compose
        docker_compose = self.generate_docker_compose()
        (output_path / "docker-compose.yml").write_text(docker_compose)
        
        # Kubernetes manifests
        k8s_dir = output_path / "kubernetes"
        k8s_dir.mkdir(exist_ok=True)
        
        manifests = self.generate_kubernetes_manifests()
        for filename, content in manifests.items():
            (k8s_dir / filename).write_text(content)
        
        # Nginx config
        nginx_config = self.generate_nginx_config()
        (output_path / "nginx.conf").write_text(nginx_config)
        
        # Prometheus config
        prometheus_config = self.generate_prometheus_config()
        (output_path / "prometheus.yml").write_text(prometheus_config)
        
        print(f"Deployment configurations saved to {output_dir}")


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate deployment configurations")
    parser.add_argument("--cluster-name", default="superinsight-sync", 
                       help="Cluster name")
    parser.add_argument("--output-dir", default="./deploy", 
                       help="Output directory")
    
    args = parser.parse_args()
    
    generator = DeploymentConfigGenerator(args.cluster_name)
    generator.save_configurations(args.output_dir)