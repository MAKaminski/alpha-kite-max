"use client";

import { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";
import type { RecentBar } from "@/lib/queries";

interface Props {
  initial: RecentBar[];
  supabaseUrl: string | null;
  supabaseAnonKey: string | null;
}

/**
 * Live feed diagnostic. Shows whether the bars table is actually getting
 * populated by the engine in real time. Subscribes to ``bars`` INSERTs via
 * Realtime (migration 0003 already exposes this table) and computes:
 *
 *  - bars/min arrival rate over the trailing 60 s
 *  - last 5 bars (symbol, time, close, volume)
 *  - age of the most recent bar
 *
 * If the engine + market_data_stream are wired correctly to IBKR/yfinance,
 * this panel should tick every minute during RTH. Outside RTH it stays
 * quiet and the rate falls to 0 within a minute.
 */
export default function LiveFeedPanel({
  initial,
  supabaseUrl,
  supabaseAnonKey,
}: Props) {
  const [bars, setBars] = useState<RecentBar[]>(initial);
  const [now, setNow] = useState<number>(Date.now());
  const [streamLive, setStreamLive] = useState(false);

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    if (!supabaseUrl || !supabaseAnonKey) return;
    const client = createClient(supabaseUrl, supabaseAnonKey, {
      realtime: { params: { eventsPerSecond: 10 } },
    });
    const channel = client
      .channel("status-live-feed")
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "bars" },
        (payload) => {
          const r = payload.new as {
            symbol: string;
            open_time: string;
            close: string | number;
            volume: number;
          };
          setBars((prev) =>
            [
              {
                symbol: r.symbol,
                openTime: r.open_time,
                close: typeof r.close === "string" ? Number(r.close) : r.close,
                volume: r.volume,
              },
              ...prev,
            ].slice(0, 50),   // keep ring buffer modest
          );
        },
      )
      .subscribe((status) => {
        setStreamLive(status === "SUBSCRIBED");
      });

    return () => {
      void client.removeChannel(channel);
    };
  }, [supabaseUrl, supabaseAnonKey]);

  // Bars/min over the trailing 60 s — based on bars whose open_time is
  // within the last minute of `now`.
  const oneMinuteAgo = now - 60_000;
  const recentRate = bars.filter(
    (b) => new Date(b.openTime).getTime() >= oneMinuteAgo,
  ).length;

  const newest = bars[0];
  const newestAgeSec = newest
    ? Math.max(0, Math.floor((now - new Date(newest.openTime).getTime()) / 1000))
    : null;
  const ageBadgeClass =
    newestAgeSec === null
      ? "bg-gray-100 text-gray-700 ring-gray-300"
      : newestAgeSec <= 90
        ? "bg-emerald-100 text-emerald-700 ring-emerald-300"
        : newestAgeSec <= 600
          ? "bg-yellow-100 text-yellow-800 ring-yellow-300"
          : "bg-red-100 text-red-700 ring-red-300";

  const fmtVol = (n: number): string => {
    if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
    if (n >= 1e3) return `${(n / 1e3).toFixed(1)}k`;
    return String(n);
  };

  const last5 = bars.slice(0, 5);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-700">
            Live feed
          </h2>
          <p className="text-xs text-gray-500">
            Real-time view of bars persisting into Supabase. Confirms the
            IBKR/yfinance stream is flowing without touching the gateway.
          </p>
        </div>
        <span
          className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${
            streamLive
              ? "bg-green-50 text-green-700 ring-green-200"
              : "bg-gray-100 text-gray-600 ring-gray-300"
          }`}
        >
          <span className={`mr-1 ${streamLive ? "animate-pulse" : ""}`}>●</span>
          {streamLive ? "subscribed" : "polling"}
        </span>
      </div>

      <div className="mb-3 flex flex-wrap gap-3 text-xs">
        <span className="inline-flex items-center gap-2">
          <span className="text-gray-500">arrival rate</span>
          <span className="font-mono text-gray-900">{recentRate}/min</span>
        </span>
        <span
          className={`inline-flex items-center gap-2 rounded px-2 py-0.5 ring-1 ring-inset ${ageBadgeClass}`}
        >
          <span>last bar</span>
          <span className="font-mono">
            {newestAgeSec === null
              ? "never"
              : newestAgeSec < 60
                ? `${newestAgeSec}s ago`
                : `${Math.floor(newestAgeSec / 60)}m ${newestAgeSec % 60}s ago`}
          </span>
        </span>
      </div>

      {last5.length === 0 ? (
        <p className="text-xs text-gray-500">
          No bars have landed yet. Outside regular trading hours this is
          expected — bars start arriving at 09:30 ET on the next session.
        </p>
      ) : (
        <table className="w-full text-xs">
          <thead className="text-gray-500">
            <tr className="text-left">
              <th className="pb-1 font-normal">Time (UTC)</th>
              <th className="pb-1 font-normal">Symbol</th>
              <th className="pb-1 text-right font-normal">Close</th>
              <th className="pb-1 text-right font-normal">Volume</th>
            </tr>
          </thead>
          <tbody>
            {last5.map((b, i) => (
              <tr key={`${b.symbol}-${b.openTime}-${i}`} className="border-t border-gray-100">
                <td className="py-1 font-mono">
                  {new Date(b.openTime).toISOString().slice(11, 19)}
                </td>
                <td className="py-1 font-mono">{b.symbol}</td>
                <td className="py-1 text-right font-mono">
                  {b.close.toFixed(2)}
                </td>
                <td className="py-1 text-right font-mono text-gray-600">
                  {fmtVol(b.volume)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
