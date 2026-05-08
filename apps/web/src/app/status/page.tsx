import { fetchSystemStatus, type ComponentHealth, type ComponentStatus } from "@/lib/queries";
import { fmtTime } from "@/lib/format";
import { Nav } from "@/components/Nav";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const HEALTH_LABEL: Record<ComponentHealth, string> = {
  healthy: "Healthy",
  stale: "Stale",
  down: "Down",
  unknown: "Unknown",
};

const HEALTH_COLOR: Record<ComponentHealth, string> = {
  healthy: "bg-green-100 text-green-800 ring-green-300",
  stale: "bg-yellow-100 text-yellow-800 ring-yellow-300",
  down: "bg-red-100 text-red-800 ring-red-300",
  unknown: "bg-gray-100 text-gray-700 ring-gray-300",
};

function lastSeenAgo(iso: string | null): string {
  if (!iso) return "never";
  const ageSec = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (ageSec < 60) return `${Math.floor(ageSec)}s ago`;
  if (ageSec < 3600) return `${Math.floor(ageSec / 60)} min ago`;
  if (ageSec < 86400) return `${Math.floor(ageSec / 3600)}h ago`;
  return `${Math.floor(ageSec / 86400)}d ago`;
}

function StatusBadge({ health }: { health: ComponentHealth }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${HEALTH_COLOR[health]}`}
    >
      <span className="mr-1.5">●</span>
      {HEALTH_LABEL[health]}
    </span>
  );
}

function ComponentRow({ c }: { c: ComponentStatus }) {
  return (
    <tr className="border-b last:border-b-0">
      <td className="px-4 py-3 align-top">
        <div className="font-medium">{c.name}</div>
        <div className="mt-1 text-xs text-gray-600">{c.detail}</div>
      </td>
      <td className="px-4 py-3 align-top whitespace-nowrap">
        <StatusBadge health={c.health} />
      </td>
      <td className="px-4 py-3 align-top whitespace-nowrap">
        <div>{lastSeenAgo(c.lastSeen)}</div>
        {c.lastSeen && (
          <div className="mt-0.5 text-xs text-gray-500">{fmtTime(c.lastSeen)}</div>
        )}
      </td>
      <td className="px-4 py-3 align-top text-sm text-gray-700">{c.cadence}</td>
    </tr>
  );
}

export default async function StatusPage() {
  const status = await fetchSystemStatus();

  const counts = status.components.reduce(
    (acc, c) => ({ ...acc, [c.health]: (acc[c.health] ?? 0) + 1 }),
    {} as Record<ComponentHealth, number>,
  );
  const overall: ComponentHealth =
    counts.down > 0 ? "down" : counts.stale > 0 ? "stale" : counts.unknown > 0 ? "unknown" : "healthy";

  return (
    <div>
      <Nav current="/status" />
      <main className="mx-auto max-w-5xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">System status</h1>
            <p className="mt-1 text-sm text-gray-600">
              What is running, when it was last seen, and how often it is supposed to run.
            </p>
          </div>
          <div>
            <StatusBadge health={overall} />
          </div>
        </div>

        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wider text-gray-700">
              <tr>
                <th className="px-4 py-3">Component</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Last seen</th>
                <th className="px-4 py-3">Expected cadence</th>
              </tr>
            </thead>
            <tbody>
              {status.components.map((c) => (
                <ComponentRow key={c.name} c={c} />
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-6 rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700">
          <h2 className="mb-2 font-medium text-gray-900">How to read this page</h2>
          <ul className="space-y-1 text-xs">
            <li>
              <span className="font-medium">Healthy</span> — the component reported in within the
              last expected cycle.
            </li>
            <li>
              <span className="font-medium">Stale</span> — last seen recently but past its expected
              cycle. Often just a quiet market.
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
            Generated at {fmtTime(status.generatedAt)}. Refresh the page for an update.
          </p>
        </div>
      </main>
    </div>
  );
}
