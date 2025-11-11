#!/usr/bin/env python3
"""
테스트 파일의 TestStatus.COMPLETED를 TestStatus.PASSED로 변경하는 스크립트
"""

import os
import re

def fix_test_status_in_file(file_path):
    """파일 내의 TestStatus.COMPLETED를 TestStatus.PASSED로 변경"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # TestStatus.COMPLETED를 TestStatus.PASSED로 변경
        updated_content = re.sub(
            r'TestStatus\.COMPLETED',
            'TestStatus.PASSED',
            content
        )
        
        # TestPriority.MEDIUM를 TestPriority.NORMAL로 변경
        updated_content = re.sub(
            r'TestPriority\.MEDIUM',
            'TestPriority.NORMAL',
            updated_content
        )
        
        if content != updated_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
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
        'tests/unit/services/test_automated_test_service.py',
        'tests/unit/services/test_timescale_service.py',
        'tests/unit/services/test_i18n_service.py'
    ]
    
    print("🔧 테스트 파일 수정 시작...")
    fixed_count = 0
    
    for file_path in test_files:
        if os.path.exists(file_path):
            if fix_test_status_in_file(file_path):
                fixed_count += 1
        else:
            print(f"⚠️ {file_path} 파일을 찾을 수 없습니다.")
    
    print(f"\n✨ 작업 완료! {fixed_count}개 파일이 수정되었습니다.")

if __name__ == "__main__":
    main()