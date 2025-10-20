import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const ticker = searchParams.get('ticker') || 'QQQ';
    const date = searchParams.get('date');

    if (!date) {
      return NextResponse.json(
        { error: 'Date parameter is required' },
        { status: 400 }
      );
    }

    // Initialize Supabase client
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

    if (!supabaseUrl || !supabaseKey) {
      console.error('Missing Supabase credentials');
      return NextResponse.json(
        { error: 'Server configuration error' },
        { status: 500 }
      );
    }

    const supabase = createClient(supabaseUrl, supabaseKey);

    // Query synthetic options data for the specified date
    const { data, error } = await supabase
      .from('synthetic_option_prices')
      .select('*')
      .eq('ticker', ticker)
      .gte('timestamp', `${date}T00:00:00`)
      .lte('timestamp', `${date}T23:59:59`)
      .order('timestamp', { ascending: true });

    if (error) {
      console.error('Supabase query error:', error);
      return NextResponse.json(
        { error: 'Failed to fetch options data', details: error.message },
        { status: 500 }
      );
    }

    // Transform data for chart display
    const optionsData = (data || []).map((row: any) => ({
      timestamp: row.timestamp,
      ticker: row.ticker,
      option_symbol: row.option_symbol,
      option_type: row.option_type,
      strike_price: parseFloat(row.strike_price),
      market_price: parseFloat(row.market_price),
      spot_price: parseFloat(row.spot_price),
      delta: parseFloat(row.delta),
      gamma: parseFloat(row.gamma),
      theta: parseFloat(row.theta),
      vega: parseFloat(row.vega),
      implied_volatility: parseFloat(row.implied_volatility),
      data_source: row.data_source || 'black_scholes_synthetic',
    }));

    return NextResponse.json({
      data: optionsData,
      count: optionsData.length,
      date: date,
      ticker: ticker,
    });
  } catch (error) {
    console.error('Error fetching options data:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

