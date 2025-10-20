'use client';

import AdminPanelSimplified from '@/components/AdminPanelSimplified';
import { useEffect, useState } from 'react';

export default function TokenManagementPage() {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center text-gray-500 dark:text-gray-400">
            Loading token management...
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Token Management
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Monitor and manage Schwab API authentication tokens
          </p>
        </div>

        {/* Full Admin Panel Inline */}
        <AdminPanelSimplified isOpen onClose={()=>{}} inline />

        {/* Additional Information */}
        <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Token Lifecycle */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
              Token Lifecycle
            </h2>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <div>
                  <div className="font-medium text-gray-900 dark:text-white">Access Token</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    Valid for 7 days, used for API calls
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                <div>
                  <div className="font-medium text-gray-900 dark:text-white">Refresh Token</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    Valid for 90 days, used to get new access tokens
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                <div>
                  <div className="font-medium text-gray-900 dark:text-white">Auto-Refresh</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    Lambda automatically refreshes before expiration
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Troubleshooting */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
              Troubleshooting
            </h2>
            <div className="space-y-3 text-sm">
              <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded">
                <div className="font-medium text-red-800 dark:text-red-200">Token Expired</div>
                <div className="text-red-600 dark:text-red-300">
                  Click &quot;Re-Authorize&quot; to get new tokens
                </div>
              </div>
              <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded">
                <div className="font-medium text-yellow-800 dark:text-yellow-200">Refresh Failed</div>
                <div className="text-yellow-600 dark:text-yellow-300">
                  Manual re-authorization may be required
                </div>
              </div>
              <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded">
                <div className="font-medium text-blue-800 dark:text-blue-200">403 Forbidden</div>
                <div className="text-blue-600 dark:text-blue-300">
                  Contact Schwab Developer Support for OAuth approval
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            Quick Actions
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={() => window.open('https://developer.schwab.com/dashboard', '_blank')}
              className="p-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-left"
            >
              <div className="font-semibold">Schwab Developer Portal</div>
              <div className="text-sm opacity-90">Check app status and settings</div>
            </button>
            <button
              onClick={() => window.open('https://console.aws.amazon.com/secretsmanager/home?region=us-east-1#/secret?name=schwab-api-token-prod', '_blank')}
              className="p-4 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors text-left"
            >
              <div className="font-semibold">AWS Secrets Manager</div>
              <div className="text-sm opacity-90">View stored tokens</div>
            </button>
            <button
              onClick={() => window.open('https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Faws$252Flambda$252Falpha-kite-real-time-streamer', '_blank')}
              className="p-4 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors text-left"
            >
              <div className="font-semibold">Lambda Logs</div>
              <div className="text-sm opacity-90">Check token refresh logs</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
