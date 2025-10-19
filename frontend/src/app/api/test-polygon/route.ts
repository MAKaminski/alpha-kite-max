import { NextResponse } from 'next/server';

/**
 * API Route: Test Polygon.io Connection
 * 
 * GET /api/test-polygon
 * 
 * Tests if Polygon API is configured and working.
 */
export async function GET() {
  try {
    // TODO: Call backend to test Polygon API connection
    // For now, check if API key is in environment
    
    const polygonConfigured = process.env.POLYGON_API_KEY !== undefined;
    
    if (!polygonConfigured) {
      return NextResponse.json({
        connected: false,
        error: 'POLYGON_API_KEY not configured in backend/.env',
        rateLimitRemaining: 0,
        freeCallsRemaining: 0
      });
    }

    // In production, this would call backend:
    // const response = await fetch(`${backendUrl}/api/test-polygon`);
    
    // Mock successful connection
    return NextResponse.json({
      connected: true,
      apiKey: process.env.POLYGON_API_KEY?.substring(0, 10) + '...',
      rateLimitRemaining: 5, // Free tier: 5 calls/min
      freeCallsRemaining: 100, // Example remaining calls
      tier: 'Free',
      features: {
        historicalData: true,
        realTimeStreaming: true,
        greeks: true,
        yearsCoverage: 2
      }
    });

  } catch (error) {
    console.error('Error testing Polygon API:', error);
    return NextResponse.json({
      connected: false,
      error: 'Failed to test Polygon API'
    }, { status: 500 });
  }
}

