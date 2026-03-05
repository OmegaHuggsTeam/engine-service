"""
Cost context - Thread-safe context for per-request cost profiling.

Allows llm_client and other modules to record token usage without
explicit parameter passing. The orchestrator sets the profile at
the start of process() and clears at the end.
"""

from contextvars import ContextVar
from typing import Any

_cost_profile: ContextVar[Any] = ContextVar("cost_profile", default=None)


def set_cost_profile(profile: Any) -> None:
    """Set the current request's cost profile (call from orchestrator)."""
    _cost_profile.set(profile)


def get_cost_profile() -> Any:
    """Get the current request's cost profile, or None."""
    return _cost_profile.get()


def clear_cost_profile() -> None:
    """Clear the cost profile (reset to default)."""
    try:
        _cost_profile.set(None)
    except LookupError:
        pass
