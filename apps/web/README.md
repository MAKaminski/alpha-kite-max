# alpha-kite web

Read-only Next.js 15 dashboard for alpha-kite-v2. Server components query
Supabase directly via `@supabase/supabase-js`.

## Pages

- `/signals` — last 100 strategy signals
- `/positions` — currently open positions (quantity != 0)
- `/pnl` — daily P&L, trailing 30 trading days (with sparkline)
- `/audit` — last 200 audit log rows, filterable by severity

## Local development

```bash
npm install --no-audit --no-fund
npm run dev
```

Set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` in your
environment to query a live database. If unset, the queries return small
deterministic fixtures so the UI renders without an empty state.

## Build

```bash
npm run build
npm start
```

## Stack

- Next.js 15 App Router (server components by default)
- Tailwind CSS, monochrome look (no chart library; sparkline is inline SVG)
- Supabase JS client; types come from `src/types/api.ts`
