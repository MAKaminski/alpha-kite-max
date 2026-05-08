"use client";

import { useState } from "react";
import { setDryRunOverride } from "./PromoteAction";

interface ChecklistItem {
  label: string;
  ok: boolean;
  detail: string;
}

interface Props {
  checklist: ChecklistItem[];
  currentDryRun: boolean | null;
  serviceRoleConfigured: boolean;
}

export default function PromoteForm({
  checklist,
  currentDryRun,
  serviceRoleConfigured,
}: Props) {
  const allGreen = checklist.every((c) => c.ok);
  const [pending, setPending] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const submit = async (enableLive: boolean) => {
    setPending(true);
    setErr(null);
    setMsg(null);
    const r = await setDryRunOverride({ enableLive });
    setPending(false);
    if (r.ok) {
      setMsg(
        enableLive
          ? "Live trading enabled. The engine will pick this up on its next heartbeat (~60s)."
          : "Reverted to dry-run. The engine will pick this up on its next heartbeat (~60s).",
      );
    } else {
      setErr(r.error);
    }
  };

  return (
    <div className="space-y-4">
      {!serviceRoleConfigured && (
        <div className="rounded-md border border-yellow-300 bg-yellow-50 px-3 py-2 text-xs text-yellow-800">
          <span className="font-medium">Promote button disabled.</span>{" "}
          Set <code className="font-mono">SUPABASE_SERVICE_ROLE_KEY</code> on
          Vercel so the dashboard can write to{" "}
          <code className="font-mono">runtime_settings</code>.
        </div>
      )}

      <ul className="divide-y divide-[var(--border)] rounded-lg border border-[var(--border)]">
        {checklist.map((c, i) => (
          <li key={i} className="flex items-start gap-3 p-3">
            <span
              className={
                c.ok
                  ? "mt-0.5 inline-flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-emerald-700"
                  : "mt-0.5 inline-flex h-5 w-5 items-center justify-center rounded-full bg-rose-100 text-rose-700"
              }
            >
              {c.ok ? "✓" : "✗"}
            </span>
            <div>
              <div className="text-sm font-medium">{c.label}</div>
              <div className="text-xs text-[var(--muted)]">{c.detail}</div>
            </div>
          </li>
        ))}
      </ul>

      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3">
        <span className="text-sm">
          Current engine state:{" "}
          {currentDryRun === null ? (
            <span className="text-[var(--muted)]">unknown</span>
          ) : currentDryRun ? (
            <span className="font-mono text-emerald-700">dry-run</span>
          ) : (
            <span className="font-mono text-rose-700">LIVE</span>
          )}
        </span>
        <div className="ml-auto flex gap-2">
          <button
            type="button"
            disabled={pending || !serviceRoleConfigured}
            onClick={() => submit(false)}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Revert to dry-run
          </button>
          <button
            type="button"
            disabled={pending || !serviceRoleConfigured || !allGreen}
            onClick={() => submit(true)}
            className="rounded-md bg-rose-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-50"
            title={
              allGreen
                ? "All gates green — promote to live trading"
                : "Resolve all checklist items before promoting"
            }
          >
            {pending ? "Working…" : "Promote to LIVE"}
          </button>
        </div>
      </div>

      {msg && (
        <div className="rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {msg}
        </div>
      )}
      {err && (
        <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800">
          {err}
        </div>
      )}
    </div>
  );
}
