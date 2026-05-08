import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/**
 * Supabase client singleton for the dashboard.
 *
 * If env is unset (typical local dev without a Supabase project), `null` is
 * returned. Callers in `queries.ts` then fall back to fixtures so the UI
 * always renders with content rather than empty states.
 */
let cached: SupabaseClient | null | undefined;

export function getSupabase(): SupabaseClient | null {
  if (cached !== undefined) return cached;

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!url || !anonKey) {
    cached = null;
    return cached;
  }

  cached = createClient(url, anonKey, {
    auth: { persistSession: false },
    db: { schema: "public" },
  });
  return cached;
}

export function isLive(): boolean {
  return getSupabase() !== null;
}
