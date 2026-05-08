import { Nav } from "@/components/Nav";
import {
  KNOWN_STRATEGIES,
  fetchAvailableSymbols,
  fetchBrokerSnapshot,
  fetchChartBars,
  fetchChartMarkers,
  fetchChartDailyPnl,
  fetchOpenPositions,
  type StrategyId,
} from "@/lib/queries";
import ChartView from "./ChartView";
import PortfolioCard from "./PortfolioCard";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const DEFAULT_SYMBOL = "QQQ";

interface PageProps {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
}

export default async function ChartsPage(props: PageProps) {
  const params = (await props.searchParams) ?? {};
  const sp = (k: string): string | undefined =>
    typeof params[k] === "string" ? (params[k] as string) : undefined;

  const day = new Date().toISOString().slice(0, 10);
  const availableSymbols = await fetchAvailableSymbols();
  const symbolParam = sp("symbol");
  const symbol =
    symbolParam && availableSymbols.includes(symbolParam)
      ? symbolParam
      : (availableSymbols[0] ?? DEFAULT_SYMBOL);

  const strategyParam = sp("strategy");
  const strategy: StrategyId =
    strategyParam && KNOWN_STRATEGIES.some((s) => s.id === strategyParam)
      ? (strategyParam as StrategyId)
      : "sma_vwap_cross";

  const [bars, markers, dailyPnl, brokerSnap, positions] = await Promise.all([
    fetchChartBars(symbol, day),
    fetchChartMarkers(symbol, day),
    fetchChartDailyPnl(30),
    fetchBrokerSnapshot(),
    fetchOpenPositions(),
  ]);

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? null;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? null;

  return (
    <div>
      <Nav current="/charts" />
      <main className="mx-auto max-w-6xl px-4 py-8 space-y-6">
        <PortfolioCard snapshot={brokerSnap} positions={positions} />
        <ChartView
          symbol={symbol}
          availableSymbols={availableSymbols}
          activeStrategy={strategy}
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
