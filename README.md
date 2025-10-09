# Multi-threaded HTTP Server

Simple HTTP server with socket programming and multi-threading for Computer Networking assignment.

## Features
- TCP Socket Programming
- Multi-threading
- GET/POST requests
- File serving (HTML, TXT, JPEG, PNG)
- Binary file transfer
- Path traversal protection

## Usage

```bash
python3 server.py [port] [host]

# Examples:
python3 server.py              # Default: localhost:8080
python3 server.py 8000         # Custom port
python3 server.py 8000 0.0.0.0 # Custom host and port
```

## Test URLs

- Home: `http://localhost:8080/`
- HTML: `http://localhost:8080/html/sample.html`
- Text: `http://localhost:8080/text/test1.txt`
- Images: `http://localhost:8080/images/anime.jpeg`
- POST Form: `http://localhost:8080/html/form.html`

## Testing

```bash
# Basic requests
curl http://localhost:8080/
curl http://localhost:8080/text/test1.txt

# Image downloads
curl -o test.jpg http://localhost:8080/images/anime.jpeg
curl -o test.png http://localhost:8080/images/goku.png

# POST test
curl -X POST -d "name=Test" http://localhost:8080/

# Error tests
curl http://localhost:8080/nonexistent.html
curl -X DELETE http://localhost:8080/
```

## Project Structure

```
project/
├── server.py                    # Main server
├── README.md                    # Documentation
├── www/                         # Document root
│   ├── html/                    # HTML files
│   │   ├── index.html
│   │   ├── sample.html
│   │   └── form.html
│   ├── text/                    # Text files
│   │   ├── test1.txt
│   │   └── test2.txt
│   └── images/                  # Image files
│       ├── anime.jpeg
│       ├── naruto.jpeg
│       ├── goku.png
│       └── sample.png
└── testing/                     # Test documentation
```

## Requirements

✅ TCP Socket Programming
✅ Multi-threading
✅ HTTP GET/POST requests
✅ Binary file transfer
✅ Error handling (404, 405, 403)
✅ Path traversal protection
✅ Command line configuration


