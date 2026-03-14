"""
Screenshot Analyzer - Captures and processes screen images for visual detection.

Requirements: 4.1, 4.2, 4.3, 4.5
"""

import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import ImageGrab

from .exceptions import CatarataError, ScreenshotError

logger = logging.getLogger(__name__)


class ScreenshotAnalyzer:
    """
    Captures screenshots and performs image processing for template matching.

    Implements in-memory processing without disk I/O for efficiency.
    """

    def __init__(self, telemetry_hub=None):
        """
        Initialize screenshot analyzer.

        Args:
            telemetry_hub: Optional TelemetryHub for error reporting
        """
        self.telemetry_hub = telemetry_hub
        self._last_screenshot: Optional[np.ndarray] = None

    def capture_screenshot(self) -> np.ndarray:
        """
        Capture current screen as numpy array.

        Returns:
            Screenshot as RGB numpy array (H, W, 3)

        Raises:
            CatarataError: If screen is black or permission denied
            ScreenshotError: If capture fails for other reasons

        Requirements: 4.1 - Screenshots processed in memory without disk I/O
        """
        try:
            # Capture screen using PIL
            screenshot = ImageGrab.grab()

            # Convert PIL Image to numpy array (RGB)
            img_array = np.array(screenshot)

            # Validate screenshot is not black (Catarata test)
            self._validate_screenshot(img_array)

            # Cache for debugging
            self._last_screenshot = img_array

            logger.debug(
                "Screenshot captured: shape=%s, dtype=%s", img_array.shape, img_array.dtype
            )

            return img_array

        except CatarataError:
            # Re-raise CatarataError without wrapping
            raise

        except PermissionError as e:
            error_msg = "Screenshot permission denied by OS - Catarata detected"
            logger.error(error_msg)
            self._report_catarata_error(error_msg, "permission_denied")
            raise CatarataError(error_msg) from e

        except Exception as e:
            error_msg = f"Screenshot capture failed: {e}"
            logger.error(error_msg)
            self._report_error(error_msg, "capture_failed")
            raise ScreenshotError(error_msg) from e

    def _validate_screenshot(self, img_array: np.ndarray) -> None:
        """
        Validate screenshot is not black (Catarata condition).

        Args:
            img_array: Screenshot array to validate

        Raises:
            CatarataError: If screen appears to be black
        """
        # Calculate mean brightness across all channels
        mean_brightness = np.mean(img_array)

        # Threshold for black screen detection (very low brightness)
        BLACK_THRESHOLD = 10.0

        if mean_brightness < BLACK_THRESHOLD:
            error_msg = (
                f"Catarata detected: Screen is black "
                f"(mean brightness: {mean_brightness:.2f} < {BLACK_THRESHOLD})"
            )
            logger.error(error_msg)
            self._report_catarata_error(error_msg, "black_screen")
            raise CatarataError(error_msg)

        # Check if image has valid dimensions
        if img_array.shape[0] == 0 or img_array.shape[1] == 0:
            error_msg = f"Catarata detected: Invalid screenshot dimensions {img_array.shape}"
            logger.error(error_msg)
            self._report_catarata_error(error_msg, "invalid_dimensions")
            raise CatarataError(error_msg)

    def _report_catarata_error(self, message: str, error_type: str) -> None:
        """
        Report Catarata error to TelemetryHub.

        Args:
            message: Error message
            error_type: Type of catarata error
        """
        if self.telemetry_hub:
            try:
                from src.neural_link.telemetry.provider import EventType, TelemetryEvent

                event = TelemetryEvent(
                    event_type=EventType.TASK_FAILED,
                    source="sentinela_screenshot",
                    message=f"CATARATA: {message}",
                    data={
                        "error_type": error_type,
                        "component": "ScreenshotAnalyzer",
                        "severity": "critical",
                    },
                )

                # Push event directly to hub's event log
                self.telemetry_hub._event_log.append(event)

                logger.info("Catarata error reported to TelemetryHub")

            except Exception as e:
                logger.warning(f"Failed to report to TelemetryHub: {e}")

    def _report_error(self, message: str, error_type: str) -> None:
        """
        Report general error to TelemetryHub.

        Args:
            message: Error message
            error_type: Type of error
        """
        if self.telemetry_hub:
            try:
                from src.neural_link.telemetry.provider import EventType, TelemetryEvent

                event = TelemetryEvent(
                    event_type=EventType.LOG,
                    source="sentinela_screenshot",
                    message=message,
                    data={
                        "error_type": error_type,
                        "component": "ScreenshotAnalyzer",
                        "severity": "error",
                    },
                )

                self.telemetry_hub._event_log.append(event)

            except Exception as e:
                logger.warning(f"Failed to report to TelemetryHub: {e}")

    def to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """
        Convert RGB image to grayscale.

        Args:
            image: RGB numpy array (H, W, 3)

        Returns:
            Grayscale numpy array (H, W)

        Requirements: 4.2 - Images converted to grayscale for faster analysis
        """
        if len(image.shape) == 2:
            # Already grayscale
            return image

        if len(image.shape) == 3 and image.shape[2] == 3:
            # Convert RGB to grayscale using OpenCV
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            logger.debug("Converted image to grayscale: shape=%s", gray.shape)
            return gray

        raise ValueError(f"Unexpected image shape: {image.shape}")

    def match_template(
        self, image: np.ndarray, template: np.ndarray, method: int = cv2.TM_CCOEFF_NORMED
    ) -> Tuple[float, int, int]:
        """
        Find template in image using OpenCV template matching.

        Args:
            image: Grayscale image to search (H, W)
            template: Grayscale template to find (h, w)
            method: OpenCV matching method (default: normalized cross-correlation)

        Returns:
            (confidence, top_left_x, top_left_y)

        Requirements: 4.3 - Use normalized cross-correlation for template matching
        """
        # Ensure both images are grayscale
        if len(image.shape) != 2:
            raise ValueError(f"Image must be grayscale, got shape {image.shape}")
        if len(template.shape) != 2:
            raise ValueError(f"Template must be grayscale, got shape {template.shape}")

        # Perform template matching
        result = cv2.matchTemplate(image, template, method)

        # Find best match location
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # For TM_CCOEFF_NORMED, higher is better
        confidence = max_val
        top_left = max_loc

        logger.debug("Template match: confidence=%.3f, location=%s", confidence, top_left)

        return confidence, top_left[0], top_left[1]

    def match_multiscale(
        self, image: np.ndarray, template: np.ndarray, scales: List[float] = [0.9, 1.0, 1.1]
    ) -> Tuple[float, int, int, float]:
        """
        Match template at multiple scales.

        Args:
            image: Grayscale image to search
            template: Grayscale template to find
            scales: List of scale factors to try

        Returns:
            (confidence, center_x, center_y, scale)

        Requirements: 5.3 - Detect elements at different scales (90% to 110%)
        """
        best_confidence = 0.0
        best_location = (0, 0)
        best_scale = 1.0
        best_template_size = template.shape

        for scale in scales:
            # Resize template
            scaled_width = int(template.shape[1] * scale)
            scaled_height = int(template.shape[0] * scale)

            if scaled_width <= 0 or scaled_height <= 0:
                continue

            scaled_template = cv2.resize(
                template, (scaled_width, scaled_height), interpolation=cv2.INTER_LINEAR
            )

            # Skip if scaled template is larger than image
            if (
                scaled_template.shape[0] > image.shape[0]
                or scaled_template.shape[1] > image.shape[1]
            ):
                continue

            # Match at this scale
            confidence, top_left_x, top_left_y = self.match_template(image, scaled_template)

            # Update best match
            if confidence > best_confidence:
                best_confidence = confidence
                best_location = (top_left_x, top_left_y)
                best_scale = scale
                best_template_size = scaled_template.shape

        # Calculate center coordinates
        center_x = best_location[0] + best_template_size[1] // 2
        center_y = best_location[1] + best_template_size[0] // 2

        logger.debug(
            "Multiscale match: confidence=%.3f, center=(%d, %d), scale=%.2f",
            best_confidence,
            center_x,
            center_y,
            best_scale,
        )

        return best_confidence, center_x, center_y, best_scale

    def get_last_screenshot(self) -> Optional[np.ndarray]:
        """Get the last captured screenshot for debugging."""
        return self._last_screenshot
