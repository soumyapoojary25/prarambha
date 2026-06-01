"""WSGI entry point for Vercel and other production servers."""
import os
import sys

# Add project root to path
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import app

if __name__ == "__main__":
    app.run()
