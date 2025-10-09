#!/usr/bin/env python3
"""
HTTP Server Test Client
Downloads files from resources/ and tests JSON upload to /upload endpoint
"""

import socket
import os
import json
from datetime import datetime

def log(message):
    """Simple logging function"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def download_file(host, port, url_path, save_path):
    """
    Download a file from the HTTP server
    returns True if successful, False otherwise
    """
    try:
        # create HTTP GET request
        request = f"GET {url_path} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n"
        
        # connect to server and send request
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
        client_socket.send(request.encode())
        
        # receive response headers first, then body per Content-Length
        response = b""
        client_socket.settimeout(5)
        # read until headers complete
        while b"\r\n\r\n" not in response:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            response += chunk

        header_end = response.find(b"\r\n\r\n")
        if header_end == -1:
            client_socket.close()
            log(f"Invalid response format for {url_path}")
            return False

        headers_blob = response[:header_end].decode('utf-8', errors='ignore')
        body = response[header_end + 4:]

        # parse status
        status_line = headers_blob.split("\r\n", 1)[0]
        if "200 OK" not in status_line:
            client_socket.close()
            log(f"Server error for {url_path} ({status_line})")
            return False

        # parse Content-Length
        content_length = None
        for line in headers_blob.split("\r\n"):
            if line.lower().startswith('content-length:'):
                try:
                    content_length = int(line.split(':', 1)[1].strip())
                except Exception:
                    content_length = None
                break

        # if Content-Length present, read exactly that much
        if content_length is not None:
            while len(body) < content_length:
                chunk = client_socket.recv(8192)
                if not chunk:
                    break
                body += chunk
            body = body[:content_length]
        else:
            # no length, read until close
            while True:
                chunk = client_socket.recv(8192)
                if not chunk:
                    break
                body += chunk

        client_socket.close()

        # save the file
        with open(save_path, 'wb') as f:
            f.write(body)
        
        file_size = len(body)
        log(f"Downloaded {url_path} -> {save_path} ({file_size} bytes)")
        return True
            
    except Exception as e:
        log(f"Error downloading {url_path}: {e}")
        return False

def test_json_upload(host, port):
    """test JSON upload functionality"""
    try:
        data = {"name": "Student", "message": "Hello JSON"}
        body = json.dumps(data)
        request = (
            f"POST /upload HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"Content-Type: application/json\r\n"
            f"Content-Length: {len(body.encode())}\r\n\r\n{body}"
        )
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.sendall(request.encode())
        resp = s.recv(4096)
        s.close()
        if b"201 Created" in resp and b"application/json" in resp:
            log("JSON upload to /upload - PASSED (201 Created)")
            return True
        else:
            log("JSON upload to /upload - FAILED")
            return False
    except Exception as e:
        log(f"JSON upload error: {e}")
        return False

def run_tests():
    """run basic tests to verify server functionality"""
    host = '127.0.0.1'
    port = 8080
    
    log("=" * 50)
    log("HTTP SERVER TEST CLIENT")
    log("=" * 50)
    
    # files to test downloading (resources/ served at root paths)
    test_files = [
        ("/", "downloaded_homepage.html"),                 # resources/index.html
        ("/sample.html", "downloaded_sample.html"),        # resources/sample.html
        ("/test1.txt", "downloaded_test1.txt"),           # resources/test1.txt
        ("/anime.jpeg", "downloaded_anime.jpeg"),         # resources/anime.jpeg
        ("/goku.png", "downloaded_goku.png"),            # resources/goku.png
    ]
    
    log("Testing file downloads...")
    
    success_count = 0
    # ensure downloads directory exists
    downloads_dir = "testing/downloads"
    os.makedirs(downloads_dir, exist_ok=True)

    for url_path, save_path in test_files:
        if download_file(host, port, url_path, f"{downloads_dir}/{save_path}"):
            success_count += 1
    
    # test JSON upload
    if test_json_upload(host, port):
        success_count += 1
    
    total_tests = len(test_files) + 1

    log("=" * 50)
    log(f"TESTS COMPLETED: {success_count}/{total_tests} PASSED")
    log("=" * 50)
    
    # show downloaded files
    log("Downloaded files:")
    for url_path, save_path in test_files:
        file_path = f"{downloads_dir}/{save_path}"
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            log(f"  {save_path} ({size} bytes)")

if __name__ == "__main__":
    run_tests()
