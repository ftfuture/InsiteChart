"""
Locust performance testing file for InsiteChart API.

This module defines performance tests for all major API endpoints
including stock data, sentiment analysis, real-time notifications,
and other core features.
"""

from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask
import json
import random
import time
from datetime import datetime, timedelta
import uuid

# Test data
SAMPLE_STOCKS = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'V', 'WMT']
SAMPLE_CURRENCIES = ['USD', 'EUR', 'GBP', 'JPY', 'KRW', 'CNY', 'CAD', 'AUD']
SAMPLE_CRYPTOS = ['BTC', 'ETH', 'ADA', 'SOL', 'DOT', 'MATIC', 'LINK', 'UNI']

class InsiteChartUser(HttpUser):
    """
    Simulates different types of users accessing the InsiteChart platform.
    """
    
    wait_time = between(1, 5)
    
    def on_start(self):
        """Called when a simulated user starts."""
        # Generate unique user ID
        self.user_id = str(uuid.uuid4())
        
        # Login to get authentication token
        self.login()
        
        # Initialize user preferences
        self.preferences = {
            'watchlist': random.sample(SAMPLE_STOCKS, k=5),
            'currency': random.choice(SAMPLE_CURRENCIES),
            'theme': random.choice(['light', 'dark']),
            'notifications_enabled': random.choice([True, False])
        }
        
        # Track user session
        self.session_start = time.time()
        self.request_count = 0
        
    def login(self):
        """Authenticate user and store token."""
        try:
            # Try to login with test credentials
            response = self.client.post(
                "/api/v1/auth/login",
                json={
                    "email": f"testuser_{self.user_id[:8]}@insitechart.com",
                    "password": "testpassword123"
                },
                catch_response=True
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'access_token' in data:
                    self.token = data['access_token']
                    self.headers = {
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json"
                    }
                    self.client.headers.update(self.headers)
                else:
                    # Create new user if login fails
                    self.create_user()
            else:
                self.create_user()
                
        except Exception as e:
            print(f"Login failed: {e}")
            self.create_user()
    
    def create_user(self):
        """Create a new user account."""
        try:
            response = self.client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"testuser_{self.user_id[:8]}@insitechart.com",
                    "password": "testpassword123",
                    "full_name": f"Test User {self.user_id[:8]}",
                    "preferences": self.preferences
                },
                catch_response=True
            )
            
            if response.status_code == 201:
                data = response.json()
                if 'access_token' in data:
                    self.token = data['access_token']
                    self.headers = {
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json"
                    }
                    self.client.headers.update(self.headers)
                    
        except Exception as e:
            print(f"User creation failed: {e}")
    
    @task(20)
    def get_stock_data(self):
        """Fetch stock data for random symbols."""
        symbol = random.choice(SAMPLE_STOCKS)
        
        with self.client.get(
            f"/api/v1/stocks/{symbol}",
            catch_response=True,
            name="/api/v1/stocks/[symbol]"
        ) as response:
            if response.status_code == 200:
                response.success()
                self.request_count += 1
            else:
                response.failure(f"Stock data request failed: {response.status_code}")
    
    @task(15)
    def get_stock_history(self):
        """Fetch historical stock data."""
        symbol = random.choice(SAMPLE_STOCKS)
        period = random.choice(['1d', '1w', '1m', '3m', '6m', '1y'])
        
        with self.client.get(
            f"/api/v1/stocks/{symbol}/history?period={period}",
            catch_response=True,
            name="/api/v1/stocks/[symbol]/history"
        ) as response:
            if response.status_code == 200:
                response.success()
                self.request_count += 1
            else:
                response.failure(f"Stock history request failed: {response.status_code}")
    
    @task(10)
    def get_sentiment_analysis(self):
        """Fetch sentiment analysis for stocks."""
        symbol = random.choice(SAMPLE_STOCKS)
        
        with self.client.get(
            f"/api/v1/sentiment/stock/{symbol}",
            catch_response=True,
            name="/api/v1/sentiment/stock/[symbol]"
        ) as response:
            if response.status_code == 200:
                response.success()
                self.request_count += 1
            else:
                response.failure(f"Sentiment analysis request failed: {response.status_code}")
    
    @task(8)
    def get_correlation_analysis(self):
        """Fetch correlation analysis between stocks."""
        symbols = random.sample(SAMPLE_STOCKS, k=2)
        
        with self.client.get(
            f"/api/v1/correlation/stocks?symbols={','.join(symbols)}",
            catch_response=True,
            name="/api/v1/correlation/stocks"
        ) as response:
            if response.status_code == 200:
                response.success()
                self.request_count += 1
            else:
                response.failure(f"Correlation analysis request failed: {response.status_code}")
    
    @task(5)
    def get_ml_trends(self):
        """Fetch ML-based trend predictions."""
        symbol = random.choice(SAMPLE_STOCKS)
        
        with self.client.get(
            f"/api/v1/ml-trends/predict/{symbol}",
            catch_response=True,
            name="/api/v1/ml-trends/predict/[symbol]"
        ) as response:
            if response.status_code == 200:
                response.success()
                self.request_count += 1
            else:
                response.failure(f"ML trends request failed: {response.status_code}")
    
    @task(5)
    def get_watchlist(self):
        """Fetch user's watchlist."""
        with self.client.get(
            "/api/v1/stocks/watchlist",
            catch_response=True,
            name="/api/v1/stocks/watchlist"
        ) as response:
            if response.status_code == 200:
                response.success()
                self.request_count += 1
            else:
                response.failure(f"Watchlist request failed: {response.status_code}")
    
    @task(3)
    def add_to_watchlist(self):
        """Add stock to watchlist."""
        symbol = random.choice(SAMPLE_STOCKS)
        
        with self.client.post(
            "/api/v1/stocks/watchlist/add",
            json={"symbol": symbol},
            catch_response=True,
            name="/api/v1/stocks/watchlist/add"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
                self.request_count += 1
            else:
                response.failure(f"Add to watchlist failed: {response.status_code}")
    
    @task(3)
    def get_notifications(self):
        """Fetch user notifications."""
        with self.client.get(
            "/api/v1/notifications",
            catch_response=True,
            name="/api/v1/notifications"
        ) as response:
            if response.status_code == 200:
                response.success()
                self.request_count += 1
            else:
                response.failure(f"Notifications request failed: {response.status_code}")
    
    @task(2)
    def create_notification_rule(self):
        """Create a notification rule."""
        symbol = random.choice(SAMPLE_STOCKS)
        rule_type = random.choice(['price_above', 'price_below', 'sentiment_change'])
        
        with self.client.post(
            "/api/v1/notifications/rules",
            json={
                "symbol": symbol,
                "rule_type": rule_type,
                "threshold": random.uniform(100, 1000),
                "enabled": True
            },
            catch_response=True,
            name="/api/v1/notifications/rules"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
                self.request_count += 1
            else:
                response.failure(f"Create notification rule failed: {response.status_code}")
    
    @task(2)
    def get_market_overview(self):
        """Fetch market overview data."""
        with self.client.get(
            "/api/v1/stocks/market/overview",
            catch_response=True,
            name="/api/v1/stocks/market/overview"
        ) as response:
            if response.status_code == 200:
                response.success()
                self.request_count += 1
            else:
                response.failure(f"Market overview request failed: {response.status_code}")
    
    @task(2)
    def search_stocks(self):
        """Search for stocks."""
        query = random.choice(['Apple', 'Google', 'Microsoft', 'Amazon', 'Tesla'])
        
        with self.client.get(
            f"/api/v1/stocks/search?q={query}",
            catch_response=True,
            name="/api/v1/stocks/search"
        ) as response:
            if response.status_code == 200:
                response.success()
                self.request_count += 1
            else:
                response.failure(f"Stock search failed: {response.status_code}")
    
    @task(1)
    def get_user_profile(self):
        """Fetch user profile."""
        with self.client.get(
            "/api/v1/auth/profile",
            catch_response=True,
            name="/api/v1/auth/profile"
        ) as response:
            if response.status_code == 200:
                response.success()
                self.request_count += 1
            else:
                response.failure(f"User profile request failed: {response.status_code}")
    
    @task(1)
    def update_user_preferences(self):
        """Update user preferences."""
        new_preferences = {
            "watchlist": random.sample(SAMPLE_STOCKS, k=5),
            "currency": random.choice(SAMPLE_CURRENCIES),
            "theme": random.choice(['light', 'dark']),
            "notifications_enabled": random.choice([True, False])
        }
        
        with self.client.put(
            "/api/v1/auth/preferences",
            json=new_preferences,
            catch_response=True,
            name="/api/v1/auth/preferences"
        ) as response:
            if response.status_code == 200:
                response.success()
                self.request_count += 1
                self.preferences = new_preferences
            else:
                response.failure(f"Update preferences failed: {response.status_code}")
    
    @task(1)
    def get_system_health(self):
        """Check system health."""
        with self.client.get(
            "/health",
            catch_response=True,
            name="/health"
        ) as response:
            if response.status_code == 200:
                response.success()
                self.request_count += 1
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(1)
    def get_performance_metrics(self):
        """Fetch performance metrics (admin only)."""
        # Only attempt if user has admin privileges
        if hasattr(self, 'is_admin') and self.is_admin:
            with self.client.get(
                "/api/v1/monitoring/metrics",
                catch_response=True,
                name="/api/v1/monitoring/metrics"
            ) as response:
                if response.status_code == 200:
                    response.success()
                    self.request_count += 1
                else:
                    response.failure(f"Performance metrics request failed: {response.status_code}")


class PowerUser(InsiteChartUser):
    """
    Simulates a power user with more frequent and intensive usage patterns.
    """
    
    wait_time = between(0.5, 3)
    
    @task(30)
    def get_stock_data(self):
        """Power users check stock data more frequently."""
        super().get_stock_data()
    
    @task(20)
    def get_real_time_data(self):
        """Fetch real-time stock data."""
        symbol = random.choice(SAMPLE_STOCKS)
        
        with self.client.get(
            f"/api/v1/stocks/{symbol}/realtime",
            catch_response=True,
            name="/api/v1/stocks/[symbol]/realtime"
        ) as response:
            if response.status_code == 200:
                response.success()
                self.request_count += 1
            else:
                response.failure(f"Real-time data request failed: {response.status_code}")
    
    @task(15)
    def get_advanced_analytics(self):
        """Fetch advanced analytics data."""
        symbol = random.choice(SAMPLE_STOCKS)
        
        with self.client.get(
            f"/api/v1/analytics/advanced/{symbol}",
            catch_response=True,
            name="/api/v1/analytics/advanced/[symbol]"
        ) as response:
            if response.status_code == 200:
                response.success()
                self.request_count += 1
            else:
                response.failure(f"Advanced analytics request failed: {response.status_code}")


class CasualUser(InsiteChartUser):
    """
    Simulates a casual user with less frequent usage patterns.
    """
    
    wait_time = between(5, 15)
    
    @task(10)
    def get_stock_data(self):
        """Casual users check stock data less frequently."""
        super().get_stock_data()
    
    @task(5)
    def get_market_overview(self):
        """Casual users prefer market overview."""
        super().get_market_overview()
    
    @task(3)
    def search_stocks(self):
        """Casual users search for stocks occasionally."""
        super().search_stocks()


# Event handlers for performance monitoring
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """
    Called for each request to collect performance metrics.
    """
    if exception:
        print(f"Request to {name} failed with exception: {exception}")
    else:
        # Log slow requests
        if response_time > 2000:  # 2 seconds
            print(f"Slow request: {name} took {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when a test starts."""
    print("Performance test started")
    print(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when a test stops."""
    print("Performance test completed")
    
    # Print summary statistics
    stats = environment.stats
    
    print("\n=== Performance Test Summary ===")
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Median response time: {stats.total.median_response_time:.2f}ms")
    print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"Requests per second: {stats.total.current_rps:.2f}")
    
    # Print slowest endpoints
    print("\n=== Slowest Endpoints ===")
    sorted_stats = sorted(stats.entries.items(), key=lambda x: x[1].avg_response_time, reverse=True)
    for name, stats in sorted_stats[:5]:
        print(f"{name}: {stats.avg_response_time:.2f}ms avg")


# Custom weight classes for different user types
class UserWeights:
    """Defines user weight distribution for realistic load testing."""
    
    @staticmethod
    def get_weighted_users():
        """Return weighted user distribution."""
        return {
            InsiteChartUser: 70,  # 70% regular users
            PowerUser: 20,       # 20% power users
            CasualUser: 10       # 10% casual users
        }
