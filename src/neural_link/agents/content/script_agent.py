"""
ScriptAgent — LLM-powered podcast script generator for Omega Content Factory.

Takes a research digest and brand voice, generates a structured podcast script
with SSML annotations for TTS rendering.

Sections:
- [ABERTURA] — Opening hook with engaging question or stat
- [BLOCO N — Title] — Content segments (one per topic)
- [FECHAMENTO] — Closing with CTA

SSML markers:
- [...] → <break time="600ms"/> (natural pause)
- **word** → <emphasis>word</emphasis> (stress/emphasis)
"""

import logging
import re
from pathlib import Path
from typing import Any

from src.neural_link.agents.base_agent import BaseAgent
from src.neural_link.agents.content.models import PodcastScript, ScriptSection

logger = logging.getLogger(__name__)

BRAND_VOICE_PATH = Path("vault/Knowledge/omega_brand_voice.txt")


class ScriptAgent(BaseAgent):
    """
    Agent that generates podcast scripts from research digests using LLM + brand voice.

    Inherits from BaseAgent with capabilities:
    {"copywriting", "script", "podcast", "brand_voice"}
    """

    @property
    def capabilities(self) -> set[str]:
        return {"copywriting", "script", "podcast", "brand_voice"}

    def execute(self, task: str, **kwargs: Any) -> dict:
        """
        Generate a podcast script from a research digest.

        Args:
            task: Description of the script generation task.
            **kwargs: Required/optional overrides:
                - digest (list[dict]): Research items with title/summary.
                - episode_number (int): Episode number. Default 1.

        Returns:
            dict: PodcastScript.model_dump() with sections, SSML, plain text.
        """
        digest = kwargs.get("digest", [])
        episode_number = kwargs.get("episode_number", 1)

        brand_voice = self._load_brand_voice()
        prompt = self._build_prompt(digest, brand_voice, episode_number)
        raw_response = self._call_llm(prompt)
        script = self._parse_script(raw_response, episode_number)

        return script.model_dump()

    # ------------------------------------------------------------------
    # Brand voice
    # ------------------------------------------------------------------

    def _load_brand_voice(self) -> str:
        """Load brand voice from vault file. Returns fallback if missing."""
        try:
            return BRAND_VOICE_PATH.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning(
                "Brand voice file not found at %s, using fallback.", BRAND_VOICE_PATH
            )
            return "Tom direto, confiavel, brasileiro. Fale como gente, nao como manual."

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def _build_prompt(
        self, digest: list[dict], brand_voice: str, episode_number: int
    ) -> str:
        """Build LLM prompt combining digest items + brand voice + instructions."""
        items_text = ""
        for i, item in enumerate(digest, 1):
            title = item.get("title", "Sem titulo")
            summary = item.get("summary", "")
            items_text += f"\n{i}. {title}\n   {summary}\n"

        return f"""Voce e um roteirista de podcast da Omega.

=== BRAND VOICE ===
{brand_voice}

=== EPISODIO ===
Numero: {episode_number}

=== ITENS DE PESQUISA ===
{items_text}

=== INSTRUCOES ===
Gere um roteiro de podcast com as seguintes secoes:
- [ABERTURA]: Gancho inicial com pergunta ou dado impactante (30-60 segundos)
- [BLOCO N — Titulo]: Um bloco por item de pesquisa relevante (1-2 minutos cada)
- [FECHAMENTO]: CTA claro e despedida (30 segundos)

Use [...] para pausas naturais e **palavra** para enfase.
Maximo 5-8 minutos total. Frases curtas. Tom direto e humano.
"""

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    def _call_llm(self, prompt: str) -> str:
        """Call LLM to generate script. Falls back to stub if LLMClient unavailable."""
        try:
            from src.utils.llm_client import LLMClient  # type: ignore[import-not-found]

            client = LLMClient()
            return client.generate(prompt)
        except ImportError:
            logger.warning(
                "LLMClient not available. Returning stub response for development."
            )
            return (
                "[ABERTURA]\n"
                "Bem-vindos ao Omega Insights!\n\n"
                "[BLOCO 1 — Placeholder]\n"
                "Conteudo de desenvolvimento.\n\n"
                "[FECHAMENTO]\n"
                "Ate o proximo episodio!\n"
            )

    # ------------------------------------------------------------------
    # Script parsing
    # ------------------------------------------------------------------

    def _parse_script(self, raw: str, episode_number: int) -> PodcastScript:
        """Parse raw LLM response into structured PodcastScript.

        Recognizes section headers:
        - [ABERTURA]
        - [BLOCO N — Title]  or  [BLOCO N - Title]
        - [FECHAMENTO]
        """
        # Pattern matches section headers: [ABERTURA], [BLOCO 1 — Title], [FECHAMENTO]
        section_pattern = re.compile(
            r"\[(ABERTURA|BLOCO\s+\d+\s*[—\-]\s*(.+?)|FECHAMENTO)\]",
            re.IGNORECASE,
        )

        sections: list[ScriptSection] = []
        matches = list(section_pattern.finditer(raw))

        for i, match in enumerate(matches):
            header = match.group(1).strip()
            # Extract content: from end of this header to start of next (or end of string)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
            content = raw[start:end].strip()

            # Determine section type and title
            if header.upper() == "ABERTURA":
                section_type = "abertura"
                title = "Abertura"
            elif header.upper() == "FECHAMENTO":
                section_type = "fechamento"
                title = "Fechamento"
            else:
                section_type = "bloco"
                # Extract title from "BLOCO N — Title"
                title_match = re.match(
                    r"BLOCO\s+\d+\s*[—\-]\s*(.+)", header, re.IGNORECASE
                )
                title = title_match.group(1).strip() if title_match else header

            duration = self._estimate_duration(content)

            sections.append(
                ScriptSection(
                    type=section_type,
                    title=title,
                    content=content,
                    duration_estimate=duration,
                )
            )

        # Build full plain text and SSML
        plain_text = "\n\n".join(s.content for s in sections)
        ssml = self._generate_ssml(plain_text)
        total_duration = sum(s.duration_estimate for s in sections)

        # Generate title
        bloco_titles = [s.title for s in sections if s.type == "bloco"]
        episode_title = (
            f"Omega Insights #{episode_number}: {', '.join(bloco_titles)}"
            if bloco_titles
            else f"Omega Insights #{episode_number}"
        )

        return PodcastScript(
            title=episode_title,
            episode_number=episode_number,
            duration_estimate=total_duration,
            sections=sections,
            ssml=ssml,
            plain_text=plain_text,
        )

    # ------------------------------------------------------------------
    # SSML generation
    # ------------------------------------------------------------------

    def _generate_ssml(self, text: str) -> str:
        """Convert plain text with markers to SSML.

        Conversions:
        - [...] → <break time="600ms"/>
        - **word or phrase** → <emphasis>word or phrase</emphasis>
        """
        result = text
        # Replace [...] with SSML break
        result = result.replace("[...]", '<break time="600ms"/>')
        # Replace **word** with SSML emphasis
        result = re.sub(r"\*\*(.+?)\*\*", r"<emphasis>\1</emphasis>", result)
        return f"<speak>{result}</speak>"

    # ------------------------------------------------------------------
    # Duration estimation
    # ------------------------------------------------------------------

    def _estimate_duration(self, text: str) -> int:
        """Estimate speech duration in seconds for pt-BR (~150 words/min).

        Returns:
            int: Duration in seconds.
        """
        word_count = len(text.split())
        # 150 words/min = 2.5 words/sec
        seconds = word_count / 2.5
        return max(1, int(round(seconds)))
