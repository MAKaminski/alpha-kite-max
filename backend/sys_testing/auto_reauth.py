#!/usr/bin/env python3
"""
One-Command Schwab OAuth Re-Authorization

Usage: python3 auto_reauth.py

This script:
1. Opens browser to Schwab OAuth
2. Waits for you to click "Allow"
3. Automatically captures callback
4. Exchanges code for tokens
5. Uploads to AWS Secrets Manager
6. Tests API access

NO manual copying, pasting, or terminal commands!
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Run the automated OAuth flow"""
    script_dir = Path(__file__).parent
    automated_script = script_dir / "automated_oauth_flow.py"
    
    print("🤖 Starting Automated Schwab OAuth Re-Authorization")
    print("   This will open your browser and handle everything automatically!")
    print()
    
    # Check if required dependencies are installed
    try:
        import requests
        import boto3
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Installing required packages...")
        
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "requests", "boto3"], check=True)
            print("✅ Dependencies installed!")
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies")
            print("   Please run: pip install requests boto3")
            return 1
    
    # Run the automated OAuth flow
    try:
        result = subprocess.run([sys.executable, str(automated_script)], check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"❌ OAuth flow failed with exit code {e.returncode}")
        return e.returncode
    except KeyboardInterrupt:
        print("\n⚠️  OAuth flow cancelled by user")
        return 1

if __name__ == "__main__":
    exit(main())