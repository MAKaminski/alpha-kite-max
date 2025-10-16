'use client';

import React, { useState, useEffect } from 'react';
import { formatToEST } from '@/lib/timezone';
import { useFeatureFlag } from '@/lib/featureFlags';
import FeatureFlagsDashboard from './FeatureFlagsDashboard';

interface SystemMetrics {
  // Lambda Metrics
  lambdaInvocations: number;
  lambdaErrors: number;
  lambdaDuration: number;
  lambdaLastExecution: string | null;
  lambdaSuccessRate: number;
  
  // Data Pipeline Metrics
  dataPointsFetched: number;
  equityRows: number;
  indicatorRows: number;
  optionRows: number;
  lastDataTimestamp: string | null;
  dataFreshness: number; // minutes since last data
  
  // Database Metrics
  totalEquityRows: number;
  totalIndicatorRows: number;
  totalOptionRows: number;
  totalPositions: number;
  totalTrades: number;
  
  // Market Status
  isMarketOpen: boolean;
  timeToMarketOpen: number; // minutes
  timeToMarketClose: number; // minutes
  
  // System Health
  supabaseConnected: boolean;
  schwabTokenValid: boolean;
  lastTokenRefresh: string | null;
  
  // Cost Metrics
  monthlyLambdaCost: number;
  monthlyStorageCost: number;
  monthlyTotalCost: number;
  freeTierUsage: {
    lambdaRequests: { used: number; limit: number; percentage: number };
    lambdaCompute: { used: number; limit: number; percentage: number };
    cloudWatchLogs: { used: number; limit: number; percentage: number };
  };
}

interface AdminPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AdminPanel({ isOpen, onClose }: AdminPanelProps) {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'status' | 'pipeline' | 'database' | 'trading' | 'costs' | 'features'>('status');
  const [showFeatureFlags, setShowFeatureFlags] = useState(false);
  
  // Feature flags for quick overview
  const realTimeDataEnabled = useFeatureFlag('real-time-data');
  const tradingEngineEnabled = useFeatureFlag('paper-trading');
  const chartZoomEnabled = useFeatureFlag('chart-zoom');
  const signalsDashboardEnabled = useFeatureFlag('signals-dashboard');
  const adminPanelEnabled = useFeatureFlag('admin-panel');
  const darkModeEnabled = useFeatureFlag('dark-mode');
  const debugModeEnabled = useFeatureFlag('debug-logs');

  useEffect(() => {
    if (isOpen) {
      fetchSystemMetrics();
      // Refresh metrics every 30 seconds
      const interval = setInterval(fetchSystemMetrics, 30000);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  const fetchSystemMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // In a real implementation, this would call your backend API
      // For now, we'll simulate the data structure
      const mockMetrics: SystemMetrics = {
        // Lambda Metrics
        lambdaInvocations: 391, // Today's executions
        lambdaErrors: 0,
        lambdaDuration: 3.2, // Average seconds
        lambdaLastExecution: new Date().toISOString(),
        lambdaSuccessRate: 100,
        
        // Data Pipeline Metrics
        dataPointsFetched: 391,
        equityRows: 391,
        indicatorRows: 391,
        optionRows: 782, // 2 per minute (CALL + PUT)
        lastDataTimestamp: new Date().toISOString(),
        dataFreshness: 1, // 1 minute ago
        
        // Database Metrics
        totalEquityRows: 8760, // ~1 month of data
        totalIndicatorRows: 8760,
        totalOptionRows: 17520,
        totalPositions: 0,
        totalTrades: 0,
        
        // Market Status
        isMarketOpen: true,
        timeToMarketOpen: 0,
        timeToMarketClose: 240, // 4 hours
        
        // System Health
        supabaseConnected: true,
        schwabTokenValid: true,
        lastTokenRefresh: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
        
        // Cost Metrics
        monthlyLambdaCost: 0.18,
        monthlyStorageCost: 1.45,
        monthlyTotalCost: 2.03,
        freeTierUsage: {
          lambdaRequests: { used: 8602, limit: 1000000, percentage: 0.86 },
          lambdaCompute: { used: 10800, limit: 400000, percentage: 2.7 },
          cloudWatchLogs: { used: 0.5, limit: 5, percentage: 10 }
        }
      };
      
      setMetrics(mockMetrics);
    } catch (err) {
      setError('Failed to fetch system metrics');
      console.error('Error fetching metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: boolean) => status ? 'text-green-500' : 'text-red-500';
  const getStatusIcon = (status: boolean) => status ? '✅' : '❌';

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-50 dark:bg-gray-900 z-50 overflow-auto">
      <div className="min-h-screen p-6">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">System Administration</h1>
              <p className="text-gray-600 dark:text-gray-400 mt-1">Monitor and manage Alpha Kite Max infrastructure</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-3xl font-bold transition-colors"
              aria-label="Close admin panel"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Main Dashboard */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
          {/* Tab Navigation */}
          <div className="border-b border-gray-200 dark:border-gray-700 px-6 pt-4">
            <nav className="flex space-x-4">
            {[
              { id: 'status', label: 'Status', icon: '📊' },
              { id: 'pipeline', label: 'Pipeline', icon: '⚡' },
              { id: 'database', label: 'Database', icon: '🗄️' },
              { id: 'trading', label: 'Trading', icon: '💰' },
              { id: 'costs', label: 'Costs', icon: '💵' },
              { id: 'features', label: 'Features', icon: '🔧' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as 'status' | 'pipeline' | 'database' | 'trading' | 'costs' | 'features')}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 hover:border-gray-300'
                }`}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-500">Loading metrics...</div>
            </div>
          ) : error ? (
            <div className="text-red-500 text-center">{error}</div>
          ) : metrics ? (
            <>
              {/* Status Tab */}
              {activeTab === 'status' && (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      System Health
                    </h3>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Supabase</span>
                        <span className={`text-sm ${getStatusColor(metrics.supabaseConnected)}`}>
                          {getStatusIcon(metrics.supabaseConnected)} Connected
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Schwab Token</span>
                        <span className={`text-sm ${getStatusColor(metrics.schwabTokenValid)}`}>
                          {getStatusIcon(metrics.schwabTokenValid)} Valid
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Lambda</span>
                        <span className={`text-sm ${getStatusColor(metrics.lambdaSuccessRate === 100)}`}>
                          {getStatusIcon(metrics.lambdaSuccessRate === 100)} {metrics.lambdaSuccessRate}% Success
                        </span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Market Status
                    </h3>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Status</span>
                        <span className={`text-sm ${getStatusColor(metrics.isMarketOpen)}`}>
                          {getStatusIcon(metrics.isMarketOpen)} {metrics.isMarketOpen ? 'Open' : 'Closed'}
                        </span>
                      </div>
                      {metrics.isMarketOpen ? (
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600 dark:text-gray-400">Time to Close</span>
                          <span className="text-sm text-gray-900 dark:text-white">
                            {formatDuration(metrics.timeToMarketClose)}
                          </span>
                        </div>
                      ) : (
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600 dark:text-gray-400">Time to Open</span>
                          <span className="text-sm text-gray-900 dark:text-white">
                            {formatDuration(metrics.timeToMarketOpen)}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Data Freshness
                    </h3>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Last Update</span>
                        <span className="text-sm text-gray-900 dark:text-white">
                          {metrics.lastDataTimestamp ? formatToEST(metrics.lastDataTimestamp, 'h:mm:ss a') : 'N/A'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Freshness</span>
                        <span className={`text-sm ${metrics.dataFreshness <= 2 ? 'text-green-500' : 'text-yellow-500'}`}>
                          {metrics.dataFreshness} min ago
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Pipeline Tab */}
              {activeTab === 'pipeline' && (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Lambda Performance
                    </h3>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Today&apos;s Executions</span>
                        <span className="text-sm text-gray-900 dark:text-white">{metrics.lambdaInvocations}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Errors</span>
                        <span className={`text-sm ${metrics.lambdaErrors === 0 ? 'text-green-500' : 'text-red-500'}`}>
                          {metrics.lambdaErrors}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Avg Duration</span>
                        <span className="text-sm text-gray-900 dark:text-white">{metrics.lambdaDuration}s</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Success Rate</span>
                        <span className={`text-sm ${getStatusColor(metrics.lambdaSuccessRate === 100)}`}>
                          {metrics.lambdaSuccessRate}%
                        </span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Data Pipeline
                    </h3>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Equity Rows</span>
                        <span className="text-sm text-gray-900 dark:text-white">{metrics.equityRows}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Indicator Rows</span>
                        <span className="text-sm text-gray-900 dark:text-white">{metrics.indicatorRows}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Option Rows</span>
                        <span className="text-sm text-gray-900 dark:text-white">{metrics.optionRows}</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Database Tab */}
              {activeTab === 'database' && (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Table Statistics
                    </h3>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Equity Data</span>
                        <span className="text-sm text-gray-900 dark:text-white">{metrics.totalEquityRows.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Indicators</span>
                        <span className="text-sm text-gray-900 dark:text-white">{metrics.totalIndicatorRows.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Option Prices</span>
                        <span className="text-sm text-gray-900 dark:text-white">{metrics.totalOptionRows.toLocaleString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Positions</span>
                        <span className="text-sm text-gray-900 dark:text-white">{metrics.totalPositions}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Trades</span>
                        <span className="text-sm text-gray-900 dark:text-white">{metrics.totalTrades}</span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Storage Usage
                    </h3>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Estimated Size</span>
                        <span className="text-sm text-gray-900 dark:text-white">~3.4 MB</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Growth Rate</span>
                        <span className="text-sm text-gray-900 dark:text-white">~34K rows/month</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Trading Tab */}
              {activeTab === 'trading' && (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Trading Engine
                    </h3>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Status</span>
                        <span className="text-sm text-yellow-500">⚠️ Simulated Only</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Open Positions</span>
                        <span className="text-sm text-gray-900 dark:text-white">{metrics.totalPositions}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Total Trades</span>
                        <span className="text-sm text-gray-900 dark:text-white">{metrics.totalTrades}</span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Trading Rules
                    </h3>
                    <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
                      <div>• SMA9 ↓ VWAP → Sell PUT</div>
                      <div>• SMA9 ↑ VWAP → Close PUT, Sell CALL</div>
                      <div>• 30min before close → Close all</div>
                      <div>• Take profit: 50% entry credit</div>
                      <div>• Stop loss: 200% entry credit</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Features Tab */}
              {activeTab === 'features' && (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Feature Flags Management
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                      Control which features are active in the application. This allows you to test new implementations
                      and decouple features as needed.
                    </p>
                    <button
                      onClick={() => setShowFeatureFlags(true)}
                      className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors"
                    >
                      Open Feature Flags Dashboard
                    </button>
                  </div>

                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Quick Feature Overview
                    </h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Real-time Data</span>
                          <span className={realTimeDataEnabled ? "text-green-500" : "text-red-500"}>
                            {realTimeDataEnabled ? "✓ Enabled" : "✗ Disabled"}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Trading Engine</span>
                          <span className={tradingEngineEnabled ? "text-green-500" : "text-red-500"}>
                            {tradingEngineEnabled ? "✓ Enabled" : "✗ Disabled"}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Chart Zoom</span>
                          <span className={chartZoomEnabled ? "text-green-500" : "text-red-500"}>
                            {chartZoomEnabled ? "✓ Enabled" : "✗ Disabled"}
                          </span>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Signals Dashboard</span>
                          <span className={signalsDashboardEnabled ? "text-green-500" : "text-red-500"}>
                            {signalsDashboardEnabled ? "✓ Enabled" : "✗ Disabled"}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Admin Panel</span>
                          <span className={adminPanelEnabled ? "text-green-500" : "text-red-500"}>
                            {adminPanelEnabled ? "✓ Enabled" : "✗ Disabled"}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Dark Mode</span>
                          <span className={darkModeEnabled ? "text-green-500" : "text-red-500"}>
                            {darkModeEnabled ? "✓ Enabled" : "✗ Disabled"}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600 dark:text-gray-400">Debug Mode</span>
                          <span className={debugModeEnabled ? "text-green-500" : "text-red-500"}>
                            {debugModeEnabled ? "✓ Enabled" : "✗ Disabled"}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Costs Tab */}
              {activeTab === 'costs' && (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Monthly Costs
                    </h3>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Lambda Compute</span>
                        <span className="text-sm text-gray-900 dark:text-white">${metrics.monthlyLambdaCost}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Storage & Logs</span>
                        <span className="text-sm text-gray-900 dark:text-white">${metrics.monthlyStorageCost}</span>
                      </div>
                      <div className="flex justify-between font-medium">
                        <span className="text-sm text-gray-900 dark:text-white">Total</span>
                        <span className="text-sm text-gray-900 dark:text-white">${metrics.monthlyTotalCost}</span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                      Free Tier Usage
                    </h3>
                    <div className="space-y-2">
                      <div>
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-600 dark:text-gray-400">Lambda Requests</span>
                          <span className="text-gray-900 dark:text-white">
                            {metrics.freeTierUsage.lambdaRequests.used.toLocaleString()} / {metrics.freeTierUsage.lambdaRequests.limit.toLocaleString()}
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                          <div 
                            className="bg-blue-600 h-2 rounded-full" 
                            style={{ width: `${Math.min(metrics.freeTierUsage.lambdaRequests.percentage, 100)}%` }}
                          ></div>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {metrics.freeTierUsage.lambdaRequests.percentage.toFixed(1)}% used
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-600 dark:text-gray-400">Lambda Compute</span>
                          <span className="text-gray-900 dark:text-white">
                            {metrics.freeTierUsage.lambdaCompute.used.toLocaleString()} / {metrics.freeTierUsage.lambdaCompute.limit.toLocaleString()} GB-sec
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                          <div 
                            className="bg-green-600 h-2 rounded-full" 
                            style={{ width: `${Math.min(metrics.freeTierUsage.lambdaCompute.percentage, 100)}%` }}
                          ></div>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {metrics.freeTierUsage.lambdaCompute.percentage.toFixed(1)}% used
                        </div>
                      </div>

                      <div>
                        <div className="flex justify-between text-xs">
                          <span className="text-gray-600 dark:text-gray-400">CloudWatch Logs</span>
                          <span className="text-gray-900 dark:text-white">
                            {metrics.freeTierUsage.cloudWatchLogs.used} / {metrics.freeTierUsage.cloudWatchLogs.limit} GB
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                          <div 
                            className="bg-yellow-600 h-2 rounded-full" 
                            style={{ width: `${Math.min(metrics.freeTierUsage.cloudWatchLogs.percentage, 100)}%` }}
                          ></div>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {metrics.freeTierUsage.cloudWatchLogs.percentage.toFixed(1)}% used
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>

        {/* Feature Flags Dashboard Modal */}
        <FeatureFlagsDashboard
          isOpen={showFeatureFlags}
          onClose={() => setShowFeatureFlags(false)}
        />
        </div>
      </div>
    </div>
  );
}
