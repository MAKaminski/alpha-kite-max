'use client';


interface TradingModeToggleProps {
  mode: 'automatic' | 'manual';
  onModeChange: (mode: 'automatic' | 'manual') => void;
  disabled?: boolean;
}

export default function TradingModeToggle({ 
  mode, 
  onModeChange, 
  disabled = false 
}: TradingModeToggleProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
      <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">
        🤖 Trading Mode
      </h3>
      
      <div className="space-y-2">
        <label className="flex items-center space-x-3 cursor-pointer">
          <input
            type="radio"
            name="tradingMode"
            value="automatic"
            checked={mode === 'automatic'}
            onChange={() => onModeChange('automatic')}
            disabled={disabled}
            className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
          />
          <div className="flex-1">
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
              Automatic
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              System trades automatically based on SMA9/VWAP strategy
            </div>
          </div>
        </label>
        
        <label className="flex items-center space-x-3 cursor-pointer">
          <input
            type="radio"
            name="tradingMode"
            value="manual"
            checked={mode === 'manual'}
            onChange={() => onModeChange('manual')}
            disabled={disabled}
            className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
          />
          <div className="flex-1">
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
              Manual
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">
              You control all trades through manual order entry
            </div>
          </div>
        </label>
      </div>
      
      {mode === 'automatic' && (
        <div className="mt-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded text-xs text-blue-700 dark:text-blue-300">
          ⚡ Automatic mode is active - system will execute trades based on strategy
        </div>
      )}
      
      {mode === 'manual' && (
        <div className="mt-3 p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded text-xs text-yellow-700 dark:text-yellow-300">
          🎯 Manual mode is active - use order entry to place trades
        </div>
      )}
    </div>
  );
}
