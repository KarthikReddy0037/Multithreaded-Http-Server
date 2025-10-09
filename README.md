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


