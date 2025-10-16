import React, { useState, useEffect } from 'react';

interface TokenStatus {
  has_token: boolean;
  has_access_token: boolean;
  has_refresh_token: boolean;
  expires_status: 'valid' | 'expires_soon' | 'expired';
  expires_at: number;
  time_until_expiry: number;
  can_refresh: boolean;
}

interface TokenRefreshProps {
  className?: string;
}

export const TokenRefresh: React.FC<TokenRefreshProps> = ({ className = '' }) => {
  const [tokenStatus, setTokenStatus] = useState<TokenStatus | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkTokenStatus = async () => {
    setIsChecking(true);
    setError(null);
    
    try {
      // Call our token refresh Lambda function
      const response = await fetch('/api/token-refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'check_token_status' }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setTokenStatus(data);
      setLastChecked(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check token status');
    } finally {
      setIsChecking(false);
    }
  };

  const refreshToken = async () => {
    setIsRefreshing(true);
    setError(null);
    
    try {
      const response = await fetch('/api/token-refresh', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: 'refresh_token' }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.success) {
        // Refresh successful, check status again
        await checkTokenStatus();
      } else {
        throw new Error(data.message || 'Token refresh failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refresh token');
    } finally {
      setIsRefreshing(false);
    }
  };

  const formatTimeUntilExpiry = (seconds: number) => {
    if (seconds <= 0) return 'Expired';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'valid': return 'text-green-600';
      case 'expires_soon': return 'text-yellow-600';
      case 'expired': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'valid': return '✅';
      case 'expires_soon': return '⚠️';
      case 'expired': return '❌';
      default: return '❓';
    }
  };

  // Check token status on mount
  useEffect(() => {
    checkTokenStatus();
  }, []);

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          🔐 Schwab Token Status
        </h3>
        <button
          onClick={checkTokenStatus}
          disabled={isChecking}
          className="px-3 py-1 text-sm bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded hover:bg-blue-200 dark:hover:bg-blue-800 disabled:opacity-50"
        >
          {isChecking ? 'Checking...' : 'Refresh Status'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 rounded">
          ❌ {error}
        </div>
      )}

      {tokenStatus && (
        <div className="space-y-3">
          {/* Token Status */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Token Status:
            </span>
            <span className={`text-sm font-semibold ${getStatusColor(tokenStatus.expires_status)}`}>
              {getStatusIcon(tokenStatus.expires_status)} {tokenStatus.expires_status.replace('_', ' ')}
            </span>
          </div>

          {/* Time Until Expiry */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Expires In:
            </span>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {formatTimeUntilExpiry(tokenStatus.time_until_expiry)}
            </span>
          </div>

          {/* Token Components */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Access Token:
              </span>
              <span className={`text-sm ${tokenStatus.has_access_token ? 'text-green-600' : 'text-red-600'}`}>
                {tokenStatus.has_access_token ? '✅ Present' : '❌ Missing'}
              </span>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Refresh Token:
              </span>
              <span className={`text-sm ${tokenStatus.has_refresh_token ? 'text-green-600' : 'text-red-600'}`}>
                {tokenStatus.has_refresh_token ? '✅ Present' : '❌ Missing'}
              </span>
            </div>
          </div>

          {/* Refresh Button */}
          <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={refreshToken}
              disabled={!tokenStatus.can_refresh || isRefreshing}
              className={`w-full px-4 py-2 rounded font-medium ${
                tokenStatus.can_refresh && !isRefreshing
                  ? 'bg-green-600 hover:bg-green-700 text-white'
                  : 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'
              }`}
            >
              {isRefreshing ? '🔄 Refreshing...' : '🔄 Refresh Token'}
            </button>
            
            {!tokenStatus.can_refresh && (
              <p className="mt-2 text-xs text-red-600 dark:text-red-400">
                Cannot refresh: {tokenStatus.expires_status === 'expired' ? 'Token expired' : 'No refresh token available'}
              </p>
            )}
          </div>

          {/* Last Checked */}
          {lastChecked && (
            <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
              Last checked: {lastChecked.toLocaleTimeString()}
            </div>
          )}
        </div>
      )}

      {/* Help Text */}
      <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded text-sm text-blue-700 dark:text-blue-300">
        <p className="font-medium">💡 Token Refresh Info:</p>
        <ul className="mt-1 space-y-1 text-xs">
          <li>• Schwab tokens expire every 7 days</li>
          <li>• Click "Refresh Token" to extend for another 7 days</li>
          <li>• If refresh fails, manual re-authentication is required</li>
          <li>• Token refresh updates both local and AWS Secrets Manager</li>
        </ul>
      </div>
    </div>
  );
};
