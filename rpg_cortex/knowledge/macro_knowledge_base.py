"""
Macro Knowledge Base - Base de conhecimento de macros.
Metadados, keywords, chain_after, estado pre/post.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_YAML = ROOT / "knowledge" / "macros_map.yaml"


@dataclass
class MacroEntry:
    """Entrada de macro na knowledge base."""

    name: str
    file_path: str
    description: str
    keywords: List[str]
    pre_state: Dict[str, Any]
    post_state: Dict[str, Any]
    success_criteria: List[Dict[str, Any]]
    failure_criteria: List[Dict[str, Any]]
    timeout_seconds: int
    chain_after: List[str] = field(default_factory=list)
    available: bool = True


class MacroKnowledgeBase:
    """Gerencia metadados e consultas de macros."""

    def __init__(self, yaml_path: Optional[Path] = None):
        self.yaml_path = Path(yaml_path or DEFAULT_YAML)
        self.macros: Dict[str, MacroEntry] = {}
        self._loaded = False

    def load(self) -> None:
        """Carrega macros do YAML."""
        if not self.yaml_path.exists():
            self.macros = {}
            self._loaded = True
            return

        with open(self.yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self.macros = {}
        for m in data.get("macros", []):
            name = m.get("name", "")
            if not name:
                continue
            fp = m.get("file_path", "")
            base = self.yaml_path.parent.parent
            full_path = (base / fp).resolve() if fp else None
            available = full_path.exists() if full_path else False
            self.macros[name] = MacroEntry(
                name=name,
                file_path=fp,
                description=m.get("description", ""),
                keywords=m.get("keywords", []),
                pre_state=m.get("pre_state", {}),
                post_state=m.get("post_state", {}),
                success_criteria=m.get("success_criteria", []),
                failure_criteria=m.get("failure_criteria", []),
                timeout_seconds=m.get("timeout_seconds", 10),
                chain_after=m.get("chain_after", []),
                available=available,
            )
        self._loaded = True

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def query_by_keyword(self, keyword: str) -> List[MacroEntry]:
        """Retorna macros cujo keyword contem o termo."""
        self._ensure_loaded()
        kw = keyword.lower()
        return [m for m in self.macros.values() if kw in " ".join(m.keywords).lower()]

    def query_by_screen_state(self, state: str) -> List[MacroEntry]:
        """Retorna macros aplicaveis ao estado de tela (pre_state.screen)."""
        self._ensure_loaded()
        st = state.lower()
        return [
            m
            for m in self.macros.values()
            if st in str(m.pre_state.get("screen", "")).lower()
        ]

    def get_macro(self, name: str) -> Optional[MacroEntry]:
        """Retorna macro por nome exato."""
        self._ensure_loaded()
        return self.macros.get(name)

    def get_chain(self, macro_name: str) -> List[str]:
        """Retorna cadeia completa (dependencias + macro) em ordem de execucao."""
        self._ensure_loaded()
        seen = set()
        result = []

        def add_deps(mname: str):
            m = self.macros.get(mname)
            if not m or mname in seen:
                return
            for dep in m.chain_after:
                add_deps(dep)
            seen.add(mname)
            result.append(mname)

        add_deps(macro_name)
        return result

    def validate_all(self) -> Dict[str, bool]:
        """Valida se todos os arquivos de macro existem."""
        self._ensure_loaded()
        base = self.yaml_path.parent.parent
        out = {}
        for name, m in self.macros.items():
            full = (base / m.file_path).resolve()
            out[name] = full.exists()
        return out

    def get_macro_path(self, name: str) -> Optional[Path]:
        """Retorna Path absoluto do arquivo de macro."""
        m = self.get_macro(name)
        if not m:
            return None
        base = self.yaml_path.parent.parent
        return (base / m.file_path).resolve()
