'use client';

import React, { useState, useEffect, useRef } from 'react';
import { formatToEST } from '@/lib/timezone';

interface DataFeedItem {
  timestamp: string;
  ticker: string;
  price: number;
  volume: number;
  sma9?: number;
  vwap?: number;
}

export default function DataManagementDashboard() {
  // Download Controls State
  const [ticker, setTicker] = useState('QQQ');
  const [singleDate, setSingleDate] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [downloadMode, setDownloadMode] = useState<'single' | 'range'>('single');
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadStatus, setDownloadStatus] = useState<string>('');

  // Streaming Controls State
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingStatus, setStreamingStatus] = useState<string>('Stopped');
  const [dataFeed, setDataFeed] = useState<DataFeedItem[]>([]);
  const dataFeedRef = useRef<HTMLDivElement>(null);
  const streamIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Set default date to today
  useEffect(() => {
    const today = new Date().toISOString().split('T')[0];
    setSingleDate(today);
    setEndDate(today);
    
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    setStartDate(weekAgo.toISOString().split('T')[0]);
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
      const payload = downloadMode === 'single' 
        ? { ticker, date: singleDate, mode: 'single' }
        : { ticker, startDate, endDate, mode: 'range' };

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const result = await response.json();

      if (response.ok) {
        setDownloadStatus(`✅ Success! Downloaded ${result.rowCount || 0} rows`);
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
          body: JSON.stringify({ action: 'start', ticker })
        });

        if (response.ok) {
          setStreamingStatus('🟢 Live');
          startDataFeed();
        } else {
          setStreamingStatus('❌ Failed to start');
          setIsStreaming(false);
        }
      } catch {
        setStreamingStatus('❌ Connection error');
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
      } catch {
        setStreamingStatus('⚫ Stopped (with errors)');
        stopDataFeed();
      }
    }
  };

  // Start mock data feed (replace with actual WebSocket/SSE in production)
  const startDataFeed = () => {
    // Clear existing interval
    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current);
    }

    // Simulate live data updates every second
    streamIntervalRef.current = setInterval(() => {
      const newDataPoint: DataFeedItem = {
        timestamp: new Date().toISOString(),
        ticker: ticker,
        price: 600 + Math.random() * 10,
        volume: Math.floor(Math.random() * 100000),
        sma9: 600 + Math.random() * 10,
        vwap: 600 + Math.random() * 10
      };

      setDataFeed(prev => {
        const updated = [...prev, newDataPoint];
        // Keep only last 15 items
        return updated.slice(-15);
      });
    }, 1000);
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
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 space-y-6">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        Data Management Dashboard
      </h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Historical Data Download Panel */}
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-5 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <span className="mr-2">📥</span> Historical Data Download
          </h3>

          {/* Ticker Input */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Ticker Symbol
            </label>
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              placeholder="QQQ"
            />
          </div>

          {/* Download Mode Toggle */}
          <div className="mb-4">
            <div className="flex gap-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  checked={downloadMode === 'single'}
                  onChange={() => setDownloadMode('single')}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Single Day</span>
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  checked={downloadMode === 'range'}
                  onChange={() => setDownloadMode('range')}
                  className="mr-2"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">Date Range</span>
              </label>
            </div>
          </div>

          {/* Date Inputs */}
          {downloadMode === 'single' ? (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Date
              </label>
              <input
                type="date"
                value={singleDate}
                onChange={(e) => setSingleDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Start Date
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  End Date
                </label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
          )}

          {/* Download Button */}
          <button
            onClick={handleDownload}
            disabled={isDownloading}
            className={`w-full py-3 px-4 rounded-md font-semibold text-white transition-colors ${
              isDownloading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {isDownloading ? 'Downloading...' : 'Download Data'}
          </button>

          {/* Download Status */}
          {downloadStatus && (
            <div className="mt-4 p-3 rounded-md bg-gray-100 dark:bg-gray-800 text-sm text-gray-900 dark:text-white">
              {downloadStatus}
            </div>
          )}
        </div>

        {/* Live Streaming Panel */}
        <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-5 border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
            <span className="mr-2">📡</span> Real-Time Data Stream
          </h3>

          {/* Streaming Toggle */}
          <div className="mb-4 flex items-center justify-between">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Stream Status: <span className="font-bold">{streamingStatus}</span>
            </label>
            <label className="flex items-center cursor-pointer">
              <div className="relative">
                <input
                  type="checkbox"
                  checked={isStreaming}
                  onChange={(e) => handleStreamingToggle(e.target.checked)}
                  className="sr-only"
                />
                <div className={`block w-14 h-8 rounded-full transition ${
                  isStreaming ? 'bg-green-500' : 'bg-gray-300 dark:bg-gray-600'
                }`}></div>
                <div className={`dot absolute left-1 top-1 bg-white w-6 h-6 rounded-full transition ${
                  isStreaming ? 'transform translate-x-6' : ''
                }`}></div>
              </div>
              <span className="ml-3 text-sm font-medium text-gray-700 dark:text-gray-300">
                {isStreaming ? 'ON' : 'OFF'}
              </span>
            </label>
          </div>

          {/* Streaming Ticker */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Streaming: {ticker}
            </label>
          </div>

          {/* Live Data Feed */}
          <div className="mt-4">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Live Data Feed (Last 15 Updates)
            </h4>
            <div
              ref={dataFeedRef}
              className="bg-black rounded-md p-3 h-80 overflow-y-auto font-mono text-xs text-green-400"
              style={{
                scrollBehavior: 'smooth'
              }}
            >
              {dataFeed.length === 0 ? (
                <div className="text-gray-500 text-center pt-8">
                  {isStreaming ? 'Waiting for data...' : 'Enable streaming to see live data'}
                </div>
              ) : (
                dataFeed.map((item, idx) => (
                  <div key={idx} className="mb-2 border-b border-gray-800 pb-2">
                    <div className="text-gray-400">{formatToEST(item.timestamp, 'h:mm:ss a')}</div>
                    <div className="flex justify-between">
                      <span>{item.ticker}</span>
                      <span className="text-blue-400">${item.price.toFixed(2)}</span>
                      <span className="text-yellow-400">Vol: {item.volume.toLocaleString()}</span>
                    </div>
                    {item.sma9 && item.vwap && (
                      <div className="text-gray-500 text-xs flex justify-between">
                        <span>SMA9: ${item.sma9.toFixed(2)}</span>
                        <span>VWAP: ${item.vwap.toFixed(2)}</span>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Info Panel */}
      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
        <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-2">
          💡 Quick Tips
        </h4>
        <ul className="text-sm text-blue-800 dark:text-blue-400 space-y-1 list-disc list-inside">
          <li>Use <strong>Single Day</strong> for downloading specific trading days</li>
          <li>Use <strong>Date Range</strong> for backfilling historical data (up to 10 days)</li>
          <li>The <strong>Real-Time Stream</strong> shows live market data during trading hours</li>
          <li>Data feed auto-scrolls and shows the most recent 15 updates</li>
          <li>Toggle streaming ON during market hours (10:00 AM - 3:00 PM ET) for live data</li>
        </ul>
      </div>
    </div>
  );
}

