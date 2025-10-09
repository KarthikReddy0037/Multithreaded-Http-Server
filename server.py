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
import queue

def get_content_type(file_path):
    if file_path.endswith('.html'):
        return 'text/html; charset=utf-8'
    # all other files served as downloads using application/octet-stream
    if file_path.endswith('.txt'):
        return 'application/octet-stream'
    if file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
        return 'application/octet-stream'
    if file_path.endswith('.png'):
        return 'application/octet-stream'
    return 'application/octet-stream'  # default for unknown types

def is_good_path(path):
    """path validation to prevent directory traversal attacks"""
    # Remove leading slash and normalize path
    path = path.lstrip('/')
    
    # check for directory traversal attempts
    if '..' in path or path.startswith('/') or path.startswith('\\'):
        return False
    
    # additional security checks
    normalized_path = os.path.normpath(path)
    
    # make sure path doesn't escape the resources directory
    if normalized_path.startswith('..') or '\\..' in normalized_path or '/..' in normalized_path:
        return False
    
    # block absolute paths and UNC paths
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

def _send_response(client_socket, status_line: str, headers: dict, body: bytes = b""):
    headers_lines = []
    for k, v in headers.items():
        headers_lines.append(f"{k}: {v}")
    header_blob = (status_line + "\r\n" + "\r\n".join(headers_lines) + "\r\n\r\n").encode()
    client_socket.sendall(header_blob)
    if body:
        client_socket.sendall(body)


def _standard_headers(content_type: str, content_length: int, keep_alive: bool):
    headers = {
        "Date": rfc7231_date(),
        "Server": "Multi-threaded HTTP Server",
        "Content-Type": content_type,
        "Content-Length": str(content_length),
        "Connection": "keep-alive" if keep_alive else "close",
    }
    if keep_alive:
        headers["Keep-Alive"] = "timeout=30, max=100"
    return headers


def _send_error(client_socket, code: int, message: str, keep_alive: bool = False):
    status_line = f"HTTP/1.1 {code} {message}"
    body = json.dumps({"error": message}).encode()
    headers = _standard_headers("application/json", len(body), keep_alive)
    _send_response(client_socket, status_line, headers, body)


def _recv_http_request(sock: socket.socket, timeout: int, max_size: int = 8192) -> bytes:
    sock.settimeout(timeout)
    data = bytearray()
    header_end = -1
    while True:
        if len(data) >= max_size:
            break
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            break
        if not chunk:
            break
        data.extend(chunk)
        if header_end == -1:
            idx = data.find(b"\r\n\r\n")
            if idx != -1:
                header_end = idx
                # If Content-Length exists, ensure full body received (but still cap by max_size)
                headers_part = data[:header_end].decode('utf-8', errors='ignore')
                lines = headers_part.split('\r\n')
                cl = 0
                for line in lines[1:]:
                    if line.lower().startswith('content-length:'):
                        try:
                            cl = int(line.split(':', 1)[1].strip())
                        except Exception:
                            cl = 0
                        break
                total_needed = header_end + 4 + cl
                while len(data) < total_needed and len(data) < max_size:
                    more = sock.recv(min(4096, max_size - len(data)))
                    if not more:
                        break
                    data.extend(more)
                break
    return bytes(data)


def handle_client(client_socket, client_address, server_host, server_port, logger, keep_alive_timeout=30, max_requests=100):
    thread_id = threading.current_thread().name
    logger.info(f"[{thread_id}] Connection from {client_address[0]}:{client_address[1]}")
    
    try:
        num_requests = 0
        while num_requests < max_requests:
            data = _recv_http_request(client_socket, keep_alive_timeout, 8192)
            if not data:
                logger.info(f"[{thread_id}] Connection closed or timeout")
                break
            request = data.decode('utf-8', errors='ignore')
            if not request:
                break

            lines = request.split('\r\n')
            request_line = lines[0] if lines else ''
            parts = request_line.split()
            if len(parts) < 3:
                logger.warning(f"[{thread_id}] Malformed request: {request_line}")
                _send_error(client_socket, 400, "Bad Request", keep_alive=False)
                break

            method, path, version = parts[0], parts[1], parts[2]
            headers = parse_headers(request)
            
            logger.info(f"[{thread_id}] Request: {method} {path} {version}")

            # host validation
            host_header = headers.get('host')
            expected_host = f"{server_host}:{server_port}"
            if not host_header:
                logger.warning(f"[{thread_id}] Missing Host header")
                _send_error(client_socket, 400, "Bad Request", keep_alive=False)
                break
            if host_header not in (expected_host, f"localhost:{server_port}", f"127.0.0.1:{server_port}"):
                logger.warning(f"[{thread_id}] Host validation failed: {host_header} (expected {expected_host})")
                _send_error(client_socket, 403, "Forbidden", keep_alive=False)
                break
            
            logger.info(f"[{thread_id}] Host validation: {host_header} OK")

            connection_header = headers.get('connection', '').lower()
            keep_alive = (version == 'HTTP/1.1' and connection_header != 'close') or connection_header == 'keep-alive'

            if method == 'GET':
                handled = handle_get_request(client_socket, path, headers, keep_alive, logger, thread_id)
            elif method == 'POST':
                handled = handle_post_upload(client_socket, request, headers, path, keep_alive, logger, thread_id)
            else:
                logger.warning(f"[{thread_id}] Method not allowed: {method}")
                _send_error(client_socket, 405, "Method Not Allowed", keep_alive=False)
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
        _send_error(client_socket, 403, "Forbidden", keep_alive=False)
        return False

    file_path = os.path.join('resources', path.lstrip('/'))
    if not (os.path.exists(file_path) and os.path.isfile(file_path)):
        logger.warning(f"[{thread_id}] File not found: {file_path}")
        _send_error(client_socket, 404, "Not Found", keep_alive=False)
        return False

    # only support .html, .txt, .png, .jpg/.jpeg, others get 415
    allowed = (file_path.endswith('.html') or file_path.endswith('.txt') or
               file_path.endswith('.png') or file_path.endswith('.jpg') or file_path.endswith('.jpeg'))
    if not allowed:
        logger.warning(f"[{thread_id}] Unsupported file type: {file_path}")
        client_socket.sendall(b"HTTP/1.1 415 Unsupported Media Type\r\nConnection: close\r\n\r\n")
        return False

    content_type = get_content_type(file_path)
    connection_hdr = 'keep-alive' if keep_alive else 'close'

    # HTML files displayed inline, others downloaded with Content-Disposition
    if file_path.endswith('.html'):
        with open(file_path, 'r', encoding='utf-8') as f:
            body_bytes = f.read().encode()
        headers = _standard_headers(content_type, len(body_bytes), keep_alive)
        _send_response(client_socket, "HTTP/1.1 200 OK", headers, body_bytes)
        logger.info(f"[{thread_id}] Sending HTML file: {os.path.basename(file_path)} ({len(body_bytes)} bytes)")
        transferred = len(body_bytes)
    else:
        filename = os.path.basename(file_path)
        total_size = os.path.getsize(file_path)
        headers = _standard_headers(content_type, total_size, keep_alive)
        headers["Content-Disposition"] = f"attachment; filename=\"{filename}\""
        # Send headers first
        _send_response(client_socket, "HTTP/1.1 200 OK", headers)
        # Stream file in chunks
        transferred = 0
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                client_socket.sendall(chunk)
                transferred += len(chunk)
        logger.info(f"[{thread_id}] Sending binary file: {filename} ({transferred} bytes)")
    
    logger.info(f"[{thread_id}] Response: 200 OK ({transferred} bytes transferred)")
    return True

def handle_post_upload(client_socket, request, headers, path, keep_alive, logger, thread_id):
    # only accept JSON to /upload endpoint
    if path != '/upload':
        logger.warning(f"[{thread_id}] POST to non-upload endpoint: {path}")
        _send_error(client_socket, 405, "Method Not Allowed", keep_alive=False)
        return False
    content_type = headers.get('content-type', '')
    if 'application/json' not in content_type:
        logger.warning(f"[{thread_id}] Invalid content type for POST: {content_type}")
        _send_error(client_socket, 415, "Unsupported Media Type", keep_alive=False)
        return False
    header_end = request.find('\r\n\r\n')
    if header_end == -1:
        logger.warning(f"[{thread_id}] Malformed POST request")
        _send_error(client_socket, 400, "Bad Request", keep_alive=False)
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
        _send_error(client_socket, 500, "Internal Server Error", keep_alive=False)
        return False

    resp_obj = {
        "status": "success",
        "message": "File created successfully",
        "filepath": f"/uploads/{fname}"
    }
    resp_body = json.dumps(resp_obj)
    headers = _standard_headers("application/json", len(resp_body.encode()), keep_alive)
    _send_response(client_socket, "HTTP/1.1 201 Created", headers, resp_body.encode())
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

    # Bounded connection queue and worker threads
    conn_queue: queue.Queue[tuple] = queue.Queue(maxsize=100)
    active_lock = threading.Lock()
    active_count = 0

    def worker_loop():
        nonlocal active_count
        while True:
            client_socket, client_address = conn_queue.get()
            thread_id = threading.current_thread().name
            logger.info(f"Connection dequeued, assigned to {thread_id}")
            with active_lock:
                active_count += 1
            try:
                handle_client(client_socket, client_address, host, port, logger)
            except Exception as e:
                logger.error(f"Error in connection handler: {e}")
                try:
                    _send_error(client_socket, 503, "Service Unavailable", keep_alive=False)
                except Exception:
                    pass
            finally:
                with active_lock:
                    active_count -= 1
                conn_queue.task_done()

    # Start worker threads
    for i in range(max_workers):
        t = threading.Thread(target=worker_loop, name=f"Thread-{i+1}", daemon=True)
        t.start()

    try:
        while True:
            try:
                client_socket, client_address = server_socket.accept()
                try:
                    conn_queue.put_nowait((client_socket, client_address))
                    # Log queueing if queue had items
                    if conn_queue.qsize() > 0:
                        logger.warning("Warning: Thread pool saturated, queuing connection")
                except queue.Full:
                    logger.warning("Connection queue full, returning 503")
                    try:
                        hdrs = {
                            "Date": rfc7231_date(),
                            "Server": "Multi-threaded HTTP Server",
                            "Retry-After": "30",
                            "Connection": "close",
                            "Content-Length": "0",
                        }
                        _send_response(client_socket, "HTTP/1.1 503 Service Unavailable", hdrs)
                    except Exception:
                        pass
                    finally:
                        client_socket.close()

                # Periodic thread pool status
                if (time.time() % 30) < 0.05:  # approx every 30s
                    with active_lock:
                        logger.info(f"Thread pool status: {active_count}/{max_workers} active")
                    
            except Exception as e:
                logger.error(f"Error accepting connection: {e}")
                continue
                
    except KeyboardInterrupt:
        logger.info("Stopping server...")
    finally:
        logger.info("Shutting down...")
        server_socket.close()
        logger.info("Server stopped")

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    host = sys.argv[2] if len(sys.argv) > 2 else '127.0.0.1'
    max_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    start_server(host, port, max_workers)


