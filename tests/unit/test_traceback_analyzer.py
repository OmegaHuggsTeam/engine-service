"""
Unit tests for TracebackAnalyzer module.
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from agents.traceback_analyzer import TracebackAnalyzer


def test_extract_library_from_selenium_traceback():
    """Test extracting library name from a selenium traceback."""
    traceback_str = """Traceback (most recent call last):
  File "/home/user/project/main.py", line 10, in <module>
    driver.find_element(By.ID, "test")
  File "/home/user/.venv/lib/python3.9/site-packages/selenium/webdriver/remote/webdriver.py", line 780, in find_element
    return self.execute(Command.FIND_ELEMENT, {
  File "/home/user/.venv/lib/python3.9/site-packages/selenium/webdriver/remote/webdriver.py", line 420, in execute
    self.error_handler.check_response(response)
selenium.common.exceptions.NoSuchElementException: Message: no such element: Unable to locate element
"""

    library_name = TracebackAnalyzer.extract_library_name(traceback_str)
    assert library_name == "selenium", f"Expected 'selenium', got '{library_name}'"


def test_extract_library_from_beautifulsoup_traceback():
    """Test extracting library name from a beautifulsoup4 traceback."""
    traceback_str = """Traceback (most recent call last):
  File "/home/user/project/scraper.py", line 15, in <module>
    soup = BeautifulSoup(html, 'html.parser')
  File "/usr/local/lib/python3.9/site-packages/bs4/__init__.py", line 215, in __init__
    self._feed()
  File "/usr/local/lib/python3.9/site-packages/bs4/__init__.py", line 239, in _feed
    self.builder.feed(self.markup)
bs4.FeatureNotFound: Couldn't find a tree builder with the features you requested
"""

    library_name = TracebackAnalyzer.extract_library_name(traceback_str)
    assert library_name == "bs4", f"Expected 'bs4', got '{library_name}'"


def test_extract_deepest_library():
    """Test that the deepest library in the call stack is returned."""
    traceback_str = """Traceback (most recent call last):
  File "/home/user/project/main.py", line 10, in <module>
    process_data()
  File "/home/user/.venv/lib/python3.9/site-packages/requests/__init__.py", line 100, in get
    return request('get', url, **kwargs)
  File "/home/user/.venv/lib/python3.9/site-packages/urllib3/connection.py", line 50, in connect
    raise ConnectionError()
urllib3.exceptions.ConnectionError: Failed to connect
"""

    library_name = TracebackAnalyzer.extract_library_name(traceback_str)
    # Should return the deepest library (urllib3), not the first one (requests)
    assert library_name == "urllib3", f"Expected 'urllib3', got '{library_name}'"


def test_empty_traceback_returns_none():
    """Test that an empty traceback returns None."""
    assert TracebackAnalyzer.extract_library_name("") is None
    assert TracebackAnalyzer.extract_library_name("   ") is None
    assert TracebackAnalyzer.extract_library_name(None) is None


def test_stdlib_only_traceback_returns_none():
    """Test that a traceback with only stdlib modules returns None."""
    traceback_str = """Traceback (most recent call last):
  File "/usr/lib/python3.9/json/__init__.py", line 346, in loads
    return _default_decoder.decode(s)
  File "/usr/lib/python3.9/json/decoder.py", line 337, in decode
    obj, end = self.raw_decode(s, idx=_w(s, 0).end())
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
"""

    library_name = TracebackAnalyzer.extract_library_name(traceback_str)
    assert library_name is None, f"Expected None for stdlib-only traceback, got '{library_name}'"


def test_normalize_library_name():
    """Test library name normalization."""
    # Test lowercase conversion
    assert TracebackAnalyzer._normalize_library_name("Selenium") == "selenium"
    assert TracebackAnalyzer._normalize_library_name("BeautifulSoup4") == "beautifulsoup4"

    # Test underscore to hyphen conversion
    assert TracebackAnalyzer._normalize_library_name("some_library") == "some-library"
    assert TracebackAnalyzer._normalize_library_name("my_test_lib") == "my-test-lib"

    # Test version number removal
    assert TracebackAnalyzer._normalize_library_name("requests-2.28.0") == "requests"

    # Test combined transformations
    assert TracebackAnalyzer._normalize_library_name("My_Library-1.0.0") == "my-library"


def test_is_stdlib_module():
    """Test stdlib module detection."""
    # Test common stdlib modules
    assert TracebackAnalyzer._is_stdlib_module("json") is True
    assert TracebackAnalyzer._is_stdlib_module("os") is True
    assert TracebackAnalyzer._is_stdlib_module("sys") is True
    assert TracebackAnalyzer._is_stdlib_module("datetime") is True

    # Test non-stdlib modules
    assert TracebackAnalyzer._is_stdlib_module("selenium") is False
    assert TracebackAnalyzer._is_stdlib_module("requests") is False
    assert TracebackAnalyzer._is_stdlib_module("bs4") is False


def test_malformed_traceback_returns_none():
    """Test that malformed tracebacks return None."""
    malformed_traceback = """This is not a valid traceback
Just some random text
No file paths here
"""

    library_name = TracebackAnalyzer.extract_library_name(malformed_traceback)
    assert library_name is None, f"Expected None for malformed traceback, got '{library_name}'"


def test_windows_path_format():
    """Test extraction from Windows-style paths."""
    traceback_str = """Traceback (most recent call last):
  File "C:\\Users\\user\\project\\main.py", line 10, in <module>
    driver.find_element(By.ID, "test")
  File "C:\\Users\\user\\.venv\\Lib\\site-packages\\selenium\\webdriver\\remote\\webdriver.py", line 780, in find_element
    return self.execute(Command.FIND_ELEMENT, {
selenium.common.exceptions.NoSuchElementException: Message: no such element
"""

    library_name = TracebackAnalyzer.extract_library_name(traceback_str)
    assert library_name == "selenium", f"Expected 'selenium', got '{library_name}'"


if __name__ == "__main__":
    print("Running TracebackAnalyzer tests...")

    test_extract_library_from_selenium_traceback()
    print("✓ test_extract_library_from_selenium_traceback passed")

    test_extract_library_from_beautifulsoup_traceback()
    print("✓ test_extract_library_from_beautifulsoup_traceback passed")

    test_extract_deepest_library()
    print("✓ test_extract_deepest_library passed")

    test_empty_traceback_returns_none()
    print("✓ test_empty_traceback_returns_none passed")

    test_stdlib_only_traceback_returns_none()
    print("✓ test_stdlib_only_traceback_returns_none passed")

    test_normalize_library_name()
    print("✓ test_normalize_library_name passed")

    test_is_stdlib_module()
    print("✓ test_is_stdlib_module passed")

    test_malformed_traceback_returns_none()
    print("✓ test_malformed_traceback_returns_none passed")

    test_windows_path_format()
    print("✓ test_windows_path_format passed")

    print("\nAll tests passed!")
