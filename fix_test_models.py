#!/usr/bin/env python3
"""
테스트 파일의 데이터 모델 필드 불일치 문제를 해결하는 스크립트
"""

import os
import re

def fix_test_model_fields(file_path):
    """파일 내의 데이터 모델 필드 불일치 문제 수정"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # TestExecution 필드 수정
        # start_time -> started_at
        content = re.sub(
            r'start_time=datetime\.utcnow\(\)',
            'started_at=datetime.utcnow()',
            content
        )
        
        # end_time -> completed_at
        content = re.sub(
            r'end_time=datetime\.utcnow\(\)',
            'completed_at=datetime.utcnow()',
            content
        )
        
        # TestSuite 필드 수정
        # priority 필드 제거 (TestSuite에 없음)
        content = re.sub(
            r',\s*priority=TestPriority\.\w+',
            '',
            content
        )
        
        # schedule 필드 제거 (TestSuite에 없음)
        content = re.sub(
            r',\s*schedule="[^"]*"',
            '',
            content
        )
        
        # TestReport 필드 수정
        # execution_id -> execution_ids
        content = re.sub(
            r'execution_id="[^"]*"',
            'execution_ids=["test_exec"]',
            content
        )
        
        # TestExecution의 tests_run, tests_passed, tests_failed 필드 제거 (없음)
        content = re.sub(
            r',\s*tests_run=\d+',
            '',
            content
        )
        content = re.sub(
            r',\s*tests_passed=\d+',
            '',
            content
        )
        content = re.sub(
            r',\s*tests_failed=\d+',
            '',
            content
        )
        
        # test_results 필드 타입 수정 (Dict -> List)
        content = re.sub(
            r'test_results=\{[^}]*\}',
            'test_results=[]',
            content
        )
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ {file_path} 파일이 성공적으로 수정되었습니다.")
            return True
        else:
            print(f"ℹ️ {file_path} 파일은 수정할 내용이 없습니다.")
            return False
            
    except Exception as e:
        print(f"❌ {file_path} 파일 처리 중 오류 발생: {e}")
        return False

def main():
    """메인 함수"""
    test_files = [
        'tests/unit/services/test_automated_test_service.py'
    ]
    
    print("🔧 테스트 모델 필드 수정 시작...")
    fixed_count = 0
    
    for file_path in test_files:
        if os.path.exists(file_path):
            if fix_test_model_fields(file_path):
                fixed_count += 1
        else:
            print(f"⚠️ {file_path} 파일을 찾을 수 없습니다.")
    
    print(f"\n✨ 작업 완료! {fixed_count}개 파일이 수정되었습니다.")

if __name__ == "__main__":
    main()