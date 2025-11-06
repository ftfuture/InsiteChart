export interface Stock {
  symbol: string;
  name: string;
  sector?: string;
  industry?: string;
  marketCap?: number;
  exchange?: string;
  quoteType: string;
  longName?: string;
  shortName?: string;
  currency?: string;
  country?: string;
}

export interface StockPrice {
  time: Date;
  symbol: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjClose?: number;
}

export interface TechnicalIndicator {
  id: string;
  symbol: string;
  indicatorType: string;
  timestamp: Date;
  value: number;
  metadata?: Record<string, any>;
}

export interface StockSearchResult {
  symbol: string;
  name: string;
  type: string;
  exchange: string;
  sector?: string;
  industry?: string;
  score?: number;
}

export interface StockInfo {
  symbol: string;
  name: string;
  currentPrice: number;
  previousClose: number;
  open: number;
  dayHigh: number;
  dayLow: number;
  volume: number;
  marketCap: number;
  fiftyTwoWeekHigh: number;
  fiftyTwoWeekLow: number;
  trailingPE?: number;
  trailingEps?: number;
  dividendYield?: number;
  beta?: number;
  currency: string;
  exchange: string;
  quoteType: string;
  sector?: string;
  industry?: string;
  longName?: string;
  shortName?: string;
}

export interface ChartData {
  timestamp: Date;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjClose?: number;
  indicators?: {
    sma?: Record<string, number>;
    ema?: Record<string, number>;
    bb?: {
      upper: number;
      middle: number;
      lower: number;
    };
    rsi?: number;
    macd?: {
      macd: number;
      signal: number;
      histogram: number;
    };
  };
}

export interface Timeframe {
  label: string;
  value: string;
  period: string;
}

export interface ChartRequest {
  symbol: string;
  period: string;
  interval?: string;
  indicators?: {
    sma?: number[];
    ema?: number[];
    bb?: { period: number; stdDev: number };
    rsi?: { period: number };
    macd?: { fast: number; slow: number; signal: number };
  };
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  timestamp: string;
}

export interface PaginationParams {
  page?: number;
  limit?: number;
  offset?: number;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

export interface CacheOptions {
  ttl?: number;
  tags?: string[];
}

export interface ServiceHealth {
  status: 'healthy' | 'unhealthy' | 'degraded';
  timestamp: string;
  version: string;
  uptime: number;
  checks: {
    database: 'pass' | 'fail';
    cache: 'pass' | 'fail';
    externalApi: 'pass' | 'fail';
  };
  metrics?: {
    responseTime: number;
    requestCount: number;
    errorRate: number;
  };
}