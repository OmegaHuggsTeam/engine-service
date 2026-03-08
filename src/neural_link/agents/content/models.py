"""Pydantic v2 data models for the Omega Content Factory pipeline.

Covers research ingestion, script generation, audio/video assets,
social media outputs, workflow execution tracking, and product definitions.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------


class ResearchItem(BaseModel):
    """A single research finding collected by the researcher agent."""

    title: str
    source: str
    url: str
    summary: str
    relevance_score: float = Field(ge=0, le=1)
    relevance_reason: str
    category: str


class ResearchDigest(BaseModel):
    """Aggregated research output for a given period."""

    items: list[ResearchItem]
    period: str
    total_collected: int
    sources_status: dict[str, str]


# ---------------------------------------------------------------------------
# Script
# ---------------------------------------------------------------------------


class ScriptSection(BaseModel):
    """One section of a podcast script (intro, segment, outro, etc.)."""

    type: str
    title: str
    content: str
    duration_estimate: float


class PodcastScript(BaseModel):
    """Complete podcast script ready for TTS rendering."""

    title: str
    episode_number: int
    duration_estimate: float
    sections: list[ScriptSection]
    ssml: str
    plain_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Audio & Video Assets
# ---------------------------------------------------------------------------


class AudioAsset(BaseModel):
    """Generated audio file with metadata."""

    file_path: str
    duration_seconds: float
    size_bytes: int
    voice_id: str
    transcript: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClipAsset(BaseModel):
    """A clip extracted from a longer audio/video asset."""

    file_path: str
    title: str
    description: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float


# ---------------------------------------------------------------------------
# Social Media Assets
# ---------------------------------------------------------------------------


class CarouselSlide(BaseModel):
    """One slide in an Instagram/LinkedIn carousel."""

    slide_number: int
    title: str
    body: str
    cta: Optional[str] = None


class CarouselAsset(BaseModel):
    """Complete carousel post asset."""

    slides: list[CarouselSlide]
    topic: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ThreadAsset(BaseModel):
    """Twitter/X thread asset."""

    tweets: list[str]
    topic: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class LinkedInAsset(BaseModel):
    """LinkedIn post asset."""

    content: str
    hashtags: list[str]
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Execution Tracking
# ---------------------------------------------------------------------------


class Execution(BaseModel):
    """Record of a single workflow product execution."""

    id: str
    workflow_product_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str
    outputs: dict[str, Any] = Field(default_factory=dict)
    cost_actual: float
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Workflow Product
# ---------------------------------------------------------------------------


class WorkflowProduct(BaseModel):
    """A reusable content production workflow (the core entity)."""

    id: str
    name: str
    description: str
    category: str
    n8n_workflow_json: dict[str, Any]
    config: dict[str, Any]
    schedule: Optional[str] = None
    agents_used: list[str]
    webhook_urls: list[str] = Field(default_factory=list)
    status: str = "draft"
    created_from_template: Optional[str] = None
    brand_voice_file: Optional[str] = None
    executions: list[Any] = Field(default_factory=list)
    cost_per_run: float
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
