"""
Testes unitários para modelos de dados do Steady Gaze Recon.

Feature: steady-gaze-recon
Testa serialização/deserialização JSON e validação de campos obrigatórios.
"""

import json

import pytest

from src.steady_gaze.models import (
    ActionRecommendation,
    AnalysisReport,
    BehaviorTimingReport,
    CookieInfo,
    DefenseAnatomyReport,
    DOMComplexity,
    EventListenerInfo,
    FlowStructureReport,
    HoneypotElement,
    HotZone,
    IdentityPersistenceReport,
    ShadowDOMRoot,
    SPAFramework,
    StorageAnalysis,
    WAFDetection,
)


class TestHoneypotElement:
    """Testes para HoneypotElement."""

    def test_creation(self):
        """Testa criação de HoneypotElement."""
        honeypot = HoneypotElement(
            selector="#trap", coordinates=(100, 200), hiding_technique="display:none", risk_level=80
        )

        assert honeypot.selector == "#trap"
        assert honeypot.coordinates == (100, 200)
        assert honeypot.hiding_technique == "display:none"
        assert honeypot.risk_level == 80


class TestDefenseAnatomyReport:
    """Testes para DefenseAnatomyReport."""

    def test_creation_with_defaults(self):
        """Testa criação com valores padrão."""
        report = DefenseAnatomyReport()

        assert report.honeypots == []
        assert report.shadow_dom_roots == []
        assert report.event_listeners == []
        assert report.istrusted_validators == []
        assert report.waf_systems == []
        assert report.risk_score == 0

    def test_creation_with_data(self):
        """Testa criação com dados."""
        honeypot = HoneypotElement(
            selector="#trap", coordinates=(100, 200), hiding_technique="opacity:0", risk_level=70
        )

        report = DefenseAnatomyReport(honeypots=[honeypot], risk_score=50)

        assert len(report.honeypots) == 1
        assert report.honeypots[0].selector == "#trap"
        assert report.risk_score == 50


class TestAnalysisReport:
    """Testes para AnalysisReport."""

    def test_creation_minimal(self):
        """Testa criação com campos mínimos."""
        report = AnalysisReport(
            url="https://example.com",
            timestamp=1234567890.0,
            analysis_duration=2.5,
            page_hash="abc123",
            overall_risk_score=45,
            phase_scores={1: 40, 2: 50, 3: 45, 4: 45},
            dimension_scores={},
            phase_1_defense_anatomy=DefenseAnatomyReport(),
            phase_2_flow_structure=FlowStructureReport(),
            phase_3_identity_persistence=IdentityPersistenceReport(),
            phase_4_behavior_timing=BehaviorTimingReport(),
        )

        assert report.url == "https://example.com"
        assert report.timestamp == 1234567890.0
        assert report.analysis_duration == 2.5
        assert report.page_hash == "abc123"
        assert report.overall_risk_score == 45
        assert len(report.recommendations) == 0
        assert len(report.critical_warnings) == 0

    def test_json_serialization(self):
        """Testa serialização para JSON."""
        report = AnalysisReport(
            url="https://example.com",
            timestamp=1234567890.0,
            analysis_duration=2.5,
            page_hash="abc123",
            overall_risk_score=45,
            phase_scores={1: 40, 2: 50, 3: 45, 4: 45},
            dimension_scores={"honeypots": 40},
            phase_1_defense_anatomy=DefenseAnatomyReport(risk_score=40),
            phase_2_flow_structure=FlowStructureReport(risk_score=50),
            phase_3_identity_persistence=IdentityPersistenceReport(risk_score=45),
            phase_4_behavior_timing=BehaviorTimingReport(risk_score=45),
        )

        json_str = report.to_json()

        # Verificar que é JSON válido
        data = json.loads(json_str)
        assert data["url"] == "https://example.com"
        assert data["overall_risk_score"] == 45
        assert data["phase_scores"]["1"] == 40
        assert data["dimension_scores"]["honeypots"] == 40

    def test_json_deserialization(self):
        """Testa deserialização de JSON."""
        # Criar relatório original
        original = AnalysisReport(
            url="https://example.com",
            timestamp=1234567890.0,
            analysis_duration=2.5,
            page_hash="abc123",
            overall_risk_score=45,
            phase_scores={1: 40, 2: 50, 3: 45, 4: 45},
            dimension_scores={"honeypots": 40},
            phase_1_defense_anatomy=DefenseAnatomyReport(
                honeypots=[
                    HoneypotElement(
                        selector="#trap",
                        coordinates=(100, 200),
                        hiding_technique="display:none",
                        risk_level=80,
                    )
                ],
                risk_score=40,
            ),
            phase_2_flow_structure=FlowStructureReport(risk_score=50),
            phase_3_identity_persistence=IdentityPersistenceReport(risk_score=45),
            phase_4_behavior_timing=BehaviorTimingReport(risk_score=45),
            recommendations=[
                ActionRecommendation(
                    action_type="delay",
                    target=None,
                    parameters={"ms": 1000},
                    priority=80,
                    reason="High cognitive latency",
                )
            ],
            critical_warnings=["WAF detected"],
        )

        # Serializar e deserializar
        json_str = original.to_json()
        restored = AnalysisReport.from_json(json_str)

        # Verificar campos principais
        assert restored.url == original.url
        assert restored.timestamp == original.timestamp
        assert restored.analysis_duration == original.analysis_duration
        assert restored.page_hash == original.page_hash
        assert restored.overall_risk_score == original.overall_risk_score

        # Verificar phase scores
        assert restored.phase_scores == original.phase_scores

        # Verificar honeypots
        assert len(restored.phase_1_defense_anatomy.honeypots) == 1
        assert restored.phase_1_defense_anatomy.honeypots[0].selector == "#trap"
        assert restored.phase_1_defense_anatomy.honeypots[0].coordinates == (100, 200)

        # Verificar recomendações
        assert len(restored.recommendations) == 1
        assert restored.recommendations[0].action_type == "delay"
        assert restored.recommendations[0].priority == 80

        # Verificar warnings
        assert len(restored.critical_warnings) == 1
        assert restored.critical_warnings[0] == "WAF detected"

    def test_json_round_trip_with_complex_data(self):
        """Testa round-trip JSON com dados complexos."""
        report = AnalysisReport(
            url="https://complex-site.com",
            timestamp=1234567890.0,
            analysis_duration=5.2,
            page_hash="xyz789",
            overall_risk_score=75,
            phase_scores={1: 80, 2: 70, 3: 75, 4: 75},
            dimension_scores={"honeypots": 80, "waf": 90},
            phase_1_defense_anatomy=DefenseAnatomyReport(
                honeypots=[
                    HoneypotElement("#trap1", (10, 20), "display:none", 80),
                    HoneypotElement("#trap2", (30, 40), "opacity:0", 70),
                ],
                shadow_dom_roots=[ShadowDOMRoot("#host1", "open", 1, "<div>content</div>")],
                event_listeners=[EventListenerInfo("click", "#button", "app.js", "bubble", True)],
                waf_systems=[WAFDetection("cloudflare", 0.95, ["cf-ray", "turnstile"], "high")],
                risk_score=80,
            ),
            phase_2_flow_structure=FlowStructureReport(
                spa_framework=SPAFramework("react", "18.2.0", "__REACT_DEVTOOLS_GLOBAL_HOOK__"),
                risk_score=70,
            ),
            phase_3_identity_persistence=IdentityPersistenceReport(
                critical_cookies=[
                    CookieInfo("session", "abc123", ".example.com", "/", True, True, "Strict", True)
                ],
                storage_data=StorageAnalysis(
                    local_storage_keys=["token", "user_id"],
                    session_storage_keys=["temp_data"],
                    auth_tokens=["token"],
                    session_data=["user_id"],
                    fingerprints=[],
                ),
                risk_score=75,
            ),
            phase_4_behavior_timing=BehaviorTimingReport(
                cognitive_latency_ms=2500,
                dom_complexity=DOMComplexity(1500, 12, 250, 100, 3000),
                hot_zones=[HotZone("#button", (100, 200, 80, 40), [(110, 210), (120, 220)], 90)],
                risk_score=75,
            ),
            recommendations=[
                ActionRecommendation("delay", None, {"ms": 2500}, 90, "Cognitive latency"),
                ActionRecommendation("avoid_element", "#trap1", {}, 100, "Honeypot detected"),
            ],
            critical_warnings=["Cloudflare WAF detected", "isTrusted validation active"],
        )

        # Round-trip
        json_str = report.to_json()
        restored = AnalysisReport.from_json(json_str)

        # Verificar estrutura completa
        assert restored.url == report.url
        assert restored.overall_risk_score == report.overall_risk_score
        assert len(restored.phase_1_defense_anatomy.honeypots) == 2
        assert len(restored.phase_1_defense_anatomy.waf_systems) == 1
        assert restored.phase_2_flow_structure.spa_framework.name == "react"
        assert len(restored.phase_3_identity_persistence.critical_cookies) == 1
        assert restored.phase_4_behavior_timing.cognitive_latency_ms == 2500
        assert len(restored.recommendations) == 2
        assert len(restored.critical_warnings) == 2


class TestStorageAnalysis:
    """Testes para StorageAnalysis."""

    def test_creation(self):
        """Testa criação de StorageAnalysis."""
        storage = StorageAnalysis(
            local_storage_keys=["key1", "key2"],
            session_storage_keys=["temp"],
            auth_tokens=["token1"],
            session_data=["session_id"],
            fingerprints=["fp_123"],
        )

        assert len(storage.local_storage_keys) == 2
        assert len(storage.session_storage_keys) == 1
        assert len(storage.auth_tokens) == 1
        assert "token1" in storage.auth_tokens


class TestDOMComplexity:
    """Testes para DOMComplexity."""

    def test_creation(self):
        """Testa criação de DOMComplexity."""
        complexity = DOMComplexity(
            total_nodes=1000,
            max_depth=10,
            script_size_kb=200,
            css_size_kb=50,
            recommended_timeout_ms=2000,
        )

        assert complexity.total_nodes == 1000
        assert complexity.max_depth == 10
        assert complexity.script_size_kb == 200
        assert complexity.css_size_kb == 50
        assert complexity.recommended_timeout_ms == 2000


class TestActionRecommendation:
    """Testes para ActionRecommendation."""

    def test_creation(self):
        """Testa criação de ActionRecommendation."""
        rec = ActionRecommendation(
            action_type="delay",
            target=None,
            parameters={"ms": 1500},
            priority=85,
            reason="Cognitive latency calculation",
        )

        assert rec.action_type == "delay"
        assert rec.target is None
        assert rec.parameters["ms"] == 1500
        assert rec.priority == 85
        assert "latency" in rec.reason.lower()


class TestFieldValidation:
    """Testes de validação de campos obrigatórios."""

    def test_honeypot_element_required_fields(self):
        """Testa que HoneypotElement requer todos os campos."""
        with pytest.raises(TypeError):
            HoneypotElement()  # Missing all required fields

    def test_analysis_report_required_fields(self):
        """Testa que AnalysisReport requer campos obrigatórios."""
        with pytest.raises(TypeError):
            AnalysisReport()  # Missing required fields

    def test_waf_detection_confidence_range(self):
        """Testa que WAFDetection aceita confidence entre 0.0 e 1.0."""
        # Valid confidence values
        waf1 = WAFDetection("cloudflare", 0.0, [], "low")
        assert waf1.confidence == 0.0

        waf2 = WAFDetection("cloudflare", 1.0, [], "high")
        assert waf2.confidence == 1.0

        waf3 = WAFDetection("cloudflare", 0.5, [], "medium")
        assert waf3.confidence == 0.5

    def test_risk_score_range(self):
        """Testa que risk_score está no intervalo 0-100."""
        report = DefenseAnatomyReport(risk_score=0)
        assert report.risk_score == 0

        report = DefenseAnatomyReport(risk_score=100)
        assert report.risk_score == 100

        report = DefenseAnatomyReport(risk_score=50)
        assert report.risk_score == 50


class TestEdgeCases:
    """Testes de casos extremos."""

    def test_empty_lists_serialization(self):
        """Testa serialização com listas vazias."""
        report = AnalysisReport(
            url="https://example.com",
            timestamp=1234567890.0,
            analysis_duration=1.0,
            page_hash="hash123",
            overall_risk_score=0,
            phase_scores={1: 0, 2: 0, 3: 0, 4: 0},
            dimension_scores={},
            phase_1_defense_anatomy=DefenseAnatomyReport(),
            phase_2_flow_structure=FlowStructureReport(),
            phase_3_identity_persistence=IdentityPersistenceReport(),
            phase_4_behavior_timing=BehaviorTimingReport(),
        )

        json_str = report.to_json()
        restored = AnalysisReport.from_json(json_str)

        assert len(restored.phase_1_defense_anatomy.honeypots) == 0
        assert len(restored.recommendations) == 0
        assert len(restored.critical_warnings) == 0

    def test_none_optional_fields_serialization(self):
        """Testa serialização com campos opcionais None."""
        report = AnalysisReport(
            url="https://example.com",
            timestamp=1234567890.0,
            analysis_duration=1.0,
            page_hash="hash123",
            overall_risk_score=0,
            phase_scores={1: 0, 2: 0, 3: 0, 4: 0},
            dimension_scores={},
            phase_1_defense_anatomy=DefenseAnatomyReport(),
            phase_2_flow_structure=FlowStructureReport(spa_framework=None),
            phase_3_identity_persistence=IdentityPersistenceReport(storage_data=None),
            phase_4_behavior_timing=BehaviorTimingReport(dom_complexity=None),
        )

        json_str = report.to_json()
        restored = AnalysisReport.from_json(json_str)

        assert restored.phase_2_flow_structure.spa_framework is None
        assert restored.phase_3_identity_persistence.storage_data is None
        assert restored.phase_4_behavior_timing.dom_complexity is None

    def test_tuple_coordinates_preservation(self):
        """Testa que coordenadas tuple são preservadas no round-trip."""
        honeypot = HoneypotElement(
            selector="#test", coordinates=(123, 456), hiding_technique="display:none", risk_level=50
        )

        report = AnalysisReport(
            url="https://example.com",
            timestamp=1234567890.0,
            analysis_duration=1.0,
            page_hash="hash123",
            overall_risk_score=0,
            phase_scores={1: 0, 2: 0, 3: 0, 4: 0},
            dimension_scores={},
            phase_1_defense_anatomy=DefenseAnatomyReport(honeypots=[honeypot]),
            phase_2_flow_structure=FlowStructureReport(),
            phase_3_identity_persistence=IdentityPersistenceReport(),
            phase_4_behavior_timing=BehaviorTimingReport(),
        )

        json_str = report.to_json()
        restored = AnalysisReport.from_json(json_str)

        # Verify tuple is preserved (not converted to list)
        assert isinstance(restored.phase_1_defense_anatomy.honeypots[0].coordinates, tuple)
        assert restored.phase_1_defense_anatomy.honeypots[0].coordinates == (123, 456)

    def test_hot_zone_nested_tuples_preservation(self):
        """Testa que tuples aninhados em HotZone são preservados."""
        hot_zone = HotZone(
            element_selector="#button",
            coordinates=(10, 20, 100, 50),
            recommended_click_points=[(15, 25), (20, 30), (25, 35)],
            priority=80,
        )

        report = AnalysisReport(
            url="https://example.com",
            timestamp=1234567890.0,
            analysis_duration=1.0,
            page_hash="hash123",
            overall_risk_score=0,
            phase_scores={1: 0, 2: 0, 3: 0, 4: 0},
            dimension_scores={},
            phase_1_defense_anatomy=DefenseAnatomyReport(),
            phase_2_flow_structure=FlowStructureReport(),
            phase_3_identity_persistence=IdentityPersistenceReport(),
            phase_4_behavior_timing=BehaviorTimingReport(hot_zones=[hot_zone]),
        )

        json_str = report.to_json()
        restored = AnalysisReport.from_json(json_str)

        restored_zone = restored.phase_4_behavior_timing.hot_zones[0]
        assert isinstance(restored_zone.coordinates, tuple)
        assert restored_zone.coordinates == (10, 20, 100, 50)
        assert len(restored_zone.recommended_click_points) == 3
        assert all(isinstance(p, tuple) for p in restored_zone.recommended_click_points)
        assert restored_zone.recommended_click_points[0] == (15, 25)

    def test_large_data_serialization(self):
        """Testa serialização com grande quantidade de dados."""
        # Create report with many items
        honeypots = [
            HoneypotElement(f"#trap{i}", (i * 10, i * 20), "display:none", 50) for i in range(100)
        ]

        report = AnalysisReport(
            url="https://example.com",
            timestamp=1234567890.0,
            analysis_duration=1.0,
            page_hash="hash123",
            overall_risk_score=0,
            phase_scores={1: 0, 2: 0, 3: 0, 4: 0},
            dimension_scores={},
            phase_1_defense_anatomy=DefenseAnatomyReport(honeypots=honeypots),
            phase_2_flow_structure=FlowStructureReport(),
            phase_3_identity_persistence=IdentityPersistenceReport(),
            phase_4_behavior_timing=BehaviorTimingReport(),
        )

        json_str = report.to_json()
        restored = AnalysisReport.from_json(json_str)

        assert len(restored.phase_1_defense_anatomy.honeypots) == 100
        assert restored.phase_1_defense_anatomy.honeypots[50].selector == "#trap50"

    def test_special_characters_in_strings(self):
        """Testa serialização com caracteres especiais."""
        report = AnalysisReport(
            url="https://example.com/path?query=value&other=123",
            timestamp=1234567890.0,
            analysis_duration=1.0,
            page_hash="hash123",
            overall_risk_score=0,
            phase_scores={1: 0, 2: 0, 3: 0, 4: 0},
            dimension_scores={},
            phase_1_defense_anatomy=DefenseAnatomyReport(),
            phase_2_flow_structure=FlowStructureReport(),
            phase_3_identity_persistence=IdentityPersistenceReport(),
            phase_4_behavior_timing=BehaviorTimingReport(),
            critical_warnings=[
                "Warning with 'quotes'",
                'Warning with "double quotes"',
                "Warning with\nnewline",
            ],
        )

        json_str = report.to_json()
        restored = AnalysisReport.from_json(json_str)

        assert restored.url == "https://example.com/path?query=value&other=123"
        assert len(restored.critical_warnings) == 3
        assert "quotes" in restored.critical_warnings[0]

    def test_unicode_characters_serialization(self):
        """Testa serialização com caracteres Unicode."""
        report = AnalysisReport(
            url="https://example.com",
            timestamp=1234567890.0,
            analysis_duration=1.0,
            page_hash="hash123",
            overall_risk_score=0,
            phase_scores={1: 0, 2: 0, 3: 0, 4: 0},
            dimension_scores={},
            phase_1_defense_anatomy=DefenseAnatomyReport(),
            phase_2_flow_structure=FlowStructureReport(),
            phase_3_identity_persistence=IdentityPersistenceReport(),
            phase_4_behavior_timing=BehaviorTimingReport(),
            critical_warnings=[
                "Aviso em português",
                "警告 in Chinese",
                "Предупреждение in Russian",
            ],
        )

        json_str = report.to_json()
        restored = AnalysisReport.from_json(json_str)

        assert "português" in restored.critical_warnings[0]
        assert "警告" in restored.critical_warnings[1]
        assert "Предупреждение" in restored.critical_warnings[2]
