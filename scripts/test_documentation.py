#!/usr/bin/env python3
"""
Test Documentation Generator for MongoDB Atlas Search API

This script runs the test suite and generates detailed documentation about:
- Test coverage
- API functionality
- Test results
- Suggestions for improvements

It breaks down tests by endpoint category for better organization and error isolation.
"""

import os
import sys
import subprocess
import json
import datetime
import importlib.util
from pathlib import Path
from tabulate import tabulate

# Add root directory to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
APP_DIR = os.path.join(ROOT_DIR, "app")
TESTS_DIR = os.path.join(APP_DIR, "tests")
DOCS_DIR = os.path.join(ROOT_DIR, "docs")

# Ensure app directory is in path
sys.path.insert(0, ROOT_DIR)
sys.path.insert(0, APP_DIR)

# Test categories and their corresponding test functions
TEST_CATEGORIES = {
    "Products": [
        "test_ingest_products",
        "test_get_product",
        "test_remove_product",
        "test_remove_all_products"
    ],
    "Orders": [
        "test_ingest_orderline"
    ],
    "Search": [
        "test_search",
        "test_autosuggest",
        "test_similar_products",
        "test_query_explain"
    ],
    "User Feedback": [
        "test_feedback"
    ],
    "Recommender System": [
        "test_naive_recommender_endpoints"
    ],
    "System": [
        "test_health",
        "test_unauthorized_access"
    ]
}

class TestDocumentationGenerator:
    """Generates comprehensive documentation for API endpoint tests"""
    
    def __init__(self):
        self.results = {}
        self.summary = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0
        }
        self.timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create docs directory if it doesn't exist
        os.makedirs(DOCS_DIR, exist_ok=True)
        
    def run_tests_by_category(self):
        """Run tests grouped by category"""
        for category, test_names in TEST_CATEGORIES.items():
            print(f"\n=== Running {category} Tests ===")
            self.results[category] = {
                "test_functions": test_names,
                "results": {}
            }
            
            for test_name in test_names:
                print(f"Running {test_name}...")
                
                # Run individual test using pytest
                result = self.run_single_test(test_name)
                self.results[category]["results"][test_name] = result
                
                # Update summary
                self.summary["total_tests"] += 1
                if result["status"] == "passed":
                    self.summary["passed"] += 1
                elif result["status"] == "failed":
                    self.summary["failed"] += 1
                elif result["status"] == "error":
                    self.summary["errors"] += 1
                elif result["status"] == "skipped":
                    self.summary["skipped"] += 1
    
    def run_single_test(self, test_name):
        """Run a single test and capture the result"""
        test_path = os.path.join(TESTS_DIR, "test_endpoints.py::{}".format(test_name))
        
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test_path, "-v"],
                cwd=APP_DIR,
                capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )
            
            # Process output to determine test status
            if result.returncode == 0:
                status = "passed"
                message = "Test passed successfully"
            elif "SKIPPED" in result.stdout:
                status = "skipped"
                message = self.extract_message(result.stdout, "SKIPPED")
            elif "FAILED" in result.stdout:
                status = "failed"
                message = self.extract_message(result.stdout, "FAILED")
            else:
                status = "error"
                message = f"Test execution error: {result.stderr}"
                
            return {
                "status": status,
                "message": message,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": "Test timed out after 30 seconds",
                "stdout": "",
                "stderr": "Timeout error",
                "returncode": -1
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error running test: {str(e)}",
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
    
    def extract_message(self, output, status_type):
        """Extract error/skip message from test output"""
        # Look for lines after the status_type indication
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if status_type in line and i + 1 < len(lines):
                # Try to find the actual message in subsequent lines
                for j in range(i + 1, min(i + 10, len(lines))):
                    if lines[j].strip().startswith("E "):
                        return lines[j].replace("E ", "").strip()
        return "No detailed message found"
    
    def generate_summary_table(self):
        """Generate a summary table of test results"""
        headers = ["Category", "Total", "Passed", "Failed", "Error", "Skipped"]
        rows = []
        
        category_totals = {}
        for category, data in self.results.items():
            passed = sum(1 for _, result in data["results"].items() if result["status"] == "passed")
            failed = sum(1 for _, result in data["results"].items() if result["status"] == "failed")
            error = sum(1 for _, result in data["results"].items() if result["status"] == "error")
            skipped = sum(1 for _, result in data["results"].items() if result["status"] == "skipped")
            total = len(data["results"])
            
            category_totals[category] = {
                "total": total,
                "passed": passed,
                "failed": failed,
                "error": error,
                "skipped": skipped
            }
            
            rows.append([category, total, passed, failed, error, skipped])
        
        # Add totals row
        rows.append([
            "TOTAL", 
            self.summary["total_tests"],
            self.summary["passed"],
            self.summary["failed"],
            self.summary["errors"],
            self.summary["skipped"]
        ])
        
        return tabulate(rows, headers=headers, tablefmt="grid"), category_totals
    
    def generate_detailed_results(self):
        """Generate detailed results for each test"""
        detailed_results = {}
        
        for category, data in self.results.items():
            category_results = []
            for test_name, result in data["results"].items():
                test_result = {
                    "test_name": test_name,
                    "status": result["status"],
                    "message": result["message"]
                }
                category_results.append(test_result)
            detailed_results[category] = category_results
            
        return detailed_results
    
    def generate_endpoint_documentation(self):
        """Generate documentation for each API endpoint from test functions"""
        endpoint_docs = {}
        
        try:
            # Try to import the test file
            spec = importlib.util.spec_from_file_location(
                "test_endpoints", 
                os.path.join(TESTS_DIR, "test_endpoints.py")
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Extract docstrings from test functions
            for category, test_names in TEST_CATEGORIES.items():
                category_endpoints = []
                
                for test_name in test_names:
                    if hasattr(module, test_name) and getattr(module, test_name).__doc__:
                        doc = getattr(module, test_name).__doc__.strip()
                        
                        # Try to determine HTTP method and path from docstring and function name
                        http_method = "Unknown"
                        path = "Unknown"
                        
                        if "GET" in doc:
                            http_method = "GET"
                        elif "POST" in doc:
                            http_method = "POST"
                        elif "DELETE" in doc:
                            http_method = "DELETE"
                        elif "PUT" in doc:
                            http_method = "PUT"
                        
                        if test_name.startswith("test_ingest_"):
                            if "products" in test_name:
                                path = "/ingestProducts"
                            elif "orderline" in test_name:
                                path = "/ingestOrderline"
                        elif test_name == "test_search":
                            path = "/search"
                        elif test_name == "test_autosuggest":
                            path = "/autosuggest"
                        elif test_name == "test_get_product":
                            path = "/doc/{product_id}"
                        elif test_name == "test_similar_products":
                            path = "/similar/{product_id}"
                        elif test_name == "test_feedback":
                            path = "/feedback"
                        elif test_name == "test_query_explain":
                            path = "/query-explain"
                        elif test_name == "test_remove_product":
                            path = "/remove/product/{product_id}"
                        elif test_name == "test_remove_all_products":
                            path = "/remove/products/all"
                        elif test_name == "test_health":
                            path = "/health"
                            
                        endpoint = {
                            "http_method": http_method,
                            "path": path,
                            "description": doc,
                            "test_function": test_name,
                            "test_status": self.results.get(category, {}).get("results", {}).get(test_name, {}).get("status", "unknown")
                        }
                        
                        category_endpoints.append(endpoint)
                
                endpoint_docs[category] = category_endpoints
                
        except Exception as e:
            print(f"Error generating endpoint documentation: {str(e)}")
            return {}
        
        return endpoint_docs
    
    def generate_markdown_report(self):
        """Generate a comprehensive markdown report"""
        summary_table, category_totals = self.generate_summary_table()
        detailed_results = self.generate_detailed_results()
        endpoint_docs = self.generate_endpoint_documentation()
        
        # Create markdown report
        report = f"""# MongoDB Atlas Search API Test Report

## Test Summary
Report generated on: {self.timestamp}

```
{summary_table}
```

## API Endpoint Coverage

"""
        # Add endpoint documentation by category
        for category, endpoints in endpoint_docs.items():
            stats = category_totals.get(category, {"total": 0, "passed": 0})
            coverage_pct = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            
            report += f"### {category} Endpoints - {coverage_pct:.1f}% Passing\n\n"
            
            if endpoints:
                # Create table for each category
                report += "| Method | Endpoint | Description | Status |\n"
                report += "|--------|----------|-------------|---------|\n"
                
                for endpoint in endpoints:
                    status_icon = "PASS" if endpoint["test_status"] == "passed" else "FAIL"
                    report += f"| {endpoint['http_method']} | `{endpoint['path']}` | {endpoint['description']} | {status_icon} |\n"
                
                report += "\n"
            else:
                report += "No endpoints documented in this category.\n\n"
        
        # Add detailed results
        report += "## Detailed Test Results\n\n"
        
        for category, results in detailed_results.items():
            report += f"### {category}\n\n"
            
            if results:
                # Create table for test results
                report += "| Test | Status | Message |\n"
                report += "|------|--------|--------|\n"
                
                for result in results:
                    emoji = "PASS" if result["status"] == "passed" else "FAIL" if result["status"] == "failed" else "WARN"
                    report += f"| {result['test_name']} | {emoji} {result['status']} | {result['message']} |\n"
                
                report += "\n"
            else:
                report += "No test results available for this category.\n\n"
        
        # Add recommendations based on results
        report += "## Recommendations\n\n"
        
        if self.summary["failed"] > 0 or self.summary["errors"] > 0:
            report += "### Issues to Address\n\n"
            
            for category, data in self.results.items():
                failed_tests = [(name, result) for name, result in data["results"].items() 
                              if result["status"] in ["failed", "error"]]
                
                if failed_tests:
                    report += f"#### {category}\n\n"
                    for test_name, result in failed_tests:
                        report += f"- **{test_name}**: {result['message']}\n"
                        if result["stderr"]:
                            report += f"  ```\n  {result['stderr'][:300]}{'...' if len(result['stderr']) > 300 else ''}\n  ```\n"
                    report += "\n"
        else:
            report += "### All tests passed! Great job!\n\n"
            report += "- Consider adding more edge case tests for improved robustness\n"
            report += "- Add performance benchmarks to track API response times\n"
        
        # Save the report with UTF-8 encoding
        report_path = os.path.join(DOCS_DIR, "test_report.md")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
            
        print(f"\nTest report saved to: {report_path}")
        return report_path
    
    def generate_json_results(self):
        """Generate JSON results for programmatic use"""
        json_results = {
            "timestamp": self.timestamp,
            "summary": self.summary,
            "category_results": self.results
        }
        
        # Save the JSON with UTF-8 encoding
        json_path = os.path.join(DOCS_DIR, "test_results.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_results, f, indent=2, ensure_ascii=False)
            
        print(f"JSON results saved to: {json_path}")
        return json_path

def main():
    print("MongoDB Atlas Search API Test Documentation Generator")
    print("=====================================================\n")
    
    # Check for pytest
    try:
        import pytest
    except ImportError:
        print("pytest is required but not installed.")
        answer = input("Do you want to install it now? (y/n): ")
        if answer.lower() == "y":
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio"])
        else:
            print("Exiting as pytest is required.")
            return 1
    
    # Run tests and generate documentation
    try:
        generator = TestDocumentationGenerator()
        generator.run_tests_by_category()
        report_path = generator.generate_markdown_report()
        json_path = generator.generate_json_results()
        
        print("\nTest documentation generation complete!")
        print(f"- Markdown report: {report_path}")
        print(f"- JSON results: {json_path}")
        
        print("\nTest Summary:")
        print(f"Total: {generator.summary['total_tests']}")
        print(f"Passed: {generator.summary['passed']}")
        print(f"Failed: {generator.summary['failed']}")
        print(f"Errors: {generator.summary['errors']}")
        print(f"Skipped: {generator.summary['skipped']}")
        
        # Return error code if any tests failed
        return 0 if generator.summary["failed"] == 0 and generator.summary["errors"] == 0 else 1
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
