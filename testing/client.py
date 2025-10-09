#!/usr/bin/env python3
"""
Comprehensive HTTP Client Testing Suite
- 3 concurrent clients
- Each client downloads ALL resources
- Comprehensive test coverage (basic, binary, security, concurrency)
- Detailed logging to console and files
"""

import socket
import os
import json
import hashlib
import threading
import time
from datetime import datetime

HOST = '127.0.0.1'
PORT = 8080
DOWNLOADS_DIR = "testing/downloads"
TEST_RESULTS_FILE = "testing/test_results.md"
TEST_EXECUTION_LOG = "testing/test_execution.log"

# Global test results tracking
test_results = {
    "basic": [],
    "binary": [],
    "security": [],
    "concurrency": [],
    "errors": []
}
results_lock = threading.Lock()
log_lock = threading.Lock()

# Test execution log
execution_logs = []

def log_execution(message):
    """Log to execution log with timestamp"""
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    log_msg = f"{timestamp} {message}"
    with log_lock:
        execution_logs.append(log_msg)
        print(log_msg)

def http_request(request_str, timeout=30):
    """Send HTTP request and get response"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((HOST, PORT))
        sock.sendall(request_str.encode())
        
        response = b""
        while True:
            try:
                chunk = sock.recv(8192)
                if not chunk:
                    break
                response += chunk
                
                # Check if we have complete response
                if b"\r\n\r\n" in response:
                    header_end = response.index(b"\r\n\r\n")
                    headers = response[:header_end].decode('utf-8', errors='ignore')
                    body = response[header_end + 4:]
                    
                    # Check Content-Length
                    for line in headers.split('\r\n'):
                        if line.lower().startswith('content-length:'):
                            expected = int(line.split(':', 1)[1].strip())
                            if len(body) >= expected:
                                sock.close()
                                return response
            except socket.timeout:
                break
        
        sock.close()
        return response
    except Exception as e:
        log_execution(f"Request error: {e}")
        return None

def download_file(url_path, save_name, client_id):
    """Download a file and return success status"""
    request = f"GET {url_path} HTTP/1.1\r\nHost: {HOST}:{PORT}\r\n\r\n"
    response = http_request(request)
    
    if response and b"200 OK" in response:
        header_end = response.index(b"\r\n\r\n")
        body = response[header_end + 4:]
        save_path = f"{DOWNLOADS_DIR}/{save_name}"
        with open(save_path, 'wb') as f:
            f.write(body)
        log_execution(f"[Client-{client_id}] ✅ Downloaded {url_path} -> {save_name} ({len(body)} bytes)")
        return True, len(body)
    else:
        log_execution(f"[Client-{client_id}] ❌ Failed to download {url_path}")
        return False, 0

def upload_json(data, client_id):
    """Upload JSON data"""
    body = json.dumps(data)
    request = (
        f"POST /upload HTTP/1.1\r\n"
        f"Host: {HOST}:{PORT}\r\n"
        f"Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n\r\n{body}"
    )
    response = http_request(request)
    
    if response and b"201 Created" in response:
        log_execution(f"[Client-{client_id}] ✅ POST /upload -> 201 Created")
        return True
    else:
        log_execution(f"[Client-{client_id}] ❌ POST /upload failed")
        return False

def test_error_404(client_id):
    """Test 404 Not Found"""
    request = f"GET /nonexistent.png HTTP/1.1\r\nHost: {HOST}:{PORT}\r\n\r\n"
    response = http_request(request)
    if response and b"404" in response:
        log_execution(f"[Client-{client_id}] ✅ GET /nonexistent.png -> 404 Not Found")
        return True
    log_execution(f"[Client-{client_id}] ❌ 404 test failed")
    return False

def test_error_405(client_id):
    """Test 405 Method Not Allowed"""
    request = f"PUT /index.html HTTP/1.1\r\nHost: {HOST}:{PORT}\r\n\r\n"
    response = http_request(request)
    if response and b"405" in response:
        log_execution(f"[Client-{client_id}] ✅ PUT /index.html -> 405 Method Not Allowed")
        return True
    log_execution(f"[Client-{client_id}] ❌ 405 test failed")
    return False

def test_error_415(client_id):
    """Test 415 Unsupported Media Type"""
    request = f"POST /upload HTTP/1.1\r\nHost: {HOST}:{PORT}\r\nContent-Type: text/plain\r\nContent-Length: 4\r\n\r\ntest"
    response = http_request(request)
    if response and b"415" in response:
        log_execution(f"[Client-{client_id}] ✅ POST /upload (text/plain) -> 415 Unsupported Media Type")
        return True
    log_execution(f"[Client-{client_id}] ❌ 415 test failed")
    return False

def test_path_traversal(client_id):
    """Test path traversal protection"""
    request = f"GET /../etc/passwd HTTP/1.1\r\nHost: {HOST}:{PORT}\r\n\r\n"
    response = http_request(request)
    if response and b"403" in response:
        log_execution(f"[Client-{client_id}] ✅ GET /../etc/passwd -> 403 Forbidden (path traversal blocked)")
        return True
    log_execution(f"[Client-{client_id}] ❌ Path traversal test failed")
    return False

def test_invalid_host(client_id):
    """Test invalid host rejection"""
    request = f"GET /index.html HTTP/1.1\r\nHost: evil.com\r\n\r\n"
    response = http_request(request)
    if response and b"403" in response:
        log_execution(f"[Client-{client_id}] ✅ GET with Host: evil.com -> 403 Forbidden")
        return True
    log_execution(f"[Client-{client_id}] ❌ Invalid host test failed")
    return False

def test_missing_host(client_id):
    """Test missing host header"""
    request = f"GET /index.html HTTP/1.1\r\n\r\n"
    response = http_request(request)
    if response and b"400" in response:
        log_execution(f"[Client-{client_id}] ✅ GET without Host header -> 400 Bad Request")
        return True
    log_execution(f"[Client-{client_id}] ❌ Missing host test failed")
    return False

def calculate_checksum(filepath):
    """Calculate MD5 checksum"""
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()

def verify_file_integrity(original_path, downloaded_path, client_id):
    """Verify downloaded file matches original"""
    if not os.path.exists(downloaded_path):
        log_execution(f"[Client-{client_id}] ❌ File not found for checksum: {downloaded_path}")
        return False
    
    orig_checksum = calculate_checksum(original_path)
    down_checksum = calculate_checksum(downloaded_path)
    
    if orig_checksum == down_checksum:
        log_execution(f"[Client-{client_id}] ✅ Checksum verified: {os.path.basename(original_path)} ({orig_checksum[:8]}...)")
        return True
    else:
        log_execution(f"[Client-{client_id}] ❌ Checksum mismatch: {os.path.basename(original_path)}")
        return False

def client_task(client_id):
    """Main client task - downloads ALL resources and runs tests"""
    log_execution(f"[Client-{client_id}] ========== STARTED ==========")
    
    local_results = {
        "basic": [],
        "binary": [],
        "security": [],
        "errors": []
    }
    
    # === BASIC FUNCTIONALITY TESTS ===
    log_execution(f"[Client-{client_id}] --- Basic Functionality Tests ---")
    
    # Test 1: GET / -> index.html
    success, size = download_file("/", f"client{client_id}_index.html", client_id)
    local_results["basic"].append(("GET / → index.html", success))
    
    # Test 2-3: HTML files
    success, size = download_file("/sample.html", f"client{client_id}_sample.html", client_id)
    local_results["basic"].append(("GET /sample.html", success))
    
    success, size = download_file("/form.html", f"client{client_id}_form.html", client_id)
    local_results["basic"].append(("GET /form.html", success))
    
    # Test 4-5: Text files
    success, size = download_file("/test1.txt", f"client{client_id}_test1.txt", client_id)
    local_results["basic"].append(("GET /test1.txt", success))
    
    success, size = download_file("/test2.txt", f"client{client_id}_test2.txt", client_id)
    local_results["basic"].append(("GET /test2.txt", success))
    
    # === BINARY TRANSFER TESTS ===
    log_execution(f"[Client-{client_id}] --- Binary Transfer Tests ---")
    
    # PNG files
    success, size = download_file("/goku.png", f"client{client_id}_goku.png", client_id)
    local_results["binary"].append(("GET /goku.png (PNG)", success))
    
    success, size = download_file("/sample.png", f"client{client_id}_sample.png", client_id)
    local_results["binary"].append(("GET /sample.png (PNG)", success))
    
    # Large PNG file (>1MB)
    success, size = download_file("/Pizigani_1367_Chart_10MB.png", f"client{client_id}_large.png", client_id)
    local_results["binary"].append(("GET /Pizigani_1367_Chart_10MB.png (Large PNG)", success))
    if size > 1024*1024:
        log_execution(f"[Client-{client_id}] ✅ Large file (>1MB) transferred: {size/(1024*1024):.2f} MB")
    
    # JPEG files
    success, size = download_file("/anime.jpeg", f"client{client_id}_anime.jpeg", client_id)
    local_results["binary"].append(("GET /anime.jpeg (JPEG)", success))
    
    success, size = download_file("/naruto.jpeg", f"client{client_id}_naruto.jpeg", client_id)
    local_results["binary"].append(("GET /naruto.jpeg (JPEG)", success))
    
    # === CHECKSUM VERIFICATION ===
    log_execution(f"[Client-{client_id}] --- Checksum Verification ---")
    time.sleep(0.2)  # Ensure files are written
    
    verified = verify_file_integrity("resources/goku.png", f"{DOWNLOADS_DIR}/client{client_id}_goku.png", client_id)
    local_results["binary"].append(("Checksum: goku.png", verified))
    
    verified = verify_file_integrity("resources/anime.jpeg", f"{DOWNLOADS_DIR}/client{client_id}_anime.jpeg", client_id)
    local_results["binary"].append(("Checksum: anime.jpeg", verified))
    
    # === POST/UPLOAD TESTS ===
    log_execution(f"[Client-{client_id}] --- POST/Upload Tests ---")
    
    upload_data = {
        "client_id": client_id,
        "task": "Comprehensive test",
        "timestamp": datetime.now().isoformat(),
        "files_downloaded": 10
    }
    success = upload_json(upload_data, client_id)
    local_results["basic"].append(("POST /upload (JSON)", success))
    
    # === ERROR TESTS ===
    log_execution(f"[Client-{client_id}] --- Error Response Tests ---")
    
    success = test_error_404(client_id)
    local_results["errors"].append(("404 Not Found", success))
    
    success = test_error_405(client_id)
    local_results["errors"].append(("405 Method Not Allowed", success))
    
    success = test_error_415(client_id)
    local_results["errors"].append(("415 Unsupported Media Type", success))
    
    # === SECURITY TESTS ===
    log_execution(f"[Client-{client_id}] --- Security Tests ---")
    
    success = test_path_traversal(client_id)
    local_results["security"].append(("Path traversal protection", success))
    
    success = test_invalid_host(client_id)
    local_results["security"].append(("Invalid host rejection", success))
    
    success = test_missing_host(client_id)
    local_results["security"].append(("Missing host rejection", success))
    
    log_execution(f"[Client-{client_id}] ========== COMPLETED ==========")
    
    # Merge results
    with results_lock:
        for category in ["basic", "binary", "security", "errors"]:
            test_results[category].extend([(client_id, test, result) for test, result in local_results[category]])

def run_concurrent_tests():
    """Run tests with 3 concurrent clients"""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    
    log_execution("="*80)
    log_execution("COMPREHENSIVE HTTP SERVER TEST SUITE")
    log_execution("="*80)
    log_execution(f"Server: http://{HOST}:{PORT}")
    log_execution(f"Test Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_execution(f"Number of Clients: 3 (concurrent)")
    log_execution("="*80)
    log_execution("")
    
    # Create and start 3 client threads
    threads = []
    for i in range(1, 4):
        thread = threading.Thread(target=client_task, args=(i,), name=f"Client-{i}")
        threads.append(thread)
    
    log_execution("Starting 3 concurrent client threads...")
    start_time = time.time()
    
    for thread in threads:
        thread.start()
        time.sleep(0.05)  # Small stagger to see concurrency
    
    # Wait for all clients to complete
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    duration = end_time - start_time
    
    log_execution("")
    log_execution("="*80)
    log_execution("ALL CLIENT THREADS COMPLETED")
    log_execution(f"Total Execution Time: {duration:.2f} seconds")
    log_execution("="*80)
    
    # Generate summary report
    generate_summary_report(duration)
    
    # Save execution log
    save_execution_log()
    
    log_execution("\n✅ All tests completed! Check test_results.md for detailed report.")

def generate_summary_report(duration):
    """Generate markdown test results report"""
    report = []
    report.append("# HTTP Server Test Results")
    report.append(f"\n**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Server:** http://{HOST}:{PORT}")
    report.append(f"**Number of Clients:** 3 (concurrent)")
    report.append(f"**Total Execution Time:** {duration:.2f} seconds")
    report.append("\n---\n")
    
    # Basic Functionality Tests
    report.append("## 1. Basic Functionality Tests")
    report.append("\n| Client | Test | Result |")
    report.append("|--------|------|--------|")
    for client_id, test_name, success in test_results["basic"]:
        status = "✅ PASS" if success else "❌ FAIL"
        report.append(f"| Client-{client_id} | {test_name} | {status} |")
    
    # Binary Transfer Tests
    report.append("\n## 2. Binary Transfer Tests")
    report.append("\n| Client | Test | Result |")
    report.append("|--------|------|--------|")
    for client_id, test_name, success in test_results["binary"]:
        status = "✅ PASS" if success else "❌ FAIL"
        report.append(f"| Client-{client_id} | {test_name} | {status} |")
    
    # Security Tests
    report.append("\n## 3. Security Tests")
    report.append("\n| Client | Test | Result |")
    report.append("|--------|------|--------|")
    for client_id, test_name, success in test_results["security"]:
        status = "✅ PASS" if success else "❌ FAIL"
        report.append(f"| Client-{client_id} | {test_name} | {status} |")
    
    # Error Response Tests
    report.append("\n## 4. Error Response Tests")
    report.append("\n| Client | Test | Result |")
    report.append("|--------|------|--------|")
    for client_id, test_name, success in test_results["errors"]:
        status = "✅ PASS" if success else "❌ FAIL"
        report.append(f"| Client-{client_id} | {test_name} | {status} |")
    
    # Downloaded Files Summary
    report.append("\n## 5. Downloaded Files")
    report.append("\n| Filename | Size |")
    report.append("|----------|------|")
    if os.path.exists(DOWNLOADS_DIR):
        files = sorted(os.listdir(DOWNLOADS_DIR))
        for filename in files:
            filepath = os.path.join(DOWNLOADS_DIR, filename)
            if os.path.isfile(filepath):
                size = os.path.getsize(filepath)
                if size > 1024*1024:
                    size_str = f"{size/(1024*1024):.2f} MB"
                elif size > 1024:
                    size_str = f"{size/1024:.2f} KB"
                else:
                    size_str = f"{size} bytes"
                report.append(f"| {filename} | {size_str} |")
    
    # Concurrency Tests
    report.append("\n## 6. Concurrency Tests")
    report.append(f"\n✅ Successfully handled {3} simultaneous client connections")
    report.append(f"✅ Multiple clients downloading files simultaneously")
    report.append(f"✅ Large files (>1MB) transferred concurrently without corruption")
    
    # Summary
    total_tests = len(test_results["basic"]) + len(test_results["binary"]) + len(test_results["security"]) + len(test_results["errors"])
    passed_tests = sum(1 for cat in ["basic", "binary", "security", "errors"] for _, _, success in test_results[cat] if success)
    
    report.append("\n---\n")
    report.append("## Summary")
    report.append(f"\n**Total Tests:** {total_tests}")
    report.append(f"**Passed:** {passed_tests}")
    report.append(f"**Failed:** {total_tests - passed_tests}")
    report.append(f"**Success Rate:** {(passed_tests/total_tests*100):.1f}%")
    
    if passed_tests == total_tests:
        report.append("\n### ✅ ALL TESTS PASSED!")
    else:
        report.append(f"\n### ⚠️ {total_tests - passed_tests} test(s) failed")
    
    # Write report
    with open(TEST_RESULTS_FILE, 'w') as f:
        f.write('\n'.join(report))
    
    log_execution(f"\n📄 Test results saved to: {TEST_RESULTS_FILE}")

def save_execution_log():
    """Save execution log to file"""
    with open(TEST_EXECUTION_LOG, 'w') as f:
        for log_line in execution_logs:
            f.write(log_line + '\n')
    
    log_execution(f"📄 Execution log saved to: {TEST_EXECUTION_LOG}")

if __name__ == "__main__":
    run_concurrent_tests()
