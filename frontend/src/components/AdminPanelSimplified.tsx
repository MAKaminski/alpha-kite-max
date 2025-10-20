'use client';

import { useFeatureFlag } from '@/lib/featureFlags';
import { formatToEST } from '@/lib/timezone';
import { useEffect, useState } from 'react';
import TokenManagement from './TokenManagement';

interface SystemMetrics {
  // Health
  supabaseConnected: boolean;
  schwabTokenValid: boolean;
  polygonApiConnected: boolean;
  lambdaSuccessRate: number;
  
  // Market
  isMarketOpen: boolean;
  currentTime: string;
  
  // AWS
  lambdaInvocations: number;
  lambdaErrors: number;
  lambdaDuration: number;
  awsRegion: string;
  
  // Data
  lastDataTimestamp: string;
  dataFreshness: number;
  totalDataPoints: number;
  databaseSize: string;
}

interface AdminPanelProps {
  isOpen: boolean;
  onClose: () => void;
  inline?: boolean; // when true, render inline inside page (no overlay)
}

export default function AdminPanelSimplified({ isOpen, onClose, inline = false }: AdminPanelProps) {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Feature flags
  const realTimeDataEnabled = useFeatureFlag('real-time-data');
  const tradingEngineEnabled = useFeatureFlag('paper-trading');
  const signalsDashboardEnabled = useFeatureFlag('signals-dashboard');
  const darkModeEnabled = useFeatureFlag('dark-mode');
  const debugModeEnabled = useFeatureFlag('debug-logs');

  useEffect(() => {
    if (!isOpen) return;

    const fetchMetrics = async () => {
      // Simulate metrics - in production, fetch from API
      setMetrics({
        supabaseConnected: true,
        schwabTokenValid: false, // Currently invalid
        polygonApiConnected: true, // Polygon.io configured
        lambdaSuccessRate: 0,
        isMarketOpen: true,
        currentTime: new Date().toISOString(),
        lambdaInvocations: 391,
        lambdaErrors: 391, // All failing
        lambdaDuration: 0.4,
        awsRegion: 'us-east-1',
        lastDataTimestamp: '2025-10-09T18:07:00Z',
        dataFreshness: 10080, // 7 days in minutes
        totalDataPoints: 2000,
        databaseSize: '180 KB'
      });
      setLoading(false);
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 30000); // Update every 30 seconds
    
    return () => clearInterval(interval);
  }, [isOpen]);

  if (!isOpen) return null;

  const getStatusColor = (status: boolean) => status ? 'text-green-500' : 'text-red-500';
  const getStatusIcon = (status: boolean) => status ? '✅' : '❌';

  const Container = inline ? 'div' : 'div';
  return (
    <Container className={inline ? "" : "fixed inset-0 bg-gray-50 dark:bg-gray-900 z-50 overflow-auto"}>
      <div className={inline ? "p-0" : "min-h-screen p-6"}>
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">System Administration</h1>
              <p className="text-gray-600 dark:text-gray-400 mt-1">Complete system overview - Updates every 30 seconds</p>
            </div>
            {!inline && (
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 text-3xl font-bold transition-colors"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {loading ? (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
            <div className="text-gray-500 dark:text-gray-400">Loading system metrics...</div>
          </div>
        ) : metrics ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* System Health */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <span className="text-2xl">🏥</span> System Health
              </h2>
              <div className="space-y-3">
                <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Supabase Database</span>
                  <span className={`text-sm font-bold ${getStatusColor(metrics.supabaseConnected)}`}>
                    {getStatusIcon(metrics.supabaseConnected)} Connected
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Schwab API Token</span>
                  <span className={`text-sm font-bold ${getStatusColor(metrics.schwabTokenValid)}`}>
                    {getStatusIcon(metrics.schwabTokenValid)} {metrics.schwabTokenValid ? 'Valid' : 'EXPIRED - RE-AUTH NEEDED'}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Polygon.io API</span>
                  <span className={`text-sm font-bold ${getStatusColor(metrics.polygonApiConnected)}`}>
                    {getStatusIcon(metrics.polygonApiConnected)} {metrics.polygonApiConnected ? 'Connected' : 'NOT CONFIGURED'}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Lambda Function</span>
                  <span className={`text-sm font-bold ${getStatusColor(metrics.lambdaSuccessRate > 50)}`}>
                    {metrics.lambdaSuccessRate}% Success Rate
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Market Status</span>
                  <span className={`text-sm font-bold ${getStatusColor(metrics.isMarketOpen)}`}>
                    {getStatusIcon(metrics.isMarketOpen)} {metrics.isMarketOpen ? 'Open' : 'Closed'}
                  </span>
                </div>
              </div>
            </div>

            {/* Data Pipeline */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <span className="text-2xl">⚡</span> Data Pipeline
              </h2>
              <div className="space-y-3">
                <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Today&apos;s Executions</span>
                  <span className="text-sm font-bold text-gray-900 dark:text-white">{metrics.lambdaInvocations}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Errors Today</span>
                  <span className={`text-sm font-bold ${metrics.lambdaErrors === 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {metrics.lambdaErrors}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Avg Duration</span>
                  <span className="text-sm font-bold text-gray-900 dark:text-white">{metrics.lambdaDuration}s</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">AWS Region</span>
                  <span className="text-sm font-bold text-gray-900 dark:text-white">{metrics.awsRegion}</span>
                </div>
              </div>
            </div>

            {/* Database Stats */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <span className="text-2xl">🗄️</span> Database
              </h2>
              <div className="space-y-3">
                <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Total Data Points</span>
                  <span className="text-sm font-bold text-gray-900 dark:text-white">{metrics.totalDataPoints.toLocaleString()}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Database Size</span>
                  <span className="text-sm font-bold text-gray-900 dark:text-white">{metrics.databaseSize}</span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Last Update</span>
                  <span className="text-sm font-bold text-gray-900 dark:text-white">
                    {metrics.lastDataTimestamp ? formatToEST(metrics.lastDataTimestamp, 'MMM dd, h:mm a') : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Data Freshness</span>
                  <span className={`text-sm font-bold ${metrics.dataFreshness <= 2 ? 'text-green-500' : 'text-red-500'}`}>
                    {metrics.dataFreshness > 1440 ? `${Math.floor(metrics.dataFreshness / 1440)} days ago` : `${metrics.dataFreshness} mins ago`}
                  </span>
                </div>
              </div>
            </div>

            {/* Feature Flags */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <span className="text-2xl">🔧</span> Active Features
              </h2>
              <div className="space-y-2">
                <div className="flex justify-between items-center p-2 bg-gray-50 dark:bg-gray-700 rounded text-sm">
                  <span className="text-gray-700 dark:text-gray-300">Real-time Data</span>
                  <span className={realTimeDataEnabled ? 'text-green-500 font-bold' : 'text-gray-400'}>
                    {realTimeDataEnabled ? '✅ ON' : '❌ OFF'}
                  </span>
                </div>
                <div className="flex justify-between items-center p-2 bg-gray-50 dark:bg-gray-700 rounded text-sm">
                  <span className="text-gray-700 dark:text-gray-300">Paper Trading</span>
                  <span className={tradingEngineEnabled ? 'text-green-500 font-bold' : 'text-gray-400'}>
                    {tradingEngineEnabled ? '✅ ON' : '❌ OFF'}
                  </span>
                </div>
                <div className="flex justify-between items-center p-2 bg-gray-50 dark:bg-gray-700 rounded text-sm">
                  <span className="text-gray-700 dark:text-gray-300">Signals Dashboard</span>
                  <span className={signalsDashboardEnabled ? 'text-green-500 font-bold' : 'text-gray-400'}>
                    {signalsDashboardEnabled ? '✅ ON' : '❌ OFF'}
                  </span>
                </div>
                <div className="flex justify-between items-center p-2 bg-gray-50 dark:bg-gray-700 rounded text-sm">
                  <span className="text-gray-700 dark:text-gray-300">Dark Mode</span>
                  <span className={darkModeEnabled ? 'text-green-500 font-bold' : 'text-gray-400'}>
                    {darkModeEnabled ? '✅ ON' : '❌ OFF'}
                  </span>
                </div>
                <div className="flex justify-between items-center p-2 bg-gray-50 dark:bg-gray-700 rounded text-sm">
                  <span className="text-gray-700 dark:text-gray-300">Debug Logs</span>
                  <span className={debugModeEnabled ? 'text-green-500 font-bold' : 'text-gray-400'}>
                    {debugModeEnabled ? '✅ ON' : '❌ OFF'}
                  </span>
                </div>
              </div>
              <button
                onClick={() => window.open('#', '_self')}
                className="mt-4 w-full py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors"
              >
                Manage All Features
              </button>
            </div>

            {/* Critical Alerts */}
            {(!metrics.schwabTokenValid || metrics.lambdaErrors > 10 || metrics.dataFreshness > 120) && (
              <div className="lg:col-span-2 bg-red-50 dark:bg-red-900/20 border-2 border-red-300 dark:border-red-800 rounded-lg p-6">
                <h2 className="text-xl font-bold text-red-900 dark:text-red-200 mb-4 flex items-center gap-2">
                  <span className="text-2xl">🚨</span> Critical Alerts
                </h2>
                <div className="space-y-3">
                  {!metrics.schwabTokenValid && (
                    <div className="bg-white dark:bg-gray-800 rounded p-4">
                      <h3 className="font-bold text-red-600 dark:text-red-400 mb-2">❌ Schwab Token Expired</h3>
                      <p className="text-sm text-gray-700 dark:text-gray-300 mb-3">
                        Lambda cannot fetch data. Re-authorization required.
                      </p>
                      <a
                        href="/admin/reauth"
                        target="_blank"
                        className="inline-block px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded transition-colors"
                      >
                        🔐 Re-Authorize Now
                      </a>
                    </div>
                  )}
                  {metrics.dataFreshness > 120 && (
                    <div className="bg-white dark:bg-gray-800 rounded p-4">
                      <h3 className="font-bold text-orange-600 dark:text-orange-400 mb-2">⚠️ Data Stale</h3>
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        Last data: {metrics.dataFreshness > 1440 ? `${Math.floor(metrics.dataFreshness / 1440)} days ago` : `${metrics.dataFreshness} minutes ago`}
                      </p>
                    </div>
                  )}
                  {metrics.lambdaErrors > 10 && (
                    <div className="bg-white dark:bg-gray-800 rounded p-4">
                      <h3 className="font-bold text-red-600 dark:text-red-400 mb-2">❌ Lambda Errors</h3>
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        {metrics.lambdaErrors} errors today - Check CloudWatch logs
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Quick Actions */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <span className="text-2xl">⚙️</span> Quick Actions
              </h2>
              <div className="space-y-3">
                <button
                  onClick={() => window.open('https://xwcauibwyxhsifnotnzz.supabase.co', '_blank')}
                  className="w-full py-3 px-4 bg-green-600 hover:bg-green-700 text-white text-sm font-semibold rounded transition-colors text-left"
                >
                  🗄️ Open Supabase Dashboard
                </button>
                <button
                  onClick={() => window.open('https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions/alpha-kite-real-time-streamer', '_blank')}
                  className="w-full py-3 px-4 bg-orange-600 hover:bg-orange-700 text-white text-sm font-semibold rounded transition-colors text-left"
                >
                  ⚡ View Lambda Logs
                </button>
                <button
                  onClick={() => window.open('/admin/reauth', '_blank')}
                  className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded transition-colors text-left"
                >
                  🔐 Re-Authorize Schwab
                </button>
                <button
                  onClick={() => window.location.reload()}
                  className="w-full py-3 px-4 bg-gray-600 hover:bg-gray-700 text-white text-sm font-semibold rounded transition-colors text-left"
                >
                  🔄 Refresh Dashboard
                </button>
              </div>
            </div>

            {/* System Info */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                <span className="text-2xl">📋</span> System Info
              </h2>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-gray-600 dark:text-gray-400">AWS Region:</span>
                  <span className="font-mono text-gray-900 dark:text-white">{metrics.awsRegion}</span>
                </div>
                <div className="flex justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-gray-600 dark:text-gray-400">Lambda Function:</span>
                  <span className="font-mono text-xs text-gray-900 dark:text-white">alpha-kite-real-time-streamer</span>
                </div>
                <div className="flex justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-gray-600 dark:text-gray-400">Database:</span>
                  <span className="font-mono text-xs text-gray-900 dark:text-white">xwcauibwyxhsifnotnzz</span>
                </div>
                <div className="flex justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded">
                  <span className="text-gray-600 dark:text-gray-400">Current Time (EST):</span>
                  <span className="font-mono text-gray-900 dark:text-white">
                    {formatToEST(metrics.currentTime, 'h:mm:ss a')}
                  </span>
                </div>
              </div>
            </div>

            {/* Token Management */}
            <div className="lg:col-span-2">
              <TokenManagement />
            </div>

          </div>
        ) : null}

      </div>
    </Container>
  );
}

