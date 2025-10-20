"""
Test script for account deletion endpoint

Usage:
    python test_account_deletion.py YOUR_JWT_TOKEN

This will test the DELETE /api/v1/users/me endpoint
"""

import sys
import requests

def test_account_deletion(token: str):
    """Test account deletion endpoint"""

    url = "http://localhost:8000/api/v1/users/me"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print("🧪 Testing Account Deletion Endpoint")
    print(f"URL: {url}")
    print(f"Token: {token[:20]}..." if len(token) > 20 else f"Token: {token}")
    print()

    # Test 1: Get user profile first (to verify user exists)
    print("1️⃣ Fetching user profile...")
    profile_url = "http://localhost:8000/api/v1/users/profile"
    profile_response = requests.get(profile_url, headers=headers)

    if profile_response.status_code == 200:
        user_data = profile_response.json()
        print(f"✅ User found: {user_data.get('email')}")
        print(f"   User ID: {user_data.get('id')}")
        print(f"   Credits: {user_data.get('credits')}")
        print(f"   Total Checks: {user_data.get('stats', {}).get('totalChecks', 0)}")
    else:
        print(f"❌ Failed to get profile: {profile_response.status_code}")
        print(f"   Response: {profile_response.text}")
        return

    print()

    # Test 2: Delete account
    print("2️⃣ Deleting user account...")
    confirmation = input("⚠️  Are you sure you want to delete this account? Type 'DELETE' to confirm: ")

    if confirmation != "DELETE":
        print("❌ Deletion cancelled")
        return

    delete_response = requests.delete(url, headers=headers)

    print()
    print(f"Status Code: {delete_response.status_code}")

    if delete_response.status_code == 200:
        result = delete_response.json()
        print(f"✅ Account deleted successfully!")
        print(f"   Message: {result.get('message')}")
        print(f"   User ID: {result.get('userId')}")
    else:
        print(f"❌ Deletion failed: {delete_response.status_code}")
        print(f"   Response: {delete_response.text}")
        return

    print()

    # Test 3: Verify user is gone
    print("3️⃣ Verifying user is deleted...")
    verify_response = requests.get(profile_url, headers=headers)

    if verify_response.status_code == 404:
        print("✅ User successfully deleted (404 Not Found)")
    elif verify_response.status_code == 401:
        print("✅ User successfully deleted (401 Unauthorized - expected if token is invalidated)")
    else:
        print(f"⚠️  Unexpected status: {verify_response.status_code}")
        print(f"   Response: {verify_response.text}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Error: JWT token required")
        print()
        print("Usage:")
        print("    python test_account_deletion.py YOUR_JWT_TOKEN")
        print()
        print("To get a JWT token:")
        print("    1. Sign in to http://localhost:3000")
        print("    2. Open DevTools → Application → Local Storage")
        print("    3. Find __clerk_db_jwt or similar")
        print("    4. Copy the token value")
        sys.exit(1)

    token = sys.argv[1]

    try:
        test_account_deletion(token)
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to backend")
        print("   Make sure the backend is running: cd backend && .\\start-backend.bat")
    except Exception as e:
        print(f"❌ Error: {e}")
