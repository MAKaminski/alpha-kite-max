#!/usr/bin/env python3
"""
Simple callback server for OAuth
"""

import http.server
import socketserver
import urllib.parse
import json
from pathlib import Path

PORT = 8182

class SimpleHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"\n🔔 OAuth Callback Received!")
        print(f"📥 URL: {self.path}")
        
        # Parse the callback URL
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        if 'code' in query_params:
            code = query_params['code'][0]
            print(f"✅ Authorization Code: {code}")
            
            # Save the code
            with open('/tmp/schwab_auth_code.txt', 'w') as f:
                f.write(code)
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            response = f"""
            <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: green;">✅ Authorization Successful!</h1>
                <p>Authorization Code: <strong>{code}</strong></p>
                <p>You can close this window.</p>
                <p>Code saved to /tmp/schwab_auth_code.txt</p>
            </body>
            </html>
            """
            
            self.wfile.write(response.encode())
            print("✅ Success page sent!")
            
        else:
            error = query_params.get('error', ['Unknown error'])[0]
            print(f"❌ OAuth Error: {error}")
            
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            response = f"""
            <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: red;">❌ Authorization Failed</h1>
                <p>Error: {error}</p>
            </body>
            </html>
            """
            
            self.wfile.write(response.encode())
    
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    try:
        with socketserver.TCPServer(("127.0.0.1", PORT), SimpleHandler) as httpd:
            print(f"🚀 OAuth Callback Server running on http://127.0.0.1:{PORT}")
            print("⏳ Waiting for OAuth callback...")
            print("Press Ctrl+C to stop")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
