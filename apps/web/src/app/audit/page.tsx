import Link from "next/link";
import { Nav } from "@/components/Nav";
import { Table, type Column } from "@/components/Table";
import { Empty } from "@/components/Empty";
import { fetchAuditLog } from "@/lib/queries";
import { fmtJson, fmtTime, classNames } from "@/lib/format";
import type { AuditEvent, AuditSeverity } from "@/types/api";

export const dynamic = "force-dynamic";
export const revalidate = 0;

interface AuditPageProps {
  searchParams?: Promise<{ severity?: string }>;
}

const SEVERITIES: ReadonlyArray<AuditSeverity> = ["INFO", "WARN", "ERROR"];

export default async function AuditPage({ searchParams }: AuditPageProps) {
  const params = (await searchParams) ?? {};
  const filterRaw = params.severity?.toUpperCase();
  const filter: AuditSeverity | undefined =
    filterRaw === "INFO" || filterRaw === "WARN" || filterRaw === "ERROR"
      ? filterRaw
      : undefined;

  const events = await fetchAuditLog(200, filter);

  const columns: ReadonlyArray<Column<AuditEvent>> = [
    {
      header: "Time",
      cell: (e) => <span className="font-mono">{fmtTime(e.ts)}</span>,
    },
    {
      header: "Severity",
      cell: (e) => <SeverityPill severity={e.severity} />,
    },
    {
      header: "Actor",
      cell: (e) => e.actor,
    },
    {
      header: "Event",
      cell: (e) => <span className="font-mono">{e.eventType}</span>,
    },
    {
      header: "Message",
      cell: (e) => e.message,
    },
    {
      header: "Payload",
      cell: (e) => (
        <code className="block max-w-md truncate font-mono text-xs text-[var(--muted)]">
          {fmtJson(e.payload)}
        </code>
      ),
    },
  ];

  return (
    <>
      <Nav current="/audit" />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <h1 className="mb-4 text-xl font-semibold">Audit log</h1>
        <p className="mb-4 text-sm text-[var(--muted)]">
          Last {events.length} entr{events.length === 1 ? "y" : "ies"}
          {filter ? ` (filtered to ${filter})` : ""}.
        </p>

        <div className="mb-6 flex flex-wrap items-center gap-2">
          <span className="text-xs uppercase tracking-wider text-[var(--muted)]">
            Severity
          </span>
          <FilterPill href="/audit" label="All" active={!filter} />
          {SEVERITIES.map((s) => (
            <FilterPill
              key={s}
              href={`/audit?severity=${s}`}
              label={s}
              active={filter === s}
              tone={s}
            />
          ))}
        </div>

        {events.length === 0 ? (
          <Empty
            message={
              filter
                ? `No ${filter} events recorded.`
                : "No audit events recorded yet."
            }
            hint="The engine writes here for every safety-critical decision."
          />
        ) : (
          <Table columns={columns} rows={events} rowKey={(e) => e.id} />
        )}
      </main>
    </>
  );
}

function FilterPill({
  href,
  label,
  active,
  tone,
}: {
  href: string;
  label: string;
  active: boolean;
  tone?: AuditSeverity;
}) {
  return (
    <Link
      href={href}
      className={classNames(
        "rounded-full border px-3 py-1 text-xs font-mono transition-colors",
        active
          ? "border-[var(--accent)] bg-[var(--accent)] text-[var(--bg)]"
          : "border-[var(--border)] text-[var(--muted)] hover:text-[var(--fg)]",
        tone && !active ? severityBorder(tone) : "",
      )}
    >
      {label}
    </Link>
  );
}

function severityBorder(s: AuditSeverity): string {
  if (s === "INFO") return "border-sky-500/40";
  if (s === "WARN") return "border-amber-500/40";
  return "border-rose-500/40";
}

function SeverityPill({ severity }: { severity: AuditSeverity }) {
  const tone =
    severity === "INFO"
      ? "border-sky-500/40 text-sky-700 dark:text-sky-300"
      : severity === "WARN"
        ? "border-amber-500/40 text-amber-700 dark:text-amber-300"
        : "border-rose-500/40 text-rose-700 dark:text-rose-300";
  return (
    <span
      className={classNames(
        "inline-flex rounded-full border px-2 py-0.5 text-xs font-mono",
        tone,
      )}
    >
      {severity}
    </span>
  );
}
