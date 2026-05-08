"use server";

/**
 * Server Action that flips ``runtime_settings.dry_run_override`` to either
 * ``{value: false}`` (live trading) or removes the override. The engine's
 * heartbeat picks the new value up within ~60s and emits a DRY_RUN_FLIPPED
 * audit row.
 *
 * Requires SUPABASE_SERVICE_ROLE_KEY on the web app environment — the anon
 * key has read-only RLS so it can't write the table.
 */

import { createClient } from "@supabase/supabase-js";

export async function setDryRunOverride(input: {
  enableLive: boolean;
}): Promise<{ ok: true } | { ok: false; error: string }> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !serviceKey) {
    return {
      ok: false,
      error:
        "SUPABASE_SERVICE_ROLE_KEY is not configured on the web app. Set it (and NEXT_PUBLIC_SUPABASE_URL) in Vercel project settings.",
    };
  }
  const sb = createClient(url, serviceKey, { auth: { persistSession: false } });
  const { error } = await sb
    .from("runtime_settings")
    .upsert(
      {
        key: "dry_run_override",
        value: { value: !input.enableLive },
        updated_by: "dashboard:/live-enable",
      },
      { onConflict: "key" },
    );
  if (error) return { ok: false, error: error.message };

  // Mirror the action into audit_log so the operator has a permanent record.
  await sb.from("audit_log").insert({
    actor: "operator",
    event_type: "LIVE_ENABLE",
    severity: "WARN",
    message: input.enableLive
      ? "live trading promoted from dashboard"
      : "live trading reverted to dry-run from dashboard",
    payload: { dry_run: !input.enableLive },
  });

  return { ok: true };
}
