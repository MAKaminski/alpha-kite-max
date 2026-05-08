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
