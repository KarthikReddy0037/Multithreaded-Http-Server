# Multi-threaded HTTP Server

## Overview
This is a multi-threaded HTTP server implementation built using Python. It supports GET and POST requests, serves static files, and handles JSON uploads. The server uses ThreadPoolExecutor to manage concurrent client connections efficiently.

## Build and Run Instructions

### Prerequisites
- Python 3.8 or above

### Setup
1. Clone or download this repository
2. Create a folder named `resources` in the project directory
3. Place your static files (e.g., index.html) inside the `resources` folder
4. Create a subdirectory `resources/uploads` for uploaded files

### Run the Server
```bash
python server.py [port] [host] [thread_pool_size]
```
Example:
```bash
python server.py 8080 127.0.0.1 10
```
The server will start at:
```
http://127.0.0.1:8080
```
Logs will be stored in `server.log`.

## Binary Transfer Implementation

The server supports binary file transfers for .png, .jpg, .jpeg, and .txt files using the Content-Disposition: attachment header. When a client requests such a file, the server reads it in binary mode and transmits it directly to the client with accurate Content-Length and Content-Type headers.

Example:
Request:
```
GET /image.png HTTP/1.1
```
Response Headers:
```
HTTP/1.1 200 OK
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="image.png"
Content-Length: <size>
```

## Thread Pool Architecture

The server uses Python's built-in ThreadPoolExecutor to manage client connections efficiently.

Key Points:
- Each incoming client connection is handled by a worker thread
- The pool size can be configured via command-line arguments
- The main thread accepts connections and submits tasks to the pool
- Thread pool saturation is logged and queued connections are handled gracefully

This design ensures concurrency, scalability, and thread safety while preventing resource exhaustion.

## Security Measures Implemented

1. Directory Traversal Protection
   - Validates all file paths using the is_good_path() function to prevent access outside the resources directory

2. Content-Type Validation
   - Ensures only supported file types are served
   - Blocks malicious or unsupported file extensions

3. Timeouts and Error Handling
   - Client connections are automatically closed after inactivity
   - All major operations include try-except blocks for safe error handling

4. Logging
   - Every request, response, and error is logged with timestamps and thread identifiers in both console and server.log

## Known Limitations

- No HTTPS support (plain HTTP only)
- Does not handle partial content requests (e.g., Range headers)
- No persistent caching or compression mechanisms
- Limited to simple static file serving and JSON uploads

## About

This project implements all requirements from the Computer Networking assignment for building a multi-threaded HTTP server using socket programming. All features including multi-threading, binary file transfers, JSON uploads, security measures, and comprehensive logging have been successfully implemented and tested.

Assignment Requirements Completed:
- Multi-threaded architecture with configurable thread pool
- HTTP/1.1 compliance with Keep-Alive support
- Binary file transfers with proper Content-Disposition headers
- JSON upload handling with file creation
- Comprehensive security including path traversal protection
- Detailed logging with timestamps and thread tracking
- All required test files and documentation



## What We Implemented (Summary)

- Connection Queue and Workers:
  - Bounded pending connection queue (max 100) with worker threads (`Thread-1..N`).
  - Logs when connections are queued and when dequeued/assigned.
  - Returns `503 Service Unavailable` with `Retry-After` when queue is full.

- Robust HTTP Parsing (8192-byte cap):
  - Reads until `\r\n\r\n`, respects `Content-Length`, and caps total request size at 8192 bytes.
  - Proper status handling for malformed requests (400) and unsupported methods (405).

- Streaming File Responses:
  - Streams files in 8KB chunks with accurate `Content-Length` and `Content-Disposition` for downloads.
  - Serves `.html` inline with `text/html; charset=utf-8`; `.txt/.png/.jpg/.jpeg` as `application/octet-stream`.

- Standardized Headers and Errors:
  - All responses include `Date`, `Server`, `Content-Type`, `Content-Length`, `Connection`, and `Keep-Alive` (when applicable).
  - Error responses return JSON bodies (e.g., `{ "error": "Forbidden" }`).

- Security:
  - Host header validation (`localhost:PORT`, `127.0.0.1:PORT` allowed; otherwise 403; missing Host ⇒ 400).
  - Path traversal protection using canonical checks; blocks `..`, absolute paths, and UNC paths.

- Keep-Alive and Limits:
  - HTTP/1.1 keep-alive by default; honors `Connection: close`.
  - `Keep-Alive: timeout=30, max=100`; up to 100 requests per persistent connection.

- Testing and Logs:
  - `testing/client.py` enhanced to read full responses using `Content-Length`.
  - Test logs: `testing/test_execution.log`; summary: `testing/test_results.md`; server logs: `server.log`.
  - Verified: basic GET/POST, 10MB binary download, 5 concurrent downloads, negative/security scenarios.

- How to Re-run Clean Tests:
  1. Clean artifacts: remove `testing/downloads/*`, `resources/uploads/upload_*.json`, reset `server.log` and test logs.
  2. Start server: `python server.py 8080 127.0.0.1 10`.
  3. Run client once: `python testing/client.py`.
  4. For concurrent runs, execute multiple clients in parallel or use the provided scripts in the test log steps.

