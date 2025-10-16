#!/usr/bin/env python3
"""Local test script for Lambda function.

Run this to test Lambda logic locally before deploying to AWS.
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock AWS Lambda context
class MockContext:
    """Mock Lambda context for local testing."""
    def __init__(self):
        self.function_name = "alpha-kite-real-time-streamer"
        self.function_version = "$LATEST"
        self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:alpha-kite-real-time-streamer"
        self.memory_limit_in_mb = "256"
        self.aws_request_id = "test-request-id"
        self.log_group_name = "/aws/lambda/alpha-kite-real-time-streamer"
        self.log_stream_name = "test-stream"
    
    def get_remaining_time_in_millis(self):
        return 60000  # 60 seconds


def main():
    """Run Lambda function locally."""
    print("=" * 80)
    print("LOCAL LAMBDA FUNCTION TEST")
    print("=" * 80)
    
    # Check environment variables
    required_env = [
        'SUPABASE_URL',
        'SUPABASE_SERVICE_ROLE_KEY',
        'SCHWAB_APP_KEY',
        'SCHWAB_APP_SECRET'
    ]
    
    missing = [env for env in required_env if not os.environ.get(env)]
    
    if missing:
        print(f"\n❌ Missing environment variables: {', '.join(missing)}")
        print("\nPlease set these in your .env file or export them:")
        for env in missing:
            print(f"  export {env}='your-value-here'")
        return 1
    
    print("\n✅ All required environment variables set")
    
    # Load environment variables from .env file if it exists
    env_file = Path(__file__).parent.parent / '.env'
    if env_file.exists():
        print(f"\n📋 Loading environment from: {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value.strip('"').strip("'")
    
    # Import Lambda handler
    try:
        from real_time_streamer import lambda_handler
    except ImportError as e:
        print(f"\n❌ Failed to import Lambda handler: {e}")
        print("\nMake sure you're in the lambda directory or parent modules are available")
        return 1
    
    # Create mock event and context
    event = {}
    context = MockContext()
    
    print("\n🚀 Invoking Lambda handler...")
    print(f"   Function: {context.function_name}")
    print(f"   Version: {context.function_version}")
    
    try:
        # Call Lambda handler
        response = lambda_handler(event, context)
        
        print("\n📤 Lambda Response:")
        print(json.dumps(response, indent=2))
        
        # Parse response body if it's a string
        if isinstance(response.get('body'), str):
            body = json.loads(response['body'])
            print("\n📊 Response Body:")
            print(json.dumps(body, indent=2))
            
            # Check status
            if response['statusCode'] == 200:
                print("\n✅ Lambda execution successful!")
                
                if body.get('skipped'):
                    print("   ⚠️  Market is closed - no data fetched")
                else:
                    print(f"   Ticker: {body.get('ticker')}")
                    print(f"   Timestamp: {body.get('timestamp')}")
                    print(f"   Equity rows: {body.get('equity_rows')}")
                    print(f"   Indicator rows: {body.get('indicator_rows')}")
            else:
                print(f"\n❌ Lambda execution failed with status {response['statusCode']}")
                if 'error' in body:
                    print(f"   Error: {body['error']}")
        
        return 0 if response['statusCode'] == 200 else 1
        
    except Exception as e:
        print(f"\n❌ Lambda execution error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

