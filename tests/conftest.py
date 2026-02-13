"""
Pytest configuration and fixtures
"""

import os
import sys
import pytest


# Ensure repository root is on sys.path so tests can import top-level modules
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
