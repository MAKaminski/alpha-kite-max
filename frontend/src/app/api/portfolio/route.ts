import { NextRequest, NextResponse } from 'next/server';

/**
 * API Route: Portfolio Data
 * 
 * GET /api/portfolio
 * 
 * Returns portfolio summary including account balance, positions, and trade history.
 */

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const ticker = searchParams.get('ticker') || 'QQQ';

    // TODO: In production, this would call the Python portfolio tracker
    // const response = await fetch('http://localhost:8000/api/portfolio');
    // const portfolio = await response.json();

    // For now, return mock portfolio data
    const mockPortfolio = {
      account_balance: 105500.00,
      cash_balance: 100000.00,
      initial_balance: 100000.00,
      total_pnl: 5500.00,
      open_positions: 1,
      total_exposure: 5500.00,
      positions: [
        {
          ticker: ticker,
          option_symbol: `${ticker}251020P00600000`,
          option_type: 'PUT',
          strike_price: 600.0,
          contracts: 10,
          entry_price: 5.50,
          current_price: 4.50,
          unrealized_pnl: 1000.00
        }
      ],
      balance_history: [
        {
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          balance: 100000.00,
          cash: 100000.00,
          open_positions: 0,
          trade_id: null
        },
        {
          timestamp: new Date(Date.now() - 1800000).toISOString(),
          balance: 105500.00,
          cash: 105500.00,
          open_positions: 1,
          trade_id: `${ticker}251020P00600000`
        },
        {
          timestamp: new Date().toISOString(),
          balance: 105500.00,
          cash: 100000.00,
          open_positions: 1,
          trade_id: null
        }
      ],
      trades: [
        {
          timestamp: new Date(Date.now() - 1800000).toISOString(),
          ticker: ticker,
          option_symbol: `${ticker}251020P00600000`,
          action: 'SELL_TO_OPEN',
          option_type: 'PUT',
          strike_price: 600.0,
          contracts: 10,
          price: 5.50,
          credit_debit: 5500.00
        }
      ]
    };

    return NextResponse.json(mockPortfolio);

  } catch (error) {
    console.error('Error fetching portfolio data:', error);
    return NextResponse.json(
      { error: 'Failed to fetch portfolio data' },
      { status: 500 }
    );
  }
}
