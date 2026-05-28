# Multi-threaded HTTP Server

A Python-based HTTP/1.1 server built from scratch using socket programming with multi-threading support, binary file transfers, and security features.

---

## Project Overview

Built using Python socket programming and multi-threading.

### Key Features

- Static file serving (HTML, TXT, PNG, JPEG, JSON)
- Concurrent client handling with thread pool
- JSON GET and POST request processing
- HTTP/1.1 persistent connections
- Path traversal protection and host validation
- Comprehensive logging and automated testing

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

**Run the automated test suite** (ensure server is running first):
```bash
python3 testing/client.py
```

**Test Results**: 54/54 tests passing ✓

See [Testing Steps](#testing-steps) section below for detailed instructions.

### Accessing the Server

**Browser**:
- http://127.0.0.1:8080/
- http://127.0.0.1:8080/about.html
- http://127.0.0.1:8080/contact.html
- http://127.0.0.1:8080/new.json

**cURL Examples**:
```bash
# GET HTML
curl http://127.0.0.1:8080/

# GET JSON
curl http://127.0.0.1:8080/new.json

# Download binary files
curl -O http://127.0.0.1:8080/logo.png
curl -O http://127.0.0.1:8080/photo.jpg

# POST JSON data
curl -X POST http://127.0.0.1:8080/upload \
  -H "Content-Type: application/json" \
  -d '{"name": "test", "data": "value"}'
```

---

## Binary Transfer Implementation

### Supported File Types

| Extension | Content-Type | Transfer Mode |
|-----------|--------------|---------------|
| .html | text/html; charset=utf-8 | Text |
| .json | application/json; charset=utf-8 | Text |
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
- File extension whitelist (.html, .json, .txt, .jpg, .jpeg, .png)
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
│   ├── new.json              # JSON data file
│   ├── logo.png              # PNG image
│   ├── photo.jpg             # JPEG image
│   ├── largePhoto.png        # Large PNG (>10MB)
│   └── uploads/              # JSON uploads
├── testing/
│   ├── client.py             # Automated test suite
│   ├── test_results.md       # Test report
│   └── downloads/            # Client downloads
├── logs/
│   └── server.log            # Server logs
└── README.md
```

---

## Testing Steps

### Prerequisites

1. Ensure Python 3.8+ is installed
2. Navigate to the project directory
3. Ensure `resources/` and `testing/downloads/` directories exist

### Step-by-Step Testing Guide

#### 1. Start the Server

Open a terminal and run:
```bash
python3 server.py
```

**Expected Output**:
```
==================================================
HTTP/1.1 Server Started
==================================================
Host: 127.0.0.1
Port: 8080
Thread Pool: 10 workers
Resources Directory: resources/
Logs: server.log
==================================================
Press Ctrl+C to stop server
```

#### 2. Run Automated Tests

Open a **new terminal** (keep the server running) and execute:
```bash
python3 testing/client.py
```

**Expected Output**:
```
==================================================
HTTP SERVER TEST SUITE
==================================================
Server: http://127.0.0.1:8080
Clients: 3 concurrent
==================================================

[Client-1] ===== STARTED =====
[Client-1] -- Basic Tests --
[Client-1] Downloaded / (439 bytes)
[Client-1] Downloaded /about.html (428 bytes)
[Client-1] Downloaded /contact.html (287 bytes)
[Client-1] Downloaded /sample.txt (240 bytes)
[Client-1] -- JSON Tests --
[Client-1] Downloaded /new.json (113 bytes)
[Client-1] -- Binary Tests --
[Client-1] Downloaded /logo.png (29794 bytes)
...
==================================================
Test Summary: 54/54 passed (100%)
Results saved to: testing/test_results.md
==================================================
```

#### 3. Verify Test Results

```bash
cat testing/test_results.md
```

**What to Look For**:
- ✓ All 54 tests should show **PASS**
- ✓ Success Rate: **100.0%**
- ✓ Message: **ALL TESTS PASSED!**

#### 4. Verify Downloaded Files

```bash
ls -lh testing/downloads/
```

**Expected Files** (per client):
- `client[1-3]_index.html` - Homepage
- `client[1-3]_about.html` - About page
- `client[1-3]_contact.html` - Contact page
- `client[1-3]_sample.txt` - Text file
- `client[1-3]_new.json` - JSON data ✨ **NEW**
- `client[1-3]_logo.png` - Small image (~29KB)
- `client[1-3]_large.png` - Large image (~10MB)
- `client[1-3]_photo.jpg` - JPEG image

#### 5. Check Server Logs

```bash
tail -n 50 logs/server.log
```

**What to Look For**:
```
[2025-10-10 10:39:14] [ThreadPoolExecutor-0_1] Request: GET /new.json
[2025-10-10 10:39:14] [ThreadPoolExecutor-0_1] Sent JSON: new.json (113 bytes)
[2025-10-10 10:39:14] [ThreadPoolExecutor-0_1] Response: 200 OK
```

### Test Coverage Details

The automated test suite validates:

#### ✅ **Basic Tests** (per client)
- GET `/` → index.html
- GET `/about.html`
- GET `/contact.html`
- GET `/sample.txt`

#### ✅ **JSON Tests** (per client) ✨ **NEW**
- GET `/new.json` - Download JSON file
- JSON validation - Parse and verify structure

#### ✅ **Binary Tests** (per client)
- GET `/logo.png` - Small PNG (~29KB)
- GET `/largePhoto.png` - Large PNG (~10MB)
- GET `/photo.jpg` - JPEG image

#### ✅ **Integrity Tests** (per client)
- MD5 checksum verification for `logo.png`
- MD5 checksum verification for `photo.jpg`
- Ensures no data corruption during transfer

#### ✅ **POST Tests** (per client)
- POST `/upload` with JSON payload
- Verify 201 Created response
- Check uploaded files in `resources/uploads/`

#### ✅ **Error Response Tests** (per client)
- 404 Not Found - `/nonexistent.png`
- 405 Method Not Allowed - `PUT /index.html`
- 415 Unsupported Media Type - POST with `text/plain`

#### ✅ **Security Tests** (per client)
- 403 Forbidden - Path traversal attempt `/../etc/passwd`
- 403 Forbidden - Invalid host header `evil.com`
- 400 Bad Request - Missing Host header

### Manual Testing

You can also test manually using cURL:

```bash
# Test JSON endpoint
curl http://127.0.0.1:8080/new.json

# Test with verbose output
curl -v http://127.0.0.1:8080/new.json

# Verify JSON structure
curl http://127.0.0.1:8080/new.json | python3 -m json.tool

# Test POST
curl -X POST http://127.0.0.1:8080/upload \
  -H "Content-Type: application/json" \
  -d '{"test": "data", "timestamp": "2025-10-10"}'

# Test error handling
curl http://127.0.0.1:8080/nonexistent.json  # Should return 404
curl http://127.0.0.1:8080/../etc/passwd      # Should return 403
```

### Test Summary

| Category | Tests | Status |
|----------|-------|--------|
| Basic GET Requests | 12 | ✅ PASS |
| JSON Tests | 6 | ✅ PASS |
| Binary Transfers | 9 | ✅ PASS |
| Integrity Checks | 6 | ✅ PASS |
| JSON Validation | 3 | ✅ PASS |
| POST Requests | 3 | ✅ PASS |
| Error Handling | 9 | ✅ PASS |
| Security Tests | 6 | ✅ PASS |
| **Total** | **54** | **✅ 100%** |

### Troubleshooting

**Problem**: `OSError: [Errno 48] Address already in use`
```bash
# Solution: Kill existing server process
ps aux | grep "server.py" | grep -v grep | awk '{print $2}' | xargs kill
```

**Problem**: Tests fail with connection errors
```bash
# Solution: Ensure server is running first
python3 server.py  # In terminal 1
python3 testing/client.py  # In terminal 2
```

**Problem**: Downloaded files are corrupted
```bash
# Solution: Check checksum tests - they should all PASS
# If checksums fail, there may be a transfer issue
```

### Log Files

- `logs/server.log` - Server activity, requests, responses, security events
- `testing/test_results.md` - Detailed test report with pass/fail status
- All connections and errors are logged with timestamps

---

**Author**: KarthikReddy0037  
**Assignment**: Multi-threaded HTTP Server Using Socket Programming  
Updated by KarthikReddy

