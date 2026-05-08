import { Nav } from "@/components/Nav";
import { Table, type Column } from "@/components/Table";
import { Empty } from "@/components/Empty";
import { Stat } from "@/components/Stat";
import { fetchDailyPnl } from "@/lib/queries";
import { fmtDate, fmtInt, fmtUsd } from "@/lib/format";
import type { DailyPnl } from "@/types/api";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function PnlPage() {
  // fetchDailyPnl returns oldest→newest already.
  const rows = await fetchDailyPnl(30);
  const ordered = rows;
  // Newest first for table display.
  const tableRows = [...ordered].reverse();

  const totalRealized = ordered.reduce((s, r) => s + safeNum(r.realizedUsd), 0);
  const totalUnrealized = ordered.reduce(
    (s, r) => s + safeNum(r.unrealizedUsd),
    0,
  );
  const totalTrades = ordered.reduce((s, r) => s + r.trades, 0);
  const totalWins = ordered.reduce((s, r) => s + r.wins, 0);

  const columns: ReadonlyArray<Column<DailyPnl>> = [
    {
      header: "Day",
      cell: (r) => <span className="font-mono">{fmtDate(r.tradingDay)}</span>,
    },
    {
      header: "Realized",
      align: "right",
      cell: (r) => <PnlCell value={r.realizedUsd} />,
    },
    {
      header: "Unrealized",
      align: "right",
      cell: (r) => <PnlCell value={r.unrealizedUsd} />,
    },
    {
      header: "Trades",
      align: "right",
      cell: (r) => fmtInt(r.trades),
    },
    {
      header: "Wins",
      align: "right",
      cell: (r) => fmtInt(r.wins),
    },
    {
      header: "Losses",
      align: "right",
      cell: (r) => fmtInt(r.losses),
    },
  ];

  return (
    <>
      <Nav current="/pnl" />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-xl font-semibold">Daily P&amp;L</h1>
            <p className="text-sm text-[var(--muted)]">
              Trailing 30 trading days.
            </p>
          </div>
          <Sparkline points={ordered.map((r) => safeNum(r.realizedUsd))} />
        </div>

        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat
            label="Σ Realized"
            value={fmtUsd(totalRealized)}
            tone={totalRealized > 0 ? "positive" : totalRealized < 0 ? "negative" : "neutral"}
          />
          <Stat
            label="Σ Unrealized"
            value={fmtUsd(totalUnrealized)}
            tone={
              totalUnrealized > 0
                ? "positive"
                : totalUnrealized < 0
                  ? "negative"
                  : "neutral"
            }
          />
          <Stat label="Σ Trades" value={fmtInt(totalTrades)} />
          <Stat
            label="Win rate"
            value={
              totalTrades > 0
                ? `${((totalWins / totalTrades) * 100).toFixed(1)}%`
                : "—"
            }
          />
        </div>

        {tableRows.length === 0 ? (
          <Empty
            message="No P&L recorded yet."
            hint="Daily P&L rows are written by the engine at end-of-day."
          />
        ) : (
          <Table
            columns={columns}
            rows={tableRows}
            rowKey={(r) => r.tradingDay}
          />
        )}
      </main>
    </>
  );
}

function safeNum(value: string): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function PnlCell({ value }: { value: string }) {
  const n = safeNum(value);
  const cls =
    n > 0
      ? "text-emerald-600 dark:text-emerald-400"
      : n < 0
        ? "text-rose-600 dark:text-rose-400"
        : "";
  return <span className={cls}>{fmtUsd(n)}</span>;
}

/**
 * Inline cumulative-realized sparkline. No external chart library.
 * Renders the running sum so the operator sees equity-curve shape.
 */
function Sparkline({ points }: { points: ReadonlyArray<number> }) {
  if (points.length < 2) return null;

  const cum: number[] = [];
  let acc = 0;
  for (const p of points) {
    acc += p;
    cum.push(acc);
  }

  const min = Math.min(...cum);
  const max = Math.max(...cum);
  const range = max - min || 1;
  const W = 240;
  const H = 56;
  const stepX = points.length > 1 ? W / (points.length - 1) : W;

  const coords = cum.map((y, i) => {
    const x = i * stepX;
    const yy = H - ((y - min) / range) * (H - 4) - 2;
    return [x, yy] as const;
  });

  const d = coords
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`)
    .join(" ");

  const last = cum[cum.length - 1];
  const tone =
    last > 0
      ? "stroke-emerald-500"
      : last < 0
        ? "stroke-rose-500"
        : "stroke-[var(--fg)]";

  return (
    <div className="flex flex-col items-end">
      <div className="text-xs uppercase tracking-wider text-[var(--muted)]">
        Cumulative realized
      </div>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        className="mt-1"
        aria-hidden="true"
      >
        <line
          x1={0}
          x2={W}
          y1={H - ((0 - min) / range) * (H - 4) - 2}
          y2={H - ((0 - min) / range) * (H - 4) - 2}
          className="stroke-[var(--border)]"
          strokeDasharray="2 3"
          strokeWidth={1}
        />
        <path
          d={d}
          fill="none"
          className={tone}
          strokeWidth={1.5}
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
}
