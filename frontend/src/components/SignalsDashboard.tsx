'use client';

import { Cross } from '@/lib/crossDetection';
import { formatToEST } from '@/lib/timezone';

interface SignalsDashboardProps {
  crosses: Cross[];
  selectedDate: Date;
}

export default function SignalsDashboard({ crosses, selectedDate }: SignalsDashboardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Signals
        </h2>
        <div className="text-sm text-gray-600 dark:text-gray-400">
          {formatToEST(selectedDate, 'MMM dd, yyyy')}
        </div>
      </div>

      {crosses.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          No crosses detected for this date
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                <th className="text-left py-3 px-4 font-medium text-gray-700 dark:text-gray-300">
                  Time (EST)
                </th>
                <th className="text-right py-3 px-4 font-medium text-gray-700 dark:text-gray-300">
                  Price
                </th>
                <th className="text-right py-3 px-4 font-medium text-gray-700 dark:text-gray-300">
                  SMA9
                </th>
                <th className="text-right py-3 px-4 font-medium text-gray-700 dark:text-gray-300">
                  VWAP
                </th>
                <th className="text-center py-3 px-4 font-medium text-gray-700 dark:text-gray-300">
                  Direction
                </th>
              </tr>
            </thead>
            <tbody>
              {crosses.map((cross, idx) => (
                <tr
                  key={idx}
                  className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                >
                  <td className="py-3 px-4 font-mono text-gray-900 dark:text-white">
                    {formatToEST(cross.timestamp, 'h:mm:ss a')}
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-gray-900 dark:text-white">
                    ${cross.price.toFixed(2)}
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-green-600 dark:text-green-400">
                    ${cross.sma9.toFixed(2)}
                  </td>
                  <td className="py-3 px-4 text-right font-mono text-purple-600 dark:text-purple-400">
                    ${cross.vwap.toFixed(2)}
                  </td>
                  <td className="py-3 px-4 text-center">
                    {cross.direction === 'up' ? (
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300">
                        ↑ Up
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300">
                        ↓ Down
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

