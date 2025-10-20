import { NextRequest, NextResponse } from 'next/server';

/**
 * API Route: Auto-Backfill System
 * 
 * POST /api/auto-backfill
 * 
 * Triggers automatic backfill of missing data from Schwab/Polygon APIs.
 */

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { ticker = 'QQQ', data_types = ['equity', 'options'] } = body;

    // Validate inputs
    if (!ticker || typeof ticker !== 'string') {
      return NextResponse.json(
        { error: 'Valid ticker symbol is required' },
        { status: 400 }
      );
    }

    if (!Array.isArray(data_types) || data_types.length === 0) {
      return NextResponse.json(
        { error: 'Data types array is required' },
        { status: 400 }
      );
    }

    const valid_data_types = ['equity', 'options'];
    const invalid_types = data_types.filter(type => !valid_data_types.includes(type));
    if (invalid_types.length > 0) {
      return NextResponse.json(
        { error: `Invalid data types: ${invalid_types.join(', ')}. Valid types: ${valid_data_types.join(', ')}` },
        { status: 400 }
      );
    }

    // TODO: Call the Python auto-backfill system
    // For now, return a mock response
    const mockResults = {
      ticker,
      data_types,
      results: {
        equity: true,
        options: true
      },
      message: 'Auto-backfill completed successfully',
      timestamp: new Date().toISOString(),
      backfilled_data: {
        equity: {
          start_date: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          end_date: new Date().toISOString(),
          records_added: 1440, // 24 hours of minute data
          duplicates_skipped: 0
        },
        options: {
          start_date: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          end_date: new Date().toISOString(),
          records_added: 500,
          duplicates_skipped: 0
        }
      }
    };

    return NextResponse.json(mockResults);

  } catch (error) {
    console.error('Error in auto-backfill route:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const ticker = searchParams.get('ticker') || 'QQQ';

    // TODO: Get current data range status
    // For now, return mock status
    const mockStatus = {
      ticker,
      data_ranges: {
        equity: {
          earliest: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
          latest: new Date().toISOString(),
          total_records: 43200, // 30 days of minute data
          last_updated: new Date().toISOString()
        },
        options: {
          earliest: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
          latest: new Date().toISOString(),
          total_records: 15000,
          last_updated: new Date().toISOString()
        }
      },
      needs_backfill: {
        equity: false,
        options: false
      },
      last_backfill: new Date().toISOString()
    };

    return NextResponse.json(mockStatus);

  } catch (error) {
    console.error('Error getting backfill status:', error);
    return NextResponse.json(
      { error: 'Failed to get backfill status' },
      { status: 500 }
    );
  }
}
