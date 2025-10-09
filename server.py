#!/usr/bin/env python3
"""
Multi-threaded HTTP Server
A comprehensive HTTP server implementation for Computer Networking assignment
"""

import socket
import threading
import sys
import os
import mimetypes
import time
from urllib.parse import unquote
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler()
    ]
)

class HTTPServer:
    def __init__(self, host='127.0.0.1', port=8080, document_root='.'):
        self.host = host
        self.port = port
        self.document_root = os.path.abspath(document_root)
        self.server_socket = None
        
    def parse_request(self, request_data):
        """Parse HTTP request and extract method, path, headers"""
        try:
            lines = request_data.split('\r\n')
            if not lines:
                return None
                
            # Parse request line
            request_line = lines[0]
            parts = request_line.split()
            if len(parts) < 3:
                return None
                
            method = parts[0]
            path = parts[1]
            version = parts[2]
            
            # Parse headers
            headers = {}
            for line in lines[1:]:
                if line == '':
                    break
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip().lower()] = value.strip()
            
            return {
                'method': method,
                'path': path,
                'version': version,
                'headers': headers
            }
        except Exception as e:
            logging.error(f"Error parsing request: {e}")
            return None
    
    def get_content_type(self, file_path):
        """Get MIME type for file"""
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or 'application/octet-stream'
    
    def serve_file(self, file_path, client_socket):
        """Serve a file to the client"""
        try:
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                self.send_error(client_socket, 404, "File Not Found")
                return
                
            with open(file_path, 'rb') as f:
                content = f.read()
                
            content_type = self.get_content_type(file_path)
            
            response = (
                "HTTP/1.1 200 OK\r\n"
                f"Content-Type: {content_type}\r\n"
                f"Content-Length: {len(content)}\r\n"
                "Connection: close\r\n"
                "\r\n"
            )
            
            client_socket.send(response.encode())
            client_socket.send(content)
            
            logging.info(f"Served file: {file_path}")
            
        except Exception as e:
            logging.error(f"Error serving file {file_path}: {e}")
            self.send_error(client_socket, 500, "Internal Server Error")
    
    def list_directory(self, dir_path, request_path, client_socket):
        """Generate directory listing"""
        try:
            files = os.listdir(dir_path)
            files.sort()
            
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Directory listing for {request_path}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        ul {{ list-style-type: none; padding: 0; }}
        li {{ margin: 5px 0; }}
        a {{ text-decoration: none; color: #0066cc; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>Directory listing for {request_path}</h1>
    <ul>
"""
            
            # Add parent directory link if not root
            if request_path != '/':
                parent_path = '/'.join(request_path.rstrip('/').split('/')[:-1]) or '/'
                html_content += f'        <li><a href="{parent_path}">../</a></li>\n'
            
            # Add file/directory links
            for file in files:
                file_path = os.path.join(dir_path, file)
                is_dir = os.path.isdir(file_path)
                display_name = file + ('/' if is_dir else '')
                link_path = request_path.rstrip('/') + '/' + file
                
                html_content += f'        <li><a href="{link_path}">{display_name}</a></li>\n'
            
            html_content += """
    </ul>
</body>
</html>
"""
            
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html\r\n"
                f"Content-Length: {len(html_content.encode())}\r\n"
                "Connection: close\r\n"
                "\r\n"
            )
            
            client_socket.send(response.encode())
            client_socket.send(html_content.encode())
            
            logging.info(f"Directory listing for: {request_path}")
            
        except Exception as e:
            logging.error(f"Error listing directory {dir_path}: {e}")
            self.send_error(client_socket, 500, "Internal Server Error")
    
    def send_error(self, client_socket, status_code, message):
        """Send HTTP error response"""
        status_messages = {
            400: "Bad Request",
            404: "Not Found",
            405: "Method Not Allowed",
            500: "Internal Server Error"
        }
        
        status_text = status_messages.get(status_code, "Unknown Error")
        
        error_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{status_code} {status_text}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; text-align: center; }}
        h1 {{ color: #cc0000; }}
    </style>
</head>
<body>
    <h1>{status_code} {status_text}</h1>
    <p>{message}</p>
</body>
</html>
"""
        
        response = (
            f"HTTP/1.1 {status_code} {status_text}\r\n"
            "Content-Type: text/html\r\n"
            f"Content-Length: {len(error_html.encode())}\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        
        try:
            client_socket.send(response.encode())
            client_socket.send(error_html.encode())
        except Exception as e:
            logging.error(f"Error sending error response: {e}")
    
    def handle_client(self, client_socket, client_address):
        """Handle a single client connection in a separate thread"""
        logging.info(f"New connection from {client_address[0]}:{client_address[1]}")
        
        try:
            # Receive request data
            request_data = client_socket.recv(4096).decode('utf-8')
            if not request_data:
                return
            
            # Parse the request
            request = self.parse_request(request_data)
            if not request:
                self.send_error(client_socket, 400, "Bad Request")
                return
            
            method = request['method']
            path = request['path']
            
            logging.info(f"{client_address[0]}:{client_address[1]} - {method} {path}")
            
            # Handle different HTTP methods
            if method not in ['GET', 'HEAD']:
                self.send_error(client_socket, 405, "Method Not Allowed")
                return
            
            # Decode URL path
            decoded_path = unquote(path)
            
            # Prevent path traversal attacks
            if '..' in decoded_path or decoded_path.startswith('/'):
                # Construct safe file path
                if decoded_path == '/':
                    file_path = os.path.join(self.document_root, 'index.html')
                    if not os.path.exists(file_path):
                        file_path = self.document_root
                else:
                    file_path = os.path.join(self.document_root, decoded_path.lstrip('/'))
                    file_path = os.path.abspath(file_path)
                
                # Ensure the file is within document root
                if not file_path.startswith(self.document_root):
                    self.send_error(client_socket, 403, "Forbidden")
                    return
                
                # Serve file or directory
                if os.path.isdir(file_path):
                    self.list_directory(file_path, path, client_socket)
                elif os.path.isfile(file_path):
                    if method == 'HEAD':
                        # For HEAD requests, send headers only
                        self.send_head_response(file_path, client_socket)
                    else:
                        self.serve_file(file_path, client_socket)
                else:
                    self.send_error(client_socket, 404, "File Not Found")
            else:
                self.send_error(client_socket, 400, "Bad Request")
                
        except Exception as e:
            logging.error(f"Error handling client {client_address}: {e}")
            self.send_error(client_socket, 500, "Internal Server Error")
        finally:
            client_socket.close()
            logging.info(f"Connection closed for {client_address[0]}:{client_address[1]}")
    
    def send_head_response(self, file_path, client_socket):
        """Send HEAD response (headers only)"""
        try:
            file_size = os.path.getsize(file_path)
            content_type = self.get_content_type(file_path)
            
            response = (
                "HTTP/1.1 200 OK\r\n"
                f"Content-Type: {content_type}\r\n"
                f"Content-Length: {file_size}\r\n"
                "Connection: close\r\n"
                "\r\n"
            )
            
            client_socket.send(response.encode())
            
        except Exception as e:
            logging.error(f"Error sending HEAD response for {file_path}: {e}")
            self.send_error(client_socket, 500, "Internal Server Error")

    def start(self):
        """Start the HTTP server"""
        try:
            # Create server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind to host and port
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            logging.info(f"HTTP Server started on {self.host}:{self.port}")
            logging.info(f"Document root: {self.document_root}")
            print(f"Server started on http://{self.host}:{self.port}")
            print(f"Document root: {self.document_root}")
            print("Press Ctrl+C to stop the server")
            
            while True:
                try:
                    # Accept connection
                    client_socket, client_address = self.server_socket.accept()
                    
                    # Create thread for each client
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error as e:
                    if self.server_socket:
                        logging.error(f"Socket error: {e}")
                        break
                        
        except KeyboardInterrupt:
            logging.info("Server shutdown requested")
            print("\nShutting down server...")
        except Exception as e:
            logging.error(f"Server error: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the HTTP server"""
        if self.server_socket:
            self.server_socket.close()
            logging.info("Server stopped")

def main():
    """Main function to start the server"""
    # Parse command line arguments
    port = 8080
    host = '127.0.0.1'
    document_root = '.'
    
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number: {sys.argv[1]}")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        host = sys.argv[2]
    
    if len(sys.argv) > 3:
        document_root = sys.argv[3]
        if not os.path.exists(document_root):
            print(f"Document root does not exist: {document_root}")
            sys.exit(1)
    
    # Create and start server
    server = HTTPServer(host, port, document_root)
    try:
        server.start()
    except Exception as e:
        logging.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


