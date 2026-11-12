# ClearGuard Admin Dashboard (`frontend/`)

Lightweight static Single-Page Application (SPA) for ClearGuard administration, built with **Vite + React + TypeScript + Tailwind CSS v4 + shadcn/ui** (no Next.js / SSR server runtime).

## Tech Stack
- **Vite** + **React** + **TypeScript** -> compiles to static `dist/` assets
- **shadcn/ui** (`radix-nova`) for UI primitives, **Data Tables** (`@tanstack/react-table`), and **Charts** (`recharts`)
- **React Router** (`react-router-dom`) for SPA navigation
- **Lucide Icons** (`lucide-react`)

## Local Development

1. Configure your API endpoint (optional — defaults to `http://127.0.0.1:8000/api/v1`):
   ```bash
   cp .env.example .env
   ```
2. Install dependencies and start the dev server:
   ```bash
   pnpm install
   pnpm dev
   ```
3. Build static production assets:
   ```bash
   pnpm build
   ```

## Dashboard Sections
- **Overview (`/`)**: Live `/health` & `/health/ready` status, KPI summary cards, and **shadcn Charts** for blocklist sizes and pending 60-day deactivation cool-off timelines.
- **Emergency Overrides (`/overrides`)**: Pending deactivation queue, admin Ed25519 override approval dialog, and signed certificate viewer/copier.
- **Blocklists (`/blocklists`, `/blocklists/:id`)**: Paginated blocklists table, create/edit/delete actions, domain management, raw feed ingestion (Hosts / Adblock / plain), and version publish/rollback controls.
- **Security Keys (`/keys`)**: Export & inspect the ClearGuard Admin Ed25519 public key (`PEM`) used for offline Android verification.
- **Partner Co-Sign (`/verify?token=...`)**: Public route for accountability partners to validate email tokens and approve or reject deactivation requests.
