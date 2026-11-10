# ClearGuard Backend — Production Deployment Guide

**Document Version:** 1.0.0  
**Target Milestone:** B5 (Security, Deployment and MVP Readiness)  
**Target Platform:** Containerized (Docker, Docker Compose, Kubernetes)  

---

## 1. Overview & Architecture

The ClearGuard backend is delivered as a lightweight, containerized Python/FastAPI service utilizing a multi-stage Docker build with non-root security boundaries.

```text
[ Mobile / Web Clients ]
           │
           ▼ (HTTPS / 443)
  [ Reverse Proxy / Cloudflare ]
           │
           ▼ (HTTP / 8000)
┌──────────────────────────────────────┐
│ ClearGuard API Container             │
│  - FastAPI / Uvicorn                 │
│  - SecurityHeaders & RateLimiter     │
│  - Readiness & Liveness Probes       │
└──────────────────┬───────────────────┘
                   │ (asyncpg pool)
                   ▼
┌──────────────────────────────────────┐
│ PostgreSQL 16+ Managed Database      │
│  - Persistent storage volume         │
│  - Automatic WAL archiving           │
└──────────────────────────────────────┘
```

---

## 2. Docker Compose Deployment

For single-host production or staging environments:

```bash
# 1. Clone repository & configure production environment
cp .env.example .env.production
# Edit .env.production with real PostgreSQL credentials & secrets

# 2. Build and launch services in background
docker compose up -d --build

# 3. Apply database migrations
docker compose exec api uv run alembic upgrade head

# 4. Verify service status
docker compose ps
curl http://localhost:8000/api/v1/health/ready
```

---

## 3. Production Health Probes (Kubernetes & Load Balancers)

The backend exposes dedicated probe endpoints:

1. **Liveness Probe (`GET /api/v1/health/live`)**:
   - Confirms process is running and responding to HTTP requests.
   - Initial delay: 5s, Period: 10s.

2. **Readiness Probe (`GET /api/v1/health/ready`)**:
   - Verifies active database connectivity (`SELECT 1`).
   - If database connection drops, container is temporarily taken out of rotation.

---

## 4. Production Reverse Proxy (Nginx Configuration)

```nginx
server {
    listen 443 ssl http2;
    server_name api.clearguard.net;

    ssl_certificate /etc/letsencrypt/live/api.clearguard.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.clearguard.net/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 5. Zero-Downtime Rolling Update SOP

1. Build new container image tagged with commit SHA.
2. Run database migration task: `alembic upgrade head`.
3. Perform rolling restart:
   - In Docker Compose: `docker compose up -d --no-deps --build api`
   - In Kubernetes: `kubectl rollout restart deployment/clearguard-api`
4. Query `/api/v1/health/ready` to verify healthy status of new pods.

