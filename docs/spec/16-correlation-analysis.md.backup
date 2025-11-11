# 상관관계 분석 기능 구현 계획

## 1. 개요

주식 가격과 소셜 센티먼트 간의 상관관계를 분석하는 기능을 설계합니다. 이 기능은 사용자가 주가 움직임과 소셜 트렌드 간의 관계를 이해하고, 이를 통해 투자 결정에 도움을 주는 것을 목표로 합니다.

## 2. 상관관계 분석 아키텍처

### 2.1 고수준 아키텍처

```mermaid
graph TB
    A[Data Collection Layer] --> B[Data Processing Layer]
    B --> C[Correlation Analysis Engine]
    C --> D[Visualization Layer]
    D --> E[Insight Generation]
    
    subgraph "Data Collection Layer"
        A1[Price Data Collector]
        A2[Sentiment Data Collector]
        A3[Volume Data Collector]
        A4[External Events Collector]
    end
    
    subgraph "Data Processing Layer"
        B1[Data Normalizer]
        B2[Time Series Aligner]
        B3[Feature Extractor]
        B4[Data Validator]
    end
    
    subgraph "Correlation Analysis Engine"
        C1[Correlation Calculator]
        C2[Lag Analysis Engine]
        C3[Causality Detector]
        C4[Statistical Significance Tester]
    end
    
    subgraph "Visualization Layer"
        D1[Correlation Heatmap]
        D2[Time Series Overlay]
        D3[Lag Analysis Chart]
        D4[Causality Graph]
    end
    
    subgraph "Insight Generation"
        E1[Pattern Detector]
        E2[Anomaly Identifier]
        E3[Predictive Model]
        E4[Report Generator]
    end
    
    A --> A1
    A --> A2
    A --> A3
    A --> A4
    
    B --> B1
    B --> B2
    B --> B3
    B --> B4
    
    C --> C1
    C --> C2
    C --> C3
    C --> C4
    
    D --> D1
    D --> D2
    D --> D3
    D --> D4
    
    E --> E1
    E --> E2
    E --> E3
    E --> E4
```

### 2.2 데이터 흐름

```mermaid
sequenceDiagram
    participant DC as Data Collector
    participant DP as Data Processor
    participant CA as Correlation Analyzer
    participant Viz as Visualizer
    participant IG as Insight Generator
    participant User as User
    
    DC->>DP: Raw Data (Price, Sentiment, Volume)
    DP->>DP: Normalize & Align Data
    DP->>CA: Processed Time Series Data
    CA->>CA: Calculate Correlations
    CA->>CA: Analyze Lag Effects
    CA->>CA: Test Statistical Significance
    CA->>Viz: Correlation Results
    Viz->>Viz: Generate Visualizations
    Viz->>IG: Visualization Data
    IG->>IG: Generate Insights
    IG->>User: Analysis Report & Insights
    User->>User: Make Investment Decisions
```

## 3. 상관관계 분석 구현

### 3.1 데이터 수집 및 전처리

```python
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import correlate
import logging

@dataclass
class TimeSeriesData:
    """시계열 데이터 모델"""
    symbol: str
    timestamps: List[datetime]
    prices: List[float]
    sentiment_scores: List[float]
    volumes: List[int]
    mentions: List[int]
    external_events: List[Dict] = field(default_factory=list)
    
    def to_dataframe(self) -> pd.DataFrame:
        """DataFrame으로 변환"""
        return pd.DataFrame({
            'timestamp': self.timestamps,
            'price': self.prices,
            'sentiment_score': self.sentiment_scores,
            'volume': self.volumes,
            'mentions': self.mentions
        }).set_index('timestamp')

class DataCollector:
    """데이터 수집기"""
    
    def __init__(self, data_sources: Dict[str, Any]):
        self.data_sources = data_sources
        self.logger = logging.getLogger(__name__)
    
    async def collect_data(self, symbol: str, start_date: datetime, 
                       end_date: datetime) -> TimeSeriesData:
        """시계열 데이터 수집"""
        try:
            # 병렬로 여러 데이터 소스에서 데이터 수집
            tasks = [
                self._collect_price_data(symbol, start_date, end_date),
                self._collect_sentiment_data(symbol, start_date, end_date),
                self._collect_volume_data(symbol, start_date, end_date),
                self._collect_external_events(symbol, start_date, end_date)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 결과 처리
            price_data = results[0] if not isinstance(results[0], Exception) else []
            sentiment_data = results[1] if not isinstance(results[1], Exception) else []
            volume_data = results[2] if not isinstance(results[2], Exception) else []
            external_events = results[3] if not isinstance(results[3], Exception) else []
            
            # 시계열 데이터 생성
            return self._create_time_series_data(
                symbol, price_data, sentiment_data, 
                volume_data, external_events, start_date, end_date
            )
            
        except Exception as e:
            self.logger.error(f"Error collecting data for {symbol}: {str(e)}")
            raise
    
    async def _collect_price_data(self, symbol: str, start_date: datetime, 
                             end_date: datetime) -> List[Tuple[datetime, float]]:
        """가격 데이터 수집"""
        # 실제 구현에서는 Yahoo Finance API 등에서 데이터 수집
        # 여기서는 시뮬레이션된 데이터 반환
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        prices = []
        
        base_price = 100.0
        for i, date in enumerate(dates):
            # 랜덤 워직임 생성
            change = np.random.normal(0, 2)
            price = base_price * (1 + change / 100)
            prices.append((date, price))
            base_price = price
        
        return prices
    
    async def _collect_sentiment_data(self, symbol: str, start_date: datetime, 
                                end_date: datetime) -> List[Tuple[datetime, float]]:
        """센티먼트 데이터 수집"""
        # 실제 구현에서는 Reddit, Twitter API에서 데이터 수집
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        sentiment_data = []
        
        for date in dates:
            # 시뮬레이션된 센티먼트 데이터 생성
            score = np.random.normal(0, 30)
            sentiment_data.append((date, score))
        
        return sentiment_data
    
    async def _collect_volume_data(self, symbol: str, start_date: datetime, 
                             end_date: datetime) -> List[Tuple[datetime, int]]:
        """거래량 데이터 수집"""
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        volume_data = []
        
        for date in dates:
            # 시뮬레이션된 거래량 데이터 생성
            volume = int(np.random.lognormal(10, 1))
            volume_data.append((date, volume))
        
        return volume_data
    
    async def _collect_external_events(self, symbol: str, start_date: datetime, 
                                 end_date: datetime) -> List[Dict]:
        """외부 이벤트 데이터 수집"""
        # 실제 구현에서는 뉴스, 보도서, 경제 발표 등에서 데이터 수집
        events = []
        
        # 시뮬레이션된 외부 이벤트
        event_dates = pd.date_range(start=start_date, end=end_date, freq='W')
        
        for event_date in event_dates:
            if np.random.random() > 0.8:  # 20% 확률로 이벤트 발생
                events.append({
                    'date': event_date,
                    'type': np.random.choice(['earnings', 'news', 'analyst_upgrade', 'regulatory']),
                    'title': f"{symbol} {np.random.choice(['beat', 'missed', 'raised'])} expectations",
                    'impact': np.random.choice(['positive', 'negative', 'neutral'])
                })
        
        return events
    
    def _create_time_series_data(self, symbol: str, price_data: List[Tuple[datetime, float]], 
                                sentiment_data: List[Tuple[datetime, float]], 
                                volume_data: List[Tuple[datetime, int]], 
                                external_events: List[Dict], start_date: datetime, 
                                end_date: datetime) -> TimeSeriesData:
        """시계열 데이터 생성"""
        # 날짜 범위 생성
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # 데이터 딕셔너리 생성
        price_dict = dict(price_data)
        sentiment_dict = dict(sentiment_data)
        volume_dict = dict(volume_data)
        
        timestamps = []
        prices = []
        sentiment_scores = []
        volumes = []
        mentions = []
        
        for date in date_range:
            timestamps.append(date)
            
            # 가격 데이터
            if date in price_dict:
                prices.append(price_dict[date])
            else:
                # 이전 가격으로 채우기
                if prices:
                    prices.append(prices[-1])
                else:
                    prices.append(100.0)
            
            # 센티먼트 데이터
            if date in sentiment_dict:
                sentiment_scores.append(sentiment_dict[date])
            else:
                sentiment_scores.append(0.0)
            
            # 거래량 데이터
            if date in volume_dict:
                volumes.append(volume_dict[date])
            else:
                volumes.append(0)
            
            # 언급량 (센티먼트와 관련)
            mentions.append(int(np.random.exponential(10)))
        
        return TimeSeriesData(
            symbol=symbol,
            timestamps=timestamps,
            prices=prices,
            sentiment_scores=sentiment_scores,
            volumes=volumes,
            mentions=mentions,
            external_events=external_events
        )

class DataProcessor:
    """데이터 전처리기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def normalize_data(self, data: TimeSeriesData) -> TimeSeriesData:
        """데이터 정규화"""
        try:
            df = data.to_dataframe()
            
            # 가격 데이터 정규화 (첫날을 100으로)
            if len(df) > 0 and df['price'].iloc[0] > 0:
                price_normalizer = 100.0 / df['price'].iloc[0]
                df['price_normalized'] = df['price'] * price_normalizer
            else:
                df['price_normalized'] = df['price']
            
            # 센티먼트 점수 정규화 (-100 ~ 100)
            df['sentiment_normalized'] = np.clip(df['sentiment_score'], -100, 100)
            
            # 거래량 정규화 (로그 스케일)
            df['volume_normalized'] = np.log1p(df['volume'])
            
            # 언급량 정규화 (로그 스케일)
            df['mentions_normalized'] = np.log1p(df['mentions'])
            
            # 이동 평균 계산 (7일, 30일)
            df['price_ma_7'] = df['price_normalized'].rolling(window=7).mean()
            df['price_ma_30'] = df['price_normalized'].rolling(window=30).mean()
            df['sentiment_ma_7'] = df['sentiment_normalized'].rolling(window=7).mean()
            df['sentiment_ma_30'] = df['sentiment_normalized'].rolling(window=30).mean()
            
            # 변화율 계산
            df['price_change'] = df['price_normalized'].pct_change()
            df['sentiment_change'] = df['sentiment_normalized'].diff()
            
            # 변동성 계산 (표준편차)
            df['price_volatility'] = df['price_change'].rolling(window=20).std()
            df['sentiment_volatility'] = df['sentiment_change'].rolling(window=20).std()
            
            # TimeSeriesData로 변환
            return TimeSeriesData(
                symbol=data.symbol,
                timestamps=data.timestamps,
                prices=df['price_normalized'].tolist(),
                sentiment_scores=df['sentiment_normalized'].tolist(),
                volumes=df['volume_normalized'].tolist(),
                mentions=df['mentions_normalized'].tolist(),
                external_events=data.external_events
            )
            
        except Exception as e:
            self.logger.error(f"Error normalizing data: {str(e)}")
            raise
    
    def align_time_series(self, data1: TimeSeriesData, data2: TimeSeriesData) -> Tuple[TimeSeriesData, TimeSeriesData]:
        """두 시계열 데이터 정렬"""
        try:
            df1 = data1.to_dataframe()
            df2 = data2.to_dataframe()
            
            # 공통 날짜 범위 찾기
            common_dates = df1.index.intersection(df2.index)
            
            if len(common_dates) == 0:
                self.logger.warning("No common dates found between time series")
                return data1, data2
            
            # 공통 날짜로 데이터 필터링
            df1_aligned = df1.loc[common_dates]
            df2_aligned = df2.loc[common_dates]
            
            # 정렬된 TimeSeriesData 생성
            aligned_data1 = TimeSeriesData(
                symbol=data1.symbol,
                timestamps=common_dates.tolist(),
                prices=df1_aligned['price'].tolist(),
                sentiment_scores=df1_aligned['sentiment_score'].tolist(),
                volumes=df1_aligned['volume'].tolist(),
                mentions=df1_aligned['mentions'].tolist(),
                external_events=data1.external_events
            )
            
            aligned_data2 = TimeSeriesData(
                symbol=data2.symbol,
                timestamps=common_dates.tolist(),
                prices=df2_aligned['price'].tolist(),
                sentiment_scores=df2_aligned['sentiment_score'].tolist(),
                volumes=df2_aligned['volume'].tolist(),
                mentions=df2_aligned['mentions'].tolist(),
                external_events=data2.external_events
            )
            
            return aligned_data1, aligned_data2
            
        except Exception as e:
            self.logger.error(f"Error aligning time series: {str(e)}")
            raise
    
    def extract_features(self, data: TimeSeriesData) -> Dict[str, List[float]]:
        """특징 추출"""
        try:
            df = data.to_dataframe()
            
            features = {}
            
            # 기술적 지표
            features['returns'] = df['price'].pct_change().fillna(0).tolist()
            features['log_returns'] = np.log(df['price'] / df['price'].shift(1)).fillna(0).tolist()
            features['volatility'] = df['price'].rolling(window=20).std().fillna(0).tolist()
            features['rsi'] = self._calculate_rsi(df['price']).tolist()
            
            # 센티먼트 관련 특징
            features['sentiment_ma'] = df['sentiment_score'].rolling(window=7).mean().fillna(0).tolist()
            features['sentiment_volatility'] = df['sentiment_score'].rolling(window=20).std().fillna(0).tolist()
            features['sentiment_momentum'] = df['sentiment_score'].diff().fillna(0).tolist()
            
            # 거래량 관련 특징
            features['volume_ma'] = df['volume'].rolling(window=7).mean().fillna(0).tolist()
            features['volume_ratio'] = (df['volume'] / df['volume'].rolling(window=30).mean()).fillna(1).tolist()
            
            # 언급량 관련 특징
            features['mentions_ma'] = df['mentions'].rolling(window=7).mean().fillna(0).tolist()
            features['mentions_ratio'] = (df['mentions'] / df['mentions'].rolling(window=30).mean()).fillna(1).tolist()
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error extracting features: {str(e)}")
            raise
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI(Relative Strength Index) 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = 100 - (100 / (1 + gain / loss))
        return rs.fillna(50)
```

### 3.2 상관관계 분석 엔진

```python
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import correlate
import logging

class CorrelationMethod(Enum):
    PEARSON = "pearson"
    SPEARMAN = "spearman"
    KENDALL = "kendall"
    CROSS_CORRELATION = "cross_correlation"
    GRANGER_CAUSALITY = "granger_causality"

@dataclass
class CorrelationResult:
    """상관관계 분석 결과"""
    symbol: str
    method: CorrelationMethod
    correlation_value: float
    p_value: float
    confidence_interval: Tuple[float, float]
    statistical_significance: bool
    effect_size: str
    sample_size: int
    time_lag: Optional[int] = None
    additional_metrics: Dict[str, Any] = field(default_factory=dict)

class CorrelationAnalyzer:
    """상관관계 분석기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_correlation(self, data1: TimeSeriesData, data2: TimeSeriesData, 
                           method: CorrelationMethod = CorrelationMethod.PEARSON,
                           time_lag: int = 0) -> CorrelationResult:
        """상관관계 계산"""
        try:
            # 데이터 정렬 및 특징 추출
            aligned_data1, aligned_data2 = self._prepare_data(data1, data2, time_lag)
            
            if method == CorrelationMethod.PEARSON:
                result = self._calculate_pearson_correlation(aligned_data1, aligned_data2)
            elif method == CorrelationMethod.SPEARMAN:
                result = self._calculate_spearman_correlation(aligned_data1, aligned_data2)
            elif method == CorrelationMethod.KENDALL:
                result = self._calculate_kendall_correlation(aligned_data1, aligned_data2)
            elif method == CorrelationMethod.CROSS_CORRELATION:
                result = self._calculate_cross_correlation(aligned_data1, aligned_data2)
            elif method == CorrelationMethod.GRANGER_CAUSALITY:
                result = self._calculate_granger_causality(aligned_data1, aligned_data2)
            else:
                raise ValueError(f"Unsupported correlation method: {method}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error calculating correlation: {str(e)}")
            raise
    
    def _prepare_data(self, data1: TimeSeriesData, data2: TimeSeriesData, 
                     time_lag: int = 0) -> Tuple[np.ndarray, np.ndarray]:
        """데이터 준비"""
        # 데이터 정렬
        processor = DataProcessor()
        aligned_data1, aligned_data2 = processor.align_time_series(data1, data2)
        
        # 시간 지연 적용
        if time_lag > 0:
            aligned_data2.prices = aligned_data2.prices[time_lag:]
            aligned_data2.sentiment_scores = aligned_data2.sentiment_scores[time_lag:]
            aligned_data2.volumes = aligned_data2.volumes[time_lag:]
            aligned_data2.mentions = aligned_data2.mentions[time_lag:]
            aligned_data2.timestamps = aligned_data2.timestamps[time_lag:]
        
        # 배열로 변환
        prices1 = np.array(aligned_data1.prices)
        prices2 = np.array(aligned_data2.prices)
        sentiments1 = np.array(aligned_data1.sentiment_scores)
        sentiments2 = np.array(aligned_data2.sentiment_scores)
        
        return prices1, sentiments2
    
    def _calculate_pearson_correlation(self, data1: np.ndarray, 
                                        data2: np.ndarray) -> CorrelationResult:
        """피어슨 상관계계 계산"""
        # NaN 값 제거
        mask = ~(np.isnan(data1) | np.isnan(data2))
        clean_data1 = data1[mask]
        clean_data2 = data2[mask]
        
        if len(clean_data1) < 2:
            return self._create_invalid_result()
        
        # 피어슨 상관계계 계산
        correlation, p_value = stats.pearsonr(clean_data1, clean_data2)
        
        # 신뢰 구간 계산
        n = len(clean_data1)
        fisher_z = np.arctanh(correlation) * np.sqrt(n - 3) / np.sqrt(1 - correlation**2)
        se = 1 / np.sqrt(n - 3)
        
        confidence_interval = (
            np.tanh(np.arctanh(correlation) - 1.96 * se),
            np.tanh(np.arctanh(correlation) + 1.96 * se)
        )
        
        # 효과 크기 계산
        effect_size = self._calculate_effect_size(correlation)
        
        return CorrelationResult(
            symbol="",  # 상위 레벨에서 설정
            method=CorrelationMethod.PEARSON,
            correlation_value=correlation,
            p_value=p_value,
            confidence_interval=confidence_interval,
            statistical_significance=p_value < 0.05,
            effect_size=effect_size,
            sample_size=n,
            additional_metrics={
                "fisher_z": fisher_z,
                "standard_error": se
            }
        )
    
    def _calculate_spearman_correlation(self, data1: np.ndarray, 
                                         data2: np.ndarray) -> CorrelationResult:
        """스피어만 상관계계 계산"""
        # NaN 값 제거
        mask = ~(np.isnan(data1) | np.isnan(data2))
        clean_data1 = data1[mask]
        clean_data2 = data2[mask]
        
        if len(clean_data1) < 2:
            return self._create_invalid_result()
        
        # 스피어만 상관계계 계산
        correlation, p_value = stats.spearmanr(clean_data1, clean_data2)
        
        # 효과 크기 계산
        effect_size = self._calculate_effect_size(correlation)
        
        return CorrelationResult(
            symbol="",  # 상위 레벨에서 설정
            method=CorrelationMethod.SPEARMAN,
            correlation_value=correlation,
            p_value=p_value,
            confidence_interval=(0, 0),  # 스피어만은 신뢰 구간 계산 복잡
            statistical_significance=p_value < 0.05,
            effect_size=effect_size,
            sample_size=len(clean_data1)
        )
    
    def _calculate_kendall_correlation(self, data1: np.ndarray, 
                                       data2: np.ndarray) -> CorrelationResult:
        """켄달 상관계계 계산"""
        # NaN 값 제거
        mask = ~(np.isnan(data1) | np.isnan(data2))
        clean_data1 = data1[mask]
        clean_data2 = data2[mask]
        
        if len(clean_data1) < 2:
            return self._create_invalid_result()
        
        # 켔달 타우 계산
        correlation, p_value = stats.kendalltau(clean_data1, clean_data2)
        
        # 효과 크기 계산
        effect_size = self._calculate_effect_size(correlation)
        
        return CorrelationResult(
            symbol="",  # 상위 레벨에서 설정
            method=CorrelationMethod.KENDALL,
            correlation_value=correlation,
            p_value=p_value,
            confidence_interval=(0, 0),  # 켔달 타우는 신뢰 구간 계산 복잡
            statistical_significance=p_value < 0.05,
            effect_size=effect_size,
            sample_size=len(clean_data1)
        )
    
    def _calculate_cross_correlation(self, data1: np.ndarray, 
                                      data2: np.ndarray) -> CorrelationResult:
        """교차 상관계 계산"""
        # NaN 값 제거
        mask = ~(np.isnan(data1) | np.isnan(data2))
        clean_data1 = data1[mask]
        clean_data2 = data2[mask]
        
        if len(clean_data1) < 2:
            return self._create_invalid_result()
        
        # 교차 상관계 계산
        correlation = correlate(clean_data1, clean_data2)
        max_corr_idx = np.argmax(np.abs(correlation))
        max_corr = correlation[max_corr_idx]
        time_lag = max_corr_idx - len(clean_data1) // 2
        
        # p-value 계산 (근사치)
        n = len(clean_data1)
        t_stat = max_corr * np.sqrt((n - 2) / (1 - max_corr**2))
        p_value = 2 * (1 - stats.t.cdf(t_stat, n - 2))
        
        # 효과 크기 계산
        effect_size = self._calculate_effect_size(max_corr)
        
        return CorrelationResult(
            symbol="",  # 상위 레벨에서 설정
            method=CorrelationMethod.CROSS_CORRELATION,
            correlation_value=max_corr,
            p_value=p_value,
            confidence_interval=(0, 0),  # 교차 상관계는 신뢰 구간 계산 복잡
            statistical_significance=p_value < 0.05,
            effect_size=effect_size,
            sample_size=n,
            time_lag=time_lag,
            additional_metrics={
                "cross_correlation_array": correlation.tolist(),
                "max_lag": time_lag
            }
        )
    
    def _calculate_granger_causality(self, data1: np.ndarray, 
                                      data2: np.ndarray) -> CorrelationResult:
        """그랜저 인과관계 분석"""
        # NaN 값 제거
        mask = ~(np.isnan(data1) | np.isnan(data2))
        clean_data1 = data1[mask]
        clean_data2 = data2[mask]
        
        if len(clean_data1) < 10:
            return self._create_invalid_result()
        
        # 그랜저 인과관계 분석 (단순화된 구현)
        # 실제 구현에서는 통계 라이브러리 사용 필요
        
        # 시차 지연 테스트 (0-5일)
        max_lag = 5
        f_stat = 0
        optimal_lag = 0
        
        for lag in range(max_lag + 1):
            if lag == 0:
                continue
            
            # 시차 지연 데이터 준비
            data1_lagged = clean_data1[:-lag]
            data2_lagged = clean_data2[lag:]
            
            # F-통계량 계산
            # 단순화된 구현: 데이터2의 시차 지연 버전으로 데이터1 예측
            mse = np.mean((data1_lagged - data2_lagged)**2)
            
            if mse < f_stat:
                f_stat = mse
                optimal_lag = lag
        
        # p-value 계산 (근사치)
        n = len(clean_data1)
        p_value = 1 - stats.f.cdf(f_stat, n-2, n-2)
        
        # 효과 크기 계산
        effect_size = "small" if optimal_lag == 0 else "medium"
        
        return CorrelationResult(
            symbol="",  # 상위 레벨에서 설정
            method=CorrelationMethod.GRANGER_CAUSALITY,
            correlation_value=1.0 / (1 + f_stat),  # 단순화된 상관계값
            p_value=p_value,
            confidence_interval=(0, 0),
            statistical_significance=p_value < 0.05,
            effect_size=effect_size,
            sample_size=n,
            time_lag=optimal_lag,
            additional_metrics={
                "f_statistic": f_stat,
                "optimal_lag": optimal_lag,
                "mse": mse
            }
        )
    
    def _calculate_effect_size(self, correlation: float) -> str:
        """효과 크기 계산"""
        abs_corr = abs(correlation)
        
        if abs_corr < 0.1:
            return "negligible"
        elif abs_corr < 0.3:
            return "small"
        elif abs_corr < 0.5:
            return "medium"
        elif abs_corr < 0.7:
            return "large"
        else:
            return "very large"
    
    def _create_invalid_result(self) -> CorrelationResult:
        """무효 결과 생성"""
        return CorrelationResult(
            symbol="",
            method=CorrelationMethod.PEARSON,
            correlation_value=0.0,
            p_value=1.0,
            confidence_interval=(0.0, 0.0),
            statistical_significance=False,
            effect_size="negligible",
            sample_size=0
        )
    
    def analyze_multiple_correlations(self, data: TimeSeriesData, 
                                     methods: List[CorrelationMethod] = None) -> Dict[str, List[CorrelationResult]]:
        """다중 상관관계 분석"""
        if methods is None:
            methods = [CorrelationMethod.PEARSON, CorrelationMethod.SPEARMAN, CorrelationMethod.CROSS_CORRELATION]
        
        results = {}
        
        # 가격-센티먼트 상관관계
        results['price_sentiment'] = [
            self.calculate_correlation(data, data, method) for method in methods
        ]
        
        # 가격-거래량 상관관계
        results['price_volume'] = [
            self.calculate_correlation(data, data, method) for method in methods
        ]
        
        # 가격-언급량 상관관계
        results['price_mentions'] = [
            self.calculate_correlation(data, data, method) for method in methods
        ]
        
        # 센티먼트-거래량 상관관계
        results['sentiment_volume'] = [
            self.calculate_correlation(data, data, method) for method in methods
        ]
        
        # 센티먼트-언급량 상관관계
        results['sentiment_mentions'] = [
            self.calculate_correlation(data, data, method) for method in methods
        ]
        
        return results
```

### 3.3 시각화 및 인사이트 생성

```python
from typing import Dict, List, Optional, Any
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

class CorrelationVisualizer:
    """상관관계 시각화기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def create_correlation_heatmap(self, results: Dict[str, List[CorrelationResult]]) -> go.Figure:
        """상관관계 히트맵 생성"""
        try:
            # 데이터 준비
            correlations = []
            methods = []
            pairs = []
            
            for pair, result_list in results.items():
                for result in result_list:
                    correlations.append(result.correlation_value)
                    methods.append(result.method.value)
                    pairs.append(pair)
            
            # 히트맵 데이터 생성
            heatmap_data = pd.DataFrame({
                'Correlation': correlations,
                'Method': methods,
                'Pair': pairs
            })
            
            # 히트맵 생성
            fig = go.Figure(data=go.Heatmap(
                z=heatmap_data['Correlation'],
                x=heatmap_data['Method'],
                y=heatmap_data['Pair'],
                colorscale='RdBu',
                text=heatmap_data['Correlation'],
                texttemplate="%{text:.3f}",
                textfont={"size": 10},
                hoveronginfo='x: %{x}<br>Correlation: %{z:.3f}'
            ))
            
            fig.update_layout(
                title='상관관계 분석 히트맵',
                xaxis_title='분석 방법',
                yaxis_title='데이터 쌍',
                width=800,
                height=600
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating correlation heatmap: {str(e)}")
            raise
    
    def create_time_series_overlay(self, data: TimeSeriesData, 
                                  correlation_result: CorrelationResult) -> go.Figure:
        """시계열 오버레이 차트 생성"""
        try:
            df = data.to_dataframe()
            
            # 서브플롯 생성
            fig = go.Figure()
            
            # 가격 차트 (주축)
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df['price'],
                mode='lines',
                name='가격',
                line=dict(color='blue', width=2),
                yaxis='y'
            ))
            
            # 센티먼트 차트 (보조축)
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df['sentiment_score'],
                mode='lines',
                name='센티먼트',
                line=dict(color='red', width=2),
                yaxis='y2'
            ))
            
            # 거래량 막대 그래프 (보조축2)
            fig.add_trace(go.Bar(
                x=df.index,
                y=df['volume'],
                name='거래량',
                marker_color='lightblue',
                opacity=0.3,
                yaxis='y3'
            ))
            
            # 레이아웃 업데이트
            fig.update_layout(
                title=f"{data.symbol} 상관관계 분석 (상관계: {correlation_result.correlation_value:.3f})",
                xaxis_title='날짜',
                yaxis=dict(
                    title='가격',
                    titlefont=dict(color='blue')
                ),
                yaxis2=dict(
                    title='센티먼트 점수',
                    titlefont=dict(color='red'),
                    overlaying='y',
                    side='right'
                ),
                yaxis3=dict(
                    title='거래량',
                    titlefont=dict(color='lightblue'),
                    overlaying='y',
                    side='right',
                    position=0.85
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                width=1000,
                height=600,
                template='plotly_white'
            )
            
            # 상관관계 정보 주석 추가
            fig.add_annotation(
                text=f"상관계계수: {correlation_result.correlation_value:.3f}<br>"
                     f"P-value: {correlation_result.p_value:.4f}<br>"
                     f"효과 크기: {correlation_result.effect_size}",
                xref="paper",
                yref="paper",
                x=0.02,
                y=0.98,
                showarrow=False,
                font=dict(size=12),
                bgcolor="white",
                bordercolor="black",
                borderwidth=1
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating time series overlay: {str(e)}")
            raise
    
    def create_lag_analysis_chart(self, data: TimeSeriesData, 
                                max_lag: int = 10) -> go.Figure:
        """시차 지연 분석 차트 생성"""
        try:
            df = data.to_dataframe()
            
            # 시차 지연별 상관계 계산
            correlations = []
            lags = list(range(max_lag + 1))
            
            for lag in lags:
                if lag == 0:
                    correlations.append(1.0)  # 자기 상관계
                else:
                    # 시차 지연 적용
                    shifted_sentiment = df['sentiment_score'].shift(lag)
                    correlation = df['price'].corr(shifted_sentiment)
                    correlations.append(correlation)
            
            # 차트 생성
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=lags,
                y=correlations,
                mode='lines+markers',
                name='상관계',
                line=dict(color='blue', width=2),
                marker=dict(size=8, color='red')
            ))
            
            # 최적 시차 지연 표시
            max_corr_lag = lags[np.argmax(np.abs(correlations[1:]))  # 0 제외
            max_corr_value = max(correlations[1:])  # 0 제외
            
            fig.add_annotation(
                x=max_corr_lag,
                y=max_corr_value,
                text=f"최적 시차: {max_corr_lag}일<br>상관계: {max_corr_value:.3f}",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
                arrowcolor="red"
            )
            
            fig.update_layout(
                title='시차 지연 분석',
                xaxis_title='시차 지연 (일)',
                yaxis_title='상관계계수',
                width=800,
                height=500
            )
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Error creating lag analysis chart: {str(e)}")
            raise

class InsightGenerator:
    """인사이트 생성기"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_insights(self, results: Dict[str, List[CorrelationResult]], 
                        data: TimeSeriesData) -> Dict[str, Any]:
        """인사이트 생성"""
        try:
            insights = {}
            
            # 주요 상관관계 분석
            price_sentiment_corr = self._get_best_correlation(results['price_sentiment'])
            price_volume_corr = self._get_best_correlation(results['price_volume'])
            
            insights['summary'] = {
                'price_sentiment_correlation': price_sentiment_corr.correlation_value,
                'price_volume_correlation': price_volume_corr.correlation_value,
                'sentiment_volume_correlation': self._get_best_correlation(results['sentiment_volume']).correlation_value,
                'most_significant_correlation': self._find_most_significant(results)
            }
            
            # 패턴 분석
            insights['patterns'] = self._analyze_patterns(results, data)
            
            # 추천사항 생성
            insights['recommendations'] = self._generate_recommendations(insights)
            
            # 리스크 평가
            insights['risk_assessment'] = self._assess_risk(insights, data)
            
            return insights
            
        except Exception as e:
            self.logger.error(f"Error generating insights: {str(e)}")
            raise
    
    def _get_best_correlation(self, results: List[CorrelationResult]) -> CorrelationResult:
        """가장 유의미 있는 상관관계 결과 선택"""
        # p-value가 가장 낮은 결과 선택
        valid_results = [r for r in results if r.sample_size > 0]
        
        if not valid_results:
            return CorrelationResult(
                correlation_value=0.0,
                p_value=1.0,
                statistical_significance=False
            )
        
        return min(valid_results, key=lambda x: x.p_value)
    
    def _find_most_significant(self, results: Dict[str, List[CorrelationResult]]) -> Dict[str, CorrelationResult]:
        """가장 통계적으로 유의미한 상관관계 찾기"""
        most_significant = {}
        
        for pair, result_list in results.items():
            best_result = self._get_best_correlation(result_list)
            most_significant[pair] = best_result
        
        return most_significant
    
    def _analyze_patterns(self, results: Dict[str, List[CorrelationResult]], 
                        data: TimeSeriesData) -> Dict[str, Any]:
        """패턴 분석"""
        patterns = {}
        
        # 상관관계 패턴 분석
        price_sentiment = self._get_best_correlation(results['price_sentiment'])
        
        if abs(price_sentiment.correlation_value) > 0.5:
            patterns['sentiment_price_alignment'] = {
                'type': 'positive_correlation',
                'strength': 'strong' if abs(price_sentiment.correlation_value) > 0.7 else 'moderate',
                'description': '센티먼트와 가격이 강한 양의 상관관계를 보입니다.'
            }
        elif abs(price_sentiment.correlation_value) < -0.5:
            patterns['sentiment_price_opposition'] = {
                'type': 'negative_correlation',
                'strength': 'strong' if abs(price_sentiment.correlation_value) > 0.7 else 'moderate',
                'description': '센티먼트와 가격이 강한 음의 상관관계를 보입니다.'
            }
        
        # 시차 지연 패턴 분석
        cross_corr = [r for r in results['price_sentiment'] 
                    if r.method == CorrelationMethod.CROSS_CORRELATION]
        
        if cross_corr:
            best_cross_corr = max(cross_corr, key=lambda x: abs(x.correlation_value))
            if best_cross_corr.time_lag > 0:
                patterns['sentiment_leads_price'] = {
                    'lag_days': best_cross_corr.time_lag,
                    'strength': abs(best_cross_corr.correlation_value),
                    'description': f'센티먼트 변화가 {best_cross_corr.time_lag}일 후 가격 변화에 선행합니다.'
                }
        
        return patterns
    
    def _generate_recommendations(self, insights: Dict[str, Any]) -> List[str]:
        """추천사항 생성"""
        recommendations = []
        
        summary = insights['summary']
        patterns = insights.get('patterns', {})
        
        # 상관관계 기반 추천
        if abs(summary['price_sentiment_correlation']) > 0.6:
            recommendations.append(
                "센티먼트 분석을 통해 주식 매매 타이밍을 고려해볼 수 있습니다."
            )
        elif abs(summary['price_sentiment_correlation']) < -0.6:
            recommendations.append(
                "센티먼트가 부정적일 때 주식 매도를 피하는 것이 좋을 수 있습니다."
            )
        
        # 패턴 기반 추천
        if 'sentiment_leads_price' in patterns:
            recommendations.append(
                f"센티먼트 변화를 주시하여 {patterns['sentiment_leads_price']['lag_days']}일 뒤의 주가 움직임을 예측해볼 수 있습니다."
            )
        
        # 일반적인 추천사항
        recommendations.append(
            "상관관계 분석 결과를 다른 기술적 분석 도구와 함께 종합적으로 검토하세요."
        )
        
        recommendations.append(
            "과거 데이터를 통해 현재 패턴이 미래에도 유지될지 검증해보세요."
        )
        
        return recommendations
    
    def _assess_risk(self, insights: Dict[str, Any], data: TimeSeriesData) -> Dict[str, Any]:
        """리스크 평가"""
        risk_factors = []
        risk_score = 0
        
        summary = insights['summary']
        
        # 상관관계 기반 리스크
        if abs(summary['price_sentiment_correlation']) > 0.7:
            risk_factors.append("높은 센티먼트-가격 상관관계")
            risk_score += 2
        
        # 변동성 기반 리스크
        df = data.to_dataframe()
        price_volatility = df['price'].rolling(window=20).std().mean()
        
        if price_volatility > df['price'].std() * 1.5:
            risk_factors.append("높은 가격 변동성")
            risk_score += 1
        
        # 최근 동향 기반 리스크
        recent_trend = df['price'].tail(10).mean() / df['price'].head(10).mean()
        
        if recent_trend < 0.95:
            risk_factors.append("하락하는 최근 동향")
            risk_score += 1
        
        # 리스크 등급 결정
        if risk_score >= 3:
            risk_level = "high"
        elif risk_score >= 2:
            risk_level = "medium"
        elif risk_score >= 1:
            risk_level = "low"
        else:
            risk_level = "very_low"
        
        return {
            'risk_factors': risk_factors,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'recommendation': self._get_risk_recommendation(risk_level)
        }
    
    def _get_risk_recommendation(self, risk_level: str) -> str:
        """리스크 등급별 추천사항"""
        recommendations = {
            "high": "높은 리스크 수준: 포트폴리오를 재조정하고, 손실을 최소화하세요.",
            "medium": "중간 리스크 수준: 분산 투자를 고려하고, 리스크 관리를 강화하세요.",
            "low": "낮은 리스크 수준: 현재 전략을 유지하되도록 모니터링하세요.",
            "very_low": "매우 낮은 리스크 수준: 현재 전략을 확장할 수 있습니다."
        }
        
        return recommendations.get(risk_level, "리스크 관리가 권장됩니다.")
```

## 4. 구현 계획

### 4.1 Phase 1: 기반 데이터 처리 (1주일)

#### 4.1.1 데이터 수집기 구현
- DataCollector 클래스 구현
- 다양한 데이터 소스에서 시계열 데이터 수집
- 데이터 정합 및 TimeSeriesData 모델 생성

#### 4.1.2 데이터 전처리기 구현
- DataProcessor 클래스 구현
- 데이터 정규화 및 정렬 기능
- 특징 추출 기능

### 4.2 Phase 2: 상관관계 분석 엔진 (1주일)

#### 4.2.1 CorrelationAnalyzer 구현
- 다양한 상관관계 분석 방법 구현
- 통계적 유의미성 검증
- 시차 지연 분석 기능

#### 4.2.2 분석 결과 모델링
- CorrelationResult 클래스 구현
- 다양한 메트릭 및 추가 정보 저장

### 4.3 Phase 3: 시각화 및 인사이트 (1주일)

#### 4.3.1 시각화기 구현
- CorrelationVisualizer 클래스 구현
- 상관관계 히트맵 생성
- 시계열 오버레이 차트 생성
- 시차 지연 분석 차트 생성

#### 4.3.2 인사이트 생성기 구현
- InsightGenerator 클래스 구현
- 패턴 분석 기능
- 리스크 평가 기능
- 추천사항 생성 기능

### 4.4 Phase 4: 통합 및 최적화 (1주일)

#### 4.4.1 통합 시스템 연동
- 기존 시스템과의 통합
- 실시간 상관관계 분석
- 사용자 인터페이스 연동

#### 4.4.2 성능 최적화
- 대용량 데이터 처리 최적화
- 계산 캐싱 구현
- 병렬 처리 최적화

## 5. 기술적 고려사항

### 5.1 통계적 유효성
1. **표본 크기**: 최소 30개 데이터 포인트 확보
2. **정상성 검증**: 데이터 정상성 가정 검증
3. **다중 비교 검정**: Bonferroni 보정 적용
4. **효과 크기**: Cohen's d 등 적절한 효과 크기 사용

### 5.2 계산 복잡도
1. **알고리즘**: O(n log n) 이하의 복잡도 목표
2. **메모리 관리**: 대용량 데이터의 효율적 처리
3. **병렬 처리**: NumPy, SciPy의 벡터화 연산 활용
4. **캐싱**: 반복 계산 결과 캐싱

### 5.3 데이터 품질
1. **결측치 처리**: 결측치, 이상치 제거
2. **이상치 탐지**: 통계적 방법으로 이상치 탐지
3. **데이터 보정**: 누락된 데이터 보정 메커니즘
4. **품질 점수**: 데이터 품질 지표 계산

### 5.4 해석 가능성
1. **시각화**: 직관적이고 이해하기 쉬운 시각화 제공
2. **인사이트**: 비전문가도 이해하기 쉬운 인사이트 생성
3. **상호작용**: 인터랙티브 차트 및 탐색 기능
4. **설명서**: 분석 방법 및 결과에 대한 상세한 설명

## 6. 성공 지표

### 6.1 기술적 지표
- 분석 처리 시간: 5초 이하 (30일 데이터)
- 상관관계 계산 정확도: 99% 이상
- 시각화 생성 시간: 3초 이하
- 메모리 사용량: 1GB 이하 (대용량 데이터)

### 6.2 분석 정확도 지표
- 통계적 유의미성: 95% 이상
- 시차 지연 정확도: 90% 이상
- 패턴 탐지 정확도: 85% 이상

### 6.3 사용자 경험 지표
- 인터페이스 응답 시간: 2초 이하
- 분석 이해도: 4.5/5.0 이상
- 인사이트 유용성: 4.0/5.0 이상

이 상관관계 분석 기능 구현 계획을 통해 주식 가격과 소셜 센티먼트 간의 관계를 과학적으로 분석하고, 사용자에게 투자 결정에 도움을 줄 수 있는 강력한 도구를 제공할 수 있습니다.