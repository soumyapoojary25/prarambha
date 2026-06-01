#!/usr/bin/env python
"""Test POST requests to find errors."""
from app import app
from flask import session

print("=" * 70)
print("TESTING POST REQUESTS - Finding the 500 Error")
print("=" * 70)

with app.test_client() as client:
    # First, try to login to create a session
    print("\n1. Testing /admin/login POST...")
    with client:
        # Test login POST with valid credentials
        r = client.post('/admin/login', data={
            'password': 'Admin@123'
        }, follow_redirects=False)
        print(f"   Login response: {r.status_code}")
        
        # Now try seats POST while authenticated
        if 'admin_authenticated' in dict(session):
            print("\n2. Testing /admin/seats POST (authenticated)...")
            r = client.post('/admin/seats', data={
                'course_BCA': '180'
            }, follow_redirects=False)
            print(f"   Seats update response: {r.status_code}")
            if r.status_code >= 400:
                try:
                    print(f"   Error: {r.json}")
                except:
                    print(f"   Response: {r.data.decode()[:300]}")
        else:
            print("   (Not authenticated, skipping /seats POST test)")

print("\n" + "=" * 70)
