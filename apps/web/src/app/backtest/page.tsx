import { Nav } from "@/components/Nav";
import BacktestForm from "./BacktestForm";
import { listFixtures } from "./RunBacktestAction";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function BacktestPage() {
  const apiConfigured = !!process.env.BACKTEST_API_URL;
  const fixtures = apiConfigured ? await listFixtures() : [];

  return (
    <div>
      <Nav current="/backtest" />
      <main className="mx-auto max-w-6xl px-6 py-8 space-y-4">
        <div>
          <h1 className="text-xl font-semibold">Backtest</h1>
          <p className="text-sm text-[var(--muted)]">
            Replay a fixture through the configured strategy and see the
            resulting trade ledger + summary stats. Optionally split the
            trade history by date to compare in-sample vs. out-of-sample
            performance.
          </p>
        </div>
        <BacktestForm fixtures={fixtures} apiConfigured={apiConfigured} />
      </main>
    </div>
  );
}
