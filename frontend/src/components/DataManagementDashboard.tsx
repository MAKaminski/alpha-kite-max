'use client';

import { formatToEST } from '@/lib/timezone';
import { memo, useEffect, useRef, useState } from 'react';
import OptionsDownloadPanel from './OptionsDownloadPanel';

interface DataFeedItem {
  timestamp: string;
  ticker: string;
  price: number;
  volume: number;
  sma9?: number;
  vwap?: number;
}

interface DataManagementDashboardProps {
  ticker?: string;
  selectedDate?: Date;
}

function DataManagementDashboard({ 
  ticker: initialTicker = 'QQQ',
  selectedDate = new Date()
}: DataManagementDashboardProps) {
  // Download Controls State
  const [ticker, setTicker] = useState(initialTicker);
  const [singleDate, setSingleDate] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [downloadMode, setDownloadMode] = useState<'single' | 'range'>('single');
  const [downloadTarget, setDownloadTarget] = useState<'database' | 'csv'>('database');
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadStatus, setDownloadStatus] = useState<string>('');

  // Streaming Controls State
  const [isStreaming, setIsStreaming] = useState(false); // Default to OFF for safety
  const [streamingStatus, setStreamingStatus] = useState<string>('⚫ Stopped');
  const [dataFeed, setDataFeed] = useState<DataFeedItem[]>([]);
  const dataFeedRef = useRef<HTMLDivElement>(null);
  const streamIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [streamingMode, setStreamingMode] = useState<'mock' | 'real'>('mock'); // Track streaming mode
  const [streamingType, setStreamingType] = useState<'equity' | 'options' | 'both'>('both'); // Track what to stream

  // Set default date to today and start streaming
  useEffect(() => {
    const today = new Date().toISOString().split('T')[0];
    setSingleDate(today);
    setEndDate(today);
    
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    setStartDate(weekAgo.toISOString().split('T')[0]);
    
    // Don't auto-start streaming for safety
    // startDataFeed();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-scroll data feed to bottom when new data arrives
  useEffect(() => {
    if (dataFeedRef.current) {
      dataFeedRef.current.scrollTop = dataFeedRef.current.scrollHeight;
    }
  }, [dataFeed]);

  // Handle Historical Data Download
  const handleDownload = async () => {
    setIsDownloading(true);
    setDownloadStatus('Downloading...');

    try {
      const endpoint = '/api/download-data';
      const payload = {
        ticker,
        mode: downloadMode,
        target: downloadTarget,
        ...(downloadMode === 'single' ? { date: singleDate } : { startDate, endDate })
      };

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const result = await response.json();

      if (response.ok) {
        if (downloadTarget === 'csv') {
          // Trigger CSV download
          const blob = new Blob([result.csvData || ''], { type: 'text/csv' });
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `${ticker}_${downloadMode === 'single' ? singleDate : `${startDate}_to_${endDate}`}.csv`;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
          
          setDownloadStatus(`✅ CSV downloaded! Check your Downloads folder`);
        } else {
          setDownloadStatus(`✅ Success! ${result.rowCount || 0} rows saved to database`);
        }
      } else {
        setDownloadStatus(`❌ Error: ${result.error || 'Download failed'}`);
      }
    } catch (err) {
      setDownloadStatus(`❌ Error: ${err instanceof Error ? err.message : 'Network error'}`);
    } finally {
      setIsDownloading(false);
      setTimeout(() => setDownloadStatus(''), 5000);
    }
  };

  // Handle Streaming Toggle
  const handleStreamingToggle = async (enabled: boolean) => {
    setIsStreaming(enabled);

    if (enabled) {
      setStreamingStatus('Starting...');
      
      try {
        // Start streaming endpoint
        const response = await fetch('/api/stream-control', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            action: 'start', 
            ticker,
            mode: streamingMode,
            type: streamingType
          })
        });

        if (response.ok) {
          const data = await response.json();
          if (streamingMode === 'mock') {
            setStreamingStatus('🟡 Live (MOCK)');
            startDataFeed();
          } else {
            setStreamingStatus('🟢 Live (REAL)');
            startRealDataFeed();
          }
        } else {
          setStreamingStatus('❌ Failed');
          setIsStreaming(false);
        }
      } catch (error) {
        console.error('Streaming start error:', error);
        setStreamingStatus('❌ Error');
        setIsStreaming(false);
      }
    } else {
      setStreamingStatus('Stopping...');
      
      try {
        // Stop streaming endpoint
        await fetch('/api/stream-control', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'stop', ticker })
        });

        setStreamingStatus('⚫ Stopped');
        stopDataFeed();
      } catch (error) {
        console.error('Streaming stop error:', error);
        setStreamingStatus('⚫ Stopped');
        stopDataFeed();
      }
    }
  };

  // Start mock data feed for testing
  const startDataFeed = () => {
    // Clear existing interval
    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current);
    }

    // Simulate live data updates every second (MOCK MODE)
    streamIntervalRef.current = setInterval(() => {
      const newDataPoint: DataFeedItem = {
        timestamp: new Date().toISOString(),
        ticker: ticker,
        price: 600 + Math.random() * 10,  // MOCK: Random price around 600
        volume: Math.floor(Math.random() * 100000),  // MOCK: Random volume
        sma9: 600 + Math.random() * 10,  // MOCK: Random SMA9
        vwap: 600 + Math.random() * 10   // MOCK: Random VWAP
      };

      setDataFeed(prev => {
        const updated = [...prev, newDataPoint];
        // Keep only last 15 items
        return updated.slice(-15);
      });
    }, 1000);
  };

  // Start real data feed from Schwab
  const startRealDataFeed = () => {
    // Clear existing interval
    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current);
    }

    // Connect to real-time WebSocket or polling
    streamIntervalRef.current = setInterval(async () => {
      try {
        // Fetch real-time data from backend
        const response = await fetch(`/api/real-time-data?ticker=${ticker}&type=${streamingType}`);
        if (response.ok) {
          const data = await response.json();
          const newDataPoint: DataFeedItem = {
            timestamp: new Date().toISOString(),
            ticker: ticker,
            price: data.price || 0,
            volume: data.volume || 0,
            sma9: data.sma9 || 0,
            vwap: data.vwap || 0
          };

          setDataFeed(prev => {
            const updated = [...prev, newDataPoint];
            return updated.slice(-15);
          });
        }
      } catch (error) {
        console.error('Real data feed error:', error);
      }
    }, 1000); // Real data every second
  };

  // Stop data feed
  const stopDataFeed = () => {
    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current);
      streamIntervalRef.current = null;
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopDataFeed();
    };
  }, []);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-2 space-y-2">
      <h2 className="text-sm font-bold text-gray-900 dark:text-white">
        Data Management
      </h2>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-1">
        {/* Historical Data Download Panel */}
        <div className="bg-gray-50 dark:bg-gray-900 rounded p-1 border border-gray-200 dark:border-gray-700">
          <h3 className="text-xs font-semibold text-gray-900 dark:text-white mb-0.5 flex items-center">
            <span className="mr-1">📥</span> Download
          </h3>

          {/* Ticker Input */}
          <div className="mb-1">
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="w-full px-1 py-0.5 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-1 focus:ring-blue-500"
              placeholder="QQQ"
            />
          </div>

          {/* Download Mode Toggle */}
          <div className="mb-1 flex gap-2">
            <label className="flex items-center">
              <input
                type="radio"
                checked={downloadMode === 'single'}
                onChange={() => setDownloadMode('single')}
                className="mr-0.5"
              />
              <span className="text-[10px] text-gray-700 dark:text-gray-300">Day</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                checked={downloadMode === 'range'}
                onChange={() => setDownloadMode('range')}
                className="mr-0.5"
              />
              <span className="text-[10px] text-gray-700 dark:text-gray-300">Range</span>
            </label>
          </div>

          {/* Download Target Toggle */}
          <div className="mb-1 flex gap-2">
            <label className="flex items-center">
              <input
                type="radio"
                checked={downloadTarget === 'database'}
                onChange={() => setDownloadTarget('database')}
                className="mr-0.5"
              />
              <span className="text-[10px] text-gray-700 dark:text-gray-300">DB</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                checked={downloadTarget === 'csv'}
                onChange={() => setDownloadTarget('csv')}
                className="mr-0.5"
              />
              <span className="text-[10px] text-gray-700 dark:text-gray-300">CSV</span>
            </label>
          </div>

          {/* Date Inputs */}
          {downloadMode === 'single' ? (
            <div className="mb-1">
              <input
                type="date"
                value={singleDate}
                onChange={(e) => setSingleDate(e.target.value)}
                className="w-full px-1 py-0.5 text-[10px] border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-1 focus:ring-blue-500"
              />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-1 mb-1">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-1 py-0.5 text-[10px] border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-1 focus:ring-blue-500"
              />
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-1 py-0.5 text-[10px] border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-1 focus:ring-blue-500"
              />
            </div>
          )}

          {/* Download Button */}
          <button
            onClick={handleDownload}
            disabled={isDownloading}
            className={`w-full py-1 px-2 text-[10px] rounded font-semibold text-white transition-colors ${
              isDownloading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {isDownloading ? 'Loading...' : 'Download'}
          </button>

          {/* Download Status */}
          {downloadStatus && (
            <div className="mt-1 p-1 rounded bg-gray-100 dark:bg-gray-800 text-[9px] text-gray-900 dark:text-white">
              {downloadStatus}
            </div>
          )}
        </div>

        {/* Live Streaming Panel */}
        <div className="bg-gray-50 dark:bg-gray-900 rounded p-1 border border-gray-200 dark:border-gray-700">
          <h3 className="text-xs font-semibold text-gray-900 dark:text-white mb-0.5 flex items-center">
            <span className="mr-1">📡</span> Stream
          </h3>

          {/* Streaming Toggle */}
          <div className="mb-1">
            <div className="flex items-center justify-between">
              <label className="text-[10px] font-medium text-gray-700 dark:text-gray-300">
                {streamingStatus}
              </label>
              <label className="flex items-center cursor-pointer">
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={isStreaming}
                    onChange={(e) => handleStreamingToggle(e.target.checked)}
                    className="sr-only"
                  />
                  <div className={`block w-8 h-5 rounded-full transition ${
                    isStreaming ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'
                  }`}></div>
                  <div className={`dot absolute left-1 top-1 bg-white w-3 h-3 rounded-full transition ${
                    isStreaming ? 'transform translate-x-3' : ''
                  }`}></div>
                </div>
                <span className="ml-1 text-[10px] font-medium text-gray-700 dark:text-gray-300">
                  {isStreaming ? 'ON' : 'OFF'}
                </span>
              </label>
            </div>
            {/* Streaming Mode Selection */}
            <div className="mb-1">
              <label className="text-[9px] font-medium text-gray-700 dark:text-gray-300 block mb-0.5">
                Mode:
              </label>
              <div className="flex gap-1">
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={streamingMode === 'mock'}
                    onChange={() => setStreamingMode('mock')}
                    className="mr-0.5"
                  />
                  <span className="text-[9px] text-gray-700 dark:text-gray-300">Mock</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={streamingMode === 'real'}
                    onChange={() => setStreamingMode('real')}
                    className="mr-0.5"
                  />
                  <span className="text-[9px] text-gray-700 dark:text-gray-300">Real</span>
                </label>
              </div>
            </div>

            {/* Streaming Type Selection */}
            <div className="mb-1">
              <label className="text-[9px] font-medium text-gray-700 dark:text-gray-300 block mb-0.5">
                Type:
              </label>
              <div className="flex gap-1">
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={streamingType === 'equity'}
                    onChange={() => setStreamingType('equity')}
                    className="mr-0.5"
                  />
                  <span className="text-[9px] text-gray-700 dark:text-gray-300">Equity</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={streamingType === 'options'}
                    onChange={() => setStreamingType('options')}
                    className="mr-0.5"
                  />
                  <span className="text-[9px] text-gray-700 dark:text-gray-300">Options</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    checked={streamingType === 'both'}
                    onChange={() => setStreamingType('both')}
                    className="mr-0.5"
                  />
                  <span className="text-[9px] text-gray-700 dark:text-gray-300">Both</span>
                </label>
              </div>
            </div>

            {/* Mode Warning */}
            {streamingMode === 'mock' && isStreaming && (
              <div className="mt-1 px-1 py-0.5 bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700 rounded">
                <p className="text-[8px] text-yellow-800 dark:text-yellow-300 font-semibold">
                  ⚠️ MOCK MODE: Test data only
                </p>
              </div>
            )}
            {streamingMode === 'real' && isStreaming && (
              <div className="mt-1 px-1 py-0.5 bg-green-100 dark:bg-green-900/30 border border-green-300 dark:border-green-700 rounded">
                <p className="text-[8px] text-green-800 dark:text-green-300 font-semibold">
                  🟢 LIVE MODE: Real Schwab data
                </p>
              </div>
            )}
          </div>

          {/* Live Data Feed */}
          <div
            ref={dataFeedRef}
            className="bg-black dark:bg-gray-950 rounded p-1 h-32 overflow-y-auto font-mono text-[9px] text-green-400"
            style={{
              scrollBehavior: 'smooth'
            }}
          >
            {dataFeed.length === 0 ? (
              <div className="text-gray-500 text-center pt-2 text-[9px]">
                {isStreaming ? 'Waiting...' : 'Toggle ON'}
              </div>
            ) : (
              dataFeed.map((item, idx) => (
                <div key={idx} className="mb-0.5 border-b border-gray-800 pb-0.5">
                  <div className="text-gray-400 text-[9px]">{formatToEST(item.timestamp, 'h:mm:ss a')}</div>
                  <div className="flex justify-between text-[9px]">
                    <span>{item.ticker}</span>
                    <span className="text-blue-400">${item.price.toFixed(2)}</span>
                    <span className="text-yellow-400">{(item.volume / 1000).toFixed(0)}K</span>
                  </div>
                  {item.sma9 && item.vwap && (
                    <div className="text-gray-500 text-[8px] flex justify-between">
                      <span>SMA: ${item.sma9.toFixed(2)}</span>
                      <span>VWAP: ${item.vwap.toFixed(2)}</span>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Options Download Panel */}
        <OptionsDownloadPanel ticker={ticker} selectedDate={selectedDate} />

        {/* Info Panel */}
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded p-2 border border-blue-200 dark:border-blue-800">
          <h4 className="text-xs font-semibold text-blue-900 dark:text-blue-300 mb-1">
            💡 Tips
          </h4>
          <ul className="text-[9px] text-blue-800 dark:text-blue-400 space-y-0.5 list-disc list-inside">
            <li><strong>Day</strong>: Specific date</li>
            <li><strong>Range</strong>: Multiple days</li>
            <li><strong>DB</strong>: Saves to database</li>
            <li><strong>CSV</strong>: Downloads file</li>
            <li><strong>Options</strong>: 0DTE strikes via Polygon</li>
            <li><strong>Stream</strong>: 10 AM - 3 PM ET</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

// Export memoized version to prevent unnecessary re-renders
export default memo(DataManagementDashboard);
