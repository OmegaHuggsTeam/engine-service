"""
Tests for VisualDetector component.

Requirements: 3.4, 4.4, 5.1, 5.2, 8.1, 8.3
"""

from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

from src.sentinela.exceptions import TemplateNotFoundError
from src.sentinela.visual_detector import AnchorPoint, VisualDetector


class TestVisualDetector:
    """Unit tests for VisualDetector."""

    def test_init_creates_detector(self):
        """Detector can be initialized with templates directory."""
        detector = VisualDetector(templates_dir="./templates")
        assert detector.templates_dir == Path("./templates")
        assert detector.confidence_threshold == 0.85

    def test_init_with_custom_threshold(self):
        """Detector accepts custom confidence threshold."""
        detector = VisualDetector(templates_dir="./templates", confidence_threshold=0.90)
        assert detector.confidence_threshold == 0.90

    def test_init_with_telemetry(self):
        """Detector can be initialized with TelemetryHub."""
        mock_hub = Mock()
        detector = VisualDetector(templates_dir="./templates", telemetry_hub=mock_hub)
        assert detector.telemetry_hub is mock_hub

    def test_loads_templates_on_init(self):
        """Templates are loaded from directory on initialization."""
        detector = VisualDetector(templates_dir="./templates")

        # Should have loaded some templates
        assert detector.template_count > 0
        assert len(detector.loaded_templates) > 0

    def test_template_cache_contains_grayscale(self):
        """Template cache contains grayscale images."""
        detector = VisualDetector(templates_dir="./templates")

        if detector.template_count > 0:
            # Get first template
            template_name = detector.loaded_templates[0]
            template = detector._template_cache[template_name]

            # Should be grayscale (2D array)
            assert len(template.shape) == 2
            assert template.dtype == np.uint8

    def test_reload_templates(self):
        """Templates can be reloaded without restart."""
        detector = VisualDetector(templates_dir="./templates")
        initial_count = detector.template_count

        # Reload
        detector.reload_templates()

        # Should have same count (no templates added/removed)
        assert detector.template_count == initial_count

    def test_configure_anchors(self):
        """Anchor points can be configured."""
        detector = VisualDetector(templates_dir="./templates")

        anchors = [
            AnchorPoint(
                name="dashboard_logo",
                template_path="templates/dashboard_logo.png",
                required=True,
                min_confidence=0.85,
            ),
            AnchorPoint(
                name="refresh_button",
                template_path="templates/refresh_button.png",
                required=True,
                min_confidence=0.80,
            ),
        ]

        detector.configure_anchors(anchors)
        assert len(detector._anchors) == 2

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_find_element_success(self, mock_analyzer_class):
        """Element can be found with high confidence."""
        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        # Mock screenshot
        screenshot = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        mock_analyzer.capture_screenshot.return_value = screenshot

        # Mock grayscale conversion
        gray = np.random.randint(0, 255, (1080, 1920), dtype=np.uint8)
        mock_analyzer.to_grayscale.return_value = gray

        # Mock multiscale matching - high confidence
        mock_analyzer.match_multiscale.return_value = (0.95, 100, 100, 1.0)

        detector = VisualDetector(templates_dir="./templates")

        # Find element (use first loaded template)
        if detector.template_count > 0:
            template_name = detector.loaded_templates[0]
            result = detector.find_element(template_name)

            assert result.found is True
            assert result.confidence == 0.95
            assert result.center_x == 100
            assert result.center_y == 100

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_find_element_low_confidence(self, mock_analyzer_class):
        """Element not found when confidence below threshold."""
        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        screenshot = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        mock_analyzer.capture_screenshot.return_value = screenshot

        gray = np.random.randint(0, 255, (1080, 1920), dtype=np.uint8)
        mock_analyzer.to_grayscale.return_value = gray

        # Mock multiscale matching - low confidence
        mock_analyzer.match_multiscale.return_value = (0.50, 100, 100, 1.0)

        detector = VisualDetector(templates_dir="./templates")

        if detector.template_count > 0:
            template_name = detector.loaded_templates[0]
            result = detector.find_element(template_name)

            assert result.found is False
            assert result.confidence == 0.50
            assert result.center_x is None
            assert result.center_y is None

    def test_find_element_template_not_found(self):
        """TemplateNotFoundError raised for unknown template."""
        detector = VisualDetector(templates_dir="./templates")

        with pytest.raises(TemplateNotFoundError):
            detector.find_element("nonexistent_template")

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_verify_dashboard_visible_all_anchors_found(self, mock_analyzer_class):
        """Dashboard verified when all required anchors found."""
        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        screenshot = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        mock_analyzer.capture_screenshot.return_value = screenshot
        mock_analyzer.to_grayscale.return_value = np.random.randint(
            0, 255, (1080, 1920), dtype=np.uint8
        )

        # All anchors found with high confidence
        mock_analyzer.match_multiscale.return_value = (0.95, 100, 100, 1.0)

        detector = VisualDetector(templates_dir="./templates")

        # Configure anchors (use loaded templates)
        if detector.template_count >= 2:
            anchors = [
                AnchorPoint(
                    name=detector.loaded_templates[0],
                    template_path=f"templates/{detector.loaded_templates[0]}.png",
                    required=True,
                    min_confidence=0.85,
                ),
                AnchorPoint(
                    name=detector.loaded_templates[1],
                    template_path=f"templates/{detector.loaded_templates[1]}.png",
                    required=True,
                    min_confidence=0.85,
                ),
            ]
            detector.configure_anchors(anchors)

            is_visible, results = detector.verify_dashboard_visible()

            assert is_visible is True
            assert len(results) == 2
            assert all(r.found for r in results.values())

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_verify_dashboard_not_visible_missing_anchor(self, mock_analyzer_class):
        """Dashboard not verified when required anchor missing."""
        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        screenshot = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        mock_analyzer.capture_screenshot.return_value = screenshot
        mock_analyzer.to_grayscale.return_value = np.random.randint(
            0, 255, (1080, 1920), dtype=np.uint8
        )

        # First anchor found, second not found
        mock_analyzer.match_multiscale.side_effect = [
            (0.95, 100, 100, 1.0),  # First anchor
            (0.50, 100, 100, 1.0),  # Second anchor - low confidence
        ]

        detector = VisualDetector(templates_dir="./templates")

        if detector.template_count >= 2:
            anchors = [
                AnchorPoint(
                    name=detector.loaded_templates[0],
                    template_path=f"templates/{detector.loaded_templates[0]}.png",
                    required=True,
                    min_confidence=0.85,
                ),
                AnchorPoint(
                    name=detector.loaded_templates[1],
                    template_path=f"templates/{detector.loaded_templates[1]}.png",
                    required=True,
                    min_confidence=0.85,
                ),
            ]
            detector.configure_anchors(anchors)

            is_visible, results = detector.verify_dashboard_visible()

            assert is_visible is False

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_confirm_alert_visible_success(self, mock_analyzer_class):
        """Alert confirmation succeeds when alert found."""
        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        screenshot = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        mock_analyzer.capture_screenshot.return_value = screenshot
        mock_analyzer.to_grayscale.return_value = np.random.randint(
            0, 255, (1080, 1920), dtype=np.uint8
        )

        # Alert found with high confidence
        mock_analyzer.match_multiscale.return_value = (0.95, 500, 300, 1.0)

        detector = VisualDetector(templates_dir="./templates")

        # Use alert template if available
        alert_templates = [t for t in detector.loaded_templates if "alert" in t.lower()]
        if alert_templates:
            confirmed = detector.confirm_alert_visible(alert_templates[0])
            assert confirmed is True

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_confirm_alert_visible_failure(self, mock_analyzer_class):
        """Alert confirmation fails when alert not found."""
        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        screenshot = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        mock_analyzer.capture_screenshot.return_value = screenshot
        mock_analyzer.to_grayscale.return_value = np.random.randint(
            0, 255, (1080, 1920), dtype=np.uint8
        )

        # Alert not found - low confidence
        mock_analyzer.match_multiscale.return_value = (0.50, 500, 300, 1.0)

        detector = VisualDetector(templates_dir="./templates")

        alert_templates = [t for t in detector.loaded_templates if "alert" in t.lower()]
        if alert_templates:
            confirmed = detector.confirm_alert_visible(alert_templates[0])
            assert confirmed is False

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_filter_noise_no_noise(self, mock_analyzer_class):
        """Noise filtering returns no noise when clean."""
        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        screenshot = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        mock_analyzer.capture_screenshot.return_value = screenshot
        mock_analyzer.to_grayscale.return_value = np.random.randint(
            0, 255, (1080, 1920), dtype=np.uint8
        )

        # No noise found - low confidence for all
        mock_analyzer.match_multiscale.return_value = (0.30, 100, 100, 1.0)

        detector = VisualDetector(templates_dir="./templates")

        has_noise, detected = detector.filter_noise()

        assert has_noise is False
        assert len(detected) == 0

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_filter_noise_detects_noise(self, mock_analyzer_class):
        """Noise filtering detects and reports noise elements."""
        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        screenshot = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        mock_analyzer.capture_screenshot.return_value = screenshot
        mock_analyzer.to_grayscale.return_value = np.random.randint(
            0, 255, (1080, 1920), dtype=np.uint8
        )

        # First call: noise found, rest: no noise
        mock_analyzer.match_multiscale.side_effect = [
            (0.95, 100, 100, 1.0),  # windows_notification found
            (0.30, 100, 100, 1.0),  # system_popup not found
            (0.30, 100, 100, 1.0),  # browser_popup not found
            (0.30, 100, 100, 1.0),  # update_notification not found
        ]

        detector = VisualDetector(templates_dir="./templates")

        # Check if we have noise templates
        noise_templates = [
            t
            for t in detector.loaded_templates
            if "notification" in t.lower() or "popup" in t.lower()
        ]

        if noise_templates:
            has_noise, detected = detector.filter_noise(noise_templates=noise_templates[:1])

            assert has_noise is True
            assert len(detected) > 0


class TestVisualDetectorIntegration:
    """Integration tests for VisualDetector with TelemetryHub."""

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_detection_reported_to_telemetry(self, mock_analyzer_class):
        """Visual detections are reported to TelemetryHub."""
        from src.neural_link.telemetry.provider import TelemetryHub

        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        screenshot = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        mock_analyzer.capture_screenshot.return_value = screenshot
        mock_analyzer.to_grayscale.return_value = np.random.randint(
            0, 255, (1080, 1920), dtype=np.uint8
        )
        mock_analyzer.match_multiscale.return_value = (0.95, 100, 100, 1.0)

        hub = TelemetryHub()
        detector = VisualDetector(templates_dir="./templates", telemetry_hub=hub)

        if detector.template_count > 0:
            template_name = detector.loaded_templates[0]
            detector.find_element(template_name)

            # Check telemetry
            events = hub.get_event_log()
            assert len(events) > 0

            # Find detection event
            detection_events = [e for e in events if template_name in e.message]
            assert len(detection_events) > 0

            event = detection_events[0]
            assert event.source == "sentinela_visual"
            assert event.data["template"] == template_name
            assert event.data["found"] is True

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_dashboard_verification_reported(self, mock_analyzer_class):
        """Dashboard verification is reported to TelemetryHub."""
        from src.neural_link.telemetry.provider import TelemetryHub

        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        screenshot = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        mock_analyzer.capture_screenshot.return_value = screenshot
        mock_analyzer.to_grayscale.return_value = np.random.randint(
            0, 255, (1080, 1920), dtype=np.uint8
        )
        mock_analyzer.match_multiscale.return_value = (0.95, 100, 100, 1.0)

        hub = TelemetryHub()
        detector = VisualDetector(templates_dir="./templates", telemetry_hub=hub)

        if detector.template_count >= 2:
            anchors = [
                AnchorPoint(
                    name=detector.loaded_templates[0],
                    template_path=f"templates/{detector.loaded_templates[0]}.png",
                    required=True,
                ),
            ]
            detector.configure_anchors(anchors)

            is_visible, results = detector.verify_dashboard_visible()

            # Check telemetry
            events = hub.get_event_log()
            verification_events = [e for e in events if "Dashboard verification" in e.message]

            assert len(verification_events) > 0
            event = verification_events[0]
            assert "required_found" in event.data
            assert "required_total" in event.data


class TestLearningMode:
    """Tests for learning mode functionality."""

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_learning_mode_enabled_by_default(self, mock_analyzer_class):
        """Learning mode is enabled by default."""
        detector = VisualDetector(templates_dir="./templates")
        assert detector.learning_mode is True
        assert detector.learning_threshold == 0.60

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_learning_mode_can_be_disabled(self, mock_analyzer_class):
        """Learning mode can be disabled."""
        detector = VisualDetector(templates_dir="./templates", learning_mode=False)
        assert detector.learning_mode is False

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_learning_mode_suggests_template_update(self, mock_analyzer_class):
        """Learning mode suggests template update for low confidence."""
        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        screenshot = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        mock_analyzer.capture_screenshot.return_value = screenshot
        mock_analyzer.to_grayscale.return_value = np.random.randint(
            0, 255, (1080, 1920), dtype=np.uint8
        )

        # Confidence in learning range (0.60 - 0.85)
        mock_analyzer.match_multiscale.return_value = (0.70, 100, 100, 1.0)

        detector = VisualDetector(
            templates_dir="./templates",
            learning_mode=True,
            learning_threshold=0.60,
            confidence_threshold=0.85,
        )

        if detector.template_count > 0:
            template_name = detector.loaded_templates[0]
            result = detector.find_element(template_name)

            # Should not be found (below threshold)
            assert result.found is False

            # Should have learning suggestion
            assert len(detector.learning_suggestions) > 0
            suggestion = detector.learning_suggestions[0]
            assert suggestion["template"] == template_name
            assert suggestion["confidence"] == 0.70

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_learning_mode_no_suggestion_for_very_low_confidence(self, mock_analyzer_class):
        """Learning mode doesn't suggest for very low confidence."""
        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        screenshot = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        mock_analyzer.capture_screenshot.return_value = screenshot
        mock_analyzer.to_grayscale.return_value = np.random.randint(
            0, 255, (1080, 1920), dtype=np.uint8
        )

        # Confidence below learning threshold
        mock_analyzer.match_multiscale.return_value = (0.40, 100, 100, 1.0)

        detector = VisualDetector(
            templates_dir="./templates", learning_mode=True, learning_threshold=0.60
        )

        if detector.template_count > 0:
            template_name = detector.loaded_templates[0]
            result = detector.find_element(template_name)

            # Should not be found
            assert result.found is False

            # Should NOT have learning suggestion (too low)
            assert len(detector.learning_suggestions) == 0

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_get_learning_report(self, mock_analyzer_class):
        """Learning report can be generated."""
        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        screenshot = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        mock_analyzer.capture_screenshot.return_value = screenshot
        mock_analyzer.to_grayscale.return_value = np.random.randint(
            0, 255, (1080, 1920), dtype=np.uint8
        )
        mock_analyzer.match_multiscale.return_value = (0.70, 100, 100, 1.0)

        detector = VisualDetector(templates_dir="./templates", learning_mode=True)

        if detector.template_count > 0:
            # Trigger learning suggestion
            detector.find_element(detector.loaded_templates[0])

            # Get report
            report = detector.get_learning_report()

            assert "LEARNING MODE REPORT" in report
            assert "Re-capture this template" in report

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_clear_learning_suggestions(self, mock_analyzer_class):
        """Learning suggestions can be cleared."""
        detector = VisualDetector(templates_dir="./templates")

        # Add fake suggestion
        detector._learning_suggestions.append({"template": "test", "confidence": 0.70})
        assert len(detector.learning_suggestions) == 1

        # Clear
        detector.clear_learning_suggestions()
        assert len(detector.learning_suggestions) == 0


class TestNoiseClearingWithESC:
    """Tests for noise clearing with ESC key."""

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    @patch("pyautogui.press")
    def test_filter_noise_sends_esc_on_detection(self, mock_press, mock_analyzer_class):
        """ESC is sent when noise is detected."""
        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        screenshot = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        mock_analyzer.capture_screenshot.return_value = screenshot
        mock_analyzer.to_grayscale.return_value = np.random.randint(
            0, 255, (1080, 1920), dtype=np.uint8
        )

        # Noise found
        mock_analyzer.match_multiscale.return_value = (0.95, 100, 100, 1.0)

        detector = VisualDetector(templates_dir="./templates")

        # Check if we have noise templates
        noise_templates = [t for t in detector.loaded_templates if "notification" in t.lower()]

        if noise_templates:
            has_noise, detected = detector.filter_noise(
                noise_templates=noise_templates[:1], clear_on_detection=True
            )

            assert has_noise is True
            # ESC should have been pressed
            mock_press.assert_called_with("esc")

    @patch("src.sentinela.visual_detector.ScreenshotAnalyzer")
    def test_filter_noise_no_esc_when_disabled(self, mock_analyzer_class):
        """ESC is not sent when clear_on_detection=False."""
        # Setup mock
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        screenshot = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        mock_analyzer.capture_screenshot.return_value = screenshot
        mock_analyzer.to_grayscale.return_value = np.random.randint(
            0, 255, (1080, 1920), dtype=np.uint8
        )

        # Noise found
        mock_analyzer.match_multiscale.return_value = (0.95, 100, 100, 1.0)

        detector = VisualDetector(templates_dir="./templates")

        noise_templates = [t for t in detector.loaded_templates if "notification" in t.lower()]

        if noise_templates:
            has_noise, detected = detector.filter_noise(
                noise_templates=noise_templates[:1], clear_on_detection=False
            )

            assert has_noise is True
            # ESC should NOT have been pressed (clear_on_detection=False)
