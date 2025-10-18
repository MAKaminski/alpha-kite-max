#!/usr/bin/env python3
"""
Debug callback server with enhanced logging for VS Code debugging
"""

import http.server
import socketserver
import urllib.parse
import json
import sys
from pathlib import Path
from datetime import datetime

PORT = 8182

class DebugCallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n{'='*60}")
        print(f"🔔 [{timestamp}] CALLBACK RECEIVED!")
        print(f"{'='*60}")
        print(f"📥 Full URL: {self.path}")
        print(f"📥 Method: {self.command}")
        print(f"📥 Headers:")
        for header, value in self.headers.items():
            print(f"   {header}: {value}")
        
        # Parse the callback URL
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        print(f"\n📥 Parsed URL: {parsed_url}")
        print(f"📥 Query params: {json.dumps(query_params, indent=2)}")
        
        # Set breakpoint here for debugging
        # import pdb; pdb.set_trace()
        
        if 'code' in query_params:
            code = query_params['code'][0]
            print(f"\n✅ SUCCESS - Authorization Code received!")
            print(f"🔑 Code: {code}")
            
            # Save the code to file
            code_file = '/tmp/schwab_auth_code.txt'
            with open(code_file, 'w') as f:
                f.write(code)
            print(f"💾 Code saved to: {code_file}")
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            response = f"""
            <html>
            <head>
                <title>OAuth Success</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f8f0; }}
                    .success {{ color: green; }}
                    .code {{ background: #e8f5e8; padding: 10px; border-radius: 5px; margin: 20px; }}
                </style>
            </head>
            <body>
                <h1 class="success">✅ Authorization Successful!</h1>
                <p>Authorization Code received and saved.</p>
                <div class="code">
                    <strong>Code:</strong> {code}
                </div>
                <p>You can close this window and check the terminal for next steps.</p>
                <p><small>Code saved to /tmp/schwab_auth_code.txt</small></p>
            </body>
            </html>
            """
            
            self.wfile.write(response.encode())
            print(f"✅ Success response sent to browser")
            
        elif 'error' in query_params:
            error = query_params['error'][0]
            error_description = query_params.get('error_description', [''])[0]
            error_uri = query_params.get('error_uri', [''])[0]
            
            print(f"\n❌ OAUTH ERROR!")
            print(f"🚨 Error Code: {error}")
            print(f"📝 Description: {error_description}")
            print(f"🔗 Error URI: {error_uri}")
            
            # Send error response
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            response = f"""
            <html>
            <head>
                <title>OAuth Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #fff0f0; }}
                    .error {{ color: red; }}
                    .details {{ background: #ffe8e8; padding: 10px; border-radius: 5px; margin: 20px; text-align: left; }}
                </style>
            </head>
            <body>
                <h1 class="error">❌ Authorization Failed</h1>
                <div class="details">
                    <p><strong>Error:</strong> {error}</p>
                    <p><strong>Description:</strong> {error_description}</p>
                    <p><strong>URI:</strong> {error_uri}</p>
                </div>
                <p>Check the terminal for more debugging information.</p>
            </body>
            </html>
            """
            
            self.wfile.write(response.encode())
            print(f"❌ Error response sent to browser")
            
        else:
            print(f"\n❓ UNKNOWN CALLBACK")
            print(f"🚫 No 'code' or 'error' parameter found")
            print(f"📋 All parameters: {list(query_params.keys())}")
            
            # Send unknown response
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            response = f"""
            <html>
            <head>
                <title>Unknown Callback</title>
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #fff8f0; }}
                    .warning {{ color: orange; }}
                    .details {{ background: #fff8e8; padding: 10px; border-radius: 5px; margin: 20px; text-align: left; }}
                </style>
            </head>
            <body>
                <h1 class="warning">❓ Unknown Callback</h1>
                <p>No authorization code or error found in the callback.</p>
                <div class="details">
                    <p><strong>Received parameters:</strong> {', '.join(query_params.keys())}</p>
                    <p><strong>Full URL:</strong> {self.path}</p>
                </div>
                <p>Check the terminal for debugging information.</p>
            </body>
            </html>
            """
            
            self.wfile.write(response.encode())
            print(f"❓ Unknown response sent to browser")
        
        print(f"{'='*60}")
    
    def log_message(self, format, *args):
        """Suppress default HTTP server logging"""
        pass

def main():
    print(f"🚀 Debug OAuth Callback Server")
    print(f"{'='*50}")
    print(f"📍 Port: {PORT}")
    print(f"🌐 URL: http://127.0.0.1:{PORT}")
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")
    print("💡 Ready to receive OAuth callbacks!")
    print("🔧 Set breakpoints in the do_GET method for debugging")
    print("🛑 Press Ctrl+C to stop")
    print()
    
    try:
        with socketserver.TCPServer(("127.0.0.1", PORT), DebugCallbackHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
