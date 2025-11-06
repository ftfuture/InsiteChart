# 단계별 구현 계획

## 1. 개요

본 문서는 주식 차트 분석 애플리케이션의 종합 구현 로드맵을 바탕으로, 각 단계별 상세한 구현 계획을 제시합니다. 각 단계별 구체적인 작업 항목, 기술적 세부사항, 검증 기준, 그리고 단계 간 의존성을 명확히 정의합니다.

## 2. 1단계: 핵심 아키텍처 전환 (4-6주)

### 2.1 개요

**목표**: 단일 모놀리식 Streamlit 애플리케이션을 마이크로서비스 아키텍처로 전환

**핵심 성과**:
- API Gateway를 통한 모든 요청 처리
- 서비스별 분리 및 독립적인 배포 가능
- 데이터베이스 분리 및 마이그레이션 완료

### 2.2 상세 작업 계획

#### 2.2.1 API Gateway 구현 (1-2주)

**작업 항목**:
```yaml
API_Gateway_Setup:
  기술_스택:
    - Kong Gateway 3.x
    - Kong Admin API
    - Kong Plugin Manager
  
  구성_요소:
    - 라우팅 규칙 정의
    - 로드 밸런싱 설정
    - SSL/TLS 종료
    - 기본 인증 미들웨어
    - 속도 제한(rate limiting)
    - 요청/응답 로깅
  
  구현_단계:
    1. Kong Gateway 설치 및 설정
    2. 서비스 및 라우트 정의
    3. 플러그인 설정 및 테스트
    4. 모니터링 대시보드 구성
  
  검증_기준:
    - 모든 API 요청이 Gateway를 통해 라우팅
    - 속도 제한 정상 작동
    - SSL 인증서 적용
    - 모니터링 데이터 수집
```

**API Gateway 라우팅 설정**:
```yaml
# kong-config.yml
services:
  - name: stock-service
    url: http://stock-service:3001
    plugins:
      - name: rate-limiting
        config:
          minute: 100
          hour: 1000
    routes:
      - name: stock-api
        paths: ["/api/stocks"]
        methods: ["GET", "POST"]

  - name: user-service
    url: http://user-service:3002
    plugins:
      - name: jwt
      config:
        secret_is_base64: false
    routes:
      - name: user-api
        paths: ["/api/users"]
        methods: ["GET", "POST", "PUT", "DELETE"]

  - name: portfolio-service
    url: http://portfolio-service:3003
    plugins:
      - name: acl
        config:
          whitelist: ["admin", "user"]
    routes:
      - name: portfolio-api
        paths: ["/api/portfolios"]
        methods: ["GET", "POST", "PUT", "DELETE"]
```

#### 2.2.2 마이크로서비스 분리 (2-3주)

**주식 데이터 서비스 (Stock Service)**:
```typescript
// services/stock-service/src/app.ts
import express from 'express';
import { StockController } from './controllers/stock-controller';
import { StockRepository } from './repositories/stock-repository';
import { YahooFinanceAPI } from './external/yahoo-finance-api';

const app = express();
const port = process.env.PORT || 3001;

// 의존성 주입
const yahooAPI = new YahooFinanceAPI();
const stockRepo = new StockRepository();
const stockController = new StockController(yahooAPI, stockRepo);

// 미들웨어
app.use(express.json());
app.use(cors());
app.use(helmet());

// 라우트
app.get('/stocks/search', stockController.searchStocks.bind(stockController));
app.get('/stocks/:symbol', stockController.getStockInfo.bind(stockController));
app.get('/stocks/:symbol/chart', stockController.getStockChart.bind(stockController));
app.get('/stocks/:symbol/indicators', stockController.getTechnicalIndicators.bind(stockController));

// 헬스 체크
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'healthy', service: 'stock-service' });
});

app.listen(port, () => {
  console.log(`Stock service running on port ${port}`);
});
```

**사용자 관리 서비스 (User Service)**:
```typescript
// services/user-service/src/app.ts
import express from 'express';
import { UserController } from './controllers/user-controller';
import { UserRepository } from './repositories/user-repository';
import { AuthService } from './services/auth-service';
import { authMiddleware } from './middleware/auth-middleware';

const app = express();
const port = process.env.PORT || 3002;

const userRepo = new UserRepository();
const authService = new AuthService(userRepo);
const userController = new UserController(userRepo, authService);

app.use(express.json());
app.use(cors());
app.use(helmet());

// 인증 없는 라우트
app.post('/auth/login', userController.login.bind(userController));
app.post('/auth/register', userController.register.bind(userController));

// 인증 필요 라우트
app.use('/users', authMiddleware);
app.get('/users/profile', userController.getProfile.bind(userController));
app.put('/users/profile', userController.updateProfile.bind(userController));
app.post('/users/change-password', userController.changePassword.bind(userController));

app.listen(port, () => {
  console.log(`User service running on port ${port}`);
});
```

**포트폴리오 서비스 (Portfolio Service)**:
```typescript
// services/portfolio-service/src/app.ts
import express from 'express';
import { PortfolioController } from './controllers/portfolio-controller';
import { PortfolioRepository } from './repositories/portfolio-repository';
import { StockService } from './external/stock-service';

const app = express();
const port = process.env.PORT || 3003;

const portfolioRepo = new PortfolioRepository();
const stockService = new StockService();
const portfolioController = new PortfolioController(portfolioRepo, stockService);

app.use(express.json());
app.use(cors());
app.use(helmet());

app.get('/portfolios', portfolioController.getPortfolios.bind(portfolioController));
app.post('/portfolios', portfolioController.createPortfolio.bind(portfolioController));
app.put('/portfolios/:id', portfolioController.updatePortfolio.bind(portfolioController));
app.delete('/portfolios/:id', portfolioController.deletePortfolio.bind(portfolioController));
app.post('/portfolios/:id/add-stock', portfolioController.addStock.bind(portfolioController));
app.delete('/portfolios/:id/remove-stock/:symbol', portfolioController.removeStock.bind(portfolioController));

app.listen(port, () => {
  console.log(`Portfolio service running on port ${port}`);
});
```

#### 2.2.3 데이터베이스 분리 (1주)

**데이터베이스 스키마 분리**:
```sql
-- stock-service 데이터베이스
CREATE DATABASE stock_service;

-- 주식 정보 테이블
CREATE TABLE stocks (
    symbol VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 주식 가격 테이블 (TimescaleDB)
CREATE TABLE stock_prices (
    time TIMESTAMP NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    open DECIMAL(10,2),
    high DECIMAL(10,2),
    low DECIMAL(10,2),
    close DECIMAL(10,2),
    volume BIGINT,
    PRIMARY KEY (time, symbol)
);

SELECT create_hypertable('stock_prices', 'time');

-- 기술적 지표 테이블
CREATE TABLE technical_indicators (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    indicator_type VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    value DECIMAL(10,4),
    metadata JSONB,
    FOREIGN KEY (symbol) REFERENCES stocks(symbol)
);

-- user-service 데이터베이스
CREATE DATABASE user_service;

-- 사용자 테이블
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- 사용자 설정 테이블
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    theme VARCHAR(20) DEFAULT 'light',
    language VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',
    notifications_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- portfolio-service 데이터베이스
CREATE DATABASE portfolio_service;

-- 포트폴리오 테이블
CREATE TABLE portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 포트폴리오-주식 관계 테이블
CREATE TABLE portfolio_stocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    symbol VARCHAR(10) NOT NULL,
    shares INTEGER NOT NULL,
    purchase_price DECIMAL(10,2),
    purchase_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE(portfolio_id, symbol)
);
```

**데이터 마이그레이션 스크립트**:
```python
# migration/data-migration.py
import pandas as pd
import psycopg2
from datetime import datetime

class DataMigration:
    def __init__(self, source_db_config, target_db_configs):
        self.source_conn = psycopg2.connect(**source_db_config)
        self.target_conns = {
            'stock': psycopg2.connect(**target_db_configs['stock']),
            'user': psycopg2.connect(**target_db_configs['user']),
            'portfolio': psycopg2.connect(**target_db_configs['portfolio'])
        }
    
    def migrate_stock_data(self):
        """기존 주식 데이터 마이그레이션"""
        cursor = self.source_conn.cursor()
        
        # 주식 기본 정보 마이그레이션
        cursor.execute("SELECT * FROM stocks")
        stocks = cursor.fetchall()
        
        stock_cursor = self.target_conns['stock'].cursor()
        for stock in stocks:
            stock_cursor.execute("""
                INSERT INTO stocks (symbol, name, sector, industry, market_cap)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (symbol) DO NOTHING
            """, stock)
        
        # 주식 가격 데이터 마이그레이션
        cursor.execute("SELECT * FROM stock_prices ORDER BY date")
        prices = cursor.fetchall()
        
        for price in prices:
            stock_cursor.execute("""
                INSERT INTO stock_prices (time, symbol, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, price)
        
        self.target_conns['stock'].commit()
        stock_cursor.close()
    
    def migrate_user_data(self):
        """사용자 데이터 마이그레이션"""
        cursor = self.source_conn.cursor()
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        
        user_cursor = self.target_conns['user'].cursor()
        for user in users:
            user_cursor.execute("""
                INSERT INTO users (id, email, password_hash, first_name, last_name, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
            """, user)
        
        self.target_conns['user'].commit()
        user_cursor.close()
    
    def migrate_portfolio_data(self):
        """포트폴리오 데이터 마이그레이션"""
        cursor = self.source_conn.cursor()
        cursor.execute("SELECT * FROM portfolios")
        portfolios = cursor.fetchall()
        
        portfolio_cursor = self.target_conns['portfolio'].cursor()
        for portfolio in portfolios:
            portfolio_cursor.execute("""
                INSERT INTO portfolios (id, user_id, name, description, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, portfolio)
        
        # 포트폴리오-주식 관계 마이그레이션
        cursor.execute("SELECT * FROM portfolio_stocks")
        portfolio_stocks = cursor.fetchall()
        
        for ps in portfolio_stocks:
            portfolio_cursor.execute("""
                INSERT INTO portfolio_stocks (id, portfolio_id, symbol, shares, purchase_price, purchase_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (portfolio_id, symbol) DO NOTHING
            """, ps)
        
        self.target_conns['portfolio'].commit()
        portfolio_cursor.close()
    
    def run_migration(self):
        """전체 마이그레이션 실행"""
        try:
            print("Starting stock data migration...")
            self.migrate_stock_data()
            print("Stock data migration completed.")
            
            print("Starting user data migration...")
            self.migrate_user_data()
            print("User data migration completed.")
            
            print("Starting portfolio data migration...")
            self.migrate_portfolio_data()
            print("Portfolio data migration completed.")
            
            print("All migrations completed successfully!")
        except Exception as e:
            print(f"Migration failed: {e}")
            raise
        finally:
            self.close_connections()
    
    def close_connections(self):
        """데이터베이스 연결 종료"""
        self.source_conn.close()
        for conn in self.target_conns.values():
            conn.close()

# 마이그레이션 실행
if __name__ == "__main__":
    source_config = {
        'host': 'localhost',
        'database': 'insitechart',
        'user': 'postgres',
        'password': 'password'
    }
    
    target_configs = {
        'stock': {
            'host': 'localhost',
            'database': 'stock_service',
            'user': 'postgres',
            'password': 'password'
        },
        'user': {
            'host': 'localhost',
            'database': 'user_service',
            'user': 'postgres',
            'password': 'password'
        },
        'portfolio': {
            'host': 'localhost',
            'database': 'portfolio_service',
            'user': 'postgres',
            'password': 'password'
        }
    }
    
    migration = DataMigration(source_config, target_configs)
    migration.run_migration()
```

### 2.3 1단계 검증 기준

| 검증 항목 | 성공 기준 | 측정 방법 |
|-----------|-----------|-----------|
| API Gateway 라우팅 | 모든 API 요청 정상 라우팅 | Postman 테스트 스위트 |
| 서비스 분리 | 각 서비스 독립적 실행 | Docker 컨테이너 테스트 |
| 데이터 마이그레이션 | 데이터 무손실 마이그레이션 | 데이터 무결성 검증 |
| 성능 | API 응답 시간 < 500ms | 부하 테스트 |
| 가용성 | 서비스 가용성 99% | 헬스 체크 모니터링 |

## 3. 2단계: 실시간 데이터 처리 (3-4주)

### 3.1 개요

**목표**: 실시간 주식 데이터 스트리밍 및 동기화 구현

**핵심 성과**:
- WebSocket을 통한 실시간 주식 가격 업데이트
- 안정적인 클라이언트 연결 관리
- 오프라인 상태에서의 데이터 일관성

### 3.2 상세 작업 계획

#### 3.2.1 WebSocket 인프라 구축 (1주)

**WebSocket 서버 구현**:
```typescript
// realtime/websocket-server.ts
import { Server as SocketIOServer } from 'socket.io';
import { Server as HTTPServer } from 'http';
import { RedisClient } from '../cache/redis-client';
import { StockStreamingService } from './stock-streaming-service';

export class RealtimeServer {
  private io: SocketIOServer;
  private stockStreaming: StockStreamingService;

  constructor(
    private httpServer: HTTPServer,
    private redisClient: RedisClient
  ) {
    this.io = new SocketIOServer(httpServer, {
      cors: {
        origin: process.env.FRONTEND_URL || "http://localhost:3000",
        methods: ["GET", "POST"]
      },
      transports: ['websocket', 'polling']
    });

    this.stockStreaming = new StockStreamingService(redisClient);
    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    this.io.on('connection', (socket) => {
      console.log(`Client connected: ${socket.id}`);

      // 주식 구독
      socket.on('subscribe_stock', async (data: { symbol: string }) => {
        await this.stockStreaming.subscribe(socket.id, data.symbol);
        socket.join(`stock_${data.symbol}`);
        console.log(`Client ${socket.id} subscribed to ${data.symbol}`);
      });

      // 주식 구독 해지
      socket.on('unsubscribe_stock', async (data: { symbol: string }) => {
        await this.stockStreaming.unsubscribe(socket.id, data.symbol);
        socket.leave(`stock_${data.symbol}`);
        console.log(`Client ${socket.id} unsubscribed from ${data.symbol}`);
      });

      // 포트폴리오 구독
      socket.on('subscribe_portfolio', async (data: { portfolioId: string }) => {
        socket.join(`portfolio_${data.portfolioId}`);
        console.log(`Client ${socket.id} subscribed to portfolio ${data.portfolioId}`);
      });

      // 연결 종료
      socket.on('disconnect', () => {
        console.log(`Client disconnected: ${socket.id}`);
        this.stockStreaming.removeAllSubscriptions(socket.id);
      });
    });

    // 주식 업데이트 브로드캐스트
    this.stockStreaming.on('stock_update', (data) => {
      this.io.to(`stock_${data.symbol}`).emit('stock_update', data);
    });

    // 포트폴리오 업데이트 브로드캐스트
    this.stockStreaming.on('portfolio_update', (data) => {
      this.io.to(`portfolio_${data.portfolioId}`).emit('portfolio_update', data);
    });
  }
}
```

**클라이언트 WebSocket 관리**:
```typescript
// client/src/services/websocket-service.ts
export class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor() {
    this.connect();
  }

  private connect(): void {
    this.socket = io(process.env.REACT_APP_WS_URL || 'ws://localhost:3001', {
      transports: ['websocket', 'polling'],
      timeout: 20000,
      forceNew: true
    });

    this.socket.on('connect', () => {
      console.log('Connected to WebSocket server');
      this.reconnectAttempts = 0;
    });

    this.socket.on('disconnect', (reason) => {
      console.log('Disconnected from WebSocket server:', reason);
      this.handleReconnect();
    });

    this.socket.on('stock_update', (data) => {
      this.handleStockUpdate(data);
    });

    this.socket.on('portfolio_update', (data) => {
      this.handlePortfolioUpdate(data);
    });
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        this.reconnectAttempts++;
        console.log(`Reconnection attempt ${this.reconnectAttempts}`);
        this.connect();
      }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts));
    }
  }

  subscribeToStock(symbol: string): void {
    if (this.socket) {
      this.socket.emit('subscribe_stock', { symbol });
    }
  }

  unsubscribeFromStock(symbol: string): void {
    if (this.socket) {
      this.socket.emit('unsubscribe_stock', { symbol });
    }
  }

  subscribeToPortfolio(portfolioId: string): void {
    if (this.socket) {
      this.socket.emit('subscribe_portfolio', { portfolioId });
    }
  }

  private handleStockUpdate(data: any): void {
    // Redux store 업데이트
    store.dispatch(updateStockPrice(data));
  }

  private handlePortfolioUpdate(data: any): void {
    // Redux store 업데이트
    store.dispatch(updatePortfolioValue(data));
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }
}
```

#### 3.2.2 실시간 데이터 스트리밍 (2주)

**주식 데이터 스트리밍 서비스**:
```typescript
// realtime/stock-streaming-service.ts
import { EventEmitter } from 'events';
import { YahooFinanceAPI } from '../external/yahoo-finance-api';
import { RedisClient } from '../cache/redis-client';

export interface StockUpdate {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: number;
}

export class StockStreamingService extends EventEmitter {
  private subscriptions: Map<string, Set<string>> = new Map(); // symbol -> clientIds
  private updateIntervals: Map<string, NodeJS.Timeout> = new Map();
  private lastPrices: Map<string, number> = new Map();

  constructor(
    private yahooAPI: YahooFinanceAPI,
    private redisClient: RedisClient
  ) {
    super();
  }

  async subscribe(clientId: string, symbol: string): Promise<void> {
    symbol = symbol.toUpperCase();

    if (!this.subscriptions.has(symbol)) {
      this.subscriptions.set(symbol, new Set());
    }

    const subscribers = this.subscriptions.get(symbol)!;
    subscribers.add(clientId);

    // 첫 구독자인 경우 스트리밍 시작
    if (subscribers.size === 1) {
      this.startStreaming(symbol);
    }

    // 현재 데이터 즉시 전송
    const currentData = await this.getCurrentStockData(symbol);
    if (currentData) {
      this.emit('stock_update', currentData);
    }
  }

  async unsubscribe(clientId: string, symbol: string): Promise<void> {
    symbol = symbol.toUpperCase();

    const subscribers = this.subscriptions.get(symbol);
    if (!subscribers) return;

    subscribers.delete(clientId);

    // 구독자가 없는 경우 스트리밍 중지
    if (subscribers.size === 0) {
      this.stopStreaming(symbol);
      this.subscriptions.delete(symbol);
    }
  }

  private startStreaming(symbol: string): void {
    console.log(`Starting streaming for ${symbol}`);

    // 기존 인터벌 제거
    this.stopStreaming(symbol);

    // 5초마다 데이터 업데이트
    const interval = setInterval(async () => {
      try {
        await this.updateStockData(symbol);
      } catch (error) {
        console.error(`Error updating ${symbol}:`, error);
      }
    }, 5000);

    this.updateIntervals.set(symbol, interval);

    // 즉시 첫 업데이트
    this.updateStockData(symbol);
  }

  private stopStreaming(symbol: string): void {
    const interval = this.updateIntervals.get(symbol);
    if (interval) {
      clearInterval(interval);
      this.updateIntervals.delete(symbol);
      console.log(`Stopped streaming for ${symbol}`);
    }
  }

  private async updateStockData(symbol: string): Promise<void> {
    try {
      const stockData = await this.yahooAPI.getRealTimeData(symbol);
      
      if (!stockData) {
        return;
      }

      const lastPrice = this.lastPrices.get(symbol);
      const currentPrice = stockData.price;

      // 가격이 변경된 경우에만 업데이트
      if (lastPrice !== currentPrice) {
        this.lastPrices.set(symbol, currentPrice);

        const update: StockUpdate = {
          symbol,
          price: stockData.price,
          change: stockData.change || 0,
          changePercent: stockData.changePercent || 0,
          volume: stockData.volume || 0,
          timestamp: Date.now()
        };

        // Redis에 캐시
        await this.redisClient.setex(
          `stock:${symbol}:current`,
          300, // 5분 TTL
          JSON.stringify(update)
        );

        // 이벤트 발생
        this.emit('stock_update', update);
      }
    } catch (error) {
      console.error(`Failed to update ${symbol}:`, error);
    }
  }

  private async getCurrentStockData(symbol: string): Promise<StockUpdate | null> {
    try {
      // Redis에서 캐시된 데이터 조회
      const cached = await this.redisClient.get(`stock:${symbol}:current`);
      if (cached) {
        return JSON.parse(cached);
      }

      // API에서 직접 조회
      const stockData = await this.yahooAPI.getRealTimeData(symbol);
      if (stockData) {
        const update: StockUpdate = {
          symbol,
          price: stockData.price,
          change: stockData.change || 0,
          changePercent: stockData.changePercent || 0,
          volume: stockData.volume || 0,
          timestamp: Date.now()
        };

        await this.redisClient.setex(
          `stock:${symbol}:current`,
          300,
          JSON.stringify(update)
        );

        return update;
      }

      return null;
    } catch (error) {
      console.error(`Error getting current data for ${symbol}:`, error);
      return null;
    }
  }

  removeAllSubscriptions(clientId: string): void {
    this.subscriptions.forEach((subscribers, symbol) => {
      if (subscribers.has(clientId)) {
        this.unsubscribe(clientId, symbol);
      }
    });
  }

  getActiveSubscriptions(): string[] {
    return Array.from(this.subscriptions.keys());
  }

  getSubscriptionCount(symbol: string): number {
    return this.subscriptions.get(symbol)?.size || 0;
  }
}
```

#### 3.2.3 오프라인 지원 (1주)

**오프라인 데이터 관리자**:
```typescript
// client/src/services/offline-manager.ts
export interface OfflineAction {
  id: string;
  type: string;
  data: any;
  timestamp: number;
  syncStatus: 'pending' | 'syncing' | 'synced' | 'failed';
  retryCount: number;
}

export class OfflineManager {
  private actions: OfflineAction[] = [];
  private isOnline = navigator.onLine;

  constructor() {
    this.setupEventListeners();
    this.loadOfflineActions();
  }

  private setupEventListeners(): void {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.syncPendingActions();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
    });
  }

  async addAction(type: string, data: any): Promise<string> {
    const action: OfflineAction = {
      id: this.generateId(),
      type,
      data,
      timestamp: Date.now(),
      syncStatus: 'pending',
      retryCount: 0
    };

    this.actions.push(action);
    await this.saveOfflineActions();

    // 온라인 상태이면 즉시 동기화 시도
    if (this.isOnline) {
      this.syncAction(action);
    }

    return action.id;
  }

  private async syncPendingActions(): Promise<void> {
    const pendingActions = this.actions.filter(
      action => action.syncStatus === 'pending' || action.syncStatus === 'failed'
    );

    for (const action of pendingActions) {
      await this.syncAction(action);
    }
  }

  private async syncAction(action: OfflineAction): Promise<void> {
    if (!this.isOnline) return;

    try {
      action.syncStatus = 'syncing';
      await this.saveOfflineActions();

      // API 호출로 동기화
      const response = await fetch('/api/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          id: action.id,
          type: action.type,
          data: action.data,
          timestamp: action.timestamp
        })
      });

      if (response.ok) {
        action.syncStatus = 'synced';
        this.removeAction(action.id);
      } else {
        throw new Error('Sync failed');
      }
    } catch (error) {
      action.syncStatus = 'failed';
      action.retryCount++;
      
      // 최대 3번 재시도
      if (action.retryCount < 3) {
        setTimeout(() => {
          this.syncAction(action);
        }, 5000 * Math.pow(2, action.retryCount - 1));
      }
    }

    await this.saveOfflineActions();
  }

  private async saveOfflineActions(): Promise<void> {
    try {
      localStorage.setItem('offline_actions', JSON.stringify(this.actions));
    } catch (error) {
      console.error('Error saving offline actions:', error);
    }
  }

  private async loadOfflineActions(): Promise<void> {
    try {
      const stored = localStorage.getItem('offline_actions');
      if (stored) {
        this.actions = JSON.parse(stored);
      }
    } catch (error) {
      console.error('Error loading offline actions:', error);
      this.actions = [];
    }
  }

  private removeAction(id: string): void {
    const index = this.actions.findIndex(action => action.id === id);
    if (index > -1) {
      this.actions.splice(index, 1);
    }
  }

  private generateId(): string {
    return `action_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  getPendingActions(): OfflineAction[] {
    return this.actions.filter(action => action.syncStatus === 'pending');
  }

  getFailedActions(): OfflineAction[] {
    return this.actions.filter(action => action.syncStatus === 'failed');
  }

  async retryFailedActions(): Promise<void> {
    const failedActions = this.getFailedActions();
    for (const action of failedActions) {
      action.syncStatus = 'pending';
      action.retryCount = 0;
    }
    await this.saveOfflineActions();
    await this.syncPendingActions();
  }

  async clearAllActions(): Promise<void> {
    this.actions = [];
    await this.saveOfflineActions();
  }
}
```

### 3.3 2단계 검증 기준

| 검증 항목 | 성공 기준 | 측정 방법 |
|-----------|-----------|-----------|
| WebSocket 연결 | 1000개 동시 연결 지원 | 부하 테스트 |
| 실시간 업데이트 | 5초 내 가격 업데이트 | 지연 시간 측정 |
| 오프라인 지원 | 오프라인 상태에서 데이터 일관성 | 오프라인 테스트 |
| 재연결 | 네트워크 복구 시 자동 재연결 | 연결 테스트 |
| 데이터 무결성 | 오프라인-온라인 전환 시 데이터 무결성 | 데이터 검증 |

## 4. 3단계: 성능 최적화 (2-3주)

### 4.1 개요

**목표**: 다중 레벨 캐싱 및 데이터베이스 최적화

**핵심 성과**:
- API 응답 시간 50% 개선
- 캐시 히트율 80% 이상
- 데이터베이스 쿼리 성능 최적화

### 4.2 상세 작업 계획

#### 4.2.1 캐싱 시스템 구현 (1-2주)

**Redis 캐싱 레이어**:
```typescript
// cache/redis-cache.ts
import Redis from 'ioredis';

export interface CacheConfig {
  host: string;
  port: number;
  password?: string;
  db: number;
  keyPrefix: string;
  ttl: number;
}

export class RedisCache {
  private redis: Redis;
  private keyPrefix: string;

  constructor(private config: CacheConfig) {
    this.redis = new Redis({
      host: config.host,
      port: config.port,
      password: config.password,
      db: config.db,
      retryDelayOnFailover: 100,
      maxRetriesPerRequest: 3,
      lazyConnect: true
    });

    this.keyPrefix = config.keyPrefix;
  }

  private getKey(key: string): string {
    return `${this.keyPrefix}:${key}`;
  }

  async get<T>(key: string): Promise<T | null> {
    try {
      const value = await this.redis.get(this.getKey(key));
      return value ? JSON.parse(value) : null;
    } catch (error) {
      console.error(`Cache get error for key ${key}:`, error);
      return null;
    }
  }

  async set<T>(key: string, value: T, ttl?: number): Promise<void> {
    try {
      const serialized = JSON.stringify(value);
      const cacheKey = this.getKey(key);
      const expireTime = ttl || this.config.ttl;

      if (expireTime > 0) {
        await this.redis.setex(cacheKey, expireTime, serialized);
      } else {
        await this.redis.set(cacheKey, serialized);
      }
    } catch (error) {
      console.error(`Cache set error for key ${key}:`, error);
    }
  }

  async del(key: string): Promise<void> {
    try {
      await this.redis.del(this.getKey(key));
    } catch (error) {
      console.error(`Cache delete error for key ${key}:`, error);
    }
  }

  async exists(key: string): Promise<boolean> {
    try {
      const result = await this.redis.exists(this.getKey(key));
      return result === 1;
    } catch (error) {
      console.error(`Cache exists error for key ${key}:`, error);
      return false;
    }
  }

  async invalidatePattern(pattern: string): Promise<void> {
    try {
      const keys = await this.redis.keys(`${this.keyPrefix}:${pattern}`);
      if (keys.length > 0) {
        await this.redis.del(...keys);
      }
    } catch (error) {
      console.error(`Cache invalidate pattern error for ${pattern}:`, error);
    }
  }

  async getTTL(key: string): Promise<number> {
    try {
      return await this.redis.ttl(this.getKey(key));
    } catch (error) {
      console.error(`Cache TTL error for key ${key}:`, error);
      return -1;
    }
  }

  async increment(key: string, amount = 1): Promise<number> {
    try {
      return await this.redis.incrby(this.getKey(key), amount);
    } catch (error) {
      console.error(`Cache increment error for key ${key}:`, error);
      return 0;
    }
  }

  async addToSet(key: string, members: string[]): Promise<void> {
    try {
      await this.redis.sadd(this.getKey(key), ...members);
    } catch (error) {
      console.error(`Cache add to set error for key ${key}:`, error);
    }
  }

  async getSetMembers(key: string): Promise<string[]> {
    try {
      return await this.redis.smembers(this.getKey(key));
    } catch (error) {
      console.error(`Cache get set members error for key ${key}:`, error);
      return [];
    }
  }

  async removeFromSet(key: string, members: string[]): Promise<void> {
    try {
      await this.redis.srem(this.getKey(key), ...members);
    } catch (error) {
      console.error(`Cache remove from set error for key ${key}:`, error);
    }
  }

  async disconnect(): Promise<void> {
    await this.redis.disconnect();
  }
}

// 캐시 레이어 팩토리
export class CacheFactory {
  private static instances: Map<string, RedisCache> = new Map();

  static getInstance(config: CacheConfig): RedisCache {
    const instanceKey = `${config.host}:${config.port}:${config.db}`;
    
    if (!this.instances.has(instanceKey)) {
      this.instances.set(instanceKey, new RedisCache(config));
    }

    return this.instances.get(instanceKey)!;
  }
}
```

**다중 레벨 캐싱 구현**:
```typescript
// cache/multi-level-cache.ts
export interface CacheLevel {
  name: string;
  get<T>(key: string): Promise<T | null>;
  set<T>(key: string, value: T, ttl?: number): Promise<void>;
  del(key: string): Promise<void>;
  clear(): Promise<void>;
}

export class MemoryCache implements CacheLevel {
  name = 'memory';
  private cache = new Map<string, { value: any; expiry: number }>();

  async get<T>(key: string): Promise<T | null> {
    const item = this.cache.get(key);
    if (!item) return null;

    if (Date.now() > item.expiry) {
      this.cache.delete(key);
      return null;
    }

    return item.value;
  }

  async set<T>(key: string, value: T, ttl = 300000): Promise<void> {
    this.cache.set(key, {
      value,
      expiry: Date.now() + ttl
    });
  }

  async del(key: string): Promise<void> {
    this.cache.delete(key);
  }

  async clear(): Promise<void> {
    this.cache.clear();
  }
}

export class MultiLevelCache {
  constructor(
    private levels: CacheLevel[],
    private fallbackLevel = 0
  ) {}

  async get<T>(key: string): Promise<T | null> {
    // L1 캐시에서 조회
    for (let i = 0; i < this.levels.length; i++) {
      const value = await this.levels[i].get<T>(key);
      if (value !== null) {
        // 상위 레벨 캐시에 값이 없으면 채워넣기
        if (i > 0) {
          for (let j = 0; j < i; j++) {
            await this.levels[j].set(key, value);
          }
        }
        return value;
      }
    }

    return null;
  }

  async set<T>(key: string, value: T, ttl?: number): Promise<void> {
    // 모든 레벨에 설정
    await Promise.all(
      this.levels.map(level => level.set(key, value, ttl))
    );
  }

  async del(key: string): Promise<void> {
    // 모든 레벨에서 삭제
    await Promise.all(
      this.levels.map(level => level.del(key))
    );
  }

  async invalidatePattern(pattern: string): Promise<void> {
    // Redis 패턴 무효화 (L2 캐시)
    const redisCache = this.levels.find(level => level.name === 'redis');
    if (redisCache && 'invalidatePattern' in redisCache) {
      await (redisCache as any).invalidatePattern(pattern);
    }

    // 메모리 캐시 클리어
    const memoryCache = this.levels.find(level => level.name === 'memory');
    if (memoryCache) {
      await memoryCache.clear();
    }
  }

  async getStats(): Promise<{ [levelName: string]: any }> {
    const stats: { [levelName: string]: any } = {};
    
    for (const level of this.levels) {
      stats[level.name] = {
        name: level.name,
        // 각 캐시 레벨별 통계 정보
      };
    }

    return stats;
  }
}

// 캐시 서비스
export class CacheService {
  private multiLevelCache: MultiLevelCache;

  constructor() {
    const memoryCache = new MemoryCache();
    const redisCache = CacheFactory.getInstance({
      host: process.env.REDIS_HOST || 'localhost',
      port: parseInt(process.env.REDIS_PORT || '6379'),
      password: process.env.REDIS_PASSWORD,
      db: 0,
      keyPrefix: 'insitechart',
      ttl: 3600
    });

    this.multiLevelCache = new MultiLevelCache([
      memoryCache,
      redisCache
    ]);
  }

  async getStockInfo(symbol: string): Promise<any | null> {
    return await this.multiLevelCache.get(`stock:${symbol}:info`);
  }

  async setStockInfo(symbol: string, info: any): Promise<void> {
    await this.multiLevelCache.set(`stock:${symbol}:info`, info, 1800); // 30분
  }

  async getStockPrices(symbol: string, timeframe: string): Promise<any[] | null> {
    return await this.multiLevelCache.get(`stock:${symbol}:prices:${timeframe}`);
  }

  async setStockPrices(symbol: string, timeframe: string, prices: any[]): Promise<void> {
    await this.multiLevelCache.set(`stock:${symbol}:prices:${timeframe}`, prices, 300); // 5분
  }

  async getUserPortfolio(userId: string): Promise<any | null> {
    return await this.multiLevelCache.get(`user:${userId}:portfolio`);
  }

  async setUserPortfolio(userId: string, portfolio: any): Promise<void> {
    await this.multiLevelCache.set(`user:${userId}:portfolio`, portfolio, 600); // 10분
  }

  async invalidateStockData(symbol: string): Promise<void> {
    await this.multiLevelCache.invalidatePattern(`stock:${symbol}:*`);
  }

  async invalidateUserData(userId: string): Promise<void> {
    await this.multiLevelCache.invalidatePattern(`user:${userId}:*`);
  }
}
```

#### 4.2.2 데이터베이스 최적화 (1주)

**TimescaleDB 최적화**:
```sql
-- 하이퍼테이블 최적화
SELECT add_retention_policy('stock_prices', INTERVAL '1 year');

-- 압축 정책 설정
ALTER TABLE stock_prices SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'symbol',
  timescaledb.compress_orderby = 'time DESC'
);

SELECT add_compression_policy('stock_prices', INTERVAL '7 days');

-- 연속 집계 뷰 생성
CREATE MATERIALIZED VIEW daily_stock_summary
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 day', time) AS day,
    symbol,
    FIRST(open, time) AS open,
    MAX(high) AS high,
    MIN(low) AS low,
    LAST(close, time) AS close,
    SUM(volume) AS volume
FROM stock_prices
GROUP BY day, symbol;

-- 연속 집계 정책 설정
SELECT add_continuous_aggregate_policy('daily_stock_summary',
    start_offset => INTERVAL '1 month',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour'
);

-- 인덱스 최적화
CREATE INDEX idx_stock_prices_symbol_time ON stock_prices (symbol, time DESC);
CREATE INDEX idx_stock_prices_time ON stock_prices (time DESC);

-- 파티션 튜닝
SELECT set_chunk_time_interval('stock_prices', INTERVAL '1 day');
```

**쿼리 성능 최적화**:
```typescript
// repositories/optimized-stock-repository.ts
export class OptimizedStockRepository {
  constructor(private db: Pool) {}

  async getLatestPrice(symbol: string): Promise<any | null> {
    const query = `
      SELECT time, close, volume
      FROM stock_prices
      WHERE symbol = $1
      ORDER BY time DESC
      LIMIT 1
    `;
    
    const result = await this.db.query(query, [symbol]);
    return result.rows[0] || null;
  }

  async getPriceHistory(symbol: string, startDate: Date, endDate: Date): Promise<any[]> {
    const query = `
      SELECT time, open, high, low, close, volume
      FROM stock_prices
      WHERE symbol = $1 
        AND time BETWEEN $2 AND $3
      ORDER BY time ASC
    `;
    
    const result = await this.db.query(query, [symbol, startDate, endDate]);
    return result.rows;
  }

  async getDailySummary(symbol: string, days: number): Promise<any[]> {
    const query = `
      SELECT * FROM daily_stock_summary
      WHERE symbol = $1
        AND day >= NOW() - INTERVAL '${days} days'
      ORDER BY day ASC
    `;
    
    const result = await this.db.query(query, [symbol]);
    return result.rows;
  }

  async getTopGainers(limit = 10): Promise<any[]> {
    const query = `
      WITH latest_prices AS (
        SELECT DISTINCT ON (symbol) 
          symbol, close, time
        FROM stock_prices
        ORDER BY symbol, time DESC
      ),
      previous_prices AS (
        SELECT 
          sp.symbol,
          sp.close as previous_close,
          sp.time as previous_time
        FROM stock_prices sp
        INNER JOIN latest_prices lp ON sp.symbol = lp.symbol
        WHERE sp.time < lp.time
        ORDER BY sp.symbol, sp.time DESC
        LIMIT 1
      )
      SELECT 
        lp.symbol,
        lp.close as current_price,
        pp.previous_close,
        ((lp.close - pp.previous_close) / pp.previous_close * 100) as change_percent
      FROM latest_prices lp
      LEFT JOIN previous_prices pp ON lp.symbol = pp.symbol
      WHERE pp.previous_close IS NOT NULL
      ORDER BY change_percent DESC
      LIMIT $1
    `;
    
    const result = await this.db.query(query, [limit]);
    return result.rows;
  }

  async getTopLosers(limit = 10): Promise<any[]> {
    const query = `
      WITH latest_prices AS (
        SELECT DISTINCT ON (symbol) 
          symbol, close, time
        FROM stock_prices
        ORDER BY symbol, time DESC
      ),
      previous_prices AS (
        SELECT 
          sp.symbol,
          sp.close as previous_close,
          sp.time as previous_time
        FROM stock_prices sp
        INNER JOIN latest_prices lp ON sp.symbol = lp.symbol
        WHERE sp.time < lp.time
        ORDER BY sp.symbol, sp.time DESC
        LIMIT 1
      )
      SELECT 
        lp.symbol,
        lp.close as current_price,
        pp.previous_close,
        ((lp.close - pp.previous_close) / pp.previous_close * 100) as change_percent
      FROM latest_prices lp
      LEFT JOIN previous_prices pp ON lp.symbol = pp.symbol
      WHERE pp.previous_close IS NOT NULL
      ORDER BY change_percent ASC
      LIMIT $1
    `;
    
    const result = await this.db.query(query, [limit]);
    return result.rows;
  }

  async getMostActive(limit = 10): Promise<any[]> {
    const query = `
      SELECT 
        symbol,
        close,
        volume,
        change_percent
      FROM daily_stock_summary
      WHERE day >= CURRENT_DATE - INTERVAL '1 day'
      ORDER BY volume DESC
      LIMIT $1
    `;
    
    const result = await this.db.query(query, [limit]);
    return result.rows;
  }
}
```

### 4.3 3단계 검증 기준

| 검증 항목 | 성공 기준 | 측정 방법 |
|-----------|-----------|-----------|
| API 응답 시간 | 평균 200ms 이하 | 성능 테스트 |
| 캐시 히트율 | 80% 이상 | 캐시 통계 |
| 데이터베이스 쿼리 | 쿼리 시간 50% 개선 | 쿼리 분석 |
| 메모리 사용 | 메모리 사용량 30% 감소 | 리소스 모니터링 |
| 동시 사용자 | 1000명 동시 접속 지원 | 부하 테스트 |

## 5. 4단계: 소셜 감성 분석 통합 (3-4주)

### 5.1 개요

**목표**: 소셜 미디어 데이터 수집 및 감성 분석 기능 구현

**핵심 성과**:
- Reddit/Twitter 데이터 실시간 수집
- 감성 분석 정확도 80% 이상
- 주식-감성 상관관계 시각화

### 5.2 상세 작업 계획

#### 5.2.1 소셜 데이터 수집 (1-2주)

**Reddit API 연동**:
```typescript
// social/reddit-collector.ts
import snoowrap from 'snoowrap';

export interface RedditPost {
  id: string;
  title: string;
  text: string;
  author: string;
  subreddit: string;
  score: number;
  upvoteRatio: number;
  numComments: number;
  created: number;
  permalink: string;
}

export interface RedditComment {
  id: string;
  body: string;
  author: string;
  score: number;
  created: number;
  postId: string;
}

export class RedditCollector {
  private reddit: snoowrap;

  constructor() {
    this.reddit = new snoowrap({
      userAgent: 'insitechart:v1.0.0',
      clientId: process.env.REDDIT_CLIENT_ID,
      clientSecret: process.env.REDDIT_CLIENT_SECRET,
      username: process.env.REDDIT_USERNAME,
      password: process.env.REDDIT_PASSWORD
    });
  }

  async searchStockMentions(symbol: string, timeRange: 'day' | 'week' | 'month' = 'day'): Promise<RedditPost[]> {
    const searchQuery = `${symbol} OR $${symbol}`;
    const timeFilter = this.getTimeFilter(timeRange);
    
    try {
      const results = await this.reddit.search({
        query: searchQuery,
        sort: 'relevance',
        timeFilter,
        subreddit: ['wallstreetbets', 'stocks', 'investing', 'SecurityAnalysis']
      });

      const posts: RedditPost[] = [];
      
      for await (const post of results) {
        posts.push({
          id: post.id,
          title: post.title,
          text: post.selftext || '',
          author: post.author.name,
          subreddit: post.subreddit.display_name,
          score: post.score,
          upvoteRatio: post.upvote_ratio,
          numComments: post.num_comments,
          created: post.created_utc * 1000,
          permalink: `https://reddit.com${post.permalink}`
        });
      }

      return posts;
    } catch (error) {
      console.error(`Error searching Reddit for ${symbol}:`, error);
      return [];
    }
  }

  async getPostComments(postId: string, limit = 100): Promise<RedditComment[]> {
    try {
      const submission = await this.reddit.getSubmission(postId);
      const comments = await submission.comments.fetchMore({ amount: limit });

      const commentData: RedditComment[] = [];
      
      comments.forEach(comment => {
        if (comment.body && !comment.author.name.includes('[deleted]')) {
          commentData.push({
            id: comment.id,
            body: comment.body,
            author: comment.author.name,
            score: comment.score,
            created: comment.created_utc * 1000,
            postId
          });
        }
      });

      return commentData;
    } catch (error) {
      console.error(`Error getting comments for post ${postId}:`, error);
      return [];
    }
  }

  async getHotPosts(subreddits: string[] = ['wallstreetbets', 'stocks'], limit = 50): Promise<RedditPost[]> {
    try {
      const posts: RedditPost[] = [];
      
      for (const subreddit of subreddits) {
        const subredditObj = await this.reddit.getSubreddit(subreddit);
        const hotPosts = await subredditObj.getHot({ limit });

        for (const post of hotPosts) {
          posts.push({
            id: post.id,
            title: post.title,
            text: post.selftext || '',
            author: post.author.name,
            subreddit: post.subreddit.display_name,
            score: post.score,
            upvoteRatio: post.upvote_ratio,
            numComments: post.num_comments,
            created: post.created_utc * 1000,
            permalink: `https://reddit.com${post.permalink}`
          });
        }
      }

      return posts.sort((a, b) => b.score - a.score);
    } catch (error) {
      console.error('Error getting hot posts:', error);
      return [];
    }
  }

  private getTimeFilter(timeRange: 'day' | 'week' | 'month'): string {
    switch (timeRange) {
      case 'day': return 'day';
      case 'week': return 'week';
      case 'month': return 'month';
      default: return 'day';
    }
  }
}
```

**Twitter API 연동**:
```typescript
// social/twitter-collector.ts
import { TwitterApi } from 'twitter-api-v2';

export interface Tweet {
  id: string;
  text: string;
  author: {
    id: string;
    username: string;
    name: string;
    followersCount: number;
    verified: boolean;
  };
  metrics: {
    retweetCount: number;
    likeCount: number;
    replyCount: number;
    quoteCount: number;
  };
  createdAt: string;
  lang: string;
  hashtags: string[];
  mentions: string[];
}

export class TwitterCollector {
  private twitterClient: TwitterApi;

  constructor() {
    this.twitterClient = new TwitterApi({
      appKey: process.env.TWITTER_API_KEY,
      appSecret: process.env.TWITTER_API_SECRET,
      accessToken: process.env.TWITTER_ACCESS_TOKEN,
      accessSecret: process.env.TWITTER_ACCESS_SECRET
    });
  }

  async searchStockTweets(symbol: string, timeRange: 'day' | 'week' | 'month' = 'day'): Promise<Tweet[]> {
    const searchQuery = `$${symbol} OR ${symbol} stock`;
    const maxResults = 100;
    
    try {
      const searchResult = await this.twitterClient.v2.search(searchQuery, {
        max_results: maxResults,
        'tweet.fields': ['created_at', 'author_id', 'public_metrics', 'lang', 'context_annotations'],
        'user.fields': ['username', 'name', 'public_metrics', 'verified'],
        'expansions': ['author_id']
      });

      const tweets: Tweet[] = [];
      const users = searchResult.includes?.users || [];

      searchResult.data?.forEach(tweet => {
        const author = users.find(user => user.id === tweet.author_id);
        
        if (author) {
          tweets.push({
            id: tweet.id,
            text: tweet.text,
            author: {
              id: author.id,
              username: author.username,
              name: author.name,
              followersCount: author.public_metrics?.followers_count || 0,
              verified: author.verified || false
            },
            metrics: {
              retweetCount: tweet.public_metrics?.retweet_count || 0,
              likeCount: tweet.public_metrics?.like_count || 0,
              replyCount: tweet.public_metrics?.reply_count || 0,
              quoteCount: tweet.public_metrics?.quote_count || 0
            },
            createdAt: tweet.created_at || '',
            lang: tweet.lang || '',
            hashtags: this.extractHashtags(tweet.text),
            mentions: this.extractMentions(tweet.text)
          });
        }
      });

      return tweets;
    } catch (error) {
      console.error(`Error searching Twitter for ${symbol}:`, error);
      return [];
    }
  }

  async getTweetsByUser(username: string, limit = 50): Promise<Tweet[]> {
    try {
      const user = await this.twitterClient.v2.userByUsername(username);
      
      const tweetsResult = await this.twitterClient.v2.userTimeline(user.data.id, {
        max_results: limit,
        'tweet.fields': ['created_at', 'public_metrics', 'lang'],
        'user.fields': ['username', 'name', 'public_metrics', 'verified']
      });

      const tweets: Tweet[] = [];

      tweetsResult.data?.forEach(tweet => {
        tweets.push({
          id: tweet.id,
          text: tweet.text,
          author: {
            id: user.data.id,
            username: user.data.username,
            name: user.data.name,
            followersCount: user.data.public_metrics?.followers_count || 0,
            verified: user.data.verified || false
          },
          metrics: {
            retweetCount: tweet.public_metrics?.retweet_count || 0,
            likeCount: tweet.public_metrics?.like_count || 0,
            replyCount: tweet.public_metrics?.reply_count || 0,
            quoteCount: tweet.public_metrics?.quote_count || 0
          },
          createdAt: tweet.created_at || '',
          lang: tweet.lang || '',
          hashtags: this.extractHashtags(tweet.text),
          mentions: this.extractMentions(tweet.text)
        });
      });

      return tweets;
    } catch (error) {
      console.error(`Error getting tweets for ${username}:`, error);
      return [];
    }
  }

  private extractHashtags(text: string): string[] {
    const hashtags = text.match(/#\w+/g) || [];
    return hashtags.map(tag => tag.substring(1));
  }

  private extractMentions(text: string): string[] {
    const mentions = text.match(/@\w+/g) || [];
    return mentions.map(mention => mention.substring(1));
  }
}
```

#### 5.2.2 감성 분석 엔진 (1-2주)

**NLP 감성 분석 서비스**:
```typescript
// sentiment/sentiment-analyzer.ts
export interface SentimentResult {
  score: number; // -1 to 1
  label: 'positive' | 'negative' | 'neutral';
  confidence: number; // 0 to 1
  emotions: {
    joy: number;
    anger: number;
    fear: number;
    sadness: number;
    disgust: number;
    surprise: number;
  };
  keywords: string[];
}

export class SentimentAnalyzer {
  private vader: any;
  private transformer: any;

  constructor() {
    // VADER for social media text
    this.initializeVader();
    
    // Transformer for more accurate analysis
    this.initializeTransformer();
  }

  private async initializeVader(): Promise<void> {
    // VADER sentiment analysis for social media
    const { SentimentIntensityAnalyzer } = await import('vader-sentiment');
    this.vader = new SentimentIntensityAnalyzer();
  }

  private async initializeTransformer(): Promise<void> {
    // Initialize transformer model for more accurate sentiment analysis
    const { pipeline } = await import('@xenova/transformers');
    this.transformer = await pipeline('sentiment-analysis', 'distilbert-base-uncased-finetuned-sst-2-english');
  }

  async analyzeSentiment(text: string): Promise<SentimentResult> {
    // Clean and preprocess text
    const cleanedText = this.preprocessText(text);
    
    // VADER analysis (fast, good for social media)
    const vaderResult = this.vader.polarity_scores(cleanedText);
    
    // Transformer analysis (more accurate)
    const transformerResult = await this.transformer(cleanedText);
    
    // Combine results
    const combinedScore = this.combineResults(vaderResult, transformerResult);
    const label = this.getLabel(combinedScore);
    const confidence = this.calculateConfidence(vaderResult, transformerResult);
    
    // Extract emotions using keyword-based approach
    const emotions = this.extractEmotions(cleanedText);
    
    // Extract keywords
    const keywords = this.extractKeywords(cleanedText);

    return {
      score: combinedScore,
      label,
      confidence,
      emotions,
      keywords
    };
  }

  async analyzeBatch(texts: string[]): Promise<SentimentResult[]> {
    const results: SentimentResult[] = [];
    
    // Process in batches to avoid memory issues
    const batchSize = 10;
    for (let i = 0; i < texts.length; i += batchSize) {
      const batch = texts.slice(i, i + batchSize);
      const batchResults = await Promise.all(
        batch.map(text => this.analyzeSentiment(text))
      );
      results.push(...batchResults);
    }

    return results;
  }

  private preprocessText(text: string): string {
    return text
      .toLowerCase()
      .replace(/[^\w\s]/g, '') // Remove punctuation
      .replace(/\s+/g, ' ') // Normalize whitespace
      .replace(/https?:\/\/\S+/g, '') // Remove URLs
      .replace(/@\w+/g, '') // Remove mentions
      .replace(/#\w+/g, '') // Remove hashtags
      .trim();
  }

  private combineResults(vaderResult: any, transformerResult: any): number {
    // Weight VADER higher for social media content
    const vaderScore = vaderResult.compound;
    const transformerScore = transformerResult[0].score > 0.5 ? 1 : -1;
    
    return (vaderScore * 0.7) + (transformerScore * 0.3);
  }

  private getLabel(score: number): 'positive' | 'negative' | 'neutral' {
    if (score > 0.1) return 'positive';
    if (score < -0.1) return 'negative';
    return 'neutral';
  }

  private calculateConfidence(vaderResult: any, transformerResult: any): number {
    const vaderConfidence = Math.abs(vaderResult.compound);
    const transformerConfidence = Math.max(transformerResult[0].score, 1 - transformerResult[0].score);
    
    return (vaderConfidence + transformerConfidence) / 2;
  }

  private extractEmotions(text: string): any {
    // Simple keyword-based emotion extraction
    const emotionKeywords = {
      joy: ['happy', 'excited', 'bullish', 'gain', 'profit', 'moon', 'rocket'],
      anger: ['angry', 'frustrated', 'bearish', 'loss', 'crash', 'dump'],
      fear: ['scared', 'worried', 'panic', 'recession', 'crisis'],
      sadness: ['sad', 'disappointed', 'loss', 'decline'],
      disgust: ['disgusted', 'terrible', 'awful'],
      surprise: ['surprised', 'shocked', 'unexpected', 'wow']
    };

    const emotions = {
      joy: 0,
      anger: 0,
      fear: 0,
      sadness: 0,
      disgust: 0,
      surprise: 0
    };

    const words = text.split(' ');
    
    words.forEach(word => {
      Object.entries(emotionKeywords).forEach(([emotion, keywords]) => {
        if (keywords.includes(word)) {
          emotions[emotion as keyof typeof emotions] += 1;
        }
      });
    });

    // Normalize emotions
    const total = Object.values(emotions).reduce((sum, count) => sum + count, 0);
    if (total > 0) {
      Object.keys(emotions).forEach(emotion => {
        emotions[emotion as keyof typeof emotions] /= total;
      });
    }

    return emotions;
  }

  private extractKeywords(text: string): string[] {
    // Simple keyword extraction using TF-IDF or frequency
    const words = text.split(' ').filter(word => word.length > 3);
    const wordFreq: { [key: string]: number } = {};
    
    words.forEach(word => {
      wordFreq[word] = (wordFreq[word] || 0) + 1;
    });

    // Return top 5 keywords
    return Object.entries(wordFreq)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5)
      .map(([word]) => word);
  }
}
```

#### 5.2.3 상관관계 분석 (1주)

**주식-감성 상관관계 분석**:
```typescript
// correlation/sentiment-correlation.ts
export interface CorrelationResult {
  symbol: string;
  correlation: number; // -1 to 1
  pValue: number;
  significance: 'high' | 'medium' | 'low' | 'none';
  lag: number; // Days of lag
  insights: string[];
}

export class SentimentCorrelationAnalyzer {
  async analyzeCorrelation(
    symbol: string,
    stockData: any[],
    sentimentData: any[],
    timeRange: number = 30 // days
  ): Promise<CorrelationResult> {
    // Align data by date
    const alignedData = this.alignData(stockData, sentimentData, timeRange);
    
    if (alignedData.length < 10) {
      return {
        symbol,
        correlation: 0,
        pValue: 1,
        significance: 'none',
        lag: 0,
        insights: ['Insufficient data for correlation analysis']
      };
    }

    // Calculate correlation for different lags
    const correlations = [];
    for (let lag = 0; lag <= 5; lag++) {
      const correlation = this.calculateCorrelation(alignedData, lag);
      correlations.push({ lag, ...correlation });
    }

    // Find best correlation
    const bestCorrelation = correlations.reduce((best, current) => 
      Math.abs(current.correlation) > Math.abs(best.correlation) ? current : best
    );

    // Calculate significance
    const significance = this.calculateSignificance(bestCorrelation.correlation, alignedData.length);
    
    // Generate insights
    const insights = this.generateInsights(bestCorrelation, alignedData);

    return {
      symbol,
      correlation: bestCorrelation.correlation,
      pValue: bestCorrelation.pValue,
      significance,
      lag: bestCorrelation.lag,
      insights
    };
  }

  private alignData(stockData: any[], sentimentData: any[], timeRange: number): any[] {
    const aligned = [];
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - timeRange);

    // Create date range
    const dateRange = [];
    for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
      dateRange.push(new Date(d));
    }

    // Align data for each date
    dateRange.forEach(date => {
      const dateStr = date.toISOString().split('T')[0];
      
      const stockEntry = stockData.find(item => 
        item.date.startsWith(dateStr)
      );
      
      const sentimentEntry = sentimentData.find(item => 
        item.date.startsWith(dateStr)
      );

      if (stockEntry && sentimentEntry) {
        aligned.push({
          date: dateStr,
          stockReturn: stockEntry.return || 0,
          sentimentScore: sentimentEntry.avgSentiment || 0,
          volume: stockEntry.volume || 0
        });
      }
    });

    return aligned;
  }

  private calculateCorrelation(data: any[], lag: number): any {
    const n = data.length;
    if (n <= lag) return { correlation: 0, pValue: 1 };

    const stockReturns = data.slice(lag).map(d => d.stockReturn);
    const sentimentScores = data.slice(0, -lag).map(d => d.sentimentScore);

    // Calculate Pearson correlation
    const meanStock = stockReturns.reduce((sum, val) => sum + val, 0) / stockReturns.length;
    const meanSentiment = sentimentScores.reduce((sum, val) => sum + val, 0) / sentimentScores.length;

    let numerator = 0;
    let stockVariance = 0;
    let sentimentVariance = 0;

    for (let i = 0; i < stockReturns.length; i++) {
      const stockDiff = stockReturns[i] - meanStock;
      const sentimentDiff = sentimentScores[i] - meanSentiment;
      
      numerator += stockDiff * sentimentDiff;
      stockVariance += stockDiff * stockDiff;
      sentimentVariance += sentimentDiff * sentimentDiff;
    }

    const correlation = numerator / Math.sqrt(stockVariance * sentimentVariance);
    
    // Calculate p-value
    const t = correlation * Math.sqrt((n - 2) / (1 - correlation * correlation));
    const pValue = 2 * (1 - this.tDistribution(Math.abs(t), n - 2));

    return { correlation, pValue };
  }

  private tDistribution(t: number, df: number): number {
    // Simplified t-distribution CDF
    // In production, use a proper statistical library
    return 0.5 + (t * Math.exp(-0.5 * t * t)) / Math.sqrt(df * Math.PI);
  }

  private calculateSignificance(correlation: number, sampleSize: number): 'high' | 'medium' | 'low' | 'none' {
    const absCorrelation = Math.abs(correlation);
    
    if (absCorrelation >= 0.7) return 'high';
    if (absCorrelation >= 0.5) return 'medium';
    if (absCorrelation >= 0.3) return 'low';
    return 'none';
  }

  private generateInsights(correlation: any, data: any[]): string[] {
    const insights = [];
    const { correlation: corr, lag } = correlation;

    if (Math.abs(corr) >= 0.5) {
      insights.push(`Strong ${corr > 0 ? 'positive' : 'negative'} correlation detected`);
      
      if (lag > 0) {
        insights.push(`Sentiment leads price movements by ${lag} day(s)`);
      } else if (lag < 0) {
        insights.push(`Price movements lead sentiment by ${Math.abs(lag)} day(s)`);
      } else {
        insights.push('Sentiment and price move simultaneously');
      }
    } else if (Math.abs(corr) >= 0.3) {
      insights.push(`Moderate ${corr > 0 ? 'positive' : 'negative'} correlation detected`);
    } else {
      insights.push('Weak or no correlation detected');
    }

    // Analyze volume correlation
    const volumeCorrelation = this.calculateVolumeCorrelation(data);
    if (volumeCorrelation > 0.5) {
      insights.push('High sentiment periods correlate with increased trading volume');
    }

    // Analyze sentiment extremes
    const extremeSentimentDays = data.filter(d => Math.abs(d.sentimentScore) > 0.7).length;
    const extremeSentimentRatio = extremeSentimentDays / data.length;
    
    if (extremeSentimentRatio > 0.2) {
      insights.push('High sentiment volatility detected - consider risk management');
    }

    return insights;
  }

  private calculateVolumeCorrelation(data: any[]): number {
    const sentimentScores = data.map(d => d.sentimentScore);
    const volumes = data.map(d => Math.log(d.volume + 1)); // Log transform

    const meanSentiment = sentimentScores.reduce((sum, val) => sum + val, 0) / sentimentScores.length;
    const meanVolume = volumes.reduce((sum, val) => sum + val, 0) / volumes.length;

    let numerator = 0;
    let sentimentVariance = 0;
    let volumeVariance = 0;

    for (let i = 0; i < sentimentScores.length; i++) {
      const sentimentDiff = sentimentScores[i] - meanSentiment;
      const volumeDiff = volumes[i] - meanVolume;
      
      numerator += sentimentDiff * volumeDiff;
      sentimentVariance += sentimentDiff * sentimentDiff;
      volumeVariance += volumeDiff * volumeDiff;
    }

    return numerator / Math.sqrt(sentimentVariance * volumeVariance);
  }
}
```

### 5.3 4단계 검증 기준

| 검증 항목 | 성공 기준 | 측정 방법 |
|-----------|-----------|-----------|
| 소셜 데이터 수집 | 하루 1000개 이상 게시물 수집 | 데이터 수집 통계 |
| 감성 분석 정확도 | 80% 이상 정확도 | 수동 레이블링 비교 |
| 상관관계 분석 | 유의미한 상관관계 식별 | 통계적 유의성 검증 |
| 실시간 처리 | 5분 내 감성 업데이트 | 처리 지연 시간 측정 |
| 데이터 저장 | 수집된 데이터 99% 저장 | 데이터 무결성 검증 |

## 6. 5단계: 보안 및 접근성 (2-3주)

### 6.1 개요

**목표**: 보안 아키텍처 강화 및 WCAG 2.1 AA 준수

**핵심 성과**:
- 보안 취약점 90% 이상 해결
- WCAG 2.1 AA 준수율 95% 이상
- 다국어 지원 (한국어, 영어, 일본어)

### 6.2 상세 작업 계획

#### 6.2.1 보안 아키텍처 (1-2주)

**인증/인가 시스템**:
```typescript
// security/auth-service.ts
import jwt from 'jsonwebtoken';
import bcrypt from 'bcrypt';
import { User } from '../models/user';

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export interface JWTPayload {
  userId: string;
  email: string;
  role: string;
  permissions: string[];
}

export class AuthService {
  private jwtSecret: string;
  private refreshTokenSecret: string;
  private tokenExpiry: string;
  private refreshTokenExpiry: string;

  constructor() {
    this.jwtSecret = process.env.JWT_SECRET || 'default-secret';
    this.refreshTokenSecret = process.env.REFRESH_TOKEN_SECRET || 'refresh-secret';
    this.tokenExpiry = process.env.TOKEN_EXPIRY || '15m';
    this.refreshTokenExpiry = process.env.REFRESH_TOKEN_EXPIRY || '7d';
  }

  async register(userData: {
    email: string;
    password: string;
    firstName: string;
    lastName: string;
  }): Promise<{ user: User; tokens: AuthTokens }> {
    // Check if user already exists
    const existingUser = await User.findByEmail(userData.email);
    if (existingUser) {
      throw new Error('User already exists');
    }

    // Hash password
    const saltRounds = 12;
    const passwordHash = await bcrypt.hash(userData.password, saltRounds);

    // Create user
    const user = await User.create({
      email: userData.email,
      passwordHash,
      firstName: userData.firstName,
      lastName: userData.lastName,
      role: 'user',
      isActive: true
    });

    // Generate tokens
    const tokens = await this.generateTokens(user);

    return { user, tokens };
  }

  async login(email: string, password: string): Promise<{ user: User; tokens: AuthTokens }> {
    // Find user
    const user = await User.findByEmail(email);
    if (!user || !user.isActive) {
      throw new Error('Invalid credentials');
    }

    // Verify password
    const isValidPassword = await bcrypt.compare(password, user.passwordHash);
    if (!isValidPassword) {
      throw new Error('Invalid credentials');
    }

    // Update last login
    await user.updateLastLogin();

    // Generate tokens
    const tokens = await this.generateTokens(user);

    return { user, tokens };
  }

  async refreshToken(refreshToken: string): Promise<AuthTokens> {
    try {
      const payload = jwt.verify(refreshToken, this.refreshTokenSecret) as JWTPayload;
      
      // Find user
      const user = await User.findById(payload.userId);
      if (!user || !user.isActive) {
        throw new Error('Invalid refresh token');
      }

      // Generate new tokens
      return await this.generateTokens(user);
    } catch (error) {
      throw new Error('Invalid refresh token');
    }
  }

  async generateTokens(user: User): Promise<AuthTokens> {
    const payload: JWTPayload = {
      userId: user.id,
      email: user.email,
      role: user.role,
      permissions: await this.getUserPermissions(user)
    };

    const accessToken = jwt.sign(payload, this.jwtSecret, {
      expiresIn: this.tokenExpiry,
      issuer: 'insitechart',
      audience: 'insitechart-users'
    });

    const refreshToken = jwt.sign(
      { userId: user.id },
      this.refreshTokenSecret,
      {
        expiresIn: this.refreshTokenExpiry,
        issuer: 'insitechart'
      }
    );

    return { accessToken, refreshToken };
  }

  async verifyToken(token: string): Promise<JWTPayload> {
    try {
      const payload = jwt.verify(token, this.jwtSecret) as JWTPayload;
      
      // Check if user is still active
      const user = await User.findById(payload.userId);
      if (!user || !user.isActive) {
        throw new Error('User not found or inactive');
      }

      return payload;
    } catch (error) {
      throw new Error('Invalid token');
    }
  }

  async changePassword(userId: string, currentPassword: string, newPassword: string): Promise<void> {
    const user = await User.findById(userId);
    if (!user) {
      throw new Error('User not found');
    }

    // Verify current password
    const isValidPassword = await bcrypt.compare(currentPassword, user.passwordHash);
    if (!isValidPassword) {
      throw new Error('Current password is incorrect');
    }

    // Hash new password
    const saltRounds = 12;
    const passwordHash = await bcrypt.hash(newPassword, saltRounds);

    // Update password
    await user.updatePassword(passwordHash);
  }

  async resetPassword(email: string): Promise<string> {
    const user = await User.findByEmail(email);
    if (!user) {
      throw new Error('User not found');
    }

    // Generate reset token
    const resetToken = jwt.sign(
      { userId: user.id, type: 'password-reset' },
      this.jwtSecret,
      { expiresIn: '1h' }
    );

    // In production, send email with reset link
    console.log(`Password reset token for ${email}: ${resetToken}`);

    return resetToken;
  }

  async confirmPasswordReset(token: string, newPassword: string): Promise<void> {
    try {
      const payload = jwt.verify(token, this.jwtSecret) as any;
      
      if (payload.type !== 'password-reset') {
        throw new Error('Invalid reset token');
      }

      const user = await User.findById(payload.userId);
      if (!user) {
        throw new Error('User not found');
      }

      // Hash new password
      const saltRounds = 12;
      const passwordHash = await bcrypt.hash(newPassword, saltRounds);

      // Update password
      await user.updatePassword(passwordHash);
    } catch (error) {
      throw new Error('Invalid or expired reset token');
    }
  }

  private async getUserPermissions(user: User): Promise<string[]> {
    // Get permissions based on user role
    const rolePermissions = {
      admin: [
        'read:all-stocks',
        'write:all-stocks',
        'read:all-users',
        'write:all-users',
        'read:system-metrics',
        'write:system-config'
      ],
      user: [
        'read:stocks',
        'write:portfolio',
        'read:portfolio',
        'write:preferences',
        'read:preferences'
      ],
      guest: [
        'read:stocks'
      ]
    };

    return rolePermissions[user.role as keyof typeof rolePermissions] || [];
  }
}
```

**데이터 암호화 서비스**:
```typescript
// security/encryption-service.ts
import crypto from 'crypto';

export class EncryptionService {
  private algorithm = 'aes-256-gcm';
  private keyLength = 32;
  private ivLength = 16;
  private tagLength = 16;
  private encryptionKey: Buffer;

  constructor() {
    const keyString = process.env.ENCRYPTION_KEY || 'default-encryption-key-32-chars';
    this.encryptionKey = crypto.scryptSync(keyString, 'salt', this.keyLength);
  }

  encrypt(text: string): { encrypted: string; iv: string; tag: string } {
    const iv = crypto.randomBytes(this.ivLength);
    const cipher = crypto.createCipher(this.algorithm, this.encryptionKey);
    cipher.setAAD(Buffer.from('additional-data'));
    
    let encrypted = cipher.update(text, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    
    const tag = cipher.getAuthTag();
    
    return {
      encrypted,
      iv: iv.toString('hex'),
      tag: tag.toString('hex')
    };
  }

  decrypt(encryptedData: { encrypted: string; iv: string; tag: string }): string {
    const decipher = crypto.createDecipher(this.algorithm, this.encryptionKey);
    decipher.setAAD(Buffer.from('additional-data'));
    decipher.setAuthTag(Buffer.from(tag, 'hex'));
    
    let decrypted = decipher.update(encrypted, 'hex', 'utf8');
    decrypted += decipher.final('utf8');
    
    return decrypted;
  }

  hash(data: string): string {
    return crypto.createHash('sha256').update(data).digest('hex');
  }

  generateSecureToken(length = 32): string {
    return crypto.randomBytes(length).toString('hex');
  }

  async encryptPII(data: any): Promise<string> {
    const jsonString = JSON.stringify(data);
    const encrypted = this.encrypt(jsonString);
    
    // Store encrypted data with metadata
    const encryptedPackage = {
      data: encrypted.encrypted,
      iv: encrypted.iv,
      tag: encrypted.tag,
      algorithm: this.algorithm,
      timestamp: Date.now()
    };
    
    return Buffer.from(JSON.stringify(encryptedPackage)).toString('base64');
  }

  async decryptPII(encryptedData: string): Promise<any> {
    try {
      const encryptedPackage = JSON.parse(
        Buffer.from(encryptedData, 'base64').toString('utf8')
      );
      
      const decrypted = this.decrypt({
        encrypted: encryptedPackage.data,
        iv: encryptedPackage.iv,
        tag: encryptedPackage.tag
      });
      
      return JSON.parse(decrypted);
    } catch (error) {
      throw new Error('Failed to decrypt PII data');
    }
  }

  maskEmail(email: string): string {
    const [username, domain] = email.split('@');
    const maskedUsername = username.substring(0, 2) + '*'.repeat(username.length - 2);
    return `${maskedUsername}@${domain}`;
  }

  maskPhoneNumber(phone: string): string {
    return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2');
  }
}
```

#### 6.2.2 접근성 개선 (1주)

**키보드 내비게이션 컴포넌트**:
```typescript
// accessibility/keyboard-navigation.tsx
import React, { useEffect, useRef, useState } from 'react';

interface FocusTrapProps {
  children: React.ReactNode;
  isActive: boolean;
  onEscape?: () => void;
}

export const FocusTrap: React.FC<FocusTrapProps> = ({ 
  children, 
  isActive, 
  onEscape 
}) => {
  const containerRef = useRef<HTMLElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!isActive) return;

    const container = containerRef.current;
    if (!container) return;

    // Store current focus
    previousFocusRef.current = document.activeElement as HTMLElement;

    // Focus first focusable element
    const focusableElements = container.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    
    if (focusableElements.length > 0) {
      (focusableElements[0] as HTMLElement).focus();
    }

    // Handle tab navigation
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Tab') {
        event.preventDefault();
        
        const focusableElements = Array.from(
          container.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          )
        ) as HTMLElement[];
        
        const currentIndex = focusableElements.indexOf(
          document.activeElement as HTMLElement
        );
        
        let nextIndex;
        if (event.shiftKey) {
          // Shift + Tab: go to previous
          nextIndex = currentIndex <= 0 
            ? focusableElements.length - 1 
            : currentIndex - 1;
        } else {
          // Tab: go to next
          nextIndex = currentIndex >= focusableElements.length - 1 
            ? 0 
            : currentIndex + 1;
        }
        
        focusableElements[nextIndex]?.focus();
      } else if (event.key === 'Escape' && onEscape) {
        onEscape();
      }
    };

    container.addEventListener('keydown', handleKeyDown);

    return () => {
      container.removeEventListener('keydown', handleKeyDown);
      
      // Restore focus when trap is deactivated
      if (previousFocusRef.current) {
        previousFocusRef.current.focus();
      }
    };
  }, [isActive, onEscape]);

  return (
    <div 
      ref={containerRef}
      role="dialog"
      aria-modal={isActive}
      tabIndex={isActive ? -1 : undefined}
    >
      {children}
    </div>
  );
};

// Skip links component
export const SkipLinks: React.FC = () => {
  return (
    <>
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <a href="#navigation" className="skip-link">
        Skip to navigation
      </a>
      <a href="#search" className="skip-link">
        Skip to search
      </a>
    </>
  );
};
```

### 6.3 5단계 검증 기준

| 검증 항목 | 성공 기준 | 측정 방법 |
|-----------|-----------|-----------|
| 보안 취약점 | 90% 이상 해결 | 보안 감사 도구 |
| 인증/인가 | 모든 API 엔드포인트 보호 | 보안 테스트 |
| 데이터 암호화 | PII 데이터 100% 암호화 | 데이터 검증 |
| WCAG 준수율 | 95% 이상 | 접근성 테스트 |
| 키보드 내비게이션 | 모든 기능 키보드 접근 | 키보드 테스트 |
| 다국어 지원 | 3개 언어 완전 지원 | 언어 테스트 |

## 7. 6단계: 테스트 및 배포 자동화 (2-3주)

### 7.1 개요

**목표**: 포괄적인 테스트 프레임워크 및 CI/CD 파이프라인 구축

**핵심 성과**:
- 테스트 커버리지 80% 이상
- 자동화 배포 파이프라인
- 모니터링 및 알림 시스템

### 7.2 상세 작업 계획

#### 7.2.1 테스트 프레임워크 (1-2주)

**통합 테스트 설정**:
```typescript
// tests/integration/stock-api.test.ts
import request from 'supertest';
import { app } from '../../src/app';
import { setupTestDatabase, cleanupTestDatabase } from '../helpers/database';

describe('Stock API Integration Tests', () => {
  beforeAll(async () => {
    await setupTestDatabase();
  });

  afterAll(async () => {
    await cleanupTestDatabase();
  });

  describe('GET /api/stocks/search', () => {
    it('should return search results for valid query', async () => {
      const response = await request(app)
        .get('/api/stocks/search')
        .query({ q: 'AAPL' })
        .expect(200);

      expect(response.body).toHaveProperty('data');
      expect(Array.isArray(response.body.data)).toBe(true);
      expect(response.body.data.length).toBeGreaterThan(0);
    });

    it('should return empty array for invalid query', async () => {
      const response = await request(app)
        .get('/api/stocks/search')
        .query({ q: 'INVALID_SYMBOL' })
        .expect(200);

      expect(response.body).toHaveProperty('data');
      expect(Array.isArray(response.body.data)).toBe(true);
      expect(response.body.data.length).toBe(0);
    });
  });

  describe('GET /api/stocks/:symbol', () => {
    it('should return stock information for valid symbol', async () => {
      const response = await request(app)
        .get('/api/stocks/AAPL')
        .expect(200);

      expect(response.body).toHaveProperty('data');
      expect(response.body.data).toHaveProperty('symbol', 'AAPL');
      expect(response.body.data).toHaveProperty('name');
      expect(response.body.data).toHaveProperty('price');
    });

    it('should return 404 for invalid symbol', async () => {
      await request(app)
        .get('/api/stocks/INVALID')
        .expect(404);
    });
  });
});
```

**E2E 테스트 설정**:
```typescript
// tests/e2e/user-journey.test.ts
import { test, expect } from '@playwright/test';

test.describe('User Journey Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('complete stock analysis workflow', async ({ page }) => {
    // Search for a stock
    await page.fill('[data-testid="stock-search"]', 'AAPL');
    await page.press('[data-testid="stock-search"]', 'Enter');
    
    // Wait for results
    await page.waitForSelector('[data-testid="stock-results"]');
    
    // Click on first result
    await page.click('[data-testid="stock-result-0"]');
    
    // Verify stock details page
    await expect(page.locator('[data-testid="stock-symbol"]')).toContainText('AAPL');
    await expect(page.locator('[data-testid="stock-price"]')).toBeVisible();
    await expect(page.locator('[data-testid="stock-chart"]')).toBeVisible();
    
    // Test timeframe selection
    await page.click('[data-testid="timeframe-1d"]');
    await expect(page.locator('[data-testid="chart-period"]')).toContainText('1 Day');
    
    await page.click('[data-testid="timeframe-1w"]');
    await expect(page.locator('[data-testid="chart-period"]')).toContainText('1 Week');
    
    // Test technical indicators
    await page.click('[data-testid="indicator-rsi"]');
    await expect(page.locator('[data-testid="rsi-chart"]')).toBeVisible();
    
    // Test portfolio functionality
    await page.click('[data-testid="add-to-portfolio"]');
    await page.fill('[data-testid="portfolio-name"]', 'Test Portfolio');
    await page.fill('[data-testid="shares"]', '10');
    await page.click('[data-testid="save-portfolio"]');
    
    // Verify portfolio created
    await expect(page.locator('[data-testid="portfolio-success"]')).toBeVisible();
    
    // Navigate to portfolio page
    await page.click('[data-testid="portfolio-link"]');
    await expect(page.locator('[data-testid="portfolio-list"]')).toContainText('Test Portfolio');
  });

  test('real-time data updates', async ({ page }) => {
    // Navigate to stock page
    await page.goto('/stocks/AAPL');
    
    // Get initial price
    const initialPrice = await page.locator('[data-testid="stock-price"]').textContent();
    
    // Wait for real-time update (simulate)
    await page.waitForTimeout(6000); // Wait for WebSocket update
    
    // Verify price updated
    const updatedPrice = await page.locator('[data-testid="stock-price"]').textContent();
    expect(updatedPrice).not.toBe(initialPrice);
  });

  test('accessibility features', async ({ page }) => {
    // Test keyboard navigation
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toBeVisible();
    
    // Test skip links
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    await expect(page.locator('[data-testid="main-content"]')).toBeFocused();
    
    // Test screen reader announcements
    const announcements = await page.locator('[aria-live="polite"]').allTextContents();
    expect(announcements.length).toBeGreaterThan(0);
  });
});
```

#### 7.2.2 CI/CD 파이프라인 (1주)

**GitHub Actions 워크플로우**:
```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  NODE_VERSION: '18'
  PYTHON_VERSION: '3.11'
  DOCKER_REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup Node.js
      uses: actions/setup-node@v4
      with:
        node-version: ${{ env.NODE_VERSION }}
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json

    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
        cache: 'pip'
        cache-dependency-path: backend/requirements.txt

    - name: Install frontend dependencies
      run: |
        cd frontend
        npm ci

    - name: Install backend dependencies
      run: |
        cd backend
        pip install -r requirements.txt

    - name: Run frontend tests
      run: |
        cd frontend
        npm run test:unit
        npm run test:integration
        npm run test:e2e

    - name: Run backend tests
      run: |
        cd backend
        pytest tests/ --cov=. --cov-report=xml

    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
      with:
        files: ./frontend/coverage/lcov.info,./backend/coverage.xml
        flags: unittests
        name: codecov-umbrella

    - name: Run accessibility tests
      run: |
        cd frontend
        npm run test:a11y

    - name: Run security scan
      run: |
        cd frontend
        npm audit --audit-level high
        cd ../backend
        safety check

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Log in to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.DOCKER_REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.DOCKER_REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=ref,event=branch
          type=ref,event=pr
          type=sha,prefix={{branch}}-
          type=raw,value=latest,enable={{is_default_branch}}

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup kubectl
      uses: azure/setup-kubectl@v3
      with:
        version: 'v1.28.0'

    - name: Configure kubectl
      run: |
        echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig

    - name: Deploy to Kubernetes
      run: |
        export KUBECONFIG=kubeconfig
        kubectl set image deployment/frontend frontend=${{ env.DOCKER_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
        kubectl set image deployment/backend backend=${{ env.DOCKER_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
        kubectl rollout status deployment/frontend
        kubectl rollout status deployment/backend

    - name: Run smoke tests
      run: |
        cd frontend
        npm run test:smoke

    - name: Notify deployment
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ job.status }}
        channel: '#deployments'
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### 7.3 6단계 검증 기준

| 검증 항목 | 성공 기준 | 측정 방법 |
|-----------|-----------|-----------|
| 테스트 커버리지 | 80% 이상 | 커버리지 도구 |
| 자동화 배포 | 모든 변경사항 자동 배포 | CI/CD 파이프라인 |
| 모니터링 | 모든 서비스 모니터링 | 모니터링 대시보드 |
| 알림 시스템 | 5분 내 이슈 알림 | 알림 테스트 |
| 롤백 | 10분 내 롤백 가능 | 롤백 테스트 |

## 8. 결론

본 단계별 구현 계획은 6개월에 걸쳐 현재의 단순한 Streamlit 애플리케이션을 엔터프라이즈급 주식 분석 플랫폼으로 전환하기 위한 구체적인 실행 계획을 제시합니다.

각 단계는 명확한 목표와 검증 기준을 가지며, 이전 단계의 성공적 완료를 다음 단계의 선행 조건으로 하여 안정적인 시스템 전환을 보장합니다.

성공적인 구현을 위한 핵심 요소:
1. **단계적 접근**: 위험을 최소화하면서 안정적인 전환
2. **지속적인 테스트**: 각 단계별 품질 보증
3. **자동화**: 반복 작업의 자동화를 통한 효율성 증대
4. **모니터링**: 시스템 상태의 지속적인 추적 및 개선

이 계획을 통해 모든 스펙 요구사항을 충족하는 고품질의 주식 분석 플랫폼을 구축할 수 있을 것입니다.