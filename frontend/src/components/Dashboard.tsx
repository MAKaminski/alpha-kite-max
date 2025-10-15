'use client';

import { useState, useEffect } from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { supabase, isSupabaseConfigured } from '@/lib/supabase';
import { ChartDataPoint } from '../../../shared/types';
import { detectCrosses, filterCrossesByDate, Cross } from '@/lib/crossDetection';
import { formatToEST } from '@/lib/timezone';
import EquityChart from './EquityChart';
import ESTClock from './ESTClock';
import SignalsDashboard from './SignalsDashboard';

export default function Dashboard() {
  const [ticker, setTicker] = useState('QQQ');
  const [allData, setAllData] = useState<ChartDataPoint[]>([]);
  const [displayData, setDisplayData] = useState<ChartDataPoint[]>([]);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [todayCrosses, setTodayCrosses] = useState<Cross[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);

    if (!isSupabaseConfigured()) {
      setError('Supabase not configured. Please add NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY to .env.local');
      setLoading(false);
      return;
    }

    try {
      // Fetch all available equity data (paginate if needed for large datasets)
      let allEquityData: Array<Record<string, unknown>> = [];
      let allIndicatorData: Array<Record<string, unknown>> = [];
      let page = 0;
      const pageSize = 1000;
      
      // Fetch equity data in pages
      while (true) {
        const { data: equityData, error: equityError } = await supabase
          .from('equity_data')
          .select('*')
          .eq('ticker', ticker)
          .order('timestamp', { ascending: true })
          .range(page * pageSize, (page + 1) * pageSize - 1);

        if (equityError) throw equityError;
        if (!equityData || equityData.length === 0) break;
        
        allEquityData = [...allEquityData, ...equityData];
        if (equityData.length < pageSize) break;
        page++;
      }
      
      // Fetch indicator data in pages
      page = 0;
      while (true) {
        const { data: indicatorData, error: indicatorError } = await supabase
          .from('indicators')
          .select('*')
          .eq('ticker', ticker)
          .order('timestamp', { ascending: true })
          .range(page * pageSize, (page + 1) * pageSize - 1);

        if (indicatorError) throw indicatorError;
        if (!indicatorData || indicatorData.length === 0) break;
        
        allIndicatorData = [...allIndicatorData, ...indicatorData];
        if (indicatorData.length < pageSize) break;
        page++;
      }

      const equityData = allEquityData;
      const indicatorData = allIndicatorData;

      // Merge data
      const mergedData: ChartDataPoint[] = (equityData || []).map((eq) => {
        const indicator = (indicatorData || []).find((ind) => ind.timestamp === eq.timestamp);
        return {
          timestamp: eq.timestamp as string,
          price: eq.price as number,
          volume: eq.volume as number,
          sma9: (indicator?.sma9 as number) || 0,
          vwap: (indicator?.vwap as number) || 0,
        };
      });

      setAllData(mergedData);
      
      // Set selected date to most recent data
      if (mergedData.length > 0) {
        const latestDate = new Date(mergedData[mergedData.length - 1].timestamp);
        setSelectedDate(latestDate);
      }
    } catch (err) {
      const error = err as Error;
      setError(error.message || 'Failed to fetch data');
      console.error('Error fetching data:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchLatestData = async () => {
    if (!isSupabaseConfigured()) return;

    try {
      // Fetch only the latest few records
      const { data: equityData } = await supabase
        .from('equity_data')
        .select('*')
        .eq('ticker', ticker)
        .order('timestamp', { ascending: false })
        .limit(10);

      const { data: indicatorData } = await supabase
        .from('indicators')
        .select('*')
        .eq('ticker', ticker)
        .order('timestamp', { ascending: false })
        .limit(10);

      if (equityData && equityData.length > 0) {
        const newPoints: ChartDataPoint[] = equityData.map((eq) => {
          const indicator = (indicatorData || []).find((ind) => ind.timestamp === eq.timestamp);
          return {
            timestamp: eq.timestamp,
            price: eq.price,
            volume: eq.volume,
            sma9: indicator?.sma9 || 0,
            vwap: indicator?.vwap || 0,
          };
        });

        // Merge with existing data, removing duplicates
        setAllData(prev => {
          const combined = [...prev, ...newPoints];
          const unique = combined.filter((item, index, self) =>
            index === self.findIndex((t) => t.timestamp === item.timestamp)
          );
          return unique.sort((a, b) => 
            new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
          );
        });
      }
    } catch (err) {
      console.error('Error fetching latest data:', err);
    }
  };

  // Fetch data when ticker changes
  useEffect(() => {
    fetchData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  // Real-time update every minute
  useEffect(() => {
    const interval = setInterval(() => {
      fetchLatestData();
    }, 60000); // 60 seconds

    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  // Filter data by selected date
  useEffect(() => {
    if (allData.length === 0) return;

    const selectedDateStr = selectedDate.toISOString().split('T')[0];
    const filtered = allData.filter(point => {
      const pointDateStr = new Date(point.timestamp).toISOString().split('T')[0];
      return pointDateStr === selectedDateStr;
    });

    setDisplayData(filtered);

    // Detect all crosses and filter for selected date
    const crosses = detectCrosses(allData);
    const dayCrosses = filterCrossesByDate(crosses, selectedDate);
    setTodayCrosses(dayCrosses);
  }, [allData, selectedDate]);

  const goToPreviousDay = () => {
    const newDate = new Date(selectedDate);
    newDate.setDate(newDate.getDate() - 1);
    setSelectedDate(newDate);
  };

  const goToNextDay = () => {
    const newDate = new Date(selectedDate);
    newDate.setDate(newDate.getDate() + 1);
    setSelectedDate(newDate);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6 mb-6">
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 mb-6">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Trading Dashboard
            </h1>
            
            <div className="flex items-center gap-4">
              <ESTClock />
              
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Ticker:
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
          </div>

          {/* Metrics Row */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
              <div className="text-sm font-medium text-blue-600 dark:text-blue-400">Ticker</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">{ticker}</div>
            </div>
            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
              <div className="text-sm font-medium text-green-600 dark:text-green-400">SMA9</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {displayData.length > 0 ? `$${displayData[displayData.length - 1].sma9.toFixed(2)}` : '-'}
              </div>
            </div>
            <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
              <div className="text-sm font-medium text-purple-600 dark:text-purple-400">VWAP</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {displayData.length > 0 ? `$${displayData[displayData.length - 1].vwap.toFixed(2)}` : '-'}
              </div>
            </div>
            <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
              <div className="text-sm font-medium text-red-600 dark:text-red-400">Crosses Today</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">
                {todayCrosses.length}
              </div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-900/20 rounded-lg p-4">
              <div className="text-sm font-medium text-gray-600 dark:text-gray-400">Period</div>
              <div className="text-2xl font-bold text-gray-900 dark:text-white">Minutes</div>
            </div>
          </div>

          {/* Date Navigation */}
          <div className="flex items-center gap-4 justify-center">
            <button
              onClick={goToPreviousDay}
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
            >
              ← Previous Day
            </button>
            
            <div className="relative">
              <DatePicker
                selected={selectedDate}
                onChange={(date) => date && setSelectedDate(date)}
                dateFormat="MMM dd, yyyy"
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent text-center cursor-pointer"
              />
            </div>
            
            <button
              onClick={goToNextDay}
              className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
            >
              Next Day →
            </button>
          </div>
        </div>

        {/* Chart */}
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6 mb-6">
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

          {!loading && !error && displayData.length > 0 && (
            <EquityChart data={displayData} ticker={ticker} crosses={todayCrosses} />
          )}

          {!loading && !error && displayData.length === 0 && (
            <div className="flex items-center justify-center h-96">
              <div className="text-lg text-gray-600 dark:text-gray-400">
                No data available for {ticker} on {formatToEST(selectedDate, 'MMM dd, yyyy')}
              </div>
            </div>
          )}
        </div>

        {/* Signals Dashboard */}
        {!loading && !error && (
          <SignalsDashboard crosses={todayCrosses} selectedDate={selectedDate} />
        )}
      </div>
    </div>
  );
}
