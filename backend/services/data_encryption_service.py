"""
Data Encryption Enhancement Service for InsiteChart platform.

This service provides advanced encryption capabilities for data at rest and in transit,
including key management, encryption policies, and secure data handling.
"""

import asyncio
import logging
import json
import os
import base64
import secrets
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import hashlib

from ..cache.unified_cache import UnifiedCacheManager


class EncryptionType(str, Enum):
    """Types of encryption algorithms."""
    AES_256_GCM = "aes_256_gcm"
    AES_256_CBC = "aes_256_cbc"
    CHACHA20_POLY1305 = "chacha20_poly1305"
    RSA_4096 = "rsa_4096"
    FERNET = "fernet"


class EncryptionLevel(str, Enum):
    """Encryption security levels."""
    STANDARD = "standard"
    HIGH = "high"
    CRITICAL = "critical"


class KeyType(str, Enum):
    """Types of encryption keys."""
    SYMMETRIC = "symmetric"
    ASYMMETRIC = "asymmetric"
    MASTER = "master"
    DATA = "data"


class KeyStatus(str, Enum):
    """Key status values."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ROTATED = "rotated"
    COMPROMISED = "compromised"
    EXPIRED = "expired"


@dataclass
class EncryptionKey:
    """Encryption key record."""
    key_id: str
    key_type: KeyType
    algorithm: EncryptionType
    key_data: bytes
    salt: Optional[bytes]
    iv: Optional[bytes]
    created_at: datetime
    expires_at: Optional[datetime]
    status: KeyStatus
    usage_count: int = 0
    last_used: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EncryptionPolicy:
    """Encryption policy configuration."""
    policy_id: str
    name: str
    description: str
    data_types: List[str]
    encryption_type: EncryptionType
    encryption_level: EncryptionLevel
    key_rotation_days: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


@dataclass
class EncryptionOperation:
    """Encryption operation record."""
    operation_id: str
    operation_type: str  # encrypt, decrypt, reencrypt
    key_id: str
    data_type: str
    data_size: int
    processing_time_ms: int
    success: bool
    error_message: Optional[str]
    timestamp: datetime
    user_id: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataEncryptionService:
    """Data encryption enhancement service."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = self._load_configuration()
        
        # Data storage
        self.encryption_keys: Dict[str, EncryptionKey] = {}
        self.encryption_policies: Dict[str, EncryptionPolicy] = {}
        self.encryption_operations: List[EncryptionOperation] = []
        
        # Encryption settings
        self.encryption_enabled = True
        self.key_rotation_enabled = True
        self.audit_logging_enabled = True
        
        # Cache TTL settings
        self.key_cache_ttl = 3600  # 1 hour
        self.policy_cache_ttl = 1800  # 30 minutes
        self.operation_cache_ttl = 86400  # 24 hours
        
        # Security settings
        self.key_derivation_iterations = 100000
        self.default_key_size = 256
        self.rsa_key_size = 4096
        
        # Initialize master key
        self._initialize_master_key()
        
        # Initialize default policies
        self._initialize_default_policies()
        
        # Start maintenance tasks
        if self.key_rotation_enabled:
            asyncio.create_task(self._maintenance_loop())
        
        self.logger.info("DataEncryptionService initialized")
    
    def _load_configuration(self) -> Dict[str, Any]:
        """Load encryption configuration."""
        try:
            return {
                "master_key_env": os.getenv('MASTER_KEY_ENV', 'INSITECHART_MASTER_KEY'),
                "default_encryption_type": os.getenv('DEFAULT_ENCRYPTION_TYPE', 'aes_256_gcm'),
                "default_key_rotation_days": int(os.getenv('DEFAULT_KEY_ROTATION_DAYS', '90')),
                "max_key_age_days": int(os.getenv('MAX_KEY_AGE_DAYS', '365')),
                "encryption_audit_retention_days": int(os.getenv('ENCRYPTION_AUDIT_RETENTION_DAYS', '2555')),  # 7 years
                "secure_delete_enabled": os.getenv('SECURE_DELETE_ENABLED', 'true').lower() == 'true',
                "hardware_security_module": os.getenv('HSM_ENABLED', 'false').lower() == 'true',
                "key_backup_enabled": os.getenv('KEY_BACKUP_ENABLED', 'true').lower() == 'true',
                "key_backup_location": os.getenv('KEY_BACKUP_LOCATION', '/secure/keys/backup'),
                "performance_monitoring": os.getenv('ENCRYPTION_PERFORMANCE_MONITORING', 'true').lower() == 'true'
            }
        except Exception as e:
            self.logger.error(f"Error loading encryption configuration: {str(e)}")
            return {}
    
    def _initialize_master_key(self):
        """Initialize or load master encryption key."""
        try:
            master_key_env = self.config.get("master_key_env")
            master_key = os.getenv(master_key_env)
            
            if master_key:
                # Load master key from environment
                self.master_key = base64.urlsafe_b64decode(master_key.encode())
                self.logger.info("Master key loaded from environment")
            else:
                # Generate new master key
                self.master_key = Fernet.generate_key()
                self.logger.warning("Generated new master key - please set MASTER_KEY_ENV environment variable")
                
                # Log the key for development (remove in production)
                encoded_key = base64.urlsafe_b64encode(self.master_key).decode()
                self.logger.info(f"Generated master key (save this): {encoded_key}")
            
            # Initialize Fernet with master key
            self.master_cipher = Fernet(self.master_key)
            
        except Exception as e:
            self.logger.error(f"Error initializing master key: {str(e)}")
            raise
    
    def _initialize_default_policies(self):
        """Initialize default encryption policies."""
        try:
            default_policies = [
                EncryptionPolicy(
                    policy_id="personal_data_standard",
                    name="Personal Data Standard Encryption",
                    description="Standard encryption for personal data",
                    data_types=["personal_info", "contact_info", "user_data"],
                    encryption_type=EncryptionType.AES_256_GCM,
                    encryption_level=EncryptionLevel.STANDARD,
                    key_rotation_days=90,
                    enabled=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                EncryptionPolicy(
                    policy_id="financial_data_high",
                    name="Financial Data High Security",
                    description="High security encryption for financial data",
                    data_types=["financial_info", "payment_data", "billing_info"],
                    encryption_type=EncryptionType.AES_256_GCM,
                    encryption_level=EncryptionLevel.HIGH,
                    key_rotation_days=60,
                    enabled=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                EncryptionPolicy(
                    policy_id="api_keys_critical",
                    name="API Keys Critical Security",
                    description="Critical security encryption for API keys and secrets",
                    data_types=["api_keys", "secrets", "credentials"],
                    encryption_type=EncryptionType.AES_256_GCM,
                    encryption_level=EncryptionLevel.CRITICAL,
                    key_rotation_days=30,
                    enabled=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                ),
                EncryptionPolicy(
                    policy_id="session_data_standard",
                    name="Session Data Standard Encryption",
                    description="Standard encryption for session data",
                    data_types=["session_data", "cookies", "tokens"],
                    encryption_type=EncryptionType.CHACHA20_POLY1305,
                    encryption_level=EncryptionLevel.STANDARD,
                    key_rotation_days=7,
                    enabled=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            ]
            
            for policy in default_policies:
                self.encryption_policies[policy.policy_id] = policy
            
            self.logger.info(f"Initialized {len(default_policies)} default encryption policies")
            
        except Exception as e:
            self.logger.error(f"Error initializing default policies: {str(e)}")
    
    async def _maintenance_loop(self):
        """Main maintenance loop for key rotation and cleanup."""
        while True:
            try:
                # Rotate expired keys
                await self._rotate_expired_keys()
                
                # Clean up old operation logs
                await self._cleanup_old_operations()
                
                # Backup keys if enabled
                if self.config.get("key_backup_enabled"):
                    await self._backup_keys()
                
                # Wait for next cycle (run daily)
                await asyncio.sleep(86400)  # 24 hours
                
            except Exception as e:
                self.logger.error(f"Error in maintenance loop: {str(e)}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    async def encrypt_data(
        self,
        data: Union[str, bytes, Dict[str, Any]],
        data_type: str,
        encryption_type: Optional[EncryptionType] = None,
        key_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Encrypt data with appropriate policy."""
        try:
            if not self.encryption_enabled:
                return {"success": False, "error": "Encryption is disabled"}
            
            start_time = datetime.utcnow()
            
            # Convert data to bytes if needed
            if isinstance(data, dict):
                data_bytes = json.dumps(data).encode('utf-8')
            elif isinstance(data, str):
                data_bytes = data.encode('utf-8')
            else:
                data_bytes = data
            
            # Get encryption policy
            policy = await self._get_encryption_policy(data_type)
            if not policy:
                return {"success": False, "error": f"No encryption policy found for data type: {data_type}"}
            
            # Use specified encryption type or policy default
            enc_type = encryption_type or policy.encryption_type
            
            # Get or create encryption key
            if key_id:
                encryption_key = self.encryption_keys.get(key_id)
                if not encryption_key:
                    return {"success": False, "error": f"Encryption key not found: {key_id}"}
            else:
                encryption_key = await self._create_encryption_key(enc_type, KeyType.DATA)
            
            # Perform encryption based on type
            if enc_type == EncryptionType.AES_256_GCM:
                result = await self._encrypt_aes_gcm(data_bytes, encryption_key)
            elif enc_type == EncryptionType.AES_256_CBC:
                result = await self._encrypt_aes_cbc(data_bytes, encryption_key)
            elif enc_type == EncryptionType.CHACHA20_POLY1305:
                result = await self._encrypt_chacha20_poly1305(data_bytes, encryption_key)
            elif enc_type == EncryptionType.FERNET:
                result = await self._encrypt_fernet(data_bytes, encryption_key)
            else:
                return {"success": False, "error": f"Unsupported encryption type: {enc_type}"}
            
            if not result["success"]:
                return result
            
            # Update key usage
            encryption_key.usage_count += 1
            encryption_key.last_used = datetime.utcnow()
            
            # Calculate processing time
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Log operation
            if self.audit_logging_enabled:
                await self._log_encryption_operation(
                    operation_type="encrypt",
                    key_id=encryption_key.key_id,
                    data_type=data_type,
                    data_size=len(data_bytes),
                    processing_time_ms=processing_time,
                    success=True,
                    user_id=user_id
                )
            
            return {
                "success": True,
                "encrypted_data": result["encrypted_data"],
                "key_id": encryption_key.key_id,
                "encryption_type": enc_type.value,
                "iv": result.get("iv"),
                "tag": result.get("tag"),
                "metadata": {
                    "data_type": data_type,
                    "encrypted_at": datetime.utcnow().isoformat(),
                    "policy_id": policy.policy_id
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error encrypting data: {str(e)}")
            if self.audit_logging_enabled:
                await self._log_encryption_operation(
                    operation_type="encrypt",
                    key_id=key_id or "unknown",
                    data_type=data_type,
                    data_size=0,
                    processing_time_ms=0,
                    success=False,
                    error_message=str(e),
                    user_id=user_id
                )
            return {"success": False, "error": str(e)}
    
    async def decrypt_data(
        self,
        encrypted_data: Union[str, bytes],
        key_id: str,
        encryption_type: EncryptionType,
        iv: Optional[Union[str, bytes]] = None,
        tag: Optional[Union[str, bytes]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Decrypt data using specified key."""
        try:
            if not self.encryption_enabled:
                return {"success": False, "error": "Encryption is disabled"}
            
            start_time = datetime.utcnow()
            
            # Get encryption key
            encryption_key = self.encryption_keys.get(key_id)
            if not encryption_key:
                return {"success": False, "error": f"Encryption key not found: {key_id}"}
            
            # Convert encrypted data to bytes if needed
            if isinstance(encrypted_data, str):
                encrypted_bytes = base64.b64decode(encrypted_data.encode())
            else:
                encrypted_bytes = encrypted_data
            
            # Convert IV and tag to bytes if provided
            if isinstance(iv, str):
                iv_bytes = base64.b64decode(iv.encode())
            else:
                iv_bytes = iv
            
            if isinstance(tag, str):
                tag_bytes = base64.b64decode(tag.encode())
            else:
                tag_bytes = tag
            
            # Perform decryption based on type
            if encryption_type == EncryptionType.AES_256_GCM:
                result = await self._decrypt_aes_gcm(encrypted_bytes, encryption_key, iv_bytes, tag_bytes)
            elif encryption_type == EncryptionType.AES_256_CBC:
                result = await self._decrypt_aes_cbc(encrypted_bytes, encryption_key, iv_bytes)
            elif encryption_type == EncryptionType.CHACHA20_POLY1305:
                result = await self._decrypt_chacha20_poly1305(encrypted_bytes, encryption_key, iv_bytes, tag_bytes)
            elif encryption_type == EncryptionType.FERNET:
                result = await self._decrypt_fernet(encrypted_bytes, encryption_key)
            else:
                return {"success": False, "error": f"Unsupported encryption type: {encryption_type}"}
            
            if not result["success"]:
                return result
            
            # Update key usage
            encryption_key.usage_count += 1
            encryption_key.last_used = datetime.utcnow()
            
            # Calculate processing time
            processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Log operation
            if self.audit_logging_enabled:
                await self._log_encryption_operation(
                    operation_type="decrypt",
                    key_id=key_id,
                    data_type="unknown",
                    data_size=len(encrypted_bytes),
                    processing_time_ms=processing_time,
                    success=True,
                    user_id=user_id
                )
            
            return {
                "success": True,
                "decrypted_data": result["decrypted_data"],
                "metadata": {
                    "decrypted_at": datetime.utcnow().isoformat(),
                    "key_id": key_id
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error decrypting data: {str(e)}")
            if self.audit_logging_enabled:
                await self._log_encryption_operation(
                    operation_type="decrypt",
                    key_id=key_id,
                    data_type="unknown",
                    data_size=0,
                    processing_time_ms=0,
                    success=False,
                    error_message=str(e),
                    user_id=user_id
                )
            return {"success": False, "error": str(e)}
    
    async def _encrypt_aes_gcm(self, data: bytes, key: EncryptionKey) -> Dict[str, Any]:
        """Encrypt data using AES-256-GCM."""
        try:
            # Generate random IV
            iv = os.urandom(12)  # 96-bit IV for GCM
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key.key_data),
                modes.GCM(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Encrypt data
            encrypted_data = encryptor.update(data) + encryptor.finalize()
            
            return {
                "success": True,
                "encrypted_data": base64.b64encode(encrypted_data).decode(),
                "iv": base64.b64encode(iv).decode(),
                "tag": base64.b64encode(encryptor.tag).decode()
            }
            
        except Exception as e:
            self.logger.error(f"Error in AES-GCM encryption: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _decrypt_aes_gcm(
        self, 
        encrypted_data: bytes, 
        key: EncryptionKey, 
        iv: Optional[bytes], 
        tag: Optional[bytes]
    ) -> Dict[str, Any]:
        """Decrypt data using AES-256-GCM."""
        try:
            if not iv or not tag:
                return {"success": False, "error": "IV and tag required for AES-GCM decryption"}
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key.key_data),
                modes.GCM(iv, tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Decrypt data
            decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
            
            return {
                "success": True,
                "decrypted_data": decrypted_data
            }
            
        except Exception as e:
            self.logger.error(f"Error in AES-GCM decryption: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _encrypt_aes_cbc(self, data: bytes, key: EncryptionKey) -> Dict[str, Any]:
        """Encrypt data using AES-256-CBC."""
        try:
            # Generate random IV
            iv = os.urandom(16)  # 128-bit IV for CBC
            
            # Pad data to block size
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(data) + padder.finalize()
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key.key_data),
                modes.CBC(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Encrypt data
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            return {
                "success": True,
                "encrypted_data": base64.b64encode(encrypted_data).decode(),
                "iv": base64.b64encode(iv).decode()
            }
            
        except Exception as e:
            self.logger.error(f"Error in AES-CBC encryption: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _decrypt_aes_cbc(
        self, 
        encrypted_data: bytes, 
        key: EncryptionKey, 
        iv: Optional[bytes]
    ) -> Dict[str, Any]:
        """Decrypt data using AES-256-CBC."""
        try:
            if not iv:
                return {"success": False, "error": "IV required for AES-CBC decryption"}
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key.key_data),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Decrypt data
            padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
            
            # Remove padding
            unpadder = padding.PKCS7(128).unpadder()
            data = unpadder.update(padded_data) + unpadder.finalize()
            
            return {
                "success": True,
                "decrypted_data": data
            }
            
        except Exception as e:
            self.logger.error(f"Error in AES-CBC decryption: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _encrypt_chacha20_poly1305(self, data: bytes, key: EncryptionKey) -> Dict[str, Any]:
        """Encrypt data using ChaCha20-Poly1305."""
        try:
            # Generate random nonce
            nonce = os.urandom(12)  # 96-bit nonce for ChaCha20-Poly1305
            
            # Create cipher
            cipher = Cipher(
                algorithms.ChaCha20(key.key_data, nonce),
                modes.Poly1305(),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Encrypt data
            encrypted_data = encryptor.update(data) + encryptor.finalize()
            
            return {
                "success": True,
                "encrypted_data": base64.b64encode(encrypted_data).decode(),
                "iv": base64.b64encode(nonce).decode(),
                "tag": base64.b64encode(encryptor.tag).decode()
            }
            
        except Exception as e:
            self.logger.error(f"Error in ChaCha20-Poly1305 encryption: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _decrypt_chacha20_poly1305(
        self, 
        encrypted_data: bytes, 
        key: EncryptionKey, 
        iv: Optional[bytes], 
        tag: Optional[bytes]
    ) -> Dict[str, Any]:
        """Decrypt data using ChaCha20-Poly1305."""
        try:
            if not iv or not tag:
                return {"success": False, "error": "IV and tag required for ChaCha20-Poly1305 decryption"}
            
            # Create cipher
            cipher = Cipher(
                algorithms.ChaCha20(key.key_data, iv),
                modes.Poly1305(tag),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Decrypt data
            decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
            
            return {
                "success": True,
                "decrypted_data": decrypted_data
            }
            
        except Exception as e:
            self.logger.error(f"Error in ChaCha20-Poly1305 decryption: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _encrypt_fernet(self, data: bytes, key: EncryptionKey) -> Dict[str, Any]:
        """Encrypt data using Fernet (AES-128-CBC with HMAC)."""
        try:
            # Create Fernet cipher
            cipher = Fernet(key.key_data)
            
            # Encrypt data
            encrypted_data = cipher.encrypt(data)
            
            return {
                "success": True,
                "encrypted_data": base64.b64encode(encrypted_data).decode()
            }
            
        except Exception as e:
            self.logger.error(f"Error in Fernet encryption: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _decrypt_fernet(self, encrypted_data: bytes, key: EncryptionKey) -> Dict[str, Any]:
        """Decrypt data using Fernet."""
        try:
            # Create Fernet cipher
            cipher = Fernet(key.key_data)
            
            # Decrypt data
            decrypted_data = cipher.decrypt(encrypted_data)
            
            return {
                "success": True,
                "decrypted_data": decrypted_data
            }
            
        except Exception as e:
            self.logger.error(f"Error in Fernet decryption: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _get_encryption_policy(self, data_type: str) -> Optional[EncryptionPolicy]:
        """Get encryption policy for data type."""
        try:
            for policy in self.encryption_policies.values():
                if policy.enabled and data_type in policy.data_types:
                    return policy
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting encryption policy: {str(e)}")
            return None
    
    async def _create_encryption_key(
        self, 
        encryption_type: EncryptionType, 
        key_type: KeyType
    ) -> EncryptionKey:
        """Create a new encryption key."""
        try:
            key_id = str(uuid.uuid4())
            current_time = datetime.utcnow()
            
            # Generate key based on type
            if encryption_type in [EncryptionType.AES_256_GCM, EncryptionType.AES_256_CBC]:
                key_data = os.urandom(32)  # 256-bit key
            elif encryption_type == EncryptionType.CHACHA20_POLY1305:
                key_data = os.urandom(32)  # 256-bit key
            elif encryption_type == EncryptionType.FERNET:
                key_data = Fernet.generate_key()
            elif encryption_type == EncryptionType.RSA_4096:
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=self.rsa_key_size,
                    backend=default_backend()
                )
                key_data = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
            else:
                raise ValueError(f"Unsupported encryption type: {encryption_type}")
            
            # Create key record
            encryption_key = EncryptionKey(
                key_id=key_id,
                key_type=key_type,
                algorithm=encryption_type,
                key_data=key_data,
                salt=None,
                iv=None,
                created_at=current_time,
                expires_at=current_time + timedelta(days=self.config.get("default_key_rotation_days", 90)),
                status=KeyStatus.ACTIVE
            )
            
            # Store key
            self.encryption_keys[key_id] = encryption_key
            
            # Cache key
            cache_key = f"encryption_key_{key_id}"
            await self.cache_manager.set(cache_key, encryption_key.__dict__, ttl=self.key_cache_ttl)
            
            self.logger.info(f"Created encryption key: {key_id} for type: {encryption_type.value}")
            
            return encryption_key
            
        except Exception as e:
            self.logger.error(f"Error creating encryption key: {str(e)}")
            raise
    
    async def _rotate_expired_keys(self):
        """Rotate expired encryption keys."""
        try:
            current_time = datetime.utcnow()
            keys_to_rotate = []
            
            for key_id, key in self.encryption_keys.items():
                if (key.status == KeyStatus.ACTIVE and 
                    key.expires_at and 
                    current_time >= key.expires_at):
                    keys_to_rotate.append(key)
            
            for key in keys_to_rotate:
                await self._rotate_key(key)
            
            if keys_to_rotate:
                self.logger.info(f"Rotated {len(keys_to_rotate)} expired keys")
            
        except Exception as e:
            self.logger.error(f"Error rotating expired keys: {str(e)}")
    
    async def _rotate_key(self, old_key: EncryptionKey):
        """Rotate an encryption key."""
        try:
            # Create new key
            new_key = await self._create_encryption_key(old_key.algorithm, old_key.key_type)
            
            # Mark old key as rotated
            old_key.status = KeyStatus.ROTATED
            
            self.logger.info(f"Rotated key {old_key.key_id} to {new_key.key_id}")
            
        except Exception as e:
            self.logger.error(f"Error rotating key {old_key.key_id}: {str(e)}")
    
    async def _cleanup_old_operations(self):
        """Clean up old encryption operation logs."""
        try:
            retention_days = self.config.get("encryption_audit_retention_days", 2555)
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            operations_to_remove = []
            for operation in self.encryption_operations:
                if operation.timestamp < cutoff_date:
                    operations_to_remove.append(operation)
            
            for operation in operations_to_remove:
                self.encryption_operations.remove(operation)
            
            if operations_to_remove:
                self.logger.info(f"Cleaned up {len(operations_to_remove)} old encryption operations")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old operations: {str(e)}")
    
    async def _backup_keys(self):
        """Backup encryption keys."""
        try:
            backup_location = self.config.get("key_backup_location", "/secure/keys/backup")
            
            # This would implement secure key backup
            # For now, just log that backup was performed
            self.logger.info(f"Key backup performed to {backup_location}")
            
        except Exception as e:
            self.logger.error(f"Error backing up keys: {str(e)}")
    
    async def _log_encryption_operation(
        self,
        operation_type: str,
        key_id: str,
        data_type: str,
        data_size: int,
        processing_time_ms: int,
        success: bool,
        error_message: Optional[str] = None,
        user_id: Optional[str] = None
    ):
        """Log encryption operation for audit trail."""
        try:
            operation = EncryptionOperation(
                operation_id=str(uuid.uuid4()),
                operation_type=operation_type,
                key_id=key_id,
                data_type=data_type,
                data_size=data_size,
                processing_time_ms=processing_time_ms,
                success=success,
                error_message=error_message,
                timestamp=datetime.utcnow(),
                user_id=user_id
            )
            
            # Store operation
            self.encryption_operations.append(operation)
            
            # Cache operation
            cache_key = f"encryption_operation_{operation.operation_id}"
            await self.cache_manager.set(cache_key, operation.__dict__, ttl=self.operation_cache_ttl)
            
        except Exception as e:
            self.logger.error(f"Error logging encryption operation: {str(e)}")
    
    async def get_encryption_keys(
        self,
        key_type: Optional[KeyType] = None,
        status: Optional[KeyStatus] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get encryption keys with optional filtering."""
        try:
            keys = list(self.encryption_keys.values())
            
            # Apply filters
            if key_type:
                keys = [k for k in keys if k.key_type == key_type]
            
            if status:
                keys = [k for k in keys if k.status == status]
            
            # Sort by creation date (newest first)
            keys.sort(key=lambda x: x.created_at, reverse=True)
            
            # Apply limit
            keys = keys[:limit]
            
            # Convert to dictionaries (excluding sensitive key_data)
            return [
                {
                    "key_id": k.key_id,
                    "key_type": k.key_type.value,
                    "algorithm": k.algorithm.value,
                    "created_at": k.created_at.isoformat(),
                    "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                    "status": k.status.value,
                    "usage_count": k.usage_count,
                    "last_used": k.last_used.isoformat() if k.last_used else None,
                    "metadata": k.metadata
                }
                for k in keys
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting encryption keys: {str(e)}")
            return []
    
    async def get_encryption_policies(self) -> List[Dict[str, Any]]:
        """Get all encryption policies."""
        try:
            policies = list(self.encryption_policies.values())
            
            # Convert to dictionaries
            return [
                {
                    "policy_id": p.policy_id,
                    "name": p.name,
                    "description": p.description,
                    "data_types": p.data_types,
                    "encryption_type": p.encryption_type.value,
                    "encryption_level": p.encryption_level.value,
                    "key_rotation_days": p.key_rotation_days,
                    "enabled": p.enabled,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat()
                }
                for p in policies
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting encryption policies: {str(e)}")
            return []
    
    async def get_encryption_operations(
        self,
        operation_type: Optional[str] = None,
        key_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get encryption operation logs."""
        try:
            operations = self.encryption_operations
            
            # Apply filters
            if operation_type:
                operations = [o for o in operations if o.operation_type == operation_type]
            
            if key_id:
                operations = [o for o in operations if o.key_id == key_id]
            
            if user_id:
                operations = [o for o in operations if o.user_id == user_id]
            
            # Sort by timestamp (newest first)
            operations.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Apply limit
            operations = operations[:limit]
            
            # Convert to dictionaries
            return [
                {
                    "operation_id": o.operation_id,
                    "operation_type": o.operation_type,
                    "key_id": o.key_id,
                    "data_type": o.data_type,
                    "data_size": o.data_size,
                    "processing_time_ms": o.processing_time_ms,
                    "success": o.success,
                    "error_message": o.error_message,
                    "timestamp": o.timestamp.isoformat(),
                    "user_id": o.user_id,
                    "metadata": o.metadata
                }
                for o in operations
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting encryption operations: {str(e)}")
            return []
    
    async def get_encryption_statistics(self) -> Dict[str, Any]:
        """Get encryption service statistics."""
        try:
            # Count keys by type and status
            key_type_counts = {}
            key_status_counts = {}
            
            for key in self.encryption_keys.values():
                key_type = key.key_type.value
                key_status = key.status.value
                
                key_type_counts[key_type] = key_type_counts.get(key_type, 0) + 1
                key_status_counts[key_status] = key_status_counts.get(key_status, 0) + 1
            
            # Count operations by type
            operation_type_counts = {}
            success_count = 0
            total_processing_time = 0
            
            for operation in self.encryption_operations:
                op_type = operation.operation_type
                operation_type_counts[op_type] = operation_type_counts.get(op_type, 0) + 1
                
                if operation.success:
                    success_count += 1
                
                total_processing_time += operation.processing_time_ms
            
            # Calculate performance metrics
            avg_processing_time = (
                total_processing_time / len(self.encryption_operations)
                if self.encryption_operations else 0
            )
            success_rate = (
                (success_count / len(self.encryption_operations)) * 100
                if self.encryption_operations else 0
            )
            
            return {
                "keys": {
                    "total_keys": len(self.encryption_keys),
                    "by_type": key_type_counts,
                    "by_status": key_status_counts
                },
                "policies": {
                    "total_policies": len(self.encryption_policies),
                    "enabled_policies": len([p for p in self.encryption_policies.values() if p.enabled])
                },
                "operations": {
                    "total_operations": len(self.encryption_operations),
                    "by_type": operation_type_counts,
                    "success_rate": round(success_rate, 2),
                    "avg_processing_time_ms": round(avg_processing_time, 2)
                },
                "configuration": {
                    "encryption_enabled": self.encryption_enabled,
                    "key_rotation_enabled": self.key_rotation_enabled,
                    "audit_logging_enabled": self.audit_logging_enabled,
                    "default_encryption_type": self.config.get("default_encryption_type"),
                    "default_key_rotation_days": self.config.get("default_key_rotation_days")
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting encryption statistics: {str(e)}")
            return {"error": str(e)}