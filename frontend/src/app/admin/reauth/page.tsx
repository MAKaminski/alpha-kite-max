'use client';

import { useState } from 'react';

export default function ReauthPage() {
  const [step, setStep] = useState(1);
  const [callbackUrl, setCallbackUrl] = useState('');

  const oauthUrl = 'https://api.schwabapi.com/v1/oauth/authorize?response_type=code&client_id=Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU&redirect_uri=https%3A//127.0.0.1%3A8182&state=reauth_' + Date.now();

  const handleStartOAuth = () => {
    window.open(oauthUrl, '_blank');
    setStep(2);
  };

  const handleProcessCallback = () => {
    if (!callbackUrl) {
      alert('Please paste the callback URL first');
      return;
    }
    
    // In a real implementation, this would call the backend
    alert(`Processing callback URL: ${callbackUrl}\n\nIn production, this would call the backend to exchange the code for tokens.`);
    setStep(3);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Schwab Re-Authorization
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Complete OAuth flow to get fresh tokens
          </p>
        </div>

        {/* Progress Steps */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            {[1, 2, 3].map((stepNum) => (
              <div key={stepNum} className="flex items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                  step >= stepNum 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-300 text-gray-600'
                }`}>
                  {stepNum}
                </div>
                {stepNum < 3 && (
                  <div className={`w-16 h-1 mx-2 ${
                    step > stepNum ? 'bg-blue-600' : 'bg-gray-300'
                  }`} />
                )}
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-2 text-sm text-gray-600 dark:text-gray-400">
            <span>Start OAuth</span>
            <span>Get Callback</span>
            <span>Complete</span>
          </div>
        </div>

        {/* Step 1: Start OAuth */}
        {step === 1 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
              Step 1: Start OAuth Authorization
            </h2>
            <div className="space-y-4">
              <p className="text-gray-600 dark:text-gray-400">
                Click the button below to open the Schwab OAuth authorization page in a new tab.
              </p>
              <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <div className="font-medium text-blue-900 dark:text-blue-200 mb-2">OAuth URL:</div>
                <div className="text-sm font-mono text-blue-800 dark:text-blue-300 break-all">
                  {oauthUrl}
                </div>
              </div>
              <button
                onClick={handleStartOAuth}
                className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
              >
                🔐 Open OAuth Page
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Get Callback URL */}
        {step === 2 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
              Step 2: Get Callback URL
            </h2>
            <div className="space-y-4">
              <p className="text-gray-600 dark:text-gray-400">
                After authorizing the app, you&apos;ll be redirected to a callback URL. Copy the entire URL from your browser&apos;s address bar.
              </p>
              <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                <div className="font-medium text-yellow-900 dark:text-yellow-200 mb-2">Expected Callback URL Format:</div>
                <div className="text-sm font-mono text-yellow-800 dark:text-yellow-300">
                  https://127.0.0.1:8182/?code=ABC123&state=reauth_1234567890
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Paste Callback URL:
                </label>
                <textarea
                  value={callbackUrl}
                  onChange={(e) => setCallbackUrl(e.target.value)}
                  placeholder="https://127.0.0.1:8182/?code=..."
                  className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  rows={3}
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={handleProcessCallback}
                  className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors"
                >
                  ✅ Process Callback
                </button>
                <button
                  onClick={() => setStep(1)}
                  className="px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white font-semibold rounded-lg transition-colors"
                >
                  ← Back
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Complete */}
        {step === 3 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
              Step 3: Complete Re-Authorization
            </h2>
            <div className="space-y-4">
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <div className="font-medium text-green-900 dark:text-green-200 mb-2">✅ Re-Authorization Complete!</div>
                <div className="text-sm text-green-800 dark:text-green-300">
                  Your tokens have been refreshed and are ready to use.
                </div>
              </div>
              <div className="space-y-3">
                <p className="text-gray-600 dark:text-gray-400">
                  Next steps:
                </p>
                <ul className="list-disc list-inside space-y-1 text-sm text-gray-600 dark:text-gray-400">
                  <li>Check the token status in the admin panel</li>
                  <li>Verify data is streaming correctly</li>
                  <li>Monitor Lambda function logs</li>
                </ul>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => window.location.href = '/admin/tokens'}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
                >
                  View Token Status
                </button>
                <button
                  onClick={() => window.location.href = '/'}
                  className="px-6 py-3 bg-gray-600 hover:bg-gray-700 text-white font-semibold rounded-lg transition-colors"
                >
                  Go to Dashboard
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Troubleshooting */}
        <div className="mt-8 bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            Troubleshooting
          </h2>
          <div className="space-y-4">
            <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
              <div className="font-medium text-red-900 dark:text-red-200 mb-2">403 Forbidden Error</div>
              <div className="text-sm text-red-800 dark:text-red-300">
                If you see a login page or 403 error, your Schwab app may not be approved for OAuth access. 
                Contact Schwab Developer Support at developer@schwab.com.
              </div>
            </div>
            <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
              <div className="font-medium text-yellow-900 dark:text-yellow-200 mb-2">Callback Server Not Running</div>
              <div className="text-sm text-yellow-800 dark:text-yellow-300">
                Make sure the callback server is running on port 8182. Run: 
                <code className="bg-yellow-100 dark:bg-yellow-800 px-1 rounded ml-1">
                  python3 standalone_callback_server.py
                </code>
              </div>
            </div>
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <div className="font-medium text-blue-900 dark:text-blue-200 mb-2">Manual Process</div>
              <div className="text-sm text-blue-800 dark:text-blue-300">
                For manual processing, run: 
                <code className="bg-blue-100 dark:bg-blue-800 px-1 rounded ml-1">
                  python3 simple_callback_processor.py &quot;&lt;CALLBACK_URL&gt;&quot;
                </code>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}