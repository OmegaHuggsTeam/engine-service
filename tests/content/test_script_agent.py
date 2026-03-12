"""
Tests for ScriptAgent — LLM-powered podcast script generator for Omega Content Factory.

TDD: These tests are written FIRST. All LLM calls are mocked.
"""

import textwrap
from unittest.mock import MagicMock, patch

import pytest

from src.neural_link.agents.base_agent import BaseAgent
from src.neural_link.agents.content.models import PodcastScript, ScriptSection
from src.neural_link.agents.content.script_agent import ScriptAgent


# ============================================================
# Sample data (fixtures)
# ============================================================

SAMPLE_BRAND_VOICE = "Tecnologia que fecha vendas. Direta, confiavel, brasileira."

SAMPLE_DIGEST_ITEMS = [
    {
        "title": "AI Sales Agent para WhatsApp",
        "summary": "Framework que automatiza vendas pelo WhatsApp usando LLMs.",
    },
    {
        "title": "CRM com IA integrada",
        "summary": "Novo CRM que usa agentes para qualificar leads automaticamente.",
    },
]

SAMPLE_LLM_RESPONSE = textwrap.dedent("""\
[ABERTURA]
E ai, galera! Bem-vindos ao Omega Insights, episodio numero 42.
Hoje a gente vai falar sobre como a IA esta transformando vendas.
Voce sabia que [...] empresas que usam IA vendem 30% mais?

[BLOCO 1 — AI Sales no WhatsApp]
Imagina ter um **agente** respondendo seus leads no WhatsApp 24 horas.
Isso ja e realidade. Um novo framework [...] permite criar bots de venda
que entendem contexto e fecham negocio sozinhos.

[BLOCO 2 — CRM Inteligente]
E nao para por ai. Agora temos CRMs que usam **inteligencia artificial**
pra qualificar leads automaticamente. Chega de perder tempo com lead frio.
O agente analisa [...] o historico e prioriza quem vai comprar.

[FECHAMENTO]
Entao e isso, pessoal. A IA nao e mais futuro — e presente.
Se voce quer automatizar suas vendas, da uma olhada nos links.
Ate o proximo episodio do **Omega Insights**!
""")


# ============================================================
# TestCapabilities
# ============================================================

class TestCapabilities:
    def test_script_agent_has_correct_capabilities(self):
        agent = ScriptAgent()
        assert agent.capabilities == {"copywriting", "script", "podcast", "brand_voice"}

    def test_script_agent_inherits_base_agent(self):
        agent = ScriptAgent()
        assert isinstance(agent, BaseAgent)


# ============================================================
# TestBuildPrompt
# ============================================================

class TestBuildPrompt:
    def test_build_prompt_includes_brand_voice(self):
        agent = ScriptAgent()
        prompt = agent._build_prompt(
            digest=SAMPLE_DIGEST_ITEMS,
            brand_voice=SAMPLE_BRAND_VOICE,
            episode_number=42,
        )
        assert SAMPLE_BRAND_VOICE in prompt
        assert "42" in prompt
        assert "AI Sales Agent para WhatsApp" in prompt


# ============================================================
# TestParseScript
# ============================================================

class TestParseScript:
    def test_parse_script_response_creates_podcast_script(self):
        """Parse raw LLM text with [ABERTURA]/[BLOCO N]/[FECHAMENTO] markers."""
        agent = ScriptAgent()
        script = agent._parse_script(SAMPLE_LLM_RESPONSE, episode_number=42)

        assert isinstance(script, PodcastScript)
        assert script.episode_number == 42

        # Should have 4 sections: ABERTURA + 2 BLOCOs + FECHAMENTO
        assert len(script.sections) == 4

        # Check section types
        assert script.sections[0].type == "abertura"
        assert script.sections[1].type == "bloco"
        assert script.sections[2].type == "bloco"
        assert script.sections[3].type == "fechamento"

        # Check titles
        assert script.sections[1].title == "AI Sales no WhatsApp"
        assert script.sections[2].title == "CRM Inteligente"

        # Content should be populated
        assert len(script.sections[0].content) > 0
        assert "WhatsApp" in script.sections[1].content

        # Duration estimate should be positive
        assert script.duration_estimate > 0

        # SSML and plain_text should be populated
        assert len(script.ssml) > 0
        assert len(script.plain_text) > 0


# ============================================================
# TestSSML
# ============================================================

class TestSSML:
    def test_generate_ssml_wraps_in_speak_tags(self):
        """[...] becomes <break time='600ms'/>, **word** becomes <emphasis>."""
        agent = ScriptAgent()

        text = "Voce sabia que [...] empresas usam **inteligencia artificial** para vender?"
        ssml = agent._generate_ssml(text)

        assert ssml.startswith("<speak>")
        assert ssml.endswith("</speak>")
        assert '<break time="600ms"/>' in ssml
        assert "<emphasis>inteligencia artificial</emphasis>" in ssml
        assert "[...]" not in ssml
        assert "**" not in ssml


# ============================================================
# TestExecute
# ============================================================

class TestExecute:
    @patch.object(ScriptAgent, "_call_llm", return_value=SAMPLE_LLM_RESPONSE)
    @patch.object(ScriptAgent, "_load_brand_voice", return_value=SAMPLE_BRAND_VOICE)
    def test_execute_calls_llm_and_returns_dict(self, mock_brand_voice, mock_llm):
        """execute() should load brand voice, call LLM, and return PodcastScript dict."""
        agent = ScriptAgent()
        result = agent.execute(
            task="generate podcast script",
            digest=SAMPLE_DIGEST_ITEMS,
            episode_number=42,
        )

        # Should have called both mocked methods
        mock_brand_voice.assert_called_once()
        mock_llm.assert_called_once()

        # Result should be a dict (model_dump output)
        assert isinstance(result, dict)

        # Validate it conforms to PodcastScript
        script = PodcastScript(**result)
        assert script.episode_number == 42
        assert len(script.sections) >= 1
        assert len(script.ssml) > 0
        assert len(script.plain_text) > 0
        assert script.duration_estimate > 0
