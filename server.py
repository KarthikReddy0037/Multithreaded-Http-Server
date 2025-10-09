#!/usr/bin/env python3
"""
Multi-threaded HTTP Server
- Handles GET and POST requests
- Binary file transfers with chunked reading
- Thread pool for concurrent client connections
- Comprehensive security validation
- Full HTTP/1.1 protocol compliance
"""

import socket
import threading
import sys
import os
import json
import logging
from datetime import datetime
from email.utils import formatdate
from concurrent.futures import ThreadPoolExecutor

# Supported content types
CONTENT_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.txt': 'application/octet-stream',
    '.jpg': 'application/octet-stream',
    '.jpeg': 'application/octet-stream',
    '.png': 'application/octet-stream'
}

# Configuration constants
MAX_HEADER_SIZE = 8192
CHUNK_SIZE = 8192
REQUEST_TIMEOUT = 30
MAX_REQUESTS_PER_CONNECTION = 100


def setup_logging():
    """Configure dual logging to file and console with timestamps"""
    formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    file_handler = logging.FileHandler('server.log', mode='a')
    file_handler.setFormatter(formatter)
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    
    return logger


def is_safe_path(path):
    """Validate path to prevent directory traversal attacks"""
    path = path.lstrip('/')
    return '..' not in path and not os.path.isabs(path)


def send_response(sock, status, headers, body=b""):
    """Send HTTP response with standard headers"""
    if "Date" not in headers:
        headers["Date"] = formatdate(timeval=None, localtime=False, usegmt=True)
    if "Server" not in headers:
        headers["Server"] = "Multi-threaded HTTP Server"
    
    response = f"HTTP/1.1 {status}\r\n"
    response += "\r\n".join(f"{key}: {value}" for key, value in headers.items())
    response += "\r\n\r\n"
    sock.sendall(response.encode() + body)


def send_error(sock, code, message):
    """Send JSON error response"""
    body = json.dumps({"error": message}).encode()
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
        "Connection": "close"
    }
    send_response(sock, f"{code} {message}", headers, body)


def receive_request(sock, timeout=REQUEST_TIMEOUT):
    """Receive and parse HTTP request with body handling"""
    sock.settimeout(timeout)
    try:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = sock.recv(4096)
            if not chunk:
                return None
            data += chunk
            if len(data) > MAX_HEADER_SIZE:
                return None
        
        header_end = data.index(b"\r\n\r\n")
        headers_text = data[:header_end].decode('utf-8', errors='ignore')
        
        # Extract Content-Length if present
        content_length = 0
        for line in headers_text.split('\r\n'):
            if line.lower().startswith('content-length:'):
                content_length = int(line.split(':', 1)[1].strip())
                break
        
        # Read request body if Content-Length is specified
        body_start = header_end + 4
        body = data[body_start:]
        while len(body) < content_length:
            chunk = sock.recv(4096)
            if not chunk:
                break
            body += chunk
        
        return data[:body_start] + body[:content_length]
    except (socket.timeout, Exception):
        return None


def handle_get(sock, path, keep_alive, logger, thread_id):
    """Handle GET request - serve files from resources directory"""
    if path == '/':
        path = '/index.html'
    
    # Security: validate path
    if not is_safe_path(path):
        logger.warning(f"[{thread_id}] Blocked path traversal: {path}")
        send_error(sock, 403, "Forbidden")
        return False
    
    file_path = os.path.join('resources', path.lstrip('/'))
    
    # Check file exists
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        logger.warning(f"[{thread_id}] File not found: {path}")
        send_error(sock, 404, "Not Found")
        return False
    
    # Validate file type
    ext = os.path.splitext(file_path)[1]
    if ext not in CONTENT_TYPES:
        logger.warning(f"[{thread_id}] Unsupported file type: {ext}")
        send_error(sock, 415, "Unsupported Media Type")
        return False
    
    # Prepare response headers
    file_size = os.path.getsize(file_path)
    headers = {
        "Content-Type": CONTENT_TYPES[ext],
        "Content-Length": str(file_size),
        "Connection": "keep-alive" if keep_alive else "close"
    }
    
    if keep_alive:
        headers["Keep-Alive"] = "timeout=30, max=100"
    
    # Send file
    filename = os.path.basename(file_path)
    if ext == '.html':
        with open(file_path, 'rb') as f:
            send_response(sock, "200 OK", headers, f.read())
        logger.info(f"[{thread_id}] Sent HTML: {filename} ({file_size} bytes)")
    else:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        send_response(sock, "200 OK", headers)
        logger.info(f"[{thread_id}] Sending binary: {filename} ({file_size} bytes)")
        with open(file_path, 'rb') as f:
            while chunk := f.read(CHUNK_SIZE):
                sock.sendall(chunk)
    
    logger.info(f"[{thread_id}] Response: 200 OK ({file_size} bytes transferred)")
    return True


def handle_post(sock, request, keep_alive, logger, thread_id):
    """Handle POST request - JSON upload to /upload endpoint"""
    lines = request.decode('utf-8', errors='ignore').split('\r\n')
    request_line = lines[0]
    path = request_line.split()[1]
    
    # Only accept POST to /upload
    if path != '/upload':
        logger.warning(f"[{thread_id}] POST to invalid path: {path}")
        send_error(sock, 405, "Method Not Allowed")
        return False
    
    # Parse headers
    headers = {}
    for line in lines[1:]:
        if ':' in line:
            key, val = line.split(':', 1)
            headers[key.strip().lower()] = val.strip()
    
    # Validate Content-Type
    if 'application/json' not in headers.get('content-type', ''):
        logger.warning(f"[{thread_id}] Invalid Content-Type for POST")
        send_error(sock, 415, "Unsupported Media Type")
        return False
    
    # Parse JSON body
    try:
        header_end = request.index(b'\r\n\r\n')
        body = request[header_end + 4:].decode('utf-8')
        data = json.loads(body)
    except Exception as e:
        logger.warning(f"[{thread_id}] Invalid JSON: {e}")
        send_error(sock, 400, "Bad Request")
        return False
    
    # Save uploaded JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    thread_num = threading.get_ident() % 10000
    filename = f"upload_{timestamp}_{thread_num:04d}.json"
    filepath = os.path.join('resources', 'uploads', filename)
    
    with open(filepath, 'w') as f:
        json.dump(data, f)
    
    logger.info(f"[{thread_id}] Saved upload: {filename}")
    
    # Send success response
    response_data = {
        "status": "success",
        "message": "File created successfully",
        "filepath": f"/uploads/{filename}"
    }
    response_body = json.dumps(response_data).encode()
    
    response_headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(response_body)),
        "Connection": "keep-alive" if keep_alive else "close"
    }
    
    if keep_alive:
        response_headers["Keep-Alive"] = "timeout=30, max=100"
    
    send_response(sock, "201 Created", response_headers, response_body)
    logger.info(f"[{thread_id}] Response: 201 Created")
    return True


def handle_client(sock, addr, server_host, server_port, logger):
    """Handle client connection with HTTP/1.1 persistent connections"""
    thread_id = threading.current_thread().name
    logger.info(f"[{thread_id}] Connection from {addr[0]}:{addr[1]}")
    
    try:
        for _ in range(MAX_REQUESTS_PER_CONNECTION):
            request = receive_request(sock)
            if not request:
                break
            
            # Parse request line
            lines = request.decode('utf-8', errors='ignore').split('\r\n')
            parts = lines[0].split()
            
            if len(parts) < 3:
                logger.warning(f"[{thread_id}] Invalid request line")
                send_error(sock, 400, "Bad Request")
                break
            
            method, path, version = parts
            logger.info(f"[{thread_id}] Request: {method} {path} {version}")
            
            # Parse headers
            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    key, val = line.split(':', 1)
                    headers[key.strip().lower()] = val.strip()
            
            # Validate Host header
            host_header = headers.get('host', '')
            if not host_header:
                logger.warning(f"[{thread_id}] Missing Host header")
                send_error(sock, 400, "Bad Request")
                break
            
            expected_hosts = [f"{server_host}:{server_port}", f"localhost:{server_port}", f"127.0.0.1:{server_port}"]
            if host_header not in expected_hosts:
                logger.warning(f"[{thread_id}] Invalid Host: {host_header}")
                send_error(sock, 403, "Forbidden")
                break
            
            logger.info(f"[{thread_id}] Host validation: {host_header} ✓")
            
            # Determine connection persistence
            connection = headers.get('connection', '').lower()
            keep_alive = (version == 'HTTP/1.1' and connection != 'close') or connection == 'keep-alive'
            
            # Route request by method
            if method == 'GET':
                handle_get(sock, path, keep_alive, logger, thread_id)
            elif method == 'POST':
                handle_post(sock, request, keep_alive, logger, thread_id)
            else:
                logger.warning(f"[{thread_id}] Method {method} not allowed")
                send_error(sock, 405, "Method Not Allowed")
                break
            
            # Log and handle connection status
            logger.info(f"[{thread_id}] Connection: {'keep-alive' if keep_alive else 'close'}")
            if not keep_alive:
                break
    
    except Exception as e:
        logger.error(f"[{thread_id}] Error: {e}")
    finally:
        sock.close()
        logger.info(f"[{thread_id}] Connection closed")


def start_server(host='127.0.0.1', port=8080, max_workers=10):
    """Initialize and start the HTTP server"""
    logger = setup_logging()
    
    # Create and configure server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(50)
    
    # Log server startup
    logger.info(f"HTTP Server started on http://{host}:{port}")
    logger.info(f"Thread pool size: {max_workers}")
    logger.info("Serving files from 'resources' directory")
    logger.info("Press Ctrl+C to stop the server")
    
    # Handle connections with thread pool
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        connection_count = 0
        try:
            while True:
                client_sock, client_addr = server_socket.accept()
                connection_count += 1
                
                # Periodic thread pool status logging
                if connection_count % 10 == 0:
                    active = threading.active_count()
                    logger.info(f"Thread pool status: {active} threads active, {connection_count} total connections")
                
                executor.submit(handle_client, client_sock, client_addr, host, port, logger)
        except KeyboardInterrupt:
            logger.info("Stopping server...")
        finally:
            server_socket.close()
            logger.info("Server stopped")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    host = sys.argv[2] if len(sys.argv) > 2 else '127.0.0.1'
    max_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    start_server(host, port, max_workers)
