// TypeScript mirror of contracts/*.py and infra/supabase/migrations/0001_initial.sql.
// Hand-maintained — keep in sync when contracts change. Ordered to match the
// Python module-by-module layout for diff-ability.

// ───── Data feed ─────────────────────────────────────────────────────────
export type OptionRight = "C" | "P";

export interface Quote {
  symbol: string;
  timestamp: string; // ISO-8601
  bid: string; // decimal as string (preserve precision)
  ask: string;
  last: string | null;
  volume: number | null;
}

export interface Bar {
  symbol: string;
  intervalSeconds: number;
  openTime: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: number;
  vwap: string | null;
  feed: string;
}

export interface OptionContract {
  underlying: string;
  expiry: string; // ISO date
  strike: string;
  right: OptionRight;
  multiplier?: number;
  exchange?: string;
}

export interface OptionQuote {
  underlying: string;
  expiry: string;
  strike: string;
  right: OptionRight;
  timestamp: string;
  bid: string;
  ask: string;
  last: string | null;
  iv: string | null;
  delta: string | null;
  gamma: string | null;
  theta: string | null;
  vega: string | null;
}

// ───── Broker ────────────────────────────────────────────────────────────
export type OrderSide = "BUY" | "SELL";
export type OrderType = "MKT" | "LMT";
export type TimeInForce = "DAY" | "GTC" | "IOC";
export type OrderStatus =
  | "PENDING_SUBMIT"
  | "SUBMITTED"
  | "PARTIAL"
  | "FILLED"
  | "CANCELLED"
  | "REJECTED";
export type AccountType = "PAPER" | "DEMO" | "LIVE" | "UNKNOWN";

export interface OrderIntent {
  intentId: string; // uuid
  createdAt: string;
  symbol: string;
  isOption: boolean;
  option: OptionContract | null;
  side: OrderSide;
  quantity: number;
  orderType: OrderType;
  limitPrice: string | null;
  timeInForce: TimeInForce;
  dryRun: boolean;
  tag: string;
  submitted: boolean;
  brokerOrderId: string | null;
}

export interface Fill {
  fillId: string;
  intentId: string;
  brokerOrderId: string;
  timestamp: string;
  symbol: string;
  isOption: boolean;
  option: OptionContract | null;
  side: OrderSide;
  quantity: number;
  price: string;
  commission: string;
}

export interface Position {
  symbol: string;
  isOption: boolean;
  option: OptionContract | null;
  quantity: number;
  avgCost: string;
  marketValue: string | null;
  unrealizedPnl: string | null;
}

export interface AccountSummary {
  accountId: string;
  accountType: AccountType;
  cash: string;
  buyingPower: string;
  netLiquidation: string;
  realizedPnlToday: string;
  unrealizedPnl: string;
  fetchedAt: string;
}

// ───── Strategy ──────────────────────────────────────────────────────────
export type SignalDirection = "LONG_VOL_UP" | "LONG_VOL_DOWN" | "EXIT" | "NONE";

export interface Signal {
  name: string;
  direction: SignalDirection;
  timestamp: string;
  symbol: string;
  strength: string;
  metadata: Record<string, string>;
}

// ───── P&L ───────────────────────────────────────────────────────────────
export interface DailyPnl {
  tradingDay: string;
  realizedUsd: string;
  unrealizedUsd: string;
  trades: number;
  wins: number;
  losses: number;
  updatedAt: string;
}

// ───── Audit log ─────────────────────────────────────────────────────────
export type AuditSeverity = "INFO" | "WARN" | "ERROR";

export interface AuditEvent {
  id: number;
  ts: string;
  actor: string;
  eventType: string;
  severity: AuditSeverity;
  message: string;
  payload: Record<string, unknown>;
}
