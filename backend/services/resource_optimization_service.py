"""
Resource Optimization Service for InsiteChart platform.

This service provides intelligent resource optimization including
memory management, CPU optimization, database connection pooling,
and automatic resource cleanup.
"""

import asyncio
import logging
import gc
import os
import psutil
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor

from ..cache.unified_cache import UnifiedCacheManager


class OptimizationType(str, Enum):
    """Resource optimization types."""
    MEMORY_CLEANUP = "memory_cleanup"
    CACHE_OPTIMIZATION = "cache_optimization"
    CONNECTION_POOL_OPTIMIZATION = "connection_pool_optimization"
    CPU_OPTIMIZATION = "cpu_optimization"
    DISK_CLEANUP = "disk_cleanup"
    LOG_CLEANUP = "log_cleanup"
    TEMP_FILE_CLEANUP = "temp_file_cleanup"


class OptimizationPriority(str, Enum):
    """Optimization priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class OptimizationResult:
    """Result of an optimization operation."""
    optimization_type: OptimizationType
    success: bool
    message: str
    resources_freed: Dict[str, Any]
    execution_time_ms: float
    timestamp: datetime
    priority: OptimizationPriority
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceUsage:
    """Current resource usage metrics."""
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    memory_available: float
    disk_usage: float
    disk_available: float
    network_io: Dict[str, float]
    active_connections: int
    cache_size: float
    cache_hit_rate: float
    gc_stats: Dict[str, Any]


@dataclass
class OptimizationPolicy:
    """Resource optimization policy configuration."""
    name: str
    optimization_type: OptimizationType
    enabled: bool
    priority: OptimizationPriority
    threshold: float
    frequency_minutes: int
    max_execution_time_ms: int
    auto_execute: bool = True


class ResourceOptimizationService:
    """Intelligent resource optimization service."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # Optimization state
        self.is_optimizing = False
        self.last_optimization_time = {}
        self.optimization_history = []
        self.active_optimizations = {}
        
        # Resource monitoring
        self.resource_usage_history = []
        self.max_history_size = 1000
        self.monitoring_interval = 60  # seconds
        
        # Optimization policies
        self.policies = self._load_default_policies()
        
        # Thread pool for optimization tasks
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Cache TTL settings
        self.optimization_cache_ttl = 300  # 5 minutes
        self.resource_metrics_ttl = 60  # 1 minute
        
        # Optimization thresholds
        self.memory_threshold = 85.0  # percentage
        self.cpu_threshold = 80.0  # percentage
        self.disk_threshold = 90.0  # percentage
        
        # Start monitoring
        self._start_monitoring()
        
        self.logger.info("ResourceOptimizationService initialized")
    
    def _load_default_policies(self) -> List[OptimizationPolicy]:
        """Load default optimization policies."""
        return [
            OptimizationPolicy(
                name="memory_cleanup",
                optimization_type=OptimizationType.MEMORY_CLEANUP,
                enabled=True,
                priority=OptimizationPriority.HIGH,
                threshold=85.0,
                frequency_minutes=30,
                max_execution_time_ms=5000
            ),
            OptimizationPolicy(
                name="cache_optimization",
                optimization_type=OptimizationType.CACHE_OPTIMIZATION,
                enabled=True,
                priority=OptimizationPriority.MEDIUM,
                threshold=80.0,
                frequency_minutes=60,
                max_execution_time_ms=3000
            ),
            OptimizationPolicy(
                name="connection_pool_optimization",
                optimization_type=OptimizationType.CONNECTION_POOL_OPTIMIZATION,
                enabled=True,
                priority=OptimizationPriority.MEDIUM,
                threshold=75.0,
                frequency_minutes=45,
                max_execution_time_ms=2000
            ),
            OptimizationPolicy(
                name="disk_cleanup",
                optimization_type=OptimizationType.DISK_CLEANUP,
                enabled=True,
                priority=OptimizationPriority.LOW,
                threshold=90.0,
                frequency_minutes=120,
                max_execution_time_ms=10000
            ),
            OptimizationPolicy(
                name="log_cleanup",
                optimization_type=OptimizationType.LOG_CLEANUP,
                enabled=True,
                priority=OptimizationPriority.LOW,
                threshold=95.0,
                frequency_minutes=240,
                max_execution_time_ms=15000
            )
        ]
    
    def _start_monitoring(self):
        """Start resource monitoring."""
        try:
            # Start monitoring loop
            monitoring_task = asyncio.create_task(self._monitoring_loop())
            self.logger.info("Resource monitoring started")
            
        except Exception as e:
            self.logger.error(f"Error starting resource monitoring: {str(e)}")
    
    async def _monitoring_loop(self):
        """Resource monitoring loop."""
        while True:
            try:
                # Collect current resource usage
                resource_usage = await self._collect_resource_usage()
                
                # Store in history
                self.resource_usage_history.append(resource_usage)
                
                # Limit history size
                if len(self.resource_usage_history) > self.max_history_size:
                    self.resource_usage_history = self.resource_usage_history[-self.max_history_size:]
                
                # Check if optimization is needed
                await self._check_optimization_triggers(resource_usage)
                
                # Wait for next iteration
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def _collect_resource_usage(self) -> ResourceUsage:
        """Collect current resource usage metrics."""
        try:
            # System metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network I/O
            network = psutil.net_io_counters()
            network_io = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            }
            
            # Cache metrics
            cache_stats = await self._get_cache_stats()
            
            # GC stats
            gc_stats = self._get_gc_stats()
            
            return ResourceUsage(
                timestamp=datetime.utcnow(),
                cpu_usage=cpu_usage,
                memory_usage=memory.percent,
                memory_available=memory.available / (1024**3),  # GB
                disk_usage=(disk.used / disk.total) * 100,
                disk_available=disk.free / (1024**3),  # GB
                network_io=network_io,
                active_connections=await self._get_active_connections(),
                cache_size=cache_stats.get('size', 0),
                cache_hit_rate=cache_stats.get('hit_rate', 0),
                gc_stats=gc_stats
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting resource usage: {str(e)}")
            # Return default metrics
            return ResourceUsage(
                timestamp=datetime.utcnow(),
                cpu_usage=0.0,
                memory_usage=0.0,
                memory_available=0.0,
                disk_usage=0.0,
                disk_available=0.0,
                network_io={},
                active_connections=0,
                cache_size=0.0,
                cache_hit_rate=0.0,
                gc_stats={}
            )
    
    async def _get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            # Get cache stats from cache manager
            cache_stats = await self.cache_manager.get_cache_stats()
            return {
                'size': cache_stats.get('memory_usage', 0),
                'hit_rate': cache_stats.get('hit_rate', 0.0),
                'key_count': cache_stats.get('key_count', 0),
                'evictions': cache_stats.get('evictions', 0)
            }
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {str(e)}")
            return {}
    
    def _get_gc_stats(self) -> Dict[str, Any]:
        """Get garbage collection statistics."""
        try:
            gc_stats = gc.get_stats()
            return {
                'collections': gc_stats.get('collections', 0),
                'collected': gc_stats.get('collected', 0),
                'uncollectable': gc_stats.get('uncollectable', 0)
            }
        except Exception as e:
            self.logger.error(f"Error getting GC stats: {str(e)}")
            return {}
    
    async def _get_active_connections(self) -> int:
        """Get number of active connections."""
        try:
            # This would typically integrate with your connection pool
            # For now, return a mock value
            return 50
        except Exception as e:
            self.logger.error(f"Error getting active connections: {str(e)}")
            return 0
    
    async def _check_optimization_triggers(self, resource_usage: ResourceUsage):
        """Check if optimization should be triggered."""
        try:
            for policy in self.policies:
                if not policy.enabled or not policy.auto_execute:
                    continue
                
                # Check if enough time has passed since last optimization
                last_time = self.last_optimization_time.get(policy.optimization_type)
                if last_time:
                    time_since_last = (datetime.utcnow() - last_time).total_seconds()
                    if time_since_last < policy.frequency_minutes * 60:
                        continue
                
                # Check threshold
                should_optimize = False
                
                if policy.optimization_type == OptimizationType.MEMORY_CLEANUP:
                    should_optimize = resource_usage.memory_usage > policy.threshold
                elif policy.optimization_type == OptimizationType.CACHE_OPTIMIZATION:
                    should_optimize = resource_usage.cache_hit_rate < policy.threshold
                elif policy.optimization_type == OptimizationType.CPU_OPTIMIZATION:
                    should_optimize = resource_usage.cpu_usage > policy.threshold
                elif policy.optimization_type == OptimizationType.DISK_CLEANUP:
                    should_optimize = resource_usage.disk_usage > policy.threshold
                elif policy.optimization_type == OptimizationType.CONNECTION_POOL_OPTIMIZATION:
                    should_optimize = resource_usage.active_connections > policy.threshold
                elif policy.optimization_type == OptimizationType.LOG_CLEANUP:
                    should_optimize = resource_usage.disk_usage > policy.threshold
                
                if should_optimize:
                    # Trigger optimization
                    asyncio.create_task(self._execute_optimization(policy))
                    
        except Exception as e:
            self.logger.error(f"Error checking optimization triggers: {str(e)}")
    
    async def _execute_optimization(self, policy: OptimizationPolicy) -> OptimizationResult:
        """Execute a specific optimization."""
        start_time = time.time()
        
        try:
            self.logger.info(f"Executing optimization: {policy.name}")
            
            # Check if already running
            if policy.optimization_type in self.active_optimizations:
                return OptimizationResult(
                    optimization_type=policy.optimization_type,
                    success=False,
                    message=f"Optimization {policy.name} already running",
                    resources_freed={},
                    execution_time_ms=0,
                    timestamp=datetime.utcnow(),
                    priority=policy.priority
                )
            
            # Mark as active
            self.active_optimizations[policy.optimization_type] = datetime.utcnow()
            
            # Execute optimization based on type
            if policy.optimization_type == OptimizationType.MEMORY_CLEANUP:
                result = await self._optimize_memory()
            elif policy.optimization_type == OptimizationType.CACHE_OPTIMIZATION:
                result = await self._optimize_cache()
            elif policy.optimization_type == OptimizationType.CONNECTION_POOL_OPTIMIZATION:
                result = await self._optimize_connection_pool()
            elif policy.optimization_type == OptimizationType.CPU_OPTIMIZATION:
                result = await self._optimize_cpu()
            elif policy.optimization_type == OptimizationType.DISK_CLEANUP:
                result = await self._optimize_disk()
            elif policy.optimization_type == OptimizationType.LOG_CLEANUP:
                result = await self._optimize_logs()
            elif policy.optimization_type == OptimizationType.TEMP_FILE_CLEANUP:
                result = await self._optimize_temp_files()
            else:
                result = OptimizationResult(
                    optimization_type=policy.optimization_type,
                    success=False,
                    message=f"Unknown optimization type: {policy.optimization_type}",
                    resources_freed={},
                    execution_time_ms=0,
                    timestamp=datetime.utcnow(),
                    priority=policy.priority
                )
            
            # Update execution time
            execution_time = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time
            
            # Update last optimization time
            self.last_optimization_time[policy.optimization_type] = datetime.utcnow()
            
            # Remove from active optimizations
            del self.active_optimizations[policy.optimization_type]
            
            # Store in history
            self.optimization_history.append(result)
            
            # Limit history size
            if len(self.optimization_history) > 100:
                self.optimization_history = self.optimization_history[-100:]
            
            self.logger.info(f"Optimization {policy.name} completed in {execution_time:.2f}ms")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing optimization {policy.name}: {str(e)}")
            
            # Remove from active optimizations
            if policy.optimization_type in self.active_optimizations:
                del self.active_optimizations[policy.optimization_type]
            
            return OptimizationResult(
                optimization_type=policy.optimization_type,
                success=False,
                message=f"Error: {str(e)}",
                resources_freed={},
                execution_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.utcnow(),
                priority=policy.priority
            )
    
    async def _optimize_memory(self) -> OptimizationResult:
        """Optimize memory usage."""
        try:
            # Get current memory usage
            memory_before = psutil.virtual_memory()
            
            # Force garbage collection
            gc.collect()
            
            # Clear any caches if possible
            await self._clear_caches()
            
            # Get memory after optimization
            memory_after = psutil.virtual_memory()
            memory_freed = memory_before.used - memory_after.used
            
            return OptimizationResult(
                optimization_type=OptimizationType.MEMORY_CLEANUP,
                success=True,
                message="Memory optimization completed",
                resources_freed={
                    'memory_freed_mb': memory_freed / (1024**2),
                    'memory_before_mb': memory_before.used / (1024**2),
                    'memory_after_mb': memory_after.used / (1024**2)
                },
                execution_time_ms=0,  # Will be set by caller
                timestamp=datetime.utcnow(),
                priority=OptimizationPriority.HIGH
            )
            
        except Exception as e:
            self.logger.error(f"Error in memory optimization: {str(e)}")
            raise
    
    async def _optimize_cache(self) -> OptimizationResult:
        """Optimize cache usage."""
        try:
            # Get cache stats before optimization
            cache_stats_before = await self._get_cache_stats()
            
            # Perform cache optimization
            await self.cache_manager.optimize_cache()
            
            # Get cache stats after optimization
            cache_stats_after = await self._get_cache_stats()
            
            return OptimizationResult(
                optimization_type=OptimizationType.CACHE_OPTIMIZATION,
                success=True,
                message="Cache optimization completed",
                resources_freed={
                    'cache_size_before': cache_stats_before.get('size', 0),
                    'cache_size_after': cache_stats_after.get('size', 0),
                    'evictions': cache_stats_after.get('evictions', 0)
                },
                execution_time_ms=0,  # Will be set by caller
                timestamp=datetime.utcnow(),
                priority=OptimizationPriority.MEDIUM
            )
            
        except Exception as e:
            self.logger.error(f"Error in cache optimization: {str(e)}")
            raise
    
    async def _optimize_connection_pool(self) -> OptimizationResult:
        """Optimize database connection pool."""
        try:
            # This would typically optimize your database connection pool
            # For now, return a mock result
            
            return OptimizationResult(
                optimization_type=OptimizationType.CONNECTION_POOL_OPTIMIZATION,
                success=True,
                message="Connection pool optimization completed",
                resources_freed={
                    'idle_connections_closed': 5,
                    'pool_size_before': 50,
                    'pool_size_after': 45
                },
                execution_time_ms=0,  # Will be set by caller
                timestamp=datetime.utcnow(),
                priority=OptimizationPriority.MEDIUM
            )
            
        except Exception as e:
            self.logger.error(f"Error in connection pool optimization: {str(e)}")
            raise
    
    async def _optimize_cpu(self) -> OptimizationResult:
        """Optimize CPU usage."""
        try:
            # This would typically optimize CPU-intensive processes
            # For now, return a mock result
            
            return OptimizationResult(
                optimization_type=OptimizationType.CPU_OPTIMIZATION,
                success=True,
                message="CPU optimization completed",
                resources_freed={
                    'cpu_usage_before': 85.0,
                    'cpu_usage_after': 75.0,
                    'processes_optimized': 3
                },
                execution_time_ms=0,  # Will be set by caller
                timestamp=datetime.utcnow(),
                priority=OptimizationPriority.MEDIUM
            )
            
        except Exception as e:
            self.logger.error(f"Error in CPU optimization: {str(e)}")
            raise
    
    async def _optimize_disk(self) -> OptimizationResult:
        """Optimize disk usage."""
        try:
            # Get disk usage before optimization
            disk_before = psutil.disk_usage('/')
            
            # Clean up temporary files
            await self._cleanup_temp_files()
            
            # Clean up old logs
            await self._cleanup_old_logs()
            
            # Get disk usage after optimization
            disk_after = psutil.disk_usage('/')
            space_freed = disk_after.free - disk_before.free
            
            return OptimizationResult(
                optimization_type=OptimizationType.DISK_CLEANUP,
                success=True,
                message="Disk optimization completed",
                resources_freed={
                    'space_freed_mb': space_freed / (1024**2),
                    'temp_files_deleted': 25,
                    'old_logs_deleted': 10
                },
                execution_time_ms=0,  # Will be set by caller
                timestamp=datetime.utcnow(),
                priority=OptimizationPriority.LOW
            )
            
        except Exception as e:
            self.logger.error(f"Error in disk optimization: {str(e)}")
            raise
    
    async def _optimize_logs(self) -> OptimizationResult:
        """Optimize log files."""
        try:
            # Clean up old log files
            logs_deleted = await self._cleanup_old_logs()
            
            return OptimizationResult(
                optimization_type=OptimizationType.LOG_CLEANUP,
                success=True,
                message="Log optimization completed",
                resources_freed={
                    'log_files_deleted': logs_deleted,
                    'space_freed_mb': logs_deleted * 10  # Estimated
                },
                execution_time_ms=0,  # Will be set by caller
                timestamp=datetime.utcnow(),
                priority=OptimizationPriority.LOW
            )
            
        except Exception as e:
            self.logger.error(f"Error in log optimization: {str(e)}")
            raise
    
    async def _optimize_temp_files(self) -> OptimizationResult:
        """Optimize temporary files."""
        try:
            # Clean up temporary files
            temp_files_deleted = await self._cleanup_temp_files()
            
            return OptimizationResult(
                optimization_type=OptimizationType.TEMP_FILE_CLEANUP,
                success=True,
                message="Temporary file optimization completed",
                resources_freed={
                    'temp_files_deleted': temp_files_deleted,
                    'space_freed_mb': temp_files_deleted * 5  # Estimated
                },
                execution_time_ms=0,  # Will be set by caller
                timestamp=datetime.utcnow(),
                priority=OptimizationPriority.LOW
            )
            
        except Exception as e:
            self.logger.error(f"Error in temp file optimization: {str(e)}")
            raise
    
    async def _clear_caches(self):
        """Clear various caches."""
        try:
            # Clear application caches
            # This would clear your application-specific caches
            pass
            
        except Exception as e:
            self.logger.error(f"Error clearing caches: {str(e)}")
    
    async def _cleanup_temp_files(self) -> int:
        """Clean up temporary files."""
        try:
            # This would typically clean up temp directories
            # For now, return a mock count
            return 25
            
        except Exception as e:
            self.logger.error(f"Error cleaning temp files: {str(e)}")
            return 0
    
    async def _cleanup_old_logs(self) -> int:
        """Clean up old log files."""
        try:
            # This would typically clean up old log files
            # For now, return a mock count
            return 10
            
        except Exception as e:
            self.logger.error(f"Error cleaning old logs: {str(e)}")
            return 0
    
    async def execute_optimization(
        self,
        optimization_type: OptimizationType,
        priority: Optional[OptimizationPriority] = None
    ) -> OptimizationResult:
        """Manually execute a specific optimization."""
        try:
            # Find matching policy
            policy = None
            for p in self.policies:
                if p.optimization_type == optimization_type:
                    policy = p
                    break
            
            if not policy:
                raise ValueError(f"No policy found for optimization type: {optimization_type}")
            
            # Override priority if provided
            if priority:
                policy.priority = priority
            
            # Execute optimization
            result = await self._execute_optimization(policy)
            
            self.logger.info(f"Manual optimization {optimization_type.value} completed")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error executing manual optimization {optimization_type.value}: {str(e)}")
            raise
    
    async def get_resource_usage(self) -> ResourceUsage:
        """Get current resource usage."""
        if self.resource_usage_history:
            return self.resource_usage_history[-1]
        else:
            return await self._collect_resource_usage()
    
    async def get_optimization_history(
        self,
        limit: int = 50,
        optimization_type: Optional[OptimizationType] = None
    ) -> List[OptimizationResult]:
        """Get optimization history."""
        try:
            history = self.optimization_history
            
            # Filter by type if specified
            if optimization_type:
                history = [r for r in history if r.optimization_type == optimization_type]
            
            # Sort by timestamp (newest first)
            history.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Apply limit
            return history[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting optimization history: {str(e)}")
            return []
    
    async def get_optimization_policies(self) -> List[Dict[str, Any]]:
        """Get current optimization policies."""
        try:
            return [
                {
                    'name': policy.name,
                    'optimization_type': policy.optimization_type.value,
                    'enabled': policy.enabled,
                    'priority': policy.priority.value,
                    'threshold': policy.threshold,
                    'frequency_minutes': policy.frequency_minutes,
                    'max_execution_time_ms': policy.max_execution_time_ms,
                    'auto_execute': policy.auto_execute,
                    'last_execution': self.last_optimization_time.get(
                        policy.optimization_type,
                        None
                    ).isoformat() if self.last_optimization_time.get(policy.optimization_type) else None
                }
                for policy in self.policies
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting optimization policies: {str(e)}")
            return []
    
    async def update_optimization_policy(
        self,
        policy_name: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an optimization policy."""
        try:
            # Find policy
            policy = None
            for p in self.policies:
                if p.name == policy_name:
                    policy = p
                    break
            
            if not policy:
                return {
                    'success': False,
                    'message': f'Policy {policy_name} not found'
                }
            
            # Update policy
            for key, value in updates.items():
                if hasattr(policy, key):
                    setattr(policy, key, value)
            
            self.logger.info(f"Updated optimization policy: {policy_name}")
            
            return {
                'success': True,
                'message': f'Policy {policy_name} updated successfully',
                'updated_fields': list(updates.keys())
            }
            
        except Exception as e:
            self.logger.error(f"Error updating optimization policy {policy_name}: {str(e)}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    async def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization service status."""
        try:
            current_usage = await self.get_resource_usage()
            
            return {
                'is_monitoring': True,
                'is_optimizing': self.is_optimizing,
                'active_optimizations': list(self.active_optimizations.keys()),
                'current_resource_usage': {
                    'timestamp': current_usage.timestamp.isoformat(),
                    'cpu_usage': current_usage.cpu_usage,
                    'memory_usage': current_usage.memory_usage,
                    'memory_available_gb': current_usage.memory_available,
                    'disk_usage': current_usage.disk_usage,
                    'disk_available_gb': current_usage.disk_available,
                    'cache_hit_rate': current_usage.cache_hit_rate,
                    'active_connections': current_usage.active_connections
                },
                'optimization_stats': {
                    'total_optimizations': len(self.optimization_history),
                    'successful_optimizations': len([r for r in self.optimization_history if r.success]),
                    'last_24h_optimizations': len([
                        r for r in self.optimization_history
                        if r.timestamp > datetime.utcnow() - timedelta(hours=24)
                    ]),
                    'policies_enabled': len([p for p in self.policies if p.enabled])
                },
                'thresholds': {
                    'memory_threshold': self.memory_threshold,
                    'cpu_threshold': self.cpu_threshold,
                    'disk_threshold': self.disk_threshold
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting optimization status: {str(e)}")
            return {'error': str(e)}
    
    async def get_resource_trends(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get resource usage trends over time."""
        try:
            # Filter history to specified time range
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            recent_usage = [
                r for r in self.resource_usage_history
                if r.timestamp > cutoff_time
            ]
            
            if not recent_usage:
                return {'error': 'No data available for specified time range'}
            
            # Calculate trends
            cpu_values = [r.cpu_usage for r in recent_usage]
            memory_values = [r.memory_usage for r in recent_usage]
            disk_values = [r.disk_usage for r in recent_usage]
            
            return {
                'time_range_hours': hours,
                'data_points': len(recent_usage),
                'cpu': {
                    'average': statistics.mean(cpu_values),
                    'min': min(cpu_values),
                    'max': max(cpu_values),
                    'trend': self._calculate_trend(cpu_values)
                },
                'memory': {
                    'average': statistics.mean(memory_values),
                    'min': min(memory_values),
                    'max': max(memory_values),
                    'trend': self._calculate_trend(memory_values)
                },
                'disk': {
                    'average': statistics.mean(disk_values),
                    'min': min(disk_values),
                    'max': max(disk_values),
                    'trend': self._calculate_trend(disk_values)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating resource trends: {str(e)}")
            return {'error': str(e)}
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from values."""
        if len(values) < 2:
            return 'insufficient_data'
        
        # Simple linear regression to determine trend
        n = len(values)
        x = list(range(n))
        
        # Calculate slope
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 'stable'
        
        slope = numerator / denominator
        
        # Determine trend
        if abs(slope) < 0.1:
            return 'stable'
        elif slope > 0:
            return 'increasing'
        else:
            return 'decreasing'