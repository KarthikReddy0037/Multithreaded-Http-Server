# Multi-threaded HTTP Server

A Python-based HTTP/1.1 server built from scratch using socket programming with multi-threading support, binary file transfers, and security features.

---

## Project Overview

Built using Python socket programming and multi-threading.

### Key Features

- Static file serving (HTML, TXT, PNG, JPEG)
- Concurrent client handling with thread pool
- JSON POST request processing
- HTTP/1.1 persistent connections
- Path traversal protection and host validation
- Comprehensive logging

### Requirements

```
Python 3.8+ (no external dependencies)
```

---

## Build and Run Instructions

### Installation

```bash
git clone https://github.com/Raghavendra1729-cell/Multithreaded-Http-Server
cd "Multithreaded Http Server"
mkdir -p resources/uploads testing/downloads
```

### Running the Server

**Default Configuration** (127.0.0.1:8080, 10 threads):
```bash
python3 server.py
```

**Custom Configuration**:
```bash
python3 server.py [PORT] [HOST] [MAX_THREADS]

# Examples:
python3 server.py 9000
python3 server.py 8000 0.0.0.0 20
```

### Testing

```bash
python3 testing/client.py
```

**Test Results**: 48/48 tests passing

### Accessing the Server

**Browser**:
- http://127.0.0.1:8080/
- http://127.0.0.1:8080/about.html
- http://127.0.0.1:8080/contact.html
- http://127.0.0.1:8080/logo.png

**cURL**:
```bash
curl http://127.0.0.1:8080/
curl -O http://127.0.0.1:8080/logo.png
curl -O http://127.0.0.1:8080/photo.jpg
curl -X POST http://127.0.0.1:8080/upload -H "Content-Type: application/json" -d '{"name": "test"}'
```

---

## Binary Transfer Implementation

### Supported File Types

| Extension | Content-Type | Transfer Mode |
|-----------|--------------|---------------|
| .html | text/html | Text |
| .txt | application/octet-stream | Binary |
| .png | application/octet-stream | Binary |
| .jpg, .jpeg | application/octet-stream | Binary |

### Transfer Method

**Chunked Streaming** (8KB chunks):
```python
CHUNK_SIZE = 8192

with open(file_path, 'rb') as f:
    while chunk := f.read(CHUNK_SIZE):
        sock.sendall(chunk)
```

### Features

- Memory efficient (only 8KB in memory at a time)
- Low latency streaming
- Handles large files without corruption
- Binary mode preserves data integrity
- MD5 checksum verification in tests

### Example Response

```http
HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Length: 1048576
Content-Disposition: attachment; filename="image.png"
Connection: keep-alive

[binary data]
```

---

## Thread Pool Architecture

### Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Thread Pool Size | 10 | Configurable via command line |
| Max Requests/Connection | 100 | Persistent connection limit |
| Idle Timeout | 30 sec | Auto-close inactive connections |

### Implementation

```python
with ThreadPoolExecutor(max_workers=10) as executor:
    while True:
        client_sock, client_addr = server_socket.accept()
        executor.submit(handle_client, client_sock, client_addr, host, port, logger)
```

### How It Works

1. **Client Connection**: Each client assigned to an available thread
2. **Queue Management**: Excess connections queued automatically
3. **Thread Safety**: No shared state between handlers
4. **Monitoring**: Status logged every 10 connections

### Example Log

```
[2025-10-09 14:49:12] [Thread-6] Connection from 127.0.0.1:60630
[2025-10-09 14:49:12] [Thread-6] Request: GET /photo.jpg
[2025-10-09 14:49:12] [Thread-6] Response: 200 OK (13070 bytes)
```

---

## Security Measures

### Path Traversal Protection

```python
def is_safe_path(path):
    path = path.lstrip('/')
    return '..' not in path and not os.path.isabs(path)
```

**Blocked Patterns**:
- `/../etc/passwd` → 403 Forbidden
- `../../config` → 403 Forbidden
- Absolute paths → 403 Forbidden

### Host Header Validation

**Allowed Hosts**:
- `localhost:8080`
- `127.0.0.1:8080`

**Security Responses**:
- Missing Host → 400 Bad Request
- Invalid Host → 403 Forbidden

### Error Handling

| Error Code | Condition | Response |
|------------|-----------|----------|
| 404 | Not Found | Resource doesn't exist |
| 405 | Method Not Allowed | Unsupported HTTP method |
| 415 | Unsupported Media Type | Invalid content type |
| 500 | Internal Server Error | Unexpected errors |

### Additional Protections

- Max 8KB header size
- File extension whitelist (.html, .txt, .jpg, .jpeg, .png)
- 30-second timeout (slowloris protection)
- All security events logged

---

## Known Limitations

| Limitation | Impact | Future Enhancement |
|------------|--------|-------------------|
| HTTP Methods | Only GET and POST | Add PUT, DELETE, PATCH |
| POST Content-Type | JSON only | Support form data, multipart |
| Security | HTTP only (no HTTPS) | SSL/TLS implementation |
| Performance | Synchronous I/O | Async optimization |
| Scalability | Single process, GIL limited | Multi-process workers |
| Caching | No cache support | ETag, cache-control |
| Compression | No compression | gzip, brotli support |
| Authentication | Public access only | Add auth system |

---

## Project Structure

```
Multithreaded Http Server/
├── server.py                  # Main server
├── resources/                 # Static files
│   ├── index.html            # HTML files
│   ├── about.html
│   ├── contact.html
│   ├── sample.txt            # Text file
│   ├── logo.png              # PNG image
│   ├── photo.jpg             # JPEG image
│   ├── largePhoto.png        # Large PNG (>1MB)
│   └── uploads/              # JSON uploads
├── testing/
│   ├── client.py             # Test suite
│   ├── test_results.md
│   ├── test_execution.log
│   └── downloads/
├── server.log
└── README.md
```

---

## Testing and Logs

### Test Coverage

- GET request testing (all file types)
- POST request testing (JSON payloads)
- Security testing (path traversal, host validation)
- Binary transfer integrity (MD5 checksums)
- Error response verification
- Concurrent client handling

### Log Files

- `server.log` - Server activity and security events
- `testing/test_execution.log` - Client test execution
- `testing/test_results.md` - Detailed test report

---

**Author**: Lingaraghavendra  
**Assignment**: Multi-threaded HTTP Server Using Socket Programming  

