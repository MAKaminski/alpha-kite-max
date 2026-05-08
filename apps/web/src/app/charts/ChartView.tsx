"use client";

import { useEffect, useRef, useState } from "react";
import { createClient } from "@supabase/supabase-js";
import type { ChartBar, ChartMarker, DayPnl } from "@/lib/queries";
import PriceChart from "./PriceChart";
import DailyPnlChart from "./DailyPnlChart";

interface Props {
  symbol: string;
  initialDay: string;
  initialBars: ChartBar[];
  initialMarkers: ChartMarker[];
  dailyPnl: DayPnl[];
  supabaseUrl: string | null;
  supabaseAnonKey: string | null;
}

const NUM = (v: string | number | null | undefined): number =>
  v === null || v === undefined ? 0 : typeof v === "number" ? v : Number(v);

type Mode = "day" | "range";

export default function ChartView({
  symbol,
  initialDay,
  initialBars,
  initialMarkers,
  dailyPnl,
  supabaseUrl,
  supabaseAnonKey,
}: Props) {
  const [mode, setMode] = useState<Mode>("day");
  const [day, setDay] = useState(initialDay);
  const [fromDay, setFromDay] = useState(initialDay);
  const [toDay, setToDay] = useState(initialDay);
  const [bars, setBars] = useState<ChartBar[]>(initialBars);
  const [markers, setMarkers] = useState<ChartMarker[]>(initialMarkers);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isFirstRender = useRef(true);

  // Re-fetch whenever the user touches the date inputs or mode. We skip
  // the very first effect run so the server-rendered initial bars stay
  // visible without a redundant client round-trip.
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    if (!supabaseUrl || !supabaseAnonKey) return;

    const startDay = mode === "day" ? day : fromDay;
    const endDay = mode === "day" ? day : toDay;
    if (startDay > endDay) {
      setError("'From' date must be on or before 'To' date.");
      return;
    }
    setError(null);

    const supabase = createClient(supabaseUrl, supabaseAnonKey, {
      auth: { persistSession: false },
    });
    const startIso = `${startDay}T00:00:00Z`;
    const endIso = `${endDay}T23:59:59Z`;
    let cancelled = false;
    setLoading(true);

    (async () => {
      const [barsRes, signalsRes, fillsRes] = await Promise.all([
        supabase
          .from("bars")
          .select("symbol,open_time,open,high,low,close,volume,vwap")
          .eq("symbol", symbol)
          .gte("open_time", startIso)
          .lte("open_time", endIso)
          .order("open_time", { ascending: true }),
        supabase
          .from("signals")
          .select("ts,direction,symbol,metadata")
          .eq("symbol", symbol)
          .gte("ts", startIso)
          .lte("ts", endIso)
          .order("ts", { ascending: true }),
        supabase
          .from("fills")
          .select("ts,symbol,side,price,is_option,option_strike,option_right")
          .eq("symbol", symbol)
          .gte("ts", startIso)
          .lte("ts", endIso)
          .order("ts", { ascending: true }),
      ]);
      if (cancelled) return;

      const newBars: ChartBar[] = (barsRes.data ?? []).map((r) => ({
        time: Math.floor(new Date(r.open_time).getTime() / 1000),
        open: NUM(r.open),
        high: NUM(r.high),
        low: NUM(r.low),
        close: NUM(r.close),
        volume: r.volume,
        vwap: r.vwap === null ? null : NUM(r.vwap),
      }));

      const newMarkers: ChartMarker[] = [];
      for (const r of signalsRes.data ?? []) {
        if (r.direction === "LONG_VOL_UP" || r.direction === "LONG_VOL_DOWN") {
          newMarkers.push({
            time: Math.floor(new Date(r.ts).getTime() / 1000),
            kind: r.direction === "LONG_VOL_UP" ? "signal_up" : "signal_down",
            label: r.direction === "LONG_VOL_UP" ? "▲ UP" : "▼ DN",
            price: null,
          });
        }
      }
      for (const r of fillsRes.data ?? []) {
        newMarkers.push({
          time: Math.floor(new Date(r.ts).getTime() / 1000),
          kind: r.side === "BUY" ? "buy_fill" : "sell_fill",
          label: `${r.side} ${r.is_option ? `${r.option_strike}${r.option_right ?? ""}` : ""}`.trim(),
          price: NUM(r.price),
        });
      }
      newMarkers.sort((a, b) => a.time - b.time);

      setBars(newBars);
      setMarkers(newMarkers);
      setLoading(false);
    })().catch((err: unknown) => {
      if (cancelled) return;
      setError(err instanceof Error ? err.message : "fetch failed");
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [mode, day, fromDay, toDay, symbol, supabaseUrl, supabaseAnonKey]);

  const todayStr = new Date().toISOString().slice(0, 10);
  const barCount = bars.length;
  const signalCount = markers.filter(
    (m) => m.kind === "signal_up" || m.kind === "signal_down",
  ).length;
  const fillCount = markers.filter(
    (m) => m.kind === "buy_fill" || m.kind === "sell_fill",
  ).length;
  const dayCount =
    mode === "day"
      ? 1
      : Math.max(
          1,
          Math.round((Date.parse(toDay) - Date.parse(fromDay)) / 86_400_000) + 1,
        );

  const headerLabel =
    mode === "day"
      ? day
      : fromDay === toDay
        ? fromDay
        : `${fromDay} → ${toDay} (${dayCount} days)`;

  return (
    <div className="space-y-8">
      <section>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              {symbol} — {mode === "day" ? "intraday" : "history"}
            </h1>
            <p className="text-sm text-gray-600">
              1-minute bars with SMA(9), session VWAP, volume, and signal/fill
              markers · <span className="font-medium">{headerLabel}</span>
            </p>
          </div>

          <div className="flex flex-wrap items-end gap-3">
            <div className="flex rounded-md border border-gray-300 text-xs">
              <button
                type="button"
                onClick={() => setMode("day")}
                aria-pressed={mode === "day"}
                className={`px-3 py-1 ${mode === "day" ? "bg-gray-900 text-white" : "text-gray-700 hover:bg-gray-100"}`}
              >
                Single day
              </button>
              <button
                type="button"
                onClick={() => setMode("range")}
                aria-pressed={mode === "range"}
                className={`px-3 py-1 ${mode === "range" ? "bg-gray-900 text-white" : "text-gray-700 hover:bg-gray-100"}`}
              >
                Range
              </button>
            </div>

            {mode === "day" ? (
              <label className="flex flex-col gap-1 text-xs text-gray-600">
                Trading day (UTC)
                <input
                  type="date"
                  value={day}
                  max={todayStr}
                  onChange={(e) => setDay(e.target.value)}
                  className="rounded-md border border-gray-300 px-2 py-1 text-sm text-gray-900"
                />
              </label>
            ) : (
              <>
                <label className="flex flex-col gap-1 text-xs text-gray-600">
                  From
                  <input
                    type="date"
                    value={fromDay}
                    max={todayStr}
                    onChange={(e) => setFromDay(e.target.value)}
                    className="rounded-md border border-gray-300 px-2 py-1 text-sm text-gray-900"
                  />
                </label>
                <label className="flex flex-col gap-1 text-xs text-gray-600">
                  To
                  <input
                    type="date"
                    value={toDay}
                    max={todayStr}
                    onChange={(e) => setToDay(e.target.value)}
                    className="rounded-md border border-gray-300 px-2 py-1 text-sm text-gray-900"
                  />
                </label>
              </>
            )}
          </div>
        </div>

        {error && (
          <div className="mb-3 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-700">
            {error}
          </div>
        )}

        <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
          {loading ? (
            <div className="flex h-[480px] items-center justify-center text-sm text-gray-500">
              Loading bars for {headerLabel}…
            </div>
          ) : barCount === 0 ? (
            <div className="flex h-[480px] flex-col items-center justify-center gap-1 text-sm text-gray-500">
              <p>No bars persisted for {symbol} on {headerLabel}.</p>
              <p className="text-xs">
                Bars only land during regular trading hours (09:30–16:00 ET).
              </p>
            </div>
          ) : (
            <PriceChart bars={bars} markers={markers} />
          )}
        </div>

        <div className="mt-2 flex flex-wrap gap-4 text-xs text-gray-600">
          <span>
            <span className="font-medium text-gray-900">{barCount}</span> bars
          </span>
          <span>
            <span className="font-medium text-gray-900">{signalCount}</span> signals
          </span>
          <span>
            <span className="font-medium text-gray-900">{fillCount}</span> fills
          </span>
          <span className="text-gray-500">
            trade window: 09:40–15:30 ET (10 min after open · 30 min before close)
          </span>
        </div>
      </section>

      <section>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Daily P&amp;L — last 30 days
          </h2>
          <p className="text-sm text-gray-600">
            Per-day realized $ and the running cumulative line.
          </p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
          {dailyPnl.length === 0 ? (
            <div className="flex h-[280px] items-center justify-center text-sm text-gray-500">
              No daily P&amp;L rows yet.
            </div>
          ) : (
            <DailyPnlChart rows={dailyPnl} />
          )}
        </div>
      </section>
    </div>
  );
}
