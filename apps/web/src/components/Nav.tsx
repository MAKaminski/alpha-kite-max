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
 * env. Returns null when nothing is configured (local dev).
 */
function activeAccount(): { account: string; mode: string } | null {
  const account =
    process.env.NEXT_PUBLIC_IBKR_ACCOUNT ??
    process.env.NEXT_PUBLIC_BROKER_ACCOUNT ??
    null;
  if (!account) return null;
  const mode = process.env.NEXT_PUBLIC_BROKER_MODE ?? "paper";
  return { account, mode };
}

export function Nav({ current }: NavProps) {
  const acct = activeAccount();
  return (
    <header className="border-b border-[var(--border)]">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-4">
        <Link
          href="/"
          className="text-sm font-semibold tracking-wider uppercase"
        >
          alpha-kite
        </Link>
        <nav className="flex flex-wrap items-center gap-6 text-sm">
          {acct && (
            <span
              className="font-mono text-xs text-gray-500"
              title={`Active broker account · ${acct.mode}`}
            >
              {acct.account}
            </span>
          )}
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
