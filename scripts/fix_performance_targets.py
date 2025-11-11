#!/usr/bin/env python3
"""
성능 목표 재설정 스크립트
MVP: 1000ms, 베타: 700ms, 정식: 500ms 단계별 성능 목표 적용
"""

import os
import re
from pathlib import Path

def fix_performance_targets(file_path: str) -> bool:
    """성능 목표 수정"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 단계별 성능 목표 패턴
        performance_patterns = [
            # API 응답 시간 목표
            (r'API 응답 시간[:\s]*([0-9]+)ms', 
             'API 응답 시간: **단계별 목표**\n- MVP: 1000ms\n- 베타: 700ms\n- 정식: 500ms'),
            
            # 응답 시간 관련 목표
            (r'응답 시간[:\s]*([0-9]+)ms', 
             '응답 시간: **단계별 목표**\n- MVP: 1000ms\n- 베타: 700ms\n- 정식: 500ms'),
            
            # 처리 시간 관련 목표
            (r'처리 시간[:\s]*([0-9]+)ms', 
             '처리 시간: **단계별 목표**\n- MVP: 1000ms\n- 베타: 700ms\n- 정식: 500ms'),
            
            # 95% 요청 응답 시간
            (r'95%.*요청.*([0-9]+)ms', 
             '95% 요청: **단계별 목표**\n- MVP: 1000ms\n- 베타: 700ms\n- 정식: 500ms'),
            
            # API 응답 시간 200ms 이하 (단일 목표)
            (r'API 응답 시간.*200ms.*이하', 
             'API 응답 시간: **단계별 목표**\n- MVP: 1000ms\n- 베타: 700ms\n- 정식: 500ms'),
        ]
        
        # 패턴 적용
        for pattern, replacement in performance_patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # 특정 문서에 대한 추가 수정
        if '04-performance-scalability.md' in file_path:
            # 성능 목표 섹션 추가
            if '## 성능 목표' not in content:
                # 문서 시작 부분에 성능 목표 섹션 추가
                lines = content.split('\n')
                insert_index = 2  # 제목 다음에 삽입
                
                performance_goals_section = """## 성능 목표

### 단계별 성능 목표
- **MVP 단계**: API 응답 시간 1000ms 이하
- **베타 단계**: API 응답 시간 700ms 이하  
- **정식 버전**: API 응답 시간 500ms 이하

### 세부 성능 지표
- **API 응답 시간**: 95%의 요청이 단계별 목표 시간 내 응답
- **데이터베이스 쿼리**: 95%의 쿼리가 200ms 이내 완료
- **캐시 응답 시간**: 95%의 캐시 요청이 50ms 이내 응답
- **외부 API 호출**: 95%의 외부 API 호출이 300ms 이내 완료

"""
                
                lines.insert(insert_index, performance_goals_section)
                content = '\n'.join(lines)
        
        elif '12-api-gateway-routing.md' in file_path:
            # API 게이트웨이 성능 목표 수정
            if '## 6. 성공 지표' in content:
                # 성공 지표 섹션의 성능 관련 부분 수정
                content = re.sub(
                    r'API 응답 시간[:\s]*95%.*요청.*200ms.*이내',
                    'API 응답 시간: **단계별 목표**\n- MVP: 95% 요청 1000ms 이내\n- 베타: 95% 요청 700ms 이내\n- 정식: 95% 요청 500ms 이내',
                    content
                )
        
        elif '17-final-implementation-roadmap.md' in file_path:
            # 구현 로드맵 성능 목표 수정
            if '## 7.2.1 기술적 지표' in content:
                # 기술적 지표 섹션의 성능 부분 수정
                content = re.sub(
                    r'- \*\*성능\*\*: API 응답 시간 200ms 이하',
                    '- **성능**: API 응답 시간 **단계별 목표**\n  - MVP: 1000ms 이하\n  - 베타: 700ms 이하\n  - 정식: 500ms 이하',
                    content
                )
        
        # 변경된 내용이 있으면 파일 저장
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 백업 파일 생성
            backup_path = file_path + '.backup'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            print(f"✅ {file_path} 성능 목표 수정 완료")
            return True
        else:
            print(f"ℹ️ {file_path} 수정할 내용 없음")
            return False
            
    except Exception as e:
        print(f"❌ {file_path} 수정 중 오류: {str(e)}")
        return False

def main():
    """메인 함수"""
    target_files = [
        "docs/spec/04-performance-scalability.md",
        "docs/spec/12-api-gateway-routing.md", 
        "docs/spec/17-final-implementation-roadmap.md"
    ]
    
    print("🚀 성능 목표 재설정 시작...")
    print("단계별 성능 목표: MVP(1000ms) → 베타(700ms) → 정식(500ms)")
    print("-" * 60)
    
    modified_count = 0
    for file_path in target_files:
        if os.path.exists(file_path):
            if fix_performance_targets(file_path):
                modified_count += 1
        else:
            print(f"⚠️ 파일을 찾을 수 없음: {file_path}")
    
    print("-" * 60)
    print(f"📊 수정 완료: {modified_count}/{len(target_files)} 파일")
    
    if modified_count > 0:
        print("✨ 성능 목표 재설정이 완료되었습니다!")
        print("📝 각 단계별 현실적인 성능 목표가 설정되었습니다.")
    else:
        print("ℹ️ 수정할 파일이 없습니다.")

if __name__ == "__main__":
    main()