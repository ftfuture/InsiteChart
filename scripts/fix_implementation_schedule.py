#!/usr/bin/env python3
"""
구현 일정 현실화 스크립트
총 기간 19주에서 28주로 수정하고 각 단계별 일정 조정
"""

import os
import re
from pathlib import Path

def fix_implementation_schedule(file_path: str) -> bool:
    """구현 일정 수정"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 총 기간 수정 패턴
        duration_patterns = [
            # 총 19주 -> 총 28주
            (r'총\s*19주', '총 28주'),
            (r'19주.*x.*10인', '28주 x 10인'),
            (r'19주.*10인.*평균', '28주 x 10인 x 평균'),
            
            # Phase 0: 2주 -> 3주
            (r'Phase 0.*준비.*\(2주\)', 'Phase 0: 준비 및 기반 구축 (3주)'),
            (r'#### 4\.1\.1 목표.*\n.*개발 환경 구축.*\n.*프로젝트 구조 설정.*\n.*핵심 라이브러리 및 프레임워크 설치.*\n.*CI/CD 파이프라인 기본 설정', 
             '#### 4.1.1 목표\n- 개발 환경 구축\n- 프로젝트 구조 설정\n- 핵심 라이브러리 및 프레임워크 설치\n- CI/CD 파이프라인 기본 설정\n- 팀 빌딩 및 역할 정의'),
            
            # Phase 1: 4주 -> 6주
            (r'Phase 1.*핵심 데이터 수집.*\(4주\)', 'Phase 1: 핵심 데이터 수집 및 처리 (6주)'),
            
            # Phase 2: 4주 -> 6주
            (r'Phase 2.*핵심 API.*\(4주\)', 'Phase 2: 핵심 API 및 서비스 구현 (6주)'),
            
            # Phase 3: 4주 -> 5주
            (r'Phase 3.*기본 프론트엔드.*\(4주\)', 'Phase 3: 기본 프론트엔드 및 UI 구현 (5주)'),
            
            # Phase 4: 4주 -> 5주
            (r'Phase 4.*고급 분석.*\(4주\)', 'Phase 4: 고급 분석 기능 구현 (5주)'),
            
            # Phase 5: 3주 -> 4주
            (r'Phase 5.*통합.*\(3주\)', 'Phase 5: 통합 및 최적화 (4주)'),
            
            # Phase 6: 2주 -> 3주
            (r'Phase 6.*배포.*\(2주\)', 'Phase 6: 배포 및 운영 준비 (3주)'),
        ]
        
        # 패턴 적용
        for pattern, replacement in duration_patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # 특정 문서에 대한 추가 수정
        if '09-implementation-plan.md' in file_path:
            # 구현 계획 문서의 일정 수정
            if '## 3. 구현 일정' in content:
                # 일정 표 수정
                content = re.sub(
                    r'\|\s*Phase\s*\|\s*기간\s*\|\s*설명\s*\|.*?\|\s*Phase\s*0\s*\|\s*2주\s*\|.*?\|\s*Phase\s*1\s*\|\s*4주\s*\|.*?\|\s*Phase\s*2\s*\|\s*4주\s*\|.*?\|\s*Phase\s*3\s*\|\s*4주\s*\|.*?\|\s*Phase\s*4\s*\|\s*4주\s*\|.*?\|\s*Phase\s*5\s*\|\s*3주\s*\|.*?\|\s*Phase\s*6\s*\|\s*2주\s*\|.*?\|',
                    '''| Phase | 기간 | 설명 |
|-------|------|------|
| Phase 0 | 3주 | 준비 및 기반 구축 |
| Phase 1 | 6주 | 핵심 데이터 수집 및 처리 |
| Phase 2 | 6주 | 핵심 API 및 서비스 구현 |
| Phase 3 | 5주 | 기본 프론트엔드 및 UI 구현 |
| Phase 4 | 5주 | 고급 분석 기능 구현 |
| Phase 5 | 4주 | 통합 및 최적화 |
| Phase 6 | 3주 | 배포 및 운영 준비 |''',
                    content,
                    flags=re.DOTALL
                )
        
        elif '17-final-implementation-roadmap.md' in file_path:
            # 최종 구현 로드맵 문서의 일정 수정
            if '## 5. 상세 일정' in content:
                # 간트 차트 일정 수정
                content = re.sub(
                    r'개발 환경 구축.*:p0-1.*2024-01-01.*1w',
                    '개발 환경 구축           :p0-1, 2024-01-01, 2w',
                    content
                )
                
                content = re.sub(
                    r'프로젝트 구조 설정.*:p0-2.*after p0-1.*1w',
                    '프로젝트 구조 설정        :p0-2, after p0-1, 1w',
                    content
                )
                
                # 각 Phase 기간 수정
                phase_duration_updates = [
                    (r'주식 데이터 수집.*:p1-1.*after p0-2.*2w', '주식 데이터 수집          :p1-1, after p0-2, 3w'),
                    (r'소셜 데이터 수집.*:p1-2.*after p1-1.*2w', '소셜 데이터 수집          :p1-2, after p1-1, 3w'),
                    (r'주식 검색 API.*:p2-1.*after p1-2.*2w', '주식 검색 API             :p2-1, after p1-2, 3w'),
                    (r'센티먼트 분석 API.*:p2-2.*after p2-1.*2w', '센티먼트 분석 API         :p2-2, after p2-1, 3w'),
                    (r'기본 UI 구현.*:p3-1.*after p2-2.*2w', '기본 UI 구현              :p3-1, after p2-2, 3w'),
                    (r'대시보드 구현.*:p3-2.*after p3-1.*2w', '대시보드 구현             :p3-2, after p3-1, 2w'),
                    (r'상관관계 분석.*:p4-1.*after p3-2.*2w', '상관관계 분석             :p4-1, after p3-2, 3w'),
                    (r'실시간 스트리밍.*:p4-2.*after p4-1.*2w', '실시간 스트리밍           :p4-2, after p4-1, 2w'),
                    (r'시스템 통합.*:p5-1.*after p4-2.*2w', '시스템 통합               :p5-1, after p4-2, 3w'),
                    (r'최적화 및 테스트.*:p5-2.*after p5-1.*1w', '최적화 및 테스트          :p5-2, after p5-1, 1w'),
                    (r'프로덕션 배포.*:p6-1.*after p5-2.*1w', '프로덕션 배포             :p6-1, after p5-2, 2w'),
                    (r'운영 준비.*:p6-2.*after p6-1.*1w', '운영 준비                 :p6-2, after p6-1, 1w'),
                ]
                
                for pattern, replacement in phase_duration_updates:
                    content = re.sub(pattern, replacement, content)
            
            # 예산 수정
            if '## 6.3 예산' in content:
                content = re.sub(
                    r'인건비.*\$XXX,XXX.*19주.*10인.*평균 시급',
                    '인건비 | $XXX,XXX | 28주 x 10인 x 평균 시급',
                    content
                )
        
        elif '20-final-spec-improvements.md' in file_path:
            # 최종 스펙 개선 문서의 일정 수정
            if '## 4. 구현 일정 현실화' in content:
                content = re.sub(
                    r'총 기간.*19주.*28주로 확장',
                    '총 기간을 19주에서 28주로 현실화하여 각 단계별 여유 시간 확보',
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
            
            print(f"✅ {file_path} 구현 일정 수정 완료")
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
        "docs/spec/09-implementation-plan.md",
        "docs/spec/17-final-implementation-roadmap.md", 
        "docs/spec/20-final-spec-improvements.md"
    ]
    
    print("🚀 구현 일정 현실화 시작...")
    print("총 기간: 19주 → 28주 (47% 증가)")
    print("각 단계별 여유 시간 확보로 현실적인 일정 조정")
    print("-" * 60)
    
    modified_count = 0
    for file_path in target_files:
        if os.path.exists(file_path):
            if fix_implementation_schedule(file_path):
                modified_count += 1
        else:
            print(f"⚠️ 파일을 찾을 수 없음: {file_path}")
    
    print("-" * 60)
    print(f"📊 수정 완료: {modified_count}/{len(target_files)} 파일")
    
    if modified_count > 0:
        print("✨ 구현 일정 현실화가 완료되었습니다!")
        print("📝 각 단계별 여유 시간이 확보된 현실적인 일정으로 조정되었습니다.")
        print("⏰ Phase별 일정:")
        print("   - Phase 0: 2주 → 3주 (+1주)")
        print("   - Phase 1: 4주 → 6주 (+2주)")
        print("   - Phase 2: 4주 → 6주 (+2주)")
        print("   - Phase 3: 4주 → 5주 (+1주)")
        print("   - Phase 4: 4주 → 5주 (+1주)")
        print("   - Phase 5: 3주 → 4주 (+1주)")
        print("   - Phase 6: 2주 → 3주 (+1주)")
    else:
        print("ℹ️ 수정할 파일이 없습니다.")

if __name__ == "__main__":
    main()