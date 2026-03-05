"""
Modelos de dados para o sistema Steady Gaze Recon.

Define todas as estruturas de dados usadas para representar
resultados de análise anti-detecção.
"""

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any


@dataclass
class HoneypotElement:
    """Elemento honeypot detectado."""
    selector: str
    coordinates: Tuple[int, int]
    hiding_technique: str  # "display:none", "opacity:0", "z-index:-1", "off-viewport"
    risk_level: int  # 0-100


@dataclass
class ShadowDOMRoot:
    """Raiz de Shadow DOM detectada."""
    host_selector: str
    mode: str  # "open" ou "closed"
    depth: int  # Profundidade na hierarquia
    internal_structure: str  # Estrutura simplificada


@dataclass
class EventListenerInfo:
    """Informação sobre event listener."""
    event_type: str  # "click", "mousemove", "focus", etc
    target_selector: str
    script_url: str
    phase: str  # "capture" ou "bubble"
    validates_istrusted: bool


@dataclass
class IsTrustedValidator:
    """Validador de isTrusted detectado."""
    element_selector: str
    event_types: List[str]
    validation_code: str  # Trecho do código que valida


@dataclass
class WAFDetection:
    """Sistema WAF/Anti-Bot detectado."""
    type: str  # "cloudflare", "akamai", "datadome", "perimeterx"
    confidence: float  # 0.0-1.0
    signatures: List[str]  # Assinaturas encontradas
    protection_level: str  # "low", "medium", "high", "extreme"


@dataclass
class SPAFramework:
    """Framework SPA detectado."""
    name: str  # "react", "vue", "angular"
    version: Optional[str] = None
    devtools_hook: Optional[str] = None


@dataclass
class StateObject:
    """Objeto de estado SPA."""
    path: str  # Caminho no objeto global
    component_count: int
    has_router: bool


@dataclass
class IframeInfo:
    """Informação sobre iframe."""
    selector: str
    src: str
    is_same_origin: bool
    sandbox_attributes: List[str]
    nesting_level: int


@dataclass
class RedirectPattern:
    """Padrão de redirecionamento detectado."""
    type: str  # "http_302", "http_301", "history_pushstate", "history_replacestate"
    from_url: str
    to_url: str
    timestamp: float


@dataclass
class MonitoringScript:
    """Script de monitoramento detectado."""
    type: str  # "gtm", "hotjar", "ga", "mixpanel", "logrocket", "fullstory"
    script_url: str
    capabilities: List[str]  # ["session_replay", "heatmaps", "event_tracking"]


@dataclass
class APICallInfo:
    """Informação sobre chamada de API."""
    url: str
    method: str
    headers: Dict[str, str]
    payload: Optional[str]
    triggered_by: str  # "hover", "focus", "click", "load"
    is_tracking: bool


@dataclass
class CookieInfo:
    """Informação sobre cookie."""
    name: str
    value: str
    domain: str
    path: str
    httponly: bool
    secure: bool
    samesite: str  # "Strict", "Lax", "None"
    is_session_critical: bool


@dataclass
class StorageAnalysis:
    """Análise de storage."""
    local_storage_keys: List[str]
    session_storage_keys: List[str]
    auth_tokens: List[str]
    session_data: List[str]
    fingerprints: List[str]


@dataclass
class FingerprintTechnique:
    """Técnica de fingerprinting detectada."""
    type: str  # "canvas", "audio", "webgl", "fonts"
    library: Optional[str] = None  # "fingerprintjs", "clientjs", etc
    code_location: str = ""


@dataclass
class TLSEvent:
    """Evento TLS detectado."""
    event_type: str  # "connection", "renegotiation"
    timestamp: float
    certificate_info: Optional[Dict[str, Any]] = None


@dataclass
class DOMComplexity:
    """Complexidade do DOM."""
    total_nodes: int
    max_depth: int
    script_size_kb: int
    css_size_kb: int
    recommended_timeout_ms: int


@dataclass
class IdleDetector:
    """Detector de inatividade."""
    type: str  # "requestIdleCallback", "visibilitychange", "timer"
    threshold_ms: int
    callback_location: str


@dataclass
class HotZone:
    """Zona de clique natural."""
    element_selector: str
    coordinates: Tuple[int, int, int, int]  # x, y, width, height
    recommended_click_points: List[Tuple[int, int]]  # Distribuição gaussiana
    priority: int  # 0-100


@dataclass
class PoWChallenge:
    """Desafio Proof of Work detectado."""
    type: str  # "hcaptcha", "friendlycaptcha", "custom"
    uses_wasm: bool
    uses_workers: bool
    estimated_time_ms: int


@dataclass
class ActionRecommendation:
    """Recomendação de ação."""
    action_type: str  # "delay", "avoid_element", "use_js_click", etc
    target: Optional[str]  # Seletor do elemento alvo
    parameters: Dict[str, Any]
    priority: int  # 0-100
    reason: str


@dataclass
class DefenseAnatomyReport:
    """Fase 1: Anatomia de Defesa (Reconhecimento de Armadilhas)."""
    honeypots: List[HoneypotElement] = field(default_factory=list)
    shadow_dom_roots: List[ShadowDOMRoot] = field(default_factory=list)
    event_listeners: List[EventListenerInfo] = field(default_factory=list)
    istrusted_validators: List[IsTrustedValidator] = field(default_factory=list)
    waf_systems: List[WAFDetection] = field(default_factory=list)
    risk_score: int = 0


@dataclass
class FlowStructureReport:
    """Fase 2: Estrutura de Fluxo (Lógica Interna)."""
    spa_framework: Optional[SPAFramework] = None
    spa_state_objects: List[StateObject] = field(default_factory=list)
    iframes: List[IframeInfo] = field(default_factory=list)
    redirect_patterns: List[RedirectPattern] = field(default_factory=list)
    monitoring_scripts: List[MonitoringScript] = field(default_factory=list)
    api_calls: List[APICallInfo] = field(default_factory=list)
    risk_score: int = 0


@dataclass
class IdentityPersistenceReport:
    """Fase 3: Identidade & Persistência (Stealth)."""
    critical_cookies: List[CookieInfo] = field(default_factory=list)
    storage_data: Optional[StorageAnalysis] = None
    fingerprinting_techniques: List[FingerprintTechnique] = field(default_factory=list)
    user_agent_inconsistencies: List[str] = field(default_factory=list)
    tls_events: List[TLSEvent] = field(default_factory=list)
    risk_score: int = 0


@dataclass
class BehaviorTimingReport:
    """Fase 4: Comportamento & Timing (Mimicry)."""
    cognitive_latency_ms: int = 0
    dom_complexity: Optional[DOMComplexity] = None
    idle_detection_zones: List[IdleDetector] = field(default_factory=list)
    hot_zones: List[HotZone] = field(default_factory=list)
    pow_challenges: List[PoWChallenge] = field(default_factory=list)
    risk_score: int = 0


@dataclass
class AnalysisReport:
    """Relatório completo de análise Steady Gaze."""
    
    # Metadados
    url: str
    timestamp: float
    analysis_duration: float
    page_hash: str
    
    # Scores de risco (0-100, onde 100 = máximo risco)
    overall_risk_score: int
    phase_scores: Dict[int, int]  # {phase_number: score}
    dimension_scores: Dict[str, int]  # {dimension_name: score}
    
    # Resultados por fase
    phase_1_defense_anatomy: DefenseAnatomyReport
    phase_2_flow_structure: FlowStructureReport
    phase_3_identity_persistence: IdentityPersistenceReport
    phase_4_behavior_timing: BehaviorTimingReport
    
    # Recomendações
    recommendations: List[ActionRecommendation] = field(default_factory=list)
    critical_warnings: List[str] = field(default_factory=list)
    
    def to_json(self) -> str:
        """
        Serializa relatório para JSON.
        
        Returns:
            String JSON do relatório
        """
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AnalysisReport':
        """
        Deserializa relatório de JSON.
        
        Args:
            json_str: String JSON do relatório
            
        Returns:
            Instância de AnalysisReport
        """
        data = json.loads(json_str)
        
        # Converter chaves de phase_scores de string para int (JSON converte int keys para string)
        if 'phase_scores' in data:
            data['phase_scores'] = {int(k): v for k, v in data['phase_scores'].items()}
        
        # Reconstruir objetos aninhados
        data['phase_1_defense_anatomy'] = DefenseAnatomyReport(
            honeypots=[HoneypotElement(
                selector=h['selector'],
                coordinates=tuple(h['coordinates']),  # Convert list back to tuple
                hiding_technique=h['hiding_technique'],
                risk_level=h['risk_level']
            ) for h in data['phase_1_defense_anatomy']['honeypots']],
            shadow_dom_roots=[ShadowDOMRoot(**s) for s in data['phase_1_defense_anatomy']['shadow_dom_roots']],
            event_listeners=[EventListenerInfo(**e) for e in data['phase_1_defense_anatomy']['event_listeners']],
            istrusted_validators=[IsTrustedValidator(**i) for i in data['phase_1_defense_anatomy']['istrusted_validators']],
            waf_systems=[WAFDetection(**w) for w in data['phase_1_defense_anatomy']['waf_systems']],
            risk_score=data['phase_1_defense_anatomy']['risk_score']
        )
        
        data['phase_2_flow_structure'] = FlowStructureReport(
            spa_framework=SPAFramework(**data['phase_2_flow_structure']['spa_framework']) if data['phase_2_flow_structure']['spa_framework'] else None,
            spa_state_objects=[StateObject(**s) for s in data['phase_2_flow_structure']['spa_state_objects']],
            iframes=[IframeInfo(**i) for i in data['phase_2_flow_structure']['iframes']],
            redirect_patterns=[RedirectPattern(**r) for r in data['phase_2_flow_structure']['redirect_patterns']],
            monitoring_scripts=[MonitoringScript(**m) for m in data['phase_2_flow_structure']['monitoring_scripts']],
            api_calls=[APICallInfo(**a) for a in data['phase_2_flow_structure']['api_calls']],
            risk_score=data['phase_2_flow_structure']['risk_score']
        )
        
        data['phase_3_identity_persistence'] = IdentityPersistenceReport(
            critical_cookies=[CookieInfo(**c) for c in data['phase_3_identity_persistence']['critical_cookies']],
            storage_data=StorageAnalysis(**data['phase_3_identity_persistence']['storage_data']) if data['phase_3_identity_persistence']['storage_data'] else None,
            fingerprinting_techniques=[FingerprintTechnique(**f) for f in data['phase_3_identity_persistence']['fingerprinting_techniques']],
            user_agent_inconsistencies=data['phase_3_identity_persistence']['user_agent_inconsistencies'],
            tls_events=[TLSEvent(**t) for t in data['phase_3_identity_persistence']['tls_events']],
            risk_score=data['phase_3_identity_persistence']['risk_score']
        )
        
        data['phase_4_behavior_timing'] = BehaviorTimingReport(
            cognitive_latency_ms=data['phase_4_behavior_timing']['cognitive_latency_ms'],
            dom_complexity=DOMComplexity(**data['phase_4_behavior_timing']['dom_complexity']) if data['phase_4_behavior_timing']['dom_complexity'] else None,
            idle_detection_zones=[IdleDetector(**i) for i in data['phase_4_behavior_timing']['idle_detection_zones']],
            hot_zones=[HotZone(
                element_selector=h['element_selector'],
                coordinates=tuple(h['coordinates']),  # Convert list back to tuple
                recommended_click_points=[tuple(p) for p in h['recommended_click_points']],  # Convert lists back to tuples
                priority=h['priority']
            ) for h in data['phase_4_behavior_timing']['hot_zones']],
            pow_challenges=[PoWChallenge(**p) for p in data['phase_4_behavior_timing']['pow_challenges']],
            risk_score=data['phase_4_behavior_timing']['risk_score']
        )
        
        data['recommendations'] = [ActionRecommendation(**r) for r in data['recommendations']]
        
        return cls(**data)
