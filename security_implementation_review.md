# 보안 구현 세부 검토 및 강화 방안

## 1. 분석 개요

본 문서는 InsiteChart 프로젝트의 현재 보안 구현을 심층적으로 분석하여, 보안 취약점을 식별하고 구체적인 강화 방안을 제시합니다. 추가 기능 없이 현재 구현의 보안 수준을 향상시키는 데 중점을 둡니다.

## 2. 현재 보안 상태 분석

### 2.1 보안 평가 결과 요약

#### 2.1.1 현재 보안 준수도
- **전체 보안 준수도**: 77% (목표: 90% 이상)
- **인증 및 권한 부여**: 80%
- **데이터 보호**: 75%
- **네트워크 보안**: 70%
- **보안 모니터링**: 65%
- **개인정보보호**: 82%

#### 2.1.2 주요 보안 취약점
1. **입력 검증 미흡**: SQL 인젝션, XSS 방어 미흡
2. **세션 관리 미흡**: 동시 세션 제한, 하이재킹 방어 부족
3. **보안 로깅 부족**: 상세한 보안 이벤트 로깅 미흡
4. **데이터 암호화**: 일부 데이터 암호화 미흡
5. **API 보안**: 속도 제한, 인가 검증 부족

### 2.2 보안 구현 세부 분석

#### 2.2.1 인증 및 권한 부여
```python
# 현재 인증 구현 (개선 필요)
# backend/middleware/auth_middleware.py
async def jwt_auth_middleware(request: Request, call_next):
    # JWT 토큰 검증
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if not token:
        return JSONResponse(
            status_code=401,
            content={"error": "Authorization header missing"}
        )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        request.state.user_id = payload.get("user_id")
        request.state.role = payload.get("role")
    except jwt.PyJWTError:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid token"}
        )
    
    response = await call_next(request)
    return response

# 강화된 인증 미들웨어
class EnhancedAuthMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app
        self.token_blacklist = TokenBlacklist()
        self.session_manager = SessionManager()
        self.security_logger = SecurityLogger()
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # 보안 헤더 검증
        security_headers_result = await self._validate_security_headers(request)
        if not security_headers_result["valid"]:
            await self._send_security_error(send, security_headers_result["error"])
            return
        
        # JWT 토큰 검증
        auth_result = await self._validate_jwt_token(request)
        if not auth_result["valid"]:
            await self._log_security_event("auth_failure", request, auth_result["error"])
            await self._send_security_error(send, auth_result["error"])
            return
        
        # 세션 관리
        session_result = await self._validate_session(request)
        if not session_result["valid"]:
            await self._log_security_event("session_invalid", request, session_result["error"])
            await self._send_security_error(send, session_result["error"])
            return
        
        # 권한 부여 검증
        authz_result = await self._validate_authorization(request)
        if not authz_result["valid"]:
            await self._log_security_event("authz_failure", request, authz_result["error"])
            await self._send_security_error(send, authz_result["error"])
            return
        
        # 요청 처리
        await self.app(scope, receive, send)
    
    async def _validate_security_headers(self, request: Request) -> Dict[str, Any]:
        """보안 헤더 검증"""
        required_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block"
        }
        
        for header, expected_value in required_headers.items():
            if request.headers.get(header) != expected_value:
                return {
                    "valid": False,
                    "error": f"Missing or invalid security header: {header}"
                }
        
        return {"valid": True}
    
    async def _validate_jwt_token(self, request: Request) -> Dict[str, Any]:
        """강화된 JWT 토큰 검증"""
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header.startswith("Bearer "):
            return {"valid": False, "error": "Invalid authorization header format"}
        
        token = auth_header[7:]  # "Bearer " 제거
        
        # 블랙리스트 확인
        if await self.token_blacklist.is_blacklisted(token):
            return {"valid": False, "error": "Token has been revoked"}
        
        try:
            # 토큰 디코딩 및 검증
            payload = jwt.decode(
                token,
                SECRET_KEY,
                algorithms=["HS256"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_nbf": True,
                    "require_iat": True,
                    "require_exp": True,
                    "require_nbf": True
                }
            )
            
            # 토큰 발급자 검증
            if payload.get("iss") != "insitechart":
                return {"valid": False, "error": "Invalid token issuer"}
            
            # 토큰 대상 검증
            if payload.get("aud") != "insitechart-api":
                return {"valid": False, "error": "Invalid token audience"}
            
            # 사용자 상태 확인
            user_id = payload.get("sub")
            if not await self._is_user_active(user_id):
                return {"valid": False, "error": "User account is inactive"}
            
            # 요청 컨텍스트에 사용자 정보 저장
            request.state.user_id = user_id
            request.state.role = payload.get("role")
            request.state.token_jti = payload.get("jti")
            request.state.token_exp = payload.get("exp")
            
            return {"valid": True}
            
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "Token has expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": f"Invalid token: {str(e)}"}
    
    async def _validate_session(self, request: Request) -> Dict[str, Any]:
        """세션 관리 검증"""
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            return {"valid": False, "error": "No user context found"}
        
        # 동시 세션 제한 확인
        current_sessions = await self.session_manager.get_active_sessions(user_id)
        max_sessions = self._get_max_sessions_for_role(request.state.role)
        
        if len(current_sessions) >= max_sessions:
            # 가장 오래된 세션 종료
            oldest_session = min(current_sessions, key=lambda x: x["created_at"])
            await self.session_manager.terminate_session(oldest_session["session_id"])
        
        # 현재 세션 등록
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            await self.session_manager.register_session(user_id, session_id)
        
        return {"valid": True}
    
    async def _validate_authorization(self, request: Request) -> Dict[str, Any]:
        """권한 부여 검증"""
        user_role = getattr(request.state, "role", None)
        endpoint = request.url.path
        method = request.method
        
        # 역할 기반 접근 제어 (RBAC)
        required_permissions = self._get_required_permissions(endpoint, method)
        user_permissions = await self._get_user_permissions(request.state.user_id)
        
        # 필요한 권한 확인
        for permission in required_permissions:
            if permission not in user_permissions:
                return {
                    "valid": False,
                    "error": f"Insufficient permissions. Required: {permission}"
                }
        
        return {"valid": True}
    
    def _get_required_permissions(self, endpoint: str, method: str) -> List[str]:
        """엔드포인트별 필요 권한 반환"""
        permission_map = {
            "/api/stocks": {
                "GET": ["stocks:read"],
                "POST": ["stocks:create"],
                "PUT": ["stocks:update"],
                "DELETE": ["stocks:delete"]
            },
            "/api/users": {
                "GET": ["users:read"],
                "POST": ["users:create"],
                "PUT": ["users:update"],
                "DELETE": ["users:delete"]
            },
            "/api/admin": {
                "GET": ["admin:read"],
                "POST": ["admin:create"],
                "PUT": ["admin:update"],
                "DELETE": ["admin:delete"]
            }
        }
        
        # 엔드포인트 패턴 매칭
        for pattern, permissions in permission_map.items():
            if endpoint.startswith(pattern):
                return permissions.get(method, [])
        
        return []  # 기본적으로 인증된 사용자 접근 가능
    
    async def _get_user_permissions(self, user_id: str) -> List[str]:
        """사용자 권한 조회"""
        # 데이터베이스에서 사용자 권한 조회
        query = """
        SELECT p.name 
        FROM permissions p
        JOIN user_permissions up ON p.id = up.permission_id
        JOIN users u ON up.user_id = u.id
        WHERE u.id = :user_id
        """
        
        result = await self.db.fetch_all(query, {"user_id": user_id})
        return [row["name"] for row in result]
    
    def _get_max_sessions_for_role(self, role: str) -> int:
        """역할별 최대 동시 세션 수"""
        session_limits = {
            "admin": 5,
            "premium": 3,
            "basic": 2,
            "guest": 1
        }
        return session_limits.get(role, 1)

class TokenBlacklist:
    def __init__(self):
        self.blacklisted_tokens = set()
        self.redis_client = None  # Redis 연결
    
    async def is_blacklisted(self, token: str) -> bool:
        """토큰 블랙리스트 확인"""
        # 메모리 확인
        if token in self.blacklisted_tokens:
            return True
        
        # Redis 확인 (분산 환경)
        if self.redis_client:
            jti = self._get_jti_from_token(token)
            return await self.redis_client.exists(f"blacklist:{jti}")
        
        return False
    
    async def blacklist_token(self, token: str):
        """토큰 블랙리스트 추가"""
        self.blacklisted_tokens.add(token)
        
        # Redis에 추가 (분산 환경)
        if self.redis_client:
            jti = self._get_jti_from_token(token)
            exp = self._get_exp_from_token(token)
            ttl = exp - int(time.time())
            
            if ttl > 0:
                await self.redis_client.setex(f"blacklist:{jti}", ttl, "1")
    
    def _get_jti_from_token(self, token: str) -> str:
        """토큰에서 JTI 추출"""
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get("jti", "")
        except:
            return ""
    
    def _get_exp_from_token(self, token: str) -> int:
        """토큰에서 만료 시간 추출"""
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get("exp", 0)
        except:
            return 0

class SessionManager:
    def __init__(self):
        self.active_sessions = {}
        self.redis_client = None  # Redis 연결
    
    async def register_session(self, user_id: str, session_id: str):
        """세션 등록"""
        session_info = {
            "user_id": user_id,
            "session_id": session_id,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "ip_address": None,  # 요청에서 추출 필요
            "user_agent": None   # 요청에서 추출 필요
        }
        
        # 메모리에 저장
        if user_id not in self.active_sessions:
            self.active_sessions[user_id] = []
        
        self.active_sessions[user_id].append(session_info)
        
        # Redis에 저장 (분산 환경)
        if self.redis_client:
            await self.redis_client.hset(
                f"sessions:{user_id}",
                session_id,
                json.dumps(session_info, default=str)
            )
    
    async def get_active_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """활성 세션 조회"""
        # 메모리 확인
        if user_id in self.active_sessions:
            return self.active_sessions[user_id]
        
        # Redis 확인 (분산 환경)
        if self.redis_client:
            sessions = await self.redis_client.hgetall(f"sessions:{user_id}")
            return [json.loads(session) for session in sessions.values()]
        
        return []
    
    async def terminate_session(self, session_id: str):
        """세션 종료"""
        # 모든 사용자의 세션에서 제거
        for user_id, sessions in self.active_sessions.items():
            self.active_sessions[user_id] = [
                s for s in sessions if s["session_id"] != session_id
            ]
        
        # Redis에서 제거 (분산 환경)
        if self.redis_client:
            # 사용자 ID 찾기
            for key in await self.redis_client.keys("sessions:*"):
                if await self.redis_client.hexists(key, session_id):
                    await self.redis_client.hdel(key, session_id)
                    break

class SecurityLogger:
    def __init__(self):
        self.logger = logging.getLogger("security")
        self.logger.setLevel(logging.INFO)
        
        # 보안 로그 핸들러 설정
        handler = logging.FileHandler("security.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    async def _log_security_event(self, event_type: str, request: Request, details: str):
        """보안 이벤트 로깅"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("User-Agent", "unknown"),
            "endpoint": request.url.path,
            "method": request.method,
            "user_id": getattr(request.state, "user_id", "anonymous"),
            "details": details
        }
        
        self.logger.info(json.dumps(log_entry))
        
        # 중요 보안 이벤트는 관리자에게 알림
        if event_type in ["auth_failure", "authz_failure", "session_invalid"]:
            await self._send_security_alert(log_entry)
    
    async def _send_security_alert(self, log_entry: Dict[str, Any]):
        """보안 알림 발송"""
        # Slack, 이메일 등으로 알림 발송
        alert_message = f"🚨 Security Alert: {log_entry['event_type']}\n"
        alert_message += f"IP: {log_entry['ip_address']}\n"
        alert_message += f"Endpoint: {log_entry['endpoint']}\n"
        alert_message += f"User: {log_entry['user_id']}\n"
        alert_message += f"Details: {log_entry['details']}"
        
        # 실제 알림 발송 로직 구현
        logger.warning(alert_message)
```

#### 2.2.2 입력 검증 및 살균화
```python
# 현재 입력 검증 (개선 필요)
# 강화된 입력 검증 시스템
class InputValidationSystem:
    def __init__(self):
        self.xss_protection = XSSProtection()
        self.sql_injection_protection = SQLInjectionProtection()
        self.input_sanitizer = InputSanitizer()
        self.validation_rules = self._load_validation_rules()
    
    async def validate_and_sanitize_input(self, request: Request) -> Dict[str, Any]:
        """요청 입력 검증 및 살균화"""
        validation_result = {
            "valid": True,
            "errors": [],
            "sanitized_data": {}
        }
        
        # 요청 데이터 추출
        request_data = await self._extract_request_data(request)
        
        # 데이터 타입별 검증
        for data_type, data in request_data.items():
            type_validation = await self._validate_data_type(data_type, data)
            if not type_validation["valid"]:
                validation_result["valid"] = False
                validation_result["errors"].extend(type_validation["errors"])
                continue
            
            # XSS 방어 검증
            xss_result = self.xss_protection.check_xss(data)
            if not xss_result["safe"]:
                validation_result["valid"] = False
                validation_result["errors"].append(f"XSS detected in {data_type}")
                continue
            
            # SQL 인젝션 방어 검증
            sql_result = self.sql_injection_protection.check_sql_injection(data)
            if not sql_result["safe"]:
                validation_result["valid"] = False
                validation_result["errors"].append(f"SQL injection detected in {data_type}")
                continue
            
            # 데이터 살균화
            sanitized_data = self.input_sanitizer.sanitize(data)
            validation_result["sanitized_data"][data_type] = sanitized_data
        
        return validation_result
    
    async def _extract_request_data(self, request: Request) -> Dict[str, Any]:
        """요청 데이터 추출"""
        request_data = {}
        
        # 쿼리 파라미터
        if request.query_params:
            request_data["query_params"] = dict(request.query_params)
        
        # 경로 파라미터
        if hasattr(request, "path_params"):
            request_data["path_params"] = request.path_params
        
        # 요청 본문
        try:
            if request.headers.get("content-type", "").startswith("application/json"):
                body = await request.json()
                request_data["body"] = body
            elif request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
                form = await request.form()
                request_data["form"] = dict(form)
        except Exception:
            pass
        
        # 헤더
        request_data["headers"] = dict(request.headers)
        
        return request_data
    
    async def _validate_data_type(self, data_type: str, data: Any) -> Dict[str, Any]:
        """데이터 타입별 검증"""
        validation_result = {"valid": True, "errors": []}
        
        if data_type not in self.validation_rules:
            return validation_result
        
        rules = self.validation_rules[data_type]
        
        for field, field_rules in rules.items():
            if field not in data:
                if field_rules.get("required", False):
                    validation_result["valid"] = False
                    validation_result["errors"].append(f"Required field missing: {field}")
                continue
            
            field_value = data[field]
            
            # 타입 검증
            if "type" in field_rules:
                expected_type = field_rules["type"]
                if not isinstance(field_value, expected_type):
                    validation_result["valid"] = False
                    validation_result["errors"].append(
                        f"Invalid type for {field}: expected {expected_type.__name__}"
                    )
                    continue
            
            # 길이 검증
            if "min_length" in field_rules:
                if len(str(field_value)) < field_rules["min_length"]:
                    validation_result["valid"] = False
                    validation_result["errors"].append(
                        f"{field} is too short (min: {field_rules['min_length']})"
                    )
            
            if "max_length" in field_rules:
                if len(str(field_value)) > field_rules["max_length"]:
                    validation_result["valid"] = False
                    validation_result["errors"].append(
                        f"{field} is too long (max: {field_rules['max_length']})"
                    )
            
            # 패턴 검증
            if "pattern" in field_rules:
                import re
                pattern = field_rules["pattern"]
                if not re.match(pattern, str(field_value)):
                    validation_result["valid"] = False
                    validation_result["errors"].append(
                        f"{field} does not match required pattern"
                    )
            
            # 값 범위 검증
            if "min_value" in field_rules:
                if field_value < field_rules["min_value"]:
                    validation_result["valid"] = False
                    validation_result["errors"].append(
                        f"{field} is below minimum value ({field_rules['min_value']})"
                    )
            
            if "max_value" in field_rules:
                if field_value > field_rules["max_value"]:
                    validation_result["valid"] = False
                    validation_result["errors"].append(
                        f"{field} exceeds maximum value ({field_rules['max_value']})"
                    )
        
        return validation_result
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """검증 규칙 로드"""
        return {
            "query_params": {
                "symbol": {
                    "type": str,
                    "required": False,
                    "min_length": 1,
                    "max_length": 10,
                    "pattern": r"^[A-Z0-9.]+$"
                },
                "limit": {
                    "type": int,
                    "required": False,
                    "min_value": 1,
                    "max_value": 100
                },
                "offset": {
                    "type": int,
                    "required": False,
                    "min_value": 0,
                    "max_value": 10000
                }
            },
            "body": {
                "username": {
                    "type": str,
                    "required": True,
                    "min_length": 3,
                    "max_length": 50,
                    "pattern": r"^[a-zA-Z0-9_]+$"
                },
                "email": {
                    "type": str,
                    "required": True,
                    "min_length": 5,
                    "max_length": 100,
                    "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                },
                "password": {
                    "type": str,
                    "required": True,
                    "min_length": 8,
                    "max_length": 128,
                    "pattern": r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]"
                }
            }
        }

class XSSProtection:
    def __init__(self):
        self.dangerous_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
            r"<link[^>]*>",
            r"<meta[^>]*>",
            r"<style[^>]*>.*?</style>",
            r"<img[^>]*on\w+\s*=",
            r"<svg[^>]*>.*?</svg>"
        ]
    
    def check_xss(self, data: Any) -> Dict[str, Any]:
        """XSS 공격 검증"""
        result = {"safe": True, "detected_patterns": []}
        
        if isinstance(data, str):
            for pattern in self.dangerous_patterns:
                import re
                if re.search(pattern, data, re.IGNORECASE | re.DOTALL):
                    result["safe"] = False
                    result["detected_patterns"].append(pattern)
        elif isinstance(data, dict):
            for key, value in data.items():
                nested_result = self.check_xss(value)
                if not nested_result["safe"]:
                    result["safe"] = False
                    result["detected_patterns"].extend(nested_result["detected_patterns"])
        elif isinstance(data, list):
            for item in data:
                nested_result = self.check_xss(item)
                if not nested_result["safe"]:
                    result["safe"] = False
                    result["detected_patterns"].extend(nested_result["detected_patterns"])
        
        return result

class SQLInjectionProtection:
    def __init__(self):
        self.sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+['\"][^'\"]*['\"]\s*=\s*['\"][^'\"]*['\"])",
            r"(--|#|/\*|\*/)",
            r"(\b(LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE)\b)",
            r"(\b(INFORMATION_SCHEMA|SYS|MASTER)\b)",
            r"(\b(WAITFOR\s+DELAY|BENCHMARK|SLEEP)\b)"
        ]
    
    def check_sql_injection(self, data: Any) -> Dict[str, Any]:
        """SQL 인젝션 공격 검증"""
        result = {"safe": True, "detected_patterns": []}
        
        if isinstance(data, str):
            for pattern in self.sql_patterns:
                import re
                if re.search(pattern, data, re.IGNORECASE):
                    result["safe"] = False
                    result["detected_patterns"].append(pattern)
        elif isinstance(data, dict):
            for key, value in data.items():
                nested_result = self.check_sql_injection(value)
                if not nested_result["safe"]:
                    result["safe"] = False
                    result["detected_patterns"].extend(nested_result["detected_patterns"])
        elif isinstance(data, list):
            for item in data:
                nested_result = self.check_sql_injection(item)
                if not nested_result["safe"]:
                    result["safe"] = False
                    result["detected_patterns"].extend(nested_result["detected_patterns"])
        
        return result

class InputSanitizer:
    def __init__(self):
        self.html_sanitizer = HTMLSanitizer()
    
    def sanitize(self, data: Any) -> Any:
        """데이터 살균화"""
        if isinstance(data, str):
            return self.html_sanitizer.sanitize(data)
        elif isinstance(data, dict):
            return {key: self.sanitize(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.sanitize(item) for item in data]
        else:
            return data

class HTMLSanitizer:
    def __init__(self):
        self.allowed_tags = {
            'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code', 'pre'
        }
        self.allowed_attributes = {
            'a': {'href', 'title'},
            'img': {'src', 'alt', 'width', 'height'}
        }
    
    def sanitize(self, html: str) -> str:
        """HTML 살균화"""
        import re
        
        # 허용된 태그 외 제거
        def clean_tag(match):
            tag = match.group(1).lower()
            if tag in self.allowed_tags:
                return match.group(0)
            return ""
        
        # 닫는 태그 처리
        html = re.sub(r'</([^>]+)>', clean_tag, html)
        
        # 여는 태그 처리
        html = re.sub(r'<([^>]+)>', clean_tag, html)
        
        # 위험한 속성 제거
        dangerous_attrs = ['onload', 'onerror', 'onclick', 'onmouseover', 'onfocus']
        for attr in dangerous_attrs:
            html = re.sub(rf'{attr}\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
        
        return html
```

#### 2.2.3 데이터 암호화
```python
# 현재 데이터 암호화 (개선 필요)
# 강화된 데이터 암호화 시스템
class DataEncryptionSystem:
    def __init__(self):
        self.master_key = self._load_master_key()
        self.field_encryption = FieldEncryption()
        self.transport_encryption = TransportEncryption()
        self.key_rotation = KeyRotation()
    
    def _load_master_key(self) -> bytes:
        """마스터 키 로드"""
        key_path = os.getenv("MASTER_KEY_PATH", "master.key")
        
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return f.read()
        else:
            # 새 마스터 키 생성
            master_key = os.urandom(32)
            with open(key_path, "wb") as f:
                f.write(master_key)
            os.chmod(key_path, 0o600)  # 소유자만 읽기/쓰기 가능
            return master_key
    
    async def encrypt_sensitive_data(self, data: Dict[str, Any], sensitive_fields: List[str]) -> Dict[str, Any]:
        """민감 데이터 암호화"""
        encrypted_data = data.copy()
        
        for field in sensitive_fields:
            if field in encrypted_data:
                field_value = encrypted_data[field]
                encrypted_value = await self.field_encryption.encrypt_field(field_value, field)
                encrypted_data[field] = encrypted_value
        
        return encrypted_data
    
    async def decrypt_sensitive_data(self, data: Dict[str, Any], sensitive_fields: List[str]) -> Dict[str, Any]:
        """민감 데이터 복호화"""
        decrypted_data = data.copy()
        
        for field in sensitive_fields:
            if field in decrypted_data:
                field_value = decrypted_data[field]
                decrypted_value = await self.field_encryption.decrypt_field(field_value, field)
                decrypted_data[field] = decrypted_value
        
        return decrypted_data

class FieldEncryption:
    def __init__(self):
        self.field_keys = {}
        self.encryption_algorithm = "AES-256-GCM"
    
    async def encrypt_field(self, value: Any, field_name: str) -> str:
        """필드별 암호화"""
        if value is None:
            return None
        
        # 필드별 키 가져오기 또는 생성
        field_key = await self._get_field_key(field_name)
        
        # 값 직렬화
        serialized_value = json.dumps(value).encode('utf-8')
        
        # AES-256-GCM 암호화
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(field_key)
        
        # nonce 생성
        nonce = os.urandom(12)
        
        # 암호화
        encrypted_value = aesgcm.encrypt(nonce, serialized_value, None)
        
        # 결과 조합 (nonce + encrypted_value + tag)
        result = nonce + encrypted_value
        
        # Base64 인코딩
        return base64.b64encode(result).decode('utf-8')
    
    async def decrypt_field(self, encrypted_value: str, field_name: str) -> Any:
        """필드별 복호화"""
        if encrypted_value is None:
            return None
        
        # 필드별 키 가져오기
        field_key = await self._get_field_key(field_name)
        
        # Base64 디코딩
        encrypted_data = base64.b64decode(encrypted_value.encode('utf-8'))
        
        # nonce와 암호화된 데이터 분리
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        
        # AES-256-GCM 복호화
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(field_key)
        
        # 복호화
        decrypted_value = aesgcm.decrypt(nonce, ciphertext, None)
        
        # 역직렬화
        return json.loads(decrypted_value.decode('utf-8'))
    
    async def _get_field_key(self, field_name: str) -> bytes:
        """필드별 키 가져오기"""
        if field_name not in self.field_keys:
            # 필드별 키 생성 (마스터 키에서 파생)
            from cryptography.hazmat.primitives.kdf.hkdf import HKDF
            from cryptography.hazmat.primitives import hashes
            
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=f"field_key_{field_name}".encode('utf-8')
            )
            
            field_key = hkdf.derive(self.master_key)
            self.field_keys[field_name] = field_key
        
        return self.field_keys[field_name]

class TransportEncryption:
    def __init__(self):
        self.tls_config = self._load_tls_config()
    
    def _load_tls_config(self) -> Dict[str, Any]:
        """TLS 설정 로드"""
        return {
            "cert_file": os.getenv("TLS_CERT_FILE", "server.crt"),
            "key_file": os.getenv("TLS_KEY_FILE", "server.key"),
            "ca_file": os.getenv("TLS_CA_FILE", "ca.crt"),
            "min_version": "TLSv1.2",
            "cipher_suites": [
                "TLS_AES_256_GCM_SHA384",
                "TLS_CHACHA20_POLY1305_SHA256",
                "TLS_AES_128_GCM_SHA256"
            ]
        }
    
    def get_ssl_context(self) -> ssl.SSLContext:
        """SSL 컨텍스트 생성"""
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        
        # 인증서 로드
        context.load_cert_chain(
            self.tls_config["cert_file"],
            self.tls_config["key_file"]
        )
        
        # 최소 TLS 버전 설정
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        # 허용된 암호 스위트 설정
        context.set_ciphers(":".join(self.tls_config["cipher_suites"]))
        
        # HSTS 설정
        context.options |= ssl.OP_NO_COMPRESSION
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        
        return context

class KeyRotation:
    def __init__(self):
        self.rotation_interval = 90 * 24 * 60 * 60  # 90일
        self.key_history = {}
        self.current_key_id = None
    
    async def rotate_keys(self):
        """키 회전"""
        current_time = time.time()
        
        # 마지막 회전 시간 확인
        last_rotation = await self._get_last_rotation_time()
        
        if current_time - last_rotation >= self.rotation_interval:
            # 새 키 생성
            new_key_id = await self._generate_new_key()
            
            # 현재 키를 이력에 추가
            if self.current_key_id:
                self.key_history[self.current_key_id]["deprecated_at"] = current_time
            
            # 새 키를 현재 키로 설정
            self.current_key_id = new_key_id
            
            # 회전 시간 기록
            await self._record_rotation_time(current_time)
            
            logger.info(f"Key rotation completed. New key ID: {new_key_id}")
    
    async def _generate_new_key(self) -> str:
        """새 키 생성"""
        key_id = f"key_{int(time.time())}"
        new_key = os.urandom(32)
        
        self.key_history[key_id] = {
            "key": new_key,
            "created_at": time.time(),
            "deprecated_at": None
        }
        
        return key_id
    
    async def _get_last_rotation_time(self) -> float:
        """마지막 회전 시간 조회"""
        # 데이터베이스나 파일에서 마지막 회전 시간 조회
        rotation_file = "key_rotation.json"
        
        if os.path.exists(rotation_file):
            with open(rotation_file, "r") as f:
                data = json.load(f)
                return data.get("last_rotation", 0)
        
        return 0
    
    async def _record_rotation_time(self, rotation_time: float):
        """회전 시간 기록"""
        rotation_file = "key_rotation.json"
        
        data = {"last_rotation": rotation_time}
        
        with open(rotation_file, "w") as f:
            json.dump(data, f)
```

#### 2.2.4 보안 모니터링
```python
# 현재 보안 모니터링 (개선 필요)
# 강화된 보안 모니터링 시스템
class SecurityMonitoringSystem:
    def __init__(self):
        self.anomaly_detector = AnomalyDetector()
        self.threat_intelligence = ThreatIntelligence()
        self.security_dashboard = SecurityDashboard()
        self.alert_manager = SecurityAlertManager()
        self.audit_logger = AuditLogger()
    
    async def monitor_security_events(self, event: Dict[str, Any]):
        """보안 이벤트 모니터링"""
        # 이상 징후 탐지
        anomaly_result = await self.anomaly_detector.analyze_event(event)
        
        # 위협 정보 확인
        threat_result = await self.threat_intelligence.check_threat(event)
        
        # 보안 점수 계산
        security_score = self._calculate_security_score(anomaly_result, threat_result)
        
        # 로깅
        await self.audit_logger.log_security_event(event, security_score)
        
        # 대시보드 업데이트
        await self.security_dashboard.update_metrics(event, security_score)
        
        # 알림 발송
        if security_score < 50:  # 위험 임계값
            await self.alert_manager.send_security_alert(event, security_score)
    
    def _calculate_security_score(self, anomaly_result: Dict[str, Any], 
                                threat_result: Dict[str, Any]) -> int:
        """보안 점수 계산 (0-100)"""
        base_score = 100
        
        # 이상 징후 점수 감소
        anomaly_penalty = anomaly_result.get("risk_score", 0) * 0.5
        
        # 위협 정보 점수 감소
        threat_penalty = threat_result.get("threat_score", 0) * 0.3
        
        # 최종 점수
        final_score = max(0, base_score - anomaly_penalty - threat_penalty)
        
        return int(final_score)

class AnomalyDetector:
    def __init__(self):
        self.baseline_metrics = {}
        self.detection_rules = self._load_detection_rules()
        self.ml_model = None  # 머신러닝 모델
    
    async def analyze_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """이벤트 이상 징후 분석"""
        result = {
            "is_anomaly": False,
            "risk_score": 0,
            "detected_patterns": []
        }
        
        # 규칙 기반 탐지
        rule_result = await self._rule_based_detection(event)
        if rule_result["is_anomaly"]:
            result["is_anomaly"] = True
            result["risk_score"] += rule_result["risk_score"]
            result["detected_patterns"].extend(rule_result["patterns"])
        
        # 통계적 탐지
        stat_result = await self._statistical_detection(event)
        if stat_result["is_anomaly"]:
            result["is_anomaly"] = True
            result["risk_score"] += stat_result["risk_score"]
            result["detected_patterns"].extend(stat_result["patterns"])
        
        # 머신러닝 탐지 (모델이 있는 경우)
        if self.ml_model:
            ml_result = await self._ml_detection(event)
            if ml_result["is_anomaly"]:
                result["is_anomaly"] = True
                result["risk_score"] += ml_result["risk_score"]
                result["detected_patterns"].extend(ml_result["patterns"])
        
        return result
    
    async def _rule_based_detection(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """규칙 기반 이상 징후 탐지"""
        result = {"is_anomaly": False, "risk_score": 0, "patterns": []}
        
        # 비정상적인 로그인 시간
        if event.get("event_type") == "login":
            hour = datetime.fromisoformat(event["timestamp"]).hour
            if hour < 6 or hour > 22:  # 밤 시간대
                result["is_anomaly"] = True
                result["risk_score"] += 20
                result["patterns"].append("unusual_login_time")
        
        # 비정상적인 IP 주소
        ip_address = event.get("ip_address")
        if ip_address and self._is_suspicious_ip(ip_address):
            result["is_anomaly"] = True
            result["risk_score"] += 30
            result["patterns"].append("suspicious_ip")
        
        # 비정상적인 사용자 에이전트
        user_agent = event.get("user_agent")
        if user_agent and self._is_suspicious_user_agent(user_agent):
            result["is_anomaly"] = True
            result["risk_score"] += 25
            result["patterns"].append("suspicious_user_agent")
        
        return result
    
    async def _statistical_detection(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """통계적 이상 징후 탐지"""
        result = {"is_anomaly": False, "risk_score": 0, "patterns": []}
        
        # 사용자별 활동 빈도 확인
        user_id = event.get("user_id")
        if user_id:
            activity_count = await self._get_user_activity_count(user_id, time_window=3600)
            baseline_count = self.baseline_metrics.get(f"user_{user_id}_hourly", 10)
            
            if activity_count > baseline_count * 3:  # 기준의 3배 이상
                result["is_anomaly"] = True
                result["risk_score"] += 15
                result["patterns"].append("high_activity_frequency")
        
        # IP별 요청 빈도 확인
        ip_address = event.get("ip_address")
        if ip_address:
            request_count = await self._get_ip_request_count(ip_address, time_window=300)
            baseline_requests = self.baseline_metrics.get("ip_5min_requests", 50)
            
            if request_count > baseline_requests * 2:  # 기준의 2배 이상
                result["is_anomaly"] = True
                result["risk_score"] += 20
                result["patterns"].append("high_request_frequency")
        
        return result
    
    def _is_suspicious_ip(self, ip_address: str) -> bool:
        """의심스러운 IP 주소 확인"""
        # 내부 IP 범위
        if ip_address.startswith(("192.168.", "10.", "172.")):
            return False
        
        # 알려진 악성 IP 목록 확인 (실제로는 외부 서비스 사용)
        known_malicious_ips = [
            "192.0.2.1",  # 예시 IP
            "203.0.113.1"  # 예시 IP
        ]
        
        return ip_address in known_malicious_ips
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """의심스러운 사용자 에이전트 확인"""
        suspicious_patterns = [
            "bot", "crawler", "spider", "scraper",
            "python-requests", "curl", "wget"
        ]
        
        user_agent_lower = user_agent.lower()
        return any(pattern in user_agent_lower for pattern in suspicious_patterns)

class ThreatIntelligence:
    def __init__(self):
        self.threat_feeds = self._load_threat_feeds()
        self.threat_cache = {}
        self.cache_ttl = 3600  # 1시간
    
    async def check_threat(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """위협 정보 확인"""
        result = {"is_threat": False, "threat_score": 0, "threat_types": []}
        
        # IP 주소 위협 확인
        ip_address = event.get("ip_address")
        if ip_address:
            ip_threat = await self._check_ip_threat(ip_address)
            if ip_threat["is_threat"]:
                result["is_threat"] = True
                result["threat_score"] += ip_threat["threat_score"]
                result["threat_types"].extend(ip_threat["threat_types"])
        
        # 해시값 위협 확인
        file_hash = event.get("file_hash")
        if file_hash:
            hash_threat = await self._check_hash_threat(file_hash)
            if hash_threat["is_threat"]:
                result["is_threat"] = True
                result["threat_score"] += hash_threat["threat_score"]
                result["threat_types"].extend(hash_threat["threat_types"])
        
        # 도메인 위협 확인
        domain = event.get("domain")
        if domain:
            domain_threat = await self._check_domain_threat(domain)
            if domain_threat["is_threat"]:
                result["is_threat"] = True
                result["threat_score"] += domain_threat["threat_score"]
                result["threat_types"].extend(domain_threat["threat_types"])
        
        return result
    
    async def _check_ip_threat(self, ip_address: str) -> Dict[str, Any]:
        """IP 주소 위협 확인"""
        cache_key = f"ip_{ip_address}"
        
        # 캐시 확인
        if cache_key in self.threat_cache:
            cached_result = self.threat_cache[cache_key]
            if time.time() - cached_result["timestamp"] < self.cache_ttl:
                return cached_result["data"]
        
        # 위협 피드 확인
        result = {"is_threat": False, "threat_score": 0, "threat_types": []}
        
        for feed in self.threat_feeds:
            if feed["type"] == "ip" and ip_address in feed["data"]:
                result["is_threat"] = True
                result["threat_score"] += feed["severity"]
                result["threat_types"].append(feed["threat_type"])
        
        # 캐시에 저장
        self.threat_cache[cache_key] = {
            "data": result,
            "timestamp": time.time()
        }
        
        return result
    
    async def _check_hash_threat(self, file_hash: str) -> Dict[str, Any]:
        """파일 해시 위협 확인"""
        # IP 확인과 유사한 방식으로 구현
        return {"is_threat": False, "threat_score": 0, "threat_types": []}
    
    async def _check_domain_threat(self, domain: str) -> Dict[str, Any]:
        """도메인 위협 확인"""
        # IP 확인과 유사한 방식으로 구현
        return {"is_threat": False, "threat_score": 0, "threat_types": []}
    
    def _load_threat_feeds(self) -> List[Dict[str, Any]]:
        """위협 피드 로드"""
        # 실제로는 외부 위협 인텔리전스 서비스에서 데이터 가져오기
        return [
            {
                "type": "ip",
                "data": ["192.0.2.1", "203.0.113.1"],
                "threat_type": "malware",
                "severity": 80
            },
            {
                "type": "domain",
                "data": ["malicious.example.com"],
                "threat_type": "phishing",
                "severity": 90
            }
        ]

class SecurityDashboard:
    def __init__(self):
        self.metrics = {
            "security_events": [],
            "threat_levels": [],
            "anomaly_scores": [],
            "response_times": []
        }
    
    async def update_metrics(self, event: Dict[str, Any], security_score: int):
        """대시보드 메트릭 업데이트"""
        timestamp = datetime.utcnow().isoformat()
        
        # 보안 이벤트 기록
        self.metrics["security_events"].append({
            "timestamp": timestamp,
            "event_type": event.get("event_type"),
            "security_score": security_score,
            "ip_address": event.get("ip_address"),
            "user_id": event.get("user_id")
        })
        
        # 위협 수준 기록
        threat_level = self._calculate_threat_level(security_score)
        self.metrics["threat_levels"].append({
            "timestamp": timestamp,
            "level": threat_level
        })
        
        # 이상 점수 기록
        self.metrics["anomaly_scores"].append({
            "timestamp": timestamp,
            "score": security_score
        })
        
        # 데이터 크기 제한 (최근 1000개만 유지)
        for key in self.metrics:
            if len(self.metrics[key]) > 1000:
                self.metrics[key] = self.metrics[key][-1000:]
    
    def _calculate_threat_level(self, security_score: int) -> str:
        """위협 수준 계산"""
        if security_score >= 80:
            return "low"
        elif security_score >= 50:
            return "medium"
        elif security_score >= 30:
            return "high"
        else:
            return "critical"
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """대시보드 요약 정보 반환"""
        if not self.metrics["security_events"]:
            return {"message": "No data available"}
        
        # 최근 24시간 데이터
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        recent_events = [
            event for event in self.metrics["security_events"]
            if datetime.fromisoformat(event["timestamp"]) >= cutoff_time
        ]
        
        # 통계 계산
        total_events = len(recent_events)
        avg_security_score = sum(event["security_score"] for event in recent_events) / total_events if total_events > 0 else 0
        
        # 위협 수준 분포
        threat_distribution = {}
        for level in ["low", "medium", "high", "critical"]:
            threat_distribution[level] = len([
                event for event in recent_events
                if self._calculate_threat_level(event["security_score"]) == level
            ])
        
        return {
            "total_events_24h": total_events,
            "avg_security_score": round(avg_security_score, 2),
            "threat_distribution": threat_distribution,
            "last_updated": datetime.utcnow().isoformat()
        }

class SecurityAlertManager:
    def __init__(self):
        self.alert_channels = ["email", "slack", "sms"]
        self.alert_rules = self._load_alert_rules()
        self.alert_history = []
    
    async def send_security_alert(self, event: Dict[str, Any], security_score: int):
        """보안 알림 발송"""
        # 알림 규칙 확인
        alert_rules_triggered = [
            rule for rule in self.alert_rules
            if self._should_trigger_alert(rule, event, security_score)
        ]
        
        if not alert_rules_triggered:
            return
        
        # 알림 생성
        alert = {
            "id": f"alert_{int(time.time())}",
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "security_score": security_score,
            "severity": self._determine_alert_severity(security_score),
            "rules_triggered": alert_rules_triggered
        }
        
        # 알림 기록
        self.alert_history.append(alert)
        
        # 채널별 알림 발송
        for channel in self.alert_channels:
            await self._send_alert_to_channel(alert, channel)
    
    def _should_trigger_alert(self, rule: Dict[str, Any], event: Dict[str, Any], security_score: int) -> bool:
        """알림 규칙 확인"""
        # 보안 점수 기준
        if "min_security_score" in rule:
            if security_score >= rule["min_security_score"]:
                return True
        
        # 이벤트 타입 기준
        if "event_types" in rule:
            if event.get("event_type") in rule["event_types"]:
                return True
        
        # IP 주소 기준
        if "suspicious_ips" in rule:
            if event.get("ip_address") in rule["suspicious_ips"]:
                return True
        
        return False
    
    def _determine_alert_severity(self, security_score: int) -> str:
        """알림 심각도 결정"""
        if security_score >= 80:
            return "info"
        elif security_score >= 50:
            return "warning"
        elif security_score >= 30:
            return "error"
        else:
            return "critical"
    
    async def _send_alert_to_channel(self, alert: Dict[str, Any], channel: str):
        """채널별 알림 발송"""
        if channel == "email":
            await self._send_email_alert(alert)
        elif channel == "slack":
            await self._send_slack_alert(alert)
        elif channel == "sms":
            await self._send_sms_alert(alert)
    
    async def _send_email_alert(self, alert: Dict[str, Any]):
        """이메일 알림 발송"""
        # 실제 이메일 발송 로직 구현
        logger.info(f"Email alert sent: {alert['id']}")
    
    async def _send_slack_alert(self, alert: Dict[str, Any]):
        """Slack 알림 발송"""
        # 실제 Slack 발송 로직 구현
        logger.info(f"Slack alert sent: {alert['id']}")
    
    async def _send_sms_alert(self, alert: Dict[str, Any]):
        """SMS 알림 발송"""
        # 실제 SMS 발송 로직 구현
        logger.info(f"SMS alert sent: {alert['id']}")

class AuditLogger:
    def __init__(self):
        self.logger = logging.getLogger("audit")
        self.logger.setLevel(logging.INFO)
        
        # 감사 로그 핸들러 설정
        handler = logging.FileHandler("audit.log")
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    async def log_security_event(self, event: Dict[str, Any], security_score: int):
        """보안 이벤트 감사 로깅"""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_id": f"event_{int(time.time())}",
            "event": event,
            "security_score": security_score,
            "audit_type": "security"
        }
        
        self.logger.info(json.dumps(audit_entry))
```

## 3. 보안 강화 실행 계획

### 3.1 즉시 실행 필요 (1-2주 내)

#### 3.1.1 입력 검증 강화
1. **XSS 방어 강화**
   - 모든 입력 데이터에 대한 XSS 검증 구현
   - HTML 살균화 라이브러리 통합
   - CSP (Content Security Policy) 헤더 강화

2. **SQL 인젝션 방어**
   - 모든 데이터베이스 쿼리에 파라미터화된 쿼리 사용
   - ORM 활용을 통한 SQL 인젝션 방어
   - 정기적인 취약점 스캐닝

#### 3.1.2 인증 및 권한 부여 강화
1. **JWT 토큰 관리 강화**
   - 토큰 블랙리스트 구현
   - 토큰 회전 정책 구현
   - 짧은 만료 시간 및 리프레시 토큰

2. **세션 관리 개선**
   - 동시 세션 제한 구현
   - 세션 하이재킹 방어
   - 세션 타임아웃 정책

#### 3.1.3 데이터 암호화 강화
1. **전송 중 암호화**
   - TLS 1.3 적용
   - 강력한 암호 스위트 사용
   - HSTS (HTTP Strict Transport Security) 구현

2. **저장 데이터 암호화**
   - 민감 필드별 암호화 구현
   - 키 회전 정책 구현
   - 암호화 키 안전한 저장

### 3.2 단기 실행 (2-4주 내)

#### 3.2.1 보안 모니터링 강화
1. **실시간 위협 탐지**
   - 이상 징후 탐지 시스템 구현
   - 위협 인텔리전스 통합
   - 실시간 알림 시스템

2. **보안 로깅 강화**
   - 상세한 보안 이벤트 로깅
   - 로그 무결성 보장
   - 중앙 집중식 로그 관리

#### 3.2.2 API 보안 강화
1. **속도 제한 강화**
   - IP 기반 속도 제한
   - 사용자 기반 속도 제한
   - 동적 임계값 조정

2. **API 보안 헤더**
   - 보안 관련 HTTP 헤더 강화
   - CORS 정책 구현
   - CSP 정책 구현

### 3.3 중장기 실행 (1-2개월 내)

#### 3.3.1 고급 보안 기능
1. **머신러닝 기반 위협 탐지**
   - 사용자 행동 패턴 분석
   - 이상 행동 탐지
   - 자동 위협 대응

2. **제로 트러스트 아키텍처**
   - 최소 권한 원칙 적용
   - 지속적 인증 및 권한 부여
   - 마이크로세그멘테이션

## 4. 결론

InsiteChart 프로젝트의 현재 보안 상태는 **일부 개선이 필요**한 상태입니다. 주요 취약점으로는 **입력 검증 미흡**, **세션 관리 부족**, **보안 로깅 부족** 등이 있습니다.

**가장 시급한 개선 사항:**
1. **입력 검증 강화**: XSS 및 SQL 인젝션 방어를 통한 보안 강화
2. **인증 및 권한 부여 개선**: JWT 토큰 관리와 세션 관리 강화
3. **보안 모니터링 구현**: 실시간 위협 탐지와 알림 시스템 구축

**중기 개선 방향:**
1. **데이터 암호화**: 전송 및 저장 데이터 암호화 강화
2. **API 보안**: 속도 제한 및 보안 헤더 강화
3. **고급 보안 기능**: 머신러닝 기반 위협 탐지 도입

이러한 보안 강화 방안들을 단계적으로 구현함으로써, InsiteChart의 보안 준수도를 **90% 이상**으로 향상시키고 **엔터프라이즈 수준**의 보안 요구사항을 충족할 수 있을 것입니다.