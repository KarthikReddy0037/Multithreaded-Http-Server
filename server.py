#!/usr/bin/env python3
import socket
import threading
import sys
import os
from datetime import datetime

def get_content_type(file_path):
    if file_path.endswith('.html'):
        return 'text/html'
    elif file_path.endswith('.txt'):
        return 'text/plain'
    elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
        return 'image/jpeg'
    elif file_path.endswith('.png'):
        return 'image/png'
    else:
        return 'application/octet-stream'

def is_good_path(path):
    path = os.path.normpath(path.lstrip('/'))
    return not ('..' in path or path.startswith('/'))

def handle_client(client_socket, client_address):
    print(f"Connection from {client_address[0]}:{client_address[1]}")
    
    try:
        request = client_socket.recv(4096).decode('utf-8')
        if not request:
            return
        
        first_line = request.split('\n')[0]
        parts = first_line.split()
        
        if len(parts) >= 2:
            method = parts[0]
            path = parts[1]
            
            print(f"{method} {path}")
            
            if method == 'GET':
                handle_get_request(client_socket, path)
            elif method == 'POST':
                handle_post_request(client_socket, request, path)
            else:
                client_socket.send("HTTP/1.1 405 Method Not Allowed\r\n\r\n".encode())
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

def handle_get_request(client_socket, path):
    if path == '/':
        path = '/html/index.html'
    
    if not is_good_path(path):
        client_socket.send("HTTP/1.1 403 Forbidden\r\n\r\n".encode())
        return
    
    file_path = 'www' + path
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        content_type = get_content_type(file_path)
        
        if file_path.endswith(('.jpg', '.jpeg', '.png')):
            with open(file_path, 'rb') as f:
                content = f.read()
            response = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(content)}\r\n\r\n"
            client_socket.send(response.encode() + content)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            response = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(content.encode())}\r\n\r\n{content}"
            client_socket.send(response.encode())
        
        print(f"Served: {file_path}")
    else:
        client_socket.send("HTTP/1.1 404 Not Found\r\n\r\n".encode())

def handle_post_request(client_socket, request, path):
    try:
        header_end = request.find('\r\n\r\n')
        if header_end == -1:
            client_socket.send("HTTP/1.1 400 Bad Request\r\n\r\n".encode())
            return
        
        body = request[header_end + 4:]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"post_data_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write(f"POST data: {body}")
        
        response_html = f"<h1>Data saved to {filename}</h1>"
        response = f"HTTP/1.1 201 Created\r\nContent-Type: text/html\r\nContent-Length: {len(response_html)}\r\n\r\n{response_html}"
        client_socket.send(response.encode())
        print(f"POST saved: {filename}")
        
    except Exception as e:
        print(f"POST error: {e}")
        client_socket.send("HTTP/1.1 500 Internal Server Error\r\n\r\n".encode())

def start_server(host='127.0.0.1', port=8080):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)
    
    print(f"Server started on {host}:{port}")
    print(f"Open: http://{host}:{port}/")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            client_socket, client_address = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
            client_thread.daemon = True
            client_thread.start()
            
    except KeyboardInterrupt:
        print("\nServer stopped")
    finally:
        server_socket.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    host = sys.argv[2] if len(sys.argv) > 2 else '127.0.0.1'
    start_server(host, port)


