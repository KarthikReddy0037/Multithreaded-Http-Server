#!/usr/bin/env python3
"""
Simple Multi-threaded HTTP Server
Learning socket programming step by step
"""

import socket
import threading
import sys

def handle_client(client_socket, client_address):
    """Handle a single client connection in a separate thread"""
    print(f"New connection from {client_address[0]}:{client_address[1]}")
    
    try:
        # For now, just send a simple message
        message = "Hello! You connected to our server!\n"
        client_socket.send(message.encode())
        
    except Exception as e:
        print(f"Error handling client: {e}")
    finally:
        client_socket.close()
        print(f"Connection closed for {client_address[0]}:{client_address[1]}")

def start_server(host='127.0.0.1', port=8080):
    """Start the server and accept connections"""
    
    # Create a socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Allow reusing the address (helpful for testing)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Bind to host and port
    server_socket.bind((host, port))
    
    # Listen for connections (up to 5 queued connections)
    server_socket.listen(5)
    
    print(f"Server started on {host}:{port}")
    print("Waiting for connections...")
    
    try:
        while True:
            # Accept a connection
            client_socket, client_address = server_socket.accept()
            
            # Create a new thread to handle this client
            client_thread = threading.Thread(
                target=handle_client, 
                args=(client_socket, client_address)
            )
            client_thread.start()
            
    except KeyboardInterrupt:
        print("\nShutting down server...")
    finally:
        server_socket.close()

if __name__ == "__main__":
    # Get command line arguments
    port = 8080
    host = '127.0.0.1'
    
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    if len(sys.argv) > 2:
        host = sys.argv[2]
    
    print(f"Starting server on {host}:{port}")
    start_server(host, port)


