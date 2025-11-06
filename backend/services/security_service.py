"""
Automated Security Response Service for InsiteChart platform.

This service provides automated threat detection, security monitoring,
and incident response capabilities for the platform.
"""

import asyncio
import logging
import hashlib
import hmac
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json
import re
import ipaddress
from collections import defaultdict, deque

from ..cache.unified_cache import UnifiedCacheManager


class SecurityEventType(str, Enum):
    """Types of security events."""
    FAILED_LOGIN = "failed_login"
    BRUTE_FORCE = "brute_force"
    SUSPICIOUS_REQUEST = "suspicious_request"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_ANOMALY = "data_anomaly"
    INJECTION_ATTEMPT = "injection_attempt"
    XSS_ATTEMPT = "xss_attempt"
    CSRF_ATTEMPT = "csrf_attempt"
    MALICIOUS_PAYLOAD = "malicious_payload"
    UNUSUAL_TRAFFIC = "unusual_traffic"
    SYSTEM_ANOMALY = "system_anomaly"


class SecuritySeverity(str, Enum):
    """Security event severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityAction(str, Enum):
    """Automated security response actions."""
    BLOCK_IP = "block_ip"
    RATE_LIMIT = "rate_limit"
    LOG_EVENT = "log_event"
    ALERT_ADMIN = "alert_admin"
    REQUIRE_2FA = "require_2fa"
    SESSION_TERMINATE = "session_terminate"
    TEMPORARY_BAN = "temporary_ban"
    INVESTIGATE = "investigate"


@dataclass
class SecurityEvent:
    """Security event data structure."""
    id: str
    event_type: SecurityEventType
    severity: SecuritySeverity
    timestamp: datetime
    source_ip: str
    user_id: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    request_data: Optional[Dict] = None
    description: str = ""
    metadata: Dict[str, Any] = None
    resolved: bool = False
    response_actions: List[SecurityAction] = None


@dataclass
class SecurityRule:
    """Security rule configuration."""
    id: str
    name: str
    event_type: SecurityEventType
    conditions: Dict[str, Any]
    actions: List[SecurityAction]
    severity: SecuritySeverity
    enabled: bool = True
    cooldown_period: int = 300  # seconds


@dataclass
class SecurityMetrics:
    """Security metrics and statistics."""
    total_events: int
    events_by_type: Dict[str, int]
    events_by_severity: Dict[str, int]
    blocked_ips: int
    rate_limited_requests: int
    active_investigations: int
    false_positives: int
    detection_accuracy: float
    last_updated: datetime


class SecurityService:
    """Automated security response service."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # Security rules
        self.rules: Dict[str, SecurityRule] = {}
        
        # Event tracking
        self.events: deque = deque(maxlen=10000)  # Keep last 10K events
        self.active_investigations: Dict[str, SecurityEvent] = {}
        
        # IP tracking
        self.ip_reputation: Dict[str, Dict] = {}
        self.blocked_ips: Dict[str, datetime] = {}
        self.rate_limits: Dict[str, List[datetime]] = defaultdict(list)
        
        # Pattern matching
        self.injection_patterns = self._load_injection_patterns()
        self.xss_patterns = self._load_xss_patterns()
        self.suspicious_user_agents = self._load_suspicious_user_agents()
        
        # Background tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Metrics
        self.metrics = SecurityMetrics(
            total_events=0,
            events_by_type=defaultdict(int),
            events_by_severity=defaultdict(int),
            blocked_ips=0,
            rate_limited_requests=0,
            active_investigations=0,
            false_positives=0,
            detection_accuracy=0.0,
            last_updated=datetime.utcnow()
        )
        
        # Initialize default rules
        self._initialize_default_rules()
        
        self.logger.info("SecurityService initialized")
    
    async def start(self):
        """Start security monitoring service."""
        try:
            # Start background tasks
            self.monitoring_task = asyncio.create_task(self._monitor_security_events())
            self.cleanup_task = asyncio.create_task(self._cleanup_expired_data())
            
            self.logger.info("SecurityService started")
            
        except Exception as e:
            self.logger.error(f"Failed to start SecurityService: {str(e)}")
            raise
    
    async def stop(self):
        """Stop security monitoring service."""
        try:
            # Cancel background tasks
            if self.monitoring_task:
                self.monitoring_task.cancel()
            if self.cleanup_task:
                self.cleanup_task.cancel()
            
            self.logger.info("SecurityService stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping SecurityService: {str(e)}")
    
    async def analyze_request(
        self,
        request_data: Dict[str, Any],
        source_ip: str,
        user_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> List[SecurityEvent]:
        """Analyze incoming request for security threats."""
        try:
            events = []
            
            # Check for various threat patterns
            events.extend(await self._check_injection_attacks(request_data, source_ip, user_id, user_agent, endpoint))
            events.extend(await self._check_xss_attacks(request_data, source_ip, user_id, user_agent, endpoint))
            events.extend(await self._check_rate_limiting(source_ip, user_id))
            events.extend(await self._check_suspicious_patterns(request_data, source_ip, user_id, user_agent, endpoint))
            events.extend(await self._check_ip_reputation(source_ip, user_id))
            events.extend(await self._check_data_anomalies(request_data, source_ip, user_id))
            
            # Process detected events
            for event in events:
                await self._process_security_event(event)
            
            return events
            
        except Exception as e:
            self.logger.error(f"Error analyzing request: {str(e)}")
            return []
    
    async def add_security_rule(self, rule: SecurityRule):
        """Add a new security rule."""
        try:
            self.rules[rule.id] = rule
            
            # Cache rule
            await self.cache_manager.set(
                f"security_rule_{rule.id}",
                asdict(rule),
                ttl=3600
            )
            
            self.logger.info(f"Added security rule: {rule.name}")
            
        except Exception as e:
            self.logger.error(f"Error adding security rule: {str(e)}")
            raise
    
    async def update_security_rule(self, rule_id: str, updates: Dict[str, Any]):
        """Update an existing security rule."""
        try:
            if rule_id not in self.rules:
                raise ValueError(f"Rule {rule_id} not found")
            
            rule = self.rules[rule_id]
            
            # Update rule properties
            for key, value in updates.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)
            
            # Cache updated rule
            await self.cache_manager.set(
                f"security_rule_{rule_id}",
                asdict(rule),
                ttl=3600
            )
            
            self.logger.info(f"Updated security rule: {rule.name}")
            
        except Exception as e:
            self.logger.error(f"Error updating security rule: {str(e)}")
            raise
    
    async def block_ip(self, ip_address: str, duration_hours: int = 24, reason: str = "Security violation"):
        """Block an IP address."""
        try:
            # Validate IP address
            ipaddress.ip_address(ip_address)
            
            # Calculate expiration
            expiration = datetime.utcnow() + timedelta(hours=duration_hours)
            
            # Add to blocked IPs
            self.blocked_ips[ip_address] = expiration
            
            # Cache block
            await self.cache_manager.set(
                f"blocked_ip_{ip_address}",
                {
                    "ip": ip_address,
                    "blocked_at": datetime.utcnow().isoformat(),
                    "expires_at": expiration.isoformat(),
                    "reason": reason
                },
                ttl=duration_hours * 3600
            )
            
            # Update metrics
            self.metrics.blocked_ips += 1
            
            # Log event
            event = SecurityEvent(
                id=f"block_{int(time.time())}",
                event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
                severity=SecuritySeverity.HIGH,
                timestamp=datetime.utcnow(),
                source_ip=ip_address,
                description=f"IP blocked: {reason}",
                metadata={"duration_hours": duration_hours, "reason": reason},
                response_actions=[SecurityAction.BLOCK_IP]
            )
            
            await self._process_security_event(event)
            
            self.logger.warning(f"Blocked IP {ip_address} for {duration_hours} hours: {reason}")
            
        except ValueError:
            self.logger.error(f"Invalid IP address: {ip_address}")
        except Exception as e:
            self.logger.error(f"Error blocking IP {ip_address}: {str(e)}")
    
    async def unblock_ip(self, ip_address: str):
        """Unblock an IP address."""
        try:
            # Remove from blocked IPs
            if ip_address in self.blocked_ips:
                del self.blocked_ips[ip_address]
            
            # Remove from cache
            await self.cache_manager.delete(f"blocked_ip_{ip_address}")
            
            # Log event
            event = SecurityEvent(
                id=f"unblock_{int(time.time())}",
                event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
                severity=SecuritySeverity.LOW,
                timestamp=datetime.utcnow(),
                source_ip=ip_address,
                description="IP unblocked",
                metadata={"action": "unblock"},
                response_actions=[SecurityAction.LOG_EVENT]
            )
            
            await self._process_security_event(event)
            
            self.logger.info(f"Unblocked IP: {ip_address}")
            
        except Exception as e:
            self.logger.error(f"Error unblocking IP {ip_address}: {str(e)}")
    
    async def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if an IP address is blocked."""
        try:
            # Check memory
            if ip_address in self.blocked_ips:
                expiration = self.blocked_ips[ip_address]
                if datetime.utcnow() < expiration:
                    return True
                else:
                    # Expired block, remove it
                    del self.blocked_ips[ip_address]
            
            # Check cache
            cached_block = await self.cache_manager.get(f"blocked_ip_{ip_address}")
            if cached_block:
                expires_at = datetime.fromisoformat(cached_block["expires_at"])
                if datetime.utcnow() < expires_at:
                    return True
                else:
                    # Expired block, remove from cache
                    await self.cache_manager.delete(f"blocked_ip_{ip_address}")
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking IP block status: {str(e)}")
            return False
    
    async def get_security_metrics(self) -> SecurityMetrics:
        """Get current security metrics."""
        try:
            # Update metrics timestamp
            self.metrics.last_updated = datetime.utcnow()
            
            # Calculate detection accuracy
            if self.metrics.total_events > 0:
                self.metrics.detection_accuracy = 1.0 - (self.metrics.false_positives / self.metrics.total_events)
            
            return self.metrics
            
        except Exception as e:
            self.logger.error(f"Error getting security metrics: {str(e)}")
            return self.metrics
    
    async def get_recent_events(
        self, 
        limit: int = 100,
        severity: Optional[SecuritySeverity] = None,
        event_type: Optional[SecurityEventType] = None
    ) -> List[SecurityEvent]:
        """Get recent security events."""
        try:
            events = list(self.events)
            
            # Filter by severity
            if severity:
                events = [e for e in events if e.severity == severity]
            
            # Filter by event type
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            
            # Sort by timestamp (newest first)
            events.sort(key=lambda x: x.timestamp, reverse=True)
            
            return events[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting recent events: {str(e)}")
            return []
    
    async def _monitor_security_events(self):
        """Background task to monitor security events."""
        try:
            while True:
                try:
                    # Check for automated responses
                    await self._check_automated_responses()
                    
                    # Update metrics
                    await self._update_metrics()
                    
                    # Wait before next check
                    await asyncio.sleep(60)  # Check every minute
                    
                except Exception as e:
                    self.logger.error(f"Error in security monitoring: {str(e)}")
                    await asyncio.sleep(300)  # Wait longer on error
                    
        except asyncio.CancelledError:
            self.logger.info("Security monitoring task cancelled")
        except Exception as e:
            self.logger.error(f"Fatal error in security monitoring: {str(e)}")
    
    async def _cleanup_expired_data(self):
        """Background task to clean up expired security data."""
        try:
            while True:
                try:
                    current_time = datetime.utcnow()
                    
                    # Clean up expired IP blocks
                    expired_blocks = [
                        ip for ip, expiration in self.blocked_ips.items()
                        if current_time >= expiration
                    ]
                    
                    for ip in expired_blocks:
                        del self.blocked_ips[ip]
                        await self.cache_manager.delete(f"blocked_ip_{ip}")
                    
                    # Clean up old rate limit entries
                    cutoff_time = current_time - timedelta(hours=1)
                    for ip, timestamps in list(self.rate_limits.items()):
                        self.rate_limits[ip] = [
                            ts for ts in timestamps if ts > cutoff_time
                        ]
                        if not self.rate_limits[ip]:
                            del self.rate_limits[ip]
                    
                    # Wait before next cleanup
                    await asyncio.sleep(300)  # Clean up every 5 minutes
                    
                except Exception as e:
                    self.logger.error(f"Error in security cleanup: {str(e)}")
                    await asyncio.sleep(600)  # Wait longer on error
                    
        except asyncio.CancelledError:
            self.logger.info("Security cleanup task cancelled")
        except Exception as e:
            self.logger.error(f"Fatal error in security cleanup: {str(e)}")
    
    async def _check_injection_attacks(
        self,
        request_data: Dict[str, Any],
        source_ip: str,
        user_id: Optional[str],
        user_agent: Optional[str],
        endpoint: Optional[str]
    ) -> List[SecurityEvent]:
        """Check for SQL injection and other injection attacks."""
        events = []
        
        try:
            # Extract request parameters
            params = []
            if isinstance(request_data, dict):
                for key, value in request_data.items():
                    if isinstance(value, str):
                        params.append(value)
                    elif isinstance(value, (list, dict)):
                        params.extend(str(v) for v in value.values() if isinstance(v, str))
            
            # Check against injection patterns
            for param in params:
                for pattern_name, pattern in self.injection_patterns.items():
                    if re.search(pattern, param, re.IGNORECASE):
                        event = SecurityEvent(
                            id=f"injection_{int(time.time())}_{hash(param) % 10000}",
                            event_type=SecurityEventType.INJECTION_ATTEMPT,
                            severity=SecuritySeverity.HIGH,
                            timestamp=datetime.utcnow(),
                            source_ip=source_ip,
                            user_id=user_id,
                            user_agent=user_agent,
                            endpoint=endpoint,
                            request_data={"suspicious_param": param},
                            description=f"Potential {pattern_name} injection detected",
                            metadata={"pattern": pattern_name, "matched_param": param}
                        )
                        events.append(event)
                        break
            
        except Exception as e:
            self.logger.error(f"Error checking injection attacks: {str(e)}")
        
        return events
    
    async def _check_xss_attacks(
        self,
        request_data: Dict[str, Any],
        source_ip: str,
        user_id: Optional[str],
        user_agent: Optional[str],
        endpoint: Optional[str]
    ) -> List[SecurityEvent]:
        """Check for XSS attacks."""
        events = []
        
        try:
            # Extract request parameters
            params = []
            if isinstance(request_data, dict):
                for key, value in request_data.items():
                    if isinstance(value, str):
                        params.append(value)
            
            # Check against XSS patterns
            for param in params:
                for pattern_name, pattern in self.xss_patterns.items():
                    if re.search(pattern, param, re.IGNORECASE):
                        event = SecurityEvent(
                            id=f"xss_{int(time.time())}_{hash(param) % 10000}",
                            event_type=SecurityEventType.XSS_ATTEMPT,
                            severity=SecuritySeverity.HIGH,
                            timestamp=datetime.utcnow(),
                            source_ip=source_ip,
                            user_id=user_id,
                            user_agent=user_agent,
                            endpoint=endpoint,
                            request_data={"suspicious_param": param},
                            description=f"Potential XSS attack detected: {pattern_name}",
                            metadata={"pattern": pattern_name, "matched_param": param}
                        )
                        events.append(event)
                        break
            
        except Exception as e:
            self.logger.error(f"Error checking XSS attacks: {str(e)}")
        
        return events
    
    async def _check_rate_limiting(
        self,
        source_ip: str,
        user_id: Optional[str]
    ) -> List[SecurityEvent]:
        """Check for rate limiting violations."""
        events = []
        
        try:
            current_time = datetime.utcnow()
            
            # Check IP-based rate limiting
            ip_requests = self.rate_limits[source_ip]
            recent_requests = [ts for ts in ip_requests if ts > current_time - timedelta(minutes=1)]
            self.rate_limits[source_ip] = recent_requests
            
            if len(recent_requests) > 100:  # 100 requests per minute
                event = SecurityEvent(
                    id=f"rate_limit_{int(time.time())}_{hash(source_ip) % 10000}",
                    event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                    severity=SecuritySeverity.MEDIUM,
                    timestamp=current_time,
                    source_ip=source_ip,
                    user_id=user_id,
                    description=f"Rate limit exceeded: {len(recent_requests)} requests/minute",
                    metadata={"request_count": len(recent_requests), "time_window": "1 minute"}
                )
                events.append(event)
            
            # Add current request to rate limit tracking
            self.rate_limits[source_ip].append(current_time)
            
        except Exception as e:
            self.logger.error(f"Error checking rate limiting: {str(e)}")
        
        return events
    
    async def _check_suspicious_patterns(
        self,
        request_data: Dict[str, Any],
        source_ip: str,
        user_id: Optional[str],
        user_agent: Optional[str],
        endpoint: Optional[str]
    ) -> List[SecurityEvent]:
        """Check for suspicious request patterns."""
        events = []
        
        try:
            # Check user agent
            if user_agent:
                for suspicious_ua in self.suspicious_user_agents:
                    if suspicious_ua.lower() in user_agent.lower():
                        event = SecurityEvent(
                            id=f"suspicious_ua_{int(time.time())}_{hash(source_ip) % 10000}",
                            event_type=SecurityEventType.SUSPICIOUS_REQUEST,
                            severity=SecuritySeverity.MEDIUM,
                            timestamp=datetime.utcnow(),
                            source_ip=source_ip,
                            user_id=user_id,
                            user_agent=user_agent,
                            endpoint=endpoint,
                            description=f"Suspicious user agent detected",
                            metadata={"user_agent": user_agent, "matched_pattern": suspicious_ua}
                        )
                        events.append(event)
                        break
            
            # Check for unusual request sizes
            if isinstance(request_data, dict):
                total_size = len(str(request_data))
                if total_size > 100000:  # 100KB
                    event = SecurityEvent(
                        id=f"large_request_{int(time.time())}_{hash(source_ip) % 10000}",
                        event_type=SecurityEventType.SUSPICIOUS_REQUEST,
                        severity=SecuritySeverity.LOW,
                        timestamp=datetime.utcnow(),
                        source_ip=source_ip,
                        user_id=user_id,
                        endpoint=endpoint,
                        description=f"Unusually large request detected",
                        metadata={"request_size": total_size}
                    )
                    events.append(event)
            
        except Exception as e:
            self.logger.error(f"Error checking suspicious patterns: {str(e)}")
        
        return events
    
    async def _check_ip_reputation(
        self,
        source_ip: str,
        user_id: Optional[str]
    ) -> List[SecurityEvent]:
        """Check IP reputation and known malicious IPs."""
        events = []
        
        try:
            # Check if IP is already blocked
            if await self.is_ip_blocked(source_ip):
                event = SecurityEvent(
                    id=f"blocked_ip_access_{int(time.time())}_{hash(source_ip) % 10000}",
                    event_type=SecurityEventType.UNAUTHORIZED_ACCESS,
                    severity=SecuritySeverity.HIGH,
                    timestamp=datetime.utcnow(),
                    source_ip=source_ip,
                    user_id=user_id,
                    description="Access attempt from blocked IP",
                    metadata={"blocked_ip": source_ip}
                )
                events.append(event)
            
            # Check IP reputation (simplified)
            if source_ip not in self.ip_reputation:
                self.ip_reputation[source_ip] = {
                    "first_seen": datetime.utcnow(),
                    "request_count": 0,
                    "suspicious_events": 0,
                    "reputation_score": 0.5
                }
            
            # Update IP tracking
            ip_info = self.ip_reputation[source_ip]
            ip_info["request_count"] += 1
            
            # Check for suspicious activity patterns
            if ip_info["suspicious_events"] > 5:
                event = SecurityEvent(
                    id=f"bad_reputation_{int(time.time())}_{hash(source_ip) % 10000}",
                    event_type=SecurityEventType.SUSPICIOUS_REQUEST,
                    severity=SecuritySeverity.MEDIUM,
                    timestamp=datetime.utcnow(),
                    source_ip=source_ip,
                    user_id=user_id,
                    description="IP with poor reputation detected",
                    metadata=ip_info
                )
                events.append(event)
            
        except Exception as e:
            self.logger.error(f"Error checking IP reputation: {str(e)}")
        
        return events
    
    async def _check_data_anomalies(
        self,
        request_data: Dict[str, Any],
        source_ip: str,
        user_id: Optional[str]
    ) -> List[SecurityEvent]:
        """Check for data anomalies and unusual patterns."""
        events = []
        
        try:
            # This is a simplified anomaly detection
            # In production, you'd use more sophisticated ML-based detection
            
            # Check for unusual parameter names
            if isinstance(request_data, dict):
                param_names = list(request_data.keys())
                
                # Check for common attack parameter names
                suspicious_params = [
                    "admin", "password", "passwd", "secret", "token",
                    "key", "auth", "debug", "test", "exec", "cmd"
                ]
                
                for param in param_names:
                    if param.lower() in suspicious_params:
                        event = SecurityEvent(
                            id=f"suspicious_param_{int(time.time())}_{hash(source_ip) % 10000}",
                            event_type=SecurityEventType.DATA_ANOMALY,
                            severity=SecuritySeverity.LOW,
                            timestamp=datetime.utcnow(),
                            source_ip=source_ip,
                            user_id=user_id,
                            description=f"Suspicious parameter name detected: {param}",
                            metadata={"parameter": param}
                        )
                        events.append(event)
            
        except Exception as e:
            self.logger.error(f"Error checking data anomalies: {str(e)}")
        
        return events
    
    async def _process_security_event(self, event: SecurityEvent):
        """Process a security event and trigger responses."""
        try:
            # Add to events list
            self.events.append(event)
            
            # Update metrics
            self.metrics.total_events += 1
            self.metrics.events_by_type[event.event_type.value] += 1
            self.metrics.events_by_severity[event.severity.value] += 1
            
            # Check against security rules
            for rule in self.rules.values():
                if rule.enabled and await self._evaluate_rule(rule, event):
                    # Execute rule actions
                    for action in rule.actions:
                        await self._execute_security_action(action, event, rule)
            
            # Cache event
            await self.cache_manager.set(
                f"security_event_{event.id}",
                asdict(event),
                ttl=86400  # 24 hours
            )
            
            self.logger.warning(f"Security event processed: {event.event_type.value} from {event.source_ip}")
            
        except Exception as e:
            self.logger.error(f"Error processing security event: {str(e)}")
    
    async def _evaluate_rule(self, rule: SecurityRule, event: SecurityEvent) -> bool:
        """Evaluate if a security rule matches an event."""
        try:
            # Check event type
            if rule.event_type != event.event_type:
                return False
            
            # Check conditions
            conditions = rule.conditions
            
            # Check severity
            if "severity" in conditions:
                if isinstance(conditions["severity"], list):
                    if event.severity not in conditions["severity"]:
                        return False
                elif event.severity != conditions["severity"]:
                    return False
            
            # Check source IP patterns
            if "source_ip" in conditions:
                ip_pattern = conditions["source_ip"]
                if not re.match(ip_pattern, event.source_ip):
                    return False
            
            # Check user agent patterns
            if "user_agent" in conditions and event.user_agent:
                ua_pattern = conditions["user_agent"]
                if not re.search(ua_pattern, event.user_agent, re.IGNORECASE):
                    return False
            
            # Check cooldown period
            if rule.cooldown_period > 0:
                cache_key = f"rule_cooldown_{rule.id}_{event.source_ip}"
                last_triggered = await self.cache_manager.get(cache_key)
                if last_triggered:
                    last_time = datetime.fromisoformat(last_triggered)
                    if (datetime.utcnow() - last_time).total_seconds() < rule.cooldown_period:
                        return False
                
                # Update cooldown
                await self.cache_manager.set(
                    cache_key,
                    datetime.utcnow().isoformat(),
                    ttl=rule.cooldown_period
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error evaluating security rule: {str(e)}")
            return False
    
    async def _execute_security_action(
        self,
        action: SecurityAction,
        event: SecurityEvent,
        rule: SecurityRule
    ):
        """Execute a security action."""
        try:
            if action == SecurityAction.BLOCK_IP:
                await self.block_ip(event.source_ip, reason=rule.name)
                event.response_actions.append(action)
            
            elif action == SecurityAction.RATE_LIMIT:
                # Add to rate limiting with stricter limits
                self.rate_limits[event.source_ip].extend(
                    [datetime.utcnow() - timedelta(seconds=1)] * 50
                )
                event.response_actions.append(action)
            
            elif action == SecurityAction.LOG_EVENT:
                # Event is already logged
                event.response_actions.append(action)
            
            elif action == SecurityAction.ALERT_ADMIN:
                # In production, this would send alerts to administrators
                self.logger.critical(f"SECURITY ALERT: {rule.name} - {event.description}")
                event.response_actions.append(action)
            
            elif action == SecurityAction.REQUIRE_2FA:
                # Mark user for 2FA requirement
                if event.user_id:
                    await self.cache_manager.set(
                        f"require_2fa_{event.user_id}",
                        {"reason": rule.name, "timestamp": datetime.utcnow().isoformat()},
                        ttl=3600
                    )
                event.response_actions.append(action)
            
            elif action == SecurityAction.SESSION_TERMINATE:
                # Terminate user sessions
                if event.user_id:
                    await self.cache_manager.delete(f"session_{event.user_id}")
                event.response_actions.append(action)
            
            elif action == SecurityAction.TEMPORARY_BAN:
                await self.block_ip(event.source_ip, duration_hours=1, reason=rule.name)
                event.response_actions.append(action)
            
            elif action == SecurityAction.INVESTIGATE:
                # Add to active investigations
                self.active_investigations[event.id] = event
                self.metrics.active_investigations += 1
                event.response_actions.append(action)
            
        except Exception as e:
            self.logger.error(f"Error executing security action {action}: {str(e)}")
    
    async def _check_automated_responses(self):
        """Check for conditions requiring automated responses."""
        try:
            # Check for brute force attacks
            await self._detect_brute_force_attacks()
            
            # Check for unusual traffic patterns
            await self._detect_unusual_traffic()
            
            # Check for system anomalies
            await self._detect_system_anomalies()
            
        except Exception as e:
            self.logger.error(f"Error in automated response check: {str(e)}")
    
    async def _detect_brute_force_attacks(self):
        """Detect brute force attack patterns."""
        try:
            # Group events by source IP
            ip_events = defaultdict(list)
            for event in self.events:
                if event.event_type == SecurityEventType.FAILED_LOGIN:
                    ip_events[event.source_ip].append(event)
            
            # Check for brute force patterns
            for ip, events in ip_events.items():
                recent_events = [
                    e for e in events
                    if (datetime.utcnow() - e.timestamp).total_seconds() < 300  # 5 minutes
                ]
                
                if len(recent_events) > 10:  # 10 failed logins in 5 minutes
                    # Create brute force event
                    event = SecurityEvent(
                        id=f"brute_force_{int(time.time())}_{hash(ip) % 10000}",
                        event_type=SecurityEventType.BRUTE_FORCE,
                        severity=SecuritySeverity.HIGH,
                        timestamp=datetime.utcnow(),
                        source_ip=ip,
                        description=f"Brute force attack detected: {len(recent_events)} failed attempts",
                        metadata={"failed_attempts": len(recent_events)}
                    )
                    
                    await self._process_security_event(event)
            
        except Exception as e:
            self.logger.error(f"Error detecting brute force attacks: {str(e)}")
    
    async def _detect_unusual_traffic(self):
        """Detect unusual traffic patterns."""
        try:
            # This is a simplified implementation
            # In production, you'd use more sophisticated traffic analysis
            
            # Calculate request rate per IP
            ip_rates = defaultdict(int)
            cutoff_time = datetime.utcnow() - timedelta(minutes=10)
            
            for event in self.events:
                if event.timestamp > cutoff_time:
                    ip_rates[event.source_ip] += 1
            
            # Check for unusually high request rates
            avg_rate = sum(ip_rates.values()) / len(ip_rates) if ip_rates else 0
            
            for ip, rate in ip_rates.items():
                if rate > avg_rate * 5:  # 5x average rate
                    event = SecurityEvent(
                        id=f"unusual_traffic_{int(time.time())}_{hash(ip) % 10000}",
                        event_type=SecurityEventType.UNUSUAL_TRAFFIC,
                        severity=SecuritySeverity.MEDIUM,
                        timestamp=datetime.utcnow(),
                        source_ip=ip,
                        description=f"Unusual traffic pattern detected: {rate} requests/10min",
                        metadata={"request_rate": rate, "average_rate": avg_rate}
                    )
                    
                    await self._process_security_event(event)
            
        except Exception as e:
            self.logger.error(f"Error detecting unusual traffic: {str(e)}")
    
    async def _detect_system_anomalies(self):
        """Detect system-level anomalies."""
        try:
            # Check for sudden spikes in security events
            recent_events = [
                e for e in self.events
                if (datetime.utcnow() - e.timestamp).total_seconds() < 300  # 5 minutes
            ]
            
            # Calculate event rate
            event_rate = len(recent_events) / 5  # events per minute
            
            # Check for anomaly (sudden spike)
            if event_rate > 50:  # More than 50 events per minute
                event = SecurityEvent(
                    id=f"system_anomaly_{int(time.time())}",
                    event_type=SecurityEventType.SYSTEM_ANOMALY,
                    severity=SecuritySeverity.HIGH,
                    timestamp=datetime.utcnow(),
                    source_ip="system",
                    description=f"System anomaly detected: {event_rate:.1f} events/minute",
                    metadata={"event_rate": event_rate}
                )
                
                await self._process_security_event(event)
            
        except Exception as e:
            self.logger.error(f"Error detecting system anomalies: {str(e)}")
    
    async def _update_metrics(self):
        """Update security metrics."""
        try:
            # Calculate current metrics
            self.metrics.active_investigations = len(self.active_investigations)
            self.metrics.blocked_ips = len(self.blocked_ips)
            
            # Calculate rate limited requests
            total_rate_limited = sum(len(timestamps) for timestamps in self.rate_limits.values())
            self.metrics.rate_limited_requests = total_rate_limited
            
            # Update timestamp
            self.metrics.last_updated = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"Error updating metrics: {str(e)}")
    
    def _load_injection_patterns(self) -> Dict[str, str]:
        """Load SQL injection patterns."""
        return {
            "sql_union": r"(?i)(union\s+select)",
            "sql_comment": r"(?i)(--|#|/\*|\*/)",
            "sql_drop": r"(?i)(drop\s+(table|database))",
            "sql_insert": r"(?i)(insert\s+into)",
            "sql_update": r"(?i)(update\s+\w+\s+set)",
            "sql_delete": r"(?i)(delete\s+from)",
            "sql_exec": r"(?i)(exec\s*\(|execute\s*\()",
            "sql_script": r"(?i)(script\s*>|<\s*script)",
            "sql_or": r"(?i)(\s+or\s+['\"]?\d+['\"]?\s*=)",
            "sql_and": r"(?i)(\s+and\s+['\"]?\d+['\"]?\s*=)"
        }
    
    def _load_xss_patterns(self) -> Dict[str, str]:
        """Load XSS patterns."""
        return {
            "script_tag": r"(?i)(<\s*script[^>]*>)",
            "javascript": r"(?i)(javascript\s*:)",
            "on_event": r"(?i)(on\w+\s*=)",
            "iframe": r"(?i)(<\s*iframe[^>]*>)",
            "object": r"(?i)(<\s*object[^>]*>)",
            "embed": r"(?i)(<\s*embed[^>]*>)",
            "link": r"(?i)(<\s*link[^>]*>)",
            "meta": r"(?i)(<\s*meta[^>]*>)",
            "img_src": r"(?i)(<\s*img[^>]*src\s*=\s*['\"]\s*javascript)",
            "expression": r"(?i)(expression\s*\()"
        }
    
    def _load_suspicious_user_agents(self) -> List[str]:
        """Load suspicious user agent patterns."""
        return [
            "sqlmap", "nikto", "dirb", "nmap", "masscan", "zap",
            "burp", "w3af", "arachni", "skipfish", "netsparker",
            "acunetix", "havij", "pangolin", "bbscan", "sqlninja",
            "metasploit", "python-requests", "curl", "wget", "powershell"
        ]
    
    def _initialize_default_rules(self):
        """Initialize default security rules."""
        try:
            # Brute force detection rule
            brute_force_rule = SecurityRule(
                id="brute_force_detection",
                name="Brute Force Attack Detection",
                event_type=SecurityEventType.BRUTE_FORCE,
                conditions={"severity": [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL]},
                actions=[SecurityAction.BLOCK_IP, SecurityAction.ALERT_ADMIN],
                severity=SecuritySeverity.HIGH,
                cooldown_period=300
            )
            self.rules[brute_force_rule.id] = brute_force_rule
            
            # Injection attack rule
            injection_rule = SecurityRule(
                id="injection_attack_detection",
                name="Injection Attack Detection",
                event_type=SecurityEventType.INJECTION_ATTEMPT,
                conditions={},
                actions=[SecurityAction.BLOCK_IP, SecurityAction.ALERT_ADMIN],
                severity=SecuritySeverity.HIGH,
                cooldown_period=600
            )
            self.rules[injection_rule.id] = injection_rule
            
            # Rate limiting rule
            rate_limit_rule = SecurityRule(
                id="rate_limit_violation",
                name="Rate Limit Violation",
                event_type=SecurityEventType.RATE_LIMIT_EXCEEDED,
                conditions={},
                actions=[SecurityAction.RATE_LIMIT],
                severity=SecuritySeverity.MEDIUM,
                cooldown_period=60
            )
            self.rules[rate_limit_rule.id] = rate_limit_rule
            
            # Suspicious request rule
            suspicious_rule = SecurityRule(
                id="suspicious_request_detection",
                name="Suspicious Request Detection",
                event_type=SecurityEventType.SUSPICIOUS_REQUEST,
                conditions={},
                actions=[SecurityAction.LOG_EVENT],
                severity=SecuritySeverity.LOW,
                cooldown_period=300
            )
            self.rules[suspicious_rule.id] = suspicious_rule
            
            self.logger.info(f"Initialized {len(self.rules)} default security rules")
            
        except Exception as e:
            self.logger.error(f"Error initializing default rules: {str(e)}")