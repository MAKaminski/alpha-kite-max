import { NextRequest, NextResponse } from 'next/server';

/**
 * API Route: Manual Historical Data Download
 * 
 * POST /api/download-data
 * 
 * Triggers the backend Python ETL pipeline to download historical data
 * for a specific date or date range.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { ticker, date, startDate, endDate, mode } = body;

    // Validate inputs
    if (!ticker) {
      return NextResponse.json(
        { error: 'Ticker symbol is required' },
        { status: 400 }
      );
    }

    if (mode === 'single' && !date) {
      return NextResponse.json(
        { error: 'Date is required for single day download' },
        { status: 400 }
      );
    }

    if (mode === 'range' && (!startDate || !endDate)) {
      return NextResponse.json(
        { error: 'Start date and end date are required for range download' },
        { status: 400 }
      );
    }

    // TODO: Call backend Python API to trigger download
    // For now, return mock success response
    
    // In production, this would call something like:
    // const backendUrl = process.env.BACKEND_API_URL || 'http://localhost:8000';
    // const response = await fetch(`${backendUrl}/api/download`, {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ ticker, date, startDate, endDate, mode })
    // });

    // Mock successful download
    const rowCount = mode === 'single' ? 390 : 2000; // ~390 minutes per day
    
    return NextResponse.json({
      success: true,
      message: `Successfully downloaded data for ${ticker}`,
      ticker,
      mode,
      date: mode === 'single' ? date : undefined,
      startDate: mode === 'range' ? startDate : undefined,
      endDate: mode === 'range' ? endDate : undefined,
      rowCount
    });

  } catch (error) {
    console.error('Error in download-data route:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

