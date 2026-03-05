"""
KubectlLogAnalyzer - Retrieves Pod logs via kubectl or Kubernetes API.

Task 6.x: Extract last N lines of log for error analysis.
Fallback to Python client if kubectl unavailable.
"""

import logging
import subprocess
import threading
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_TAIL_LINES = 100
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_CONCURRENT = 5


class KubectlLogAnalyzer:
    """
    Retrieves Pod logs for analysis.
    Uses kubectl with semaphore for concurrency control.
    """

    def __init__(
        self,
        kubeconfig_path: Optional[str] = None,
        tail_lines: int = DEFAULT_TAIL_LINES,
        timeout: int = DEFAULT_TIMEOUT,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    ):
        """
        Initialize KubectlLogAnalyzer.

        Args:
            kubeconfig_path: Path to kubeconfig (None = default/in-cluster)
            tail_lines: Number of log lines to retrieve (default 100)
            timeout: Timeout for kubectl execution in seconds
            max_concurrent: Max concurrent kubectl calls (semaphore)
        """
        self._kubeconfig_path = kubeconfig_path
        self._tail_lines = tail_lines
        self._timeout = timeout
        self._semaphore = threading.Semaphore(max_concurrent)
        self._v1_api = None

    def get_pod_logs(
        self,
        pod_name: str,
        namespace: str = "default",
        tail_lines: Optional[int] = None,
        container: Optional[str] = None,
    ) -> str:
        """
        Retrieve last N lines of Pod logs.

        Args:
            pod_name: Pod name
            namespace: Namespace
            tail_lines: Override default tail lines (default: 100)
            container: Specific container (optional for multi-container pods)

        Returns:
            Log content as string, or empty string on failure
        """
        lines = tail_lines or self._tail_lines

        with self._semaphore:
            try:
                return self._execute_kubectl(pod_name, namespace, lines, container)
            except Exception as e:
                logger.warning("kubectl failed, trying Python client: %s", e)
                return self._get_logs_via_api(pod_name, namespace, lines, container)

    def _execute_kubectl(
        self,
        pod_name: str,
        namespace: str,
        tail_lines: int,
        container: Optional[str],
    ) -> str:
        """Execute kubectl logs with timeout and error handling."""
        cmd = [
            "kubectl",
            "logs",
            pod_name,
            "-n",
            namespace,
            f"--tail={tail_lines}",
        ]
        if container:
            cmd.extend(["-c", container])

        if self._kubeconfig_path:
            cmd.extend(["--kubeconfig", self._kubeconfig_path])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            if result.returncode != 0:
                stderr = result.stderr or ""
                logger.warning("kubectl logs stderr: %s", stderr[:500])
                raise RuntimeError(f"kubectl exited {result.returncode}: {stderr[:200]}")
            return result.stdout or ""
        except subprocess.TimeoutExpired:
            logger.warning("kubectl logs timeout for %s/%s", namespace, pod_name)
            raise
        except FileNotFoundError:
            logger.warning("kubectl not found in PATH")
            raise

    def _get_logs_via_api(
        self,
        pod_name: str,
        namespace: str,
        tail_lines: int,
        container: Optional[str],
    ) -> str:
        """Fallback: get logs via Kubernetes Python client."""
        try:
            from kubernetes import client, config

            if self._v1_api is None:
                if self._kubeconfig_path:
                    config.load_kube_config(config_file=self._kubeconfig_path)
                else:
                    try:
                        config.load_incluster_config()
                    except config.ConfigException:
                        config.load_kube_config()
                self._v1_api = client.CoreV1Api()

            resp = self._v1_api.read_namespaced_pod_log(
                name=pod_name,
                namespace=namespace,
                container=container,
                tail_lines=tail_lines,
            )
            return resp or ""
        except Exception as e:
            logger.error("Kubernetes API log read failed: %s", e)
            return ""
