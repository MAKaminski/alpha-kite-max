"use client";

import { useMemo, useState } from "react";
import {
  runBacktest,
  type BacktestInput,
  type BacktestResult,
  type BacktestSummary,
  type SymbolEntry,
} from "./RunBacktestAction";

interface Props {
  fixtures: string[];
  symbols: SymbolEntry[];
  apiConfigured: boolean;
}

type Source = "fixture" | "supabase";

export default function BacktestForm({ fixtures, symbols, apiConfigured }: Props) {
  const defaultSource: Source = symbols.length > 0 ? "supabase" : "fixture";
  const [source, setSource] = useState<Source>(defaultSource);
  const [fixture, setFixture] = useState(fixtures[0] ?? "");
  const [symbolKey, setSymbolKey] = useState(
    symbols.length > 0 ? `${symbols[0].symbol}|${symbols[0].interval_seconds}` : "",
  );
  const selectedSymbol = useMemo(
    () => symbols.find((s) => `${s.symbol}|${s.interval_seconds}` === symbolKey),
    [symbols, symbolKey],
  );
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [splitDate, setSplitDate] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Default the date range to the symbol's full coverage when one is picked.
  useMemo(() => {
    if (selectedSymbol) {
      if (!start) setStart(selectedSymbol.first_bar.slice(0, 16));
      if (!end) setEnd(selectedSymbol.last_bar.slice(0, 16));
    }
  }, [selectedSymbol, start, end]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setRunning(true);
    setError(null);
    setResult(null);

    let input: BacktestInput;
    if (source === "fixture") {
      if (!fixture) {
        setError("Pick a fixture first.");
        setRunning(false);
        return;
      }
      input = { source: "fixture", fixture, splitDate: splitDate || undefined };
    } else {
      if (!selectedSymbol || !start || !end) {
        setError("Pick a symbol and start/end timestamps.");
        setRunning(false);
        return;
      }
      input = {
        source: "supabase",
        symbol: selectedSymbol.symbol,
        start: new Date(start).toISOString(),
        end: new Date(end).toISOString(),
        intervalSeconds: selectedSymbol.interval_seconds,
        splitDate: splitDate || undefined,
      };
    }

    const res = await runBacktest(input);
    if (res.ok) setResult(res.data);
    else setError(res.error);
    setRunning(false);
  };

  return (
    <div className="space-y-6">
      {!apiConfigured && (
        <div className="rounded-md border border-yellow-300 bg-yellow-50 px-3 py-2 text-xs text-yellow-800">
          <span className="font-medium">Sidecar not configured.</span>{" "}
          Set <code className="font-mono">BACKTEST_API_URL</code> on Vercel to
          point at your Railway-deployed services/backtest-api/ instance.
        </div>
      )}

      <form
        onSubmit={onSubmit}
        className="flex flex-wrap items-end gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm"
      >
        <label className="flex flex-col gap-1 text-xs text-[var(--muted)]">
          Source
          <select
            value={source}
            onChange={(e) => setSource(e.target.value as Source)}
            className="rounded-md border border-gray-300 px-2 py-1 text-sm"
          >
            <option value="supabase" disabled={symbols.length === 0}>
              Supabase bars {symbols.length === 0 ? "(no rows yet)" : ""}
            </option>
            <option value="fixture" disabled={fixtures.length === 0}>
              Fixture file
            </option>
          </select>
        </label>

        {source === "fixture" ? (
          <label className="flex flex-col gap-1 text-xs text-[var(--muted)]">
            Fixture
            <select
              value={fixture}
              onChange={(e) => setFixture(e.target.value)}
              disabled={fixtures.length === 0}
              className="rounded-md border border-gray-300 px-2 py-1 text-sm font-mono"
            >
              {fixtures.length === 0 ? (
                <option value="">(none available)</option>
              ) : (
                fixtures.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))
              )}
            </select>
          </label>
        ) : (
          <>
            <label className="flex flex-col gap-1 text-xs text-[var(--muted)]">
              Symbol · interval
              <select
                value={symbolKey}
                onChange={(e) => {
                  setSymbolKey(e.target.value);
                  // Reset range so the new symbol's coverage gets picked up.
                  setStart("");
                  setEnd("");
                }}
                disabled={symbols.length === 0}
                className="rounded-md border border-gray-300 px-2 py-1 text-sm font-mono"
              >
                {symbols.length === 0 ? (
                  <option value="">(no bars in DB — run scripts/backfill_bars.py)</option>
                ) : (
                  symbols.map((s) => {
                    const k = `${s.symbol}|${s.interval_seconds}`;
                    const lbl =
                      s.interval_seconds === 60 ? "1m" :
                      s.interval_seconds === 300 ? "5m" :
                      s.interval_seconds === 3600 ? "1h" :
                      s.interval_seconds === 86400 ? "1d" :
                      `${s.interval_seconds}s`;
                    return (
                      <option key={k} value={k}>
                        {s.symbol} {lbl} ({s.n_bars} bars)
                      </option>
                    );
                  })
                )}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-[var(--muted)]">
              Start
              <input
                type="datetime-local"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                className="rounded-md border border-gray-300 px-2 py-1 text-sm font-mono"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-[var(--muted)]">
              End
              <input
                type="datetime-local"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                className="rounded-md border border-gray-300 px-2 py-1 text-sm font-mono"
              />
            </label>
          </>
        )}

        <label className="flex flex-col gap-1 text-xs text-[var(--muted)]">
          Split date (optional, ISO)
          <input
            type="text"
            placeholder="2026-04-15T15:00Z"
            value={splitDate}
            onChange={(e) => setSplitDate(e.target.value)}
            className="rounded-md border border-gray-300 px-2 py-1 text-sm font-mono"
          />
        </label>
        <button
          type="submit"
          disabled={running || !apiConfigured}
          className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {running ? "Running…" : "Run backtest"}
        </button>
      </form>

      {error && (
        <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </div>
      )}

      {result && <ResultPanel result={result} />}
    </div>
  );
}

function ResultPanel({ result }: { result: BacktestResult }) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wider text-[var(--muted)]">
          Summary
        </h2>
        {result.split ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <SummaryCard title="In-sample" summary={result.split.in_sample} accent="emerald" />
            <SummaryCard title="Out-of-sample" summary={result.split.out_of_sample} accent="blue" />
            <SummaryCard title="All trades" summary={result.split.all} accent="gray" />
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <SummaryCard title="All trades" summary={result.summary} accent="blue" />
          </div>
        )}
      </div>

      {result.trades.length > 0 && (
        <div>
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wider text-[var(--muted)]">
            Trades ({result.trades.length})
          </h2>
          <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
            <table className="w-full text-xs">
              <thead className="bg-[var(--surface-muted)] text-[var(--muted)]">
                <tr className="text-left">
                  <th className="px-2 py-1 font-normal">Entry</th>
                  <th className="px-2 py-1 font-normal">Exit</th>
                  <th className="px-2 py-1 font-normal">Right</th>
                  <th className="px-2 py-1 font-normal">Strike</th>
                  <th className="px-2 py-1 text-right font-normal">Entry $</th>
                  <th className="px-2 py-1 text-right font-normal">Exit $</th>
                  <th className="px-2 py-1 text-right font-normal">P&L %</th>
                  <th className="px-2 py-1 font-normal">Reason</th>
                </tr>
              </thead>
              <tbody>
                {result.trades.map((t, i) => (
                  <tr key={t.intent_id || i} className="border-t border-[var(--border)]">
                    <td className="px-2 py-1 font-mono">
                      {t.entry_ts.slice(0, 19).replace("T", " ")}
                    </td>
                    <td className="px-2 py-1 font-mono">
                      {t.exit_ts ? t.exit_ts.slice(0, 19).replace("T", " ") : "—"}
                    </td>
                    <td className="px-2 py-1">{t.right}</td>
                    <td className="px-2 py-1 font-mono">{t.strike}</td>
                    <td className="px-2 py-1 text-right font-mono">{t.entry_price}</td>
                    <td className="px-2 py-1 text-right font-mono">{t.exit_price ?? "—"}</td>
                    <td
                      className={`px-2 py-1 text-right font-mono ${
                        t.pnl_pct === null
                          ? ""
                          : Number(t.pnl_pct) >= 0
                            ? "text-emerald-700"
                            : "text-rose-700"
                      }`}
                    >
                      {t.pnl_pct ?? "—"}
                    </td>
                    <td className="px-2 py-1 text-[var(--muted)]">{t.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryCard({
  title,
  summary,
  accent,
}: {
  title: string;
  summary: BacktestSummary;
  accent: "emerald" | "blue" | "gray";
}) {
  const ring =
    accent === "emerald"
      ? "border-emerald-200 bg-emerald-50"
      : accent === "blue"
        ? "border-blue-200 bg-blue-50"
        : "border-gray-200 bg-gray-50";
  const sign = (n: number) => (n >= 0 ? "text-emerald-700" : "text-rose-700");
  return (
    <div className={`rounded-lg border ${ring} p-4`}>
      <div className="text-xs uppercase tracking-wider text-gray-600">{title}</div>
      <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <span className="text-gray-500">Trades</span>
        <span className="text-right font-mono">{summary.trades}</span>
        <span className="text-gray-500">Win rate</span>
        <span className="text-right font-mono">{summary.win_rate_pct}%</span>
        <span className="text-gray-500">Expectancy</span>
        <span className={`text-right font-mono ${sign(summary.expectancy_pct)}`}>
          {summary.expectancy_pct}%
        </span>
        <span className="text-gray-500">Total P&L</span>
        <span className={`text-right font-mono ${sign(summary.total_pnl_pct)}`}>
          {summary.total_pnl_pct}%
        </span>
        <span className="text-gray-500">Avg win</span>
        <span className="text-right font-mono">{summary.avg_win_pct}%</span>
        <span className="text-gray-500">Avg loss</span>
        <span className="text-right font-mono">{summary.avg_loss_pct}%</span>
      </div>
    </div>
  );
}
