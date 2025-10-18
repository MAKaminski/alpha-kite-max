#!/usr/bin/env python3
"""
Standalone OAuth callback server without dependencies.
This avoids the pydantic version conflict issues.
"""

import http.server
import socketserver
import urllib.parse
import json
from datetime import datetime

class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"\n{'='*70}")
        print(f"🔔 CALLBACK RECEIVED at {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*70}")
        print(f"Path: {self.path}")
        print(f"Headers: {dict(self.headers)}")
        print()
        
        # Parse query parameters
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        print("📋 Query Parameters:")
        for key, value in query_params.items():
            print(f"   {key}: {value[0] if value else 'None'}")
        print()
        
        if 'code' in query_params:
            code = query_params['code'][0]
            state = query_params.get('state', [''])[0]
            
            print(f"✅ SUCCESS! Authorization code received: {code[:20]}...")
            if state:
                print(f"✅ State: {state[:20]}...")
            print()
            print("🎯 Next steps:")
            print(f"   python3 simple_callback_processor.py \"{self.path}\"")
            print()
        elif 'error' in query_params:
            error = query_params['error'][0]
            error_desc = query_params.get('error_description', [''])[0]
            print(f"❌ ERROR: {error}")
            if error_desc:
                print(f"   Description: {error_desc}")
            print()
        else:
            print("⚠️  No authorization code or error found in URL")
            print()
        
        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>OAuth Callback</title>
            <style>
                body { 
                    font-family: Arial, sans-serif; 
                    text-align: center; 
                    padding: 50px;
                    background: #f5f5f5;
                }
                .container {
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    max-width: 600px;
                    margin: 0 auto;
                }
                .success { color: #28a745; font-weight: bold; }
                .error { color: #dc3545; font-weight: bold; }
                .info { color: #007bff; }
                .code { 
                    background: #f8f9fa; 
                    padding: 10px; 
                    border-radius: 5px; 
                    font-family: monospace;
                    word-break: break-all;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>OAuth Callback Received</h1>
                <p class="info">Check the terminal for details.</p>
                <p>You can close this window.</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

def run_server():
    PORT = 8182
    print(f"🚀 Starting standalone callback server on port {PORT}")
    print(f"   URL: https://127.0.0.1:{PORT}")
    print(f"   (No trailing slash - matches your registered callback)")
    print()
    print("🔗 Try this OAuth URL:")
    print("https://api.schwabapi.com/v1/oauth/authorize?response_type=code&client_id=Os3C2znHkqciGVi5IMHlq7NeXqbEenDfGrnj5sijzJfRCGhU&redirect_uri=https%3A//127.0.0.1%3A8182&state=test123")
    print()
    print("Press Ctrl+C to stop the server")
    print("="*70)
    
    try:
        with socketserver.TCPServer(("", PORT), CallbackHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {PORT} is already in use")
            print("   Kill existing process or use a different port")
        else:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_server()
