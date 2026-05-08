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
// /charts data shapes — bars + signal/fill markers for a given trading day
// ─────────────────────────────────────────────────────────────────────────

export interface ChartBar {
  time: number;       // unix seconds (lightweight-charts native format)
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  vwap: number | null;
}

export interface ChartMarker {
  time: number;       // unix seconds
  kind: "signal_up" | "signal_down" | "buy_fill" | "sell_fill";
  label: string;
  price: number | null;
}

export interface DayPnl {
  day: string;        // YYYY-MM-DD
  realizedUsd: number;
  cumulativeUsd: number;
  trades: number;
  wins: number;
  losses: number;
}

interface BarRow {
  symbol: string;
  open_time: string;
  open: string | number;
  high: string | number;
  low: string | number;
  close: string | number;
  volume: number;
  vwap: string | number | null;
}

interface SignalRowChart {
  ts: string;
  direction: string;
  symbol: string;
  metadata: Record<string, unknown> | null;
}

interface FillRowChart {
  ts: string;
  symbol: string;
  side: string;
  price: string | number;
  is_option: boolean;
  option_strike: string | number | null;
  option_right: string | null;
}

interface DailyPnlRowChart {
  trading_day: string;
  realized_usd: string | number;
  trades: number;
  wins: number;
  losses: number;
}

const NUM = (v: string | number | null | undefined): number =>
  v === null || v === undefined ? 0 : typeof v === "number" ? v : Number(v);

export async function fetchChartBars(
  symbol: string,
  day: string,                     // YYYY-MM-DD (UTC date)
): Promise<ChartBar[]> {
  const supabase = getSupabase();
  if (!supabase) return [];
  const dayStart = `${day}T00:00:00Z`;
  const dayEnd = `${day}T23:59:59Z`;
  const { data, error } = await supabase
    .from("bars")
    .select("symbol,open_time,open,high,low,close,volume,vwap")
    .eq("symbol", symbol)
    .gte("open_time", dayStart)
    .lte("open_time", dayEnd)
    .order("open_time", { ascending: true });
  if (error || !data) return [];
  return (data as BarRow[]).map((r) => ({
    time: Math.floor(new Date(r.open_time).getTime() / 1000),
    open: NUM(r.open),
    high: NUM(r.high),
    low: NUM(r.low),
    close: NUM(r.close),
    volume: r.volume,
    vwap: r.vwap === null || r.vwap === undefined ? null : NUM(r.vwap),
  }));
}

export async function fetchChartMarkers(
  symbol: string,
  day: string,
): Promise<ChartMarker[]> {
  const supabase = getSupabase();
  if (!supabase) return [];
  const dayStart = `${day}T00:00:00Z`;
  const dayEnd = `${day}T23:59:59Z`;

  const [signalsRes, fillsRes] = await Promise.all([
    supabase
      .from("signals")
      .select("ts,direction,symbol,metadata")
      .eq("symbol", symbol)
      .gte("ts", dayStart)
      .lte("ts", dayEnd)
      .order("ts", { ascending: true }),
    supabase
      .from("fills")
      .select("ts,symbol,side,price,is_option,option_strike,option_right")
      .eq("symbol", symbol)
      .gte("ts", dayStart)
      .lte("ts", dayEnd)
      .order("ts", { ascending: true }),
  ]);

  const markers: ChartMarker[] = [];
  if (signalsRes.data) {
    for (const r of signalsRes.data as SignalRowChart[]) {
      const dir = r.direction;
      if (dir === "LONG_VOL_UP" || dir === "LONG_VOL_DOWN") {
        markers.push({
          time: Math.floor(new Date(r.ts).getTime() / 1000),
          kind: dir === "LONG_VOL_UP" ? "signal_up" : "signal_down",
          label: dir === "LONG_VOL_UP" ? "▲ UP" : "▼ DN",
          price: null,
        });
      }
    }
  }
  if (fillsRes.data) {
    for (const r of fillsRes.data as FillRowChart[]) {
      markers.push({
        time: Math.floor(new Date(r.ts).getTime() / 1000),
        kind: r.side === "BUY" ? "buy_fill" : "sell_fill",
        label: `${r.side} ${r.is_option ? `${r.option_strike}${r.option_right}` : ""}`.trim(),
        price: NUM(r.price),
      });
    }
  }
  markers.sort((a, b) => a.time - b.time);
  return markers;
}

// ─────────────────────────────────────────────────────────────────────────
// Broker / account snapshot — read by /status (IBKR connection row) and
// /charts (portfolio balance card). Source of truth is the latest
// BROKER_HEARTBEAT audit row written by the strategy engine every 60 s.
// ─────────────────────────────────────────────────────────────────────────

export interface BrokerSnapshot {
  accountId: string | null;
  brokerMode: string | null;     // "paper" | "live"
  dryRun: boolean | null;
  navUsd: string | null;
  cashUsd: string | null;
  buyingPowerUsd: string | null;
  connected: boolean | null;
  lastError: string | null;
  lastSeen: string | null;       // ISO timestamp
  severity: AuditSeverity | null;
}

export async function fetchBrokerSnapshot(): Promise<BrokerSnapshot> {
  const empty: BrokerSnapshot = {
    accountId: null,
    brokerMode: null,
    dryRun: null,
    navUsd: null,
    cashUsd: null,
    buyingPowerUsd: null,
    connected: null,
    lastError: null,
    lastSeen: null,
    severity: null,
  };
  const supabase = getSupabase();
  if (!supabase) return empty;
  const { data, error } = await supabase
    .from("audit_log")
    .select("ts,event_type,severity,message,payload")
    .in("event_type", ["BROKER_HEARTBEAT", "BROKER_ERROR"])
    .order("ts", { ascending: false })
    .limit(1);
  if (error || !data || data.length === 0) return empty;
  const row = data[0] as {
    ts: string;
    event_type: string;
    severity: string;
    message: string;
    payload: Record<string, unknown> | null;
  };
  const p = row.payload ?? {};
  const get = (k: string): string | null => {
    const v = p[k];
    if (v === null || v === undefined) return null;
    return typeof v === "string" ? v : String(v);
  };
  return {
    accountId: get("account_id"),
    brokerMode: get("broker_mode"),
    dryRun: typeof p["dry_run"] === "boolean" ? (p["dry_run"] as boolean) : null,
    navUsd: get("nav"),
    cashUsd: get("cash"),
    buyingPowerUsd: get("buying_power"),
    connected:
      typeof p["connected"] === "boolean"
        ? (p["connected"] as boolean)
        : row.event_type === "BROKER_HEARTBEAT",
    lastError: row.event_type === "BROKER_ERROR" ? (get("error") ?? row.message) : null,
    lastSeen: row.ts,
    severity:
      row.severity === "INFO" || row.severity === "WARN" || row.severity === "ERROR"
        ? (row.severity as AuditSeverity)
        : "INFO",
  };
}

export async function fetchChartDailyPnl(daysBack = 30): Promise<DayPnl[]> {
  const supabase = getSupabase();
  if (!supabase) return [];
  const since = new Date();
  since.setUTCDate(since.getUTCDate() - daysBack);
  const sinceStr = since.toISOString().slice(0, 10);
  const { data, error } = await supabase
    .from("daily_pnl")
    .select("trading_day,realized_usd,trades,wins,losses")
    .gte("trading_day", sinceStr)
    .order("trading_day", { ascending: true });
  if (error || !data) return [];
  let cum = 0;
  return (data as DailyPnlRowChart[]).map((r) => {
    const realized = NUM(r.realized_usd);
    cum += realized;
    return {
      day: r.trading_day,
      realizedUsd: realized,
      cumulativeUsd: cum,
      trades: r.trades,
      wins: r.wins,
      losses: r.losses,
    };
  });
}

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

function mapPosition(
  row: PositionRow,
  enteredAt: string | null = null,
  entryPrice: string | null = null,
  isFixture: boolean = false,
): Position {
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
    enteredAt,
    entryPrice,
    isFixture,
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

/** Open positions (quantity != 0). Joins the earliest matching BUY fill so
 *  we can show "entered at" + entry price next to avg_cost. */
export async function fetchOpenPositions(): Promise<Position[]> {
  const supa = getSupabase();
  if (!supa) {
    return POSITION_FIXTURES.map((p) => ({ ...p, isFixture: true }));
  }

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
  const positions = (data ?? []) as PositionRow[];
  if (positions.length === 0) return [];

  // Pull the earliest BUY fill per contract so we can attach an entry
  // timestamp + entry price. One round-trip; we filter by symbols.
  const symbols = Array.from(new Set(positions.map((p) => p.symbol)));
  const { data: fillRows } = await supa
    .from("fills")
    .select("ts,symbol,side,price,is_option,option_expiry,option_strike,option_right")
    .in("symbol", symbols)
    .eq("side", "BUY")
    .order("ts", { ascending: true });

  const firstBuy = new Map<string, { ts: string; price: string }>();
  for (const f of (fillRows ?? []) as Array<{
    ts: string; symbol: string; side: string; price: string | number;
    is_option: boolean; option_expiry: string | null;
    option_strike: string | number | null; option_right: string | null;
  }>) {
    const k = positionKey({
      symbol: f.symbol,
      is_option: f.is_option,
      option_expiry: f.option_expiry,
      option_strike: f.option_strike,
      option_right: f.option_right,
    });
    if (!firstBuy.has(k)) {
      firstBuy.set(k, { ts: f.ts, price: toStr(f.price) });
    }
  }

  return positions.map((r) => {
    const k = positionKey(r);
    const entry = firstBuy.get(k) ?? null;
    return mapPosition(r, entry?.ts ?? null, entry?.price ?? null, false);
  });
}

function positionKey(p: {
  symbol: string;
  is_option: boolean;
  option_expiry: string | null;
  option_strike: string | number | null;
  option_right: string | null;
}): string {
  return [
    p.symbol,
    p.is_option ? "OPT" : "EQ",
    p.option_expiry ?? "",
    p.option_strike !== null && p.option_strike !== undefined
      ? String(p.option_strike)
      : "",
    p.option_right ?? "",
  ].join("|");
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

// ─────────────────────────────────────────────────────────────────────────
// /pnl drill-down — fills grouped by trading day so users can expand a
// daily-P&L row and see every individual buy/sell with its timestamp.
// ─────────────────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────────────────
// /orders view — order_intents joined to fills (1:N) and to RISK_BLOCK
// audit rows (intent_id in payload) so each row shows queued / blocked /
// placed / filled state.
// ─────────────────────────────────────────────────────────────────────────

export type OrderStatus = "filled" | "placed" | "blocked" | "dry-run" | "queued";

export interface OrderIntentRecord {
  intentId: string;
  createdAt: string;
  symbol: string;
  isOption: boolean;
  optionExpiry: string | null;
  optionStrike: string | null;
  optionRight: string | null;
  side: string;
  quantity: number;
  orderType: string;
  limitPrice: string | null;
  dryRun: boolean;
  submitted: boolean;
  brokerOrderId: string | null;
  tag: string;
  fills: { ts: string; quantity: number; price: string }[];
  blockReasons: string[];
  status: OrderStatus;
}

export async function fetchOrderIntents(limit = 50): Promise<OrderIntentRecord[]> {
  const supa = getSupabase();
  if (!supa) return [];

  const { data: intentRows, error } = await supa
    .from("order_intents")
    .select(
      "intent_id,created_at,symbol,is_option,option_expiry,option_strike,option_right,side,quantity,order_type,limit_price,dry_run,submitted,broker_order_id,tag",
    )
    .order("created_at", { ascending: false })
    .limit(limit);
  if (error || !intentRows || intentRows.length === 0) return [];

  const intentIds = (intentRows as Array<{ intent_id: string }>).map(
    (r) => r.intent_id,
  );

  const [fillsRes, riskRes] = await Promise.all([
    supa
      .from("fills")
      .select("intent_id,ts,quantity,price")
      .in("intent_id", intentIds),
    supa
      .from("audit_log")
      .select("event_type,payload")
      .eq("event_type", "RISK_BLOCK")
      .order("ts", { ascending: false })
      .limit(500),
  ]);

  const fillsByIntent = new Map<
    string,
    { ts: string; quantity: number; price: string }[]
  >();
  for (const f of (fillsRes.data ?? []) as Array<{
    intent_id: string;
    ts: string;
    quantity: number;
    price: string | number;
  }>) {
    const list = fillsByIntent.get(f.intent_id) ?? [];
    list.push({
      ts: f.ts,
      quantity: f.quantity,
      price: typeof f.price === "string" ? f.price : String(f.price),
    });
    fillsByIntent.set(f.intent_id, list);
  }

  const blocksByIntent = new Map<string, string[]>();
  for (const a of (riskRes.data ?? []) as Array<{
    event_type: string;
    payload: Record<string, unknown> | null;
  }>) {
    const p = a.payload ?? {};
    const id = typeof p["intent_id"] === "string" ? (p["intent_id"] as string) : null;
    if (!id || !intentIds.includes(id)) continue;
    const reasons = Array.isArray(p["reasons"])
      ? (p["reasons"] as unknown[]).map((x) => String(x))
      : [];
    if (!blocksByIntent.has(id)) blocksByIntent.set(id, reasons);
  }

  return (
    intentRows as Array<{
      intent_id: string;
      created_at: string;
      symbol: string;
      is_option: boolean;
      option_expiry: string | null;
      option_strike: string | number | null;
      option_right: string | null;
      side: string;
      quantity: number;
      order_type: string;
      limit_price: string | number | null;
      dry_run: boolean;
      submitted: boolean;
      broker_order_id: string | null;
      tag: string;
    }>
  ).map((r) => {
    const fills = fillsByIntent.get(r.intent_id) ?? [];
    const blockReasons = blocksByIntent.get(r.intent_id) ?? [];
    let status: OrderStatus;
    if (fills.length > 0) status = "filled";
    else if (blockReasons.length > 0) status = "blocked";
    else if (r.submitted) status = "placed";
    else if (r.dry_run) status = "dry-run";
    else status = "queued";
    return {
      intentId: r.intent_id,
      createdAt: r.created_at,
      symbol: r.symbol,
      isOption: r.is_option,
      optionExpiry: r.option_expiry,
      optionStrike:
        r.option_strike === null || r.option_strike === undefined
          ? null
          : typeof r.option_strike === "string"
            ? r.option_strike
            : String(r.option_strike),
      optionRight: r.option_right,
      side: r.side,
      quantity: r.quantity,
      orderType: r.order_type,
      limitPrice:
        r.limit_price === null || r.limit_price === undefined
          ? null
          : typeof r.limit_price === "string"
            ? r.limit_price
            : String(r.limit_price),
      dryRun: r.dry_run,
      submitted: r.submitted,
      brokerOrderId: r.broker_order_id,
      tag: r.tag,
      fills,
      blockReasons,
      status,
    };
  });
}

// ─────────────────────────────────────────────────────────────────────────
// /risk dashboard — read recent RISK_BLOCK / KILL_SWITCH events plus
// today's realized P&L so the UI can show daily-loss-limit headroom.
// ─────────────────────────────────────────────────────────────────────────

export interface RiskBlockEvent {
  ts: string;
  intentId: string | null;
  reasons: string[];
  payload: Record<string, unknown>;
}

export async function fetchRiskBlocks(limit = 20): Promise<RiskBlockEvent[]> {
  const supabase = getSupabase();
  if (!supabase) return [];
  const { data, error } = await supabase
    .from("audit_log")
    .select("ts,event_type,payload")
    .eq("event_type", "RISK_BLOCK")
    .order("ts", { ascending: false })
    .limit(limit);
  if (error || !data) return [];
  return (
    data as Array<{
      ts: string;
      event_type: string;
      payload: Record<string, unknown> | null;
    }>
  ).map((r) => {
    const p = r.payload ?? {};
    const reasons = Array.isArray(p["reasons"])
      ? (p["reasons"] as unknown[]).map((x) => String(x))
      : [];
    const intentId =
      typeof p["intent_id"] === "string" ? (p["intent_id"] as string) : null;
    return { ts: r.ts, intentId, reasons, payload: p };
  });
}

export async function fetchTodayRealizedUsd(): Promise<number> {
  const supabase = getSupabase();
  if (!supabase) return 0;
  const today = new Date().toISOString().slice(0, 10);
  const { data, error } = await supabase
    .from("daily_pnl")
    .select("realized_usd")
    .eq("trading_day", today)
    .limit(1);
  if (error || !data || data.length === 0) return 0;
  const v = (data[0] as { realized_usd: string | number }).realized_usd;
  const n = typeof v === "string" ? Number(v) : v;
  return Number.isFinite(n) ? n : 0;
}

/** Latest KILL_SWITCH event (active if exists and severity != INFO). */
export async function fetchKillSwitchState(): Promise<{
  lastSeen: string | null;
  active: boolean;
}> {
  const supabase = getSupabase();
  if (!supabase) return { lastSeen: null, active: false };
  const { data, error } = await supabase
    .from("audit_log")
    .select("ts,severity,payload")
    .eq("event_type", "KILL_SWITCH")
    .order("ts", { ascending: false })
    .limit(1);
  if (error || !data || data.length === 0) return { lastSeen: null, active: false };
  const row = data[0] as {
    ts: string;
    severity: string;
    payload: Record<string, unknown> | null;
  };
  const active =
    row.severity === "ERROR" ||
    (row.payload?.["engaged"] === true) ||
    (typeof row.payload?.["state"] === "string" &&
      (row.payload["state"] as string).toLowerCase() === "engaged");
  return { lastSeen: row.ts, active };
}

/** Most recent N bars across all symbols. Powers /status's "Live feed"
 *  panel: the initial server-render fills the ring buffer that the
 *  realtime subscription then keeps current. */
export interface RecentBar {
  symbol: string;
  openTime: string;       // ISO
  close: number;
  volume: number;
}

export async function fetchRecentBars(limit = 10): Promise<RecentBar[]> {
  const supabase = getSupabase();
  if (!supabase) return [];
  const { data, error } = await supabase
    .from("bars")
    .select("symbol,open_time,close,volume")
    .order("open_time", { ascending: false })
    .limit(limit);
  if (error || !data) return [];
  return (
    data as Array<{
      symbol: string;
      open_time: string;
      close: string | number;
      volume: number;
    }>
  ).map((r) => ({
    symbol: r.symbol,
    openTime: r.open_time,
    close: typeof r.close === "string" ? Number(r.close) : r.close,
    volume: r.volume,
  }));
}

/** Distinct symbols seen in the bars table (newest first). Powers the
 *  /charts symbol picker. Falls back to a single-element array when
 *  Supabase is unconfigured so the picker always has at least one option. */
export async function fetchAvailableSymbols(): Promise<string[]> {
  const supabase = getSupabase();
  if (!supabase) return ["QQQ"];
  // Supabase JS doesn't expose DISTINCT directly; we pull recent rows and
  // dedupe in memory. 1k rows is enough to surface every active symbol.
  const { data, error } = await supabase
    .from("bars")
    .select("symbol")
    .order("open_time", { ascending: false })
    .limit(1000);
  if (error || !data) return ["QQQ"];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const r of data as { symbol: string }[]) {
    if (!seen.has(r.symbol)) {
      seen.add(r.symbol);
      out.push(r.symbol);
    }
  }
  if (out.length === 0) out.push("QQQ");
  return out;
}

/** Names of the strategies the engine knows how to run. UI displays them
 *  in a picker; the picker is read-only until Stream E ships the
 *  runtime-override mechanism. */
export const KNOWN_STRATEGIES = [
  { id: "sma_vwap_cross", label: "Buy-vol cross (1-min bars)" },
  { id: "sma_vwap_cross_tick", label: "Buy-vol cross (tick)" },
  { id: "sell_put_qqq_cross", label: "Sell-put cross (tiered scale-out)" },
] as const;

export type StrategyId = (typeof KNOWN_STRATEGIES)[number]["id"];

export interface FillRecord {
  ts: string;                    // ISO timestamp
  symbol: string;
  side: "BUY" | "SELL" | string; // string fallback for forward-compat
  quantity: number;
  price: string;
  isOption: boolean;
  optionExpiry: string | null;
  optionStrike: string | null;
  optionRight: string | null;
}

/** Fetch all fills in [sinceDay, today], oldest → newest. Caller groups. */
export async function fetchFillsSince(sinceDay: string): Promise<FillRecord[]> {
  const supabase = getSupabase();
  if (!supabase) return [];
  const sinceIso = `${sinceDay}T00:00:00Z`;
  const { data, error } = await supabase
    .from("fills")
    .select(
      "ts,symbol,side,quantity,price,is_option,option_expiry,option_strike,option_right",
    )
    .gte("ts", sinceIso)
    .order("ts", { ascending: true });
  if (error || !data) return [];
  return (
    data as Array<{
      ts: string;
      symbol: string;
      side: string;
      quantity: number;
      price: string | number;
      is_option: boolean;
      option_expiry: string | null;
      option_strike: string | number | null;
      option_right: string | null;
    }>
  ).map((r) => ({
    ts: r.ts,
    symbol: r.symbol,
    side: r.side,
    quantity: r.quantity,
    price: typeof r.price === "string" ? r.price : String(r.price),
    isOption: r.is_option,
    optionExpiry: r.option_expiry,
    optionStrike:
      r.option_strike === null || r.option_strike === undefined
        ? null
        : typeof r.option_strike === "string"
          ? r.option_strike
          : String(r.option_strike),
    optionRight: r.option_right,
  }));
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
    brokerSnap,
  ] = await Promise.all([
    fetchLatestTs("audit_log", "ts", { col: "actor",      eq: "engine" }),
    fetchLatestTs("audit_log", "ts", { col: "actor",      eq: "market_data_stream" }),
    fetchLatestTs("bars",      "open_time"),
    fetchLatestTs("signals",   "ts"),
    fetchLatestTs("fills",     "ts"),
    fetchLatestTs("audit_log", "ts", { col: "event_type", eq: "KILL_SWITCH" }),
    fetchBrokerSnapshot(),
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
        name: "IBKR gateway",
        // Healthy if a BROKER_HEARTBEAT landed inside the last 5 min and
        // payload.connected was true. Anything older or a BROKER_ERROR
        // demotes the row.
        health: brokerSnap.lastSeen
          ? brokerSnap.connected
            ? classifyFreshness(brokerSnap.lastSeen, 300, 1800)
            : "down"
          : "unknown",
        lastSeen: brokerSnap.lastSeen,
        cadence: "Heartbeat every 60s",
        detail: brokerSnap.lastError
          ? `IBKR error: ${brokerSnap.lastError}`
          : brokerSnap.accountId
            ? `Connected to ${brokerSnap.accountId} (${brokerSnap.brokerMode ?? "paper"})${brokerSnap.dryRun ? " · dry-run" : ""}`
            : "Awaiting first broker heartbeat from the engine.",
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
    enteredAt: "2026-05-06T13:42:00Z",
    entryPrice: "508.42",
    isFixture: true,
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
    enteredAt: "2026-05-07T14:02:00Z",
    entryPrice: "3.40",
    isFixture: true,
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
