# Kubernetes Monitoring for n8n Superpower

This module provides Kubernetes cluster monitoring capabilities including:
- Event monitoring via Kubernetes Watch API
- Pod status detection and failure analysis
- Automatic log retrieval and analysis via SpecialistAgent
- Telegram notifications for cluster events
- Cluster status collection and reporting

## Quick Start

### Running as a Script

```bash
# Set required environment variables
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export KUBECONFIG="/path/to/kubeconfig"  # Optional, uses in-cluster config if not set

# Run the monitoring system
python -m src.neural_link.k8s_monitoring.wire_monitoring
```

### Using as a Module

```python
from src.neural_link.k8s_monitoring.wire_monitoring import wire_and_start

# Start monitoring with default configuration
k8s_monitor, pod_monitor = wire_and_start(
    manifest_path="superpowers/n8n/manifest.json",
    kubeconfig_path="/path/to/kubeconfig",
    bot_token="your_bot_token",
    default_chat_id=12345,
)

# Keep running...
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    k8s_monitor.stop()
```

## Configuration

### Environment Variables

**Required:**
- `TELEGRAM_BOT_TOKEN`: Telegram bot authentication token

**Optional:**
- `KUBECONFIG`: Path to kubeconfig file (defaults to in-cluster config or ~/.kube/config)
- `K8S_MANIFEST_PATH`: Path to manifest.json (default: `superpowers/n8n/manifest.json`)
- `TELEGRAM_DEFAULT_CHAT_ID`: Default chat ID for notifications
- `LOG_LEVEL`: Logging level (default: `INFO`)

### Manifest Configuration

The manifest.json file defines hooks and commands for the monitoring system:

```json
{
  "name": "n8n-kubernetes-monitoring",
  "version": "2.0.0",
  "hooks": {
    "on_k8s_event": [
      {
        "resource_type": "Pod",
        "namespace": "*",
        "event_types": ["MODIFIED"],
        "filters": {
          "status.phase": "Failed",
          "status.containerStatuses[*].state.waiting.reason": "CrashLoopBackOff"
        },
        "handler": "handle_pod_crash"
      }
    ]
  },
  "commands": {
    "/cluster_status": {
      "handler": "handle_cluster_status",
      "description": "Display cluster health and service status"
    }
  }
}
```

## Architecture

### Components

1. **ManifestLoader**: Loads and validates configuration from manifest.json
2. **K8sEventMonitor**: Watches Kubernetes events using the Watch API
3. **PodStatusMonitor**: Detects Pod failures (CrashLoopBackOff, etc.)
4. **KubectlLogAnalyzer**: Retrieves Pod logs for analysis
5. **SpecialistAgent**: Analyzes logs and identifies root causes
6. **TelegramNotifier**: Sends alerts and status updates to Telegram

### Event Flow

```
Kubernetes API → K8sEventMonitor → PodStatusMonitor → KubectlLogAnalyzer
                                                              ↓
                                                       SpecialistAgent
                                                              ↓
                                                      TelegramNotifier
```

## Features

### Automatic Pod Failure Detection

When a Pod enters CrashLoopBackOff state:
1. The system detects the failure within 10 seconds
2. Retrieves the last 100 lines of logs
3. Analyzes logs using SpecialistAgent with k8s_error_patterns knowledge
4. Sends a formatted alert to Telegram with:
   - Pod name, namespace, container
   - Failure reason and restart count
   - Root cause analysis
   - Suggested fix
   - Recent logs

### Graceful Shutdown

The system handles SIGINT and SIGTERM signals gracefully:
- Stops the K8sEventMonitor
- Processes any queued Telegram messages
- Closes all connections cleanly

## Deployment

### Kubernetes Deployment

See the deployment manifests in the design document for:
- ServiceAccount and RBAC configuration
- Deployment manifest with resource limits
- Secret for Telegram bot token

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export TELEGRAM_BOT_TOKEN="your_token"
export KUBECONFIG="~/.kube/config"
export LOG_LEVEL="DEBUG"

# Run the monitoring system
python -m src.neural_link.k8s_monitoring.wire_monitoring
```

## Testing

```bash
# Run unit tests
pytest tests/unit/test_wire_monitoring.py -v

# Run all k8s monitoring tests
pytest tests/unit/test_manifest_loader.py -v
pytest tests/unit/test_k8s_event_monitor.py -v
pytest tests/unit/test_pod_status_monitor.py -v
pytest tests/unit/test_telegram_notifier.py -v
```

## Troubleshooting

### Connection Issues

If the system can't connect to Kubernetes:
- Check KUBECONFIG path is correct
- Verify kubectl can connect: `kubectl get pods`
- Check ServiceAccount permissions if running in-cluster

### No Notifications

If Telegram notifications aren't working:
- Verify TELEGRAM_BOT_TOKEN is set correctly
- Check bot has permission to send messages to the chat
- Review logs for Telegram API errors

### Missing Dependencies

If SpecialistAgent or TelegramNotifier are unavailable:
- The system will log warnings but continue running
- Pod failures will still be detected
- Notifications will be queued if Telegram is temporarily unavailable

## License

Part of the Neural Link project.
