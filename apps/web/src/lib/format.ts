/**
 * Number / date formatters used by the dashboard.
 * Small and dependency-free — money values arrive as strings (decimal-safe)
 * and are rendered by parsing into Number for display only.
 */

const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

const usd4 = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 4,
});

const numFmt = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 4,
});

const intFmt = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
});

export function fmtUsd(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return "—";
  return usd.format(n);
}

export function fmtUsdPrecise(
  value: string | number | null | undefined,
): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return "—";
  return usd4.format(n);
}

export function fmtNumber(
  value: string | number | null | undefined,
  digits = 4,
): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(n);
}

export function fmtInt(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(n)) return "—";
  return intFmt.format(n);
}

/** Render a UTC timestamp as a short local string (date + HH:MM:SS). */
export function fmtTime(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  // YYYY-MM-DD HH:MM:SS — stable across locales for a trader-style UI.
  const pad = (n: number) => n.toString().padStart(2, "0");
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  );
}

export function fmtDate(value: string | null | undefined): string {
  if (!value) return "—";
  // value is either ISO date (YYYY-MM-DD) or full ISO timestamp.
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** Compact JSON for the metadata column. Uses single line, no spaces. */
export function fmtJson(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

export function classNames(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

/** Suppress unused-import warning when only Intl formatters are needed. */
void numFmt;
