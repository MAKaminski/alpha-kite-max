import { NextRequest, NextResponse } from 'next/server';

/**
 * API Route: Get Recommended Option
 * 
 * POST /api/get-recommended-option
 * 
 * Returns a recommended 0DTE option based on current market conditions.
 */

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { ticker, action, current_price, price_action, contracts = 10 } = body;

    // Validate inputs
    if (!ticker || !action || !current_price) {
      return NextResponse.json(
        { error: 'Missing required parameters' },
        { status: 400 }
      );
    }

    if (!['SELL_TO_OPEN', 'BUY_TO_CLOSE'].includes(action)) {
      return NextResponse.json(
        { error: 'Invalid action. Must be SELL_TO_OPEN or BUY_TO_CLOSE' },
        { status: 400 }
      );
    }

    // Get today's date for 0DTE
    const today = new Date();
    const year = today.getFullYear().toString().slice(-2);
    const month = (today.getMonth() + 1).toString().padStart(2, '0');
    const day = today.getDate().toString().padStart(2, '0');
    const dateStr = `${year}${month}${day}`;

    // Determine option type based on price action
    let optionType: 'CALL' | 'PUT' = 'CALL';
    let strikePrice = current_price;
    let rationale = '';

    // Helper function to round to nearest strike (nearest dollar or nearest $5 increment for higher prices)
    const roundToNearestStrike = (price: number): number => {
      if (price < 100) {
        // For prices under $100, strikes are typically in $1 increments
        return Math.round(price);
      } else if (price < 500) {
        // For prices $100-$500, strikes are typically in $5 increments
        return Math.round(price / 5) * 5;
      } else {
        // For prices over $500, strikes are typically in $5 or $10 increments
        return Math.round(price / 5) * 5;
      }
    };

    if (action === 'SELL_TO_OPEN') {
      // Choose option type based on trend
      if (price_action?.trend === 'bullish') {
        // Bullish: sell OTM puts (expect price to stay above strike)
        optionType = 'PUT';
        // For bullish, sell slightly OTM put (1-2% below current price)
        const otmPrice = current_price * 0.985; // 1.5% OTM
        strikePrice = roundToNearestStrike(otmPrice);
        rationale = `Bullish trend detected (SMA9: ${price_action.sma9?.toFixed(2)}). Selling OTM PUT at $${strikePrice} (nearest strike to ${otmPrice.toFixed(2)}) with expectation price stays above strike.`;
      } else if (price_action?.trend === 'bearish') {
        // Bearish: sell OTM calls (expect price to stay below strike)
        optionType = 'CALL';
        // For bearish, sell slightly OTM call (1-2% above current price)
        const otmPrice = current_price * 1.015; // 1.5% OTM
        strikePrice = roundToNearestStrike(otmPrice);
        rationale = `Bearish trend detected (SMA9: ${price_action.sma9?.toFixed(2)}). Selling OTM CALL at $${strikePrice} (nearest strike to ${otmPrice.toFixed(2)}) with expectation price stays below strike.`;
      } else {
        // Neutral: sell ATM put (higher premium)
        optionType = 'PUT';
        strikePrice = roundToNearestStrike(current_price);
        rationale = `Neutral trend. Selling ATM PUT at $${strikePrice} (nearest strike to ${current_price.toFixed(2)}) for premium collection.`;
      }
    } else {
      // BUY_TO_CLOSE: use nearest strike to current price
      // For now, assume we're closing a PUT position
      optionType = 'PUT';
      strikePrice = roundToNearestStrike(current_price);
      rationale = `Closing existing position at nearest strike $${strikePrice} to current market price $${current_price.toFixed(2)}.`;
    }

    // Generate option symbol
    const optionSymbol = `${ticker}${dateStr}${optionType.charAt(0)}${strikePrice.toString().padStart(8, '0')}`;

    // Estimate option price (simplified - would use Black-Scholes in production)
    // For 0DTE, options are typically 0.5% - 2% of underlying price
    const estimatedPrice = action === 'SELL_TO_OPEN' 
      ? current_price * 0.01 // 1% for selling
      : current_price * 0.008; // 0.8% for buying back

    const estimatedCreditDebit = estimatedPrice * contracts * 100;

    const recommendation = {
      ticker,
      option_symbol: optionSymbol,
      option_type: optionType,
      strike_price: strikePrice,
      expiration_date: today.toISOString().split('T')[0],
      action,
      contracts,
      estimated_price: parseFloat(estimatedPrice.toFixed(2)),
      estimated_credit_debit: parseFloat((action === 'SELL_TO_OPEN' ? estimatedCreditDebit : -estimatedCreditDebit).toFixed(2)),
      current_equity_price: current_price,
      rationale
    };

    return NextResponse.json(recommendation);

  } catch (error) {
    console.error('Error generating option recommendation:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
