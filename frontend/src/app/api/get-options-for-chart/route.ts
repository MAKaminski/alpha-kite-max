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

    // Initialize Supabase client (prefer server-side service role if available)
    const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

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
    interface SupabaseOptionRow {
      timestamp: string;
      ticker: string;
      option_symbol: string;
      option_type: string;
      strike_price: string;
      market_price: string;
      spot_price: string;
      delta: string;
      gamma: string;
      theta: string;
      vega: string;
      implied_volatility: string;
      data_source?: string;
    }
    
    const optionsData = (data || []).map((row: SupabaseOptionRow & { id?: number; expiration_date?: string; bid?: string; ask?: string; volume?: number; open_interest?: number }) => ({
      id: row.id || 0,
      timestamp: row.timestamp,
      ticker: row.ticker,
      option_symbol: row.option_symbol,
      option_type: row.option_type,
      strike_price: parseFloat(row.strike_price),
      expiration_date: row.expiration_date || row.timestamp.split('T')[0],
      spot_price: parseFloat(row.spot_price),
      market_price: parseFloat(row.market_price),
      bid: parseFloat(row.bid || row.market_price),
      ask: parseFloat(row.ask || row.market_price),
      volume: row.volume || 0,
      open_interest: row.open_interest || 0,
      implied_volatility: parseFloat(row.implied_volatility),
      delta: parseFloat(row.delta),
      gamma: parseFloat(row.gamma),
      theta: parseFloat(row.theta),
      vega: parseFloat(row.vega),
      data_source: row.data_source || 'black_scholes_synthetic',
    }));

    // TEMP DIAGNOSTIC: include supabase URL source to verify live env wiring (will be removed)
    return NextResponse.json({
      data: optionsData,
      count: optionsData.length,
      date: date,
      ticker: ticker,
      diag_supabase_url: supabaseUrl,
      diag_uses_service_role: Boolean(process.env.SUPABASE_SERVICE_ROLE_KEY),
    });
  } catch (error) {
    console.error('Error fetching options data:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}

