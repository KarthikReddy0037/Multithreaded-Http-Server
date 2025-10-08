# Simple Multi-threaded HTTP Server

A simple HTTP server implementation using socket programming and multi-threading for Computer Networking assignment.

## ✅ Requirements 1-3 COMPLETED

This simple server covers the basic requirements:

- **Requirement 1**: Server configuration with command-line arguments
- **Requirement 2**: TCP socket implementation (bind, listen, accept)
- **Requirement 3**: Multi-threading for concurrent client connections

## How to Run

```bash
# Default: localhost:8080
python3 server.py

# Custom port
python3 server.py 9000

# Custom host and port
python3 server.py 9000 0.0.0.0
```

## What It Does

1. **Creates a TCP socket** and binds to host:port
2. **Listens for connections** (up to 5 queued connections)
3. **Accepts each client** in a separate thread
4. **Sends a simple message** to each connected client
5. **Closes the connection** after sending the message

## Code Structure

```python
# Main server function
def start_server(host='127.0.0.1', port=8080):
    # Create socket, bind, listen
    # Accept connections in loop
    # Create thread for each client

# Client handler function  
def handle_client(client_socket, client_address):
    # Send message to client
    # Close connection
```

## Key Concepts

**Socket Programming:**
- `socket.socket()` - Create a socket
- `bind()` - Attach to host:port
- `listen()` - Wait for connections
- `accept()` - Accept a connection

**Multi-threading:**
- `threading.Thread()` - Create new thread
- Each client gets its own thread
- Multiple clients can connect simultaneously

**Command Line Arguments:**
- `sys.argv[1]` - Port number
- `sys.argv[2]` - Host address

## Testing

1. Start the server: `python3 server.py`
2. Open another terminal
3. Connect with: `telnet 127.0.0.1 8080`
4. You should see: "Hello! You connected to our server!"

## Project Structure

```
project/
├── server.py              # Simple server implementation
└── resources/             # Directory for future files
    └── uploads/          # Directory for future uploads
```

## Next Steps

When ready to continue, we'll add:
- HTTP request parsing
- File serving (HTML, images, text)
- POST request handling
- Security features

This simple foundation makes it easy to understand and build upon!


