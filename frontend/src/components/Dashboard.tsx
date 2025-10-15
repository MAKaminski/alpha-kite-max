'use client';

import { useState, useEffect } from 'react';
import { supabase, isSupabaseConfigured } from '@/lib/supabase';
import { ChartDataPoint } from '../../../shared/types';
import EquityChart from './EquityChart';

export default function Dashboard() {
  const [ticker, setTicker] = useState('QQQ');
  const [data, setData] = useState<ChartDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Fetch equity data and indicators
      const { data: equityData, error: equityError } = await supabase
        .from('equity_data')
        .select('*')
        .eq('ticker', ticker)
        .order('timestamp', { ascending: true })
        .limit(390); // ~1 trading day of minute data

      if (equityError) throw equityError;

      const { data: indicatorData, error: indicatorError } = await supabase
        .from('indicators')
        .select('*')
        .eq('ticker', ticker)
        .order('timestamp', { ascending: true })
        .limit(390);

      if (indicatorError) throw indicatorError;

      // Merge data
      const mergedData: ChartDataPoint[] = (equityData || []).map((eq) => {
        const indicator = (indicatorData || []).find((ind) => ind.timestamp === eq.timestamp);
        return {
          timestamp: eq.timestamp,
          price: eq.price,
          volume: eq.volume,
          sma9: indicator?.sma9 || 0,
          vwap: indicator?.vwap || 0,
        };
      });

      setData(mergedData);
    } catch (err) {
      const error = err as Error;
      setError(error.message || 'Failed to fetch data');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isSupabaseConfigured()) {
      setError('Supabase not configured. Please add NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY to .env.local');
      setLoading(false);
      return;
    }
    fetchData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6 mb-6">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Trading Dashboard
            </h1>
            <div className="flex items-center gap-4">
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Equity:
              </label>
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter ticker"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
              <div className="text-sm font-medium text-blue-600 dark:text-blue-400">Ticker</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">{ticker}</div>
            </div>
            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
              <div className="text-sm font-medium text-green-600 dark:text-green-400">SMA9</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {data.length > 0 ? `$${data[data.length - 1].sma9.toFixed(2)}` : '-'}
              </div>
            </div>
            <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
              <div className="text-sm font-medium text-purple-600 dark:text-purple-400">Session VWAP</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {data.length > 0 ? `$${data[data.length - 1].vwap.toFixed(2)}` : '-'}
              </div>
            </div>
          </div>

          <div className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            Moving Period: <span className="font-medium">Minutes</span>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6">
          {loading && (
            <div className="flex items-center justify-center h-96">
              <div className="text-lg text-gray-600 dark:text-gray-400">Loading chart data...</div>
            </div>
          )}

          {error && (
            <div className="flex items-center justify-center h-96">
              <div className="text-lg text-red-600 dark:text-red-400">
                Error: {error}
                <p className="text-sm mt-2">Please configure Supabase credentials in .env.local</p>
              </div>
            </div>
          )}

          {!loading && !error && data.length > 0 && (
            <EquityChart data={data} ticker={ticker} />
          )}

          {!loading && !error && data.length === 0 && (
            <div className="flex items-center justify-center h-96">
              <div className="text-lg text-gray-600 dark:text-gray-400">
                No data available for {ticker}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

