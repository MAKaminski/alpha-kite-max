import Link from "next/link";
import { classNames } from "@/lib/format";

interface NavProps {
  current: string;
}

const LINKS: ReadonlyArray<{ href: string; label: string }> = [
  { href: "/status", label: "Status" },
  { href: "/signals", label: "Signals" },
  { href: "/positions", label: "Positions" },
  { href: "/pnl", label: "P&L" },
  { href: "/audit", label: "Audit" },
];

export function Nav({ current }: NavProps) {
  return (
    <header className="border-b border-[var(--border)]">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link
          href="/"
          className="text-sm font-semibold tracking-wider uppercase"
        >
          alpha-kite
        </Link>
        <nav className="flex gap-6 text-sm">
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
