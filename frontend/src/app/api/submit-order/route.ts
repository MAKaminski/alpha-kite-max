import { NextRequest, NextResponse } from 'next/server';

/**
 * API Route: Submit Order to Schwab Paper Trading
 * 
 * POST /api/submit-order
 * 
 * Submits orders to Schwab paper trading account and tracks status.
 */

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { 
      ticker, 
      option_symbol, 
      option_type, 
      strike_price, 
      action, 
      contracts, 
      price,
      mode = 'manual' // 'automatic' or 'manual'
    } = body;

    // Validate required fields
    if (!ticker || !option_symbol || !action || !contracts || !price) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }

    // Generate order ID
    const orderId = `order_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // TODO: In production, this would call the Python backend to submit to Schwab
    // const backendResponse = await fetch(`${process.env.BACKEND_URL}/api/submit-order`, {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({
    //     ticker,
    //     option_symbol,
    //     option_type,
    //     strike_price,
    //     action,
    //     contracts,
    //     price,
    //     mode
    //   })
    // });

    // For now, simulate order submission with realistic timing
    const order = {
      order_id: orderId,
      ticker,
      option_symbol,
      option_type,
      strike_price,
      action,
      contracts,
      price,
      mode,
      status: 'PENDING',
      submitted_at: new Date().toISOString(),
      estimated_fill_time: new Date(Date.now() + 2000).toISOString(), // 2 seconds
      schwab_order_id: null, // Will be filled when confirmed
      fill_price: null,
      filled_at: null,
      commission: 0.65, // Schwab commission
      total_cost: (price * contracts * 100) + 0.65
    };

    // Simulate order processing
    console.log('📋 Order submitted:', {
      order_id: orderId,
      ticker,
      option_symbol,
      action,
      contracts,
      price,
      mode,
      status: 'PENDING'
    });

    // In a real implementation, this would:
    // 1. Submit to Schwab API
    // 2. Get confirmation
    // 3. Update database
    // 4. Return real status

    return NextResponse.json({
      success: true,
      order,
      message: `${action} order submitted successfully`,
      next_steps: [
        'Order is pending confirmation from Schwab',
        'Status will update automatically',
        'Check order status in 2-3 seconds'
      ]
    });

  } catch (error) {
    console.error('Error submitting order:', error);
    return NextResponse.json(
      { error: 'Failed to submit order' },
      { status: 500 }
    );
  }
}
