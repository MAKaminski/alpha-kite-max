"use client";

import { useEffect, useState } from "react";
import { createClient } from "@supabase/supabase-js";
import type { ComponentStatus, SystemStatus } from "@/lib/queries";
import { fmtTime } from "@/lib/format";

type Health = ComponentStatus["health"];

const HEALTH_LABEL: Record<Health, string> = {
  healthy: "Healthy",
  stale: "Stale",
  down: "Down",
  unknown: "Unknown",
};

const HEALTH_COLOR: Record<Health, string> = {
  healthy: "bg-green-100 text-green-800 ring-green-300",
  stale: "bg-yellow-100 text-yellow-800 ring-yellow-300",
  down: "bg-red-100 text-red-800 ring-red-300",
  unknown: "bg-gray-100 text-gray-700 ring-gray-300",
};

function lastSeenAgo(iso: string | null, now: number): string {
  if (!iso) return "never";
  const ageSec = Math.max(0, (now - new Date(iso).getTime()) / 1000);
  if (ageSec < 1) return "just now";
  if (ageSec < 60) return `${Math.floor(ageSec)}s ago`;
  if (ageSec < 3600) return `${Math.floor(ageSec / 60)} min ago`;
  if (ageSec < 86400) return `${Math.floor(ageSec / 3600)}h ago`;
  return `${Math.floor(ageSec / 86400)}d ago`;
}

function classifyAge(iso: string | null, healthyWithinSec: number, staleWithinSec: number,
                    now: number): Health {
  if (!iso) return "unknown";
  const ageSec = (now - new Date(iso).getTime()) / 1000;
  if (ageSec <= healthyWithinSec) return "healthy";
  if (ageSec <= staleWithinSec) return "stale";
  return "down";
}

function StatusBadge({ health }: { health: Health }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${HEALTH_COLOR[health]}`}
    >
      <span className="mr-1.5">●</span>
      {HEALTH_LABEL[health]}
    </span>
  );
}

interface LiveProps {
  initial: SystemStatus;
  supabaseUrl: string | null;
  supabaseAnonKey: string | null;
}

/**
 * Re-classifies stale/healthy on every tick using the SAME freshness rules
 * as the server query. Keeps the badges accurate as time passes (e.g. a
 * "Healthy 30s ago" row flips to "Stale 121s ago" without a page reload).
 */
function freshen(components: ComponentStatus[], now: number): ComponentStatus[] {
  return components.map((c) => {
    if (c.name === "Strategy engine" || c.name === "Market-data stream") {
      return { ...c, health: classifyAge(c.lastSeen, 120, 600, now) };
    }
    if (c.name === "Bars persisted") {
      return { ...c, health: classifyAge(c.lastSeen, 120, 86_400, now) };
    }
    if (c.name === "Latest signal" || c.name === "Latest fill") {
      return {
        ...c,
        health: c.lastSeen ? classifyAge(c.lastSeen, 3600, 86_400, now) : "unknown",
      };
    }
    return c;
  });
}

export default function LiveStatusTable({ initial, supabaseUrl, supabaseAnonKey }: LiveProps) {
  const [components, setComponents] = useState<ComponentStatus[]>(initial.components);
  const [now, setNow] = useState<number>(Date.now());
  const [streamLive, setStreamLive] = useState<boolean>(false);

  // Tick every second so "Xs ago" displays advance smoothly
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  // Subscribe to Supabase Realtime — push updates the moment new rows land
  useEffect(() => {
    if (!supabaseUrl || !supabaseAnonKey) return;
    const client = createClient(supabaseUrl, supabaseAnonKey, {
      realtime: { params: { eventsPerSecond: 10 } },
    });

    const updateRow = (name: string, ts: string) =>
      setComponents((prev) =>
        prev.map((c) => (c.name === name ? { ...c, lastSeen: ts } : c)),
      );

    const channel = client
      .channel("status-live")
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "audit_log" },
        (payload) => {
          const row = payload.new as { actor: string; ts: string; event_type: string };
          if (row.actor === "engine") updateRow("Strategy engine", row.ts);
          if (row.actor === "market_data_stream") updateRow("Market-data stream", row.ts);
        },
      )
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "bars" },
        (payload) => {
          const row = payload.new as { open_time: string };
          updateRow("Bars persisted", row.open_time);
        },
      )
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "signals" },
        (payload) => {
          const row = payload.new as { ts: string };
          updateRow("Latest signal", row.ts);
        },
      )
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "fills" },
        (payload) => {
          const row = payload.new as { ts: string };
          updateRow("Latest fill", row.ts);
        },
      )
      .subscribe((status) => {
        setStreamLive(status === "SUBSCRIBED");
      });

    return () => {
      void client.removeChannel(channel);
    };
  }, [supabaseUrl, supabaseAnonKey]);

  const liveComponents = freshen(components, now);
  const counts = liveComponents.reduce<Record<Health, number>>(
    (acc, c) => ({ ...acc, [c.health]: (acc[c.health] ?? 0) + 1 }),
    {} as Record<Health, number>,
  );
  const overall: Health =
    counts.down > 0
      ? "down"
      : counts.stale > 0
        ? "stale"
        : counts.unknown > 0
          ? "unknown"
          : "healthy";

  return (
    <>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">System status</h1>
          <p className="mt-1 text-sm text-gray-600">
            What is running, when it was last seen, and how often it is supposed to run.
            <span
              className={`ml-2 inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ring-1 ring-inset ${
                streamLive
                  ? "bg-green-50 text-green-700 ring-green-200"
                  : "bg-gray-100 text-gray-600 ring-gray-300"
              }`}
              title={streamLive ? "Receiving Supabase Realtime updates" : "Polling — no realtime stream"}
            >
              <span className={`mr-1 ${streamLive ? "animate-pulse" : ""}`}>●</span>
              {streamLive ? "live" : "offline"}
            </span>
          </p>
        </div>
        <StatusBadge health={overall} />
      </div>

      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wider text-gray-700">
            <tr>
              <th className="px-4 py-3">Component</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Last seen</th>
              <th className="px-4 py-3">Expected cadence</th>
            </tr>
          </thead>
          <tbody>
            {liveComponents.map((c) => (
              <tr key={c.name} className="border-b last:border-b-0">
                <td className="px-4 py-3 align-top">
                  <div className="font-medium">{c.name}</div>
                  <div className="mt-1 text-xs text-gray-600">{c.detail}</div>
                </td>
                <td className="px-4 py-3 align-top whitespace-nowrap">
                  <StatusBadge health={c.health} />
                </td>
                <td className="px-4 py-3 align-top whitespace-nowrap">
                  <div className="font-mono tabular-nums">{lastSeenAgo(c.lastSeen, now)}</div>
                  {c.lastSeen && (
                    <div className="mt-0.5 text-xs text-gray-500">{fmtTime(c.lastSeen)}</div>
                  )}
                </td>
                <td className="px-4 py-3 align-top text-sm text-gray-700">{c.cadence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
