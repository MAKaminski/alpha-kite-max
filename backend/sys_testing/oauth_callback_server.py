#!/usr/bin/env python3
"""
Simple HTTP server to catch Schwab OAuth callback
Run this before starting the OAuth flow
"""

import http.server
import socketserver
import urllib.parse
import threading
import time
import sys
from pathlib import Path

# Add parent directory to path to import config
sys.path.append(str(Path(__file__).parent.parent))
from schwab_integration.config import SchwabConfig

class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle OAuth callback"""
        print(f"\n🔔 OAuth Callback Received!")
        print(f"📥 URL: {self.path}")
        
        # Parse the callback URL
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        if 'code' in query_params:
            code = query_params['code'][0]
            print(f"✅ Authorization Code: {code}")
            
            # Save the code to a file for processing
            with open('/tmp/schwab_auth_code.txt', 'w') as f:
                f.write(code)
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            response = """
            <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: green;">✅ Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                <p><strong>Authorization Code:</strong> <code>{}</code></p>
                <p style="color: gray; font-size: 12px;">Code saved to /tmp/schwab_auth_code.txt</p>
            </body>
            </html>
            """.format(code)
            
            self.wfile.write(response.encode())
            
            # Stop the server
            print("🛑 Stopping callback server...")
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            
        else:
            # Error case
            error = query_params.get('error', ['Unknown error'])[0]
            print(f"❌ OAuth Error: {error}")
            
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            response = f"""
            <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: red;">❌ Authorization Failed</h1>
                <p>Error: {error}</p>
                <p>Please try again.</p>
            </body>
            </html>
            """
            
            self.wfile.write(response.encode())
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

def start_callback_server():
    """Start the callback server"""
    PORT = 8182
    
    try:
        with socketserver.TCPServer(("127.0.0.1", PORT), CallbackHandler) as httpd:
            print(f"🚀 OAuth Callback Server started on http://127.0.0.1:{PORT}")
            print("⏳ Waiting for OAuth callback...")
            print("💡 Now run the OAuth flow in another terminal")
            print()
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")

if __name__ == "__main__":
    start_callback_server()
