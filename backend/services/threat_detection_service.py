"""
Automated Threat Detection and Response Service for InsiteChart platform.

This service provides real-time threat detection, automated response actions,
and security monitoring capabilities to protect the platform from various threats.
"""

import asyncio
import logging
import json
import os
import re
import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import uuid

from ..cache.unified_cache import UnifiedCacheManager


class ThreatType(str, Enum):
    """Types of security threats."""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    BRUTE_FORCE = "brute_force"
    DDOS = "ddos"
    SUSPICIOUS_REQUEST = "suspicious_request"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    MALICIOUS_PAYLOAD = "malicious_payload"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    RATE_LIMIT_VIOLATION = "rate_limit_violation"


class ThreatSeverity(str, Enum):
    """Threat severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResponseAction(str, Enum):
    """Automated response actions."""
    BLOCK_IP = "block_ip"
    RATE_LIMIT = "rate_limit"
    LOGOUT_USER = "logout_user"
    DISABLE_ACCOUNT = "disable_account"
    NOTIFY_ADMIN = "notify_admin"
    REQUIRE_MFA = "require_mfa"
    QUARANTINE_SESSION = "quarantine_session"
    BLOCK_REQUEST = "block_request"
    INCREMENT_RISK_SCORE = "increment_risk_score"


@dataclass
class ThreatEvent:
    """Threat event record."""
    event_id: str
    threat_type: ThreatType
    severity: ThreatSeverity
    source_ip: str
    user_id: Optional[str]
    timestamp: datetime
    description: str
    request_data: Dict[str, Any]
    response_data: Dict[str, Any]
    automated_actions: List[str]
    risk_score: float
    status: str
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None


@dataclass
class SecurityRule:
    """Security rule for threat detection."""
    rule_id: str
    name: str
    description: str
    threat_type: ThreatType
    severity: ThreatSeverity
    enabled: bool
    pattern: str
    response_actions: List[ResponseAction]
    conditions: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass
class SecurityPolicy:
    """Security policy configuration."""
    policy_id: str
    name: str
    description: str
    rules: List[str]
    enabled: bool
    priority: int
    created_at: datetime
    updated_at: datetime


@dataclass
class RiskProfile:
    """Risk profile for IP address or user."""
    profile_id: str
    identifier: str  # IP address or user ID
    risk_score: float
    last_updated: datetime
    threat_count: int
    blocked_until: Optional[datetime]
    notes: List[str]


class ThreatDetectionService:
    """Automated threat detection and response service."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = self._load_configuration()
        
        # Data storage
        self.threat_events: Dict[str, ThreatEvent] = {}
        self.security_rules: Dict[str, SecurityRule] = {}
        self.security_policies: Dict[str, SecurityPolicy] = {}
        self.risk_profiles: Dict[str, RiskProfile] = {}
        
        # Detection settings
        self.detection_enabled = True
        self.auto_response_enabled = True
        self.learning_enabled = True
        
        # Cache TTL settings
        self.threat_cache_ttl = 86400  # 24 hours
        self.risk_cache_ttl = 3600  # 1 hour
        self.rule_cache_ttl = 1800  # 30 minutes
        
        # Risk thresholds
        self.risk_thresholds = {
            "low": 20.0,
            "medium": 50.0,
            "high": 75.0,
            "critical": 90.0
        }
        
        # Rate limiting
        self.request_history = defaultdict(lambda: deque(maxlen=1000))
        self.blocked_ips = {}
        
        # Anomaly detection
        self.behavioral_patterns = {}
        self.anomaly_threshold = 2.0  # Standard deviations
        
        # Initialize default security rules
        self._initialize_default_rules()
        
        # Start monitoring tasks
        if self.detection_enabled:
            asyncio.create_task(self._monitoring_loop())
        
        self.logger.info("ThreatDetectionService initialized")
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load threat detection configuration."""
        try:
            return {
                "max_failed_attempts": int(os.getenv('MAX_FAILED_ATTEMPTS', '5')),
                "lockout_duration": int(os.getenv('LOCKOUT_DURATION', '900')),  # 15 minutes
                "rate_limit_requests": int(os.getenv('RATE_LIMIT_REQUESTS', '100')),
                "rate_limit_window": int(os.getenv('RATE_LIMIT_WINDOW', '60')),  # 1 minute
                "anomaly_detection_enabled": os.getenv('ANOMALY_DETECTION_ENABLED', 'true').lower() == 'true',
                "auto_block_enabled": os.getenv('AUTO_BLOCK_ENABLED', 'true').lower() == 'true',
                "admin_notification_email": os.getenv('ADMIN_NOTIFICATION_EMAIL', 'security@insitechart.com'),
                "risk_decay_rate": float(os.getenv('RISK_DECAY_RATE', '0.1')),
                "max_risk_score": float(os.getenv('MAX_RISK_SCORE', '100.0')),
                "log_retention_days": int(os.getenv('LOG_RETENTION_DAYS', '90')),
                "ml_model_path": os.getenv('ML_MODEL_PATH', 'models/threat_detection.pkl'),
                "update_rules_interval": int(os.getenv('UPDATE_RULES_INTERVAL', '3600'))  # 1 hour
            }
        except Exception as e:
            self.logger.error(f"Error loading threat detection configuration: {str(e)}")
            return {}
    
    def _initialize_default_rules(self):
        """Initialize default security rules."""
        try:
            default_rules = [
                SecurityRule(
                    rule_id="sql_injection_basic",
                    name="Basic SQL Injection Detection",
                    description="Detects common SQL injection patterns",
                    threat_type=ThreatType.SQL_INJECTION,
                    severity=ThreatSeverity.HIGH,
                    enabled=True,
                    pattern=r"(?i)(union|select|insert|update|delete|drop|create|alter|exec|execute)\s+",
                    response_actions=[ResponseAction.BLOCK_REQUEST, ResponseAction.INCREMENT_RISK_SCORE, ResponseAction.NOTIFY_ADMIN],
                    conditions={"min_confidence": 0.7},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                SecurityRule(
                    rule_id="xss_basic",
                    name="Basic XSS Detection",
                    description="Detects common XSS attack patterns",
                    threat_type=ThreatType.XSS,
                    severity=ThreatSeverity.HIGH,
                    enabled=True,
                    pattern=r"(?i)(<script|javascript:|onload=|onerror=|alert\(|document\.)",
                    response_actions=[ResponseAction.BLOCK_REQUEST, ResponseAction.INCREMENT_RISK_SCORE],
                    conditions={"min_confidence": 0.6},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                SecurityRule(
                    rule_id="brute_force_detection",
                    name="Brute Force Attack Detection",
                    description="Detects brute force login attempts",
                    threat_type=ThreatType.BRUTE_FORCE,
                    severity=ThreatSeverity.MEDIUM,
                    enabled=True,
                    pattern=r"",  # Pattern-based detection not used for this rule
                    response_actions=[ResponseAction.BLOCK_IP, ResponseAction.INCREMENT_RISK_SCORE, ResponseAction.NOTIFY_ADMIN],
                    conditions={"max_attempts": 5, "time_window": 300},  # 5 attempts in 5 minutes
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                SecurityRule(
                    rule_id="ddos_detection",
                    name="DDoS Attack Detection",
                    description="Detects potential DDoS attacks",
                    threat_type=ThreatType.DDOS,
                    severity=ThreatSeverity.CRITICAL,
                    enabled=True,
                    pattern=r"",  # Pattern-based detection not used for this rule
                    response_actions=[ResponseAction.BLOCK_IP, ResponseAction.RATE_LIMIT, ResponseAction.NOTIFY_ADMIN],
                    conditions={"requests_per_minute": 1000, "burst_threshold": 500},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                SecurityRule(
                    rule_id="suspicious_payload",
                    name="Suspicious Payload Detection",
                    description="Detects suspicious request payloads",
                    threat_type=ThreatType.MALICIOUS_PAYLOAD,
                    severity=ThreatSeverity.MEDIUM,
                    enabled=True,
                    pattern=r"(?i)(cmd\.exe|powershell|bash|sh|eval\(|base64_decode|shell_exec)",
                    response_actions=[ResponseAction.BLOCK_REQUEST, ResponseAction.INCREMENT_RISK_SCORE],
                    conditions={"min_confidence": 0.5},
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            ]
            
            for rule in default_rules:
                self.security_rules[rule.rule_id] = rule
            
            self.logger.info(f"Initialized {len(default_rules)} default security rules")
            
        except Exception as e:
            self.logger.error(f"Error initializing default rules: {str(e)}")
    
    async def _monitoring_loop(self):
        """Main monitoring loop for threat detection."""
        while True:
            try:
                # Clean up old threat events
                await self._cleanup_old_events()
                
                # Update risk scores (decay over time)
                await self._update_risk_scores()
                
                # Update security rules from external source
                if self.config.get("update_rules_interval"):
                    await self._update_security_rules()
                
                # Analyze behavioral patterns
                if self.learning_enabled:
                    await self._analyze_behavioral_patterns()
                
                # Wait for next cycle (run every 5 minutes)
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def analyze_request(
        self,
        request_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze incoming request for threats."""
        try:
            if not self.detection_enabled:
                return {"threat_detected": False, "risk_score": 0.0}
            
            source_ip = request_data.get("client_ip", "unknown")
            request_method = request_data.get("method", "GET")
            request_path = request_data.get("path", "/")
            request_headers = request_data.get("headers", {})
            request_body = request_data.get("body", "")
            
            # Initialize results
            threats_detected = []
            total_risk_score = 0.0
            response_actions = []
            
            # Check against blocked IPs
            if await self._is_ip_blocked(source_ip):
                return {
                    "threat_detected": True,
                    "threat_type": ThreatType.UNAUTHORIZED_ACCESS,
                    "severity": ThreatSeverity.HIGH,
                    "risk_score": 100.0,
                    "actions": [ResponseAction.BLOCK_REQUEST],
                    "blocked": True
                }
            
            # Rate limiting check
            rate_limit_result = await self._check_rate_limit(source_ip)
            if rate_limit_result["violated"]:
                threats_detected.append({
                    "type": ThreatType.RATE_LIMIT_VIOLATION,
                    "severity": ThreatSeverity.MEDIUM,
                    "risk_score": 30.0,
                    "description": rate_limit_result["description"]
                })
                total_risk_score += 30.0
                response_actions.append(ResponseAction.RATE_LIMIT)
            
            # Pattern-based detection
            for rule_id, rule in self.security_rules.items():
                if not rule.enabled:
                    continue
                
                threat_result = await self._check_security_rule(rule, request_data)
                if threat_result["detected"]:
                    threats_detected.append({
                        "type": rule.threat_type,
                        "severity": rule.severity,
                        "risk_score": threat_result["risk_score"],
                        "description": threat_result["description"],
                        "rule_id": rule_id
                    })
                    total_risk_score += threat_result["risk_score"]
                    response_actions.extend(rule.response_actions)
            
            # Anomaly detection
            if self.config.get("anomaly_detection_enabled"):
                anomaly_result = await self._detect_anomalies(source_ip, user_id, request_data)
                if anomaly_result["detected"]:
                    threats_detected.append({
                        "type": ThreatType.ANOMALOUS_BEHAVIOR,
                        "severity": ThreatSeverity.MEDIUM,
                        "risk_score": anomaly_result["risk_score"],
                        "description": anomaly_result["description"]
                    })
                    total_risk_score += anomaly_result["risk_score"]
                    response_actions.append(ResponseAction.INCREMENT_RISK_SCORE)
            
            # Update request history
            self._update_request_history(source_ip, request_data)
            
            # Create threat events if needed
            if threats_detected:
                for threat in threats_detected:
                    await self._create_threat_event(
                        threat_type=threat["type"],
                        severity=threat["severity"],
                        source_ip=source_ip,
                        user_id=user_id,
                        description=threat["description"],
                        request_data=request_data,
                        response_data={"actions": response_actions},
                        risk_score=threat["risk_score"]
                    )
                
                # Update risk profile
                await self._update_risk_profile(source_ip, user_id, total_risk_score)
                
                # Execute automated responses
                if self.auto_response_enabled:
                    await self._execute_response_actions(source_ip, user_id, response_actions)
                
                return {
                    "threat_detected": True,
                    "threats": threats_detected,
                    "total_risk_score": total_risk_score,
                    "actions": response_actions
                }
            
            return {
                "threat_detected": False,
                "risk_score": total_risk_score
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing request: {str(e)}")
            return {"threat_detected": False, "error": str(e)}
    
    async def _check_security_rule(self, rule: SecurityRule, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check if request matches a security rule."""
        try:
            # Special handling for different rule types
            if rule.threat_type == ThreatType.BRUTE_FORCE:
                return await self._check_brute_force(rule, request_data)
            elif rule.threat_type == ThreatType.DDOS:
                return await self._check_ddos(rule, request_data)
            elif rule.pattern:
                return await self._check_pattern_rule(rule, request_data)
            else:
                return {"detected": False, "risk_score": 0.0}
                
        except Exception as e:
            self.logger.error(f"Error checking security rule {rule.rule_id}: {str(e)}")
            return {"detected": False, "error": str(e)}
    
    async def _check_pattern_rule(self, rule: SecurityRule, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check pattern-based security rule."""
        try:
            # Extract relevant data from request
            request_body = request_data.get("body", "")
            request_path = request_data.get("path", "")
            query_params = request_data.get("query_params", {})
            
            # Combine all text data for pattern matching
            text_data = f"{request_path} {request_body}"
            for key, value in query_params.items():
                text_data += f" {key}={value}"
            
            # Check pattern
            matches = re.findall(rule.pattern, text_data)
            if matches:
                confidence = min(len(matches) * 0.2, 1.0)  # Confidence based on number of matches
                min_confidence = rule.conditions.get("min_confidence", 0.5)
                
                if confidence >= min_confidence:
                    risk_score = self._calculate_risk_score(rule.severity, confidence)
                    return {
                        "detected": True,
                        "risk_score": risk_score,
                        "description": f"Pattern '{rule.pattern}' matched {len(matches)} times",
                        "confidence": confidence,
                        "matches": matches
                    }
            
            return {"detected": False, "risk_score": 0.0}
            
        except Exception as e:
            self.logger.error(f"Error checking pattern rule {rule.rule_id}: {str(e)}")
            return {"detected": False, "error": str(e)}
    
    async def _check_brute_force(self, rule: SecurityRule, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check for brute force attacks."""
        try:
            source_ip = request_data.get("client_ip", "unknown")
            request_path = request_data.get("path", "")
            max_attempts = rule.conditions.get("max_attempts", 5)
            time_window = rule.conditions.get("time_window", 300)  # 5 minutes
            
            # Only check login endpoints
            if "login" not in request_path.lower():
                return {"detected": False, "risk_score": 0.0}
            
            # Get recent login attempts
            current_time = time.time()
            recent_attempts = [
                req_time for req_time in self.request_history[source_ip]
                if current_time - req_time <= time_window
            ]
            
            if len(recent_attempts) >= max_attempts:
                risk_score = self._calculate_risk_score(rule.severity, 1.0)
                return {
                    "detected": True,
                    "risk_score": risk_score,
                    "description": f"{len(recent_attempts)} login attempts in {time_window} seconds",
                    "attempts": len(recent_attempts),
                    "time_window": time_window
                }
            
            return {"detected": False, "risk_score": 0.0}
            
        except Exception as e:
            self.logger.error(f"Error checking brute force: {str(e)}")
            return {"detected": False, "error": str(e)}
    
    async def _check_ddos(self, rule: SecurityRule, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check for DDoS attacks."""
        try:
            source_ip = request_data.get("client_ip", "unknown")
            requests_per_minute = rule.conditions.get("requests_per_minute", 1000)
            burst_threshold = rule.conditions.get("burst_threshold", 500)
            
            # Get recent requests
            current_time = time.time()
            one_minute_ago = current_time - 60
            recent_requests = [
                req_time for req_time in self.request_history[source_ip]
                if req_time >= one_minute_ago
            ]
            
            # Check sustained rate
            if len(recent_requests) >= requests_per_minute:
                risk_score = self._calculate_risk_score(rule.severity, 1.0)
                return {
                    "detected": True,
                    "risk_score": risk_score,
                    "description": f"{len(recent_requests)} requests in last minute",
                    "requests_per_minute": len(recent_requests),
                    "threshold": requests_per_minute
                }
            
            # Check burst rate (last 10 seconds)
            ten_seconds_ago = current_time - 10
            burst_requests = [
                req_time for req_time in self.request_history[source_ip]
                if req_time >= ten_seconds_ago
            ]
            
            if len(burst_requests) >= burst_threshold:
                risk_score = self._calculate_risk_score(rule.severity, 0.8)
                return {
                    "detected": True,
                    "risk_score": risk_score,
                    "description": f"{len(burst_requests)} requests in last 10 seconds",
                    "burst_requests": len(burst_requests),
                    "threshold": burst_threshold
                }
            
            return {"detected": False, "risk_score": 0.0}
            
        except Exception as e:
            self.logger.error(f"Error checking DDoS: {str(e)}")
            return {"detected": False, "error": str(e)}
    
    async def _detect_anomalies(
        self, 
        source_ip: str, 
        user_id: Optional[str], 
        request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect anomalous behavior using statistical analysis."""
        try:
            # This is a simplified anomaly detection
            # In production, you would use machine learning models
            
            identifier = user_id or source_ip
            if identifier not in self.behavioral_patterns:
                # Initialize baseline for new identifier
                self.behavioral_patterns[identifier] = {
                    "request_count": 0,
                    "unique_paths": set(),
                    "avg_request_size": 0,
                    "request_times": deque(maxlen=100),
                    "last_seen": time.time()
                }
                return {"detected": False, "risk_score": 0.0}
            
            pattern = self.behavioral_patterns[identifier]
            current_time = time.time()
            
            # Update pattern
            pattern["request_count"] += 1
            pattern["unique_paths"].add(request_data.get("path", "/"))
            pattern["request_times"].append(current_time)
            pattern["last_seen"] = current_time
            
            # Calculate request size
            request_size = len(str(request_data.get("body", "")))
            pattern["avg_request_size"] = (
                (pattern["avg_request_size"] * (pattern["request_count"] - 1) + request_size) /
                pattern["request_count"]
            )
            
            # Anomaly checks
            anomalies = []
            total_risk_score = 0.0
            
            # Check request frequency anomaly
            if len(pattern["request_times"]) >= 10:
                recent_times = list(pattern["request_times"])[-10:]
                intervals = [recent_times[i] - recent_times[i-1] for i in range(1, len(recent_times))]
                avg_interval = sum(intervals) / len(intervals)
                
                if avg_interval < 1.0:  # Less than 1 second between requests
                    anomalies.append("High request frequency")
                    total_risk_score += 20.0
            
            # Check path diversity anomaly
            if len(pattern["unique_paths"]) > 50:
                anomalies.append("Unusual path diversity")
                total_risk_score += 15.0
            
            # Check request size anomaly
            if request_size > pattern["avg_request_size"] * 5:
                anomalies.append("Unusually large request")
                total_risk_score += 25.0
            
            if anomalies:
                return {
                    "detected": True,
                    "risk_score": total_risk_score,
                    "description": f"Anomalies detected: {', '.join(anomalies)}",
                    "anomalies": anomalies
                }
            
            return {"detected": False, "risk_score": 0.0}
            
        except Exception as e:
            self.logger.error(f"Error detecting anomalies: {str(e)}")
            return {"detected": False, "error": str(e)}
    
    async def _check_rate_limit(self, source_ip: str) -> Dict[str, Any]:
        """Check if IP has exceeded rate limits."""
        try:
            rate_limit_requests = self.config.get("rate_limit_requests", 100)
            rate_limit_window = self.config.get("rate_limit_window", 60)
            
            current_time = time.time()
            window_start = current_time - rate_limit_window
            
            # Count requests in window
            recent_requests = [
                req_time for req_time in self.request_history[source_ip]
                if req_time >= window_start
            ]
            
            if len(recent_requests) >= rate_limit_requests:
                return {
                    "violated": True,
                    "description": f"Rate limit exceeded: {len(recent_requests)} requests in {rate_limit_window} seconds",
                    "requests": len(recent_requests),
                    "limit": rate_limit_requests
                }
            
            return {"violated": False}
            
        except Exception as e:
            self.logger.error(f"Error checking rate limit: {str(e)}")
            return {"violated": False, "error": str(e)}
    
    async def _is_ip_blocked(self, source_ip: str) -> bool:
        """Check if IP address is blocked."""
        try:
            if source_ip in self.blocked_ips:
                block_expiry = self.blocked_ips[source_ip]
                if datetime.utcnow() < block_expiry:
                    return True
                else:
                    # Block expired, remove it
                    del self.blocked_ips[source_ip]
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking IP block: {str(e)}")
            return False
    
    def _update_request_history(self, source_ip: str, request_data: Dict[str, Any]):
        """Update request history for IP address."""
        try:
            current_time = time.time()
            self.request_history[source_ip].append(current_time)
            
        except Exception as e:
            self.logger.error(f"Error updating request history: {str(e)}")
    
    def _calculate_risk_score(self, severity: ThreatSeverity, confidence: float) -> float:
        """Calculate risk score based on severity and confidence."""
        try:
            base_scores = {
                ThreatSeverity.LOW: 20.0,
                ThreatSeverity.MEDIUM: 40.0,
                ThreatSeverity.HIGH: 70.0,
                ThreatSeverity.CRITICAL: 90.0
            }
            
            base_score = base_scores.get(severity, 20.0)
            return base_score * confidence
            
        except Exception as e:
            self.logger.error(f"Error calculating risk score: {str(e)}")
            return 20.0
    
    async def _create_threat_event(
        self,
        threat_type: ThreatType,
        severity: ThreatSeverity,
        source_ip: str,
        user_id: Optional[str],
        description: str,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        risk_score: float
    ):
        """Create a threat event record."""
        try:
            event_id = str(uuid.uuid4())
            current_time = datetime.utcnow()
            
            event = ThreatEvent(
                event_id=event_id,
                threat_type=threat_type,
                severity=severity,
                source_ip=source_ip,
                user_id=user_id,
                timestamp=current_time,
                description=description,
                request_data=request_data,
                response_data=response_data,
                automated_actions=[action.value for action in response_data.get("actions", [])],
                risk_score=risk_score,
                status="active"
            )
            
            # Store event
            self.threat_events[event_id] = event
            
            # Cache event
            cache_key = f"threat_event_{event_id}"
            await self.cache_manager.set(cache_key, event.__dict__, ttl=self.threat_cache_ttl)
            
            self.logger.info(f"Created threat event: {event_id} - {threat_type.value}")
            
        except Exception as e:
            self.logger.error(f"Error creating threat event: {str(e)}")
    
    async def _update_risk_profile(
        self, 
        source_ip: str, 
        user_id: Optional[str], 
        risk_score: float
    ):
        """Update risk profile for IP address or user."""
        try:
            identifier = user_id or source_ip
            profile_id = f"risk_{identifier}"
            
            # Get existing profile or create new one
            if profile_id in self.risk_profiles:
                profile = self.risk_profiles[profile_id]
                profile.risk_score = min(profile.risk_score + risk_score, self.config.get("max_risk_score", 100.0))
                profile.threat_count += 1
                profile.last_updated = datetime.utcnow()
                profile.notes.append(f"Risk increased by {risk_score} at {datetime.utcnow().isoformat()}")
            else:
                profile = RiskProfile(
                    profile_id=profile_id,
                    identifier=identifier,
                    risk_score=min(risk_score, self.config.get("max_risk_score", 100.0)),
                    last_updated=datetime.utcnow(),
                    threat_count=1,
                    blocked_until=None,
                    notes=[f"Initial risk score: {risk_score} at {datetime.utcnow().isoformat()}"]
                )
                self.risk_profiles[profile_id] = profile
            
            # Check if profile should be blocked
            if profile.risk_score >= self.risk_thresholds["high"] and not profile.blocked_until:
                profile.blocked_until = datetime.utcnow() + timedelta(
                    seconds=self.config.get("lockout_duration", 900)
                )
                self.blocked_ips[identifier] = profile.blocked_until
                profile.notes.append(f"Blocked until {profile.blocked_until.isoformat()}")
            
            # Cache profile
            cache_key = f"risk_profile_{profile_id}"
            await self.cache_manager.set(cache_key, profile.__dict__, ttl=self.risk_cache_ttl)
            
        except Exception as e:
            self.logger.error(f"Error updating risk profile: {str(e)}")
    
    async def _execute_response_actions(
        self, 
        source_ip: str, 
        user_id: Optional[str], 
        actions: List[ResponseAction]
    ):
        """Execute automated response actions."""
        try:
            for action in actions:
                if action == ResponseAction.BLOCK_IP:
                    block_duration = self.config.get("lockout_duration", 900)
                    block_until = datetime.utcnow() + timedelta(seconds=block_duration)
                    self.blocked_ips[source_ip] = block_until
                    self.logger.info(f"Blocked IP {source_ip} until {block_until.isoformat()}")
                
                elif action == ResponseAction.RATE_LIMIT:
                    # Rate limiting is handled in the request analysis
                    pass
                
                elif action == ResponseAction.LOGOUT_USER and user_id:
                    # This would invalidate user sessions
                    self.logger.info(f"Logged out user {user_id} due to security threat")
                
                elif action == ResponseAction.DISABLE_ACCOUNT and user_id:
                    # This would disable the user account
                    self.logger.info(f"Disabled user account {user_id} due to security threat")
                
                elif action == ResponseAction.NOTIFY_ADMIN:
                    await self._notify_admin(source_ip, user_id, actions)
                
                elif action == ResponseAction.REQUIRE_MFA and user_id:
                    # This would require MFA for next login
                    self.logger.info(f"Required MFA for user {user_id} due to security threat")
                
                elif action == ResponseAction.QUARANTINE_SESSION and user_id:
                    # This would quarantine the user session
                    self.logger.info(f"Quarantined session for user {user_id}")
                
                elif action == ResponseAction.BLOCK_REQUEST:
                    # This is handled by returning a block response
                    pass
                
                elif action == ResponseAction.INCREMENT_RISK_SCORE:
                    # This is handled in the risk profile update
                    pass
            
        except Exception as e:
            self.logger.error(f"Error executing response actions: {str(e)}")
    
    async def _notify_admin(
        self, 
        source_ip: str, 
        user_id: Optional[str], 
        actions: List[ResponseAction]
    ):
        """Notify administrators about security threats."""
        try:
            admin_email = self.config.get("admin_notification_email")
            if admin_email:
                # This would send an email notification
                self.logger.info(f"Admin notification sent to {admin_email} for IP {source_ip}, user {user_id}")
            
        except Exception as e:
            self.logger.error(f"Error notifying admin: {str(e)}")
    
    async def _cleanup_old_events(self):
        """Clean up old threat events."""
        try:
            retention_days = self.config.get("log_retention_days", 90)
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            events_to_remove = []
            for event_id, event in self.threat_events.items():
                if event.timestamp < cutoff_date:
                    events_to_remove.append(event_id)
            
            for event_id in events_to_remove:
                del self.threat_events[event_id]
            
            if events_to_remove:
                self.logger.info(f"Cleaned up {len(events_to_remove)} old threat events")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old events: {str(e)}")
    
    async def _update_risk_scores(self):
        """Update risk scores with decay over time."""
        try:
            decay_rate = self.config.get("risk_decay_rate", 0.1)
            
            for profile_id, profile in self.risk_profiles.items():
                if profile.risk_score > 0:
                    # Apply decay
                    profile.risk_score = max(0, profile.risk_score - decay_rate)
                    profile.last_updated = datetime.utcnow()
                    
                    # Update cache
                    cache_key = f"risk_profile_{profile_id}"
                    await self.cache_manager.set(cache_key, profile.__dict__, ttl=self.risk_cache_ttl)
            
        except Exception as e:
            self.logger.error(f"Error updating risk scores: {str(e)}")
    
    async def _update_security_rules(self):
        """Update security rules from external source."""
        try:
            # This would fetch updated rules from an external source
            # For now, just log that the check was performed
            self.logger.debug("Security rules update check performed")
            
        except Exception as e:
            self.logger.error(f"Error updating security rules: {str(e)}")
    
    async def _analyze_behavioral_patterns(self):
        """Analyze behavioral patterns for new threats."""
        try:
            # This would use machine learning to analyze patterns
            # For now, just log that the analysis was performed
            self.logger.debug("Behavioral pattern analysis performed")
            
        except Exception as e:
            self.logger.error(f"Error analyzing behavioral patterns: {str(e)}")
    
    async def get_threat_events(
        self,
        threat_type: Optional[ThreatType] = None,
        severity: Optional[ThreatSeverity] = None,
        source_ip: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get threat events with optional filtering."""
        try:
            events = list(self.threat_events.values())
            
            # Apply filters
            if threat_type:
                events = [e for e in events if e.threat_type == threat_type]
            
            if severity:
                events = [e for e in events if e.severity == severity]
            
            if source_ip:
                events = [e for e in events if e.source_ip == source_ip]
            
            if user_id:
                events = [e for e in events if e.user_id == user_id]
            
            # Sort by timestamp (newest first)
            events.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Apply limit
            events = events[:limit]
            
            # Convert to dictionaries
            return [
                {
                    "event_id": e.event_id,
                    "threat_type": e.threat_type.value,
                    "severity": e.severity.value,
                    "source_ip": e.source_ip,
                    "user_id": e.user_id,
                    "timestamp": e.timestamp.isoformat(),
                    "description": e.description,
                    "risk_score": e.risk_score,
                    "status": e.status,
                    "automated_actions": e.automated_actions,
                    "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
                    "resolution_notes": e.resolution_notes
                }
                for e in events
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting threat events: {str(e)}")
            return []
    
    async def get_risk_profiles(
        self,
        identifier: Optional[str] = None,
        min_risk_score: Optional[float] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get risk profiles with optional filtering."""
        try:
            profiles = list(self.risk_profiles.values())
            
            # Apply filters
            if identifier:
                profiles = [p for p in profiles if identifier in p.identifier]
            
            if min_risk_score is not None:
                profiles = [p for p in profiles if p.risk_score >= min_risk_score]
            
            # Sort by risk score (highest first)
            profiles.sort(key=lambda x: x.risk_score, reverse=True)
            
            # Apply limit
            profiles = profiles[:limit]
            
            # Convert to dictionaries
            return [
                {
                    "profile_id": p.profile_id,
                    "identifier": p.identifier,
                    "risk_score": p.risk_score,
                    "last_updated": p.last_updated.isoformat(),
                    "threat_count": p.threat_count,
                    "blocked_until": p.blocked_until.isoformat() if p.blocked_until else None,
                    "notes": p.notes
                }
                for p in profiles
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting risk profiles: {str(e)}")
            return []
    
    async def get_security_rules(self) -> List[Dict[str, Any]]:
        """Get all security rules."""
        try:
            rules = list(self.security_rules.values())
            
            # Convert to dictionaries
            return [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "description": r.description,
                    "threat_type": r.threat_type.value,
                    "severity": r.severity.value,
                    "enabled": r.enabled,
                    "pattern": r.pattern,
                    "response_actions": [action.value for action in r.response_actions],
                    "conditions": r.conditions,
                    "created_at": r.created_at.isoformat(),
                    "updated_at": r.updated_at.isoformat()
                }
                for r in rules
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting security rules: {str(e)}")
            return []
    
    async def get_blocked_ips(self) -> List[Dict[str, Any]]:
        """Get list of blocked IP addresses."""
        try:
            current_time = datetime.utcnow()
            blocked_ips = []
            
            for ip, block_until in self.blocked_ips.items():
                if current_time < block_until:
                    blocked_ips.append({
                        "ip_address": ip,
                        "blocked_until": block_until.isoformat(),
                        "remaining_seconds": int((block_until - current_time).total_seconds())
                    })
            
            return blocked_ips
            
        except Exception as e:
            self.logger.error(f"Error getting blocked IPs: {str(e)}")
            return []
    
    async def unblock_ip(self, ip_address: str) -> Dict[str, Any]:
        """Unblock an IP address."""
        try:
            if ip_address in self.blocked_ips:
                del self.blocked_ips[ip_address]
                
                # Update risk profile if exists
                profile_id = f"risk_{ip_address}"
                if profile_id in self.risk_profiles:
                    self.risk_profiles[profile_id].blocked_until = None
                    self.risk_profiles[profile_id].notes.append(f"Unblocked at {datetime.utcnow().isoformat()}")
                
                self.logger.info(f"Unblocked IP address: {ip_address}")
                
                return {
                    "success": True,
                    "message": f"IP address {ip_address} unblocked successfully"
                }
            else:
                return {
                    "success": False,
                    "message": f"IP address {ip_address} is not currently blocked"
                }
                
        except Exception as e:
            self.logger.error(f"Error unblocking IP {ip_address}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_threat_statistics(self) -> Dict[str, Any]:
        """Get threat detection statistics."""
        try:
            current_time = datetime.utcnow()
            last_24h = current_time - timedelta(hours=24)
            last_7d = current_time - timedelta(days=7)
            
            # Count threats by time period
            threats_24h = [e for e in self.threat_events.values() if e.timestamp >= last_24h]
            threats_7d = [e for e in self.threat_events.values() if e.timestamp >= last_7d]
            
            # Count by threat type
            threat_types_24h = defaultdict(int)
            threat_types_7d = defaultdict(int)
            
            for event in threats_24h:
                threat_types_24h[event.threat_type.value] += 1
            
            for event in threats_7d:
                threat_types_7d[event.threat_type.value] += 1
            
            # Count by severity
            severity_counts_24h = defaultdict(int)
            severity_counts_7d = defaultdict(int)
            
            for event in threats_24h:
                severity_counts_24h[event.severity.value] += 1
            
            for event in threats_7d:
                severity_counts_7d[event.severity.value] += 1
            
            # Risk profile statistics
            high_risk_profiles = [
                p for p in self.risk_profiles.values() 
                if p.risk_score >= self.risk_thresholds["high"]
            ]
            
            return {
                "time_periods": {
                    "last_24h": {
                        "total_threats": len(threats_24h),
                        "by_type": dict(threat_types_24h),
                        "by_severity": dict(severity_counts_24h)
                    },
                    "last_7d": {
                        "total_threats": len(threats_7d),
                        "by_type": dict(threat_types_7d),
                        "by_severity": dict(severity_counts_7d)
                    }
                },
                "risk_profiles": {
                    "total_profiles": len(self.risk_profiles),
                    "high_risk_count": len(high_risk_profiles),
                    "blocked_ips": len(self.blocked_ips)
                },
                "security_rules": {
                    "total_rules": len(self.security_rules),
                    "enabled_rules": len([r for r in self.security_rules.values() if r.enabled])
                },
                "configuration": {
                    "detection_enabled": self.detection_enabled,
                    "auto_response_enabled": self.auto_response_enabled,
                    "learning_enabled": self.learning_enabled,
                    "risk_thresholds": self.risk_thresholds
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting threat statistics: {str(e)}")
            return {"error": str(e)}