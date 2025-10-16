import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { action } = body;

    if (!action || !['refresh_token', 'check_token_status'].includes(action)) {
      return NextResponse.json(
        { error: 'Invalid action. Use "refresh_token" or "check_token_status"' },
        { status: 400 }
      );
    }

    // Call the Lambda function
    const lambdaResponse = await fetch(
      `https://8xpo1jfbfg.execute-api.us-east-1.amazonaws.com/prod/token-refresh`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action }),
      }
    );

    if (!lambdaResponse.ok) {
      throw new Error(`Lambda function error: ${lambdaResponse.status}`);
    }

    const lambdaData = await lambdaResponse.json();
    
    return NextResponse.json(lambdaData);

  } catch (error) {
    console.error('Token refresh API error:', error);
    
    return NextResponse.json(
      { 
        error: 'Failed to process token refresh request',
        message: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
