'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabase';

interface Position {
  id: string;
  ticker: string;
  option_symbol: string;
  option_type: 'PUT' | 'CALL';
  strike_price: number;
  expiration_date: string;
  contracts: number;
  entry_price: number;
  entry_credit: number;
  current_price?: number;
  unrealized_pnl?: number;
  status: 'OPEN' | 'CLOSED' | 'EXPIRED';
  created_at: string;
}

interface DailyPnL {
  id: string;
  ticker: string;
  trade_date: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  total_realized_pnl: number;
  total_unrealized_pnl: number;
  total_credits_received: number;
  max_drawdown: number;
}

interface TradingSummary {
  ticker: string;
  date: string;
  daily_pnl?: DailyPnL;
  open_positions: Position[];
  total_unrealized_pnl: number;
  position_count: number;
}

interface TradingDashboardProps {
  ticker: string;
  selectedDate: Date;
}

export default function TradingDashboard({ ticker, selectedDate }: TradingDashboardProps) {
  const [tradingSummary, setTradingSummary] = useState<TradingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTradingSummary();
  }, [ticker, selectedDate]);

  const fetchTradingSummary = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get daily P&L
      const { data: dailyPnL, error: pnlError } = await supabase
        .from('daily_pnl')
        .select('*')
        .eq('ticker', ticker)
        .eq('trade_date', selectedDate.toISOString().split('T')[0])
        .single();

      // Get open positions
      const { data: positions, error: posError } = await supabase
        .from('positions')
        .select('*')
        .eq('ticker', ticker)
        .eq('status', 'OPEN')
        .order('created_at', { ascending: false });

      if (pnlError && pnlError.code !== 'PGRST116') {
        throw pnlError;
      }

      if (posError) {
        throw posError;
      }

      const totalUnrealizedPnL = positions?.reduce((sum, pos) => sum + (pos.unrealized_pnl || 0), 0) || 0;

      setTradingSummary({
        ticker,
        date: selectedDate.toISOString().split('T')[0],
        daily_pnl: dailyPnL || undefined,
        open_positions: positions || [],
        total_unrealized_pnl: totalUnrealizedPnL,
        position_count: positions?.length || 0
      });

    } catch (err) {
      console.error('Error fetching trading summary:', err);
      setError('Failed to load trading data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Trading Summary</h2>
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-700 rounded w-3/4"></div>
          <div className="h-4 bg-gray-700 rounded w-1/2"></div>
          <div className="h-4 bg-gray-700 rounded w-2/3"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Trading Summary</h2>
        <div className="text-red-400">{error}</div>
      </div>
    );
  }

  if (!tradingSummary) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Trading Summary</h2>
        <div className="text-gray-400">No trading data available</div>
      </div>
    );
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  return (
    <div className="space-y-6">
      {/* Daily Summary */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-semibold text-white mb-4">
          Trading Summary - {formatDate(selectedDate.toISOString())}
        </h2>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-700 rounded-lg p-4">
            <div className="text-gray-400 text-sm">Open Positions</div>
            <div className="text-2xl font-bold text-white">{tradingSummary.position_count}</div>
          </div>
          
          <div className="bg-gray-700 rounded-lg p-4">
            <div className="text-gray-400 text-sm">Unrealized P&L</div>
            <div className={`text-2xl font-bold ${
              tradingSummary.total_unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              {formatCurrency(tradingSummary.total_unrealized_pnl)}
            </div>
          </div>
          
          {tradingSummary.daily_pnl && (
            <>
              <div className="bg-gray-700 rounded-lg p-4">
                <div className="text-gray-400 text-sm">Total Trades</div>
                <div className="text-2xl font-bold text-white">{tradingSummary.daily_pnl.total_trades}</div>
              </div>
              
              <div className="bg-gray-700 rounded-lg p-4">
                <div className="text-gray-400 text-sm">Realized P&L</div>
                <div className={`text-2xl font-bold ${
                  tradingSummary.daily_pnl.total_realized_pnl >= 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {formatCurrency(tradingSummary.daily_pnl.total_realized_pnl)}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Open Positions */}
      {tradingSummary.open_positions.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Open Positions</h3>
          
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-600">
                  <th className="text-left py-2 text-gray-300">Option</th>
                  <th className="text-left py-2 text-gray-300">Strike</th>
                  <th className="text-left py-2 text-gray-300">Expiry</th>
                  <th className="text-left py-2 text-gray-300">Contracts</th>
                  <th className="text-left py-2 text-gray-300">Entry</th>
                  <th className="text-left py-2 text-gray-300">Current</th>
                  <th className="text-left py-2 text-gray-300">P&L</th>
                </tr>
              </thead>
              <tbody>
                {tradingSummary.open_positions.map((position) => (
                  <tr key={position.id} className="border-b border-gray-700">
                    <td className="py-2 text-white">
                      <span className={`px-2 py-1 rounded text-xs ${
                        position.option_type === 'CALL' ? 'bg-blue-600' : 'bg-red-600'
                      }`}>
                        {position.option_type}
                      </span>
                    </td>
                    <td className="py-2 text-white">${position.strike_price}</td>
                    <td className="py-2 text-white">{formatDate(position.expiration_date)}</td>
                    <td className="py-2 text-white">{position.contracts}</td>
                    <td className="py-2 text-white">{formatCurrency(position.entry_price)}</td>
                    <td className="py-2 text-white">
                      {position.current_price ? formatCurrency(position.current_price) : 'N/A'}
                    </td>
                    <td className={`py-2 font-semibold ${
                      (position.unrealized_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {position.unrealized_pnl ? formatCurrency(position.unrealized_pnl) : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* No Positions Message */}
      {tradingSummary.open_positions.length === 0 && (
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="text-center text-gray-400">
            <div className="text-4xl mb-2">📊</div>
            <div>No open positions</div>
            <div className="text-sm mt-1">Positions will appear here when trades are executed</div>
          </div>
        </div>
      )}
    </div>
  );
}
