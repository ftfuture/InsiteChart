import dotenv from 'dotenv';
import path from 'path';

// Load environment variables
dotenv.config({ path: path.join(__dirname, '../../.env') });

export const config = {
  server: {
    port: parseInt(process.env.PORT || '3001'),
    env: process.env.NODE_ENV || 'development',
    logLevel: process.env.LOG_LEVEL || 'info'
  },

  database: {
    host: process.env.DB_HOST || 'localhost',
    port: parseInt(process.env.DB_PORT || '5432'),
    name: process.env.DB_NAME || 'stock_service',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || 'password',
    ssl: process.env.DB_SSL === 'true',
    maxConnections: parseInt(process.env.DB_MAX_CONNECTIONS || '20'),
    idleTimeout: parseInt(process.env.DB_IDLE_TIMEOUT || '30000'),
    connectionTimeout: parseInt(process.env.DB_CONNECTION_TIMEOUT || '10000')
  },

  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379'),
    password: process.env.REDIS_PASSWORD || '',
    db: parseInt(process.env.REDIS_DB || '0'),
    ttl: parseInt(process.env.REDIS_TTL || '3600')
  },

  cache: {
    ttl: {
      default: parseInt(process.env.CACHE_TTL_DEFAULT || '300'),
      stockInfo: parseInt(process.env.CACHE_TTL_STOCK_INFO || '1800'),
      chartData: parseInt(process.env.CACHE_TTL_CHART_DATA || '300')
    }
  },

  externalApis: {
    yahooFinance: {
      timeout: parseInt(process.env.YAHOO_FINANCE_API_TIMEOUT || '10000')
    }
  },

  rateLimit: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '900000'), // 15 minutes
    maxRequests: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS || '100')
  },

  security: {
    jwt: {
      secret: process.env.JWT_SECRET || 'default-jwt-secret',
      expiresIn: process.env.JWT_EXPIRES_IN || '15m'
    },
    refreshToken: {
      secret: process.env.REFRESH_TOKEN_SECRET || 'default-refresh-secret',
      expiresIn: process.env.REFRESH_TOKEN_EXPIRES_IN || '7d'
    }
  },

  cors: {
    origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
    credentials: process.env.CORS_CREDENTIALS === 'true'
  },

  monitoring: {
    enabled: process.env.METRICS_ENABLED === 'true',
    healthCheckInterval: parseInt(process.env.HEALTH_CHECK_INTERVAL || '30000')
  }
};

// Validate required environment variables
const requiredEnvVars = [
  'DB_HOST',
  'DB_NAME',
  'DB_USER',
  'DB_PASSWORD'
];

const missingEnvVars = requiredEnvVars.filter(envVar => !process.env[envVar]);

if (missingEnvVars.length > 0) {
  throw new Error(`Missing required environment variables: ${missingEnvVars.join(', ')}`);
}

// Log configuration (without sensitive data)
console.log('Configuration loaded:', {
  server: {
    port: config.server.port,
    env: config.server.env,
    logLevel: config.server.logLevel
  },
  database: {
    host: config.database.host,
    port: config.database.port,
    name: config.database.name,
    ssl: config.database.ssl
  },
  redis: {
    host: config.redis.host,
    port: config.redis.port,
    db: config.redis.db
  }
});

export default config;