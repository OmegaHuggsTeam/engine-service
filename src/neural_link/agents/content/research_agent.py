"""
ResearchAgent — Multi-source content research collector for Omega Content Factory.

Collects trending AI/business content from:
- Arxiv (academic papers via Atom XML API)
- HuggingFace (trending models via JSON API)
- GitHub (trending repositories via search API)
- ProductHunt (new products via GraphQL, requires PRODUCTHUNT_TOKEN)

Ranks items by relevance to the Omega audience:
business owners using AI for sales automation.
"""

import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import httpx

from src.neural_link.agents.base_agent import BaseAgent
from src.neural_link.agents.content.models import ResearchDigest, ResearchItem

logger = logging.getLogger(__name__)

TIMEOUT = 15  # seconds per source

# Keyword weights for relevance scoring (Omega audience: AI for sales/business)
HIGH_RELEVANCE_KEYWORDS = {
    "sales": 0.25,
    "conversion": 0.20,
    "customer": 0.15,
    "whatsapp": 0.20,
    "agent": 0.10,
    "automation": 0.15,
    "commerce": 0.15,
    "crm": 0.20,
    "chatbot": 0.15,
    "revenue": 0.15,
    "lead": 0.10,
    "engagement": 0.10,
}

LOW_RELEVANCE_KEYWORDS = {
    "benchmark": -0.15,
    "theory": -0.15,
    "theoretical": -0.15,
    "bounds": -0.10,
    "abstract": -0.05,
    "proof": -0.10,
}

# Arxiv Atom XML namespace
ATOM_NS = "http://www.w3.org/2005/Atom"


class ResearchAgent(BaseAgent):
    """
    Agent that collects and curates AI/business research from multiple sources.

    Inherits from BaseAgent with capabilities:
    {"research", "papers", "trends", "curation"}
    """

    @property
    def capabilities(self) -> set[str]:
        return {"research", "papers", "trends", "curation"}

    def execute(self, task: str, **kwargs: Any) -> dict:
        """
        Execute a research collection task.

        Args:
            task: Description of the research task.
            **kwargs: Optional overrides:
                - query (str): Search query for Arxiv. Default "AI agent sales automation".
                - top_n (int): Max items to return. Default 10.

        Returns:
            dict: ResearchDigest.model_dump() with ranked items and source statuses.
        """
        query = kwargs.get("query", "AI agent sales automation")
        top_n = kwargs.get("top_n", 10)

        all_items: list[ResearchItem] = []
        sources_status: dict[str, str] = {}

        # Collect from all sources
        for source_name, fetcher, fetch_kwargs in [
            ("arxiv", self._fetch_arxiv, {"query": query}),
            ("huggingface", self._fetch_huggingface, {}),
            ("github", self._fetch_github_trending, {}),
            ("producthunt", self._fetch_producthunt, {}),
        ]:
            try:
                items = fetcher(**fetch_kwargs)
                all_items.extend(items)
                sources_status[source_name] = f"ok ({len(items)} items)"
            except Exception as exc:
                logger.warning("Source %s failed: %s", source_name, exc)
                sources_status[source_name] = f"error: {exc}"

        # Rank and trim
        ranked = self._rank_items(all_items)
        top_items = ranked[:top_n]

        digest = ResearchDigest(
            items=top_items,
            period=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            total_collected=len(all_items),
            sources_status=sources_status,
        )

        return digest.model_dump()

    # ------------------------------------------------------------------
    # Source fetchers
    # ------------------------------------------------------------------

    def _fetch_arxiv(self, query: str = "AI agent sales automation") -> list[ResearchItem]:
        """Fetch papers from Arxiv API (Atom XML)."""
        try:
            url = "http://export.arxiv.org/api/query"
            params = {
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": 20,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            resp = httpx.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            return self._parse_arxiv_xml(resp.text)
        except Exception as exc:
            logger.warning("Arxiv fetch failed: %s", exc)
            return []

    def _parse_arxiv_xml(self, xml_text: str) -> list[ResearchItem]:
        """Parse Arxiv Atom XML feed into ResearchItems."""
        items: list[ResearchItem] = []
        root = ET.fromstring(xml_text)

        for entry in root.findall(f"{{{ATOM_NS}}}entry"):
            title_el = entry.find(f"{{{ATOM_NS}}}title")
            summary_el = entry.find(f"{{{ATOM_NS}}}summary")
            link_el = entry.find(f"{{{ATOM_NS}}}link")

            title = title_el.text.strip() if title_el is not None and title_el.text else "Untitled"
            summary = (
                summary_el.text.strip()
                if summary_el is not None and summary_el.text
                else ""
            )
            url = link_el.get("href", "") if link_el is not None else ""

            items.append(
                ResearchItem(
                    title=title,
                    source="arxiv",
                    url=url,
                    summary=summary[:500],
                    relevance_score=0.0,
                    relevance_reason="",
                    category="research",
                )
            )

        return items

    def _fetch_huggingface(self) -> list[ResearchItem]:
        """Fetch trending models from HuggingFace API."""
        try:
            url = "https://huggingface.co/api/models"
            params = {"sort": "trending", "limit": 20}
            resp = httpx.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            items: list[ResearchItem] = []
            for model in data:
                model_id = model.get("modelId", model.get("id", "unknown"))
                tags = model.get("tags", [])
                likes = model.get("likes", 0)
                downloads = model.get("downloads", 0)

                items.append(
                    ResearchItem(
                        title=model_id,
                        source="huggingface",
                        url=f"https://huggingface.co/{model_id}",
                        summary=f"Tags: {', '.join(tags[:5])}. Likes: {likes}, Downloads: {downloads}",
                        relevance_score=0.0,
                        relevance_reason="",
                        category="model",
                    )
                )

            return items
        except Exception as exc:
            logger.warning("HuggingFace fetch failed: %s", exc)
            return []

    def _fetch_github_trending(self) -> list[ResearchItem]:
        """Fetch trending AI repositories from GitHub search API."""
        try:
            url = "https://api.github.com/search/repositories"
            params = {
                "q": "AI agent sales automation",
                "sort": "stars",
                "order": "desc",
                "per_page": 20,
            }
            resp = httpx.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            items: list[ResearchItem] = []
            for repo in data.get("items", []):
                items.append(
                    ResearchItem(
                        title=repo.get("full_name", "unknown"),
                        source="github",
                        url=repo.get("html_url", ""),
                        summary=repo.get("description", "") or "",
                        relevance_score=0.0,
                        relevance_reason="",
                        category="repository",
                    )
                )

            return items
        except Exception as exc:
            logger.warning("GitHub trending fetch failed: %s", exc)
            return []

    def _fetch_producthunt(self) -> list[ResearchItem]:
        """Fetch new AI products from ProductHunt GraphQL API.

        Requires PRODUCTHUNT_TOKEN env var. Skips gracefully if not set.
        """
        token = os.environ.get("PRODUCTHUNT_TOKEN")
        if not token:
            logger.info("PRODUCTHUNT_TOKEN not set, skipping ProductHunt source.")
            return []

        try:
            url = "https://api.producthunt.com/v2/api/graphql"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            query = """
            {
                posts(first: 20, order: RANKING) {
                    edges {
                        node {
                            name
                            tagline
                            url
                            votesCount
                            topics {
                                edges {
                                    node {
                                        name
                                    }
                                }
                            }
                        }
                    }
                }
            }
            """
            resp = httpx.post(
                url,
                json={"query": query},
                headers=headers,
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            items: list[ResearchItem] = []
            edges = data.get("data", {}).get("posts", {}).get("edges", [])
            for edge in edges:
                node = edge.get("node", {})
                topics = [
                    t["node"]["name"]
                    for t in node.get("topics", {}).get("edges", [])
                ]
                items.append(
                    ResearchItem(
                        title=node.get("name", "Unknown"),
                        source="producthunt",
                        url=node.get("url", ""),
                        summary=f"{node.get('tagline', '')}. Topics: {', '.join(topics)}",
                        relevance_score=0.0,
                        relevance_reason="",
                        category="product",
                    )
                )

            return items
        except Exception as exc:
            logger.warning("ProductHunt fetch failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------

    def _rank_items(self, items: list[ResearchItem]) -> list[ResearchItem]:
        """Rank items by relevance to Omega audience (AI for sales/business).

        Uses keyword-based scoring on title + summary text.
        Returns items sorted by relevance_score descending.
        """
        scored: list[ResearchItem] = []
        for item in items:
            score, reasons = self._score_relevance(item)
            scored.append(
                item.model_copy(
                    update={
                        "relevance_score": score,
                        "relevance_reason": "; ".join(reasons) if reasons else "No strong signals",
                    }
                )
            )

        scored.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored

    def _score_relevance(self, item: ResearchItem) -> tuple[float, list[str]]:
        """Score a single item's relevance to Omega audience.

        Returns:
            Tuple of (score 0.0-1.0, list of reason strings).
        """
        text = f"{item.title} {item.summary}".lower()
        score = 0.3  # base score
        reasons: list[str] = []

        for keyword, weight in HIGH_RELEVANCE_KEYWORDS.items():
            if keyword in text:
                score += weight
                reasons.append(f"'{keyword}' (+{weight})")

        for keyword, penalty in LOW_RELEVANCE_KEYWORDS.items():
            if keyword in text:
                score += penalty  # penalty is negative
                reasons.append(f"'{keyword}' ({penalty})")

        # Clamp to [0.0, 1.0]
        score = max(0.0, min(1.0, score))

        return score, reasons
