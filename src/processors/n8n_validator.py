"""
n8n Flow Validator - Verifica fluxos gerados por agentes contra templates de referencia.

Compara node types, parameter keys e type versions de um fluxo novo
com o indice de referencia construido a partir dos workflows existentes.

Uso:
    from src.processors.n8n_validator import N8nFlowValidator

    validator = N8nFlowValidator.from_reference_dir("data/raw")
    result = validator.validate("path/to/agent_generated_flow.json")
    print(result.summary())
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.extractors.n8n_extractor import (
    build_reference_index,
    extract_all_workflows,
    extract_operation_modules,
    is_n8n_workflow,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Um problema encontrado na validacao."""
    severity: str  # "error" | "warning"
    node_name: str
    message: str


@dataclass
class ValidationResult:
    """Resultado completo da validacao de um fluxo n8n."""
    file_path: str
    valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    nodes_checked: int = 0
    nodes_known: int = 0
    nodes_unknown: int = 0

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def summary(self) -> str:
        status = "VALIDO" if self.valid else "INVALIDO"
        lines = [
            f"[{status}] {self.file_path}",
            f"  Nodes: {self.nodes_checked} verificados, "
            f"{self.nodes_known} conhecidos, {self.nodes_unknown} desconhecidos",
        ]
        if self.errors:
            lines.append(f"  Erros: {len(self.errors)}")
            for e in self.errors:
                lines.append(f"    - [{e.node_name}] {e.message}")
        if self.warnings:
            lines.append(f"  Avisos: {len(self.warnings)}")
            for w in self.warnings:
                lines.append(f"    - [{w.node_name}] {w.message}")
        return "\n".join(lines)


class N8nFlowValidator:
    """
    Valida fluxos n8n gerados contra um indice de referencia.

    O indice de referencia e construido a partir dos workflows existentes
    e contem: node types validos, parameter keys esperados, versoes conhecidas.
    """

    def __init__(self, reference_index: dict[str, dict[str, Any]]):
        """
        Args:
            reference_index: Output de build_reference_index().
                {node_type: {"parameter_keys": set, "type_versions": set, ...}}
        """
        self._index = reference_index

    @classmethod
    def from_reference_dir(cls, search_dir: str | Path) -> "N8nFlowValidator":
        """Constroi validador a partir de um diretorio com fluxos de referencia."""
        modules = extract_all_workflows(search_dir)
        if not modules:
            logger.warning("Nenhum modulo de referencia encontrado em %s", search_dir)
        index = build_reference_index(modules)
        return cls(index)

    @classmethod
    def from_modules(cls, modules: list[dict]) -> "N8nFlowValidator":
        """Constroi validador a partir de modulos ja extraidos."""
        index = build_reference_index(modules)
        return cls(index)

    @property
    def known_node_types(self) -> set[str]:
        return set(self._index.keys())

    def validate(self, flow_path: str | Path) -> ValidationResult:
        """
        Valida um fluxo n8n contra o indice de referencia.

        Checks:
          1. O arquivo e um fluxo n8n valido
          2. Cada node type existe nos templates de referencia
          3. Os parameter keys usados existem nos templates
          4. A type_version e compativel
        """
        p = Path(flow_path)
        result = ValidationResult(file_path=str(p), valid=True)

        if not is_n8n_workflow(p):
            result.valid = False
            result.issues.append(ValidationIssue(
                severity="error",
                node_name="<file>",
                message="Arquivo nao e um fluxo n8n valido",
            ))
            return result

        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            result.valid = False
            result.issues.append(ValidationIssue(
                severity="error",
                node_name="<file>",
                message=f"Erro ao ler JSON: {e}",
            ))
            return result

        nodes = data.get("nodes", [])

        # Skip sticky notes for validation
        skip = {"n8n-nodes-base.stickyNote", "n8n-nodes-base.noOp"}

        for node in nodes:
            if not isinstance(node, dict):
                continue
            node_type = node.get("type", "")
            if node_type in skip:
                continue

            node_name = node.get("name", "unnamed")
            result.nodes_checked += 1

            ref = self._index.get(node_type)
            if ref is None:
                result.nodes_unknown += 1
                result.issues.append(ValidationIssue(
                    severity="warning",
                    node_name=node_name,
                    message=f"Node type desconhecido: {node_type} "
                            f"(nao encontrado nos templates de referencia)",
                ))
                continue

            result.nodes_known += 1

            # Check parameter keys
            params = node.get("parameters", {})
            if isinstance(params, dict):
                known_keys = ref["parameter_keys"]
                for key in params.keys():
                    if key not in known_keys:
                        result.issues.append(ValidationIssue(
                            severity="warning",
                            node_name=node_name,
                            message=f"Parametro '{key}' nao encontrado nos "
                                    f"templates de referencia para {node_type}",
                        ))

            # Check type version
            tv = node.get("typeVersion")
            if tv is not None and ref["type_versions"]:
                known_versions = ref["type_versions"]
                if tv not in known_versions:
                    result.issues.append(ValidationIssue(
                        severity="warning",
                        node_name=node_name,
                        message=f"typeVersion {tv} nao vista nos templates "
                                f"(conhecidas: {sorted(known_versions)})",
                    ))

        # Flow is invalid only if it has errors (not just warnings)
        if result.errors:
            result.valid = False

        return result

    def validate_json_string(self, json_str: str) -> ValidationResult:
        """
        Valida um fluxo n8n a partir de uma string JSON (ex: output de agente).
        Cria um arquivo temporario para reuso do pipeline.
        """
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write(json_str)
            tmp_path = f.name

        try:
            return self.validate(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)
