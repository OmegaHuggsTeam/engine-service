"""
Wire Monitoring - Main application entry point for n8n-k8s-monitoring.

This module wires together all components:
- ManifestLoader: Loads and validates configuration
- K8sEventMonitor: Watches Kubernetes events
- PodStatusMonitor: Detects Pod failures
- KubectlLogAnalyzer: Retrieves Pod logs
- SpecialistAgent: Analyzes logs and identifies root causes
- TelegramNotifier: Sends alerts and status updates

Uso:
    # As a module
    from src.neural_link.k8s_monitoring.wire_monitoring import wire_and_start
    monitor, pod_monitor = wire_and_start(manifest_path="superpowers/n8n/manifest.json")
    
    # As a script
    python -m src.neural_link.k8s_monitoring.wire_monitoring
"""

import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Optional

from .manifest_loader import ManifestLoader
from .k8s_event_monitor import K8sEventMonitor
from .pod_status_monitor import PodStatusMonitor
from .log_analyzer import KubectlLogAnalyzer
from . import __version__

logger = logging.getLogger(__name__)

# Global references for graceful shutdown
_k8s_monitor: Optional[K8sEventMonitor] = None
_pod_monitor: Optional[PodStatusMonitor] = None
_notifier = None


def wire_and_start(
    manifest_path: str = "superpowers/n8n/manifest.json",
    kubeconfig_path: Optional[str] = None,
    bot_token: Optional[str] = None,
    default_chat_id: Optional[int] = None,
) -> tuple[K8sEventMonitor, PodStatusMonitor]:
    """
    Carrega manifest, cria componentes e conecta o pipeline:
    K8sEventMonitor -> PodStatusMonitor -> LogAnalyzer -> SpecialistAgent -> TelegramNotifier

    Args:
        manifest_path: Path to manifest.json configuration file
        kubeconfig_path: Path to kubeconfig (None = in-cluster or default)
        bot_token: Telegram bot token (None = read from env TELEGRAM_BOT_TOKEN)
        default_chat_id: Default Telegram chat ID for notifications

    Returns:
        (K8sEventMonitor, PodStatusMonitor) for start/stop control
    """
    global _k8s_monitor, _pod_monitor, _notifier
    
    logger.info("Starting n8n-k8s-monitoring v%s", __version__)
    
    # Load and validate manifest
    loader = ManifestLoader()
    manifest = loader.load_manifest(manifest_path)
    loader.validate_hooks(manifest)
    hooks = loader.get_k8s_hooks(manifest)
    logger.info("Loaded %d hooks from manifest", len(hooks))

    # Initialize KubectlLogAnalyzer
    log_analyzer = KubectlLogAnalyzer(
        kubeconfig_path=kubeconfig_path,
        tail_lines=100,
    )
    logger.info("Initialized KubectlLogAnalyzer")

    # Initialize SpecialistAgent for log analysis
    specialist = None
    try:
        from src.neural_link.agents.specialist_agent import SpecialistAgent
        specialist = SpecialistAgent()
        specialist.load_knowledge("k8s_error_patterns")
        logger.info("Initialized SpecialistAgent with k8s_error_patterns knowledge")
    except Exception as e:
        logger.warning("SpecialistAgent not available: %s", e)

    # Initialize TelegramNotifier
    notifier = None
    try:
        # Get bot token from parameter or environment
        token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            logger.warning("TELEGRAM_BOT_TOKEN not provided, notifications disabled")
        else:
            from .telegram_notifier import TelegramNotifier
            notifier = TelegramNotifier(
                bot_token=token,
                default_chat_id=default_chat_id,
            )
            _notifier = notifier
            logger.info("Initialized TelegramNotifier")
    except Exception as e:
        logger.warning("TelegramNotifier not available: %s", e)

    # Initialize PodStatusMonitor
    pod_monitor = PodStatusMonitor(
        log_analyzer=log_analyzer,
        specialist_agent=specialist,
        notifier=notifier,
    )
    _pod_monitor = pod_monitor
    logger.info("Initialized PodStatusMonitor")

    # Initialize K8sEventMonitor
    k8s_monitor = K8sEventMonitor(kubeconfig_path=kubeconfig_path)
    k8s_monitor.register_hooks(hooks)
    _k8s_monitor = k8s_monitor

    # Register handler: handle_pod_crash -> PodStatusMonitor.handle_pod_event
    for hook in hooks:
        handler_name = hook.get("handler")
        if handler_name == "handle_pod_crash":
            k8s_monitor.register_handler(handler_name, pod_monitor.handle_pod_event)
            logger.info("Registered handle_pod_crash -> PodStatusMonitor.handle_pod_event")
            break

    # Start monitoring
    k8s_monitor.start()
    logger.info("K8s monitoring started successfully (v%s)", __version__)
    
    return k8s_monitor, pod_monitor



def validate_configuration() -> tuple[bool, list[str]]:
    """
    Validate required environment variables and configuration.
    
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    # Check for Telegram bot token
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        errors.append("TELEGRAM_BOT_TOKEN environment variable not set")
    
    # Check for kubeconfig (optional, can use in-cluster config)
    kubeconfig_path = os.environ.get("KUBECONFIG")
    if kubeconfig_path and not Path(kubeconfig_path).exists():
        errors.append(f"KUBECONFIG file not found: {kubeconfig_path}")
    
    # Check for manifest file
    manifest_path = os.environ.get("K8S_MANIFEST_PATH", "superpowers/n8n/manifest.json")
    if not Path(manifest_path).exists():
        errors.append(f"Manifest file not found: {manifest_path}")
    
    return len(errors) == 0, errors


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info("Received signal %d, initiating graceful shutdown...", signum)
        shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("Signal handlers registered for graceful shutdown")


def shutdown() -> None:
    """Gracefully shutdown all components."""
    global _k8s_monitor, _pod_monitor, _notifier
    
    logger.info("Shutting down n8n-k8s-monitoring...")
    
    # Stop K8sEventMonitor
    if _k8s_monitor:
        try:
            _k8s_monitor.stop()
            logger.info("K8sEventMonitor stopped")
        except Exception as e:
            logger.error("Error stopping K8sEventMonitor: %s", e)
    
    # Process any remaining queued messages
    if _notifier and hasattr(_notifier, "process_queue"):
        try:
            sent = _notifier.process_queue()
            logger.info("Processed %d queued messages before shutdown", sent)
        except Exception as e:
            logger.error("Error processing message queue: %s", e)
    
    logger.info("Shutdown complete")


def main() -> int:
    """
    Main entry point for n8n-k8s-monitoring application.
    
    Reads configuration from environment variables:
    - TELEGRAM_BOT_TOKEN (required): Telegram bot authentication token
    - KUBECONFIG (optional): Path to kubeconfig file
    - K8S_MANIFEST_PATH (optional): Path to manifest.json (default: superpowers/n8n/manifest.json)
    - TELEGRAM_DEFAULT_CHAT_ID (optional): Default chat ID for notifications
    - LOG_LEVEL (optional): Logging level (default: INFO)
    
    Returns:
        Exit code (0 = success, 1 = error)
    """
    # Configure logging
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger.info("=" * 60)
    logger.info("n8n-k8s-monitoring v%s", __version__)
    logger.info("=" * 60)
    
    # Validate configuration
    is_valid, errors = validate_configuration()
    if not is_valid:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error("  - %s", error)
        logger.error("Please set required environment variables and try again")
        return 1
    
    logger.info("Configuration validation passed")
    
    # Setup signal handlers for graceful shutdown
    setup_signal_handlers()
    
    # Get configuration from environment
    manifest_path = os.environ.get("K8S_MANIFEST_PATH", "superpowers/n8n/manifest.json")
    kubeconfig_path = os.environ.get("KUBECONFIG")
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    default_chat_id_str = os.environ.get("TELEGRAM_DEFAULT_CHAT_ID")
    default_chat_id = int(default_chat_id_str) if default_chat_id_str else None
    
    logger.info("Configuration:")
    logger.info("  Manifest: %s", manifest_path)
    logger.info("  Kubeconfig: %s", kubeconfig_path or "in-cluster/default")
    logger.info("  Default Chat ID: %s", default_chat_id or "not set")
    logger.info("  Log Level: %s", log_level)
    
    try:
        # Wire and start all components
        k8s_monitor, pod_monitor = wire_and_start(
            manifest_path=manifest_path,
            kubeconfig_path=kubeconfig_path,
            bot_token=bot_token,
            default_chat_id=default_chat_id,
        )
        
        logger.info("=" * 60)
        logger.info("n8n-k8s-monitoring is running")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        shutdown()
        return 0
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        shutdown()
        return 1


if __name__ == "__main__":
    sys.exit(main())
