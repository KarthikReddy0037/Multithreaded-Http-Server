#!/usr/bin/env python3
"""
HTTP Server Test Client
Downloads HTML, text, and images to testing/downloads/
"""

import socket
import os
from datetime import datetime

def log(message):
    """Simple logging function"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def download_file(host, port, url_path, save_path):
    """
    Download a file from the HTTP server
    Returns True if successful, False otherwise
    """
    try:
        # Create HTTP GET request
        request = f"GET {url_path} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n"
        
        # Connect to server and send request
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
        client_socket.send(request.encode())
        
        # Receive response
        response = client_socket.recv(4096)
        client_socket.close()
        
        # Check if server responded with 200 OK
        if b"200 OK" in response:
            # Find where content starts (after HTTP headers)
            header_end = response.find(b"\r\n\r\n")
            if header_end != -1:
                content = response[header_end + 4:]
                
                # Save the file
                with open(save_path, 'wb') as f:
                    f.write(content)
                
                file_size = len(content)
                log(f"✅ Downloaded {url_path} -> {save_path} ({file_size} bytes)")
                return True
            else:
                log(f"❌ Invalid response format for {url_path}")
                return False
        else:
            log(f"❌ Server error for {url_path}")
            return False
            
    except Exception as e:
        log(f"❌ Error downloading {url_path}: {e}")
        return False

## POST testing intentionally removed to keep testing minimal and file-only

def run_tests():
    """Run all tests to verify server functionality"""
    host = '127.0.0.1'
    port = 8080
    
    log("=" * 50)
    log("HTTP SERVER TEST CLIENT")
    log("=" * 50)
    
    # Files to test downloading
    test_files = [
        ("/", "downloaded_homepage.html"),           # Home page
        ("/html/sample.html", "downloaded_sample.html"),  # HTML file
        ("/text/test1.txt", "downloaded_text.txt"),      # Text file
        ("/images/anime.jpeg", "downloaded_image.jpeg"), # JPEG image
        ("/images/goku.png", "downloaded_image.png"),    # PNG image
    ]
    
    log("Testing file downloads...")
    
    success_count = 0
    # Ensure downloads directory exists
    downloads_dir = "testing/downloads"
    os.makedirs(downloads_dir, exist_ok=True)

    for url_path, save_path in test_files:
        if download_file(host, port, url_path, f"{downloads_dir}/{save_path}"):
            success_count += 1
    
    log("=" * 50)
    log(f"TESTS COMPLETED: {success_count}/{len(test_files)} PASSED")
    log("=" * 50)
    
    # Show downloaded files
    log("Downloaded files:")
    for url_path, save_path in test_files:
        file_path = f"{downloads_dir}/{save_path}"
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            log(f"  📄 {save_path} ({size} bytes)")

if __name__ == "__main__":
    run_tests()
