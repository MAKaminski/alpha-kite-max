import { Nav } from "@/components/Nav";
import { Table, type Column } from "@/components/Table";
import { Empty } from "@/components/Empty";
import { fetchSignals } from "@/lib/queries";
import { fmtJson, fmtNumber, fmtTime } from "@/lib/format";
import type { Signal } from "@/types/api";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function SignalsPage() {
  const signals = await fetchSignals(100);

  const columns: ReadonlyArray<Column<Signal>> = [
    {
      header: "Time",
      cell: (s) => <span className="font-mono">{fmtTime(s.timestamp)}</span>,
    },
    {
      header: "Strategy",
      cell: (s) => s.name,
    },
    {
      header: "Symbol",
      cell: (s) => <span className="font-mono">{s.symbol}</span>,
    },
    {
      header: "Direction",
      cell: (s) => <DirectionPill direction={s.direction} />,
    },
    {
      header: "Strength",
      align: "right",
      cell: (s) => fmtNumber(s.strength, 4),
    },
    {
      header: "Metadata",
      cell: (s) => (
        <code className="block max-w-md truncate font-mono text-xs text-[var(--muted)]">
          {fmtJson(s.metadata)}
        </code>
      ),
    },
  ];

  return (
    <>
      <Nav current="/signals" />
      <main className="mx-auto max-w-6xl px-6 py-8">
        <h1 className="mb-4 text-xl font-semibold">Signals</h1>
        <p className="mb-6 text-sm text-[var(--muted)]">
          Last {signals.length} strategy signal{signals.length === 1 ? "" : "s"}.
        </p>
        {signals.length === 0 ? (
          <Empty
            message="No signals yet — engine has not emitted any."
            hint="When the engine emits a signal it will appear here within a few seconds."
          />
        ) : (
          <Table
            columns={columns}
            rows={signals}
            rowKey={(s, i) => `${s.timestamp}-${s.symbol}-${i}`}
          />
        )}
      </main>
    </>
  );
}

function DirectionPill({ direction }: { direction: Signal["direction"] }) {
  const tone =
    direction === "LONG_VOL_UP"
      ? "border-emerald-500/40 text-emerald-700 dark:text-emerald-300"
      : direction === "LONG_VOL_DOWN"
        ? "border-sky-500/40 text-sky-700 dark:text-sky-300"
        : direction === "EXIT"
          ? "border-rose-500/40 text-rose-700 dark:text-rose-300"
          : "border-[var(--border)] text-[var(--muted)]";
  return (
    <span
      className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-mono ${tone}`}
    >
      {direction}
    </span>
  );
}
