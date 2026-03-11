# Docker Local-First Development

**Paste this to any Claude working on deployments, infrastructure, or debugging.**

---

## Why Local Docker is SUPERIOR for AI-Assisted Development

### The Problem with Remote Deployments

```
Remote Platform (Render/Vercel/AWS)
┌─────────────────────────────────────┐
│  ┌─────────────┐                    │
│  │ Your Code   │  ← You can see this│
│  └─────────────┘                    │
│         ↓                           │
│  ┌─────────────┐                    │
│  │   BUILD     │  ← Limited logs    │
│  └─────────────┘                    │
│         ↓                           │
│  ┌─────────────┐                    │
│  │   RUNTIME   │  ← BLACK BOX      │
│  └─────────────┘                    │
│                                     │
│  Memory usage? 🤷                   │
│  CPU spikes? 🤷                     │
│  Container internals? 🤷            │
│  Why did it crash? 🤷               │
└─────────────────────────────────────┘
```

### The Local Docker Advantage

```
Local Docker (96GB Mac Studio)
┌─────────────────────────────────────┐
│  ┌─────────────┐                    │
│  │ Your Code   │  ← Full access     │
│  └─────────────┘                    │
│         ↓                           │
│  ┌─────────────┐                    │
│  │   BUILD     │  ← Every line      │
│  └─────────────┘                    │
│         ↓                           │
│  ┌─────────────┐                    │
│  │   RUNTIME   │  ← FULL VISIBILITY │
│  └─────────────┘                    │
│                                     │
│  Memory: docker stats ✓             │
│  CPU: docker stats ✓                │
│  Logs: docker logs -f ✓             │
│  Errors: Real-time ✓                │
│  Exec into container: docker exec ✓ │
│  Network: docker network inspect ✓  │
│  Disk: docker system df ✓           │
└─────────────────────────────────────┘
```

---

## What Claude Can Inspect Locally

| Dimension | Command | What Claude Learns |
|-----------|---------|-------------------|
| **Logs** | `docker logs -f <container>` | Every print, every error, every stack trace |
| **Memory** | `docker stats` | Real-time MB usage, is it leaking? |
| **CPU** | `docker stats` | Spikes, sustained load, idle waste |
| **Disk** | `docker system df` | Image bloat, volume growth |
| **Network** | `docker network inspect` | Service connectivity, DNS resolution |
| **Processes** | `docker exec <c> ps aux` | What's actually running inside |
| **Files** | `docker exec <c> ls -la` | Are files where expected? |
| **Environment** | `docker exec <c> env` | Are env vars set correctly? |
| **Health** | `docker inspect --format='{{.State.Health}}'` | Why is health check failing? |
| **Exit codes** | `docker inspect --format='{{.State.ExitCode}}'` | Why did it crash? |

**Claude cannot see ANY of this on Render/Vercel.** Only endpoint responses and limited logs.

---

## The Core Principle

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║  LOCAL DOCKER = FULL OBSERVABILITY = CLAUDE CAN ACTUALLY DEBUG               ║
║  REMOTE DEPLOY = BLACK BOX = GUESSING WHAT WENT WRONG                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

## Hardware Context: 96GB Mac Studio

This machine can run the **entire production stack** locally:

| Service | Production (Render) | Local Allocation | Headroom |
|---------|---------------------|------------------|----------|
| API + Workers 1-3 | 512MB | 2GB | 4x production |
| Projection Worker | 512MB | 1GB | 2x production |
| Cache Listener | 256MB | 512MB | 2x production |
| Embedding Worker | 512MB | 2GB | 4x production |
| Redis | Cloud | 1GB | Generous |
| PostgreSQL | Cloud | 4GB | Generous |
| Frontend | Cloud | 2GB | Generous |
| **TOTAL** | ~2GB | ~13GB | **83GB FREE** |

**You have 83GB of headroom.** Run everything. Run it twice. Run it with debugging enabled. No constraints.

---

## The Observable Stack

### docker-compose.macstudio.yml

Create this file to run the full stack locally with maximum observability:

```yaml
version: '3.8'

# =============================================================================
# CELESTE FULL STACK - Mac Studio Local Development
# =============================================================================
# 96GB RAM available - allocate generously for debugging headroom
# All services fully observable via docker commands
# =============================================================================

services:
  # ===========================================================================
  # LOCAL INFRASTRUCTURE (Replaces Cloud Services)
  # ===========================================================================

  postgres:
    image: postgres:15-alpine
    container_name: celeste-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: localdev
      POSTGRES_DB: celeste
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 1G

  redis:
    image: redis:7-alpine
    container_name: celeste-redis
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 256M

  # ===========================================================================
  # APPLICATION SERVICES
  # ===========================================================================

  api:
    build:
      context: ./apps/api
      dockerfile: Dockerfile
    container_name: celeste-api
    ports:
      - "8000:8000"
    environment:
      - PORT=8000
      - DATABASE_URL=postgresql://postgres:localdev@postgres:5432/celeste
      - READ_DB_DSN=postgresql://postgres:localdev@postgres:5432/celeste
      - REDIS_URL=redis://redis:6379
      - PYTHONUNBUFFERED=1
      - LOG_LEVEL=DEBUG
      # Add your other env vars here or use env_file
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M

  projection-worker:
    build:
      context: ./apps/api
      dockerfile: Dockerfile
    container_name: celeste-projection-worker
    environment:
      - DATABASE_URL=postgresql://postgres:localdev@postgres:5432/celeste
      - F1_PROJECTION_WORKER_ENABLED=true
      - PROJECTION_BATCH_SIZE=50
      - PROJECTION_POLL_INTERVAL=5
      - PYTHONUNBUFFERED=1
      - LOG_LEVEL=DEBUG
    command: ["python", "workers/projection_worker.py"]
    depends_on:
      postgres:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 256M

  cache-listener:
    build:
      context: ./apps/api
      dockerfile: Dockerfile
    container_name: celeste-cache-listener
    environment:
      - READ_DB_DSN=postgresql://postgres:localdev@postgres:5432/celeste
      - REDIS_URL=redis://redis:6379
      - PYTHONUNBUFFERED=1
      - LOG_LEVEL=DEBUG
    command: ["python", "cache/invalidation_listener.py"]
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 128M

  embedding-worker:
    build:
      context: ./apps/api
      dockerfile: Dockerfile
    container_name: celeste-embedding-worker
    environment:
      - DATABASE_URL=postgresql://postgres:localdev@postgres:5432/celeste
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - EMBED_MODEL=text-embedding-3-small
      - EMBED_DIM=1536
      - BATCH_SIZE=100
      - PYTHONUNBUFFERED=1
      - LOG_LEVEL=DEBUG
    command: ["python", "workers/embedding_worker_1536.py"]
    depends_on:
      postgres:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M

  web:
    build:
      context: ./apps/web
      dockerfile: Dockerfile
    container_name: celeste-web
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_SUPABASE_URL=http://localhost:5432
      - NEXT_PUBLIC_API_URL=http://api:8000
      - NEXT_PUBLIC_APP_URL=http://localhost:3000
    depends_on:
      - api
    deploy:
      resources:
        limits:
          memory: 2G
        reservations:
          memory: 512M

volumes:
  postgres-data:
  redis-data:

networks:
  default:
    name: celeste-local
```

---

## Observability Commands for Claude

### Real-Time Monitoring

```bash
# Watch ALL container stats (memory, CPU, network I/O)
docker stats

# Follow logs from all services
docker-compose -f docker-compose.macstudio.yml logs -f

# Follow logs from specific service
docker logs -f celeste-api

# Watch for errors only
docker logs -f celeste-api 2>&1 | grep -i error
```

### Debugging Commands

```bash
# Exec into container to inspect
docker exec -it celeste-api /bin/bash

# Check environment variables
docker exec celeste-api env

# Check running processes
docker exec celeste-api ps aux

# Check file system
docker exec celeste-api ls -la /app

# Check network connectivity
docker exec celeste-api curl -v http://redis:6379
```

### Health & Status

```bash
# Container health status
docker inspect --format='{{json .State.Health}}' celeste-api | jq

# Exit codes (why did it crash?)
docker inspect --format='{{.State.ExitCode}}' celeste-api

# Full container state
docker inspect celeste-api | jq '.[0].State'

# Resource usage breakdown
docker system df -v
```

### Image Analysis

```bash
# Image size breakdown
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# Layer analysis (what's bloating the image?)
docker history celeste-api:latest

# Dive deep into image layers
dive celeste-api:latest  # (install: brew install dive)
```

---

## Workflow: Claude Debugging Locally

### Step 1: Start the Stack

```bash
cd /Volumes/Backup/CELESTE/BACK_BUTTON_CLOUD_PMS
docker-compose -f docker-compose.macstudio.yml up --build -d
```

### Step 2: Claude Monitors Health

```bash
# Check all services are healthy
docker-compose -f docker-compose.macstudio.yml ps

# Watch resource usage
docker stats --no-stream

# Check for any crashes
docker-compose -f docker-compose.macstudio.yml ps -a | grep -E "Exit|Restarting"
```

### Step 3: Claude Investigates Issues

```bash
# If API is unhealthy, check logs
docker logs celeste-api --tail 100

# If worker crashed, check exit code and logs
docker inspect --format='{{.State.ExitCode}}' celeste-projection-worker
docker logs celeste-projection-worker --tail 200

# If memory issue suspected
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

### Step 4: Claude Fixes & Verifies

```bash
# Rebuild single service after fix
docker-compose -f docker-compose.macstudio.yml up --build -d api

# Verify fix worked
docker logs -f celeste-api
curl http://localhost:8000/health
```

### Step 5: Only THEN Push to Remote

```bash
# All local checks pass? Now push once.
git add .
git commit -m "Fix: [issue] - verified locally via docker-compose.macstudio.yml"
git push
```

---

## Cost Comparison

| Approach | Cost | Debug Visibility | Iteration Speed |
|----------|------|------------------|-----------------|
| Remote builds (Render) | $7+/month per service | 10% (logs only) | 5-10 min per cycle |
| Remote builds (Vercel) | $20+/month | 10% (logs only) | 3-5 min per cycle |
| **Local Docker (Mac Studio)** | **$0** | **100% (everything)** | **10-30 seconds** |

---

## Quick Reference

```
┌────────────────────────────────────────────────────────────────────┐
│  START STACK                                                       │
├────────────────────────────────────────────────────────────────────┤
│  docker-compose -f docker-compose.macstudio.yml up --build -d     │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  OBSERVE EVERYTHING                                                │
├────────────────────────────────────────────────────────────────────┤
│  docker stats                    # Memory, CPU, Network            │
│  docker logs -f <container>      # Real-time logs                  │
│  docker exec -it <c> /bin/bash   # Get inside container           │
│  docker inspect <container>      # Full state dump                 │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  STOP STACK                                                        │
├────────────────────────────────────────────────────────────────────┤
│  docker-compose -f docker-compose.macstudio.yml down              │
│  docker-compose -f docker-compose.macstudio.yml down -v  # +data  │
└────────────────────────────────────────────────────────────────────┘
```

---

## The Mindset

**Remote platforms hide information. Local Docker reveals everything.**

When Claude can see memory usage, CPU spikes, logs, errors, container internals, network traffic, and disk usage — debugging becomes **deterministic** instead of guesswork.

**Build locally. Debug locally. Observe locally. Push once. Deploy once. Done.**
