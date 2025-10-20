'use client';

import { useState } from 'react';

interface OrderPreview {
  ticker: string;
  option_symbol: string;
  option_type: 'CALL' | 'PUT';
  strike_price: number;
  expiration_date: string;
  action: 'SELL_TO_OPEN' | 'BUY_TO_CLOSE';
  contracts: number;
  estimated_price: number;
  estimated_credit_debit: number;
  current_equity_price: number;
  rationale: string;
}

interface ManualOrderEntryProps {
  ticker?: string;
  currentPrice?: number;
  recentPriceAction?: {
    sma9: number;
    vwap: number;
    trend: 'bullish' | 'bearish' | 'neutral';
  };
  hasOpenPosition?: boolean;
  onSubmit?: (order: OrderPreview) => void;
}

export default function ManualOrderEntry({
  ticker = 'QQQ',
  currentPrice = 0,
  recentPriceAction,
  hasOpenPosition = false,
  onSubmit
}: ManualOrderEntryProps) {
  const [orderPreview, setOrderPreview] = useState<OrderPreview | null>(null);
  const [contracts, setContracts] = useState<number>(10);
  const [isLoading, setIsLoading] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [orderStatus, setOrderStatus] = useState<string | null>(null);
  const [orderId, setOrderId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Auto-populate order based on current market conditions
  const populateOrder = async (action: 'SELL_TO_OPEN' | 'BUY_TO_CLOSE') => {
    setIsLoading(true);
    
    try {
      // Call API to get recommended 0DTE option
      const response = await fetch('/api/get-recommended-option', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker,
          action,
          current_price: currentPrice,
          price_action: recentPriceAction,
          contracts
        })
      });

      if (response.ok) {
        const data = await response.json();
        setOrderPreview(data);
        setShowConfirmation(true);
      } else {
        console.error('Failed to get order recommendation');
      }
    } catch (error) {
      console.error('Error fetching order recommendation:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!orderPreview) return;

    setIsSubmitting(true);
    setOrderStatus('SUBMITTING');

    try {
      const response = await fetch('/api/submit-order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...orderPreview,
          mode: 'manual'
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Order submitted successfully:', result);
        
        setOrderId(result.order.order_id);
        setOrderStatus('PENDING');
        
        // Start polling for order status
        pollOrderStatus(result.order.order_id);
        
        // Call parent callback
        if (onSubmit) {
          onSubmit(orderPreview);
        }
      } else {
        const error = await response.json();
        console.error('Order submission failed:', error);
        setOrderStatus('FAILED');
        alert(`Order failed: ${error.error}`);
      }
    } catch (error) {
      console.error('Error submitting order:', error);
      setOrderStatus('FAILED');
      alert('Failed to submit order');
    } finally {
      setIsSubmitting(false);
    }
  };

  const pollOrderStatus = async (orderId: string) => {
    const maxAttempts = 10;
    let attempts = 0;

    const poll = async () => {
      try {
        const response = await fetch(`/api/order-status?order_id=${orderId}`);
        if (response.ok) {
          const result = await response.json();
          setOrderStatus(result.order.status);
          
          if (result.order.status === 'FILLED' || result.order.status === 'FAILED') {
            // Order completed, stop polling
            return;
          }
        }
        
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 2000); // Poll every 2 seconds
        } else {
          setOrderStatus('TIMEOUT');
        }
      } catch (error) {
        console.error('Error polling order status:', error);
        setOrderStatus('ERROR');
      }
    };

    // Start polling after a short delay
    setTimeout(poll, 1000);
  };

  const handleCancel = () => {
    setOrderPreview(null);
    setShowConfirmation(false);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 border border-gray-200 dark:border-gray-700">
      <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-2">
        📝 Manual Order Entry
      </h3>

      {/* Market Context */}
      <div className="mb-3 p-2 bg-gray-50 dark:bg-gray-700 rounded text-xs">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className="font-medium text-gray-600 dark:text-gray-400">Current Price:</span>
            <span className="ml-1 text-gray-800 dark:text-gray-200">${currentPrice.toFixed(2)}</span>
          </div>
          <div>
            <span className="font-medium text-gray-600 dark:text-gray-400">Trend:</span>
            <span className={`ml-1 font-semibold ${
              recentPriceAction?.trend === 'bullish' ? 'text-green-600' :
              recentPriceAction?.trend === 'bearish' ? 'text-red-600' :
              'text-gray-600'
            }`}>
              {recentPriceAction?.trend?.toUpperCase() || 'N/A'}
            </span>
          </div>
          <div>
            <span className="font-medium text-gray-600 dark:text-gray-400">SMA9:</span>
            <span className="ml-1 text-gray-800 dark:text-gray-200">
              ${recentPriceAction?.sma9?.toFixed(2) || 'N/A'}
            </span>
          </div>
          <div>
            <span className="font-medium text-gray-600 dark:text-gray-400">VWAP:</span>
            <span className="ml-1 text-gray-800 dark:text-gray-200">
              ${recentPriceAction?.vwap?.toFixed(2) || 'N/A'}
            </span>
          </div>
        </div>
      </div>

      {/* Position Status */}
      <div className="mb-3 p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium text-blue-800 dark:text-blue-300">
            Open Position:
          </span>
          <span className={`font-semibold ${hasOpenPosition ? 'text-green-600' : 'text-gray-500'}`}>
            {hasOpenPosition ? '✓ YES' : '✗ NO'}
          </span>
        </div>
      </div>

      {/* Contract Size Input */}
      <div className="mb-3">
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
          Contracts:
        </label>
        <input
          type="number"
          value={contracts}
          onChange={(e) => setContracts(parseInt(e.target.value) || 1)}
          min="1"
          max="100"
          className="w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200"
        />
      </div>

      {/* Action Buttons */}
      {!showConfirmation && (
        <div className="grid grid-cols-2 gap-2 mb-3">
          <button
            onClick={() => populateOrder('SELL_TO_OPEN')}
            disabled={isLoading || hasOpenPosition}
            className={`py-2 px-3 text-xs font-semibold rounded transition-colors ${
              isLoading || hasOpenPosition
                ? 'bg-gray-300 dark:bg-gray-600 text-gray-500 cursor-not-allowed'
                : 'bg-green-600 hover:bg-green-700 text-white'
            }`}
          >
            {isLoading ? '⏳ Loading...' : '📤 SELL TO OPEN'}
          </button>
          <button
            onClick={() => populateOrder('BUY_TO_CLOSE')}
            disabled={isLoading || !hasOpenPosition}
            className={`py-2 px-3 text-xs font-semibold rounded transition-colors ${
              isLoading || !hasOpenPosition
                ? 'bg-gray-300 dark:bg-gray-600 text-gray-500 cursor-not-allowed'
                : 'bg-red-600 hover:bg-red-700 text-white'
            }`}
          >
            {isLoading ? '⏳ Loading...' : '📥 BUY TO CLOSE'}
          </button>
        </div>
      )}

      {/* Order Status */}
      {orderStatus && (
        <div className="mb-3 p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-blue-800 dark:text-blue-300">
              Order Status:
            </span>
            <span className={`font-semibold ${
              orderStatus === 'FILLED' ? 'text-green-600' :
              orderStatus === 'PENDING' || orderStatus === 'SUBMITTING' ? 'text-yellow-600' :
              orderStatus === 'FAILED' || orderStatus === 'ERROR' || orderStatus === 'TIMEOUT' ? 'text-red-600' :
              'text-gray-600'
            }`}>
              {orderStatus === 'SUBMITTING' ? '⏳ SUBMITTING...' :
               orderStatus === 'PENDING' ? '⏳ PENDING' :
               orderStatus === 'FILLED' ? '✅ FILLED' :
               orderStatus === 'FAILED' ? '❌ FAILED' :
               orderStatus === 'ERROR' ? '❌ ERROR' :
               orderStatus === 'TIMEOUT' ? '⏰ TIMEOUT' :
               orderStatus}
            </span>
          </div>
          {orderId && (
            <div className="text-[10px] text-blue-600 dark:text-blue-400 mt-1">
              Order ID: {orderId}
            </div>
          )}
        </div>
      )}

      {/* Order Preview */}
      {showConfirmation && orderPreview && (
        <div className="mb-3 p-2 bg-yellow-50 dark:bg-yellow-900/20 border-2 border-yellow-400 dark:border-yellow-600 rounded">
          <div className="text-xs font-semibold text-yellow-800 dark:text-yellow-300 mb-2">
            📋 ORDER PREVIEW - CONFIRM DETAILS
          </div>
          
          <div className="space-y-1 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Action:</span>
              <span className={`font-semibold ${
                orderPreview.action === 'SELL_TO_OPEN' ? 'text-green-600' : 'text-red-600'
              }`}>
                {orderPreview.action}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Option:</span>
              <span className="font-mono font-semibold text-gray-800 dark:text-gray-200">
                {orderPreview.option_symbol}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Type:</span>
              <span className="font-semibold text-gray-800 dark:text-gray-200">
                {orderPreview.option_type}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Strike:</span>
              <span className="font-semibold text-gray-800 dark:text-gray-200">
                ${orderPreview.strike_price.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Contracts:</span>
              <span className="font-semibold text-gray-800 dark:text-gray-200">
                {orderPreview.contracts}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">Est. Price:</span>
              <span className="font-semibold text-gray-800 dark:text-gray-200">
                ${orderPreview.estimated_price.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between border-t border-yellow-300 dark:border-yellow-700 pt-1 mt-1">
              <span className="text-gray-600 dark:text-gray-400 font-semibold">Total:</span>
              <span className={`font-bold ${
                orderPreview.action === 'SELL_TO_OPEN' ? 'text-green-600' : 'text-red-600'
              }`}>
                {orderPreview.action === 'SELL_TO_OPEN' ? '+' : '-'}
                ${Math.abs(orderPreview.estimated_credit_debit).toFixed(2)}
              </span>
            </div>
            <div className="mt-2 p-1 bg-white dark:bg-gray-800 rounded">
              <span className="text-gray-600 dark:text-gray-400 text-[10px]">Rationale:</span>
              <p className="text-gray-700 dark:text-gray-300 text-[10px] mt-1">
                {orderPreview.rationale}
              </p>
            </div>
          </div>

          {/* Confirmation Buttons */}
          <div className="grid grid-cols-2 gap-2 mt-3">
            <button
              onClick={handleCancel}
              className="py-1 px-2 text-xs bg-gray-500 hover:bg-gray-600 text-white rounded transition-colors"
            >
              ✗ Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={isSubmitting}
              className={`py-1 px-2 text-xs font-semibold rounded transition-colors ${
                isSubmitting
                  ? 'bg-gray-500 text-gray-300 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              {isSubmitting ? '⏳ Submitting...' : '✓ Submit Order'}
            </button>
          </div>
        </div>
      )}

      {/* Warning */}
      <div className="mt-2 p-1 bg-orange-100 dark:bg-orange-900/30 border border-orange-300 dark:border-orange-700 rounded">
        <p className="text-[9px] text-orange-800 dark:text-orange-300">
          ⚠️ TESTING MODE: This feature is for testing portfolio calculations and trade tracking.
          Disable in production.
        </p>
      </div>
    </div>
  );
}
