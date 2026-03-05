"""
Traceback Analyzer Module

This module provides functionality to extract library names from Python exception tracebacks.
It identifies the root cause library (deepest in the call stack) and normalizes library names.
"""

import re
import sys
from pathlib import Path
from typing import Optional


class TracebackAnalyzer:
    """Analyzes Python exception tracebacks to extract library information."""
    
    # Python standard library modules (common ones to skip)
    STDLIB_MODULES = {
        'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio', 'asyncore',
        'atexit', 'audioop', 'base64', 'bdb', 'binascii', 'binhex', 'bisect', 'builtins',
        'bz2', 'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code', 'codecs',
        'codeop', 'collections', 'colorsys', 'compileall', 'concurrent', 'configparser',
        'contextlib', 'contextvars', 'copy', 'copyreg', 'cProfile', 'crypt', 'csv',
        'ctypes', 'curses', 'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib',
        'dis', 'distutils', 'doctest', 'email', 'encodings', 'enum', 'errno', 'faulthandler',
        'fcntl', 'filecmp', 'fileinput', 'fnmatch', 'formatter', 'fractions', 'ftplib',
        'functools', 'gc', 'getopt', 'getpass', 'gettext', 'glob', 'graphlib', 'grp',
        'gzip', 'hashlib', 'heapq', 'hmac', 'html', 'http', 'imaplib', 'imghdr', 'imp',
        'importlib', 'inspect', 'io', 'ipaddress', 'itertools', 'json', 'keyword',
        'lib2to3', 'linecache', 'locale', 'logging', 'lzma', 'mailbox', 'mailcap',
        'marshal', 'math', 'mimetypes', 'mmap', 'modulefinder', 'msilib', 'msvcrt',
        'multiprocessing', 'netrc', 'nis', 'nntplib', 'numbers', 'operator', 'optparse',
        'os', 'ossaudiodev', 'parser', 'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes',
        'pkgutil', 'platform', 'plistlib', 'poplib', 'posix', 'posixpath', 'pprint',
        'profile', 'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc', 'queue',
        'quopri', 'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter',
        'runpy', 'sched', 'secrets', 'select', 'selectors', 'shelve', 'shlex', 'shutil',
        'signal', 'site', 'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver', 'spwd',
        'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'stringprep', 'struct',
        'subprocess', 'sunau', 'symbol', 'symtable', 'sys', 'sysconfig', 'syslog',
        'tabnanny', 'tarfile', 'telnetlib', 'tempfile', 'termios', 'test', 'textwrap',
        'threading', 'time', 'timeit', 'tkinter', 'token', 'tokenize', 'tomllib', 'trace',
        'traceback', 'tracemalloc', 'tty', 'turtle', 'turtledemo', 'types', 'typing',
        'unicodedata', 'unittest', 'urllib', 'uu', 'uuid', 'venv', 'warnings', 'wave',
        'weakref', 'webbrowser', 'winreg', 'winsound', 'wsgiref', 'xdrlib', 'xml',
        'xmlrpc', 'zipapp', 'zipfile', 'zipimport', 'zlib', 'zoneinfo'
    }
    
    @staticmethod
    def extract_library_name(traceback_str: str) -> Optional[str]:
        """
        Extract the root cause library name from a Python exception traceback.
        
        This method parses the traceback to find site-packages or .venv paths,
        identifies the deepest non-stdlib library in the call stack, and returns
        the normalized library name.
        
        Args:
            traceback_str: The full exception traceback as a string
            
        Returns:
            The normalized library name (lowercase with hyphens) or None if not found
        """
        if not traceback_str or not traceback_str.strip():
            return None
        
        # Parse traceback lines to find file paths
        lines = traceback_str.split('\n')
        library_candidates = []
        
        for line in lines:
            # Look for file paths in traceback (typically after 'File "')
            file_match = re.search(r'File "([^"]+)"', line)
            if not file_match:
                continue
            
            file_path = file_match.group(1)
            
            # Extract library name from path
            library_name = TracebackAnalyzer._extract_library_from_path(file_path)
            if library_name:
                library_candidates.append(library_name)
        
        # Return the deepest (last) library in the call stack
        if library_candidates:
            return library_candidates[-1]
        
        return None
    
    @staticmethod
    def _extract_library_from_path(file_path: str) -> Optional[str]:
        """
        Extract library name from a file path.
        
        Args:
            file_path: The file path from the traceback
            
        Returns:
            The normalized library name or None if not a library path
        """
        # Normalize path separators
        file_path = file_path.replace('\\', '/')
        
        # Look for site-packages or .venv patterns
        patterns = [
            r'site-packages/([^/]+)',
            r'\.venv/[^/]+/site-packages/([^/]+)',
            r'venv/[^/]+/site-packages/([^/]+)',
            r'virtualenv/[^/]+/site-packages/([^/]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, file_path)
            if match:
                raw_name = match.group(1)
                
                # Skip if it's a stdlib module
                if TracebackAnalyzer._is_stdlib_module(raw_name):
                    continue
                
                # Normalize and return
                return TracebackAnalyzer._normalize_library_name(raw_name)
        
        return None
    
    @staticmethod
    def _normalize_library_name(raw_name: str) -> str:
        """
        Normalize library name to lowercase with hyphens.
        
        Args:
            raw_name: The raw library name extracted from the path
            
        Returns:
            The normalized library name
        """
        # Remove version numbers and file extensions
        name = re.sub(r'-\d+\.\d+.*', '', raw_name)
        name = re.sub(r'\.py$', '', name)
        
        # Convert to lowercase
        name = name.lower()
        
        # Replace underscores with hyphens (but keep existing hyphens)
        name = name.replace('_', '-')
        
        return name
    
    @staticmethod
    def _is_stdlib_module(module_name: str) -> bool:
        """
        Check if a module name is part of the Python standard library.
        
        Args:
            module_name: The module name to check
            
        Returns:
            True if the module is part of stdlib, False otherwise
        """
        # Normalize the module name
        normalized = module_name.lower().replace('-', '_').replace('.py', '')
        
        # Check against known stdlib modules
        return normalized in TracebackAnalyzer.STDLIB_MODULES
