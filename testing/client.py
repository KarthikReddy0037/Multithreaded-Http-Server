#!/usr/bin/env python3
"""
HTTP Client Test Suite
Tests server with 3 concurrent clients
"""

import socket
import os
import json
import hashlib
import threading
import time
from datetime import datetime

# Config
HOST = '127.0.0.1'
PORT = 8080
DOWNLOADS_DIR = "testing/downloads"

# Thread-safe storage
test_results = []
lock = threading.Lock()


def http_request(request_str):
    """Send HTTP request and get response"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(30)
        sock.connect((HOST, PORT))
        sock.sendall(request_str.encode())
        
        response = b""
        while True:
            chunk = sock.recv(8192)
            if not chunk:
                break
            response += chunk
            
            # Check if complete
            if b"\r\n\r\n" in response:
                header_end = response.index(b"\r\n\r\n")
                headers = response[:header_end].decode('utf-8', errors='ignore')
                body = response[header_end + 4:]
                
                for line in headers.split('\r\n'):
                    if line.lower().startswith('content-length:'):
                        expected = int(line.split(':', 1)[1].strip())
                        if len(body) >= expected:
                            sock.close()
                            return response
        
        sock.close()
        return response
    except Exception as e:
        print(f"Error: {e}")
        return None


def download_file(url_path, save_name, client_id):
    """Download file from server"""
    request = f"GET {url_path} HTTP/1.1\r\nHost: {HOST}:{PORT}\r\n\r\n"
    response = http_request(request)
    
    if response and b"200 OK" in response:
        header_end = response.index(b"\r\n\r\n")
        body = response[header_end + 4:]
        save_path = f"{DOWNLOADS_DIR}/{save_name}"
        with open(save_path, 'wb') as f:
            f.write(body)
        print(f"[Client-{client_id}] Downloaded {url_path} ({len(body)} bytes)")
        return True
    
    print(f"[Client-{client_id}] Failed: {url_path}")
    return False


def upload_json(data, client_id):
    """Upload JSON via POST"""
    body = json.dumps(data)
    request = (
        f"POST /upload HTTP/1.1\r\n"
        f"Host: {HOST}:{PORT}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n\r\n{body}"
    )
    response = http_request(request)
    
    if response and b"201 Created" in response:
        print(f"[Client-{client_id}] POST /upload -> 201 Created")
        return True
    
    print(f"[Client-{client_id}] POST failed")
    return False


def test_error(client_id, method, path, headers, expected_code):
    """Test error response"""
    request = f"{method} {path} HTTP/1.1\r\n"
    for key, value in headers.items():
        request += f"{key}: {value}\r\n"
    request += "\r\n"
    
    response = http_request(request)
    if response and str(expected_code).encode() in response:
        print(f"[Client-{client_id}] {method} {path} -> {expected_code}")
        return True
    
    print(f"[Client-{client_id}] Error test failed")
    return False


def checksum(filepath):
    """Calculate MD5 checksum"""
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()


def verify_file(original, downloaded, client_id):
    """Verify file integrity"""
    if not os.path.exists(downloaded):
        print(f"[Client-{client_id}] File missing: {downloaded}")
        return False
    
    orig_sum = checksum(original)
    down_sum = checksum(downloaded)
    
    if orig_sum == down_sum:
        print(f"[Client-{client_id}] Checksum OK: {os.path.basename(original)}")
        return True
    
    print(f"[Client-{client_id}] Checksum FAIL: {os.path.basename(original)}")
    return False


def verify_json(downloaded, client_id):
    """Verify JSON file is valid"""
    if not os.path.exists(downloaded):
        print(f"[Client-{client_id}] JSON file missing: {downloaded}")
        return False
    
    try:
        with open(downloaded, 'r') as f:
            data = json.load(f)
        print(f"[Client-{client_id}] JSON valid: {os.path.basename(downloaded)}")
        return True
    except json.JSONDecodeError as e:
        print(f"[Client-{client_id}] JSON invalid: {os.path.basename(downloaded)} - {e}")
        return False


def run_client(client_id):
    """Run all tests for one client"""
    print(f"\n[Client-{client_id}] ===== STARTED =====")
    results = []
    
    # Basic tests
    print(f"[Client-{client_id}] -- Basic Tests --")
    files = [
        ("/", f"client{client_id}_index.html"),
        ("/about.html", f"client{client_id}_about.html"),
        ("/contact.html", f"client{client_id}_contact.html"),
        ("/sample.txt", f"client{client_id}_sample.txt")
    ]
    
    for url, save_name in files:
        success = download_file(url, save_name, client_id)
        results.append(("GET " + url, success))
    
    # JSON tests
    print(f"[Client-{client_id}] -- JSON Tests --")
    json_files = [
        ("/new.json", f"client{client_id}_new.json")
    ]
    
    for url, save_name in json_files:
        success = download_file(url, save_name, client_id)
        results.append(("GET " + url, success))
    
    # Binary tests
    print(f"[Client-{client_id}] -- Binary Tests --")
    binary_files = [
        ("/logo.png", f"client{client_id}_logo.png"),
        ("/largePhoto.png", f"client{client_id}_large.png"),
        ("/photo.jpg", f"client{client_id}_photo.jpg")
    ]
    
    for url, save_name in binary_files:
        success = download_file(url, save_name, client_id)
        results.append(("GET " + url, success))
    
    # Checksum verification
    print(f"[Client-{client_id}] -- Checksum Tests --")
    time.sleep(0.1)
    
    checksums = [
        ("resources/logo.png", f"{DOWNLOADS_DIR}/client{client_id}_logo.png"),
        ("resources/photo.jpg", f"{DOWNLOADS_DIR}/client{client_id}_photo.jpg")
    ]
    
    for original, downloaded in checksums:
        verified = verify_file(original, downloaded, client_id)
        results.append(("Checksum " + os.path.basename(original), verified))
    
    # JSON validation
    print(f"[Client-{client_id}] -- JSON Validation --")
    json_verification = verify_json(f"{DOWNLOADS_DIR}/client{client_id}_new.json", client_id)
    results.append(("JSON Validation new.json", json_verification))
    
    # POST test
    print(f"[Client-{client_id}] -- POST Test --")
    upload_data = {
        "client_id": client_id,
        "test": "Upload test",
        "timestamp": datetime.now().isoformat()
    }
    success = upload_json(upload_data, client_id)
    results.append(("POST /upload", success))
    
    # Error tests
    print(f"[Client-{client_id}] -- Error Tests --")
    error_tests = [
        ("GET", "/nonexistent.png", {"Host": f"{HOST}:{PORT}"}, 404),
        ("PUT", "/index.html", {"Host": f"{HOST}:{PORT}"}, 405),
    ]
    
    for method, path, headers, code in error_tests:
        success = test_error(client_id, method, path, headers, code)
        results.append((f"{code} Error", success))
    
    # 415 test
    request = f"POST /upload HTTP/1.1\r\nHost: {HOST}:{PORT}\r\nContent-Type: text/plain\r\nContent-Length: 4\r\n\r\ntest"
    response = http_request(request)
    success = response and b"415" in response
    if success:
        print(f"[Client-{client_id}] POST text/plain -> 415")
    results.append(("415 Error", success))
    
    # Security tests
    print(f"[Client-{client_id}] -- Security Tests --")
    security_tests = [
        ("GET", "/../etc/passwd", {"Host": f"{HOST}:{PORT}"}, 403),
        ("GET", "/index.html", {"Host": "evil.com"}, 403),
    ]
    
    for method, path, headers, code in security_tests:
        success = test_error(client_id, method, path, headers, code)
        results.append(("Security " + str(code), success))
    
    # Missing host
    request = "GET /index.html HTTP/1.1\r\n\r\n"
    response = http_request(request)
    success = response and b"400" in response
    if success:
        print(f"[Client-{client_id}] Missing Host -> 400")
    results.append(("Missing Host", success))
    
    print(f"[Client-{client_id}] ===== COMPLETED =====")
    
    # Save results
    with lock:
        test_results.extend([(client_id, test, result) for test, result in results])


def save_results():
    """Save test results to file"""
    total = len(test_results)
    passed = sum(1 for _, _, result in test_results if result)
    failed = total - passed
    
    report = [
        "# HTTP Server Test Results",
        f"\n**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Server:** http://{HOST}:{PORT}",
        f"**Clients:** 3 concurrent",
        "\n---\n",
        "## Test Results\n",
        "| Client | Test | Result |",
        "|--------|------|--------|"
    ]
    
    for client_id, test, result in test_results:
        status = "PASS" if result else "FAIL"
        report.append(f"| Client-{client_id} | {test} | {status} |")
    
    report.extend([
        "\n---\n",
        "## Summary\n",
        f"**Total Tests:** {total}",
        f"**Passed:** {passed}",
        f"**Failed:** {failed}",
        f"**Success Rate:** {(passed/total*100):.1f}%",
        f"\n### {'ALL TESTS PASSED!' if failed == 0 else f'{failed} TEST(S) FAILED'}"
    ])
    
    with open("testing/test_results.md", 'w') as f:
        f.write('\n'.join(report))
    
    print(f"\n{'='*50}")
    print(f"Test Summary: {passed}/{total} passed ({(passed/total*100):.0f}%)")
    print(f"Results saved to: testing/test_results.md")
    print(f"{'='*50}")


if __name__ == "__main__":
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    
    print("="*50)
    print("HTTP SERVER TEST SUITE")
    print("="*50)
    print(f"Server: http://{HOST}:{PORT}")
    print(f"Clients: 3 concurrent")
    print("="*50)
    
    # Run 3 clients concurrently
    threads = []
    for i in range(1, 4):
        t = threading.Thread(target=run_client, args=(i,))
        threads.append(t)
        t.start()
        time.sleep(0.05)
    
    for t in threads:
        t.join()
    
    print("\n" + "="*50)
    print("ALL CLIENTS COMPLETED")
    print("="*50)
    
    save_results()
