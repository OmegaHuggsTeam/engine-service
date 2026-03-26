"""
Layer 1 — Triage Intelligence (Domain Router)
Classifica queries por dominio usando keywords e regex. Sem LLM.

Fluxo:
    Query -> normalizar -> match keywords/patterns -> calcular confianca -> rotear ou escalar

Custo: $0 | Latencia: < 50ms
"""

import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Optional

import yaml

log = logging.getLogger(__name__)

# Caminho padrao do arquivo de regras
_DEFAULT_RULES_PATH = Path(__file__).parent / "rules.yml"


class TriageResult:
    """Resultado da classificacao de triage."""

    def __init__(self, domain: str, confidence: float, matched_keywords: list[str],
                 matched_patterns: list[str], routed: bool):
        self.domain = domain
        self.confidence = confidence
        self.matched_keywords = matched_keywords
        self.matched_patterns = matched_patterns
        self.routed = routed  # True = confianca suficiente, False = escalar pra Layer 2

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "confidence": round(self.confidence, 3),
            "matched_keywords": self.matched_keywords,
            "matched_patterns": self.matched_patterns,
            "routed": self.routed,
            "layer": "triage_layer_1"
        }


class DomainRouter:
    """Router que classifica queries por dominio usando regras YAML."""

    def __init__(self, rules_path: str = None):
        path = Path(rules_path) if rules_path else _DEFAULT_RULES_PATH
        self._rules = self._load_rules(path)
        self._settings = self._rules.get("settings", {})
        self._min_confidence = self._settings.get("min_confidence_to_route", 0.7)
        self._fallback_domain = self._settings.get("fallback_domain", "platform")
        self._case_sensitive = self._settings.get("case_sensitive", False)
        log.info(f"[TRIAGE] Carregado {len(self._rules.get('domains', {}))} dominios de {path}")

    def _load_rules(self, path: Path) -> dict:
        """Carrega regras do YAML."""
        if not path.exists():
            log.warning(f"[TRIAGE] Arquivo de regras nao encontrado: {path}")
            return {"domains": {}, "settings": {}}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {"domains": {}, "settings": {}}

    def _normalize(self, text: str) -> str:
        """Normaliza texto: lowercase, remove acentos."""
        if not self._case_sensitive:
            text = text.lower()
        # Remove acentos (e -> e, a -> a, etc)
        nfkd = unicodedata.normalize("NFKD", text)
        return "".join(c for c in nfkd if not unicodedata.combining(c))

    def classify(self, query: str) -> TriageResult:
        """
        Classifica uma query por dominio.

        Processo:
        1. Normaliza a query
        2. Para cada dominio, conta matches de keywords e patterns
        3. Calcula confianca baseada nos matches
        4. Retorna o dominio com maior confianca

        Se confianca >= min_confidence_to_route (0.7), marca como routed=True.
        Se nao, marca como routed=False (escalar pra Layer 2).
        """
        query_norm = self._normalize(query)
        domains = self._rules.get("domains", {})

        best_domain = self._fallback_domain
        best_confidence = 0.0
        best_keywords = []
        best_patterns = []

        for domain_name, config in domains.items():
            keywords = config.get("keywords", [])
            patterns = config.get("patterns", [])
            conf_per_match = config.get("confidence_per_match", 0.25)
            max_conf = config.get("max_confidence", 0.95)

            matched_kw = []
            matched_pt = []

            # Match keywords
            for kw in keywords:
                kw_norm = self._normalize(kw)
                if kw_norm in query_norm:
                    matched_kw.append(kw)

            # Match patterns (regex)
            for pattern in patterns:
                pattern_norm = self._normalize(pattern)
                try:
                    if re.search(pattern_norm, query_norm):
                        matched_pt.append(pattern)
                except re.error:
                    log.warning(f"[TRIAGE] Regex invalido no dominio {domain_name}: {pattern}")

            # Calcular confianca
            total_matches = len(matched_kw) + len(matched_pt)
            confidence = min(total_matches * conf_per_match, max_conf)

            if confidence > best_confidence:
                best_confidence = confidence
                best_domain = domain_name
                best_keywords = matched_kw
                best_patterns = matched_pt

        routed = best_confidence >= self._min_confidence

        result = TriageResult(
            domain=best_domain,
            confidence=best_confidence,
            matched_keywords=best_keywords,
            matched_patterns=best_patterns,
            routed=routed
        )

        if routed:
            log.info(f"[TRIAGE] ROUTED -> {best_domain} | conf={best_confidence:.2f} | kw={best_keywords}")
        else:
            log.info(f"[TRIAGE] ESCALATE -> Layer 2 | best={best_domain} conf={best_confidence:.2f}")

        return result

    def get_domains(self) -> list[str]:
        """Lista dominios disponiveis."""
        return list(self._rules.get("domains", {}).keys())

    def get_domain_info(self, domain: str) -> Optional[dict]:
        """Retorna configuracao de um dominio."""
        return self._rules.get("domains", {}).get(domain)

    def reload_rules(self, rules_path: str = None) -> None:
        """Recarrega regras do YAML sem reiniciar."""
        path = Path(rules_path) if rules_path else _DEFAULT_RULES_PATH
        self._rules = self._load_rules(path)
        self._settings = self._rules.get("settings", {})
        self._min_confidence = self._settings.get("min_confidence_to_route", 0.7)
        log.info(f"[TRIAGE] Regras recarregadas: {len(self._rules.get('domains', {}))} dominios")
