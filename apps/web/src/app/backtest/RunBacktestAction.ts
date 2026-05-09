"use server";

/**
 * Server Action that proxies the backtest request to the Python sidecar
 * service running on Railway. Vercel can't run Python, so the sidecar
 * (services/backtest_api/) does the heavy lifting and we relay JSON.
 *
 * Set ``BACKTEST_API_URL`` on the Vercel environment (e.g.
 * https://alpha-kite-backtest-api.up.railway.app) for this to work.
 */

export interface BacktestSummary {
  trades: number;
  wins: number;
  losses: number;
  win_rate_pct: number;
  avg_win_pct: number;
  avg_loss_pct: number;
  expectancy_pct: number;
  total_pnl_pct: number;
}

export interface BacktestTrade {
  intent_id: string;
  entry_ts: string;
  entry_price: string;
  side: "BUY" | "SELL";
  right: "C" | "P";
  strike: string;
  expiry: string;
  exit_ts: string | null;
  exit_price: string | null;
  pnl_pct: string | null;
  reason: string;
}

export interface BacktestResult {
  fixture: string;
  config: string;
  summary: BacktestSummary;
  trades: BacktestTrade[];
  split?: {
    split_date: string;
    all: BacktestSummary;
    in_sample: BacktestSummary;
    out_of_sample: BacktestSummary;
  };
}

export interface SymbolEntry {
  symbol: string;
  interval_seconds: number;
  first_bar: string;
  last_bar: string;
  n_bars: number;
}

export type BacktestInput =
  | { source: "fixture"; fixture: string; splitDate?: string }
  | {
      source: "supabase";
      symbol: string;
      start: string;
      end: string;
      intervalSeconds: number;
      splitDate?: string;
    };

export async function runBacktest(
  input: BacktestInput,
): Promise<{ ok: true; data: BacktestResult } | { ok: false; error: string }> {
  const baseUrl = process.env.BACKTEST_API_URL;
  if (!baseUrl) {
    return {
      ok: false,
      error:
        "BACKTEST_API_URL is not set on the web app. Deploy services/backtest-api/ to Railway and set this env var.",
    };
  }
  const body: Record<string, unknown> =
    input.source === "fixture"
      ? { fixture: input.fixture, split_date: input.splitDate || null }
      : {
          symbol: input.symbol,
          start: input.start,
          end: input.end,
          interval_seconds: input.intervalSeconds,
          split_date: input.splitDate || null,
        };

  try {
    const res = await fetch(`${baseUrl.replace(/\/$/, "")}/run`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      // DB-bars backtests over many days can take longer than fixture replay.
      signal: AbortSignal.timeout(120_000),
    });
    if (!res.ok) {
      const text = await res.text();
      return { ok: false, error: `sidecar ${res.status}: ${text}` };
    }
    const data = (await res.json()) as BacktestResult;

    // Auto-write a BACKTEST_PASS audit row when the run produced closed
    // trades with positive expectancy. /live-enable's "backtest passed in
    // last 24h" gate queries audit_log for this event_type.
    if (data.summary.trades > 0 && data.summary.expectancy_pct > 0) {
      await writeBacktestPassAudit(input, data).catch(() => {
        // Audit write is best-effort — never fail the user's backtest run
        // because the dashboard couldn't write a row.
      });
    }

    return { ok: true, data };
  } catch (err) {
    return {
      ok: false,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

async function writeBacktestPassAudit(
  input: BacktestInput,
  result: BacktestResult,
): Promise<void> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  // Without service-role we can't bypass RLS to insert into audit_log.
  // Skip silently — the rest of the dashboard still works; the gate just
  // won't auto-flip on backtest success.
  if (!url || !serviceKey) return;
  const { createClient } = await import("@supabase/supabase-js");
  const sb = createClient(url, serviceKey, { auth: { persistSession: false } });
  const sourceLabel =
    input.source === "fixture"
      ? { fixture: input.fixture }
      : {
          symbol: input.symbol,
          start: input.start,
          end: input.end,
          interval_seconds: input.intervalSeconds,
        };
  await sb.from("audit_log").insert({
    actor: "dashboard:/backtest",
    event_type: "BACKTEST_PASS",
    severity: "INFO",
    message: `backtest passed: ${result.summary.trades} trades, expectancy ${result.summary.expectancy_pct}%`,
    payload: {
      ...sourceLabel,
      trades: result.summary.trades,
      wins: result.summary.wins,
      losses: result.summary.losses,
      win_rate_pct: result.summary.win_rate_pct,
      expectancy_pct: result.summary.expectancy_pct,
      total_pnl_pct: result.summary.total_pnl_pct,
    },
  });
}

export async function listFixtures(): Promise<string[]> {
  const baseUrl = process.env.BACKTEST_API_URL;
  if (!baseUrl) return [];
  try {
    const res = await fetch(`${baseUrl.replace(/\/$/, "")}/fixtures`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return [];
    const j = (await res.json()) as { fixtures: string[] };
    return j.fixtures;
  } catch {
    return [];
  }
}

export async function listSupabaseSymbols(): Promise<SymbolEntry[]> {
  const baseUrl = process.env.BACKTEST_API_URL;
  if (!baseUrl) return [];
  try {
    const res = await fetch(`${baseUrl.replace(/\/$/, "")}/symbols`, {
      // Bar coverage changes only when backfill runs — short cache is plenty.
      next: { revalidate: 30 },
    });
    if (!res.ok) return [];
    const j = (await res.json()) as { symbols?: SymbolEntry[] };
    return j.symbols ?? [];
  } catch {
    return [];
  }
}
