# 보안 및 개인정보 보호 정책

## 1. 보안 아키텍처

### 1.1 다계층 보안 모델

#### 1.1.1 네트워크 보안 계층
```yaml
# security/network-security.yml
version: '3.8'

services:
  # 웹 애플리케이션 방화벽 (WAF)
  waf:
    image: owasp/modsecurity-crs:nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./security/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./security/modsecurity.conf:/etc/nginx/modsecurity.d/modsecurity.conf:ro
      - ./security/ssl:/etc/nginx/ssl:ro
    networks:
      - frontend
      - backend
    depends_on:
      - api-gateway

  # API 게이트웨이 (보안 정책 적용)
  api-gateway:
    image: kong:latest
    environment:
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: /kong/declarative/kong.yml
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
      KONG_ADMIN_LISTEN: 0.0.0.0:8001
      KONG_PLUGINS: rate-limiting, request-size-limiting, ip-restriction, oauth2, jwt
    volumes:
      - ./security/kong.yml:/kong/declarative/kong.yml:ro
    networks:
      - backend
    depends_on:
      - stock-search-service
      - sentiment-service

  # IDS/IPS (침입 탐지/방지 시스템)
  ids:
    image: aquasec/trivy:latest
    command: server --listen 0.0.0.0:8080
    ports:
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - monitoring

  # 보안 스캐너
  security-scanner:
    image: owasp/zap2docker-stable
    command: zap.sh -daemon -host 0.0.0.0 -port 8090
    ports:
      - "8090:8090"
    networks:
      - monitoring

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # 내부 네트워크 (외부 접근 제한)
  monitoring:
    driver: bridge
```

#### 1.1.2 애플리케이션 보안 계층
```python
# security/application_security.py
import asyncio
import hashlib
import secrets
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from cryptography.fernet import Fernet
import bcrypt

class SecurityManager:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.token_expiry = timedelta(hours=24)
        self.refresh_token_expiry = timedelta(days=30)
        self.logger = logging.getLogger(__name__)
        
        # 암호화 키
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # 보안 정책
        self.password_policy = {
            'min_length': 8,
            'require_uppercase': True,
            'require_lowercase': True,
            'require_digits': True,
            'require_special': True,
            'max_age_days': 90
        }
        
        # 세션 관리
        self.active_sessions = {}
        self.failed_login_attempts = {}
        self.blocked_ips = {}
        
        # 보안 이벤트 로깅
        self.security_logger = logging.getLogger('security')
    
    def hash_password(self, password: str) -> str:
        """비밀번호 해싱"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """비밀번호 검증"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """비밀번호 강도 검증"""
        result = {
            'is_valid': True,
            'errors': [],
            'score': 0
        }
        
        # 길이 검증
        if len(password) < self.password_policy['min_length']:
            result['errors'].append(f"Password must be at least {self.password_policy['min_length']} characters long")
            result['is_valid'] = False
        else:
            result['score'] += 1
        
        # 대문자 검증
        if self.password_policy['require_uppercase'] and not any(c.isupper() for c in password):
            result['errors'].append("Password must contain at least one uppercase letter")
            result['is_valid'] = False
        else:
            result['score'] += 1
        
        # 소문자 검증
        if self.password_policy['require_lowercase'] and not any(c.islower() for c in password):
            result['errors'].append("Password must contain at least one lowercase letter")
            result['is_valid'] = False
        else:
            result['score'] += 1
        
        # 숫자 검증
        if self.password_policy['require_digits'] and not any(c.isdigit() for c in password):
            result['errors'].append("Password must contain at least one digit")
            result['is_valid'] = False
        else:
            result['score'] += 1
        
        # 특수문자 검증
        if self.password_policy['require_special'] and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            result['errors'].append("Password must contain at least one special character")
            result['is_valid'] = False
        else:
            result['score'] += 1
        
        return result
    
    def generate_tokens(self, user_data: Dict) -> Dict[str, str]:
        """JWT 토큰 생성"""
        # 액세스 토큰
        access_token_payload = {
            'user_id': user_data['user_id'],
            'username': user_data['username'],
            'email': user_data['email'],
            'roles': user_data.get('roles', []),
            'exp': datetime.utcnow() + self.token_expiry,
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        
        access_token = jwt.encode(
            access_token_payload,
            self.secret_key,
            algorithm=self.algorithm
        )
        
        # 리프레시 토큰
        refresh_token_payload = {
            'user_id': user_data['user_id'],
            'exp': datetime.utcnow() + self.refresh_token_expiry,
            'iat': datetime.utcnow(),
            'type': 'refresh'
        }
        
        refresh_token = jwt.encode(
            refresh_token_payload,
            self.secret_key,
            algorithm=self.algorithm
        )
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'bearer',
            'expires_in': int(self.token_expiry.total_seconds())
        }
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """JWT 토큰 검증"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # 토큰 만료 검증
            if payload.get('exp') < datetime.utcnow().timestamp():
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            self.security_logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            self.security_logger.warning(f"Invalid token: {str(e)}")
            return None
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """민감 데이터 암호화"""
        encrypted_data = self.cipher_suite.encrypt(data.encode())
        return encrypted_data.decode()
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """민감 데이터 복호화"""
        decrypted_data = self.cipher_suite.decrypt(encrypted_data.encode())
        return decrypted_data.decode()
    
    def check_ip_reputation(self, ip_address: str) -> Dict[str, Any]:
        """IP 주소 평판 확인"""
        # 실제 구현에서는 외부 서비스(예: AbuseIPDB) 사용
        # 여기서는 기본 로직만 구현
        
        # 차단된 IP 확인
        if ip_address in self.blocked_ips:
            block_info = self.blocked_ips[ip_address]
            if datetime.now() < block_info['expires_at']:
                return {
                    'is_blocked': True,
                    'reason': block_info['reason'],
                    'blocked_until': block_info['expires_at'].isoformat()
                }
            else:
                # 차단 기간 만료 시 제거
                del self.blocked_ips[ip_address]
        
        # 실패 로그인 시도 확인
        failed_attempts = self.failed_login_attempts.get(ip_address, 0)
        if failed_attempts >= 5:
            return {
                'is_blocked': True,
                'reason': 'Too many failed login attempts',
                'blocked_until': (datetime.now() + timedelta(hours=1)).isoformat()
            }
        
        return {'is_blocked': False}
    
    def record_failed_login(self, ip_address: str, username: str):
        """실패 로그인 기록"""
        # IP 주소별 실패 횟수 증가
        if ip_address not in self.failed_login_attempts:
            self.failed_login_attempts[ip_address] = 0
        
        self.failed_login_attempts[ip_address] += 1
        
        # 5회 이상 실패 시 IP 차단
        if self.failed_login_attempts[ip_address] >= 5:
            self.block_ip_address(ip_address, 'Too many failed login attempts', hours=1)
        
        # 보안 이벤트 로깅
        self.security_logger.warning(
            f"Failed login attempt for user '{username}' from IP {ip_address}"
        )
    
    def block_ip_address(self, ip_address: str, reason: str, hours: int = 24):
        """IP 주소 차단"""
        self.blocked_ips[ip_address] = {
            'reason': reason,
            'blocked_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(hours=hours)
        }
        
        self.security_logger.warning(
            f"IP address {ip_address} blocked for {hours} hours. Reason: {reason}"
        )
    
    def sanitize_input(self, data: str) -> str:
        """입력 데이터 정제 (XSS 방지)"""
        # HTML 태그 제거
        import html
        sanitized = html.escape(data)
        
        # SQL 인젝션 방지 (기본적인 패턴)
        sql_patterns = [
            r'(\bUNION\b|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b)',
            r'(--|#|\/\*)',
            r'(\bOR\b|\bAND\b)\s+\d+\s*=\s*\d+',
            r'(\'\s*OR\s*\'.*\'\s*=\s*\'.*\')'
        ]
        
        import re
        for pattern in sql_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        return sanitized
    
    def validate_file_upload(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """파일 업로드 검증"""
        result = {
            'is_valid': True,
            'errors': [],
            'file_size': len(file_data),
            'file_type': None
        }
        
        # 파일 크기 제한 (10MB)
        max_size = 10 * 1024 * 1024
        if len(file_data) > max_size:
            result['errors'].append(f"File size exceeds maximum allowed size of {max_size} bytes")
            result['is_valid'] = False
        
        # 파일 확장자 검증
        allowed_extensions = ['.csv', '.json', '.txt', '.pdf']
        file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        if f'.{file_extension}' not in allowed_extensions:
            result['errors'].append(f"File extension '.{file_extension}' is not allowed")
            result['is_valid'] = False
        
        # 파일 내용 검증 (매직 넘버)
        if len(file_data) >= 4:
            magic_bytes = file_data[:4]
            
            # PDF 파일 확인
            if magic_bytes == b'%PDF':
                result['file_type'] = 'pdf'
            # CSV/JSON/TXT 파일 확인 (텍스트 파일)
            elif all(32 <= byte <= 126 or byte in [9, 10, 13] for byte in magic_bytes):
                result['file_type'] = 'text'
            else:
                result['errors'].append("File type is not recognized or not allowed")
                result['is_valid'] = False
        
        return result

# 보안 미들웨어
class SecurityMiddleware:
    def __init__(self, security_manager: SecurityManager):
        self.security_manager = security_manager
        self.logger = logging.getLogger(__name__)
    
    async def __call__(self, request, call_next):
        # IP 주소 확인
        client_ip = request.client.host
        ip_reputation = self.security_manager.check_ip_reputation(client_ip)
        
        if ip_reputation['is_blocked']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access blocked due to security policy"
            )
        
        # 요청 헤더 보안 검증
        self._validate_security_headers(request)
        
        # 요청 처리
        response = await call_next(request)
        
        # 응답 헤더 보안 설정
        self._set_security_headers(response)
        
        return response
    
    def _validate_security_headers(self, request):
        """보안 헤더 검증"""
        # User-Agent 확인
        user_agent = request.headers.get('user-agent', '')
        if not user_agent:
            self.logger.warning("Request without User-Agent header")
        
        # Referer 확인 (CSRF 방지)
        referer = request.headers.get('referer', '')
        if referer and not self._is_valid_referer(referer):
            self.logger.warning(f"Suspicious referer: {referer}")
    
    def _set_security_headers(self, response):
        """보안 헤더 설정"""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    def _is_valid_referer(self, referer: str) -> bool:
        """유효한 Referer 확인"""
        # 실제 구현에서는 허용된 도메인 목록과 비교
        allowed_domains = ['insitechart.com', 'localhost']
        
        for domain in allowed_domains:
            if domain in referer:
                return True
        
        return False

# 의존성 주입을 위한 보안 검증 함수
security_manager = SecurityManager(secret_key="your-secret-key")
security_middleware = SecurityMiddleware(security_manager)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """현재 사용자 정보 가져오기"""
    token = credentials.credentials
    payload = security_manager.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return payload

async def require_role(required_role: str):
    """특정 역할 필요 확인"""
    def role_checker(current_user: Dict = Depends(get_current_user)):
        user_roles = current_user.get('roles', [])
        
        if required_role not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        
        return current_user
    
    return role_checker
```

### 1.2 데이터 암호화

#### 1.2.1 암호화 키 관리
```python
# security/key_management.py
import os
import json
import base64
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import redis.asyncio as redis

class KeyManager:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.logger = logging.getLogger(__name__)
        
        # 키 저장소
        self.key_store = {}
        
        # 키 정책
        self.key_rotation_interval = timedelta(days=90)
        self.key_derivation_iterations = 100000
        
        # 마스터 키 (실제로는 HSM이나 AWS KMS 사용)
        self.master_key = os.environ.get('MASTER_KEY', self._generate_master_key())
    
    def _generate_master_key(self) -> str:
        """마스터 키 생성"""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()
    
    async def initialize(self):
        """키 관리자 초기화"""
        # 기존 키 로드
        await self._load_keys()
        
        # 키 만료 확인 및 회전
        await self._check_key_rotation()
    
    async def _load_keys(self):
        """Redis에서 키 로드"""
        try:
            keys_data = await self.redis.get("encryption_keys")
            
            if keys_data:
                self.key_store = json.loads(keys_data)
                self.logger.info("Loaded encryption keys from Redis")
            else:
                # 초기 키 생성
                await self._generate_initial_keys()
                
        except Exception as e:
            self.logger.error(f"Failed to load keys: {str(e)}")
            await self._generate_initial_keys()
    
    async def _generate_initial_keys(self):
        """초기 암호화 키 생성"""
        self.key_store = {
            'data_encryption': {
                'key_id': 'data_key_1',
                'key': self._generate_encryption_key(),
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            },
            'api_keys': {
                'key_id': 'api_key_1',
                'key': self._generate_encryption_key(),
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            },
            'session_keys': {
                'key_id': 'session_key_1',
                'key': self._generate_encryption_key(),
                'created_at': datetime.now().isoformat(),
                'status': 'active'
            }
        }
        
        await self._save_keys()
        self.logger.info("Generated initial encryption keys")
    
    def _generate_encryption_key(self) -> str:
        """암호화 키 생성"""
        # PBKDF2를 사용한 키 유도
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=os.urandom(16),
            iterations=self.key_derivation_iterations,
            backend=default_backend()
        )
        
        key = kdf.derive(self.master_key.encode())
        return base64.urlsafe_b64encode(key).decode()
    
    async def _save_keys(self):
        """Redis에 키 저장"""
        try:
            await self.redis.set("encryption_keys", json.dumps(self.key_store))
            self.logger.info("Saved encryption keys to Redis")
        except Exception as e:
            self.logger.error(f"Failed to save keys: {str(e)}")
    
    async def _check_key_rotation(self):
        """키 회전 확인"""
        now = datetime.now()
        
        for key_type, key_info in self.key_store.items():
            created_at = datetime.fromisoformat(key_info['created_at'])
            
            if now - created_at >= self.key_rotation_interval:
                await self._rotate_key(key_type)
    
    async def _rotate_key(self, key_type: str):
        """키 회전"""
        old_key_info = self.key_store[key_type]
        
        # 새 키 생성
        new_key_info = {
            'key_id': f"{key_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'key': self._generate_encryption_key(),
            'created_at': datetime.now().isoformat(),
            'status': 'active'
        }
        
        # 이전 키 상태 변경
        old_key_info['status'] = 'deprecated'
        old_key_info['deprecated_at'] = datetime.now().isoformat()
        
        # 새 키 저장
        self.key_store[f"{key_type}_new"] = new_key_info
        
        await self._save_keys()
        
        self.logger.info(f"Rotated key for {key_type}")
        
        # 데이터 재암호화 작업 스케줄링
        asyncio.create_task(self._reencrypt_data(key_type, old_key_info, new_key_info))
    
    async def _reencrypt_data(self, key_type: str, old_key_info: Dict, new_key_info: Dict):
        """데이터 재암호화"""
        self.logger.info(f"Starting re-encryption for {key_type}")
        
        try:
            # 실제 구현에서는 해당 키로 암호화된 데이터를 찾아 재암호화
            # 여기서는 로직만 표시
            
            # 이전 키 제거
            del self.key_store[f"{key_type}_new"]
            self.key_store[key_type] = new_key_info
            
            await self._save_keys()
            
            self.logger.info(f"Completed re-encryption for {key_type}")
            
        except Exception as e:
            self.logger.error(f"Re-encryption failed for {key_type}: {str(e)}")
            
            # 실패 시 롤백
            del self.key_store[f"{key_type}_new"]
            self.key_store[key_type]['status'] = 'active'
            await self._save_keys()
    
    def get_active_key(self, key_type: str) -> Optional[Dict]:
        """활성 키 가져오기"""
        key_info = self.key_store.get(key_type)
        
        if key_info and key_info['status'] == 'active':
            return key_info
        
        return None
    
    def get_key_by_id(self, key_id: str) -> Optional[Dict]:
        """ID로 키 가져오기"""
        for key_type, key_info in self.key_store.items():
            if key_info.get('key_id') == key_id:
                return key_info
        
        return None
    
    async def revoke_key(self, key_id: str):
        """키 폐기"""
        for key_type, key_info in self.key_store.items():
            if key_info.get('key_id') == key_id:
                key_info['status'] = 'revoked'
                key_info['revoked_at'] = datetime.now().isoformat()
                
                await self._save_keys()
                
                self.logger.info(f"Revoked key {key_id}")
                return True
        
        return False
    
    async def get_key_stats(self) -> Dict:
        """키 통계 정보"""
        stats = {
            'total_keys': len(self.key_store),
            'active_keys': 0,
            'deprecated_keys': 0,
            'revoked_keys': 0,
            'keys_by_type': {},
            'last_rotation': None
        }
        
        now = datetime.now()
        
        for key_type, key_info in self.key_store.items():
            status = key_info.get('status', 'unknown')
            
            if status == 'active':
                stats['active_keys'] += 1
            elif status == 'deprecated':
                stats['deprecated_keys'] += 1
            elif status == 'revoked':
                stats['revoked_keys'] += 1
            
            # 타입별 통계
            if key_type not in stats['keys_by_type']:
                stats['keys_by_type'][key_type] = {
                    'active': 0,
                    'deprecated': 0,
                    'revoked': 0
                }
            
            stats['keys_by_type'][key_type][status] += 1
            
            # 마지막 회전 시간
            created_at = datetime.fromisoformat(key_info['created_at'])
            if not stats['last_rotation'] or created_at > stats['last_rotation']:
                stats['last_rotation'] = created_at
        
        if stats['last_rotation']:
            stats['last_rotation'] = stats['last_rotation'].isoformat()
        
        return stats

# 데이터 암호화 클래스
class DataEncryption:
    def __init__(self, key_manager: KeyManager):
        self.key_manager = key_manager
        self.logger = logging.getLogger(__name__)
    
    def encrypt_data(self, data: str, key_type: str = 'data_encryption') -> Dict:
        """데이터 암호화"""
        try:
            key_info = self.key_manager.get_active_key(key_type)
            
            if not key_info:
                raise ValueError(f"No active key found for {key_type}")
            
            # 키 디코딩
            key = base64.urlsafe_b64decode(key_info['key'])
            
            # IV 생성
            iv = os.urandom(16)
            
            # AES-GCM 암호화
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv),
                backend=default_backend()
            )
            
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(data.encode()) + encryptor.finalize()
            
            # 결과 조합 (IV + 인증태그 + 암호문)
            encrypted_data = iv + encryptor.tag + ciphertext
            
            return {
                'encrypted_data': base64.urlsafe_b64encode(encrypted_data).decode(),
                'key_id': key_info['key_id'],
                'algorithm': 'AES-256-GCM',
                'encrypted_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Data encryption failed: {str(e)}")
            raise
    
    def decrypt_data(self, encrypted_package: Dict) -> str:
        """데이터 복호화"""
        try:
            # 키 정보 가져오기
            key_id = encrypted_package['key_id']
            key_info = self.key_manager.get_key_by_id(key_id)
            
            if not key_info:
                raise ValueError(f"Key not found: {key_id}")
            
            # 키 디코딩
            key = base64.urlsafe_b64decode(key_info['key'])
            
            # 암호문 디코딩
            encrypted_data = base64.urlsafe_b64decode(encrypted_package['encrypted_data'])
            
            # 구문 분석 (IV + 인증태그 + 암호문)
            iv = encrypted_data[:16]
            tag = encrypted_data[16:32]
            ciphertext = encrypted_data[32:]
            
            # AES-GCM 복호화
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv, tag),
                backend=default_backend()
            )
            
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            return plaintext.decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"Data decryption failed: {str(e)}")
            raise
    
    def encrypt_field(self, field_value: str, field_name: str) -> Dict:
        """필드별 암호화"""
        # 필드별로 다른 키 사용 가능
        key_type = 'data_encryption'  # 기본값
        
        # 민감 필드에 따라 다른 키 사용
        if field_name in ['email', 'phone', 'ssn']:
            key_type = 'api_keys'
        elif field_name in ['session_token', 'auth_token']:
            key_type = 'session_keys'
        
        return self.encrypt_data(field_value, key_type)
    
    def decrypt_field(self, encrypted_field: Dict) -> str:
        """필드별 복호화"""
        return self.decrypt_data(encrypted_field)
```

## 2. 개인정보 보호

### 2.1 개인정보 식별 및 처리

#### 2.1.1 PII(개인정보 식별 정보) 관리
```python
# privacy/pii_manager.py
import re
import hashlib
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
import logging
import json
from dataclasses import dataclass

@dataclass
class PIIField:
    """PII 필드 정의"""
    name: str
    pattern: re.Pattern
    sensitivity_level: int  # 1-5 (5가 가장 민감)
    retention_period: timedelta
    encryption_required: bool = True
    anonymization_method: str = 'hash'  # hash, mask, remove

class PIIManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # PII 필드 정의
        self.pii_fields = {
            'email': PIIField(
                name='email',
                pattern=re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
                sensitivity_level=3,
                retention_period=timedelta(days=365),
                encryption_required=True,
                anonymization_method='hash'
            ),
            'phone': PIIField(
                name='phone',
                pattern=re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),
                sensitivity_level=3,
                retention_period=timedelta(days=365),
                encryption_required=True,
                anonymization_method='mask'
            ),
            'ssn': PIIField(
                name='ssn',
                pattern=re.compile(r'\b\d{3}-\d{2}-\d{4}\b|\b\d{9}\b'),
                sensitivity_level=5,
                retention_period=timedelta(days=30),
                encryption_required=True,
                anonymization_method='remove'
            ),
            'credit_card': PIIField(
                name='credit_card',
                pattern=re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
                sensitivity_level=5,
                retention_period=timedelta(days=0),  # 즉시 삭제
                encryption_required=True,
                anonymization_method='remove'
            ),
            'ip_address': PIIField(
                name='ip_address',
                pattern=re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
                sensitivity_level=2,
                retention_period=timedelta(days=90),
                encryption_required=False,
                anonymization_method='hash'
            ),
            'name': PIIField(
                name='name',
                pattern=re.compile(r'\b[A-Z][a-z]+\s[A-Z][a-z]+\b'),
                sensitivity_level=2,
                retention_period=timedelta(days=365),
                encryption_required=True,
                anonymization_method='hash'
            )
        }
        
        # 데이터 보존 정책
        self.retention_policies = {
            'user_data': timedelta(days=365 * 7),  # 7년
            'transaction_data': timedelta(days=365 * 10),  # 10년
            'analytics_data': timedelta(days=365),  # 1년
            'session_data': timedelta(days=30),  # 30일
            'error_logs': timedelta(days=90)  # 90일
        }
        
        # 동의 관리
        self.consent_records = {}
    
    def scan_for_pii(self, text: str) -> Dict[str, List[str]]:
        """텍스트에서 PII 스캔"""
        found_pii = {}
        
        for field_name, pii_field in self.pii_fields.items():
            matches = pii_field.pattern.findall(text)
            if matches:
                found_pii[field_name] = matches
        
        return found_pii
    
    def anonymize_data(self, data: Any, context: str = 'general') -> Any:
        """데이터 익명화"""
        if isinstance(data, str):
            return self._anonymize_text(data, context)
        elif isinstance(data, dict):
            return self._anonymize_dict(data, context)
        elif isinstance(data, list):
            return [self.anonymize_data(item, context) for item in data]
        else:
            return data
    
    def _anonymize_text(self, text: str, context: str) -> str:
        """텍스트 익명화"""
        anonymized_text = text
        
        for field_name, pii_field in self.pii_fields.items():
            if pii_field.anonymization_method == 'hash':
                # 해시 처리
                matches = pii_field.pattern.findall(text)
                for match in matches:
                    hash_value = hashlib.sha256(match.encode()).hexdigest()[:8]
                    anonymized_text = anonymized_text.replace(match, f"[{field_name}:{hash_value}]")
            
            elif pii_field.anonymization_method == 'mask':
                # 마스킹 처리
                matches = pii_field.pattern.findall(text)
                for match in matches:
                    masked_value = self._mask_value(match, field_name)
                    anonymized_text = anonymized_text.replace(match, masked_value)
            
            elif pii_field.anonymization_method == 'remove':
                # 제거 처리
                matches = pii_field.pattern.findall(text)
                for match in matches:
                    anonymized_text = anonymized_text.replace(match, f"[{field_name}_REMOVED]")
        
        return anonymized_text
    
    def _anonymize_dict(self, data: Dict, context: str) -> Dict:
        """딕셔너리 익명화"""
        anonymized_data = {}
        
        for key, value in data.items():
            # 필드 이름으로 PII 확인
            pii_field = self._get_pii_field_by_name(key)
            
            if pii_field:
                if pii_field.anonymization_method == 'hash':
                    # 해시 처리
                    hash_value = hashlib.sha256(str(value).encode()).hexdigest()[:8]
                    anonymized_data[key] = f"[{pii_field.name}:{hash_value}]"
                elif pii_field.anonymization_method == 'mask':
                    # 마스킹 처리
                    anonymized_data[key] = self._mask_value(str(value), pii_field.name)
                elif pii_field.anonymization_method == 'remove':
                    # 제거 처리
                    anonymized_data[key] = f"[{pii_field.name}_REMOVED]"
            else:
                # 재귀적 처리
                anonymized_data[key] = self.anonymize_data(value, context)
        
        return anonymized_data
    
    def _get_pii_field_by_name(self, field_name: str) -> Optional[PIIField]:
        """필드 이름으로 PII 필드 찾기"""
        field_name_lower = field_name.lower()
        
        for pii_name, pii_field in self.pii_fields.items():
            if pii_name in field_name_lower:
                return pii_field
        
        return None
    
    def _mask_value(self, value: str, pii_type: str) -> str:
        """값 마스킹"""
        if pii_type == 'email':
            # 이메일 마스킹: u***@example.com
            parts = value.split('@')
            if len(parts) == 2:
                username = parts[0]
                domain = parts[1]
                masked_username = username[0] + '*' * (len(username) - 2) + username[-1] if len(username) > 2 else username[0] + '*'
                return f"{masked_username}@{domain}"
        
        elif pii_type == 'phone':
            # 전화번호 마스킹: ***-***-1234
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                return '*' * (len(digits) - 4) + digits[-4:]
        
        elif pii_type == 'ssn':
            # SSN 마스킹: ***-**-1234
            digits = re.sub(r'\D', '', value)
            if len(digits) == 9:
                return f"***-**-{digits[-4:]}"
        
        elif pii_type == 'credit_card':
            # 신용카드 마스킹: ****-****-****-1234
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                return '*' * (len(digits) - 4) + digits[-4:]
        
        # 기본 마스킹
        if len(value) > 4:
            return value[:2] + '*' * (len(value) - 4) + value[-2:]
        else:
            return '*' * len(value)
    
    def check_retention_compliance(self, data_type: str, created_at: datetime) -> Dict[str, Any]:
        """데이터 보존 규정 준수 확인"""
        retention_period = self.retention_policies.get(data_type)
        
        if not retention_period:
            return {'compliant': True, 'reason': 'No retention policy for this data type'}
        
        now = datetime.now()
        age = now - created_at
        
        if age > retention_period:
            return {
                'compliant': False,
                'reason': f'Data exceeds retention period of {retention_period}',
                'age_days': age.days,
                'retention_days': retention_period.days,
                'action_required': 'delete'
            }
        else:
            return {
                'compliant': True,
                'age_days': age.days,
                'retention_days': retention_period.days,
                'days_until_expiry': (retention_period - age).days
            }
    
    def record_consent(self, user_id: str, consent_type: str, granted: bool, 
                      context: Dict = None) -> str:
        """동의 기록"""
        consent_id = hashlib.sha256(
            f"{user_id}_{consent_type}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        consent_record = {
            'consent_id': consent_id,
            'user_id': user_id,
            'consent_type': consent_type,
            'granted': granted,
            'timestamp': datetime.now().isoformat(),
            'context': context or {},
            'ip_address': context.get('ip_address') if context else None,
            'user_agent': context.get('user_agent') if context else None
        }
        
        self.consent_records[consent_id] = consent_record
        
        self.logger.info(f"Recorded consent {consent_id} for user {user_id}: {consent_type} = {granted}")
        
        return consent_id
    
    def check_consent(self, user_id: str, consent_type: str) -> Dict[str, Any]:
        """동의 확인"""
        user_consents = [
            record for record in self.consent_records.values()
            if record['user_id'] == user_id and record['consent_type'] == consent_type
        ]
        
        if not user_consents:
            return {
                'has_consent': False,
                'reason': 'No consent record found',
                'required_action': 'request_consent'
            }
        
        # 가장 최신 동의 확인
        latest_consent = max(user_consents, key=lambda x: x['timestamp'])
        
        if latest_consent['granted']:
            return {
                'has_consent': True,
                'consent_id': latest_consent['consent_id'],
                'granted_at': latest_consent['timestamp']
            }
        else:
            return {
                'has_consent': False,
                'consent_id': latest_consent['consent_id'],
                'denied_at': latest_consent['timestamp'],
                'required_action': 'request_consent'
            }
    
    def revoke_consent(self, user_id: str, consent_type: str) -> bool:
        """동의 철회"""
        # 거부 동의 기록
        consent_id = self.record_consent(user_id, consent_type, False)
        
        self.logger.info(f"User {user_id} revoked consent for {consent_type}")
        
        return True
    
    def get_pii_summary(self) -> Dict[str, Any]:
        """PII 관리 요약"""
        return {
            'pii_fields_count': len(self.pii_fields),
            'pii_fields': [
                {
                    'name': field.name,
                    'sensitivity_level': field.sensitivity_level,
                    'retention_days': field.retention_period.days,
                    'encryption_required': field.encryption_required,
                    'anonymization_method': field.anonymization_method
                }
                for field in self.pii_fields.values()
            ],
            'retention_policies': {
                data_type: f"{period.days} days"
                for data_type, period in self.retention_policies.items()
            },
            'consent_records_count': len(self.consent_records)
        }
```

#### 1.2.2 GDPR 준수
```python
# privacy/gdpr_compliance.py
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import json

class GDPRComplianceManager:
    def __init__(self, db_connection, pii_manager):
        self.db = db_connection
        self.pii_manager = pii_manager
        self.logger = logging.getLogger(__name__)
        
        # GDPR 요청 추적
        self.gdpr_requests = {}
        
        # 데이터 처리 활동 등록
        self.data_processing_activities = {}
    
    async def handle_data_subject_request(self, user_id: str, request_type: str, 
                                       request_details: Dict = None) -> Dict[str, Any]:
        """데이터 주체 요청 처리"""
        request_id = f"gdpr_{user_id}_{request_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 요청 기록
        request_record = {
            'request_id': request_id,
            'user_id': user_id,
            'request_type': request_type,  # access, rectification, erasure, portability
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'details': request_details or {},
            'completed_at': None,
            'result': None
        }
        
        self.gdpr_requests[request_id] = request_record
        
        self.logger.info(f"GDPR request {request_id} created for user {user_id}: {request_type}")
        
        try:
            if request_type == 'access':
                result = await self._handle_access_request(user_id)
            elif request_type == 'rectification':
                result = await self._handle_rectification_request(user_id, request_details)
            elif request_type == 'erasure':
                result = await self._handle_erasure_request(user_id)
            elif request_type == 'portability':
                result = await self._handle_portability_request(user_id)
            else:
                raise ValueError(f"Unknown request type: {request_type}")
            
            # 요청 완료 기록
            request_record['status'] = 'completed'
            request_record['completed_at'] = datetime.now().isoformat()
            request_record['result'] = result
            
            self.logger.info(f"GDPR request {request_id} completed for user {user_id}")
            
            return {
                'request_id': request_id,
                'status': 'completed',
                'result': result
            }
            
        except Exception as e:
            # 요청 실패 기록
            request_record['status'] = 'failed'
            request_record['completed_at'] = datetime.now().isoformat()
            request_record['error'] = str(e)
            
            self.logger.error(f"GDPR request {request_id} failed for user {user_id}: {str(e)}")
            
            return {
                'request_id': request_id,
                'status': 'failed',
                'error': str(e)
            }
    
    async def _handle_access_request(self, user_id: str) -> Dict[str, Any]:
        """데이터 접근 요청 처리"""
        # 사용자 데이터 조회
        user_data = await self._get_user_data(user_id)
        
        # PII 스캔
        pii_summary = {}
        for data_type, data in user_data.items():
            if isinstance(data, str):
                found_pii = self.pii_manager.scan_for_pii(data)
                if found_pii:
                    pii_summary[data_type] = found_pii
        
        # 데이터 처리 활동
        processing_activities = self._get_user_processing_activities(user_id)
        
        # 동의 기록
        consent_records = [
            record for record in self.pii_manager.consent_records.values()
            if record['user_id'] == user_id
        ]
        
        return {
            'user_data': user_data,
            'pii_summary': pii_summary,
            'processing_activities': processing_activities,
            'consent_records': consent_records,
            'data_retention_info': self._get_data_retention_info(user_data)
        }
    
    async def _handle_rectification_request(self, user_id: str, 
                                          request_details: Dict) -> Dict[str, Any]:
        """데이터 정정 요청 처리"""
        corrections = request_details.get('corrections', {})
        
        updated_data = {}
        
        for field_name, new_value in corrections.items():
            # 데이터 정정
            success = await self._update_user_data_field(user_id, field_name, new_value)
            
            updated_data[field_name] = {
                'new_value': new_value,
                'updated': success
            }
        
        # 변경 로그 기록
        await self._log_data_changes(user_id, updated_data, 'rectification')
        
        return {
            'updated_data': updated_data,
            'message': 'Data rectification completed'
        }
    
    async def _handle_erasure_request(self, user_id: str) -> Dict[str, Any]:
        """데이터 삭제 요청 처리 (잊힐 권리)"""
        # 삭제할 데이터 목록
        user_data = await self._get_user_data(user_id)
        deleted_data = {}
        
        for data_type, data in user_data.items():
            # 보존 기간 확인
            if data_type == 'user_data':
                created_at = datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
                compliance = self.pii_manager.check_retention_compliance(data_type, created_at)
                
                if not compliance['compliant'] or compliance['action_required'] == 'delete':
                    # 데이터 삭제
                    success = await self._delete_user_data(user_id, data_type)
                    deleted_data[data_type] = {
                        'deleted': success,
                        'reason': compliance.get('reason', 'User request')
                    }
                else:
                    deleted_data[data_type] = {
                        'deleted': False,
                        'reason': compliance.get('reason', 'Retention policy')
                    }
            else:
                # 기타 데이터는 즉시 삭제
                success = await self._delete_user_data(user_id, data_type)
                deleted_data[data_type] = {
                    'deleted': success,
                    'reason': 'User request'
                }
        
        # 삭제 로그 기록
        await self._log_data_changes(user_id, deleted_data, 'erasure')
        
        return {
            'deleted_data': deleted_data,
            'message': 'Data erasure completed'
        }
    
    async def _handle_portability_request(self, user_id: str) -> Dict[str, Any]:
        """데이터 이동성 요청 처리"""
        # 사용자 데이터 조회
        user_data = await self._get_user_data(user_id)
        
        # JSON 형식으로 변환
        portable_data = {
            'export_date': datetime.now().isoformat(),
            'user_id': user_id,
            'data': user_data
        }
        
        # CSV 형식으로 변환 (기본 데이터만)
        csv_data = self._convert_to_csv(user_data)
        
        return {
            'json_data': portable_data,
            'csv_data': csv_data,
            'message': 'Data portability export completed'
        }
    
    async def _get_user_data(self, user_id: str) -> Dict[str, Any]:
        """사용자 데이터 조회"""
        # 실제 구현에서는 데이터베이스에서 조회
        # 여기서는 더미 데이터 반환
        
        return {
            'user_data': {
                'user_id': user_id,
                'email': f'user{user_id}@example.com',
                'name': 'User Name',
                'phone': '+1234567890',
                'created_at': '2023-01-01T00:00:00',
                'last_login': '2023-12-01T00:00:00'
            },
            'transaction_data': [
                {
                    'transaction_id': 'txn_123',
                    'amount': 100.0,
                    'date': '2023-11-01T00:00:00'
                }
            ],
            'analytics_data': {
                'page_views': 100,
                'session_duration': 3600
            },
            'session_data': {
                'last_session': '2023-12-01T00:00:00',
                'session_count': 50
            }
        }
    
    async def _update_user_data_field(self, user_id: str, field_name: str, new_value: Any) -> bool:
        """사용자 데이터 필드 업데이트"""
        # 실제 구현에서는 데이터베이스 업데이트
        self.logger.info(f"Updated {field_name} for user {user_id} to {new_value}")
        return True
    
    async def _delete_user_data(self, user_id: str, data_type: str) -> bool:
        """사용자 데이터 삭제"""
        # 실제 구현에서는 데이터베이스 삭제
        self.logger.info(f"Deleted {data_type} for user {user_id}")
        return True
    
    async def _log_data_changes(self, user_id: str, changes: Dict, change_type: str):
        """데이터 변경 로그 기록"""
        log_entry = {
            'user_id': user_id,
            'change_type': change_type,
            'changes': changes,
            'timestamp': datetime.now().isoformat()
        }
        
        # 실제 구현에서는 로그 저장
        self.logger.info(f"Data change logged: {json.dumps(log_entry)}")
    
    def _get_user_processing_activities(self, user_id: str) -> List[Dict]:
        """사용자 데이터 처리 활동 조회"""
        # 실제 구현에서는 데이터베이스에서 조회
        return [
            {
                'activity': 'User profile management',
                'purpose': 'Service provision',
                'legal_basis': 'Contract',
                'data_categories': ['name', 'email', 'phone'],
                'retention_period': '7 years'
            },
            {
                'activity': 'Analytics',
                'purpose': 'Service improvement',
                'legal_basis': 'Legitimate interest',
                'data_categories': ['usage patterns'],
                'retention_period': '1 year'
            }
        ]
    
    def _get_data_retention_info(self, user_data: Dict) -> Dict[str, Any]:
        """데이터 보존 정보"""
        retention_info = {}
        
        for data_type, data in user_data.items():
            if isinstance(data, dict) and 'created_at' in data:
                created_at = datetime.fromisoformat(data['created_at'])
                compliance = self.pii_manager.check_retention_compliance(data_type, created_at)
                retention_info[data_type] = compliance
        
        return retention_info
    
    def _convert_to_csv(self, data: Dict) -> str:
        """CSV 형식으로 변환"""
        # 간단한 CSV 변환 (실제로는 더 복잡한 로직 필요)
        csv_lines = ['field,value']
        
        for key, value in data.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    csv_lines.append(f"{key}_{sub_key},{sub_value}")
            else:
                csv_lines.append(f"{key},{value}")
        
        return '\n'.join(csv_lines)
    
    def register_processing_activity(self, activity_id: str, activity_details: Dict):
        """데이터 처리 활동 등록"""
        self.data_processing_activities[activity_id] = {
            'activity_id': activity_id,
            'name': activity_details.get('name'),
            'purpose': activity_details.get('purpose'),
            'legal_basis': activity_details.get('legal_basis'),
            'data_categories': activity_details.get('data_categories', []),
            'data_subjects': activity_details.get('data_subjects', []),
            'retention_period': activity_details.get('retention_period'),
            'security_measures': activity_details.get('security_measures', []),
            'international_transfers': activity_details.get('international_transfers', False),
            'registered_at': datetime.now().isoformat()
        }
        
        self.logger.info(f"Registered processing activity: {activity_id}")
    
    def get_gdpr_request_status(self, request_id: str) -> Optional[Dict]:
        """GDPR 요청 상태 조회"""
        return self.gdpr_requests.get(request_id)
    
    def get_gdpr_compliance_report(self) -> Dict[str, Any]:
        """GDPR 준수 보고서"""
        total_requests = len(self.gdpr_requests)
        completed_requests = sum(1 for req in self.gdpr_requests.values() if req['status'] == 'completed')
        failed_requests = sum(1 for req in self.gdpr_requests.values() if req['status'] == 'failed')
        pending_requests = sum(1 for req in self.gdpr_requests.values() if req['status'] == 'pending')
        
        return {
            'total_requests': total_requests,
            'completed_requests': completed_requests,
            'failed_requests': failed_requests,
            'pending_requests': pending_requests,
            'completion_rate': (completed_requests / total_requests * 100) if total_requests > 0 else 0,
            'processing_activities_count': len(self.data_processing_activities),
            'last_updated': datetime.now().isoformat()
        }
```

## 3. 보안 감사 및 모니터링

### 3.1 보안 이벤트 감지

#### 3.1.1 보안 이벤트 관리자
```python
# security/security_event_manager.py
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import logging
import json
from enum import Enum
import re

class SecurityEventType(Enum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_EXPORT = "data_export"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    MALICIOUS_REQUEST = "malicious_request"
    BRUTE_FORCE_ATTEMPT = "brute_force_attempt"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"

class SecuritySeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SecurityEventManager:
    def __init__(self, alert_handlers: List[Callable] = None):
        self.logger = logging.getLogger('security_events')
        self.alert_handlers = alert_handlers or []
        
        # 보안 이벤트 저장
        self.security_events = []
        
        # 위협 패턴
        self.threat_patterns = {
            'sql_injection': re.compile(
                r'(\bUNION\b|\bSELECT\b|\bINSERT\b|\bUPDATE\b|\bDELETE\b|\bDROP\b)',
                re.IGNORECASE
            ),
            'xss': re.compile(
                r'<script|javascript:|on\w+\s*=',
                re.IGNORECASE
            ),
            'path_traversal': re.compile(
                r'\.\./|\.\.\\',
                re.IGNORECASE
            ),
            'command_injection': re.compile(
                r'[;&|`$()]',
                re.IGNORECASE
            )
        }
        
        # 위협 지표
        self.threat_indicators = {
            'multiple_failed_logins': 5,
            'rapid_requests': 100,  # 1분당
            'unusual_access_time': True,
            'privileged_access': True,
            'data_export_volume': 1000,  # 레코드 수
            'concurrent_sessions': 5
        }
        
        # 사용자 행동 기준선
        self.user_baselines = {}
        
        # 이상 탐지 임계값
        self.anomaly_thresholds = {
            'login_time_deviation': 2.0,  # 표준편차
            'request_rate_deviation': 3.0,
            'data_access_deviation': 2.5,
            'location_deviation': 1000  # km
        }
    
    async def record_security_event(self, event_type: SecurityEventType, 
                                  severity: SecuritySeverity, 
                                  user_id: str = None,
                                  ip_address: str = None,
                                  details: Dict = None) -> str:
        """보안 이벤트 기록"""
        event_id = f"sec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.security_events)}"
        
        event = {
            'event_id': event_id,
            'event_type': event_type.value,
            'severity': severity.value,
            'user_id': user_id,
            'ip_address': ip_address,
            'timestamp': datetime.now().isoformat(),
            'details': details or {},
            'investigated': False,
            'false_positive': False
        }
        
        self.security_events.append(event)
        
        # 심각도에 따라 즉시 알림
        if severity in [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL]:
            await self._trigger_alert(event)
        
        # 이상 패턴 확인
        await self._check_for_threat_patterns(event)
        
        self.logger.info(f"Security event recorded: {event_id} - {event_type.value}")
        
        return event_id
    
    async def _trigger_alert(self, event: Dict):
        """보안 알림 트리거"""
        alert_data = {
            'event_id': event['event_id'],
            'event_type': event['event_type'],
            'severity': event['severity'],
            'user_id': event['user_id'],
            'ip_address': event['ip_address'],
            'timestamp': event['timestamp'],
            'details': event['details']
        }
        
        # 알림 핸들러 실행
        for handler in self.alert_handlers:
            try:
                await handler(alert_data)
            except Exception as e:
                self.logger.error(f"Alert handler failed: {str(e)}")
    
    async def _check_for_threat_patterns(self, event: Dict):
        """위협 패턴 확인"""
        event_details = event.get('details', {})
        
        # SQL 인젝션 확인
        if 'request_data' in event_details:
            request_data = str(event_details['request_data'])
            
            for threat_name, pattern in self.threat_patterns.items():
                if pattern.search(request_data):
                    await self.record_security_event(
                        SecurityEventType.MALICIOUS_REQUEST,
                        SecuritySeverity.HIGH,
                        user_id=event['user_id'],
                        ip_address=event['ip_address'],
                        details={
                            'threat_type': threat_name,
                            'pattern_matched': True,
                            'request_data': request_data[:500]  # 첫 500자만 저장
                        }
                    )
        
        # 브루트 포스 확인
        if event['event_type'] == SecurityEventType.LOGIN_FAILURE:
            await self._check_brute_force(event)
        
        # 권한 상승 확인
        if event['event_type'] == SecurityEventType.PRIVILEGE_ESCALATION:
            await self.record_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                SecuritySeverity.HIGH,
                user_id=event['user_id'],
                ip_address=event['ip_address'],
                details={
                    'reason': 'Privilege escalation detected',
                    'original_event': event['event_id']
                }
            )
    
    async def _check_brute_force(self, event: Dict):
        """브루트 포스 공격 확인"""
        user_id = event['user_id']
        ip_address = event['ip_address']
        
        # 사용자별 실패 로그인 확인
        user_failures = [
            e for e in self.security_events
            if (e['event_type'] == SecurityEventType.LOGIN_FAILURE and 
                e['user_id'] == user_id and
                datetime.fromisoformat(e['timestamp']) > datetime.now() - timedelta(minutes=15))
        ]
        
        # IP 주소별 실패 로그인 확인
        ip_failures = [
            e for e in self.security_events
            if (e['event_type'] == SecurityEventType.LOGIN_FAILURE and 
                e['ip_address'] == ip_address and
                datetime.fromisoformat(e['timestamp']) > datetime.now() - timedelta(minutes=15))
        ]
        
        # 브루트 포스 임계값 확인
        if len(user_failures) >= self.threat_indicators['multiple_failed_logins']:
            await self.record_security_event(
                SecurityEventType.BRUTE_FORCE_ATTEMPT,
                SecuritySeverity.HIGH,
                user_id=user_id,
                ip_address=ip_address,
                details={
                    'failure_count': len(user_failures),
                    'time_window': '15 minutes',
                    'target': 'user'
                }
            )
        
        if len(ip_failures) >= self.threat_indicators['multiple_failed_logins']:
            await self.record_security_event(
                SecurityEventType.BRUTE_FORCE_ATTEMPT,
                SecuritySeverity.HIGH,
                user_id=user_id,
                ip_address=ip_address,
                details={
                    'failure_count': len(ip_failures),
                    'time_window': '15 minutes',
                    'target': 'ip_address'
                }
            )
    
    async def analyze_user_behavior(self, user_id: str, current_activity: Dict) -> Dict:
        """사용자 행동 분석"""
        # 사용자 기준선 가져오기
        baseline = self.user_baselines.get(user_id, {})
        
        # 이상 탐지
        anomalies = []
        
        # 로그인 시간 이상
        if 'login_time' in current_activity:
            login_time = current_activity['login_time']
            if 'avg_login_time' in baseline:
                avg_time = baseline['avg_login_time']
                std_dev = baseline.get('login_time_std_dev', 1.0)
                
                if abs(login_time - avg_time) > self.anomaly_thresholds['login_time_deviation'] * std_dev:
                    anomalies.append({
                        'type': 'unusual_login_time',
                        'severity': 'medium',
                        'current': login_time,
                        'baseline': avg_time,
                        'deviation': abs(login_time - avg_time) / std_dev
                    })
        
        # 요청 속도 이상
        if 'request_rate' in current_activity:
            request_rate = current_activity['request_rate']
            if 'avg_request_rate' in baseline:
                avg_rate = baseline['avg_request_rate']
                std_dev = baseline.get('request_rate_std_dev', 1.0)
                
                if request_rate > avg_rate + self.anomaly_thresholds['request_rate_deviation'] * std_dev:
                    anomalies.append({
                        'type': 'high_request_rate',
                        'severity': 'high',
                        'current': request_rate,
                        'baseline': avg_rate,
                        'deviation': (request_rate - avg_rate) / std_dev
                    })
        
        # 데이터 접근 이상
        if 'data_access_count' in current_activity:
            data_access = current_activity['data_access_count']
            if 'avg_data_access' in baseline:
                avg_access = baseline['avg_data_access']
                std_dev = baseline.get('data_access_std_dev', 1.0)
                
                if data_access > avg_access + self.anomaly_thresholds['data_access_deviation'] * std_dev:
                    anomalies.append({
                        'type': 'unusual_data_access',
                        'severity': 'medium',
                        'current': data_access,
                        'baseline': avg_access,
                        'deviation': (data_access - avg_access) / std_dev
                    })
        
        # 위치 이상
        if 'location' in current_activity and 'usual_locations' in baseline:
            current_location = current_activity['location']
            usual_locations = baseline['usual_locations']
            
            is_unusual = True
            for usual_location in usual_locations:
                if self._calculate_distance(current_location, usual_location) <= self.anomaly_thresholds['location_deviation']:
                    is_unusual = False
                    break
            
            if is_unusual:
                anomalies.append({
                    'type': 'unusual_location',
                    'severity': 'high',
                    'current': current_location,
                    'usual_locations': usual_locations
                })
        
        # 이상 행동 이벤트 기록
        if anomalies:
            max_severity = max(a['severity'] for a in anomalies)
            severity_map = {'low': SecuritySeverity.LOW, 'medium': SecuritySeverity.MEDIUM, 
                          'high': SecuritySeverity.HIGH, 'critical': SecuritySeverity.CRITICAL}
            
            await self.record_security_event(
                SecurityEventType.ANOMALOUS_BEHAVIOR,
                severity_map[max_severity],
                user_id=user_id,
                details={
                    'anomalies': anomalies,
                    'current_activity': current_activity
                }
            )
        
        return {
            'anomalies_detected': len(anomalies),
            'anomalies': anomalies,
            'risk_score': self._calculate_risk_score(anomalies)
        }
    
    def _calculate_distance(self, location1: Dict, location2: Dict) -> float:
        """두 위치 간 거리 계산 (km)"""
        # Haversine 공식 사용
        import math
        
        lat1, lon1 = location1['lat'], location1['lon']
        lat2, lon2 = location2['lat'], location2['lon']
        
        R = 6371  # 지구 반경 (km)
        
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        
        a = (math.sin(dLat/2)**2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dLon/2)**2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    def _calculate_risk_score(self, anomalies: List[Dict]) -> float:
        """위험 점수 계산"""
        if not anomalies:
            return 0.0
        
        severity_weights = {'low': 1.0, 'medium': 2.5, 'high': 5.0, 'critical': 10.0}
        
        total_score = 0.0
        for anomaly in anomalies:
            severity = anomaly['severity']
            weight = severity_weights.get(severity, 1.0)
            
            # 편차에 따른 가중치 조정
            deviation = anomaly.get('deviation', 1.0)
            adjusted_weight = weight * min(deviation, 5.0)  # 최대 5배까지
            
            total_score += adjusted_weight
        
        # 정규화 (0-100)
        normalized_score = min(total_score * 5, 100.0)
        
        return round(normalized_score, 2)
    
    async def update_user_baseline(self, user_id: str, activity_data: Dict):
        """사용자 기준선 업데이트"""
        if user_id not in self.user_baselines:
            self.user_baselines[user_id] = {}
        
        baseline = self.user_baselines[user_id]
        
        # 이동 평균으로 기준선 업데이트
        alpha = 0.1  # 학습률
        
        if 'login_time' in activity_data:
            current_time = activity_data['login_time']
            if 'avg_login_time' in baseline:
                baseline['avg_login_time'] = alpha * current_time + (1 - alpha) * baseline['avg_login_time']
            else:
                baseline['avg_login_time'] = current_time
        
        if 'request_rate' in activity_data:
            current_rate = activity_data['request_rate']
            if 'avg_request_rate' in baseline:
                baseline['avg_request_rate'] = alpha * current_rate + (1 - alpha) * baseline['avg_request_rate']
            else:
                baseline['avg_request_rate'] = current_rate
        
        if 'data_access_count' in activity_data:
            current_access = activity_data['data_access_count']
            if 'avg_data_access' in baseline:
                baseline['avg_data_access'] = alpha * current_access + (1 - alpha) * baseline['avg_data_access']
            else:
                baseline['avg_data_access'] = current_access
        
        if 'location' in activity_data:
            current_location = activity_data['location']
            if 'usual_locations' not in baseline:
                baseline['usual_locations'] = []
            
            # 위치 목록 업데이트 (최대 10개)
            if current_location not in baseline['usual_locations']:
                baseline['usual_locations'].append(current_location)
                if len(baseline['usual_locations']) > 10:
                    baseline['usual_locations'].pop(0)
    
    def get_security_summary(self, time_range: str = '24h') -> Dict:
        """보안 요약 정보"""
        now = datetime.now()
        
        # 시간 범위 계산
        if time_range == '24h':
            start_time = now - timedelta(hours=24)
        elif time_range == '7d':
            start_time = now - timedelta(days=7)
        elif time_range == '30d':
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(hours=24)
        
        # 필터링된 이벤트
        filtered_events = [
            event for event in self.security_events
            if datetime.fromisoformat(event['timestamp']) >= start_time
        ]
        
        # 통계 계산
        total_events = len(filtered_events)
        severity_counts = {
            'low': 0,
            'medium': 0,
            'high': 0,
            'critical': 0
        }
        
        event_type_counts = {}
        
        for event in filtered_events:
            severity = event['severity']
            severity_counts[severity] += 1
            
            event_type = event['event_type']
            if event_type not in event_type_counts:
                event_type_counts[event_type] = 0
            event_type_counts[event_type] += 1
        
        # 위협 트렌드
        threat_trends = {}
        for event_type, count in event_type_counts.items():
            if event_type in ['brute_force_attempt', 'malicious_request', 'unauthorized_access']:
                threat_trends[event_type] = count
        
        return {
            'time_range': time_range,
            'total_events': total_events,
            'severity_distribution': severity_counts,
            'event_type_distribution': event_type_counts,
            'threat_trends': threat_trends,
            'investigated_events': sum(1 for e in filtered_events if e['investigated']),
            'false_positives': sum(1 for e in filtered_events if e['false_positive']),
            'high_risk_users': self._get_high_risk_users(filtered_events),
            'blocked_ips': self._get_blocked_ips(filtered_events),
            'generated_at': now.isoformat()
        }
    
    def _get_high_risk_users(self, events: List[Dict]) -> List[Dict]:
        """고위험 사용자 목록"""
        user_risk_scores = {}
        
        for event in events:
            user_id = event.get('user_id')
            if not user_id:
                continue
            
            if user_id not in user_risk_scores:
                user_risk_scores[user_id] = 0
            
            # 심각도별 점수
            severity_scores = {'low': 1, 'medium': 5, 'high': 10, 'critical': 25}
            user_risk_scores[user_id] += severity_scores.get(event['severity'], 1)
        
        # 상위 10명
        sorted_users = sorted(user_risk_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return [
            {'user_id': user_id, 'risk_score': score}
            for user_id, score in sorted_users
        ]
    
    def _get_blocked_ips(self, events: List[Dict]) -> List[Dict]:
        """차단된 IP 목록"""
        ip_events = {}
        
        for event in events:
            ip_address = event.get('ip_address')
            if not ip_address:
                continue
            
            if ip_address not in ip_events:
                ip_events[ip_address] = 0
            
            # 심각도별 점수
            severity_scores = {'low': 1, 'medium': 5, 'high': 10, 'critical': 25}
            ip_events[ip_address] += severity_scores.get(event['severity'], 1)
        
        # 상위 10개
        sorted_ips = sorted(ip_events.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return [
            {'ip_address': ip_address, 'risk_score': score}
            for ip_address, score in sorted_ips
        ]
```

이 보안 및 개인정보 보호 정책 문서는 시스템의 보안 강화와 개인정보 보호를 위한 포괄적인 접근 방식을 제공합니다. 다계층 보안 아키텍처, 데이터 암호화, PII 관리, GDPR 준수, 보안 감시 및 모니터링 등을 통해 사용자 데이터를 안전하게 보호할 수 있습니다.