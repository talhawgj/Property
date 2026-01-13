"""
Test script for the signin authentication endpoint.
Tests various scenarios including valid/invalid credentials.

Usage:
    python test_signin.py
"""

import asyncio
import httpx
import json
from datetime import datetime


BASE_URL = "http://localhost:8000"  # Adjust if your server runs on a different port


async def test_signin_valid():
    """Test signin with valid credentials"""
    print("\n" + "="*60)
    print("TEST 1: Signin with valid credentials")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/signin",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✓ SUCCESS: User authenticated")
            print(f"  Token Type: {data.get('token_type')}")
            print(f"  Access Token: {data.get('access_token')[:50]}...")
            print(f"  User Email: {data.get('user', {}).get('email')}")
            print(f"  User ID: {data.get('user', {}).get('id')}")
            return data.get('access_token')
        else:
            print("\n✗ FAILED: Authentication failed")
            return None


async def test_signin_invalid_password():
    """Test signin with invalid password"""
    print("\n" + "="*60)
    print("TEST 2: Signin with invalid password")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/signin",
            json={
                "email": "test@example.com",
                "password": "wrongpassword"
            }
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 401:
            print("\n✓ SUCCESS: Correctly rejected invalid password")
        else:
            print("\n✗ FAILED: Should have returned 401")


async def test_signin_invalid_email():
    """Test signin with non-existent email"""
    print("\n" + "="*60)
    print("TEST 3: Signin with non-existent email")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/signin",
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword"
            }
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 401:
            print("\n✓ SUCCESS: Correctly rejected non-existent user")
        else:
            print("\n✗ FAILED: Should have returned 401")


async def test_signin_invalid_email_format():
    """Test signin with invalid email format"""
    print("\n" + "="*60)
    print("TEST 4: Signin with invalid email format")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/signin",
            json={
                "email": "not-an-email",
                "password": "anypassword"
            }
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 422:
            print("\n✓ SUCCESS: Correctly rejected invalid email format")
        else:
            print("\n✗ FAILED: Should have returned 422 (validation error)")


async def verify_token(token: str):
    """Verify JWT token structure"""
    print("\n" + "="*60)
    print("TEST 5: Verify JWT token structure")
    print("="*60)
    
    if not token:
        print("✗ SKIPPED: No token to verify")
        return
    
    # Decode JWT without verification (just to inspect)
    import base64
    try:
        parts = token.split('.')
        if len(parts) == 3:
            # Decode header and payload
            header = json.loads(base64.urlsafe_b64decode(parts[0] + '=='))
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=='))
            
            print("Token Header:")
            print(f"  {json.dumps(header, indent=2)}")
            print("\nToken Payload:")
            print(f"  {json.dumps(payload, indent=2)}")
            print("\n✓ SUCCESS: Token structure is valid")
        else:
            print("✗ FAILED: Invalid token structure")
    except Exception as e:
        print(f"✗ FAILED: Error decoding token: {e}")


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("SIGNIN AUTHENTICATION TESTS")
    print("="*60)
    print(f"Testing against: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Test valid signin
        token = await test_signin_valid()
        
        # Test invalid scenarios
        await test_signin_invalid_password()
        await test_signin_invalid_email()
        await test_signin_invalid_email_format()
        
        # Verify token
        await verify_token(token)
        
        print("\n" + "="*60)
        print("ALL TESTS COMPLETED")
        print("="*60 + "\n")
        
    except httpx.ConnectError:
        print("\n✗ ERROR: Could not connect to server")
        print(f"  Make sure the server is running at {BASE_URL}")
    except Exception as e:
        print(f"\n✗ ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(main())
