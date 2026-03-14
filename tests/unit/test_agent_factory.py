"""
Unit tests for AgentFactory orchestrator.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from agents.agent_factory import AgentFactory


def test_handle_exception_with_unknown_library():
    """Test handle_exception with a library that doesn't exist yet."""
    # Create a sample traceback with a fake library
    traceback_str = """
Traceback (most recent call last):
  File "test.py", line 10, in <module>
    result = process_data()
  File "/path/to/.venv/lib/python3.11/site-packages/fakelibrary/core.py", line 42, in process
    raise ValueError("Invalid data format")
ValueError: Invalid data format
"""

    exception = ValueError("Invalid data format")

    # Note: This will try to call Groq API, which may fail in test environment
    # For now, we just verify the structure of the response
    response = AgentFactory.handle_exception(exception, traceback_str)

    # Verify response structure
    assert "specialist_name" in response
    assert "specialist_exists" in response
    assert "combat_maneuvers_applied" in response
    assert "evolution_triggered" in response
    assert "suggested_solution" in response
    assert "error" in response

    # The library should be identified
    assert response["specialist_name"] == "fakelibrary"

    print("✓ handle_exception returns correct structure")


def test_handle_exception_with_no_library():
    """Test handle_exception with a traceback that has no library."""
    traceback_str = """
Traceback (most recent call last):
  File "test.py", line 10, in <module>
    result = process_data()
  File "/usr/lib/python3.11/json/__init__.py", line 42, in loads
    raise ValueError("Invalid JSON")
ValueError: Invalid JSON
"""

    exception = ValueError("Invalid JSON")
    response = AgentFactory.handle_exception(exception, traceback_str)

    # Should fail to identify library (stdlib only)
    assert response["specialist_name"] is None
    assert response["error"] == "Could not identify library from traceback"

    print("✓ handle_exception handles stdlib-only traceback correctly")


def test_check_specialist_exists():
    """Test _check_specialist_exists method."""
    # Test with a library that doesn't exist
    exists = AgentFactory._check_specialist_exists("nonexistent-library")
    assert exists is False

    print("✓ _check_specialist_exists works correctly")


def test_load_specialist_nonexistent():
    """Test _load_specialist with nonexistent library."""
    specialist = AgentFactory._load_specialist("nonexistent-library")
    assert specialist is None

    print("✓ _load_specialist handles nonexistent library correctly")


def test_apply_specialist_no_match():
    """Test _apply_specialist with no matching combat maneuver."""
    specialist = {
        "library_name": "test-lib",
        "combat_maneuvers": [
            {
                "title": "Test Maneuver",
                "error_signature": "ConnectionError",
                "solution_code": "retry_connection()",
            }
        ],
    }

    # Error message doesn't match any signature
    solution, applied = AgentFactory._apply_specialist(specialist, "ValueError: Invalid input")
    assert solution is None
    assert applied == []

    print("✓ _apply_specialist returns None when no match found")


def test_apply_specialist_with_match():
    """Test _apply_specialist with matching combat maneuver."""
    specialist = {
        "library_name": "test-lib",
        "combat_maneuvers": [
            {
                "title": "Connection Error Handler",
                "error_signature": "ConnectionError",
                "solution_code": "retry_connection()",
            }
        ],
    }

    # Error message matches signature
    solution, applied = AgentFactory._apply_specialist(
        specialist, "ConnectionError: Failed to connect"
    )
    assert solution == "retry_connection()"
    assert "Connection Error Handler" in applied

    print("✓ _apply_specialist returns solution when match found")


def run_all_tests():
    """Run all AgentFactory tests."""
    print("\n[AgentFactory Tests]")
    print("-" * 70)

    tests = [
        test_handle_exception_with_no_library,
        test_check_specialist_exists,
        test_load_specialist_nonexistent,
        test_apply_specialist_no_match,
        test_apply_specialist_with_match,
        # Skip test_handle_exception_with_unknown_library as it requires Groq API
    ]

    for test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"✗ {test_func.__name__}: {e}")
            raise


if __name__ == "__main__":
    run_all_tests()
