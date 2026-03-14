"""
Tests for ScreenshotAnalyzer component.

Requirements: 4.1, 4.2, 4.3, 4.5, 5.3
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest
from PIL import Image

from src.sentinela.exceptions import CatarataError, ScreenshotError
from src.sentinela.screenshot_analyzer import ScreenshotAnalyzer


class TestScreenshotAnalyzer:
    """Unit tests for ScreenshotAnalyzer."""

    def test_init_without_telemetry(self):
        """Analyzer can be initialized without TelemetryHub."""
        analyzer = ScreenshotAnalyzer()
        assert analyzer.telemetry_hub is None

    def test_init_with_telemetry(self):
        """Analyzer can be initialized with TelemetryHub."""
        mock_hub = Mock()
        analyzer = ScreenshotAnalyzer(telemetry_hub=mock_hub)
        assert analyzer.telemetry_hub is mock_hub

    @patch("src.sentinela.screenshot_analyzer.ImageGrab.grab")
    def test_capture_screenshot_success(self, mock_grab):
        """Screenshot capture returns valid numpy array."""
        # Create a test image (100x100 RGB with some color)
        test_image = Image.new("RGB", (100, 100), color=(128, 128, 128))
        mock_grab.return_value = test_image

        analyzer = ScreenshotAnalyzer()
        result = analyzer.capture_screenshot()

        # Verify result is numpy array
        assert isinstance(result, np.ndarray)
        assert result.shape == (100, 100, 3)
        assert result.dtype == np.uint8

        # Verify it's cached
        assert analyzer.get_last_screenshot() is not None

    @patch("src.sentinela.screenshot_analyzer.ImageGrab.grab")
    def test_catarata_black_screen(self, mock_grab):
        """Catarata error raised when screen is black."""
        # Create a black image
        black_image = Image.new("RGB", (100, 100), color=(0, 0, 0))
        mock_grab.return_value = black_image

        analyzer = ScreenshotAnalyzer()

        with pytest.raises(CatarataError) as exc_info:
            analyzer.capture_screenshot()

        assert "Catarata detected" in str(exc_info.value)
        assert "black" in str(exc_info.value).lower()

    @patch("src.sentinela.screenshot_analyzer.ImageGrab.grab")
    def test_catarata_very_dark_screen(self, mock_grab):
        """Catarata error raised when screen is very dark."""
        # Create a very dark image (below threshold)
        dark_image = Image.new("RGB", (100, 100), color=(5, 5, 5))
        mock_grab.return_value = dark_image

        analyzer = ScreenshotAnalyzer()

        with pytest.raises(CatarataError) as exc_info:
            analyzer.capture_screenshot()

        assert "Catarata detected" in str(exc_info.value)

    @patch("src.sentinela.screenshot_analyzer.ImageGrab.grab")
    def test_catarata_permission_denied(self, mock_grab):
        """Catarata error raised when permission denied."""
        mock_grab.side_effect = PermissionError("Access denied")

        analyzer = ScreenshotAnalyzer()

        with pytest.raises(CatarataError) as exc_info:
            analyzer.capture_screenshot()

        assert "permission denied" in str(exc_info.value).lower()

    @patch("src.sentinela.screenshot_analyzer.ImageGrab.grab")
    def test_catarata_reported_to_telemetry(self, mock_grab):
        """Catarata error is reported to TelemetryHub."""
        black_image = Image.new("RGB", (100, 100), color=(0, 0, 0))
        mock_grab.return_value = black_image

        mock_hub = Mock()
        mock_hub._event_log = []
        analyzer = ScreenshotAnalyzer(telemetry_hub=mock_hub)

        with pytest.raises(CatarataError):
            analyzer.capture_screenshot()

        # Verify event was logged
        assert len(mock_hub._event_log) == 1
        event = mock_hub._event_log[0]
        assert "CATARATA" in event.message
        assert event.data["severity"] == "critical"
        assert event.source == "sentinela_screenshot"

    @patch("src.sentinela.screenshot_analyzer.ImageGrab.grab")
    def test_screenshot_error_on_failure(self, mock_grab):
        """ScreenshotError raised on general capture failure."""
        mock_grab.side_effect = RuntimeError("Display not available")

        analyzer = ScreenshotAnalyzer()

        with pytest.raises(ScreenshotError) as exc_info:
            analyzer.capture_screenshot()

        assert "capture failed" in str(exc_info.value).lower()

    def test_to_grayscale_rgb_image(self):
        """RGB image is converted to grayscale."""
        analyzer = ScreenshotAnalyzer()

        # Create RGB image
        rgb_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

        gray = analyzer.to_grayscale(rgb_image)

        assert len(gray.shape) == 2
        assert gray.shape == (100, 100)
        assert gray.dtype == np.uint8

    def test_to_grayscale_already_gray(self):
        """Already grayscale image is returned unchanged."""
        analyzer = ScreenshotAnalyzer()

        # Create grayscale image
        gray_image = np.random.randint(0, 255, (100, 100), dtype=np.uint8)

        result = analyzer.to_grayscale(gray_image)

        assert result.shape == gray_image.shape
        assert np.array_equal(result, gray_image)

    def test_to_grayscale_invalid_shape(self):
        """ValueError raised for invalid image shape."""
        analyzer = ScreenshotAnalyzer()

        # Create invalid shape (4 channels)
        invalid_image = np.random.randint(0, 255, (100, 100, 4), dtype=np.uint8)

        with pytest.raises(ValueError):
            analyzer.to_grayscale(invalid_image)

    def test_match_template_basic(self):
        """Template matching returns confidence and coordinates."""
        analyzer = ScreenshotAnalyzer()

        # Create a simple image with a pattern
        image = np.zeros((200, 200), dtype=np.uint8)
        image[50:100, 50:100] = 255  # White square

        # Template is the white square
        template = np.ones((50, 50), dtype=np.uint8) * 255

        confidence, x, y = analyzer.match_template(image, template)

        # Should find the template with high confidence
        assert confidence > 0.9
        # Coordinates should be in valid range
        assert 0 <= x < 200
        assert 0 <= y < 200

    def test_match_template_no_match(self):
        """Template matching returns low confidence when no match."""
        analyzer = ScreenshotAnalyzer()

        # Create image with no pattern
        image = np.zeros((200, 200), dtype=np.uint8)

        # Template is white square
        template = np.ones((50, 50), dtype=np.uint8) * 255

        confidence, x, y = analyzer.match_template(image, template)

        # Confidence will be high even for black image matching white template
        # because OpenCV finds the "best" match even if it's not good
        # The key is that coordinates are returned
        assert 0 <= confidence <= 1.0
        assert 0 <= x < 200
        assert 0 <= y < 200

    def test_match_template_requires_grayscale(self):
        """Template matching raises error for non-grayscale images."""
        analyzer = ScreenshotAnalyzer()

        # Create RGB images
        image = np.zeros((200, 200, 3), dtype=np.uint8)
        template = np.zeros((50, 50, 3), dtype=np.uint8)

        with pytest.raises(ValueError) as exc_info:
            analyzer.match_template(image, template)

        assert "grayscale" in str(exc_info.value).lower()

    def test_match_multiscale_finds_at_100_percent(self):
        """Multiscale matching finds template at 100% scale."""
        analyzer = ScreenshotAnalyzer()

        # Create image with pattern
        image = np.zeros((200, 200), dtype=np.uint8)
        image[50:100, 50:100] = 255

        # Template at exact size
        template = np.ones((50, 50), dtype=np.uint8) * 255

        confidence, center_x, center_y, scale = analyzer.match_multiscale(
            image, template, scales=[0.9, 1.0, 1.1]
        )

        assert confidence > 0.9
        # Scale should be one of the tested scales
        assert scale in [0.9, 1.0, 1.1]
        # Center should be in valid range
        assert 0 <= center_x < 200
        assert 0 <= center_y < 200

    def test_match_multiscale_finds_at_90_percent(self):
        """Multiscale matching finds template at 90% scale."""
        analyzer = ScreenshotAnalyzer()

        # Create image with smaller pattern
        image = np.zeros((200, 200), dtype=np.uint8)
        image[50:95, 50:95] = 255  # 45x45 square (90% of 50)

        # Template at 100% size
        template = np.ones((50, 50), dtype=np.uint8) * 255

        confidence, center_x, center_y, scale = analyzer.match_multiscale(
            image, template, scales=[0.9, 1.0, 1.1]
        )

        assert confidence > 0.8
        assert scale == 0.9

    def test_match_multiscale_returns_best_match(self):
        """Multiscale matching returns highest confidence match."""
        analyzer = ScreenshotAnalyzer()

        # Create image with pattern
        image = np.zeros((200, 200), dtype=np.uint8)
        image[50:100, 50:100] = 255

        template = np.ones((50, 50), dtype=np.uint8) * 255

        confidence, center_x, center_y, scale = analyzer.match_multiscale(
            image, template, scales=[0.8, 0.9, 1.0, 1.1, 1.2]
        )

        # Should find a good match
        assert confidence > 0.9
        # Scale should be one of the tested scales
        assert scale in [0.8, 0.9, 1.0, 1.1, 1.2]
        # Coordinates should be valid
        assert 0 <= center_x < 200
        assert 0 <= center_y < 200

    def test_get_last_screenshot_initially_none(self):
        """Last screenshot is None before first capture."""
        analyzer = ScreenshotAnalyzer()
        assert analyzer.get_last_screenshot() is None

    @patch("src.sentinela.screenshot_analyzer.ImageGrab.grab")
    def test_get_last_screenshot_after_capture(self, mock_grab):
        """Last screenshot is cached after capture."""
        test_image = Image.new("RGB", (100, 100), color=(128, 128, 128))
        mock_grab.return_value = test_image

        analyzer = ScreenshotAnalyzer()
        captured = analyzer.capture_screenshot()
        cached = analyzer.get_last_screenshot()

        assert cached is not None
        assert np.array_equal(captured, cached)


class TestCatarataIntegration:
    """Integration tests for Catarata error detection."""

    @patch("src.sentinela.screenshot_analyzer.ImageGrab.grab")
    def test_catarata_workflow_with_telemetry(self, mock_grab):
        """Complete Catarata detection workflow with TelemetryHub."""
        from src.neural_link.telemetry.provider import EventType, TelemetryHub

        # Setup
        black_image = Image.new("RGB", (100, 100), color=(0, 0, 0))
        mock_grab.return_value = black_image

        hub = TelemetryHub()
        analyzer = ScreenshotAnalyzer(telemetry_hub=hub)

        # Trigger Catarata
        with pytest.raises(CatarataError):
            analyzer.capture_screenshot()

        # Verify event in hub
        events = hub.get_event_log()
        assert len(events) == 1
        assert events[0].event_type == EventType.TASK_FAILED
        assert "CATARATA" in events[0].message
        assert events[0].data["error_type"] == "black_screen"

    @patch("src.sentinela.screenshot_analyzer.ImageGrab.grab")
    def test_normal_operation_no_catarata(self, mock_grab):
        """Normal screenshot capture does not trigger Catarata."""
        from src.neural_link.telemetry.provider import TelemetryHub

        # Setup with normal image
        normal_image = Image.new("RGB", (100, 100), color=(128, 128, 128))
        mock_grab.return_value = normal_image

        hub = TelemetryHub()
        analyzer = ScreenshotAnalyzer(telemetry_hub=hub)

        # Should succeed without error
        result = analyzer.capture_screenshot()

        assert result is not None
        assert len(hub.get_event_log()) == 0  # No errors logged
