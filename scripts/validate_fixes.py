#!/usr/bin/env python3
"""
수정 내용 검증 스크립트
"""

import os
import re
from pathlib import Path

def validate_unified_stock_data(file_path: str) -> bool:
    """UnifiedStockData 모델 검증"""
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
        print(f"누락된 필드: {missing_fields}")
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
    
    print(f"추가된 새 필드: {found_new_fields}")
    
    # 센티먼트 점수 범위 주석 확인
    if '-100~+100 범위' not in content and '-100~+100 범위' not in content:
        print("경고: 센티먼트 점수 범위 주석을 추가하세요")
        return False
    
    # SentimentPoint 및 MentionDetail 클래스 확인
    if 'class SentimentPoint:' not in content:
        print("경고: SentimentPoint 클래스가 없습니다")
        return False
    
    if 'class MentionDetail:' not in content:
        print("경고: MentionDetail 클래스가 없습니다")
        return False
    
    print(f"✅ {file_path} 검증 통과")
    return True

if __name__ == "__main__":
    target_files = [
        "docs/spec/11-integrated-data-model.md",
        "docs/spec/16-correlation-analysis.md",
        "docs/spec/18-spec-compatibility-analysis.md"
    ]
    
    all_valid = True
    for file_path in target_files:
        if os.path.exists(file_path):
            if not validate_unified_stock_data(file_path):
                all_valid = False
        else:
            print(f"파일을 찾을 수 없음: {file_path}")
            all_valid = False
    
    if all_valid:
        print("🎉 모든 파일 검증 통과!")
    else:
        print("❌ 검증 실패: 수정이 필요합니다")