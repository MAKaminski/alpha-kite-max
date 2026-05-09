import { Nav } from "@/components/Nav";
import { Empty } from "@/components/Empty";
import { Stat } from "@/components/Stat";
import { fetchDailyPnl, fetchFillsSince, type FillRecord } from "@/lib/queries";
import { fmtDate, fmtInt, fmtUsd } from "@/lib/format";
import type { DailyPnl } from "@/types/api";
import CumulativePnlChart from "./CumulativePnlChart";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function PnlPage() {
  // fetchDailyPnl returns oldest→newest already.
  const ordered = await fetchDailyPnl(30);
  // Newest first for table display.
  const tableRows = [...ordered].reverse();

  // Pull every fill in the trailing range so we can render a per-day
  // drill-down without a second round-trip per day.
  const sinceDay =
    ordered.length > 0
      ? ordered[0].tradingDay
      : new Date(Date.now() - 30 * 86_400_000).toISOString().slice(0, 10);
  const allFills = await fetchFillsSince(sinceDay);
  const fillsByDay = groupFillsByDay(allFills);

  const totalRealized = ordered.reduce((s, r) => s + safeNum(r.realizedUsd), 0);
  const totalUnrealized = ordered.reduce(
    (s, r) => s + safeNum(r.unrealizedUsd),
    0,
  );
  const totalTrades = ordered.reduce((s, r) => s + r.trades, 0);
  const totalWins = ordered.reduce((s, r) => s + r.wins, 0);

  return (
    <>
      <Nav current="/pnl" />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <div className="mb-6">
          <h1 className="text-xl font-semibold">Daily P&amp;L</h1>
          <p className="text-sm text-[var(--muted)]">
            Trailing 30 trading days · expand a row to see every fill on that day.
          </p>
        </div>

        {ordered.length > 1 && (
          <div className="mb-6 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3 shadow-sm">
            <div className="mb-2 text-xs uppercase tracking-wider text-[var(--muted)]">
              Cumulative realized P&amp;L
            </div>
            <CumulativePnlChart rows={ordered} />
          </div>
        )}

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
          <div className="overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface)]">
            <div className="grid grid-cols-[2fr_repeat(5,1fr)_2rem] border-b border-[var(--border)] bg-[var(--surface-muted)] px-4 py-2 text-[11px] uppercase tracking-wider text-[var(--muted)]">
              <div>Day</div>
              <div className="text-right">Realized</div>
              <div className="text-right">Unrealized</div>
              <div className="text-right">Trades</div>
              <div className="text-right">Wins</div>
              <div className="text-right">Losses</div>
              <div />
            </div>
            <ul>
              {tableRows.map((r) => (
                <PnlDayRow
                  key={r.tradingDay}
                  row={r}
                  fills={fillsByDay.get(r.tradingDay) ?? []}
                />
              ))}
            </ul>
          </div>
        )}
      </main>
    </>
  );
}

function PnlDayRow({ row, fills }: { row: DailyPnl; fills: FillRecord[] }) {
  const realized = safeNum(row.realizedUsd);
  const unrealized = safeNum(row.unrealizedUsd);
  return (
    <li className="border-b border-[var(--border)] last:border-b-0">
      <details className="group">
        <summary className="grid cursor-pointer grid-cols-[2fr_repeat(5,1fr)_2rem] items-center px-4 py-2 text-sm hover:bg-[var(--surface-muted)]">
          <span className="font-mono">{fmtDate(row.tradingDay)}</span>
          <span className="text-right">
            <PnlSpan value={realized} />
          </span>
          <span className="text-right">
            <PnlSpan value={unrealized} />
          </span>
          <span className="text-right">{fmtInt(row.trades)}</span>
          <span className="text-right">{fmtInt(row.wins)}</span>
          <span className="text-right">{fmtInt(row.losses)}</span>
          <span className="text-right text-[var(--muted)] transition-transform group-open:rotate-90">
            ›
          </span>
        </summary>
        <div className="border-t border-[var(--border)] bg-[var(--surface-muted)] px-4 py-3">
          {fills.length === 0 ? (
            <p className="text-xs text-[var(--muted)]">
              No fills recorded for {fmtDate(row.tradingDay)}. Daily roll-up
              counts may include trades that pre-date the fills retention
              window, or this day&apos;s P&amp;L was rolled forward without
              broker fills (e.g. backtested days).
            </p>
          ) : (
            <table className="w-full text-xs">
              <thead className="text-[var(--muted)]">
                <tr className="text-left">
                  <th className="pb-1 font-normal">Time (UTC)</th>
                  <th className="pb-1 font-normal">Symbol</th>
                  <th className="pb-1 font-normal">Side</th>
                  <th className="pb-1 text-right font-normal">Qty</th>
                  <th className="pb-1 text-right font-normal">Price</th>
                </tr>
              </thead>
              <tbody>
                {fills.map((f, i) => (
                  <tr key={i} className="border-t border-[var(--border)]">
                    <td className="py-1 font-mono">
                      {new Date(f.ts).toISOString().slice(11, 19)}
                    </td>
                    <td className="py-1 font-mono">
                      {f.isOption
                        ? `${f.symbol} ${f.optionExpiry ?? ""} ${f.optionStrike ?? ""}${f.optionRight ?? ""}`
                        : f.symbol}
                    </td>
                    <td
                      className={
                        f.side === "BUY"
                          ? "py-1 text-emerald-700 dark:text-emerald-400"
                          : "py-1 text-rose-700 dark:text-rose-400"
                      }
                    >
                      {f.side}
                    </td>
                    <td className="py-1 text-right">{fmtInt(f.quantity)}</td>
                    <td className="py-1 text-right font-mono">{fmtUsd(f.price)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </details>
    </li>
  );
}

function groupFillsByDay(fills: FillRecord[]): Map<string, FillRecord[]> {
  const out = new Map<string, FillRecord[]>();
  for (const f of fills) {
    const day = f.ts.slice(0, 10);
    const list = out.get(day);
    if (list) list.push(f);
    else out.set(day, [f]);
  }
  return out;
}

function safeNum(value: string): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function PnlSpan({ value }: { value: number }) {
  const cls =
    value > 0
      ? "text-emerald-600 dark:text-emerald-400"
      : value < 0
        ? "text-rose-600 dark:text-rose-400"
        : "";
  return <span className={cls}>{fmtUsd(value)}</span>;
}

