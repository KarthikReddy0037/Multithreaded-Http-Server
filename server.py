#!/usr/bin/env python3
import socket
import threading
import sys
import os
import json
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import time

def get_content_type(file_path):
    if file_path.endswith('.html'):
        return 'text/html; charset=utf-8'
    # Per spec, non-HTML served as downloads using application/octet-stream
    if file_path.endswith('.txt'):
        return 'application/octet-stream'
    if file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
        return 'application/octet-stream'
    if file_path.endswith('.png'):
        return 'application/octet-stream'
    return 'application/octet-stream'

def is_good_path(path):
    """Enhanced path validation to prevent directory traversal attacks"""
    # Remove leading slash and normalize path
    path = path.lstrip('/')
    
    # Check for directory traversal attempts
    if '..' in path or path.startswith('/') or path.startswith('\\'):
        return False
    
    # Additional security checks
    normalized_path = os.path.normpath(path)
    
    # Ensure path doesn't escape the resources directory
    if normalized_path.startswith('..') or '\\..' in normalized_path or '/..' in normalized_path:
        return False
    
    # Block absolute paths and UNC paths
    if os.path.isabs(normalized_path) or normalized_path.startswith('\\\\'):
        return False
        
    return True

def setup_logging():
    """Setup comprehensive logging to both console and file"""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler('server.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def rfc7231_date():
    return datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')

def parse_headers(raw_request: str):
    lines = raw_request.split('\r\n')
    headers = {}
    for line in lines[1:]:
        if not line:
            break
        if ':' in line:
            k, v = line.split(':', 1)
            headers[k.strip().lower()] = v.strip()
    return headers

def handle_client(client_socket, client_address, server_host, server_port, logger, keep_alive_timeout=30, max_requests=100):
    thread_id = threading.current_thread().name
    logger.info(f"[{thread_id}] Connection from {client_address[0]}:{client_address[1]}")
    
    try:
        client_socket.settimeout(keep_alive_timeout)
        num_requests = 0
        while num_requests < max_requests:
            data = b''
            try:
                chunk = client_socket.recv(8192)
                if not chunk:
                    logger.info(f"[{thread_id}] Connection closed by client")
                    break
                data += chunk
                # simple read; for small requests this is enough
            except socket.timeout:
                logger.info(f"[{thread_id}] Connection timeout")
                break

            request = data.decode('utf-8', errors='ignore')
            if not request:
                break

            lines = request.split('\r\n')
            request_line = lines[0] if lines else ''
            parts = request_line.split()
            if len(parts) < 3:
                logger.warning(f"[{thread_id}] Malformed request: {request_line}")
                client_socket.sendall(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n")
                break

            method, path, version = parts[0], parts[1], parts[2]
            headers = parse_headers(request)
            
            logger.info(f"[{thread_id}] Request: {method} {path} {version}")

            # Host validation
            host_header = headers.get('host')
            expected_host = f"{server_host}:{server_port}"
            if not host_header:
                logger.warning(f"[{thread_id}] Missing Host header")
                client_socket.sendall(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n")
                break
            if host_header not in (expected_host, f"localhost:{server_port}", f"127.0.0.1:{server_port}"):
                logger.warning(f"[{thread_id}] Host validation failed: {host_header} (expected {expected_host})")
                client_socket.sendall(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n")
                break
            
            logger.info(f"[{thread_id}] Host validation: {host_header} ✓")

            connection_header = headers.get('connection', '').lower()
            keep_alive = (version == 'HTTP/1.1' and connection_header != 'close') or connection_header == 'keep-alive'

            if method == 'GET':
                handled = handle_get_request(client_socket, path, headers, keep_alive, logger, thread_id)
            elif method == 'POST':
                handled = handle_post_upload(client_socket, request, headers, path, keep_alive, logger, thread_id)
            else:
                logger.warning(f"[{thread_id}] Method not allowed: {method}")
                client_socket.sendall(b"HTTP/1.1 405 Method Not Allowed\r\nConnection: close\r\n\r\n")
                handled = False

            num_requests += 1
            if not keep_alive:
                logger.info(f"[{thread_id}] Connection: close")
                break
            else:
                logger.info(f"[{thread_id}] Connection: keep-alive")
        
    except Exception as e:
        logger.error(f"[{thread_id}] Client error: {e}")
    finally:
        try:
            client_socket.close()
            logger.info(f"[{thread_id}] Connection closed")
        except Exception:
            pass

def handle_get_request(client_socket, path, headers, keep_alive, logger, thread_id):
    if path == '/':
        path = '/index.html'
    if not is_good_path(path):
        logger.warning(f"[{thread_id}] Path traversal attempt blocked: {path}")
        client_socket.sendall(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n")
        return False

    file_path = os.path.join('resources', path.lstrip('/'))
    if not (os.path.exists(file_path) and os.path.isfile(file_path)):
        logger.warning(f"[{thread_id}] File not found: {file_path}")
        client_socket.sendall(b"HTTP/1.1 404 Not Found\r\nConnection: close\r\n\r\n")
        return False

    # Only support .html, .txt, .png, .jpg/.jpeg per spec, others 415
    allowed = (file_path.endswith('.html') or file_path.endswith('.txt') or
               file_path.endswith('.png') or file_path.endswith('.jpg') or file_path.endswith('.jpeg'))
    if not allowed:
        logger.warning(f"[{thread_id}] Unsupported file type: {file_path}")
        client_socket.sendall(b"HTTP/1.1 415 Unsupported Media Type\r\nConnection: close\r\n\r\n")
        return False

    content_type = get_content_type(file_path)
    date_hdr = rfc7231_date()
    server_hdr = 'Multi-threaded HTTP Server'
    connection_hdr = 'keep-alive' if keep_alive else 'close'

    # HTML inline, others as download with Content-Disposition
    if file_path.endswith('.html'):
        with open(file_path, 'r', encoding='utf-8') as f:
            body = f.read()
        headers_str = (
            f"HTTP/1.1 200 OK\r\n"
            f"Date: {date_hdr}\r\n"
            f"Server: {server_hdr}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body.encode())}\r\n"
            f"Connection: {connection_hdr}\r\n"
        )
        if keep_alive:
            headers_str += "Keep-Alive: timeout=30, max=100\r\n"
        headers_str += "\r\n"
        client_socket.sendall(headers_str.encode() + body.encode())
        logger.info(f"[{thread_id}] Sending HTML file: {os.path.basename(file_path)} ({len(body.encode())} bytes)")
    else:
        filename = os.path.basename(file_path)
        with open(file_path, 'rb') as f:
            body = f.read()
        headers_str = (
            f"HTTP/1.1 200 OK\r\n"
            f"Date: {date_hdr}\r\n"
            f"Server: {server_hdr}\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Content-Disposition: attachment; filename=\"{filename}\"\r\n"
            f"Connection: {connection_hdr}\r\n"
        )
        if keep_alive:
            headers_str += "Keep-Alive: timeout=30, max=100\r\n"
        headers_str += "\r\n"
        client_socket.sendall(headers_str.encode() + body)
        logger.info(f"[{thread_id}] Sending binary file: {filename} ({len(body)} bytes)")
    
    logger.info(f"[{thread_id}] Response: 200 OK ({len(body)} bytes transferred)")
    return True

def handle_post_upload(client_socket, request, headers, path, keep_alive, logger, thread_id):
    # Only accept JSON to /upload
    if path != '/upload':
        logger.warning(f"[{thread_id}] POST to non-upload endpoint: {path}")
        client_socket.sendall(b"HTTP/1.1 405 Method Not Allowed\r\nConnection: close\r\n\r\n")
        return False
    content_type = headers.get('content-type', '')
    if 'application/json' not in content_type:
        logger.warning(f"[{thread_id}] Invalid content type for POST: {content_type}")
        client_socket.sendall(b"HTTP/1.1 415 Unsupported Media Type\r\nConnection: close\r\n\r\n")
        return False
    header_end = request.find('\r\n\r\n')
    if header_end == -1:
        logger.warning(f"[{thread_id}] Malformed POST request")
        client_socket.sendall(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n")
        return False
    body = request[header_end + 4:]
    try:
        data = json.loads(body)
        logger.info(f"[{thread_id}] Received valid JSON data")
    except Exception as e:
        logger.warning(f"[{thread_id}] Invalid JSON in POST body: {e}")
        client_socket.sendall(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\n")
        return False

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    rand = f"{threading.get_ident()%10000:04d}"
    fname = f"upload_{ts}_{rand}.json"
    out_path = os.path.join('resources', 'uploads', fname)
    
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        logger.info(f"[{thread_id}] Created file: {fname}")
    except Exception as e:
        logger.error(f"[{thread_id}] Failed to create file: {e}")
        client_socket.sendall(b"HTTP/1.1 500 Internal Server Error\r\nConnection: close\r\n\r\n")
        return False

    resp_obj = {
        "status": "success",
        "message": "File created successfully",
        "filepath": f"/uploads/{fname}"
    }
    resp_body = json.dumps(resp_obj)
    date_hdr = rfc7231_date()
    server_hdr = 'Multi-threaded HTTP Server'
    connection_hdr = 'keep-alive' if keep_alive else 'close'
    headers_str = (
        f"HTTP/1.1 201 Created\r\n"
        f"Date: {date_hdr}\r\n"
        f"Server: {server_hdr}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(resp_body.encode())}\r\n"
        f"Connection: {connection_hdr}\r\n"
    )
    if keep_alive:
        headers_str += "Keep-Alive: timeout=30, max=100\r\n"
    headers_str += "\r\n"
    client_socket.sendall(headers_str.encode() + resp_body.encode())
    logger.info(f"[{thread_id}] Response: 201 Created")
    return True

def start_server(host='127.0.0.1', port=8080, max_workers=10):
    # Setup logging
    logger = setup_logging()
    
    backlog = 50
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(backlog)

    logger.info(f"HTTP Server started on http://{host}:{port}")
    logger.info(f"Thread pool size: {max_workers}")
    logger.info("Serving files from 'resources' directory")
    logger.info("Press Ctrl+C to stop the server")

    executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="Thread")
    active_connections = 0
    
    def handle_connection_with_503(client_socket, client_address, host, port, logger):
        """Handle connection with 503 Service Unavailable if thread pool is full"""
        try:
            handle_client(client_socket, client_address, host, port, logger)
        except Exception as e:
            logger.error(f"Error in connection handler: {e}")
            try:
                client_socket.sendall(b"HTTP/1.1 503 Service Unavailable\r\nRetry-After: 30\r\nConnection: close\r\n\r\n")
                client_socket.close()
            except:
                pass
    
    try:
        while True:
            try:
                client_socket, client_address = server_socket.accept()
                active_connections += 1
                
                # Submit to thread pool
                try:
                    executor.submit(handle_connection_with_503, client_socket, client_address, host, port, logger)
                except RuntimeError:
                    # Thread pool is shutting down
                    logger.warning("Thread pool shutting down, rejecting connection")
                    client_socket.sendall(b"HTTP/1.1 503 Service Unavailable\r\nRetry-After: 30\r\nConnection: close\r\n\r\n")
                    client_socket.close()
                    continue
                
                # Log thread pool status periodically
                if active_connections % 10 == 0:
                    # Get approximate thread count
                    thread_count = len([t for t in threading.enumerate() if t.name.startswith("Thread")])
                    logger.info(f"Thread pool status: {thread_count}/{max_workers} active")
                    
            except Exception as e:
                logger.error(f"Error accepting connection: {e}")
                continue
                
    except KeyboardInterrupt:
        logger.info("Stopping server...")
    finally:
        logger.info("Shutting down thread pool...")
        executor.shutdown(wait=True)
        server_socket.close()
        logger.info("Server stopped")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    host = sys.argv[2] if len(sys.argv) > 2 else '127.0.0.1'
    max_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    start_server(host, port, max_workers)


