import { Pool, PoolClient } from 'pg';
import { logger } from '@/utils/logger';
import config from '@/config';

export interface DatabaseConfig {
  host: string;
  port: number;
  database: string;
  username: string;
  password: string;
  ssl: boolean;
  maxConnections: number;
  idleTimeoutMillis: number;
  connectionTimeoutMillis: number;
}

class Database {
  private pool: Pool;
  private config: DatabaseConfig;

  constructor() {
    this.config = {
      host: config.database.host,
      port: config.database.port,
      database: config.database.name,
      username: config.database.user,
      password: config.database.password,
      ssl: config.database.ssl,
      maxConnections: config.database.maxConnections,
      idleTimeoutMillis: config.database.idleTimeout,
      connectionTimeoutMillis: config.database.connectionTimeout
    };

    this.pool = new Pool({
      host: this.config.host,
      port: this.config.port,
      database: this.config.database,
      user: this.config.username,
      password: this.config.password,
      ssl: this.config.ssl ? { rejectUnauthorized: false } : false,
      max: this.config.maxConnections,
      idleTimeoutMillis: this.config.idleTimeoutMillis,
      connectionTimeoutMillis: this.config.connectionTimeoutMillis,
      // Enable TimescaleDB extension
      // This will be checked on connection
    });

    // Handle pool errors
    this.pool.on('error', (err: Error) => {
      logger.error('Unexpected error on idle client', err);
    });

    // Log connection events
    this.pool.on('connect', (client: PoolClient) => {
      logger.debug('New client connected to database');
    });

    this.pool.on('remove', (client: PoolClient) => {
      logger.debug('Client removed from database pool');
    });
  }

  async connect(): Promise<void> {
    try {
      const client = await this.pool.connect();
      
      // Check if TimescaleDB is enabled
      const timescaleResult = await client.query(`
        SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'
      `);
      
      if (timescaleResult.rows.length === 0) {
        logger.warn('TimescaleDB extension is not enabled');
      } else {
        logger.info('TimescaleDB extension is enabled');
      }

      // Test basic query
      await client.query('SELECT NOW()');
      client.release();
      
      logger.info('Database connection established successfully');
    } catch (error) {
      logger.error('Failed to connect to database:', error);
      throw error;
    }
  }

  async getClient(): Promise<PoolClient> {
    return this.pool.connect();
  }

  async query<T = any>(text: string, params?: any[]): Promise<T[]> {
    const start = Date.now();
    const client = await this.pool.connect();
    
    try {
      const result = await client.query(text, params);
      const duration = Date.now() - start;
      
      logger.debug('Query executed', {
        query: text,
        params,
        duration,
        rowCount: result.rowCount
      });
      
      return result.rows;
    } catch (error) {
      logger.error('Query failed', {
        query: text,
        params,
        error: error instanceof Error ? error.message : String(error)
      });
      throw error;
    } finally {
      client.release();
    }
  }

  async queryOne<T = any>(text: string, params?: any[]): Promise<T | null> {
    const rows = await this.query<T>(text, params);
    return rows.length > 0 ? rows[0] : null;
  }

  async transaction<T>(callback: (client: PoolClient) => Promise<T>): Promise<T> {
    const client = await this.pool.connect();
    
    try {
      await client.query('BEGIN');
      const result = await callback(client);
      await client.query('COMMIT');
      return result;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async close(): Promise<void> {
    await this.pool.end();
    logger.info('Database connection pool closed');
  }

  async healthCheck(): Promise<boolean> {
    try {
      await this.query('SELECT 1');
      return true;
    } catch (error) {
      logger.error('Database health check failed:', error);
      return false;
    }
  }

  getPoolStats() {
    return {
      totalCount: this.pool.totalCount,
      idleCount: this.pool.idleCount,
      waitingCount: this.pool.waitingCount
    };
  }
}

// Create singleton instance
export const database = new Database();