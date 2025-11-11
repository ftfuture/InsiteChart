"""
구조화된 로깅 시스템 모듈
JSON 형식의 구조화된 로그, 레벨별 필터링, 중앙 집중식 로그 수집 기능 제공
"""

import json
import logging
import traceback
import sys
from typing import Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path
import asyncio
import redis.asyncio as redis

logger = logging.getLogger(__name__)

@dataclass
class LogContext:
    """로그 컨텍스트 모델"""
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    service: Optional[str] = None
    module: Optional[str] = None
    function: Optional[str] = None
    line_number: Optional[int] = None
    additional_context: Optional[Dict[str, Any]] = None

@dataclass
class LogEntry:
    """로그 엔트리 모델"""
    timestamp: str
    level: str
    message: str
    service: str
    context: LogContext
    exception: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    tags: Optional[list] = None

class StructuredFormatter(logging.Formatter):
    """구조화된 로그 포매터 클래스"""
    
    def __init__(
        self,
        service_name: str = "insitechart",
        include_extra_fields: bool = True,
        max_exception_length: int = 1000
    ):
        super().__init__()
        self.service_name = service_name
        self.include_extra_fields = include_extra_fields
        self.max_exception_length = max_exception_length
    
    def format(self, record: logging.LogRecord) -> str:
        """로그 레코드 포맷"""
        try:
            # 기본 로그 데이터
            log_data = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "message": record.getMessage(),
                "service": self.service_name,
                "module": record.module,
                "function": record.funcName,
                "line_number": record.lineno
            }
            
            # 컨텍스트 정보 추가
            context = LogContext()
            
            # request_id, user_id 등 추가 필드 확인
            if hasattr(record, 'request_id'):
                context.request_id = record.request_id
            if hasattr(record, 'user_id'):
                context.user_id = record.user_id
            if hasattr(record, 'session_id'):
                context.session_id = record.session_id
            if hasattr(record, 'correlation_id'):
                context.correlation_id = record.correlation_id
            
            # 추가 컨텍스트
            if hasattr(record, 'context'):
                context.additional_context = record.context
            
            log_data["context"] = asdict(context)
            
            # 예외 정보 처리
            if record.exc_info:
                exc_type, exc_value, exc_traceback = record.exc_info
                exception_data = {
                    "type": exc_type.__name__ if exc_type else None,
                    "message": str(exc_value) if exc_value else None,
                    "traceback": self._format_traceback(exc_traceback)
                }
                log_data["exception"] = exception_data
            
            # 메트릭 정보 추가
            if hasattr(record, 'metrics'):
                log_data["metrics"] = record.metrics
            
            # 태그 정보 추가
            if hasattr(record, 'tags'):
                log_data["tags"] = record.tags
            
            # 추가 필드 포함
            if self.include_extra_fields:
                extra_fields = {}
                for key, value in record.__dict__.items():
                    if key not in {
                        'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                        'filename', 'module', 'lineno', 'funcName', 'created',
                        'msecs', 'relativeCreated', 'thread', 'threadName',
                        'processName', 'process', 'getMessage', 'exc_info',
                        'exc_text', 'stack_info'
                    } and not key.startswith('_'):
                        extra_fields[key] = value
                
                if extra_fields:
                    log_data["extra"] = extra_fields
            
            return json.dumps(log_data, ensure_ascii=False, default=str)
            
        except Exception as e:
            # 포맷 오류 시 기본 포맷 사용
            return json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "level": "ERROR",
                "message": f"Log formatting error: {str(e)}",
                "service": self.service_name,
                "original_message": record.getMessage(),
                "exception": {
                    "type": type(e).__name__,
                    "message": str(e),
                    "traceback": traceback.format_exc()
                }
            }, ensure_ascii=False)
    
    def _format_traceback(self, tb) -> str:
        """예외 추적 포맷"""
        if not tb:
            return ""
        
        formatted_tb = traceback.format_tb(tb)
        tb_str = "".join(formatted_tb)
        
        # 최대 길이 제한
        if len(tb_str) > self.max_exception_length:
            tb_str = tb_str[:self.max_exception_length] + "... (truncated)"
        
        return tb_str

class StructuredLogger:
    """구조화된 로거 클래스"""
    
    def __init__(
        self,
        name: str,
        service_name: str = "insitechart",
        redis_url: Optional[str] = None,
        log_level: str = "INFO",
        enable_console: bool = True,
        enable_file: bool = True,
        log_file_path: Optional[str] = None,
        enable_remote: bool = False,
        remote_config: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.service_name = service_name
        self.redis_url = redis_url
        self.log_level = getattr(logging, log_level.upper())
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.enable_remote = enable_remote
        self.log_file_path = log_file_path
        self.remote_config = remote_config or {}
        
        # 로거 설정
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.log_level)
        
        # Redis 클라이언트 (원격 로깅용)
        self.redis_client = None
        
        # 포매터
        self.formatter = StructuredFormatter(service_name=service_name)
        
        # 핸들러 설정
        self._setup_handlers()
    
    async def initialize(self):
        """로거 초기화"""
        try:
            # Redis 클라이언트 초기화 (원격 로깅용)
            if self.enable_remote and self.redis_url:
                self.redis_client = redis.from_url(self.redis_url)
                await self.redis_client.ping()
            
            # 파일 핸들러 초기화
            if self.enable_file and self.log_file_path:
                await self._setup_file_handler()
            
            logger.info(f"Structured logger {self.name} initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize structured logger {self.name}: {str(e)}")
            raise
    
    def info(self, message: str, **kwargs):
        """정보 로그 기록"""
        self._log(logging.INFO, message, **kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """에러 로그 기록"""
        if error:
            kwargs['exc_info'] = (type(error), error, error.__traceback__)
        self._log(logging.ERROR, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """경고 로그 기록"""
        self._log(logging.WARNING, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """디버그 로그 기록"""
        self._log(logging.DEBUG, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """치명적 에러 로그 기록"""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def audit(self, event: str, user_id: Optional[str] = None, **kwargs):
        """감사 로그 기록"""
        audit_data = {
            "event": event,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        self._log(
            logging.INFO,
            f"Audit event: {event}",
            context=audit_data,
            tags=["audit"]
        )
    
    def performance(self, operation: str, duration: float, **kwargs):
        """성능 로그 기록"""
        metrics = {
            "operation": operation,
            "duration_ms": duration * 1000,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        self._log(
            logging.INFO,
            f"Performance: {operation} took {duration:.3f}s",
            metrics=metrics,
            tags=["performance"]
        )
    
    def security(self, event: str, severity: str = "info", **kwargs):
        """보안 로그 기록"""
        security_data = {
            "event": event,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        self._log(
            logging.INFO,
            f"Security event: {event}",
            context=security_data,
            tags=["security"]
        )
    
    def business(self, event: str, **kwargs):
        """비즈니스 로그 기록"""
        business_data = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        self._log(
            logging.INFO,
            f"Business event: {event}",
            context=business_data,
            tags=["business"]
        )
    
    def bind(self, **kwargs):
        """컨텍스트 바인딩"""
        # 바인딩된 컨텍스트를 가진 새 로거 인스턴스 반환
        bound_logger = StructuredLogger(
            name=self.name,
            service_name=self.service_name,
            redis_url=self.redis_url,
            log_level=logging.getLevelName(self.log_level),
            enable_console=self.enable_console,
            enable_file=self.enable_file,
            log_file_path=self.log_file_path,
            enable_remote=self.enable_remote,
            remote_config=self.remote_config
        )
        
        # 바인딩된 컨텍스트 저장
        bound_logger._bound_context = kwargs
        
        return bound_logger
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """컨텍스트와 함께 로깅"""
        # 바인딩된 컨텍스트가 있는 경우
        if hasattr(self, '_bound_context'):
            kwargs.update(self._bound_context)
        
        self._log(level, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """내부 로깅 메서드"""
        # 로그 레코드 생성
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=level,
            fn="",  # 자동으로 설정됨
            lno=0,  # 자동으로 설정됨
            msg=message,
            args=(),
            exc_info=kwargs.get('exc_info')
        )
        
        # 바인딩된 컨텍스트가 있는 경우 추가
        if hasattr(self, '_bound_context'):
            for key, value in self._bound_context.items():
                setattr(record, key, value)
        
        # 추가 속성 설정
        for key, value in kwargs.items():
            if key != 'exc_info':
                setattr(record, key, value)
        
        # 로그 처리
        self.logger.handle(record)
    
    def _setup_handlers(self):
        """로그 핸들러 설정"""
        # 기존 핸들러 제거
        self.logger.handlers.clear()
        
        # 콘솔 핸들러
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(self.formatter)
            console_handler.setLevel(self.log_level)
            self.logger.addHandler(console_handler)
        
        # 파일 핸들러 (비동기 설정)
        if self.enable_file and self.log_file_path:
            file_handler = logging.FileHandler(self.log_file_path)
            file_handler.setFormatter(self.formatter)
            file_handler.setLevel(self.log_level)
            self.logger.addHandler(file_handler)
    
    async def _setup_file_handler(self):
        """파일 핸들러 비동기 설정"""
        try:
            # 로그 디렉토리 생성
            log_path = Path(self.log_file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 로그 회전 설정 (선택적)
            # 실제 구현에서는 RotatingFileHandler 사용 가능
            
        except Exception as e:
            logger.error(f"Failed to setup file handler: {str(e)}")
    
    async def log_to_remote(self, log_entry: LogEntry):
        """원격 로그 저장"""
        try:
            if not self.redis_client:
                return
            
            # 로그 데이터 직렬화
            log_data = asdict(log_entry)
            
            # Redis에 저장
            log_key = f"logs:{self.service_name}:{log_entry.level.lower()}"
            await self.redis_client.lpush(log_key, json.dumps(log_data))
            
            # 로그 보관 정책 (최근 10000개만 유지)
            await self.redis_client.ltrim(log_key, 0, 9999)
            
            # 만료 시간 설정 (7일)
            await self.redis_client.expire(log_key, 604800)
            
        except Exception as e:
            logger.error(f"Failed to log to remote: {str(e)}")
    
    def set_context(self, **kwargs):
        """로그 컨텍스트 설정"""
        # 스레드 로컬 저장소에 컨텍스트 저장
        import threading
        context = threading.local()
        
        for key, value in kwargs.items():
            setattr(context, key, value)
    
    def clear_context(self):
        """로그 컨텍스트 클리어"""
        import threading
        context = threading.local()
        
        # 모든 컨텍스트 속성 제거
        for attr in dir(context):
            if not attr.startswith('_'):
                delattr(context, attr)

class LoggerManager:
    """로거 관리자 클래스"""
    
    def __init__(self):
        self.loggers: Dict[str, StructuredLogger] = {}
        self.default_config = {
            "service_name": "insitechart",
            "log_level": "INFO",
            "enable_console": True,
            "enable_file": True,
            "enable_remote": False
        }
    
    async def get_logger(
        self,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> StructuredLogger:
        """
        구조화된 로거 인스턴스 가져오기
        
        Args:
            name: 로거 이름
            config: 로거 설정
            
        Returns:
            구조화된 로거 인스턴스
        """
        if name not in self.loggers:
            # 설정 병합
            logger_config = {**self.default_config, **(config or {})}
            
            # 로거 생성
            logger_instance = StructuredLogger(name, **logger_config)
            await logger_instance.initialize()
            
            self.loggers[name] = logger_instance
        
        return self.loggers[name]
    
    async def update_global_config(self, config: Dict[str, Any]):
        """
        전역 로거 설정 업데이트
        
        Args:
            config: 새 설정
        """
        self.default_config.update(config)
        
        # 기존 로거 설정 업데이트
        for logger in self.loggers.values():
            # 필요한 설정만 업데이트
            if hasattr(logger, 'log_level'):
                logger.log_level = getattr(logging, config.get('log_level', 'INFO').upper())
                logger.logger.setLevel(logger.log_level)
    
    def get_all_loggers(self) -> Dict[str, StructuredLogger]:
        """모든 로거 인스턴스 가져오기"""
        return self.loggers.copy()
    
    async def shutdown(self):
        """모든 로거 종료"""
        for logger in self.loggers.values():
            if logger.redis_client:
                await logger.redis_client.close()
        
        self.loggers.clear()

# 전역 로거 관리자 인스턴스
logger_manager = LoggerManager()

# 편의 함수
async def get_logger(name: str, config: Optional[Dict[str, Any]] = None) -> StructuredLogger:
    """
    구조화된 로거 가져오기 편의 함수
    
    Args:
        name: 로거 이름
        config: 로거 설정
        
    Returns:
        구조화된 로거 인스턴스
    """
    return await logger_manager.get_logger(name, config)

# 컨텍스트 관리 데코레이터
def log_context(**context_kwargs):
    """
    로그 컨텍스트 데코레이터
    
    Args:
        **context_kwargs: 컨텍스트 키워드 인자
        
    Returns:
        데코레이터 함수
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 컨텍스트 설정
            logger = await get_logger(func.__module__)
            logger.set_context(**context_kwargs)
            
            try:
                return await func(*args, **kwargs)
            finally:
                # 컨텍스트 클리어
                logger.clear_context()
        
        return wrapper
    return decorator

# 성능 측정 데코레이터
def log_performance(operation_name: Optional[str] = None):
    """
    성능 측정 데코레이터
    
    Args:
        operation_name: 작업 이름 (None이면 함수 이름 사용)
        
    Returns:
        데코레이터 함수
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            # 작업 이름 결정
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = await func(*args, **kwargs)
                
                # 성능 로그 기록
                duration = time.time() - start_time
                logger = await get_logger(func.__module__)
                logger.performance(
                    operation=op_name,
                    duration=duration,
                    success=True
                )
                
                return result
                
            except Exception as e:
                # 실패 로그 기록
                duration = time.time() - start_time
                logger = await get_logger(func.__module__)
                logger.performance(
                    operation=op_name,
                    duration=duration,
                    success=False,
                    error=str(e)
                )
                
                raise
        
        return wrapper
    return decorator

# 감사 로그 데코레이터
def log_audit(event_name: Optional[str] = None):
    """
    감사 로그 데코레이터
    
    Args:
        event_name: 이벤트 이름 (None이면 함수 이름 사용)
        
    Returns:
        데코레이터 함수
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 이벤트 이름 결정
            ev_name = event_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = await func(*args, **kwargs)
                
                # 성공 감사 로그
                logger = await get_logger(func.__module__)
                logger.audit(
                    event=ev_name,
                    status="success",
                    result="completed"
                )
                
                return result
                
            except Exception as e:
                # 실패 감사 로그
                logger = await get_logger(func.__module__)
                logger.audit(
                    event=ev_name,
                    status="failed",
                    error=str(e)
                )
                
                raise
        
        return wrapper
    return decorator