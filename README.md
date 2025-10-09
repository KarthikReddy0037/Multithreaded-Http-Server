# Multi-threaded HTTP Server

A multi-threaded HTTP server implementation built using Python socket programming. Supports GET and POST requests, serves static files, and handles JSON uploads using a ThreadPoolExecutor for concurrent client connections.

## Build and Run Instructions

### Prerequisites
- Python 3.8 or above

### Setup
1. Clone or download this repository.
2. Create a folder named `resources` in the project directory.
3. Place your static files (e.g., `index.html`) inside the `resources` folder.
4. Optionally, create a subdirectory `resources/uploads` for uploaded files.

### Run the Server

```bash
python3 server.py [port] [host] [thread_pool_size]

# Examples
python3 server.py                 # Default: 127.0.0.1:8080, 10 workers
python3 server.py 8000           # Custom port
python3 server.py 8000 0.0.0.0 20 # Custom host and thread pool size
```

The server will start at:
```
http://127.0.0.1:8080
```

Logs will be stored in `server.log`.

### Testing

```bash
# Run basic tests
cd testing
python3 client.py

# Manual testing with curl
curl -i http://127.0.0.1:8080/
curl -i http://127.0.0.1:8080/goku.png
```

## Project Structure

```
project/
├── server.py                    # Main HTTP server implementation
├── README.md                    # This documentation
├── server.log                   # Server logs (created at runtime)
├── resources/                   # Static files served by server
│   ├── index.html              # Default homepage
│   ├── sample.html             # Sample HTML page
│   ├── form.html               # Sample form page
│   ├── test1.txt               # Sample text file
│   ├── test2.txt               # Sample text file
│   ├── anime.jpeg              # Sample JPEG image
│   ├── goku.png                # Sample PNG image
│   ├── naruto.jpeg             # Sample JPEG image
│   ├── sample.png              # Sample PNG image
│   └── uploads/                # JSON uploads saved here
└── testing/
    ├── client.py               # Test client
    └── downloads/              # Downloaded test files (created during testing)
```

## Binary Transfer Implementation

The server supports **binary file transfers** for `.png`, `.jpg`, `.jpeg`, and `.txt` files using the `Content-Disposition: attachment` header.  
When a client requests such a file, the server reads it in binary mode and transmits it directly to the client with accurate **Content-Length** and **Content-Type** headers.

### Example:

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

The server uses Python's built-in `ThreadPoolExecutor` to manage client connections efficiently.

### Key Points:

* Each incoming client connection is handled by a **worker thread**.
* The pool size can be configured via command-line arguments.
* The main thread accepts connections and submits tasks to the pool.
* Thread pool saturation is logged and queued connections are handled gracefully.

This design ensures **concurrency**, **scalability**, and **thread safety** while preventing resource exhaustion.

## Security Measures Implemented

1. **Directory Traversal Protection**  
   * Validates all file paths using the `is_good_path()` function to prevent access outside the `resources` directory.
2. **Content-Type Validation**  
   * Ensures only supported file types are served.  
   * Blocks malicious or unsupported file extensions.
3. **Timeouts and Error Handling**  
   * Client connections are automatically closed after inactivity.  
   * All major operations include try-except blocks for safe error handling.
4. **Logging**  
   * Every request, response, and error is logged with timestamps and thread identifiers in both console and `server.log`.

## Known Limitations

* No HTTPS support (plain HTTP only).
* Does not handle partial content requests (e.g., `Range` headers).
* No persistent caching or compression mechanisms.
* Limited to simple static file serving and JSON uploads.


