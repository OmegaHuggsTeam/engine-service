"""
Demo: Sentinela IFTTT Connector with Connectivity Watchdog

Demonstrates:
- Health check before sending critical alerts
- Exponential retry logic (30s, 1min, 5min)
- Offline isolation detection
- TelemetryHub integration
- Obsidian logging for failures

Usage:
    python examples/sentinela_ifttt_demo.py
"""

import os
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sentinela.ifttt_connector import ConnectivityStatus, IFTTTConnector, RetryConfig


class MockObsidianLogger:
    """Mock Obsidian logger for demo."""

    def __init__(self):
        self.failures = []

    def log_failure(self, log_entry: str):
        """Log failure to memory."""
        self.failures.append(log_entry)
        print(f"\n{'='*70}")
        print("OBSIDIAN LOG ENTRY")
        print(f"{'='*70}")
        print(log_entry)
        print(f"{'='*70}\n")


def demo_health_check():
    """Demo: Health check functionality."""
    print("\n" + "=" * 70)
    print("DEMO 1: Health Check")
    print("=" * 70)

    # Get webhook key from environment
    webhook_key = os.getenv("IFTTT_WEBHOOK_KEY", "demo_key_12345")

    connector = IFTTTConnector(webhook_key=webhook_key)

    print(f"Webhook key: {webhook_key[:10]}...")
    print("\nPerforming health check...")

    is_healthy, status, message = connector.health_check()

    print("\nResult:")
    print(f"  Healthy: {is_healthy}")
    print(f"  Status: {status.value}")
    print(f"  Message: {message}")

    if status == ConnectivityStatus.OFFLINE:
        print("\n⚠ OFFLINE_ISOLATION detected!")
        print(f"  Offline events: {connector.offline_events}")


def demo_send_alert():
    """Demo: Send alert with automatic retry."""
    print("\n" + "=" * 70)
    print("DEMO 2: Send Alert with Retry")
    print("=" * 70)

    webhook_key = os.getenv("IFTTT_WEBHOOK_KEY", "demo_key_12345")

    # Configure retry with shorter delays for demo
    retry_config = RetryConfig(
        delays_seconds=[5, 10, 15],  # 5s, 10s, 15s for demo
        max_attempts=3,
    )

    connector = IFTTTConnector(webhook_key=webhook_key, retry_config=retry_config)

    print(f"Retry delays: {retry_config.delays_seconds}")
    print(f"Max attempts: {retry_config.max_attempts}")

    print("\nSending alert to Telegram...")

    success, message = connector.send_alert(
        event_name="telegram_alert",
        value1="🔔 Sentinela Alert: Quality score below threshold",
        value2="Agent: agent_123",
        value3="Score: 3.5",
        alert_id="demo_alert_001",
    )

    print("\nResult:")
    print(f"  Success: {success}")
    print(f"  Message: {message}")

    if not success:
        print("\n⏱ Alert scheduled for retry")
        pending = connector.get_pending_alerts()
        if pending:
            alert = pending[0]
            print(f"  Alert ID: {alert['alert_id']}")
            print(f"  Status: {alert['status']}")
            print(f"  Next retry: {alert['next_retry_at']}")


def demo_critical_alert_with_health_check():
    """Demo: Critical alert with health check."""
    print("\n" + "=" * 70)
    print("DEMO 3: Critical Alert with Health Check")
    print("=" * 70)

    webhook_key = os.getenv("IFTTT_WEBHOOK_KEY", "demo_key_12345")

    connector = IFTTTConnector(webhook_key=webhook_key)

    print("Sending CRITICAL alert (health check will be performed first)...")

    success, message = connector.send_alert(
        event_name="telegram_critical",
        value1="🚨 CRITICAL: System offline isolation detected",
        value2="Component: IFTTT Connector",
        value3="Action: Manual intervention required",
        critical=True,  # Triggers health check
    )

    print("\nResult:")
    print(f"  Success: {success}")
    print(f"  Message: {message}")

    stats = connector.get_statistics()
    print("\nConnector Statistics:")
    print(f"  Connectivity: {stats['connectivity_status']}")
    print(f"  Alerts sent: {stats['total_alerts_sent']}")
    print(f"  Alerts failed: {stats['total_alerts_failed']}")
    print(f"  Offline events: {stats['offline_events']}")


def demo_retry_processing():
    """Demo: Process pending retries."""
    print("\n" + "=" * 70)
    print("DEMO 4: Retry Processing")
    print("=" * 70)

    webhook_key = os.getenv("IFTTT_WEBHOOK_KEY", "demo_key_12345")

    retry_config = RetryConfig(
        delays_seconds=[2, 4, 6],  # Short delays for demo
        max_attempts=3,
    )

    obsidian_logger = MockObsidianLogger()

    connector = IFTTTConnector(
        webhook_key=webhook_key, retry_config=retry_config, obsidian_logger=obsidian_logger
    )

    print("Sending alert (may fail and schedule retry)...")

    connector.send_alert(
        event_name="telegram_alert", value1="Test message for retry demo", alert_id="retry_demo_001"
    )

    print(f"\nPending alerts: {len(connector.pending_alerts)}")

    if connector.pending_alerts:
        print("\nWaiting for retry window...")

        # Simulate retry processing loop
        for i in range(5):
            time.sleep(1)

            retries_processed = connector.process_retries()

            if retries_processed > 0:
                print(f"  Processed {retries_processed} retry(ies)")

            if not connector.pending_alerts:
                print("  All alerts processed!")
                break

        # Show final statistics
        stats = connector.get_statistics()
        print("\nFinal Statistics:")
        print(f"  Alerts sent: {stats['total_alerts_sent']}")
        print(f"  Alerts failed: {stats['total_alerts_failed']}")
        print(f"  Total retries: {stats['total_retries']}")
        print(f"  Pending: {stats['pending_alerts']}")

        # Show Obsidian logs if any failures
        if obsidian_logger.failures:
            print(f"\n📝 {len(obsidian_logger.failures)} failure(s) logged to Obsidian")


def demo_statistics():
    """Demo: View connector statistics."""
    print("\n" + "=" * 70)
    print("DEMO 5: Connector Statistics")
    print("=" * 70)

    webhook_key = os.getenv("IFTTT_WEBHOOK_KEY", "demo_key_12345")

    connector = IFTTTConnector(webhook_key=webhook_key)

    # Perform some operations
    connector.health_check()
    connector.send_alert(event_name="telegram_alert", value1="Statistics demo message")

    # Get statistics
    stats = connector.get_statistics()

    print("\nConnector Statistics:")
    print(f"  Connectivity Status: {stats['connectivity_status']}")
    print(f"  Last Health Check: {stats['last_health_check']}")
    print(f"  Last Successful Send: {stats['last_successful_send']}")
    print(f"  Total Alerts Sent: {stats['total_alerts_sent']}")
    print(f"  Total Alerts Failed: {stats['total_alerts_failed']}")
    print(f"  Total Retries: {stats['total_retries']}")
    print(f"  Offline Events: {stats['offline_events']}")
    print(f"  Pending Alerts: {stats['pending_alerts']}")

    print("\nRetry Configuration:")
    print(f"  Delays: {stats['retry_config']['delays_seconds']} seconds")
    print(f"  Max Attempts: {stats['retry_config']['max_attempts']}")

    # Get pending alerts
    pending = connector.get_pending_alerts()
    if pending:
        print("\nPending Alerts:")
        for alert in pending:
            print(f"  - {alert['alert_id']}: {alert['status']} ({alert['attempts']} attempts)")


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("SENTINELA IFTTT CONNECTOR DEMO")
    print("=" * 70)
    print("\nThis demo shows the connectivity watchdog features:")
    print("  1. Health check before critical alerts")
    print("  2. Exponential retry logic (30s, 1min, 5min)")
    print("  3. Offline isolation detection")
    print("  4. Retry processing")
    print("  5. Statistics and monitoring")

    # Check for webhook key
    webhook_key = os.getenv("IFTTT_WEBHOOK_KEY")
    if not webhook_key:
        print("\n⚠ WARNING: IFTTT_WEBHOOK_KEY not set in environment")
        print("  Set it in .env file or export IFTTT_WEBHOOK_KEY=your_key")
        print("  Demo will use mock key (requests will fail)")

    try:
        # Run demos
        demo_health_check()
        input("\nPress Enter to continue to next demo...")

        demo_send_alert()
        input("\nPress Enter to continue to next demo...")

        demo_critical_alert_with_health_check()
        input("\nPress Enter to continue to next demo...")

        demo_retry_processing()
        input("\nPress Enter to continue to next demo...")

        demo_statistics()

        print("\n" + "=" * 70)
        print("DEMO COMPLETE")
        print("=" * 70)
        print("\nKey Features Demonstrated:")
        print("  ✓ Health check connectivity verification")
        print("  ✓ Exponential retry with configurable delays")
        print("  ✓ Offline isolation detection (403/404/network errors)")
        print("  ✓ Automatic retry processing")
        print("  ✓ Statistics and monitoring")
        print("  ✓ Obsidian logging for definitive failures")

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
