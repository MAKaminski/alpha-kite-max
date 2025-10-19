'use client';

import React, { useState, useEffect } from 'react';
import { formatToEST } from '@/lib/timezone';

interface StrikeOption {
  strike: number;
  inRange: boolean;
  selected: boolean;
}

interface OptionsDownloadPanelProps {
  ticker: string;
  selectedDate: Date;
}

export default function OptionsDownloadPanel({ ticker, selectedDate }: OptionsDownloadPanelProps) {
  const [strikes, setStrikes] = useState<StrikeOption[]>([]);
  const [dailyLow, setDailyLow] = useState<number | null>(null);
  const [dailyHigh, setDailyHigh] = useState<number | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadStatus, setDownloadStatus] = useState<string>('');
  const [autoGenerateStrikes, setAutoGenerateStrikes] = useState(true);

  // Generate strike prices based on daily range
  useEffect(() => {
    const generateStrikes = async () => {
      if (!autoGenerateStrikes) return;
      
      try {
        // Fetch daily price data from Supabase to determine range
        const response = await fetch(`/api/get-daily-range?ticker=${ticker}&date=${selectedDate.toISOString().split('T')[0]}`);
        
        if (response.ok) {
          const { low, high } = await response.json();
          setDailyLow(low);
          setDailyHigh(high);
          
          // Generate strikes in $5 increments within range
          const strikeList: StrikeOption[] = [];
          const roundedLow = Math.floor(low / 5) * 5;
          const roundedHigh = Math.ceil(high / 5) * 5;
          
          for (let strike = roundedLow; strike <= roundedHigh; strike += 5) {
            strikeList.push({
              strike,
              inRange: strike >= low && strike <= high,
              selected: strike >= low && strike <= high // Auto-select in-range strikes
            });
          }
          
          setStrikes(strikeList);
        } else {
          // Default strikes if no data
          setDefaultStrikes();
        }
      } catch (error) {
        console.error('Error fetching daily range:', error);
        setDefaultStrikes();
      }
    };

    generateStrikes();
  }, [ticker, selectedDate, autoGenerateStrikes]);

  const setDefaultStrikes = () => {
    // Default QQQ strikes around $600
    const defaultList: StrikeOption[] = [];
    for (let strike = 580; strike <= 620; strike += 5) {
      defaultList.push({
        strike,
        inRange: strike >= 595 && strike <= 605, // Assume typical range
        selected: false
      });
    }
    setStrikes(defaultList);
    setDailyLow(595);
    setDailyHigh(605);
  };

  const toggleStrike = (index: number) => {
    setStrikes(prev => {
      const updated = [...prev];
      updated[index].selected = !updated[index].selected;
      return updated;
    });
  };

  const selectAll = () => {
    setStrikes(prev => prev.map(s => ({ ...s, selected: true })));
  };

  const selectInRange = () => {
    setStrikes(prev => prev.map(s => ({ ...s, selected: s.inRange })));
  };

  const deselectAll = () => {
    setStrikes(prev => prev.map(s => ({ ...s, selected: false })));
  };

  const handleDownload = async () => {
    const selectedStrikes = strikes.filter(s => s.selected).map(s => s.strike);
    
    if (selectedStrikes.length === 0) {
      setDownloadStatus('❌ Please select at least one strike');
      setTimeout(() => setDownloadStatus(''), 3000);
      return;
    }

    setIsDownloading(true);
    setDownloadStatus(`Downloading ${selectedStrikes.length} strikes...`);

    try {
      const response = await fetch('/api/download-options', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker,
          date: selectedDate.toISOString().split('T')[0],
          strikes: selectedStrikes
        })
      });

      const result = await response.json();

      if (response.ok) {
        setDownloadStatus(`✅ Downloaded ${result.rowCount || 0} rows for ${selectedStrikes.length} strikes`);
      } else {
        setDownloadStatus(`❌ Error: ${result.error || 'Download failed'}`);
      }
    } catch (error) {
      setDownloadStatus(`❌ Error: ${error instanceof Error ? error.message : 'Network error'}`);
    } finally {
      setIsDownloading(false);
      setTimeout(() => setDownloadStatus(''), 5000);
    }
  };

  const selectedCount = strikes.filter(s => s.selected).length;

  return (
    <div className="bg-gray-50 dark:bg-gray-900 rounded p-2 border border-gray-200 dark:border-gray-700">
      <h3 className="text-xs font-semibold text-gray-900 dark:text-white mb-1 flex items-center justify-between">
        <span className="flex items-center">
          <span className="mr-1">📈</span> 0DTE Options
        </span>
        <span className="text-[9px] text-gray-600 dark:text-gray-400">
          {dailyLow && dailyHigh ? `$${dailyLow.toFixed(0)}-$${dailyHigh.toFixed(0)}` : 'Loading...'}
        </span>
      </h3>

      {/* Date Info */}
      <div className="mb-1 p-1 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
        <p className="text-[9px] text-blue-800 dark:text-blue-300">
          <strong>Date:</strong> {formatToEST(selectedDate, 'MMM dd, yyyy')}
        </p>
        <p className="text-[9px] text-blue-800 dark:text-blue-300">
          <strong>Ticker:</strong> {ticker} (0DTE expires this date)
        </p>
      </div>

      {/* Quick Actions */}
      <div className="mb-1 flex gap-1">
        <button
          onClick={selectInRange}
          className="flex-1 px-1 py-0.5 text-[9px] bg-green-600 hover:bg-green-700 text-white rounded font-semibold"
        >
          In-Range
        </button>
        <button
          onClick={selectAll}
          className="flex-1 px-1 py-0.5 text-[9px] bg-blue-600 hover:bg-blue-700 text-white rounded font-semibold"
        >
          All
        </button>
        <button
          onClick={deselectAll}
          className="flex-1 px-1 py-0.5 text-[9px] bg-gray-500 hover:bg-gray-600 text-white rounded font-semibold"
        >
          None
        </button>
      </div>

      {/* Strike Checkboxes */}
      <div className="mb-1 max-h-32 overflow-y-auto bg-white dark:bg-gray-800 rounded border border-gray-300 dark:border-gray-600 p-1">
        <div className="grid grid-cols-3 gap-1">
          {strikes.map((strikeOption, index) => (
            <label
              key={strikeOption.strike}
              className={`flex items-center text-[9px] p-0.5 rounded cursor-pointer transition-colors ${
                strikeOption.inRange
                  ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-300 font-semibold'
                  : 'text-gray-700 dark:text-gray-400'
              } ${
                strikeOption.selected
                  ? 'ring-1 ring-blue-500'
                  : ''
              }`}
            >
              <input
                type="checkbox"
                checked={strikeOption.selected}
                onChange={() => toggleStrike(index)}
                className="mr-0.5 w-2.5 h-2.5"
              />
              <span>${strikeOption.strike}</span>
              {strikeOption.inRange && <span className="ml-0.5">✓</span>}
            </label>
          ))}
        </div>
      </div>

      {/* Selected Count */}
      <div className="mb-1 text-[9px] text-gray-600 dark:text-gray-400 text-center">
        {selectedCount} strike{selectedCount !== 1 ? 's' : ''} selected
      </div>

      {/* Download Button */}
      <button
        onClick={handleDownload}
        disabled={isDownloading || selectedCount === 0}
        className={`w-full py-1 px-2 text-[10px] rounded font-semibold text-white transition-colors ${
          isDownloading || selectedCount === 0
            ? 'bg-gray-400 cursor-not-allowed'
            : 'bg-purple-600 hover:bg-purple-700'
        }`}
      >
        {isDownloading ? 'Downloading...' : `Download ${selectedCount} Strike${selectedCount !== 1 ? 's' : ''}`}
      </button>

      {/* Download Status */}
      {downloadStatus && (
        <div className="mt-1 p-1 rounded bg-gray-100 dark:bg-gray-800 text-[9px] text-gray-900 dark:text-white">
          {downloadStatus}
        </div>
      )}

      {/* Info */}
      <div className="mt-1 p-1 bg-yellow-50 dark:bg-yellow-900/30 rounded border border-yellow-200 dark:border-yellow-700">
        <p className="text-[8px] text-yellow-800 dark:text-yellow-300">
          <strong>In-Range</strong> (green): Strikes QQQ traded through on this date.
          Downloads both CALL and PUT for each strike.
        </p>
      </div>
    </div>
  );
}

