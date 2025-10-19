import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

/**
 * API Route: Get Daily Price Range
 * 
 * GET /api/get-daily-range?ticker=QQQ&date=2025-10-19
 * 
 * Returns the low and high price for a specific ticker on a specific date.
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const ticker = searchParams.get('ticker');
    const date = searchParams.get('date');

    if (!ticker || !date) {
      return NextResponse.json(
        { error: 'Ticker and date are required' },
        { status: 400 }
      );
    }

    // Connect to Supabase
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

    if (!supabaseUrl || !supabaseKey) {
      return NextResponse.json(
        { error: 'Supabase not configured' },
        { status: 500 }
      );
    }

    const supabase = createClient(supabaseUrl, supabaseKey);

    // Query equity data for the specific date
    const startOfDay = `${date} 00:00:00`;
    const endOfDay = `${date} 23:59:59`;

    const { data, error } = await supabase
      .from('equity_data')
      .select('price')
      .eq('ticker', ticker)
      .gte('timestamp', startOfDay)
      .lte('timestamp', endOfDay)
      .order('price', { ascending: true });

    if (error) {
      console.error('Supabase query error:', error);
      return NextResponse.json(
        { error: 'Database query failed' },
        { status: 500 }
      );
    }

    if (!data || data.length === 0) {
      // No data for this date, return estimated range
      return NextResponse.json({
        low: 595,
        high: 605,
        dataPoints: 0,
        estimated: true
      });
    }

    // Calculate low and high
    const prices = data.map(d => Number(d.price));
    const low = Math.min(...prices);
    const high = Math.max(...prices);

    return NextResponse.json({
      low,
      high,
      dataPoints: data.length,
      estimated: false,
      ticker,
      date
    });

  } catch (error) {
    console.error('Error in get-daily-range route:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

