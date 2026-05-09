import type { BrokerSnapshot } from "@/lib/queries";
import type { Position } from "@/types/api";

interface Props {
  snapshot: BrokerSnapshot;
  positions: Position[];
}

function fmtUsd(value: string | null): string {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return value;
  return n.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });
}

function fmtAge(iso: string | null): string {
  if (!iso) return "never";
  const ageSec = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (ageSec < 60) return `${Math.floor(ageSec)}s ago`;
  if (ageSec < 3600) return `${Math.floor(ageSec / 60)} min ago`;
  if (ageSec < 86400) return `${Math.floor(ageSec / 3600)}h ago`;
  return `${Math.floor(ageSec / 86400)}d ago`;
}

export default function PortfolioCard({ snapshot, positions }: Props) {
  const connected = snapshot.connected === true;
  const stale = !!snapshot.lastSeen
    && (Date.now() - new Date(snapshot.lastSeen).getTime()) / 1000 > 300;
  const dotClass = !snapshot.lastSeen
    ? "bg-gray-400"
    : !connected
      ? "bg-red-500"
      : stale
        ? "bg-yellow-500"
        : "bg-emerald-500";
  const stateLabel = !snapshot.lastSeen
    ? "Awaiting first heartbeat"
    : !connected
      ? snapshot.lastError ?? "Disconnected"
      : stale
        ? "Stale"
        : "Connected";

  const openPositions = positions.filter((p) => p.quantity !== 0);
  const unrealizedTotal = openPositions.reduce((acc, p) => {
    const v = Number(p.unrealizedPnl ?? "0");
    return acc + (Number.isFinite(v) ? v : 0);
  }, 0);

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span className={`inline-block h-2 w-2 rounded-full ${dotClass}`} />
            <span className="uppercase tracking-wider">IBKR · {snapshot.brokerMode ?? "paper"}</span>
            {snapshot.dryRun && (
              <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] uppercase text-gray-700">
                dry-run
              </span>
            )}
          </div>
          <h2 className="mt-1 font-mono text-lg text-gray-900">
            {snapshot.accountId ?? "—"}
          </h2>
          <p className="text-xs text-gray-500">
            {stateLabel} · last seen {fmtAge(snapshot.lastSeen)}
          </p>
        </div>

        <div className="grid grid-cols-3 gap-x-6 gap-y-1 text-right">
          <div>
            <div className="text-xs uppercase text-gray-500">NAV</div>
            <div className="font-mono text-base text-gray-900">
              {fmtUsd(snapshot.navUsd)}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase text-gray-500">Cash</div>
            <div className="font-mono text-base text-gray-900">
              {fmtUsd(snapshot.cashUsd)}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase text-gray-500">Buying power</div>
            <div className="font-mono text-base text-gray-900">
              {fmtUsd(snapshot.buyingPowerUsd)}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 border-t border-gray-100 pt-3">
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-gray-600">
          <div>
            <span className="font-medium text-gray-900">{openPositions.length}</span>{" "}
            open position{openPositions.length === 1 ? "" : "s"}
            {openPositions.length > 0 && (
              <span className="ml-3 text-gray-500">
                unrealized{" "}
                <span
                  className={
                    unrealizedTotal >= 0
                      ? "font-mono text-emerald-700"
                      : "font-mono text-red-700"
                  }
                >
                  {fmtUsd(unrealizedTotal.toFixed(2))}
                </span>
              </span>
            )}
          </div>
          <a href="/positions" className="text-xs text-blue-600 hover:underline">
            View positions →
          </a>
        </div>
        {openPositions.length > 0 && (
          <ul className="mt-2 space-y-1 text-xs text-gray-700">
            {openPositions.slice(0, 5).map((p, i) => {
              const label = p.isOption && p.option
                ? `${p.symbol} ${p.option.expiry} ${p.option.strike}${p.option.right}`
                : p.symbol;
              const entered = p.enteredAt
                ? new Date(p.enteredAt).toISOString().slice(0, 16).replace("T", " ") + "Z"
                : null;
              return (
                <li key={`${label}-${i}`} className="flex flex-wrap justify-between gap-1">
                  <span className="font-mono">
                    {label}
                    {p.isFixture && (
                      <span className="ml-2 rounded bg-yellow-100 px-1 py-px text-[10px] uppercase text-yellow-800">
                        demo
                      </span>
                    )}
                  </span>
                  <span className="text-gray-500">
                    qty {p.quantity} · entry {fmtUsd(p.entryPrice ?? p.avgCost)}
                    {entered && <span className="ml-2 text-gray-400">@ {entered}</span>}
                    {p.unrealizedPnl !== null && (
                      <span className={Number(p.unrealizedPnl) >= 0 ? " ml-2 text-emerald-700" : " ml-2 text-red-700"}>
                        ({fmtUsd(p.unrealizedPnl)})
                      </span>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
