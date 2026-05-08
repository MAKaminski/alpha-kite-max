import { Nav } from "@/components/Nav";
import {
  fetchKillSwitchState,
  fetchOpenPositions,
  fetchRiskBlocks,
  fetchTodayRealizedUsd,
} from "@/lib/queries";
import { fmtUsd } from "@/lib/format";

export const dynamic = "force-dynamic";
export const revalidate = 0;

// Defaults mirror config/strategy.yaml. The dashboard surfaces them as
// stubs until the engine starts persisting its actual config (Stream E).
const DEFAULT_DAILY_LOSS_LIMIT_USD = 50;
const DEFAULT_MAX_OPEN_POSITIONS = 1;

export default async function RiskPage() {
  const [killSwitch, todayRealized, openPositions, blocks] = await Promise.all([
    fetchKillSwitchState(),
    fetchTodayRealizedUsd(),
    fetchOpenPositions(),
    fetchRiskBlocks(20),
  ]);

  const lossHeadroom = DEFAULT_DAILY_LOSS_LIMIT_USD + Math.min(todayRealized, 0);
  const lossPctUsed =
    todayRealized < 0
      ? Math.min(100, Math.abs(todayRealized) / DEFAULT_DAILY_LOSS_LIMIT_USD * 100)
      : 0;
  const positionPctUsed = Math.min(
    100,
    (openPositions.length / DEFAULT_MAX_OPEN_POSITIONS) * 100,
  );

  return (
    <div>
      <Nav current="/risk" />
      <main className="mx-auto max-w-5xl px-6 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-semibold">Risk gauges</h1>
          <p className="text-sm text-[var(--muted)]">
            Live view of the safety rails. The engine&apos;s risk pipeline blocks
            order intents whenever any of these gauges trip.
          </p>
        </div>

        <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Gauge
            label="Kill switch"
            value={killSwitch.active ? "ENGAGED" : "Disengaged"}
            sub={
              killSwitch.lastSeen
                ? `last event ${new Date(killSwitch.lastSeen).toISOString().slice(0, 19).replace("T", " ")} UTC`
                : "no events on record"
            }
            tone={killSwitch.active ? "danger" : "ok"}
          />
          <Gauge
            label="Daily loss headroom"
            value={fmtUsd(lossHeadroom)}
            sub={`limit ${fmtUsd(DEFAULT_DAILY_LOSS_LIMIT_USD)} · used ${lossPctUsed.toFixed(0)}%`}
            tone={lossPctUsed >= 90 ? "danger" : lossPctUsed >= 50 ? "warn" : "ok"}
            barPct={lossPctUsed}
          />
          <Gauge
            label="Open positions"
            value={`${openPositions.length} / ${DEFAULT_MAX_OPEN_POSITIONS}`}
            sub={`max_open_positions=${DEFAULT_MAX_OPEN_POSITIONS}`}
            tone={positionPctUsed >= 100 ? "warn" : "ok"}
            barPct={positionPctUsed}
          />
        </section>

        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-[var(--muted)]">
            Recent RISK_BLOCK events
          </h2>
          {blocks.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">
              No intents have been blocked recently.
            </p>
          ) : (
            <ul className="divide-y divide-[var(--border)] rounded-lg border border-[var(--border)] bg-[var(--surface)]">
              {blocks.map((b, i) => (
                <li key={`${b.ts}-${i}`} className="px-4 py-2 text-sm">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <span className="font-mono text-xs text-[var(--muted)]">
                      {new Date(b.ts).toISOString().slice(0, 19).replace("T", " ")}Z
                    </span>
                    {b.intentId && (
                      <span className="font-mono text-[10px] text-[var(--muted)]">
                        intent {b.intentId.slice(0, 8)}…
                      </span>
                    )}
                  </div>
                  <ul className="mt-1 space-y-0.5 text-xs text-rose-700 dark:text-rose-400">
                    {b.reasons.length === 0 ? (
                      <li>(no reasons recorded)</li>
                    ) : (
                      b.reasons.map((r, j) => <li key={j}>· {r}</li>)
                    )}
                  </ul>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}

interface GaugeProps {
  label: string;
  value: string;
  sub: string;
  tone: "ok" | "warn" | "danger";
  barPct?: number;
}

function Gauge({ label, value, sub, tone, barPct }: GaugeProps) {
  const ring =
    tone === "danger"
      ? "border-red-300 bg-red-50 text-red-900 dark:bg-red-950"
      : tone === "warn"
        ? "border-yellow-300 bg-yellow-50 text-yellow-900 dark:bg-yellow-950"
        : "border-emerald-200 bg-emerald-50 text-emerald-900 dark:bg-emerald-950";
  const bar =
    tone === "danger" ? "bg-red-500" : tone === "warn" ? "bg-yellow-500" : "bg-emerald-500";
  return (
    <div className={`rounded-lg border ${ring} p-4`}>
      <div className="text-xs uppercase tracking-wider opacity-75">{label}</div>
      <div className="mt-1 font-mono text-xl">{value}</div>
      <div className="mt-1 text-[11px] opacity-75">{sub}</div>
      {typeof barPct === "number" && (
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-black/10">
          <div
            className={`h-full ${bar}`}
            style={{ width: `${Math.max(0, Math.min(100, barPct))}%` }}
          />
        </div>
      )}
    </div>
  );
}
