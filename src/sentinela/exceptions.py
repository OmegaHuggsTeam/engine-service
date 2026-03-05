"""
Custom exceptions for Sentinela Monitor.
"""


class SentinelaError(Exception):
    """Base exception for Sentinela Monitor."""
    pass


class ScreenshotError(SentinelaError):
    """Raised when screenshot capture fails."""
    pass


class CatarataError(ScreenshotError):
    """
    Raised when screen is black (cataract condition) or capture permission denied.
    
    This error indicates the visual system cannot see properly:
    - Black screen detected (all pixels near zero)
    - Screenshot permission denied by OS
    - Display not accessible
    """
    pass


class VisualDetectionError(SentinelaError):
    """Raised when visual element detection fails."""
    pass


class TemplateNotFoundError(VisualDetectionError):
    """Raised when template image file is not found."""
    pass


class PageLoadTimeoutError(VisualDetectionError):
    """Raised when page load detection times out."""
    pass


class JitbitError(SentinelaError):
    """Raised when Jitbit macro execution fails."""
    pass


class LogWatcherError(SentinelaError):
    """Raised when log monitoring fails."""
    pass
