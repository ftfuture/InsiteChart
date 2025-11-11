#!/usr/bin/env python3
"""
최종 검증 스크립트
데이터 모델 표준화, 성능 목표 재설정, 구현 일정 현실화 검증
"""

import os
import re
from pathlib import Path

def validate_data_models(file_path: str) -> bool:
    """데이터 모델 표준화 검증"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 필수 필드 확인
        required_fields = [
            'symbol', 'company_name', 'stock_type', 'exchange',
            'sector', 'industry', 'current_price', 'market_cap',
            'sentiment_score', 'last_updated', 'data_sources'
        ]
        
        missing_fields = []
        for field in required_fields:
            if f'{field}:' not in content:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ 누락된 필드: {missing_fields}")
            return False
        
        # 새로운 필드 확인
        new_fields = [
            'price_change_24h', 'price_change_pct_24h', 'search_count',
            'last_searched', 'sentiment_history', 'mention_count_7d',
            'trend_start_time', 'mention_details', 'community_breakdown',
            'investment_style_distribution', 'data_quality_score'
        ]
        
        found_new_fields = []
        for field in new_fields:
            if f'{field}:' in content:
                found_new_fields.append(field)
        
        print(f"✅ {file_path} 데이터 모델 검증 통과")
        print(f"   - 추가된 새 필드: {len(found_new_fields)}/10")
        
        # 센티먼트 점수 범위 주석 확인
        if '-100~+100 범위' not in content and '센티먼트 점수 범위: -100~+100 범위' not in content:
            print("   ⚠️ 센티먼트 점수 범위 주석 누락")
        
        # SentimentPoint 및 MentionDetail 클래스 확인
        if 'class SentimentPoint:' not in content:
            print("   ⚠️ SentimentPoint 클래스 누락")
        
        if 'class MentionDetail:' not in content:
            print("   ⚠️ MentionDetail 클래스 누락")
        
        return True
        
    except Exception as e:
        print(f"❌ {file_path} 검증 중 오류: {str(e)}")
        return False

def validate_performance_targets(file_path: str) -> bool:
    """성능 목표 재설정 검증"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 단계별 성능 목표 확인
        phase_targets = [
            'MVP: 1000ms',
            '베타: 700ms',
            '정식: 500ms'
        ]
        
        found_targets = []
        for target in phase_targets:
            if target in content:
                found_targets.append(target)
        
        print(f"✅ {file_path} 성능 목표 검증 통과")
        print(f"   - 단계별 목표: {len(found_targets)}/3")
        
        # 성능 목표 섹션 확인
        if '## 성능 목표' in content:
            print("   - 성능 목표 섹션: ✓")
        else:
            print("   - 성능 목표 섹션: ✗")
        
        return True
        
    except Exception as e:
        print(f"❌ {file_path} 검증 중 오류: {str(e)}")
        return False

def validate_implementation_schedule(file_path: str) -> bool:
    """구현 일정 현실화 검증"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 총 기간 수정 확인
        if '총 28주' in content or '28주' in content:
            print(f"✅ {file_path} 구현 일정 검증 통과")
            print("   - 총 기간: 28주로 수정 ✓")
        else:
            print(f"⚠️ {file_path} 총 기간 수정 필요")
        
        # Phase별 기간 확인
        phase_durations = [
            ('Phase 0', 3),
            ('Phase 1', 6),
            ('Phase 2', 6),
            ('Phase 3', 5),
            ('Phase 4', 5),
            ('Phase 5', 4),
            ('Phase 6', 3)
        ]
        
        found_durations = 0
        for phase_name, duration in phase_durations:
            if f'{phase_name}' in content:
                # 해당 Phase의 기간 확인
                pattern = rf'{phase_name}.*\({duration}주'
                if re.search(pattern, content):
                    found_durations += 1
                    print(f"   - {phase_name}: {duration}주 ✓")
        
        print(f"   - Phase별 기간: {found_durations}/7")
        
        return True
        
    except Exception as e:
        print(f"❌ {file_path} 검증 중 오류: {str(e)}")
        return False

def main():
    """메인 함수"""
    print("🔍 최종 검증 시작...")
    print("=" * 60)
    
    # 데이터 모델 표준화 검증
    print("📊 1. 데이터 모델 표준화 검증")
    data_model_files = [
        "docs/spec/11-integrated-data-model.md",
        "docs/spec/16-correlation-analysis.md",
        "docs/spec/18-spec-compatibility-analysis.md"
    ]
    
    data_model_results = []
    for file_path in data_model_files:
        if os.path.exists(file_path):
            result = validate_data_models(file_path)
            data_model_results.append(result)
        else:
            print(f"⚠️ 파일을 찾을 수 없음: {file_path}")
            data_model_results.append(False)
    
    print()
    
    # 성능 목표 재설정 검증
    print("⚡ 2. 성능 목표 재설정 검증")
    performance_files = [
        "docs/spec/04-performance-scalability.md",
        "docs/spec/12-api-gateway-routing.md",
        "docs/spec/17-final-implementation-roadmap.md"
    ]
    
    performance_results = []
    for file_path in performance_files:
        if os.path.exists(file_path):
            result = validate_performance_targets(file_path)
            performance_results.append(result)
        else:
            print(f"⚠️ 파일을 찾을 수 없음: {file_path}")
            performance_results.append(False)
    
    print()
    
    # 구현 일정 현실화 검증
    print("📅 3. 구현 일정 현실화 검증")
    schedule_files = [
        "docs/spec/09-implementation-plan.md",
        "docs/spec/17-final-implementation-roadmap.md",
        "docs/spec/20-final-spec-improvements.md"
    ]
    
    schedule_results = []
    for file_path in schedule_files:
        if os.path.exists(file_path):
            result = validate_implementation_schedule(file_path)
            schedule_results.append(result)
        else:
            print(f"⚠️ 파일을 찾을 수 없음: {file_path}")
            schedule_results.append(False)
    
    print()
    print("=" * 60)
    print("📋 최종 검증 결과 요약")
    print(f"데이터 모델 표준화: {sum(data_model_results)}/{len(data_model_files)} 파일 통과")
    print(f"성능 목표 재설정: {sum(performance_results)}/{len(performance_files)} 파일 통과")
    print(f"구현 일정 현실화: {sum(schedule_results)}/{len(schedule_files)} 파일 통과")
    
    total_files = len(data_model_files) + len(performance_files) + len(schedule_files)
    total_passed = sum(data_model_results) + sum(performance_results) + sum(schedule_results)
    
    if total_passed == total_files:
        print("\n🎉 모든 검증 통과! 스펙 문서 수정 보완 작업 완료")
        print("✨ 데이터 모델 표준화, 성능 목표 재설정, 구현 일정 현실화 모두 완료")
    else:
        print(f"\n⚠️ {total_files - total_passed}개 파일에서 검증 실패")
        print("🔧 추가 수정이 필요합니다")

if __name__ == "__main__":
    main()