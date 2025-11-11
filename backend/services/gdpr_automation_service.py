"""
GDPR Automation Service for InsiteChart platform.

This service provides automated GDPR compliance management including
data subject rights, consent management, data retention policies,
and automated compliance reporting.
"""

import asyncio
import logging
import json
import os
import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid

from ..cache.unified_cache import UnifiedCacheManager


class DataSubjectRequestType(str, Enum):
    """Types of data subject requests."""
    ACCESS = "access"
    RECTIFICATION = "rectification"
    ERASURE = "erasure"
    PORTABILITY = "portability"
    RESTRICTION = "restriction"
    OBJECTION = "objection"


class ConsentType(str, Enum):
    """Types of consent."""
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    PERSONALIZATION = "personalization"
    THIRD_PARTY = "third_party"
    COOKIES = "cookies"


class ConsentStatus(str, Enum):
    """Consent status values."""
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"
    EXPIRED = "expired"


class DataCategory(str, Enum):
    """Categories of personal data."""
    PERSONAL_INFO = "personal_info"
    CONTACT_INFO = "contact_info"
    FINANCIAL_INFO = "financial_info"
    USAGE_DATA = "usage_data"
    LOCATION_DATA = "location_data"
    BEHAVIORAL_DATA = "behavioral_data"
    TECHNICAL_DATA = "technical_data"


class RetentionPolicy(str, Enum):
    """Data retention policy types."""
    IMMEDIATE = "immediate"
    DAYS_30 = "30_days"
    DAYS_90 = "90_days"
    DAYS_365 = "365_days"
    YEARS_2 = "2_years"
    YEARS_5 = "5_years"
    YEARS_7 = "7_years"
    CUSTOM = "custom"


@dataclass
class DataSubjectRequest:
    """Data subject request record."""
    request_id: str
    subject_id: str
    request_type: DataSubjectRequestType
    status: str
    created_at: datetime
    updated_at: datetime
    due_date: datetime
    description: str
    data_categories: List[DataCategory]
    response_data: Optional[Dict[str, Any]]
    processing_notes: List[str]
    automated_actions: List[str]
    completed_at: Optional[datetime] = None


@dataclass
class ConsentRecord:
    """Consent record for a data subject."""
    consent_id: str
    subject_id: str
    consent_type: ConsentType
    status: ConsentStatus
    granted_at: Optional[datetime]
    withdrawn_at: Optional[datetime]
    expires_at: Optional[datetime]
    purpose: str
    legal_basis: str
    metadata: Dict[str, Any]


@dataclass
class DataRetentionRule:
    """Data retention rule."""
    rule_id: str
    data_category: DataCategory
    retention_policy: RetentionPolicy
    custom_retention_days: Optional[int]
    automated_deletion: bool
    notification_before_deletion: bool
    exceptions: List[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class ComplianceReport:
    """GDPR compliance report."""
    report_id: str
    report_type: str
    period_start: datetime
    period_end: datetime
    generated_at: datetime
    total_requests: int
    completed_requests: int
    overdue_requests: int
    data_subjects_count: int
    consents_granted: int
    consents_denied: int
    data_breaches: int
    automated_actions: int
    compliance_score: float
    recommendations: List[str]


class GDPRAutomationService:
    """GDPR automation service."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = self._load_configuration()
        
        # Data storage
        self.data_subject_requests: Dict[str, DataSubjectRequest] = {}
        self.consent_records: Dict[str, ConsentRecord] = {}
        self.retention_rules: Dict[str, DataRetentionRule] = {}
        self.compliance_reports: List[ComplianceReport] = []
        
        # Automation settings
        self.automation_enabled = True
        self.auto_response_enabled = True
        self.auto_deletion_enabled = True
        self.consent_expiry_enabled = True
        
        # Cache TTL settings
        self.request_cache_ttl = 3600  # 1 hour
        self.consent_cache_ttl = 1800  # 30 minutes
        self.report_cache_ttl = 86400  # 24 hours
        
        # Legal timeframes (in days)
        self.response_deadline_days = 30
        self.erasure_deadline_days = 30
        self.portability_deadline_days = 30
        
        # Initialize default policies
        self._initialize_default_policies()
        
        # Start automation tasks
        if self.automation_enabled:
            asyncio.create_task(self._automation_loop())
        
        self.logger.info("GDPRAutomationService initialized")
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load GDPR automation configuration."""
        try:
            return {
                "dpo_contact_email": os.getenv('DPO_CONTACT_EMAIL', 'dpo@insitechart.com'),
                "company_name": os.getenv('COMPANY_NAME', 'InsiteChart'),
                "data_controller": os.getenv('DATA_CONTROLLER', 'InsiteChart Inc.'),
                "legal_basis": os.getenv('LEGAL_BASIS', 'Legitimate interest'),
                "default_retention_days": int(os.getenv('DEFAULT_RETENTION_DAYS', '365')),
                "consent_expiry_days": int(os.getenv('CONSENT_EXPIRY_DAYS', '365')),
                "encryption_required": os.getenv('ENCRYPTION_REQUIRED', 'true').lower() == 'true',
                "anonymization_required": os.getenv('ANONYMIZATION_REQUIRED', 'true').lower() == 'true',
                "audit_logging": os.getenv('AUDIT_LOGGING', 'true').lower() == 'true'
            }
        except Exception as e:
            self.logger.error(f"Error loading GDPR configuration: {str(e)}")
            return {}
    
    def _initialize_default_policies(self):
        """Initialize default GDPR policies."""
        try:
            # Default retention rules
            default_retention_rules = [
                DataRetentionRule(
                    rule_id="personal_info_default",
                    data_category=DataCategory.PERSONAL_INFO,
                    retention_policy=RetentionPolicy.YEARS_2,
                    custom_retention_days=None,
                    automated_deletion=True,
                    notification_before_deletion=True,
                    exceptions=["legal_hold", "active_request"],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                DataRetentionRule(
                    rule_id="usage_data_default",
                    data_category=DataCategory.USAGE_DATA,
                    retention_policy=RetentionPolicy.DAYS_365,
                    custom_retention_days=None,
                    automated_deletion=True,
                    notification_before_deletion=True,
                    exceptions=["active_subscription", "legal_hold"],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                DataRetentionRule(
                    rule_id="analytics_data_default",
                    data_category=DataCategory.BEHAVIORAL_DATA,
                    retention_policy=RetentionPolicy.DAYS_90,
                    custom_retention_days=None,
                    automated_deletion=True,
                    notification_before_deletion=False,
                    exceptions=["research_data", "aggregated_analytics"],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            ]
            
            for rule in default_retention_rules:
                self.retention_rules[rule.rule_id] = rule
            
            self.logger.info(f"Initialized {len(default_retention_rules)} default retention rules")
            
        except Exception as e:
            self.logger.error(f"Error initializing default policies: {str(e)}")
    
    async def _automation_loop(self):
        """Main automation loop for GDPR compliance."""
        while True:
            try:
                # Process data subject requests
                await self._process_pending_requests()
                
                # Handle consent expiry
                if self.consent_expiry_enabled:
                    await self._process_consent_expiry()
                
                # Execute data retention policies
                if self.auto_deletion_enabled:
                    await self._execute_retention_policies()
                
                # Generate compliance reports
                await self._generate_compliance_reports()
                
                # Wait for next cycle (run daily)
                await asyncio.sleep(86400)  # 24 hours
                
            except Exception as e:
                self.logger.error(f"Error in automation loop: {str(e)}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    async def create_data_subject_request(
        self,
        subject_id: str,
        request_type: DataSubjectRequestType,
        description: str,
        data_categories: List[DataCategory]
    ) -> Dict[str, Any]:
        """Create a new data subject request."""
        try:
            request_id = str(uuid.uuid4())
            created_at = datetime.utcnow()
            
            # Calculate due date based on request type
            if request_type == DataSubjectRequestType.ACCESS:
                due_date = created_at + timedelta(days=self.response_deadline_days)
            elif request_type == DataSubjectRequestType.ERASURE:
                due_date = created_at + timedelta(days=self.erasure_deadline_days)
            elif request_type == DataSubjectRequestType.PORTABILITY:
                due_date = created_at + timedelta(days=self.portability_deadline_days)
            else:
                due_date = created_at + timedelta(days=self.response_deadline_days)
            
            # Create request record
            request = DataSubjectRequest(
                request_id=request_id,
                subject_id=subject_id,
                request_type=request_type,
                status="pending",
                created_at=created_at,
                updated_at=created_at,
                due_date=due_date,
                description=description,
                data_categories=data_categories,
                response_data=None,
                processing_notes=[],
                automated_actions=[],
                completed_at=None
            )
            
            # Store request
            self.data_subject_requests[request_id] = request
            
            # Cache request
            cache_key = f"dsr_{request_id}"
            await self.cache_manager.set(cache_key, request.__dict__, ttl=self.request_cache_ttl)
            
            # Send confirmation notification
            await self._send_request_confirmation(request)
            
            # Auto-process if enabled
            if self.auto_response_enabled:
                await self._auto_process_request(request_id)
            
            self.logger.info(f"Created data subject request: {request_id} for subject: {subject_id}")
            
            return {
                "success": True,
                "request_id": request_id,
                "due_date": due_date.isoformat(),
                "message": "Data subject request created successfully"
            }
            
        except Exception as e:
            self.logger.error(f"Error creating data subject request: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_consent(
        self,
        subject_id: str,
        consent_type: ConsentType,
        status: ConsentStatus,
        purpose: str,
        legal_basis: str = None
    ) -> Dict[str, Any]:
        """Update consent record for a data subject."""
        try:
            consent_id = str(uuid.uuid4())
            current_time = datetime.utcnow()
            
            # Check if consent already exists
            existing_consent = None
            for cid, consent in self.consent_records.items():
                if (consent.subject_id == subject_id and 
                    consent.consent_type == consent_type and 
                    consent.status in [ConsentStatus.GRANTED, ConsentStatus.PENDING]):
                    existing_consent = consent
                    break
            
            # Create or update consent record
            if status == ConsentStatus.GRANTED:
                consent = ConsentRecord(
                    consent_id=consent_id,
                    subject_id=subject_id,
                    consent_type=consent_type,
                    status=status,
                    granted_at=current_time,
                    withdrawn_at=None,
                    expires_at=current_time + timedelta(days=self.config.get("consent_expiry_days", 365)),
                    purpose=purpose,
                    legal_basis=legal_basis or self.config.get("legal_basis", "Legitimate interest"),
                    metadata={"ip_address": self._get_client_ip(), "user_agent": self._get_user_agent()}
                )
            elif status == ConsentStatus.WITHDRAWN:
                if existing_consent:
                    consent = existing_consent
                    consent.status = status
                    consent.withdrawn_at = current_time
                    consent.metadata = {
                        **consent.metadata,
                        "withdrawal_reason": "User withdrawal",
                        "withdrawal_timestamp": current_time.isoformat()
                    }
                else:
                    consent = ConsentRecord(
                        consent_id=consent_id,
                        subject_id=subject_id,
                        consent_type=consent_type,
                        status=status,
                        granted_at=None,
                        withdrawn_at=current_time,
                        expires_at=None,
                        purpose=purpose,
                        legal_basis=legal_basis or self.config.get("legal_basis", "Legitimate interest"),
                        metadata={"withdrawal_reason": "Direct withdrawal without prior consent"}
                    )
            else:
                consent = ConsentRecord(
                    consent_id=consent_id,
                    subject_id=subject_id,
                    consent_type=consent_type,
                    status=status,
                    granted_at=None,
                    withdrawn_at=None,
                    expires_at=None,
                    purpose=purpose,
                    legal_basis=legal_basis or self.config.get("legal_basis", "Legitimate interest"),
                    metadata={}
                )
            
            # Store consent record
            self.consent_records[consent_id] = consent
            
            # Cache consent
            cache_key = f"consent_{subject_id}_{consent_type.value}"
            await self.cache_manager.set(cache_key, consent.__dict__, ttl=self.consent_cache_ttl)
            
            # Log consent change
            await self._log_consent_change(consent)
            
            self.logger.info(f"Updated consent: {consent_id} for subject: {subject_id}")
            
            return {
                "success": True,
                "consent_id": consent_id,
                "message": f"Consent updated successfully: {status.value}"
            }
            
        except Exception as e:
            self.logger.error(f"Error updating consent: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _process_pending_requests(self):
        """Process pending data subject requests."""
        try:
            current_time = datetime.utcnow()
            
            for request_id, request in self.data_subject_requests.items():
                if request.status == "pending":
                    # Check if request is overdue
                    if current_time > request.due_date:
                        await self._handle_overdue_request(request_id, request)
                    else:
                        # Auto-process based on request type
                        if request.request_type == DataSubjectRequestType.ACCESS:
                            await self._auto_process_access_request(request_id, request)
                        elif request.request_type == DataSubjectRequestType.ERASURE:
                            await self._auto_process_erasure_request(request_id, request)
                        elif request.request_type == DataSubjectRequestType.PORTABILITY:
                            await self._auto_process_portability_request(request_id, request)
                        
        except Exception as e:
            self.logger.error(f"Error processing pending requests: {str(e)}")
    
    async def _auto_process_request(self, request_id: str):
        """Auto-process a data subject request."""
        try:
            request = self.data_subject_requests.get(request_id)
            if not request or request.status != "pending":
                return
            
            # Process based on request type
            if request.request_type == DataSubjectRequestType.ACCESS:
                await self._auto_process_access_request(request_id, request)
            elif request.request_type == DataSubjectRequestType.ERASURE:
                await self._auto_process_erasure_request(request_id, request)
            elif request.request_type == DataSubjectRequestType.PORTABILITY:
                await self._auto_process_portability_request(request_id, request)
            
        except Exception as e:
            self.logger.error(f"Error auto-processing request {request_id}: {str(e)}")
    
    async def _auto_process_access_request(self, request_id: str, request: DataSubjectRequest):
        """Auto-process data access request."""
        try:
            # Collect requested data
            collected_data = await self._collect_subject_data(request.subject_id, request.data_categories)
            
            # Apply data minimization
            minimized_data = await self._apply_data_minimization(collected_data, request.data_categories)
            
            # Prepare response data
            response_data = {
                "collected_at": datetime.utcnow().isoformat(),
                "data_categories": [cat.value for cat in request.data_categories],
                "data": minimized_data,
                "format": "json",
                "encryption": self.config.get("encryption_required", True)
            }
            
            # Update request
            request.status = "completed"
            request.response_data = response_data
            request.processing_notes.append("Auto-processed data access request")
            request.automated_actions.append("Data collection and minimization")
            request.completed_at = datetime.utcnow()
            request.updated_at = datetime.utcnow()
            
            # Send response to subject
            await self._send_access_response(request)
            
            self.logger.info(f"Auto-processed access request: {request_id}")
            
        except Exception as e:
            self.logger.error(f"Error auto-processing access request {request_id}: {str(e)}")
            request.status = "error"
            request.processing_notes.append(f"Auto-processing error: {str(e)}")
            request.updated_at = datetime.utcnow()
    
    async def _auto_process_erasure_request(self, request_id: str, request: DataSubjectRequest):
        """Auto-process data erasure request."""
        try:
            # Verify identity and consent
            verification_result = await self._verify_subject_identity(request.subject_id)
            if not verification_result["verified"]:
                request.status = "verification_required"
                request.processing_notes.append("Identity verification required")
                request.updated_at = datetime.utcnow()
                return
            
            # Collect and anonymize data
            subject_data = await self._collect_subject_data(request.subject_id, request.data_categories)
            anonymized_data = await self._anonymize_data(subject_data)
            
            # Schedule deletion
            deletion_scheduled = await self._schedule_data_deletion(request.subject_id, anonymized_data)
            
            # Update request
            request.status = "in_progress"
            request.processing_notes.append("Data erasure scheduled")
            request.automated_actions.append("Data anonymization and deletion scheduling")
            request.response_data = {
                "deletion_scheduled": True,
                "deletion_date": deletion_scheduled["date"],
                "confirmation_id": deletion_scheduled["confirmation_id"]
            }
            request.updated_at = datetime.utcnow()
            
            # Send confirmation
            await self._send_erasure_confirmation(request)
            
            self.logger.info(f"Auto-processed erasure request: {request_id}")
            
        except Exception as e:
            self.logger.error(f"Error auto-processing erasure request {request_id}: {str(e)}")
            request.status = "error"
            request.processing_notes.append(f"Auto-processing error: {str(e)}")
            request.updated_at = datetime.utcnow()
    
    async def _auto_process_portability_request(self, request_id: str, request: DataSubjectRequest):
        """Auto-process data portability request."""
        try:
            # Collect requested data
            collected_data = await self._collect_subject_data(request.subject_id, request.data_categories)
            
            # Convert to portable format
            portable_data = await self._convert_to_portable_format(collected_data)
            
            # Create export package
            export_info = await self._create_export_package(request.subject_id, portable_data)
            
            # Update request
            request.status = "completed"
            request.response_data = {
                "export_id": export_info["export_id"],
                "download_url": export_info["download_url"],
                "format": export_info["format"],
                "size_mb": export_info["size_mb"],
                "expires_at": export_info["expires_at"]
            }
            request.processing_notes.append("Auto-processed data portability request")
            request.automated_actions.append("Data export and package creation")
            request.completed_at = datetime.utcnow()
            request.updated_at = datetime.utcnow()
            
            # Send download link
            await self._send_portability_response(request)
            
            self.logger.info(f"Auto-processed portability request: {request_id}")
            
        except Exception as e:
            self.logger.error(f"Error auto-processing portability request {request_id}: {str(e)}")
            request.status = "error"
            request.processing_notes.append(f"Auto-processing error: {str(e)}")
            request.updated_at = datetime.utcnow()
    
    async def _process_consent_expiry(self):
        """Process expired consent records."""
        try:
            current_time = datetime.utcnow()
            expired_consents = []
            
            for consent_id, consent in self.consent_records.items():
                if (consent.status == ConsentStatus.GRANTED and 
                    consent.expires_at and 
                    current_time >= consent.expires_at):
                    expired_consents.append(consent)
            
            # Process expired consents
            for consent in expired_consents:
                consent.status = ConsentStatus.EXPIRED
                consent.metadata = {
                    **consent.metadata,
                    "expiry_processed_at": current_time.isoformat()
                }
                
                # Log consent expiry
                await self._log_consent_expiry(consent)
                
                # Send expiry notification
                await self._send_consent_expiry_notification(consent)
            
            if expired_consents:
                self.logger.info(f"Processed {len(expired_consents)} expired consents")
            
        except Exception as e:
            self.logger.error(f"Error processing consent expiry: {str(e)}")
    
    async def _execute_retention_policies(self):
        """Execute data retention policies."""
        try:
            current_time = datetime.utcnow()
            executed_deletions = []
            
            for rule_id, rule in self.retention_rules.items():
                if rule.automated_deletion:
                    # Find data subject to which this rule applies
                    subjects_to_delete = await self._find_subjects_for_retention_rule(rule)
                    
                    for subject_id in subjects_to_delete:
                        # Check if subject has legal hold or active request
                        if await self._has_legal_hold(subject_id):
                            continue
                        
                        # Execute deletion
                        deletion_result = await self._execute_data_deletion(subject_id, rule.data_category)
                        if deletion_result["success"]:
                            executed_deletions.append({
                                "subject_id": subject_id,
                                "data_category": rule.data_category.value,
                                "deletion_id": deletion_result["deletion_id"],
                                "deleted_at": current_time.isoformat()
                            })
                            
                            # Send notification if required
                            if rule.notification_before_deletion:
                                await self._send_deletion_notification(subject_id, rule)
            
            if executed_deletions:
                self.logger.info(f"Executed {len(executed_deletions)} data deletions")
            
        except Exception as e:
            self.logger.error(f"Error executing retention policies: {str(e)}")
    
    async def _generate_compliance_reports(self):
        """Generate GDPR compliance reports."""
        try:
            # Check if daily report should be generated
            last_report_date = self._get_last_report_date()
            current_date = datetime.utcnow().date()
            
            if last_report_date and last_report_date >= current_date:
                return  # Already generated today's report
            
            # Calculate report period
            period_end = datetime.utcnow()
            period_start = period_end - timedelta(days=1)  # Yesterday's report
            
            # Calculate compliance metrics
            total_requests = len(self.data_subject_requests)
            completed_requests = len([r for r in self.data_subject_requests.values() if r.status == "completed"])
            overdue_requests = len([r for r in self.data_subject_requests.values() 
                               if r.status == "pending" and r.due_date < period_end])
            
            # Calculate consent metrics
            granted_consents = len([c for c in self.consent_records.values() if c.status == ConsentStatus.GRANTED])
            denied_consents = len([c for c in self.consent_records.values() if c.status == ConsentStatus.DENIED])
            
            # Calculate compliance score
            compliance_score = self._calculate_compliance_score(
                total_requests, completed_requests, overdue_requests
            )
            
            # Generate recommendations
            recommendations = self._generate_compliance_recommendations(
                total_requests, completed_requests, overdue_requests, compliance_score
            )
            
            # Create report
            report = ComplianceReport(
                report_id=str(uuid.uuid4()),
                report_type="daily_compliance",
                period_start=period_start,
                period_end=period_end,
                generated_at=datetime.utcnow(),
                total_requests=total_requests,
                completed_requests=completed_requests,
                overdue_requests=overdue_requests,
                data_subjects_count=len(set(r.subject_id for r in self.data_subject_requests.values())),
                consents_granted=granted_consents,
                consents_denied=denied_consents,
                data_breaches=0,  # Would be populated from security system
                automated_actions=len([r for r in self.data_subject_requests.values() if r.automated_actions]),
                compliance_score=compliance_score,
                recommendations=recommendations
            )
            
            # Store report
            self.compliance_reports.append(report)
            
            # Cache report
            cache_key = f"compliance_report_{report.report_id}"
            await self.cache_manager.set(cache_key, report.__dict__, ttl=self.report_cache_ttl)
            
            # Send report to DPO
            await self._send_compliance_report(report)
            
            self.logger.info(f"Generated compliance report: {report.report_id}")
            
        except Exception as e:
            self.logger.error(f"Error generating compliance report: {str(e)}")
    
    async def _collect_subject_data(self, subject_id: str, data_categories: List[DataCategory]) -> Dict[str, Any]:
        """Collect data for a subject based on categories."""
        try:
            # This would typically query your database for subject data
            # For now, return mock data
            mock_data = {}
            
            for category in data_categories:
                if category == DataCategory.PERSONAL_INFO:
                    mock_data[category.value] = {
                        "name": "John Doe",
                        "email": "john.doe@example.com",
                        "phone": "+1234567890"
                    }
                elif category == DataCategory.USAGE_DATA:
                    mock_data[category.value] = {
                        "login_count": 150,
                        "last_login": datetime.utcnow().isoformat(),
                        "features_used": ["charts", "sentiment", "correlation"]
                    }
                elif category == DataCategory.FINANCIAL_INFO:
                    mock_data[category.value] = {
                        "subscription_type": "premium",
                        "payment_method": "credit_card",
                        "billing_address": "123 Main St, City, State"
                    }
                else:
                    mock_data[category.value] = {}
            
            return mock_data
            
        except Exception as e:
            self.logger.error(f"Error collecting subject data: {str(e)}")
            return {}
    
    async def _apply_data_minimization(self, data: Dict[str, Any], categories: List[DataCategory]) -> Dict[str, Any]:
        """Apply data minimization principles."""
        try:
            if not self.config.get("anonymization_required", True):
                return data
            
            # Apply minimization based on data categories
            minimized_data = {}
            
            for category in categories:
                if category in data:
                    category_data = data[category]
                    
                    if category == DataCategory.PERSONAL_INFO:
                        # Minimize personal info - keep only essential
                        if isinstance(category_data, dict):
                            minimized_data[category.value] = {
                                "email": category_data.get("email"),
                                "name": category_data.get("name", "User"),
                                # Remove phone, address, etc. unless necessary
                            }
                    elif category == DataCategory.USAGE_DATA:
                        # Keep only recent usage data
                        if isinstance(category_data, dict):
                            minimized_data[category.value] = {
                                "last_login": category_data.get("last_login"),
                                "features_used": category_data.get("features_used", [])[:5],  # Last 5 features
                                "login_count": min(category_data.get("login_count", 0), 100)  # Cap at 100
                            }
                    else:
                        minimized_data[category.value] = category_data
                else:
                    minimized_data[category.value] = data[category]
            
            return minimized_data
            
        except Exception as e:
            self.logger.error(f"Error applying data minimization: {str(e)}")
            return data
    
    async def _anonymize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Anonymize personal data."""
        try:
            if not self.config.get("anonymization_required", True):
                return data
            
            anonymized_data = {}
            
            for key, value in data.items():
                if isinstance(value, str):
                    # Hash sensitive string values
                    if any(sensitive in key.lower() for sensitive in ["email", "phone", "name", "address"]):
                        anonymized_data[key] = hashlib.sha256(value.encode()).hexdigest()[:16]
                    else:
                        anonymized_data[key] = value
                elif isinstance(value, dict):
                    # Recursively anonymize nested dictionaries
                    anonymized_data[key] = await self._anonymize_data(value)
                else:
                    anonymized_data[key] = value
            
            return anonymized_data
            
        except Exception as e:
            self.logger.error(f"Error anonymizing data: {str(e)}")
            return data
    
    async def _convert_to_portable_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert data to portable format (JSON/CSV)."""
        try:
            # Create portable data package
            portable_data = {
                "export_date": datetime.utcnow().isoformat(),
                "format": "json",
                "version": "1.0",
                "data": data
            }
            
            return portable_data
            
        except Exception as e:
            self.logger.error(f"Error converting to portable format: {str(e)}")
            return {}
    
    async def _create_export_package(self, subject_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create export package for data portability."""
        try:
            export_id = str(uuid.uuid4())
            
            # Create export file (in real implementation)
            export_size = len(json.dumps(data)) / 1024  # Size in KB
            
            # Generate secure download URL
            download_url = f"/api/gdpr/download/{export_id}"
            expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
            
            return {
                "export_id": export_id,
                "download_url": download_url,
                "format": "json",
                "size_mb": export_size / 1024,
                "expires_at": expires_at
            }
            
        except Exception as e:
            self.logger.error(f"Error creating export package: {str(e)}")
            return {}
    
    async def _verify_subject_identity(self, subject_id: str) -> Dict[str, Any]:
        """Verify data subject identity."""
        try:
            # This would typically verify identity through multi-factor authentication
            # For now, return mock verification
            return {
                "verified": True,
                "method": "email_verification",
                "verified_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error verifying subject identity: {str(e)}")
            return {"verified": False, "error": str(e)}
    
    async def _schedule_data_deletion(self, subject_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule data deletion."""
        try:
            deletion_id = str(uuid.uuid4())
            deletion_date = datetime.utcnow() + timedelta(days=30)  # 30 days grace period
            
            return {
                "deletion_id": deletion_id,
                "date": deletion_date.isoformat(),
                "confirmation_id": str(uuid.uuid4())
            }
            
        except Exception as e:
            self.logger.error(f"Error scheduling data deletion: {str(e)}")
            return {}
    
    async def _execute_data_deletion(self, subject_id: str, data_category: DataCategory) -> Dict[str, Any]:
        """Execute data deletion."""
        try:
            deletion_id = str(uuid.uuid4())
            
            # This would actually delete data from your database
            # For now, return mock result
            return {
                "success": True,
                "deletion_id": deletion_id,
                "deleted_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error executing data deletion: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _find_subjects_for_retention_rule(self, rule: DataRetentionRule) -> List[str]:
        """Find subjects that match retention rule."""
        try:
            # This would query your database for subjects matching the rule
            # For now, return mock subject IDs
            return ["subject_1", "subject_2", "subject_3"]
            
        except Exception as e:
            self.logger.error(f"Error finding subjects for retention rule: {str(e)}")
            return []
    
    async def _has_legal_hold(self, subject_id: str) -> bool:
        """Check if subject has legal hold."""
        try:
            # This would check for legal holds in your system
            # For now, return False
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking legal hold: {str(e)}")
            return False
    
    def _calculate_compliance_score(self, total: int, completed: int, overdue: int) -> float:
        """Calculate GDPR compliance score."""
        try:
            if total == 0:
                return 100.0
            
            # Base score from completion rate
            completion_rate = completed / total
            base_score = completion_rate * 80  # 80% weight
            
            # Penalty for overdue requests
            overdue_rate = overdue / total
            overdue_penalty = overdue_rate * 50  # 50% penalty
            
            # Calculate final score
            score = max(0, base_score - overdue_penalty)
            
            return round(score, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating compliance score: {str(e)}")
            return 0.0
    
    def _generate_compliance_recommendations(
        self, 
        total: int, 
        completed: int, 
        overdue: int, 
        score: float
    ) -> List[str]:
        """Generate compliance recommendations."""
        try:
            recommendations = []
            
            if score < 70:
                recommendations.append("Compliance score is below threshold - review processes")
            
            if overdue > 0:
                recommendations.append(f"{overdue} requests are overdue - prioritize processing")
            
            completion_rate = completed / total if total > 0 else 0
            if completion_rate < 0.8:
                recommendations.append("Request completion rate is low - investigate bottlenecks")
            
            if not recommendations:
                recommendations.append("Compliance metrics are within acceptable ranges")
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {str(e)}")
            return ["Error generating recommendations"]
    
    def _get_last_report_date(self) -> Optional[datetime]:
        """Get date of last compliance report."""
        try:
            if not self.compliance_reports:
                return None
            
            # Get most recent report
            latest_report = max(self.compliance_reports, key=lambda x: x.generated_at)
            return latest_report.generated_at.date()
            
        except Exception as e:
            self.logger.error(f"Error getting last report date: {str(e)}")
            return None
    
    def _get_client_ip(self) -> str:
        """Get client IP address."""
        # This would typically get the real client IP
        return "127.0.0.1"  # Mock IP
    
    def _get_user_agent(self) -> str:
        """Get user agent string."""
        # This would typically get the real user agent
        return "GDPR Automation Service/1.0"  # Mock user agent
    
    async def _send_request_confirmation(self, request: DataSubjectRequest):
        """Send request confirmation to data subject."""
        try:
            # This would send an email or notification
            self.logger.info(f"Request confirmation sent for: {request.request_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending request confirmation: {str(e)}")
    
    async def _send_access_response(self, request: DataSubjectRequest):
        """Send access response to data subject."""
        try:
            # This would send an email with download link
            self.logger.info(f"Access response sent for: {request.request_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending access response: {str(e)}")
    
    async def _send_erasure_confirmation(self, request: DataSubjectRequest):
        """Send erasure confirmation to data subject."""
        try:
            # This would send an email with deletion details
            self.logger.info(f"Erasure confirmation sent for: {request.request_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending erasure confirmation: {str(e)}")
    
    async def _send_portability_response(self, request: DataSubjectRequest):
        """Send portability response to data subject."""
        try:
            # This would send an email with download link
            self.logger.info(f"Portability response sent for: {request.request_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending portability response: {str(e)}")
    
    async def _send_consent_expiry_notification(self, consent: ConsentRecord):
        """Send consent expiry notification."""
        try:
            # This would send an email about consent expiry
            self.logger.info(f"Consent expiry notification sent for: {consent.consent_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending consent expiry notification: {str(e)}")
    
    async def _send_deletion_notification(self, subject_id: str, rule: DataRetentionRule):
        """Send deletion notification to data subject."""
        try:
            # This would send an email about scheduled deletion
            self.logger.info(f"Deletion notification sent for subject: {subject_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending deletion notification: {str(e)}")
    
    async def _log_consent_change(self, consent: ConsentRecord):
        """Log consent change for audit trail."""
        try:
            # This would log to your audit system
            self.logger.info(f"Consent change logged: {consent.consent_id}")
            
        except Exception as e:
            self.logger.error(f"Error logging consent change: {str(e)}")
    
    async def _log_consent_expiry(self, consent: ConsentRecord):
        """Log consent expiry for audit trail."""
        try:
            # This would log to your audit system
            self.logger.info(f"Consent expiry logged: {consent.consent_id}")
            
        except Exception as e:
            self.logger.error(f"Error logging consent expiry: {str(e)}")
    
    async def _send_compliance_report(self, report: ComplianceReport):
        """Send compliance report to DPO."""
        try:
            # This would email the report to the DPO
            self.logger.info(f"Compliance report sent: {report.report_id}")
            
        except Exception as e:
            self.logger.error(f"Error sending compliance report: {str(e)}")
    
    async def _handle_overdue_request(self, request_id: str, request: DataSubjectRequest):
        """Handle overdue data subject request."""
        try:
            request.status = "overdue"
            request.processing_notes.append(f"Request overdue by {(datetime.utcnow() - request.due_date).days} days")
            request.updated_at = datetime.utcnow()
            
            # Escalate to DPO
            await self._escalate_to_dpo(request_id, request)
            
        except Exception as e:
            self.logger.error(f"Error handling overdue request {request_id}: {str(e)}")
    
    async def _escalate_to_dpo(self, request_id: str, request: DataSubjectRequest):
        """Escalate overdue request to DPO."""
        try:
            # This would notify the DPO about the overdue request
            self.logger.info(f"Request escalated to DPO: {request_id}")
            
        except Exception as e:
            self.logger.error(f"Error escalating to DPO {request_id}: {str(e)}")
    
    async def get_data_subject_requests(
        self,
        subject_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get data subject requests."""
        try:
            requests = list(self.data_subject_requests.values())
            
            # Apply filters
            if subject_id:
                requests = [r for r in requests if r.subject_id == subject_id]
            
            if status:
                requests = [r for r in requests if r.status == status]
            
            # Sort by creation date (newest first)
            requests.sort(key=lambda x: x.created_at, reverse=True)
            
            # Apply limit
            requests = requests[:limit]
            
            # Convert to dictionaries
            return [
                {
                    "request_id": r.request_id,
                    "subject_id": r.subject_id,
                    "request_type": r.request_type.value,
                    "status": r.status,
                    "created_at": r.created_at.isoformat(),
                    "updated_at": r.updated_at.isoformat(),
                    "due_date": r.due_date.isoformat(),
                    "description": r.description,
                    "data_categories": [cat.value for cat in r.data_categories],
                    "processing_notes": r.processing_notes,
                    "automated_actions": r.automated_actions,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None
                }
                for r in requests
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting data subject requests: {str(e)}")
            return []
    
    async def get_consent_records(
        self,
        subject_id: Optional[str] = None,
        consent_type: Optional[ConsentType] = None,
        status: Optional[ConsentStatus] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get consent records."""
        try:
            records = list(self.consent_records.values())
            
            # Apply filters
            if subject_id:
                records = [r for r in records if r.subject_id == subject_id]
            
            if consent_type:
                records = [r for r in records if r.consent_type == consent_type]
            
            if status:
                records = [r for r in records if r.status == status]
            
            # Sort by granted date (newest first)
            records.sort(key=lambda x: x.granted_at or x.created_at, reverse=True)
            
            # Apply limit
            records = records[:limit]
            
            # Convert to dictionaries
            return [
                {
                    "consent_id": r.consent_id,
                    "subject_id": r.subject_id,
                    "consent_type": r.consent_type.value,
                    "status": r.status.value,
                    "purpose": r.purpose,
                    "legal_basis": r.legal_basis,
                    "granted_at": r.granted_at.isoformat() if r.granted_at else None,
                    "withdrawn_at": r.withdrawn_at.isoformat() if r.withdrawn_at else None,
                    "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                    "metadata": r.metadata
                }
                for r in records
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting consent records: {str(e)}")
            return []
    
    async def get_retention_rules(self) -> List[Dict[str, Any]]:
        """Get data retention rules."""
        try:
            rules = list(self.retention_rules.values())
            
            # Sort by creation date (newest first)
            rules.sort(key=lambda x: x.created_at, reverse=True)
            
            # Convert to dictionaries
            return [
                {
                    "rule_id": r.rule_id,
                    "data_category": r.data_category.value,
                    "retention_policy": r.retention_policy.value,
                    "custom_retention_days": r.custom_retention_days,
                    "automated_deletion": r.automated_deletion,
                    "notification_before_deletion": r.notification_before_deletion,
                    "exceptions": r.exceptions,
                    "created_at": r.created_at.isoformat(),
                    "updated_at": r.updated_at.isoformat()
                }
                for r in rules
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting retention rules: {str(e)}")
            return []
    
    async def get_compliance_reports(
        self,
        report_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get compliance reports."""
        try:
            reports = self.compliance_reports
            
            # Apply filter
            if report_type:
                reports = [r for r in reports if r.report_type == report_type]
            
            # Sort by generation date (newest first)
            reports.sort(key=lambda x: x.generated_at, reverse=True)
            
            # Apply limit
            reports = reports[:limit]
            
            # Convert to dictionaries
            return [
                {
                    "report_id": r.report_id,
                    "report_type": r.report_type,
                    "period_start": r.period_start.isoformat(),
                    "period_end": r.period_end.isoformat(),
                    "generated_at": r.generated_at.isoformat(),
                    "total_requests": r.total_requests,
                    "completed_requests": r.completed_requests,
                    "overdue_requests": r.overdue_requests,
                    "data_subjects_count": r.data_subjects_count,
                    "consents_granted": r.consents_granted,
                    "consents_denied": r.consents_denied,
                    "data_breaches": r.data_breaches,
                    "automated_actions": r.automated_actions,
                    "compliance_score": r.compliance_score,
                    "recommendations": r.recommendations
                }
                for r in reports
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting compliance reports: {str(e)}")
            return []
    
    async def get_gdpr_status(self) -> Dict[str, Any]:
        """Get overall GDPR compliance status."""
        try:
            # Calculate current metrics
            total_requests = len(self.data_subject_requests)
            pending_requests = len([r for r in self.data_subject_requests.values() if r.status == "pending"])
            overdue_requests = len([r for r in self.data_subject_requests.values() 
                               if r.status == "pending" and r.due_date < datetime.utcnow()])
            
            active_consents = len([c for c in self.consent_records.values() if c.status == ConsentStatus.GRANTED])
            expired_consents = len([c for c in self.consent_records.values() if c.status == ConsentStatus.EXPIRED])
            
            # Calculate compliance score
            completed_requests = len([r for r in self.data_subject_requests.values() if r.status == "completed"])
            compliance_score = self._calculate_compliance_score(
                total_requests, completed_requests, overdue_requests
            )
            
            return {
                "automation_enabled": self.automation_enabled,
                "auto_response_enabled": self.auto_response_enabled,
                "auto_deletion_enabled": self.auto_deletion_enabled,
                "consent_expiry_enabled": self.consent_expiry_enabled,
                "metrics": {
                    "total_requests": total_requests,
                    "pending_requests": pending_requests,
                    "overdue_requests": overdue_requests,
                    "completed_requests": completed_requests,
                    "active_consents": active_consents,
                    "expired_consents": expired_consents,
                    "retention_rules": len(self.retention_rules),
                    "compliance_score": compliance_score
                },
                "configuration": self.config,
                "last_automation_run": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting GDPR status: {str(e)}")
            return {"error": str(e)}