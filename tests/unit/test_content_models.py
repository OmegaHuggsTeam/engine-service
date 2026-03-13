"""Comprehensive tests for Content Factory Pydantic v2 models.

52 test expectations covering all 12 models:
- Creation, validation, defaults, serialization, edge cases, isolation.
"""

from datetime import datetime, timezone

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
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def _make_research_item(**overrides) -> ResearchItem:
    defaults = dict(
        title="Attention Is All You Need v2",
        source="arxiv",
        url="https://arxiv.org/abs/9999.99999",
        summary="New transformer architecture. Beats GPT-5 on all benchmarks.",
        relevance_score=0.95,
        relevance_reason="Impacta diretamente agentes de conversao",
        category="paper",
    )
    defaults.update(overrides)
    return ResearchItem(**defaults)


def _make_script_section(**overrides) -> ScriptSection:
    defaults = dict(
        type="opening",
        title="Abertura",
        content="Fala pessoal, bem vindos ao Omega Weekly.",
        duration_estimate=15,
    )
    defaults.update(overrides)
    return ScriptSection(**defaults)


def _make_workflow_product(**overrides) -> WorkflowProduct:
    defaults = dict(
        id="omega-weekly-podcast",
        name="Podcast Semanal Omega",
        description="Podcast automatico semanal",
        category="content",
        n8n_workflow_json={"nodes": []},
        cost_per_run=1.08,
    )
    defaults.update(overrides)
    return WorkflowProduct(**defaults)


# ===================================================================
# 1. ResearchItem  (tests 1-6)
# ===================================================================

class TestResearchItem:
    def test_creation_with_all_fields(self):
        """T1: ResearchItem can be created with all required fields."""
        item = _make_research_item()
        assert item.title == "Attention Is All You Need v2"
        assert item.source == "arxiv"
        assert item.url == "https://arxiv.org/abs/9999.99999"
        assert 0 <= item.relevance_score <= 1

    def test_relevance_score_rejects_above_one(self):
        """T2: relevance_score > 1 is rejected."""
        with pytest.raises(ValidationError):
            _make_research_item(relevance_score=1.5)

    def test_relevance_score_rejects_below_zero(self):
        """T3: relevance_score < 0 is rejected."""
        with pytest.raises(ValidationError):
            _make_research_item(relevance_score=-0.1)

    def test_relevance_score_boundary_zero(self):
        """T4: relevance_score=0 is valid."""
        item = _make_research_item(relevance_score=0)
        assert item.relevance_score == 0.0

    def test_relevance_score_boundary_one(self):
        """T5: relevance_score=1 is valid."""
        item = _make_research_item(relevance_score=1)
        assert item.relevance_score == 1.0

    def test_serialization_round_trip(self):
        """T6: model_dump -> model_validate round trip preserves data."""
        item = _make_research_item()
        data = item.model_dump()
        restored = ResearchItem.model_validate(data)
        assert restored == item


# ===================================================================
# 2. ResearchDigest  (tests 7-11)
# ===================================================================

class TestResearchDigest:
    def test_creation_with_items(self):
        """T7: ResearchDigest created with a list of items."""
        item = _make_research_item()
        digest = ResearchDigest(
            items=[item],
            period="2026-03-01 a 2026-03-07",
            total_collected=20,
            sources_status={"arxiv": "ok", "huggingface": "ok"},
        )
        assert len(digest.items) == 1
        assert digest.total_collected == 20

    def test_empty_items_list(self):
        """T8: Digest can be created with empty items list."""
        digest = ResearchDigest(
            items=[],
            period="2026-W10",
            total_collected=0,
            sources_status={},
        )
        assert digest.items == []
        assert digest.total_collected == 0

    def test_sources_status_tracks_errors(self):
        """T9: sources_status can contain error messages."""
        digest = ResearchDigest(
            items=[],
            period="2026-W10",
            total_collected=0,
            sources_status={"arxiv": "ok", "huggingface": "error: timeout"},
        )
        assert digest.sources_status["huggingface"] == "error: timeout"

    def test_multiple_items_preserved(self):
        """T10: Multiple items are preserved in order."""
        items = [
            _make_research_item(title=f"Paper {i}", relevance_score=i * 0.1)
            for i in range(1, 6)
        ]
        digest = ResearchDigest(
            items=items,
            period="2026-W11",
            total_collected=50,
            sources_status={"arxiv": "ok"},
        )
        assert len(digest.items) == 5
        assert digest.items[0].title == "Paper 1"
        assert digest.items[4].title == "Paper 5"

    def test_serialization_round_trip(self):
        """T11: ResearchDigest survives serialization round trip."""
        item = _make_research_item()
        digest = ResearchDigest(
            items=[item],
            period="2026-W10",
            total_collected=1,
            sources_status={"arxiv": "ok"},
        )
        data = digest.model_dump()
        restored = ResearchDigest.model_validate(data)
        assert restored.items[0].title == item.title


# ===================================================================
# 3. ScriptSection  (tests 12-14)
# ===================================================================

class TestScriptSection:
    def test_creation(self):
        """T12: ScriptSection created with required fields."""
        section = _make_script_section()
        assert section.type == "opening"
        assert section.title == "Abertura"
        assert section.duration_estimate == 15

    def test_different_section_types(self):
        """T13: Different section types (opening, block, closing)."""
        for section_type in ("opening", "block", "closing"):
            s = _make_script_section(type=section_type)
            assert s.type == section_type

    def test_serialization_round_trip(self):
        """T14: ScriptSection survives round trip."""
        section = _make_script_section()
        data = section.model_dump()
        restored = ScriptSection.model_validate(data)
        assert restored == section


# ===================================================================
# 4. PodcastScript  (tests 15-19)
# ===================================================================

class TestPodcastScript:
    def test_creation_with_sections(self):
        """T15: PodcastScript created with sections list."""
        section = _make_script_section()
        script = PodcastScript(
            title="Omega Weekly #1",
            episode_number=1,
            duration_estimate=300,
            sections=[section],
            ssml="<speak>Fala pessoal</speak>",
            plain_text="Fala pessoal, bem vindos ao Omega Weekly.",
            metadata={"digest_id": "d-001"},
        )
        assert script.episode_number == 1
        assert len(script.sections) == 1
        assert script.metadata["digest_id"] == "d-001"

    def test_metadata_defaults_to_empty_dict(self):
        """T16: metadata defaults to empty dict when not provided."""
        script = PodcastScript(
            title="T",
            episode_number=1,
            duration_estimate=60,
            sections=[],
            ssml="",
            plain_text="",
        )
        assert script.metadata == {}

    def test_metadata_default_factory_isolation(self):
        """T17: Default metadata dicts are independent across instances."""
        s1 = PodcastScript(
            title="A", episode_number=1, duration_estimate=60,
            sections=[], ssml="", plain_text="",
        )
        s2 = PodcastScript(
            title="B", episode_number=2, duration_estimate=60,
            sections=[], ssml="", plain_text="",
        )
        s1.metadata["key"] = "value"
        assert "key" not in s2.metadata

    def test_empty_sections_allowed(self):
        """T18: Script with empty sections list is valid."""
        script = PodcastScript(
            title="Empty", episode_number=0, duration_estimate=0,
            sections=[], ssml="", plain_text="",
        )
        assert script.sections == []

    def test_serialization_round_trip(self):
        """T19: PodcastScript survives round trip with nested sections."""
        section = _make_script_section()
        script = PodcastScript(
            title="T", episode_number=1, duration_estimate=300,
            sections=[section], ssml="<speak/>", plain_text="text",
        )
        data = script.model_dump()
        restored = PodcastScript.model_validate(data)
        assert len(restored.sections) == 1
        assert restored.sections[0].type == "opening"


# ===================================================================
# 5. AudioAsset  (tests 20-24)
# ===================================================================

class TestAudioAsset:
    def test_creation(self):
        """T20: AudioAsset created with required fields."""
        asset = AudioAsset(
            file_path="/tmp/omega-weekly-1.mp3",
            duration_seconds=300,
            size_bytes=4800000,
            voice_id="EXAVITQu4vr4xnSDxMaL",
            transcript="Fala pessoal...",
            metadata={"episode": 1},
        )
        assert asset.duration_seconds == 300
        assert asset.size_bytes == 4800000
        assert asset.voice_id == "EXAVITQu4vr4xnSDxMaL"

    def test_metadata_defaults_to_empty_dict(self):
        """T21: metadata defaults to empty dict."""
        asset = AudioAsset(
            file_path="/a.mp3", duration_seconds=10,
            size_bytes=1000, voice_id="v1", transcript="t",
        )
        assert asset.metadata == {}

    def test_metadata_isolation(self):
        """T22: Metadata dicts are independent across instances."""
        a1 = AudioAsset(
            file_path="/a.mp3", duration_seconds=10,
            size_bytes=1000, voice_id="v1", transcript="t",
        )
        a2 = AudioAsset(
            file_path="/b.mp3", duration_seconds=20,
            size_bytes=2000, voice_id="v2", transcript="t",
        )
        a1.metadata["x"] = 1
        assert "x" not in a2.metadata

    def test_accepts_float_duration(self):
        """T23: duration_seconds accepts float values."""
        asset = AudioAsset(
            file_path="/a.mp3", duration_seconds=300.5,
            size_bytes=4800000, voice_id="v1", transcript="t",
        )
        assert asset.duration_seconds == 300.5

    def test_serialization_round_trip(self):
        """T24: AudioAsset survives serialization round trip."""
        asset = AudioAsset(
            file_path="/a.mp3", duration_seconds=300,
            size_bytes=4800000, voice_id="v1", transcript="t",
            metadata={"k": "v"},
        )
        data = asset.model_dump()
        restored = AudioAsset.model_validate(data)
        assert restored == asset


# ===================================================================
# 6. ClipAsset  (tests 25-28)
# ===================================================================

class TestClipAsset:
    def test_creation(self):
        """T25: ClipAsset created with required fields."""
        clip = ClipAsset(
            file_path="/tmp/clip-1.mp3",
            title="Momento destaque",
            description="Trecho sobre transformers",
            start_seconds=30,
            end_seconds=90,
            duration_seconds=60,
        )
        assert clip.duration_seconds == 60
        assert clip.start_seconds == 30
        assert clip.end_seconds == 90

    def test_zero_start(self):
        """T26: Clip starting at 0 seconds is valid."""
        clip = ClipAsset(
            file_path="/c.mp3", title="T", description="D",
            start_seconds=0, end_seconds=30, duration_seconds=30,
        )
        assert clip.start_seconds == 0

    def test_accepts_float_timestamps(self):
        """T27: Float timestamps are valid for precise cuts."""
        clip = ClipAsset(
            file_path="/c.mp3", title="T", description="D",
            start_seconds=30.5, end_seconds=90.75, duration_seconds=60.25,
        )
        assert clip.start_seconds == 30.5
        assert clip.end_seconds == 90.75

    def test_serialization_round_trip(self):
        """T28: ClipAsset survives round trip."""
        clip = ClipAsset(
            file_path="/c.mp3", title="T", description="D",
            start_seconds=10, end_seconds=70, duration_seconds=60,
        )
        data = clip.model_dump()
        restored = ClipAsset.model_validate(data)
        assert restored == clip


# ===================================================================
# 7. CarouselSlide  (tests 29-31)
# ===================================================================

class TestCarouselSlide:
    def test_creation_without_cta(self):
        """T29: CarouselSlide without CTA defaults to None."""
        slide = CarouselSlide(
            slide_number=1,
            title="O paper da semana",
            body="Novo transformer bate todos os benchmarks",
        )
        assert slide.slide_number == 1
        assert slide.cta is None

    def test_creation_with_cta(self):
        """T30: CarouselSlide with explicit CTA."""
        slide = CarouselSlide(
            slide_number=7,
            title="CTA",
            body="Conteudo",
            cta="Ouca o podcast completo",
        )
        assert slide.cta == "Ouca o podcast completo"

    def test_serialization_round_trip(self):
        """T31: CarouselSlide survives round trip."""
        slide = CarouselSlide(slide_number=1, title="T", body="B", cta="C")
        data = slide.model_dump()
        restored = CarouselSlide.model_validate(data)
        assert restored == slide


# ===================================================================
# 8. CarouselAsset  (tests 32-34)
# ===================================================================

class TestCarouselAsset:
    def test_creation_with_slides(self):
        """T32: CarouselAsset with a list of slides."""
        slide = CarouselSlide(slide_number=1, title="S1", body="B1")
        asset = CarouselAsset(slides=[slide], topic="Transformer v2", metadata={})
        assert len(asset.slides) == 1
        assert asset.topic == "Transformer v2"

    def test_metadata_defaults_to_empty_dict(self):
        """T33: CarouselAsset metadata defaults to empty dict."""
        asset = CarouselAsset(slides=[], topic="T")
        assert asset.metadata == {}

    def test_multiple_slides_preserved_in_order(self):
        """T34: Multiple slides maintain their order."""
        slides = [
            CarouselSlide(slide_number=i, title=f"S{i}", body=f"B{i}")
            for i in range(1, 8)
        ]
        asset = CarouselAsset(slides=slides, topic="Test")
        assert len(asset.slides) == 7
        assert asset.slides[0].slide_number == 1
        assert asset.slides[6].slide_number == 7


# ===================================================================
# 9. ThreadAsset  (tests 35-37)
# ===================================================================

class TestThreadAsset:
    def test_creation(self):
        """T35: ThreadAsset created with tweets list."""
        asset = ThreadAsset(
            tweets=["Tweet 1: gancho", "Tweet 2: conteudo", "Tweet 3: CTA"],
            topic="AI Weekly",
            metadata={},
        )
        assert len(asset.tweets) == 3

    def test_metadata_defaults_to_empty_dict(self):
        """T36: ThreadAsset metadata defaults to empty dict."""
        asset = ThreadAsset(tweets=["T1"], topic="T")
        assert asset.metadata == {}

    def test_empty_tweets_list(self):
        """T37: ThreadAsset with empty tweets list is valid."""
        asset = ThreadAsset(tweets=[], topic="Empty")
        assert asset.tweets == []


# ===================================================================
# 10. LinkedInAsset  (tests 38-40)
# ===================================================================

class TestLinkedInAsset:
    def test_creation(self):
        """T38: LinkedInAsset created with content and hashtags."""
        asset = LinkedInAsset(
            content="Post LinkedIn aqui",
            hashtags=["#IA", "#Vendas"],
            metadata={},
        )
        assert len(asset.hashtags) == 2
        assert asset.content == "Post LinkedIn aqui"

    def test_metadata_defaults_to_empty_dict(self):
        """T39: LinkedInAsset metadata defaults to empty dict."""
        asset = LinkedInAsset(content="C", hashtags=[])
        assert asset.metadata == {}

    def test_empty_hashtags_list(self):
        """T40: LinkedInAsset with empty hashtags is valid."""
        asset = LinkedInAsset(content="Content", hashtags=[])
        assert asset.hashtags == []


# ===================================================================
# 11. Execution  (tests 41-46)
# ===================================================================

class TestExecution:
    def test_creation(self):
        """T41: Execution created with required fields."""
        ex = Execution(
            id="ex-001",
            workflow_product_id="omega-weekly-podcast",
            status="success",
            outputs={"podcast_url": "https://example.com/ep1.mp3"},
            cost_actual=1.08,
        )
        assert ex.status == "success"
        assert ex.outputs["podcast_url"] == "https://example.com/ep1.mp3"

    def test_started_at_defaults_to_utc_datetime(self):
        """T42: started_at defaults to a timezone-aware UTC datetime."""
        ex = Execution(
            id="ex-002", workflow_product_id="wp-001",
            status="running", cost_actual=0.0,
        )
        assert isinstance(ex.started_at, datetime)
        assert ex.started_at.tzinfo is not None

    def test_completed_at_defaults_to_none(self):
        """T43: completed_at is None by default."""
        ex = Execution(
            id="ex-003", workflow_product_id="wp-001",
            status="running", cost_actual=0.0,
        )
        assert ex.completed_at is None

    def test_with_error(self):
        """T44: Execution can store error message."""
        ex = Execution(
            id="ex-004", workflow_product_id="wp-001",
            status="failed", cost_actual=0.01,
            error="Timeout after 30s",
        )
        assert ex.error == "Timeout after 30s"
        assert ex.status == "failed"

    def test_outputs_defaults_to_empty_dict(self):
        """T45: outputs defaults to empty dict."""
        ex = Execution(
            id="ex-005", workflow_product_id="wp-001",
            status="running", cost_actual=0.0,
        )
        assert ex.outputs == {}

    def test_serialization_round_trip(self):
        """T46: Execution survives serialization round trip."""
        now = datetime(2026, 3, 7, 12, 0, 0, tzinfo=timezone.utc)
        ex = Execution(
            id="ex-006", workflow_product_id="wp-001",
            status="completed", cost_actual=0.10,
            started_at=now, completed_at=now,
            outputs={"key": "val"},
        )
        data = ex.model_dump()
        restored = Execution.model_validate(data)
        assert restored.id == ex.id
        assert restored.completed_at == now


# ===================================================================
# 12. WorkflowProduct  (tests 47-52)
# ===================================================================

class TestWorkflowProduct:
    def test_creation_minimal(self):
        """T47: WorkflowProduct created with minimal required fields."""
        wp = _make_workflow_product()
        assert wp.status == "draft"
        assert wp.category == "content"
        assert wp.schedule is None

    def test_default_lists_are_empty(self):
        """T48: agents_used, webhook_urls, executions default to empty."""
        wp = _make_workflow_product()
        assert wp.agents_used == []
        assert wp.webhook_urls == []
        assert wp.executions == []

    def test_default_lists_isolated(self):
        """T49: Default list factories produce independent instances."""
        wp1 = _make_workflow_product(id="wp-a")
        wp2 = _make_workflow_product(id="wp-b")
        wp1.executions.append("fake")
        wp1.webhook_urls.append("http://x")
        assert "fake" not in wp2.executions
        assert "http://x" not in wp2.webhook_urls

    def test_all_optional_fields(self):
        """T50: WorkflowProduct with all optional fields populated."""
        wp = WorkflowProduct(
            id="wp-full",
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

    def test_created_at_and_updated_at_are_utc_datetimes(self):
        """T51: created_at and updated_at default to timezone-aware UTC."""
        wp = _make_workflow_product()
        assert isinstance(wp.created_at, datetime)
        assert isinstance(wp.updated_at, datetime)
        assert wp.created_at.tzinfo is not None
        assert wp.updated_at.tzinfo is not None

    def test_serialization_round_trip(self):
        """T52: WorkflowProduct survives serialization round trip."""
        wp = _make_workflow_product(
            agents_used=["research", "script"],
            webhook_urls=["https://hook.example.com"],
        )
        data = wp.model_dump()
        restored = WorkflowProduct.model_validate(data)
        assert restored.id == wp.id
        assert restored.agents_used == ["research", "script"]
        assert restored.cost_per_run == wp.cost_per_run
