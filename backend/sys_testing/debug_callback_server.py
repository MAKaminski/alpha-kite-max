#!/usr/bin/env python3
"""
Debug callback server to see what Schwab is sending
"""

import http.server
import socketserver
import urllib.parse
import json
from pathlib import Path

PORT = 8182

class DebugHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"\n🔔 CALLBACK RECEIVED!")
        print(f"📥 Full URL: {self.path}")
        print(f"📥 Headers: {dict(self.headers)}")
        
        # Parse the callback URL
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        print(f"📥 Query params: {query_params}")
        
        if 'code' in query_params:
            code = query_params['code'][0]
            print(f"✅ SUCCESS - Authorization Code: {code}")
            
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
            </body>
            </html>
            """
            
            self.wfile.write(response.encode())
            
        elif 'error' in query_params:
            error = query_params['error'][0]
            error_description = query_params.get('error_description', [''])[0]
            print(f"❌ OAUTH ERROR: {error}")
            print(f"❌ Error Description: {error_description}")
            
            # Send error response
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            response = f"""
            <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: red;">❌ Authorization Failed</h1>
                <p><strong>Error:</strong> {error}</p>
                <p><strong>Description:</strong> {error_description}</p>
                <p>Check the terminal for more details.</p>
            </body>
            </html>
            """
            
            self.wfile.write(response.encode())
            
        else:
            print(f"❓ UNKNOWN CALLBACK - No code or error found")
            print(f"📥 All params: {query_params}")
            
            # Send unknown response
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            response = f"""
            <html>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: orange;">❓ Unknown Callback</h1>
                <p>No authorization code or error found.</p>
                <p>Check the terminal for details.</p>
            </body>
            </html>
            """
            
            self.wfile.write(response.encode())
    
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    try:
        with socketserver.TCPServer(("127.0.0.1", PORT), DebugHandler) as httpd:
            print(f"🚀 Debug Callback Server running on http://127.0.0.1:{PORT}")
            print("⏳ Waiting for OAuth callback...")
            print("Press Ctrl+C to stop")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
