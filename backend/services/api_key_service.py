"""
API 키 관리 서비스 모듈
API 키 생성, 검증, 관리 및 권한 부여 기능 제공
"""

import secrets
import hashlib
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import redis.asyncio as redis
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class APIKeyInfo:
    """API 키 정보 데이터 클래스"""
    api_key: str
    key_id: str
    user_id: str
    name: str
    permissions: List[str]
    created_at: str
    expires_at: str
    last_used: Optional[str] = None
    usage_count: int = 0
    is_active: bool = True
    rate_limit: int = 1000  # 시간당 요청 제한
    tier: str = "basic"  # basic, premium, enterprise

@dataclass
class APIKeyUsage:
    """API 키 사용량 정보"""
    api_key: str
    timestamp: str
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float

class APIKeyService:
    """API 키 관리 서비스 클래스"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.key_prefix = "insitechart:api_keys:"
        self.usage_prefix = "insitechart:api_usage:"
        
        # 기본 권한 정의
        self.default_permissions = {
            "basic": ["stock:read", "search:read"],
            "premium": ["stock:read", "search:read", "sentiment:read", "realtime:read"],
            "enterprise": ["stock:read", "search:read", "sentiment:read", "realtime:read", "admin:read"]
        }
        
        # 티어별 속도 제한
        self.tier_rate_limits = {
            "basic": 1000,      # 시간당 1000 요청
            "premium": 5000,    # 시간당 5000 요청
            "enterprise": 20000 # 시간당 20000 요청
        }
    
    async def initialize(self):
        """Redis 클라이언트 초기화"""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("API Key Service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize API Key Service: {str(e)}")
            raise
    
    async def generate_api_key(
        self, 
        user_id: str, 
        name: str, 
        tier: str = "basic",
        custom_permissions: Optional[List[str]] = None,
        expires_in_days: int = 365
    ) -> str:
        """
        API 키 생성
        
        Args:
            user_id: 사용자 ID
            name: API 키 이름
            tier: 티어 (basic, premium, enterprise)
            custom_permissions: 사용자 정의 권한 목록
            expires_in_days: 만료일수
            
        Returns:
            생성된 API 키
            
        Raises:
            ValueError: 유효하지 않은 파라미터
        """
        if tier not in self.default_permissions:
            raise ValueError(f"Invalid tier: {tier}")
        
        # 고유 키 ID 생성
        key_id = secrets.token_urlsafe(16)
        
        # API 키 생성 (ic_ 접두사 추가)
        api_key = f"ic_{secrets.token_urlsafe(32)}"
        
        # 권한 설정
        permissions = custom_permissions or self.default_permissions[tier]
        
        # 만료 시간 설정
        expires_at = (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()
        created_at = datetime.utcnow().isoformat()
        
        # API 키 정보 생성
        key_info = APIKeyInfo(
            api_key=api_key,
            key_id=key_id,
            user_id=user_id,
            name=name,
            permissions=permissions,
            created_at=created_at,
            expires_at=expires_at,
            rate_limit=self.tier_rate_limits[tier],
            tier=tier
        )
        
        try:
            # Redis에 API 키 정보 저장
            await self._store_key_info(key_info)
            
            # 사용자 API 키 목록에 추가
            await self.redis_client.sadd(
                f"{self.key_prefix}user:{user_id}",
                api_key
            )
            
            logger.info(f"API key generated for user {user_id}: {key_id}")
            return api_key
            
        except Exception as e:
            logger.error(f"Failed to generate API key: {str(e)}")
            raise
    
    async def validate_api_key(self, api_key: str) -> Optional[APIKeyInfo]:
        """
        API 키 검증
        
        Args:
            api_key: 검증할 API 키
            
        Returns:
            API 키 정보 또는 None
        """
        try:
            # API 키 정보 조회
            key_info = await self._get_key_info(api_key)
            
            if not key_info:
                logger.warning(f"Invalid API key: {api_key[:10]}...")
                return None
            
            # 활성 상태 확인
            if not key_info.is_active:
                logger.warning(f"Inactive API key: {key_info.key_id}")
                return None
            
            # 만료 확인
            expires_at = datetime.fromisoformat(key_info.expires_at)
            if datetime.utcnow() > expires_at:
                logger.warning(f"Expired API key: {key_info.key_id}")
                return None
            
            # 사용량 업데이트
            await self._update_usage(key_info)
            
            return key_info
            
        except Exception as e:
            logger.error(f"Error validating API key: {str(e)}")
            return None
    
    async def check_rate_limit(self, api_key: str, endpoint: str = "") -> tuple[bool, Dict[str, Any]]:
        """
        API 키 속도 제한 확인
        
        Args:
            api_key: API 키
            endpoint: API 엔드포인트
            
        Returns:
            (허용 여부, 제한 정보)
        """
        try:
            key_info = await self._get_key_info(api_key)
            if not key_info:
                return False, {"error": "Invalid API key"}
            
            # 현재 시간 윈도우 (시간 단위)
            current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
            window_key = f"{self.usage_prefix}hourly:{api_key}:{current_hour.isoformat()}"
            
            # 현재 사용량 조회
            current_usage = await self.redis_client.get(window_key)
            current_count = int(current_usage) if current_usage else 0
            
            # 속도 제한 확인
            if current_count >= key_info.rate_limit:
                reset_time = current_hour + timedelta(hours=1)
                return False, {
                    "allowed": False,
                    "limit": key_info.rate_limit,
                    "remaining": 0,
                    "reset_time": reset_time.isoformat(),
                    "retry_after": (reset_time - datetime.utcnow()).total_seconds()
                }
            
            # 사용량 증가
            await self.redis_client.incr(window_key)
            await self.redis_client.expire(window_key, 3600)  # 1시간 후 만료
            
            return True, {
                "allowed": True,
                "limit": key_info.rate_limit,
                "remaining": key_info.rate_limit - current_count - 1,
                "reset_time": (current_hour + timedelta(hours=1)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {str(e)}")
            return False, {"error": "Rate limit check failed"}
    
    async def revoke_api_key(self, api_key: str) -> bool:
        """
        API 키 폐기
        
        Args:
            api_key: 폐기할 API 키
            
        Returns:
            성공 여부
        """
        try:
            key_info = await self._get_key_info(api_key)
            if not key_info:
                return False
            
            # 비활성화
            key_info.is_active = False
            await self._store_key_info(key_info)
            
            logger.info(f"API key revoked: {key_info.key_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error revoking API key: {str(e)}")
            return False
    
    async def get_user_api_keys(self, user_id: str) -> List[APIKeyInfo]:
        """
        사용자의 모든 API 키 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            API 키 정보 목록
        """
        try:
            # 사용자 API 키 목록 조회
            api_keys = await self.redis_client.smembers(f"{self.key_prefix}user:{user_id}")
            
            key_infos = []
            for api_key in api_keys:
                key_info = await self._get_key_info(api_key)
                if key_info:
                    key_infos.append(key_info)
            
            return key_infos
            
        except Exception as e:
            logger.error(f"Error getting user API keys: {str(e)}")
            return []
    
    async def update_api_key_permissions(self, api_key: str, permissions: List[str]) -> bool:
        """
        API 키 권한 업데이트
        
        Args:
            api_key: API 키
            permissions: 새 권한 목록
            
        Returns:
            성공 여부
        """
        try:
            key_info = await self._get_key_info(api_key)
            if not key_info:
                return False
            
            key_info.permissions = permissions
            await self._store_key_info(key_info)
            
            logger.info(f"API key permissions updated: {key_info.key_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating API key permissions: {str(e)}")
            return False
    
    async def get_api_key_usage_stats(self, api_key: str, days: int = 7) -> Dict[str, Any]:
        """
        API 키 사용량 통계 조회
        
        Args:
            api_key: API 키
            days: 조회 기간 (일)
            
        Returns:
            사용량 통계
        """
        try:
            key_info = await self._get_key_info(api_key)
            if not key_info:
                return {"error": "Invalid API key"}
            
            # 기간별 사용량 조회
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            daily_usage = {}
            total_requests = 0
            
            current_date = start_date
            while current_date <= end_date:
                date_key = f"{self.usage_prefix}daily:{api_key}:{current_date.strftime('%Y-%m-%d')}"
                daily_count = await self.redis_client.get(date_key)
                daily_usage[current_date.strftime('%Y-%m-%d')] = int(daily_count) if daily_count else 0
                total_requests += daily_usage[current_date.strftime('%Y-%m-%d')]
                current_date += timedelta(days=1)
            
            return {
                "api_key": api_key,
                "key_id": key_info.key_id,
                "period_days": days,
                "total_requests": total_requests,
                "daily_average": total_requests / days if days > 0 else 0,
                "daily_usage": daily_usage,
                "tier": key_info.tier,
                "rate_limit": key_info.rate_limit
            }
            
        except Exception as e:
            logger.error(f"Error getting API key usage stats: {str(e)}")
            return {"error": "Failed to get usage stats"}
    
    async def _store_key_info(self, key_info: APIKeyInfo) -> None:
        """API 키 정보 저장"""
        key_data = asdict(key_info)
        await self.redis_client.hset(
            f"{self.key_prefix}info:{key_info.api_key}",
            mapping=key_data
        )
    
    async def _get_key_info(self, api_key: str) -> Optional[APIKeyInfo]:
        """API 키 정보 조회"""
        try:
            key_data = await self.redis_client.hgetall(f"{self.key_prefix}info:{api_key}")
            if not key_data:
                return None
            
            # 문자열 값을 적절한 타입으로 변환
            if b'usage_count' in key_data:
                key_data[b'usage_count'] = int(key_data[b'usage_count'])
            if b'is_active' in key_data:
                key_data[b'is_active'] = key_data[b'is_active'] == b'True'
            if b'rate_limit' in key_data:
                key_data[b'rate_limit'] = int(key_data[b'rate_limit'])
            
            # 바이트를 문자열로 변환
            str_key_data = {k.decode(): v.decode() if isinstance(v, bytes) else v 
                          for k, v in key_data.items()}
            
            return APIKeyInfo(**str_key_data)
            
        except Exception as e:
            logger.error(f"Error getting key info: {str(e)}")
            return None
    
    async def _update_usage(self, key_info: APIKeyInfo) -> None:
        """API 키 사용량 업데이트"""
        try:
            # 마지막 사용 시간 업데이트
            key_info.last_used = datetime.utcnow().isoformat()
            key_info.usage_count += 1
            
            await self._store_key_info(key_info)
            
            # 일일 사용량 기록
            today = datetime.utcnow().strftime('%Y-%m-%d')
            daily_key = f"{self.usage_prefix}daily:{key_info.api_key}:{today}"
            await self.redis_client.incr(daily_key)
            await self.redis_client.expire(daily_key, 86400 * 7)  # 7일간 유지
            
        except Exception as e:
            logger.error(f"Error updating usage: {str(e)}")

# 전역 API 키 서비스 인스턴스
api_key_service = APIKeyService()