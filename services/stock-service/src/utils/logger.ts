import winston from 'winston';
import config from '@/config';

const logFormat = winston.format.combine(
  winston.format.timestamp(),
  winston.format.errors({ stack: true }),
  winston.format.json(),
  winston.format.prettyPrint()
);

const consoleFormat = winston.format.combine(
  winston.format.colorize(),
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
  winston.format.printf(({ timestamp, level, message, stack, ...meta }: any) => {
    let msg = `${timestamp} [${level}]: ${message}`;
    
    if (Object.keys(meta).length > 0) {
      msg += ` ${JSON.stringify(meta)}`;
    }
    
    if (stack) {
      msg += `\n${stack}`;
    }
    
    return msg;
  })
);

export const logger = winston.createLogger({
  level: config.server.logLevel,
  format: logFormat,
  defaultMeta: {
    service: 'stock-service',
    version: '1.0.0'
  },
  transports: [
    new winston.transports.File({
      filename: 'logs/error.log',
      level: 'error',
      maxsize: 5242880, // 5MB
      maxFiles: 5
    }),
    new winston.transports.File({
      filename: 'logs/combined.log',
      maxsize: 5242880, // 5MB
      maxFiles: 5
    })
  ],
  // Handle uncaught exceptions and rejections
  exceptionHandlers: [
    new winston.transports.File({ filename: 'logs/exceptions.log' })
  ],
  rejectionHandlers: [
    new winston.transports.File({ filename: 'logs/rejections.log' })
  ]
});

// Add console transport for development
if (config.server.env !== 'production') {
  logger.add(new winston.transports.Console({
    format: consoleFormat
  }));
}

// Create a stream object for Morgan HTTP logging
export const loggerStream = {
  write: (message: string) => {
    logger.info(message.trim());
  }
};

// Helper functions for structured logging
export const logRequest = (req: any, res: any, responseTime?: number) => {
  logger.info('HTTP Request', {
    method: req.method,
    url: req.url,
    statusCode: res.statusCode,
    responseTime,
    userAgent: req.get('User-Agent'),
    ip: req.ip || req.connection.remoteAddress
  });
};

export const logError = (error: Error, context?: any) => {
  logger.error('Application Error', {
    message: error.message,
    stack: error.stack,
    context
  });
};

export const logPerformance = (operation: string, duration: number, metadata?: any) => {
  logger.info('Performance Metric', {
    operation,
    duration,
    metadata
  });
};

export const logCache = (operation: string, key: string, hit: boolean, duration?: number) => {
  logger.debug('Cache Operation', {
    operation,
    key,
    hit,
    duration
  });
};

export const logDatabase = (operation: string, table: string, duration: number, rowCount?: number) => {
  logger.debug('Database Operation', {
    operation,
    table,
    duration,
    rowCount
  });
};

export const logExternalApi = (service: string, endpoint: string, method: string, statusCode: number, duration: number) => {
  logger.info('External API Call', {
    service,
    endpoint,
    method,
    statusCode,
    duration
  });
};