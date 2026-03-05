"""
Test runner for core components (TracebackAnalyzer and SpecManager).
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import test modules
from unit.test_traceback_analyzer import (
    test_extract_library_from_selenium_traceback,
    test_extract_library_from_beautifulsoup_traceback,
    test_extract_deepest_library,
    test_empty_traceback_returns_none,
    test_stdlib_only_traceback_returns_none,
    test_normalize_library_name,
    test_is_stdlib_module,
    test_malformed_traceback_returns_none,
    test_windows_path_format
)

from unit.test_spec_manager import (
    test_spec_exists,
    test_save_and_load_spec,
    test_update_spec,
    test_validate_spec
)

from unit.test_agent_factory import (
    test_handle_exception_with_no_library,
    test_check_specialist_exists,
    test_load_specialist_nonexistent,
    test_apply_specialist_no_match,
    test_apply_specialist_with_match
)


def run_all_tests():
    """Run all core component tests."""
    print("=" * 70)
    print("RUNNING CORE COMPONENT TESTS")
    print("=" * 70)
    
    tests_passed = 0
    tests_failed = 0
    
    # TracebackAnalyzer tests
    print("\n[TracebackAnalyzer Tests]")
    print("-" * 70)
    
    traceback_tests = [
        ("Extract library from selenium traceback", test_extract_library_from_selenium_traceback),
        ("Extract library from beautifulsoup traceback", test_extract_library_from_beautifulsoup_traceback),
        ("Extract deepest library", test_extract_deepest_library),
        ("Empty traceback returns None", test_empty_traceback_returns_none),
        ("Stdlib-only traceback returns None", test_stdlib_only_traceback_returns_none),
        ("Normalize library name", test_normalize_library_name),
        ("Is stdlib module", test_is_stdlib_module),
        ("Malformed traceback returns None", test_malformed_traceback_returns_none),
        ("Windows path format", test_windows_path_format),
    ]
    
    for test_name, test_func in traceback_tests:
        try:
            test_func()
            print(f"✓ {test_name}")
            tests_passed += 1
        except Exception as e:
            print(f"✗ {test_name}: {e}")
            tests_failed += 1
    
    # SpecManager tests
    print("\n[SpecManager Tests]")
    print("-" * 70)
    
    spec_tests = [
        ("Spec exists", test_spec_exists),
        ("Save and load spec", test_save_and_load_spec),
        ("Update spec", test_update_spec),
        ("Validate spec", test_validate_spec),
    ]
    
    for test_name, test_func in spec_tests:
        try:
            test_func()
            print(f"✓ {test_name}")
            tests_passed += 1
        except Exception as e:
            print(f"✗ {test_name}: {e}")
            tests_failed += 1
    
    # AgentFactory tests
    print("\n[AgentFactory Tests]")
    print("-" * 70)
    
    agent_factory_tests = [
        ("Handle exception with no library", test_handle_exception_with_no_library),
        ("Check specialist exists", test_check_specialist_exists),
        ("Load specialist nonexistent", test_load_specialist_nonexistent),
        ("Apply specialist no match", test_apply_specialist_no_match),
        ("Apply specialist with match", test_apply_specialist_with_match),
    ]
    
    for test_name, test_func in agent_factory_tests:
        try:
            test_func()
            print(f"✓ {test_name}")
            tests_passed += 1
        except Exception as e:
            print(f"✗ {test_name}: {e}")
            tests_failed += 1
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total tests: {tests_passed + tests_failed}")
    print(f"Passed: {tests_passed}")
    print(f"Failed: {tests_failed}")
    
    if tests_failed == 0:
        print("\n✓ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n✗ {tests_failed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
