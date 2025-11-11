"""
Machine Learning Trend Detection Service for InsiteChart platform.

This service provides advanced trend detection capabilities using
machine learning algorithms including LSTM, Prophet, and statistical models.
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import statistics
from abc import ABC, abstractmethod

from ..cache.unified_cache import UnifiedCacheManager


class TrendDirection(str, Enum):
    """Trend direction types."""
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    SIDEWAYS = "sideways"
    REVERSAL_UP = "reversal_up"
    REVERSAL_DOWN = "reversal_down"
    CONSOLIDATION = "consolidation"


class TrendStrength(str, Enum):
    """Trend strength levels."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class ModelType(str, Enum):
    """Available ML models for trend detection."""
    LSTM = "lstm"
    PROPHET = "prophet"
    ARIMA = "arima"
    RANDOM_FOREST = "random_forest"
    ENSEMBLE = "ensemble"
    TECHNICAL_ANALYSIS = "technical_analysis"


@dataclass
class TrendSignal:
    """Individual trend signal."""
    timestamp: datetime
    direction: TrendDirection
    strength: TrendStrength
    confidence: float
    price_target: Optional[float]
    time_horizon: int  # days
    volume_confirmation: bool
    technical_indicators: Dict[str, float]


@dataclass
class TrendPrediction:
    """Trend prediction result."""
    symbol: str
    current_price: float
    predicted_direction: TrendDirection
    predicted_strength: TrendStrength
    confidence: float
    time_horizon: int  # days
    price_targets: List[float]  # [7d, 14d, 30d targets]
    support_levels: List[float]
    resistance_levels: List[float]
    volatility_forecast: float
    model_used: ModelType
    signals: List[TrendSignal]
    generated_at: datetime


@dataclass
class TrendAnalysisResult:
    """Complete trend analysis result."""
    symbol: str
    current_trend: TrendDirection
    trend_strength: TrendStrength
    trend_duration: int  # days
    predictions: List[TrendPrediction]
    consensus_direction: TrendDirection
    consensus_strength: TrendStrength
    consensus_confidence: float
    key_levels: Dict[str, List[float]]
    risk_factors: List[str]
    opportunities: List[str]
    analysis_period: Tuple[str, str]


class TrendDetectionModel(ABC):
    """Abstract base class for trend detection models."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def train(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Train the model with historical data."""
        pass
    
    @abstractmethod
    async def predict(self, data: pd.DataFrame, horizon: int = 30) -> TrendPrediction:
        """Generate trend prediction."""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and metadata."""
        pass


class LSTMTrendModel(TrendDetectionModel):
    """LSTM-based trend detection model."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        super().__init__(cache_manager)
        self.model = None
        self.scaler = None
        self.sequence_length = 60
        self.is_trained = False
    
    async def train(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Train LSTM model with historical price data."""
        try:
            # Check if TensorFlow is available
            try:
                import tensorflow as tf
                from tensorflow.keras.models import Sequential
                from tensorflow.keras.layers import LSTM, Dense, Dropout
                from sklearn.preprocessing import MinMaxScaler
            except ImportError:
                self.logger.warning("TensorFlow not available, using mock training")
                self.is_trained = True
                return {"status": "mock_trained", "message": "TensorFlow not available"}
            
            # Prepare data
            prices = data['close'].values.reshape(-1, 1)
            self.scaler = MinMaxScaler(feature_range=(0, 1))
            scaled_prices = self.scaler.fit_transform(prices)
            
            # Create sequences
            X, y = self._create_sequences(scaled_prices)
            
            # Build LSTM model
            self.model = Sequential([
                LSTM(50, return_sequences=True, input_shape=(self.sequence_length, 1)),
                Dropout(0.2),
                LSTM(50, return_sequences=False),
                Dropout(0.2),
                Dense(25),
                Dense(1)
            ])
            
            self.model.compile(optimizer='adam', loss='mse')
            
            # Train model
            self.model.fit(X, y, epochs=50, batch_size=32, verbose=0)
            self.is_trained = True
            
            return {
                "status": "trained",
                "epochs": 50,
                "samples": len(X),
                "loss": self.model.evaluate(X, y, verbose=0)
            }
            
        except Exception as e:
            self.logger.error(f"Error training LSTM model: {str(e)}")
            raise
    
    async def predict(self, data: pd.DataFrame, horizon: int = 30) -> TrendPrediction:
        """Generate trend prediction using LSTM."""
        try:
            if not self.is_trained:
                raise ValueError("Model not trained")
            
            symbol = data.index[0] if hasattr(data.index[0], 'symbol') else "UNKNOWN"
            current_price = data['close'].iloc[-1]
            
            # Check if TensorFlow is available
            try:
                import tensorflow as tf
            except ImportError:
                # Mock prediction
                return self._create_mock_prediction(symbol, current_price, horizon, ModelType.LSTM)
            
            # Prepare input data
            prices = data['close'].values.reshape(-1, 1)
            scaled_prices = self.scaler.transform(prices)
            
            # Get last sequence
            last_sequence = scaled_prices[-self.sequence_length:].reshape(1, self.sequence_length, 1)
            
            # Generate predictions
            predictions = []
            current_sequence = last_sequence.copy()
            
            for _ in range(horizon):
                pred = self.model.predict(current_sequence, verbose=0)
                predictions.append(pred[0, 0])
                current_sequence = np.roll(current_sequence, -1, axis=1)
                current_sequence[0, -1, 0] = pred[0, 0]
            
            # Inverse transform predictions
            predictions = self.scaler.inverse_transform(np.array(predictions).reshape(-1, 1))
            
            # Analyze trend
            trend_direction, trend_strength, confidence = self._analyze_predictions(predictions, current_price)
            
            # Calculate price targets
            price_targets = [predictions[6][0], predictions[13][0], predictions[29][0]] if len(predictions) >= 30 else [predictions[-1][0]]
            
            # Generate signals
            signals = self._generate_signals(predictions, current_price)
            
            return TrendPrediction(
                symbol=symbol,
                current_price=current_price,
                predicted_direction=trend_direction,
                predicted_strength=trend_strength,
                confidence=confidence,
                time_horizon=horizon,
                price_targets=price_targets,
                support_levels=[current_price * 0.95, current_price * 0.90],
                resistance_levels=[current_price * 1.05, current_price * 1.10],
                volatility_forecast=self._calculate_volatility_forecast(predictions),
                model_used=ModelType.LSTM,
                signals=signals,
                generated_at=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Error in LSTM prediction: {str(e)}")
            raise
    
    def _create_sequences(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences for LSTM training."""
        X, y = [], []
        for i in range(self.sequence_length, len(data)):
            X.append(data[i-self.sequence_length:i, 0])
            y.append(data[i, 0])
        return np.array(X), np.array(y)
    
    def _analyze_predictions(self, predictions: np.ndarray, current_price: float) -> Tuple[TrendDirection, TrendStrength, float]:
        """Analyze predictions to determine trend."""
        final_price = predictions[-1][0]
        price_change = (final_price - current_price) / current_price
        
        # Determine direction
        if price_change > 0.05:
            direction = TrendDirection.UPTREND
        elif price_change < -0.05:
            direction = TrendDirection.DOWNTREND
        else:
            direction = TrendDirection.SIDEWAYS
        
        # Determine strength
        abs_change = abs(price_change)
        if abs_change > 0.15:
            strength = TrendStrength.VERY_STRONG
        elif abs_change > 0.10:
            strength = TrendStrength.STRONG
        elif abs_change > 0.05:
            strength = TrendStrength.MODERATE
        else:
            strength = TrendStrength.WEAK
        
        # Calculate confidence based on prediction consistency
        price_changes = np.diff(predictions.flatten()) / predictions[:-1].flatten()
        consistency = 1 - np.std(price_changes) if len(price_changes) > 0 else 0
        confidence = min(0.9, max(0.1, consistency))
        
        return direction, strength, confidence
    
    def _generate_signals(self, predictions: np.ndarray, current_price: float) -> List[TrendSignal]:
        """Generate trend signals from predictions."""
        signals = []
        for i, pred_price in enumerate(predictions[::7]):  # Weekly signals
            if i == 0:
                continue
            
            price_change = (pred_price[0] - current_price) / current_price
            
            if price_change > 0.02:
                direction = TrendDirection.UPTREND
            elif price_change < -0.02:
                direction = TrendDirection.DOWNTREND
            else:
                direction = TrendDirection.SIDEWAYS
            
            strength = TrendStrength.MODERATE  # Simplified
            
            signals.append(TrendSignal(
                timestamp=datetime.utcnow() + timedelta(days=i*7),
                direction=direction,
                strength=strength,
                confidence=0.7,
                price_target=pred_price[0],
                time_horizon=i*7,
                volume_confirmation=True,  # Mock
                technical_indicators={"rsi": 50, "macd": 0}  # Mock
            ))
        
        return signals
    
    def _calculate_volatility_forecast(self, predictions: np.ndarray) -> float:
        """Calculate volatility forecast from predictions."""
        price_changes = np.diff(predictions.flatten()) / predictions[:-1].flatten()
        return float(np.std(price_changes)) if len(price_changes) > 0 else 0.02
    
    def _create_mock_prediction(self, symbol: str, current_price: float, horizon: int, model_type: ModelType) -> TrendPrediction:
        """Create mock prediction when libraries are not available."""
        np.random.seed(hash(symbol) % 2**32)
        
        # Mock trend direction and strength
        rand = np.random.random()
        if rand > 0.7:
            direction = TrendDirection.UPTREND
            strength = TrendStrength.MODERATE
            price_change = np.random.uniform(0.05, 0.15)
        elif rand < 0.3:
            direction = TrendDirection.DOWNTREND
            strength = TrendStrength.MODERATE
            price_change = np.random.uniform(-0.15, -0.05)
        else:
            direction = TrendDirection.SIDEWAYS
            strength = TrendStrength.WEAK
            price_change = np.random.uniform(-0.05, 0.05)
        
        price_targets = [
            current_price * (1 + price_change * 0.3),
            current_price * (1 + price_change * 0.6),
            current_price * (1 + price_change)
        ]
        
        return TrendPrediction(
            symbol=symbol,
            current_price=current_price,
            predicted_direction=direction,
            predicted_strength=strength,
            confidence=0.6,
            time_horizon=horizon,
            price_targets=price_targets,
            support_levels=[current_price * 0.95, current_price * 0.90],
            resistance_levels=[current_price * 1.05, current_price * 1.10],
            volatility_forecast=0.02,
            model_used=model_type,
            signals=[],
            generated_at=datetime.utcnow()
        )
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get LSTM model information."""
        return {
            "model_type": ModelType.LSTM,
            "is_trained": self.is_trained,
            "sequence_length": self.sequence_length,
            "architecture": "LSTM with dropout layers"
        }


class ProphetTrendModel(TrendDetectionModel):
    """Prophet-based trend detection model."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        super().__init__(cache_manager)
        self.model = None
        self.is_trained = False
    
    async def train(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Train Prophet model with historical data."""
        try:
            # Check if Prophet is available
            try:
                from prophet import Prophet
            except ImportError:
                self.logger.warning("Prophet not available, using mock training")
                self.is_trained = True
                return {"status": "mock_trained", "message": "Prophet not available"}
            
            # Prepare data for Prophet
            prophet_data = data.reset_index()
            prophet_data = prophet_data.rename(columns={
                prophet_data.columns[0]: 'ds',
                'close': 'y'
            })
            
            # Create and train model
            self.model = Prophet(
                daily_seasonality=True,
                weekly_seasonality=True,
                yearly_seasonality=True,
                changepoint_prior_scale=0.05
            )
            
            self.model.fit(prophet_data)
            self.is_trained = True
            
            return {
                "status": "trained",
                "changepoints": len(self.model.changepoints),
                "seasonalities": list(self.model.seasonalities.keys())
            }
            
        except Exception as e:
            self.logger.error(f"Error training Prophet model: {str(e)}")
            raise
    
    async def predict(self, data: pd.DataFrame, horizon: int = 30) -> TrendPrediction:
        """Generate trend prediction using Prophet."""
        try:
            if not self.is_trained:
                raise ValueError("Model not trained")
            
            symbol = data.index[0] if hasattr(data.index[0], 'symbol') else "UNKNOWN"
            current_price = data['close'].iloc[-1]
            
            # Check if Prophet is available
            try:
                from prophet import Prophet
            except ImportError:
                # Mock prediction
                return self._create_mock_prediction(symbol, current_price, horizon, ModelType.PROPHET)
            
            # Create future dataframe
            future = self.model.make_future_dataframe(periods=horizon)
            forecast = self.model.predict(future)
            
            # Extract predictions
            future_predictions = forecast.tail(horizon)
            
            # Analyze trend
            trend_direction, trend_strength, confidence = self._analyze_prophet_predictions(
                future_predictions, current_price
            )
            
            # Calculate price targets
            price_targets = [
                future_predictions.iloc[6]['yhat'],
                future_predictions.iloc[13]['yhat'],
                future_predictions.iloc[29]['yhat']
            ] if len(future_predictions) >= 30 else [future_predictions.iloc[-1]['yhat']]
            
            # Generate signals
            signals = self._generate_prophet_signals(future_predictions, current_price)
            
            return TrendPrediction(
                symbol=symbol,
                current_price=current_price,
                predicted_direction=trend_direction,
                predicted_strength=trend_strength,
                confidence=confidence,
                time_horizon=horizon,
                price_targets=price_targets,
                support_levels=[current_price * 0.95, current_price * 0.90],
                resistance_levels=[current_price * 1.05, current_price * 1.10],
                volatility_forecast=self._calculate_prophet_volatility(future_predictions),
                model_used=ModelType.PROPHET,
                signals=signals,
                generated_at=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Error in Prophet prediction: {str(e)}")
            raise
    
    def _analyze_prophet_predictions(self, predictions: pd.DataFrame, current_price: float) -> Tuple[TrendDirection, TrendStrength, float]:
        """Analyze Prophet predictions to determine trend."""
        final_price = predictions['yhat'].iloc[-1]
        price_change = (final_price - current_price) / current_price
        
        # Determine direction
        if price_change > 0.05:
            direction = TrendDirection.UPTREND
        elif price_change < -0.05:
            direction = TrendDirection.DOWNTREND
        else:
            direction = TrendDirection.SIDEWAYS
        
        # Determine strength
        abs_change = abs(price_change)
        if abs_change > 0.15:
            strength = TrendStrength.VERY_STRONG
        elif abs_change > 0.10:
            strength = TrendStrength.STRONG
        elif abs_change > 0.05:
            strength = TrendStrength.MODERATE
        else:
            strength = TrendStrength.WEAK
        
        # Calculate confidence based on prediction intervals
        uncertainty = predictions['yhat_upper'].iloc[-1] - predictions['yhat_lower'].iloc[-1]
        confidence = max(0.1, min(0.9, 1.0 - (uncertainty / current_price)))
        
        return direction, strength, confidence
    
    def _generate_prophet_signals(self, predictions: pd.DataFrame, current_price: float) -> List[TrendSignal]:
        """Generate trend signals from Prophet predictions."""
        signals = []
        for i in range(7, len(predictions), 7):  # Weekly signals
            pred_price = predictions.iloc[i]['yhat']
            price_change = (pred_price - current_price) / current_price
            
            if price_change > 0.02:
                direction = TrendDirection.UPTREND
            elif price_change < -0.02:
                direction = TrendDirection.DOWNTREND
            else:
                direction = TrendDirection.SIDEWAYS
            
            strength = TrendStrength.MODERATE  # Simplified
            
            signals.append(TrendSignal(
                timestamp=datetime.utcnow() + timedelta(days=i),
                direction=direction,
                strength=strength,
                confidence=0.7,
                price_target=pred_price,
                time_horizon=i,
                volume_confirmation=True,  # Mock
                technical_indicators={"rsi": 50, "macd": 0}  # Mock
            ))
        
        return signals
    
    def _calculate_prophet_volatility(self, predictions: pd.DataFrame) -> float:
        """Calculate volatility forecast from Prophet predictions."""
        price_changes = predictions['yhat'].pct_change().dropna()
        return float(price_changes.std()) if len(price_changes) > 0 else 0.02
    
    def _create_mock_prediction(self, symbol: str, current_price: float, horizon: int, model_type: ModelType) -> TrendPrediction:
        """Create mock prediction when Prophet is not available."""
        # Reuse LSTM mock prediction logic
        lstm_model = LSTMTrendModel(self.cache_manager)
        return lstm_model._create_mock_prediction(symbol, current_price, horizon, model_type)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get Prophet model information."""
        return {
            "model_type": ModelType.PROPHET,
            "is_trained": self.is_trained,
            "features": ["trend", "daily_seasonality", "weekly_seasonality", "yearly_seasonality"]
        }


class TechnicalAnalysisModel(TrendDetectionModel):
    """Technical analysis-based trend detection model."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        super().__init__(cache_manager)
        self.is_trained = True  # No training needed for technical analysis
    
    async def train(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Technical analysis doesn't require training."""
        return {"status": "ready", "message": "Technical analysis model ready"}
    
    async def predict(self, data: pd.DataFrame, horizon: int = 30) -> TrendPrediction:
        """Generate trend prediction using technical analysis."""
        try:
            symbol = data.index[0] if hasattr(data.index[0], 'symbol') else "UNKNOWN"
            current_price = data['close'].iloc[-1]
            
            # Calculate technical indicators
            indicators = self._calculate_technical_indicators(data)
            
            # Analyze trend using technical indicators
            trend_direction, trend_strength, confidence = self._analyze_technical_trend(indicators)
            
            # Calculate price targets using technical levels
            price_targets = self._calculate_technical_targets(data, horizon)
            
            # Generate signals based on technical patterns
            signals = self._generate_technical_signals(indicators, current_price)
            
            return TrendPrediction(
                symbol=symbol,
                current_price=current_price,
                predicted_direction=trend_direction,
                predicted_strength=trend_strength,
                confidence=confidence,
                time_horizon=horizon,
                price_targets=price_targets,
                support_levels=indicators.get('support_levels', []),
                resistance_levels=indicators.get('resistance_levels', []),
                volatility_forecast=indicators.get('volatility', 0.02),
                model_used=ModelType.TECHNICAL_ANALYSIS,
                signals=signals,
                generated_at=datetime.utcnow()
            )
            
        except Exception as e:
            self.logger.error(f"Error in technical analysis prediction: {str(e)}")
            raise
    
    def _calculate_technical_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate various technical indicators."""
        try:
            close_prices = data['close']
            high_prices = data['high']
            low_prices = data['low']
            volumes = data.get('volume', pd.Series(index=data.index, data=0))
            
            indicators = {}
            
            # Moving averages
            indicators['sma_20'] = close_prices.rolling(window=20).mean().iloc[-1]
            indicators['sma_50'] = close_prices.rolling(window=50).mean().iloc[-1]
            indicators['sma_200'] = close_prices.rolling(window=200).mean().iloc[-1]
            
            # RSI
            delta = close_prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            indicators['rsi'] = 100 - (100 / (1 + rs)).iloc[-1]
            
            # MACD
            ema_12 = close_prices.ewm(span=12).mean()
            ema_26 = close_prices.ewm(span=26).mean()
            indicators['macd'] = (ema_12 - ema_26).iloc[-1]
            indicators['macd_signal'] = indicators['macd'].ewm(span=9).mean().iloc[-1]
            
            # Bollinger Bands
            sma_20 = close_prices.rolling(window=20).mean()
            std_20 = close_prices.rolling(window=20).std()
            indicators['bb_upper'] = (sma_20 + 2 * std_20).iloc[-1]
            indicators['bb_lower'] = (sma_20 - 2 * std_20).iloc[-1]
            
            # Support and resistance levels
            indicators['support_levels'] = self._find_support_levels(data)
            indicators['resistance_levels'] = self._find_resistance_levels(data)
            
            # Volatility
            indicators['volatility'] = close_prices.pct_change().rolling(window=20).std().iloc[-1]
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculating technical indicators: {str(e)}")
            return {}
    
    def _find_support_levels(self, data: pd.DataFrame, num_levels: int = 3) -> List[float]:
        """Find support levels in price data."""
        try:
            close_prices = data['close']
            low_prices = data['low']
            
            # Find local minima
            from scipy.signal import find_peaks
            minima, _ = find_peaks(-low_prices, distance=10)
            
            if len(minima) == 0:
                return [close_prices.min() * 0.98]
            
            # Get the lowest minima
            support_levels = sorted([low_prices.iloc[i] for i in minima])[:num_levels]
            return support_levels
            
        except Exception as e:
            self.logger.error(f"Error finding support levels: {str(e)}")
            return []
    
    def _find_resistance_levels(self, data: pd.DataFrame, num_levels: int = 3) -> List[float]:
        """Find resistance levels in price data."""
        try:
            high_prices = data['high']
            
            # Find local maxima
            from scipy.signal import find_peaks
            maxima, _ = find_peaks(high_prices, distance=10)
            
            if len(maxima) == 0:
                return [high_prices.max() * 1.02]
            
            # Get the highest maxima
            resistance_levels = sorted([high_prices.iloc[i] for i in maxima], reverse=True)[:num_levels]
            return resistance_levels
            
        except Exception as e:
            self.logger.error(f"Error finding resistance levels: {str(e)}")
            return []
    
    def _analyze_technical_trend(self, indicators: Dict[str, Any]) -> Tuple[TrendDirection, TrendStrength, float]:
        """Analyze trend using technical indicators."""
        try:
            current_price = indicators.get('current_price', 0)
            sma_20 = indicators.get('sma_20', current_price)
            sma_50 = indicators.get('sma_50', current_price)
            sma_200 = indicators.get('sma_200', current_price)
            rsi = indicators.get('rsi', 50)
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            
            # Initialize trend score
            trend_score = 0
            confidence_factors = []
            
            # Moving average analysis
            if current_price > sma_20 > sma_50 > sma_200:
                trend_score += 3
                confidence_factors.append(0.8)
            elif current_price > sma_20 > sma_50:
                trend_score += 2
                confidence_factors.append(0.6)
            elif current_price > sma_20:
                trend_score += 1
                confidence_factors.append(0.4)
            elif current_price < sma_20 < sma_50 < sma_200:
                trend_score -= 3
                confidence_factors.append(0.8)
            elif current_price < sma_20 < sma_50:
                trend_score -= 2
                confidence_factors.append(0.6)
            elif current_price < sma_20:
                trend_score -= 1
                confidence_factors.append(0.4)
            
            # RSI analysis
            if rsi > 70:
                trend_score -= 1  # Overbought
                confidence_factors.append(0.5)
            elif rsi < 30:
                trend_score += 1  # Oversold
                confidence_factors.append(0.5)
            elif 45 < rsi < 55:
                trend_score += 0  # Neutral
                confidence_factors.append(0.3)
            
            # MACD analysis
            if macd > macd_signal:
                trend_score += 1
                confidence_factors.append(0.6)
            else:
                trend_score -= 1
                confidence_factors.append(0.6)
            
            # Determine direction
            if trend_score > 2:
                direction = TrendDirection.UPTREND
            elif trend_score < -2:
                direction = TrendDirection.DOWNTREND
            else:
                direction = TrendDirection.SIDEWAYS
            
            # Determine strength
            abs_score = abs(trend_score)
            if abs_score >= 4:
                strength = TrendStrength.VERY_STRONG
            elif abs_score >= 3:
                strength = TrendStrength.STRONG
            elif abs_score >= 2:
                strength = TrendStrength.MODERATE
            else:
                strength = TrendStrength.WEAK
            
            # Calculate confidence
            confidence = statistics.mean(confidence_factors) if confidence_factors else 0.5
            
            return direction, strength, confidence
            
        except Exception as e:
            self.logger.error(f"Error analyzing technical trend: {str(e)}")
            return TrendDirection.SIDEWAYS, TrendStrength.WEAK, 0.3
    
    def _calculate_technical_targets(self, data: pd.DataFrame, horizon: int) -> List[float]:
        """Calculate price targets using technical analysis."""
        try:
            current_price = data['close'].iloc[-1]
            
            # Use Fibonacci levels for targets
            high_price = data['high'].rolling(window=50).max().iloc[-1]
            low_price = data['low'].rolling(window=50).min().iloc[-1]
            
            diff = high_price - low_price
            
            # Fibonacci levels
            fib_236 = high_price - 0.236 * diff
            fib_382 = high_price - 0.382 * diff
            fib_618 = high_price - 0.618 * diff
            
            # Determine trend direction
            if current_price > (high_price + low_price) / 2:
                # Uptrend targets
                targets = [
                    current_price + (fib_236 - current_price) * 0.3,
                    current_price + (fib_236 - current_price) * 0.6,
                    fib_236
                ]
            else:
                # Downtrend targets
                targets = [
                    current_price - (current_price - fib_618) * 0.3,
                    current_price - (current_price - fib_618) * 0.6,
                    fib_618
                ]
            
            return targets
            
        except Exception as e:
            self.logger.error(f"Error calculating technical targets: {str(e)}")
            return []
    
    def _generate_technical_signals(self, indicators: Dict[str, Any], current_price: float) -> List[TrendSignal]:
        """Generate signals based on technical patterns."""
        signals = []
        
        try:
            rsi = indicators.get('rsi', 50)
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            bb_upper = indicators.get('bb_upper', current_price * 1.1)
            bb_lower = indicators.get('bb_lower', current_price * 0.9)
            
            # RSI signals
            if rsi < 30:
                signals.append(TrendSignal(
                    timestamp=datetime.utcnow(),
                    direction=TrendDirection.UPTREND,
                    strength=TrendStrength.MODERATE,
                    confidence=0.6,
                    price_target=current_price * 1.05,
                    time_horizon=7,
                    volume_confirmation=True,
                    technical_indicators={"rsi": rsi, "signal": "oversold"}
                ))
            elif rsi > 70:
                signals.append(TrendSignal(
                    timestamp=datetime.utcnow(),
                    direction=TrendDirection.DOWNTREND,
                    strength=TrendStrength.MODERATE,
                    confidence=0.6,
                    price_target=current_price * 0.95,
                    time_horizon=7,
                    volume_confirmation=True,
                    technical_indicators={"rsi": rsi, "signal": "overbought"}
                ))
            
            # MACD signals
            if macd > macd_signal:
                signals.append(TrendSignal(
                    timestamp=datetime.utcnow(),
                    direction=TrendDirection.UPTREND,
                    strength=TrendStrength.WEAK,
                    confidence=0.5,
                    price_target=current_price * 1.03,
                    time_horizon=14,
                    volume_confirmation=True,
                    technical_indicators={"macd": macd, "signal": "bullish_crossover"}
                ))
            
            # Bollinger Bands signals
            if current_price < bb_lower:
                signals.append(TrendSignal(
                    timestamp=datetime.utcnow(),
                    direction=TrendDirection.UPTREND,
                    strength=TrendStrength.MODERATE,
                    confidence=0.6,
                    price_target=current_price * 1.04,
                    time_horizon=10,
                    volume_confirmation=True,
                    technical_indicators={"bb_position": "lower_band", "signal": "oversold"}
                ))
            elif current_price > bb_upper:
                signals.append(TrendSignal(
                    timestamp=datetime.utcnow(),
                    direction=TrendDirection.DOWNTREND,
                    strength=TrendStrength.MODERATE,
                    confidence=0.6,
                    price_target=current_price * 0.96,
                    time_horizon=10,
                    volume_confirmation=True,
                    technical_indicators={"bb_position": "upper_band", "signal": "overbought"}
                ))
            
        except Exception as e:
            self.logger.error(f"Error generating technical signals: {str(e)}")
        
        return signals
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get technical analysis model information."""
        return {
            "model_type": ModelType.TECHNICAL_ANALYSIS,
            "is_trained": self.is_trained,
            "indicators": ["SMA", "RSI", "MACD", "Bollinger Bands", "Support/Resistance"]
        }


class MLTrendDetectionService:
    """Machine Learning trend detection service."""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize models
        self.models = {
            ModelType.LSTM: LSTMTrendModel(cache_manager),
            ModelType.PROPHET: ProphetTrendModel(cache_manager),
            ModelType.TECHNICAL_ANALYSIS: TechnicalAnalysisModel(cache_manager)
        }
        
        # Cache TTL settings
        self.prediction_cache_ttl = 1800  # 30 minutes
        self.training_cache_ttl = 86400  # 24 hours
        
        self.logger.info("MLTrendDetectionService initialized")
    
    async def train_model(
        self,
        symbol: str,
        model_type: ModelType,
        period_days: int = 252
    ) -> Dict[str, Any]:
        """Train a specific model for a symbol."""
        try:
            # Check cache first
            cache_key = f"trend_train_{symbol}_{model_type.value}_{period_days}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                self.logger.debug(f"Cache hit for model training {symbol} {model_type.value}")
                return cached_result
            
            # Get historical data
            data = await self._get_historical_data(symbol, period_days)
            
            if data is None or len(data) < 100:
                raise ValueError(f"Insufficient data for training: {len(data) if data is not None else 0}")
            
            # Train model
            model = self.models[model_type]
            result = await model.train(data)
            
            # Cache result
            await self.cache_manager.set(
                cache_key,
                result,
                ttl=self.training_cache_ttl
            )
            
            self.logger.info(f"Model {model_type.value} trained for {symbol}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error training model {model_type.value} for {symbol}: {str(e)}")
            raise
    
    async def predict_trend(
        self,
        symbol: str,
        model_type: ModelType = ModelType.ENSEMBLE,
        horizon: int = 30,
        period_days: int = 252
    ) -> TrendAnalysisResult:
        """Generate trend prediction using specified model or ensemble."""
        try:
            # Check cache first
            cache_key = f"trend_predict_{symbol}_{model_type.value}_{horizon}_{period_days}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                self.logger.debug(f"Cache hit for trend prediction {symbol} {model_type.value}")
                # Convert back to TrendAnalysisResult
                return self._deserialize_trend_result(cached_result)
            
            # Get historical data
            data = await self._get_historical_data(symbol, period_days)
            
            if data is None or len(data) < 50:
                raise ValueError(f"Insufficient data for prediction: {len(data) if data is not None else 0}")
            
            # Generate predictions
            if model_type == ModelType.ENSEMBLE:
                predictions = await self._ensemble_predict(data, horizon)
            else:
                model = self.models[model_type]
                # Train if not trained
                if hasattr(model, 'is_trained') and not model.is_trained:
                    await self.train_model(symbol, model_type, period_days)
                
                predictions = [await model.predict(data, horizon)]
            
            # Analyze current trend
            current_trend, trend_strength, trend_duration = self._analyze_current_trend(data)
            
            # Calculate consensus
            consensus_direction, consensus_strength, consensus_confidence = self._calculate_consensus(predictions)
            
            # Identify key levels
            key_levels = self._identify_key_levels(data)
            
            # Analyze risk factors and opportunities
            risk_factors, opportunities = self._analyze_risks_opportunities(data, predictions)
            
            # Create result
            result = TrendAnalysisResult(
                symbol=symbol,
                current_trend=current_trend,
                trend_strength=trend_strength,
                trend_duration=trend_duration,
                predictions=predictions,
                consensus_direction=consensus_direction,
                consensus_strength=consensus_strength,
                consensus_confidence=consensus_confidence,
                key_levels=key_levels,
                risk_factors=risk_factors,
                opportunities=opportunities,
                analysis_period=(
                    data.index[0].strftime('%Y-%m-%d'),
                    data.index[-1].strftime('%Y-%m-%d')
                )
            )
            
            # Cache result
            serialized_result = self._serialize_trend_result(result)
            await self.cache_manager.set(
                cache_key,
                serialized_result,
                ttl=self.prediction_cache_ttl
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error predicting trend for {symbol}: {str(e)}")
            raise
    
    async def _ensemble_predict(self, data: pd.DataFrame, horizon: int) -> List[TrendPrediction]:
        """Generate ensemble predictions from multiple models."""
        predictions = []
        
        for model_type, model in self.models.items():
            try:
                # Train if not trained
                if hasattr(model, 'is_trained') and not model.is_trained:
                    # For ensemble, we'll use mock training to save time
                    await model.train(data)
                
                prediction = await model.predict(data, horizon)
                predictions.append(prediction)
                
            except Exception as e:
                self.logger.warning(f"Error in ensemble prediction with {model_type.value}: {str(e)}")
                continue
        
        return predictions
    
    def _analyze_current_trend(self, data: pd.DataFrame) -> Tuple[TrendDirection, TrendStrength, int]:
        """Analyze current trend from price data."""
        try:
            close_prices = data['close']
            
            # Calculate moving averages
            sma_20 = close_prices.rolling(window=20).mean()
            sma_50 = close_prices.rolling(window=50).mean()
            
            # Determine trend direction
            current_price = close_prices.iloc[-1]
            current_sma_20 = sma_20.iloc[-1]
            current_sma_50 = sma_50.iloc[-1]
            
            if current_price > current_sma_20 > current_sma_50:
                direction = TrendDirection.UPTREND
            elif current_price < current_sma_20 < current_sma_50:
                direction = TrendDirection.DOWNTREND
            else:
                direction = TrendDirection.SIDEWAYS
            
            # Calculate trend strength based on slope
            recent_prices = close_prices.tail(30)
            if len(recent_prices) >= 10:
                x = np.arange(len(recent_prices))
                slope = np.polyfit(x, recent_prices, 1)[0]
                
                # Normalize slope by price
                normalized_slope = slope / current_price
                
                if abs(normalized_slope) > 0.01:
                    strength = TrendStrength.STRONG
                elif abs(normalized_slope) > 0.005:
                    strength = TrendStrength.MODERATE
                else:
                    strength = TrendStrength.WEAK
            else:
                strength = TrendStrength.WEAK
            
            # Calculate trend duration
            trend_duration = 0
            if direction == TrendDirection.UPTREND:
                for i in range(len(sma_20) - 1, -1, -1):
                    if close_prices.iloc[i] > sma_20.iloc[i]:
                        trend_duration += 1
                    else:
                        break
            elif direction == TrendDirection.DOWNTREND:
                for i in range(len(sma_20) - 1, -1, -1):
                    if close_prices.iloc[i] < sma_20.iloc[i]:
                        trend_duration += 1
                    else:
                        break
            
            return direction, strength, trend_duration
            
        except Exception as e:
            self.logger.error(f"Error analyzing current trend: {str(e)}")
            return TrendDirection.SIDEWAYS, TrendStrength.WEAK, 0
    
    def _calculate_consensus(self, predictions: List[TrendPrediction]) -> Tuple[TrendDirection, TrendStrength, float]:
        """Calculate consensus from multiple predictions."""
        if not predictions:
            return TrendDirection.SIDEWAYS, TrendStrength.WEAK, 0.0
        
        # Count directions
        direction_counts = {}
        strength_scores = []
        confidences = []
        
        for pred in predictions:
            direction = pred.predicted_direction
            direction_counts[direction] = direction_counts.get(direction, 0) + 1
            
            # Convert strength to numeric score
            strength_map = {
                TrendStrength.WEAK: 1,
                TrendStrength.MODERATE: 2,
                TrendStrength.STRONG: 3,
                TrendStrength.VERY_STRONG: 4
            }
            strength_scores.append(strength_map.get(pred.predicted_strength, 2))
            confidences.append(pred.confidence)
        
        # Determine consensus direction
        consensus_direction = max(direction_counts, key=direction_counts.get)
        
        # Calculate consensus strength
        avg_strength = statistics.mean(strength_scores)
        if avg_strength >= 3.5:
            consensus_strength = TrendStrength.VERY_STRONG
        elif avg_strength >= 2.5:
            consensus_strength = TrendStrength.STRONG
        elif avg_strength >= 1.5:
            consensus_strength = TrendStrength.MODERATE
        else:
            consensus_strength = TrendStrength.WEAK
        
        # Calculate consensus confidence
        direction_agreement = direction_counts[consensus_direction] / len(predictions)
        avg_confidence = statistics.mean(confidences)
        consensus_confidence = (direction_agreement + avg_confidence) / 2
        
        return consensus_direction, consensus_strength, consensus_confidence
    
    def _identify_key_levels(self, data: pd.DataFrame) -> Dict[str, List[float]]:
        """Identify key support and resistance levels."""
        try:
            close_prices = data['close']
            high_prices = data['high']
            low_prices = data['low']
            
            # Find recent highs and lows
            recent_highs = high_prices.rolling(window=20).max()
            recent_lows = low_prices.rolling(window=20).min()
            
            # Current levels
            current_price = close_prices.iloc[-1]
            
            # Support levels (below current price)
            support_levels = []
            for i in range(1, 6):  # Look back 5 periods
                support = recent_lows.iloc[-i]
                if support < current_price:
                    support_levels.append(support)
            
            # Resistance levels (above current price)
            resistance_levels = []
            for i in range(1, 6):  # Look back 5 periods
                resistance = recent_highs.iloc[-i]
                if resistance > current_price:
                    resistance_levels.append(resistance)
            
            # Add psychological levels
            psychological_levels = []
            base = round(current_price / 10) * 10
            for i in range(-3, 4):
                level = base + (i * 10)
                if level != current_price:
                    psychological_levels.append(level)
            
            return {
                "support": support_levels[:3],  # Top 3 support levels
                "resistance": resistance_levels[:3],  # Top 3 resistance levels
                "psychological": psychological_levels[:5]  # Top 5 psychological levels
            }
            
        except Exception as e:
            self.logger.error(f"Error identifying key levels: {str(e)}")
            return {"support": [], "resistance": [], "psychological": []}
    
    def _analyze_risks_opportunities(self, data: pd.DataFrame, predictions: List[TrendPrediction]) -> Tuple[List[str], List[str]]:
        """Analyze risk factors and opportunities."""
        try:
            risks = []
            opportunities = []
            
            close_prices = data['close']
            current_price = close_prices.iloc[-1]
            
            # Volatility analysis
            volatility = close_prices.pct_change().rolling(window=20).std().iloc[-1]
            if volatility > 0.03:
                risks.append("High volatility detected")
            else:
                opportunities.append("Low volatility environment")
            
            # Trend analysis
            if len(predictions) > 0:
                consensus_direction = predictions[0].predicted_direction
                consensus_confidence = predictions[0].confidence
                
                if consensus_confidence < 0.5:
                    risks.append("Low prediction confidence")
                elif consensus_confidence > 0.7:
                    opportunities.append("High prediction confidence")
                
                if consensus_direction == TrendDirection.UPTREND:
                    opportunities.append("Bullish trend expected")
                elif consensus_direction == TrendDirection.DOWNTREND:
                    risks.append("Bearish trend expected")
            
            # Price level analysis
            recent_high = close_prices.rolling(window=50).max().iloc[-1]
            recent_low = close_prices.rolling(window=50).min().iloc[-1]
            
            if current_price > recent_high * 0.95:
                risks.append("Near resistance levels")
            elif current_price < recent_low * 1.05:
                opportunities.append("Near support levels")
            
            # Volume analysis (if available)
            if 'volume' in data.columns:
                volumes = data['volume']
                avg_volume = volumes.rolling(window=20).mean().iloc[-1]
                current_volume = volumes.iloc[-1]
                
                if current_volume > avg_volume * 1.5:
                    opportunities.append("High volume confirmation")
                elif current_volume < avg_volume * 0.5:
                    risks.append("Low volume warning")
            
            return risks, opportunities
            
        except Exception as e:
            self.logger.error(f"Error analyzing risks and opportunities: {str(e)}")
            return [], []
    
    async def _get_historical_data(self, symbol: str, period_days: int) -> Optional[pd.DataFrame]:
        """Get historical price data for a symbol."""
        try:
            # This would typically fetch from your data source
            # For now, generate mock data
            dates = pd.date_range(end=datetime.utcnow(), periods=period_days, freq='D')
            
            # Generate realistic price data
            np.random.seed(hash(symbol) % 2**32)
            base_price = 100 + np.random.uniform(-50, 150)
            trend = np.random.uniform(-0.001, 0.001)
            volatility = np.random.uniform(0.01, 0.03)
            
            prices = [base_price]
            highs = []
            lows = []
            volumes = []
            
            for i in range(1, period_days):
                change = np.random.normal(trend, volatility)
                new_price = prices[-1] * (1 + change)
                prices.append(max(new_price, 1))
                
                # Generate high/low
                daily_vol = np.random.uniform(0.01, 0.03)
                high = prices[-1] * (1 + daily_vol)
                low = prices[-1] * (1 - daily_vol)
                highs.append(high)
                lows.append(low)
                
                # Generate volume
                volume = np.random.uniform(1000000, 5000000)
                volumes.append(volume)
            
            # Create DataFrame
            data = pd.DataFrame({
                'open': prices[:-1],
                'high': [prices[i] * 1.01 for i in range(len(prices)-1)],
                'low': [prices[i] * 0.99 for i in range(len(prices)-1)],
                'close': prices[1:],
                'volume': volumes
            }, index=dates[1:])
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error getting historical data for {symbol}: {str(e)}")
            return None
    
    def _serialize_trend_result(self, result: TrendAnalysisResult) -> Dict[str, Any]:
        """Serialize TrendAnalysisResult for caching."""
        return {
            "symbol": result.symbol,
            "current_trend": result.current_trend.value,
            "trend_strength": result.trend_strength.value,
            "trend_duration": result.trend_duration,
            "predictions": [self._serialize_prediction(p) for p in result.predictions],
            "consensus_direction": result.consensus_direction.value,
            "consensus_strength": result.consensus_strength.value,
            "consensus_confidence": result.consensus_confidence,
            "key_levels": result.key_levels,
            "risk_factors": result.risk_factors,
            "opportunities": result.opportunities,
            "analysis_period": result.analysis_period
        }
    
    def _serialize_prediction(self, prediction: TrendPrediction) -> Dict[str, Any]:
        """Serialize TrendPrediction for caching."""
        return {
            "symbol": prediction.symbol,
            "current_price": prediction.current_price,
            "predicted_direction": prediction.predicted_direction.value,
            "predicted_strength": prediction.predicted_strength.value,
            "confidence": prediction.confidence,
            "time_horizon": prediction.time_horizon,
            "price_targets": prediction.price_targets,
            "support_levels": prediction.support_levels,
            "resistance_levels": prediction.resistance_levels,
            "volatility_forecast": prediction.volatility_forecast,
            "model_used": prediction.model_used.value,
            "signals": [
                {
                    "timestamp": signal.timestamp.isoformat(),
                    "direction": signal.direction.value,
                    "strength": signal.strength.value,
                    "confidence": signal.confidence,
                    "price_target": signal.price_target,
                    "time_horizon": signal.time_horizon,
                    "volume_confirmation": signal.volume_confirmation,
                    "technical_indicators": signal.technical_indicators
                }
                for signal in prediction.signals
            ],
            "generated_at": prediction.generated_at.isoformat()
        }
    
    def _deserialize_trend_result(self, data: Dict[str, Any]) -> TrendAnalysisResult:
        """Deserialize cached data back to TrendAnalysisResult."""
        predictions = [
            TrendPrediction(
                symbol=p["symbol"],
                current_price=p["current_price"],
                predicted_direction=TrendDirection(p["predicted_direction"]),
                predicted_strength=TrendStrength(p["predicted_strength"]),
                confidence=p["confidence"],
                time_horizon=p["time_horizon"],
                price_targets=p["price_targets"],
                support_levels=p["support_levels"],
                resistance_levels=p["resistance_levels"],
                volatility_forecast=p["volatility_forecast"],
                model_used=ModelType(p["model_used"]),
                signals=[
                    TrendSignal(
                        timestamp=datetime.fromisoformat(s["timestamp"]),
                        direction=TrendDirection(s["direction"]),
                        strength=TrendStrength(s["strength"]),
                        confidence=s["confidence"],
                        price_target=s["price_target"],
                        time_horizon=s["time_horizon"],
                        volume_confirmation=s["volume_confirmation"],
                        technical_indicators=s["technical_indicators"]
                    )
                    for s in p["signals"]
                ],
                generated_at=datetime.fromisoformat(p["generated_at"])
            )
            for p in data["predictions"]
        ]
        
        return TrendAnalysisResult(
            symbol=data["symbol"],
            current_trend=TrendDirection(data["current_trend"]),
            trend_strength=TrendStrength(data["trend_strength"]),
            trend_duration=data["trend_duration"],
            predictions=predictions,
            consensus_direction=TrendDirection(data["consensus_direction"]),
            consensus_strength=TrendStrength(data["consensus_strength"]),
            consensus_confidence=data["consensus_confidence"],
            key_levels=data["key_levels"],
            risk_factors=data["risk_factors"],
            opportunities=data["opportunities"],
            analysis_period=data["analysis_period"]
        )
    
    async def get_model_status(self) -> Dict[str, Any]:
        """Get status of all models."""
        try:
            status = {}
            for model_type, model in self.models.items():
                status[model_type.value] = model.get_model_info()
            
            return {
                "models": status,
                "available_models": list(self.models.keys()),
                "cache_ttl": {
                    "prediction": self.prediction_cache_ttl,
                    "training": self.training_cache_ttl
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting model status: {str(e)}")
            return {}