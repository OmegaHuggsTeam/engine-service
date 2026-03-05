"""
Demo: Sentinela Vision Stress Test

Demonstrates how to run the long-duration stability test for VisualDetector.

Usage:
    # Run 5-minute test (default)
    python examples/sentinela_stress_test_demo.py
    
    # Run 10-minute test
    python examples/sentinela_stress_test_demo.py --duration 600
    
    # Run with custom interval
    python examples/sentinela_stress_test_demo.py --duration 300 --interval 1.0
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.sentinela.stress_test_vision import run_stress_test
from src.sentinela.exceptions import CatarataError


def main():
    parser = argparse.ArgumentParser(
        description="Run Sentinela Vision stress test"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Test duration in seconds (default: 300 = 5 minutes)"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Capture interval in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--templates",
        type=str,
        default="templates",
        help="Templates directory (default: templates)"
    )
    parser.add_argument(
        "--leak-threshold",
        type=float,
        default=50.0,
        help="Memory leak threshold in MB (default: 50.0)"
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("SENTINELA VISION STRESS TEST DEMO")
    print("="*70)
    print(f"Duration: {args.duration}s ({args.duration/60:.1f} minutes)")
    print(f"Interval: {args.interval}s")
    print(f"Templates: {args.templates}")
    print(f"Leak threshold: {args.leak_threshold} MB")
    print("="*70)
    print("\nPress Ctrl+C to stop the test early\n")
    
    try:
        results = run_stress_test(
            duration_seconds=args.duration,
            capture_interval_seconds=args.interval,
            templates_dir=args.templates,
            leak_threshold_mb=args.leak_threshold
        )
        
        print("\n✓ Stress test completed successfully!")
        print(f"  Success rate: {results['success_rate']:.1f}%")
        print(f"  Memory increase: {results['memory_stats']['increase_mb']:.2f} MB")
        print(f"  Recoveries: {results['recovery_stats']['total_recoveries']}")
        
        if results['memory_leak_detected']:
            print("\n⚠ WARNING: Memory leak detected!")
            return 1
        
        return 0
        
    except CatarataError as e:
        print(f"\n✗ STRESS TEST FAILED: {e}")
        print("\nCatarata error indicates:")
        print("  - Memory leak in OpenCV processing")
        print("  - Screen capture permission issues")
        print("  - Display driver problems")
        return 1
    
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 0
    
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
