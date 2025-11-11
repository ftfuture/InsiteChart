#!/bin/bash

# InsiteChart 테스트 실행 스크립트
# 이 스크립트는 다양한 테스트 유형을 쉽게 실행할 수 있도록 도와줍니다.

set -e  # 오류 발생 시 즉시 종료

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 도움말 함수
show_help() {
    cat << EOF
InsiteChart 테스트 실행 스크립트

사용법:
    $0 [옵션] [명령어]

명령어:
    unit            단위 테스트 실행
    integration     통합 테스트 실행
    e2e             엔드투엔드 테스트 실행
    performance     성능 테스트 실행
    all             모든 테스트 실행 (기본값)
    lint            코드 린팅 실행
    security        보안 스캔 실행
    coverage        커버리지 보고서만 생성
    clean           테스트 관련 파일 정리

옵션:
    -h, --help              이 도움말 메시지 표시
    -v, --verbose           상세한 출력
    -r, --report            테스트 결과 보고서 생성
    -t, --type TYPE         단위 테스트 세부 유형 (services, cache, models, api)
    --no-coverage           커버리지 보고서 생성 안 함
    --parallel              병렬로 테스트 실행
    --watch                 파일 변경 감지 및 자동 테스트 실행

예시:
    $0 unit --type services    # 서비스 단위 테스트만 실행
    $0 integration --report    # 통합 테스트 실행 및 보고서 생성
    $0 all --verbose           # 모든 테스트를 상세하게 실행
    $0 lint                    # 코드 린팅만 실행
    $0 clean                   # 테스트 관련 파일 정리

EOF
}

# 환경 설정 함수
setup_environment() {
    log_info "테스트 환경 설정 중..."
    
    # Python 가상환경 확인
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        log_warning "가상환경이 활성화되어 있지 않습니다. 가상환경을 활성화해주세요."
    fi
    
    # 필요한 디렉토리 생성
    mkdir -p logs test_data test_reports htmlcov reports
    
    # 환경 변수 설정
    export TESTING=true
    export LOG_LEVEL=DEBUG
    
    log_success "테스트 환경 설정 완료"
}

# 테스트 정리 함수
clean_tests() {
    log_info "테스트 관련 파일 정리 중..."
    
    # 테스트 결과 파일 정리
    find . -name "*.pyc" -delete
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name ".coverage" -delete 2>/dev/null || true
    find . -name "coverage.xml" -delete 2>/dev/null || true
    
    # 보고서 디렉토리 정리
    rm -rf htmlcov/
    rm -rf test_reports/
    rm -rf reports/
    
    # 로그 파일 정리
    rm -f logs/test_*.log
    
    log_success "테스트 관련 파일 정리 완료"
}

# 의존성 설치 함수
install_dependencies() {
    log_info "테스트 의존성 설치 중..."
    
    # Python 테스트 의존성 설치
    pip install pytest pytest-asyncio pytest-cov pytest-mock pytest-xdist
    pip install pytest-html pytest-json-report
    pip install coverage
    pip install flake8 black isort mypy
    pip install bandit safety
    pip install locust
    
    log_success "테스트 의존성 설치 완료"
}

# 테스트 실행 함수
run_tests() {
    local command=$1
    local type=$2
    local verbose=$3
    local report=$4
    local coverage=$5
    local parallel=$6
    
    log_info "$command 테스트 실행 중..."
    
    # 기본 명령어 구성
    local cmd="python run_enhanced_tests.py $command"
    
    # 옵션 추가
    if [[ "$type" != "" ]]; then
        cmd="$cmd --type $type"
    fi
    
    if [[ "$verbose" == "true" ]]; then
        cmd="$cmd --verbose"
    fi
    
    if [[ "$report" == "true" ]]; then
        cmd="$cmd --report"
    fi
    
    if [[ "$coverage" == "true" ]]; then
        cmd="$cmd --coverage"
    fi
    
    if [[ "$parallel" == "true" ]]; then
        cmd="$cmd --parallel"
    fi
    
    # 명령어 실행
    eval $cmd
    
    if [[ $? -eq 0 ]]; then
        log_success "$command 테스트가 성공적으로 완료되었습니다."
        
        # 커버리지 보고서가 있는 경우 열기
        if [[ "$coverage" == "true" ]] && [[ -f "htmlcov/index.html" ]]; then
            log_info "커버리지 보고서: htmlcov/index.html"
        fi
    else
        log_error "$command 테스트가 실패했습니다."
        exit 1
    fi
}

# 파일 감지 테스트 함수
watch_tests() {
    log_info "파일 변경 감지 모드로 테스트 실행 중..."
    log_info "Ctrl+C를 눌러 종료하세요."
    
    # watchdog 설치 확인
    if ! python -c "import watchdog" 2>/dev/null; then
        log_info "watchdog 설치 중..."
        pip install watchdog
    fi
    
    # 파일 변경 감지 및 테스트 실행
    python -c "
import time
import subprocess
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class TestHandler(FileSystemEventHandler):
    def __init__(self, command):
        self.command = command
        self.last_run = 0
        
    def on_modified(self, event):
        if event.is_directory:
            return
            
        # Python 파일만 감지
        if not event.src_path.endswith('.py'):
            return
            
        # 너무 잦은 실행 방지
        current_time = time.time()
        if current_time - self.last_run < 2:
            return
            
        self.last_run = current_time
        print(f'\\n파일 변경 감지: {event.src_path}')
        print('테스트 실행 중...')
        
        try:
            result = subprocess.run(self.command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                print('✅ 테스트 통과')
            else:
                print('❌ 테스트 실패')
                print(result.stderr)
        except Exception as e:
            print(f'오류: {e}')

if __name__ == '__main__':
    command = 'python run_enhanced_tests.py unit --type services'
    event_handler = TestHandler(command)
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
"
}

# 메인 함수
main() {
    local command="all"
    local type=""
    local verbose="false"
    local report="false"
    local coverage="true"
    local parallel="false"
    local watch_mode="false"
    local clean_only="false"
    local install_deps="false"
    
    # 인자 파싱
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                verbose="true"
                shift
                ;;
            -r|--report)
                report="true"
                shift
                ;;
            -t|--type)
                type="$2"
                shift 2
                ;;
            --no-coverage)
                coverage="false"
                shift
                ;;
            --parallel)
                parallel="true"
                shift
                ;;
            --watch)
                watch_mode="true"
                shift
                ;;
            clean)
                clean_only="true"
                shift
                ;;
            install)
                install_deps="true"
                shift
                ;;
            unit|integration|e2e|performance|all|lint|security|coverage)
                command="$1"
                shift
                ;;
            *)
                log_error "알 수 없는 옵션: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 정리 모드
    if [[ "$clean_only" == "true" ]]; then
        clean_tests
        exit 0
    fi
    
    # 의존성 설치 모드
    if [[ "$install_deps" == "true" ]]; then
        install_dependencies
        exit 0
    fi
    
    # 파일 감지 모드
    if [[ "$watch_mode" == "true" ]]; then
        setup_environment
        watch_tests
        exit 0
    fi
    
    # 환경 설정
    setup_environment
    
    # 테스트 실행
    run_tests "$command" "$type" "$verbose" "$report" "$coverage" "$parallel"
    
    log_success "모든 작업이 완료되었습니다."
}

# 스크립트 실행
main "$@"