'use client';

import { Cross, detectCrosses, filterCrossesByDate } from '@/lib/crossDetection';
import { useFeatureFlag } from '@/lib/featureFlags';
import { getTradeOptionPrices, TradeOptionPrice } from '@/lib/optionPrices';
import { RealTimeOptionPrice, realTimeOptionsService } from '@/lib/realTimeOptions';
import { isSupabaseConfigured, supabase } from '@/lib/supabase';
import { formatToEST } from '@/lib/timezone';
import { useEffect, useState } from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
import { ChartDataPoint } from '../../../shared/types';
import DarkModeToggle from './DarkModeToggle';
import DataManagementDashboard from './DataManagementDashboard';
import EquityChart from './EquityChart';
import ESTClock from './ESTClock';
import SignalsDashboard from './SignalsDashboard';
import TradingDashboard from './TradingDashboard';

export default function Dashboard() {
  const [ticker, setTicker] = useState('QQQ');
  const [allData, setAllData] = useState<ChartDataPoint[]>([]);
  const [displayData, setDisplayData] = useState<ChartDataPoint[]>([]);
  // Default to Oct 17, 2025 - the last date with equity data
  const [selectedDate, setSelectedDate] = useState(new Date('2025-10-17'));
  const [todayCrosses, setTodayCrosses] = useState<Cross[]>([]);
  const [optionPrices, setOptionPrices] = useState<TradeOptionPrice[]>([]);
  const [realTimeOptionPrices, setRealTimeOptionPrices] = useState<RealTimeOptionPrice[]>([]);
  interface SyntheticOption {
    id: number;
    timestamp: string;
    ticker: string;
    option_symbol: string;
    option_type: string;
    strike_price: number;
    expiration_date: string;
    spot_price: number;
    market_price: number;
    bid: number;
    ask: number;
    volume: number;
    open_interest: number;
    implied_volatility: number;
    delta: number;
    gamma: number;
    theta: number;
    vega: number;
    data_source: string;
  }
  
  const [syntheticOptionPrices, setSyntheticOptionPrices] = useState<SyntheticOption[]>([]);
  const [showNonMarketHours, setShowNonMarketHours] = useState(false);
  const [period, setPeriod] = useState<'minute' | 'hour'>('minute');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAdminPanel, setShowAdminPanel] = useState(false);

  // Feature flags
  const realTimeDataEnabled = useFeatureFlag('real-time-data');
  const realTimeClockEnabled = useFeatureFlag('real-time-clock');
  const signalsDashboardEnabled = useFeatureFlag('signals-dashboard');
  const tradingDashboardEnabled = useFeatureFlag('trading-dashboard');
  const adminPanelEnabled = useFeatureFlag('admin-panel');
  const optionPricesEnabled = useFeatureFlag('option-prices');
  const realTimeOptionsEnabled = useFeatureFlag('real-time-options');
  const crossDetectionEnabled = useFeatureFlag('cross-detection');
  const marketHoursHighlightingEnabled = useFeatureFlag('market-hours-highlighting');
  const nonMarketHoursToggleEnabled = useFeatureFlag('non-market-hours-toggle');
  const darkModeEnabled = useFeatureFlag('dark-mode');

  // Aggregate minute data to hourly data
  const aggregateToHourly = (data: ChartDataPoint[]): ChartDataPoint[] => {
    if (data.length === 0) return [];
    
    // Group data by hour
    const hourlyGroups: { [key: string]: ChartDataPoint[] } = {};
    
    data.forEach(point => {
      const date = new Date(point.timestamp);
      const hourKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:00:00`;
      
      if (!hourlyGroups[hourKey]) {
        hourlyGroups[hourKey] = [];
      }
      hourlyGroups[hourKey].push(point);
    });
    
    // Aggregate each hour
    const hourlyData: ChartDataPoint[] = Object.entries(hourlyGroups).map(([hourKey, points]) => {
      if (points.length === 0) return null;
      
      // Calculate volume-weighted averages
      const prices = points.map(p => p.price);
      const volumes = points.map(p => p.volume);
      const sma9Values = points.map(p => p.sma9);
      const vwapValues = points.map(p => p.vwap);
      
      const close = prices[prices.length - 1];
      const totalVolume = volumes.reduce((sum, vol) => sum + vol, 0);
      
      // Use close price as the representative price
      const price = close;
      
      // Volume-weighted average of SMA9 and VWAP
      const totalVolumeWeight = volumes.reduce((sum, vol) => sum + vol, 0);
      const sma9 = totalVolumeWeight > 0 ? 
        sma9Values.reduce((sum, val, i) => sum + (val * volumes[i]), 0) / totalVolumeWeight : 
        sma9Values[sma9Values.length - 1];
      const vwap = totalVolumeWeight > 0 ? 
        vwapValues.reduce((sum, val, i) => sum + (val * volumes[i]), 0) / totalVolumeWeight : 
        vwapValues[vwapValues.length - 1];
      
      return {
        timestamp: hourKey,
        price,
        volume: totalVolume,
        sma9,
        vwap
      };
    }).filter(Boolean) as ChartDataPoint[];
    
    return hourlyData.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  };

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

      // Apply period aggregation if needed
      const processedData = period === 'hour' ? aggregateToHourly(mergedData) : mergedData;
      setAllData(processedData);
      
      // Set selected date to most recent data
      if (processedData.length > 0) {
        const latestDate = new Date(processedData[processedData.length - 1].timestamp);
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

  const fetchOptionPrices = async () => {
    try {
      const prices = await getTradeOptionPrices(ticker, selectedDate);
      setOptionPrices(prices || []);
    } catch (error) {
      console.error('Error fetching option prices:', error);
      setOptionPrices([]);
    }
  };

  const fetchRealTimeOptionPrices = async () => {
    try {
      const prices = await realTimeOptionsService.getHistoricalOptionPrices(ticker, selectedDate);
      setRealTimeOptionPrices(prices || []);
    } catch (error) {
      console.error('Error fetching real-time option prices:', error);
      setRealTimeOptionPrices([]);
    }
  };

  const fetchSyntheticOptionPrices = async () => {
    try {
      const dateStr = selectedDate.toISOString().split('T')[0];
      console.log('🔍 Fetching synthetic options for:', ticker, 'date:', dateStr);
      const response = await fetch(`/api/get-options-for-chart?ticker=${ticker}&date=${dateStr}`);
      
      if (!response.ok) {
        console.error('Failed to fetch synthetic options:', response.statusText);
        setSyntheticOptionPrices([]);
        return;
      }
      
      const result = await response.json();
      console.log('✅ Fetched synthetic options:', result.count, 'options');
      if (result.data && result.data.length > 0) {
        console.log('   First option:', result.data[0]);
      }
      setSyntheticOptionPrices(result.data || []);
    } catch (error) {
      console.error('Error fetching synthetic option prices:', error);
      setSyntheticOptionPrices([]);
    }
  };

  // Fetch data when ticker or period changes
  useEffect(() => {
    fetchData();
    if (optionPricesEnabled) {
      fetchOptionPrices();
    }
    if (realTimeOptionsEnabled) {
      fetchRealTimeOptionPrices();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker, period, optionPricesEnabled, realTimeOptionsEnabled]);

  // Fetch option prices when date changes (only if enabled)
  useEffect(() => {
    if (optionPricesEnabled) {
      fetchOptionPrices();
    }
    if (realTimeOptionsEnabled) {
      fetchRealTimeOptionPrices();
    }
    // Always fetch synthetic options (for 0DTE chart display)
    fetchSyntheticOptionPrices();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate, ticker, optionPricesEnabled, realTimeOptionsEnabled]);

  // Start real-time options pricing for current ticker (only if enabled)
  useEffect(() => {
    if (!realTimeOptionsEnabled) {
      setRealTimeOptionPrices([]);
      return;
    }

    realTimeOptionsService.start(ticker);
    
    const unsubscribe = realTimeOptionsService.subscribe((update) => {
      // Update real-time option prices
      setRealTimeOptionPrices(prev => {
        const updated = [...prev];
        const existingIndex = updated.findIndex(p => p.timestamp === update.timestamp);
        
        if (existingIndex >= 0) {
          updated[existingIndex] = {
            timestamp: update.timestamp,
            ticker: update.ticker,
            put_strike: 590, // Mock strike prices
            put_price: update.put_price,
            call_strike: 595,
            call_price: update.call_price,
            current_price: update.current_price
          };
        } else {
          updated.push({
            timestamp: update.timestamp,
            ticker: update.ticker,
            put_strike: 590,
            put_price: update.put_price,
            call_strike: 595,
            call_price: update.call_price,
            current_price: update.current_price
          });
        }
        
        return updated.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
      });
    });

    return () => {
      unsubscribe();
      realTimeOptionsService.stop();
    };
  }, [ticker, realTimeOptionsEnabled]);

  // Real-time update every minute (only if enabled)
  useEffect(() => {
    if (!realTimeDataEnabled) return;

    const interval = setInterval(() => {
      fetchLatestData();
    }, 60000); // 60 seconds

    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker, realTimeDataEnabled]);

  // Filter data by selected date
  useEffect(() => {
    if (allData.length === 0) return;

    const selectedDateStr = selectedDate.toISOString().split('T')[0];
    const filtered = allData.filter(point => {
      const pointDateStr = new Date(point.timestamp).toISOString().split('T')[0];
      return pointDateStr === selectedDateStr;
    });

    setDisplayData(filtered);

    // Detect all crosses and filter for selected date (only if enabled)
    if (crossDetectionEnabled) {
      const crosses = detectCrosses(allData);
      const dayCrosses = filterCrossesByDate(crosses, selectedDate);
      setTodayCrosses(dayCrosses);
    } else {
      setTodayCrosses([]);
    }
  }, [allData, selectedDate, crossDetectionEnabled]);

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
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-2 md:p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-3 mb-3">
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-2 mb-3">
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">
              Trading Dashboard
            </h1>
            
            <div className="flex items-center gap-2 flex-wrap">
              {realTimeClockEnabled && <ESTClock />}
              
              <div className="flex items-center gap-1">
                <label className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  Ticker:
                </label>
                <input
                  type="text"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-1 focus:ring-blue-500"
                  placeholder="QQQ"
                />
              </div>

              <div className="flex items-center gap-1">
                <label className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  Period:
                </label>
                <select
                  value={period}
                  onChange={(e) => setPeriod(e.target.value as 'minute' | 'hour')}
                  className="px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-1 focus:ring-blue-500"
                >
                  <option value="minute">Minute</option>
                  <option value="hour">Hour</option>
                </select>
              </div>

              {/* Dark Mode Toggle */}
              {darkModeEnabled && <DarkModeToggle />}
            </div>
          </div>

          {/* Metrics Row - More Compact */}
          <div className="grid grid-cols-3 lg:grid-cols-5 gap-2 mb-2">
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded p-2">
              <div className="text-[10px] font-medium text-blue-600 dark:text-blue-400">Ticker</div>
              <div className="text-base font-bold text-gray-900 dark:text-white">{ticker}</div>
            </div>
            <div className="bg-green-50 dark:bg-green-900/20 rounded p-2">
              <div className="text-[10px] font-medium text-green-600 dark:text-green-400">SMA9</div>
              <div className="text-base font-bold text-gray-900 dark:text-white">
                {displayData.length > 0 ? `$${displayData[displayData.length - 1].sma9.toFixed(2)}` : '-'}
              </div>
            </div>
            <div className="bg-purple-50 dark:bg-purple-900/20 rounded p-2">
              <div className="text-[10px] font-medium text-purple-600 dark:text-purple-400">VWAP</div>
              <div className="text-base font-bold text-gray-900 dark:text-white">
                {displayData.length > 0 ? `$${displayData[displayData.length - 1].vwap.toFixed(2)}` : '-'}
              </div>
            </div>
            <div className="bg-red-50 dark:bg-red-900/20 rounded p-2">
              <div className="text-[10px] font-medium text-red-600 dark:text-red-400">Crosses</div>
              <div className="text-base font-bold text-gray-900 dark:text-white">
                {todayCrosses.length}
              </div>
            </div>
            <div className="bg-gray-50 dark:bg-gray-900/20 rounded p-2">
              <div className="text-[10px] font-medium text-gray-600 dark:text-gray-400">Period</div>
              <div className="text-base font-bold text-gray-900 dark:text-white">Min</div>
            </div>
          </div>

          {/* Date Navigation - Compact */}
          <div className="flex items-center gap-2 justify-center">
            <button
              onClick={goToPreviousDay}
              className="px-2 py-1 text-xs bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
            >
              ← Prev
            </button>
            
            <div className="relative">
              <DatePicker
                selected={selectedDate}
                onChange={(date) => date && setSelectedDate(date)}
                dateFormat="MMM dd, yyyy"
                className="px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-1 focus:ring-blue-500 text-center cursor-pointer"
              />
            </div>
            
            <button
              onClick={goToNextDay}
              className="px-2 py-1 text-xs bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
            >
              Next →
            </button>
          </div>
        </div>

        {/* Chart */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-3 mb-3">
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
            <EquityChart 
              data={displayData} 
              ticker={ticker} 
              crosses={crossDetectionEnabled ? todayCrosses : []}
              optionPrices={optionPricesEnabled ? optionPrices : []}
              realTimeOptionPrices={realTimeOptionsEnabled ? realTimeOptionPrices : []}
              syntheticOptionPrices={syntheticOptionPrices}
              showNonMarketHours={showNonMarketHours}
              onToggleNonMarketHours={nonMarketHoursToggleEnabled ? setShowNonMarketHours : undefined}
              marketHoursHighlighting={marketHoursHighlightingEnabled}
              period={period}
            />
          )}

          {!loading && !error && displayData.length === 0 && (
            <div className="flex items-center justify-center h-96">
              <div className="text-lg text-gray-600 dark:text-gray-400">
                No data available for {ticker} on {formatToEST(selectedDate, 'MMM dd, yyyy')}
              </div>
            </div>
          )}
        </div>

        {/* Data Management Dashboard */}
        {!loading && !error && (
          <div className="mb-3">
            <DataManagementDashboard ticker={ticker} selectedDate={selectedDate} />
          </div>
        )}

        {/* Trading Dashboard */}
        {!loading && !error && tradingDashboardEnabled && (
          <TradingDashboard ticker={ticker} selectedDate={selectedDate} />
        )}

        {/* Signals Dashboard */}
        {!loading && !error && signalsDashboardEnabled && (
          <SignalsDashboard crosses={todayCrosses} selectedDate={selectedDate} />
        )}

        {/* Admin controls moved to sticky top tabs (Options/Admin). Floating FAB removed. */}
      </div>
    </div>
  );
}
