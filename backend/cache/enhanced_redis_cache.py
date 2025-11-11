"""
향상된 Redis 연결 관리자

이 모듈은 Redis 연결 안정성 문제를 해결하기 위한 고급 연결 관리 기능을 제공합니다.
지수 백오프 재연결, 상태 관리, 헬스 체크 등의 기능을 포함합니다.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, Callable, List
from enum import Enum
from dataclasses import dataclass
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"

@dataclass
class ConnectionStats:
    total_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    reconnection_attempts: int = 0
    last_connection_time: Optional[float] = None
    last_error_time: Optional[float] = None
    consecutive_failures: int = 0

class EnhancedRedisManager:
    """향상된 Redis 연결 관리자"""
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 10,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True,
        health_check_interval: int = 30,
        max_reconnection_attempts: int = 10,
        initial_backoff: float = 1.0,
        max_backoff: float = 60.0,
        backoff_multiplier: float = 2.0
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        
        # 연결 관리 설정
        self.health_check_interval = health_check_interval
        self.max_reconnection_attempts = max_reconnection_attempts
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier
        
        # 상태 관리
        self.connection_state = ConnectionState.DISCONNECTED
        self.connection_stats = ConnectionStats()
        self.redis_client = None
        self.connection_pool = None
        self.health_check_task = None
        self.reconnection_task = None
        
        # 이벤트 콜백
        self.connection_callbacks: List[Callable] = []
        self.error_callbacks: List[Callable] = []
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Redis 관리자 초기화"""
        try:
            await self._create_connection_pool()
            await self.connect()
            await self._start_health_check()
            self.logger.info("Enhanced Redis Manager initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Enhanced Redis Manager: {str(e)}")
            raise
    
    async def _create_connection_pool(self):
        """연결 풀 생성"""
        self.connection_pool = redis.ConnectionPool(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            max_connections=self.max_connections,
            socket_timeout=self.socket_timeout,
            socket_connect_timeout=self.socket_connect_timeout,
            retry_on_timeout=self.retry_on_timeout,
            socket_keepalive=True,
            socket_keepalive_options={},
            health_check_interval=30,
            # 추가 연결 옵션
            retry_on_error=[redis.ConnectionError, redis.TimeoutError]
        )
    
    async def connect(self) -> bool:
        """Redis 연결"""
        if self.connection_state in [ConnectionState.CONNECTING, ConnectionState.CONNECTED]:
            return True
        
        self.connection_state = ConnectionState.CONNECTING
        self.connection_stats.total_connections += 1
        
        try:
            if not self.connection_pool:
                await self._create_connection_pool()
            
            self.redis_client = redis.Redis(connection_pool=self.connection_pool)
            
            # 연결 테스트
            await self.redis_client.ping()
            
            self.connection_state = ConnectionState.CONNECTED
            self.connection_stats.successful_connections += 1
            self.connection_stats.last_connection_time = time.time()
            self.connection_stats.consecutive_failures = 0
            
            # 연결 성공 콜백 호출
            await self._trigger_connection_callbacks(True)
            
            self.logger.info(f"Connected to Redis at {self.host}:{self.port}")
            return True
            
        except Exception as e:
            self.connection_state = ConnectionState.FAILED
            self.connection_stats.failed_connections += 1
            self.connection_stats.last_error_time = time.time()
            self.connection_stats.consecutive_failures += 1
            
            # 연결 실패 콜백 호출
            await self._trigger_connection_callbacks(False, str(e))
            
            self.logger.error(f"Failed to connect to Redis: {str(e)}")
            
            # 자동 재연결 시도
            if self.connection_stats.consecutive_failures <= self.max_reconnection_attempts:
                asyncio.create_task(self._schedule_reconnection())
            
            return False
    
    async def disconnect(self):
        """Redis 연결 해제"""
        try:
            if self.health_check_task:
                self.health_check_task.cancel()
                self.health_check_task = None
            
            if self.reconnection_task:
                self.reconnection_task.cancel()
                self.reconnection_task = None
            
            if self.redis_client:
                await self.redis_client.close()
                self.redis_client = None
            
            if self.connection_pool:
                await self.connection_pool.disconnect()
                self.connection_pool = None
            
            self.connection_state = ConnectionState.DISCONNECTED
            self.logger.info("Disconnected from Redis")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from Redis: {str(e)}")
    
    async def _start_health_check(self):
        """상태 확인 시작"""
        if self.health_check_task:
            self.health_check_task.cancel()
        
        self.health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def _health_check_loop(self):
        """상태 확인 루프"""
        while self.connection_state == ConnectionState.CONNECTED:
            try:
                await asyncio.sleep(self.health_check_interval)
                
                if self.redis_client:
                    await self.redis_client.ping()
                    self.logger.debug("Redis health check passed")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.warning(f"Redis health check failed: {str(e)}")
                
                # 연결 상태 확인 및 재연결
                if self.connection_state == ConnectionState.CONNECTED:
                    await self._handle_connection_failure(str(e))
    
    async def _handle_connection_failure(self, error_message: str):
        """연결 실패 처리"""
        self.connection_state = ConnectionState.FAILED
        self.connection_stats.last_error_time = time.time()
        self.connection_stats.consecutive_failures += 1
        
        # 에러 콜백 호출
        await self._trigger_error_callbacks(error_message)
        
        # 재연결 시도
        if self.connection_stats.consecutive_failures <= self.max_reconnection_attempts:
            asyncio.create_task(self._schedule_reconnection())
        else:
            self.logger.error("Max reconnection attempts reached, giving up")
            self.connection_state = ConnectionState.FAILED
    
    async def _schedule_reconnection(self):
        """재연결 스케줄링"""
        if self.reconnection_task:
            self.reconnection_task.cancel()
        
        # 지수 백오프 계산
        backoff_time = min(
            self.initial_backoff * (self.backoff_multiplier ** (self.connection_stats.consecutive_failures - 1)),
            self.max_backoff
        )
        
        self.logger.info(f"Scheduling reconnection in {backoff_time:.2f} seconds")
        await asyncio.sleep(backoff_time)
        
        self.connection_state = ConnectionState.RECONNECTING
        self.connection_stats.reconnection_attempts += 1
        
        success = await self.connect()
        if not success:
            self.logger.warning(f"Reconnection attempt {self.connection_stats.reconnection_attempts} failed")
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """연결 통계 조회"""
        return {
            "state": self.connection_state.value,
            "stats": {
                "total_connections": self.connection_stats.total_connections,
                "successful_connections": self.connection_stats.successful_connections,
                "failed_connections": self.connection_stats.failed_connections,
                "reconnection_attempts": self.connection_stats.reconnection_attempts,
                "last_connection_time": self.connection_stats.last_connection_time,
                "last_error_time": self.connection_stats.last_error_time,
                "consecutive_failures": self.connection_stats.consecutive_failures
            },
            "success_rate": (
                self.connection_stats.successful_connections / max(self.connection_stats.total_connections, 1) * 100
            )
        }
    
    def add_connection_callback(self, callback: Callable):
        """연결 상태 콜백 추가"""
        self.connection_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable):
        """에러 콜백 추가"""
        self.error_callbacks.append(callback)
    
    async def _trigger_connection_callbacks(self, success: bool, error_message: str = None):
        """연결 상태 콜백 트리거"""
        for callback in self.connection_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(success, error_message)
                else:
                    callback(success, error_message)
            except Exception as e:
                self.logger.error(f"Error in connection callback: {str(e)}")
    
    async def _trigger_error_callbacks(self, error_message: str):
        """에러 콜백 트리거"""
        for callback in self.error_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(error_message)
                else:
                    callback(error_message)
            except Exception as e:
                self.logger.error(f"Error in error callback: {str(e)}")
    
    async def execute_with_fallback(self, operation, fallback_operation=None):
        """폴백 기능이 있는 작업 실행"""
        try:
            if self.connection_state != ConnectionState.CONNECTED:
                if not await self.connect():
                    raise ConnectionError("Redis is not connected")
            
            return await operation(self.redis_client)
            
        except Exception as e:
            self.logger.error(f"Redis operation failed: {str(e)}")
            
            if fallback_operation:
                self.logger.info("Executing fallback operation")
                return await fallback_operation()
            else:
                raise

# 전역 인스턴스
enhanced_redis_manager = EnhancedRedisManager()

# Alias for backward compatibility with tests
EnhancedRedisCacheManager = EnhancedRedisManager