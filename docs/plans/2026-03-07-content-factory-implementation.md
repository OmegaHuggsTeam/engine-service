# Omega Content Factory — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build 8 content agents + workflow registry API that power the Omega Weekly Podcast — a fully automated pipeline from research to multi-platform publishing.

**Architecture:** New `content/` agent family inside Neural Link, following existing `BaseAgent` contract. Workflow Registry exposes CRUD REST API on Sovereign Gateway (8766). n8n orchestrates agent execution via HTTP webhooks. Brand voice stored in RAG knowledge vault.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, httpx, feedparser (Arxiv), ElevenLabs SDK, pydub (audio), pytest

**Design doc:** `docs/plans/2026-03-07-content-factory-workflow-products-design.md`

---

## Task 1: Content Models (data contracts)

**Files:**
- Create: `src/neural_link/agents/content/__init__.py`
- Create: `src/neural_link/agents/content/models.py`
- Test: `tests/content/test_models.py`

**Step 1: Write failing test**

```python
# tests/content/test_models.py
import pytest
from datetime import datetime


def test_research_item_creation():
    from src.neural_link.agents.content.models import ResearchItem

    item = ResearchItem(
        title="Attention Is All You Need v2",
        source="arxiv",
        url="https://arxiv.org/abs/9999.99999",
        summary="New transformer architecture. Beats GPT-5 on all benchmarks.",
        relevance_score=0.95,
        relevance_reason="Impacta diretamente agentes de conversao",
        category="paper",
    )
    assert item.title == "Attention Is All You Need v2"
    assert item.source == "arxiv"
    assert 0 <= item.relevance_score <= 1


def test_research_digest_creation():
    from src.neural_link.agents.content.models import ResearchDigest, ResearchItem

    item = ResearchItem(
        title="Test Paper",
        source="arxiv",
        url="https://example.com",
        summary="Test summary.",
        relevance_score=0.8,
        relevance_reason="Relevante",
        category="paper",
    )
    digest = ResearchDigest(
        items=[item],
        period="2026-03-01 a 2026-03-07",
        total_collected=20,
        sources_status={"arxiv": "ok", "huggingface": "ok"},
    )
    assert len(digest.items) == 1
    assert digest.total_collected == 20


def test_podcast_script_creation():
    from src.neural_link.agents.content.models import PodcastScript, ScriptSection

    section = ScriptSection(
        type="opening",
        title="Abertura",
        content="Fala pessoal, bem vindos ao Omega Weekly.",
        duration_estimate=15,
    )
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


def test_audio_asset_creation():
    from src.neural_link.agents.content.models import AudioAsset

    asset = AudioAsset(
        file_path="/tmp/omega-weekly-1.mp3",
        duration_seconds=300,
        size_bytes=4800000,
        voice_id="EXAVITQu4vr4xnSDxMaL",
        transcript="Fala pessoal...",
        metadata={"episode": 1},
    )
    assert asset.duration_seconds == 300


def test_carousel_asset_creation():
    from src.neural_link.agents.content.models import CarouselAsset, CarouselSlide

    slide = CarouselSlide(
        slide_number=1,
        title="O paper da semana",
        body="Novo transformer bate todos os benchmarks",
        cta=None,
    )
    asset = CarouselAsset(
        slides=[slide],
        topic="Transformer v2",
        metadata={},
    )
    assert len(asset.slides) == 1


def test_thread_asset_creation():
    from src.neural_link.agents.content.models import ThreadAsset

    asset = ThreadAsset(
        tweets=["Tweet 1: gancho", "Tweet 2: conteudo", "Tweet 3: CTA"],
        topic="AI Weekly",
        metadata={},
    )
    assert len(asset.tweets) == 3


def test_linkedin_asset_creation():
    from src.neural_link.agents.content.models import LinkedInAsset

    asset = LinkedInAsset(
        content="Post LinkedIn aqui",
        hashtags=["#IA", "#Vendas"],
        metadata={},
    )
    assert len(asset.hashtags) == 2


def test_clip_asset_creation():
    from src.neural_link.agents.content.models import ClipAsset

    clip = ClipAsset(
        file_path="/tmp/clip-1.mp3",
        title="Momento destaque",
        description="Trecho sobre transformers",
        start_seconds=30,
        end_seconds=90,
        duration_seconds=60,
    )
    assert clip.duration_seconds == 60


def test_workflow_product_creation():
    from src.neural_link.agents.content.models import WorkflowProduct

    wp = WorkflowProduct(
        id="omega-weekly-podcast",
        name="Podcast Semanal Omega",
        description="Podcast automatico semanal",
        category="content",
        n8n_workflow_json={"nodes": []},
        config={"sources": "all"},
        schedule="0 6 * * 5",
        agents_used=["research", "script", "audio"],
        webhook_urls=[],
        status="draft",
    )
    assert wp.status == "draft"
    assert wp.category == "content"


def test_execution_creation():
    from src.neural_link.agents.content.models import Execution

    ex = Execution(
        id="ex-001",
        workflow_product_id="omega-weekly-podcast",
        status="success",
        outputs={"podcast_url": "https://example.com/ep1.mp3"},
        cost_actual=1.08,
    )
    assert ex.status == "success"
```

**Step 2: Run test to verify it fails**

Run: `cd C:\labs\inteligence\chunk-generator && python -m pytest tests/content/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.neural_link.agents.content'`

**Step 3: Write implementation**

```python
# src/neural_link/agents/content/__init__.py
"""Omega Content Factory — agent family for automated content production."""

# src/neural_link/agents/content/models.py
"""Data models for the Content Factory pipeline.

All models use Pydantic BaseModel for validation and serialization.
These flow through agents: ResearchDigest → PodcastScript → AudioAsset → derivatives.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# --- Research Stage ---

class ResearchItem(BaseModel):
    """Single research finding from any source."""
    title: str
    source: str  # "arxiv" | "huggingface" | "github" | "producthunt"
    url: str
    summary: str  # 2 sentences max
    relevance_score: float = Field(ge=0, le=1)
    relevance_reason: str  # Why it matters for Omega audience
    category: str  # "paper" | "model" | "tool" | "product"


class ResearchDigest(BaseModel):
    """Weekly research collection, ranked by relevance."""
    items: list[ResearchItem]
    period: str  # "2026-03-01 a 2026-03-07"
    total_collected: int
    sources_status: dict[str, str]  # {"arxiv": "ok", "hf": "error: timeout"}


# --- Script Stage ---

class ScriptSection(BaseModel):
    """One section of the podcast script."""
    type: str  # "opening" | "block" | "closing"
    title: str
    content: str  # Plain text with [...] pauses and **emphasis**
    duration_estimate: int  # seconds


class PodcastScript(BaseModel):
    """Complete podcast script ready for TTS."""
    title: str  # "Omega Weekly #12: O paper que muda tudo"
    episode_number: int
    duration_estimate: int  # total seconds
    sections: list[ScriptSection]
    ssml: str  # SSML-tagged version for TTS
    plain_text: str  # Clean version without markup
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- Audio Stage ---

class AudioAsset(BaseModel):
    """Generated audio file with metadata."""
    file_path: str
    duration_seconds: int
    size_bytes: int
    voice_id: str
    transcript: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClipAsset(BaseModel):
    """Short clip extracted from full podcast."""
    file_path: str
    title: str
    description: str
    start_seconds: int
    end_seconds: int
    duration_seconds: int


# --- Social Media Stage ---

class CarouselSlide(BaseModel):
    """Single slide in an Instagram carousel."""
    slide_number: int
    title: str
    body: str  # max 3 lines
    cta: Optional[str] = None


class CarouselAsset(BaseModel):
    """Instagram carousel content."""
    slides: list[CarouselSlide]
    topic: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ThreadAsset(BaseModel):
    """X/Twitter thread content."""
    tweets: list[str]  # 8-12 tweets, each <= 280 chars
    topic: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class LinkedInAsset(BaseModel):
    """LinkedIn post content."""
    content: str  # 1000-1500 chars
    hashtags: list[str]  # max 5
    metadata: dict[str, Any] = Field(default_factory=dict)


# --- Workflow Product Platform ---

class Execution(BaseModel):
    """Record of a single workflow execution."""
    id: str
    workflow_product_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str  # "running" | "success" | "failed"
    outputs: dict[str, Any] = Field(default_factory=dict)
    cost_actual: float = 0.0
    error: Optional[str] = None


class WorkflowProduct(BaseModel):
    """A productized n8n workflow registered in the platform."""
    id: str
    name: str
    description: str
    category: str  # "content" | "sales" | "support" | "ops"
    n8n_workflow_json: dict[str, Any]
    config: dict[str, Any] = Field(default_factory=dict)
    schedule: Optional[str] = None  # cron expression
    agents_used: list[str] = Field(default_factory=list)
    webhook_urls: list[str] = Field(default_factory=list)
    status: str = "draft"  # "draft" | "active" | "paused" | "error"
    created_from_template: Optional[str] = None
    brand_voice_file: Optional[str] = None
    executions: list[Execution] = Field(default_factory=list)
    cost_per_run: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

**Step 4: Run test to verify it passes**

Run: `cd C:\labs\inteligence\chunk-generator && python -m pytest tests/content/test_models.py -v`
Expected: ALL PASS (11 tests)

**Step 5: Commit**

```bash
git add src/neural_link/agents/content/__init__.py src/neural_link/agents/content/models.py tests/content/test_models.py
git commit -m "feat(content): add data models for content factory pipeline"
```

---

## Task 2: Brand Voice Knowledge File

**Files:**
- Create: `vault/Knowledge/omega_brand_voice.txt`
- Test: Manual — verify RAG can find it

**Step 1: Create brand voice file**

```text
# Omega Brand Voice — Referencia para Agentes de Conteudo

## Essencia
Tecnologia que fecha vendas — nao so conversa.
A Omega existe no momento em que o lead vira cliente.
Nao na aquisicao, nao no awareness — no fechamento.

## Personalidade
- DIRETA: Fala o que precisa ser dito, sem enrolar. O cliente nao precisa entender de IA — precisa entender o resultado.
- CONFIAVEL: Acessa banco de dados, processa pagamentos, integra com ERP. Transmite solidez tecnica sem ser fria.
- BRASILEIRA: Nao e startup de SP tentando parecer gringa. Ousada, pratica, fala a lingua de quem usa WhatsApp pra vender.

## Posicionamento
Nem agencia, nem SaaS frio. O ponto entre "ferramenta que voce configura sozinho" e "agencia que voce depende". Tecnologia com presenca humana.

## Tom de Voz — Regras

### DIRETO (como falar)
BOM: "Seu estoque atualiza sozinho quando uma venda fecha"
RUIM: "Nossa solucao de automacao integrada oferece sincronizacao bidirecional de inventario"

### HUMANO (como soar)
BOM: "A gente instala um pequeno programa no servidor de voces"
RUIM: "O middleware estabelece conexao via protocolo TCP ao banco relacional"

### CONFIANTE (como afirmar)
BOM: "Resultado em 2 semanas ou a gente resolve"
RUIM: "Acreditamos que possivelmente voce pode ter melhorias"

## Frases Modelo (usar como referencia de qualidade)
- "Seu agente ja respondeu 47 leads enquanto voce dormia"
- "Funciona com o sistema que voce ja usa — sem trocar nada"
- "Pagamento confirmado, estoque baixado, pedido registrado. Automatico."
- "Resultado em 30 dias ou a gente ajusta de graca"
- "Nenhum lead sem resposta. Em nenhum canal."

## NUNCA usar (anti-padroes)
- "Nossa plataforma de IA generativa multiagente oferece solucoes omnichannel"
- "Potencializamos sua jornada de transformacao digital"
- "Estamos muito felizes em poder ajudar voce nessa missao!"
- "Utilizamos LLMs de ultima geracao para otimizar seus KPIs de conversao"
- "E com grande satisfacao que apresentamos nossa solucao inovadora"

## Paleta Visual (para agentes que geram conteudo visual)
- Fundo escuro: Ink (#0D0D12) — serio, profissional
- Cor de marca: Azul Omega (#1B4FFF) — CTAs, destaques
- Acento urgencia: Laranja (#FF5C35) — SO para urgencia, nunca cor principal
- Fundo claro: Off-white (#F8F7F4) — neutro, limpo
- Tipografia display: Bricolage Grotesque (800 ExtraBold)
- Tipografia corpo: Plus Jakarta Sans (400 Regular)

## Para Podcast (ScriptAgent)
- Falar como gente, nao como manual
- Frases curtas. Pausas naturais.
- Analogias do dia-a-dia para conceitos abstratos
- Maximo 5-8 minutos por episodio
- Abertura com gancho (pergunta ou dado impactante)
- Fechamento com CTA claro

## Para Twitter/X (ThreadAgent)
- Tweet 1: gancho (pergunta provocativa ou numero impactante)
- Corpo: 1 insight por tweet, max 280 chars
- Final: CTA com link pro podcast
- Tom: direto, esperto, sem emoji excessivo

## Para LinkedIn (LinkedInAgent)
- Tom profissional mas nao corporativo
- Hook forte na primeira linha (aparece no preview)
- 3 insights concretos com numeros quando possivel
- CTA no final
- Max 5 hashtags relevantes

## Para Instagram (CarouselAgent)
- Max 3 linhas por slide
- Slide 1: gancho visual forte
- Slides 2-6: conteudo (1 insight por slide)
- Slide final: CTA
- Paleta: Ink + Azul Omega + Off-white
```

**Step 2: Verify file exists and RAG can index it**

Run: `cd C:\labs\inteligence\chunk-generator && python -c "from pathlib import Path; p = Path('vault/Knowledge/omega_brand_voice.txt'); print(f'Exists: {p.exists()}, Size: {p.stat().st_size} bytes')"`
Expected: `Exists: True, Size: ~3000 bytes`

**Step 3: Commit**

```bash
git add vault/Knowledge/omega_brand_voice.txt
git commit -m "feat(content): add Omega brand voice knowledge file for RAG"
```

---

## Task 3: ResearchAgent

**Files:**
- Create: `src/neural_link/agents/content/research_agent.py`
- Test: `tests/content/test_research_agent.py`

**Step 1: Write failing test**

```python
# tests/content/test_research_agent.py
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json


def test_research_agent_has_correct_capabilities():
    from src.neural_link.agents.content.research_agent import ResearchAgent

    agent = ResearchAgent()
    assert "research" in agent.capabilities
    assert "papers" in agent.capabilities
    assert "trends" in agent.capabilities


def test_research_agent_inherits_base_agent():
    from src.neural_link.agents.content.research_agent import ResearchAgent
    from src.neural_link.agents.base_agent import BaseAgent

    agent = ResearchAgent()
    assert isinstance(agent, BaseAgent)


def test_fetch_arxiv_parses_xml():
    from src.neural_link.agents.content.research_agent import ResearchAgent

    agent = ResearchAgent()
    # Minimal Arxiv Atom XML
    mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Test Paper Title</title>
        <summary>This is a test summary of a paper about AI.</summary>
        <link href="http://arxiv.org/abs/2026.12345"/>
        <published>2026-03-05T00:00:00Z</published>
      </entry>
    </feed>"""

    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200, text=mock_xml, raise_for_status=lambda: None
        )
        items = agent._fetch_arxiv(max_results=5)

    assert len(items) == 1
    assert items[0]["title"] == "Test Paper Title"
    assert items[0]["source"] == "arxiv"


def test_fetch_huggingface_parses_json():
    from src.neural_link.agents.content.research_agent import ResearchAgent

    agent = ResearchAgent()
    mock_json = [
        {
            "modelId": "meta-llama/Llama-4",
            "likes": 5000,
            "pipeline_tag": "text-generation",
        }
    ]

    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_json,
            raise_for_status=lambda: None,
        )
        items = agent._fetch_huggingface(limit=5)

    assert len(items) == 1
    assert items[0]["source"] == "huggingface"
    assert "Llama-4" in items[0]["title"]


def test_fetch_github_trending_parses_json():
    from src.neural_link.agents.content.research_agent import ResearchAgent

    agent = ResearchAgent()
    mock_json = {
        "items": [
            {
                "full_name": "openai/whisper-v4",
                "description": "Next-gen speech recognition",
                "html_url": "https://github.com/openai/whisper-v4",
                "stargazers_count": 15000,
            }
        ]
    }

    with patch("httpx.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_json,
            raise_for_status=lambda: None,
        )
        items = agent._fetch_github_trending(limit=5)

    assert len(items) == 1
    assert items[0]["source"] == "github"


def test_rank_items_returns_sorted_list():
    from src.neural_link.agents.content.research_agent import ResearchAgent

    agent = ResearchAgent()
    raw_items = [
        {"title": "Paper A", "source": "arxiv", "url": "http://a", "summary": "About GANs"},
        {"title": "Tool B", "source": "github", "url": "http://b", "summary": "Sales AI assistant"},
        {"title": "Model C", "source": "huggingface", "url": "http://c", "summary": "Fine-tuned for Portuguese"},
    ]

    with patch.object(agent, "_score_relevance") as mock_score:
        mock_score.side_effect = [0.3, 0.9, 0.7]
        ranked = agent._rank_items(raw_items, max_items=2)

    assert len(ranked) == 2
    assert ranked[0]["title"] == "Tool B"  # highest score


def test_execute_returns_research_digest():
    from src.neural_link.agents.content.research_agent import ResearchAgent
    from src.neural_link.agents.content.models import ResearchDigest

    agent = ResearchAgent()

    with patch.object(agent, "_fetch_arxiv", return_value=[]), \
         patch.object(agent, "_fetch_huggingface", return_value=[]), \
         patch.object(agent, "_fetch_github_trending", return_value=[]), \
         patch.object(agent, "_fetch_producthunt", return_value=[]):

        result = agent.execute(task={"period": "7d", "sources": "all", "max_items": 8})

    assert isinstance(result, dict)
    assert "items" in result
    assert "period" in result
    assert "sources_status" in result
```

**Step 2: Run test to verify it fails**

Run: `cd C:\labs\inteligence\chunk-generator && python -m pytest tests/content/test_research_agent.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# src/neural_link/agents/content/research_agent.py
"""ResearchAgent — collects and ranks AI/tech trends from multiple sources.

Sources: Arxiv, HuggingFace, GitHub Trending, ProductHunt.
Ranks by relevance to Omega audience (business owners using AI for sales).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from xml.etree import ElementTree

import httpx

from src.neural_link.agents.base_agent import BaseAgent
from src.neural_link.agents.content.models import ResearchDigest, ResearchItem

logger = logging.getLogger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"
ARXIV_CATEGORIES = "cat:cs.AI+OR+cat:cs.CL+OR+cat:cs.LG"
HF_API = "https://huggingface.co/api/models"
GITHUB_API = "https://api.github.com/search/repositories"
PH_API = "https://api.producthunt.com/v2/api/graphql"

# Keywords that boost relevance for Omega audience
RELEVANCE_KEYWORDS = {
    "high": ["sales", "conversion", "customer", "whatsapp", "chatbot", "agent",
             "portuguese", "brazil", "crm", "ecommerce", "revenue", "lead"],
    "medium": ["rag", "embedding", "fine-tune", "api", "deploy", "production",
               "cost", "optimization", "fast", "efficient", "small model"],
    "low": ["benchmark", "theory", "proof", "mathematical", "abstract"],
}
TIMEOUT = 15  # seconds per source


class ResearchAgent(BaseAgent):
    """Collects weekly AI/tech trends and ranks by Omega audience relevance."""

    @property
    def capabilities(self) -> set[str]:
        return {"research", "papers", "trends", "curation"}

    def execute(self, task: str | dict = "", **kwargs: Any) -> dict:
        """Collect and rank research items.

        Args:
            task: dict with keys: period (str), sources (str|list), max_items (int)
        """
        if isinstance(task, str):
            task = {"period": "7d", "sources": "all", "max_items": 8}

        period = task.get("period", "7d")
        sources = task.get("sources", "all")
        max_items = task.get("max_items", 8)

        all_items: list[dict] = []
        status: dict[str, str] = {}

        # Fetch from each source
        fetchers = {
            "arxiv": lambda: self._fetch_arxiv(max_results=20),
            "huggingface": lambda: self._fetch_huggingface(limit=15),
            "github": lambda: self._fetch_github_trending(limit=15),
            "producthunt": lambda: self._fetch_producthunt(limit=10),
        }

        for name, fetcher in fetchers.items():
            if sources != "all" and name not in sources:
                continue
            try:
                items = fetcher()
                all_items.extend(items)
                status[name] = f"ok ({len(items)} items)"
            except Exception as e:
                logger.warning("Failed to fetch %s: %s", name, e)
                status[name] = f"error: {e}"

        # Rank and select top items
        ranked = self._rank_items(all_items, max_items=max_items)

        # Build digest
        digest = ResearchDigest(
            items=[
                ResearchItem(
                    title=item["title"],
                    source=item["source"],
                    url=item["url"],
                    summary=item.get("summary", ""),
                    relevance_score=item.get("relevance_score", 0.5),
                    relevance_reason=item.get("relevance_reason", ""),
                    category=item.get("category", "paper"),
                )
                for item in ranked
            ],
            period=period,
            total_collected=len(all_items),
            sources_status=status,
        )
        return digest.model_dump()

    def _fetch_arxiv(self, max_results: int = 20) -> list[dict]:
        """Fetch recent papers from Arxiv API (Atom XML)."""
        params = {
            "search_query": ARXIV_CATEGORIES,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
            "max_results": max_results,
        }
        resp = httpx.get(ARXIV_API, params=params, timeout=TIMEOUT)
        resp.raise_for_status()

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ElementTree.fromstring(resp.text)
        items = []
        for entry in root.findall("atom:entry", ns):
            title = entry.findtext("atom:title", "", ns).strip()
            summary = entry.findtext("atom:summary", "", ns).strip()
            link_el = entry.find("atom:link", ns)
            url = link_el.get("href", "") if link_el is not None else ""
            items.append({
                "title": title,
                "source": "arxiv",
                "url": url,
                "summary": summary[:200],
                "category": "paper",
            })
        return items

    def _fetch_huggingface(self, limit: int = 15) -> list[dict]:
        """Fetch trending models from HuggingFace API."""
        params = {"sort": "trending", "limit": limit}
        resp = httpx.get(HF_API, params=params, timeout=TIMEOUT)
        resp.raise_for_status()

        items = []
        for model in resp.json():
            model_id = model.get("modelId", "")
            items.append({
                "title": model_id,
                "source": "huggingface",
                "url": f"https://huggingface.co/{model_id}",
                "summary": f"Model {model_id} — {model.get('pipeline_tag', 'unknown')} — {model.get('likes', 0)} likes",
                "category": "model",
            })
        return items

    def _fetch_github_trending(self, limit: int = 15) -> list[dict]:
        """Fetch trending AI repos from GitHub Search API."""
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        params = {
            "q": f"topic:ai topic:llm language:python created:>{week_ago}",
            "sort": "stars",
            "order": "desc",
            "per_page": limit,
        }
        resp = httpx.get(GITHUB_API, params=params, timeout=TIMEOUT)
        resp.raise_for_status()

        items = []
        for repo in resp.json().get("items", []):
            items.append({
                "title": repo.get("full_name", ""),
                "source": "github",
                "url": repo.get("html_url", ""),
                "summary": repo.get("description", "")[:200],
                "category": "tool",
            })
        return items

    def _fetch_producthunt(self, limit: int = 10) -> list[dict]:
        """Fetch recent AI products from ProductHunt GraphQL API.

        Note: Requires PH API token in env var PRODUCTHUNT_TOKEN.
        Falls back to empty list if not configured.
        """
        import os
        token = os.environ.get("PRODUCTHUNT_TOKEN", "")
        if not token:
            logger.info("PRODUCTHUNT_TOKEN not set, skipping ProductHunt")
            return []

        query = """
        query { posts(order: NEWEST, topic: "artificial-intelligence", first: %d) {
            edges { node { name tagline url votesCount } }
        }}
        """ % limit

        resp = httpx.post(
            PH_API,
            json={"query": query},
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()

        items = []
        edges = resp.json().get("data", {}).get("posts", {}).get("edges", [])
        for edge in edges:
            node = edge.get("node", {})
            items.append({
                "title": node.get("name", ""),
                "source": "producthunt",
                "url": node.get("url", ""),
                "summary": node.get("tagline", ""),
                "category": "product",
            })
        return items

    def _score_relevance(self, item: dict) -> float:
        """Score 0-1 based on keyword matching for Omega audience."""
        text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
        score = 0.5  # base

        for keyword in RELEVANCE_KEYWORDS["high"]:
            if keyword in text:
                score += 0.1
        for keyword in RELEVANCE_KEYWORDS["medium"]:
            if keyword in text:
                score += 0.05
        for keyword in RELEVANCE_KEYWORDS["low"]:
            if keyword in text:
                score -= 0.05

        return max(0.0, min(1.0, score))

    def _rank_items(self, items: list[dict], max_items: int = 8) -> list[dict]:
        """Score, sort, and select top items."""
        for item in items:
            item["relevance_score"] = self._score_relevance(item)
            item["relevance_reason"] = self._build_reason(item)

        items.sort(key=lambda x: x["relevance_score"], reverse=True)
        return items[:max_items]

    def _build_reason(self, item: dict) -> str:
        """Build human-readable relevance reason."""
        text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
        reasons = []
        for keyword in RELEVANCE_KEYWORDS["high"]:
            if keyword in text:
                reasons.append(keyword)
        if reasons:
            return f"Relevante para Omega: {', '.join(reasons[:3])}"
        return "Tendencia geral em AI"
```

**Step 4: Run test to verify it passes**

Run: `cd C:\labs\inteligence\chunk-generator && python -m pytest tests/content/test_research_agent.py -v`
Expected: ALL PASS (6 tests)

**Step 5: Commit**

```bash
git add src/neural_link/agents/content/research_agent.py tests/content/test_research_agent.py
git commit -m "feat(content): add ResearchAgent with multi-source collection"
```

---

## Task 4: ScriptAgent

**Files:**
- Create: `src/neural_link/agents/content/script_agent.py`
- Test: `tests/content/test_script_agent.py`

**Step 1: Write failing test**

```python
# tests/content/test_script_agent.py
import pytest
from unittest.mock import patch, MagicMock


def test_script_agent_has_correct_capabilities():
    from src.neural_link.agents.content.script_agent import ScriptAgent

    agent = ScriptAgent()
    assert "copywriting" in agent.capabilities
    assert "podcast" in agent.capabilities
    assert "brand_voice" in agent.capabilities


def test_script_agent_inherits_base_agent():
    from src.neural_link.agents.content.script_agent import ScriptAgent
    from src.neural_link.agents.base_agent import BaseAgent

    assert issubclass(ScriptAgent, BaseAgent)


def test_build_prompt_includes_brand_voice():
    from src.neural_link.agents.content.script_agent import ScriptAgent

    agent = ScriptAgent()
    digest = {
        "items": [
            {"title": "Paper X", "summary": "About AI sales", "source": "arxiv",
             "relevance_reason": "Sales AI"},
        ],
        "period": "2026-03-01 a 2026-03-07",
    }
    brand_voice = "Tom direto, brasileiro, confiante."

    prompt = agent._build_prompt(digest, brand_voice, episode_number=1)

    assert "Omega Weekly" in prompt
    assert "Paper X" in prompt
    assert "direto" in prompt.lower()


def test_parse_script_response_creates_podcast_script():
    from src.neural_link.agents.content.script_agent import ScriptAgent

    agent = ScriptAgent()
    raw = """[ABERTURA]
Fala pessoal, bem vindos ao Omega Weekly.

[BLOCO 1]
Essa semana o destaque e o Paper X.

[FECHAMENTO]
Resumindo: AI esta mudando vendas."""

    script = agent._parse_script(raw, episode_number=1)

    assert script.episode_number == 1
    assert len(script.sections) >= 2
    assert script.plain_text != ""


def test_generate_ssml_wraps_in_speak_tags():
    from src.neural_link.agents.content.script_agent import ScriptAgent

    agent = ScriptAgent()
    text = "Fala pessoal. [...] Vamos la."
    ssml = agent._generate_ssml(text)

    assert ssml.startswith("<speak>")
    assert ssml.endswith("</speak>")
    assert '<break time="600ms"/>' in ssml  # [...] becomes break


def test_execute_calls_llm_and_returns_dict():
    from src.neural_link.agents.content.script_agent import ScriptAgent

    agent = ScriptAgent()
    task = {
        "digest": {
            "items": [{"title": "T", "summary": "S", "source": "arxiv", "relevance_reason": "R"}],
            "period": "test",
        },
        "brand": "omega",
        "episode_number": 1,
    }

    mock_response = """[ABERTURA]
Fala pessoal.

[BLOCO 1]
Teste.

[FECHAMENTO]
Ate a proxima."""

    with patch.object(agent, "_load_brand_voice", return_value="Tom direto."), \
         patch.object(agent, "_call_llm", return_value=mock_response):
        result = agent.execute(task=task)

    assert "title" in result
    assert "sections" in result
    assert "ssml" in result
    assert "plain_text" in result
```

**Step 2: Run test to verify it fails**

Run: `cd C:\labs\inteligence\chunk-generator && python -m pytest tests/content/test_script_agent.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/neural_link/agents/content/script_agent.py
"""ScriptAgent — generates podcast scripts from research digests.

Uses Omega brand voice (from RAG knowledge vault) to write
conversational, direct, Brazilian Portuguese podcast scripts.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

from src.neural_link.agents.base_agent import BaseAgent
from src.neural_link.agents.content.models import PodcastScript, ScriptSection

logger = logging.getLogger(__name__)

BRAND_VOICE_PATH = Path("vault/Knowledge/omega_brand_voice.txt")

SCRIPT_SYSTEM_PROMPT = """Voce e o roteirista do podcast "Omega Weekly".
Gere um roteiro de podcast em portugues BR seguindo EXATAMENTE este formato:

[ABERTURA]
<gancho em 1 frase + contexto da semana, 15-20 segundos>

[BLOCO 1 — <titulo>]
<conteudo do item 1, 60-90 segundos, linguagem falada>

[BLOCO 2 — <titulo>]
<conteudo do item 2, 60-90 segundos>

(repita para cada item relevante, max 5 blocos)

[FECHAMENTO]
<resumo 3 pontos + CTA, 15-20 segundos>

REGRAS:
- Marque pausas com [...]
- Marque enfase com **palavra**
- Tom: direto, humano, confiante, brasileiro
- NUNCA use jargao tecnico sem explicar
- Frases curtas, ritmo de conversa
- Duracao total: 5-8 minutos
"""


class ScriptAgent(BaseAgent):
    """Generates podcast scripts using LLM + brand voice context."""

    @property
    def capabilities(self) -> set[str]:
        return {"copywriting", "script", "podcast", "brand_voice"}

    def execute(self, task: str | dict = "", **kwargs: Any) -> dict:
        """Generate podcast script from research digest.

        Args:
            task: dict with keys: digest (dict), brand (str), episode_number (int)
        """
        if isinstance(task, str):
            return {"error": "Task must be a dict with 'digest' key"}

        digest = task.get("digest", {})
        episode_number = task.get("episode_number", 1)

        # Load brand voice
        brand_voice = self._load_brand_voice()

        # Build prompt with digest + brand voice
        prompt = self._build_prompt(digest, brand_voice, episode_number)

        # Call LLM
        raw_script = self._call_llm(prompt)

        # Parse into structured script
        script = self._parse_script(raw_script, episode_number)

        return script.model_dump()

    def _load_brand_voice(self) -> str:
        """Load brand voice from knowledge vault."""
        if BRAND_VOICE_PATH.exists():
            return BRAND_VOICE_PATH.read_text(encoding="utf-8")
        logger.warning("Brand voice file not found at %s", BRAND_VOICE_PATH)
        return "Tom direto, humano, confiante. Portugues BR."

    def _build_prompt(self, digest: dict, brand_voice: str, episode_number: int) -> str:
        """Build the LLM prompt combining digest + brand voice."""
        items_text = ""
        for i, item in enumerate(digest.get("items", []), 1):
            items_text += (
                f"\n{i}. {item['title']} ({item['source']})\n"
                f"   Resumo: {item['summary']}\n"
                f"   Relevancia: {item.get('relevance_reason', 'N/A')}\n"
            )

        return f"""{SCRIPT_SYSTEM_PROMPT}

## Brand Voice
{brand_voice[:500]}

## Episodio
Numero: {episode_number}
Titulo: Omega Weekly #{episode_number}
Periodo: {digest.get('period', 'esta semana')}

## Items da Semana (use os mais relevantes)
{items_text}

Gere o roteiro agora."""

    def _call_llm(self, prompt: str) -> str:
        """Call LLM to generate script. Uses Opus for creative quality."""
        try:
            from src.utils.llm_client import LLMClient
            client = LLMClient()
            return client.generate(prompt, model="opus", max_tokens=4000)
        except ImportError:
            logger.error("LLMClient not available")
            return "[ABERTURA]\nScript generation failed.\n[FECHAMENTO]\nEnd."

    def _parse_script(self, raw: str, episode_number: int) -> PodcastScript:
        """Parse raw LLM output into structured PodcastScript."""
        sections: list[ScriptSection] = []
        current_type = "unknown"
        current_title = ""
        current_content: list[str] = []

        for line in raw.split("\n"):
            # Detect section headers: [ABERTURA], [BLOCO 1 — Title], [FECHAMENTO]
            header_match = re.match(r"\[(\w+)(?:\s+\d+)?(?:\s*[—-]\s*(.+))?\]", line.strip())
            if header_match:
                # Save previous section
                if current_content:
                    sections.append(ScriptSection(
                        type=current_type,
                        title=current_title or current_type,
                        content="\n".join(current_content).strip(),
                        duration_estimate=self._estimate_duration(
                            "\n".join(current_content)
                        ),
                    ))
                    current_content = []

                tag = header_match.group(1).lower()
                subtitle = header_match.group(2) or ""
                if tag == "abertura":
                    current_type = "opening"
                    current_title = "Abertura"
                elif tag.startswith("bloco"):
                    current_type = "block"
                    current_title = subtitle.strip() if subtitle else f"Bloco"
                elif tag == "fechamento":
                    current_type = "closing"
                    current_title = "Fechamento"
                else:
                    current_type = tag
                    current_title = subtitle.strip() if subtitle else tag
            else:
                if line.strip():
                    current_content.append(line)

        # Don't forget last section
        if current_content:
            sections.append(ScriptSection(
                type=current_type,
                title=current_title or current_type,
                content="\n".join(current_content).strip(),
                duration_estimate=self._estimate_duration(
                    "\n".join(current_content)
                ),
            ))

        plain_text = "\n\n".join(s.content for s in sections)
        total_duration = sum(s.duration_estimate for s in sections)

        return PodcastScript(
            title=f"Omega Weekly #{episode_number}",
            episode_number=episode_number,
            duration_estimate=total_duration,
            sections=sections,
            ssml=self._generate_ssml(plain_text),
            plain_text=plain_text,
            metadata={"episode_number": episode_number},
        )

    def _generate_ssml(self, text: str) -> str:
        """Convert plain text with markers to SSML for TTS."""
        ssml = text
        # [...] → <break>
        ssml = ssml.replace("[...]", '<break time="600ms"/>')
        # **word** → <emphasis>
        ssml = re.sub(r"\*\*(.+?)\*\*", r'<emphasis level="strong">\1</emphasis>', ssml)
        return f"<speak>{ssml}</speak>"

    def _estimate_duration(self, text: str) -> int:
        """Estimate speech duration in seconds (~150 words/min in pt-BR)."""
        word_count = len(text.split())
        return max(5, int(word_count / 2.5))  # ~150 wpm = 2.5 wps
```

**Step 4: Run test to verify it passes**

Run: `cd C:\labs\inteligence\chunk-generator && python -m pytest tests/content/test_script_agent.py -v`
Expected: ALL PASS (6 tests)

**Step 5: Commit**

```bash
git add src/neural_link/agents/content/script_agent.py tests/content/test_script_agent.py
git commit -m "feat(content): add ScriptAgent with LLM-powered podcast scripts"
```

---

## Task 5: AudioAgent

**Files:**
- Create: `src/neural_link/agents/content/audio_agent.py`
- Test: `tests/content/test_audio_agent.py`

**Step 1: Write failing test**

```python
# tests/content/test_audio_agent.py
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


def test_audio_agent_has_correct_capabilities():
    from src.neural_link.agents.content.audio_agent import AudioAgent

    agent = AudioAgent()
    assert "tts" in agent.capabilities
    assert "audio" in agent.capabilities


def test_audio_agent_inherits_base_agent():
    from src.neural_link.agents.content.audio_agent import AudioAgent
    from src.neural_link.agents.base_agent import BaseAgent

    assert issubclass(AudioAgent, BaseAgent)


def test_execute_calls_tts_and_returns_audio_asset(tmp_path):
    from src.neural_link.agents.content.audio_agent import AudioAgent

    agent = AudioAgent(output_dir=str(tmp_path))
    task = {
        "script": {
            "ssml": "<speak>Fala pessoal</speak>",
            "plain_text": "Fala pessoal",
            "title": "Omega Weekly #1",
            "episode_number": 1,
        },
        "voice": "pt-br-conversational",
    }

    fake_audio = b"\xff\xfb\x90\x00" * 1000  # fake MP3 bytes

    with patch.object(agent, "_call_tts", return_value=fake_audio):
        result = agent.execute(task=task)

    assert result["duration_seconds"] >= 0
    assert result["file_path"].endswith(".mp3")
    assert Path(result["file_path"]).exists()


def test_call_tts_elevenlabs_fallback_to_openai():
    from src.neural_link.agents.content.audio_agent import AudioAgent

    agent = AudioAgent()

    with patch.object(agent, "_tts_elevenlabs", side_effect=Exception("API error")), \
         patch.object(agent, "_tts_openai", return_value=b"audio_bytes") as mock_openai:
        result = agent._call_tts("<speak>Test</speak>", "test-voice")

    mock_openai.assert_called_once()
    assert result == b"audio_bytes"
```

**Step 2: Run test to verify it fails**

Run: `cd C:\labs\inteligence\chunk-generator && python -m pytest tests/content/test_audio_agent.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/neural_link/agents/content/audio_agent.py
"""AudioAgent — converts podcast scripts to audio via TTS.

Primary: ElevenLabs (best pt-BR quality)
Fallback: OpenAI TTS (alloy/nova voices)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from src.neural_link.agents.base_agent import BaseAgent
from src.neural_link.agents.content.models import AudioAsset

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = "data/audio"


class AudioAgent(BaseAgent):
    """Converts SSML scripts to MP3 audio files."""

    def __init__(self, output_dir: str = DEFAULT_OUTPUT_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def capabilities(self) -> set[str]:
        return {"tts", "audio", "elevenlabs"}

    def execute(self, task: str | dict = "", **kwargs: Any) -> dict:
        """Generate audio from script.

        Args:
            task: dict with keys: script (dict), voice (str)
        """
        if isinstance(task, str):
            return {"error": "Task must be a dict with 'script' key"}

        script = task.get("script", {})
        voice = task.get("voice", "pt-br-conversational")

        ssml = script.get("ssml", "")
        plain_text = script.get("plain_text", "")
        episode = script.get("episode_number", 0)
        title = script.get("title", f"episode-{episode}")

        # Generate audio
        audio_bytes = self._call_tts(ssml or plain_text, voice)

        # Save to file
        safe_title = title.lower().replace(" ", "-").replace("#", "")
        filename = f"{safe_title}.mp3"
        file_path = self.output_dir / filename
        file_path.write_bytes(audio_bytes)

        # Estimate duration (~128kbps MP3 = 16KB/s)
        size_bytes = len(audio_bytes)
        duration_seconds = max(1, size_bytes // 16000)

        asset = AudioAsset(
            file_path=str(file_path),
            duration_seconds=duration_seconds,
            size_bytes=size_bytes,
            voice_id=voice,
            transcript=plain_text,
            metadata={"episode": episode, "title": title},
        )
        return asset.model_dump()

    def _call_tts(self, text: str, voice: str) -> bytes:
        """Call TTS API. Try ElevenLabs first, fallback to OpenAI."""
        try:
            return self._tts_elevenlabs(text, voice)
        except Exception as e:
            logger.warning("ElevenLabs failed (%s), falling back to OpenAI TTS", e)
            return self._tts_openai(text, voice)

    def _tts_elevenlabs(self, text: str, voice: str) -> bytes:
        """Call ElevenLabs TTS API."""
        import httpx

        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY not set")

        voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")

        resp = httpx.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": api_key},
            json={
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                },
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.content

    def _tts_openai(self, text: str, voice: str) -> bytes:
        """Call OpenAI TTS API as fallback."""
        import httpx

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        # Strip SSML tags for OpenAI (doesn't support SSML)
        import re
        clean_text = re.sub(r"<[^>]+>", "", text)

        resp = httpx.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "tts-1",
                "voice": "nova",  # Good for pt-BR
                "input": clean_text,
                "response_format": "mp3",
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.content
```

**Step 4: Run test to verify it passes**

Run: `cd C:\labs\inteligence\chunk-generator && python -m pytest tests/content/test_audio_agent.py -v`
Expected: ALL PASS (4 tests)

**Step 5: Commit**

```bash
git add src/neural_link/agents/content/audio_agent.py tests/content/test_audio_agent.py
git commit -m "feat(content): add AudioAgent with ElevenLabs + OpenAI TTS fallback"
```

---

## Task 6: Social Media Agents (Clip + Carousel + Thread + LinkedIn)

**Files:**
- Create: `src/neural_link/agents/content/clip_agent.py`
- Create: `src/neural_link/agents/content/carousel_agent.py`
- Create: `src/neural_link/agents/content/thread_agent.py`
- Create: `src/neural_link/agents/content/linkedin_agent.py`
- Test: `tests/content/test_social_agents.py`

**Step 1: Write failing test**

```python
# tests/content/test_social_agents.py
import pytest
from unittest.mock import patch, MagicMock


# --- ClipAgent ---

def test_clip_agent_capabilities():
    from src.neural_link.agents.content.clip_agent import ClipAgent
    agent = ClipAgent()
    assert "clips" in agent.capabilities
    assert "short_form" in agent.capabilities


def test_clip_agent_finds_clip_worthy_moments():
    from src.neural_link.agents.content.clip_agent import ClipAgent
    agent = ClipAgent()

    sections = [
        {"type": "opening", "content": "Fala pessoal", "duration_estimate": 15},
        {"type": "block", "content": "Essa semana o destaque e incrivel. Um paper que muda tudo sobre vendas com IA.", "duration_estimate": 60},
        {"type": "block", "content": "Outro ponto interessante sobre chatbots.", "duration_estimate": 60},
        {"type": "closing", "content": "Ate a proxima", "duration_estimate": 15},
    ]
    moments = agent._find_clip_moments(sections, max_clips=3)
    assert len(moments) >= 1
    assert all("start_seconds" in m for m in moments)


# --- CarouselAgent ---

def test_carousel_agent_capabilities():
    from src.neural_link.agents.content.carousel_agent import CarouselAgent
    agent = CarouselAgent()
    assert "carousel" in agent.capabilities
    assert "instagram" in agent.capabilities


def test_carousel_agent_execute_returns_slides():
    from src.neural_link.agents.content.carousel_agent import CarouselAgent
    agent = CarouselAgent()

    task = {
        "digest": {
            "items": [
                {"title": "Paper X", "summary": "About AI sales", "source": "arxiv",
                 "relevance_reason": "Sales AI", "relevance_score": 0.9},
            ],
        },
    }

    mock_response = """SLIDE 1: O paper que muda vendas com IA
SLIDE 2: Paper X descobriu que agentes de IA vendem 35% mais
SLIDE 3: Como isso funciona na pratica
SLIDE 4: 3 insights do paper
SLIDE 5: Quer saber mais? Link na bio"""

    with patch.object(agent, "_load_brand_voice", return_value="Tom direto."), \
         patch.object(agent, "_call_llm", return_value=mock_response):
        result = agent.execute(task=task)

    assert "slides" in result
    assert len(result["slides"]) >= 3


# --- ThreadAgent ---

def test_thread_agent_capabilities():
    from src.neural_link.agents.content.thread_agent import ThreadAgent
    agent = ThreadAgent()
    assert "twitter" in agent.capabilities
    assert "threads" in agent.capabilities


def test_thread_agent_execute_returns_tweets():
    from src.neural_link.agents.content.thread_agent import ThreadAgent
    agent = ThreadAgent()

    task = {
        "digest": {
            "items": [
                {"title": "Paper X", "summary": "About AI sales", "source": "arxiv",
                 "relevance_reason": "Sales AI", "relevance_score": 0.9},
            ],
        },
    }

    mock_response = "1/ Voce sabia que IA ja vende mais que humano?\n\n2/ Paper X provou isso essa semana\n\n3/ Link pro podcast completo na bio"

    with patch.object(agent, "_load_brand_voice", return_value="Tom direto."), \
         patch.object(agent, "_call_llm", return_value=mock_response):
        result = agent.execute(task=task)

    assert "tweets" in result
    assert len(result["tweets"]) >= 2


# --- LinkedInAgent ---

def test_linkedin_agent_capabilities():
    from src.neural_link.agents.content.linkedin_agent import LinkedInAgent
    agent = LinkedInAgent()
    assert "linkedin" in agent.capabilities
    assert "b2b" in agent.capabilities


def test_linkedin_agent_execute_returns_post():
    from src.neural_link.agents.content.linkedin_agent import LinkedInAgent
    agent = LinkedInAgent()

    task = {
        "digest": {
            "items": [
                {"title": "Paper X", "summary": "About AI sales", "source": "arxiv",
                 "relevance_reason": "Sales AI", "relevance_score": 0.9},
            ],
        },
    }

    mock_response = "Essa semana um paper mudou minha visao sobre vendas com IA.\n\n3 insights:\n1. Agentes vendem mais\n2. Custo cai 60%\n3. Funciona 24/7\n\n#IA #Vendas #Omega"

    with patch.object(agent, "_load_brand_voice", return_value="Tom direto."), \
         patch.object(agent, "_call_llm", return_value=mock_response):
        result = agent.execute(task=task)

    assert "content" in result
    assert "hashtags" in result
    assert len(result["hashtags"]) >= 1
```

**Step 2: Run test to verify it fails**

Run: `cd C:\labs\inteligence\chunk-generator && python -m pytest tests/content/test_social_agents.py -v`
Expected: FAIL

**Step 3: Write implementations**

Create all 4 files. Each follows the same pattern: inherits BaseAgent, loads brand voice, calls LLM, parses output. See design doc sections 4.4-4.7 for exact behavior.

The implementations follow the identical pattern to ScriptAgent but with format-specific prompts and parsers. Key difference per agent:

- **ClipAgent**: No LLM needed. Analyzes script sections by word count and keyword density to find clip-worthy moments. Outputs timestamp ranges.
- **CarouselAgent**: LLM (Sonnet) generates slide text. Parses "SLIDE N:" format.
- **ThreadAgent**: LLM (Sonnet) generates numbered tweets. Parses "N/" format.
- **LinkedInAgent**: LLM (Sonnet) generates single post. Extracts hashtags via regex.

**Step 4: Run test to verify it passes**

Run: `cd C:\labs\inteligence\chunk-generator && python -m pytest tests/content/test_social_agents.py -v`
Expected: ALL PASS (8 tests)

**Step 5: Commit**

```bash
git add src/neural_link/agents/content/clip_agent.py \
        src/neural_link/agents/content/carousel_agent.py \
        src/neural_link/agents/content/thread_agent.py \
        src/neural_link/agents/content/linkedin_agent.py \
        tests/content/test_social_agents.py
git commit -m "feat(content): add ClipAgent, CarouselAgent, ThreadAgent, LinkedInAgent"
```

---

## Task 7: PublishAgent

**Files:**
- Create: `src/neural_link/agents/content/publish_agent.py`
- Test: `tests/content/test_publish_agent.py`

**Step 1: Write failing test**

```python
# tests/content/test_publish_agent.py
import pytest
from unittest.mock import patch, MagicMock


def test_publish_agent_capabilities():
    from src.neural_link.agents.content.publish_agent import PublishAgent
    agent = PublishAgent()
    assert "publish" in agent.capabilities
    assert "distribution" in agent.capabilities


def test_publish_agent_routes_by_asset_type():
    from src.neural_link.agents.content.publish_agent import PublishAgent
    agent = PublishAgent()

    task = {
        "asset_type": "thread",
        "asset": {"tweets": ["Tweet 1", "Tweet 2"], "topic": "AI"},
    }

    with patch.object(agent, "_publish_twitter", return_value={"url": "https://x.com/thread/123"}) as mock:
        result = agent.execute(task=task)

    mock.assert_called_once()
    assert "url" in result


def test_publish_agent_handles_unknown_type():
    from src.neural_link.agents.content.publish_agent import PublishAgent
    agent = PublishAgent()

    task = {"asset_type": "unknown_format", "asset": {}}
    result = agent.execute(task=task)

    assert "error" in result
```

**Step 2-5: Implement, test, commit**

PublishAgent is a router — dispatches to platform-specific publishers. Each publisher is a stub initially (logs intent, returns mock URL). Real API integration added per-platform later.

```bash
git commit -m "feat(content): add PublishAgent with platform routing stubs"
```

---

## Task 8: Register Agents in AGENT_REGISTRY

**Files:**
- Modify: `src/neural_link/orchestrator/agent_selector.py`
- Test: `tests/content/test_agent_registration.py`

**Step 1: Write failing test**

```python
# tests/content/test_agent_registration.py
import pytest


def test_content_agents_registered():
    from src.neural_link.orchestrator.agent_selector import AGENT_REGISTRY

    content_agents = [
        "content_research",
        "content_script",
        "content_audio",
        "content_clip",
        "content_carousel",
        "content_thread",
        "content_linkedin",
        "content_publish",
    ]
    for agent_id in content_agents:
        assert agent_id in AGENT_REGISTRY, f"{agent_id} not in AGENT_REGISTRY"
        assert "capabilities" in AGENT_REGISTRY[agent_id]
        assert "module_path" in AGENT_REGISTRY[agent_id]


def test_content_agents_have_correct_types():
    from src.neural_link.orchestrator.agent_selector import AGENT_REGISTRY

    assert AGENT_REGISTRY["content_research"]["type"] == "domain"
    assert AGENT_REGISTRY["content_script"]["type"] == "domain"
    assert AGENT_REGISTRY["content_audio"]["type"] == "specialist"
    assert AGENT_REGISTRY["content_publish"]["type"] == "operator"
```

**Step 2: Run test to verify it fails**

Run: `cd C:\labs\inteligence\chunk-generator && python -m pytest tests/content/test_agent_registration.py -v`
Expected: FAIL — agents not in registry

**Step 3: Add entries to AGENT_REGISTRY**

Add to the existing `AGENT_REGISTRY` dict in `agent_selector.py`:

```python
# --- Content Factory Agents ---
"content_research": {
    "name": "Research Agent",
    "type": "domain",
    "module_path": "src.neural_link.agents.content.research_agent",
    "agent_class": "ResearchAgent",
    "invoke": "execute",
    "capabilities": {"research", "papers", "trends", "curation"},
},
"content_script": {
    "name": "Script Agent",
    "type": "domain",
    "module_path": "src.neural_link.agents.content.script_agent",
    "agent_class": "ScriptAgent",
    "invoke": "execute",
    "capabilities": {"copywriting", "script", "podcast", "brand_voice"},
},
"content_audio": {
    "name": "Audio Agent",
    "type": "specialist",
    "module_path": "src.neural_link.agents.content.audio_agent",
    "agent_class": "AudioAgent",
    "invoke": "execute",
    "capabilities": {"tts", "audio", "elevenlabs"},
},
"content_clip": {
    "name": "Clip Agent",
    "type": "specialist",
    "module_path": "src.neural_link.agents.content.clip_agent",
    "agent_class": "ClipAgent",
    "invoke": "execute",
    "capabilities": {"clips", "short_form", "reels"},
},
"content_carousel": {
    "name": "Carousel Agent",
    "type": "specialist",
    "module_path": "src.neural_link.agents.content.carousel_agent",
    "agent_class": "CarouselAgent",
    "invoke": "execute",
    "capabilities": {"carousel", "instagram", "visual_content"},
},
"content_thread": {
    "name": "Thread Agent",
    "type": "specialist",
    "module_path": "src.neural_link.agents.content.thread_agent",
    "agent_class": "ThreadAgent",
    "invoke": "execute",
    "capabilities": {"twitter", "threads", "microcopy"},
},
"content_linkedin": {
    "name": "LinkedIn Agent",
    "type": "specialist",
    "module_path": "src.neural_link.agents.content.linkedin_agent",
    "agent_class": "LinkedInAgent",
    "invoke": "execute",
    "capabilities": {"linkedin", "professional", "b2b"},
},
"content_publish": {
    "name": "Publish Agent",
    "type": "operator",
    "module_path": "src.neural_link.agents.content.publish_agent",
    "agent_class": "PublishAgent",
    "invoke": "execute",
    "capabilities": {"publish", "social_media", "distribution"},
},
```

**Step 4: Run test to verify it passes**

Run: `cd C:\labs\inteligence\chunk-generator && python -m pytest tests/content/test_agent_registration.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add src/neural_link/orchestrator/agent_selector.py tests/content/test_agent_registration.py
git commit -m "feat(content): register 8 content agents in AGENT_REGISTRY"
```

---

## Task 9: Workflow Registry API

**Files:**
- Create: `src/neural_link/api/workflow_registry.py`
- Test: `tests/content/test_workflow_registry.py`

**Step 1: Write failing test**

```python
# tests/content/test_workflow_registry.py
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from src.neural_link.api.workflow_registry import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def test_create_workflow_product(client):
    resp = client.post("/api/v1/workflows", json={
        "id": "omega-weekly-podcast",
        "name": "Podcast Semanal Omega",
        "description": "Podcast automatico semanal sobre AI",
        "category": "content",
        "n8n_workflow_json": {"nodes": [], "connections": {}},
        "agents_used": ["content_research", "content_script", "content_audio"],
        "schedule": "0 6 * * 5",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == "omega-weekly-podcast"
    assert data["status"] == "draft"


def test_list_workflow_products(client):
    # Create one first
    client.post("/api/v1/workflows", json={
        "id": "test-wf",
        "name": "Test",
        "description": "Test",
        "category": "content",
        "n8n_workflow_json": {},
    })
    resp = client.get("/api/v1/workflows")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_workflow_product(client):
    client.post("/api/v1/workflows", json={
        "id": "test-get",
        "name": "Test",
        "description": "Test",
        "category": "content",
        "n8n_workflow_json": {},
    })
    resp = client.get("/api/v1/workflows/test-get")
    assert resp.status_code == 200
    assert resp.json()["id"] == "test-get"


def test_get_nonexistent_returns_404(client):
    resp = client.get("/api/v1/workflows/nonexistent")
    assert resp.status_code == 404


def test_update_workflow_product(client):
    client.post("/api/v1/workflows", json={
        "id": "test-update",
        "name": "Test",
        "description": "Test",
        "category": "content",
        "n8n_workflow_json": {},
    })
    resp = client.put("/api/v1/workflows/test-update", json={
        "status": "active",
        "schedule": "0 9 * * 1",
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


def test_delete_workflow_product(client):
    client.post("/api/v1/workflows", json={
        "id": "test-delete",
        "name": "Test",
        "description": "Test",
        "category": "content",
        "n8n_workflow_json": {},
    })
    resp = client.delete("/api/v1/workflows/test-delete")
    assert resp.status_code == 200

    # Should be soft-deleted (paused)
    resp2 = client.get("/api/v1/workflows/test-delete")
    assert resp2.json()["status"] == "paused"


def test_search_templates(client):
    resp = client.get("/api/v1/workflows/templates", params={"q": "podcast automation"})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
```

**Step 2: Run test to verify it fails**

Run: `cd C:\labs\inteligence\chunk-generator && python -m pytest tests/content/test_workflow_registry.py -v`
Expected: FAIL

**Step 3: Write implementation**

```python
# src/neural_link/api/workflow_registry.py
"""Workflow Registry — CRUD API for Workflow Products.

Manages the lifecycle of productized n8n workflows:
register → configure → deploy → run → monitor.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.neural_link.agents.content.models import WorkflowProduct, Execution

logger = logging.getLogger(__name__)

router = APIRouter(tags=["workflows"])

# In-memory store (swap for Redis/Postgres in production)
_store: dict[str, WorkflowProduct] = {}


# --- Request/Response Models ---

class WorkflowCreateRequest(BaseModel):
    id: str
    name: str
    description: str
    category: str
    n8n_workflow_json: dict[str, Any]
    config: dict[str, Any] = Field(default_factory=dict)
    schedule: Optional[str] = None
    agents_used: list[str] = Field(default_factory=list)
    webhook_urls: list[str] = Field(default_factory=list)
    brand_voice_file: Optional[str] = None
    cost_per_run: float = 0.0


class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    schedule: Optional[str] = None
    status: Optional[str] = None
    n8n_workflow_json: Optional[dict[str, Any]] = None
    agents_used: Optional[list[str]] = None


# --- Endpoints ---

@router.post("/workflows", status_code=201)
def create_workflow(req: WorkflowCreateRequest) -> dict:
    """Register a new workflow product."""
    if req.id in _store:
        raise HTTPException(400, f"Workflow '{req.id}' already exists")

    wp = WorkflowProduct(
        id=req.id,
        name=req.name,
        description=req.description,
        category=req.category,
        n8n_workflow_json=req.n8n_workflow_json,
        config=req.config,
        schedule=req.schedule,
        agents_used=req.agents_used,
        webhook_urls=req.webhook_urls,
        brand_voice_file=req.brand_voice_file,
        cost_per_run=req.cost_per_run,
        status="draft",
    )
    _store[req.id] = wp
    return wp.model_dump()


@router.get("/workflows")
def list_workflows(category: Optional[str] = None) -> list[dict]:
    """List all workflow products, optionally filtered by category."""
    workflows = list(_store.values())
    if category:
        workflows = [w for w in workflows if w.category == category]
    return [w.model_dump() for w in workflows]


@router.get("/workflows/templates")
def search_templates(q: str = "") -> list[dict]:
    """Search the 4700+ n8n template library via RAG."""
    try:
        from src.neural_link.rag.hybrid_rag import HybridRAG
        rag = HybridRAG.from_env()
        results = rag.query(q, top_k=10, category="external_template")
        return results
    except Exception as e:
        logger.warning("RAG search failed: %s", e)
        return []


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str) -> dict:
    """Get workflow product details."""
    if workflow_id not in _store:
        raise HTTPException(404, f"Workflow '{workflow_id}' not found")
    return _store[workflow_id].model_dump()


@router.put("/workflows/{workflow_id}")
def update_workflow(workflow_id: str, req: WorkflowUpdateRequest) -> dict:
    """Update workflow product configuration."""
    if workflow_id not in _store:
        raise HTTPException(404, f"Workflow '{workflow_id}' not found")

    wp = _store[workflow_id]
    update_data = req.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(wp, key, value)
    wp.updated_at = datetime.utcnow()
    _store[workflow_id] = wp
    return wp.model_dump()


@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: str) -> dict:
    """Soft-delete (pause) a workflow product."""
    if workflow_id not in _store:
        raise HTTPException(404, f"Workflow '{workflow_id}' not found")

    wp = _store[workflow_id]
    wp.status = "paused"
    wp.updated_at = datetime.utcnow()
    return {"message": f"Workflow '{workflow_id}' paused", "id": workflow_id}


@router.post("/workflows/{workflow_id}/deploy")
def deploy_workflow(workflow_id: str) -> dict:
    """Deploy workflow to n8n instance."""
    if workflow_id not in _store:
        raise HTTPException(404, f"Workflow '{workflow_id}' not found")

    wp = _store[workflow_id]
    try:
        from src.neural_link.api._n8n_client import inject_workflow
        result = inject_workflow(wp.n8n_workflow_json)
        wp.status = "active"
        wp.updated_at = datetime.utcnow()
        return {"message": "Deployed", "n8n_result": result}
    except Exception as e:
        wp.status = "error"
        raise HTTPException(500, f"Deploy failed: {e}")


@router.post("/workflows/{workflow_id}/run")
def run_workflow(workflow_id: str) -> dict:
    """Manually trigger a workflow execution."""
    if workflow_id not in _store:
        raise HTTPException(404, f"Workflow '{workflow_id}' not found")

    wp = _store[workflow_id]
    execution = Execution(
        id=f"ex-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        workflow_product_id=workflow_id,
        status="running",
    )
    wp.executions.append(execution)
    # TODO: Actually trigger n8n workflow via webhook
    return execution.model_dump()


@router.post("/agents/{agent_slug}/execute")
def execute_agent(agent_slug: str, body: dict[str, Any] = {}) -> dict:
    """Execute a specific content agent (called by n8n via webhook)."""
    from src.neural_link.orchestrator.agent_selector import AGENT_REGISTRY
    import importlib

    agent_id = f"content_{agent_slug}"
    if agent_id not in AGENT_REGISTRY:
        raise HTTPException(404, f"Agent '{agent_slug}' not found")

    reg = AGENT_REGISTRY[agent_id]
    module = importlib.import_module(reg["module_path"])
    agent_class = getattr(module, reg["agent_class"])
    agent = agent_class()

    invoke_method = getattr(agent, reg["invoke"])
    result = invoke_method(task=body)
    return result
```

**Step 4: Run test to verify it passes**

Run: `cd C:\labs\inteligence\chunk-generator && python -m pytest tests/content/test_workflow_registry.py -v`
Expected: ALL PASS (7 tests)

**Step 5: Commit**

```bash
git add src/neural_link/api/workflow_registry.py tests/content/test_workflow_registry.py
git commit -m "feat(content): add Workflow Registry CRUD API with agent execution endpoint"
```

---

## Task 10: Wire Registry into Sovereign Gateway

**Files:**
- Modify: `src/neural_link/api/sovereign_gateway.py`
- Test: Manual — verify routes appear

**Step 1: Add router import and include**

In `sovereign_gateway.py`, add after existing router includes:

```python
from src.neural_link.api.workflow_registry import router as workflow_router

app.include_router(workflow_router, prefix="/api/v1")
```

**Step 2: Verify routes**

Run: `cd C:\labs\inteligence\chunk-generator && python -c "from src.neural_link.api.sovereign_gateway import app; print([r.path for r in app.routes if '/workflow' in getattr(r, 'path', '') or '/agents/' in getattr(r, 'path', '')])""`
Expected: List of workflow + agent routes

**Step 3: Commit**

```bash
git add src/neural_link/api/sovereign_gateway.py
git commit -m "feat(content): wire workflow registry routes into sovereign gateway"
```

---

## Task 11: n8n Workflow Template

**Files:**
- Create: `data/workflows/omega-weekly-podcast.json`
- Test: Validate with N8nValidator

**Step 1: Create workflow JSON**

Full n8n workflow with Schedule Trigger → Research → Script → Audio → parallel social → Publish. See design doc section 5 for the complete JSON structure. Each node calls `http://localhost:8766/api/v1/agents/{slug}/execute`.

**Step 2: Validate**

Run: `cd C:\labs\inteligence\chunk-generator && python -c "from src.processors.n8n_validator import N8nFlowValidator; v = N8nFlowValidator.from_reference_dir('data/raw'); r = v.validate('data/workflows/omega-weekly-podcast.json'); print(r.summary())"`
Expected: Valid with possible warnings about custom node types

**Step 3: Commit**

```bash
git add data/workflows/omega-weekly-podcast.json
git commit -m "feat(content): add omega-weekly-podcast n8n workflow template"
```

---

## Task 12: Integration Test — Full Pipeline

**Files:**
- Create: `tests/content/test_pipeline_integration.py`

**Step 1: Write integration test**

```python
# tests/content/test_pipeline_integration.py
"""End-to-end test: Research → Script → Audio → Social → Publish.

Mocks external APIs (Arxiv, HF, GitHub, TTS) but exercises
the full agent chain and data flow.
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.integration
def test_full_podcast_pipeline():
    from src.neural_link.agents.content.research_agent import ResearchAgent
    from src.neural_link.agents.content.script_agent import ScriptAgent
    from src.neural_link.agents.content.thread_agent import ThreadAgent

    # Step 1: Research
    research = ResearchAgent()
    with patch.object(research, "_fetch_arxiv", return_value=[
        {"title": "AI Sales Agent", "source": "arxiv", "url": "http://test",
         "summary": "AI agents close 35% more sales", "category": "paper"}
    ]), patch.object(research, "_fetch_huggingface", return_value=[]), \
       patch.object(research, "_fetch_github_trending", return_value=[]), \
       patch.object(research, "_fetch_producthunt", return_value=[]):

        digest = research.execute({"period": "7d", "sources": "all", "max_items": 5})

    assert len(digest["items"]) == 1
    assert digest["sources_status"]["arxiv"].startswith("ok")

    # Step 2: Script
    script_agent = ScriptAgent()
    mock_script = "[ABERTURA]\nFala pessoal.\n[BLOCO 1]\nEssa semana AI vende mais.\n[FECHAMENTO]\nAte a proxima."

    with patch.object(script_agent, "_load_brand_voice", return_value="Tom direto"), \
         patch.object(script_agent, "_call_llm", return_value=mock_script):

        script = script_agent.execute({
            "digest": digest,
            "brand": "omega",
            "episode_number": 1,
        })

    assert len(script["sections"]) >= 2
    assert "ssml" in script

    # Step 3: Thread (social derivative)
    thread_agent = ThreadAgent()
    mock_thread = "1/ AI vende mais que humano\n\n2/ Paper provou isso\n\n3/ Link na bio"

    with patch.object(thread_agent, "_load_brand_voice", return_value="Tom direto"), \
         patch.object(thread_agent, "_call_llm", return_value=mock_thread):

        thread = thread_agent.execute({"digest": digest})

    assert len(thread["tweets"]) >= 2


@pytest.mark.integration
def test_workflow_registry_with_agents():
    """Test that workflow registry can execute registered agents."""
    from fastapi.testclient import TestClient
    from src.neural_link.api.workflow_registry import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    # Register workflow
    client.post("/api/v1/workflows", json={
        "id": "test-integration",
        "name": "Test",
        "description": "Integration test",
        "category": "content",
        "n8n_workflow_json": {"nodes": []},
        "agents_used": ["content_research"],
    })

    # Verify it exists
    resp = client.get("/api/v1/workflows/test-integration")
    assert resp.status_code == 200
    assert resp.json()["agents_used"] == ["content_research"]
```

**Step 2: Run integration test**

Run: `cd C:\labs\inteligence\chunk-generator && python -m pytest tests/content/test_pipeline_integration.py -v -m integration`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add tests/content/test_pipeline_integration.py
git commit -m "test(content): add full pipeline integration test"
```

---

## Summary

| Task | What | Files | Tests |
|------|------|-------|-------|
| 1 | Content Models | models.py | 11 |
| 2 | Brand Voice | omega_brand_voice.txt | 1 |
| 3 | ResearchAgent | research_agent.py | 6 |
| 4 | ScriptAgent | script_agent.py | 6 |
| 5 | AudioAgent | audio_agent.py | 4 |
| 6 | Social Agents (4) | clip/carousel/thread/linkedin | 8 |
| 7 | PublishAgent | publish_agent.py | 3 |
| 8 | Agent Registry | agent_selector.py | 2 |
| 9 | Workflow Registry API | workflow_registry.py | 7 |
| 10 | Gateway Wiring | sovereign_gateway.py | 1 |
| 11 | n8n Workflow Template | omega-weekly-podcast.json | 1 |
| 12 | Integration Test | test_pipeline_integration.py | 2 |
| **Total** | **12 tasks** | **~18 files** | **~52 tests** |
