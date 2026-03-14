"""
SpecialistAgent - Knowledge-Powered Agent com Prompt Decorator e Creative Synthesis.

Herda de BaseAgent. Carrega conhecimento por categoria (chunk_type),
injeta top 5 chunks relevantes como Contexto de Referência antes de cada tarefa,
e oferece modo creative_synthesis para propor conexões entre chunks.
"""

import copy
import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Any, Optional

import httpx

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CHUNKS_DIR = PROJECT_ROOT / "data" / "chunks"
TOP_K_CONTEXT = 5


def _load_chunks_from_json(chunks_dir: Path, chunk_type: str) -> list[dict]:
    """Carrega chunks de arquivos JSON, filtrados por category ou source_file."""
    if not chunks_dir.exists():
        return []

    ct_lower = chunk_type.lower()
    all_chunks = []

    for json_file in chunks_dir.glob("*.json"):
        try:
            raw = json_file.read_text(encoding="utf-8").strip()
            if not raw:
                continue
            data = json.loads(raw)
            items = data if isinstance(data, list) else data.get("chunks", [])
            for c in items:
                if not isinstance(c, dict) or not c.get("content"):
                    continue
                cat = (c.get("category") or "").lower()
                specialty = (c.get("agent_specialty") or "").lower()
                source = (c.get("source_file") or "").lower()
                if ct_lower in (cat, specialty) or ct_lower in source:
                    all_chunks.append(c)
        except (json.JSONDecodeError, OSError) as e:
            logger.debug("Erro ao ler %s: %s", json_file.name, e)

    return all_chunks


def _search_chunks(chunks: list[dict], query: str, top_k: int = TOP_K_CONTEXT) -> list[dict]:
    """Retorna os top_k chunks mais relevantes para a query (busca dentro da lista)."""
    if not chunks:
        return []

    # TF-IDF se disponível
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        contents = [c.get("content", "") for c in chunks]
        if contents and any(contents):
            vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
            doc_matrix = vectorizer.fit_transform(contents)
            query_vec = vectorizer.transform([query])
            scores = cosine_similarity(query_vec, doc_matrix).flatten()

            # Score-based filtering: remove low-relevance noise
            scored_chunks = []
            for i, score in enumerate(scores):
                if score >= 0.35:  # Score threshold
                    chunk = chunks[i].copy()
                    chunk["score"] = float(score)
                    scored_chunks.append(chunk)

            # Sort by score and take top_k
            scored_chunks.sort(key=lambda x: x["score"], reverse=True)
            result = scored_chunks[:top_k]

            # Apply adaptive truncation: higher score = more content
            for chunk in result:
                score = chunk.get("score", 0.5)
                max_chars = max(100, int(500 * score))
                content = chunk.get("content", "")
                if len(content) > max_chars:
                    chunk["content"] = content[:max_chars]

            if result:
                return result
    except ImportError:
        pass

    # Fallback: busca por palavras-chave
    query_words = set(w.lower() for w in query.split() if len(w) > 2)
    scored = []
    for c in chunks:
        content = (c.get("content") or "").lower()
        matches = sum(1 for w in query_words if w in content)
        if matches > 0:
            scored.append((matches, c))
    scored.sort(key=lambda x: -x[0])
    result = [c for _, c in scored[:top_k]]
    if result:
        return result
    return chunks[:top_k]


def _build_context_block(chunks: list[dict]) -> str:
    """Monta o bloco de Contexto de Referência para o prompt."""
    if not chunks:
        return ""
    parts = []
    for i, c in enumerate(chunks, 1):
        content = c.get("content", "")
        source = c.get("source_file", "N/A")
        parts.append(f"[Referência {i} - {source}]\n{content}")
    return "\n\n---\n\n".join(parts)


def _credential_to_env_var(cred_type: str) -> str:
    """
    Converte nome CamelCase de credencial para UPPER_SNAKE_CASE.

    Exemplos:
        "groqApi" -> "GROQ_API"
        "googleSheetsOAuth2Api" -> "GOOGLE_SHEETS_OAUTH2_API"
    """
    # Insert underscore before uppercase letters preceded by lowercase
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", cred_type)
    # Insert underscore between consecutive uppercase and following lowercase
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    return s.upper()


def _extract_expressions(raw_json: str) -> list[dict]:
    """
    Faz scan de expressoes n8n no JSON bruto.

    Detecta patterns:
      - {{ $('NodeName').item.json.fieldName }}
      - {{ $node["NodeName"].json["fieldName"] }}

    Returns:
        Lista de dicts {"node": str, "field": str} (deduplicada).
    """
    results: list[dict] = []
    seen: set[tuple[str, str]] = set()

    # Modern pattern: {{ $('NodeName').item.json.fieldPath }}
    for m in re.finditer(r"\{\{\s*\$\('([^']+)'\)\.item\.json\.(\w+)", raw_json):
        key = (m.group(1), m.group(2))
        if key not in seen:
            seen.add(key)
            results.append({"node": m.group(1), "field": m.group(2)})

    # Legacy pattern: {{ $node["NodeName"].json["fieldName"] }}
    # In raw JSON the quotes may appear as \" (escaped)
    for m in re.finditer(
        r'\{\{\s*\$node\[\\?"([^"\\]+)\\?"\]\.json\[\\?"([^"\\]+)\\?"\]', raw_json
    ):
        key = (m.group(1), m.group(2))
        if key not in seen:
            seen.add(key)
            results.append({"node": m.group(1), "field": m.group(2)})

    return results


def _adapt_workflow_json(workflow_data: dict) -> tuple[str, list[str]]:
    """
    Deep-copia o workflow e substitui credential id/name por {{ $env.VAR }}.

    Returns:
        (json_adaptado_str, lista_de_linhas_env)
    """
    adapted = copy.deepcopy(workflow_data)
    env_lines: list[str] = []
    seen_creds: set[str] = set()

    for node in adapted.get("nodes", []):
        creds = node.get("credentials", {})
        if not isinstance(creds, dict):
            continue
        for cred_type, cred_value in creds.items():
            env_var = _credential_to_env_var(cred_type)
            if cred_type not in seen_creds:
                seen_creds.add(cred_type)
                env_lines.append(f"{env_var}_ID=<seu-id-aqui>")
                env_lines.append(f"{env_var}_NAME=<seu-nome-aqui>")
            if isinstance(cred_value, dict):
                cred_value["id"] = "{{ $env." + env_var + "_ID }}"
                cred_value["name"] = "{{ $env." + env_var + "_NAME }}"

    adapted_str = json.dumps(adapted, indent=2, ensure_ascii=False)
    return adapted_str, env_lines


class SpecialistAgent(BaseAgent):
    """
    Agente especialista alimentado por conhecimento (chunks).
    - load_knowledge(chunk_type): carrega chunks filtrados por categoria
    - Prompt Decorator: injeta top 5 chunks como Contexto de Referência
    - creative_synthesis: propõe conexão entre chunk A (Trigger) e chunk B (Action)
    """

    def __init__(
        self,
        capabilities: Optional[set[str]] = None,
        chunks_dir: Path = CHUNKS_DIR,
    ):
        self._capabilities = capabilities or set()
        self._chunks_dir = chunks_dir
        self._knowledge: list[dict] = []
        self._chunk_type_loaded: Optional[str] = None

    @property
    def capabilities(self) -> set[str]:
        return self._capabilities

    def load_knowledge(self, chunk_type: str) -> list[dict]:
        """
        Busca no extrator de chunks todos os dados filtrados por categoria.

        Args:
            chunk_type: Categoria (ex: 'n8n_templates', 'Uncategorized').

        Returns:
            Lista de chunks filtrados.
        """
        self._knowledge = []
        self._chunk_type_loaded = chunk_type

        try:
            from src.utils.vector_db import get_by_category

            self._knowledge = get_by_category(chunk_type)
        except Exception as e:
            logger.debug("ChromaDB get_by_category falhou: %s", e)

        if not self._knowledge:
            self._knowledge = _load_chunks_from_json(self._chunks_dir, chunk_type)

        logger.info(
            "SpecialistAgent: load_knowledge(%s) -> %d chunks",
            chunk_type,
            len(self._knowledge),
        )
        return self._knowledge

    def _decorate_prompt(self, task: str, query: Optional[str] = None) -> str:
        """
        Prompt Decorator: injeta os top 5 chunks mais relevantes como
        'Contexto de Referência' antes da tarefa.
        """
        search_query = query or task
        top_chunks = _search_chunks(self._knowledge, search_query, top_k=TOP_K_CONTEXT)
        context_block = _build_context_block(top_chunks)

        if not context_block:
            return task

        return (
            "## Contexto de Referência\n\n"
            "Use o material abaixo como base para sua resposta. "
            "Responda com base nesse conhecimento.\n\n"
            f"{context_block}\n\n"
            "---\n\n"
            f"## Tarefa\n\n{task}"
        )

    def execute(
        self,
        task: str,
        *,
        mode: str = "default",
        chunk_a: Optional[dict] = None,
        chunk_b: Optional[dict] = None,
        chunk_type: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """
        Executa a tarefa. Antes de cada execução, injeta top 5 chunks como contexto.

        Args:
            task: Descrição da tarefa.
            mode: 'default' ou 'creative_synthesis'.
            chunk_a: Chunk Trigger (para creative_synthesis).
            chunk_b: Chunk Action (para creative_synthesis).
            chunk_type: Categoria para load_knowledge (se ainda não carregado).
        """
        if chunk_type and (not self._knowledge or self._chunk_type_loaded != chunk_type):
            self.load_knowledge(chunk_type)

        if mode == "creative_synthesis":
            return self._creative_synthesis(chunk_a, chunk_b, task)

        decorated = self._decorate_prompt(task, query=kwargs.get("query"))
        return self._invoke_llm(decorated, **kwargs)

    def _creative_synthesis(
        self,
        chunk_a: Optional[dict],
        chunk_b: Optional[dict],
        task: str = "",
    ) -> str:
        """
        Modo creative_synthesis: olha para chunk A (Trigger) e chunk B (Action)
        e propõe uma conexão baseada no que aprendeu.
        """
        if not chunk_a or not chunk_b:
            return (
                "creative_synthesis requer chunk_a (Trigger) e chunk_b (Action). "
                "Forneça ambos como argumentos."
            )

        content_a = chunk_a.get("content", "")[:800]
        content_b = chunk_b.get("content", "")[:800]
        source_a = chunk_a.get("source_file", "Chunk A")
        source_b = chunk_b.get("source_file", "Chunk B")

        prompt = (
            "## Chunk A (Trigger)\n"
            f"Fonte: {source_a}\n\n{content_a}\n\n"
            "## Chunk B (Action)\n"
            f"Fonte: {source_b}\n\n{content_b}\n\n"
            "---\n\n"
            "Com base no que você aprendeu desses dois chunks, proponha uma **conexão** "
            "entre eles: como o Trigger (A) pode disparar ou alimentar a Action (B)? "
            "Sugira um fluxo, integração ou automação concreta. Seja específico e prático."
        )
        if task:
            prompt += f"\n\nContexto adicional: {task}"

        return self._invoke_llm(prompt)

    def _invoke_llm(self, prompt: str, **kwargs: Any) -> str:
        """Invoca o LLM com o prompt decorado."""
        try:
            from src.utils.llm_client import chat_completion

            system = (
                "Você é um especialista que responde com base exclusivamente "
                "no Contexto de Referência fornecido. Seja preciso e prático."
            )
            return chat_completion(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                **{k: v for k, v in kwargs.items() if k in ("model",)},
            )
        except Exception as e:
            logger.error("SpecialistAgent LLM invoke failed: %s", e)
            return f"[Erro ao invocar LLM: {e}]"

    def analyze_pod_logs(
        self,
        logs: str,
        *,
        pod_name: str = "",
        namespace: str = "",
        chunk_type: str = "k8s_error_patterns",
    ) -> str:
        """
        Analisa logs de Pod em CrashLoopBackOff usando conhecimento de padrões de erro Kubernetes.

        Identifica padrões de erro comuns (conexão, autenticação, configuração, recursos, etc.)
        e fornece sugestões de correção baseadas em conhecimento especializado.

        Args:
            logs: Conteúdo dos logs do Pod (últimas 100 linhas recomendadas)
            pod_name: Nome do Pod (para contexto)
            namespace: Namespace (para contexto)
            chunk_type: Conhecimento a carregar (default: k8s_error_patterns)

        Returns:
            Sugestão de correção em linguagem natural com análise de causa raiz
        """
        if not logs or not logs.strip():
            return "Logs vazios. Verifique se o Pod está gerando logs."

        # Load Kubernetes error patterns knowledge base
        if not self._knowledge or self._chunk_type_loaded != chunk_type:
            self.load_knowledge(chunk_type)

        # Build comprehensive analysis prompt with structured output
        task = (
            "Analise os logs de um Pod Kubernetes em CrashLoopBackOff.\n\n"
            "## Logs do Pod\n```\n"
            f"{logs[:4000]}\n```\n\n"
            "## Análise Requerida\n"
            "1. **Identificar Padrão de Erro**: Classifique o erro principal:\n"
            "   - Conexão/Rede (connection refused, timeout, DNS, etc.)\n"
            "   - Autenticação/Autorização (401, 403, auth failed, token inválido)\n"
            "   - Configuração (config not found, missing env var, parse error)\n"
            "   - Recursos (OOMKilled, memory limit, CPU, disk pressure)\n"
            "   - Imagem (ImagePullBackOff, registry errors)\n"
            "   - Volume/Mount (mount failed, PVC not found)\n"
            "   - Health Checks (liveness/readiness probe failed)\n"
            "   - Database (connection failed, auth error)\n"
            "   - Dependências (ModuleNotFoundError, command not found)\n"
            "   - Permissões (permission denied, read-only filesystem)\n"
            "   - Outro (descreva)\n\n"
            "2. **Causa Raiz**: Identifique a causa raiz específica do problema\n\n"
            "3. **Sugestão de Correção**: Forneça passos práticos e objetivos para resolver:\n"
            "   - Comandos kubectl específicos se aplicável\n"
            "   - Mudanças de configuração necessárias\n"
            "   - Verificações a realizar\n\n"
            "Seja conciso mas completo. Priorize ações que podem ser tomadas imediatamente."
        )

        # Add Pod context if provided
        if pod_name or namespace:
            task = f"**Pod**: {pod_name} (namespace: {namespace})\n\n" + task

        try:
            return self.execute(task, chunk_type=chunk_type)
        except Exception as e:
            logger.error("analyze_pod_logs failed: %s", e)
            return f"[Falha na análise: {e}]"

    def explain_and_adapt(self, url: str) -> str:
        """
        Baixa um workflow n8n de uma URL, analisa, e retorna explicacao
        em Portugues + JSON adaptado no formato Telegram Markdown.

        Flow:
          1. Download JSON via httpx
          2. Parse e valida (precisa de "nodes")
          3. Extrai modulos via extract_operation_modules
          4. Classifica via classify_workflow
          5. Monta resumo deterministico (sem LLM)
          6. Escaneia expressoes entre nodes
          7. Adapta credenciais para $env
          8. Formata e retorna Telegram Markdown
        """
        from src.extractors.n8n_extractor import _extract_service_name, extract_operation_modules
        from src.processors.n8n_knowledge import classify_workflow

        # 1. Download
        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                r = client.get(url)
                r.raise_for_status()
                raw_json = r.text
        except Exception as e:
            logger.error("explain_and_adapt download failed: %s", e)
            return f"*Erro ao baixar workflow:* {e}"

        # 2. Parse JSON
        try:
            workflow_data = json.loads(raw_json)
        except json.JSONDecodeError as e:
            return f"*Erro ao parsear JSON:* {e}"

        if not isinstance(workflow_data, dict) or "nodes" not in workflow_data:
            return "*Erro:* JSON nao parece ser um workflow n8n (chave 'nodes' ausente)."

        # 3. Extract modules via temp file
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as f:
                f.write(raw_json)
                tmp_path = f.name

            try:
                modules = extract_operation_modules(tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        except Exception as e:
            logger.error("explain_and_adapt extraction failed: %s", e)
            return f"*Erro ao extrair modulos:* {e}"

        # 4. Classify
        category = classify_workflow(modules)

        # 5. Build deterministic Portuguese summary
        workflow_name = workflow_data.get("name", "Workflow sem nome")
        ordered_nodes = sorted(modules, key=lambda m: m["chunk_index"])
        chain = " -> ".join(_extract_service_name(m["node_type"]) for m in ordered_nodes)
        services = sorted({m["service"] for m in modules})
        cred_types = sorted({c for m in modules for c in m.get("credential_types", [])})

        # 6. Scan expressions
        expressions = _extract_expressions(raw_json)

        # 7. Adapt credentials
        adapted_json, env_lines = _adapt_workflow_json(workflow_data)

        # 8. Format Telegram Markdown
        parts: list[str] = []

        parts.append(f"*{workflow_name}*")
        parts.append(f"_Categoria: {category}_")
        parts.append("")

        parts.append("*Objetivo do Fluxo*")
        parts.append(f"Fluxo com {len(modules)} nodes operacionais.")
        parts.append(f"Cadeia: `{chain}`")
        parts.append("")

        parts.append("*Servicos Necessarios*")
        for svc in services:
            parts.append(f"- {svc}")
        parts.append("")

        if cred_types:
            parts.append("*Credenciais*")
            for cred in cred_types:
                env_var = _credential_to_env_var(cred)
                parts.append(f"- `{cred}` -> `{env_var}`")
            parts.append("")

        if expressions:
            parts.append("*Dicas de Configuracao*")
            parts.append(
                f"O workflow usa {len(expressions)} expressao(oes) "
                "referenciando dados entre nodes:"
            )
            for expr in expressions:
                parts.append(f"- Node `{expr['node']}` campo `{expr['field']}`")
            parts.append("")

        if env_lines:
            parts.append("*Variaveis .env necessarias:*")
            parts.append("```")
            for line in env_lines:
                parts.append(line)
            parts.append("```")
            parts.append("")

        # Truncate adapted JSON for Telegram (4096 char limit)
        max_json_len = 3000
        truncated_json = adapted_json
        if len(adapted_json) > max_json_len:
            truncated_json = adapted_json[:max_json_len] + "\n... (truncado)"

        parts.append("*JSON Adaptado:*")
        parts.append("```json")
        parts.append(truncated_json)
        parts.append("```")

        return "\n".join(parts)
