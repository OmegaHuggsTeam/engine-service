"""
Visual Detector - Template-based visual element detection with anchoring.

Requirements: 3.4, 4.4, 5.1, 5.2, 8.1, 8.3

Implements:
- Template loading and caching
- Anchor-based Dashboard detection (logo, refresh button, status icon)
- Visual confirmation for mission completion
- Noise filtering (ignore system notifications/popups)
- Last failure screenshot for Visual Evidence Uploader
"""

import base64
import logging
import os
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
import cv2
import numpy as np

from .screenshot_analyzer import ScreenshotAnalyzer
from .exceptions import TemplateNotFoundError, VisualDetectionError

logger = logging.getLogger(__name__)

DEFAULT_EVIDENCE_DIR = Path("temp/evidence")


@dataclass
class VisualMatchResult:
    """Result of visual element detection."""
    found: bool
    confidence: float
    center_x: Optional[int] = None
    center_y: Optional[int] = None
    template_name: Optional[str] = None
    scale: float = 1.0


@dataclass
class AnchorPoint:
    """Anchor point for Dashboard identification."""
    name: str
    template_path: str
    required: bool = True
    min_confidence: float = 0.85


class VisualDetector:
    """
    Visual detector with template matching and anchor-based identification.
    
    Anchor System:
    - Uses 3 fixed elements to confirm Dashboard is visible
    - Only proceeds with mission if anchors are detected
    - Filters out noise (system notifications, popups)
    """
    
    def __init__(
        self,
        templates_dir: str,
        confidence_threshold: float = 0.85,
        learning_mode: bool = True,
        learning_threshold: float = 0.60,
        telemetry_hub=None
    ):
        """
        Initialize visual detector.
        
        Args:
            templates_dir: Directory containing template images
            confidence_threshold: Minimum confidence for matches (0.0-1.0)
            learning_mode: Enable learning mode for template suggestions
            learning_threshold: Threshold for learning mode detection (0.0-1.0)
            telemetry_hub: Optional TelemetryHub for event reporting
        """
        self.templates_dir = Path(templates_dir)
        self.confidence_threshold = confidence_threshold
        self.learning_mode = learning_mode
        self.learning_threshold = learning_threshold
        self.telemetry_hub = telemetry_hub
        
        # Screenshot analyzer
        self.analyzer = ScreenshotAnalyzer(telemetry_hub=telemetry_hub)
        
        # Template cache: {name: grayscale_image}
        self._template_cache: Dict[str, np.ndarray] = {}
        
        # Anchor points for Dashboard identification
        self._anchors: List[AnchorPoint] = []
        
        # Learning mode suggestions
        self._learning_suggestions: List[Dict] = []
        
        # Last failure screenshot for Visual Evidence Uploader
        self._last_failure_screenshot: Optional[np.ndarray] = None
        self._last_failure_path: Optional[Path] = None
        self._evidence_dir = Path(os.environ.get("EVIDENCE_DIR", str(DEFAULT_EVIDENCE_DIR)))
        
        # Load templates on initialization
        self._load_templates()
        
        logger.info(
            "VisualDetector initialized: templates_dir=%s, threshold=%.2f, learning=%s",
            templates_dir,
            confidence_threshold,
            learning_mode
        )
    
    def _load_templates(self) -> None:
        """Load all template images from templates directory."""
        if not self.templates_dir.exists():
            logger.warning("Templates directory does not exist: %s", self.templates_dir)
            return
        
        # Find all image files
        image_extensions = ['.png', '.jpg', '.jpeg', '.bmp']
        template_files = []
        
        for ext in image_extensions:
            template_files.extend(self.templates_dir.glob(f'*{ext}'))
        
        logger.info("Found %d template files", len(template_files))
        
        for template_path in template_files:
            try:
                # Load image
                img = cv2.imread(str(template_path))
                if img is None:
                    logger.warning("Failed to load template: %s", template_path)
                    continue
                
                # Convert to grayscale
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                
                # Cache with filename (without extension) as key
                template_name = template_path.stem
                self._template_cache[template_name] = gray
                
                logger.debug("Loaded template: %s (%s)", template_name, gray.shape)
                
            except Exception as e:
                logger.error("Error loading template %s: %s", template_path, e)
    
    def reload_templates(self) -> None:
        """
        Reload all templates from disk.
        
        Requirements: 8.3 - Hot-reload without restart
        """
        logger.info("Reloading templates from %s", self.templates_dir)
        self._template_cache.clear()
        self._load_templates()
        
        if self.telemetry_hub:
            self._report_event(
                "Templates reloaded",
                {"count": len(self._template_cache)}
            )
    
    def _save_failure_screenshot(self, screenshot: Optional[np.ndarray] = None) -> None:
        """
        Save screenshot when a visual detection fails (for Visual Evidence Uploader).
        Stores in memory and writes to evidence dir for Evidence Server.
        """
        if screenshot is None:
            screenshot = self.analyzer.capture_screenshot()
        if screenshot is None:
            return
        self._last_failure_screenshot = screenshot.copy()
        self._evidence_dir.mkdir(parents=True, exist_ok=True)
        self._last_failure_path = self._evidence_dir / "last_fail.png"
        try:
            # OpenCV uses BGR; PIL/cv2.imwrite expects BGR
            cv2.imwrite(str(self._last_failure_path), screenshot)
            logger.debug("Saved failure screenshot to %s", self._last_failure_path)
        except Exception as e:
            logger.warning("Could not save failure screenshot: %s", e)
    
    def get_last_failure_screenshot_as_base64(self) -> str:
        """
        Return the last failure screenshot as base64-encoded PNG.
        Used by Visual Evidence Uploader for IFTTT / Evidence Server.
        
        Returns:
            Base64 string of PNG image, or empty string if none available.
        """
        img = self._last_failure_screenshot
        if img is None and self._last_failure_path and self._last_failure_path.exists():
            img = cv2.imread(str(self._last_failure_path))
        if img is None:
            return ""
        _, buf = cv2.imencode(".png", img)
        return base64.b64encode(buf.tobytes()).decode("ascii")
    
    def configure_anchors(self, anchors: List[AnchorPoint]) -> None:
        """
        Configure anchor points for Dashboard identification.
        
        Args:
            anchors: List of anchor points (logo, refresh, status, etc)
        """
        self._anchors = anchors
        logger.info("Configured %d anchor points", len(anchors))
        
        for anchor in anchors:
            logger.debug(
                "Anchor: %s (required=%s, min_conf=%.2f)",
                anchor.name,
                anchor.required,
                anchor.min_confidence
            )
    
    def find_element(
        self,
        template_name: str,
        screenshot: Optional[np.ndarray] = None
    ) -> VisualMatchResult:
        """
        Find visual element on screen using template matching.
        
        Args:
            template_name: Name of template (without extension)
            screenshot: Optional pre-captured screenshot (captures new if None)
            
        Returns:
            VisualMatchResult with detection details
            
        Requirements: 5.1, 5.2 - Accept template, return coordinates
        """
        # Get template from cache
        if template_name not in self._template_cache:
            logger.error("Template not found in cache: %s", template_name)
            raise TemplateNotFoundError(f"Template '{template_name}' not found")
        
        template = self._template_cache[template_name]
        
        # Capture screenshot if not provided
        if screenshot is None:
            screenshot = self.analyzer.capture_screenshot()
        
        # Convert to grayscale
        gray_screenshot = self.analyzer.to_grayscale(screenshot)
        
        # Multi-scale matching
        confidence, center_x, center_y, scale = self.analyzer.match_multiscale(
            gray_screenshot,
            template,
            scales=[0.9, 1.0, 1.1]
        )
        
        # Check confidence threshold
        found = confidence >= self.confidence_threshold
        
        if not found:
            self._save_failure_screenshot(screenshot)
        
        # Learning mode: Check if detection is in learning range
        if not found and self.learning_mode:
            if self.learning_threshold <= confidence < self.confidence_threshold:
                # Found with lower confidence - suggest template update
                logger.warning(
                    "LEARNING MODE: Template '%s' detected with low confidence %.3f "
                    "(threshold: %.3f). Consider re-capturing this template.",
                    template_name,
                    confidence,
                    self.confidence_threshold
                )
                
                # Store suggestion
                suggestion = {
                    "template": template_name,
                    "confidence": confidence,
                    "threshold": self.confidence_threshold,
                    "position": (center_x, center_y),
                    "message": f"Template '{template_name}' may need update (conf={confidence:.3f})"
                }
                self._learning_suggestions.append(suggestion)
                
                # Report to telemetry
                if self.telemetry_hub:
                    self._report_event(
                        f"LEARNING: Template '{template_name}' needs update",
                        {
                            "template": template_name,
                            "confidence": confidence,
                            "threshold": self.confidence_threshold,
                            "suggestion": "re-capture template"
                        }
                    )
        
        result = VisualMatchResult(
            found=found,
            confidence=confidence,
            center_x=center_x if found else None,
            center_y=center_y if found else None,
            template_name=template_name,
            scale=scale
        )
        
        logger.debug(
            "Element search: %s, found=%s, conf=%.3f, pos=(%s, %s)",
            template_name,
            found,
            confidence,
            center_x if found else "N/A",
            center_y if found else "N/A"
        )
        
        # Report to telemetry
        if self.telemetry_hub:
            self._report_detection(result)
        
        return result
    
    def verify_dashboard_visible(
        self,
        screenshot: Optional[np.ndarray] = None
    ) -> Tuple[bool, Dict[str, VisualMatchResult]]:
        """
        Verify Dashboard is visible using anchor points.
        
        This is the "Confirmação de Visualização" - ensures we're looking
        at the correct Dashboard before proceeding with mission.
        
        Args:
            screenshot: Optional pre-captured screenshot
            
        Returns:
            (is_visible, anchor_results) tuple
            - is_visible: True if all required anchors detected
            - anchor_results: Dict of anchor_name -> VisualMatchResult
            
        Requirements: 3.4 - Confidence threshold filtering
        """
        if not self._anchors:
            logger.warning("No anchors configured, cannot verify Dashboard")
            return False, {}
        
        # Capture screenshot once for all anchors
        if screenshot is None:
            screenshot = self.analyzer.capture_screenshot()
        
        anchor_results = {}
        required_found = 0
        required_total = sum(1 for a in self._anchors if a.required)
        
        for anchor in self._anchors:
            try:
                # Find anchor element
                result = self.find_element(anchor.name, screenshot=screenshot)
                anchor_results[anchor.name] = result
                
                # Check if meets minimum confidence
                if result.found and result.confidence >= anchor.min_confidence:
                    if anchor.required:
                        required_found += 1
                    logger.debug(
                        "Anchor '%s' detected: conf=%.3f at (%d, %d)",
                        anchor.name,
                        result.confidence,
                        result.center_x,
                        result.center_y
                    )
                else:
                    if anchor.required:
                        logger.warning(
                            "Required anchor '%s' not found (conf=%.3f < %.3f)",
                            anchor.name,
                            result.confidence,
                            anchor.min_confidence
                        )
                
            except Exception as e:
                logger.error("Error detecting anchor '%s': %s", anchor.name, e)
                anchor_results[anchor.name] = VisualMatchResult(
                    found=False,
                    confidence=0.0,
                    template_name=anchor.name
                )
        
        # Dashboard is visible if all required anchors found
        is_visible = required_found == required_total
        
        if not is_visible:
            self._save_failure_screenshot(screenshot)
        
        logger.info(
            "Dashboard verification: visible=%s (%d/%d required anchors)",
            is_visible,
            required_found,
            required_total
        )
        
        # Report to telemetry
        if self.telemetry_hub:
            self._report_event(
                f"Dashboard verification: {'VISIBLE' if is_visible else 'NOT VISIBLE'}",
                {
                    "required_found": required_found,
                    "required_total": required_total,
                    "anchors": {
                        name: {"found": r.found, "confidence": r.confidence}
                        for name, r in anchor_results.items()
                    }
                }
            )
        
        return is_visible, anchor_results
    
    def confirm_alert_visible(
        self,
        alert_template_name: str = "alert_quality_low",
        screenshot: Optional[np.ndarray] = None
    ) -> bool:
        """
        Confirm quality_score alert is visible on Dashboard.
        
        This is the mission completion check - Sentinela only marks
        mission as complete if it "sees" the alert.
        
        Args:
            alert_template_name: Name of alert template
            screenshot: Optional pre-captured screenshot
            
        Returns:
            True if alert is visible with high confidence
        """
        logger.info("Confirming alert visibility: %s", alert_template_name)
        
        if screenshot is None:
            screenshot = self.analyzer.capture_screenshot()
        
        try:
            result = self.find_element(alert_template_name, screenshot=screenshot)
            
            if result.found:
                logger.info(
                    "✓ Alert CONFIRMED visible: conf=%.3f at (%d, %d)",
                    result.confidence,
                    result.center_x,
                    result.center_y
                )
                
                # Report success to telemetry
                if self.telemetry_hub:
                    self._report_event(
                        "MISSION COMPLETE: Alert confirmed visible",
                        {
                            "alert": alert_template_name,
                            "confidence": result.confidence,
                            "position": (result.center_x, result.center_y)
                        }
                    )
                
                return True
            else:
                self._save_failure_screenshot(screenshot)
                logger.warning(
                    "✗ Alert NOT visible: conf=%.3f < %.3f",
                    result.confidence,
                    self.confidence_threshold
                )
                return False
                
        except TemplateNotFoundError:
            logger.error("Alert template not found: %s", alert_template_name)
            return False
        except Exception as e:
            logger.error("Error confirming alert: %s", e)
            return False
    
    def filter_noise(
        self,
        screenshot: Optional[np.ndarray] = None,
        noise_templates: Optional[List[str]] = None,
        clear_on_detection: bool = True
    ) -> Tuple[bool, List[str]]:
        """
        Detect and filter visual noise (system notifications, popups).
        
        This is the "Ambiente Ruidoso" test - ensures Sentinela ignores
        distractions and focuses only on the Dashboard.
        
        Args:
            screenshot: Optional pre-captured screenshot
            noise_templates: List of noise template names to check
            clear_on_detection: If True, attempt to clear noise with ESC
            
        Returns:
            (has_noise, detected_noise) tuple
            - has_noise: True if any noise detected
            - detected_noise: List of detected noise template names
            
        Requirements: 4.4 (from Task 4) - Ignore non-Dashboard elements
        """
        if noise_templates is None:
            # Default noise templates
            noise_templates = [
                "windows_notification",
                "system_popup",
                "browser_popup",
                "update_notification"
            ]
        
        if screenshot is None:
            screenshot = self.analyzer.capture_screenshot()
        
        detected_noise = []
        noise_positions = []
        
        for noise_name in noise_templates:
            # Skip if template not in cache
            if noise_name not in self._template_cache:
                continue
            
            try:
                result = self.find_element(noise_name, screenshot=screenshot)
                
                if result.found:
                    detected_noise.append(noise_name)
                    noise_positions.append((result.center_x, result.center_y))
                    logger.warning(
                        "NOISE detected: %s (conf=%.3f) at (%d, %d) - IGNORING",
                        noise_name,
                        result.confidence,
                        result.center_x,
                        result.center_y
                    )
            except Exception as e:
                logger.debug("Error checking noise template %s: %s", noise_name, e)
        
        has_noise = len(detected_noise) > 0
        
        if has_noise:
            logger.info("Noise filtering: %d noise elements detected", len(detected_noise))
            
            # Attempt to clear noise if requested
            if clear_on_detection:
                self._clear_noise_with_esc(detected_noise, noise_positions)
            
            # Report to telemetry
            if self.telemetry_hub:
                self._report_event(
                    "Noise detected and filtered",
                    {
                        "noise_elements": detected_noise,
                        "positions": noise_positions,
                        "cleared": clear_on_detection
                    }
                )
        
        return has_noise, detected_noise
    
    def _clear_noise_with_esc(
        self,
        noise_elements: List[str],
        positions: List[Tuple[int, int]]
    ) -> bool:
        """
        Attempt to clear noise by sending ESC key.
        
        Args:
            noise_elements: List of detected noise element names
            positions: List of (x, y) positions of noise elements
            
        Returns:
            True if ESC was sent successfully
        """
        logger.info("Attempting to clear noise with ESC key...")
        
        try:
            import pyautogui
            
            # Send ESC key to close notifications/popups
            pyautogui.press('esc')
            
            logger.info("✓ ESC sent to clear noise")
            
            # Wait a moment for noise to clear
            import time
            time.sleep(0.5)
            
            # Report to telemetry
            if self.telemetry_hub:
                self._report_event(
                    "Noise cleared with ESC",
                    {
                        "noise_elements": noise_elements,
                        "method": "ESC key"
                    }
                )
            
            return True
            
        except ImportError:
            logger.warning("pyautogui not available - cannot send ESC")
            return False
        except Exception as e:
            logger.error("Error sending ESC: %s", e)
            return False
    
    def _report_detection(self, result: VisualMatchResult) -> None:
        """Report detection result to TelemetryHub."""
        if not self.telemetry_hub:
            return
        
        try:
            from src.neural_link.telemetry.provider import TelemetryEvent, EventType
            
            event = TelemetryEvent(
                event_type=EventType.LOG,
                source="sentinela_visual",
                message=f"Visual detection: {result.template_name}",
                data={
                    "template": result.template_name,
                    "found": result.found,
                    "confidence": result.confidence,
                    "position": (result.center_x, result.center_y) if result.found else None,
                    "scale": result.scale,
                }
            )
            
            self.telemetry_hub._event_log.append(event)
            
        except Exception as e:
            logger.warning("Failed to report detection to TelemetryHub: %s", e)
    
    def _report_event(self, message: str, data: dict) -> None:
        """Report general event to TelemetryHub."""
        if not self.telemetry_hub:
            return
        
        try:
            from src.neural_link.telemetry.provider import TelemetryEvent, EventType
            
            event = TelemetryEvent(
                event_type=EventType.LOG,
                source="sentinela_visual",
                message=message,
                data=data
            )
            
            self.telemetry_hub._event_log.append(event)
            
        except Exception as e:
            logger.warning("Failed to report event to TelemetryHub: %s", e)
    
    @property
    def loaded_templates(self) -> List[str]:
        """Get list of loaded template names."""
        return list(self._template_cache.keys())
    
    @property
    def template_count(self) -> int:
        """Get count of loaded templates."""
        return len(self._template_cache)
    
    @property
    def learning_suggestions(self) -> List[Dict]:
        """Get list of learning mode suggestions."""
        return list(self._learning_suggestions)
    
    def clear_learning_suggestions(self) -> None:
        """Clear all learning mode suggestions."""
        self._learning_suggestions.clear()
        logger.info("Learning suggestions cleared")
    
    def get_learning_report(self) -> str:
        """
        Get formatted report of learning suggestions.
        
        Returns:
            Formatted string with suggestions
        """
        if not self._learning_suggestions:
            return "No learning suggestions"
        
        report = f"\n{'='*70}\n"
        report += "LEARNING MODE REPORT\n"
        report += f"{'='*70}\n"
        report += f"Total suggestions: {len(self._learning_suggestions)}\n\n"
        
        for i, suggestion in enumerate(self._learning_suggestions, 1):
            report += f"{i}. Template: {suggestion['template']}\n"
            report += f"   Confidence: {suggestion['confidence']:.3f} "
            report += f"(threshold: {suggestion['threshold']:.3f})\n"
            report += f"   Position: {suggestion['position']}\n"
            report += f"   Recommendation: Re-capture this template\n"
            report += f"   Command: python -m src.sentinela.tools.capture_templates\n\n"
        
        return report
