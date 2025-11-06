"""
Test runner script for InsiteChart platform.

This script provides a convenient way to run all tests
and generate coverage reports.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(command, description):
    """Run a command and handle the result."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.stdout:
        print("STDOUT:")
        print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    if result.returncode != 0:
        print(f"Command failed with exit code: {result.returncode}")
        return False
    
    return True


def run_backend_tests():
    """Run backend tests."""
    print("Running Backend Tests")
    
    # Change to backend directory
    backend_dir = Path("backend")
    if not backend_dir.exists():
        print("Backend directory not found")
        return False
    
    os.chdir(backend_dir)
    
    # Run tests
    success = run_command(
        "python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term",
        "Backend pytest with coverage"
    )
    
    # Return to root directory
    os.chdir("..")
    return success


def run_frontend_tests():
    """Run frontend tests."""
    print("Running Frontend Tests")
    
    # Change to frontend directory
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("Frontend directory not found")
        return False
    
    os.chdir(frontend_dir)
    
    # Run tests
    success = run_command(
        "python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term",
        "Frontend pytest with coverage"
    )
    
    # Return to root directory
    os.chdir("..")
    return success


def run_integration_tests():
    """Run integration tests."""
    print("Running Integration Tests")
    
    # Check if tests directory exists
    tests_dir = Path("tests")
    if not tests_dir.exists():
        print("Tests directory not found")
        return False
    
    # Run integration tests
    success = run_command(
        "python -m pytest tests/test_integration.py -v -s",
        "Integration tests"
    )
    
    return success


def run_all_tests():
    """Run all tests."""
    print("Running All Tests")
    
    success = True
    
    # Run backend tests
    if not run_backend_tests():
        success = False
    
    # Run frontend tests
    if not run_frontend_tests():
        success = False
    
    # Run integration tests
    if not run_integration_tests():
        success = False
    
    return success


def run_linting():
    """Run code linting."""
    print("Running Code Linting")
    
    success = True
    
    # Lint backend
    backend_success = run_command(
        "flake8 backend/ --max-line-length=100 --ignore=E203,W503",
        "Backend linting with flake8"
    )
    
    # Lint frontend
    frontend_success = run_command(
        "flake8 frontend/ --max-line-length=100 --ignore=E203,W503",
        "Frontend linting with flake8"
    )
    
    # Check code formatting
    format_success = run_command(
        "black --check backend/ frontend/ tests/",
        "Code formatting check with black"
    )
    
    # Check import sorting
    import_success = run_command(
        "isort --check-only backend/ frontend/ tests/",
        "Import sorting check with isort"
    )
    
    return backend_success and frontend_success and format_success and import_success


def run_security_scan():
    """Run security scan."""
    print("Running Security Scan")
    
    # Run bandit security scan
    success = run_command(
        "bandit -r backend/ -f json -o security_report.json",
        "Security scan with bandit"
    )
    
    return success


def setup_test_environment():
    """Setup test environment."""
    print("Setting up Test Environment")
    
    # Create test directories
    test_dirs = ["logs", "test_data", "test_reports"]
    for dir_name in test_dirs:
        Path(dir_name).mkdir(exist_ok=True)
    
    # Set environment variables
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    print("Test environment setup complete")
    return True


def cleanup_test_environment():
    """Cleanup test environment."""
    print("Cleaning up Test Environment")
    
    # Remove test files
    test_files = [
        ".coverage",
        "coverage.xml",
        "security_report.json",
        "test_db.sqlite3"
    ]
    
    for file_name in test_files:
        file_path = Path(file_name)
        if file_path.exists():
            file_path.unlink()
    
    # Remove test directories (optional)
    # test_dirs = ["test_data", "test_reports"]
    # for dir_name in test_dirs:
    #     dir_path = Path(dir_name)
    #     if dir_path.exists():
    #         import shutil
    #         shutil.rmtree(dir_path)
    
    print("Test environment cleanup complete")
    return True


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="InsiteChart Test Runner")
    parser.add_argument(
        "command",
        choices=["backend", "frontend", "integration", "all", "lint", "security", "setup", "cleanup"],
        help="Command to run"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage reports"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Setup test environment
    if not setup_test_environment():
        print("Failed to setup test environment")
        sys.exit(1)
    
    try:
        # Run command
        success = True
        
        if args.command == "backend":
            success = run_backend_tests()
        elif args.command == "frontend":
            success = run_frontend_tests()
        elif args.command == "integration":
            success = run_integration_tests()
        elif args.command == "all":
            success = run_all_tests()
        elif args.command == "lint":
            success = run_linting()
        elif args.command == "security":
            success = run_security_scan()
        elif args.command == "setup":
            success = setup_test_environment()
        elif args.command == "cleanup":
            success = cleanup_test_environment()
        
        # Print summary
        print(f"\n{'='*60}")
        if success:
            print("✅ All operations completed successfully!")
        else:
            print("❌ Some operations failed!")
        print(f"{'='*60}")
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
    
    finally:
        # Cleanup test environment
        if args.command not in ["setup", "cleanup"]:
            cleanup_test_environment()


if __name__ == "__main__":
    main()