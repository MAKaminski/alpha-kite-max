import { Nav } from "@/components/Nav";
import {
  fetchBrokerSnapshot,
  fetchChartBars,
  fetchChartMarkers,
  fetchChartDailyPnl,
  fetchOpenPositions,
} from "@/lib/queries";
import ChartView from "./ChartView";
import PortfolioCard from "./PortfolioCard";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const DEFAULT_SYMBOL = "QQQ";

export default async function ChartsPage() {
  const day = new Date().toISOString().slice(0, 10);

  const [bars, markers, dailyPnl, brokerSnap, positions] = await Promise.all([
    fetchChartBars(DEFAULT_SYMBOL, day),
    fetchChartMarkers(DEFAULT_SYMBOL, day),
    fetchChartDailyPnl(30),
    fetchBrokerSnapshot(),
    fetchOpenPositions(),
  ]);

  // Anon key is exposed safely; RLS read policies (migration 0002) gate access.
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? null;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? null;

  return (
    <div>
      <Nav current="/charts" />
      <main className="mx-auto max-w-6xl px-4 py-8 space-y-6">
        <PortfolioCard snapshot={brokerSnap} positions={positions} />
        <ChartView
          symbol={DEFAULT_SYMBOL}
          initialDay={day}
          initialBars={bars}
          initialMarkers={markers}
          dailyPnl={dailyPnl}
          supabaseUrl={supabaseUrl}
          supabaseAnonKey={supabaseAnonKey}
        />
      </main>
    </div>
  );
}
