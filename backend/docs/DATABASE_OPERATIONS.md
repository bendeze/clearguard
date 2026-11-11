# ClearGuard Backend — Production Database Operations & Backup Runbook

**Document Version:** 1.0.0  
**Target Database:** PostgreSQL 16+ (Production) / SQLite 3 (Local Development)  
**ORM / Driver:** SQLAlchemy 2.0+ with `asyncpg` / `aiosqlite`  

---

## 1. Production PostgreSQL Connection Architecture

In production, the ClearGuard backend connects to PostgreSQL using the asynchronous `asyncpg` driver via SQLAlchemy's `AsyncEngine`.

### 1.1 Connection Pool Settings

The connection pool is configured via environment variables in `Settings`:

| Setting | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/dbname` | Full connection string (driver auto-adjusted to `asyncpg`) |
| `DB_POOL_SIZE` | `20` | Base number of persistent connections in the pool |
| `DB_MAX_OVERFLOW` | `10` | Maximum temporary connections created during traffic spikes |
| `DB_POOL_TIMEOUT` | `30` | Seconds to wait for a free connection before raising `TimeoutError` |
| `DB_POOL_RECYCLE` | `1800` | Seconds (30m) after which a connection is closed and recreated |
| `pool_pre_ping` | `True` | Executes a lightweight `SELECT 1` ping to drop stale connections |

---

## 2. Migration Execution SOP

Migrations must be run prior to starting new application container instances.

### 2.1 Online Automated Migration
```bash
# Executed within container or deployment job
uv run alembic upgrade head
```

### 2.2 Offline SQL Review (Zero-Downtime Verification)
To inspect the raw DDL before execution on production:
```bash
uv run alembic upgrade head --sql > migration_review.sql
```

---

## 3. Database Backup & Disaster Recovery

### 3.1 Daily Logical Backups (`pg_dump`)
Automated nightly backup jobs execute compressed directory or custom format dumps:

```bash
pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME -Fc -f "/backups/clearguard_$(date +%Y%m%d_%H%M%S).dump"
```

### 3.2 Restoration Runbook
To restore a backup into a fresh or recovery PostgreSQL instance:

```bash
# 1. Terminate existing app connections
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'clearguard_prod';

# 2. Restore database
pg_restore -h $DB_HOST -U $DB_USER -d $DB_NAME -v "/backups/clearguard_target.dump"

# 3. Verify Alembic migration version table
SELECT version_num FROM alembic_version;
```

### 3.3 Recovery Time Objective (RTO) & Recovery Point Objective (RPO)
- **RPO**: < 1 hour (via automated hourly incremental WAL archiving)
- **RTO**: < 15 minutes (spin up restored PostgreSQL replica + verify API connectivity)

