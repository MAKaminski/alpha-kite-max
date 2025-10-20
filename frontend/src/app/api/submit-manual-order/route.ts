import { NextRequest, NextResponse } from 'next/server';

/**
 * API Route: Submit Manual Order
 * 
 * POST /api/submit-manual-order
 * 
 * Submits a manual order to the portfolio tracker and Schwab API.
 */

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const {
      ticker,
      option_symbol,
      option_type,
      strike_price,
      expiration_date,
      action,
      contracts,
      estimated_price,
      estimated_credit_debit
    } = body;

    // Validate inputs
    if (!ticker || !option_symbol || !option_type || !strike_price || !action || !contracts) {
      return NextResponse.json(
        { error: 'Missing required order parameters' },
        { status: 400 }
      );
    }

    // TODO: In production, this would:
    // 1. Submit order to Schwab API
    // 2. Wait for confirmation
    // 3. Update portfolio tracker with actual fill price
    
    // For now, simulate order submission
    const simulatedOrder = {
      order_id: `ORD-${Date.now()}`,
      ticker,
      option_symbol,
      option_type,
      strike_price,
      expiration_date,
      action,
      contracts,
      fill_price: estimated_price,
      credit_debit: estimated_credit_debit,
      status: 'FILLED',
      filled_at: new Date().toISOString(),
      message: 'Order filled successfully (SIMULATED)'
    };

    // TODO: Call Python backend to update portfolio tracker
    // await fetch('http://localhost:8000/api/add-trade', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify(simulatedOrder)
    // });

    return NextResponse.json({
      success: true,
      order: simulatedOrder
    });

  } catch (error) {
    console.error('Error submitting manual order:', error);
    return NextResponse.json(
      { error: 'Failed to submit order' },
      { status: 500 }
    );
  }
}
