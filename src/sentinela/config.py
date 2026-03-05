"""
Configuration management for Sentinela Monitor.
"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SentinelaConfig:
    """System configuration for Sentinela Monitor."""
    
    # Neo4j monitoring
    neo4j_log_path: str = ""
    poll_interval: float = 2.0
    
    # Visual detection
    templates_dir: str = "./templates"
    confidence_threshold: float = 0.85
    
    # Jitbit automation
    jitbit_path: str = "C:/Program Files/Jitbit/jitbit.exe"
    macros_dir: str = "./macros"
    
    # Dashboard
    dashboard_url: str = "http://localhost:3000"
    page_load_timeout: float = 30.0
    screenshot_interval: float = 0.5
    
    # Error handling
    max_retries: int = 3
    retry_delay: float = 5.0
    
    # Logging
    log_level: str = "INFO"
    
    @classmethod
    def from_env(cls) -> "SentinelaConfig":
        """Load configuration from environment variables."""
        return cls(
            neo4j_log_path=os.getenv("NEO4J_LOG_PATH", ""),
            poll_interval=float(os.getenv("POLL_INTERVAL", "2.0")),
            templates_dir=os.getenv("TEMPLATES_DIR", "./templates"),
            confidence_threshold=float(os.getenv("CONFIDENCE_THRESHOLD", "0.85")),
            jitbit_path=os.getenv("JITBIT_PATH", "C:/Program Files/Jitbit/jitbit.exe"),
            macros_dir=os.getenv("MACROS_DIR", "./macros"),
            dashboard_url=os.getenv("DASHBOARD_URL", "http://localhost:3000"),
            page_load_timeout=float(os.getenv("PAGE_LOAD_TIMEOUT", "30.0")),
            screenshot_interval=float(os.getenv("SCREENSHOT_INTERVAL", "0.5")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("RETRY_DELAY", "5.0")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
