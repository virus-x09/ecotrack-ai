import http.server
import socketserver
import mimetypes
import os

PORT = 5500

# Fix Windows registry MIME type bugs for CSS and JS
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="frontend", **kwargs)

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving frontend directory at http://127.0.0.1:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
