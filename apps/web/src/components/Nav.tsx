import Link from "next/link";
import { classNames } from "@/lib/format";

interface NavProps {
  current: string;
}

const LINKS: ReadonlyArray<{ href: string; label: string }> = [
  { href: "/status", label: "Status" },
  { href: "/charts", label: "Charts" },
  { href: "/signals", label: "Signals" },
  { href: "/positions", label: "Positions" },
  { href: "/pnl", label: "P&L" },
  { href: "/audit", label: "Audit" },
];

/**
 * Resolve the active broker account label. Designed to scale to multiple
 * accounts later — for now we surface a single IBKR paper account from
 * env. Falls back to "—" when nothing is configured (e.g. local dev).
 */
function activeAccount(): { broker: string; account: string; mode: string } {
  const account =
    process.env.NEXT_PUBLIC_IBKR_ACCOUNT ??
    process.env.NEXT_PUBLIC_BROKER_ACCOUNT ??
    "—";
  const mode = process.env.NEXT_PUBLIC_BROKER_MODE ?? "paper";
  return { broker: "IBKR", account, mode };
}

export function Nav({ current }: NavProps) {
  const { broker, account, mode } = activeAccount();
  const modeColor =
    mode === "live"
      ? "bg-red-100 text-red-700"
      : "bg-emerald-100 text-emerald-700";

  return (
    <header className="border-b border-[var(--border)]">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-4">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="text-sm font-semibold tracking-wider uppercase"
          >
            alpha-kite
          </Link>
          <span
            className="hidden items-center gap-2 rounded-md border border-[var(--border)] px-2 py-0.5 text-xs sm:inline-flex"
            title="Active broker account (configure via NEXT_PUBLIC_IBKR_ACCOUNT)"
          >
            <span className="text-[var(--muted)]">{broker}</span>
            <span className="font-mono text-[var(--fg)]">{account}</span>
            <span className={classNames("rounded px-1.5 py-0.5 text-[10px] font-medium uppercase", modeColor)}>
              {mode}
            </span>
          </span>
        </div>
        <nav className="flex flex-wrap gap-6 text-sm">
          {LINKS.map((link) => {
            const isActive = current === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                aria-current={isActive ? "page" : undefined}
                className={classNames(
                  "border-b-2 pb-1 transition-colors",
                  isActive
                    ? "border-[var(--accent)] text-[var(--fg)]"
                    : "border-transparent text-[var(--muted)] hover:text-[var(--fg)]",
                )}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
