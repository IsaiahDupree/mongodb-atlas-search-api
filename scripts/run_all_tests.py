#!/usr/bin/env python3
"""
Test runner for MongoDB Atlas Search API

This script runs all the focused test modules and generates a summary report.
It follows the best practice of running modular tests while providing a simple
unified interface to execute all tests.

Usage:
  python run_all_tests.py [--verbose] [--module MODULE_NAME]
  
Options:
  --verbose, -v     Show detailed test output
  --module, -m      Run only a specific test module (products, orders, search, health, recommender)
"""

import os
import sys
import argparse
import subprocess
import time
from tabulate import tabulate

# Add parent directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
APP_DIR = os.path.join(ROOT_DIR, "app")
TESTS_DIR = os.path.join(APP_DIR, "tests")

# Test modules
TEST_MODULES = {
    "products": "test_products.py",
    "orders": "test_orders.py",
    "search": "test_search.py",
    "health": "test_health.py",
    "recommender": "test_naive_recommender.py"
}

def run_test_module(module_name, verbose=False):
    """Run a specific test module and return results"""
    module_file = TEST_MODULES.get(module_name)
    if not module_file:
        print(f"Error: Unknown test module '{module_name}'")
        return None
    
    module_path = os.path.join(TESTS_DIR, module_file)
    if not os.path.exists(module_path):
        print(f"Error: Test module file not found: {module_path}")
        return None
    
    print(f"\nRunning {module_name.upper()} tests...")
    start_time = time.time()
    
    # Build pytest command
    pytest_args = []
    if verbose:
        pytest_args.append("-v")
    
    # Run pytest
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", module_path] + pytest_args,
            cwd=APP_DIR,
            capture_output=True,
            text=True,
            check=False  # Don't fail on test failures
        )
        
        duration = time.time() - start_time
        
        # Count tests by parsing output
        tests_run = 0
        tests_passed = 0
        tests_failed = 0
        tests_skipped = 0
        
        if result.returncode == 0:
            # All tests passed
            output_lines = result.stdout.splitlines()
            for line in output_lines:
                if " passed " in line and " in " in line:
                    parts = line.strip().split(" ")
                    for i, part in enumerate(parts):
                        if part == "passed" and i > 0:
                            tests_run = tests_passed = int(parts[i-1])
                            break
        else:
            # Some tests failed
            output_lines = result.stdout.splitlines()
            for line in output_lines:
                if "failed" in line and "passed" in line and "skipped" in line:
                    parts = line.strip().split(", ")
                    for part in parts:
                        if "failed" in part:
                            tests_failed = int(part.split(" ")[0])
                        elif "passed" in part:
                            tests_passed = int(part.split(" ")[0])
                        elif "skipped" in part:
                            tests_skipped = int(part.split(" ")[0])
            
            tests_run = tests_passed + tests_failed + tests_skipped
        
        return {
            "module": module_name,
            "returncode": result.returncode,
            "tests_run": tests_run,
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "tests_skipped": tests_skipped,
            "duration": duration,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return {
            "module": module_name,
            "returncode": -1,
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "tests_skipped": 0,
            "duration": time.time() - start_time,
            "stdout": "",
            "stderr": str(e)
        }

def main():
    parser = argparse.ArgumentParser(description="Run MongoDB Atlas Search API tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed test output")
    parser.add_argument("--module", "-m", help="Run only a specific test module")
    
    args = parser.parse_args()
    
    if args.module:
        if args.module not in TEST_MODULES:
            print(f"Error: Unknown test module '{args.module}'")
            print(f"Available modules: {', '.join(TEST_MODULES.keys())}")
            return 1
        
        modules_to_run = [args.module]
    else:
        modules_to_run = list(TEST_MODULES.keys())
    
    results = []
    all_passed = True
    
    print("MongoDB Atlas Search API Test Runner")
    print("===================================")
    
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    
    for module_name in modules_to_run:
        result = run_test_module(module_name, args.verbose)
        
        if result:
            results.append(result)
            
            if result["returncode"] != 0:
                all_passed = False
            
            # Print details if verbose
            if args.verbose:
                print("\nOutput:")
                print(result["stdout"])
                
                if result["stderr"]:
                    print("\nErrors:")
                    print(result["stderr"])
            
            # Update totals
            total_tests += result["tests_run"]
            total_passed += result["tests_passed"]
            total_failed += result["tests_failed"]
            total_skipped += result["tests_skipped"]
    
    # Print summary table
    print("\nTest Summary:")
    table_data = []
    headers = ["Module", "Run", "Passed", "Failed", "Skipped", "Duration (s)", "Status"]
    
    for result in results:
        status = "PASS" if result["returncode"] == 0 else "FAIL"
        table_data.append([
            result["module"],
            result["tests_run"],
            result["tests_passed"],
            result["tests_failed"],
            result["tests_skipped"],
            f"{result['duration']:.2f}",
            status
        ])
    
    # Add a total row
    table_data.append([
        "TOTAL",
        total_tests,
        total_passed,
        total_failed,
        total_skipped,
        "",
        "PASS" if all_passed else "FAIL"
    ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
