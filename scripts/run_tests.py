#!/usr/bin/env python3
"""
Test Runner for MongoDB Atlas Search API

This script provides a robust way to run the API endpoint tests.
It handles path configuration, dependency checking, and test reporting.

Usage:
  python run_tests.py [--verbose] [--collect-only] [--test-path TEST_PATH]
"""

import os
import sys
import argparse
import importlib.util
import subprocess
from pathlib import Path

# Add root directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
APP_DIR = os.path.join(ROOT_DIR, "app")

# Ensure the app directory is in the path
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, APP_DIR)

def check_dependencies():
    """Verify that all required dependencies are installed"""
    required_packages = [
        "pytest", "pytest-asyncio", "fastapi", "httpx", 
        "motor", "pymongo", "python-multipart"
    ]
    
    missing = []
    
    for package in required_packages:
        try:
            importlib.util.find_spec(package.replace("-", "_"))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Missing required packages: {', '.join(missing)}")
        install = input(f"Do you want to install them? (y/n): ")
        
        if install.lower() == "y":
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
                print("Dependencies installed successfully!")
            except Exception as e:
                print(f"Failed to install dependencies: {e}")
                return False
        else:
            print("Please install the required dependencies manually.")
            return False
    
    return True

def setup_test_environment():
    """Ensure the test environment is properly set up"""
    # Create tests directory if it doesn't exist
    tests_dir = os.path.join(APP_DIR, "tests")
    os.makedirs(tests_dir, exist_ok=True)
    
    # Create __init__.py if it doesn't exist
    init_file = os.path.join(tests_dir, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("# Test package\n")
    
    # Check for conftest.py (pytest configuration)
    conftest_file = os.path.join(tests_dir, "conftest.py")
    if not os.path.exists(conftest_file):
        print(f"Creating {conftest_file}...")
        with open(conftest_file, "w") as f:
            f.write("""
import pytest
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

@pytest.fixture
def test_app():
    from app.main import app
    return app
""")
    
    # Check if the API key environment variable is set for testing
    if not os.environ.get("TEST_API_KEY"):
        os.environ["TEST_API_KEY"] = "test_api_key_for_testing"

def run_tests(test_path=None, verbose=False, collect_only=False):
    """Run the pytest tests"""
    # Default test path if not specified
    if not test_path:
        test_path = os.path.join(APP_DIR, "tests", "test_endpoints.py")
    
    # Verify the test file exists
    if not os.path.exists(test_path):
        print(f"Test file not found: {test_path}")
        return False
    
    # Build pytest command
    pytest_args = ["-v"] if verbose else []
    if collect_only:
        pytest_args.append("--collect-only")
    
    # Run pytest
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_path] + pytest_args,
            cwd=APP_DIR,
            check=False,  # Don't fail on test failures
            capture_output=True,
            text=True
        )
        
        # Print output
        print("\n--- STDOUT ---\n")
        print(result.stdout)
        
        print("\n--- STDERR ---\n")
        print(result.stderr)
        
        print(f"\nTest exit code: {result.returncode}")
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error running tests: {e}")
        return False

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run MongoDB Atlas Search API tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--collect-only", action="store_true", help="Only collect tests, don't run them")
    parser.add_argument("--test-path", help="Specific test file or directory to run")
    
    args = parser.parse_args()
    
    # Print environment info
    print(f"Python: {sys.version}")
    print(f"Root directory: {ROOT_DIR}")
    print(f"App directory: {APP_DIR}")
    
    # Check for dependencies
    print("\nChecking dependencies...")
    if not check_dependencies():
        return 1
    
    # Setup environment
    print("\nSetting up test environment...")
    setup_test_environment()
    
    # Run tests
    print("\nRunning tests...")
    success = run_tests(
        test_path=args.test_path,
        verbose=args.verbose,
        collect_only=args.collect_only
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
