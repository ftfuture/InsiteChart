"""
테스트 실행 스크립트
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from datetime import datetime


def run_command(cmd, cwd=None, capture_output=True):
    """명령어 실행"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            timeout=1800  # 30분 타임아웃
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out after 30 minutes"
    except Exception as e:
        return False, "", str(e)


def setup_test_environment():
    """테스트 환경 설정"""
    print("Setting up test environment...")
    
    # reports 디렉토리 생성
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    
    # logs 디렉토리 생성
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # test_data 디렉토리 생성
    test_data_dir = Path("test_data")
    test_data_dir.mkdir(exist_ok=True)
    
    # 환경 변수 설정
    os.environ['TESTING'] = 'true'
    os.environ['LOG_LEVEL'] = 'DEBUG'
    
    # 테스트 데이터베이스 설정
    os.environ['DATABASE_URL'] = 'sqlite:///./test_data/test.db'
    
    # Redis 설정 (테스트용)
    os.environ['REDIS_URL'] = 'redis://localhost:6379/1'  # DB 1 사용
    
    print("Test environment setup complete")


def run_unit_tests(args):
    """단위 테스트 실행"""
    print("Running unit tests...")
    
    cmd = [
        "python", "-m", "pytest",
        "tests/unit/",
        "-v",
        "--junit-xml=reports/unit-test-results.xml",
        "--cov=backend",
        "--cov-report=xml:reports/unit-coverage.xml",
        "--cov-report=html:reports/unit-coverage-html",
        "--cov-report=term-missing",
        "--tb=short"
    ]
    
    if args.marker:
        cmd.extend(["-m", args.marker])
    
    if args.keyword:
        cmd.extend(["-k", args.keyword])
    
    if args.failed:
        cmd.append("--lf")
    
    if args.verbose:
        cmd.append("-vv")
    
    success, stdout, stderr = run_command(" ".join(cmd))
    
    if not success:
        print(f"Unit tests failed: {stderr}")
        return False
    
    print("Unit tests completed successfully")
    return True


def run_integration_tests(args):
    """통합 테스트 실행"""
    print("Running integration tests...")
    
    cmd = [
        "python", "-m", "pytest",
        "tests/integration/",
        "-v",
        "--junit-xml=reports/integration-test-results.xml",
        "--cov=backend",
        "--cov-report=xml:reports/integration-coverage.xml",
        "--cov-report=html:reports/integration-coverage-html",
        "--tb=short"
    ]
    
    if args.marker:
        cmd.extend(["-m", args.marker])
    
    if args.keyword:
        cmd.extend(["-k", args.keyword])
    
    success, stdout, stderr = run_command(" ".join(cmd))
    
    if not success:
        print(f"Integration tests failed: {stderr}")
        return False
    
    print("Integration tests completed successfully")
    return True


def run_performance_tests(args):
    """성능 테스트 실행"""
    print("Running performance tests...")
    
    cmd = [
        "python", "-m", "pytest",
        "tests/performance/",
        "-v",
        "--junit-xml=reports/performance-test-results.xml",
        "--tb=short"
    ]
    
    if args.marker:
        cmd.extend(["-m", args.marker])
    
    if args.keyword:
        cmd.extend(["-k", args.keyword])
    
    success, stdout, stderr = run_command(" ".join(cmd))
    
    if not success:
        print(f"Performance tests failed: {stderr}")
        return False
    
    print("Performance tests completed successfully")
    return True


def run_security_tests(args):
    """보안 테스트 실행"""
    print("Running security tests...")
    
    cmd = [
        "python", "-m", "pytest",
        "tests/security/",
        "-v",
        "--junit-xml=reports/security-test-results.xml",
        "--tb=short"
    ]
    
    if args.marker:
        cmd.extend(["-m", args.marker])
    
    if args.keyword:
        cmd.extend(["-k", args.keyword])
    
    success, stdout, stderr = run_command(" ".join(cmd))
    
    if not success:
        print(f"Security tests failed: {stderr}")
        return False
    
    print("Security tests completed successfully")
    return True


def run_all_tests(args):
    """모든 테스트 실행"""
    print("Running all tests...")
    
    results = {
        'unit': run_unit_tests(args),
        'integration': run_integration_tests(args),
        'performance': run_performance_tests(args),
        'security': run_security_tests(args)
    }
    
    return results


def generate_coverage_report():
    """커버리지 보고서 생성"""
    print("Generating combined coverage report...")
    
    cmd = [
        "python", "-m", "pytest",
        "tests/",
        "--cov=backend",
        "--cov-report=xml:reports/coverage.xml",
        "--cov-report=html:reports/coverage-html",
        "--cov-report=term",
        "--cov-fail-under=80"
    ]
    
    success, stdout, stderr = run_command(" ".join(cmd))
    
    if not success:
        print(f"Coverage report generation failed: {stderr}")
        return False
    
    print("Coverage report generated successfully")
    return True


def check_dependencies():
    """의존성 확인"""
    print("Checking dependencies...")
    
    # 필수 패키지 확인
    required_packages = [
        "pytest",
        "pytest-asyncio",
        "pytest-cov",
        "pytest-mock",
        "pytest-xdist",
        "pytest-html"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        success, _, _ = run_command(f"python -c \"import {package.replace('-', '_')}\"")
        if not success:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Missing packages: {', '.join(missing_packages)}")
        print("Installing missing packages...")
        
        install_cmd = f"pip install {' '.join(missing_packages)}"
        success, stdout, stderr = run_command(install_cmd)
        
        if not success:
            print(f"Failed to install packages: {stderr}")
            return False
    
    print("All dependencies are available")
    return True


def cleanup_test_environment():
    """테스트 환경 정리"""
    print("Cleaning up test environment...")
    
    # 테스트 데이터베이스 파일 정리
    test_db_files = Path("test_data").glob("*.db")
    for db_file in test_db_files:
        db_file.unlink()
    
    # 임시 로그 파일 정리
    temp_log_files = Path("logs").glob("*.tmp")
    for log_file in temp_log_files:
        log_file.unlink()
    
    print("Test environment cleanup complete")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="Run InsiteChart tests")
    
    # 테스트 타입 선택
    parser.add_argument(
        "--type",
        choices=["unit", "integration", "performance", "security", "all"],
        default="all",
        help="Type of tests to run"
    )
    
    # 필터링 옵션
    parser.add_argument(
        "--marker",
        help="Run tests with specific marker"
    )
    
    parser.add_argument(
        "--keyword",
        help="Run tests matching keyword"
    )
    
    parser.add_argument(
        "--failed",
        action="store_true",
        help="Run only failed tests from last run"
    )
    
    # 출력 옵션
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Skip cleanup after tests"
    )
    
    # 환경 옵션
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip dependency check"
    )
    
    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="Skip test environment setup"
    )
    
    args = parser.parse_args()
    
    # 시작 시간 기록
    start_time = datetime.now()
    
    try:
        # 의존성 확인
        if not args.skip_deps:
            if not check_dependencies():
                sys.exit(1)
        
        # 테스트 환경 설정
        if not args.skip_setup:
            setup_test_environment()
        
        # 테스트 실행
        results = {}
        
        if args.type == "unit":
            results['unit'] = run_unit_tests(args)
        elif args.type == "integration":
            results['integration'] = run_integration_tests(args)
        elif args.type == "performance":
            results['performance'] = run_performance_tests(args)
        elif args.type == "security":
            results['security'] = run_security_tests(args)
        elif args.type == "all":
            results = run_all_tests(args)
        
        # 커버리지 보고서 생성
        if args.type == "all":
            generate_coverage_report()
        
        # 테스트 보고서 생성
        print("Generating test reports...")
        success, _, _ = run_command("python scripts/generate_test_report.py")
        
        if not success:
            print("Failed to generate test reports")
        
        # 결과 요약
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "="*50)
        print("TEST EXECUTION SUMMARY")
        print("="*50)
        print(f"Start time: {start_time}")
        print(f"End time: {end_time}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Test type: {args.type}")
        
        if args.type == "all":
            for test_type, success in results.items():
                status = "PASSED" if success else "FAILED"
                print(f"{test_type.capitalize()} tests: {status}")
        else:
            success = list(results.values())[0]
            status = "PASSED" if success else "FAILED"
            print(f"Tests: {status}")
        
        print("="*50)
        
        # 종료 코드 결정
        if args.type == "all":
            # 모든 테스트가 성공해야 성공
            overall_success = all(results.values())
        else:
            # 단일 테스트 타입의 결과에 따라 결정
            overall_success = list(results.values())[0]
        
        if not overall_success:
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error during test execution: {str(e)}")
        sys.exit(1)
    finally:
        # 정리
        if not args.no_cleanup:
            cleanup_test_environment()


if __name__ == "__main__":
    main()