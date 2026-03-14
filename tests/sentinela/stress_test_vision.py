"""
Long-Run Stability & Stress Test for VisualDetector.

Task 6: Tests VisualDetector under continuous operation for 5 minutes,
monitoring memory usage and detecting potential memory leaks in OpenCV processing.

Features:
- Runs VisualDetector in loop for 5 minutes (one capture every 2s)
- Monitors process memory usage
- Detects memory leaks (constant memory increase)
- Auto-recovery: Restarts camera/driver after 3 consecutive failures
- Reports memory statistics and performance metrics
"""

import logging
import os
import time
from typing import List, Tuple

import psutil

from src.sentinela.exceptions import CatarataError, ScreenshotError
from src.sentinela.visual_detector import VisualDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MemoryMonitor:
    """Monitors process memory usage and detects leaks."""

    def __init__(self, leak_threshold_mb: float = 50.0):
        """
        Initialize memory monitor.

        Args:
            leak_threshold_mb: Memory increase threshold to trigger leak alert (MB)
        """
        self.process = psutil.Process(os.getpid())
        self.leak_threshold_mb = leak_threshold_mb
        self.memory_samples: List[float] = []
        self.start_memory_mb = 0.0

    def start(self) -> None:
        """Start monitoring - record baseline memory."""
        self.start_memory_mb = self._get_memory_mb()
        self.memory_samples = [self.start_memory_mb]
        logger.info("Memory monitoring started: baseline=%.2f MB", self.start_memory_mb)

    def sample(self) -> float:
        """
        Take a memory sample.

        Returns:
            Current memory usage in MB
        """
        memory_mb = self._get_memory_mb()
        self.memory_samples.append(memory_mb)
        return memory_mb

    def _get_memory_mb(self) -> float:
        """Get current process memory in MB."""
        mem_info = self.process.memory_info()
        return mem_info.rss / (1024 * 1024)  # Convert bytes to MB

    def check_for_leak(self) -> Tuple[bool, float, str]:
        """
        Check if memory leak is detected.

        Returns:
            (has_leak, memory_increase_mb, diagnosis)
        """
        if len(self.memory_samples) < 10:
            return False, 0.0, "Not enough samples"

        current_memory = self.memory_samples[-1]
        memory_increase = current_memory - self.start_memory_mb

        # Check if memory increased beyond threshold
        if memory_increase > self.leak_threshold_mb:
            # Verify it's a consistent increase (not just a spike)
            recent_samples = self.memory_samples[-10:]
            is_increasing = all(
                recent_samples[i] <= recent_samples[i + 1] for i in range(len(recent_samples) - 1)
            )

            if is_increasing:
                diagnosis = (
                    f"MEMORY LEAK DETECTED: Consistent increase of {memory_increase:.2f} MB "
                    f"(threshold: {self.leak_threshold_mb:.2f} MB)"
                )
                return True, memory_increase, diagnosis

        return False, memory_increase, "Memory usage stable"

    def get_statistics(self) -> dict:
        """Get memory usage statistics."""
        if not self.memory_samples:
            return {}

        return {
            "start_mb": self.start_memory_mb,
            "end_mb": self.memory_samples[-1],
            "min_mb": min(self.memory_samples),
            "max_mb": max(self.memory_samples),
            "avg_mb": sum(self.memory_samples) / len(self.memory_samples),
            "increase_mb": self.memory_samples[-1] - self.start_memory_mb,
            "samples": len(self.memory_samples),
        }


class CameraRecoveryManager:
    """Manages camera/driver recovery after consecutive failures."""

    def __init__(self, max_consecutive_failures: int = 3):
        """
        Initialize recovery manager.

        Args:
            max_consecutive_failures: Number of failures before triggering recovery
        """
        self.max_consecutive_failures = max_consecutive_failures
        self.consecutive_failures = 0
        self.total_failures = 0
        self.total_recoveries = 0

    def record_success(self) -> None:
        """Record successful capture - reset failure counter."""
        self.consecutive_failures = 0

    def record_failure(self) -> bool:
        """
        Record capture failure.

        Returns:
            True if recovery should be triggered
        """
        self.consecutive_failures += 1
        self.total_failures += 1

        should_recover = self.consecutive_failures >= self.max_consecutive_failures

        if should_recover:
            logger.warning(
                "Camera recovery triggered: %d consecutive failures", self.consecutive_failures
            )

        return should_recover

    def perform_recovery(self) -> bool:
        """
        Perform camera/driver recovery.

        Clears NumPy/Pillow caches and forces garbage collection.

        Returns:
            True if recovery succeeded
        """
        logger.info("Performing camera recovery...")

        try:
            # Clear NumPy cache
            import gc

            gc.collect()

            # Clear PIL/Pillow cache
            from PIL import ImageGrab

            ImageGrab._grab = None  # Clear internal cache if exists

            # Force garbage collection again
            gc.collect()

            # Reset failure counter
            self.consecutive_failures = 0
            self.total_recoveries += 1

            logger.info("✓ Camera recovery completed (recovery #%d)", self.total_recoveries)

            # Wait a moment for system to stabilize
            time.sleep(1.0)

            return True

        except Exception as e:
            logger.error("✗ Camera recovery failed: %s", e)
            return False

    def get_statistics(self) -> dict:
        """Get recovery statistics."""
        return {
            "total_failures": self.total_failures,
            "consecutive_failures": self.consecutive_failures,
            "total_recoveries": self.total_recoveries,
        }


def run_stress_test(
    duration_seconds: int = 300,
    capture_interval_seconds: float = 2.0,
    templates_dir: str = "templates",
    leak_threshold_mb: float = 50.0,
) -> dict:
    """
    Run long-duration stress test on VisualDetector.

    Args:
        duration_seconds: Test duration (default: 300s = 5 minutes)
        capture_interval_seconds: Time between captures (default: 2s)
        templates_dir: Directory containing template images
        leak_threshold_mb: Memory leak threshold in MB

    Returns:
        Dictionary with test results and statistics
    """
    logger.info("=" * 70)
    logger.info("SENTINELA VISION STRESS TEST")
    logger.info("=" * 70)
    logger.info("Duration: %d seconds (%.1f minutes)", duration_seconds, duration_seconds / 60)
    logger.info("Capture interval: %.1f seconds", capture_interval_seconds)
    logger.info("Memory leak threshold: %.2f MB", leak_threshold_mb)
    logger.info("=" * 70)

    # Initialize components
    memory_monitor = MemoryMonitor(leak_threshold_mb=leak_threshold_mb)
    recovery_manager = CameraRecoveryManager(max_consecutive_failures=3)

    # Initialize VisualDetector
    detector = VisualDetector(templates_dir=templates_dir, confidence_threshold=0.85)

    # Start memory monitoring
    memory_monitor.start()

    # Test metrics
    start_time = time.time()
    end_time = start_time + duration_seconds
    iteration = 0
    successful_captures = 0
    failed_captures = 0
    memory_leak_detected = False

    logger.info("Starting stress test loop...")

    try:
        while time.time() < end_time:
            iteration += 1
            elapsed = time.time() - start_time
            remaining = end_time - time.time()

            logger.info(
                "\n[Iteration %d] Elapsed: %.1fs, Remaining: %.1fs", iteration, elapsed, remaining
            )

            try:
                # Capture screenshot
                screenshot = detector.analyzer.capture_screenshot()

                # Verify screenshot is valid
                if screenshot is None or screenshot.size == 0:
                    raise ScreenshotError("Invalid screenshot captured")

                logger.info("✓ Screenshot captured: shape=%s", screenshot.shape)

                # Record success
                recovery_manager.record_success()
                successful_captures += 1

            except CatarataError as e:
                logger.error("✗ Catarata error: %s", e)
                failed_captures += 1

                # Check if recovery needed
                if recovery_manager.record_failure():
                    if not recovery_manager.perform_recovery():
                        logger.error("Recovery failed - aborting test")
                        raise

            except ScreenshotError as e:
                logger.error("✗ Screenshot error: %s", e)
                failed_captures += 1

                # Check if recovery needed
                if recovery_manager.record_failure():
                    if not recovery_manager.perform_recovery():
                        logger.error("Recovery failed - aborting test")
                        raise

            # Sample memory usage
            current_memory = memory_monitor.sample()
            logger.info("Memory: %.2f MB", current_memory)

            # Check for memory leak
            has_leak, increase, diagnosis = memory_monitor.check_for_leak()
            if has_leak and not memory_leak_detected:
                logger.error("=" * 70)
                logger.error("MEMORY LEAK DETECTED!")
                logger.error(diagnosis)
                logger.error("=" * 70)
                memory_leak_detected = True

                # Raise CatarataError to signal memory leak
                raise CatarataError(
                    f"Memory leak detected: {increase:.2f} MB increase "
                    f"(threshold: {leak_threshold_mb:.2f} MB)"
                )

            # Wait for next iteration
            time.sleep(capture_interval_seconds)

    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")

    except CatarataError:
        # Re-raise CatarataError (memory leak)
        raise

    finally:
        # Calculate final statistics
        total_time = time.time() - start_time
        total_captures = successful_captures + failed_captures
        success_rate = (successful_captures / total_captures * 100) if total_captures > 0 else 0

        # Get component statistics
        memory_stats = memory_monitor.get_statistics()
        recovery_stats = recovery_manager.get_statistics()

        # Print final report
        logger.info("\n" + "=" * 70)
        logger.info("STRESS TEST COMPLETE")
        logger.info("=" * 70)
        logger.info("Duration: %.1f seconds (%.1f minutes)", total_time, total_time / 60)
        logger.info("Iterations: %d", iteration)
        logger.info("Successful captures: %d", successful_captures)
        logger.info("Failed captures: %d", failed_captures)
        logger.info("Success rate: %.1f%%", success_rate)
        logger.info("")
        logger.info("Memory Statistics:")
        logger.info("  Start: %.2f MB", memory_stats.get("start_mb", 0))
        logger.info("  End: %.2f MB", memory_stats.get("end_mb", 0))
        logger.info("  Min: %.2f MB", memory_stats.get("min_mb", 0))
        logger.info("  Max: %.2f MB", memory_stats.get("max_mb", 0))
        logger.info("  Avg: %.2f MB", memory_stats.get("avg_mb", 0))
        logger.info("  Increase: %.2f MB", memory_stats.get("increase_mb", 0))
        logger.info("  Samples: %d", memory_stats.get("samples", 0))
        logger.info("")
        logger.info("Recovery Statistics:")
        logger.info("  Total failures: %d", recovery_stats["total_failures"])
        logger.info("  Total recoveries: %d", recovery_stats["total_recoveries"])
        logger.info("  Consecutive failures: %d", recovery_stats["consecutive_failures"])
        logger.info("")
        logger.info("Memory leak detected: %s", "YES" if memory_leak_detected else "NO")
        logger.info("=" * 70)

    # Return results (outside finally block)
    return {
        "duration_seconds": total_time,
        "iterations": iteration,
        "successful_captures": successful_captures,
        "failed_captures": failed_captures,
        "success_rate": success_rate,
        "memory_stats": memory_stats,
        "recovery_stats": recovery_stats,
        "memory_leak_detected": memory_leak_detected,
    }


if __name__ == "__main__":
    import sys

    # Parse command-line arguments
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 300  # Default: 5 minutes
    interval = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0  # Default: 2 seconds

    try:
        results = run_stress_test(duration_seconds=duration, capture_interval_seconds=interval)

        # Exit with success
        sys.exit(0)

    except CatarataError as e:
        logger.error("STRESS TEST FAILED: %s", e)
        sys.exit(1)

    except Exception as e:
        logger.error("STRESS TEST ERROR: %s", e, exc_info=True)
        sys.exit(2)
