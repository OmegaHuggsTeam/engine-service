"""
Kubernetes monitoring module for n8n superpower.

This module provides Kubernetes cluster monitoring capabilities including:
- Event monitoring via Kubernetes Watch API
- Pod status detection and failure analysis
- Automatic log retrieval and analysis via SpecialistAgent
- Telegram notifications for cluster events
- Cluster status collection and reporting
"""

from .k8s_event_monitor import K8sEventMonitor
from .manifest_loader import ManifestLoader
from .pod_status_monitor import PodStatusMonitor, PodFailureEvent
from .log_analyzer import KubectlLogAnalyzer

__all__ = [
    "K8sEventMonitor",
    "ManifestLoader",
    "PodStatusMonitor",
    "PodFailureEvent",
    "KubectlLogAnalyzer",
]

__version__ = "1.0.0"
