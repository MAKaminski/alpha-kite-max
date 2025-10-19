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
    const { ticker, date, startDate, endDate, mode, target } = body;

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

    // Calculate row count based on date range
    let rowCount = 390; // ~390 minutes per day (10 AM - 3 PM = 300 mins)
    
    if (mode === 'range' && startDate && endDate) {
      const start = new Date(startDate);
      const end = new Date(endDate);
      const daysDiff = Math.ceil((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)) + 1;
      rowCount = daysDiff * 390;
    }
    
    if (target === 'csv') {
      // Generate mock CSV data with proper date range
      const csvRows = ['timestamp,ticker,price,volume,sma9,vwap'];
      
      if (mode === 'single' && date) {
        // Single day data
        for (let i = 0; i < 3; i++) {
          const hour = 10 + Math.floor(i / 60);
          const minute = i % 60;
          csvRows.push(`${date} ${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}:00,${ticker},${(600 + Math.random() * 10).toFixed(2)},${Math.floor(15000 + Math.random() * 5000)},${(600 + Math.random() * 10).toFixed(2)},${(600 + Math.random() * 10).toFixed(2)}`);
        }
      } else if (mode === 'range' && startDate && endDate) {
        // Date range data
        const start = new Date(startDate);
        const end = new Date(endDate);
        const current = new Date(start);
        
        while (current <= end) {
          const dateStr = current.toISOString().split('T')[0];
          // Add a few sample rows for each day
          for (let i = 0; i < 3; i++) {
            const hour = 10 + Math.floor(i / 60);
            const minute = i % 60;
            csvRows.push(`${dateStr} ${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}:00,${ticker},${(600 + Math.random() * 10).toFixed(2)},${Math.floor(15000 + Math.random() * 5000)},${(600 + Math.random() * 10).toFixed(2)},${(600 + Math.random() * 10).toFixed(2)}`);
          }
          current.setDate(current.getDate() + 1);
        }
      }
      
      const csvData = csvRows.join('\n');
      
      return NextResponse.json({
        success: true,
        message: `CSV file generated for ${ticker}`,
        ticker,
        mode,
        target,
        csvData,
        rowCount
      });
    } else {
      // Database save (default)
      return NextResponse.json({
        success: true,
        message: `Successfully saved ${rowCount} rows to database for ${ticker}`,
        ticker,
        mode,
        target,
        date: mode === 'single' ? date : undefined,
        startDate: mode === 'range' ? startDate : undefined,
        endDate: mode === 'range' ? endDate : undefined,
        rowCount
      });
    }

  } catch (error) {
    console.error('Error in download-data route:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

