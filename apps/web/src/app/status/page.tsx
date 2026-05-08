import { fetchSystemStatus } from "@/lib/queries";
import { Nav } from "@/components/Nav";
import LiveStatusTable from "./LiveStatusTable";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function StatusPage() {
  // Server-render the initial state for fast first paint, then hand off to the
  // client component which (a) ticks "X seconds ago" labels every second and
  // (b) subscribes to Supabase Realtime for INSERT events on audit_log /
  // bars / signals / fills so the page updates the moment new rows land.
  const initial = await fetchSystemStatus();

  // Anon key is safe to expose; only allows row-level access already guarded
  // by RLS read policies.
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? null;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? null;

  return (
    <div>
      <Nav current="/status" />
      <main className="mx-auto max-w-5xl px-4 py-8">
        <LiveStatusTable
          initial={initial}
          supabaseUrl={supabaseUrl}
          supabaseAnonKey={supabaseAnonKey}
        />

        <div className="mt-6 rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700">
          <h2 className="mb-2 font-medium text-gray-900">How to read this page</h2>
          <ul className="space-y-1 text-xs">
            <li>
              <span className="font-medium">Healthy</span> — the component reported in within the
              last expected cycle.
            </li>
            <li>
              <span className="font-medium">Stale</span> — last seen recently but past its
              expected cycle. Often just a quiet market.
            </li>
            <li>
              <span className="font-medium">Down</span> — silent for an unusually long time.
              Investigate the Railway service logs.
            </li>
            <li>
              <span className="font-medium">Unknown</span> — no events of this kind have ever been
              recorded yet.
            </li>
          </ul>
          <p className="mt-3 text-xs text-gray-500">
            Timestamps update every second; new events push instantly via the live stream.
          </p>
        </div>
      </main>
    </div>
  );
}
