# Deployment Guide

This guide covers best practices for deploying litestar-admin to production environments.

## Pre-Deployment Checklist

Before deploying, ensure you have:

- [ ] Configured authentication with a secure secret key
- [ ] Enabled HTTPS for all traffic
- [ ] Set secure cookie options
- [ ] Configured rate limiting
- [ ] Set up audit logging
- [ ] Tested all admin functionality
- [ ] Configured proper database connections

## Security Configuration

### Secret Keys

Never use hardcoded or weak secret keys in production:

```python
import os
import secrets

# Generate a secure key for development
# Run once: print(secrets.token_urlsafe(32))

# Load from environment in production
secret_key = os.environ.get("ADMIN_JWT_SECRET")
if not secret_key:
    raise ValueError("ADMIN_JWT_SECRET environment variable must be set")
```

### HTTPS Configuration

Always use HTTPS in production:

```python
from litestar_admin import AdminConfig
from litestar_admin.auth import JWTConfig

jwt_config = JWTConfig(
    secret_key=os.environ["ADMIN_JWT_SECRET"],
    cookie_secure=True,  # Only send cookies over HTTPS
    cookie_samesite="strict",  # Prevent CSRF
)

admin_config = AdminConfig(
    auth_backend=auth_backend,
    session_cookie_secure=True,
    session_cookie_httponly=True,
    session_cookie_samesite="lax",
)
```

### Rate Limiting

Configure appropriate rate limits for your traffic:

```python
admin_config = AdminConfig(
    rate_limit_enabled=True,
    rate_limit_requests=100,  # Requests per window
    rate_limit_window_seconds=60,  # 1 minute window
)
```

For high-traffic deployments, use a distributed rate limit store like Redis.

## Database Configuration

### Production Database Setup

Use a production-ready database with connection pooling:

```python
from litestar.plugins.sqlalchemy import SQLAlchemyConfig

db_config = SQLAlchemyConfig(
    # PostgreSQL with asyncpg driver
    connection_string=os.environ["DATABASE_URL"],

    # Connection pool settings
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=1800,

    # Echo SQL for debugging (disable in production)
    echo=False,
)
```

### Environment-Specific Configuration

```python
import os

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    db_url = os.environ["DATABASE_URL"]
    debug = False
    cookie_secure = True
else:
    db_url = "sqlite+aiosqlite:///dev.db"
    debug = True
    cookie_secure = False
```

## Deployment Options

### Docker Deployment

Create a production Dockerfile:

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

# Copy application
COPY src/ src/

# Set environment
ENV PYTHONPATH=/app/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Run with uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Docker Compose for local testing:

```yaml
# docker-compose.yml
version: "3.8"

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/app
      - ADMIN_JWT_SECRET=${ADMIN_JWT_SECRET}
      - ENVIRONMENT=production
    depends_on:
      - db

  db:
    image: postgres:16
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=app
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: litestar-admin
spec:
  replicas: 3
  selector:
    matchLabels:
      app: litestar-admin
  template:
    metadata:
      labels:
        app: litestar-admin
    spec:
      containers:
        - name: app
          image: your-registry/litestar-admin:latest
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: database-url
            - name: ADMIN_JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: app-secrets
                  key: jwt-secret
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /admin/api/health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /admin/api/health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
```

### Systemd Service

For traditional server deployments:

```ini
# /etc/systemd/system/litestar-admin.service
[Unit]
Description=Litestar Admin Application
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/litestar-admin
Environment="PATH=/opt/litestar-admin/.venv/bin"
Environment="DATABASE_URL=postgresql+asyncpg://user:pass@localhost/app"
Environment="ADMIN_JWT_SECRET=your-secret-key"
ExecStart=/opt/litestar-admin/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable litestar-admin
sudo systemctl start litestar-admin
```

## Reverse Proxy Configuration

### Nginx

```nginx
upstream litestar_admin {
    server 127.0.0.1:8000;
    keepalive 64;
}

server {
    listen 443 ssl http2;
    server_name admin.example.com;

    ssl_certificate /etc/ssl/certs/admin.example.com.crt;
    ssl_certificate_key /etc/ssl/private/admin.example.com.key;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Admin panel
    location /admin {
        proxy_pass http://litestar_admin;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # WebSocket support (if needed)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static files with caching
    location /admin/static {
        proxy_pass http://litestar_admin;
        proxy_cache_valid 200 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Caddy

```text
admin.example.com {
    reverse_proxy localhost:8000

    header {
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}
```

### Traefik

```yaml
# traefik dynamic configuration
http:
  routers:
    admin:
      rule: "Host(`admin.example.com`)"
      service: litestar-admin
      entryPoints:
        - websecure
      tls:
        certResolver: letsencrypt
      middlewares:
        - security-headers

  services:
    litestar-admin:
      loadBalancer:
        servers:
          - url: "http://app:8000"

  middlewares:
    security-headers:
      headers:
        frameDeny: true
        contentTypeNosniff: true
        browserXssFilter: true
        referrerPolicy: "strict-origin-when-cross-origin"
```

## Monitoring

### Health Check Endpoint

The admin API includes a health check endpoint:

```bash
curl https://admin.example.com/admin/api/health
```

### Logging Configuration

Configure structured logging for production:

```python
import logging
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Set log level
logging.basicConfig(level=logging.INFO)
```

### Metrics with Prometheus

Export metrics for monitoring:

```python
from prometheus_client import Counter, Histogram, generate_latest

admin_requests = Counter(
    "admin_requests_total",
    "Total admin requests",
    ["method", "endpoint", "status"],
)

admin_latency = Histogram(
    "admin_request_duration_seconds",
    "Admin request latency",
    ["method", "endpoint"],
)
```

## Audit Logging

Configure audit logging for compliance:

```python
from litestar_admin.audit import AuditLogger, AuditEntry


class DatabaseAuditLogger:
    """Store audit logs in database."""

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def log(self, entry: AuditEntry) -> None:
        async with self._session_factory() as session:
            record = AuditLog(**entry.to_dict())
            session.add(record)
            await session.commit()

    async def query(self, filters) -> list[AuditEntry]:
        # Query implementation
        ...
```

## Scaling Considerations

### Horizontal Scaling

For multiple instances, ensure:

1. **Shared Session Storage**: Use Redis or database-backed sessions
2. **Distributed Rate Limiting**: Use Redis-backed rate limit store
3. **Load Balancer Configuration**: Enable sticky sessions if needed

### Redis for Rate Limiting

```python
# Example Redis rate limit store (implement based on your needs)
class RedisRateLimitStore:
    def __init__(self, redis_url: str):
        self._redis = aioredis.from_url(redis_url)

    async def increment(self, key: str, window: str) -> int:
        full_key = f"rate_limit:{key}:{window}"
        pipe = self._redis.pipeline()
        pipe.incr(full_key)
        pipe.expire(full_key, self._get_window_seconds(window))
        results = await pipe.execute()
        return results[0]
```

### Caching

Add caching for frequently accessed data:

```python
from litestar.stores.redis import RedisStore

cache_store = RedisStore.with_client(redis_url=os.environ["REDIS_URL"])
```

## Troubleshooting Production Issues

### Common Issues

1. **502 Bad Gateway**
   - Check if the application is running
   - Verify proxy configuration
   - Check for startup errors in logs

2. **Authentication Failures**
   - Verify JWT secret is set correctly
   - Check cookie settings for HTTPS
   - Verify user loader function

3. **Slow Performance**
   - Enable connection pooling
   - Check database query performance
   - Add caching for static data

4. **Rate Limit Issues**
   - Verify rate limit configuration
   - Check for proper client IP detection behind proxy
   - Consider distributed rate limiting

### Debug Mode

Temporarily enable debug mode for troubleshooting (never in production traffic):

```python
admin_config = AdminConfig(
    debug=True,  # Enable only for debugging
)
```

### Log Analysis

Key log patterns to watch:

```bash
# Failed authentication attempts
grep "Authentication required" /var/log/app/admin.log

# Rate limit hits
grep "429" /var/log/nginx/access.log

# Database errors
grep "DatabaseError" /var/log/app/admin.log
```
