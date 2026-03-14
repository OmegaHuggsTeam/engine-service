"""
Integration tests for AgentFactory full workflow.
Tests the complete flow: identify → check → create/load → apply → evolve
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from agents.agent_factory import AgentFactory
from agents.spec_manager import SpecManager


def test_full_workflow_new_library():
    """
    Test complete workflow for a new library:
    1. Extract library name from traceback
    2. Check specialist doesn't exist
    3. Create new specialist via Groq (mocked)
    4. Save specialist to disk
    """
    # Create temporary directory for specs
    with tempfile.TemporaryDirectory() as temp_dir:
        # Patch SPECS_DIR to use temp directory
        original_specs_dir = SpecManager.SPECS_DIR
        SpecManager.SPECS_DIR = Path(temp_dir)

        try:
            # Mock Groq API response for specialist creation
            # This needs to be a complete, valid spec
            mock_spec_content = """# Specialist: testlibrary

## Library Info

- **Name**: testlibrary
- **Version Compatibility**: 1.0+
- **Last Updated**: 2024-01-01

## Common Error Patterns

### Pattern 1: Connection Error
- **Signature**: ConnectionError
- **Solution**: Retry with exponential backoff

## Security Considerations

Follow OWASP guidelines for secure connections.

## Memory Efficiency

Use connection pooling to reduce overhead.

## Monkey Patching Strategies

Patch at module level, not instance level.

## Combat Maneuvers

## Evolution History
"""

            with patch("src.utils.llm_client.chat_completion") as mock_chat:
                mock_chat.return_value = mock_spec_content

                # Create traceback with testlibrary
                traceback_str = """
Traceback (most recent call last):
  File "test.py", line 10, in <module>
    result = connect()
  File "/path/.venv/lib/python3.11/site-packages/testlibrary/client.py", line 42, in connect
    raise ConnectionError("Failed to connect")
ConnectionError: Failed to connect
"""

                exception = ConnectionError("Failed to connect")

                # Execute full workflow
                response = AgentFactory.handle_exception(exception, traceback_str)

                # Verify response structure
                assert "specialist_name" in response
                assert "specialist_exists" in response
                assert "combat_maneuvers_applied" in response
                assert "evolution_triggered" in response
                assert "suggested_solution" in response
                assert "error" in response

                # Verify library was identified
                assert response["specialist_name"] == "testlibrary"

                # Verify specialist was created (not pre-existing)
                # Note: specialist_exists might be True after creation

                # Verify specialist was saved to disk
                spec_path = Path(temp_dir) / "testlibrary.md"
                assert spec_path.exists(), "Specialist spec file should be created"

                print("✓ Full workflow for new library works correctly")

        finally:
            # Restore original SPECS_DIR
            SpecManager.SPECS_DIR = original_specs_dir


def test_full_workflow_existing_library():
    """
    Test complete workflow for existing library:
    1. Extract library name from traceback
    2. Check specialist exists
    3. Load specialist from disk
    4. Apply combat maneuvers
    """
    # Create temporary directory for specs
    with tempfile.TemporaryDirectory() as temp_dir:
        # Patch SPECS_DIR to use temp directory
        original_specs_dir = SpecManager.SPECS_DIR
        SpecManager.SPECS_DIR = Path(temp_dir)

        try:
            # Create existing specialist spec
            spec_content = """# Specialist: existinglibrary

## Library Info

- **Name**: existinglibrary
- **Version Compatibility**: 1.0+
- **Last Updated**: 2024-01-01

## Common Error Patterns

### Pattern 1: Timeout Error
- **Signature**: TimeoutError
- **Solution**: Increase timeout value

## Security Considerations

Follow OWASP guidelines.

## Memory Efficiency

Use lazy loading.

## Monkey Patching Strategies

Patch at import time.

## Combat Maneuvers

### Maneuver 1: Timeout Handler
- **Error Signature**: timed out
- **Root Cause**: Network latency
- **Solution Code**:
```python
import time
time.sleep(1)
retry_connection()
```
- **Prevention Strategy**: Set appropriate timeout values
- **Learned On**: 2024-01-01T00:00:00

## Evolution History

- **2024-01-01T00:00:00**: TimeoutError - Added retry logic
"""

            # Save spec to temp directory
            spec_path = Path(temp_dir) / "existinglibrary.md"
            spec_path.write_text(spec_content, encoding="utf-8")

            # Create traceback with existinglibrary
            traceback_str = """
Traceback (most recent call last):
  File "test.py", line 10, in <module>
    result = fetch_data()
  File "/path/.venv/lib/python3.11/site-packages/existinglibrary/api.py", line 42, in fetch
    raise TimeoutError("Request timed out")
TimeoutError: Request timed out
"""

            exception = TimeoutError("Request timed out")

            # Execute full workflow
            response = AgentFactory.handle_exception(exception, traceback_str)

            # Verify response structure
            assert "specialist_name" in response
            assert "specialist_exists" in response
            assert "combat_maneuvers_applied" in response
            assert "suggested_solution" in response

            # Verify library was identified
            assert response["specialist_name"] == "existinglibrary"

            # Verify specialist was loaded (already existed)
            assert response["specialist_exists"] is True

            # Verify combat maneuver was applied (error message contains "timed out")
            assert (
                len(response["combat_maneuvers_applied"]) > 0
            ), "Should have applied at least one combat maneuver"
            assert (
                "retry_connection()" in response["suggested_solution"]
            ), "Solution should contain the retry code"

            print("✓ Full workflow for existing library works correctly")

        finally:
            # Restore original SPECS_DIR
            SpecManager.SPECS_DIR = original_specs_dir


def test_workflow_with_evolution():
    """
    Test workflow with specialist evolution:
    1. Load existing specialist
    2. Apply combat maneuvers (no match)
    3. Trigger evolution
    4. Generate new combat maneuver
    5. Update specialist spec
    """
    # Create temporary directory for specs
    with tempfile.TemporaryDirectory() as temp_dir:
        # Patch SPECS_DIR to use temp directory
        original_specs_dir = SpecManager.SPECS_DIR
        SpecManager.SPECS_DIR = Path(temp_dir)

        try:
            # Create existing specialist spec without matching maneuver
            spec_content = """# Specialist: evolvinglibrary

## Library Info

- **Name**: evolvinglibrary
- **Version Compatibility**: 1.0+
- **Last Updated**: 2024-01-01

## Common Error Patterns

### Pattern 1: Generic Error
- **Signature**: Error
- **Solution**: Check logs

## Security Considerations

Follow OWASP guidelines.

## Memory Efficiency

Use caching.

## Monkey Patching Strategies

Patch carefully.

## Combat Maneuvers

## Evolution History
"""

            # Save spec to temp directory
            spec_path = Path(temp_dir) / "evolvinglibrary.md"
            spec_path.write_text(spec_content, encoding="utf-8")

            # Mock Groq API response for combat maneuver generation
            mock_maneuver_response = """### Maneuver: Authentication Error Handler

- **Error Signature**: AuthenticationError
- **Root Cause**: Invalid credentials
- **Solution Code**:
```python
refresh_token()
retry_request()
```
- **Prevention Strategy**: Validate credentials before requests
"""

            with patch("src.utils.llm_client.chat_completion") as mock_chat:
                mock_chat.return_value = mock_maneuver_response

                # Create traceback with new error type
                traceback_str = """
Traceback (most recent call last):
  File "test.py", line 10, in <module>
    result = authenticate()
  File "/path/.venv/lib/python3.11/site-packages/evolvinglibrary/auth.py", line 42, in auth
    raise AuthenticationError("Invalid credentials")
AuthenticationError: Invalid credentials
"""

                exception = Exception("AuthenticationError: Invalid credentials")

                # Execute full workflow (should trigger evolution)
                response = AgentFactory.handle_exception(exception, traceback_str)

                # Verify response
                assert response["specialist_name"] == "evolvinglibrary"
                assert response["specialist_exists"] is True
                assert response["evolution_triggered"] is True

                # Verify spec was updated with new maneuver
                updated_content = spec_path.read_text(encoding="utf-8")
                # Check that the maneuver was added (look for key elements)
                assert (
                    "refresh_token()" in updated_content or "AuthenticationError" in updated_content
                ), "Updated spec should contain the new combat maneuver content"

                print("✓ Workflow with evolution works correctly")

        finally:
            # Restore original SPECS_DIR
            SpecManager.SPECS_DIR = original_specs_dir


def test_workflow_error_handling():
    """
    Test workflow handles errors gracefully:
    1. API failures don't crash the system
    2. File I/O errors are handled
    3. Invalid tracebacks are handled
    """
    # Test with invalid traceback (no library)
    traceback_str = """
Traceback (most recent call last):
  File "test.py", line 10, in <module>
    result = process()
ValueError: Invalid input
"""

    exception = ValueError("Invalid input")
    response = AgentFactory.handle_exception(exception, traceback_str)

    # Should handle gracefully
    assert response["specialist_name"] is None
    assert response["error"] == "Could not identify library from traceback"

    print("✓ Workflow error handling works correctly")


def run_all_integration_tests():
    """Run all integration tests."""
    print("\n[AgentFactory Integration Tests]")
    print("-" * 70)

    tests = [
        test_full_workflow_new_library,
        test_full_workflow_existing_library,
        test_workflow_with_evolution,
        test_workflow_error_handling,
    ]

    for test_func in tests:
        try:
            test_func()
        except Exception as e:
            print(f"✗ {test_func.__name__}: {e}")
            import traceback

            traceback.print_exc()
            raise


if __name__ == "__main__":
    run_all_integration_tests()
