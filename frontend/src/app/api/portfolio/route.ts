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
    const ticker = searchParams.get('ticker') || 'QQQ'; // eslint-disable-line @typescript-eslint/no-unused-vars

    // TODO: In production, this would call the Python portfolio tracker
    // const response = await fetch('http://localhost:8000/api/portfolio');
    // const portfolio = await response.json();

    // For now, return mock portfolio data
    const mockPortfolio = {
      account_balance: 100000.00,
      cash_balance: 100000.00,
      initial_balance: 100000.00,
      total_pnl: 0.00,
      open_positions: 0,
      total_exposure: 0.00,
      positions: [],
      balance_history: [
        {
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          balance: 100000.00,
          cash: 100000.00,
          open_positions: 0,
          trade_id: null
        },
        {
          timestamp: new Date().toISOString(),
          balance: 100000.00,
          cash: 100000.00,
          open_positions: 0,
          trade_id: null
        }
      ],
      trades: []
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
