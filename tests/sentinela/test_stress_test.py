"""
Unit tests for stress test components.

Tests the MemoryMonitor and CameraRecoveryManager in isolation.
"""

import pytest
import time
from tests.sentinela.stress_test_vision import (
    MemoryMonitor,
    CameraRecoveryManager
)


class TestMemoryMonitor:
    """Test MemoryMonitor functionality."""
    
    def test_initialization(self):
        """Test MemoryMonitor initializes correctly."""
        monitor = MemoryMonitor(leak_threshold_mb=50.0)
        
        assert monitor.leak_threshold_mb == 50.0
        assert monitor.memory_samples == []
        assert monitor.start_memory_mb == 0.0
    
    def test_start_records_baseline(self):
        """Test start() records baseline memory."""
        monitor = MemoryMonitor()
        monitor.start()
        
        assert monitor.start_memory_mb > 0
        assert len(monitor.memory_samples) == 1
        assert monitor.memory_samples[0] == monitor.start_memory_mb
    
    def test_sample_records_memory(self):
        """Test sample() records memory usage."""
        monitor = MemoryMonitor()
        monitor.start()
        
        initial_samples = len(monitor.memory_samples)
        memory_mb = monitor.sample()
        
        assert memory_mb > 0
        assert len(monitor.memory_samples) == initial_samples + 1
        assert monitor.memory_samples[-1] == memory_mb
    
    def test_check_for_leak_not_enough_samples(self):
        """Test leak detection with insufficient samples."""
        monitor = MemoryMonitor()
        monitor.start()
        
        # Add only a few samples
        for _ in range(5):
            monitor.sample()
        
        has_leak, increase, diagnosis = monitor.check_for_leak()
        
        assert not has_leak
        assert diagnosis == "Not enough samples"
    
    def test_check_for_leak_stable_memory(self):
        """Test leak detection with stable memory."""
        monitor = MemoryMonitor(leak_threshold_mb=50.0)
        monitor.start()
        
        # Simulate stable memory (add same value multiple times)
        baseline = monitor.start_memory_mb
        for _ in range(15):
            monitor.memory_samples.append(baseline + 1.0)  # Small variation
        
        has_leak, increase, diagnosis = monitor.check_for_leak()
        
        assert not has_leak
        assert increase < 50.0
    
    def test_check_for_leak_detects_leak(self):
        """Test leak detection with increasing memory."""
        monitor = MemoryMonitor(leak_threshold_mb=50.0)
        monitor.start()
        
        # Simulate memory leak (consistent increase)
        baseline = monitor.start_memory_mb
        for i in range(15):
            monitor.memory_samples.append(baseline + (i + 1) * 5.0)  # +5 MB each
        
        has_leak, increase, diagnosis = monitor.check_for_leak()
        
        assert has_leak
        assert increase > 50.0
        assert "MEMORY LEAK DETECTED" in diagnosis
    
    def test_get_statistics(self):
        """Test statistics calculation."""
        monitor = MemoryMonitor()
        monitor.start()
        
        # Add some samples
        for _ in range(10):
            monitor.sample()
        
        stats = monitor.get_statistics()
        
        assert "start_mb" in stats
        assert "end_mb" in stats
        assert "min_mb" in stats
        assert "max_mb" in stats
        assert "avg_mb" in stats
        assert "increase_mb" in stats
        assert "samples" in stats
        
        assert stats["samples"] == 11  # 1 start + 10 samples
        assert stats["start_mb"] > 0
        assert stats["end_mb"] > 0


class TestCameraRecoveryManager:
    """Test CameraRecoveryManager functionality."""
    
    def test_initialization(self):
        """Test CameraRecoveryManager initializes correctly."""
        manager = CameraRecoveryManager(max_consecutive_failures=3)
        
        assert manager.max_consecutive_failures == 3
        assert manager.consecutive_failures == 0
        assert manager.total_failures == 0
        assert manager.total_recoveries == 0
    
    def test_record_success_resets_counter(self):
        """Test record_success() resets consecutive failures."""
        manager = CameraRecoveryManager()
        
        # Simulate some failures
        manager.consecutive_failures = 2
        manager.total_failures = 5
        
        # Record success
        manager.record_success()
        
        assert manager.consecutive_failures == 0
        assert manager.total_failures == 5  # Total not reset
    
    def test_record_failure_increments_counters(self):
        """Test record_failure() increments counters."""
        manager = CameraRecoveryManager()
        
        should_recover = manager.record_failure()
        
        assert manager.consecutive_failures == 1
        assert manager.total_failures == 1
        assert not should_recover  # Not yet at threshold
    
    def test_record_failure_triggers_recovery(self):
        """Test record_failure() triggers recovery at threshold."""
        manager = CameraRecoveryManager(max_consecutive_failures=3)
        
        # Record failures up to threshold
        manager.record_failure()  # 1
        manager.record_failure()  # 2
        should_recover = manager.record_failure()  # 3
        
        assert should_recover
        assert manager.consecutive_failures == 3
        assert manager.total_failures == 3
    
    def test_perform_recovery_resets_counter(self):
        """Test perform_recovery() resets consecutive failures."""
        manager = CameraRecoveryManager()
        
        # Simulate failures
        manager.consecutive_failures = 3
        manager.total_failures = 5
        
        # Perform recovery
        success = manager.perform_recovery()
        
        assert success
        assert manager.consecutive_failures == 0
        assert manager.total_failures == 5  # Total not reset
        assert manager.total_recoveries == 1
    
    def test_get_statistics(self):
        """Test statistics retrieval."""
        manager = CameraRecoveryManager()
        
        # Simulate some activity
        manager.record_failure()
        manager.record_failure()
        manager.perform_recovery()
        manager.record_failure()
        
        stats = manager.get_statistics()
        
        assert stats["total_failures"] == 3
        assert stats["consecutive_failures"] == 1
        assert stats["total_recoveries"] == 1
    
    def test_recovery_workflow(self):
        """Test complete recovery workflow."""
        manager = CameraRecoveryManager(max_consecutive_failures=3)
        
        # Simulate failures leading to recovery
        assert not manager.record_failure()  # 1
        assert not manager.record_failure()  # 2
        assert manager.record_failure()      # 3 - triggers recovery
        
        # Perform recovery
        assert manager.perform_recovery()
        
        # Verify state after recovery
        assert manager.consecutive_failures == 0
        assert manager.total_failures == 3
        assert manager.total_recoveries == 1
        
        # Simulate success after recovery
        manager.record_success()
        
        # Verify counters
        assert manager.consecutive_failures == 0
        assert manager.total_failures == 3


@pytest.mark.integration
class TestStressTestIntegration:
    """Integration tests for stress test (short duration)."""
    
    def test_short_stress_test(self):
        """Test stress test runs for short duration."""
        from tests.sentinela.stress_test_vision import run_stress_test
        
        # Run for only 10 seconds with 1s interval
        results = run_stress_test(
            duration_seconds=10,
            capture_interval_seconds=1.0,
            templates_dir="templates",
            leak_threshold_mb=100.0  # High threshold to avoid false positives
        )
        
        # Verify results structure
        assert "duration_seconds" in results
        assert "iterations" in results
        assert "successful_captures" in results
        assert "failed_captures" in results
        assert "success_rate" in results
        assert "memory_stats" in results
        assert "recovery_stats" in results
        assert "memory_leak_detected" in results
        
        # Verify test ran
        assert results["iterations"] >= 5  # At least 5 iterations in 10s
        assert results["duration_seconds"] >= 10.0
        
        # Verify memory stats
        mem_stats = results["memory_stats"]
        assert mem_stats["start_mb"] > 0
        assert mem_stats["end_mb"] > 0
        assert mem_stats["samples"] > 0
