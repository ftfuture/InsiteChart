# 데이터 백업 및 복구 전략

## 1. 개요

### 1.1 백업 및 복구의 중요성

InsiteChart 플랫폼은 금융 데이터, 사용자 정보, 시장 분석 결과 등 중요한 데이터를 처리하므로 데이터 손실 방지와 신속한 복구 능력은 비즈니스 연속성에 필수적입니다. 본 전략은 다양한 장애 시나리오에 대응할 수 있는 포괄적인 백업 및 복구 체계를 제공합니다.

### 1.2 백업 및 복구 목표

1. **데이터 보호**: 모든 중요 데이터의 정기적 백업 보장
2. **RTO(복구 시간 목표)**: 1시간 이내 서비스 복구
3. **RPO(복구 지점 목표)**: 15분 이내 데이터 손실
4. **지역 내 재해**: 단일 데이터센터 장애 대응
5. **지역 간 재해**: 전체 지역 장애 대응
6. **데이터 무결성**: 백업 데이터의 일관성 및 정확성 보장

## 2. 백업 아키텍처

### 2.1 다계층 백업 전략

```python
# backup/backup_manager.py
import asyncio
import subprocess
import os
import gzip
import shutil
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
import json
import hashlib
import boto3
import aiofiles
import asyncpg
import redis.asyncio as redis

class BackupType(Enum):
    """백업 유형"""
    FULL = "full"           # 전체 백업
    INCREMENTAL = "incremental"  # 증분 백업
    DIFFERENTIAL = "differential"  # 차분 백업
    TRANSACTION_LOG = "transaction_log"  # 트랜잭션 로그 백업

class StorageType(Enum):
    """저장소 유형"""
    LOCAL = "local"         # 로컬 저장소
    S3 = "s3"              # AWS S3
    GCS = "gcs"             # Google Cloud Storage
    AZURE = "azure"         # Azure Blob Storage

@dataclass
class BackupConfig:
    """백업 설정"""
    name: str
    backup_type: BackupType
    source_type: str  # postgresql, redis, files
    source_config: Dict[str, Any]
    storage_type: StorageType
    storage_config: Dict[str, Any]
    schedule: str  # cron 표현식
    retention_days: int
    compression: bool = True
    encryption: bool = True
    verification: bool = True

@dataclass
class BackupResult:
    """백업 결과"""
    success: bool
    backup_id: str
    backup_type: BackupType
    start_time: datetime
    end_time: datetime
    size_bytes: int
    file_count: int
    checksum: str
    storage_path: str
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

class BackupManager:
    """백업 관리자"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.backups: Dict[str, BackupConfig] = {}
        self.backup_history: List[BackupResult] = []
        
        # 백업 실행기 등록
        self.backup_executors = {
            'postgresql': PostgreSQLBackupExecutor(),
            'redis': RedisBackupExecutor(),
            'files': FileBackupExecutor()
        }
        
        # 저장소 핸들러 등록
        self.storage_handlers = {
            StorageType.LOCAL: LocalStorageHandler(),
            StorageType.S3: S3StorageHandler(),
            StorageType.GCS: GCSStorageHandler(),
            StorageType.AZURE: AzureStorageHandler()
        }
    
    def register_backup(self, config: BackupConfig):
        """백업 설정 등록"""
        self.backups[config.name] = config
        self.logger.info(f"Registered backup configuration: {config.name}")
    
    async def execute_backup(self, backup_name: str) -> BackupResult:
        """백업 실행"""
        
        if backup_name not in self.backups:
            raise ValueError(f"Backup configuration '{backup_name}' not found")
        
        config = self.backups[backup_name]
        executor = self.backup_executors.get(config.source_type)
        
        if not executor:
            raise ValueError(f"No executor found for source type: {config.source_type}")
        
        storage_handler = self.storage_handlers.get(config.storage_type)
        
        if not storage_handler:
            raise ValueError(f"No storage handler found for storage type: {config.storage_type}")
        
        # 백업 ID 생성
        backup_id = f"{backup_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 백업 실행
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting backup: {backup_id}")
            
            # 1. 데이터 추출
            backup_files = await executor.extract_data(config.source_config, backup_id)
            
            # 2. 압축 (설정된 경우)
            if config.compression:
                backup_files = await self._compress_files(backup_files)
            
            # 3. 암호화 (설정된 경우)
            if config.encryption:
                backup_files = await self._encrypt_files(backup_files)
            
            # 4. 체크섬 계산
            checksum = await self._calculate_checksum(backup_files)
            
            # 5. 저장소 업로드
            storage_path = await storage_handler.upload_files(
                backup_files, 
                config.storage_config, 
                backup_id
            )
            
            # 6. 검증 (설정된 경우)
            if config.verification:
                await self._verify_backup(storage_handler, config.storage_config, storage_path)
            
            end_time = datetime.now()
            
            # 결과 생성
            result = BackupResult(
                success=True,
                backup_id=backup_id,
                backup_type=config.backup_type,
                start_time=start_time,
                end_time=end_time,
                size_bytes=sum(os.path.getsize(f) for f in backup_files),
                file_count=len(backup_files),
                checksum=checksum,
                storage_path=storage_path,
                metadata={
                    'config_name': backup_name,
                    'source_type': config.source_type,
                    'storage_type': config.storage_type.value
                }
            )
            
            # 7. 임시 파일 정리
            await self._cleanup_temp_files(backup_files)
            
            self.logger.info(f"Backup completed successfully: {backup_id}")
            
        except Exception as e:
            end_time = datetime.now()
            
            result = BackupResult(
                success=False,
                backup_id=backup_id,
                backup_type=config.backup_type,
                start_time=start_time,
                end_time=end_time,
                size_bytes=0,
                file_count=0,
                checksum="",
                storage_path="",
                error_message=str(e)
            )
            
            self.logger.error(f"Backup failed: {backup_id} - {str(e)}")
        
        # 백업 이력 기록
        self.backup_history.append(result)
        
        return result
    
    async def _compress_files(self, files: List[str]) -> List[str]:
        """파일 압축"""
        compressed_files = []
        
        for file_path in files:
            compressed_path = f"{file_path}.gz"
            
            async with aiofiles.open(file_path, 'rb') as f_in:
                content = await f_in.read()
                
            compressed_content = gzip.compress(content)
            
            async with aiofiles.open(compressed_path, 'wb') as f_out:
                await f_out.write(compressed_content)
            
            compressed_files.append(compressed_path)
            
            # 원본 파일 삭제
            os.remove(file_path)
        
        return compressed_files
    
    async def _encrypt_files(self, files: List[str]) -> List[str]:
        """파일 암호화"""
        # 실제 구현에서는 AES-256 등 강력한 암호화 사용
        # 여기서는 단순한 XOR 암호화 예시
        encrypted_files = []
        encryption_key = os.environ.get('BACKUP_ENCRYPTION_KEY', 'default_key').encode()
        
        for file_path in files:
            encrypted_path = f"{file_path}.enc"
            
            async with aiofiles.open(file_path, 'rb') as f_in:
                content = await f_in.read()
            
            # 간단한 XOR 암호화 (실제로는 더 안전한 방법 사용)
            encrypted_content = bytes(
                b ^ encryption_key[i % len(encryption_key)] 
                for i, b in enumerate(content)
            )
            
            async with aiofiles.open(encrypted_path, 'wb') as f_out:
                await f_out.write(encrypted_content)
            
            encrypted_files.append(encrypted_path)
            
            # 원본 파일 삭제
            os.remove(file_path)
        
        return encrypted_files
    
    async def _calculate_checksum(self, files: List[str]) -> str:
        """파일 체크섬 계산"""
        sha256_hash = hashlib.sha256()
        
        for file_path in sorted(files):
            async with aiofiles.open(file_path, 'rb') as f:
                while chunk := await f.read(8192):
                    sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    async def _verify_backup(self, storage_handler, storage_config: Dict, storage_path: str):
        """백업 검증"""
        try:
            # 저장소에서 파일 다운로드
            downloaded_files = await storage_handler.download_files(storage_config, storage_path)
            
            # 체크섬 재계산 및 비교
            calculated_checksum = await self._calculate_checksum(downloaded_files)
            
            # 원본 체크섬과 비교 (실제 구현에서는 메타데이터에서 가져옴)
            # 여기서는 단순히 파일 존재 확인만 수행
            if downloaded_files:
                self.logger.info("Backup verification successful")
            else:
                raise ValueError("No files found for verification")
            
            # 다운로드한 파일 정리
            for file_path in downloaded_files:
                os.remove(file_path)
                
        except Exception as e:
            raise ValueError(f"Backup verification failed: {str(e)}")
    
    async def _cleanup_temp_files(self, files: List[str]):
        """임시 파일 정리"""
        for file_path in files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                self.logger.warning(f"Failed to cleanup temp file {file_path}: {str(e)}")
    
    async def schedule_backups(self):
        """예약 백업 실행"""
        import croniter
        
        while True:
            current_time = datetime.now()
            
            for backup_name, config in self.backups.items():
                try:
                    # 다음 실행 시간 계산
                    cron = croniter.croniter(config.schedule, current_time)
                    next_run = cron.get_next(datetime)
                    
                    # 실행 시간이 되면 백업 실행
                    if current_time >= next_run:
                        self.logger.info(f"Scheduled backup triggered: {backup_name}")
                        await self.execute_backup(backup_name)
                
                except Exception as e:
                    self.logger.error(f"Error in scheduled backup {backup_name}: {str(e)}")
            
            # 1분 대기
            await asyncio.sleep(60)
    
    def get_backup_history(self, backup_name: Optional[str] = None) -> List[BackupResult]:
        """백업 이력 조회"""
        history = self.backup_history
        
        if backup_name:
            history = [
                backup for backup in history 
                if backup.metadata and backup.metadata.get('config_name') == backup_name
            ]
        
        return sorted(history, key=lambda x: x.start_time, reverse=True)
    
    async def cleanup_old_backups(self):
        """오래된 백업 정리"""
        current_time = datetime.now()
        
        for backup_name, config in self.backups.items():
            cutoff_date = current_time - timedelta(days=config.retention_days)
            storage_handler = self.storage_handlers.get(config.storage_type)
            
            if not storage_handler:
                continue
            
            try:
                # 저장소에서 오래된 백업 목록 조회
                old_backups = await storage_handler.list_old_backups(
                    config.storage_config, 
                    backup_name, 
                    cutoff_date
                )
                
                # 오래된 백업 삭제
                for backup_path in old_backups:
                    await storage_handler.delete_backup(config.storage_config, backup_path)
                    self.logger.info(f"Deleted old backup: {backup_path}")
                
            except Exception as e:
                self.logger.error(f"Error cleaning up old backups for {backup_name}: {str(e)}")

class PostgreSQLBackupExecutor:
    """PostgreSQL 백업 실행기"""
    
    async def extract_data(self, config: Dict[str, Any], backup_id: str) -> List[str]:
        """PostgreSQL 데이터 추출"""
        
        host = config.get('host', 'localhost')
        port = config.get('port', 5432)
        database = config.get('database')
        username = config.get('username')
        password = config.get('password')
        
        # 백업 파일 경로
        backup_dir = f"/tmp/backup_{backup_id}"
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = f"{backup_dir}/postgresql_{backup_id}.sql"
        
        # pg_dump 명령어 구성
        cmd = [
            'pg_dump',
            f'--host={host}',
            f'--port={port}',
            f'--username={username}',
            f'--dbname={database}',
            '--format=custom',
            '--compress=9',
            '--verbose',
            f'--file={backup_file}'
        ]
        
        # 환경변수 설정
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        # 백업 실행
        process = await asyncio.create_subprocess_exec(
            *cmd,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"PostgreSQL backup failed: {stderr.decode()}")
        
        return [backup_file]

class RedisBackupExecutor:
    """Redis 백업 실행기"""
    
    async def extract_data(self, config: Dict[str, Any], backup_id: str) -> List[str]:
        """Redis 데이터 추출"""
        
        host = config.get('host', 'localhost')
        port = config.get('port', 6379)
        password = config.get('password')
        database = config.get('database', 0)
        
        # 백업 파일 경로
        backup_dir = f"/tmp/backup_{backup_id}"
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = f"{backup_dir}/redis_{backup_id}.rdb"
        
        # Redis 연결
        redis_client = redis.from_url(
            f"redis://:{password}@{host}:{port}/{database}"
        )
        
        try:
            # BGSAVE 명령 실행
            await redis_client.bgsave()
            
            # 백업 완료 대기
            last_save = await redis_client.lastsave()
            
            # 최신 백업 파일 찾기
            max_wait = 60  # 최대 60초 대기
            wait_time = 0
            
            while wait_time < max_wait:
                current_save = await redis_client.lastsave()
                if current_save > last_save:
                    break
                
                await asyncio.sleep(1)
                wait_time += 1
            
            # RDB 파일 복사
            rdb_path = config.get('rdb_path', '/var/lib/redis/dump.rdb')
            shutil.copy2(rdb_path, backup_file)
            
        finally:
            await redis_client.close()
        
        return [backup_file]

class FileBackupExecutor:
    """파일 백업 실행기"""
    
    async def extract_data(self, config: Dict[str, Any], backup_id: str) -> List[str]:
        """파일 데이터 추출"""
        
        source_paths = config.get('paths', [])
        backup_dir = f"/tmp/backup_{backup_id}"
        os.makedirs(backup_dir, exist_ok=True)
        
        backup_files = []
        
        for source_path in source_paths:
            if os.path.isfile(source_path):
                # 단일 파일 백업
                filename = os.path.basename(source_path)
                backup_file = f"{backup_dir}/{filename}"
                shutil.copy2(source_path, backup_file)
                backup_files.append(backup_file)
                
            elif os.path.isdir(source_path):
                # 디렉토리 백업
                dirname = os.path.basename(source_path.rstrip('/'))
                backup_subdir = f"{backup_dir}/{dirname}"
                shutil.copytree(source_path, backup_subdir)
                
                # 백업된 파일 목록 추가
                for root, dirs, files in os.walk(backup_subdir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        backup_files.append(file_path)
        
        return backup_files

class LocalStorageHandler:
    """로컬 저장소 핸들러"""
    
    async def upload_files(self, files: List[str], config: Dict[str, Any], backup_id: str) -> str:
        """파일 업로드"""
        
        base_path = config.get('base_path', '/var/backups')
        backup_path = f"{base_path}/{backup_id}"
        
        os.makedirs(backup_path, exist_ok=True)
        
        for file_path in files:
            filename = os.path.basename(file_path)
            dest_path = f"{backup_path}/{filename}"
            shutil.move(file_path, dest_path)
        
        return backup_path
    
    async def download_files(self, config: Dict[str, Any], backup_path: str) -> List[str]:
        """파일 다운로드"""
        
        if os.path.isdir(backup_path):
            return [
                os.path.join(root, file)
                for root, dirs, files in os.walk(backup_path)
                for file in files
            ]
        elif os.path.isfile(backup_path):
            return [backup_path]
        else:
            return []
    
    async def list_old_backups(self, config: Dict[str, Any], backup_name: str, cutoff_date: datetime) -> List[str]:
        """오래된 백업 목록 조회"""
        
        base_path = config.get('base_path', '/var/backups')
        old_backups = []
        
        if os.path.exists(base_path):
            for item in os.listdir(base_path):
                if item.startswith(f"{backup_name}_"):
                    item_path = os.path.join(base_path, item)
                    item_time = datetime.fromtimestamp(os.path.getmtime(item_path))
                    
                    if item_time < cutoff_date:
                        old_backups.append(item_path)
        
        return old_backups
    
    async def delete_backup(self, config: Dict[str, Any], backup_path: str):
        """백업 삭제"""
        
        if os.path.isdir(backup_path):
            shutil.rmtree(backup_path)
        elif os.path.isfile(backup_path):
            os.remove(backup_path)

class S3StorageHandler:
    """AWS S3 저장소 핸들러"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
    
    async def upload_files(self, files: List[str], config: Dict[str, Any], backup_id: str) -> str:
        """파일 업로드"""
        
        bucket_name = config.get('bucket_name')
        prefix = config.get('prefix', 'backups')
        base_path = f"{prefix}/{backup_id}"
        
        for file_path in files:
            filename = os.path.basename(file_path)
            key = f"{base_path}/{filename}"
            
            self.s3_client.upload_file(file_path, bucket_name, key)
        
        return f"s3://{bucket_name}/{base_path}"
    
    async def download_files(self, config: Dict[str, Any], storage_path: str) -> List[str]:
        """파일 다운로드"""
        
        # S3 경로 파싱
        if storage_path.startswith('s3://'):
            storage_path = storage_path[5:]  # 's3://' 제거
        
        bucket_name, key = storage_path.split('/', 1)
        download_dir = f"/tmp/download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(download_dir, exist_ok=True)
        
        downloaded_files = []
        
        # 객체 목록 조회
        response = self.s3_client.list_objects_v2(Bucket=bucket_name, Prefix=key)
        
        for obj in response.get('Contents', []):
            obj_key = obj['Key']
            filename = os.path.basename(obj_key)
            download_path = f"{download_dir}/{filename}"
            
            self.s3_client.download_file(bucket_name, obj_key, download_path)
            downloaded_files.append(download_path)
        
        return downloaded_files
    
    async def list_old_backups(self, config: Dict[str, Any], backup_name: str, cutoff_date: datetime) -> List[str]:
        """오래된 백업 목록 조회"""
        
        bucket_name = config.get('bucket_name')
        prefix = config.get('prefix', 'backups')
        
        old_backups = []
        
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
            for obj in page.get('Contents', []):
                key = obj['Key']
                last_modified = obj['LastModified']
                
                if (backup_name in key and 
                    last_modified.replace(tzinfo=None) < cutoff_date):
                    old_backups.append(f"s3://{bucket_name}/{key}")
        
        return old_backups
    
    async def delete_backup(self, config: Dict[str, Any], backup_path: str):
        """백업 삭제"""
        
        # S3 경로 파싱
        if storage_path.startswith('s3://'):
            storage_path = storage_path[5:]  # 's3://' 제거
        
        bucket_name, key = storage_path.split('/', 1)
        
        # 객체 삭제
        self.s3_client.delete_object(Bucket=bucket_name, Key=key)

class GCSStorageHandler:
    """Google Cloud Storage 저장소 핸들러"""
    
    def __init__(self):
        # GCS 클라이언트 초기화
        pass
    
    async def upload_files(self, files: List[str], config: Dict[str, Any], backup_id: str) -> str:
        """파일 업로드"""
        # GCS 업로드 구현
        pass
    
    async def download_files(self, config: Dict[str, Any], storage_path: str) -> List[str]:
        """파일 다운로드"""
        # GCS 다운로드 구현
        pass
    
    async def list_old_backups(self, config: Dict[str, Any], backup_name: str, cutoff_date: datetime) -> List[str]:
        """오래된 백업 목록 조회"""
        # GCS 목록 조회 구현
        pass
    
    async def delete_backup(self, config: Dict[str, Any], backup_path: str):
        """백업 삭제"""
        # GCS 삭제 구현
        pass

class AzureStorageHandler:
    """Azure Blob Storage 저장소 핸들러"""
    
    def __init__(self):
        # Azure 클라이언트 초기화
        pass
    
    async def upload_files(self, files: List[str], config: Dict[str, Any], backup_id: str) -> str:
        """파일 업로드"""
        # Azure 업로드 구현
        pass
    
    async def download_files(self, config: Dict[str, Any], storage_path: str) -> List[str]:
        """파일 다운로드"""
        # Azure 다운로드 구현
        pass
    
    async def list_old_backups(self, config: Dict[str, Any], backup_name: str, cutoff_date: datetime) -> List[str]:
        """오래된 백업 목록 조회"""
        # Azure 목록 조회 구현
        pass
    
    async def delete_backup(self, config: Dict[str, Any], backup_path: str):
        """백업 삭제"""
        # Azure 삭제 구현
        pass
```

### 2.2 자동화된 백업 스케줄링

```python
# backup/scheduler.py
import asyncio
import croniter
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
from .backup_manager import BackupManager, BackupConfig, BackupResult

@dataclass
class ScheduledBackup:
    """예약 백업"""
    backup_name: str
    schedule: str  # cron 표현식
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    max_retries: int = 3
    retry_delay: int = 300  # 5분

class BackupScheduler:
    """백업 스케줄러"""
    
    def __init__(self, backup_manager: BackupManager):
        self.backup_manager = backup_manager
        self.logger = logging.getLogger(__name__)
        self.scheduled_backups: Dict[str, ScheduledBackup] = {}
        self.running = False
    
    def schedule_backup(self, backup_name: str, schedule: str, enabled: bool = True):
        """백업 예약"""
        
        if backup_name not in self.backup_manager.backups:
            raise ValueError(f"Backup configuration '{backup_name}' not found")
        
        # 다음 실행 시간 계산
        cron = croniter.croniter(schedule, datetime.now())
        next_run = cron.get_next(datetime)
        
        scheduled_backup = ScheduledBackup(
            backup_name=backup_name,
            schedule=schedule,
            enabled=enabled,
            next_run=next_run
        )
        
        self.scheduled_backups[backup_name] = scheduled_backup
        
        self.logger.info(f"Scheduled backup '{backup_name}' with schedule '{schedule}'")
    
    def unschedule_backup(self, backup_name: str):
        """백업 예약 취소"""
        
        if backup_name in self.scheduled_backups:
            del self.scheduled_backups[backup_name]
            self.logger.info(f"Unscheduled backup: {backup_name}")
    
    async def start(self):
        """스케줄러 시작"""
        
        self.running = True
        self.logger.info("Backup scheduler started")
        
        while self.running:
            try:
                await self._check_and_run_backups()
                await asyncio.sleep(60)  # 1분마다 확인
            except Exception as e:
                self.logger.error(f"Error in backup scheduler: {str(e)}")
                await asyncio.sleep(60)
    
    def stop(self):
        """스케줄러 중지"""
        self.running = False
        self.logger.info("Backup scheduler stopped")
    
    async def _check_and_run_backups(self):
        """예약된 백업 확인 및 실행"""
        
        current_time = datetime.now()
        
        for backup_name, scheduled_backup in self.scheduled_backups.items():
            if not scheduled_backup.enabled:
                continue
            
            # 실행 시간 확인
            if current_time >= scheduled_backup.next_run:
                await self._run_scheduled_backup(scheduled_backup)
    
    async def _run_scheduled_backup(self, scheduled_backup: ScheduledBackup):
        """예약된 백업 실행"""
        
        backup_name = scheduled_backup.backup_name
        retry_count = 0
        
        while retry_count <= scheduled_backup.max_retries:
            try:
                self.logger.info(f"Running scheduled backup: {backup_name}")
                
                # 백업 실행
                result = await self.backup_manager.execute_backup(backup_name)
                
                if result.success:
                    # 성공 시 다음 실행 시간 계산
                    cron = croniter.croniter(scheduled_backup.schedule, datetime.now())
                    scheduled_backup.next_run = cron.get_next(datetime)
                    scheduled_backup.last_run = datetime.now()
                    
                    self.logger.info(f"Scheduled backup completed: {backup_name}")
                    break
                else:
                    # 실패 시 재시도
                    retry_count += 1
                    if retry_count <= scheduled_backup.max_retries:
                        self.logger.warning(
                            f"Scheduled backup failed, retrying ({retry_count}/{scheduled_backup.max_retries}): {backup_name}"
                        )
                        await asyncio.sleep(scheduled_backup.retry_delay)
                    else:
                        self.logger.error(
                            f"Scheduled backup failed after {scheduled_backup.max_retries} retries: {backup_name}"
                        )
                        # 다음 실행 시간 계산 (실패해도 계속 진행)
                        cron = croniter.croniter(scheduled_backup.schedule, datetime.now())
                        scheduled_backup.next_run = cron.get_next(datetime)
            
            except Exception as e:
                retry_count += 1
                self.logger.error(f"Error running scheduled backup {backup_name}: {str(e)}")
                
                if retry_count <= scheduled_backup.max_retries:
                    await asyncio.sleep(scheduled_backup.retry_delay)
                else:
                    # 다음 실행 시간 계산
                    cron = croniter.croniter(scheduled_backup.schedule, datetime.now())
                    scheduled_backup.next_run = cron.get_next(datetime)
    
    def get_schedule_status(self) -> Dict[str, Dict]:
        """스케줄 상태 조회"""
        
        status = {}
        
        for backup_name, scheduled_backup in self.scheduled_backups.items():
            status[backup_name] = {
                'schedule': scheduled_backup.schedule,
                'enabled': scheduled_backup.enabled,
                'last_run': scheduled_backup.last_run.isoformat() if scheduled_backup.last_run else None,
                'next_run': scheduled_backup.next_run.isoformat() if scheduled_backup.next_run else None,
                'max_retries': scheduled_backup.max_retries,
                'retry_delay': scheduled_backup.retry_delay
            }
        
        return status
```

## 3. 복구 전략

### 3.1 복구 관리자

```python
# recovery/recovery_manager.py
import asyncio
import os
import tempfile
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
import json
import asyncpg
import redis.asyncio as redis

class RecoveryType(Enum):
    """복구 유형"""
    FULL = "full"           # 전체 복구
    POINT_IN_TIME = "point_in_time"  # 특정 시점 복구
    PARTIAL = "partial"     # 부분 복구
    ROLLING = "rolling"     # 롤링 복구

class RecoveryStatus(Enum):
    """복구 상태"""
    PENDING = "pending"     # 대기 중
    IN_PROGRESS = "in_progress"  # 진행 중
    COMPLETED = "completed"  # 완료
    FAILED = "failed"       # 실패
    CANCELLED = "cancelled"  # 취소됨

@dataclass
class RecoveryPlan:
    """복구 계획"""
    recovery_id: str
    recovery_type: RecoveryType
    backup_id: str
    target_time: Optional[datetime]
    target_components: List[str]  # 복구할 구성 요소
    priority: int  # 우선순위
    estimated_duration: timedelta
    status: RecoveryStatus = RecoveryStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    progress: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class RecoveryResult:
    """복구 결과"""
    success: bool
    recovery_id: str
    recovery_type: RecoveryType
    start_time: datetime
    end_time: datetime
    recovered_components: List[str]
    failed_components: List[str]
    data_loss_estimate: timedelta  # 예상 데이터 손실
    verification_results: Dict[str, bool]
    error_message: Optional[str] = None

class RecoveryManager:
    """복구 관리자"""
    
    def __init__(self, backup_manager):
        self.backup_manager = backup_manager
        self.logger = logging.getLogger(__name__)
        self.recovery_plans: Dict[str, RecoveryPlan] = {}
        self.recovery_history: List[RecoveryResult] = []
        
        # 복구 실행기 등록
        self.recovery_executors = {
            'postgresql': PostgreSQLRecoveryExecutor(),
            'redis': RedisRecoveryExecutor(),
            'files': FileRecoveryExecutor()
        }
    
    async def create_recovery_plan(self,
                               recovery_type: RecoveryType,
                               backup_id: str,
                               target_time: Optional[datetime] = None,
                               target_components: Optional[List[str]] = None,
                               priority: int = 0) -> str:
        """복구 계획 생성"""
        
        # 백업 정보 조회
        backup_result = self._find_backup_result(backup_id)
        if not backup_result:
            raise ValueError(f"Backup not found: {backup_id}")
        
        # 복구 계획 생성
        recovery_id = f"recovery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 대상 구성 요소 결정
        if not target_components:
            target_components = self._determine_components(backup_result)
        
        # 예상 복구 시간 계산
        estimated_duration = self._estimate_recovery_duration(recovery_type, target_components)
        
        recovery_plan = RecoveryPlan(
            recovery_id=recovery_id,
            recovery_type=recovery_type,
            backup_id=backup_id,
            target_time=target_time,
            target_components=target_components,
            priority=priority,
            estimated_duration=estimated_duration,
            metadata={
                'backup_type': backup_result.backup_type.value,
                'backup_size': backup_result.size_bytes,
                'backup_time': backup_result.start_time.isoformat()
            }
        )
        
        self.recovery_plans[recovery_id] = recovery_plan
        
        self.logger.info(f"Created recovery plan: {recovery_id}")
        
        return recovery_id
    
    async def execute_recovery(self, recovery_id: str) -> RecoveryResult:
        """복구 실행"""
        
        if recovery_id not in self.recovery_plans:
            raise ValueError(f"Recovery plan not found: {recovery_id}")
        
        plan = self.recovery_plans[recovery_id]
        
        # 상태 업데이트
        plan.status = RecoveryStatus.IN_PROGRESS
        plan.start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting recovery: {recovery_id}")
            
            # 백업 정보 조회
            backup_result = self._find_backup_result(plan.backup_id)
            
            # 복구 실행
            recovered_components = []
            failed_components = []
            verification_results = {}
            
            total_components = len(plan.target_components)
            
            for i, component in enumerate(plan.target_components):
                try:
                    # 진행률 업데이트
                    plan.progress = (i / total_components) * 100
                    
                    # 구성 요소 복구
                    success = await self._recover_component(
                        component, 
                        backup_result, 
                        plan.recovery_type, 
                        plan.target_time
                    )
                    
                    if success:
                        recovered_components.append(component)
                        verification_results[component] = True
                    else:
                        failed_components.append(component)
                        verification_results[component] = False
                
                except Exception as e:
                    self.logger.error(f"Failed to recover component {component}: {str(e)}")
                    failed_components.append(component)
                    verification_results[component] = False
            
            # 진행률 완료
            plan.progress = 100.0
            
            # 데이터 손실 추정
            data_loss_estimate = self._estimate_data_loss(plan, backup_result)
            
            # 결과 생성
            end_time = datetime.now()
            
            result = RecoveryResult(
                success=len(failed_components) == 0,
                recovery_id=recovery_id,
                recovery_type=plan.recovery_type,
                start_time=plan.start_time,
                end_time=end_time,
                recovered_components=recovered_components,
                failed_components=failed_components,
                data_loss_estimate=data_loss_estimate,
                verification_results=verification_results
            )
            
            # 상태 업데이트
            if result.success:
                plan.status = RecoveryStatus.COMPLETED
            else:
                plan.status = RecoveryStatus.FAILED
                plan.error_message = f"Failed to recover {len(failed_components)} components"
            
            plan.end_time = end_time
            
            self.logger.info(f"Recovery completed: {recovery_id} - Success: {result.success}")
            
        except Exception as e:
            plan.status = RecoveryStatus.FAILED
            plan.error_message = str(e)
            plan.end_time = datetime.now()
            
            result = RecoveryResult(
                success=False,
                recovery_id=recovery_id,
                recovery_type=plan.recovery_type,
                start_time=plan.start_time,
                end_time=plan.end_time,
                recovered_components=[],
                failed_components=plan.target_components,
                data_loss_estimate=timedelta.max,
                verification_results={},
                error_message=str(e)
            )
            
            self.logger.error(f"Recovery failed: {recovery_id} - {str(e)}")
        
        # 복구 이력 기록
        self.recovery_history.append(result)
        
        return result
    
    async def _recover_component(self, 
                             component: str, 
                             backup_result: Any, 
                             recovery_type: RecoveryType, 
                             target_time: Optional[datetime]) -> bool:
        """개별 구성 요소 복구"""
        
        # 구성 요소 타입 결정
        component_type = self._determine_component_type(component)
        
        # 복구 실행기 가져오기
        executor = self.recovery_executors.get(component_type)
        
        if not executor:
            self.logger.error(f"No recovery executor found for component type: {component_type}")
            return False
        
        try:
            # 복구 실행
            success = await executor.recover(
                component=component,
                backup_result=backup_result,
                recovery_type=recovery_type,
                target_time=target_time
            )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error recovering component {component}: {str(e)}")
            return False
    
    def _find_backup_result(self, backup_id: str) -> Optional[Any]:
        """백업 결과 찾기"""
        
        for backup in self.backup_manager.backup_history:
            if backup.backup_id == backup_id:
                return backup
        
        return None
    
    def _determine_components(self, backup_result: Any) -> List[str]:
        """복구할 구성 요소 결정"""
        
        # 백업 메타데이터에서 구성 요소 추출
        if backup_result.metadata:
            source_type = backup_result.metadata.get('source_type')
            
            if source_type == 'postgresql':
                return ['postgresql_database']
            elif source_type == 'redis':
                return ['redis_cache']
            elif source_type == 'files':
                return ['application_files']
        
        # 기본 구성 요소
        return ['postgresql_database', 'redis_cache', 'application_files']
    
    def _determine_component_type(self, component: str) -> str:
        """구성 요소 타입 결정"""
        
        if 'postgresql' in component or 'database' in component:
            return 'postgresql'
        elif 'redis' in component or 'cache' in component:
            return 'redis'
        elif 'file' in component:
            return 'files'
        
        return 'unknown'
    
    def _estimate_recovery_duration(self, recovery_type: RecoveryType, components: List[str]) -> timedelta:
        """복구 시간 예측"""
        
        # 구성 요소별 예상 복구 시간 (분)
        component_durations = {
            'postgresql_database': 30,
            'redis_cache': 5,
            'application_files': 10
        }
        
        # 복구 유형별 계수
        type_multipliers = {
            RecoveryType.FULL: 1.0,
            RecoveryType.POINT_IN_TIME: 1.5,
            RecoveryType.PARTIAL: 0.7,
            RecoveryType.ROLLING: 0.8
        }
        
        total_minutes = sum(
            component_durations.get(comp, 15) 
            for comp in components
        )
        
        multiplier = type_multipliers.get(recovery_type, 1.0)
        
        return timedelta(minutes=int(total_minutes * multiplier))
    
    def _estimate_data_loss(self, plan: RecoveryPlan, backup_result: Any) -> timedelta:
        """데이터 손실 추정"""
        
        if plan.recovery_type == RecoveryType.POINT_IN_TIME and plan.target_time:
            # 특정 시점 복구의 경우
            backup_time = backup_result.start_time
            if plan.target_time > backup_time:
                return plan.target_time - backup_time
        
        # 전체 복구의 경우 백업 시간 이후의 데이터 손실
        current_time = datetime.now()
        backup_time = backup_result.start_time
        
        # 최근 백업인 경우 손실 적음
        if current_time - backup_time < timedelta(hours=1):
            return timedelta(minutes=15)
        elif current_time - backup_time < timedelta(days=1):
            return timedelta(hours=1)
        else:
            return timedelta(days=1)
    
    async def cancel_recovery(self, recovery_id: str) -> bool:
        """복구 취소"""
        
        if recovery_id not in self.recovery_plans:
            return False
        
        plan = self.recovery_plans[recovery_id]
        
        if plan.status in [RecoveryStatus.COMPLETED, RecoveryStatus.FAILED, RecoveryStatus.CANCELLED]:
            return False
        
        plan.status = RecoveryStatus.CANCELLED
        plan.end_time = datetime.now()
        
        self.logger.info(f"Cancelled recovery: {recovery_id}")
        
        return True
    
    def get_recovery_plan(self, recovery_id: str) -> Optional[RecoveryPlan]:
        """복구 계획 조회"""
        return self.recovery_plans.get(recovery_id)
    
    def list_recovery_plans(self, status: Optional[RecoveryStatus] = None) -> List[RecoveryPlan]:
        """복구 계획 목록 조회"""
        
        plans = list(self.recovery_plans.values())
        
        if status:
            plans = [p for p in plans if p.status == status]
        
        return sorted(plans, key=lambda x: x.priority, reverse=True)
    
    def get_recovery_history(self, limit: int = 100) -> List[RecoveryResult]:
        """복구 이력 조회"""
        
        history = sorted(self.recovery_history, key=lambda x: x.start_time, reverse=True)
        return history[:limit]

class PostgreSQLRecoveryExecutor:
    """PostgreSQL 복구 실행기"""
    
    async def recover(self, 
                   component: str, 
                   backup_result: Any, 
                   recovery_type: RecoveryType, 
                   target_time: Optional[datetime]) -> bool:
        """PostgreSQL 복구"""
        
        try:
            # 백업 파일 다운로드
            backup_files = await self._download_backup(backup_result)
            
            if not backup_files:
                raise ValueError("No backup files found")
            
            # 복구 방법 결정
            if recovery_type == RecoveryType.POINT_IN_TIME and target_time:
                success = await self._point_in_time_recovery(backup_files, target_time)
            else:
                success = await self._full_recovery(backup_files)
            
            # 임시 파일 정리
            for file_path in backup_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            return success
            
        except Exception as e:
            logging.getLogger(__name__).error(f"PostgreSQL recovery failed: {str(e)}")
            return False
    
    async def _download_backup(self, backup_result: Any) -> List[str]:
        """백업 파일 다운로드"""
        
        # 백업 저장소 핸들러 가져오기
        storage_handler = None
        for handler in backup_result.backup_manager.storage_handlers.values():
            if hasattr(handler, 'download_files'):
                storage_handler = handler
                break
        
        if not storage_handler:
            raise ValueError("No storage handler available")
        
        # 저장소 설정 (실제로는 백업 결과에서 가져옴)
        storage_config = {}
        
        # 파일 다운로드
        files = await storage_handler.download_files(storage_config, backup_result.storage_path)
        
        return files
    
    async def _full_recovery(self, backup_files: List[str]) -> bool:
        """전체 복구"""
        
        # 백업 파일 찾기
        backup_file = None
        for file_path in backup_files:
            if file_path.endswith('.sql') or file_path.endswith('.dump'):
                backup_file = file_path
                break
        
        if not backup_file:
            raise ValueError("No valid backup file found")
        
        # 데이터베이스 복원 명령어
        cmd = [
            'pg_restore',
            '--host=localhost',
            '--port=5432',
            '--username=postgres',
            '--dbname=insitechart',
            '--clean',
            '--if-exists',
            '--verbose',
            backup_file
        ]
        
        # 복원 실행
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"PostgreSQL restore failed: {stderr.decode()}")
        
        return True
    
    async def _point_in_time_recovery(self, backup_files: List[str], target_time: datetime) -> bool:
        """특정 시점 복구"""
        
        # 실제 구현에서는 WAL 파일과 함께 복구
        # 여기서는 단순한 전체 복구로 대체
        return await self._full_recovery(backup_files)

class RedisRecoveryExecutor:
    """Redis 복구 실행기"""
    
    async def recover(self, 
                   component: str, 
                   backup_result: Any, 
                   recovery_type: RecoveryType, 
                   target_time: Optional[datetime]) -> bool:
        """Redis 복구"""
        
        try:
            # 백업 파일 다운로드
            backup_files = await self._download_backup(backup_result)
            
            if not backup_files:
                raise ValueError("No backup files found")
            
            # RDB 파일 찾기
            rdb_file = None
            for file_path in backup_files:
                if file_path.endswith('.rdb'):
                    rdb_file = file_path
                    break
            
            if not rdb_file:
                raise ValueError("No RDB backup file found")
            
            # Redis 복구
            success = await self._restore_redis(rdb_file)
            
            # 임시 파일 정리
            for file_path in backup_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            return success
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Redis recovery failed: {str(e)}")
            return False
    
    async def _download_backup(self, backup_result: Any) -> List[str]:
        """백업 파일 다운로드"""
        # PostgreSQLRecoveryExecutor와 유사한 구현
        pass
    
    async def _restore_redis(self, rdb_file: str) -> bool:
        """Redis 복구"""
        
        # Redis 중지
        stop_cmd = ['systemctl', 'stop', 'redis']
        await asyncio.create_subprocess_exec(*stop_cmd)
        
        # RDB 파일 복사
        rdb_path = '/var/lib/redis/dump.rdb'
        shutil.copy2(rdb_file, rdb_path)
        
        # Redis 시작
        start_cmd = ['systemctl', 'start', 'redis']
        process = await asyncio.create_subprocess_exec(*start_cmd)
        await process.communicate()
        
        return True

class FileRecoveryExecutor:
    """파일 복구 실행기"""
    
    async def recover(self, 
                   component: str, 
                   backup_result: Any, 
                   recovery_type: RecoveryType, 
                   target_time: Optional[datetime]) -> bool:
        """파일 복구"""
        
        try:
            # 백업 파일 다운로드
            backup_files = await self._download_backup(backup_result)
            
            if not backup_files:
                raise ValueError("No backup files found")
            
            # 파일 복구
            success = await self._restore_files(backup_files)
            
            # 임시 파일 정리
            for file_path in backup_files:
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            return success
            
        except Exception as e:
            logging.getLogger(__name__).error(f"File recovery failed: {str(e)}")
            return False
    
    async def _download_backup(self, backup_result: Any) -> List[str]:
        """백업 파일 다운로드"""
        # PostgreSQLRecoveryExecutor와 유사한 구현
        pass
    
    async def _restore_files(self, backup_files: List[str]) -> bool:
        """파일 복구"""
        
        # 대상 디렉토리 결정
        target_dirs = {
            'app': '/opt/insitechart/app',
            'config': '/opt/insitechart/config',
            'logs': '/opt/insitechart/logs',
            'static': '/opt/insitechart/static'
        }
        
        for file_path in backup_files:
            # 파일 경로 분석
            filename = os.path.basename(file_path)
            
            # 대상 디렉토리 결정
            target_dir = None
            for dir_name, dir_path in target_dirs.items():
                if dir_name in filename.lower():
                    target_dir = dir_path
                    break
            
            if not target_dir:
                # 기본 디렉토리
                target_dir = '/opt/insitechart'
            
            # 파일 복사
            target_path = os.path.join(target_dir, filename)
            shutil.copy2(file_path, target_path)
        
        return True
```

## 4. 재해 복구 계획

### 4.1 재난 복구 절차

```python
# disaster_recovery/dr_planner.py
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging
import json

class DisasterType(Enum):
    """재난 유형"""
    HARDWARE_FAILURE = "hardware_failure"      # 하드웨어 장애
    NETWORK_OUTAGE = "network_outage"          # 네트워크 장애
    DATA_CORRUPTION = "data_corruption"        # 데이터 손상
    SECURITY_BREACH = "security_breach"        # 보안 침해
    NATURAL_DISASTER = "natural_disaster"      # 자연재해
    HUMAN_ERROR = "human_error"                # 인적 오류

class RecoveryTier(Enum):
    """복구 등급"""
    TIER_1 = "tier_1"  # 0-4시간 (비즈니스 크리티컬)
    TIER_2 = "tier_2"  # 4-24시간 (중요)
    TIER_3 = "tier_3"  # 24-72시간 (일반)
    TIER_4 = "tier_4"  # 72시간 이상 (낮은 우선순위)

@dataclass
class DisasterScenario:
    """재난 시나리오"""
    name: str
    disaster_type: DisasterType
    description: str
    probability: float  # 발생 확률 (0-1)
    impact_assessment: Dict[str, Any]
    recovery_tier: RecoveryTier
    estimated_downtime: timedelta
    estimated_cost: float
    recovery_steps: List[str]
    required_resources: List[str]
    communication_plan: Dict[str, Any]

@dataclass
class RecoveryPlan:
    """복구 계획"""
    scenario_name: str
    recovery_team: List[str]  # 복구팀 구성원
    communication_channels: List[str]  # 의사소통 채널
    escalation_procedures: List[Dict[str, Any]]  # 상향 절차
    recovery_steps: List[Dict[str, Any]]  # 복구 단계
    verification_procedures: List[str]  # 검증 절차
    rollback_procedures: List[str]  # 롤백 절차
    post_recovery_actions: List[str]  # 복구 후 조치

class DisasterRecoveryPlanner:
    """재난 복구 계획자"""
    
    def __init__(self, recovery_manager):
        self.recovery_manager = recovery_manager
        self.logger = logging.getLogger(__name__)
        
        # 재난 시나리오
        self.scenarios: Dict[str, DisasterScenario] = {}
        
        # 복구 계획
        self.recovery_plans: Dict[str, RecoveryPlan] = {}
        
        # 초기 시나리오 및 계획 로드
        self._load_default_scenarios()
        self._load_default_recovery_plans()
    
    def _load_default_scenarios(self):
        """기본 재난 시나리오 로드"""
        
        # 데이터베이스 장애 시나리오
        database_failure = DisasterScenario(
            name="database_failure",
            disaster_type=DisasterType.HARDWARE_FAILURE,
            description="Primary database server failure",
            probability=0.15,
            impact_assessment={
                "service_impact": "high",
                "data_loss_potential": "medium",
                "user_impact": "high",
                "financial_impact": "high"
            },
            recovery_tier=RecoveryTier.TIER_1,
            estimated_downtime=timedelta(hours=2),
            estimated_cost=50000,
            recovery_steps=[
                "Detect failure through monitoring alerts",
                "Activate standby database",
                "Verify data integrity",
                "Update DNS records",
                "Test application connectivity"
            ],
            required_resources=[
                "standby_database_server",
                "database_administrator",
                "network_engineer"
            ],
            communication_plan={
                "internal": "incident_response_channel",
                "external": "status_page_update",
                "stakeholders": "email_notification"
            }
        )
        
        # 데이터센터 장애 시나리오
        datacenter_failure = DisasterScenario(
            name="datacenter_failure",
            disaster_type=DisasterType.NATURAL_DISASTER,
            description="Complete datacenter outage",
            probability=0.05,
            impact_assessment={
                "service_impact": "critical",
                "data_loss_potential": "low",
                "user_impact": "critical",
                "financial_impact": "critical"
            },
            recovery_tier=RecoveryTier.TIER_1,
            estimated_downtime=timedelta(hours=8),
            estimated_cost=250000,
            recovery_steps=[
                "Declare disaster",
                "Activate DR site",
                "Restore from latest backup",
                "Update DNS to DR site",
                "Verify all services",
                "Communicate with stakeholders"
            ],
            required_resources=[
                "dr_site",
                "disaster_recovery_team",
                "external_connectivity"
            ],
            communication_plan={
                "internal": "emergency_notification_system",
                "external": "press_release",
                "stakeholders": "direct_communication"
            }
        )
        
        # 데이터 손상 시나리오
        data_corruption = DisasterScenario(
            name="data_corruption",
            disaster_type=DisasterType.DATA_CORRUPTION,
            description="Critical data corruption detected",
            probability=0.08,
            impact_assessment={
                "service_impact": "high",
                "data_loss_potential": "high",
                "user_impact": "medium",
                "financial_impact": "high"
            },
            recovery_tier=RecoveryTier.TIER_1,
            estimated_downtime=timedelta(hours=4),
            estimated_cost=75000,
            recovery_steps=[
                "Isolate affected systems",
                "Identify corruption scope",
                "Restore from clean backup",
                "Replay transaction logs",
                "Verify data integrity",
                "Resume operations"
            ],
            required_resources=[
                "clean_backups",
                "database_administrator",
                "security_team"
            ],
            communication_plan={
                "internal": "incident_response_channel",
                "external": "limited_notification",
                "stakeholders": "detailed_report"
            }
        )
        
        self.scenarios = {
            "database_failure": database_failure,
            "datacenter_failure": datacenter_failure,
            "data_corruption": data_corruption
        }
    
    def _load_default_recovery_plans(self):
        """기본 복구 계획 로드"""
        
        # 데이터베이스 복구 계획
        database_recovery = RecoveryPlan(
            scenario_name="database_failure",
            recovery_team=[
                "incident_commander",
                "database_administrator",
                "network_engineer",
                "application_developer"
            ],
            communication_channels=[
                "slack_incident_channel",
                "conference_bridge",
                "email_distribution_list"
            ],
            escalation_procedures=[
                {
                    "level": 1,
                    "trigger": "initial_detection",
                    "notify": ["database_administrator", "incident_commander"],
                    "response_time": "15_minutes"
                },
                {
                    "level": 2,
                    "trigger": "no_resolution_30_min",
                    "notify": ["engineering_manager", "operations_director"],
                    "response_time": "10_minutes"
                },
                {
                    "level": 3,
                    "trigger": "no_resolution_2_hours",
                    "notify": ["cto", "ceo"],
                    "response_time": "5_minutes"
                }
            ],
            recovery_steps=[
                {
                    "step": 1,
                    "action": "Verify database failure",
                    "responsible": "database_administrator",
                    "estimated_time": "15_minutes",
                    "dependencies": []
                },
                {
                    "step": 2,
                    "action": "Activate standby database",
                    "responsible": "database_administrator",
                    "estimated_time": "30_minutes",
                    "dependencies": [1]
                },
                {
                    "step": 3,
                    "action": "Update application configuration",
                    "responsible": "application_developer",
                    "estimated_time": "15_minutes",
                    "dependencies": [2]
                },
                {
                    "step": 4,
                    "action": "Test application connectivity",
                    "responsible": "application_developer",
                    "estimated_time": "15_minutes",
                    "dependencies": [3]
                },
                {
                    "step": 5,
                    "action": "Update DNS records",
                    "responsible": "network_engineer",
                    "estimated_time": "30_minutes",
                    "dependencies": [4]
                }
            ],
            verification_procedures=[
                "Check application health endpoints",
                "Verify database connectivity",
                "Test critical user workflows",
                "Validate data integrity"
            ],
            rollback_procedures=[
                "Switch back to original database",
                "Restore original configuration",
                "Update DNS records back",
                "Verify service stability"
            ],
            post_recovery_actions=[
                "Document incident timeline",
                "Conduct root cause analysis",
                "Update monitoring alerts",
                "Schedule post-incident review"
            ]
        )
        
        # 데이터센터 복구 계획
        datacenter_recovery = RecoveryPlan(
            scenario_name="datacenter_failure",
            recovery_team=[
                "incident_commander",
                "disaster_recovery_team",
                "infrastructure_engineer",
                "security_officer",
                "communications_lead"
            ],
            communication_channels=[
                "emergency_notification_system",
                "satellite_phone",
                "external_communication_channel"
            ],
            escalation_procedures=[
                {
                    "level": 1,
                    "trigger": "datacenter_failure_declaration",
                    "notify": ["disaster_recovery_team", "incident_commander"],
                    "response_time": "5_minutes"
                },
                {
                    "level": 2,
                    "trigger": "dr_site_activation",
                    "notify": ["cto", "ceo", "board_members"],
                    "response_time": "15_minutes"
                }
            ],
            recovery_steps=[
                {
                    "step": 1,
                    "action": "Declare disaster",
                    "responsible": "incident_commander",
                    "estimated_time": "15_minutes",
                    "dependencies": []
                },
                {
                    "step": 2,
                    "action": "Activate DR site",
                    "responsible": "disaster_recovery_team",
                    "estimated_time": "2_hours",
                    "dependencies": [1]
                },
                {
                    "step": 3,
                    "action": "Restore from latest backup",
                    "responsible": "infrastructure_engineer",
                    "estimated_time": "3_hours",
                    "dependencies": [2]
                },
                {
                    "step": 4,
                    "action": "Update DNS to DR site",
                    "responsible": "infrastructure_engineer",
                    "estimated_time": "30_minutes",
                    "dependencies": [3]
                },
                {
                    "step": 5,
                    "action": "Verify all services",
                    "responsible": "disaster_recovery_team",
                    "estimated_time": "2_hours",
                    "dependencies": [4]
                }
            ],
            verification_procedures=[
                "Test all critical services",
                "Verify data integrity",
                "Test external connectivity",
                "Validate performance metrics"
            ],
            rollback_procedures=[
                "Prepare for return to primary site",
                "Schedule maintenance window",
                "Migrate back to primary site",
                "Verify full functionality"
            ],
            post_recovery_actions=[
                "Complete incident report",
                "Review DR plan effectiveness",
                "Update DR procedures",
                "Conduct team debriefing"
            ]
        )
        
        self.recovery_plans = {
            "database_failure": database_recovery,
            "datacenter_failure": datacenter_recovery
        }
    
    def get_scenario(self, scenario_name: str) -> Optional[DisasterScenario]:
        """재난 시나리오 조회"""
        return self.scenarios.get(scenario_name)
    
    def get_recovery_plan(self, scenario_name: str) -> Optional[RecoveryPlan]:
        """복구 계획 조회"""
        return self.recovery_plans.get(scenario_name)
    
    def list_scenarios(self) -> List[DisasterScenario]:
        """재난 시나리오 목록 조회"""
        return list(self.scenarios.values())
    
    def list_recovery_plans(self) -> List[RecoveryPlan]:
        """복구 계획 목록 조회"""
        return list(self.recovery_plans.values())
    
    async def execute_recovery_plan(self, scenario_name: str) -> Dict[str, Any]:
        """복구 계획 실행"""
        
        scenario = self.get_scenario(scenario_name)
        recovery_plan = self.get_recovery_plan(scenario_name)
        
        if not scenario or not recovery_plan:
            raise ValueError(f"No scenario or recovery plan found for: {scenario_name}")
        
        self.logger.info(f"Executing recovery plan for scenario: {scenario_name}")
        
        # 복구 단계 실행
        execution_results = []
        
        for step in recovery_plan.recovery_steps:
            step_result = await self._execute_recovery_step(step, recovery_plan)
            execution_results.append(step_result)
            
            if not step_result['success']:
                self.logger.error(f"Recovery step failed: {step['action']}")
                break
        
        # 검증 절차 실행
        if all(result['success'] for result in execution_results):
            verification_results = await self._execute_verification_procedures(recovery_plan)
        else:
            verification_results = {}
        
        # 결과 반환
        return {
            'scenario': scenario_name,
            'success': all(result['success'] for result in execution_results),
            'execution_results': execution_results,
            'verification_results': verification_results,
            'start_time': datetime.now().isoformat()
        }
    
    async def _execute_recovery_step(self, step: Dict[str, Any], recovery_plan: RecoveryPlan) -> Dict[str, Any]:
        """복구 단계 실행"""
        
        step_number = step['step']
        action = step['action']
        responsible = step['responsible']
        estimated_time = step['estimated_time']
        dependencies = step['dependencies']
        
        self.logger.info(f"Executing step {step_number}: {action}")
        
        start_time = datetime.now()
        
        try:
            # 의존성 확인
            if dependencies:
                for dep_step in dependencies:
                    # 이전 단계가 성공했는지 확인
                    pass
            
            # 실제 복구 작업 실행 (실제 구현에서는 구체적인 작업 수행)
            # 여기서는 시뮬레이션만 수행
            await asyncio.sleep(1)  # 작업 시뮬레이션
            
            end_time = datetime.now()
            actual_duration = end_time - start_time
            
            result = {
                'step': step_number,
                'action': action,
                'responsible': responsible,
                'success': True,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'estimated_time': estimated_time,
                'actual_duration': str(actual_duration),
                'within_estimate': actual_duration <= timedelta(minutes=int(estimated_time.split('_')[0]))
            }
            
            self.logger.info(f"Step {step_number} completed successfully")
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            
            result = {
                'step': step_number,
                'action': action,
                'responsible': responsible,
                'success': False,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'error': str(e)
            }
            
            self.logger.error(f"Step {step_number} failed: {str(e)}")
            
            return result
    
    async def _execute_verification_procedures(self, recovery_plan: RecoveryPlan) -> Dict[str, bool]:
        """검증 절차 실행"""
        
        verification_results = {}
        
        for procedure in recovery_plan.verification_procedures:
            try:
                # 실제 검증 작업 실행
                # 여기서는 시뮬레이션만 수행
                await asyncio.sleep(0.5)
                
                verification_results[procedure] = True
                
            except Exception as e:
                self.logger.error(f"Verification failed: {procedure} - {str(e)}")
                verification_results[procedure] = False
        
        return verification_results
    
    def generate_dr_report(self) -> Dict[str, Any]:
        """재난 복구 보고서 생성"""
        
        scenarios = self.list_scenarios()
        plans = self.list_recovery_plans()
        
        # 위험 평가
        total_risk = sum(
            scenario.probability * scenario.estimated_cost 
            for scenario in scenarios
        )
        
        # 복구 등급별 분석
        tier_analysis = {}
        for tier in RecoveryTier:
            tier_scenarios = [s for s in scenarios if s.recovery_tier == tier]
            tier_cost = sum(s.estimated_cost for s in tier_scenarios)
            tier_downtime = sum(s.estimated_downtime.total_seconds() for s in tier_scenarios)
            
            tier_analysis[tier.value] = {
                'scenario_count': len(tier_scenarios),
                'total_cost': tier_cost,
                'average_downtime': tier_downtime / len(tier_scenarios) if tier_scenarios else 0
            }
        
        return {
            'generated_at': datetime.now().isoformat(),
            'total_scenarios': len(scenarios),
            'total_recovery_plans': len(plans),
            'total_annual_risk': total_risk,
            'tier_analysis': tier_analysis,
            'high_risk_scenarios': [
                {
                    'name': scenario.name,
                    'probability': scenario.probability,
                    'estimated_cost': scenario.estimated_cost,
                    'risk_score': scenario.probability * scenario.estimated_cost
                }
                for scenario in sorted(scenarios, key=lambda x: x.probability * x.estimated_cost, reverse=True)[:5]
            ]
        }
```

## 5. 구현 가이드

### 5.1 단계별 구현 계획

#### 1단계: 기본 백업 시스템 (2-3주)
- PostgreSQL, Redis 백업 실행기 구현
- 로컬 및 클라우드 저장소 핸들러 구현
- 기본 백업 스케줄러 구축
- 백업 검증 기능 구현

#### 2단계: 복구 시스템 (2-3주)
- 복구 관리자 및 실행기 구현
- 전체 및 특정 시점 복구 기능
- 복구 계획 및 실행 관리
- 복구 검증 절차

#### 3단계: 재난 복구 계획 (1-2주)
- 재난 시나리오 정의 및 관리
- 복구 계획 템플릿 구축
- 자동화된 복구 절차
- 의사소통 및 상향 절차

#### 4단계: 모니터링 및 알림 (1-2주)
- 백업 상태 모니터링
- 복구 시간 및 성능 메트릭
- 자동 알림 시스템
- 대시보드 및 보고서

#### 5단계: 테스트 및 검증 (1-2주)
- 정기적인 백업 테스트
- 재난 복구 훈련
- 복구 시간 측정 및 개선
- 문서화 및 교육

### 5.2 성능 고려사항

1. **백업 성능**
   - 병렬 백업 처리로 시간 단축
   - 증분 백업으로 저장 공간 효율화
   - 압축 및 암호화 오버헤드 최적화

2. **복구 성능**
   - 사전 준비된 복구 환경
   - 네트워크 대역폭 최적화
   - 병렬 복구 처리

3. **저장소 최적화**
   - 수명 주기 관리로 비용 최적화
   - 지역 간 복제로 내구성 강화
   - 적절한 저장소 계층 구조

### 5.3 보안 고려사항

1. **백업 데이터 보안**
   - 전송 및 저장 중 암호화
   - 접근 제어 및 인증
   - 백업 데이터 무결성 검증

2. **복구 프로세스 보안**
   - 복구 권한 관리
   - 감사 로그 기록
   - 안전한 복구 환경

3. **재난 복구 보안**
   - 보안 침해 시나리오 대응
   - 데이터 유출 방지
   - 보안 팀과의 협업 절차

## 6. 결론

본 데이터 백업 및 복구 전략은 InsiteChart 플랫폼의 비즈니스 연속성을 보장하기 위한 포괄적인 접근 방식을 제공합니다. 다양한 재난 시나리오에 대비한 체계적인 백업 및 복구 절차를 통해 데이터 손실 위험을 최소화하고 신속한 서비스 복구를 가능하게 합니다.

정기적인 테스트와 훈련을 통해 복구 절차의 효과성을 검증하고, 지속적인 개선을 통해 시스템의 안정성과 회복탄력성을 강화할 수 있습니다.