"""Tests for content factory Pydantic models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.neural_link.agents.content.models import (
    AudioAsset,
    CarouselAsset,
    CarouselSlide,
    ClipAsset,
    Execution,
    LinkedInAsset,
    PodcastScript,
    ResearchDigest,
    ResearchItem,
    ScriptSection,
    ThreadAsset,
    WorkflowProduct,
)


# ---------------------------------------------------------------------------
# ResearchItem
# ---------------------------------------------------------------------------


class TestResearchItem:
    def test_valid_research_item(self):
        item = ResearchItem(
            title="AI Trends 2026",
            source="TechCrunch",
            url="https://techcrunch.com/ai-trends",
            summary="Overview of emerging AI trends.",
            relevance_score=0.85,
            relevance_reason="Directly related to our podcast topic.",
            category="technology",
        )
        assert item.title == "AI Trends 2026"
        assert item.source == "TechCrunch"
        assert item.url == "https://techcrunch.com/ai-trends"
        assert item.relevance_score == 0.85
        assert item.category == "technology"

    def test_relevance_score_bounds(self):
        """relevance_score must be between 0 and 1 inclusive."""
        with pytest.raises(ValidationError):
            ResearchItem(
                title="Bad",
                source="x",
                url="http://x.com",
                summary="s",
                relevance_score=1.5,
                relevance_reason="r",
                category="c",
            )
        with pytest.raises(ValidationError):
            ResearchItem(
                title="Bad",
                source="x",
                url="http://x.com",
                summary="s",
                relevance_score=-0.1,
                relevance_reason="r",
                category="c",
            )

    def test_relevance_score_edge_values(self):
        """0 and 1 are valid boundary values."""
        item_zero = ResearchItem(
            title="T",
            source="S",
            url="http://x.com",
            summary="s",
            relevance_score=0,
            relevance_reason="r",
            category="c",
        )
        item_one = ResearchItem(
            title="T",
            source="S",
            url="http://x.com",
            summary="s",
            relevance_score=1,
            relevance_reason="r",
            category="c",
        )
        assert item_zero.relevance_score == 0.0
        assert item_one.relevance_score == 1.0


# ---------------------------------------------------------------------------
# ResearchDigest
# ---------------------------------------------------------------------------


class TestResearchDigest:
    def test_valid_digest(self):
        item = ResearchItem(
            title="T",
            source="S",
            url="http://x.com",
            summary="s",
            relevance_score=0.5,
            relevance_reason="r",
            category="c",
        )
        digest = ResearchDigest(
            items=[item],
            period="2026-W10",
            total_collected=42,
            sources_status={"TechCrunch": "ok"},
        )
        assert len(digest.items) == 1
        assert digest.period == "2026-W10"
        assert digest.total_collected == 42
        assert digest.sources_status == {"TechCrunch": "ok"}

    def test_empty_items_list(self):
        digest = ResearchDigest(
            items=[],
            period="2026-W10",
            total_collected=0,
            sources_status={},
        )
        assert digest.items == []


# ---------------------------------------------------------------------------
# ScriptSection
# ---------------------------------------------------------------------------


class TestScriptSection:
    def test_valid_section(self):
        section = ScriptSection(
            type="intro",
            title="Welcome",
            content="Hello and welcome to the show.",
            duration_estimate=30.0,
        )
        assert section.type == "intro"
        assert section.title == "Welcome"
        assert section.duration_estimate == 30.0


# ---------------------------------------------------------------------------
# PodcastScript
# ---------------------------------------------------------------------------


class TestPodcastScript:
    def test_valid_script(self):
        section = ScriptSection(
            type="intro",
            title="Intro",
            content="Welcome!",
            duration_estimate=15.0,
        )
        script = PodcastScript(
            title="Episode 1: AI Basics",
            episode_number=1,
            duration_estimate=600.0,
            sections=[section],
            ssml="<speak>Welcome!</speak>",
            plain_text="Welcome!",
        )
        assert script.title == "Episode 1: AI Basics"
        assert script.episode_number == 1
        assert len(script.sections) == 1
        assert script.metadata == {}

    def test_metadata_default_factory(self):
        """metadata should default to empty dict, not shared reference."""
        s1 = PodcastScript(
            title="A",
            episode_number=1,
            duration_estimate=60.0,
            sections=[],
            ssml="",
            plain_text="",
        )
        s2 = PodcastScript(
            title="B",
            episode_number=2,
            duration_estimate=60.0,
            sections=[],
            ssml="",
            plain_text="",
        )
        s1.metadata["key"] = "value"
        assert "key" not in s2.metadata


# ---------------------------------------------------------------------------
# AudioAsset
# ---------------------------------------------------------------------------


class TestAudioAsset:
    def test_valid_audio_asset(self):
        asset = AudioAsset(
            file_path="/audio/ep1.mp3",
            duration_seconds=600.5,
            size_bytes=12_000_000,
            voice_id="voice-123",
            transcript="Full transcript here.",
        )
        assert asset.file_path == "/audio/ep1.mp3"
        assert asset.duration_seconds == 600.5
        assert asset.size_bytes == 12_000_000
        assert asset.voice_id == "voice-123"
        assert asset.metadata == {}

    def test_metadata_isolation(self):
        a1 = AudioAsset(
            file_path="/a.mp3",
            duration_seconds=10.0,
            size_bytes=1000,
            voice_id="v1",
            transcript="t",
        )
        a2 = AudioAsset(
            file_path="/b.mp3",
            duration_seconds=20.0,
            size_bytes=2000,
            voice_id="v2",
            transcript="t",
        )
        a1.metadata["x"] = 1
        assert "x" not in a2.metadata


# ---------------------------------------------------------------------------
# ClipAsset
# ---------------------------------------------------------------------------


class TestClipAsset:
    def test_valid_clip(self):
        clip = ClipAsset(
            file_path="/clips/clip1.mp4",
            title="Best moment",
            description="The highlight of the episode.",
            start_seconds=120.0,
            end_seconds=180.0,
            duration_seconds=60.0,
        )
        assert clip.file_path == "/clips/clip1.mp4"
        assert clip.start_seconds == 120.0
        assert clip.end_seconds == 180.0
        assert clip.duration_seconds == 60.0


# ---------------------------------------------------------------------------
# CarouselSlide & CarouselAsset
# ---------------------------------------------------------------------------


class TestCarouselSlide:
    def test_valid_slide(self):
        slide = CarouselSlide(
            slide_number=1,
            title="Slide 1",
            body="Content of slide 1.",
        )
        assert slide.slide_number == 1
        assert slide.cta is None

    def test_slide_with_cta(self):
        slide = CarouselSlide(
            slide_number=2,
            title="Slide 2",
            body="Content.",
            cta="Learn more at huggsai.com",
        )
        assert slide.cta == "Learn more at huggsai.com"


class TestCarouselAsset:
    def test_valid_carousel(self):
        slides = [
            CarouselSlide(slide_number=1, title="S1", body="B1"),
            CarouselSlide(slide_number=2, title="S2", body="B2"),
        ]
        carousel = CarouselAsset(
            slides=slides,
            topic="AI Automation",
        )
        assert len(carousel.slides) == 2
        assert carousel.topic == "AI Automation"
        assert carousel.metadata == {}


# ---------------------------------------------------------------------------
# ThreadAsset
# ---------------------------------------------------------------------------


class TestThreadAsset:
    def test_valid_thread(self):
        thread = ThreadAsset(
            tweets=["Tweet 1", "Tweet 2", "Tweet 3"],
            topic="AI Content",
        )
        assert len(thread.tweets) == 3
        assert thread.topic == "AI Content"
        assert thread.metadata == {}


# ---------------------------------------------------------------------------
# LinkedInAsset
# ---------------------------------------------------------------------------


class TestLinkedInAsset:
    def test_valid_linkedin(self):
        post = LinkedInAsset(
            content="Great insights on AI automation...",
            hashtags=["#AI", "#Automation"],
        )
        assert post.content.startswith("Great")
        assert len(post.hashtags) == 2
        assert post.metadata == {}


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


class TestExecution:
    def test_valid_execution(self):
        execution = Execution(
            id="exec-001",
            workflow_product_id="wp-001",
            status="running",
            cost_actual=0.05,
        )
        assert execution.id == "exec-001"
        assert execution.workflow_product_id == "wp-001"
        assert execution.status == "running"
        assert isinstance(execution.started_at, datetime)
        assert execution.completed_at is None
        assert execution.outputs == {}
        assert execution.error is None

    def test_execution_with_error(self):
        execution = Execution(
            id="exec-002",
            workflow_product_id="wp-001",
            status="failed",
            cost_actual=0.01,
            error="Timeout after 30s",
        )
        assert execution.error == "Timeout after 30s"
        assert execution.status == "failed"

    def test_execution_completed(self):
        now = datetime(2026, 3, 7, 12, 0, 0)
        execution = Execution(
            id="exec-003",
            workflow_product_id="wp-001",
            status="completed",
            cost_actual=0.10,
            completed_at=now,
            outputs={"audio_url": "/audio/ep1.mp3"},
        )
        assert execution.completed_at == now
        assert execution.outputs["audio_url"] == "/audio/ep1.mp3"


# ---------------------------------------------------------------------------
# WorkflowProduct
# ---------------------------------------------------------------------------


class TestWorkflowProduct:
    def test_valid_workflow_product(self):
        wp = WorkflowProduct(
            id="wp-001",
            name="Weekly Podcast",
            description="Automated weekly podcast pipeline.",
            category="podcast",
            n8n_workflow_json={"nodes": []},
            config={"voice": "alloy"},
            agents_used=["researcher", "scriptwriter"],
            cost_per_run=0.50,
        )
        assert wp.id == "wp-001"
        assert wp.name == "Weekly Podcast"
        assert wp.status == "draft"
        assert wp.schedule is None
        assert wp.created_from_template is None
        assert wp.brand_voice_file is None
        assert wp.executions == []
        assert wp.webhook_urls == []
        assert isinstance(wp.created_at, datetime)
        assert isinstance(wp.updated_at, datetime)

    def test_workflow_product_default_lists_isolated(self):
        """Default list factories must not share references."""
        wp1 = WorkflowProduct(
            id="wp-a",
            name="A",
            description="d",
            category="c",
            n8n_workflow_json={},
            config={},
            agents_used=[],
            cost_per_run=0.0,
        )
        wp2 = WorkflowProduct(
            id="wp-b",
            name="B",
            description="d",
            category="c",
            n8n_workflow_json={},
            config={},
            agents_used=[],
            cost_per_run=0.0,
        )
        wp1.executions.append("fake")
        assert "fake" not in wp2.executions
        wp1.webhook_urls.append("http://x")
        assert "http://x" not in wp2.webhook_urls

    def test_workflow_product_with_all_optional_fields(self):
        wp = WorkflowProduct(
            id="wp-003",
            name="Full Product",
            description="All fields set.",
            category="carousel",
            n8n_workflow_json={"nodes": [{"id": 1}]},
            config={"theme": "dark"},
            schedule="0 9 * * MON",
            agents_used=["designer"],
            webhook_urls=["https://hook.example.com/1"],
            status="active",
            created_from_template="tmpl-carousel-v1",
            brand_voice_file="/voices/brand.json",
            cost_per_run=0.25,
        )
        assert wp.schedule == "0 9 * * MON"
        assert wp.status == "active"
        assert wp.created_from_template == "tmpl-carousel-v1"
        assert wp.brand_voice_file == "/voices/brand.json"
        assert len(wp.webhook_urls) == 1
