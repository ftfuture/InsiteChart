"""
Auto Scaling Service for InsiteChart platform.

This service provides cloud-native auto-scaling capabilities including
horizontal scaling, vertical scaling, and performance-based resource management.
"""

import asyncio
import logging
import json
import os
import psutil
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics

from ..cache.unified_cache import UnifiedCacheManager


class ScalingDirection(str, Enum):
    """Scaling direction types."""
    SCALE_OUT = "scale_out"  # Add more instances
    SCALE_IN = "scale_in"    # Remove instances
    SCALE_UP = "scale_up"    # Increase resources
    SCALE_DOWN = "scale_down" # Decrease resources


class ScalingTrigger(str, Enum):
    """Auto-scaling trigger types."""
    CPU_THRESHOLD = "cpu_threshold"
    MEMORY_THRESHOLD = "memory_threshold"
    RESPONSE_TIME = "response_time"
    REQUEST_RATE = "request_rate"
    QUEUE_DEPTH = "queue_depth"
    CUSTOM_METRIC = "custom_metric"


class CloudProvider(str, Enum):
    """Supported cloud providers."""
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    KUBERNETES = "kubernetes"
    DOCKER = "docker"


@dataclass
class ScalingPolicy:
    """Auto-scaling policy configuration."""
    name: str
    trigger_type: ScalingTrigger
    threshold_min: float
    threshold_max: float
    scale_out_cooldown: int  # seconds
    scale_in_cooldown: int   # seconds
    min_instances: int
    max_instances: int
    scale_out_step: int
    scale_in_step: int
    enabled: bool = True


@dataclass
class ScalingEvent:
    """Auto-scaling event record."""
    timestamp: datetime
    direction: ScalingDirection
    trigger_type: ScalingTrigger
    trigger_value: float
    previous_instances: int
    new_instances: int
    reason: str
    metadata: Dict[str, Any]


@dataclass
class ResourceMetrics:
    """Current resource utilization metrics."""
    timestamp: datetime
    cpu_usage: float  # percentage
    memory_usage: float  # percentage
    disk_usage: float  # percentage
    network_io: Dict[str, float]  # bytes/s
    request_rate: float  # requests/second
    response_time: float  # milliseconds
    queue_depth: int
    active_connections: int
    custom_metrics: Dict[str, float]


@dataclass
class ScalingConfiguration:
    """Auto-scaling service configuration."""
    provider: CloudProvider
    service_name: str
    region: str
    current_instances: int
    target_cpu: float = 70.0
    target_memory: float = 80.0
    target_response_time: float = 500.0  # milliseconds
    scale_out_threshold: float = 80.0
    scale_in_threshold: float = 30.0
    cooldown_period: int = 300  # seconds
    min_instances: int = 1
    max_instances: int = 10
    policies: List[ScalingPolicy] = field(default_factory=list)


class AutoScalingService:
    """Cloud-native auto-scaling service."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = self._load_configuration()
        
        # State tracking
        self.current_instances = self.config.current_instances
        self.last_scale_time = {}
        self.scaling_history = []
        self.is_monitoring = False
        
        # Metrics collection
        self.metrics_buffer = []
        self.max_metrics_buffer = 1000
        
        # Cloud provider clients
        self.cloud_client = None
        self._initialize_cloud_client()
        
        # Cache TTL settings
        self.metrics_cache_ttl = 60  # 1 minute
        self.config_cache_ttl = 3600  # 1 hour
        
        self.logger.info("AutoScalingService initialized")
    
    def _load_configuration(self) -> ScalingConfiguration:
        """Load auto-scaling configuration from environment or defaults."""
        try:
            provider = CloudProvider(os.getenv('CLOUD_PROVIDER', 'kubernetes'))
            service_name = os.getenv('SERVICE_NAME', 'insitechart-api')
            region = os.getenv('CLOUD_REGION', 'us-west-2')
            current_instances = int(os.getenv('CURRENT_INSTANCES', '1'))
            
            config = ScalingConfiguration(
                provider=provider,
                service_name=service_name,
                region=region,
                current_instances=current_instances,
                target_cpu=float(os.getenv('TARGET_CPU', '70.0')),
                target_memory=float(os.getenv('TARGET_MEMORY', '80.0')),
                target_response_time=float(os.getenv('TARGET_RESPONSE_TIME', '500.0')),
                scale_out_threshold=float(os.getenv('SCALE_OUT_THRESHOLD', '80.0')),
                scale_in_threshold=float(os.getenv('SCALE_IN_THRESHOLD', '30.0')),
                cooldown_period=int(os.getenv('COOLDOWN_PERIOD', '300')),
                min_instances=int(os.getenv('MIN_INSTANCES', '1')),
                max_instances=int(os.getenv('MAX_INSTANCES', '10'))
            )
            
            # Add default policies
            config.policies = [
                ScalingPolicy(
                    name="cpu_based",
                    trigger_type=ScalingTrigger.CPU_THRESHOLD,
                    threshold_min=config.scale_in_threshold,
                    threshold_max=config.scale_out_threshold,
                    scale_out_cooldown=config.cooldown_period,
                    scale_in_cooldown=config.cooldown_period,
                    min_instances=config.min_instances,
                    max_instances=config.max_instances,
                    scale_out_step=1,
                    scale_in_step=1
                ),
                ScalingPolicy(
                    name="memory_based",
                    trigger_type=ScalingTrigger.MEMORY_THRESHOLD,
                    threshold_min=config.scale_in_threshold,
                    threshold_max=config.scale_out_threshold,
                    scale_out_cooldown=config.cooldown_period,
                    scale_in_cooldown=config.cooldown_period,
                    min_instances=config.min_instances,
                    max_instances=config.max_instances,
                    scale_out_step=1,
                    scale_in_step=1
                ),
                ScalingPolicy(
                    name="response_time_based",
                    trigger_type=ScalingTrigger.RESPONSE_TIME,
                    threshold_min=config.target_response_time * 0.5,
                    threshold_max=config.target_response_time * 2.0,
                    scale_out_cooldown=config.cooldown_period,
                    scale_in_cooldown=config.cooldown_period,
                    min_instances=config.min_instances,
                    max_instances=config.max_instances,
                    scale_out_step=2,
                    scale_in_step=1
                )
            ]
            
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            # Return default configuration
            return ScalingConfiguration(
                provider=CloudProvider.KUBERNETES,
                service_name="insitechart-api",
                region="us-west-2",
                current_instances=1
            )
    
    def _initialize_cloud_client(self):
        """Initialize cloud provider client."""
        try:
            if self.config.provider == CloudProvider.AWS:
                self._initialize_aws_client()
            elif self.config.provider == CloudProvider.GCP:
                self._initialize_gcp_client()
            elif self.config.provider == CloudProvider.AZURE:
                self._initialize_azure_client()
            elif self.config.provider == CloudProvider.KUBERNETES:
                self._initialize_kubernetes_client()
            elif self.config.provider == CloudProvider.DOCKER:
                self._initialize_docker_client()
            else:
                self.logger.warning(f"Unsupported cloud provider: {self.config.provider}")
                
        except Exception as e:
            self.logger.error(f"Error initializing cloud client: {str(e)}")
    
    def _initialize_aws_client(self):
        """Initialize AWS client."""
        try:
            import boto3
            self.cloud_client = {
                'autoscaling': boto3.client('autoscaling'),
                'cloudwatch': boto3.client('cloudwatch'),
                'ec2': boto3.client('ec2')
            }
            self.logger.info("AWS client initialized")
        except ImportError:
            self.logger.warning("boto3 not available, using mock AWS client")
            self.cloud_client = self._create_mock_aws_client()
    
    def _initialize_gcp_client(self):
        """Initialize GCP client."""
        try:
            from google.cloud import compute_v1
            from google.cloud import monitoring_v3
            self.cloud_client = {
                'compute': compute_v1.InstancesClient(),
                'monitoring': monitoring_v3.MetricServiceClient()
            }
            self.logger.info("GCP client initialized")
        except ImportError:
            self.logger.warning("google-cloud not available, using mock GCP client")
            self.cloud_client = self._create_mock_gcp_client()
    
    def _initialize_azure_client(self):
        """Initialize Azure client."""
        try:
            from azure.mgmt.compute import ComputeManagementClient
            from azure.mgmt.monitor import MonitorManagementClient
            from azure.identity import DefaultAzureCredential
            credential = DefaultAzureCredential()
            self.cloud_client = {
                'compute': ComputeManagementClient(credential),
                'monitor': MonitorManagementClient(credential)
            }
            self.logger.info("Azure client initialized")
        except ImportError:
            self.logger.warning("azure-mgmt not available, using mock Azure client")
            self.cloud_client = self._create_mock_azure_client()
    
    def _initialize_kubernetes_client(self):
        """Initialize Kubernetes client."""
        try:
            from kubernetes import client, config
            config.load_incluster_config() if os.getenv('KUBERNETES_SERVICE_HOST') else config.load_kube_config()
            self.cloud_client = {
                'apps_v1': client.AppsV1Api(),
                'autoscaling_v2': client.AutoscalingV2Api(),
                'core_v1': client.CoreV1Api()
            }
            self.logger.info("Kubernetes client initialized")
        except ImportError:
            self.logger.warning("kubernetes not available, using mock K8s client")
            self.cloud_client = self._create_mock_kubernetes_client()
    
    def _initialize_docker_client(self):
        """Initialize Docker client."""
        try:
            import docker
            self.cloud_client = docker.from_env()
            self.logger.info("Docker client initialized")
        except ImportError:
            self.logger.warning("docker not available, using mock Docker client")
            self.cloud_client = self._create_mock_docker_client()
    
    def _create_mock_aws_client(self) -> Dict[str, Any]:
        """Create mock AWS client for testing."""
        return {
            'type': 'mock_aws',
            'instances': self.current_instances,
            'scale_count': 0
        }
    
    def _create_mock_gcp_client(self) -> Dict[str, Any]:
        """Create mock GCP client for testing."""
        return {
            'type': 'mock_gcp',
            'instances': self.current_instances,
            'scale_count': 0
        }
    
    def _create_mock_azure_client(self) -> Dict[str, Any]:
        """Create mock Azure client for testing."""
        return {
            'type': 'mock_azure',
            'instances': self.current_instances,
            'scale_count': 0
        }
    
    def _create_mock_kubernetes_client(self) -> Dict[str, Any]:
        """Create mock Kubernetes client for testing."""
        return {
            'type': 'mock_kubernetes',
            'instances': self.current_instances,
            'scale_count': 0
        }
    
    def _create_mock_docker_client(self) -> Dict[str, Any]:
        """Create mock Docker client for testing."""
        return {
            'type': 'mock_docker',
            'instances': self.current_instances,
            'scale_count': 0
        }
    
    async def start_monitoring(self):
        """Start continuous monitoring and auto-scaling."""
        try:
            if self.is_monitoring:
                self.logger.warning("Auto-scaling monitoring already running")
                return
            
            self.is_monitoring = True
            self.logger.info("Starting auto-scaling monitoring")
            
            # Start monitoring loop
            asyncio.create_task(self._monitoring_loop())
            
        except Exception as e:
            self.logger.error(f"Error starting monitoring: {str(e)}")
            self.is_monitoring = False
            raise
    
    async def stop_monitoring(self):
        """Stop auto-scaling monitoring."""
        self.is_monitoring = False
        self.logger.info("Auto-scaling monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for auto-scaling decisions."""
        while self.is_monitoring:
            try:
                # Collect current metrics
                metrics = await self._collect_metrics()
                
                # Store metrics
                await self._store_metrics(metrics)
                
                # Evaluate scaling policies
                scaling_decisions = await self._evaluate_scaling_policies(metrics)
                
                # Execute scaling decisions
                for decision in scaling_decisions:
                    await self._execute_scaling_decision(decision)
                
                # Wait before next iteration
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _collect_metrics(self) -> ResourceMetrics:
        """Collect current resource metrics."""
        try:
            # System metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            # Network metrics
            network = psutil.net_io_counters()
            network_io = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'bytes_sent_per_sec': network.bytes_sent / (time.time() - psutil.boot_time()),
                'bytes_recv_per_sec': network.bytes_recv / (time.time() - psutil.boot_time())
            }
            
            # Application metrics (mock for now)
            request_rate = self._calculate_request_rate()
            response_time = self._calculate_response_time()
            queue_depth = self._calculate_queue_depth()
            active_connections = self._calculate_active_connections()
            
            # Custom metrics
            custom_metrics = await self._collect_custom_metrics()
            
            return ResourceMetrics(
                timestamp=datetime.utcnow(),
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                network_io=network_io,
                request_rate=request_rate,
                response_time=response_time,
                queue_depth=queue_depth,
                active_connections=active_connections,
                custom_metrics=custom_metrics
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {str(e)}")
            # Return default metrics
            return ResourceMetrics(
                timestamp=datetime.utcnow(),
                cpu_usage=0.0,
                memory_usage=0.0,
                disk_usage=0.0,
                network_io={},
                request_rate=0.0,
                response_time=0.0,
                queue_depth=0,
                active_connections=0,
                custom_metrics={}
            )
    
    def _calculate_request_rate(self) -> float:
        """Calculate current request rate."""
        # This would typically integrate with your application metrics
        # For now, return a mock value
        import random
        return random.uniform(10, 100)
    
    def _calculate_response_time(self) -> float:
        """Calculate current average response time."""
        # This would typically integrate with your application metrics
        # For now, return a mock value
        import random
        return random.uniform(100, 1000)
    
    def _calculate_queue_depth(self) -> int:
        """Calculate current queue depth."""
        # This would typically integrate with your application queue system
        # For now, return a mock value
        import random
        return int(random.uniform(0, 50))
    
    def _calculate_active_connections(self) -> int:
        """Calculate current active connections."""
        # This would typically integrate with your application connection pool
        # For now, return a mock value
        import random
        return int(random.uniform(10, 200))
    
    async def _collect_custom_metrics(self) -> Dict[str, float]:
        """Collect custom application metrics."""
        # This would integrate with your custom monitoring system
        return {
            'cache_hit_rate': 0.85,
            'error_rate': 0.02,
            'throughput': 1000.0
        }
    
    async def _store_metrics(self, metrics: ResourceMetrics):
        """Store metrics for analysis."""
        try:
            # Add to buffer
            self.metrics_buffer.append(metrics)
            
            # Limit buffer size
            if len(self.metrics_buffer) > self.max_metrics_buffer:
                self.metrics_buffer = self.metrics_buffer[-self.max_metrics_buffer:]
            
            # Cache latest metrics
            cache_key = "latest_metrics"
            metrics_dict = {
                'timestamp': metrics.timestamp.isoformat(),
                'cpu_usage': metrics.cpu_usage,
                'memory_usage': metrics.memory_usage,
                'disk_usage': metrics.disk_usage,
                'network_io': metrics.network_io,
                'request_rate': metrics.request_rate,
                'response_time': metrics.response_time,
                'queue_depth': metrics.queue_depth,
                'active_connections': metrics.active_connections,
                'custom_metrics': metrics.custom_metrics
            }
            
            await self.cache_manager.set(cache_key, metrics_dict, ttl=self.metrics_cache_ttl)
            
        except Exception as e:
            self.logger.error(f"Error storing metrics: {str(e)}")
    
    async def _evaluate_scaling_policies(self, metrics: ResourceMetrics) -> List[Dict[str, Any]]:
        """Evaluate all scaling policies against current metrics."""
        scaling_decisions = []
        
        for policy in self.config.policies:
            if not policy.enabled:
                continue
            
            try:
                decision = await self._evaluate_policy(policy, metrics)
                if decision:
                    scaling_decisions.append(decision)
                    
            except Exception as e:
                self.logger.error(f"Error evaluating policy {policy.name}: {str(e)}")
        
        return scaling_decisions
    
    async def _evaluate_policy(self, policy: ScalingPolicy, metrics: ResourceMetrics) -> Optional[Dict[str, Any]]:
        """Evaluate a single scaling policy."""
        try:
            # Get trigger value based on policy type
            trigger_value = self._get_trigger_value(policy.trigger_type, metrics)
            
            # Check cooldown period
            current_time = datetime.utcnow()
            last_scale_key = f"{policy.name}_{policy.trigger_type.value}"
            
            if last_scale_key in self.last_scale_time:
                time_since_last_scale = (current_time - self.last_scale_time[last_scale_key]).total_seconds()
                
                if trigger_value > policy.threshold_max:
                    if time_since_last_scale < policy.scale_out_cooldown:
                        return None  # Still in cooldown
                elif trigger_value < policy.threshold_min:
                    if time_since_last_scale < policy.scale_in_cooldown:
                        return None  # Still in cooldown
            
            # Determine scaling action
            if trigger_value > policy.threshold_max:
                # Scale out
                if self.current_instances < policy.max_instances:
                    new_instances = min(
                        self.current_instances + policy.scale_out_step,
                        policy.max_instances
                    )
                    
                    return {
                        'direction': ScalingDirection.SCALE_OUT,
                        'policy': policy,
                        'trigger_value': trigger_value,
                        'current_instances': self.current_instances,
                        'new_instances': new_instances,
                        'reason': f"{policy.trigger_type.value} ({trigger_value:.2f}) exceeds threshold ({policy.threshold_max})"
                    }
                    
            elif trigger_value < policy.threshold_min:
                # Scale in
                if self.current_instances > policy.min_instances:
                    new_instances = max(
                        self.current_instances - policy.scale_in_step,
                        policy.min_instances
                    )
                    
                    return {
                        'direction': ScalingDirection.SCALE_IN,
                        'policy': policy,
                        'trigger_value': trigger_value,
                        'current_instances': self.current_instances,
                        'new_instances': new_instances,
                        'reason': f"{policy.trigger_type.value} ({trigger_value:.2f}) below threshold ({policy.threshold_min})"
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error evaluating policy: {str(e)}")
            return None
    
    def _get_trigger_value(self, trigger_type: ScalingTrigger, metrics: ResourceMetrics) -> float:
        """Get trigger value for policy evaluation."""
        trigger_map = {
            ScalingTrigger.CPU_THRESHOLD: metrics.cpu_usage,
            ScalingTrigger.MEMORY_THRESHOLD: metrics.memory_usage,
            ScalingTrigger.RESPONSE_TIME: metrics.response_time,
            ScalingTrigger.REQUEST_RATE: metrics.request_rate,
            ScalingTrigger.QUEUE_DEPTH: float(metrics.queue_depth),
            ScalingTrigger.CUSTOM_METRIC: metrics.custom_metrics.get('custom_metric', 0.0)
        }
        
        return trigger_map.get(trigger_type, 0.0)
    
    async def _execute_scaling_decision(self, decision: Dict[str, Any]):
        """Execute a scaling decision."""
        try:
            direction = decision['direction']
            policy = decision['policy']
            new_instances = decision['new_instances']
            
            self.logger.info(f"Executing scaling decision: {direction.value} to {new_instances} instances")
            
            # Execute scaling based on cloud provider
            if self.config.provider == CloudProvider.AWS:
                await self._scale_aws(decision)
            elif self.config.provider == CloudProvider.GCP:
                await self._scale_gcp(decision)
            elif self.config.provider == CloudProvider.AZURE:
                await self._scale_azure(decision)
            elif self.config.provider == CloudProvider.KUBERNETES:
                await self._scale_kubernetes(decision)
            elif self.config.provider == CloudProvider.DOCKER:
                await self._scale_docker(decision)
            else:
                self.logger.warning(f"Unsupported provider for scaling: {self.config.provider}")
                return
            
            # Update state
            old_instances = self.current_instances
            self.current_instances = new_instances
            
            # Record scaling event
            scaling_event = ScalingEvent(
                timestamp=datetime.utcnow(),
                direction=direction,
                trigger_type=policy.trigger_type,
                trigger_value=decision['trigger_value'],
                previous_instances=old_instances,
                new_instances=new_instances,
                reason=decision['reason'],
                metadata={
                    'policy_name': policy.name,
                    'provider': self.config.provider.value
                }
            )
            
            self.scaling_history.append(scaling_event)
            
            # Update cooldown timer
            last_scale_key = f"{policy.name}_{policy.trigger_type.value}"
            self.last_scale_time[last_scale_key] = datetime.utcnow()
            
            # Cache scaling history
            await self._cache_scaling_history()
            
            self.logger.info(f"Scaling completed: {old_instances} -> {new_instances} instances")
            
        except Exception as e:
            self.logger.error(f"Error executing scaling decision: {str(e)}")
    
    async def _scale_aws(self, decision: Dict[str, Any]):
        """Execute scaling on AWS."""
        try:
            if self.cloud_client.get('type') == 'mock_aws':
                # Mock scaling
                self.cloud_client['instances'] = decision['new_instances']
                self.cloud_client['scale_count'] += 1
                self.logger.info(f"Mock AWS scaling to {decision['new_instances']} instances")
                return
            
            # Real AWS scaling would go here
            autoscaling_client = self.cloud_client['autoscaling']
            
            # This would use AWS Auto Scaling API
            # For example:
            # response = autoscaling_client.set_desired_capacity(
            #     AutoScalingGroupName=self.config.service_name,
            #     DesiredCapacity=decision['new_instances'],
            #     HonorCooldown=False
            # )
            
            self.logger.info(f"AWS scaling initiated to {decision['new_instances']} instances")
            
        except Exception as e:
            self.logger.error(f"Error in AWS scaling: {str(e)}")
            raise
    
    async def _scale_gcp(self, decision: Dict[str, Any]):
        """Execute scaling on GCP."""
        try:
            if self.cloud_client.get('type') == 'mock_gcp':
                # Mock scaling
                self.cloud_client['instances'] = decision['new_instances']
                self.cloud_client['scale_count'] += 1
                self.logger.info(f"Mock GCP scaling to {decision['new_instances']} instances")
                return
            
            # Real GCP scaling would go here
            compute_client = self.cloud_client['compute']
            
            # This would use GCP Compute Engine API
            self.logger.info(f"GCP scaling initiated to {decision['new_instances']} instances")
            
        except Exception as e:
            self.logger.error(f"Error in GCP scaling: {str(e)}")
            raise
    
    async def _scale_azure(self, decision: Dict[str, Any]):
        """Execute scaling on Azure."""
        try:
            if self.cloud_client.get('type') == 'mock_azure':
                # Mock scaling
                self.cloud_client['instances'] = decision['new_instances']
                self.cloud_client['scale_count'] += 1
                self.logger.info(f"Mock Azure scaling to {decision['new_instances']} instances")
                return
            
            # Real Azure scaling would go here
            compute_client = self.cloud_client['compute']
            
            # This would use Azure VM Scale Sets API
            self.logger.info(f"Azure scaling initiated to {decision['new_instances']} instances")
            
        except Exception as e:
            self.logger.error(f"Error in Azure scaling: {str(e)}")
            raise
    
    async def _scale_kubernetes(self, decision: Dict[str, Any]):
        """Execute scaling on Kubernetes."""
        try:
            if self.cloud_client.get('type') == 'mock_kubernetes':
                # Mock scaling
                self.cloud_client['instances'] = decision['new_instances']
                self.cloud_client['scale_count'] += 1
                self.logger.info(f"Mock Kubernetes scaling to {decision['new_instances']} instances")
                return
            
            # Real Kubernetes scaling would go here
            apps_v1 = self.cloud_client['apps_v1']
            
            # This would use Kubernetes API
            # For example:
            # from kubernetes.client import V1Scale
            # scale = apps_v1.read_namespaced_deployment_scale(
            #     name=self.config.service_name,
            #     namespace='default'
            # )
            # scale.spec.replicas = decision['new_instances']
            # apps_v1.patch_namespaced_deployment_scale(
            #     name=self.config.service_name,
            #     namespace='default',
            #     body=scale
            # )
            
            self.logger.info(f"Kubernetes scaling initiated to {decision['new_instances']} instances")
            
        except Exception as e:
            self.logger.error(f"Error in Kubernetes scaling: {str(e)}")
            raise
    
    async def _scale_docker(self, decision: Dict[str, Any]):
        """Execute scaling on Docker."""
        try:
            if self.cloud_client.get('type') == 'mock_docker':
                # Mock scaling
                self.cloud_client['instances'] = decision['new_instances']
                self.cloud_client['scale_count'] += 1
                self.logger.info(f"Mock Docker scaling to {decision['new_instances']} instances")
                return
            
            # Real Docker scaling would go here
            docker_client = self.cloud_client
            
            # This would use Docker API
            self.logger.info(f"Docker scaling initiated to {decision['new_instances']} instances")
            
        except Exception as e:
            self.logger.error(f"Error in Docker scaling: {str(e)}")
            raise
    
    async def _cache_scaling_history(self):
        """Cache scaling history."""
        try:
            cache_key = "scaling_history"
            history_data = [
                {
                    'timestamp': event.timestamp.isoformat(),
                    'direction': event.direction.value,
                    'trigger_type': event.trigger_type.value,
                    'trigger_value': event.trigger_value,
                    'previous_instances': event.previous_instances,
                    'new_instances': event.new_instances,
                    'reason': event.reason,
                    'metadata': event.metadata
                }
                for event in self.scaling_history[-100:]  # Last 100 events
            ]
            
            await self.cache_manager.set(cache_key, history_data, ttl=3600)
            
        except Exception as e:
            self.logger.error(f"Error caching scaling history: {str(e)}")
    
    async def get_current_metrics(self) -> Optional[ResourceMetrics]:
        """Get the most recent metrics."""
        try:
            cache_key = "latest_metrics"
            cached_metrics = await self.cache_manager.get(cache_key)
            
            if cached_metrics:
                return ResourceMetrics(
                    timestamp=datetime.fromisoformat(cached_metrics['timestamp']),
                    cpu_usage=cached_metrics['cpu_usage'],
                    memory_usage=cached_metrics['memory_usage'],
                    disk_usage=cached_metrics['disk_usage'],
                    network_io=cached_metrics['network_io'],
                    request_rate=cached_metrics['request_rate'],
                    response_time=cached_metrics['response_time'],
                    queue_depth=cached_metrics['queue_depth'],
                    active_connections=cached_metrics['active_connections'],
                    custom_metrics=cached_metrics['custom_metrics']
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting current metrics: {str(e)}")
            return None
    
    async def get_scaling_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get scaling history."""
        try:
            cache_key = "scaling_history"
            cached_history = await self.cache_manager.get(cache_key)
            
            if cached_history:
                return cached_history[-limit:]
            
            # Return from memory if cache miss
            return [
                {
                    'timestamp': event.timestamp.isoformat(),
                    'direction': event.direction.value,
                    'trigger_type': event.trigger_type.value,
                    'trigger_value': event.trigger_value,
                    'previous_instances': event.previous_instances,
                    'new_instances': event.new_instances,
                    'reason': event.reason,
                    'metadata': event.metadata
                }
                for event in self.scaling_history[-limit:]
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting scaling history: {str(e)}")
            return []
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get current auto-scaling service status."""
        try:
            current_metrics = await self.get_current_metrics()
            
            return {
                'configuration': {
                    'provider': self.config.provider.value,
                    'service_name': self.config.service_name,
                    'region': self.config.region,
                    'current_instances': self.current_instances,
                    'min_instances': self.config.min_instances,
                    'max_instances': self.config.max_instances,
                    'target_cpu': self.config.target_cpu,
                    'target_memory': self.config.target_memory,
                    'target_response_time': self.config.target_response_time
                },
                'status': {
                    'is_monitoring': self.is_monitoring,
                    'current_instances': self.current_instances,
                    'last_scale_time': self.last_scale_time,
                    'total_scaling_events': len(self.scaling_history),
                    'metrics_buffer_size': len(self.metrics_buffer)
                },
                'current_metrics': {
                    'timestamp': current_metrics.timestamp.isoformat() if current_metrics else None,
                    'cpu_usage': current_metrics.cpu_usage if current_metrics else None,
                    'memory_usage': current_metrics.memory_usage if current_metrics else None,
                    'request_rate': current_metrics.request_rate if current_metrics else None,
                    'response_time': current_metrics.response_time if current_metrics else None
                } if current_metrics else None,
                'policies': [
                    {
                        'name': policy.name,
                        'trigger_type': policy.trigger_type.value,
                        'threshold_min': policy.threshold_min,
                        'threshold_max': policy.threshold_max,
                        'enabled': policy.enabled
                    }
                    for policy in self.config.policies
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting service status: {str(e)}")
            return {'error': str(e)}
    
    async def update_configuration(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Update auto-scaling configuration."""
        try:
            # Update configuration
            for key, value in new_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            # Re-initialize cloud client if provider changed
            if 'provider' in new_config:
                self._initialize_cloud_client()
            
            self.logger.info(f"Configuration updated: {new_config}")
            
            return {
                'success': True,
                'message': 'Configuration updated successfully',
                'updated_fields': list(new_config.keys())
            }
            
        except Exception as e:
            self.logger.error(f"Error updating configuration: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def manual_scale(self, target_instances: int, reason: str = "Manual scaling") -> Dict[str, Any]:
        """Execute manual scaling."""
        try:
            if target_instances < self.config.min_instances or target_instances > self.config.max_instances:
                return {
                    'success': False,
                    'error': f'Target instances must be between {self.config.min_instances} and {self.config.max_instances}'
                }
            
            # Create manual scaling decision
            decision = {
                'direction': ScalingDirection.SCALE_OUT if target_instances > self.current_instances else ScalingDirection.SCALE_IN,
                'policy': None,
                'trigger_value': 0.0,
                'current_instances': self.current_instances,
                'new_instances': target_instances,
                'reason': reason
            }
            
            # Execute scaling
            await self._execute_scaling_decision(decision)
            
            return {
                'success': True,
                'message': f'Manual scaling completed: {self.current_instances} -> {target_instances} instances',
                'previous_instances': decision['current_instances'],
                'new_instances': target_instances
            }
            
        except Exception as e:
            self.logger.error(f"Error in manual scaling: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }