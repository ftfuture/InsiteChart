# 실시간 데이터 동기화 구현 계획

## 1. 개요

본 문서는 주식 차트 분석 애플리케이션의 실시간 데이터 동기화 시스템을 구현하기 위한 상세한 계획을 제시합니다. WebSocket 연결, 이벤트 기반 아키텍처, 데이터 스트리밍, 충돌 해결, 오프라인 지원 등 다양한 실시간 데이터 처리 측면에서의 구현 전략을 다룹니다.

## 2. 실시간 데이터 아키텍처

### 2.1 실시간 데이터 동기화 계층 모델

```
┌─────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Real-time     │  │   Offline       │  │   Conflict    │ │
│  │   UI Updates     │  │   Support       │  │   Resolution  │ │
│  │   - WebSocket    │  │   - Cache       │  │   - Merging    │ │
│  │   - Event Bus    │  │   - Sync Queue  │  │   - Timestamp │ │
│  │   - State Mgmt   │  │   - Background  │  │   - Priority  │ │
│  │   - Optimistic   │  │     Sync        │  │   - Manual     │ │
│  │     Updates      │  │   - Reconnect   │  │     Resolution │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────┐
│                    Transport Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   WebSocket     │  │   Server Sent   │  │   HTTP Long   │ │
│  │   Connection    │  │   Events (SSE)   │  │   Polling     │ │
│  │   - Bi-direction│  │   - Server Push  │  │   - Fallback  │ │
│  │   - Heartbeat   │  │   - Auto Reconnect│  │   - Compatibility│ │
│  │   - Reconnect   │  │   - Event Stream │  │   - Simplicity│ │
│  │   - Queue Mgmt  │  │   - Filtering    │  │   - Reliability│ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────┐
│                    Processing Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Event         │  │   Data          │  │   Stream      │ │
│  │   Processing    │  │   Transformation │  │   Processing  │ │
│  │   - Validation   │  │   - Normalization│  │   - Filtering │ │
│  │   - Routing     │  │   - Enrichment   │  │   - Aggregation│ │
│  │   - Enrichment   │  │   - Deduplication│  │   - Windowing │ │
│  │   - Filtering    │  │   - Validation   │  │   - Join      │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────┐
│                    Data Layer                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   Real-time     │  │   Historical     │  │   Cache       │ │
│  │   Database      │  │   Database       │  │   Layer       │ │
│  │   - TimescaleDB │  │   - PostgreSQL   │  │   - Redis     │ │
│  │   - InfluxDB     │  │   - Data Lake    │  │   - Memory    │ │
│  │   - ClickHouse   │  │   - Analytics    │  │   - CDN       │ │
│  │   - Streaming    │  │   - Archival     │  │   - Edge      │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────┘
```

### 2.2 이벤트 기반 아키텍처

```typescript
// realtime/event-system.ts
export interface RealtimeEvent {
  id: string;
  type: string;
  timestamp: number;
  source: string;
  data: any;
  metadata?: {
    version?: number;
    priority?: 'low' | 'medium' | 'high' | 'critical';
    retryCount?: number;
    ttl?: number;
  };
}

export interface EventSubscriber {
  id: string;
  eventTypes: string[];
  handler: (event: RealtimeEvent) => void | Promise<void>;
  filter?: (event: RealtimeEvent) => boolean;
  options?: {
    batchSize?: number;
    batchTimeout?: number;
    maxRetries?: number;
  };
}

export class RealtimeEventBus {
  private subscribers: Map<string, EventSubscriber> = new Map();
  private eventQueue: RealtimeEvent[] = [];
  private processing = false;
  private eventHistory: Map<string, RealtimeEvent> = new Map();

  constructor(private maxHistorySize = 1000) {}

  subscribe(subscriber: EventSubscriber): () => void {
    this.subscribers.set(subscriber.id, subscriber);
    
    // Return unsubscribe function
    return () => {
      this.subscribers.delete(subscriber.id);
    };
  }

  async publish(event: RealtimeEvent): Promise<void> {
    // Add to history
    this.eventHistory.set(event.id, event);
    if (this.eventHistory.size > this.maxHistorySize) {
      const oldestKey = this.eventHistory.keys().next().value;
      this.eventHistory.delete(oldestKey);
    }

    // Add to queue
    this.eventQueue.push(event);
    
    if (!this.processing) {
      this.processQueue();
    }
  }

  private async processQueue(): Promise<void> {
    this.processing = true;
    
    while (this.eventQueue.length > 0) {
      const event = this.eventQueue.shift();
      if (!event) continue;

      // Find matching subscribers
      const matchingSubscribers = Array.from(this.subscribers.values()).filter(
        subscriber => subscriber.eventTypes.includes(event.type) &&
                     (!subscriber.filter || subscriber.filter(event))
      );

      // Process in parallel with error handling
      await Promise.allSettled(
        matchingSubscribers.map(subscriber => this.processEvent(subscriber, event))
      );
    }

    this.processing = false;
  }

  private async processEvent(subscriber: EventSubscriber, event: RealtimeEvent): Promise<void> {
    try {
      await subscriber.handler(event);
    } catch (error) {
      console.error(`Error processing event ${event.id} in subscriber ${subscriber.id}:`, error);
      
      // Implement retry logic if specified
      if (subscriber.options?.maxRetries && event.metadata?.retryCount) {
        if (event.metadata.retryCount < subscriber.options.maxRetries) {
          event.metadata.retryCount++;
          this.eventQueue.push(event);
        }
      }
    }
  }

  getEventHistory(eventType?: string, limit = 100): RealtimeEvent[] {
    const events = Array.from(this.eventHistory.values())
      .filter(event => !eventType || event.type === eventType)
      .sort((a, b) => b.timestamp - a.timestamp);
    
    return events.slice(0, limit);
  }

  clearHistory(): void {
    this.eventHistory.clear();
  }
}
```

## 3. WebSocket 연결 관리

### 3.1 WebSocket 클라이언트 구현
```typescript
// realtime/websocket-client.ts
export interface WebSocketConfig {
  url: string;
  protocols?: string[];
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  heartbeatTimeout?: number;
  messageQueueSize?: number;
}

export interface WebSocketMessage {
  type: string;
  payload: any;
  id?: string;
  timestamp?: number;
}

export class RealtimeWebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private heartbeatTimeoutTimer: NodeJS.Timeout | null = null;
  private messageQueue: WebSocketMessage[] = [];
  private eventListeners: Map<string, Function[]> = new Map();
  private connectionState: 'disconnected' | 'connecting' | 'connected' | 'reconnecting' = 'disconnected';

  constructor(private config: WebSocketConfig) {}

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.connectionState === 'connected' || this.connectionState === 'connecting') {
        resolve();
        return;
      }

      this.connectionState = 'connecting';
      
      try {
        this.ws = new WebSocket(this.config.url, this.config.protocols);
        
        this.ws.onopen = () => {
          this.connectionState = 'connected';
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          this.processMessageQueue();
          this.emit('connected');
          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data);
        };

        this.ws.onclose = (event) => {
          this.connectionState = 'disconnected';
          this.stopHeartbeat();
          this.emit('disconnected', { code: event.code, reason: event.reason });
          
          if (!event.wasClean && this.shouldReconnect()) {
            this.scheduleReconnect();
          }
        };

        this.ws.onerror = (error) => {
          this.connectionState = 'disconnected';
          this.emit('error', error);
          reject(error);
        };
      } catch (error) {
        this.connectionState = 'disconnected';
        reject(error);
      }
    });
  }

  disconnect(): void {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    this.connectionState = 'disconnected';
  }

  send(message: WebSocketMessage): void {
    if (this.connectionState === 'connected' && this.ws?.readyState === WebSocket.OPEN) {
      const messageWithMeta = {
        ...message,
        id: message.id || this.generateMessageId(),
        timestamp: message.timestamp || Date.now()
      };
      
      this.ws.send(JSON.stringify(messageWithMeta));
    } else {
      // Queue message for when connection is restored
      this.queueMessage(message);
    }
  }

  private handleMessage(data: string): void {
    try {
      const message: WebSocketMessage = JSON.parse(data);
      this.emit('message', message);
      this.emit(message.type, message.payload);
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
      this.emit('error', { type: 'parse_error', data, error });
    }
  }

  private startHeartbeat(): void {
    if (!this.config.heartbeatInterval) return;

    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.send({ type: 'heartbeat', payload: {} });
        
        // Set timeout to detect missed heartbeat
        if (this.config.heartbeatTimeout) {
          this.heartbeatTimeoutTimer = setTimeout(() => {
            console.warn('Heartbeat timeout, reconnecting...');
            this.ws?.close(1006, 'Heartbeat timeout');
          }, this.config.heartbeatTimeout);
        }
      }
    }, this.config.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    if (this.heartbeatTimeoutTimer) {
      clearTimeout(this.heartbeatTimeoutTimer);
      this.heartbeatTimeoutTimer = null;
    }
  }

  private shouldReconnect(): boolean {
    const maxAttempts = this.config.maxReconnectAttempts || 5;
    return this.reconnectAttempts < maxAttempts;
  }

  private scheduleReconnect(): void {
    this.connectionState = 'reconnecting';
    const interval = this.config.reconnectInterval || 1000;
    const backoffInterval = interval * Math.pow(2, this.reconnectAttempts);
    
    setTimeout(() => {
      this.reconnectAttempts++;
      this.connect().catch(error => {
        console.error('Reconnection failed:', error);
      });
    }, Math.min(backoffInterval, 30000)); // Cap at 30 seconds
  }

  private queueMessage(message: WebSocketMessage): void {
    const maxSize = this.config.messageQueueSize || 100;
    
    if (this.messageQueue.length >= maxSize) {
      // Remove oldest message
      this.messageQueue.shift();
    }
    
    this.messageQueue.push(message);
  }

  private processMessageQueue(): void {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      if (message) {
        this.send(message);
      }
    }
  }

  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // Event emitter methods
  on(event: string, listener: Function): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event)!.push(listener);
  }

  off(event: string, listener: Function): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(listener);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  private emit(event: string, data?: any): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(listener => {
        try {
          listener(data);
        } catch (error) {
          console.error(`Error in event listener for ${event}:`, error);
        }
      });
    }
  }

  getConnectionState(): string {
    return this.connectionState;
  }

  isConnected(): boolean {
    return this.connectionState === 'connected' && this.ws?.readyState === WebSocket.OPEN;
  }
}
```

### 3.2 WebSocket 서버 구현
```typescript
// realtime/websocket-server.ts
import { Server as SocketIOServer } from 'socket.io';
import { Server as HTTPServer } from 'http';
import { RedisClient } from '../cache/redis-client';

export interface WebSocketServerConfig {
  cors?: {
    origin: string | string[];
    credentials?: boolean;
  };
  adapter?: any;
  transports?: string[];
  pingTimeout?: number;
  pingInterval?: number;
}

export class RealtimeWebSocketServer {
  private io: SocketIOServer;
  private connectedClients: Map<string, any> = new Map();
  private subscriptions: Map<string, Set<string>> = new Map(); // event -> clientIds

  constructor(
    private httpServer: HTTPServer,
    private redisClient: RedisClient,
    private config: WebSocketServerConfig = {}
  ) {
    this.io = new SocketIOServer(httpServer, {
      cors: config.cors || {
        origin: "*",
        credentials: true
      },
      adapter: config.adapter,
      transports: config.transports || ['websocket', 'polling'],
      pingTimeout: config.pingTimeout || 60000,
      pingInterval: config.pingInterval || 25000
    });

    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    this.io.on('connection', (socket) => {
      console.log(`Client connected: ${socket.id}`);
      
      // Store client connection
      this.connectedClients.set(socket.id, {
        socket,
        connectedAt: Date.now(),
        subscriptions: new Set<string>()
      });

      // Handle client events
      socket.on('subscribe', (data) => {
        this.handleSubscription(socket.id, data);
      });

      socket.on('unsubscribe', (data) => {
        this.handleUnsubscription(socket.id, data);
      });

      socket.on('get_stock_data', (data) => {
        this.handleStockDataRequest(socket.id, data);
      });

      socket.on('disconnect', (reason) => {
        this.handleDisconnection(socket.id, reason);
      });

      // Send initial connection acknowledgment
      socket.emit('connected', {
        clientId: socket.id,
        serverTime: Date.now(),
        availableEvents: this.getAvailableEvents()
      });
    });
  }

  private handleSubscription(clientId: string, data: { events: string[] }): void {
    const client = this.connectedClients.get(clientId);
    if (!client) return;

    data.events.forEach(event => {
      // Add to client's subscriptions
      client.subscriptions.add(event);
      
      // Add to global subscriptions
      if (!this.subscriptions.has(event)) {
        this.subscriptions.set(event, new Set());
      }
      this.subscriptions.get(event)!.add(clientId);

      // Join socket.io room for the event
      client.socket.join(event);
    });

    // Acknowledge subscription
    client.socket.emit('subscribed', { events: data.events });
  }

  private handleUnsubscription(clientId: string, data: { events: string[] }): void {
    const client = this.connectedClients.get(clientId);
    if (!client) return;

    data.events.forEach(event => {
      // Remove from client's subscriptions
      client.subscriptions.delete(event);
      
      // Remove from global subscriptions
      const eventSubscribers = this.subscriptions.get(event);
      if (eventSubscribers) {
        eventSubscribers.delete(clientId);
        if (eventSubscribers.size === 0) {
          this.subscriptions.delete(event);
        }
      }

      // Leave socket.io room
      client.socket.leave(event);
    });

    // Acknowledge unsubscription
    client.socket.emit('unsubscribed', { events: data.events });
  }

  private async handleStockDataRequest(clientId: string, data: { symbol: string; timeframe?: string }): Promise<void> {
    const client = this.connectedClients.get(clientId);
    if (!client) return;

    try {
      // Get stock data from cache or API
      const stockData = await this.getStockData(data.symbol, data.timeframe);
      
      // Send data to client
      client.socket.emit('stock_data', {
        symbol: data.symbol,
        timeframe: data.timeframe,
        data: stockData,
        timestamp: Date.now()
      });

      // Subscribe to real-time updates for this symbol
      this.handleSubscription(clientId, { events: [`stock_update_${data.symbol}`] });
    } catch (error) {
      console.error(`Error getting stock data for ${data.symbol}:`, error);
      client.socket.emit('error', {
        type: 'stock_data_error',
        symbol: data.symbol,
        message: error.message
      });
    }
  }

  private handleDisconnection(clientId: string, reason: string): void {
    console.log(`Client disconnected: ${clientId}, reason: ${reason}`);
    
    const client = this.connectedClients.get(clientId);
    if (!client) return;

    // Remove from all subscriptions
    client.subscriptions.forEach(event => {
      const eventSubscribers = this.subscriptions.get(event);
      if (eventSubscribers) {
        eventSubscribers.delete(clientId);
        if (eventSubscribers.size === 0) {
          this.subscriptions.delete(event);
        }
      }
    });

    // Remove client
    this.connectedClients.delete(clientId);
  }

  // Public methods for broadcasting events
  broadcast(event: string, data: any): void {
    this.io.emit(event, {
      type: event,
      payload: data,
      timestamp: Date.now()
    });
  }

  broadcastToRoom(room: string, event: string, data: any): void {
    this.io.to(room).emit(event, {
      type: event,
      payload: data,
      timestamp: Date.now()
    });
  }

  broadcastStockUpdate(symbol: string, data: any): void {
    const event = `stock_update_${symbol}`;
    this.broadcastToRoom(event, event, { symbol, ...data });
  }

  // Helper methods
  private async getStockData(symbol: string, timeframe?: string): Promise<any> {
    // Implementation would fetch from cache or external API
    // This is a placeholder
    return {
      symbol,
      timeframe: timeframe || '1d',
      data: [],
      lastUpdated: Date.now()
    };
  }

  private getAvailableEvents(): string[] {
    return Array.from(this.subscriptions.keys());
  }

  // Statistics and monitoring
  getConnectedClientsCount(): number {
    return this.connectedClients.size;
  }

  getSubscriptionStats(): { [event: string]: number } {
    const stats: { [event: string]: number } = {};
    this.subscriptions.forEach((clients, event) => {
      stats[event] = clients.size;
    });
    return stats;
  }

  getClientInfo(clientId: string): any {
    const client = this.connectedClients.get(clientId);
    if (!client) return null;

    return {
      clientId,
      connectedAt: client.connectedAt,
      subscriptions: Array.from(client.subscriptions),
      connectionDuration: Date.now() - client.connectedAt
    };
  }
}
```

## 4. 실시간 데이터 스트리밍

### 4.1 주식 데이터 스트리밍 서비스
```typescript
// realtime/stock-streaming-service.ts
import { RealtimeEventBus } from './event-system';
import { RealtimeWebSocketServer } from './websocket-server';
import { StockAPIClient } from '../api/stock-api-client';
import { RedisClient } from '../cache/redis-client';

export interface StockUpdate {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: number;
  bid?: number;
  ask?: number;
  dayHigh?: number;
  dayLow?: number;
  open?: number;
  previousClose?: number;
}

export interface StreamingConfig {
  updateInterval: number;
  batchSize: number;
  maxSubscriptions: number;
  subscriptionTimeout: number;
}

export class StockStreamingService {
  private activeSubscriptions: Map<string, Set<string>> = new Map(); // symbol -> clientIds
  private updateIntervals: Map<string, NodeJS.Timeout> = new Map(); // symbol -> interval
  private lastPrices: Map<string, number> = new Map();

  constructor(
    private eventBus: RealtimeEventBus,
    private wsServer: RealtimeWebSocketServer,
    private stockAPI: StockAPIClient,
    private redisClient: RedisClient,
    private config: StreamingConfig
  ) {
    this.setupEventHandlers();
  }

  private setupEventHandlers(): void {
    // Subscribe to stock subscription requests
    this.eventBus.subscribe({
      id: 'stock-subscription-handler',
      eventTypes: ['stock_subscribe', 'stock_unsubscribe'],
      handler: this.handleSubscriptionEvent.bind(this)
    });
  }

  async subscribeToStock(clientId: string, symbol: string): Promise<void> {
    // Normalize symbol
    symbol = symbol.toUpperCase();

    // Check if already subscribed
    if (!this.activeSubscriptions.has(symbol)) {
      this.activeSubscriptions.set(symbol, new Set());
    }

    const subscribers = this.activeSubscriptions.get(symbol)!;
    
    // Check subscription limits
    if (subscribers.size >= this.config.maxSubscriptions) {
      throw new Error(`Maximum subscriptions reached for ${symbol}`);
    }

    // Add client to subscribers
    subscribers.add(clientId);

    // Start streaming if this is the first subscriber
    if (subscribers.size === 1) {
      this.startStreaming(symbol);
    }

    // Send current data immediately
    const currentData = await this.getCurrentStockData(symbol);
    if (currentData) {
      this.wsServer.broadcastStockUpdate(symbol, currentData);
    }

    console.log(`Client ${clientId} subscribed to ${symbol}. Total subscribers: ${subscribers.size}`);
  }

  async unsubscribeFromStock(clientId: string, symbol: string): Promise<void> {
    symbol = symbol.toUpperCase();

    const subscribers = this.activeSubscriptions.get(symbol);
    if (!subscribers) return;

    // Remove client from subscribers
    subscribers.delete(clientId);

    // Stop streaming if no more subscribers
    if (subscribers.size === 0) {
      this.stopStreaming(symbol);
      this.activeSubscriptions.delete(symbol);
    }

    console.log(`Client ${clientId} unsubscribed from ${symbol}. Remaining subscribers: ${subscribers.size}`);
  }

  private startStreaming(symbol: string): void {
    console.log(`Starting real-time streaming for ${symbol}`);

    // Clear any existing interval
    this.stopStreaming(symbol);

    // Set up update interval
    const interval = setInterval(async () => {
      try {
        await this.updateStockData(symbol);
      } catch (error) {
        console.error(`Error updating stock data for ${symbol}:`, error);
      }
    }, this.config.updateInterval);

    this.updateIntervals.set(symbol, interval);

    // Immediate first update
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
      // Get latest stock data
      const stockData = await this.stockAPI.getRealTimeData(symbol);
      
      if (!stockData) {
        console.warn(`No data available for ${symbol}`);
        return;
      }

      // Check if price actually changed
      const lastPrice = this.lastPrices.get(symbol);
      const currentPrice = stockData.price;

      if (lastPrice === currentPrice) {
        return; // No change, don't broadcast
      }

      this.lastPrices.set(symbol, currentPrice);

      // Create update event
      const update: StockUpdate = {
        symbol,
        price: stockData.price,
        change: stockData.change || 0,
        changePercent: stockData.changePercent || 0,
        volume: stockData.volume || 0,
        timestamp: Date.now(),
        bid: stockData.bid,
        ask: stockData.ask,
        dayHigh: stockData.dayHigh,
        dayLow: stockData.dayLow,
        open: stockData.open,
        previousClose: stockData.previousClose
      };

      // Broadcast to subscribed clients
      this.wsServer.broadcastStockUpdate(symbol, update);

      // Cache the latest data
      await this.cacheStockData(symbol, update);

      // Emit event for other services
      this.eventBus.publish({
        id: `stock_update_${symbol}_${Date.now()}`,
        type: 'stock_updated',
        timestamp: Date.now(),
        source: 'stock_streaming_service',
        data: update
      });

    } catch (error) {
      console.error(`Failed to update stock data for ${symbol}:`, error);
      
      // Emit error event
      this.eventBus.publish({
        id: `stock_error_${symbol}_${Date.now()}`,
        type: 'stock_update_error',
        timestamp: Date.now(),
        source: 'stock_streaming_service',
        data: { symbol, error: error.message }
      });
    }
  }

  private async getCurrentStockData(symbol: string): Promise<StockUpdate | null> {
    try {
      // Try to get from cache first
      const cached = await this.redisClient.get(`stock:${symbol}:current`);
      if (cached) {
        return JSON.parse(cached);
      }

      // If not in cache, fetch from API
      const stockData = await this.stockAPI.getRealTimeData(symbol);
      if (stockData) {
        const update: StockUpdate = {
          symbol,
          price: stockData.price,
          change: stockData.change || 0,
          changePercent: stockData.changePercent || 0,
          volume: stockData.volume || 0,
          timestamp: Date.now(),
          bid: stockData.bid,
          ask: stockData.ask,
          dayHigh: stockData.dayHigh,
          dayLow: stockData.dayLow,
          open: stockData.open,
          previousClose: stockData.previousClose
        };

        await this.cacheStockData(symbol, update);
        return update;
      }

      return null;
    } catch (error) {
      console.error(`Error getting current stock data for ${symbol}:`, error);
      return null;
    }
  }

  private async cacheStockData(symbol: string, data: StockUpdate): Promise<void> {
    try {
      // Cache current data
      await this.redisClient.setex(
        `stock:${symbol}:current`,
        300, // 5 minutes TTL
        JSON.stringify(data)
      );

      // Add to time-series data
      await this.redisClient.zadd(
        `stock:${symbol}:timeseries`,
        data.timestamp,
        JSON.stringify(data)
      );

      // Keep only last 1000 data points
      await this.redisClient.zremrangebyrank(
        `stock:${symbol}:timeseries`,
        0,
        -1001
      );

    } catch (error) {
      console.error(`Error caching stock data for ${symbol}:`, error);
    }
  }

  private async handleSubscriptionEvent(event: any): Promise<void> {
    const { type, data } = event;

    if (type === 'stock_subscribe') {
      await this.subscribeToStock(data.clientId, data.symbol);
    } else if (type === 'stock_unsubscribe') {
      await this.unsubscribeFromStock(data.clientId, data.symbol);
    }
  }

  // Public methods for monitoring and management
  getActiveSubscriptions(): { [symbol: string]: number } {
    const result: { [symbol: string]: number } = {};
    this.activeSubscriptions.forEach((subscribers, symbol) => {
      result[symbol] = subscribers.size;
    });
    return result;
  }

  getStreamingStatus(): { [symbol: string]: boolean } {
    const result: { [symbol: string]: boolean } = {};
    this.updateIntervals.forEach((_, symbol) => {
      result[symbol] = true;
    });
    return result;
  }

  async getStockHistory(symbol: string, limit = 100): Promise<StockUpdate[]> {
    try {
      const data = await this.redisClient.zrevrange(
        `stock:${symbol}:timeseries`,
        0,
        limit - 1
      );

      return data.map(item => JSON.parse(item));
    } catch (error) {
      console.error(`Error getting stock history for ${symbol}:`, error);
      return [];
    }
  }

  // Cleanup method
  shutdown(): void {
    // Clear all intervals
    this.updateIntervals.forEach(interval => clearInterval(interval));
    this.updateIntervals.clear();
    this.activeSubscriptions.clear();
  }
}
```

## 5. 오프라인 지원 및 동기화

### 5.1 오프라인 데이터 관리자
```typescript
// realtime/offline-manager.ts
export interface OfflineData {
  id: string;
  type: string;
  data: any;
  timestamp: number;
  syncStatus: 'pending' | 'syncing' | 'synced' | 'failed';
  retryCount: number;
  lastSyncAttempt?: number;
}

export interface SyncConfig {
  maxRetries: number;
  retryDelay: number;
  syncBatchSize: number;
  conflictResolution: 'client_wins' | 'server_wins' | 'manual';
}

export class OfflineDataManager {
  private offlineQueue: OfflineData[] = [];
  private isOnline = navigator.onLine;
  private syncInProgress = false;

  constructor(
    private config: SyncConfig,
    private eventBus: any
  ) {
    this.setupEventListeners();
    this.loadOfflineData();
  }

  private setupEventListeners(): void {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.handleOnlineStatusChange();
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
      this.handleOnlineStatusChange();
    });
  }

  private handleOnlineStatusChange(): void {
    this.eventBus.publish({
      id: `online_status_${Date.now()}`,
      type: 'online_status_changed',
      timestamp: Date.now(),
      source: 'offline_manager',
      data: { online: this.isOnline }
    });

    if (this.isOnline && this.offlineQueue.length > 0) {
      this.startSync();
    }
  }

  async addToOfflineQueue(data: any, type: string): Promise<string> {
    const offlineData: OfflineData = {
      id: this.generateId(),
      type,
      data,
      timestamp: Date.now(),
      syncStatus: 'pending',
      retryCount: 0
    };

    this.offlineQueue.push(offlineData);
    await this.saveOfflineData();

    return offlineData.id;
  }

  async removeFromOfflineQueue(id: string): Promise<void> {
    const index = this.offlineQueue.findIndex(item => item.id === id);
    if (index > -1) {
      this.offlineQueue.splice(index, 1);
      await this.saveOfflineData();
    }
  }

  async updateOfflineData(id: string, updates: Partial<OfflineData>): Promise<void> {
    const item = this.offlineQueue.find(item => item.id === id);
    if (item) {
      Object.assign(item, updates);
      await this.saveOfflineData();
    }
  }

  private async startSync(): Promise<void> {
    if (this.syncInProgress || !this.isOnline) return;

    this.syncInProgress = true;

    try {
      const pendingItems = this.offlineQueue.filter(
        item => item.syncStatus === 'pending' || item.syncStatus === 'failed'
      );

      // Process in batches
      for (let i = 0; i < pendingItems.length; i += this.config.syncBatchSize) {
        const batch = pendingItems.slice(i, i + this.config.syncBatchSize);
        await this.syncBatch(batch);
      }
    } catch (error) {
      console.error('Error during sync:', error);
    } finally {
      this.syncInProgress = false;
    }
  }

  private async syncBatch(batch: OfflineData[]): Promise<void> {
    const syncPromises = batch.map(item => this.syncItem(item));
    await Promise.allSettled(syncPromises);
  }

  private async syncItem(item: OfflineData): Promise<void> {
    try {
      await this.updateOfflineData(item.id, { syncStatus: 'syncing' });

      // Send to server
      const response = await this.sendToServer(item);

      if (response.success) {
        await this.removeFromOfflineQueue(item.id);
        this.emitSyncEvent('sync_success', item);
      } else {
        throw new Error(response.error || 'Sync failed');
      }
    } catch (error) {
      console.error(`Failed to sync item ${item.id}:`, error);
      
      const retryCount = item.retryCount + 1;
      const shouldRetry = retryCount <= this.config.maxRetries;
      
      await this.updateOfflineData(item.id, {
        syncStatus: shouldRetry ? 'failed' : 'pending',
        retryCount,
        lastSyncAttempt: Date.now()
      });

      if (shouldRetry) {
        // Schedule retry
        setTimeout(() => {
          this.syncItem(item);
        }, this.config.retryDelay * Math.pow(2, retryCount - 1)); // Exponential backoff
      }

      this.emitSyncEvent('sync_error', item, error);
    }
  }

  private async sendToServer(item: OfflineData): Promise<{ success: boolean; error?: string }> {
    // Implementation would send data to server
    // This is a placeholder
    try {
      // Simulate API call
      const response = await fetch('/api/sync', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          id: item.id,
          type: item.type,
          data: item.data,
          timestamp: item.timestamp
        })
      });

      if (response.ok) {
        return { success: true };
      } else {
        const errorData = await response.json();
        return { success: false, error: errorData.message };
      }
    } catch (error) {
      return { success: false, error: error.message };
    }
  }

  private emitSyncEvent(type: string, item: OfflineData, error?: any): void {
    this.eventBus.publish({
      id: `sync_${type}_${Date.now()}`,
      type: `sync_${type}`,
      timestamp: Date.now(),
      source: 'offline_manager',
      data: { item, error }
    });
  }

  private async saveOfflineData(): Promise<void> {
    try {
      localStorage.setItem('offline_queue', JSON.stringify(this.offlineQueue));
    } catch (error) {
      console.error('Error saving offline data:', error);
    }
  }

  private async loadOfflineData(): Promise<void> {
    try {
      const stored = localStorage.getItem('offline_queue');
      if (stored) {
        this.offlineQueue = JSON.parse(stored);
      }
    } catch (error) {
      console.error('Error loading offline data:', error);
      this.offlineQueue = [];
    }
  }

  private generateId(): string {
    return `offline_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  // Public methods
  getOfflineQueue(): OfflineData[] {
    return [...this.offlineQueue];
  }

  getPendingSyncCount(): number {
    return this.offlineQueue.filter(item => item.syncStatus === 'pending').length;
  }

  getFailedSyncCount(): number {
    return this.offlineQueue.filter(item => item.syncStatus === 'failed').length;
  }

  isSyncing(): boolean {
    return this.syncInProgress;
  }

  async clearOfflineQueue(): Promise<void> {
    this.offlineQueue = [];
    await this.saveOfflineData();
  }

  async retryFailedSyncs(): Promise<void> {
    const failedItems = this.offlineQueue.filter(item => item.syncStatus === 'failed');
    
    for (const item of failedItems) {
      await this.updateOfflineData(item.id, {
        syncStatus: 'pending',
        retryCount: 0
      });
    }

    if (this.isOnline) {
      await this.startSync();
    }
  }
}
```

## 6. 충돌 해결 및 데이터 일관성

### 6.1 충돌 해결 엔진
```typescript
// realtime/conflict-resolution.ts
export interface DataVersion {
  version: number;
  timestamp: number;
  author: string;
  checksum: string;
}

export interface ConflictResolutionStrategy {
  name: string;
  description: string;
  resolve: (clientData: any, serverData: any, conflict: any) => Promise<any>;
}

export class ConflictResolutionEngine {
  private strategies: Map<string, ConflictResolutionStrategy> = new Map();

  constructor() {
    this.initializeDefaultStrategies();
  }

  private initializeDefaultStrategies(): void {
    // Client wins strategy
    this.strategies.set('client_wins', {
      name: 'Client Wins',
      description: 'Client data takes precedence over server data',
      resolve: async (clientData, serverData) => clientData
    });

    // Server wins strategy
    this.strategies.set('server_wins', {
      name: 'Server Wins',
      description: 'Server data takes precedence over client data',
      resolve: async (clientData, serverData) => serverData
    });

    // Last write wins strategy
    this.strategies.set('last_write_wins', {
      name: 'Last Write Wins',
      description: 'Most recent data based on timestamp wins',
      resolve: async (clientData, serverData) => {
        return clientData.timestamp > serverData.timestamp ? clientData : serverData;
      }
    });

    // Merge strategy
    this.strategies.set('merge', {
      name: 'Merge',
      description: 'Intelligently merge client and server data',
      resolve: async (clientData, serverData, conflict) => {
        return this.mergeData(clientData, serverData, conflict.conflictingFields);
      }
    });

    // Manual resolution strategy
    this.strategies.set('manual', {
      name: 'Manual Resolution',
      description: 'Requires user intervention to resolve conflicts',
      resolve: async (clientData, serverData, conflict) => {
        // Return conflict information for manual resolution
        return {
          conflict: true,
          clientData,
          serverData,
          conflictingFields: conflict.conflictingFields,
          requiresUserAction: true
        };
      }
    });
  }

  async resolveConflict(
    clientData: any,
    serverData: any,
    strategyName: string
  ): Promise<any> {
    const strategy = this.strategies.get(strategyName);
    if (!strategy) {
      throw new Error(`Unknown conflict resolution strategy: ${strategyName}`);
    }

    // Detect conflicts
    const conflict = this.detectConflicts(clientData, serverData);
    
    if (!conflict.hasConflicts) {
      // No conflicts, return merged data
      return this.mergeData(clientData, serverData);
    }

    // Apply resolution strategy
    return await strategy.resolve(clientData, serverData, conflict);
  }

  private detectConflicts(clientData: any, serverData: any): any {
    const conflictingFields: string[] = [];
    const allKeys = new Set([...Object.keys(clientData), ...Object.keys(serverData)]);

    allKeys.forEach(key => {
      const clientValue = clientData[key];
      const serverValue = serverData[key];

      if (JSON.stringify(clientValue) !== JSON.stringify(serverValue)) {
        conflictingFields.push(key);
      }
    });

    return {
      hasConflicts: conflictingFields.length > 0,
      conflictingFields,
      conflictCount: conflictingFields.length
    };
  }

  private mergeData(clientData: any, serverData: any, conflictingFields?: string[]): any {
    const merged = { ...serverData };

    Object.keys(clientData).forEach(key => {
      if (conflictingFields && conflictingFields.includes(key)) {
        // Skip conflicting fields - they will be handled by the strategy
        return;
      }

      // If server doesn't have this field, use client value
      if (!(key in serverData)) {
        merged[key] = clientData[key];
      }
    });

    return merged;
  }

  // Strategy management
  addStrategy(name: string, strategy: ConflictResolutionStrategy): void {
    this.strategies.set(name, strategy);
  }

  getStrategy(name: string): ConflictResolutionStrategy | undefined {
    return this.strategies.get(name);
  }

  getAllStrategies(): ConflictResolutionStrategy[] {
    return Array.from(this.strategies.values());
  }

  // Advanced conflict resolution for specific data types
  async resolveStockDataConflict(
    clientData: any,
    serverData: any
  ): Promise<any> {
    // For stock data, we want to prioritize the most recent price data
    const merged = { ...serverData };

    // Always use the most recent price
    if (clientData.timestamp > serverData.timestamp) {
      merged.price = clientData.price;
      merged.timestamp = clientData.timestamp;
    }

    // Merge volume (take the higher value)
    merged.volume = Math.max(clientData.volume || 0, serverData.volume || 0);

    // Merge arrays (like historical data)
    if (clientData.historicalData && serverData.historicalData) {
      merged.historicalData = this.mergeTimeSeriesData(
        clientData.historicalData,
        serverData.historicalData
      );
    }

    return merged;
  }

  private mergeTimeSeriesData(clientData: any[], serverData: any[]): any[] {
    const mergedMap = new Map();

    // Add server data first
    serverData.forEach(item => {
      mergedMap.set(item.timestamp, item);
    });

    // Add/overwrite with client data
    clientData.forEach(item => {
      mergedMap.set(item.timestamp, item);
    });

    // Convert back to array and sort by timestamp
    return Array.from(mergedMap.values())
      .sort((a, b) => a.timestamp - b.timestamp);
  }
}
```

## 7. 성능 최적화 및 모니터링

### 7.1 실시간 성능 모니터링
```typescript
// realtime/performance-monitor.ts
export interface PerformanceMetrics {
  connectionCount: number;
  messageRate: number;
  latency: number;
  errorRate: number;
  memoryUsage: number;
  cpuUsage: number;
  timestamp: number;
}

export class RealtimePerformanceMonitor {
  private metrics: PerformanceMetrics[] = [];
  private messageCount = 0;
  private errorCount = 0;
  private lastMetricsTime = Date.now();
  private latencyMeasurements: number[] = [];

  constructor(
    private wsServer: any,
    private eventBus: any,
    private maxHistorySize = 1000
  ) {
    this.setupMonitoring();
  }

  private setupMonitoring(): void {
    // Collect metrics every 10 seconds
    setInterval(() => {
      this.collectMetrics();
    }, 10000);

    // Monitor message events
    this.eventBus.subscribe({
      id: 'performance_monitor',
      eventTypes: ['message_sent', 'message_received', 'error_occurred'],
      handler: this.handlePerformanceEvent.bind(this)
    });
  }

  private handlePerformanceEvent(event: any): void {
    switch (event.type) {
      case 'message_sent':
      case 'message_received':
        this.messageCount++;
        
        // Track latency if timestamp is available
        if (event.data.timestamp) {
          const latency = Date.now() - event.data.timestamp;
          this.latencyMeasurements.push(latency);
          
          // Keep only last 100 measurements
          if (this.latencyMeasurements.length > 100) {
            this.latencyMeasurements.shift();
          }
        }
        break;

      case 'error_occurred':
        this.errorCount++;
        break;
    }
  }

  private async collectMetrics(): Promise<void> {
    const now = Date.now();
    const timeDiff = (now - this.lastMetricsTime) / 1000; // in seconds

    const metrics: PerformanceMetrics = {
      connectionCount: this.wsServer.getConnectedClientsCount(),
      messageRate: this.messageCount / timeDiff,
      latency: this.calculateAverageLatency(),
      errorRate: this.errorCount / timeDiff,
      memoryUsage: this.getMemoryUsage(),
      cpuUsage: await this.getCPUUsage(),
      timestamp: now
    };

    this.metrics.push(metrics);
    
    // Keep only recent metrics
    if (this.metrics.length > this.maxHistorySize) {
      this.metrics.shift();
    }

    // Reset counters
    this.messageCount = 0;
    this.errorCount = 0;
    this.lastMetricsTime = now;

    // Emit metrics event
    this.eventBus.publish({
      id: `performance_metrics_${Date.now()}`,
      type: 'performance_metrics_collected',
      timestamp: now,
      source: 'performance_monitor',
      data: metrics
    });

    // Check for performance issues
    this.checkPerformanceThresholds(metrics);
  }

  private calculateAverageLatency(): number {
    if (this.latencyMeasurements.length === 0) return 0;
    
    const sum = this.latencyMeasurements.reduce((acc, val) => acc + val, 0);
    return sum / this.latencyMeasurements.length;
  }

  private getMemoryUsage(): number {
    if (typeof process !== 'undefined' && process.memoryUsage) {
      const usage = process.memoryUsage();
      return usage.heapUsed / 1024 / 1024; // MB
    }
    return 0;
  }

  private async getCPUUsage(): Promise<number> {
    // This would need to be implemented based on the environment
    // For now, return a placeholder
    return 0;
  }

  private checkPerformanceThresholds(metrics: PerformanceMetrics): void {
    const thresholds = {
      maxLatency: 1000, // 1 second
      maxErrorRate: 0.05, // 5%
      maxMemoryUsage: 512, // 512 MB
      maxMessageRate: 1000 // messages per second
    };

    if (metrics.latency > thresholds.maxLatency) {
      this.eventBus.publish({
        id: `performance_alert_latency_${Date.now()}`,
        type: 'performance_alert',
        timestamp: Date.now(),
        source: 'performance_monitor',
        data: {
          type: 'high_latency',
          value: metrics.latency,
          threshold: thresholds.maxLatency
        }
      });
    }

    if (metrics.errorRate > thresholds.maxErrorRate) {
      this.eventBus.publish({
        id: `performance_alert_error_rate_${Date.now()}`,
        type: 'performance_alert',
        timestamp: Date.now(),
        source: 'performance_monitor',
        data: {
          type: 'high_error_rate',
          value: metrics.errorRate,
          threshold: thresholds.maxErrorRate
        }
      });
    }

    if (metrics.memoryUsage > thresholds.maxMemoryUsage) {
      this.eventBus.publish({
        id: `performance_alert_memory_${Date.now()}`,
        type: 'performance_alert',
        timestamp: Date.now(),
        source: 'performance_monitor',
        data: {
          type: 'high_memory_usage',
          value: metrics.memoryUsage,
          threshold: thresholds.maxMemoryUsage
        }
      });
    }
  }

  // Public methods
  getCurrentMetrics(): PerformanceMetrics | null {
    return this.metrics.length > 0 ? this.metrics[this.metrics.length - 1] : null;
  }

  getMetricsHistory(limit = 100): PerformanceMetrics[] {
    return this.metrics.slice(-limit);
  }

  getAverageMetrics(timeRange = 60000): PerformanceMetrics | null {
    const cutoff = Date.now() - timeRange;
    const recentMetrics = this.metrics.filter(m => m.timestamp > cutoff);
    
    if (recentMetrics.length === 0) return null;

    const sum = recentMetrics.reduce((acc, metrics) => ({
      connectionCount: acc.connectionCount + metrics.connectionCount,
      messageRate: acc.messageRate + metrics.messageRate,
      latency: acc.latency + metrics.latency,
      errorRate: acc.errorRate + metrics.errorRate,
      memoryUsage: acc.memoryUsage + metrics.memoryUsage,
      cpuUsage: acc.cpuUsage + metrics.cpuUsage,
      timestamp: 0
    }), {
      connectionCount: 0,
      messageRate: 0,
      latency: 0,
      errorRate: 0,
      memoryUsage: 0,
      cpuUsage: 0,
      timestamp: 0
    });

    const count = recentMetrics.length;

    return {
      connectionCount: Math.round(sum.connectionCount / count),
      messageRate: sum.messageRate / count,
      latency: sum.latency / count,
      errorRate: sum.errorRate / count,
      memoryUsage: sum.memoryUsage / count,
      cpuUsage: sum.cpuUsage / count,
      timestamp: Date.now()
    };
  }
}
```

## 8. 결론

본 실시간 데이터 동기화 구현 계획은 완전한 실시간 데이터 처리 시스템을 구축하기 위한 상세한 전략을 제시합니다.

주요 특징:
1. **이벤트 기반 아키텍처**: 유연하고 확장 가능한 이벤트 시스템
2. **WebSocket 연결 관리**: 안정적인 실시간 통신 및 자동 재연결
3. **주식 데이터 스트리밍**: 실시간 주식 가격 업데이트 및 구독 관리
4. **오프라인 지원**: 오프라인 상태에서의 데이터 동기화 및 충돌 해결
5. **충돌 해결 엔진**: 다양한 전략을 통한 데이터 일관성 유지
6. **성능 모니터링**: 실시간 성능 지표 추적 및 경고 시스템

이 실시간 데이터 동기화 시스템을 통해 사용자는 항상 최신의 주식 정보를 실시간으로 받을 수 있으며, 네트워크 문제가 발생하더라도 데이터의 일관성을 유지할 수 있습니다.