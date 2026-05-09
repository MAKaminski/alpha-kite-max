import { Nav } from "@/components/Nav";
import BacktestForm from "./BacktestForm";
import { listFixtures, listSupabaseSymbols } from "./RunBacktestAction";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function BacktestPage() {
  const apiConfigured = !!process.env.BACKTEST_API_URL;
  const [fixtures, symbols] = apiConfigured
    ? await Promise.all([listFixtures(), listSupabaseSymbols()])
    : [[], []];

  return (
    <div>
      <Nav current="/backtest" />
      <main className="mx-auto max-w-6xl px-6 py-8 space-y-4">
        <div>
          <h1 className="text-xl font-semibold">Backtest</h1>
          <p className="text-sm text-[var(--muted)]">
            Replay either a fixture or backfilled bars from Supabase through
            the configured strategy. The Supabase mode uses whatever
            <code className="mx-1 font-mono">scripts/backfill_bars.py</code>
            has populated. Optionally split the trade history by date to
            compare in-sample vs. out-of-sample performance.
          </p>
        </div>
        <BacktestForm
          fixtures={fixtures}
          symbols={symbols}
          apiConfigured={apiConfigured}
        />
      </main>
    </div>
  );
}
