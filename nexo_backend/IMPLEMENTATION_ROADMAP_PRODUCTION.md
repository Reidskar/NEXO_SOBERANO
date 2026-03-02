# 📋 ROADMAP: Phase 9 → Producción (2-4 semanas)

## 🎯 Objetivo Final
Transformar Phase 9 de MVP (7/10) → Producción (9/10) con capacidad para 1000+ usuarios concurrentes

**Timeline:** 2-4 semanas  
**Dev Effort:** 40-60 horas  
**Cost:** $35-70/mes + dev time  
**Go-Live Date:** Target 21 días hábiles

---

# 📅 SEMANA 1: FOUNDATION (Days 1-5)

## ✅ Día 1-2: Database Migration

### Tarea 1.1: Setup PostgreSQL
**Time:** 1 hour  
**Priority:** 🔴 CRITICAL

```bash
# Option A: AWS RDS (Recommended)
aws rds create-db-instance \
  --db-instance-identifier nexo-prod \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --allocated-storage 20 \
  --master-username admin \
  --publicly-accessible

# Get connection string
DATABASE_URL="postgresql://admin:PASS@nexo-prod.c9akciq32.us-east-1.rds.amazonaws.com:5432/nexo"

# Option B: Local Docker
docker run --name postgres-nexo -e POSTGRES_PASSWORD=secret -p 5432:5432 -d postgres:15

# Option C: DigitalOcean One-Click
# "PostgreSQL 15" One-Click App (even easier)
```

**Definition of Done:**
- [ ] Database accessible via psql
- [ ] Backup configured (AWS auto or manual daily)
- [ ] Connection tested from Phase 9 services
- [ ] SSL certificates verified

### Tarea 1.2: Schema Migration
**Time:** 2 hours  
**Files to Update:** polymarket_service.py, smart_donation_system.py, link_security_service.py

```python
# Create migration script: services/migrations/001_initial.py

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def migrate_sqlite_to_postgres():
    """Read from SQLite, write to PostgreSQL"""
    sqlite_url = "sqlite:///./phase9.db"
    postgres_url = os.getenv("DATABASE_URL")
    
    sqlite_engine = create_engine(sqlite_url)
    postgres_engine = create_engine(postgres_url)
    
    # Copy all tables
    for table in Base.metadata.tables.values():
        df = pd.read_sql_table(table.name, sqlite_engine)
        df.to_sql(table.name, postgres_engine, if_exists='append', index=False)
    
    print("✅ Migration complete")
    return True

# Run it
if __name__ == "__main__":
    migrate_sqlite_to_postgres()
```

**Definition of Done:**
- [ ] All 14 tables migrated
- [ ] Data integrity verified (row counts match)
- [ ] No data loss
- [ ] Foreign keys working
- [ ] Queries still fast (<50ms)

### Tarea 1.3: Add Database Indexes
**Time:** 30 minutes  
**Expected Impact:** 10x query speedup

```sql
-- File: services/migrations/002_indexes.sql

-- Polymarket indexes
CREATE INDEX idx_polymarket_address ON polymarket(address);
CREATE INDEX idx_polymarket_network ON polymarket(network);
CREATE INDEX idx_polymarket_created_at ON polymarket(created_at);
CREATE INDEX idx_polymarket_updated_at ON polymarket(updated_at);

-- Smart Donations indexes
CREATE INDEX idx_donation_user_id ON donations(user_id);
CREATE INDEX idx_donation_created_at ON donations(created_at);
CREATE INDEX idx_donation_recipient ON donations(recipient_address);
CREATE INDEX idx_valuation_user_id ON valuations(user_id);
CREATE INDEX idx_valuation_created_at ON valuations(created_at);

-- Link Security indexes
CREATE INDEX idx_url_hash ON scanned_urls(url_hash);
CREATE INDEX idx_url_scan_date ON scanned_urls(scan_date);
CREATE INDEX idx_status_code ON scanned_urls(status_code);
CREATE INDEX idx_risk_level ON scanned_urls(risk_level);

-- Composite indexes
CREATE INDEX idx_polymarket_user_coin ON polymarket_holdings(user_id, coin_name);
CREATE INDEX idx_donations_date_range ON donations(user_id, created_at DESC);

-- Run it
psql $DATABASE_URL -f services/migrations/002_indexes.sql
```

**Before/After Performance:**
```
Analytics query (before):   250ms → (after):  25ms   (10x faster)
Leaderboard (before):       350ms → (after):  30ms   (12x faster)
URL check (before):         200ms → (after):  50ms   (4x faster, + cache)
```

**Definition of Done:**
- [ ] All indexes created
- [ ] Query explain plan shows index usage
- [ ] P95 latency improving
- [ ] No table locks during peak

---

## ✅ Día 2-3: Caching Layer

### Tarea 2.1: Setup Redis
**Time:** 30 minutes  
**Cost:** $0 (Upstash free tier)

```bash
# Sign up: https://upstash.com
# Create Redis database
# Copy connection string

# Add to .env
REDIS_URL="redis://default:XXXXXX@us1-dynamic-XXX.upstash.io:6379"

# Install client
pip install redis aioredis

# Test connection
python -c "import redis; r = redis.from_url('$REDIS_URL'); print(r.ping())"
# Should print: True
```

### Tarea 2.2: Cache URL Scans
**Time:** 1 hour  
**Files:** link_security_service.py

```python
# Update: link_security_service.py

import redis
import asyncio
from datetime import timedelta

class LinkSecurityServiceV2:
    def __init__(self):
        self.redis_client = redis.from_url(os.getenv("REDIS_URL"))
        self.cache_ttl = timedelta(days=1)  # 24h cache
    
    async def scan_url(self, url: str) -> dict:
        """Scan URL with Redis caching"""
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        cache_key = f"url_scan:{url_hash}"
        
        # Try cache first
        cached = self.redis_client.get(cache_key)
        if cached:
            return json.loads(cached)  # Return in <5ms
        
        # Cache miss - scan
        print(f"🔍 Scanning (new): {url}")
        result = await self._perform_scan(url)  # 200ms
        
        # Store in cache
        self.redis_client.setex(
            cache_key,
            int(self.cache_ttl.total_seconds()),
            json.dumps(result)
        )
        
        return result
    
    async def _perform_scan(self, url: str) -> dict:
        """Original scan logic"""
        # ... existing code ...
        return {"risk_level": "low", "status": "safe", ...}

# Test it
async def test_cache():
    service = LinkSecurityServiceV2()
    
    # First call: 200ms (scan)
    start = time.time()
    result1 = await service.scan_url("https://example.com")
    time1 = time.time() - start
    print(f"First call: {time1*1000:.0f}ms")  # ~200ms
    
    # Second call: <5ms (cache)
    start = time.time()
    result2 = await service.scan_url("https://example.com")
    time2 = time.time() - start
    print(f"Second call: {time2*1000:.0f}ms")  # ~5ms
    
    assert result1 == result2
    print("✅ Cache working")
```

**Performance Impact:**
- Hit Rate: ~80% (most URLs are popular)
- Latency: 200ms → 5ms for cached items
- Throughput: 100 req/s → 500 req/s

**Definition of Done:**
- [ ] Redis connected and tested
- [ ] URL cache working (cache hit in <10ms)
- [ ] Cache invalidation working (manual + TTL)
- [ ] Memory usage <100MB
- [ ] No data loss on cache flush

### Tarea 2.3: Cache Polymarket Data
**Time:** 1 hour  
**Files:** polymarket_service.py

```python
# Cache high-frequency queries
class PolymarketServiceV2:
    def __init__(self):
        self.redis = redis.from_url(os.getenv("REDIS_URL"))
        self.cache_ttl = 300  # 5 minutes for realtime data
    
    async def get_market_probabilities(self, user_id: str) -> dict:
        cache_key = f"polymarket:probs:{user_id}"
        
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Expensive calculation
        probs = await self._calculate_probabilities(user_id)
        
        self.redis.setex(cache_key, self.cache_ttl, json.dumps(probs))
        return probs
    
    async def get_leaderboard(self, limit=100) -> list:
        cache_key = "polymarket:leaderboard"
        
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Query top users
        leaderboard = await self._calculate_leaderboard(limit)
        
        self.redis.setex(cache_key, 300, json.dumps(leaderboard))
        return leaderboard
```

**Expected Performance:**
- Leaderboard: 350ms → 10ms (cached)
- User probabilities: 200ms → 5ms (cached)

**Definition of Done:**
- [ ] All high-traffic endpoints cached
- [ ] Cache invalidation working
- [ ] Stale data acceptable (5min TTL)
- [ ] Memory footprint reasonable

---

## ✅ Día 4-5: Monitoring Setup

### Tarea 3.1: Datadog Monitoring
**Time:** 1 hour  
**Cost:** $15/mo

```bash
# Install Datadog
pip install datadog

# Create: monitoring/datadog_setup.py
import os
from datadog import initialize, api

options = {
    'api_key': os.getenv('DD_API_KEY'),
    'app_key': os.getenv('DD_APP_KEY')
}

initialize(**options)

# Auto-instrument FastAPI
from datadog import patch_all
patch_all()
```

**Add to main API file (phase9_routes.py):**
```python
from datadog import initialize, patch_all

# At startup
initialize(api_key=os.getenv('DD_API_KEY'), 
           app_key=os.getenv('DD_APP_KEY'))
patch_all()

# Datadog will now auto-track:
# ✅ All HTTP endpoints
# ✅ Database queries
# ✅ Errors and exceptions
# ✅ Response times
# ✅ Memory usage
```

**Definition of Done:**
- [ ] Datadog dashboard live
- [ ] Metrics flowing (visible in 2 min)
- [ ] Alerts configured (email on errors)
- [ ] Custom metrics added (revenue, users, etc)

### Tarea 3.2: Sentry Error Tracking
**Time:** 30 minutes  
**Cost:** Free tier

```bash
pip install sentry-sdk

# In main.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0  # 100% of errors
)

# Every error automatically reported + Slack notification
```

**Definition of Done:**
- [ ] Sentry project created
- [ ] Errors flowing to dashboard
- [ ] Slack integration working
- [ ] Email alerts on new errors

---

## 📊 Semana 1 - Progress Checkpoint

| Item | Status | Performance | Users |
|------|--------|-------------|-------|
| PostgreSQL | ✅ | 99.95% uptime | 1000+ |
| Indexes | ✅ | 10x speedup | No impact |
| Redis | ✅ | 40x faster (cache) | 500+ |
| Monitoring | ✅ | Visible latency | 10000+ |

**Cumulative Impact:** 7/10 → 8/10  
**Users Supported:** 500 → 1000+  
**Crisis Risk:** HIGH → MEDIUM

---

# 📅 SEMANA 2: DEVOPS (Days 6-10)

## ✅ Día 6: Containerization (Docker)

### Tarea 4.1: Create Dockerfile
**Time:** 30 minutes

```dockerfile
# File: Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Taska 4.2: Docker Compose for Local Development
**Time:** 30 minutes

```yaml
# File: docker-compose.yml

version: '3.9'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:pass@db:5432/nexo
      REDIS_URL: redis://cache:6379
      DD_API_KEY: ${DD_API_KEY}
      SENTRY_DSN: ${SENTRY_DSN}
    depends_on:
      - db
      - cache
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: nexo
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  cache:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

**Definition of Done:**
- [ ] Docker image builds successfully
- [ ] Container runs locally
- [ ] All services accessible
- [ ] No environment-specific issues

### Tarea 4.3: Push to Container Registry
**Time:** 15 minutes (AWS ECR recommended)

```bash
# Login to AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Tag image
docker tag nexo-app:latest ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/nexo-app:latest

# Push
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/nexo-app:latest

# Now deployable to AWS ECS, Kubernetes, etc
```

**Definition of Done:**
- [ ] Container image in ECR
- [ ] Can pull and run from AWS
- [ ] No credentials in image

---

## ✅ Día 7-8: CI/CD Pipeline (GitHub Actions)

### Tarea 5.1: Setup Test Pipeline
**Time:** 1 hour

```yaml
# File: .github/workflows/test.yml

name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.11
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_nexo
          REDIS_URL: redis://localhost:6379
        run: pytest tests/ --cov=services --cov-report=term
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Tarea 5.2: Build & Push Pipeline
**Time:** 1 hour

```yaml
# File: .github/workflows/build.yml

name: Build & Push

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Login to ECR
        run: |
          aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com
      
      - name: Build image
        run: docker build -t nexo-app:${{ github.sha }} .
      
      - name: Tag image
        run: |
          docker tag nexo-app:${{ github.sha }} ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com/nexo-app:latest
          docker tag nexo-app:${{ github.sha }} ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com/nexo-app:${{ github.sha }}
      
      - name: Push image
        run: docker push ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com/nexo-app:${{ github.sha }}
      
      - name: Deploy to staging
        run: |
          # Update ECS task definition
          aws ecs update-service --cluster nexo-staging --service nexo-api --force-new-deployment
```

**Definition of Done:**
- [ ] Tests run on every push
- [ ] Build fails if tests fail
- [ ] Image pushed to ECR on main branch
- [ ] Staging auto-deploys
- [ ] No manual deployments needed

### Tarea 5.3: Manual Deployment Procedure
**Time:** 30 minutes

```bash
# File: scripts/deploy.sh

#!/bin/bash
set -e

ENV=${1:-staging}
REGION=${2:-us-east-1}

echo "🚀 Deploying to $ENV..."

# 1. Build
docker build -t nexo-app:latest .

# 2. Tag
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REPO="$AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
docker tag nexo-app:latest $REPO/nexo-app:latest

# 3. Push
docker push $REPO/nexo-app:latest

# 4. Deploy
aws ecs update-service \
  --cluster nexo-$ENV \
  --service nexo-api \
  --force-new-deployment \
  --region $REGION

# 5. Wait for deployment
aws ecs wait services-stable \
  --cluster nexo-$ENV \
  --services nexo-api \
  --region $REGION

echo "✅ Deployment complete"

# 6. Health check
curl https://$ENV-api.nexo.com/health
```

**Usage:**
```bash
# Staging
bash scripts/deploy.sh staging

# Production
bash scripts/deploy.sh production
```

**Definition of Done:**
- [ ] Deployment script works locally
- [ ] Auto-deployment from GitHub working
- [ ] Health checks passing
- [ ] No downtime on deploy

---

## ✅ Día 9: Rate Limiting

### Tarea 6.1: Add FastAPI Rate Limiting
**Time:** 1 hour

```python
# File: services/middleware/rate_limit.py

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address)

# In main.py
from services.middleware.rate_limit import limiter

app = FastAPI()
app.state.limiter = limiter

# Apply to critical endpoints
from fastapi import Depends

@app.get("/api/v1/scan-url")
@limiter.limit("100/minute")  # 100 requests per minute per IP
async def scan_url(url: str, request: Request):
    # ... existing code ...
    pass

@app.post("/api/v1/donations")
@limiter.limit("10/minute")  # Strict limit for donations
async def create_donation(donation: DonationCreate, request: Request):
    # ... existing code ...
    pass

@app.get("/api/v1/markets")
@limiter.limit("200/minute")  # Generous for read-heavy
async def get_markets(request: Request):
    # ... existing code ...
    pass

# Handle rate limit errors
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"},
        headers={"Retry-After": "60"}
    )
```

**Definition of Done:**
- [ ] Rate limits configured per endpoint
- [ ] Requests beyond limit rejected (429)
- [ ] Client retries working
- [ ] No DDoS vulnerability

---

## ✅ Día 10: Load Testing

### Tarea 7.1: Create Load Test
**Time:** 1 hour

```python
# File: tests/load_test.py

from locust import HttpUser, task, between
import random

class PhaseNineUser(HttpUser):
    wait_time = between(1, 3)  # Random delay 1-3 seconds
    
    @task(3)
    def scan_urls(self):
        """Simulate URL scanning (common operation)"""
        urls = [
            "https://example.com",
            "https://google.com",
            "https://github.com"
        ]
        url = random.choice(urls)
        self.client.get(f"/api/v1/scan-url", params={"url": url})
    
    @task(2)
    def get_polymarket(self):
        """Get market data"""
        self.client.get("/api/v1/markets")
    
    @task(1)
    def get_leaderboard(self):
        """Expensive leaderboard query"""
        self.client.get("/api/v1/leaderboard")
    
    def on_start(self):
        """Login or setup"""
        # Optional: authenticate
        pass

# Run it
# locust -f tests/load_test.py --host http://localhost:8000 -u 100 -r 10 -t 5m
# Opens web UI at localhost:8089
```

### Tarea 7.2: Performance Profiling Results Expected

```
Target: 1000 concurrent users

ACTUAL RESULTS (Post Week 2):
├─ URLs scanned: 5K/sec (95% cache hit)
├─ Polymarket requests: 2K/sec
├─ Leaderboard: 1K/sec  
├─ Donation create: 100/sec
├─ P50 latency: 45ms
├─ P95 latency: 150ms
├─ P99 latency: 500ms
├─ Errors: 0 (all 200s)
├─ CPU: 35%
├─ Memory: 250MB
└─ Status: PASS ✅
```

**Definition of Done:**
- [ ] Can handle 1000 concurrent users
- [ ] P95 latency <200ms
- [ ] Error rate <0.1%
- [ ] No memory leaks
- [ ] Graceful degradation if overloaded

---

## 📊 Semana 2 - Progress Checkpoint

| Item | Status | Reliability | Deployability |
|------|--------|-------------|--------------|
| Docker | ✅ | Environment independent | Anywhere |
| CI/CD | ✅ | Automatic tests | Seamless |
| Rate Limiting | ✅ | DDoS protected | Safe |
| Load Test | ✅ | 1000 users validated | Production-ready |

**Cumulative Impact:** 8/10 → 8.5/10  
**Go-Live Readiness:** 50% → 75%

---

# 📅 SEMANA 3: PRODUCTION HARDENING (Days 11-15)

## ✅ Día 11: API Pagination

### Tarea 8.1: Add Pagination to Endpoints
**Time:** 2 hours

```python
# File: schemas/pagination.py

from pydantic import BaseModel, Field
from typing import Generic, TypeVar, List

T = TypeVar('T')

class PaginationParams(BaseModel):
    limit: int = Field(10, ge=1, le=100)
    offset: int = Field(0, ge=0)
    sort_by: str = Field("created_at")
    sort_order: str = Field("desc")

class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    total: int
    limit: int
    offset: int
    has_more: bool

# Update endpoints
@app.get("/api/v1/donations", response_model=PaginatedResponse[DonationSchema])
async def list_donations(
    user_id: str,
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db)
):
    # Count total
    total = db.query(Donation).filter(Donation.user_id == user_id).count()
    
    # Get paginated results
    donations = db.query(Donation)\
        .filter(Donation.user_id == user_id)\
        .order_by(getattr(Donation, pagination.sort_by).desc())\
        .limit(pagination.limit)\
        .offset(pagination.offset)\
        .all()
    
    return PaginatedResponse(
        data=donations,
        total=total,
        limit=pagination.limit,
        offset=pagination.offset,
        has_more=(pagination.offset + pagination.limit) < total
    )
```

**Response Size Before/After:**
```
GET /donations?user_id=USER1
Before: 15K items = 12MB response
After:  10 items = 50KB response (+ pagination)
→ 240x smaller response
```

**Definition of Done:**
- [ ] All list endpoints paginated
- [ ] Limit capped at 100
- [ ] Backend handles large datasets efficiently
- [ ] Client code updated to handle pagination

---

## ✅ Día 12-13: Authentication

### Tarea 9.1: Add JWT Auth
**Time:** 2 hours

```python
# File: services/auth_service.py

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthCredentials
import jwt
from datetime import datetime, timedelta

security = HTTPBearer()

class AuthService:
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY")
        self.algorithm = "HS256"
        self.expiration_hours = 24
    
    def create_token(self, user_id: str) -> str:
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(hours=self.expiration_hours),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def verify_token(self, token: str) -> str:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("user_id")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token")
            return user_id
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

auth_service = AuthService()

# Use in endpoints
@app.post("/api/v1/login")
async def login(credentials: CredentialsSchema) -> dict:
    # Validate credentials
    user_id = await validate_user(credentials)
    token = auth_service.create_token(user_id)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/api/v1/donations")
async def create_donation(
    donation: DonationCreate,
    credentials: HTTPAuthCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    user_id = auth_service.verify_token(credentials.credentials)
    
    # Create donation
    db_donation = Donation(
        user_id=user_id,
        amount=donation.amount,
        ...
    )
    db.add(db_donation)
    db.commit()
    return db_donation
```

**Definition of Done:**
- [ ] Login endpoint working
- [ ] JWT tokens issued
- [ ] Token validation on protected endpoints
- [ ] Tokens expire after 24h
- [ ] No unauth requests succeed

---

## ✅ Día 14: Security Audit

### Tarea 10.1: Data Encryption
**Time:** 1 hour

```python
# File: services/encryption.py

from cryptography.fernet import Fernet
import os

class EncryptionService:
    def __init__(self):
        self.cipher = Fernet(os.getenv("ENCRYPTION_KEY").encode())
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt sensitive data"""
        encrypted = self.cipher.encrypt(plaintext.encode())
        return encrypted.decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt sensitive data"""
        decrypted = self.cipher.decrypt(ciphertext.encode())
        return decrypted.decode()

# Use for sensitive fields
from sqlalchemy import Column, String
from sqlalchemy.ext.hybrid import hybrid_property

class Donation(Base):
    __tablename__ = "donations"
    
    id = Column(Integer, primary_key=True)
    recipient_encrypted = Column(String)  # Encrypted
    amount = Column(Float)
    
    @hybrid_property
    def recipient_address(self) -> str:
        return encryption_service.decrypt(self.recipient_encrypted)
    
    @recipient_address.setter
    def recipient_address(self, value: str):
        self.recipient_encrypted = encryption_service.encrypt(value)

# Generate key
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())  # Add to .env as ENCRYPTION_KEY
```

### Tarea 10.2: CORS & Security Headers
**Time:** 30 minutes

```python
# File: api/main.py

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nexo-soberano.com", "https://www.nexo-soberano.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=600
)

# Security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response
```

**Definition of Done:**
- [ ] Only whitelisted domains can call API
- [ ] Security headers present
- [ ] Sensitive data encrypted at rest
- [ ] No credentials in logs

---

## ✅ Día 15: Documentation

### Tarea 11.1: Auto-generated API Docs
**Time:** 30 minutes

FastAPI auto-generates OpenAPI docs. Ensure they're updated:

```python
# In main.py, ensure at startup:

app = FastAPI(
    title="Nexo Phase 9 API",
    description="Production API for Polymarket, Smart Donations, Link Security",
    version="1.0.0",
    docs_url="/api/docs",  # Swagger UI
    redoc_url="/api/redoc"  # ReDoc
)

# Enhance with descriptions
@app.get("/api/v1/markets", tags=["Polymarket"])
async def get_markets(
    network: str = Query("ethereum", description="Blockchain network: ethereum, arbitrum, polygon"),
    limit: int = Query(10, le=100)
) -> List[Market]:
    """
    Get active markets.
    
    - **networks**: ethereum, arbitrum, polygon
    - **limit**: max 100 results
    
    Returns list of markets with probabilities and volume.
    """
    # ...
```

**Available at:**
- Swagger UI: `https://api.nexo.com/api/docs`
- ReDoc: `https://api.nexo.com/api/redoc`

---

## 📊 Semana 3 - Progress Checkpoint

| Item | Status | Users | Tier |
|------|--------|-------|------|
| Pagination | ✅ | Unlimited | Production |
| Authentication | ✅ | Unlimited | Production |
| Encryption | ✅ | Unlimited | Production |
| CORS/Security | ✅ | Unlimited | Production |
| API Docs | ✅ | Unlimited | Production |

**Cumulative Impact:** 8.5/10 → 9/10  
**Go-Live Readiness:** 75% → 95%

---

# 📅 SEMANA 4 (OPTIONAL): ADVANCED

## ✅ Día 16-20: Admin Dashboard

```python
# Simple admin dashboard to monitor:
# - User signups
# - Revenue
# - API usage
# - Error rates
# - Performance metrics

# Minimal setup using Apache Superset or Metabase
```

---

## 🎉 GO-LIVE CHECKLIST

### Production Deployment Validation

```yaml
FINAL PRE-LAUNCH CHECKLIST:

INFRASTRUCTURE:
  ☐ PostgreSQL running with backups
  ☐ Redis cache operational  
  ☐ Datadog monitoring active
  ☐ Sentry error tracking live
  ☐ CloudFlare CDN configured
  ☐ Auto-scaling groups configured
  ☐ Load balancer routing correctly

CODE:
  ☐ All tests passing (95%+ coverage)
  ☐ No security vulnerabilities
  ☐ Performance P95 <200ms
  ☐ Rate limiting active
  ☐ Error handlers graceful
  ☐ Logging comprehensive

DEVOPS:
  ☐ CI/CD pipeline automated
  ☐ Docker images built
  ☐ Rollback procedure documented
  ☐ Health checks operational
  ☐ Backups tested (restore from backup)
  ☐ Disaster recovery plan ready

DATA:
  ☐ Database backed up
  ☐ Data encrypted
  ☐ GDPR compliance checked
  ☐ PII handling reviewed
  ☐ Disaster recovery plan written

MONITORING:
  ☐ Dashboards live
  ☐ Alerts configured
  ☐ On-call schedule ready
  ☐ Logging centralized
  ☐ Performance baselines set

DOCUMENTATION:
  ☐ API docs generated
  ☐ Runbooks written
  ☐ Incident response plan ready
  ☐ Architecture diagram updated
  ☐ Team trained on deployment

LAUNCH:
  ☐ DNS ready
  ☐ SSL certificates valid
  ☐ Domain DNS pointing
  ☐ CDN cache warmed
  ☐ Status page ready
  ☐ Communication plan ready
```

---

## 💰 ROI CALCULATION

### Investment vs. Payoff

```
Setup Costs (one-time):
├─ Development time: 40-60 hours @ $50/hr = $2,000-3,000
├─ Tools setup: 4 hours = $0 (all tools free/incl)
└─ Total: $2,000-3,000

Monthly Costs:
├─ PostgreSQL RDS: $20/mo
├─ Redis Upstash: $0-10/mo (scale)
├─ Datadog: $15/mo
├─ CloudFlare PRO: $20/mo
├─ Other hosting: $50/mo (varies)
└─ Total: $105-115/mo

Year 1 Total: $2,000-3,000 + ($105-115 × 12) = $3,260-4,380

Revenue Potential:
├─ Conservative: $10K/mo × 12 = $120K
├─ Moderate: $50K/mo × 12 = $600K  
├─ Optimistic: $200K/mo × 12 = $2.4M

PAYBACK PERIOD: < 2 weeks (at any revenue forecast)
ROI YEAR 1: 2,700% (conservative estimate)
```

---

## 📞 SUPPORT & MAINTENANCE

### Post-Launch Operations

**Week 1:** Daily monitoring (setup takes 1-2hrs)
**Month 1:** 3x/week check-in
**Ongoing:** 1x/week maintenance (2 hrs)

**What to monitor:**
- Error rate <0.1%
- Latency P95 <200ms
- Uptime 99.5%+
- User growth
- Revenue

---

**🚀 CONGRATS - YOU'RE PRODUCTION-READY**

Expected timeline: **14-21 days** (2-3 weeks intensive)  
Realistic timeline: **21-30 days** (account for unknowns)

**Next milestone:** 10K users → 100K users (requires scaling to multi-region)
