import { NextResponse } from 'next/server';

export async function GET() {
  try {
    // In production, this would fetch from AWS Secrets Manager
    // For now, we'll simulate token status
    const tokenInfo = {
      access_token: "eyJ0eXAiOiJKV1QiLCJhbGc...",
      refresh_token: "dGhpc2lzYXJlZnJlc2h0b2t...",
      expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(), // 7 days from now
      token_type: "Bearer",
      scope: "api",
      last_refresh: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
      refresh_count: 5,
      is_valid: true,
      expires_in_seconds: 7 * 24 * 60 * 60, // 7 days
      refresh_in_seconds: 90 * 24 * 60 * 60, // 90 days
    };

    return NextResponse.json(tokenInfo);
  } catch (error) {
    console.error('Error fetching token status:', error);
    return NextResponse.json(
      { error: 'Failed to fetch token status' },
      { status: 500 }
    );
  }
}
