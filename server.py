#!/usr/bin/env python3
import socket
import threading
import sys
import os
import json
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Content type mapping - simpler than multiple if statements
CONTENT_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.txt': 'application/octet-stream',
    '.jpg': 'application/octet-stream',
    '.jpeg': 'application/octet-stream',
    '.png': 'application/octet-stream'
}

def setup_logging():
    """Setup logging to both file and console"""
    # Force unbuffered file writing
    file_handler = logging.FileHandler('server.log', mode='a')
    file_handler.setLevel(logging.INFO)
    
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    
    return logger

def is_safe_path(path):
    """Check if path is safe (no directory traversal)"""
    path = path.lstrip('/')
    if '..' in path or os.path.isabs(path):
        return False
    return True

def send_response(sock, status, headers, body=b""):
    """Send HTTP response"""
    response = f"HTTP/1.1 {status}\r\n"
    for key, value in headers.items():
        response += f"{key}: {value}\r\n"
    response += "\r\n"
    sock.sendall(response.encode() + body)

def send_error(sock, code, message):
    """Send error response"""
    body = json.dumps({"error": message}).encode()
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
        "Connection": "close"
    }
    send_response(sock, f"{code} {message}", headers, body)

def receive_request(sock, timeout=30):
    """Receive HTTP request with timeout"""
    sock.settimeout(timeout)
    try:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = sock.recv(4096)
            if not chunk:
                return None
            data += chunk
            if len(data) > 8192:  # prevent too large headers
                return None
        
        # If there's a body, read it based on Content-Length
        header_end = data.index(b"\r\n\r\n")
        headers_text = data[:header_end].decode('utf-8', errors='ignore')
        
        content_length = 0
        for line in headers_text.split('\r\n'):
            if line.lower().startswith('content-length:'):
                content_length = int(line.split(':', 1)[1].strip())
                break
        
        body_start = header_end + 4
        body = data[body_start:]
        
        while len(body) < content_length:
            chunk = sock.recv(4096)
            if not chunk:
                break
            body += chunk
        
        return data[:body_start] + body[:content_length]
    except socket.timeout:
        return None
    except Exception:
        return None

def handle_get(sock, path, keep_alive, logger, thread_id):
    """Handle GET request"""
    if path == '/':
        path = '/index.html'
    
    if not is_safe_path(path):
        logger.warning(f"[{thread_id}] Blocked unsafe path: {path} - Path traversal attempt")
        logger.warning(f"[{thread_id}] Response: 403 Forbidden")
        send_error(sock, 403, "Forbidden")
        return False
    
    file_path = os.path.join('resources', path.lstrip('/'))
    
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        logger.warning(f"[{thread_id}] File not found: {path}")
        logger.warning(f"[{thread_id}] Response: 404 Not Found")
        send_error(sock, 404, "Not Found")
        return False
    
    # Check file extension is allowed
    ext = os.path.splitext(file_path)[1]
    if ext not in CONTENT_TYPES:
        logger.warning(f"[{thread_id}] Unsupported file type: {ext}")
        logger.warning(f"[{thread_id}] Response: 415 Unsupported Media Type")
        send_error(sock, 415, "Unsupported Media Type")
        return False
    
    content_type = CONTENT_TYPES[ext]
    file_size = os.path.getsize(file_path)
    
    headers = {
        "Content-Type": content_type,
        "Content-Length": str(file_size),
        "Connection": "keep-alive" if keep_alive else "close"
    }
    
    # HTML files displayed inline, others as download
    if ext == '.html':
        with open(file_path, 'rb') as f:
            body = f.read()
        send_response(sock, "200 OK", headers, body)
        logger.info(f"[{thread_id}] Sent HTML: {os.path.basename(file_path)} ({file_size} bytes)")
        logger.info(f"[{thread_id}] Response: 200 OK ({file_size} bytes transferred)")
    else:
        filename = os.path.basename(file_path)
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        send_response(sock, "200 OK", headers)
        logger.info(f"[{thread_id}] Sending binary file: {filename} ({file_size} bytes)")
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sock.sendall(chunk)
        logger.info(f"[{thread_id}] Response: 200 OK ({file_size} bytes transferred)")
    
    return True

def handle_post(sock, request, keep_alive, logger, thread_id):
    """Handle POST request for JSON upload"""
    lines = request.decode('utf-8', errors='ignore').split('\r\n')
    
    # Parse request line and headers
    request_line = lines[0]
    path = request_line.split()[1]
    
    if path != '/upload':
        logger.warning(f"[{thread_id}] POST to wrong path: {path}")
        send_error(sock, 405, "Method Not Allowed")
        return False
    
    # Check content-type header
    headers = {}
    for line in lines[1:]:
        if ':' in line:
            key, val = line.split(':', 1)
            headers[key.strip().lower()] = val.strip()
    
    if 'application/json' not in headers.get('content-type', ''):
        logger.warning(f"[{thread_id}] Wrong content-type for POST")
        send_error(sock, 415, "Unsupported Media Type")
        return False
    
    # Extract body
    header_end = request.index(b'\r\n\r\n')
    body = request[header_end + 4:].decode('utf-8')
    
    try:
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
    
    response_data = {
        "status": "success",
        "message": "File created successfully",
        "filepath": f"/uploads/{filename}"
    }
    response_body = json.dumps(response_data).encode()
    
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(response_body)),
        "Connection": "keep-alive" if keep_alive else "close"
    }
    send_response(sock, "201 Created", headers, response_body)
    logger.info(f"[{thread_id}] Response: 201 Created")
    return True

def handle_client(sock, addr, server_host, server_port, logger):
    """Handle client connection with keep-alive support"""
    thread_id = threading.current_thread().name
    logger.info(f"[{thread_id}] Connection from {addr[0]}:{addr[1]}")
    
    try:
        for request_num in range(100):  # max 100 requests per connection
            request = receive_request(sock)
            if not request:
                break
            
            lines = request.decode('utf-8', errors='ignore').split('\r\n')
            request_line = lines[0]
            parts = request_line.split()
            
            if len(parts) < 3:
                logger.warning(f"[{thread_id}] Bad Request - Invalid request line")
                send_error(sock, 400, "Bad Request")
                break
            
            method, path, version = parts[0], parts[1], parts[2]
            
            # Parse headers
            headers = {}
            for line in lines[1:]:
                if ':' in line:
                    key, val = line.split(':', 1)
                    headers[key.strip().lower()] = val.strip()
            
            logger.info(f"[{thread_id}] Request: {method} {path} {version}")
            
            # Validate Host header
            host_header = headers.get('host', '')
            if not host_header:
                logger.warning(f"[{thread_id}] Missing Host header - Returning 400")
                send_error(sock, 400, "Bad Request")
                break
            
            expected_hosts = [f"{server_host}:{server_port}", f"localhost:{server_port}", f"127.0.0.1:{server_port}"]
            if host_header not in expected_hosts:
                logger.warning(f"[{thread_id}] Invalid host: {host_header} - Returning 403")
                send_error(sock, 403, "Forbidden")
                break
            
            logger.info(f"[{thread_id}] Host validation: {host_header} ✓")
            
            # Determine keep-alive
            connection = headers.get('connection', '').lower()
            keep_alive = (version == 'HTTP/1.1' and connection != 'close') or connection == 'keep-alive'
            
            # Route request
            if method == 'GET':
                success = handle_get(sock, path, keep_alive, logger, thread_id)
            elif method == 'POST':
                success = handle_post(sock, request, keep_alive, logger, thread_id)
            else:
                logger.warning(f"[{thread_id}] Method {method} not allowed - Returning 405")
                send_error(sock, 405, "Method Not Allowed")
                break
            
            # Log connection status
            if keep_alive:
                logger.info(f"[{thread_id}] Connection: keep-alive")
            else:
                logger.info(f"[{thread_id}] Connection: close")
                break
    
    except Exception as e:
        logger.error(f"[{thread_id}] Error: {e}")
    finally:
        sock.close()
        logger.info(f"[{thread_id}] Connection closed")

def start_server(host='127.0.0.1', port=8080, max_workers=10):
    """Start the HTTP server"""
    logger = setup_logging()
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(50)
    
    logger.info(f"HTTP Server started on http://{host}:{port}")
    logger.info(f"Thread pool size: {max_workers}")
    logger.info("Serving files from 'resources' directory")
    logger.info("Press Ctrl+C to stop the server")
    
    # Use ThreadPoolExecutor - much simpler than manual queue management
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        try:
            while True:
                client_sock, client_addr = server_socket.accept()
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
