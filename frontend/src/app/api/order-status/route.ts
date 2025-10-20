import { NextRequest, NextResponse } from 'next/server';

/**
 * API Route: Check Order Status
 * 
 * GET /api/order-status?order_id=xxx
 * 
 * Checks the status of a submitted order.
 */

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const orderId = searchParams.get('order_id');

    if (!orderId) {
      return NextResponse.json(
        { error: 'Order ID is required' },
        { status: 400 }
      );
    }

    // TODO: In production, this would check actual Schwab order status
    // const backendResponse = await fetch(`${process.env.BACKEND_URL}/api/order-status?order_id=${orderId}`);
    // const status = await backendResponse.json();

    // For now, simulate order status progression
    const order = {
      order_id: orderId,
      status: 'FILLED', // Simulate successful fill
      schwab_order_id: `SCHWAB_${Date.now()}`,
      fill_price: 5.25, // Slightly different from submitted price
      filled_at: new Date().toISOString(),
      commission: 0.65,
      total_cost: 5250.65,
      message: 'Order filled successfully'
    };

    // Simulate different statuses based on time
    const now = Date.now();
    const orderTime = parseInt(orderId.split('_')[1]);
    const timeDiff = now - orderTime;

    if (timeDiff < 1000) {
      order.status = 'PENDING';
      order.message = 'Order pending confirmation';
    } else if (timeDiff < 3000) {
      order.status = 'CONFIRMED';
      order.message = 'Order confirmed by Schwab';
    } else {
      order.status = 'FILLED';
      order.message = 'Order filled successfully';
    }

    return NextResponse.json({
      success: true,
      order,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    console.error('Error checking order status:', error);
    return NextResponse.json(
      { error: 'Failed to check order status' },
      { status: 500 }
    );
  }
}
