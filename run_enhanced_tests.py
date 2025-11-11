"""
향상된 테스트 실행 스크립트

이 스크립트는 새로운 테스트 구조를 지원하며,
단위 테스트, 통합 테스트, 성능 테스트를 분리하여 실행합니다.
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path
import json
from typing import Dict, List, Any


def run_command(command: str, description: str, cwd: str = None) -> bool:
    """명령어 실행 및 결과 처리"""
    print(f"\n{'='*60}")
    print(f"실행: {description}")
    print(f"명령어: {command}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd
        )
        
        if result.stdout:
            print("STDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        success = result.returncode == 0
        if success:
            print(f"✅ 성공: {description}")
        else:
            print(f"❌ 실패: {description} (종료 코드: {result.returncode})")
        
        return success
        
    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        return False


def setup_test_environment():
    """테스트 환경 설정"""
    print("테스트 환경 설정 중...")
    
    # 환경 변수 설정
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    # 필요한 디렉토리 생성
    dirs_to_create = [
        "logs",
        "test_data", 
        "test_reports",
        "htmlcov",
        "reports"
    ]
    
    for dir_name in dirs_to_create:
        Path(dir_name).mkdir(exist_ok=True)
    
    print("✅ 테스트 환경 설정 완료")
    return True


def run_unit_tests(test_type: str = None) -> bool:
    """단위 테스트 실행"""
    print("\n🧪 단위 테스트 실행 중...")
    
    success = True
    
    # 서비스 테스트
    if not test_type or test_type in ["services", "all"]:
        print("\n📦 서비스 테스트 실행...")
        success &= run_command(
            "python -m pytest tests/unit/services/ -v --cov=backend.services --cov-report=html --cov-report=term-missing",
            "서비스 단위 테스트",
            cwd="."
        )
    
    # 캐시 테스트
    if not test_type or test_type in ["cache", "all"]:
        print("\n💾 캐시 테스트 실행...")
        success &= run_command(
            "python -m pytest tests/unit/cache/ -v --cov=backend.cache --cov-report=html --cov-report=term-missing",
            "캐시 단위 테스트",
            cwd="."
        )
    
    # 모델 테스트
    if not test_type or test_type in ["models", "all"]:
        print("\n📊 모델 테스트 실행...")
        success &= run_command(
            "python -m pytest tests/unit/models/ -v --cov=backend.models --cov-report=html --cov-report=term-missing",
            "모델 단위 테스트",
            cwd="."
        )
    
    # API 테스트
    if not test_type or test_type in ["api", "all"]:
        print("\n🌐 API 테스트 실행...")
        success &= run_command(
            "python -m pytest tests/unit/api/ -v --cov=backend.api --cov-report=html --cov-report=term-missing",
            "API 단위 테스트",
            cwd="."
        )
    
    return success


def run_integration_tests() -> bool:
    """통합 테스트 실행"""
    print("\n🔗 통합 테스트 실행 중...")
    
    success = True
    
    # API 통합 테스트
    success &= run_command(
        "python -m pytest tests/integration/api/ -v --cov=backend.api --cov-report=html --cov-report=term-missing",
        "API 통합 테스트",
        cwd="."
    )
    
    # 데이터베이스 통합 테스트
    success &= run_command(
        "python -m pytest tests/integration/database/ -v --cov=backend.database --cov-report=html --cov-report=term-missing",
        "데이터베이스 통합 테스트",
        cwd="."
    )
    
    # 기존 통합 테스트 (호환성)
    success &= run_command(
        "python -m pytest tests/test_integration.py -v --cov=backend --cov-report=html --cov-report=term-missing",
        "기존 통합 테스트",
        cwd="."
    )
    
    return success


def run_e2e_tests() -> bool:
    """엔드투엔드 테스트 실행"""
    print("\n🎭 엔드투엔드 테스트 실행 중...")
    
    success = run_command(
        "python -m pytest tests/e2e/ -v --cov=backend --cov-report=html --cov-report=term-missing",
        "엔드투엔드 테스트",
        cwd="."
    )
    
    return success


def run_performance_tests() -> bool:
    """성능 테스트 실행"""
    print("\n⚡ 성능 테스트 실행 중...")
    
    success = True
    
    # 부하 테스트
    success &= run_command(
        "python -m pytest tests/performance/ -v --junitxml=reports/performance-results.xml",
        "성능 테스트",
        cwd="."
    )
    
    return success


def run_linting() -> bool:
    """코드 린팅 실행"""
    print("\n🔍 코드 린팅 실행 중...")
    
    success = True
    
    # Python 코드 스타일 체크
    success &= run_command(
        "flake8 backend/ frontend/ tests/ --max-line-length=100 --ignore=E203,W503 --extend-ignore=E501",
        "Python 코드 스타일 체크",
        cwd="."
    )
    
    # 임포트 정렬 체크
    success &= run_command(
        "isort --check-only backend/ frontend/ tests/",
        "임포트 정렬 체크",
        cwd="."
    )
    
    # 코드 포맷 체크
    success &= run_command(
        "black --check backend/ frontend/ tests/",
        "코드 포맷 체크",
        cwd="."
    )
    
    # 타입 체크
    success &= run_command(
        "mypy backend/ --ignore-missing-imports",
        "타입 체크",
        cwd="."
    )
    
    return success


def run_security_scan() -> bool:
    """보안 스캔 실행"""
    print("\n🔒 보안 스캔 실행 중...")
    
    success = True
    
    # Bandit 보안 스캔
    success &= run_command(
        "bandit -r backend/ -f json -o test_reports/security-report.json",
        "Bandit 보안 스캔",
        cwd="."
    )
    
    # 의존성 취약점 체크
    success &= run_command(
        "safety check --json --output test_reports/safety-report.json",
        "의존성 취약점 체크",
        cwd="."
    )
    
    return success


def generate_test_report(results: Dict[str, Any]) -> str:
    """테스트 결과 보고서 생성"""
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_tests": results.get("total_tests", 0),
            "passed_tests": results.get("passed_tests", 0),
            "failed_tests": results.get("failed_tests", 0),
            "success_rate": results.get("success_rate", 0)
        },
        "details": results.get("details", {}),
        "coverage": results.get("coverage", {}),
        "recommendations": results.get("recommendations", [])
    }
    
    return json.dumps(report, indent=2, ensure_ascii=False)


def calculate_coverage() -> Dict[str, Any]:
    """커버리지 계산"""
    try:
        # coverage.xml 파일 읽기
        with open("coverage.xml", "r") as f:
            content = f.read()
        
        # 간단한 XML 파싱 (실제로는 xml.etree 사용 권장)
        import re
        lines_covered = len(re.findall(r'line-covered="(\d+)"', content))
        lines_valid = len(re.findall(r'lines-valid="(\d+)"', content))
        branch_covered = len(re.findall(r'branch-covered="(\d+)"', content))
        branch_valid = len(re.findall(r'branches-valid="(\d+)"', content))
        
        line_coverage = (lines_covered / lines_valid * 100) if lines_valid > 0 else 0
        branch_coverage = (branch_covered / branch_valid * 100) if branch_valid > 0 else 0
        
        return {
            "line_coverage": round(line_coverage, 2),
            "branch_coverage": round(branch_coverage, 2),
            "lines_covered": lines_covered,
            "lines_valid": lines_valid,
            "branch_covered": branch_covered,
            "branch_valid": branch_valid
        }
        
    except Exception as e:
        print(f"커버리지 계산 오류: {str(e)}")
        return {
            "line_coverage": 0,
            "branch_coverage": 0,
            "error": str(e)
        }


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="향상된 InsiteChart 테스트 실행기")
    parser.add_argument(
        "command",
        choices=["unit", "integration", "e2e", "performance", "all", "lint", "security"],
        help="실행할 테스트 유형"
    )
    parser.add_argument(
        "--type",
        choices=["services", "cache", "models", "api"],
        help="단위 테스트 세부 유형"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="커버리지 보고서 생성"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="테스트 결과 보고서 생성"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="상세한 출력"
    )
    
    args = parser.parse_args()
    
    # 테스트 환경 설정
    if not setup_test_environment():
        sys.exit(1)
    
    start_time = time.time()
    results = {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "details": {},
        "recommendations": []
    }
    
    try:
        # 테스트 실행
        success = True
        
        if args.command == "unit":
            success = run_unit_tests(args.type)
        elif args.command == "integration":
            success = run_integration_tests()
        elif args.command == "e2e":
            success = run_e2e_tests()
        elif args.command == "performance":
            success = run_performance_tests()
        elif args.command == "all":
            success = run_unit_tests()
            success &= run_integration_tests()
            success &= run_e2e_tests()
            success &= run_performance_tests()
        elif args.command == "lint":
            success = run_linting()
        elif args.command == "security":
            success = run_security_scan()
        
        # 커버리지 계산
        if args.coverage or args.command in ["unit", "integration", "e2e", "performance", "all"]:
            coverage_data = calculate_coverage()
            results["coverage"] = coverage_data
            
            if coverage_data.get("line_coverage", 0) < 30:
                results["recommendations"].append("단위 테스트 커버리지를 30% 이상으로 향상시켜주세요.")
            if coverage_data.get("branch_coverage", 0) < 25:
                results["recommendations"].append("분기 커버리지를 25% 이상으로 향상시켜주세요.")
        
        # 결과 요약
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n{'='*60}")
        print(f"테스트 완료 (소요 시간: {duration:.2f}초)")
        print(f"{'='*60}")
        
        if success:
            print("✅ 모든 테스트가 성공적으로 완료되었습니다.")
        else:
            print("❌ 일부 테스트가 실패했습니다.")
            sys.exit(1)
        
        # 보고서 생성
        if args.report:
            report_file = "test_reports/enhanced_test_report.json"
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(generate_test_report(results))
            
            print(f"📊 테스트 보고서가 저장되었습니다: {report_file}")
        
    except KeyboardInterrupt:
        print("\n⚠️ 테스트가 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 테스트 실행 중 오류 발생: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()