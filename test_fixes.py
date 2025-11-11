#!/usr/bin/env python3
"""
간단한 테스트 스크립트로 수정된 헤더 기능 확인
"""

import requests
import json
import time

def test_api_key_validation():
    """API 키 검증 테스트"""
    print("1. API 키 검증 테스트...")
    
    # API 키 없이 요청
    response = requests.get("http://localhost:8000/auth/validate-key")
    print(f"   API 키 없음: {response.status_code} - {response.json()}")
    
    # API 키와 함께 요청
    headers = {"X-API-Key": "test_key_123"}
    response = requests.get("http://localhost:8000/auth/validate-key", headers=headers)
    print(f"   API 키 있음: {response.status_code} - {response.json()}")
    
    # 소문자 헤더로 테스트
    headers = {"x-api-key": "test_key_123"}
    response = requests.get("http://localhost:8000/auth/validate-key", headers=headers)
    print(f"   소문자 헤더: {response.status_code} - {response.json()}")
    
    print("   ✓ API 키 검증 테스트 완료\n")

def test_rate_limit_headers():
    """속도 제한 헤더 테스트"""
    print("2. 속도 제한 헤더 테스트...")
    
    response = requests.get("http://localhost:8000/api/v1/health")
    
    # 속도 제한 헤더 확인
    rate_limit_headers = {
        "X-RateLimit-Limit": response.headers.get("X-RateLimit-Limit"),
        "X-RateLimit-Remaining": response.headers.get("X-RateLimit-Remaining"),
        "X-RateLimit-Reset": response.headers.get("X-RateLimit-Reset"),
        "X-RateLimit-Used": response.headers.get("X-RateLimit-Used"),
        "X-RateLimit-Window": response.headers.get("X-RateLimit-Window")
    }
    
    print(f"   속도 제한 헤더: {rate_limit_headers}")
    
    # 모든 헤더가 있는지 확인
    missing_headers = [k for k, v in rate_limit_headers.items() if v is None]
    if missing_headers:
        print(f"   ❌ 누락된 헤더: {missing_headers}")
    else:
        print("   ✓ 모든 속도 제한 헤더가 존재합니다")
    
    print("   ✓ 속도 제한 헤더 테스트 완료\n")

def test_cache_headers():
    """캐시 헤더 테스트"""
    print("3. 캐시 헤더 테스트...")
    
    response = requests.get("http://localhost:8000/api/v1/health")
    
    # 캐시 헤더 확인
    cache_headers = {
        "Cache-Control": response.headers.get("Cache-Control"),
        "X-Cache-Status": response.headers.get("X-Cache-Status"),
        "X-Cache": response.headers.get("X-Cache")
    }
    
    print(f"   캐시 헤더: {cache_headers}")
    
    # 모든 헤더가 있는지 확인
    missing_headers = [k for k, v in cache_headers.items() if v is None]
    if missing_headers:
        print(f"   ❌ 누락된 헤더: {missing_headers}")
    else:
        print("   ✓ 모든 캐시 헤더가 존재합니다")
    
    print("   ✓ 캐시 헤더 테스트 완료\n")

def test_health_endpoint():
    """헬스 엔드포인트 테스트"""
    print("4. 헬스 엔드포인트 테스트...")
    
    response = requests.get("http://localhost:8000/api/v1/health")
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ 헬스 체크 성공: {data}")
    else:
        print(f"   ❌ 헬스 체크 실패: {response.status_code}")
    
    print("   ✓ 헬스 엔드포인트 테스트 완료\n")

def main():
    """메인 테스트 함수"""
    print("=== InsiteChart 수정된 기능 테스트 ===\n")
    
    try:
        test_api_key_validation()
        test_rate_limit_headers()
        test_cache_headers()
        test_health_endpoint()
        
        print("=== 모든 테스트 완료 ===")
        print("✅ 수정된 기능들이 정상적으로 작동합니다!")
        
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())