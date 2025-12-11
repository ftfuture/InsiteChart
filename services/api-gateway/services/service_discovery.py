"""Service discovery and health checking."""

import asyncio
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime
import httpx

from models.gateway_models import ServiceInfo, ServiceStatus

logger = logging.getLogger(__name__)


class ServiceRegistry:
    """Registry and health checker for microservices."""

    def __init__(self, check_interval: int = 30):
        """Initialize service registry.

        Args:
            check_interval: Health check interval in seconds
        """
        self.services: Dict[str, ServiceInfo] = {}
        self.check_interval = check_interval
        self.last_check_time: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    def register_service(
        self,
        name: str,
        url: str,
        health_endpoint: str = "/health"
    ):
        """Register a microservice.

        Args:
            name: Service name
            url: Service base URL
            health_endpoint: Health check endpoint path
        """
        service_url = url.rstrip("/")
        health_url = f"{service_url}{health_endpoint}"

        self.services[name] = ServiceInfo(
            name=name,
            url=service_url,
            status=ServiceStatus.UNKNOWN,
            last_check=None,
            response_time_ms=None
        )

        # Store health endpoint for checks
        if not hasattr(self, "_health_endpoints"):
            self._health_endpoints = {}
        self._health_endpoints[name] = health_url

        logger.info(f"Registered service: {name} -> {service_url}")

    async def check_service_health(self, name: str) -> ServiceInfo:
        """Check health of a single service.

        Args:
            name: Service name

        Returns:
            Updated ServiceInfo with status

        Raises:
            ValueError: If service not registered
        """
        if name not in self.services:
            raise ValueError(f"Service not registered: {name}")

        service = self.services[name]
        health_url = self._health_endpoints.get(name)

        if not health_url:
            logger.warning(f"No health endpoint for service: {name}")
            return service

        try:
            start_time = time.time()

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)

            response_time = (time.time() - start_time) * 1000  # Convert to ms

            if response.status_code == 200:
                service.status = ServiceStatus.HEALTHY
                service.response_time_ms = response_time
                service.last_check = datetime.utcnow()
                logger.debug(f"Health check passed for {name}: {response_time:.2f}ms")
            elif response.status_code < 500:
                service.status = ServiceStatus.DEGRADED
                service.response_time_ms = response_time
                service.last_check = datetime.utcnow()
                logger.warning(f"Service degraded: {name} returned {response.status_code}")
            else:
                service.status = ServiceStatus.UNHEALTHY
                service.last_check = datetime.utcnow()
                logger.error(f"Service unhealthy: {name} returned {response.status_code}")

        except asyncio.TimeoutError:
            service.status = ServiceStatus.UNHEALTHY
            service.last_check = datetime.utcnow()
            logger.error(f"Health check timeout for service: {name}")
        except Exception as e:
            service.status = ServiceStatus.UNHEALTHY
            service.last_check = datetime.utcnow()
            logger.error(f"Health check failed for service {name}: {e}")

        self.last_check_time[name] = time.time()
        return service

    async def check_all_services(self):
        """Check health of all registered services."""
        async with self._lock:
            tasks = [
                self.check_service_health(name)
                for name in self.services.keys()
            ]

            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    def get_service(self, name: str) -> Optional[ServiceInfo]:
        """Get service info.

        Args:
            name: Service name

        Returns:
            ServiceInfo or None if not found
        """
        return self.services.get(name)

    def get_service_url(self, name: str) -> Optional[str]:
        """Get service URL.

        Args:
            name: Service name

        Returns:
            Service URL or None if not found
        """
        service = self.get_service(name)
        return service.url if service else None

    def get_all_services(self) -> List[ServiceInfo]:
        """Get all registered services.

        Returns:
            List of ServiceInfo
        """
        return list(self.services.values())

    def get_healthy_services(self) -> List[ServiceInfo]:
        """Get all healthy services.

        Returns:
            List of healthy ServiceInfo
        """
        return [
            s for s in self.services.values()
            if s.status == ServiceStatus.HEALTHY
        ]

    def is_service_available(self, name: str) -> bool:
        """Check if service is available.

        Args:
            name: Service name

        Returns:
            True if service is healthy or degraded, False otherwise
        """
        service = self.get_service(name)
        if not service:
            return False

        return service.status in [ServiceStatus.HEALTHY, ServiceStatus.DEGRADED]

    async def start_background_checks(self):
        """Start background health checks (runs continuously)."""
        logger.info("Starting background health checks...")

        while True:
            try:
                await self.check_all_services()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Background health check error: {e}")
                await asyncio.sleep(self.check_interval)


# Global service registry instance
_registry = None


def get_service_registry() -> ServiceRegistry:
    """Get global service registry instance.

    Returns:
        ServiceRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ServiceRegistry()
    return _registry


def create_service_registry(
    services_config: Dict[str, Dict[str, str]]
) -> ServiceRegistry:
    """Create and configure service registry.

    Args:
        services_config: Dictionary of service configurations
            Format: {
                "service_name": {
                    "url": "http://localhost:port",
                    "health_endpoint": "/health"  # optional
                }
            }

    Returns:
        Configured ServiceRegistry instance
    """
    registry = ServiceRegistry()

    for service_name, config in services_config.items():
        health_endpoint = config.get("health_endpoint", "/health")
        registry.register_service(
            name=service_name,
            url=config["url"],
            health_endpoint=health_endpoint
        )

    return registry
