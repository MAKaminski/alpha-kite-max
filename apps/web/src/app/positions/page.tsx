import { Nav } from "@/components/Nav";
import { Table, type Column } from "@/components/Table";
import { Empty } from "@/components/Empty";
import { Stat } from "@/components/Stat";
import { fetchOpenPositions } from "@/lib/queries";
import { fmtDate, fmtInt, fmtTime, fmtUsd, fmtUsdPrecise } from "@/lib/format";
import type { Position } from "@/types/api";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function PositionsPage() {
  const positions = await fetchOpenPositions();

  const totalMarketValue = positions.reduce((acc, p) => {
    const v = p.marketValue ? Number(p.marketValue) : 0;
    return acc + (Number.isFinite(v) ? v : 0);
  }, 0);
  const totalUnrealized = positions.reduce((acc, p) => {
    const v = p.unrealizedPnl ? Number(p.unrealizedPnl) : 0;
    return acc + (Number.isFinite(v) ? v : 0);
  }, 0);

  const columns: ReadonlyArray<Column<Position>> = [
    {
      header: "Symbol",
      cell: (p) => <span className="font-mono">{p.symbol}</span>,
    },
    {
      header: "Type",
      cell: (p) => (p.isOption ? "Option" : "Equity"),
    },
    {
      header: "Expiry",
      cell: (p) => (p.option ? fmtDate(p.option.expiry) : "—"),
    },
    {
      header: "Strike",
      align: "right",
      cell: (p) => (p.option ? fmtUsdPrecise(p.option.strike) : "—"),
    },
    {
      header: "Right",
      align: "center",
      cell: (p) => (p.option ? p.option.right : "—"),
    },
    {
      header: "Qty",
      align: "right",
      cell: (p) => fmtInt(p.quantity),
    },
    {
      header: "Entry price",
      align: "right",
      cell: (p) => (p.entryPrice ? fmtUsdPrecise(p.entryPrice) : fmtUsdPrecise(p.avgCost)),
    },
    {
      header: "Avg cost",
      align: "right",
      cell: (p) => fmtUsdPrecise(p.avgCost),
    },
    {
      header: "Entered",
      align: "right",
      cell: (p) =>
        p.enteredAt ? (
          <span className="font-mono text-xs">{fmtTime(p.enteredAt)}</span>
        ) : (
          <span className="text-[var(--muted)]">—</span>
        ),
    },
    {
      header: "Mkt Value",
      align: "right",
      cell: (p) => fmtUsd(p.marketValue),
    },
    {
      header: "Unrealized P&L",
      align: "right",
      cell: (p) => <PnlCell value={p.unrealizedPnl} />,
    },
  ];

  const allFixture = positions.length > 0 && positions.every((p) => p.isFixture);

  const unrealizedTone =
    totalUnrealized > 0 ? "positive" : totalUnrealized < 0 ? "negative" : "neutral";

  return (
    <>
      <Nav current="/positions" />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <h1 className="mb-4 text-xl font-semibold">Positions</h1>
        {allFixture && (
          <div className="mb-4 rounded-md border border-yellow-300 bg-yellow-50 px-3 py-2 text-xs text-yellow-800">
            <span className="font-medium">Demo data.</span>{" "}
            Supabase env vars (NEXT_PUBLIC_SUPABASE_URL +
            NEXT_PUBLIC_SUPABASE_ANON_KEY) aren&apos;t configured for this page,
            so these rows are local fixtures — not real holdings.
          </div>
        )}
        <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Stat label="Open positions" value={fmtInt(positions.length)} />
          <Stat label="Total market value" value={fmtUsd(totalMarketValue)} />
          <Stat
            label="Total unrealized P&L"
            value={fmtUsd(totalUnrealized)}
            tone={unrealizedTone}
          />
        </div>
        {positions.length === 0 ? (
          <Empty
            message="No open positions."
            hint="Positions appear here once the broker reports nonzero quantities."
          />
        ) : (
          <Table
            columns={columns}
            rows={positions}
            rowKey={(p, i) =>
              p.option
                ? `${p.symbol}-${p.option.expiry}-${p.option.strike}-${p.option.right}`
                : `${p.symbol}-eq-${i}`
            }
          />
        )}
      </main>
    </>
  );
}

function PnlCell({ value }: { value: string | null }) {
  if (value === null) return <>—</>;
  const n = Number(value);
  if (!Number.isFinite(n)) return <>—</>;
  const cls =
    n > 0
      ? "text-emerald-600 dark:text-emerald-400"
      : n < 0
        ? "text-rose-600 dark:text-rose-400"
        : "";
  return <span className={cls}>{fmtUsd(n)}</span>;
}
