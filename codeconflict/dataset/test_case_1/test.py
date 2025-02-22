from fastapi.testclient import TestClient
import pytest
import os
import requests
import json

BASE_URL = "http://localhost:8080"

# For direct HTTP requests
def test_health_check():
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200
    assert response.text == '"I am alive"'  # Fixed: Include quotes in expected response

def test_read_file():
    # Create a test file
    test_content = "test content"
    # Fixed: Send content as JSON with proper key
    response = requests.post(
        f"{BASE_URL}/write/test_read.txt",
        json={"content": test_content}
    )

    # Test reading existing file
    response = requests.get(f"{BASE_URL}/read/test_read.txt")
    assert response.status_code == 200
    assert response.json() == {"content": test_content}

    # Test reading non-existent file
    response = requests.get(f"{BASE_URL}/read/nonexistent.txt")
    assert response.status_code == 404

def test_write_file():
    # Test writing to a new file
    test_content = "hello world"
    # Fixed: Send content as JSON with proper key
    response = requests.post(
        f"{BASE_URL}/write/test_write.txt",
        json={"content": test_content}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "success"}

    # Verify file was written correctly
    response = requests.get(f"{BASE_URL}/read/test_write.txt")
    assert response.status_code == 200
    assert response.json()["content"] == test_content

    # Test writing to nested path
    nested_content = "nested content"
    # Fixed: Send content as JSON with proper key
    response = requests.post(
        f"{BASE_URL}/write/nested/path/test.txt",
        json={"content": nested_content}
    )
    assert response.status_code == 200
    
    # Verify nested file exists by trying to read it
    response = requests.get(f"{BASE_URL}/read/nested/path/test.txt")
    assert response.status_code == 200
    assert response.json()["content"] == nested_content

def test_execute_bash():
    # Test simple command
    # Fixed: Send command as JSON with proper key
    response = requests.post(
        f"{BASE_URL}/bash",
        json={"command": "echo 'test'"}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["stdout"].strip() == "test"
    assert result["exit_code"] == 0

    # Test command with error
    response = requests.post(
        f"{BASE_URL}/bash",
        json={"command": "nonexistent_command"}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["exit_code"] != 0

def teardown_module(module):
    """Clean up test files after tests"""
    # Clean up using bash endpoint
    test_files = [
        "test_read.txt",
        "test_write.txt",
        "nested/path/test.txt"
    ]
    for file in test_files:
        requests.post(
            f"{BASE_URL}/bash",
            json={"command": f"rm -f {file}"}
        )
    requests.post(
        f"{BASE_URL}/bash",
        json={"command": "rm -rf nested"}
    )