"""
Steady Gaze Recon - Sistema de reconhecimento anti-detecção.

Sistema de análise profunda de mecanismos de defesa web em 20 dimensões,
operando como primeira linha de defesa do framework Selum.
"""

from src.steady_gaze.models import (
    AnalysisReport,
    DefenseAnatomyReport,
    FlowStructureReport,
    IdentityPersistenceReport,
    BehaviorTimingReport,
    HoneypotElement,
    ShadowDOMRoot,
    EventListenerInfo,
    IsTrustedValidator,
    WAFDetection,
    SPAFramework,
    StateObject,
    IframeInfo,
    RedirectPattern,
    MonitoringScript,
    APICallInfo,
    CookieInfo,
    StorageAnalysis,
    FingerprintTechnique,
    TLSEvent,
    DOMComplexity,
    IdleDetector,
    HotZone,
    PoWChallenge,
    ActionRecommendation,
)
from src.steady_gaze.recon import SteadyGazeRecon
from src.steady_gaze.cache import AnalysisCache
from src.steady_gaze.cdp_connection import CDPConnection
from src.steady_gaze.exceptions import (
    SteadyGazeError,
    CDPConnectionError,
    AnalysisTimeoutError,
    DimensionAnalysisError,
    PageNotLoadedError,
)

__all__ = [
    # Main classes
    "SteadyGazeRecon",
    "AnalysisCache",
    "CDPConnection",
    # Reports
    "AnalysisReport",
    "DefenseAnatomyReport",
    "FlowStructureReport",
    "IdentityPersistenceReport",
    "BehaviorTimingReport",
    # Data models
    "HoneypotElement",
    "ShadowDOMRoot",
    "EventListenerInfo",
    "IsTrustedValidator",
    "WAFDetection",
    "SPAFramework",
    "StateObject",
    "IframeInfo",
    "RedirectPattern",
    "MonitoringScript",
    "APICallInfo",
    "CookieInfo",
    "StorageAnalysis",
    "FingerprintTechnique",
    "TLSEvent",
    "DOMComplexity",
    "IdleDetector",
    "HotZone",
    "PoWChallenge",
    "ActionRecommendation",
    # Exceptions
    "SteadyGazeError",
    "CDPConnectionError",
    "AnalysisTimeoutError",
    "DimensionAnalysisError",
    "PageNotLoadedError",
]
