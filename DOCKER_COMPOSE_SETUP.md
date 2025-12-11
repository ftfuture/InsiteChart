# Docker Compose Setup Guide

Complete setup guide for running InsiteChart with Docker Compose.

## Overview

This Docker Compose configuration includes:
- **5 Microservices**: Backend, Data Collector, Analytics, Gateway, Frontend
- **2 Infrastructure Services**: PostgreSQL Database, Redis Cache
- **Development & Production**: Separate configurations for each environment
- **Health Checks**: Automated health monitoring for all services
- **Networking**: Isolated network for inter-service communication

## Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM available
- 2GB disk space

### Development Mode (Recommended)

```bash
# 1. Clone repository
cd /path/to/InsiteChart

# 2. Setup environment
cp .env.example .env.docker

# 3. Start services
./scripts/docker-compose-up.sh dev

# 4. Access services
- API Gateway:  http://localhost:8080
- Backend:      http://localhost:8000
- Frontend:     http://localhost:8501
```

### Production Mode

```bash
# 1. Setup production environment
cp .env.example .env.docker
# Edit .env.docker with production values

# 2. Start services
./scripts/docker-compose-up.sh prod

# 3. Access gateway
curl https://api.insitechart.example.com/health
```

## Configuration Files

### docker-compose.yml
Main service definitions including:
- Service images and builds
- Port mappings
- Environment variables
- Health checks
- Dependencies
- Networks and volumes

### docker-compose.override.yml
Development overrides (auto-loaded):
- Volume mounts for hot reload
- Debug mode enabled
- Additional logging
- Development resource limits

### docker-compose.prod.yml
Production overrides (explicitly loaded):
- Optimized resource limits
- Production logging levels
- Restart policies
- Memory management

### .env.docker
Environment configuration:
- Database credentials
- Redis password
- JWT secret
- Rate limiting
- Service URLs

## Service Architecture

```
                    User/Client
                         |
                    (Port 8080)
                         |
                    ┌────▼────┐
                    │ Gateway  │──── Health Check
                    └─┬──┬──┬──┘
                      │  │  │
            ┌─────────┘  │  └──────────┐
            │            │             │
      (8000)|       (8001)|       (8002)|
            │            │             │
      ┌─────▼──┐   ┌─────▼──┐   ┌────▼────┐
      │Backend │   │DataColl│   │Analytics │
      └────┬───┘   └────┬───┘   └────┬────┘
           │            │             │
           └────┬───────┴─────┬───────┘
                │             │
           ┌────▼───┐   ┌────▼──┐
           │PostgreSQL  │Redis  │
           └──────────┘ └───────┘
```

## Common Commands

### View Service Status

```bash
# All services
docker-compose ps

# Specific service
docker-compose ps backend

# Health check
curl http://localhost:8080/health
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f analytics

# Last 100 lines
docker-compose logs --tail=100

# Filter by pattern
docker-compose logs | grep ERROR
```

### Execute Commands in Container

```bash
# Shell access
docker-compose exec backend bash

# Run command
docker-compose exec postgres psql -U insitechart -d insitechart

# View database
docker-compose exec postgres psql -U insitechart -d insitechart -c "\dt"
```

### Database Management

```bash
# Connect to database
docker-compose exec postgres psql -U insitechart -d insitechart

# Backup database
docker-compose exec postgres pg_dump -U insitechart insitechart > backup.sql

# Restore database
docker-compose exec -T postgres psql -U insitechart insitechart < backup.sql

# Reset database (destructive!)
docker-compose exec postgres psql -U insitechart -d insitechart -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

### Redis Management

```bash
# Connect to Redis
docker-compose exec redis redis-cli -a ${REDIS_PASSWORD}

# View keys
docker-compose exec redis redis-cli -a ${REDIS_PASSWORD} KEYS '*'

# Clear cache
docker-compose exec redis redis-cli -a ${REDIS_PASSWORD} FLUSHALL
```

### Stop/Start Services

```bash
# Stop all services (keep volumes)
docker-compose stop

# Start all services
docker-compose start

# Stop specific service
docker-compose stop analytics

# Restart specific service
docker-compose restart gateway

# Full cleanup (remove containers, keep volumes)
docker-compose down

# Full cleanup (remove everything)
docker-compose down -v
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs backend

# Check if ports are in use
lsof -i :8080

# Rebuild images
docker-compose build --no-cache

# Full reset
docker-compose down -v
docker-compose up -d
```

### Database Connection Issues

```bash
# Test connection
docker-compose exec backend ping postgres

# Check database is running
docker-compose exec postgres pg_isready -U insitechart

# View database logs
docker-compose logs postgres
```

### Memory Issues

```bash
# Check resource usage
docker stats

# Reduce resource limits in docker-compose.yml

# Clear Docker cache
docker system prune -a --volumes
```

### Performance Issues

```bash
# View real-time stats
docker stats --no-stream

# Check network
docker network inspect insitechart_network

# Monitor logs
docker-compose logs -f --tail=100 | grep -i error
```

## Environment Variables

### Required

```env
DB_USER=insitechart
DB_PASSWORD=<secure-password>
REDIS_PASSWORD=<secure-password>
JWT_SECRET_KEY=<long-random-string>
```

### Optional

```env
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
RATE_LIMIT_MINUTE=60
RATE_LIMIT_HOUR=1000
RATE_LIMIT_DAY=10000
```

### External APIs

```env
YAHOO_FINANCE_API_KEY=<key>
REDDIT_CLIENT_ID=<id>
REDDIT_CLIENT_SECRET=<secret>
TWITTER_API_KEY=<key>
```

## Development Workflow

### Hot Reload

Services automatically reload on code changes:

```bash
# Edit code in editor
vim services/analytics-service/main.py

# Changes are reflected immediately in running container
docker-compose logs -f analytics
```

### Testing

```bash
# Run tests in container
docker-compose exec analytics pytest tests/ -v

# With coverage
docker-compose exec analytics pytest tests/ --cov=analyzers

# Run specific test
docker-compose exec analytics pytest tests/test_analyzers.py::TestSentimentAnalyzer
```

### Database Migrations

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "Add new column"
```

## Monitoring & Logging

### Real-time Monitoring

```bash
# System resources
docker stats

# Container logs with timestamps
docker-compose logs --timestamps

# Follow specific service
docker-compose logs -f backend --tail=50
```

### Log Aggregation

```bash
# Save logs to file
docker-compose logs > logs/docker-compose.log

# Filter logs
docker-compose logs backend | grep ERROR

# Search logs
docker-compose logs | grep -A 5 "error"
```

## Security Considerations

### Production Deployment

1. **Change Default Credentials**
   ```bash
   # Edit .env.docker with strong passwords
   DB_PASSWORD=<very-strong-password>
   REDIS_PASSWORD=<very-strong-password>
   JWT_SECRET_KEY=<long-random-string>
   ```

2. **Use Secrets Management**
   ```bash
   # Use Docker secrets or external secret management
   docker secret create db_password /path/to/password.txt
   ```

3. **Network Security**
   ```bash
   # Restrict network access
   # Use firewall rules
   # Use VPN/SSH tunneling
   ```

4. **SSL/TLS**
   ```bash
   # Use reverse proxy (nginx, traefik)
   # Install SSL certificates
   ```

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      replicas: 3  # Run 3 instances
    ports:
      - "8000:8000"  # Load balanced
```

### Load Balancing

```bash
# Use nginx or traefik
# Route requests to multiple instances
```

## Backup & Recovery

### Automated Backups

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
docker-compose exec postgres pg_dump -U insitechart insitechart > \
  backups/db_$DATE.sql

# Redis backup
docker-compose exec redis redis-cli -a $REDIS_PASSWORD BGSAVE
docker cp insitechart-redis:/data/dump.rdb backups/redis_$DATE.rdb

# Compress
tar czf backups/insitechart_$DATE.tar.gz backups/
```

### Recovery

```bash
# Restore database
docker-compose exec -T postgres psql -U insitechart insitechart < backup.sql

# Restore Redis
docker cp backup.rdb insitechart-redis:/data/dump.rdb
docker-compose restart redis
```

## Advanced Topics

### Custom Networks

```yaml
networks:
  insitechart_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### Volume Management

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect insitechart_postgres_data

# Cleanup unused volumes
docker volume prune
```

### Image Registry

```bash
# Push to registry
docker tag insitechart-backend registry.example.com/insitechart/backend:latest
docker push registry.example.com/insitechart/backend:latest

# Pull from registry
docker-compose -f docker-compose.registry.yml up
```

## Performance Tuning

### Database Optimization

```sql
-- Create indexes
CREATE INDEX idx_sentiment_symbol ON sentiment(symbol);
CREATE INDEX idx_data_timestamp ON data_points(timestamp);

-- Vacuum and analyze
VACUUM ANALYZE;
```

### Redis Optimization

```bash
# Monitor commands
redis-cli --stat

# Check memory
redis-cli INFO memory

# Optimize memory
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Service Optimization

```yaml
# Adjust resource limits
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 2G
    reservations:
      cpus: '1'
      memory: 1G
```

## Contributing

To contribute changes:

1. Create feature branch
2. Test in Docker environment
3. Submit pull request

```bash
# Test your changes
docker-compose build --no-cache
docker-compose up -d
docker-compose exec <service> pytest
```

## Support & Documentation

- GitHub Issues: https://github.com/ftfuture/InsiteChart/issues
- Documentation: https://github.com/ftfuture/InsiteChart/wiki
- Docker Docs: https://docs.docker.com/compose/

## License

MIT License - Part of InsiteChart Project
