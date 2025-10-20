import { NextRequest, NextResponse } from 'next/server';

/**
 * API Route: Real-Time Data
 * 
 * GET /api/real-time-data
 * 
 * Fetches real-time data from Schwab API for streaming.
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const ticker = searchParams.get('ticker') || 'QQQ';
    const type = searchParams.get('type') || 'both';

    // TODO: Connect to actual Schwab streaming service
    // For now, return mock data that simulates real market data
    
    const mockData = {
      timestamp: new Date().toISOString(),
      ticker: ticker,
      price: 600 + (Math.random() - 0.5) * 2, // Small price movements
      volume: Math.floor(Math.random() * 1000) + 500,
      sma9: 600 + (Math.random() - 0.5) * 1.5,
      vwap: 600 + (Math.random() - 0.5) * 1.2,
      // Add options data if requested
      ...(type === 'options' || type === 'both' ? {
        options: {
          atm_call_price: Math.max(0.1, (mockData.price - 600) * 0.1 + Math.random() * 2),
          atm_put_price: Math.max(0.1, (600 - mockData.price) * 0.1 + Math.random() * 2),
          atm_call_strike: 600,
          atm_put_strike: 600
        }
      } : {})
    };

    return NextResponse.json(mockData);

  } catch (error) {
    console.error('Error fetching real-time data:', error);
    return NextResponse.json(
      { error: 'Failed to fetch real-time data' },
      { status: 500 }
    );
  }
}
