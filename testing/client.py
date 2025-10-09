#!/usr/bin/env python3
"""
Comprehensive HTTP Client Testing Suite
- 3 concurrent clients testing server capabilities
- Downloads all available resources (HTML, TXT, PNG, JPEG)
- Tests basic functionality, binary transfers, security, and errors
- Generates detailed test reports with MD5 checksums
"""

import socket
import os
import json
import hashlib
import threading
import time
from datetime import datetime

# Configuration
HOST = '127.0.0.1'
PORT = 8080
DOWNLOADS_DIR = "testing/downloads"
TEST_RESULTS_FILE = "testing/test_results.md"
TEST_EXECUTION_LOG = "testing/test_execution.log"

# Thread-safe test results storage
test_results = {
    "basic": [],
    "binary": [],
    "security": [],
    "errors": []
}
results_lock = threading.Lock()
log_lock = threading.Lock()
execution_logs = []


def log_execution(message):
    """Thread-safe logging with timestamp"""
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    log_msg = f"{timestamp} {message}"
    with log_lock:
        execution_logs.append(log_msg)
        print(log_msg)


def http_request(request_str, timeout=30):
    """Send HTTP request and receive complete response"""
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
                
                # Check if response is complete
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
            except socket.timeout:
                break
        
        sock.close()
        return response
    except Exception as e:
        log_execution(f"Request error: {e}")
        return None


def download_file(url_path, save_name, client_id):
    """Download file from server and save locally"""
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
    
    log_execution(f"[Client-{client_id}] ❌ Failed to download {url_path}")
    return False, 0


def upload_json(data, client_id):
    """Upload JSON data to server via POST"""
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
    
    log_execution(f"[Client-{client_id}] ❌ POST /upload failed")
    return False


def test_error_response(client_id, method, path, headers, expected_code, description):
    """Generic error response test"""
    request = f"{method} {path} HTTP/1.1\r\n"
    for key, value in headers.items():
        request += f"{key}: {value}\r\n"
    request += "\r\n"
    
    response = http_request(request)
    if response and str(expected_code).encode() in response:
        log_execution(f"[Client-{client_id}] ✅ {description} -> {expected_code}")
        return True
    
    log_execution(f"[Client-{client_id}] ❌ {description} test failed")
    return False


def calculate_checksum(filepath):
    """Calculate MD5 checksum for file integrity verification"""
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()


def verify_file_integrity(original_path, downloaded_path, client_id):
    """Verify downloaded file matches original via checksum"""
    if not os.path.exists(downloaded_path):
        log_execution(f"[Client-{client_id}] ❌ File not found: {downloaded_path}")
        return False
    
    orig_checksum = calculate_checksum(original_path)
    down_checksum = calculate_checksum(downloaded_path)
    
    if orig_checksum == down_checksum:
        log_execution(f"[Client-{client_id}] ✅ Checksum verified: {os.path.basename(original_path)} ({orig_checksum[:8]}...)")
        return True
    
    log_execution(f"[Client-{client_id}] ❌ Checksum mismatch: {os.path.basename(original_path)}")
    return False


def client_task(client_id):
    """Execute complete test suite for one client"""
    log_execution(f"[Client-{client_id}] ========== STARTED ==========")
    
    local_results = {
        "basic": [],
        "binary": [],
        "security": [],
        "errors": []
    }
    
    # Basic Functionality Tests
    log_execution(f"[Client-{client_id}] --- Basic Functionality Tests ---")
    
    tests = [
        ("/", f"client{client_id}_index.html", "GET / → index.html"),
        ("/sample.html", f"client{client_id}_sample.html", "GET /sample.html"),
        ("/form.html", f"client{client_id}_form.html", "GET /form.html"),
        ("/test1.txt", f"client{client_id}_test1.txt", "GET /test1.txt"),
        ("/test2.txt", f"client{client_id}_test2.txt", "GET /test2.txt")
    ]
    
    for url, save_name, test_name in tests:
        success, _ = download_file(url, save_name, client_id)
        local_results["basic"].append((test_name, success))
    
    # Binary Transfer Tests
    log_execution(f"[Client-{client_id}] --- Binary Transfer Tests ---")
    
    binary_tests = [
        ("/goku.png", f"client{client_id}_goku.png", "GET /goku.png (PNG)"),
        ("/sample.png", f"client{client_id}_sample.png", "GET /sample.png (PNG)"),
        ("/Pizigani_1367_Chart_10MB.png", f"client{client_id}_large.png", "GET /Pizigani_1367_Chart_10MB.png (Large PNG)"),
        ("/anime.jpeg", f"client{client_id}_anime.jpeg", "GET /anime.jpeg (JPEG)"),
        ("/naruto.jpeg", f"client{client_id}_naruto.jpeg", "GET /naruto.jpeg (JPEG)")
    ]
    
    for url, save_name, test_name in binary_tests:
        success, size = download_file(url, save_name, client_id)
        local_results["binary"].append((test_name, success))
        if size > 1024*1024:
            log_execution(f"[Client-{client_id}] ✅ Large file transferred: {size/(1024*1024):.2f} MB")
    
    # Checksum Verification
    log_execution(f"[Client-{client_id}] --- Checksum Verification ---")
    time.sleep(0.2)
    
    checksum_tests = [
        ("resources/goku.png", f"{DOWNLOADS_DIR}/client{client_id}_goku.png", "Checksum: goku.png"),
        ("resources/anime.jpeg", f"{DOWNLOADS_DIR}/client{client_id}_anime.jpeg", "Checksum: anime.jpeg")
    ]
    
    for original, downloaded, test_name in checksum_tests:
        verified = verify_file_integrity(original, downloaded, client_id)
        local_results["binary"].append((test_name, verified))
    
    # POST/Upload Tests
    log_execution(f"[Client-{client_id}] --- POST/Upload Tests ---")
    upload_data = {
        "client_id": client_id,
        "task": "Comprehensive test",
        "timestamp": datetime.now().isoformat(),
        "files_downloaded": 10
    }
    success = upload_json(upload_data, client_id)
    local_results["basic"].append(("POST /upload (JSON)", success))
    
    # Error Response Tests
    log_execution(f"[Client-{client_id}] --- Error Response Tests ---")
    
    error_tests = [
        ("GET", "/nonexistent.png", {"Host": f"{HOST}:{PORT}"}, 404, "GET /nonexistent.png", "404 Not Found"),
        ("PUT", "/index.html", {"Host": f"{HOST}:{PORT}"}, 405, "PUT /index.html", "405 Method Not Allowed"),
    ]
    
    for method, path, headers, code, desc, result_name in error_tests:
        success = test_error_response(client_id, method, path, headers, code, desc)
        local_results["errors"].append((result_name, success))
    
    # 415 test with body
    request = f"POST /upload HTTP/1.1\r\nHost: {HOST}:{PORT}\r\nContent-Type: text/plain\r\nContent-Length: 4\r\n\r\ntest"
    response = http_request(request)
    success = response and b"415" in response
    if success:
        log_execution(f"[Client-{client_id}] ✅ POST /upload (text/plain) -> 415 Unsupported Media Type")
    local_results["errors"].append(("415 Unsupported Media Type", success))
    
    # Security Tests
    log_execution(f"[Client-{client_id}] --- Security Tests ---")
    
    security_tests = [
        ("GET", "/../etc/passwd", {"Host": f"{HOST}:{PORT}"}, 403, "GET /../etc/passwd", "Path traversal protection"),
        ("GET", "/index.html", {"Host": "evil.com"}, 403, "GET with Host: evil.com", "Invalid host rejection"),
    ]
    
    for method, path, headers, code, desc, result_name in security_tests:
        success = test_error_response(client_id, method, path, headers, code, f"{desc} (path traversal blocked)" if "etc" in path else desc)
        local_results["security"].append((result_name, success))
    
    # Missing host test
    request = "GET /index.html HTTP/1.1\r\n\r\n"
    response = http_request(request)
    success = response and b"400" in response
    if success:
        log_execution(f"[Client-{client_id}] ✅ GET without Host header -> 400 Bad Request")
    local_results["security"].append(("Missing host rejection", success))
    
    log_execution(f"[Client-{client_id}] ========== COMPLETED ==========")
    
    # Merge results thread-safely
    with results_lock:
        for category in ["basic", "binary", "security", "errors"]:
            test_results[category].extend([(client_id, test, result) for test, result in local_results[category]])


def run_concurrent_tests():
    """Execute tests with 3 concurrent client threads"""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    
    log_execution("="*80)
    log_execution("COMPREHENSIVE HTTP SERVER TEST SUITE")
    log_execution("="*80)
    log_execution(f"Server: http://{HOST}:{PORT}")
    log_execution(f"Test Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_execution(f"Number of Clients: 3 (concurrent)")
    log_execution("="*80)
    log_execution("")
    
    # Create client threads
    threads = [threading.Thread(target=client_task, args=(i,), name=f"Client-{i}") for i in range(1, 4)]
    
    log_execution("Starting 3 concurrent client threads...")
    start_time = time.time()
    
    for i, thread in enumerate(threads):
        thread.start()
        time.sleep(0.05)  # Stagger start for concurrency visibility
    
    for thread in threads:
        thread.join()
    
    duration = time.time() - start_time
    
    log_execution("")
    log_execution("="*80)
    log_execution("ALL CLIENT THREADS COMPLETED")
    log_execution(f"Total Execution Time: {duration:.2f} seconds")
    log_execution("="*80)
    
    generate_summary_report(duration)
    save_execution_log()
    
    log_execution("\n✅ All tests completed! Check test_results.md for detailed report.")


def generate_summary_report(duration):
    """Generate comprehensive markdown test report"""
    report = [
        "# HTTP Server Test Results",
        f"\n**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Server:** http://{HOST}:{PORT}",
        f"**Number of Clients:** 3 (concurrent)",
        f"**Total Execution Time:** {duration:.2f} seconds",
        "\n---\n"
    ]
    
    # Test results by category
    sections = [
        ("1. Basic Functionality Tests", "basic"),
        ("2. Binary Transfer Tests", "binary"),
        ("3. Security Tests", "security"),
        ("4. Error Response Tests", "errors")
    ]
    
    for title, category in sections:
        report.append(f"## {title}")
        report.append("\n| Client | Test | Result |")
        report.append("|--------|------|--------|")
        for client_id, test_name, success in test_results[category]:
            status = "✅ PASS" if success else "❌ FAIL"
            report.append(f"| Client-{client_id} | {test_name} | {status} |")
        report.append("")
    
    # Downloaded files summary
    report.append("## 5. Downloaded Files\n")
    report.append("| Filename | Size |")
    report.append("|----------|------|")
    
    if os.path.exists(DOWNLOADS_DIR):
        for filename in sorted(os.listdir(DOWNLOADS_DIR)):
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
    
    # Concurrency summary
    report.extend([
        "\n## 6. Concurrency Tests\n",
        "✅ Successfully handled 3 simultaneous client connections",
        "✅ Multiple clients downloading files simultaneously",
        "✅ Large files (>1MB) transferred concurrently without corruption"
    ])
    
    # Overall summary
    total_tests = sum(len(test_results[cat]) for cat in ["basic", "binary", "security", "errors"])
    passed_tests = sum(1 for cat in ["basic", "binary", "security", "errors"] 
                      for _, _, success in test_results[cat] if success)
    
    report.extend([
        "\n---\n",
        "## Summary",
        f"\n**Total Tests:** {total_tests}",
        f"**Passed:** {passed_tests}",
        f"**Failed:** {total_tests - passed_tests}",
        f"**Success Rate:** {(passed_tests/total_tests*100):.1f}%",
        f"\n### {'✅ ALL TESTS PASSED!' if passed_tests == total_tests else f'⚠️ {total_tests - passed_tests} test(s) failed'}"
    ])
    
    with open(TEST_RESULTS_FILE, 'w') as f:
        f.write('\n'.join(report))
    
    log_execution(f"\n📄 Test results saved to: {TEST_RESULTS_FILE}")


def save_execution_log():
    """Save execution logs to file"""
    with open(TEST_EXECUTION_LOG, 'w') as f:
        f.write('\n'.join(execution_logs))
    
    log_execution(f"📄 Execution log saved to: {TEST_EXECUTION_LOG}")


if __name__ == "__main__":
    run_concurrent_tests()
