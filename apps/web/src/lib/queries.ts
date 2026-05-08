import { getSupabase } from "./supabase";
import type {
  AuditEvent,
  AuditSeverity,
  DailyPnl,
  OptionRight,
  Position,
  Signal,
  SignalDirection,
} from "@/types/api";

// ─────────────────────────────────────────────────────────────────────────
// Row shapes as returned by Supabase (snake_case mirroring the SQL schema).
// We map these into the camelCase `api.ts` interfaces below.
// ─────────────────────────────────────────────────────────────────────────

interface SignalRow {
  id: number;
  strategy: string;
  symbol: string;
  direction: string;
  ts: string;
  strength: string | number;
  metadata: Record<string, unknown> | null;
}

interface PositionRow {
  id: number;
  as_of: string;
  symbol: string;
  is_option: boolean;
  option_expiry: string | null;
  option_strike: string | number | null;
  option_right: string | null;
  quantity: number;
  avg_cost: string | number;
  market_value: string | number | null;
  unrealized_pnl: string | number | null;
}

interface DailyPnlRow {
  trading_day: string;
  realized_usd: string | number;
  unrealized_usd: string | number;
  trades: number;
  wins: number;
  losses: number;
  updated_at: string;
}

interface AuditRow {
  id: number;
  ts: string;
  actor: string;
  event_type: string;
  severity: string;
  message: string;
  payload: Record<string, unknown> | null;
}

// ─────────────────────────────────────────────────────────────────────────
// Mappers
// ─────────────────────────────────────────────────────────────────────────

function toStr(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "";
  return typeof value === "string" ? value : String(value);
}

function toStrOrNull(value: string | number | null | undefined): string | null {
  if (value === null || value === undefined) return null;
  return typeof value === "string" ? value : String(value);
}

function mapSignal(row: SignalRow): Signal {
  return {
    name: row.strategy,
    direction: (row.direction as SignalDirection) ?? "NONE",
    timestamp: row.ts,
    symbol: row.symbol,
    strength: toStr(row.strength),
    metadata: stringifyMetadata(row.metadata),
  };
}

function stringifyMetadata(
  meta: Record<string, unknown> | null,
): Record<string, string> {
  if (!meta) return {};
  const out: Record<string, string> = {};
  for (const [k, v] of Object.entries(meta)) {
    if (v === null || v === undefined) {
      out[k] = "";
    } else if (typeof v === "object") {
      out[k] = JSON.stringify(v);
    } else {
      out[k] = String(v);
    }
  }
  return out;
}

function mapPosition(row: PositionRow): Position {
  const option = row.is_option
    ? {
        underlying: row.symbol,
        expiry: row.option_expiry ?? "",
        strike: toStr(row.option_strike),
        right: ((row.option_right ?? "C") as OptionRight),
      }
    : null;
  return {
    symbol: row.symbol,
    isOption: row.is_option,
    option,
    quantity: row.quantity,
    avgCost: toStr(row.avg_cost),
    marketValue: toStrOrNull(row.market_value),
    unrealizedPnl: toStrOrNull(row.unrealized_pnl),
  };
}

function mapDailyPnl(row: DailyPnlRow): DailyPnl {
  return {
    tradingDay: row.trading_day,
    realizedUsd: toStr(row.realized_usd),
    unrealizedUsd: toStr(row.unrealized_usd),
    trades: row.trades,
    wins: row.wins,
    losses: row.losses,
    updatedAt: row.updated_at,
  };
}

function mapAudit(row: AuditRow): AuditEvent {
  const severity =
    row.severity === "INFO" || row.severity === "WARN" || row.severity === "ERROR"
      ? (row.severity as AuditSeverity)
      : "INFO";
  return {
    id: row.id,
    ts: row.ts,
    actor: row.actor,
    eventType: row.event_type,
    severity,
    message: row.message,
    payload: row.payload ?? {},
  };
}

// ─────────────────────────────────────────────────────────────────────────
// Public queries
// ─────────────────────────────────────────────────────────────────────────

/** Last `limit` signals, newest first. */
export async function fetchSignals(limit = 100): Promise<Signal[]> {
  const supa = getSupabase();
  if (!supa) return SIGNAL_FIXTURES.slice(0, limit);

  const { data, error } = await supa
    .from("signals")
    .select("id, strategy, symbol, direction, ts, strength, metadata")
    .order("ts", { ascending: false })
    .limit(limit);

  if (error) {
    console.error("[queries] fetchSignals failed:", error.message);
    return [];
  }
  return (data ?? []).map((r) => mapSignal(r as SignalRow));
}

/** Open positions (quantity != 0). */
export async function fetchOpenPositions(): Promise<Position[]> {
  const supa = getSupabase();
  if (!supa) return POSITION_FIXTURES;

  const { data, error } = await supa
    .from("positions")
    .select(
      "id, as_of, symbol, is_option, option_expiry, option_strike, option_right, quantity, avg_cost, market_value, unrealized_pnl",
    )
    .neq("quantity", 0)
    .order("symbol", { ascending: true });

  if (error) {
    console.error("[queries] fetchOpenPositions failed:", error.message);
    return [];
  }
  return (data ?? []).map((r) => mapPosition(r as PositionRow));
}

/** Trailing N daily P&L rows, oldest → newest (for sparkline). */
export async function fetchDailyPnl(limit = 30): Promise<DailyPnl[]> {
  const supa = getSupabase();
  if (!supa) return DAILY_PNL_FIXTURES.slice(-limit);

  const { data, error } = await supa
    .from("daily_pnl")
    .select(
      "trading_day, realized_usd, unrealized_usd, trades, wins, losses, updated_at",
    )
    .order("trading_day", { ascending: false })
    .limit(limit);

  if (error) {
    console.error("[queries] fetchDailyPnl failed:", error.message);
    return [];
  }
  // We fetched newest-first to use the index; reverse for display/sparkline.
  return (data ?? []).map((r) => mapDailyPnl(r as DailyPnlRow)).reverse();
}

/** Last `limit` audit rows; optional severity filter. */
export async function fetchAuditLog(
  limit = 200,
  severity?: AuditSeverity,
): Promise<AuditEvent[]> {
  const supa = getSupabase();
  if (!supa) {
    const all = AUDIT_FIXTURES;
    return severity ? all.filter((e) => e.severity === severity) : all;
  }

  let query = supa
    .from("audit_log")
    .select("id, ts, actor, event_type, severity, message, payload")
    .order("ts", { ascending: false })
    .limit(limit);
  if (severity) query = query.eq("severity", severity);

  const { data, error } = await query;
  if (error) {
    console.error("[queries] fetchAuditLog failed:", error.message);
    return [];
  }
  return (data ?? []).map((r) => mapAudit(r as AuditRow));
}

// ─────────────────────────────────────────────────────────────────────────
// /status — health check for non-technical users.
// Each component reports: alive boolean, last_seen ISO string, expected
// cadence in plain English. Health rules are intentionally simple (data
// freshness only); production deployments should add real liveness probes.
// ─────────────────────────────────────────────────────────────────────────

export type ComponentHealth = "healthy" | "stale" | "down" | "unknown";

export interface ComponentStatus {
  name: string;
  health: ComponentHealth;
  lastSeen: string | null;
  cadence: string;
  detail: string;
}

export interface SystemStatus {
  components: ComponentStatus[];
  generatedAt: string;
}

function classifyFreshness(
  isoTs: string | null,
  healthyWithinSec: number,
  staleWithinSec: number,
): ComponentHealth {
  if (!isoTs) return "unknown";
  const ageSec = (Date.now() - new Date(isoTs).getTime()) / 1000;
  if (ageSec <= healthyWithinSec) return "healthy";
  if (ageSec <= staleWithinSec) return "stale";
  return "down";
}

async function fetchLatestTs(
  table: string,
  tsCol: string,
  filter?: { col: string; eq: string },
): Promise<string | null> {
  const supabase = getSupabase();
  if (!supabase) return null;
  let q = supabase.from(table).select(tsCol).order(tsCol, { ascending: false }).limit(1);
  if (filter) q = q.eq(filter.col, filter.eq);
  const { data, error } = await q;
  if (error || !data || data.length === 0) return null;
  const row = data[0] as unknown as Record<string, string | null | undefined>;
  return row[tsCol] ?? null;
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const now = new Date().toISOString();
  if (!getSupabase()) {
    // Dev fixture: pretend everything is healthy 30s ago.
    const recent = new Date(Date.now() - 30_000).toISOString();
    return {
      generatedAt: now,
      components: [
        { name: "Strategy engine",   health: "healthy", lastSeen: recent, cadence: "Heartbeat every 60s", detail: "Watches QQQ for SMA9/VWAP crosses." },
        { name: "Market data feed",  health: "healthy", lastSeen: recent, cadence: "Heartbeat every 60s",   detail: "Streams price bars into Supabase." },
        { name: "Supabase database", health: "healthy", lastSeen: now,    cadence: "Always-on",              detail: "Stores ticks, signals, fills, audit." },
        { name: "Latest signal",     health: "stale",   lastSeen: recent, cadence: "When SMA9/VWAP crosses", detail: "Generated by the engine." },
        { name: "Latest fill",       health: "stale",   lastSeen: null,   cadence: "After signal + risk OK", detail: "DRY-RUN — no real orders placed." },
        { name: "Kill switch",       health: "healthy", lastSeen: now,    cadence: "Manual (touch ./KILL)",  detail: "Engaged: blocks all new entries." },
      ],
    };
  }

  // Real queries — issued in parallel.
  const [
    engineHb,
    feedHb,
    latestBar,
    latestSignal,
    latestFill,
    killSwitchEvent,
  ] = await Promise.all([
    fetchLatestTs("audit_log", "ts", { col: "actor",      eq: "engine" }),
    fetchLatestTs("audit_log", "ts", { col: "actor",      eq: "market_data_stream" }),
    fetchLatestTs("bars",      "open_time"),
    fetchLatestTs("signals",   "ts"),
    fetchLatestTs("fills",     "ts"),
    fetchLatestTs("audit_log", "ts", { col: "event_type", eq: "KILL_SWITCH" }),
  ]);

  // Engine: heartbeat every 60s; healthy if seen in 2 min, stale 10 min, else down.
  const engineHealth = classifyFreshness(engineHb, 120, 600);
  const feedHealth   = classifyFreshness(feedHb,   120, 600);

  return {
    generatedAt: now,
    components: [
      {
        name: "Strategy engine",
        health: engineHealth,
        lastSeen: engineHb,
        cadence: "Heartbeat every 60s",
        detail: "Watches QQQ for SMA9/VWAP crosses; emits orders.",
      },
      {
        name: "Market-data stream",
        health: feedHealth,
        lastSeen: feedHb,
        cadence: "Heartbeat every 60s",
        detail: "Pulls 1-min bars into Supabase.",
      },
      {
        name: "Bars persisted",
        health: classifyFreshness(latestBar, 120, 60 * 60 * 24),
        lastSeen: latestBar,
        cadence: "1 per minute during market hours (9:30-4:00 ET)",
        detail: "Most recent OHLCV bar saved to Supabase.",
      },
      {
        name: "Supabase database",
        health: "healthy",
        lastSeen: now,
        cadence: "Always-on",
        detail: "If you can read this page, the DB is reachable.",
      },
      {
        name: "Latest signal",
        health: latestSignal ? classifyFreshness(latestSignal, 60 * 60, 60 * 60 * 24) : "unknown",
        lastSeen: latestSignal,
        cadence: "When the SMA(9) crosses the session VWAP — typically 0–5/day",
        detail: latestSignal ? "Most recent SMA/VWAP cross detected." : "No crosses detected yet.",
      },
      {
        name: "Latest fill",
        health: latestFill ? classifyFreshness(latestFill, 60 * 60, 60 * 60 * 24) : "unknown",
        lastSeen: latestFill,
        cadence: "After every signal that passes risk checks",
        detail: latestFill ? "Most recent broker fill recorded." : "No fills yet — engine is in dry-run.",
      },
      {
        name: "Kill switch",
        health: killSwitchEvent && classifyFreshness(killSwitchEvent, 60 * 60 * 24, Number.MAX_SAFE_INTEGER) !== "down"
          ? "down"
          : "healthy",
        lastSeen: killSwitchEvent,
        cadence: "Manual operator action",
        detail: killSwitchEvent
          ? "ENGAGED — engine is blocking new entries. Remove the KILL file to resume."
          : "Disengaged — engine is free to trade per its rules.",
      },
    ],
  };
}

// ─────────────────────────────────────────────────────────────────────────
// Fixtures (used when env is unset, so the UI is never blank in dev).
// ─────────────────────────────────────────────────────────────────────────

const SIGNAL_FIXTURES: Signal[] = [
  {
    name: "vol_breakout",
    direction: "LONG_VOL_UP",
    timestamp: "2026-05-07T13:42:11Z",
    symbol: "SPY",
    strength: "0.8200",
    metadata: { iv_rank: "62", ema_fast: "510.2", ema_slow: "508.4" },
  },
  {
    name: "vol_breakout",
    direction: "EXIT",
    timestamp: "2026-05-07T13:30:02Z",
    symbol: "QQQ",
    strength: "1.0000",
    metadata: { reason: "stop", entry: "445.10" },
  },
  {
    name: "mean_revert",
    direction: "LONG_VOL_DOWN",
    timestamp: "2026-05-07T12:58:55Z",
    symbol: "IWM",
    strength: "0.6500",
    metadata: { rsi: "78.4" },
  },
];

const POSITION_FIXTURES: Position[] = [
  {
    symbol: "SPY",
    isOption: false,
    option: null,
    quantity: 100,
    avgCost: "508.42",
    marketValue: "51210.00",
    unrealizedPnl: "368.00",
  },
  {
    symbol: "SPY",
    isOption: true,
    option: {
      underlying: "SPY",
      expiry: "2026-06-19",
      strike: "520",
      right: "C",
    },
    quantity: 5,
    avgCost: "3.40",
    marketValue: "1825.00",
    unrealizedPnl: "125.00",
  },
];

function buildPnlFixtures(): DailyPnl[] {
  // Deterministic sample: 30 days ending today, gentle equity curve.
  const out: DailyPnl[] = [];
  const today = new Date("2026-05-07T00:00:00Z");
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today);
    d.setUTCDate(d.getUTCDate() - i);
    const day = d.toISOString().slice(0, 10);
    // Pseudo-random realized values, drift slightly positive.
    const realized = Math.sin(i * 0.7) * 120 + (29 - i) * 4.2;
    const unrealized = Math.cos(i * 0.5) * 80;
    const trades = 3 + (i % 5);
    const wins = Math.max(0, Math.round(trades * 0.55));
    const losses = trades - wins;
    out.push({
      tradingDay: day,
      realizedUsd: realized.toFixed(2),
      unrealizedUsd: unrealized.toFixed(2),
      trades,
      wins,
      losses,
      updatedAt: `${day}T20:00:00Z`,
    });
  }
  return out;
}

const DAILY_PNL_FIXTURES: DailyPnl[] = buildPnlFixtures();

const AUDIT_FIXTURES: AuditEvent[] = [
  {
    id: 3,
    ts: "2026-05-07T13:42:11Z",
    actor: "engine",
    eventType: "ORDER_INTENT",
    severity: "INFO",
    message: "intent created for SPY x100",
    payload: { intent_id: "5b1e…", dry_run: false },
  },
  {
    id: 2,
    ts: "2026-05-07T13:38:50Z",
    actor: "risk",
    eventType: "RISK_BLOCK",
    severity: "WARN",
    message: "intent blocked: max position size",
    payload: { symbol: "QQQ", limit: 100 },
  },
  {
    id: 1,
    ts: "2026-05-07T13:00:00Z",
    actor: "operator",
    eventType: "KILL_SWITCH",
    severity: "ERROR",
    message: "kill switch armed for session",
    payload: {},
  },
];
