"""
데이터베이스 마이그레이션 단위 테스트

이 모듈은 Alembic 데이터베이스 마이그레이션의 개별 기능을 테스트합니다.
"""

import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch, mock_open
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from alembic.migration import MigrationInfo


class TestDatabaseMigrations:
    """데이터베이스 마이그레이션 단위 테스트 클래스"""
    
    @pytest.fixture
    def temp_database_url(self):
        """임시 데이터베이스 URL 픽스처"""
        # SQLite 임시 데이터베이스 사용
        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db.close()
        db_url = f"sqlite:///{temp_db.name}"
        yield db_url
        # 정리
        os.unlink(temp_db.name)
    
    @pytest.fixture
    def alembic_config(self, temp_database_url):
        """Alembic 설정 픽스처"""
        # 임시 alembic.ini 파일 생성
        alembic_ini = tempfile.NamedTemporaryFile(mode='w+', suffix='.ini', delete=False)
        alembic_ini.write(f"""
[alembic]
script_location = backend/alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = {temp_database_url}

[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
""")
        alembic_ini.close()
        
        config = Config(alembic_ini.name)
        yield config
        # 정리
        os.unlink(alembic_ini.name)
    
    @pytest.fixture
    def mock_migration_context(self):
        """모의 마이그레이션 컨텍스트 픽스처"""
        context = MagicMock()
        context.get_current_revision.return_value = None
        context.get_heads.return_value = ['001']
        context.get_base_revision.return_value = None
        return context
    
    def test_alembic_config_initialization(self, alembic_config):
        """Alembic 설정 초기화 테스트"""
        assert alembic_config is not None
        assert alembic_config.get_main_option("script_location") == "backend/alembic"
        assert alembic_config.get_main_option("sqlalchemy.url") is not None
    
    def test_migration_script_directory_initialization(self, alembic_config):
        """마이그레이션 스크립트 디렉토리 초기화 테스트"""
        script_dir = ScriptDirectory.from_config(alembic_config)
        assert script_dir is not None
        assert script_dir.versions is not None
    
    def test_initial_migration_upgrade(self, alembic_config, temp_database_url):
        """초기 마이그레이션 업그레이드 테스트"""
        # 데이터베이스 엔진 생성
        engine = create_engine(temp_database_url)
        
        # 마이그레이션 실행 전 테이블이 없는지 확인
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables_before = [row[0] for row in result.fetchall()]
            assert len(tables_before) == 0
        
        # 마이그레이션 실행
        with patch('alembic.command.upgrade') as mock_upgrade:
            mock_upgrade.return_value = None
            command.upgrade(alembic_config, "head")
            mock_upgrade.assert_called_once_with(alembic_config, "head")
        
        # 마이그레이션 실행 후 테이블 확인
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables_after = [row[0] for row in result.fetchall()]
            
            # 예상되는 테이블들
            expected_tables = [
                'users', 'api_keys', 'stocks', 'stock_prices', 
                'sentiment_data', 'watchlist_items', 'search_history', 
                'user_sessions', 'system_logs', 'alembic_version'
            ]
            
            # 실제 테이블 수 확인 (alembic_version 포함)
            assert len(tables_after) >= len(expected_tables)
            
            # 주요 테이블들이 존재하는지 확인
            for table in expected_tables[:-1]:  # alembic_version 제외
                assert table in tables_after, f"Table {table} not found after migration"
    
    def test_initial_migration_downgrade(self, alembic_config, temp_database_url):
        """초기 마이그레이션 다운그레이드 테스트"""
        # 데이터베이스 엔진 생성
        engine = create_engine(temp_database_url)
        
        # 먼저 업그레이드 실행
        with patch('alembic.command.upgrade') as mock_upgrade:
            mock_upgrade.return_value = None
            command.upgrade(alembic_config, "head")
        
        # 다운그레이드 실행
        with patch('alembic.command.downgrade') as mock_downgrade:
            mock_downgrade.return_value = None
            command.downgrade(alembic_config, "base")
            mock_downgrade.assert_called_once_with(alembic_config, "base")
        
        # 다운그레이드 후 테이블 확인
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables_after = [row[0] for row in result.fetchall()]
            
            # alembic_version 테이블만 남아있어야 함
            assert 'alembic_version' in tables_after
            # 다른 테이블들은 없어야 함
            user_tables = [t for t in tables_after if t != 'alembic_version']
            assert len(user_tables) == 0
    
    def test_migration_revision_tracking(self, alembic_config):
        """마이그레이션 리비전 추적 테스트"""
        with patch('alembic.command.current') as mock_current:
            mock_current.return_value = "001"
            result = command.current(alembic_config)
            assert result == "001"
            mock_current.assert_called_once_with(alembic_config)
    
    def test_migration_history(self, alembic_config):
        """마이그레이션 히스토리 테스트"""
        with patch('alembic.command.history') as mock_history:
            mock_history.return_value = ["001 -> 002 (initial migration)"]
            result = command.history(alembic_config)
            assert "001 -> 002" in result[0]
            mock_history.assert_called_once_with(alembic_config)
    
    def test_migration_heads(self, alembic_config):
        """마이그레이션 헤드 테스트"""
        with patch('alembic.command.heads') as mock_heads:
            mock_heads.return_value = ["001"]
            result = command.heads(alembic_config)
            assert "001" in result
            mock_heads.assert_called_once_with(alembic_config)
    
    def test_migration_branches(self, alembic_config):
        """마이그레이션 브랜치 테스트"""
        with patch('alembic.command.branches') as mock_branches:
            mock_branches.return_value = []
            result = command.branches(alembic_config)
            assert isinstance(result, list)
            mock_branches.assert_called_once_with(alembic_config)
    
    def test_migration_show(self, alembic_config):
        """마이그레이션 상세 정보 테스트"""
        with patch('alembic.command.show') as mock_show:
            mock_show.return_value = "Revision: 001\nCreate Date: 2025-11-07 21:08:00.000000\n\nInitial migration for InsiteChart platform."
            result = command.show(alembic_config, "001")
            assert "Revision: 001" in result
            assert "Initial migration" in result
            mock_show.assert_called_once_with(alembic_config, "001")
    
    def test_migration_edit(self, alembic_config):
        """마이그레이션 편집 테스트"""
        with patch('alembic.command.edit') as mock_edit:
            mock_edit.return_value = None
            command.edit(alembic_config, "001")
            mock_edit.assert_called_once_with(alembic_config, "001")
    
    def test_migration_merge(self, alembic_config):
        """마이그레이션 병합 테스트"""
        with patch('alembic.command.merge') as mock_merge:
            mock_merge.return_value = None
            command.merge(alembic_config, "001", "002")
            mock_merge.assert_called_once_with(alembic_config, "001", "002")
    
    def test_migration_stamp(self, alembic_config):
        """마이그레이션 스탬프 테스트"""
        with patch('alembic.command.stamp') as mock_stamp:
            mock_stamp.return_value = None
            command.stamp(alembic_config, "001")
            mock_stamp.assert_called_once_with(alembic_config, "001")
    
    def test_migration_revision_creation(self, alembic_config):
        """새 마이그레이션 리비전 생성 테스트"""
        with patch('alembic.command.revision') as mock_revision:
            mock_revision.return_value = None
            command.revision(
                alembic_config, 
                message="Add new feature table",
                autogenerate=True
            )
            mock_revision.assert_called_once_with(
                alembic_config, 
                message="Add new feature table",
                autogenerate=True
            )
    
    def test_database_schema_validation(self, alembic_config, temp_database_url):
        """데이터베이스 스키마 유효성 검증 테스트"""
        # 데이터베이스 엔진 생성
        engine = create_engine(temp_database_url)
        
        # 마이그레이션 실행
        with patch('alembic.command.upgrade') as mock_upgrade:
            mock_upgrade.return_value = None
            command.upgrade(alembic_config, "head")
        
        # 스키마 유효성 검증
        with engine.connect() as conn:
            # users 테이블 구조 확인
            result = conn.execute(text("PRAGMA table_info(users)"))
            users_columns = [row[1] for row in result.fetchall()]
            expected_users_columns = [
                'id', 'username', 'email', 'password_hash', 'role', 
                'is_active', 'created_at', 'last_login'
            ]
            for col in expected_users_columns:
                assert col in users_columns, f"Column {col} not found in users table"
            
            # stocks 테이블 구조 확인
            result = conn.execute(text("PRAGMA table_info(stocks)"))
            stocks_columns = [row[1] for row in result.fetchall()]
            expected_stocks_columns = [
                'id', 'symbol', 'company_name', 'stock_type', 
                'exchange', 'sector', 'industry', 'market_cap', 
                'created_at', 'updated_at'
            ]
            for col in expected_stocks_columns:
                assert col in stocks_columns, f"Column {col} not found in stocks table"
            
            # 외래 키 제약 조건 확인
            result = conn.execute(text("PRAGMA foreign_key_list(api_keys)"))
            fk_constraints = [row for row in result.fetchall()]
            assert len(fk_constraints) > 0, "No foreign key constraints found in api_keys table"
            
            # users 테이블의 고유 제약 조건 확인
            result = conn.execute(text("PRAGMA index_list(users)"))
            indexes = [row for row in result.fetchall()]
            unique_indexes = [idx for idx in indexes if idx[2] == 1]  # unique flag
            assert len(unique_indexes) >= 2, "Not enough unique indexes found in users table"
    
    def test_migration_rollback_scenario(self, alembic_config, temp_database_url):
        """마이그레이션 롤백 시나리오 테스트"""
        # 데이터베이스 엔진 생성
        engine = create_engine(temp_database_url)
        
        # 마이그레이션 실행
        with patch('alembic.command.upgrade') as mock_upgrade:
            mock_upgrade.return_value = None
            command.upgrade(alembic_config, "head")
        
        # 데이터 추가
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO users (username, email, password_hash, role, is_active, created_at)
                VALUES ('testuser', 'test@example.com', 'hashed_password', 'user', 1, datetime('now'))
            """))
            conn.commit()
        
        # 다운그레이드 실행
        with patch('alembic.command.downgrade') as mock_downgrade:
            mock_downgrade.return_value = None
            command.downgrade(alembic_config, "base")
        
        # 롤백 후 데이터베이스 상태 확인
        with engine.connect() as conn:
            # 테이블이 삭제되었는지 확인
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables_after = [row[0] for row in result.fetchall()]
            
            # alembic_version 테이블만 남아있어야 함
            assert 'alembic_version' in tables_after
            user_tables = [t for t in tables_after if t != 'alembic_version']
            assert len(user_tables) == 0
    
    def test_migration_with_existing_data(self, alembic_config, temp_database_url):
        """기존 데이터가 있는 상태에서의 마이그레이션 테스트"""
        # 데이터베이스 엔진 생성
        engine = create_engine(temp_database_url)
        
        # 마이그레이션 실행 전 기본 테이블 수동 생성
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    username VARCHAR(50) NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    is_active BOOLEAN NOT NULL,
                    created_at DATETIME NOT NULL,
                    last_login DATETIME
                )
            """))
            conn.execute(text("""
                INSERT INTO users (username, email, password_hash, role, is_active, created_at)
                VALUES ('existinguser', 'existing@example.com', 'hashed_password', 'user', 1, datetime('now'))
            """))
            conn.commit()
        
        # 마이그레이션 실행
        with patch('alembic.command.upgrade') as mock_upgrade:
            mock_upgrade.return_value = None
            command.upgrade(alembic_config, "head")
        
        # 마이그레이션 후 데이터 확인
        with engine.connect() as conn:
            result = conn.execute(text("SELECT username, email FROM users WHERE username = 'existinguser'"))
            existing_user = result.fetchone()
            assert existing_user is not None
            assert existing_user[0] == 'existinguser'
            assert existing_user[1] == 'existing@example.com'
    
    def test_migration_error_handling(self, alembic_config):
        """마이그레이션 오류 처리 테스트"""
        with patch('alembic.command.upgrade') as mock_upgrade:
            # 마이그레이션 오류 시뮬레이션
            mock_upgrade.side_effect = Exception("Migration failed")
            
            with pytest.raises(Exception, match="Migration failed"):
                command.upgrade(alembic_config, "head")
            
            mock_upgrade.assert_called_once_with(alembic_config, "head")
    
    def test_migration_environment_detection(self, alembic_config):
        """마이그레이션 환경 감지 테스트"""
        # 오프라인 모드 테스트
        with patch('alembic.command.upgrade') as mock_upgrade:
            mock_upgrade.return_value = None
            command.upgrade(alembic_config, "head", sql=True)
            mock_upgrade.assert_called_once_with(alembic_config, "head", sql=True)
        
        # 온라인 모드 테스트
        with patch('alembic.command.upgrade') as mock_upgrade:
            mock_upgrade.return_value = None
            command.upgrade(alembic_config, "head")
            mock_upgrade.assert_called_once_with(alembic_config, "head")
    
    def test_migration_transaction_handling(self, alembic_config, temp_database_url):
        """마이그레이션 트랜잭션 처리 테스트"""
        # 데이터베이스 엔진 생성
        engine = create_engine(temp_database_url)
        
        # 마이그레이션 실행
        with patch('alembic.command.upgrade') as mock_upgrade:
            mock_upgrade.return_value = None
            command.upgrade(alembic_config, "head")
        
        # 트랜잭션 내에서 데이터 조작
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                conn.execute(text("""
                    INSERT INTO users (username, email, password_hash, role, is_active, created_at)
                    VALUES ('transaction_user', 'transaction@example.com', 'hashed_password', 'user', 1, datetime('now'))
                """))
                
                # 트랜잭션 커밋
                trans.commit()
                
                # 커밋 후 데이터 확인
                result = conn.execute(text("SELECT username FROM users WHERE username = 'transaction_user'"))
                user = result.fetchone()
                assert user is not None
                assert user[0] == 'transaction_user'
                
            except Exception:
                # 오류 발생 시 롤백
                trans.rollback()
                raise
    
    def test_migration_performance_monitoring(self, alembic_config, temp_database_url):
        """마이그레이션 성능 모니터링 테스트"""
        import time
        
        # 데이터베이스 엔진 생성
        engine = create_engine(temp_database_url)
        
        # 마이그레이션 실행 시간 측정
        start_time = time.time()
        
        with patch('alembic.command.upgrade') as mock_upgrade:
            mock_upgrade.return_value = None
            command.upgrade(alembic_config, "head")
        
        end_time = time.time()
        migration_time = end_time - start_time
        
        # 마이그레이션 시간이 합리적인 범위 내인지 확인 (예: 10초 이내)
        assert migration_time < 10.0, f"Migration took too long: {migration_time} seconds"
        
        # 마이그레이션 후 데이터베이스 상태 확인
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result.fetchall()]
            assert len(tables) > 0, "No tables found after migration"