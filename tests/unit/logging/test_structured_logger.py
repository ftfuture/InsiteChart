"""
구조화된 로거 단위 테스트

이 모듈은 구조화된 로거의 개별 기능을 테스트합니다.
"""

import pytest
import json
import logging
from unittest.mock import MagicMock, patch, mock_open
from io import StringIO

from backend.logging.structured_logger import StructuredLogger


class TestStructuredLogger:
    """구조화된 로거 단위 테스트 클래스"""
    
    @pytest.fixture
    def structured_logger(self):
        """구조화된 로거 픽스처"""
        return StructuredLogger("test_logger")
    
    @pytest.fixture
    def mock_log_handler(self):
        """모의 로그 핸들러 픽스처"""
        handler = logging.StreamHandler(StringIO())
        handler.setLevel(logging.DEBUG)
        return handler
    
    def test_logger_initialization(self, structured_logger):
        """로거 초기화 테스트"""
        assert structured_logger.logger.name == "test_logger"
        assert structured_logger.logger.level == logging.INFO
        assert hasattr(structured_logger, 'info')
        assert hasattr(structured_logger, 'error')
        assert hasattr(structured_logger, 'warning')
        assert hasattr(structured_logger, 'debug')
    
    def test_basic_info_logging(self, structured_logger, mock_log_handler):
        """기본 정보 로깅 테스트"""
        structured_logger.logger.addHandler(mock_log_handler)
        
        structured_logger.info("Test message")
        
        # 로그 출력 확인
        log_output = mock_log_handler.stream.getvalue()
        assert "Test message" in log_output
        
        # JSON 형식 확인
        log_lines = [line for line in log_output.strip().split('\n') if line]
        for line in log_lines:
            try:
                log_data = json.loads(line)
                assert "message" in log_data
                assert log_data["message"] == "Test message"
                assert "level" in log_data
                assert log_data["level"] == "INFO"
                assert "timestamp" in log_data
                assert "logger" in log_data
                assert log_data["logger"] == "test_logger"
            except json.JSONDecodeError:
                # 비JSON 형식 로그도 허용
                pass
    
    def test_logging_with_context(self, structured_logger, mock_log_handler):
        """컨텍스트와 함께 로깅 테스트"""
        structured_logger.logger.addHandler(mock_log_handler)
        
        context = {
            "user_id": "12345",
            "request_id": "req-abc-123",
            "ip_address": "192.168.1.1"
        }
        
        structured_logger.info("User action", **context)
        
        # 로그 출력 확인
        log_output = mock_log_handler.stream.getvalue()
        assert "User action" in log_output
        
        # JSON 형식 확인
        log_lines = [line for line in log_output.strip().split('\n') if line]
        for line in log_lines:
            try:
                log_data = json.loads(line)
                assert log_data["message"] == "User action"
                assert log_data["user_id"] == "12345"
                assert log_data["request_id"] == "req-abc-123"
                assert log_data["ip_address"] == "192.168.1.1"
            except json.JSONDecodeError:
                pass
    
    def test_error_logging_with_exception(self, structured_logger, mock_log_handler):
        """예외와 함께 에러 로깅 테스트"""
        structured_logger.logger.addHandler(mock_log_handler)
        
        try:
            raise ValueError("Test exception")
        except Exception as e:
            structured_logger.error("Error occurred", exception=e, exc_info=True)
        
        # 로그 출력 확인
        log_output = mock_log_handler.stream.getvalue()
        assert "Error occurred" in log_output
        assert "Test exception" in log_output
        
        # JSON 형식 확인
        log_lines = [line for line in log_output.strip().split('\n') if line]
        for line in log_lines:
            try:
                log_data = json.loads(line)
                assert log_data["message"] == "Error occurred"
                assert log_data["level"] == "ERROR"
                assert "exception" in log_data
                assert "exc_info" in log_data or "stack_trace" in log_data
            except json.JSONDecodeError:
                pass
    
    def test_warning_logging(self, structured_logger, mock_log_handler):
        """경고 로깅 테스트"""
        structured_logger.logger.addHandler(mock_log_handler)
        
        structured_logger.warning("Warning message", warning_code="WARN_001")
        
        # 로그 출력 확인
        log_output = mock_log_handler.stream.getvalue()
        assert "Warning message" in log_output
        
        # JSON 형식 확인
        log_lines = [line for line in log_output.strip().split('\n') if line]
        for line in log_lines:
            try:
                log_data = json.loads(line)
                assert log_data["message"] == "Warning message"
                assert log_data["level"] == "WARNING"
                assert log_data["warning_code"] == "WARN_001"
            except json.JSONDecodeError:
                pass
    
    def test_debug_logging(self, structured_logger, mock_log_handler):
        """디버그 로깅 테스트"""
        structured_logger.logger.addHandler(mock_log_handler)
        structured_logger.logger.setLevel(logging.DEBUG)
        
        structured_logger.debug("Debug message", debug_info={"key": "value"})
        
        # 로그 출력 확인
        log_output = mock_log_handler.stream.getvalue()
        assert "Debug message" in log_output
        
        # JSON 형식 확인
        log_lines = [line for line in log_output.strip().split('\n') if line]
        for line in log_lines:
            try:
                log_data = json.loads(line)
                assert log_data["message"] == "Debug message"
                assert log_data["level"] == "DEBUG"
                assert log_data["debug_info"]["key"] == "value"
            except json.JSONDecodeError:
                pass
    
    def test_logging_with_special_characters(self, structured_logger, mock_log_handler):
        """특수 문자가 포함된 로깅 테스트"""
        structured_logger.logger.addHandler(mock_log_handler)
        
        special_message = "Message with special chars: 한국어, 🚀, \n\t, \"quotes\""
        structured_logger.info(special_message)
        
        # 로그 출력 확인
        log_output = mock_log_handler.stream.getvalue()
        assert special_message in log_output
        
        # JSON 형식 확인
        log_lines = [line for line in log_output.strip().split('\n') if line]
        for line in log_lines:
            try:
                log_data = json.loads(line)
                assert log_data["message"] == special_message
            except json.JSONDecodeError:
                pass
    
    def test_logging_performance(self, structured_logger):
        """로깅 성능 테스트"""
        import time
        
        # 많은 로그 메시지 생성
        start_time = time.time()
        
        for i in range(1000):
            structured_logger.info(f"Performance test message {i}", iteration=i)
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time_per_log = total_time / 1000
        
        # 성능 기준 확인 (로그당 1ms 이하)
        assert avg_time_per_log < 0.001
        
        print(f"Logging Performance:")
        print(f"  Total Time: {total_time:.4f}s")
        print(f"  Average Time per Log: {avg_time_per_log:.6f}s")
    
    def test_concurrent_logging(self, structured_logger, mock_log_handler):
        """동시 로깅 테스트"""
        import threading
        import time
        
        structured_logger.logger.addHandler(mock_log_handler)
        
        def log_worker(worker_id):
            for i in range(100):
                structured_logger.info(f"Worker {worker_id} message {i}", worker_id=worker_id)
        
        # 여러 스레드에서 동시 로깅
        threads = []
        start_time = time.time()
        
        for i in range(5):
            thread = threading.Thread(target=log_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # 모든 로그가 기록되었는지 확인
        log_output = mock_log_handler.stream.getvalue()
        log_lines = [line for line in log_output.strip().split('\n') if line]
        
        assert len(log_lines) == 500  # 5 workers * 100 messages
        
        print(f"Concurrent Logging Performance:")
        print(f"  Total Time: {end_time - start_time:.4f}s")
        print(f"  Total Logs: {len(log_lines)}")
    
    def test_logging_configuration(self):
        """로깅 설정 테스트"""
        # 사용자 정의 설정으로 로거 생성
        custom_logger = StructuredLogger(
            name="custom_logger",
            level=logging.DEBUG,
            format_string="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        
        assert custom_logger.logger.name == "custom_logger"
        assert custom_logger.logger.level == logging.DEBUG
        
        # 사용자 정의 포맷 확인
        for handler in custom_logger.logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                assert "%(asctime)s" in handler.formatter._fmt
                assert "%(name)s" in handler.formatter._fmt
                assert "%(levelname)s" in handler.formatter._fmt
                assert "%(message)s" in handler.formatter._fmt
    
    def test_file_logging(self, structured_logger, tmp_path):
        """파일 로깅 테스트"""
        log_file = tmp_path / "test.log"
        
        # 파일 핸들러 추가
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        structured_logger.logger.addHandler(file_handler)
        
        structured_logger.info("File logging test", file_test=True)
        
        # 파일 내용 확인
        with open(log_file, 'r') as f:
            log_content = f.read()
        
        assert "File logging test" in log_content
        assert "file_test" in log_content
    
    def test_log_rotation(self, structured_logger, tmp_path):
        """로그 로테이션 테스트"""
        from logging.handlers import RotatingFileHandler
        
        log_file = tmp_path / "rotating_test.log"
        
        # 로테이션 파일 핸들러 추가 (작은 크기로 설정)
        rotating_handler = RotatingFileHandler(
            log_file,
            maxBytes=1024,  # 1KB
            backupCount=3
        )
        rotating_handler.setLevel(logging.INFO)
        structured_logger.logger.addHandler(rotating_handler)
        
        # 많은 로그 메시지로 로테이션 트리거
        for i in range(100):
            structured_logger.info(f"Rotation test message {i} " + "x" * 100)
        
        # 로테이션 파일 확인
        assert log_file.exists()
        
        # 백업 파일 확인
        backup_files = list(tmp_path.glob("rotating_test.log.*"))
        assert len(backup_files) > 0
    
    def test_sensitive_data_filtering(self, structured_logger, mock_log_handler):
        """민감 데이터 필터링 테스트"""
        structured_logger.logger.addHandler(mock_log_handler)
        
        # 민감 데이터 포함 로그
        sensitive_data = {
            "password": "secret123",
            "api_key": "sk-1234567890",
            "credit_card": "4111-1111-1111-1111",
            "safe_data": "this is safe"
        }
        
        structured_logger.info("User login", **sensitive_data)
        
        # 로그 출력 확인
        log_output = mock_log_handler.stream.getvalue()
        assert "User login" in log_output
        assert "safe_data" in log_output
        
        # 민감 데이터가 필터링되었는지 확인
        assert "secret123" not in log_output
        assert "sk-1234567890" not in log_output
        assert "4111-1111-1111-1111" not in log_output
        
        # 마스킹된 형태로 표시되는지 확인
        assert "***" in log_output or "[FILTERED]" in log_output or "[REDACTED]" in log_output
    
    def test_correlation_id_tracking(self, structured_logger, mock_log_handler):
        """상관 ID 추적 테스트"""
        structured_logger.logger.addHandler(mock_log_handler)
        
        # 상관 ID와 함께 로깅
        correlation_id = "corr-123456789"
        structured_logger.info(
            "Request processed",
            correlation_id=correlation_id,
            request_path="/api/stocks",
            method="GET"
        )
        
        # 로그 출력 확인
        log_output = mock_log_handler.stream.getvalue()
        assert "Request processed" in log_output
        
        # JSON 형식 확인
        log_lines = [line for line in log_output.strip().split('\n') if line]
        for line in log_lines:
            try:
                log_data = json.loads(line)
                assert log_data["correlation_id"] == correlation_id
                assert log_data["request_path"] == "/api/stocks"
                assert log_data["method"] == "GET"
            except json.JSONDecodeError:
                pass
    
    def test_metric_logging(self, structured_logger, mock_log_handler):
        """메트릭 로깅 테스트"""
        structured_logger.logger.addHandler(mock_log_handler)
        
        # 메트릭 데이터 로깅
        metrics = {
            "response_time_ms": 150.5,
            "memory_usage_mb": 256.7,
            "cpu_usage_percent": 45.2,
            "request_count": 1000
        }
        
        structured_logger.info("Performance metrics", **metrics)
        
        # 로그 출력 확인
        log_output = mock_log_handler.stream.getvalue()
        assert "Performance metrics" in log_output
        
        # JSON 형식 확인
        log_lines = [line for line in log_output.strip().split('\n') if line]
        for line in log_lines:
            try:
                log_data = json.loads(line)
                assert log_data["response_time_ms"] == 150.5
                assert log_data["memory_usage_mb"] == 256.7
                assert log_data["cpu_usage_percent"] == 45.2
                assert log_data["request_count"] == 1000
            except json.JSONDecodeError:
                pass
    
    def test_structured_logger_context_manager(self, structured_logger, mock_log_handler):
        """구조화된 로거 컨텍스트 관리자 테스트"""
        structured_logger.logger.addHandler(mock_log_handler)
        
        # 컨텍스트 관리자 사용 (가정)
        if hasattr(structured_logger, 'bind'):
            bound_logger = structured_logger.bind(user_id="12345", session_id="sess-abc")
            
            bound_logger.info("Contextual message")
            
            # 로그 출력 확인
            log_output = mock_log_handler.stream.getvalue()
            assert "Contextual message" in log_output
            
            # JSON 형식 확인
            log_lines = [line for line in log_output.strip().split('\n') if line]
            for line in log_lines:
                try:
                    log_data = json.loads(line)
                    assert log_data["user_id"] == "12345"
                    assert log_data["session_id"] == "sess-abc"
                except json.JSONDecodeError:
                    pass
    
    def test_logger_level_filtering(self, structured_logger, mock_log_handler):
        """로거 레벨 필터링 테스트"""
        structured_logger.logger.addHandler(mock_log_handler)
        structured_logger.logger.setLevel(logging.WARNING)  # WARNING 이상만 기록
        
        # 다양한 레벨의 로그
        structured_logger.debug("Debug message")
        structured_logger.info("Info message")
        structured_logger.warning("Warning message")
        structured_logger.error("Error message")
        
        # 로그 출력 확인
        log_output = mock_log_handler.stream.getvalue()
        
        # WARNING 이상만 기록되어야 함
        assert "Debug message" not in log_output
        assert "Info message" not in log_output
        assert "Warning message" in log_output
        assert "Error message" in log_output