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
          calls: [
            {
              strike: 600,
              price: 5.25 + (Math.random() - 0.5) * 0.5,
              volume: Math.floor(Math.random() * 100)
            },
            {
              strike: 605,
              price: 3.75 + (Math.random() - 0.5) * 0.3,
              volume: Math.floor(Math.random() * 80)
            }
          ],
          puts: [
            {
              strike: 595,
              price: 4.50 + (Math.random() - 0.5) * 0.4,
              volume: Math.floor(Math.random() * 90)
            },
            {
              strike: 590,
              price: 2.25 + (Math.random() - 0.5) * 0.2,
              volume: Math.floor(Math.random() * 70)
            }
          ]
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
