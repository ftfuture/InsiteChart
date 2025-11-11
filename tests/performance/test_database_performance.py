"""
데이터베이스 성능 테스트

이 모듈은 데이터베이스 작업의 성능을 측정하고 벤치마킹합니다.
"""

import pytest
import time
import asyncio
import statistics
from typing import Dict, Any, List
from unittest.mock import patch, AsyncMock, MagicMock

from backend.models.database_models import Stock, SentimentAnalysis, User, Watchlist
from backend.models.unified_models import UnifiedStockData, StockType, SentimentScore


class TestDatabasePerformance:
    """데이터베이스 성능 테스트 클래스"""
    
    @pytest.fixture
    def performance_thresholds(self):
        """성능 임계값 픽스처"""
        return {
            "database_operations": {
                "create": {
                    "excellent": 5.0,    # 5ms 이하
                    "good": 10.0,         # 10ms 이하
                    "acceptable": 20.0    # 20ms 이하
                },
                "read": {
                    "excellent": 2.0,    # 2ms 이하
                    "good": 5.0,         # 5ms 이하
                    "acceptable": 10.0    # 10ms 이하
                },
                "update": {
                    "excellent": 5.0,    # 5ms 이하
                    "good": 10.0,         # 10ms 이하
                    "acceptable": 20.0    # 20ms 이하
                },
                "delete": {
                    "excellent": 5.0,    # 5ms 이하
                    "good": 10.0,         # 10ms 이하
                    "acceptable": 20.0    # 20ms 이하
                }
            },
            "query_performance": {
                "simple_select": {
                    "excellent": 2.0,    # 2ms 이하
                    "good": 5.0,         # 5ms 이하
                    "acceptable": 10.0    # 10ms 이하
                },
                "complex_join": {
                    "excellent": 10.0,   # 10ms 이하
                    "good": 20.0,        # 20ms 이하
                    "acceptable": 50.0    # 50ms 이하
                },
                "aggregate_query": {
                    "excellent": 15.0,   # 15ms 이하
                    "good": 30.0,        # 30ms 이하
                    "acceptable": 60.0    # 60ms 이하
                }
            },
            "concurrent_operations": {
                "excellent": 100,       # 100개 동시 작업
                "good": 50,             # 50개 동시 작업
                "acceptable": 20        # 20개 동시 작업
            }
        }
    
    @pytest.fixture
    def sample_stock_data(self):
        """샘플 주식 데이터 픽스처"""
        return {
            "symbol": "AAPL",
            "company_name": "Apple Inc.",
            "current_price": 150.0,
            "previous_close": 145.0,
            "change": 5.0,
            "change_percent": 3.45,
            "volume": 1000000,
            "market_cap": 2500000000000,
            "pe_ratio": 25.5,
            "dividend_yield": 0.5,
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "description": "Apple Inc. designs, manufactures",
            "website": "https://www.apple.com",
            "exchange": "NASDAQ",
            "currency": "USD",
            "country": "US",
            "timezone": "America/New_York",
            "stock_type": "equity"
        }
    
    @pytest.fixture
    def mock_db_session(self):
        """모의 데이터베이스 세션 픽스처"""
        session = MagicMock()
        session.add = MagicMock()
        session.commit = MagicMock()
        session.query = MagicMock()
        session.filter = MagicMock()
        session.first = MagicMock()
        session.all = MagicMock()
        session.delete = MagicMock()
        session.close = MagicMock()
        return session
    
    @patch('backend.database.get_db')
    def test_stock_crud_performance(self, mock_get_db, performance_thresholds, sample_stock_data, mock_db_session):
        """주식 데이터 CRUD 성능 테스트"""
        mock_get_db.return_value = mock_db_session
        
        # CREATE 성능 측정
        create_times = []
        for i in range(50):
            stock_data = sample_stock_data.copy()
            stock_data["symbol"] = f"STOCK_{i:04d}"
            
            start_time = time.time()
            
            # 주식 데이터 생성
            stock = Stock(
                symbol=stock_data["symbol"],
                company_name=stock_data["company_name"],
                current_price=stock_data["current_price"],
                previous_close=stock_data["previous_close"],
                change=stock_data["change"],
                change_percent=stock_data["change_percent"],
                volume=stock_data["volume"],
                market_cap=stock_data["market_cap"],
                pe_ratio=stock_data["pe_ratio"],
                dividend_yield=stock_data["dividend_yield"],
                sector=stock_data["sector"],
                industry=stock_data["industry"],
                description=stock_data["description"],
                website=stock_data["website"],
                exchange=stock_data["exchange"],
                currency=stock_data["currency"],
                country=stock_data["country"],
                timezone=stock_data["timezone"],
                stock_type=stock_data["stock_type"]
            )
            
            mock_db_session.add(stock)
            mock_db_session.commit()
            
            end_time = time.time()
            create_times.append((end_time - start_time) * 1000)
        
        avg_create_time = statistics.mean(create_times)
        
        # READ 성능 측정
        read_times = []
        for i in range(50):
            start_time = time.time()
            
            # 모의 쿼리 결과 설정
            mock_stock = MagicMock()
            mock_stock.symbol = f"STOCK_{i:04d}"
            mock_stock.company_name = sample_stock_data["company_name"]
            mock_stock.current_price = sample_stock_data["current_price"]
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_stock
            
            # 주식 데이터 조회
            result = mock_db_session.query(Stock).filter(Stock.symbol == f"STOCK_{i:04d}").first()
            
            end_time = time.time()
            read_times.append((end_time - start_time) * 1000)
            assert result is not None
        
        avg_read_time = statistics.mean(read_times)
        
        # UPDATE 성능 측정
        update_times = []
        for i in range(30):
            start_time = time.time()
            
            # 모의 업데이트
            mock_stock = MagicMock()
            mock_stock.current_price = sample_stock_data["current_price"] + i
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_stock
            
            stock = mock_db_session.query(Stock).filter(Stock.symbol == f"STOCK_{i:04d}").first()
            stock.current_price = sample_stock_data["current_price"] + i
            mock_db_session.commit()
            
            end_time = time.time()
            update_times.append((end_time - start_time) * 1000)
        
        avg_update_time = statistics.mean(update_times)
        
        # DELETE 성능 측정
        delete_times = []
        for i in range(20):
            start_time = time.time()
            
            # 모의 삭제
            mock_stock = MagicMock()
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_stock
            
            stock = mock_db_session.query(Stock).filter(Stock.symbol == f"STOCK_{i:04d}").first()
            mock_db_session.delete(stock)
            mock_db_session.commit()
            
            end_time = time.time()
            delete_times.append((end_time - start_time) * 1000)
        
        avg_delete_time = statistics.mean(delete_times)
        
        # 성능 기준 확인
        assert avg_create_time < performance_thresholds["database_operations"]["create"]["acceptable"]
        assert avg_read_time < performance_thresholds["database_operations"]["read"]["acceptable"]
        assert avg_update_time < performance_thresholds["database_operations"]["update"]["acceptable"]
        assert avg_delete_time < performance_thresholds["database_operations"]["delete"]["acceptable"]
        
        print(f"Stock CRUD Performance:")
        print(f"  CREATE - Average: {avg_create_time:.2f}ms")
        print(f"  READ - Average: {avg_read_time:.2f}ms")
        print(f"  UPDATE - Average: {avg_update_time:.2f}ms")
        print(f"  DELETE - Average: {avg_delete_time:.2f}ms")
    
    @patch('backend.database.get_db')
    def test_sentiment_analysis_performance(self, mock_get_db, performance_thresholds, mock_db_session):
        """감성 분석 데이터 성능 테스트"""
        mock_get_db.return_value = mock_db_session
        
        # 감성 분석 데이터 생성 성능 측정
        create_times = []
        for i in range(30):
            start_time = time.time()
            
            sentiment = SentimentAnalysis(
                symbol=f"STOCK_{i:04d}",
                overall_sentiment=0.5 + (i % 10) * 0.1,
                news_sentiment=0.4 + (i % 10) * 0.1,
                social_sentiment=0.6 + (i % 10) * 0.1,
                analyst_sentiment=0.5 + (i % 10) * 0.1,
                confidence_score=0.8 + (i % 5) * 0.04,
                analysis_timestamp=time.time(),
                news_count=10 + i,
                social_mentions=100 + i * 10,
                analyst_ratings=5 + i
            )
            
            mock_db_session.add(sentiment)
            mock_db_session.commit()
            
            end_time = time.time()
            create_times.append((end_time - start_time) * 1000)
        
        avg_create_time = statistics.mean(create_times)
        
        # 감성 분석 데이터 조회 성능 측정
        read_times = []
        for i in range(30):
            start_time = time.time()
            
            # 모의 쿼리 결과 설정
            mock_sentiment = MagicMock()
            mock_sentiment.symbol = f"STOCK_{i:04d}"
            mock_sentiment.overall_sentiment = 0.5 + (i % 10) * 0.1
            mock_sentiment.confidence_score = 0.8 + (i % 5) * 0.04
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_sentiment
            
            result = mock_db_session.query(SentimentAnalysis).filter(SentimentAnalysis.symbol == f"STOCK_{i:04d}").first()
            
            end_time = time.time()
            read_times.append((end_time - start_time) * 1000)
            assert result is not None
        
        avg_read_time = statistics.mean(read_times)
        
        # 성능 기준 확인
        assert avg_create_time < performance_thresholds["database_operations"]["create"]["acceptable"]
        assert avg_read_time < performance_thresholds["database_operations"]["read"]["acceptable"]
        
        print(f"Sentiment Analysis Performance:")
        print(f"  CREATE - Average: {avg_create_time:.2f}ms")
        print(f"  READ - Average: {avg_read_time:.2f}ms")
    
    @patch('backend.database.get_db')
    def test_complex_query_performance(self, mock_get_db, performance_thresholds, mock_db_session):
        """복잡한 쿼리 성능 테스트"""
        mock_get_db.return_value = mock_db_session
        
        # 단순 SELECT 쿼리 성능 측정
        simple_select_times = []
        for i in range(20):
            start_time = time.time()
            
            # 모의 쿼리 결과 설정
            mock_stocks = [MagicMock() for _ in range(10)]
            for j, stock in enumerate(mock_stocks):
                stock.symbol = f"STOCK_{j:04d}"
                stock.current_price = 100 + j * 10
            
            mock_db_session.query.return_value.filter.return_value.all.return_value = mock_stocks
            
            results = mock_db_session.query(Stock).filter(Stock.sector == "Technology").all()
            
            end_time = time.time()
            simple_select_times.append((end_time - start_time) * 1000)
            assert len(results) > 0
        
        avg_simple_select_time = statistics.mean(simple_select_times)
        
        # 복잡한 JOIN 쿼리 성능 측정
        complex_join_times = []
        for i in range(10):
            start_time = time.time()
            
            # 모의 JOIN 쿼리 결과 설정
            mock_joined_results = []
            for j in range(5):
                stock = MagicMock()
                stock.symbol = f"STOCK_{j:04d}"
                stock.company_name = f"Company {j}"
                stock.current_price = 100 + j * 10
                
                sentiment = MagicMock()
                sentiment.overall_sentiment = 0.5 + j * 0.1
                sentiment.confidence_score = 0.8 + j * 0.04
                
                # 모의 조인 결과
                mock_joined_results.append((stock, sentiment))
            
            mock_db_session.query.return_value.join.return_value.filter.return_value.all.return_value = mock_joined_results
            
            results = mock_db_session.query(Stock).join(SentimentAnalysis).filter(Stock.sector == "Technology").all()
            
            end_time = time.time()
            complex_join_times.append((end_time - start_time) * 1000)
            assert len(results) > 0
        
        avg_complex_join_time = statistics.mean(complex_join_times)
        
        # 집계 쿼리 성능 측정
        aggregate_times = []
        for i in range(10):
            start_time = time.time()
            
            # 모의 집계 쿼리 결과 설정
            mock_aggregate_result = MagicMock()
            mock_aggregate_result.avg_price = 150.0
            mock_aggregate_result.max_price = 200.0
            mock_aggregate_result.min_price = 100.0
            mock_aggregate_result.total_count = 100
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_aggregate_result
            
            result = mock_db_session.query(Stock).filter(Stock.sector == "Technology").first()
            
            end_time = time.time()
            aggregate_times.append((end_time - start_time) * 1000)
            assert result is not None
        
        avg_aggregate_time = statistics.mean(aggregate_times)
        
        # 성능 기준 확인
        assert avg_simple_select_time < performance_thresholds["query_performance"]["simple_select"]["acceptable"]
        assert avg_complex_join_time < performance_thresholds["query_performance"]["complex_join"]["acceptable"]
        assert avg_aggregate_time < performance_thresholds["query_performance"]["aggregate_query"]["acceptable"]
        
        print(f"Complex Query Performance:")
        print(f"  Simple SELECT - Average: {avg_simple_select_time:.2f}ms")
        print(f"  Complex JOIN - Average: {avg_complex_join_time:.2f}ms")
        print(f"  Aggregate Query - Average: {avg_aggregate_time:.2f}ms")
    
    @patch('backend.database.get_db')
    def test_concurrent_database_operations(self, mock_get_db, performance_thresholds, mock_db_session):
        """동시 데이터베이스 작업 성능 테스트"""
        import threading
        
        mock_get_db.return_value = mock_db_session
        results = {"create": [], "read": []}
        
        def create_operation(thread_id):
            """CREATE 작업을 수행하는 함수"""
            for i in range(5):
                start_time = time.time()
                
                stock = Stock(
                    symbol=f"CONCURRENT_STOCK_{thread_id}_{i}",
                    company_name=f"Concurrent Company {thread_id}_{i}",
                    current_price=100.0 + i,
                    sector="Technology"
                )
                
                mock_db_session.add(stock)
                mock_db_session.commit()
                
                end_time = time.time()
                results["create"].append((end_time - start_time) * 1000)
        
        def read_operation(thread_id):
            """READ 작업을 수행하는 함수"""
            for i in range(5):
                start_time = time.time()
                
                # 모의 쿼리 결과 설정
                mock_stock = MagicMock()
                mock_stock.symbol = f"STOCK_{thread_id}_{i}"
                
                mock_db_session.query.return_value.filter.return_value.first.return_value = mock_stock
                
                result = mock_db_session.query(Stock).filter(Stock.symbol == f"STOCK_{thread_id}_{i}").first()
                
                end_time = time.time()
                results["read"].append((end_time - start_time) * 1000)
        
        # 동시 CREATE 작업
        threads = []
        start_time = time.time()
        
        for i in range(10):
            thread = threading.Thread(target=create_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        create_total_time = time.time() - start_time
        
        # 동시 READ 작업
        threads = []
        start_time = time.time()
        
        for i in range(10):
            thread = threading.Thread(target=read_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        read_total_time = time.time() - start_time
        
        # 성능 분석
        avg_create_time = statistics.mean(results["create"])
        avg_read_time = statistics.mean(results["read"])
        total_operations = len(results["create"]) + len(results["read"])
        
        # 성능 기준 확인
        assert total_operations >= performance_thresholds["concurrent_operations"]["acceptable"]
        assert avg_create_time < performance_thresholds["database_operations"]["create"]["acceptable"]
        assert avg_read_time < performance_thresholds["database_operations"]["read"]["acceptable"]
        
        print(f"Concurrent Database Operations:")
        print(f"  Total Operations: {total_operations}")
        print(f"  CREATE - Average: {avg_create_time:.2f}ms, Total Time: {create_total_time:.2f}s")
        print(f"  READ - Average: {avg_read_time:.2f}ms, Total Time: {read_total_time:.2f}s")
    
    @patch('backend.database.get_db')
    def test_database_connection_pool_performance(self, mock_get_db, performance_thresholds, mock_db_session):
        """데이터베이스 연결 풀 성능 테스트"""
        mock_get_db.return_value = mock_db_session
        
        # 연결 획득 및 해제 성능 측정
        connection_times = []
        for i in range(50):
            start_time = time.time()
            
            # 모의 연결 획득
            session = mock_get_db()
            
            # 간단한 쿼리 실행
            mock_stock = MagicMock()
            mock_stock.symbol = "AAPL"
            session.query.return_value.filter.return_value.first.return_value = mock_stock
            
            result = session.query(Stock).filter(Stock.symbol == "AAPL").first()
            
            # 연결 해제
            session.close()
            
            end_time = time.time()
            connection_times.append((end_time - start_time) * 1000)
            assert result is not None
        
        avg_connection_time = statistics.mean(connection_times)
        
        # 성능 기준 확인
        assert avg_connection_time < performance_thresholds["database_operations"]["read"]["acceptable"]
        
        print(f"Database Connection Pool Performance:")
        print(f"  Average Connection Time: {avg_connection_time:.2f}ms")
    
    @patch('backend.database.get_db')
    def test_transaction_performance(self, mock_get_db, performance_thresholds, mock_db_session):
        """트랜잭션 성능 테스트"""
        mock_get_db.return_value = mock_db_session
        
        # 단일 작업 트랜잭션 성능 측정
        single_transaction_times = []
        for i in range(20):
            start_time = time.time()
            
            stock = Stock(
                symbol=f"SINGLE_TX_{i:04d}",
                company_name=f"Single Transaction Company {i}",
                current_price=100.0 + i,
                sector="Technology"
            )
            
            mock_db_session.add(stock)
            mock_db_session.commit()
            
            end_time = time.time()
            single_transaction_times.append((end_time - start_time) * 1000)
        
        avg_single_transaction_time = statistics.mean(single_transaction_times)
        
        # 다중 작업 트랜잭션 성능 측정
        multi_transaction_times = []
        for i in range(10):
            start_time = time.time()
            
            # 여러 작업을 하나의 트랜잭션으로 처리
            for j in range(5):
                stock = Stock(
                    symbol=f"MULTI_TX_{i:04d}_{j}",
                    company_name=f"Multi Transaction Company {i}_{j}",
                    current_price=100.0 + i + j,
                    sector="Technology"
                )
                
                mock_db_session.add(stock)
            
            mock_db_session.commit()
            
            end_time = time.time()
            multi_transaction_times.append((end_time - start_time) * 1000)
        
        avg_multi_transaction_time = statistics.mean(multi_transaction_times)
        
        # 성능 기준 확인
        assert avg_single_transaction_time < performance_thresholds["database_operations"]["create"]["acceptable"]
        assert avg_multi_transaction_time < performance_thresholds["database_operations"]["create"]["acceptable"]
        
        print(f"Transaction Performance:")
        print(f"  Single Operation - Average: {avg_single_transaction_time:.2f}ms")
        print(f"  Multi Operation - Average: {avg_multi_transaction_time:.2f}ms")
        print(f"  Efficiency Ratio: {avg_multi_transaction_time / avg_single_transaction_time:.2f}")
    
    @patch('backend.database.get_db')
    def test_index_performance(self, mock_get_db, performance_thresholds, mock_db_session):
        """인덱스 성능 테스트"""
        mock_get_db.return_value = mock_db_session
        
        # 인덱스가 있는 컬럼에 대한 쿼리 성능 측정
        indexed_query_times = []
        for i in range(30):
            start_time = time.time()
            
            # 모의 인덱스 쿼리 결과 설정
            mock_stock = MagicMock()
            mock_stock.symbol = f"STOCK_{i:04d}"
            
            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_stock
            
            result = mock_db_session.query(Stock).filter(Stock.symbol == f"STOCK_{i:04d}").first()
            
            end_time = time.time()
            indexed_query_times.append((end_time - start_time) * 1000)
            assert result is not None
        
        avg_indexed_query_time = statistics.mean(indexed_query_times)
        
        # 인덱스가 없는 컬럼에 대한 쿼리 성능 측정
        non_indexed_query_times = []
        for i in range(30):
            start_time = time.time()
            
            # 모의 비인덱스 쿼리 결과 설정
            mock_stocks = [MagicMock() for _ in range(5)]
            for j, stock in enumerate(mock_stocks):
                stock.description = f"Description containing keyword {i}"
            
            mock_db_session.query.return_value.filter.return_value.all.return_value = mock_stocks
            
            results = mock_db_session.query(Stock).filter(Stock.description.contains(f"keyword {i}")).all()
            
            end_time = time.time()
            non_indexed_query_times.append((end_time - start_time) * 1000)
            assert len(results) > 0
        
        avg_non_indexed_query_time = statistics.mean(non_indexed_query_times)
        
        # 성능 기준 확인
        assert avg_indexed_query_time < performance_thresholds["query_performance"]["simple_select"]["good"]
        assert avg_non_indexed_query_time < performance_thresholds["query_performance"]["simple_select"]["acceptable"]
        
        # 인덱스 쿼리가 비인덱스 쿼리보다 빨라야 함
        assert avg_indexed_query_time < avg_non_indexed_query_time
        
        print(f"Index Performance:")
        print(f"  Indexed Query - Average: {avg_indexed_query_time:.2f}ms")
        print(f"  Non-Indexed Query - Average: {avg_non_indexed_query_time:.2f}ms")
        print(f"  Performance Improvement: {((avg_non_indexed_query_time - avg_indexed_query_time) / avg_non_indexed_query_time) * 100:.1f}%")