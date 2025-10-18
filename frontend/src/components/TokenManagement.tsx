'use client';

import { useState, useEffect } from 'react';
import { formatToEST } from '@/lib/timezone';

interface TokenInfo {
  access_token: string;
  refresh_token: string;
  expires_at: string;
  token_type: string;
  scope: string;
  last_refresh: string;
  refresh_count: number;
  is_valid: boolean;
  expires_in_seconds: number;
  refresh_in_seconds: number;
}

interface TokenManagementProps {
  className?: string;
}

export default function TokenManagement({ className = '' }: TokenManagementProps) {
  const [tokenInfo, setTokenInfo] = useState<TokenInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTokenInfo();
    const interval = setInterval(fetchTokenInfo, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchTokenInfo = async () => {
    try {
      const response = await fetch('/api/token-status');
      if (response.ok) {
        const data = await response.json();
        setTokenInfo(data);
        setError(null);
      } else {
        setError('Failed to fetch token status');
      }
    } catch {
      setError('Error fetching token status');
    } finally {
      setLoading(false);
    }
  };

  const refreshToken = async () => {
    setRefreshing(true);
    setError(null);
    
    try {
      const response = await fetch('/api/token-refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'refresh_token' }),
      });
      
      if (response.ok) {
        const data = await response.json();
        setTokenInfo(data);
        alert('Token refreshed successfully!');
      } else {
        const errorData = await response.json();
        setError(`Failed to refresh token: ${errorData.error}`);
      }
    } catch {
      setError('Error refreshing token');
    } finally {
      setRefreshing(false);
    }
  };

  const initiateReauth = () => {
    // Open OAuth URL in new tab
    const oauthUrl = 'https://api.schwabapi.com/v1/oauth/authorize?response_type=code&client_id=Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU&redirect_uri=https%3A//127.0.0.1%3A8182&state=reauth_' + Date.now();
    window.open(oauthUrl, '_blank');
    
    // Show instructions
    alert('OAuth window opened. After authorization, copy the callback URL and run:\n\npython3 simple_callback_processor.py "<CALLBACK_URL>"');
  };

  const getTokenStatusColor = (isValid: boolean, expiresInSeconds: number) => {
    if (!isValid) return 'text-red-500';
    if (expiresInSeconds < 300) return 'text-red-500'; // Less than 5 minutes
    if (expiresInSeconds < 1800) return 'text-yellow-500'; // Less than 30 minutes
    return 'text-green-500';
  };

  const getTokenStatusText = (isValid: boolean, expiresInSeconds: number) => {
    if (!isValid) return 'EXPIRED';
    if (expiresInSeconds < 300) return 'EXPIRING SOON';
    if (expiresInSeconds < 1800) return 'EXPIRES SOON';
    return 'VALID';
  };

  const formatTimeRemaining = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  if (loading) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 ${className}`}>
        <div className="text-center text-gray-500 dark:text-gray-400">
          Loading token information...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 ${className}`}>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <span className="text-2xl">🔐</span> Schwab Token Status
        </h2>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-4">
          <p className="text-red-600 dark:text-red-400 font-medium">Error: {error}</p>
          <button
            onClick={fetchTokenInfo}
            className="mt-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!tokenInfo) {
    return (
      <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 ${className}`}>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <span className="text-2xl">🔐</span> Schwab Token Status
        </h2>
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded p-4">
          <p className="text-yellow-600 dark:text-yellow-400 font-medium">No token information available</p>
          <button
            onClick={initiateReauth}
            className="mt-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded transition-colors"
          >
            Start Authorization
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 ${className}`}>
      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
        <span className="text-2xl">🔐</span> Schwab Token Management
      </h2>

      {/* Token Status Overview */}
      <div className="mb-6">
        <div className="flex justify-between items-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">Token Status</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {tokenInfo.is_valid ? 'Access token is valid' : 'Access token is invalid or expired'}
            </p>
          </div>
          <div className="text-right">
            <div className={`text-lg font-bold ${getTokenStatusColor(tokenInfo.is_valid, tokenInfo.expires_in_seconds)}`}>
              {getTokenStatusText(tokenInfo.is_valid, tokenInfo.expires_in_seconds)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              {tokenInfo.is_valid ? `Expires in ${formatTimeRemaining(tokenInfo.expires_in_seconds)}` : 'Expired'}
            </div>
          </div>
        </div>
      </div>

      {/* Detailed Token Information */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="space-y-3">
          <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
            <div className="text-sm font-medium text-gray-600 dark:text-gray-400">Access Token</div>
            <div className="text-sm font-mono text-gray-900 dark:text-white break-all">
              {tokenInfo.access_token.substring(0, 20)}...
            </div>
          </div>
          <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
            <div className="text-sm font-medium text-gray-600 dark:text-gray-400">Refresh Token</div>
            <div className="text-sm font-mono text-gray-900 dark:text-white break-all">
              {tokenInfo.refresh_token.substring(0, 20)}...
            </div>
          </div>
          <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
            <div className="text-sm font-medium text-gray-600 dark:text-gray-400">Token Type</div>
            <div className="text-sm text-gray-900 dark:text-white">{tokenInfo.token_type}</div>
          </div>
        </div>
        
        <div className="space-y-3">
          <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
            <div className="text-sm font-medium text-gray-600 dark:text-gray-400">Expires At</div>
            <div className="text-sm text-gray-900 dark:text-white">
              {formatToEST(tokenInfo.expires_at, 'MMM dd, yyyy h:mm:ss a')}
            </div>
          </div>
          <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
            <div className="text-sm font-medium text-gray-600 dark:text-gray-400">Last Refresh</div>
            <div className="text-sm text-gray-900 dark:text-white">
              {formatToEST(tokenInfo.last_refresh, 'MMM dd, h:mm:ss a')}
            </div>
          </div>
          <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded">
            <div className="text-sm font-medium text-gray-600 dark:text-gray-400">Refresh Count</div>
            <div className="text-sm text-gray-900 dark:text-white">{tokenInfo.refresh_count}</div>
          </div>
        </div>
      </div>

      {/* Refresh Token Status */}
      <div className="mb-6">
        <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <h4 className="font-semibold text-gray-900 dark:text-white mb-2">Refresh Token Status</h4>
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {tokenInfo.refresh_in_seconds > 0 
                ? `Valid for ${formatTimeRemaining(tokenInfo.refresh_in_seconds)}`
                : 'Refresh token expired - re-authorization required'
              }
            </span>
            <div className={`text-sm font-bold ${
              tokenInfo.refresh_in_seconds > 0 ? 'text-green-500' : 'text-red-500'
            }`}>
              {tokenInfo.refresh_in_seconds > 0 ? 'VALID' : 'EXPIRED'}
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-3">
        <button
          onClick={refreshToken}
          disabled={refreshing || tokenInfo.refresh_in_seconds <= 0}
          className={`px-4 py-2 text-sm font-semibold rounded transition-colors ${
            refreshing || tokenInfo.refresh_in_seconds <= 0
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-green-600 hover:bg-green-700 text-white'
          }`}
        >
          {refreshing ? 'Refreshing...' : '🔄 Refresh Token'}
        </button>
        
        <button
          onClick={initiateReauth}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded transition-colors"
        >
          🔐 Re-Authorize
        </button>
        
        <button
          onClick={fetchTokenInfo}
          className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm font-semibold rounded transition-colors"
        >
          🔄 Refresh Status
        </button>
      </div>

      {/* Instructions */}
      <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded">
        <h4 className="font-semibold text-blue-900 dark:text-blue-200 mb-2">Manual Re-Authorization</h4>
        <p className="text-sm text-blue-700 dark:text-blue-300 mb-2">
          If automatic refresh fails, use manual re-authorization:
        </p>
        <ol className="text-sm text-blue-700 dark:text-blue-300 list-decimal list-inside space-y-1">
          <li>Click &quot;Re-Authorize&quot; to open OAuth URL</li>
          <li>Complete authorization in the new tab</li>
          <li>Copy the callback URL from your browser</li>
          <li>Run: <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded">python3 simple_callback_processor.py &quot;&lt;CALLBACK_URL&gt;&quot;</code></li>
        </ol>
      </div>
    </div>
  );
}
