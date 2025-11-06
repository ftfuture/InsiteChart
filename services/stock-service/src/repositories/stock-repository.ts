import { database } from '@/config/database';
import { Stock, StockPrice, StockInfo, ChartData, TechnicalIndicator } from '@/types';
import { logger } from '@/utils/logger';

export class StockRepository {
  async createStock(stock: Omit<Stock, 'symbol'> & { symbol: string }): Promise<Stock> {
    try {
      const query = `
        INSERT INTO stocks (symbol, name, sector, industry, market_cap, exchange, quote_type, long_name, short_name, currency, country)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (symbol) 
        DO UPDATE SET
          name = EXCLUDED.name,
          sector = EXCLUDED.sector,
          industry = EXCLUDED.industry,
          market_cap = EXCLUDED.market_cap,
          exchange = EXCLUDED.exchange,
          quote_type = EXCLUDED.quote_type,
          long_name = EXCLUDED.long_name,
          short_name = EXCLUDED.short_name,
          currency = EXCLUDED.currency,
          country = EXCLUDED.country,
          updated_at = CURRENT_TIMESTAMP
        RETURNING *
      `;

      const result = await database.queryOne<Stock>(query, [
        stock.symbol,
        stock.name,
        stock.sector,
        stock.industry,
        stock.marketCap,
        stock.exchange,
        stock.quoteType,
        stock.longName,
        stock.shortName,
        stock.currency,
        stock.country
      ]);

      logger.logDatabase('CREATE/UPDATE', 'stocks', 0, 1);
      return result!;
    } catch (error) {
      logger.error('Failed to create/update stock', { stock, error });
      throw error;
    }
  }

  async getStockBySymbol(symbol: string): Promise<Stock | null> {
    try {
      const query = 'SELECT * FROM stocks WHERE symbol = $1';
      const result = await database.queryOne<Stock>(query, [symbol.toUpperCase()]);
      return result;
    } catch (error) {
      logger.error('Failed to get stock by symbol', { symbol, error });
      throw error;
    }
  }

  async searchStocks(query: string, limit = 10): Promise<Stock[]> {
    try {
      const searchQuery = `%${query.toUpperCase()}%`;
      const sql = `
        SELECT * FROM stocks 
        WHERE UPPER(symbol) LIKE $1 
           OR UPPER(name) LIKE $1 
           OR UPPER(sector) LIKE $1 
           OR UPPER(industry) LIKE $1
        ORDER BY 
          CASE 
            WHEN UPPER(symbol) = $2 THEN 1
            WHEN UPPER(symbol) LIKE $1 THEN 2
            WHEN UPPER(name) LIKE $1 THEN 3
            ELSE 4
          END,
          market_cap DESC NULLS LAST
        LIMIT $3
      `;

      const results = await database.query<Stock>(sql, [
        searchQuery,
        query.toUpperCase(),
        limit
      ]);

      logger.logDatabase('SEARCH', 'stocks', 0, results.length);
      return results;
    } catch (error) {
      logger.error('Failed to search stocks', { query, error });
      throw error;
    }
  }

  async saveStockPrices(prices: StockPrice[]): Promise<void> {
    if (prices.length === 0) return;

    try {
      await database.transaction(async (client) => {
        for (const price of prices) {
          const query = `
            INSERT INTO stock_prices (time, symbol, open, high, low, close, volume, adj_close)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (time, symbol) 
            DO UPDATE SET
              open = EXCLUDED.open,
              high = EXCLUDED.high,
              low = EXCLUDED.low,
              close = EXCLUDED.close,
              volume = EXCLUDED.volume,
              adj_close = EXCLUDED.adj_close
          `;
          
          await client.query(query, [
            price.time,
            price.symbol,
            price.open,
            price.high,
            price.low,
            price.close,
            price.volume,
            price.adjClose
          ]);
        }
      });

      logger.logDatabase('BATCH INSERT', 'stock_prices', 0, prices.length);
    } catch (error) {
      logger.error('Failed to save stock prices', { count: prices.length, error });
      throw error;
    }
  }

  async getStockPrices(symbol: string, startDate?: Date, endDate?: Date, limit = 1000): Promise<StockPrice[]> {
    try {
      let query = `
        SELECT time, symbol, open, high, low, close, volume, adj_close
        FROM stock_prices
        WHERE symbol = $1
      `;
      const params: any[] = [symbol.toUpperCase()];

      if (startDate) {
        query += ` AND time >= $${params.length + 1}`;
        params.push(startDate);
      }

      if (endDate) {
        query += ` AND time <= $${params.length + 1}`;
        params.push(endDate);
      }

      query += ` ORDER BY time DESC LIMIT $${params.length + 1}`;
      params.push(limit);

      const results = await database.query<StockPrice>(query, params);
      
      // Return in ascending order for charts
      const sortedResults = results.reverse();
      
      logger.logDatabase('SELECT', 'stock_prices', 0, sortedResults.length);
      return sortedResults;
    } catch (error) {
      logger.error('Failed to get stock prices', { symbol, startDate, endDate, error });
      throw error;
    }
  }

  async getLatestPrice(symbol: string): Promise<StockPrice | null> {
    try {
      const query = `
        SELECT time, symbol, open, high, low, close, volume, adj_close
        FROM stock_prices
        WHERE symbol = $1
        ORDER BY time DESC
        LIMIT 1
      `;

      const result = await database.queryOne<StockPrice>(query, [symbol.toUpperCase()]);
      return result;
    } catch (error) {
      logger.error('Failed to get latest price', { symbol, error });
      throw error;
    }
  }

  async saveTechnicalIndicator(indicator: TechnicalIndicator): Promise<void> {
    try {
      const query = `
        INSERT INTO technical_indicators (symbol, indicator_type, timestamp, value, metadata)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (symbol, indicator_type, timestamp)
        DO UPDATE SET
          value = EXCLUDED.value,
          metadata = EXCLUDED.metadata
      `;

      await database.query(query, [
        indicator.symbol,
        indicator.indicatorType,
        indicator.timestamp,
        indicator.value,
        JSON.stringify(indicator.metadata)
      ]);

      logger.logDatabase('INSERT/UPDATE', 'technical_indicators', 0, 1);
    } catch (error) {
      logger.error('Failed to save technical indicator', { indicator, error });
      throw error;
    }
  }

  async getTechnicalIndicators(
    symbol: string, 
    indicatorType: string, 
    startDate?: Date, 
    endDate?: Date,
    limit = 100
  ): Promise<TechnicalIndicator[]> {
    try {
      let query = `
        SELECT id, symbol, indicator_type, timestamp, value, metadata
        FROM technical_indicators
        WHERE symbol = $1 AND indicator_type = $2
      `;
      const params: any[] = [symbol.toUpperCase(), indicatorType];

      if (startDate) {
        query += ` AND timestamp >= $${params.length + 1}`;
        params.push(startDate);
      }

      if (endDate) {
        query += ` AND timestamp <= $${params.length + 1}`;
        params.push(endDate);
      }

      query += ` ORDER BY timestamp DESC LIMIT $${params.length + 1}`;
      params.push(limit);

      const results = await database.query<TechnicalIndicator>(query, params);
      
      // Parse metadata JSON for each result
      const parsedResults = results.map(result => ({
        ...result,
        metadata: result.metadata ? JSON.parse(result.metadata as unknown as string) : undefined
      }));
      
      logger.logDatabase('SELECT', 'technical_indicators', 0, parsedResults.length);
      return parsedResults.reverse(); // Return in chronological order
    } catch (error) {
      logger.error('Failed to get technical indicators', { symbol, indicatorType, error });
      throw error;
    }
  }

  async getTopGainers(limit = 10): Promise<Array<{ symbol: string; name: string; change: number; changePercent: number }>> {
    try {
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
          s.name,
          lp.close as current_price,
          pp.previous_close,
          (lp.close - pp.previous_close) as change,
          ((lp.close - pp.previous_close) / pp.previous_close * 100) as change_percent
        FROM latest_prices lp
        LEFT JOIN previous_prices pp ON lp.symbol = pp.symbol
        LEFT JOIN stocks s ON lp.symbol = s.symbol
        WHERE pp.previous_close IS NOT NULL
        ORDER BY change_percent DESC
        LIMIT $1
      `;

      const results = await database.query(query, [limit]);
      logger.logDatabase('SELECT', 'stock_prices', 0, results.length);
      return results;
    } catch (error) {
      logger.error('Failed to get top gainers', { limit, error });
      throw error;
    }
  }

  async getTopLosers(limit = 10): Promise<Array<{ symbol: string; name: string; change: number; changePercent: number }>> {
    try {
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
          s.name,
          lp.close as current_price,
          pp.previous_close,
          (lp.close - pp.previous_close) as change,
          ((lp.close - pp.previous_close) / pp.previous_close * 100) as change_percent
        FROM latest_prices lp
        LEFT JOIN previous_prices pp ON lp.symbol = pp.symbol
        LEFT JOIN stocks s ON lp.symbol = s.symbol
        WHERE pp.previous_close IS NOT NULL
        ORDER BY change_percent ASC
        LIMIT $1
      `;

      const results = await database.query(query, [limit]);
      logger.logDatabase('SELECT', 'stock_prices', 0, results.length);
      return results;
    } catch (error) {
      logger.error('Failed to get top losers', { limit, error });
      throw error;
    }
  }

  async getMostActive(limit = 10): Promise<Array<{ symbol: string; name: string; volume: number }>> {
    try {
      const query = `
        SELECT 
          sp.symbol,
          s.name,
          sp.volume,
          sp.time
        FROM stock_prices sp
        JOIN stocks s ON sp.symbol = s.symbol
        WHERE sp.time >= NOW() - INTERVAL '1 day'
        ORDER BY sp.volume DESC
        LIMIT $1
      `;

      const results = await database.query(query, [limit]);
      logger.logDatabase('SELECT', 'stock_prices', 0, results.length);
      return results;
    } catch (error) {
      logger.error('Failed to get most active stocks', { limit, error });
      throw error;
    }
  }

  async deleteOldData(daysToKeep = 365): Promise<void> {
    try {
      const query = `
        DELETE FROM stock_prices
        WHERE time < NOW() - INTERVAL '${daysToKeep} days'
      `;

      const result = await database.query(query);
      logger.logDatabase('DELETE', 'stock_prices', 0, result.length);
      logger.info(`Deleted ${result.length} old stock price records`);
    } catch (error) {
      logger.error('Failed to delete old data', { daysToKeep, error });
      throw error;
    }
  }
}

export const stockRepository = new StockRepository();