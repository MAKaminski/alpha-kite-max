'use client';

import React from 'react';
import { useDarkMode } from '@/contexts/DarkModeContext';

/**
 * Dark Mode Visual Inspection Test Page
 * 
 * This page displays all UI elements side-by-side to verify dark mode
 * is working correctly across all components.
 * 
 * Access at: http://localhost:3000/dark-mode-test
 */
export default function DarkModeTestPage() {
  const { isDarkMode, toggleDarkMode } = useDarkMode();

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
                Dark Mode Inspection Test
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Visual verification that dark mode is working correctly
              </p>
            </div>
            <button
              onClick={toggleDarkMode}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-colors"
            >
              Toggle Dark Mode
            </button>
          </div>
          
          <div className="mt-4 p-4 bg-gray-100 dark:bg-gray-900 rounded">
            <p className="text-sm text-gray-700 dark:text-gray-300">
              <strong>Current Mode:</strong> {isDarkMode ? '🌙 DARK MODE' : '☀️ LIGHT MODE'}
            </p>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              If dark mode is working, clicking the button should invert ALL colors below.
            </p>
          </div>
        </div>

        {/* Test Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Test 1: Basic Text Colors */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              ✅ Test 1: Text Colors
            </h3>
            <div className="space-y-2">
              <p className="text-gray-900 dark:text-white">
                ⬤ Primary text (should invert)
              </p>
              <p className="text-gray-700 dark:text-gray-300">
                ⬤ Secondary text (should lighten)
              </p>
              <p className="text-gray-600 dark:text-gray-400">
                ⬤ Tertiary text (should lighten more)
              </p>
              <p className="text-gray-500 dark:text-gray-500">
                ⬤ Muted text (stays gray)
              </p>
            </div>
          </div>

          {/* Test 2: Background Colors */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              ✅ Test 2: Backgrounds
            </h3>
            <div className="space-y-2">
              <div className="bg-white dark:bg-gray-800 p-2 rounded border border-gray-300 dark:border-gray-600">
                <span className="text-gray-900 dark:text-white text-sm">White → Dark Gray</span>
              </div>
              <div className="bg-gray-50 dark:bg-gray-900 p-2 rounded border border-gray-300 dark:border-gray-600">
                <span className="text-gray-900 dark:text-white text-sm">Gray-50 → Gray-900</span>
              </div>
              <div className="bg-gray-100 dark:bg-gray-800 p-2 rounded border border-gray-300 dark:border-gray-600">
                <span className="text-gray-900 dark:text-white text-sm">Gray-100 → Gray-800</span>
              </div>
            </div>
          </div>

          {/* Test 3: Input Fields */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              ✅ Test 3: Input Fields
            </h3>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Text input (should invert)"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder:text-gray-500 dark:placeholder:text-gray-400"
              />
              <select className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white">
                <option>Select (should invert)</option>
                <option>Option 1</option>
                <option>Option 2</option>
              </select>
              <input
                type="date"
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
            </div>
          </div>

          {/* Test 4: Buttons */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              ✅ Test 4: Buttons
            </h3>
            <div className="space-y-2">
              <button className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-semibold">
                Primary Button (stays blue)
              </button>
              <button className="w-full px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded hover:bg-gray-300 dark:hover:bg-gray-600">
                Secondary Button (should invert)
              </button>
              <button className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white rounded hover:bg-gray-50 dark:hover:bg-gray-700">
                Outline Button (should invert)
              </button>
            </div>
          </div>

          {/* Test 5: Metric Cards */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              ✅ Test 5: Metric Cards
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-blue-50 dark:bg-blue-900/20 rounded p-3 border border-blue-100 dark:border-blue-800">
                <div className="text-xs text-blue-600 dark:text-blue-400">Ticker</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">QQQ</div>
              </div>
              <div className="bg-green-50 dark:bg-green-900/20 rounded p-3 border border-green-100 dark:border-green-800">
                <div className="text-xs text-green-600 dark:text-green-400">SMA9</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">$600</div>
              </div>
              <div className="bg-purple-50 dark:bg-purple-900/20 rounded p-3 border border-purple-100 dark:border-purple-800">
                <div className="text-xs text-purple-600 dark:text-purple-400">VWAP</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">$601</div>
              </div>
              <div className="bg-red-50 dark:bg-red-900/20 rounded p-3 border border-red-100 dark:border-red-800">
                <div className="text-xs text-red-600 dark:text-red-400">Crosses</div>
                <div className="text-lg font-bold text-gray-900 dark:text-white">3</div>
              </div>
            </div>
          </div>

          {/* Test 6: Data Table */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              ✅ Test 6: Table
            </h3>
            <table className="w-full text-sm">
              <thead className="bg-gray-50 dark:bg-gray-900">
                <tr>
                  <th className="px-3 py-2 text-left text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                    Time
                  </th>
                  <th className="px-3 py-2 text-left text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-700">
                    Price
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <td className="px-3 py-2 text-gray-900 dark:text-white">10:00 AM</td>
                  <td className="px-3 py-2 text-gray-900 dark:text-white">$600.25</td>
                </tr>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <td className="px-3 py-2 text-gray-900 dark:text-white">10:01 AM</td>
                  <td className="px-3 py-2 text-gray-900 dark:text-white">$600.50</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Test 7: Alert/Status Messages */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              ✅ Test 7: Alerts
            </h3>
            <div className="space-y-3">
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-3">
                <p className="text-sm text-blue-800 dark:text-blue-300">
                  ℹ️ Info message (should invert)
                </p>
              </div>
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded p-3">
                <p className="text-sm text-yellow-800 dark:text-yellow-300">
                  ⚠️ Warning message (should invert)
                </p>
              </div>
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded p-3">
                <p className="text-sm text-green-800 dark:text-green-300">
                  ✅ Success message (should invert)
                </p>
              </div>
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-3">
                <p className="text-sm text-red-800 dark:text-red-300">
                  ❌ Error message (should invert)
                </p>
              </div>
            </div>
          </div>

          {/* Test 8: Terminal/Code Block */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 border border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              ✅ Test 8: Terminal Display
            </h3>
            <div className="bg-black dark:bg-gray-950 rounded p-4 font-mono text-sm">
              <div className="text-green-400 mb-1">$ python trading_main.py</div>
              <div className="text-gray-400">Starting trading bot...</div>
              <div className="text-blue-400">✓ Connected to Schwab API</div>
              <div className="text-yellow-400">⚠ Using DEMO MODE</div>
            </div>
          </div>
        </div>

        {/* Inspection Checklist */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-200 dark:border-gray-700">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
            🔍 Inspection Checklist
          </h2>
          
          <div className="space-y-3">
            <div className="bg-gray-50 dark:bg-gray-900 rounded p-4">
              <h4 className="font-semibold text-gray-900 dark:text-white mb-2">
                When Dark Mode is ON, you should see:
              </h4>
              <ul className="space-y-1 text-sm text-gray-700 dark:text-gray-300">
                <li>✅ Background: Nearly black (not white)</li>
                <li>✅ Primary text: White (not black)</li>
                <li>✅ Secondary text: Light gray (not dark gray)</li>
                <li>✅ Input fields: Dark background, white text</li>
                <li>✅ Buttons: Dark backgrounds with white text</li>
                <li>✅ Borders: Dark gray (not light gray)</li>
                <li>✅ Metric cards: Dark backgrounds with colored text</li>
                <li>✅ Tables: Dark rows, light text</li>
                <li>✅ Alerts: Dark backgrounds, light colored text</li>
                <li>✅ Terminal: Black background (stays black)</li>
              </ul>
            </div>

            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded p-4">
              <h4 className="font-semibold text-yellow-900 dark:text-yellow-300 mb-2">
                ⚠️ Common Dark Mode Issues
              </h4>
              <ul className="space-y-1 text-sm text-yellow-800 dark:text-yellow-400">
                <li><strong>Only header changes:</strong> Check if DarkModeProvider wraps entire app</li>
                <li><strong>Text still black:</strong> Missing dark:text-white on elements</li>
                <li><strong>White backgrounds:</strong> Missing dark:bg-gray-800 on containers</li>
                <li><strong>Hard to read:</strong> Insufficient contrast in dark mode</li>
                <li><strong>Flickering:</strong> LocalStorage not persisting darkMode state</li>
              </ul>
            </div>

            <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded p-4">
              <h4 className="font-semibold text-green-900 dark:text-green-300 mb-2">
                ✅ If All Tests Pass
              </h4>
              <p className="text-sm text-green-800 dark:text-green-400">
                Every element above should have inverted colors when toggling dark mode.
                If ANY element doesn't change, dark mode has incomplete coverage.
              </p>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
          <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-300 mb-2">
            🛠️ Quick Fix Commands
          </h3>
          <div className="space-y-2 text-sm text-blue-800 dark:text-blue-400">
            <p><strong>If dark mode not working:</strong></p>
            <code className="block bg-blue-100 dark:bg-blue-950 p-2 rounded text-xs font-mono">
              Check: app/layout.tsx has &lt;DarkModeProvider&gt; wrapping children
            </code>
            <code className="block bg-blue-100 dark:bg-blue-950 p-2 rounded text-xs font-mono">
              Check: All components use dark: prefixed classes
            </code>
            <code className="block bg-blue-100 dark:bg-blue-950 p-2 rounded text-xs font-mono">
              Check: tailwind.config.ts has darkMode: 'class'
            </code>
          </div>
        </div>

        {/* Back Link */}
        <div className="mt-6 text-center">
          <a
            href="/"
            className="inline-block px-6 py-3 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
          >
            ← Back to Dashboard
          </a>
        </div>
      </div>
    </div>
  );
}

