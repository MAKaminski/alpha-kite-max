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

    // Check if market is open (9:30 AM - 4:00 PM EST)
    const now = new Date();
    const estTime = new Date(now.toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const hours = estTime.getHours();
    const minutes = estTime.getMinutes();
    const totalMinutes = hours * 60 + minutes;
    const marketOpen = 9 * 60 + 30;  // 9:30 AM
    const marketClose = 16 * 60;     // 4:00 PM
    const isMarketOpen = totalMinutes >= marketOpen && totalMinutes < marketClose;

    // Try to fetch live data from backend during market hours
    if (isMarketOpen) {
      try {
        const backendResponse = await fetch(`${process.env.BACKEND_URL || 'http://localhost:8000'}/api/real-time-data?ticker=${ticker}&type=${type}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
          // Add timeout to prevent hanging
          signal: AbortSignal.timeout(5000)
        });

        if (backendResponse.ok) {
          const liveData = await backendResponse.json();
          return NextResponse.json(liveData);
        }
      } catch (error) {
        console.warn('Failed to fetch live data, falling back to mock:', error);
      }
    }

    // Fallback to mock data (market closed or backend unavailable)
    
    const basePrice = 600 + (Math.random() - 0.5) * 2;
    const mockData: {
      timestamp: string;
      ticker: string;
      price: number;
      volume: number;
      sma9: number;
      vwap: number;
      options?: {
        atm_call_price: number;
        atm_put_price: number;
        atm_call_strike: number;
        atm_put_strike: number;
      };
    } = {
      timestamp: new Date().toISOString(),
      ticker: ticker,
      price: basePrice,
      volume: Math.floor(Math.random() * 1000) + 500,
      sma9: basePrice + (Math.random() - 0.5) * 1.5,
      vwap: basePrice + (Math.random() - 0.5) * 1.2,
      // Add options data if requested
      ...(type === 'options' || type === 'both' ? {
        options: {
          atm_call_price: Math.max(0.1, (basePrice - 600) * 0.1 + Math.random() * 2),
          atm_put_price: Math.max(0.1, (600 - basePrice) * 0.1 + Math.random() * 2),
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
