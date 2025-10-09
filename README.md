# Multi-threaded HTTP Server

A HTTP/1.1 server implementation using Python socket programming with thread pool concurrency, binary file transfers, and security features.

## Overview

HTTP/1.1 server supporting:
- Thread pool-based concurrency (configurable size)
- GET/POST request handling
- Binary file transfers with chunked reading (8KB chunks)
- Keep-Alive persistent connections
- Path traversal & host validation security
- Comprehensive logging

**Requirements:** Python 3.8+ (no external dependencies)

---

## Build and Run Instructions

### Installation

**Clone Repository**
```bash
git clone <your-repository-url>
cd "Multithreaded Http Server"
```

**Create Directories**
```bash
mkdir -p resources/uploads testing/downloads
```

### Running the Server

**Command Format:**
```bash
python3 server.py [PORT] [HOST] [MAX_THREADS]
```

**Examples:**
```bash
# Default (127.0.0.1:8080, 10 threads)
python3 server.py

# Custom port
python3 server.py 9000

# Custom host and port
python3 server.py 8000 0.0.0.0

# Full configuration
python3 server.py 8000 0.0.0.0 20
```

### Testing

Run the test suite:
```bash
python3 testing/client.py
```

Test Results: 57/57 tests passing (100%)

### Accessing the Server

**Browser:**
- http://127.0.0.1:8080/
- http://127.0.0.1:8080/sample.html
- http://127.0.0.1:8080/goku.png

**cURL:**
```bash
# GET request
curl http://127.0.0.1:8080/

# Download file
curl -O http://127.0.0.1:8080/goku.png

# POST JSON
curl -X POST http://127.0.0.1:8080/upload \
  -H "Content-Type: application/json" \
  -d '{"name": "test"}'
```

---

## Thread Pool Architecture

### Implementation

Uses Python's `ThreadPoolExecutor`:

```python
with ThreadPoolExecutor(max_workers=10) as executor:
    while True:
        client_sock, client_addr = server_socket.accept()
        executor.submit(handle_client, client_sock, client_addr, host, port, logger)
```

### Features

**Resource Management**
- Pre-allocated thread pool (default: 10 threads)
- Configurable pool size via command-line
- Automatic thread lifecycle management

**Request Queuing**
- Automatic queuing when threads are busy
- FIFO ordering
- Prevents resource exhaustion

**Thread Safety**
- Unique thread ID for each request
- No shared state between handlers
- Thread-safe logging and file operations

**Monitoring**
- Status logged every 10 connections
- Example: `Thread pool status: 8 threads active, 40 total connections`

---

## Binary Transfer Implementation

### Chunked Transfer

Memory-efficient implementation using 8KB chunks:

```python
CHUNK_SIZE = 8192  # 8KB chunks

with open(file_path, 'rb') as f:
    while chunk := f.read(CHUNK_SIZE):
        sock.sendall(chunk)
```

### Benefits

**Memory Efficiency**
- Large files don't load entirely into memory
- Only 8KB in memory at any time
- Supports concurrent large file transfers

**Performance**
- Streaming starts immediately (low latency)
- Consistent performance regardless of file size
- No buffering delays

**Binary Mode**
- Files opened with 'rb' flag
- No encoding/decoding overhead
- Byte-for-byte integrity preserved

### HTTP Headers

```http
HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Length: [file size]
Content-Disposition: attachment; filename="file.png"
Connection: keep-alive

[binary data]
```

### Data Integrity

- Content-Length ensures complete transfer
- MD5 checksum verification in tests
- No corruption in concurrent transfers
- Tested with 10MB files successfully

---

## Security Measures

### 1. Path Traversal Protection

```python
def is_safe_path(path):
    path = path.lstrip('/')
    return '..' not in path and not os.path.isabs(path)
```

Blocks:
- `/../etc/passwd` → 403 Forbidden
- `../../config` → 403 Forbidden
- Absolute paths → 403 Forbidden

### 2. Host Header Validation

```python
expected_hosts = [f"{server_host}:{server_port}", 
                  f"localhost:{server_port}", 
                  f"127.0.0.1:{server_port}"]

if not host_header:
    return 400
if host_header not in expected_hosts:
    return 403
```

Prevents:
- Host Header Injection attacks
- Cache poisoning
- Request forgery

### 3. Input Validation

**Request Limits**
- Max 8KB for headers
- Content-Type validation for POST
- JSON parsing with error handling

**File Extension Whitelist**
- Only .html, .txt, .jpg, .jpeg, .png allowed
- Prevents serving sensitive files

**Error Handling**
- 30-second timeout prevents slowloris
- Max 100 requests per connection
- Sockets closed in finally blocks

### 4. Security Logging

All security events logged:
```
[2025-10-09 16:48:17] [Thread-1] Blocked path traversal: /../etc/passwd
[2025-10-09 16:48:17] [Thread-1] Response: 403 Forbidden
```

---

## Known Limitations

### Current Limitations

1. **Single Process** - Not horizontally scalable, limited by GIL
2. **No HTTPS** - Only HTTP protocol, no encryption
3. **Limited Methods** - Only GET and POST (no PUT, DELETE, etc.)
4. **No Caching** - No cache-control or ETag support
5. **Static Files Only** - No server-side scripting
6. **No Compression** - Files sent uncompressed
7. **No Authentication** - All resources publicly accessible
8. **Large Files** - Files >100MB may degrade performance
9. **No Range Requests** - Cannot resume interrupted downloads
10. **Fixed Thread Pool** - No dynamic scaling

### Future Enhancements

- HTTPS/TLS support
- HTTP/2 protocol
- Compression (gzip, brotli)
- Range requests for partial content
- WebSocket support
- Caching with ETags
- Rate limiting
- Multi-process workers

---

## Project Structure

```
Multithreaded Http Server/
├── server.py              # Main server (358 lines)
├── resources/             # Static files
│   ├── *.html            # HTML files
│   ├── *.txt             # Text files
│   ├── *.png             # PNG images (up to 10MB)
│   ├── *.jpeg            # JPEG images
│   └── uploads/          # JSON uploads
├── testing/
│   ├── client.py         # Test suite (403 lines)
│   ├── test_results.md   # Test report
│   └── test_execution.log
├── server.log            # Server logs
└── README.md             # Documentation
```

---

## Author

**Lingaraghavendra**  
Assignment: Multi-threaded HTTP Server Using Socket Programming  

