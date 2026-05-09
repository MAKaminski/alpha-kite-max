import { Nav } from "@/components/Nav";
import { Empty } from "@/components/Empty";
import {
  fetchOrderIntents,
  type OrderIntentRecord,
  type OrderStatus,
} from "@/lib/queries";
import { fmtUsd } from "@/lib/format";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const STATUS_COLORS: Record<OrderStatus, string> = {
  filled: "bg-emerald-100 text-emerald-800 ring-emerald-300",
  placed: "bg-blue-100 text-blue-800 ring-blue-300",
  blocked: "bg-rose-100 text-rose-800 ring-rose-300",
  "dry-run": "bg-gray-100 text-gray-700 ring-gray-300",
  queued: "bg-yellow-100 text-yellow-800 ring-yellow-300",
};

export default async function OrdersPage() {
  const orders = await fetchOrderIntents(50);

  return (
    <div>
      <Nav current="/orders" />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <h1 className="mb-1 text-xl font-semibold">Order intents</h1>
        <p className="mb-4 text-sm text-[var(--muted)]">
          Every intent the strategy emitted, joined to the broker fills (if
          any) and the RISK_BLOCK audit rows that referenced it. Click a row
          to see fills and any block reasons.
        </p>

        {orders.length === 0 ? (
          <Empty
            message="No order intents recorded yet."
            hint="Intents land here the moment the strategy emits one — even before risk decides to block or place it."
          />
        ) : (
          <div className="overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface)]">
            <ul>
              {orders.map((o) => (
                <OrderRow key={o.intentId} order={o} />
              ))}
            </ul>
          </div>
        )}
      </main>
    </div>
  );
}

function OrderRow({ order }: { order: OrderIntentRecord }) {
  const contract =
    order.isOption && order.optionStrike && order.optionRight
      ? `${order.symbol} ${order.optionExpiry ?? ""} ${order.optionStrike}${order.optionRight}`
      : order.symbol;
  return (
    <li className="border-b border-[var(--border)] last:border-b-0">
      <details className="group">
        <summary className="grid cursor-pointer grid-cols-[1.4fr_2fr_0.5fr_0.5fr_0.7fr_0.7fr_2rem] items-center gap-3 px-4 py-2 text-sm hover:bg-[var(--surface-muted)]">
          <span className="font-mono text-xs">
            {new Date(order.createdAt).toISOString().slice(0, 19).replace("T", " ")}Z
          </span>
          <span className="font-mono">{contract}</span>
          <span
            className={
              order.side === "BUY"
                ? "text-emerald-700 dark:text-emerald-400"
                : "text-rose-700 dark:text-rose-400"
            }
          >
            {order.side}
          </span>
          <span className="text-right">{order.quantity}</span>
          <span className="text-right font-mono">
            {order.limitPrice ? fmtUsd(order.limitPrice) : order.orderType}
          </span>
          <span>
            <span
              className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium uppercase ring-1 ring-inset ${STATUS_COLORS[order.status]}`}
            >
              {order.status}
            </span>
          </span>
          <span className="text-right text-[var(--muted)] transition-transform group-open:rotate-90">
            ›
          </span>
        </summary>
        <div className="border-t border-[var(--border)] bg-[var(--surface-muted)] px-4 py-3 text-xs">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <div className="mb-1 uppercase tracking-wider text-[var(--muted)]">
                Intent
              </div>
              <ul className="space-y-0.5">
                <li>
                  <span className="text-[var(--muted)]">id</span>{" "}
                  <span className="font-mono">{order.intentId}</span>
                </li>
                <li>
                  <span className="text-[var(--muted)]">tag</span>{" "}
                  <span className="font-mono">{order.tag || "—"}</span>
                </li>
                <li>
                  <span className="text-[var(--muted)]">order type</span>{" "}
                  <span className="font-mono">{order.orderType}</span>
                </li>
                <li>
                  <span className="text-[var(--muted)]">dry-run</span>{" "}
                  <span className="font-mono">{order.dryRun ? "yes" : "no"}</span>
                </li>
                {order.brokerOrderId && (
                  <li>
                    <span className="text-[var(--muted)]">broker order id</span>{" "}
                    <span className="font-mono">{order.brokerOrderId}</span>
                  </li>
                )}
              </ul>
            </div>
            <div>
              {order.fills.length > 0 && (
                <>
                  <div className="mb-1 uppercase tracking-wider text-[var(--muted)]">
                    Fills
                  </div>
                  <ul className="space-y-0.5">
                    {order.fills.map((f, i) => (
                      <li key={i}>
                        <span className="font-mono">
                          {new Date(f.ts).toISOString().slice(11, 19)}
                        </span>{" "}
                        · qty {f.quantity} @ {fmtUsd(f.price)}
                      </li>
                    ))}
                  </ul>
                </>
              )}
              {order.blockReasons.length > 0 && (
                <>
                  <div className="mb-1 mt-2 uppercase tracking-wider text-[var(--muted)]">
                    Block reasons
                  </div>
                  <ul className="space-y-0.5 text-rose-700 dark:text-rose-400">
                    {order.blockReasons.map((r, i) => (
                      <li key={i}>· {r}</li>
                    ))}
                  </ul>
                </>
              )}
              {order.fills.length === 0 && order.blockReasons.length === 0 && (
                <p className="text-[var(--muted)]">
                  No fills or block events recorded for this intent.
                </p>
              )}
            </div>
          </div>
        </div>
      </details>
    </li>
  );
}
