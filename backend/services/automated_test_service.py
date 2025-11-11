"""
Automated Test Service for InsiteChart platform.

This service provides automated testing capabilities including
unit tests, integration tests, performance tests, and test reporting.
"""

import asyncio
import logging
import json
import os
import time
import subprocess
import pytest
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
import tempfile
import shutil

from ..cache.unified_cache import UnifiedCacheManager
from ..models.unified_models import TestType, TestStatus, TestPriority, TestSuite, TestExecution, TestReport


@dataclass
class TestReport:
    """Test report."""
    report_id: str
    report_type: str
    execution_ids: List[str]
    generated_at: datetime
    summary: Dict[str, Any]
    details: Dict[str, Any]
    artifacts: List[str]


class AutomatedTestService:
    """Automated test service."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = self._load_configuration()
        
        # Data storage
        self.test_suites: Dict[str, TestSuite] = {}
        self.test_executions: Dict[str, TestExecution] = {}
        self.test_reports: List[TestReport] = []
        
        # Test execution settings
        self.test_execution_enabled = True
        self.max_parallel_tests = self.config.get("max_parallel_tests", 5)
        self.default_timeout = self.config.get("default_test_timeout", 300)
        self.test_artifact_retention_days = self.config.get("test_artifact_retention_days", 30)
        
        # Cache TTL settings
        self.suite_cache_ttl = 3600  # 1 hour
        self.execution_cache_ttl = 1800  # 30 minutes
        self.report_cache_ttl = 86400  # 24 hours
        
        # Initialize default test suites
        self._initialize_default_test_suites()
        
        # Start automated test scheduler only if event loop is running
        try:
            if self.config.get("automated_testing_enabled", True):
                loop = asyncio.get_running_loop()
                loop.create_task(self._test_scheduler_loop())
        except RuntimeError:
            # No event loop running, skip background task creation
            self.logger.warning("No event loop running, background tasks not started")
        
        self.logger.info("AutomatedTestService initialized")
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load automated test configuration."""
        try:
            return {
                "automated_testing_enabled": os.getenv('AUTOMATED_TESTING_ENABLED', 'true').lower() == 'true',
                "test_environment": os.getenv('TEST_ENVIRONMENT', 'development'),
                "test_database_url": os.getenv('TEST_DATABASE_URL', 'postgresql://test:test@localhost/testdb'),
                "test_api_base_url": os.getenv('TEST_API_BASE_URL', 'http://localhost:8000/api/v1'),
                "max_parallel_tests": int(os.getenv('MAX_PARALLEL_TESTS', '5')),
                "default_test_timeout": int(os.getenv('DEFAULT_TEST_TIMEOUT', '300')),
                "test_artifact_retention_days": int(os.getenv('TEST_ARTIFACT_RETENTION_DAYS', '30')),
                "notification_webhook": os.getenv('TEST_NOTIFICATION_WEBHOOK'),
                "slack_webhook": os.getenv('SLACK_WEBHOOK_URL'),
                "email_recipients": os.getenv('TEST_EMAIL_RECIPIENTS', 'dev-team@insitechart.com').split(','),
                "performance_thresholds": {
                    "response_time_ms": int(os.getenv('PERF_RESPONSE_TIME_THRESHOLD', '1000')),
                    "memory_usage_mb": int(os.getenv('PERF_MEMORY_THRESHOLD', '512')),
                    "cpu_usage_percent": int(os.getenv('PERF_CPU_THRESHOLD', '80'))
                },
                "test_schedule": {
                    "unit_tests": os.getenv('UNIT_TEST_SCHEDULE', '0 2 * * *'),  # Daily at 2 AM
                    "integration_tests": os.getenv('INTEGRATION_TEST_SCHEDULE', '0 4 * * *'),  # Daily at 4 AM
                    "performance_tests": os.getenv('PERF_TEST_SCHEDULE', '0 6 * * 1'),  # Daily at 6 AM on Monday
                    "security_tests": os.getenv('SECURITY_TEST_SCHEDULE', '0 8 * * 1'),  # Daily at 8 AM on Monday
                    "full_suite": os.getenv('FULL_TEST_SCHEDULE', '0 0 * * 1')  # Daily at midnight on Monday
                }
            }
        except Exception as e:
            self.logger.error(f"Error loading automated test configuration: {str(e)}")
            return {}
    
    def _initialize_default_test_suites(self):
        """Initialize default test suites."""
        try:
            default_suites = [
                TestSuite(
                    suite_id="unit_tests_backend",
                    name="Backend Unit Tests",
                    description="Unit tests for backend services and API endpoints",
                    test_type=TestType.UNIT,
                    test_paths=["tests/unit"],
                    test_files=["test_*.py"],
                    enabled=True,
                    timeout_seconds=300,
                    parallel=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                TestSuite(
                    suite_id="integration_tests_backend",
                    name="Backend Integration Tests",
                    description="Integration tests for backend services and database operations",
                    test_type=TestType.INTEGRATION,
                    test_paths=["tests/integration"],
                    test_files=["test_*.py"],
                    enabled=True,
                    timeout_seconds=600,
                    parallel=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                TestSuite(
                    suite_id="performance_tests_api",
                    name="API Performance Tests",
                    description="Performance tests for API endpoints and database operations",
                    test_type=TestType.PERFORMANCE,
                    test_paths=["tests/performance"],
                    test_files=["test_*.py"],
                    enabled=True,
                    timeout_seconds=900,
                    parallel=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                TestSuite(
                    suite_id="security_tests_api",
                    name="API Security Tests",
                    description="Security tests for API endpoints and authentication",
                    test_type=TestType.SECURITY,
                    test_paths=["tests/security"],
                    test_files=["test_*.py"],
                    enabled=True,
                    timeout_seconds=600,
                    parallel=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                TestSuite(
                    suite_id="end_to_end_tests",
                    name="End-to-End Tests",
                    description="End-to-end tests for complete user workflows",
                    test_type=TestType.END_TO_END,
                    test_paths=["tests/e2e"],
                    test_files=["test_*.py"],
                    enabled=True,
                    timeout_seconds=1200,
                    parallel=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            ]
            
            for suite in default_suites:
                self.test_suites[suite.suite_id] = suite
            
            self.logger.info(f"Initialized {len(default_suites)} default test suites")
            
        except Exception as e:
            self.logger.error(f"Error initializing default test suites: {str(e)}")
    
    async def _test_scheduler_loop(self):
        """Main test scheduler loop."""
        while True:
            try:
                current_time = datetime.utcnow()
                
                # Check if any scheduled tests should run
                await self._check_and_run_scheduled_tests(current_time)
                
                # Clean up old test artifacts
                await self._cleanup_old_test_artifacts()
                
                # Wait for next check (run every hour)
                await asyncio.sleep(3600)
                
            except Exception as e:
                self.logger.error(f"Error in test scheduler loop: {str(e)}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _check_and_run_scheduled_tests(self, current_time: datetime):
        """Check and run scheduled tests based on current time."""
        try:
            # Check unit tests schedule
            if self._should_run_schedule("unit_tests", current_time):
                await self.run_test_suite("unit_tests_backend")
            
            # Check integration tests schedule
            if self._should_run_schedule("integration_tests", current_time):
                await self.run_test_suite("integration_tests_backend")
            
            # Check performance tests schedule
            if self._should_run_schedule("performance_tests", current_time):
                await self.run_test_suite("performance_tests_api")
            
            # Check security tests schedule
            if self._should_run_schedule("security_tests", current_time):
                await self.run_test_suite("security_tests_api")
            
            # Check full suite schedule
            if self._should_run_schedule("full_suite", current_time):
                await self.run_full_test_suite()
                
        except Exception as e:
            self.logger.error(f"Error checking and running scheduled tests: {str(e)}")
    
    def _should_run_schedule(self, schedule_key: str, current_time: datetime) -> bool:
        """Check if a scheduled test should run based on current time."""
        try:
            schedule = self.config.get("test_schedule", {}).get(schedule_key, "")
            if not schedule:
                return False
            
            # Parse cron-like schedule (simplified)
            # Format: "minute hour day_of_month day_of_week"
            # For simplicity, we'll just check if current time matches the schedule
            # In production, you'd use a proper cron parser
            
            # For now, just return True if schedule is set (simplified logic)
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking schedule {schedule_key}: {str(e)}")
            return False
    
    async def run_test_suite(self, suite_id: str) -> Dict[str, Any]:
        """Run a specific test suite."""
        try:
            if not self.test_execution_enabled:
                return {"success": False, "error": "Automated testing is disabled"}
            
            # Get test suite
            suite = self.test_suites.get(suite_id)
            if not suite:
                return {"success": False, "error": f"Test suite {suite_id} not found"}
            
            if not suite.enabled:
                return {"success": False, "error": f"Test suite {suite_id} is disabled"}
            
            # Create test execution record
            execution_id = str(uuid.uuid4())
            execution = TestExecution(
                execution_id=execution_id,
                suite_id=suite_id,
                status=TestStatus.RUNNING,
                started_at=datetime.utcnow(),
                completed_at=None,
                duration_seconds=0,
                test_results=[],
                error_message=None,
                environment=self._get_test_environment(),
                metadata={"suite_name": suite.name}
            )
            
            self.test_executions[execution_id] = execution
            
            # Run tests
            if suite.parallel:
                result = await self._run_parallel_tests(suite, execution)
            else:
                result = await self._run_sequential_tests(suite, execution)
            
            # Update execution record
            execution.status = result["status"]
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = result["duration_seconds"]
            execution.test_results = result["test_results"]
            execution.error_message = result.get("error_message")
            
            # Generate test report
            await self._generate_test_report(execution)
            
            # Send notifications
            await self._send_test_notifications(execution)
            
            self.logger.info(f"Completed test suite {suite_id}: {result['status']}")
            
            return {
                "success": True,
                "execution_id": execution_id,
                "status": result["status"],
                "duration_seconds": result["duration_seconds"],
                "tests_run": len(result["test_results"]),
                "tests_passed": len([r for r in result["test_results"] if r.get("status") == "passed"]),
                "tests_failed": len([r for r in result["test_results"] if r.get("status") == "failed"])
            }
            
        except Exception as e:
            self.logger.error(f"Error running test suite {suite_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def run_full_test_suite(self) -> Dict[str, Any]:
        """Run the full test suite (all test suites)."""
        try:
            suite_ids = [suite_id for suite_id in self.test_suites.keys() if self.test_suites[suite_id].enabled]
            
            results = []
            total_duration = 0
            total_tests = 0
            total_passed = 0
            total_failed = 0
            
            for suite_id in suite_ids:
                result = await self.run_test_suite(suite_id)
                results.append(result)
                
                if result.get("success"):
                    total_duration += result.get("duration_seconds", 0)
                    total_tests += result.get("tests_run", 0)
                    total_passed += result.get("tests_passed", 0)
                    total_failed += result.get("tests_failed", 0)
            
            # Create combined execution record
            execution_id = str(uuid.uuid4())
            execution = TestExecution(
                execution_id=execution_id,
                suite_id="full_suite",
                status=TestStatus.PASSED if total_failed == 0 else TestStatus.FAILED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                duration_seconds=total_duration,
                test_results=[],
                error_message=None if total_failed == 0 else f"{total_failed} tests failed",
                environment=self._get_test_environment(),
                metadata={
                    "suite_count": len(suite_ids),
                    "total_tests": total_tests,
                    "total_passed": total_passed,
                    "total_failed": total_failed
                }
            )
            
            self.test_executions[execution_id] = execution
            
            # Generate combined test report
            await self._generate_test_report(execution)
            
            # Send notifications
            await self._send_test_notifications(execution)
            
            self.logger.info(f"Completed full test suite: {execution.status}")
            
            return {
                "success": True,
                "execution_id": execution_id,
                "status": execution.status.value,
                "duration_seconds": total_duration,
                "suites_run": len(suite_ids),
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed
            }
            
        except Exception as e:
            self.logger.error(f"Error running full test suite: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _run_parallel_tests(self, suite: TestSuite, execution: TestExecution, test_files: List[str] = None) -> Dict[str, Any]:
        """Run tests in parallel."""
        try:
            start_time = time.time()
            
            # Discover test files if not provided
            if test_files is None:
                test_files = await self._discover_test_files(suite.test_paths, suite.test_files)
            
            if not test_files:
                return {
                    "status": TestStatus.SKIPPED.value,
                    "duration_seconds": 0,
                    "test_results": [],
                    "error_message": "No test files found"
                }
            
            # Run tests in parallel batches
            batch_size = min(self.max_parallel_tests, len(test_files))
            test_results = []
            
            # Use pytest for parallel execution
            cmd = [
                "python", "-m", "pytest",
                "-v",
                f"--junit-xml=test-results-{execution.execution_id}.xml",
                f"--html=test-results-{execution.execution_id}.html",
                "--tb=short",
                f"--maxfail={len(test_files)}",
                *test_files
            ]
            
            # Set test environment variables
            env = os.environ.copy()
            env.update(self._get_test_environment())
            
            # Run tests
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=os.getcwd()
            )
            
            stdout, stderr = await process.communicate()
            
            # Parse test results (simplified)
            # In production, you'd parse the JUnit XML output
            test_results = self._parse_test_results(stdout, test_files)
            
            duration_seconds = int(time.time() - start_time)
            
            return {
                "status": TestStatus.PASSED if all(r.get("status") == "passed" for r in test_results) else TestStatus.FAILED,
                "duration_seconds": duration_seconds,
                "test_results": test_results,
                "error_message": None if all(r.get("status") == "passed" for r in test_results) else "Some tests failed"
            }
            
        except Exception as e:
            self.logger.error(f"Error running parallel tests: {str(e)}")
            return {
                "status": TestStatus.FAILED.value,
                "duration_seconds": 0,
                "test_results": [],
                "error_message": str(e)
            }
    
    async def _run_sequential_tests(self, suite: TestSuite, execution: TestExecution, test_files: List[str] = None) -> Dict[str, Any]:
        """Run tests sequentially."""
        try:
            start_time = time.time()
            
            # Discover test files if not provided
            if test_files is None:
                test_files = await self._discover_test_files(suite.test_paths, suite.test_files)
            
            if not test_files:
                return {
                    "status": TestStatus.SKIPPED.value,
                    "duration_seconds": 0,
                    "test_results": [],
                    "error_message": "No test files found"
                }
            
            test_results = []
            
            # Run tests sequentially
            for test_file in test_files:
                try:
                    # Run individual test file
                    cmd = [
                        "python", "-m", "pytest",
                        "-v",
                        f"--tb=short",
                        test_file
                    ]
                    
                    # Set test environment variables
                    env = os.environ.copy()
                    env.update(self._get_test_environment())
                    
                    # Run test
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        env=env,
                        cwd=os.getcwd()
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    # Parse test result
                    test_result = self._parse_single_test_result(stdout, test_file)
                    test_results.append(test_result)
                    
                except Exception as e:
                    self.logger.error(f"Error running test {test_file}: {str(e)}")
                    test_results.append({
                        "test_file": test_file,
                        "status": TestStatus.FAILED.value,
                        "error_message": str(e),
                        "duration_seconds": 0
                    })
            
            duration_seconds = int(time.time() - start_time)
            
            return {
                "status": TestStatus.PASSED if all(r.get("status") == "passed" for r in test_results) else TestStatus.FAILED,
                "duration_seconds": duration_seconds,
                "test_results": test_results,
                "error_message": None if all(r.get("status") == "passed" for r in test_results) else "Some tests failed"
            }
            
        except Exception as e:
            self.logger.error(f"Error running sequential tests: {str(e)}")
            return {
                "status": TestStatus.FAILED.value,
                "duration_seconds": 0,
                "test_results": [],
                "error_message": str(e)
            }
    
    async def _discover_test_files(self, test_paths: List[str], test_patterns: List[str]) -> List[str]:
        """Discover test files based on paths and patterns."""
        try:
            test_files = []
            
            for test_path in test_paths:
                if os.path.exists(test_path):
                    for pattern in test_patterns:
                        import glob
                        files = glob.glob(os.path.join(test_path, pattern))
                        test_files.extend(files)
            
            return list(set(test_files))  # Remove duplicates
            
        except Exception as e:
            self.logger.error(f"Error discovering test files: {str(e)}")
            return []
    
    def _parse_test_results(self, pytest_output: str, test_files: List[str]) -> List[Dict[str, Any]]:
        """Parse pytest output to extract test results."""
        try:
            # This is a simplified parser
            # In production, you'd parse the JUnit XML output
            
            test_results = []
            lines = pytest_output.split('\n')
            
            for test_file in test_files:
                # Look for test result in output
                status = TestStatus.FAILED
                error_message = None
                duration_seconds = 0
                
                for line in lines:
                    if test_file in line and "PASSED" in line:
                        status = TestStatus.PASSED
                    elif test_file in line and "FAILED" in line:
                        status = TestStatus.FAILED
                        # Extract error message
                        error_message = line.split("FAILED")[-1].strip() if "FAILED" in line else None
                    elif test_file in line and "duration" in line.lower():
                        # Extract duration
                        try:
                            duration_str = line.split("duration")[-1].strip().split("=")[-1].strip()
                            duration_seconds = int(float(duration_str))
                        except:
                            pass
                
                test_results.append({
                    "test_file": test_file,
                    "status": status.value,
                    "error_message": error_message,
                    "duration_seconds": duration_seconds
                })
            
            return test_results
            
        except Exception as e:
            self.logger.error(f"Error parsing test results: {str(e)}")
            return []
    
    def _parse_single_test_result(self, pytest_output, test_file: str) -> Dict[str, Any]:
        """Parse pytest output for a single test file."""
        try:
            # Convert bytes to string if needed
            if isinstance(pytest_output, bytes):
                pytest_output = pytest_output.decode('utf-8')
            
            status = TestStatus.FAILED
            error_message = None
            duration_seconds = 0
            
            lines = pytest_output.split('\n')
            
            for line in lines:
                if test_file in line and "PASSED" in line:
                    status = TestStatus.PASSED
                elif test_file in line and "FAILED" in line:
                    status = TestStatus.FAILED
                    error_message = line.split("FAILED")[-1].strip() if "FAILED" in line else None
                elif test_file in line and "duration" in line.lower():
                    try:
                        duration_str = line.split("duration")[-1].strip().split("=")[-1].strip()
                        duration_seconds = int(float(duration_str))
                    except:
                        pass
            
            return {
                "test_file": test_file,
                "status": status.value,
                "error_message": error_message,
                "duration_seconds": duration_seconds
            }
            
        except Exception as e:
            self.logger.error(f"Error parsing single test result: {str(e)}")
            return {
                "test_file": test_file,
                "status": TestStatus.FAILED.value,
                "error_message": str(e),
                "duration_seconds": 0
            }
    
    def _get_test_environment(self) -> Dict[str, str]:
        """Get test environment variables."""
        try:
            return {
                "TEST_ENVIRONMENT": self.config.get("test_environment", "development"),
                "TEST_DATABASE_URL": self.config.get("test_database_url", ""),
                "TEST_API_BASE_URL": self.config.get("test_api_base_url", ""),
                "PYTHONPATH": os.getcwd(),
                "COVERAGE_PROCESS_START": "python -m coverage run",
                "COVERAGE_PROCESS_END": "python -m coverage report",
                "PYTEST_CURRENT_TEST": os.getenv('PYTEST_CURRENT_TEST', ''),
                "CI": os.getenv('CI', 'false')
            }
        except Exception as e:
            self.logger.error(f"Error getting test environment: {str(e)}")
            return {}
    
    async def _generate_test_report(self, execution: TestExecution):
        """Generate test report."""
        try:
            suite = self.test_suites.get(execution.suite_id)
            if not suite:
                return
            
            # Calculate test statistics
            total_tests = len(execution.test_results)
            passed_tests = len([r for r in execution.test_results if r.get("status") == "passed"])
            failed_tests = len([r for r in execution.test_results if r.get("status") == "failed"])
            skipped_tests = len([r for r in execution.test_results if r.get("status") == "skipped"])
            
            # Calculate performance metrics for performance tests
            performance_metrics = {}
            if suite.test_type == TestType.PERFORMANCE:
                response_times = [r.get("duration_seconds", 0) for r in execution.test_results if r.get("status") == "passed"]
                if response_times:
                    performance_metrics = {
                        "avg_response_time_ms": sum(response_times) / len(response_times) * 1000,
                        "min_response_time_ms": min(response_times) * 1000,
                        "max_response_time_ms": max(response_times) * 1000,
                        "p95_response_time_ms": sorted(response_times)[int(len(response_times) * 0.95)] * 1000
                    }
            
            # Create report
            report = TestReport(
                report_id=str(uuid.uuid4()),
                report_type="test_execution",
                execution_ids=[execution.execution_id],
                generated_at=datetime.utcnow(),
                summary={
                    "suite_name": suite.name,
                    "suite_type": suite.test_type.value,
                    "status": execution.status.value if hasattr(execution.status, 'value') else str(execution.status),
                    "started_at": execution.started_at.isoformat(),
                    "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                    "duration_seconds": execution.duration_seconds,
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": failed_tests,
                    "skipped_tests": skipped_tests,
                    "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                    "performance_metrics": performance_metrics
                },
                details={
                    "test_results": execution.test_results,
                    "environment": execution.environment,
                    "metadata": execution.metadata
                },
                artifacts=[
                    f"test-results-{execution.execution_id}.xml",
                    f"test-results-{execution.execution_id}.html"
                ]
            )
            
            self.test_reports.append(report)
            
            # Cache report
            cache_key = f"test_report_{report.report_id}"
            await self.cache_manager.set(cache_key, report.__dict__, ttl=self.report_cache_ttl)
            
            self.logger.info(f"Generated test report: {report.report_id}")
            
        except Exception as e:
            self.logger.error(f"Error generating test report: {str(e)}")
    
    async def _send_test_notifications(self, execution: TestExecution):
        """Send test notifications."""
        try:
            suite = self.test_suites.get(execution.suite_id)
            if not suite:
                return
            
            # Prepare notification message
            if execution.status == TestStatus.PASSED:
                status_emoji = "✅"
                status_text = "PASSED"
            elif execution.status == TestStatus.FAILED:
                status_emoji = "❌"
                status_text = "FAILED"
            else:
                status_emoji = "⏸"
                status_text = execution.status.value.upper() if hasattr(execution.status, 'value') else str(execution.status).upper()
            
            message = f"""
{status_emoji} Test Suite: {suite.name}
Status: {status_text}
Duration: {execution.duration_seconds}s
Tests: {len(execution.test_results)} total, {len([r for r in execution.test_results if r.get('status') == 'passed'])} passed, {len([r for r in execution.test_results if r.get('status') == 'failed'])} failed
            """
            
            # Send webhook notification
            webhook_url = self.config.get("notification_webhook")
            if webhook_url:
                await self._send_webhook_notification(webhook_url, {
                    "type": "test_execution",
                    "execution_id": execution.execution_id,
                    "suite_name": suite.name,
                    "status": execution.status.value if hasattr(execution.status, 'value') else str(execution.status),
                    "message": message.strip()
                })
            
            # Send Slack notification
            slack_webhook = self.config.get("slack_webhook")
            if slack_webhook:
                await self._send_slack_notification(slack_webhook, message.strip())
            
            # Send email notification
            email_recipients = self.config.get("email_recipients", [])
            if email_recipients and execution.status == TestStatus.FAILED:
                await self._send_email_notification(email_recipients, f"Test Suite Failed: {suite.name}", message.strip())
            
        except Exception as e:
            self.logger.error(f"Error sending test notifications: {str(e)}")
    
    async def _send_webhook_notification(self, webhook_url: str, data: Dict[str, Any]):
        """Send webhook notification."""
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=data) as response:
                    if response.status == 200:
                        self.logger.info("Webhook notification sent successfully")
                    else:
                        self.logger.warning(f"Webhook notification failed with status: {response.status}")
            
        except Exception as e:
            self.logger.error(f"Error sending webhook notification: {str(e)}")
    
    async def _send_slack_notification(self, webhook_url: str, message: str):
        """Send Slack notification."""
        try:
            import aiohttp
            
            payload = {
                "text": message,
                "username": "InsiteChart Test Bot",
                "icon_emoji": ":robot_face:"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status == 200:
                        self.logger.info("Slack notification sent successfully")
                    else:
                        self.logger.warning(f"Slack notification failed with status: {response.status}")
            
        except Exception as e:
            self.logger.error(f"Error sending Slack notification: {str(e)}")
    
    async def _send_email_notification(self, recipients: List[str], subject: str, message: str):
        """Send email notification."""
        try:
            # This would integrate with your email service
            # For now, just log the email
            self.logger.info(f"Email notification - To: {recipients}, Subject: {subject}, Message: {message}")
            
        except Exception as e:
            self.logger.error(f"Error sending email notification: {str(e)}")
    
    async def _cleanup_old_test_artifacts(self):
        """Clean up old test artifacts."""
        try:
            # This would clean up old test reports, logs, and artifacts
            # For now, just log the cleanup action
            self.logger.info("Test artifact cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up test artifacts: {str(e)}")
    
    async def run_manual_test(
        self,
        suite_id: str,
        test_files: Optional[List[str]] = None,
        environment: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Run a manual test with custom parameters."""
        try:
            # Get test suite
            suite = self.test_suites.get(suite_id)
            if not suite:
                return {"success": False, "error": f"Test suite {suite_id} not found"}
            
            # Create test execution record
            execution_id = str(uuid.uuid4())
            execution = TestExecution(
                execution_id=execution_id,
                suite_id=suite_id,
                status=TestStatus.RUNNING,
                started_at=datetime.utcnow(),
                completed_at=None,
                duration_seconds=0,
                test_results=[],
                error_message=None,
                environment=environment or self._get_test_environment(),
                metadata={"manual_execution": True}
            )
            
            self.test_executions[execution_id] = execution
            
            # Use provided test files directly without discovery
            if test_files:
                actual_test_files = test_files
            else:
                actual_test_files = await self._discover_test_files(suite.test_paths, suite.test_files)
            
            # Run tests
            if suite.parallel and len(actual_test_files) > 1:
                result = await self._run_parallel_tests(suite, execution, actual_test_files)
            else:
                result = await self._run_sequential_tests(suite, execution, actual_test_files)
            
            # Update execution record
            execution.status = result["status"]
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = result["duration_seconds"]
            execution.test_results = result["test_results"]
            execution.error_message = result.get("error_message")
            
            # Generate test report
            await self._generate_test_report(execution)
            
            # Send notifications
            await self._send_test_notifications(execution)
            
            return {
                "success": True,
                "execution_id": execution_id,
                "status": result["status"],
                "duration_seconds": result["duration_seconds"],
                "tests_run": len(result["test_results"]),
                "tests_passed": len([r for r in result["test_results"] if r.get("status") == "passed"]),
                "tests_failed": len([r for r in result["test_results"] if r.get("status") == "failed"])
            }
            
        except Exception as e:
            self.logger.error(f"Error running manual test: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_test_suites(self) -> List[Dict[str, Any]]:
        """Get all configured test suites."""
        try:
            suites = list(self.test_suites.values())
            
            # Convert to dictionaries
            return [
                {
                    "suite_id": s.suite_id,
                    "name": s.name,
                    "description": s.description,
                    "test_type": s.test_type.value,
                    "test_paths": s.test_paths,
                    "test_files": s.test_files,
                    "enabled": s.enabled,
                    "timeout_seconds": s.timeout_seconds,
                    "parallel": s.parallel,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat()
                }
                for s in suites
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting test suites: {str(e)}")
            return []
    
    async def get_test_executions(
        self,
        suite_id: Optional[str] = None,
        status: Optional[TestStatus] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get test execution records."""
        try:
            executions = list(self.test_executions.values())
            
            # Apply filters
            if suite_id:
                executions = [e for e in executions if e.suite_id == suite_id]
            
            if status:
                executions = [e for e in executions if e.status == status]
            
            # Sort by start time (newest first)
            executions.sort(key=lambda x: x.started_at, reverse=True)
            
            # Apply limit
            executions = executions[:limit]
            
            # Convert to dictionaries
            return [
                {
                    "execution_id": e.execution_id,
                    "suite_id": e.suite_id,
                    "status": e.status.value,
                    "started_at": e.started_at.isoformat(),
                    "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                    "duration_seconds": e.duration_seconds,
                    "test_results_count": len(e.test_results),
                    "error_message": e.error_message,
                    "environment": e.environment,
                    "metadata": e.metadata
                }
                for e in executions
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting test executions: {str(e)}")
            return []
    
    async def get_test_reports(
        self,
        report_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get test reports."""
        try:
            reports = self.test_reports
            
            # Apply filter
            if report_type:
                reports = [r for r in reports if r.report_type == report_type]
            
            # Sort by generation time (newest first)
            reports.sort(key=lambda x: x.generated_at, reverse=True)
            
            # Apply limit
            reports = reports[:limit]
            
            # Convert to dictionaries
            return [
                {
                    "report_id": r.report_id,
                    "report_type": r.report_type,
                    "execution_ids": r.execution_ids,
                    "generated_at": r.generated_at.isoformat(),
                    "summary": r.summary,
                    "details": r.details,
                    "artifacts": r.artifacts
                }
                for r in reports
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting test reports: {str(e)}")
            return []
    
    async def get_test_metrics(self) -> Dict[str, Any]:
        """Get automated test metrics."""
        try:
            # Calculate execution statistics
            total_executions = len(self.test_executions)
            passed_executions = len([e for e in self.test_executions.values() if e.status == TestStatus.PASSED])
            failed_executions = len([e for e in self.test_executions.values() if e.status == TestStatus.FAILED])
            
            # Calculate suite statistics
            suite_stats = {}
            for suite_id, suite in self.test_suites.items():
                suite_executions = [e for e in self.test_executions.values() if e.suite_id == suite_id]
                suite_executions.sort(key=lambda x: x.started_at, reverse=True)
                
                if suite_executions:
                    latest_execution = suite_executions[0]
                    avg_duration = sum(e.duration_seconds for e in suite_executions) / len(suite_executions)
                else:
                    latest_execution = None
                    avg_duration = 0
                
                suite_stats[suite_id] = {
                    "total_executions": len(suite_executions),
                    "latest_execution": latest_execution.execution_id if latest_execution else None,
                    "latest_status": latest_execution.status.value if latest_execution else None,
                    "avg_duration_seconds": avg_duration
                }
            
            return {
                "total_executions": total_executions,
                "passed_executions": passed_executions,
                "failed_executions": failed_executions,
                "success_rate": (passed_executions / total_executions * 100) if total_executions > 0 else 0,
                "total_suites": len(self.test_suites),
                "enabled_suites": len([s for s in self.test_suites.values() if s.enabled]),
                "suite_statistics": suite_stats,
                "configuration": {
                    "automated_testing_enabled": self.test_execution_enabled,
                    "max_parallel_tests": self.max_parallel_tests,
                    "default_timeout": self.default_timeout,
                    "test_artifact_retention_days": self.test_artifact_retention_days
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting test metrics: {str(e)}")
            return {"error": str(e)}
    
    async def enable_test_suite(self, suite_id: str) -> Dict[str, Any]:
        """Enable a test suite."""
        try:
            if suite_id not in self.test_suites:
                return {"success": False, "error": f"Test suite {suite_id} not found"}
            
            self.test_suites[suite_id].enabled = True
            self.test_suites[suite_id].updated_at = datetime.utcnow()
            
            return {
                "success": True,
                "suite_id": suite_id,
                "message": f"Test suite {suite_id} enabled"
            }
            
        except Exception as e:
            self.logger.error(f"Error enabling test suite {suite_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def disable_test_suite(self, suite_id: str) -> Dict[str, Any]:
        """Disable a test suite."""
        try:
            if suite_id not in self.test_suites:
                return {"success": False, "error": f"Test suite {suite_id} not found"}
            
            self.test_suites[suite_id].enabled = False
            self.test_suites[suite_id].updated_at = datetime.utcnow()
            
            return {
                "success": True,
                "suite_id": suite_id,
                "message": f"Test suite {suite_id} disabled"
            }
            
        except Exception as e:
            self.logger.error(f"Error disabling test suite {suite_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def initialize(self):
        """Initialize automated test service."""
        try:
            self.logger.info("Initializing AutomatedTestService...")
            
            # Load test configurations
            await self._load_test_configurations()
            
            # Cache test suites
            await self._cache_test_suites()
            
            self.logger.info("AutomatedTestService initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize AutomatedTestService: {str(e)}")
            raise
    
    async def _load_test_configurations(self):
        """Load test configurations from files."""
        try:
            # This would load test configurations from files
            # For now, just log the action
            self.logger.info("Test configurations loaded")
            
        except Exception as e:
            self.logger.error(f"Failed to load test configurations: {str(e)}")
    
    async def _cache_test_suites(self):
        """Cache test suites for fast access."""
        try:
            for suite_id, suite in self.test_suites.items():
                cache_key = f"test_suite:{suite_id}"
                await self.cache_manager.set(cache_key, suite.__dict__, ttl=self.suite_cache_ttl)
            
            self.logger.info("Test suites cached successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to cache test suites: {str(e)}")
    
    async def close(self):
        """Close automated test service."""
        try:
            self.logger.info("Shutting down automated test service")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")