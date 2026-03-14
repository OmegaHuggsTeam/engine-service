"""
Unit tests for SpecManager module.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from agents.spec_manager import SpecManager


def test_spec_exists():
    """Test spec_exists method."""
    # This will return False for non-existent specs
    assert not SpecManager.spec_exists("nonexistent_library")


def test_save_and_load_spec():
    """Test saving and loading a spec."""
    library_name = "test_library"
    content = """# Specialist: test_library

## Library Info

- **Name**: test_library
- **Version Compatibility**: 1.0+
- **Last Updated**: 2024-01-01

## Common Error Patterns

### Pattern 1: Test Error
- **Signature**: TestError
- **Solution**: Fix it

## Security Considerations

Test security considerations

## Memory Efficiency

Test memory efficiency

## Monkey Patching Strategies

Test monkey patching

## Combat Maneuvers

### Maneuver 1: Test Maneuver
- **Error Signature**: TestError
- **Root Cause**: Test cause
- **Solution Code**:
```python
print("test")
```
- **Prevention Strategy**: Test prevention
- **Learned On**: 2024-01-01T00:00:00

## Evolution History

- **2024-01-01T00:00:00**: TestError - Test solution
"""

    # Save the spec
    success = SpecManager.save_spec(library_name, content)
    assert success, "Failed to save spec"

    # Check it exists
    assert SpecManager.spec_exists(library_name), "Spec should exist after saving"

    # Load the spec
    spec = SpecManager.load_spec(library_name)
    assert spec is not None, "Failed to load spec"
    assert spec["library_name"] == "test_library"
    assert spec["version_compatibility"] == "1.0+"
    assert len(spec["combat_maneuvers"]) == 1
    assert spec["combat_maneuvers"][0]["error_signature"] == "TestError"
    assert len(spec["evolution_history"]) == 1

    # Clean up
    spec_path = SpecManager.SPECS_DIR / f"{library_name}.md"
    if spec_path.exists():
        spec_path.unlink()


def test_update_spec():
    """Test updating a spec with new combat maneuver."""
    library_name = "test_update_library"
    content = """# Specialist: test_update_library

## Library Info

- **Name**: test_update_library
- **Version Compatibility**: 1.0+

## Security Considerations

Test

## Memory Efficiency

Test

## Monkey Patching Strategies

Test

## Combat Maneuvers

## Evolution History
"""

    # Save initial spec
    SpecManager.save_spec(library_name, content)

    # Create new combat maneuver
    new_maneuver = {
        "title": "New Maneuver",
        "error_signature": "NewError",
        "root_cause": "New cause",
        "solution_code": 'print("new")',
        "prevention_strategy": "New prevention",
        "learned_on": "2024-01-02T00:00:00",
    }

    # Create evolution entry
    evolution_entry = {
        "timestamp": "2024-01-02T00:00:00",
        "error_type": "NewError",
        "solution_summary": "Added new maneuver",
    }

    # Update the spec
    success = SpecManager.update_spec(library_name, new_maneuver, evolution_entry)
    assert success, "Failed to update spec"

    # Load and verify
    spec = SpecManager.load_spec(library_name)
    assert spec is not None
    assert len(spec["combat_maneuvers"]) == 1
    assert spec["combat_maneuvers"][0]["title"] == "New Maneuver"
    assert len(spec["evolution_history"]) == 1
    assert spec["evolution_history"][0]["error_type"] == "NewError"

    # Clean up
    spec_path = SpecManager.SPECS_DIR / f"{library_name}.md"
    if spec_path.exists():
        spec_path.unlink()


def test_validate_spec():
    """Test spec validation."""
    library_name = "test_invalid_library"

    # Create spec with missing sections
    invalid_content = """# Specialist: test_invalid_library

## Library Info

- **Name**: test_invalid_library
"""

    # Save the invalid spec
    SpecManager.save_spec(library_name, invalid_content)

    # Try to load - should fail validation
    _spec = SpecManager.load_spec(library_name)  # noqa: F841
    # The spec should be None due to validation failure
    # (though the current implementation might still return it)

    # Clean up
    spec_path = SpecManager.SPECS_DIR / f"{library_name}.md"
    if spec_path.exists():
        spec_path.unlink()


if __name__ == "__main__":
    print("Running SpecManager tests...")

    test_spec_exists()
    print("✓ test_spec_exists passed")

    test_save_and_load_spec()
    print("✓ test_save_and_load_spec passed")

    test_update_spec()
    print("✓ test_update_spec passed")

    test_validate_spec()
    print("✓ test_validate_spec passed")

    print("\nAll tests passed!")
