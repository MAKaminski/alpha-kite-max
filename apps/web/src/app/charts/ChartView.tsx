"use client";

import { useEffect, useState, useTransition } from "react";
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

export default function ChartView({
  symbol,
  initialDay,
  initialBars,
  initialMarkers,
  dailyPnl,
  supabaseUrl,
  supabaseAnonKey,
}: Props) {
  const [day, setDay] = useState(initialDay);
  const [bars, setBars] = useState<ChartBar[]>(initialBars);
  const [markers, setMarkers] = useState<ChartMarker[]>(initialMarkers);
  const [isPending, startTransition] = useTransition();

  // Re-fetch the day's bars + markers from the browser whenever the user picks
  // a different date. Keeps the page snappy without a full server round-trip.
  useEffect(() => {
    if (!supabaseUrl || !supabaseAnonKey) return;
    if (day === initialDay) return;
    const supabase = createClient(supabaseUrl, supabaseAnonKey, {
      auth: { persistSession: false },
    });
    const dayStart = `${day}T00:00:00Z`;
    const dayEnd = `${day}T23:59:59Z`;
    let cancelled = false;

    startTransition(async () => {
      const [barsRes, signalsRes, fillsRes] = await Promise.all([
        supabase
          .from("bars")
          .select("symbol,open_time,open,high,low,close,volume,vwap")
          .eq("symbol", symbol)
          .gte("open_time", dayStart)
          .lte("open_time", dayEnd)
          .order("open_time", { ascending: true }),
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
    });

    return () => {
      cancelled = true;
    };
  }, [day, initialDay, symbol, supabaseUrl, supabaseAnonKey]);

  const todayStr = new Date().toISOString().slice(0, 10);
  const barCount = bars.length;
  const signalCount = markers.filter(
    (m) => m.kind === "signal_up" || m.kind === "signal_down",
  ).length;
  const fillCount = markers.filter(
    (m) => m.kind === "buy_fill" || m.kind === "sell_fill",
  ).length;

  return (
    <div className="space-y-8">
      <section>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              {symbol} — intraday
            </h1>
            <p className="text-sm text-gray-600">
              1-minute bars with SMA(9), session VWAP, and signal/fill markers.
            </p>
          </div>
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
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
          {isPending ? (
            <div className="flex h-[480px] items-center justify-center text-sm text-gray-500">
              Loading bars for {day}…
            </div>
          ) : barCount === 0 ? (
            <div className="flex h-[480px] flex-col items-center justify-center gap-1 text-sm text-gray-500">
              <p>No bars persisted for {symbol} on {day}.</p>
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
