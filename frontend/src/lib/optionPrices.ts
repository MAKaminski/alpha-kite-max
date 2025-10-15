import { supabase } from './supabase';

export interface OptionPrice {
  timestamp: string;
  option_symbol: string;
  option_type: 'PUT' | 'CALL';
  strike_price: number;
  expiration_date: string;
  price: number;
  bid: number;
  ask: number;
  volume: number;
  open_interest: number;
}

export interface TradeOptionPrice extends OptionPrice {
  position_id: string;
  trade_id: string;
  action: 'SELL_TO_OPEN' | 'BUY_TO_CLOSE';
}

export async function getTradeOptionPrices(ticker: string, date: Date): Promise<TradeOptionPrice[]> {
  try {
    const dateStr = date.toISOString().split('T')[0];
    
    // Get all trades for the day
    const { data: trades, error: tradesError } = await supabase
      .from('trades')
      .select(`
        id,
        position_id,
        option_symbol,
        option_type,
        strike_price,
        expiration_date,
        action,
        trade_timestamp,
        price
      `)
      .eq('ticker', ticker)
      .gte('trade_timestamp', `${dateStr}T00:00:00`)
      .lte('trade_timestamp', `${dateStr}T23:59:59`)
      .order('trade_timestamp', { ascending: true });

    if (tradesError) {
      console.error('Error fetching trades:', tradesError);
      return [];
    }

    if (!trades || trades.length === 0) {
      return [];
    }

    // Get unique option symbols from trades (for future use)
    // const optionSymbols = [...new Set(trades.map(trade => trade.option_symbol))];
    
    // For now, we'll create mock option price data
    // In a real implementation, you'd fetch this from your backend/Schwab API
    const optionPrices: TradeOptionPrice[] = [];
    
    for (const trade of trades) {
      // Create mock price progression for the option throughout the day
      const basePrice = trade.price;
      const priceVariations = [-0.05, -0.03, 0.02, 0.04, -0.02, 0.01, -0.04, 0.03];
      
      // Generate 8 price points throughout the day (every 45 minutes)
      for (let i = 0; i < 8; i++) {
        const hour = 9 + Math.floor(i * 0.75); // Start at 9 AM, increment by 45 mins
        const minute = (i * 45) % 60;
        const timestamp = new Date(date);
        timestamp.setHours(hour, minute, 0, 0);
        
        const priceVariation = priceVariations[i] || 0;
        const currentPrice = Math.max(0.01, basePrice + priceVariation);
        
        optionPrices.push({
          timestamp: timestamp.toISOString(),
          position_id: trade.position_id,
          trade_id: trade.id,
          option_symbol: trade.option_symbol,
          option_type: trade.option_type,
          strike_price: trade.strike_price,
          expiration_date: trade.expiration_date,
          price: currentPrice,
          bid: Math.max(0.01, currentPrice - 0.02),
          ask: currentPrice + 0.02,
          volume: Math.floor(Math.random() * 100) + 10,
          open_interest: Math.floor(Math.random() * 1000) + 100,
          action: trade.action
        });
      }
    }

    return optionPrices.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  } catch (error) {
    console.error('Error getting trade option prices:', error);
    return [];
  }
}

export function getOptionPriceColor(optionType: 'PUT' | 'CALL'): string {
  return optionType === 'CALL' ? '#3B82F6' : '#EF4444'; // Blue for calls, red for puts
}

export function getOptionPriceSymbol(optionType: 'PUT' | 'CALL'): string {
  return optionType === 'CALL' ? '▲' : '▼';
}
