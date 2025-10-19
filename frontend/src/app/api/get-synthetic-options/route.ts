import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const ticker = searchParams.get('ticker') || 'QQQ';
    const date = searchParams.get('date');
    const dataSource = searchParams.get('dataSource') || 'black_scholes_synthetic';

    // For now, return mock data structure
    // TODO: Replace with actual Supabase query
    const mockData = {
      data: [
        {
          id: 1,
          timestamp: new Date().toISOString(),
          ticker: ticker,
          option_symbol: `${ticker}251020C00600000`,
          option_type: 'CALL',
          strike_price: 600.0,
          expiration_date: date || new Date().toISOString().split('T')[0],
          spot_price: 600.0,
          market_price: 5.25,
          bid: 5.20,
          ask: 5.30,
          volume: 150,
          open_interest: 1250,
          implied_volatility: 0.22,
          delta: 0.52,
          gamma: 0.015,
          theta: -0.08,
          vega: 0.25,
          data_source: dataSource,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        {
          id: 2,
          timestamp: new Date().toISOString(),
          ticker: ticker,
          option_symbol: `${ticker}251020P00600000`,
          option_type: 'PUT',
          strike_price: 600.0,
          expiration_date: date || new Date().toISOString().split('T')[0],
          spot_price: 600.0,
          market_price: 4.75,
          bid: 4.70,
          ask: 4.80,
          volume: 120,
          open_interest: 980,
          implied_volatility: 0.23,
          delta: -0.48,
          gamma: 0.015,
          theta: -0.07,
          vega: 0.25,
          data_source: dataSource,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }
      ],
      count: 2,
      data_source: dataSource,
      is_synthetic: dataSource === 'black_scholes_synthetic'
    };

    return NextResponse.json(mockData);
  } catch (error) {
    console.error('Error fetching synthetic options data:', error);
    return NextResponse.json(
      { error: 'Failed to fetch synthetic options data' },
      { status: 500 }
    );
  }
}
