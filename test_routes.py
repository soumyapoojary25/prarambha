#!/usr/bin/env python
"""Test all routes to find errors."""
from app import app
import traceback
import sys

print("=" * 70)
print("COMPREHENSIVE ERROR TESTING - Testing All Routes")
print("=" * 70)

test_routes = [
    ('/health', 'GET'),
    ('/admin/login', 'GET'),
    ('/admin/', 'GET'),
    ('/admin/dashboard', 'GET'),
    ('/admin/seats', 'GET'),
    ('/admin/applications', 'GET'),
    ('/admin/students', 'GET'),
    ('/admin/profile', 'GET'),
]

errors_found = []

with app.test_client() as client:
    for route, method in test_routes:
        try:
            if method == 'GET':
                r = client.get(route)
            else:
                r = client.post(route)
            
            status = r.status_code
            symbol = "✓" if status < 400 else "✗"
            print(f"{symbol} {method:4} {route:30} → {status}")
            
            if status >= 400:
                error_info = f"{route} returned {status}"
                try:
                    data = r.json
                    print(f"     Error: {data}")
                    error_info += f": {data}"
                except:
                    resp = r.data.decode()[:200]
                    print(f"     Response: {resp}")
                    error_info += f": {resp}"
                errors_found.append(error_info)
                    
        except Exception as e:
            print(f"✗ {method:4} {route:30} → Exception: {type(e).__name__}: {str(e)}")
            errors_found.append(f"{route}: {type(e).__name__}: {str(e)}")
            traceback.print_exc()

print("=" * 70)
print(f"Summary: {len([r for r in test_routes if True]) - len(errors_found)}/{len(test_routes)} routes working")
if errors_found:
    print("\nErrors found:")
    for error in errors_found:
        print(f"  - {error}")
else:
    print("✓ All routes working!")
print("=" * 70)
