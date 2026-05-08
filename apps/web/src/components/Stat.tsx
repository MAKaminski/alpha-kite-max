import type { ReactNode } from "react";
import { classNames } from "@/lib/format";

interface StatProps {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "neutral" | "positive" | "negative";
}

export function Stat({ label, value, hint, tone = "neutral" }: StatProps) {
  return (
    <div className="rounded-md border border-[var(--border)] px-4 py-3">
      <div className="text-xs uppercase tracking-wider text-[var(--muted)]">
        {label}
      </div>
      <div
        className={classNames(
          "mt-1 font-mono text-2xl",
          tone === "positive" && "text-emerald-600 dark:text-emerald-400",
          tone === "negative" && "text-rose-600 dark:text-rose-400",
        )}
      >
        {value}
      </div>
      {hint ? (
        <div className="mt-1 text-xs text-[var(--muted)]">{hint}</div>
      ) : null}
    </div>
  );
}
