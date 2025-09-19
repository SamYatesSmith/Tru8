import requests
import json

# Test creating a check via the API
API_URL = "http://localhost:8000/api/v1"

# First get a test token - we need to simulate what the frontend does
# For now, let's try without auth to see the error
response = requests.post(
    f"{API_URL}/checks/",
    headers={"Content-Type": "application/json"},
    json={
        "input_type": "text",
        "content": "Test claim to verify"
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")