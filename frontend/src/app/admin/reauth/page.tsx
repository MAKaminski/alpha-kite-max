'use client';

import { useState } from 'react';

export default function ReauthPage() {
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const handleReauth = async () => {
    setStatus('loading');
    setMessage('Initiating re-authorization...');

    try {
      // Call backend endpoint that generates auth URL
      const response = await fetch('/api/schwab/reauth', {
        method: 'POST',
      });

      const data = await response.json();

      if (data.authUrl) {
        setMessage('Opening authorization page...');
        // Open in new window
        window.open(data.authUrl, '_blank');
        setStatus('success');
        setMessage('Please complete authorization in the new window, then check back here.');
      } else {
        setStatus('error');
        setMessage('Failed to generate authorization URL');
      }
    } catch (error) {
      setStatus('error');
      setMessage(`Error: ${error}`);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-8">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            Schwab API Re-Authorization
          </h1>
          
          <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 mb-6">
            <div className="flex items-start">
              <span className="text-2xl mr-3">⚠️</span>
              <div>
                <h3 className="font-semibold text-yellow-900 dark:text-yellow-200 mb-1">
                  Token Refresh Required
                </h3>
                <p className="text-sm text-yellow-800 dark:text-yellow-300">
                  Your Schwab API refresh token has expired. This happens every 7-90 days
                  depending on your app configuration. Click below to re-authorize.
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-4 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              What Will Happen:
            </h2>
            <ol className="list-decimal list-inside space-y-2 text-gray-700 dark:text-gray-300">
              <li>A new window opens with Schwab authorization page</li>
              <li>You click &quot;Allow&quot; to authorize the app (no login needed if already logged in)</li>
              <li>The window redirects and closes</li>
              <li>New token is automatically saved</li>
              <li>Lambda function resumes data collection</li>
            </ol>
          </div>

          <button
            onClick={handleReauth}
            disabled={status === 'loading'}
            className={`w-full py-4 px-6 rounded-lg font-semibold text-white transition-colors ${
              status === 'loading'
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {status === 'loading' ? '⏳ Opening browser...' : '🔐 Re-Authorize Schwab API'}
          </button>

          {status !== 'idle' && (
            <div className={`mt-4 p-4 rounded-lg ${
              status === 'success' ? 'bg-green-50 dark:bg-green-900/20 text-green-800 dark:text-green-200' :
              status === 'error' ? 'bg-red-50 dark:bg-red-900/20 text-red-800 dark:text-red-200' :
              'bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200'
            }`}>
              <p className="text-sm">{message}</p>
            </div>
          )}

          <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
              Why is this needed?
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              For security, Schwab requires periodic re-authorization. The refresh token
              expires after 7-90 days, and there&apos;s no automated way to renew it without
              user interaction. This is an OAuth 2.0 security requirement.
            </p>
          </div>

          <div className="mt-4">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
              How to reduce frequency:
            </h3>
            <ul className="text-sm text-gray-600 dark:text-gray-400 list-disc list-inside space-y-1">
              <li>Configure your Schwab app for maximum token lifetime (90 days)</li>
              <li>Set up email alerts so you know when re-auth is needed</li>
              <li>Bookmark this page for quick access</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

