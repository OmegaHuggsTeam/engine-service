"""
Classe principal do sistema Steady Gaze Recon.

Implementa análise anti-detecção em 20 dimensões divididas em 4 fases.
"""

import time
from typing import Any, Dict, List, Optional

from selenium import webdriver

from src.steady_gaze.cache import AnalysisCache
from src.steady_gaze.cdp_connection import CDPConnection, CDPConnectionError
from src.steady_gaze.exceptions import (
    PageNotLoadedError,
)
from src.steady_gaze.models import (
    ActionRecommendation,
    AnalysisReport,
    APICallInfo,
    BehaviorTimingReport,
    CookieInfo,
    DefenseAnatomyReport,
    DOMComplexity,
    EventListenerInfo,
    FingerprintTechnique,
    FlowStructureReport,
    HoneypotElement,
    HotZone,
    IdentityPersistenceReport,
    IdleDetector,
    IframeInfo,
    IsTrustedValidator,
    MonitoringScript,
    PoWChallenge,
    RedirectPattern,
    ShadowDOMRoot,
    SPAFramework,
    StateObject,
    StorageAnalysis,
    TLSEvent,
    WAFDetection,
)
from src.utils.logger import get_logger

# JavaScript snippets for CDP/Selenium analysis
_JS_DETECT_HONEYPOTS = """
(function() {
    var honeypots = [];
    var allInputs = document.querySelectorAll('input, textarea, button, a');
    for (var i = 0; i < allInputs.length; i++) {
        var el = allInputs[i];
        var style = window.getComputedStyle(el);
        var rect = el.getBoundingClientRect();
        var technique = null;
        if (style.display === 'none') technique = 'display:none';
        else if (parseFloat(style.opacity) === 0) technique = 'opacity:0';
        else if (parseInt(style.zIndex) < 0) technique = 'z-index:-1';
        else if (rect.left < -1000 || rect.top < -1000 || rect.right < 0 || rect.bottom < 0) technique = 'off-viewport';
        else if (rect.width === 0 && rect.height === 0) technique = 'zero-size';
        if (technique) {
            var selector = el.tagName.toLowerCase();
            if (el.id) selector += '#' + el.id;
            else if (el.name) selector += '[name="' + el.name + '"]';
            else if (el.className) selector += '.' + el.className.split(' ')[0];
            honeypots.push({
                selector: selector,
                x: Math.round(rect.left),
                y: Math.round(rect.top),
                technique: technique
            });
        }
    }
    return honeypots;
})();
"""

_JS_DETECT_SHADOW_DOM = """
(function() {
    var roots = [];
    function findShadowRoots(node, depth) {
        if (depth > 10) return;
        if (node.shadowRoot) {
            var selector = node.tagName.toLowerCase();
            if (node.id) selector += '#' + node.id;
            else if (node.className) selector += '.' + String(node.className).split(' ')[0];
            var mode = 'open';
            var structure = '';
            try {
                structure = node.shadowRoot.innerHTML.substring(0, 200);
            } catch(e) {
                mode = 'closed';
                structure = '[closed]';
            }
            roots.push({
                host_selector: selector,
                mode: mode,
                depth: depth,
                internal_structure: structure
            });
        }
        var children = node.children || [];
        for (var i = 0; i < children.length; i++) {
            findShadowRoots(children[i], depth + 1);
        }
    }
    findShadowRoots(document.documentElement, 0);
    return roots;
})();
"""

_JS_DETECT_SPA_FRAMEWORK = """
(function() {
    if (window.__REACT_DEVTOOLS_GLOBAL_HOOK__ || document.querySelector('[data-reactroot]') || document.querySelector('[data-reactid]')) {
        var version = null;
        try { version = window.React && window.React.version; } catch(e) {}
        return {name: 'react', version: version, devtools_hook: '__REACT_DEVTOOLS_GLOBAL_HOOK__'};
    }
    if (window.__VUE__ || document.querySelector('[data-v-]') || window.Vue) {
        var version = null;
        try { version = window.Vue && window.Vue.version; } catch(e) {}
        return {name: 'vue', version: version, devtools_hook: '__VUE__'};
    }
    if (window.ng || document.querySelector('[ng-version]') || document.querySelector('[_nghost-]')) {
        var version = null;
        try {
            var ngEl = document.querySelector('[ng-version]');
            if (ngEl) version = ngEl.getAttribute('ng-version');
        } catch(e) {}
        return {name: 'angular', version: version, devtools_hook: 'ng'};
    }
    if (window.__NEXT_DATA__) {
        return {name: 'react', version: null, devtools_hook: '__NEXT_DATA__'};
    }
    if (window.__NUXT__) {
        return {name: 'vue', version: null, devtools_hook: '__NUXT__'};
    }
    return null;
})();
"""

_JS_DETECT_IFRAMES = """
(function() {
    var results = [];
    function findIframes(doc, level) {
        if (level > 5) return;
        var iframes = doc.querySelectorAll('iframe');
        for (var i = 0; i < iframes.length; i++) {
            var iframe = iframes[i];
            var src = iframe.src || iframe.getAttribute('data-src') || '';
            var isSameOrigin = false;
            try {
                var iframeDoc = iframe.contentDocument;
                isSameOrigin = !!iframeDoc;
            } catch(e) {
                isSameOrigin = false;
            }
            var sandbox = iframe.getAttribute('sandbox') || '';
            var selector = 'iframe';
            if (iframe.id) selector += '#' + iframe.id;
            else if (iframe.name) selector += '[name="' + iframe.name + '"]';
            results.push({
                selector: selector,
                src: src,
                is_same_origin: isSameOrigin,
                sandbox_attributes: sandbox ? sandbox.split(' ') : [],
                nesting_level: level
            });
            if (isSameOrigin) {
                try { findIframes(iframe.contentDocument, level + 1); } catch(e) {}
            }
        }
    }
    findIframes(document, 0);
    return results;
})();
"""

_JS_DETECT_MONITORING = """
(function() {
    var scripts = [];
    var patterns = [
        {type: 'gtm', pattern: /googletagmanager\\.com/, capabilities: ['event_tracking', 'tag_management']},
        {type: 'ga', pattern: /google-analytics\\.com|googleanalytics\\.com|gtag/, capabilities: ['event_tracking', 'pageview_tracking']},
        {type: 'hotjar', pattern: /hotjar\\.com|static\\.hotjar\\.com/, capabilities: ['session_replay', 'heatmaps', 'event_tracking']},
        {type: 'mixpanel', pattern: /mixpanel\\.com|cdn\\.mxpnl\\.com/, capabilities: ['event_tracking', 'user_profiling']},
        {type: 'logrocket', pattern: /logrocket\\.com|cdn\\.lr-ingest\\.io/, capabilities: ['session_replay', 'error_tracking']},
        {type: 'fullstory', pattern: /fullstory\\.com|fs\\.usr\\.io/, capabilities: ['session_replay', 'heatmaps']},
        {type: 'segment', pattern: /segment\\.com|cdn\\.segment\\.io/, capabilities: ['event_tracking', 'user_profiling']},
        {type: 'datadog', pattern: /datadoghq\\.com|datadog-rum/, capabilities: ['error_tracking', 'performance_monitoring']},
        {type: 'sentry', pattern: /sentry\\.io|browser\\.sentry-cdn\\.com/, capabilities: ['error_tracking']},
    ];
    var allScripts = document.querySelectorAll('script[src]');
    for (var i = 0; i < allScripts.length; i++) {
        var src = allScripts[i].src;
        for (var j = 0; j < patterns.length; j++) {
            if (patterns[j].pattern.test(src)) {
                scripts.push({
                    type: patterns[j].type,
                    script_url: src,
                    capabilities: patterns[j].capabilities
                });
                break;
            }
        }
    }
    return scripts;
})();
"""

_JS_DETECT_WAF = """
(function() {
    var wafs = [];
    var signatures = {
        cloudflare: {
            checks: [
                function() { return !!document.querySelector('script[src*="challenges.cloudflare.com"]'); },
                function() { return !!document.querySelector('#cf-wrapper'); },
                function() { return !!document.querySelector('[data-cf-beacon]'); },
                function() { return document.cookie.indexOf('__cf_bm') !== -1; },
                function() { return document.cookie.indexOf('cf_clearance') !== -1; },
            ],
            sigs: ['cf-ray', 'turnstile', '__cf_bm', 'cf_clearance', 'challenges.cloudflare.com']
        },
        akamai: {
            checks: [
                function() { return !!document.querySelector('script[src*="akamaihd.net"]'); },
                function() { return !!document.querySelector('script[src*="akstat"]'); },
                function() { return document.cookie.indexOf('_abck') !== -1; },
                function() { return document.cookie.indexOf('bm_sz') !== -1; },
            ],
            sigs: ['_abck', 'bm_sz', 'akamaihd.net', 'akstat']
        },
        datadome: {
            checks: [
                function() { return !!document.querySelector('script[src*="datadome"]'); },
                function() { return document.cookie.indexOf('datadome') !== -1; },
            ],
            sigs: ['datadome', 'dd.js']
        },
        perimeterx: {
            checks: [
                function() { return !!document.querySelector('script[src*="perimeterx"]'); },
                function() { return !!document.querySelector('script[src*="px-cdn"]'); },
                function() { return document.cookie.indexOf('_px') !== -1; },
            ],
            sigs: ['perimeterx', '_px', 'px-cdn']
        },
    };
    for (var wafType in signatures) {
        var waf = signatures[wafType];
        var matchedSigs = [];
        var matchCount = 0;
        for (var i = 0; i < waf.checks.length; i++) {
            try {
                if (waf.checks[i]()) {
                    matchCount++;
                    matchedSigs.push(waf.sigs[i] || wafType);
                }
            } catch(e) {}
        }
        if (matchCount > 0) {
            var confidence = matchCount / waf.checks.length;
            var level = 'low';
            if (confidence > 0.7) level = 'extreme';
            else if (confidence > 0.5) level = 'high';
            else if (confidence > 0.3) level = 'medium';
            wafs.push({
                type: wafType,
                confidence: Math.round(confidence * 100) / 100,
                signatures: matchedSigs,
                protection_level: level
            });
        }
    }
    return wafs;
})();
"""

_JS_DETECT_FINGERPRINTING = """
(function() {
    var techniques = [];
    var allScripts = document.querySelectorAll('script');
    var pageSource = '';
    for (var i = 0; i < allScripts.length; i++) {
        if (allScripts[i].textContent) pageSource += allScripts[i].textContent;
    }
    if (/toDataURL|getImageData|canvas.*fingerprint/i.test(pageSource)) {
        var lib = null;
        if (/fingerprintjs|fp\\.js|fpjs/i.test(pageSource)) lib = 'fingerprintjs';
        techniques.push({type: 'canvas', library: lib, code_location: 'inline_script'});
    }
    if (/AudioContext|OfflineAudioContext|createOscillator/i.test(pageSource)) {
        techniques.push({type: 'audio', library: null, code_location: 'inline_script'});
    }
    if (/getParameter.*RENDERER|WEBGL_debug_renderer_info/i.test(pageSource)) {
        techniques.push({type: 'webgl', library: null, code_location: 'inline_script'});
    }
    if (/measureText.*font|document\\.fonts|FontFace/i.test(pageSource)) {
        techniques.push({type: 'fonts', library: null, code_location: 'inline_script'});
    }
    var extScripts = document.querySelectorAll('script[src]');
    for (var j = 0; j < extScripts.length; j++) {
        var src = extScripts[j].src;
        if (/fingerprintjs|fpjs/i.test(src)) {
            techniques.push({type: 'canvas', library: 'fingerprintjs', code_location: src});
        }
        if (/clientjs/i.test(src)) {
            techniques.push({type: 'canvas', library: 'clientjs', code_location: src});
        }
    }
    return techniques;
})();
"""

_JS_DETECT_STORAGE = """
(function() {
    var result = {
        local_storage_keys: [],
        session_storage_keys: [],
        auth_tokens: [],
        session_data: [],
        fingerprints: []
    };
    var authPatterns = /token|jwt|auth|bearer|api.?key|access.?key/i;
    var sessionPatterns = /session|sid|user.?id|account/i;
    var fpPatterns = /fingerprint|fp|device.?id|visitor.?id|browser.?id/i;
    try {
        for (var i = 0; i < localStorage.length; i++) {
            var key = localStorage.key(i);
            result.local_storage_keys.push(key);
            if (authPatterns.test(key)) result.auth_tokens.push(key);
            if (sessionPatterns.test(key)) result.session_data.push(key);
            if (fpPatterns.test(key)) result.fingerprints.push(key);
        }
    } catch(e) {}
    try {
        for (var i = 0; i < sessionStorage.length; i++) {
            var key = sessionStorage.key(i);
            result.session_storage_keys.push(key);
            if (authPatterns.test(key)) result.auth_tokens.push(key);
            if (sessionPatterns.test(key)) result.session_data.push(key);
            if (fpPatterns.test(key)) result.fingerprints.push(key);
        }
    } catch(e) {}
    return result;
})();
"""

_JS_DETECT_DOM_COMPLEXITY = """
(function() {
    var allNodes = document.querySelectorAll('*');
    var totalNodes = allNodes.length;
    var maxDepth = 0;
    function getDepth(el) {
        var d = 0;
        var node = el;
        while (node.parentElement) {
            d++;
            node = node.parentElement;
        }
        return d;
    }
    for (var i = 0; i < Math.min(allNodes.length, 500); i++) {
        var d = getDepth(allNodes[i]);
        if (d > maxDepth) maxDepth = d;
    }
    var scriptSize = 0;
    var scripts = document.querySelectorAll('script');
    for (var i = 0; i < scripts.length; i++) {
        if (scripts[i].src) scriptSize += 50;
        else scriptSize += (scripts[i].textContent || '').length;
    }
    var cssSize = 0;
    var styles = document.querySelectorAll('style, link[rel="stylesheet"]');
    for (var i = 0; i < styles.length; i++) {
        if (styles[i].href) cssSize += 30;
        else cssSize += (styles[i].textContent || '').length;
    }
    var recommendedTimeout = Math.max(1000, Math.min(10000, totalNodes * 2 + scriptSize / 100));
    return {
        total_nodes: totalNodes,
        max_depth: maxDepth,
        script_size_kb: Math.round(scriptSize / 1024),
        css_size_kb: Math.round(cssSize / 1024),
        recommended_timeout_ms: Math.round(recommendedTimeout)
    };
})();
"""

_JS_DETECT_IDLE_DETECTORS = """
(function() {
    var detectors = [];
    var allScripts = document.querySelectorAll('script');
    var pageSource = '';
    for (var i = 0; i < allScripts.length; i++) {
        if (allScripts[i].textContent) pageSource += allScripts[i].textContent;
    }
    if (/requestIdleCallback/i.test(pageSource)) {
        detectors.push({type: 'requestIdleCallback', threshold_ms: 0, callback_location: 'inline_script'});
    }
    if (/visibilitychange|document\\.hidden|visibilityState/i.test(pageSource)) {
        detectors.push({type: 'visibilitychange', threshold_ms: 0, callback_location: 'inline_script'});
    }
    var timerMatch = pageSource.match(/setTimeout\\s*\\(\\s*function[^,]*,\\s*(\\d{4,})\\s*\\)/);
    if (timerMatch) {
        detectors.push({type: 'timer', threshold_ms: parseInt(timerMatch[1]), callback_location: 'inline_script'});
    }
    if (/IdleDetector|idle.*detect/i.test(pageSource)) {
        detectors.push({type: 'IdleDetector', threshold_ms: 60000, callback_location: 'inline_script'});
    }
    return detectors;
})();
"""

_JS_DETECT_HOT_ZONES = """
(function() {
    var zones = [];
    var interactiveSelectors = 'button, a[href], input[type="submit"], input[type="button"], [role="button"], [onclick]';
    var elements = document.querySelectorAll(interactiveSelectors);
    for (var i = 0; i < Math.min(elements.length, 50); i++) {
        var el = elements[i];
        var rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) continue;
        if (rect.top < 0 || rect.left < 0) continue;
        var selector = el.tagName.toLowerCase();
        if (el.id) selector += '#' + el.id;
        else if (el.className && typeof el.className === 'string') selector += '.' + el.className.split(' ')[0];
        var cx = Math.round(rect.left + rect.width / 2);
        var cy = Math.round(rect.top + rect.height / 2);
        var clickPoints = [
            [cx, cy],
            [cx + Math.round(rect.width * 0.1), cy + Math.round(rect.height * 0.1)],
            [cx - Math.round(rect.width * 0.1), cy - Math.round(rect.height * 0.1)],
        ];
        var priority = 50;
        if (el.tagName === 'BUTTON' || el.type === 'submit') priority = 80;
        if (/login|submit|confirm|accept|continue|next/i.test(el.textContent || el.value || '')) priority = 90;
        zones.push({
            element_selector: selector,
            coordinates: [Math.round(rect.left), Math.round(rect.top), Math.round(rect.width), Math.round(rect.height)],
            recommended_click_points: clickPoints,
            priority: priority
        });
    }
    zones.sort(function(a, b) { return b.priority - a.priority; });
    return zones.slice(0, 20);
})();
"""

_JS_DETECT_POW = """
(function() {
    var challenges = [];
    if (document.querySelector('iframe[src*="hcaptcha.com"], script[src*="hcaptcha.com"], .h-captcha')) {
        challenges.push({type: 'hcaptcha', uses_wasm: true, uses_workers: true, estimated_time_ms: 5000});
    }
    if (document.querySelector('iframe[src*="recaptcha"], script[src*="recaptcha"], .g-recaptcha')) {
        challenges.push({type: 'recaptcha', uses_wasm: false, uses_workers: false, estimated_time_ms: 3000});
    }
    if (document.querySelector('script[src*="friendlycaptcha"], .frc-captcha')) {
        challenges.push({type: 'friendlycaptcha', uses_wasm: true, uses_workers: true, estimated_time_ms: 8000});
    }
    if (document.querySelector('[data-turnstile-sitekey], script[src*="turnstile"]')) {
        challenges.push({type: 'turnstile', uses_wasm: true, uses_workers: true, estimated_time_ms: 4000});
    }
    var allScripts = document.querySelectorAll('script');
    var pageSource = '';
    for (var i = 0; i < allScripts.length; i++) {
        if (allScripts[i].textContent) pageSource += allScripts[i].textContent;
    }
    if (/proof.?of.?work|hashcash|pow.?challenge/i.test(pageSource)) {
        challenges.push({type: 'custom', uses_wasm: false, uses_workers: false, estimated_time_ms: 10000});
    }
    return challenges;
})();
"""


class SteadyGazeRecon:
    """
    Sistema de reconhecimento anti-detecção para automação web.

    Analisa 20 dimensões de mecanismos de defesa antes de qualquer ação,
    divididas em 4 fases:
    - Fase 1: Defense Anatomy (Anatomia de Defesa)
    - Fase 2: Flow Structure (Estrutura de Fluxo)
    - Fase 3: Identity & Persistence (Identidade & Persistência)
    - Fase 4: Behavior & Timing (Comportamento & Timing)
    """

    # Risk weight multipliers per dimension (higher = more dangerous)
    _DIMENSION_WEIGHTS = {
        "honeypots": 1.5,
        "shadow_dom": 0.8,
        "event_listeners": 1.0,
        "istrusted_validators": 2.0,
        "waf_systems": 2.5,
        "spa_framework": 0.5,
        "iframes": 0.7,
        "redirect_patterns": 0.6,
        "monitoring_scripts": 1.2,
        "api_calls": 0.8,
        "cookies": 0.6,
        "storage": 0.7,
        "fingerprinting": 1.8,
        "user_agent": 1.5,
        "tls": 0.5,
        "cognitive_latency": 0.8,
        "dom_complexity": 0.6,
        "idle_detection": 1.3,
        "hot_zones": 0.4,
        "pow_challenges": 2.0,
    }

    def __init__(
        self,
        driver: webdriver.Remote,
        cdp_session: Optional[CDPConnection] = None,
        timeout: int = 10,
    ):
        """
        Inicializa o sistema Steady Gaze.

        Args:
            driver: Instância do WebDriver Selenium
            cdp_session: Sessão CDP (criada automaticamente se None)
            timeout: Timeout padrão para operações CDP em segundos
        """
        self.driver = driver
        self.timeout = timeout
        self.logger = get_logger("steady_gaze.recon")

        # Estabelecer conexão CDP se não fornecida
        if cdp_session is None:
            try:
                self.cdp = CDPConnection(driver, timeout)
                self.cdp.enable_required_domains()
            except CDPConnectionError as e:
                self.logger.warning(f"CDP não disponível, usando fallback Selenium: {e}")
                self.cdp = None
        else:
            self.cdp = cdp_session

        self.logger.info("Steady Gaze Recon inicializado")

    def _execute_js(self, script: str, default: Any = None) -> Any:
        """
        Executa JavaScript com fallback seguro.

        Tenta via CDP Runtime.evaluate primeiro, depois fallback para
        Selenium execute_script.

        Args:
            script: Código JavaScript a executar
            default: Valor padrão em caso de erro

        Returns:
            Resultado da execução ou valor padrão
        """
        # Tentar via CDP se disponível
        if self.cdp is not None and self.cdp.is_domain_enabled("Runtime"):
            try:
                result = self.cdp.execute(
                    "Runtime.evaluate",
                    {
                        "expression": script,
                        "returnByValue": True,
                    },
                )
                if "result" in result and "value" in result["result"]:
                    return result["result"]["value"]
            except CDPConnectionError:
                self.logger.debug("CDP Runtime.evaluate falhou, usando Selenium fallback")

        # Fallback Selenium
        try:
            return self.driver.execute_script(f"return {script}")
        except Exception as e:
            self.logger.debug(f"Fallback Selenium execute_script falhou: {e}")
            return default

    def _calculate_dimension_score(self, items: list, weight: float, max_base: int = 100) -> int:
        """
        Calcula score de risco para uma dimensão baseado na quantidade de itens encontrados.

        Args:
            items: Lista de itens detectados
            weight: Peso multiplicador da dimensão
            max_base: Score máximo base antes do peso

        Returns:
            Score de risco 0-100
        """
        if not items:
            return 0
        # Escala logarítmica: 1 item = 30, 2 = 50, 5 = 70, 10+ = 90
        count = len(items)
        if count == 1:
            base = 30
        elif count <= 3:
            base = 50
        elif count <= 5:
            base = 70
        elif count <= 10:
            base = 85
        else:
            base = 95

        return min(100, int(base * weight))

    def analyze_full(self) -> AnalysisReport:
        """
        Executa análise completa das 20 dimensões.

        Returns:
            AnalysisReport com resultados de todas as fases

        Raises:
            PageNotLoadedError: Se página não estiver carregada
            AnalysisTimeoutError: Se análise exceder timeout global
        """
        start_time = time.time()

        # Verificar se página está carregada
        try:
            current_url = self.driver.current_url
            if not current_url or current_url == "data:,":
                raise PageNotLoadedError("Nenhuma página carregada no driver")
        except Exception as e:
            raise PageNotLoadedError(f"Erro ao verificar página: {e}")

        self.logger.info(f"Iniciando análise completa: {current_url}")

        # Gerar hash da página
        try:
            dom_structure = self.driver.execute_script(
                "return document.documentElement.outerHTML.substring(0, 1000);"
            )
        except Exception as e:
            self.logger.warning(f"Erro ao obter estrutura DOM: {e}")
            dom_structure = ""

        page_hash = AnalysisCache.generate_page_hash(current_url, dom_structure)

        # Executar análise de cada fase
        phase_1 = self._analyze_phase_1_defense_anatomy()
        phase_2 = self._analyze_phase_2_flow_structure()
        phase_3 = self._analyze_phase_3_identity_persistence()
        phase_4 = self._analyze_phase_4_behavior_timing()

        # Calcular scores
        phase_scores = {
            1: phase_1.risk_score,
            2: phase_2.risk_score,
            3: phase_3.risk_score,
            4: phase_4.risk_score,
        }

        overall_risk_score = sum(phase_scores.values()) // 4

        # Calcular scores por dimensão
        dimension_scores = self._compute_dimension_scores(phase_1, phase_2, phase_3, phase_4)

        # Gerar recomendações baseadas nos resultados
        recommendations = self._generate_recommendations(phase_1, phase_2, phase_3, phase_4)

        # Identificar warnings críticos
        critical_warnings = self._identify_critical_warnings(phase_1, phase_2, phase_3, phase_4)

        # Criar relatório
        analysis_duration = time.time() - start_time

        report = AnalysisReport(
            url=current_url,
            timestamp=start_time,
            analysis_duration=analysis_duration,
            page_hash=page_hash,
            overall_risk_score=overall_risk_score,
            phase_scores=phase_scores,
            dimension_scores=dimension_scores,
            phase_1_defense_anatomy=phase_1,
            phase_2_flow_structure=phase_2,
            phase_3_identity_persistence=phase_3,
            phase_4_behavior_timing=phase_4,
            recommendations=recommendations,
            critical_warnings=critical_warnings,
        )

        self.logger.info(
            f"Análise completa em {analysis_duration:.2f}s | "
            f"Risk Score: {overall_risk_score}/100"
        )

        return report

    def _compute_dimension_scores(
        self,
        phase_1: DefenseAnatomyReport,
        phase_2: FlowStructureReport,
        phase_3: IdentityPersistenceReport,
        phase_4: BehaviorTimingReport,
    ) -> Dict[str, int]:
        """
        Calcula scores individuais para cada uma das 20 dimensões.

        Args:
            phase_1: Relatório da Fase 1
            phase_2: Relatório da Fase 2
            phase_3: Relatório da Fase 3
            phase_4: Relatório da Fase 4

        Returns:
            Dicionário {nome_dimensão: score_0_100}
        """
        scores: Dict[str, int] = {}

        # Fase 1 dimensions
        scores["honeypots"] = self._calculate_dimension_score(
            phase_1.honeypots, self._DIMENSION_WEIGHTS["honeypots"]
        )
        scores["shadow_dom"] = self._calculate_dimension_score(
            phase_1.shadow_dom_roots, self._DIMENSION_WEIGHTS["shadow_dom"]
        )
        scores["event_listeners"] = self._calculate_dimension_score(
            phase_1.event_listeners, self._DIMENSION_WEIGHTS["event_listeners"]
        )
        scores["istrusted_validators"] = self._calculate_dimension_score(
            phase_1.istrusted_validators, self._DIMENSION_WEIGHTS["istrusted_validators"]
        )
        scores["waf_systems"] = self._calculate_dimension_score(
            phase_1.waf_systems, self._DIMENSION_WEIGHTS["waf_systems"]
        )

        # Fase 2 dimensions
        scores["spa_framework"] = min(
            100,
            int((30 if phase_2.spa_framework else 0) * self._DIMENSION_WEIGHTS["spa_framework"]),
        )
        scores["iframes"] = self._calculate_dimension_score(
            phase_2.iframes, self._DIMENSION_WEIGHTS["iframes"]
        )
        scores["redirect_patterns"] = self._calculate_dimension_score(
            phase_2.redirect_patterns, self._DIMENSION_WEIGHTS["redirect_patterns"]
        )
        scores["monitoring_scripts"] = self._calculate_dimension_score(
            phase_2.monitoring_scripts, self._DIMENSION_WEIGHTS["monitoring_scripts"]
        )
        scores["api_calls"] = self._calculate_dimension_score(
            phase_2.api_calls, self._DIMENSION_WEIGHTS["api_calls"]
        )

        # Fase 3 dimensions
        scores["cookies"] = self._calculate_dimension_score(
            phase_3.critical_cookies, self._DIMENSION_WEIGHTS["cookies"]
        )
        storage_items = []
        if phase_3.storage_data:
            storage_items = phase_3.storage_data.auth_tokens + phase_3.storage_data.fingerprints
        scores["storage"] = self._calculate_dimension_score(
            storage_items, self._DIMENSION_WEIGHTS["storage"]
        )
        scores["fingerprinting"] = self._calculate_dimension_score(
            phase_3.fingerprinting_techniques, self._DIMENSION_WEIGHTS["fingerprinting"]
        )
        scores["user_agent"] = self._calculate_dimension_score(
            phase_3.user_agent_inconsistencies, self._DIMENSION_WEIGHTS["user_agent"]
        )
        scores["tls"] = self._calculate_dimension_score(
            phase_3.tls_events, self._DIMENSION_WEIGHTS["tls"]
        )

        # Fase 4 dimensions
        latency = phase_4.cognitive_latency_ms
        if latency > 5000:
            latency_base = 80
        elif latency > 3000:
            latency_base = 60
        elif latency > 1000:
            latency_base = 40
        elif latency > 0:
            latency_base = 20
        else:
            latency_base = 0
        scores["cognitive_latency"] = min(
            100, int(latency_base * self._DIMENSION_WEIGHTS["cognitive_latency"])
        )

        dom_score = 0
        if phase_4.dom_complexity:
            nodes = phase_4.dom_complexity.total_nodes
            if nodes > 5000:
                dom_score = 80
            elif nodes > 2000:
                dom_score = 60
            elif nodes > 1000:
                dom_score = 40
            elif nodes > 500:
                dom_score = 20
        scores["dom_complexity"] = min(
            100, int(dom_score * self._DIMENSION_WEIGHTS["dom_complexity"])
        )

        scores["idle_detection"] = self._calculate_dimension_score(
            phase_4.idle_detection_zones, self._DIMENSION_WEIGHTS["idle_detection"]
        )
        scores["hot_zones"] = self._calculate_dimension_score(
            phase_4.hot_zones, self._DIMENSION_WEIGHTS["hot_zones"]
        )
        scores["pow_challenges"] = self._calculate_dimension_score(
            phase_4.pow_challenges, self._DIMENSION_WEIGHTS["pow_challenges"]
        )

        return scores

    def _generate_recommendations(
        self,
        phase_1: DefenseAnatomyReport,
        phase_2: FlowStructureReport,
        phase_3: IdentityPersistenceReport,
        phase_4: BehaviorTimingReport,
    ) -> List[ActionRecommendation]:
        """
        Gera recomendações de ação baseadas nos resultados da análise.

        Args:
            phase_1: Relatório da Fase 1
            phase_2: Relatório da Fase 2
            phase_3: Relatório da Fase 3
            phase_4: Relatório da Fase 4

        Returns:
            Lista de ActionRecommendation ordenada por prioridade
        """
        recommendations: List[ActionRecommendation] = []

        # Honeypots: evitar elementos detectados
        for honeypot in phase_1.honeypots:
            recommendations.append(
                ActionRecommendation(
                    action_type="avoid_element",
                    target=honeypot.selector,
                    parameters={"technique": honeypot.hiding_technique},
                    priority=100,
                    reason=f"Honeypot detectado ({honeypot.hiding_technique})",
                )
            )

        # isTrusted validators: usar dispatchEvent com isTrusted
        for validator in phase_1.istrusted_validators:
            recommendations.append(
                ActionRecommendation(
                    action_type="use_cdp_dispatch",
                    target=validator.element_selector,
                    parameters={"event_types": validator.event_types},
                    priority=95,
                    reason="Validador isTrusted ativo — usar CDP Input.dispatchEvent",
                )
            )

        # WAF: adicionar delays e simular comportamento humano
        for waf in phase_1.waf_systems:
            delay_ms = 2000
            if waf.protection_level == "extreme":
                delay_ms = 5000
            elif waf.protection_level == "high":
                delay_ms = 3000
            elif waf.protection_level == "medium":
                delay_ms = 1500
            recommendations.append(
                ActionRecommendation(
                    action_type="delay",
                    target=None,
                    parameters={"ms": delay_ms, "waf_type": waf.type},
                    priority=90,
                    reason=f"WAF {waf.type} detectado (nível {waf.protection_level})",
                )
            )

        # Fingerprinting: mascarar APIs
        for fp in phase_3.fingerprinting_techniques:
            recommendations.append(
                ActionRecommendation(
                    action_type="mask_api",
                    target=None,
                    parameters={"api_type": fp.type, "library": fp.library},
                    priority=85,
                    reason=f"Fingerprinting {fp.type} detectado",
                )
            )

        # Monitoring scripts: bloquear tracking
        for script in phase_2.monitoring_scripts:
            if "session_replay" in script.capabilities:
                recommendations.append(
                    ActionRecommendation(
                        action_type="block_script",
                        target=script.script_url,
                        parameters={"type": script.type, "capabilities": script.capabilities},
                        priority=80,
                        reason=f"Session replay ativo via {script.type}",
                    )
                )

        # Cognitive latency: ajustar delays entre ações
        if phase_4.cognitive_latency_ms > 0:
            recommendations.append(
                ActionRecommendation(
                    action_type="delay",
                    target=None,
                    parameters={"ms": phase_4.cognitive_latency_ms},
                    priority=75,
                    reason=f"Latência cognitiva calculada: {phase_4.cognitive_latency_ms}ms",
                )
            )

        # PoW challenges: preparar solver ou esperar
        for pow_challenge in phase_4.pow_challenges:
            recommendations.append(
                ActionRecommendation(
                    action_type="solve_challenge",
                    target=None,
                    parameters={
                        "type": pow_challenge.type,
                        "uses_wasm": pow_challenge.uses_wasm,
                        "estimated_time_ms": pow_challenge.estimated_time_ms,
                    },
                    priority=100,
                    reason=f"Desafio PoW {pow_challenge.type} requer resolução",
                )
            )

        # Idle detection: manter atividade simulada
        for idle_zone in phase_4.idle_detection_zones:
            recommendations.append(
                ActionRecommendation(
                    action_type="simulate_activity",
                    target=None,
                    parameters={
                        "detector_type": idle_zone.type,
                        "threshold_ms": idle_zone.threshold_ms,
                    },
                    priority=70,
                    reason=f"Detecção de idle via {idle_zone.type}",
                )
            )

        # Ordenar por prioridade (maior primeiro)
        recommendations.sort(key=lambda r: r.priority, reverse=True)

        return recommendations

    def _identify_critical_warnings(
        self,
        phase_1: DefenseAnatomyReport,
        phase_2: FlowStructureReport,
        phase_3: IdentityPersistenceReport,
        phase_4: BehaviorTimingReport,
    ) -> List[str]:
        """
        Identifica warnings críticos que requerem atenção imediata.

        Args:
            phase_1: Relatório da Fase 1
            phase_2: Relatório da Fase 2
            phase_3: Relatório da Fase 3
            phase_4: Relatório da Fase 4

        Returns:
            Lista de strings com warnings críticos
        """
        warnings: List[str] = []

        # WAF detectado
        for waf in phase_1.waf_systems:
            protection = waf.protection_level
            if protection in ("high", "extreme"):
                warnings.append(
                    f"{waf.type.capitalize()} WAF detected (protection: {protection}, "
                    f"confidence: {waf.confidence:.0%})"
                )

        # isTrusted validation ativa
        if phase_1.istrusted_validators:
            event_types = set()
            for v in phase_1.istrusted_validators:
                event_types.update(v.event_types)
            warnings.append(
                f"isTrusted validation active on {len(phase_1.istrusted_validators)} "
                f"element(s) for events: {', '.join(sorted(event_types))}"
            )

        # Honeypots de alto risco
        high_risk_honeypots = [h for h in phase_1.honeypots if h.risk_level >= 80]
        if high_risk_honeypots:
            warnings.append(
                f"{len(high_risk_honeypots)} high-risk honeypot(s) detected — "
                f"interaction will trigger detection"
            )

        # Fingerprinting ativo
        if phase_3.fingerprinting_techniques:
            fp_types = [fp.type for fp in phase_3.fingerprinting_techniques]
            warnings.append(f"Active fingerprinting detected: {', '.join(fp_types)}")

        # User-Agent inconsistencies
        if phase_3.user_agent_inconsistencies:
            warnings.append(
                f"User-Agent inconsistencies detected: {'; '.join(phase_3.user_agent_inconsistencies)}"
            )

        # PoW challenges
        for pow_challenge in phase_4.pow_challenges:
            warnings.append(
                f"PoW challenge detected: {pow_challenge.type} "
                f"(estimated {pow_challenge.estimated_time_ms}ms to solve)"
            )

        # Session replay ativo
        for script in phase_2.monitoring_scripts:
            if "session_replay" in script.capabilities:
                warnings.append(
                    f"Session replay active via {script.type} — all actions are being recorded"
                )

        # DOM muito complexo
        if phase_4.dom_complexity and phase_4.dom_complexity.total_nodes > 5000:
            warnings.append(
                f"High DOM complexity ({phase_4.dom_complexity.total_nodes} nodes) — "
                f"recommended timeout: {phase_4.dom_complexity.recommended_timeout_ms}ms"
            )

        return warnings

    def _analyze_phase_1_defense_anatomy(self) -> DefenseAnatomyReport:
        """
        Fase 1: Anatomia de Defesa (Reconhecimento de Armadilhas).

        Dimensões:
        - Detecção de honeypots
        - Mapeamento de Shadow DOM
        - Auditoria de event listeners
        - Análise de isTrusted
        - Identificação de WAF/Anti-Bot

        Returns:
            DefenseAnatomyReport com resultados da fase
        """
        self.logger.debug("Analisando Fase 1: Defense Anatomy")

        # Dimensão 1: Detecção de honeypots
        honeypots = self._detect_honeypots()

        # Dimensão 2: Mapeamento de Shadow DOM
        shadow_dom_roots = self._detect_shadow_dom()

        # Dimensão 3: Auditoria de event listeners
        event_listeners = self._detect_event_listeners()

        # Dimensão 4: Análise de isTrusted
        istrusted_validators = self._detect_istrusted_validators(event_listeners)

        # Dimensão 5: Identificação de WAF/Anti-Bot
        waf_systems = self._detect_waf_systems()

        # Calcular risk score da fase
        risk_score = self._calculate_phase_risk(
            [
                (honeypots, self._DIMENSION_WEIGHTS["honeypots"]),
                (shadow_dom_roots, self._DIMENSION_WEIGHTS["shadow_dom"]),
                (event_listeners, self._DIMENSION_WEIGHTS["event_listeners"]),
                (istrusted_validators, self._DIMENSION_WEIGHTS["istrusted_validators"]),
                (waf_systems, self._DIMENSION_WEIGHTS["waf_systems"]),
            ]
        )

        report = DefenseAnatomyReport(
            honeypots=honeypots,
            shadow_dom_roots=shadow_dom_roots,
            event_listeners=event_listeners,
            istrusted_validators=istrusted_validators,
            waf_systems=waf_systems,
            risk_score=risk_score,
        )

        self.logger.debug(
            f"Fase 1 concluída | honeypots={len(honeypots)} shadow_dom={len(shadow_dom_roots)} "
            f"listeners={len(event_listeners)} isTrusted={len(istrusted_validators)} "
            f"WAFs={len(waf_systems)} | risk={risk_score}"
        )

        return report

    def _analyze_phase_2_flow_structure(self) -> FlowStructureReport:
        """
        Fase 2: Estrutura de Fluxo (Lógica Interna).

        Dimensões:
        - Identificação de SPA frameworks
        - Mapeamento de iframes
        - Análise de fluxo de redirecionamento
        - Identificação de scripts de monitoramento
        - Análise de XHR/Fetch

        Returns:
            FlowStructureReport com resultados da fase
        """
        self.logger.debug("Analisando Fase 2: Flow Structure")

        # Dimensão 6: Identificação de SPA frameworks
        spa_framework = self._detect_spa_framework()
        spa_state_objects = self._detect_spa_state(spa_framework)

        # Dimensão 7: Mapeamento de iframes
        iframes = self._detect_iframes()

        # Dimensão 8: Análise de fluxo de redirecionamento
        redirect_patterns = self._detect_redirect_patterns()

        # Dimensão 9: Identificação de scripts de monitoramento
        monitoring_scripts = self._detect_monitoring_scripts()

        # Dimensão 10: Análise de XHR/Fetch (API calls)
        api_calls = self._detect_api_calls()

        # Calcular risk score da fase
        countable_items = [
            (iframes, self._DIMENSION_WEIGHTS["iframes"]),
            (redirect_patterns, self._DIMENSION_WEIGHTS["redirect_patterns"]),
            (monitoring_scripts, self._DIMENSION_WEIGHTS["monitoring_scripts"]),
            (api_calls, self._DIMENSION_WEIGHTS["api_calls"]),
        ]
        risk_score = self._calculate_phase_risk(countable_items)
        # SPA framework adds a small bonus to risk
        if spa_framework:
            risk_score = min(100, risk_score + 10)

        report = FlowStructureReport(
            spa_framework=spa_framework,
            spa_state_objects=spa_state_objects,
            iframes=iframes,
            redirect_patterns=redirect_patterns,
            monitoring_scripts=monitoring_scripts,
            api_calls=api_calls,
            risk_score=risk_score,
        )

        self.logger.debug(
            f"Fase 2 concluída | spa={spa_framework.name if spa_framework else 'none'} "
            f"iframes={len(iframes)} redirects={len(redirect_patterns)} "
            f"monitoring={len(monitoring_scripts)} apis={len(api_calls)} | risk={risk_score}"
        )

        return report

    def _analyze_phase_3_identity_persistence(self) -> IdentityPersistenceReport:
        """
        Fase 3: Identidade & Persistência (Stealth).

        Dimensões:
        - Análise de cookies
        - Análise de storage
        - Detecção de fingerprinting
        - Validação de coerência User-Agent
        - Monitoramento de integridade TLS

        Returns:
            IdentityPersistenceReport com resultados da fase
        """
        self.logger.debug("Analisando Fase 3: Identity & Persistence")

        # Dimensão 11: Análise de cookies
        critical_cookies = self._detect_critical_cookies()

        # Dimensão 12: Análise de storage
        storage_data = self._detect_storage_data()

        # Dimensão 13: Detecção de fingerprinting
        fingerprinting_techniques = self._detect_fingerprinting()

        # Dimensão 14: Validação de coerência User-Agent
        user_agent_inconsistencies = self._detect_user_agent_inconsistencies()

        # Dimensão 15: Monitoramento de integridade TLS
        tls_events = self._detect_tls_events()

        # Calcular risk score da fase
        risk_items = [
            (critical_cookies, self._DIMENSION_WEIGHTS["cookies"]),
            (fingerprinting_techniques, self._DIMENSION_WEIGHTS["fingerprinting"]),
            (user_agent_inconsistencies, self._DIMENSION_WEIGHTS["user_agent"]),
            (tls_events, self._DIMENSION_WEIGHTS["tls"]),
        ]
        risk_score = self._calculate_phase_risk(risk_items)
        # Storage risk boost
        if storage_data and (storage_data.auth_tokens or storage_data.fingerprints):
            storage_boost = len(storage_data.auth_tokens) * 5 + len(storage_data.fingerprints) * 10
            risk_score = min(100, risk_score + storage_boost)

        report = IdentityPersistenceReport(
            critical_cookies=critical_cookies,
            storage_data=storage_data,
            fingerprinting_techniques=fingerprinting_techniques,
            user_agent_inconsistencies=user_agent_inconsistencies,
            tls_events=tls_events,
            risk_score=risk_score,
        )

        self.logger.debug(
            f"Fase 3 concluída | cookies={len(critical_cookies)} "
            f"storage={'yes' if storage_data else 'none'} "
            f"fingerprinting={len(fingerprinting_techniques)} "
            f"ua_issues={len(user_agent_inconsistencies)} "
            f"tls={len(tls_events)} | risk={risk_score}"
        )

        return report

    def _analyze_phase_4_behavior_timing(self) -> BehaviorTimingReport:
        """
        Fase 4: Comportamento & Timing (Mimicry).

        Dimensões:
        - Cálculo de latência cognitiva
        - Análise de densidade DOM
        - Identificação de zonas de detecção de idle
        - Mapeamento de hot zones
        - Detecção de desafios PoW

        Returns:
            BehaviorTimingReport com resultados da fase
        """
        self.logger.debug("Analisando Fase 4: Behavior & Timing")

        # Dimensão 16: Cálculo de latência cognitiva (baseado em DOM complexity)
        dom_complexity = self._detect_dom_complexity()
        cognitive_latency_ms = self._calculate_cognitive_latency(dom_complexity)

        # Dimensão 17: Análise de densidade DOM (já calculada acima)

        # Dimensão 18: Identificação de zonas de detecção de idle
        idle_detection_zones = self._detect_idle_detectors()

        # Dimensão 19: Mapeamento de hot zones
        hot_zones = self._detect_hot_zones()

        # Dimensão 20: Detecção de desafios PoW
        pow_challenges = self._detect_pow_challenges()

        # Calcular risk score da fase
        risk_items = [
            (idle_detection_zones, self._DIMENSION_WEIGHTS["idle_detection"]),
            (pow_challenges, self._DIMENSION_WEIGHTS["pow_challenges"]),
        ]
        risk_score = self._calculate_phase_risk(risk_items)
        # DOM complexity and latency contribution
        if dom_complexity and dom_complexity.total_nodes > 2000:
            risk_score = min(100, risk_score + 15)
        if cognitive_latency_ms > 3000:
            risk_score = min(100, risk_score + 10)

        report = BehaviorTimingReport(
            cognitive_latency_ms=cognitive_latency_ms,
            dom_complexity=dom_complexity,
            idle_detection_zones=idle_detection_zones,
            hot_zones=hot_zones,
            pow_challenges=pow_challenges,
            risk_score=risk_score,
        )

        self.logger.debug(
            f"Fase 4 concluída | latency={cognitive_latency_ms}ms "
            f"dom_nodes={dom_complexity.total_nodes if dom_complexity else 0} "
            f"idle={len(idle_detection_zones)} hot_zones={len(hot_zones)} "
            f"pow={len(pow_challenges)} | risk={risk_score}"
        )

        return report

    # =========================================================================
    # Phase 1 dimension analyzers
    # =========================================================================

    def _detect_honeypots(self) -> List[HoneypotElement]:
        """Detecta elementos honeypot na página."""
        raw = self._execute_js(_JS_DETECT_HONEYPOTS, default=[])
        if not raw or not isinstance(raw, list):
            return []

        honeypots = []
        for item in raw:
            try:
                technique = item.get("technique", "unknown")
                # Risk level based on technique
                risk_level = 60
                if technique == "display:none":
                    risk_level = 80
                elif technique == "opacity:0":
                    risk_level = 85
                elif technique == "off-viewport":
                    risk_level = 70
                elif technique == "zero-size":
                    risk_level = 75
                elif technique == "z-index:-1":
                    risk_level = 65

                honeypots.append(
                    HoneypotElement(
                        selector=item.get("selector", "unknown"),
                        coordinates=(item.get("x", 0), item.get("y", 0)),
                        hiding_technique=technique,
                        risk_level=risk_level,
                    )
                )
            except (KeyError, TypeError) as e:
                self.logger.debug(f"Erro ao processar honeypot: {e}")

        return honeypots

    def _detect_shadow_dom(self) -> List[ShadowDOMRoot]:
        """Detecta Shadow DOM roots na página."""
        raw = self._execute_js(_JS_DETECT_SHADOW_DOM, default=[])
        if not raw or not isinstance(raw, list):
            return []

        roots = []
        for item in raw:
            try:
                roots.append(
                    ShadowDOMRoot(
                        host_selector=item.get("host_selector", "unknown"),
                        mode=item.get("mode", "open"),
                        depth=item.get("depth", 0),
                        internal_structure=item.get("internal_structure", ""),
                    )
                )
            except (KeyError, TypeError) as e:
                self.logger.debug(f"Erro ao processar Shadow DOM root: {e}")

        return roots

    def _detect_event_listeners(self) -> List[EventListenerInfo]:
        """Audita event listeners na página via CDP DOMDebugger."""
        listeners = []

        # Tentar via CDP DOMDebugger (mais preciso)
        if self.cdp is not None and self.cdp.is_domain_enabled("DOMDebugger"):
            try:
                # Obter document node id
                doc_result = self.cdp.execute("DOM.getDocument", {"depth": 0})
                root_node_id = doc_result.get("root", {}).get("nodeId", 0)

                if root_node_id:
                    result = self.cdp.execute(
                        "DOMDebugger.getEventListeners",
                        {
                            "objectId": str(root_node_id),
                            "depth": 3,
                        },
                    )

                    for listener_data in result.get("listeners", []):
                        validates_istrusted = False
                        handler = listener_data.get("handler", {}).get("description", "")
                        if "isTrusted" in handler:
                            validates_istrusted = True

                        listeners.append(
                            EventListenerInfo(
                                event_type=listener_data.get("type", "unknown"),
                                target_selector=listener_data.get("targetSelector", "document"),
                                script_url=listener_data.get("scriptId", ""),
                                phase="capture" if listener_data.get("useCapture") else "bubble",
                                validates_istrusted=validates_istrusted,
                            )
                        )

                    return listeners
            except CDPConnectionError as e:
                self.logger.debug(f"CDP DOMDebugger falhou, usando fallback: {e}")

        # Fallback: detectar via getEventListeners (Chrome console API)
        _raw = self._execute_js(  # noqa: F841
            """
        (function() {
            var results = [];
            var targets = [document, document.body, window];
            var selectors = ['document', 'body', 'window'];
            var interactive = document.querySelectorAll('button, a, input, form, [onclick]');
            for (var i = 0; i < Math.min(interactive.length, 20); i++) {
                targets.push(interactive[i]);
                var sel = interactive[i].tagName.toLowerCase();
                if (interactive[i].id) sel += '#' + interactive[i].id;
                selectors.push(sel);
            }
            return {targets: selectors.length, selectors: selectors};
        })();
        """,
            default=None,
        )

        return listeners

    def _detect_istrusted_validators(
        self, event_listeners: List[EventListenerInfo]
    ) -> List[IsTrustedValidator]:
        """Detecta validadores de isTrusted entre os event listeners encontrados."""
        validators = []

        # Filtrar listeners que validam isTrusted
        istrusted_map: Dict[str, List[str]] = {}
        for listener in event_listeners:
            if listener.validates_istrusted:
                selector = listener.target_selector
                if selector not in istrusted_map:
                    istrusted_map[selector] = []
                istrusted_map[selector].append(listener.event_type)

        for selector, event_types in istrusted_map.items():
            validators.append(
                IsTrustedValidator(
                    element_selector=selector,
                    event_types=event_types,
                    validation_code="event.isTrusted check detected",
                )
            )

        # Também verificar via análise de scripts
        raw = self._execute_js(
            """
        (function() {
            var validators = [];
            var scripts = document.querySelectorAll('script');
            for (var i = 0; i < scripts.length; i++) {
                var text = scripts[i].textContent || '';
                if (/\\.isTrusted\\b/.test(text) || /event\\s*\\.\\s*isTrusted/.test(text)) {
                    var match = text.match(/([\\w.]+)\\.addEventListener\\s*\\(\\s*['\"]([\\w]+)['\"]/);
                    if (match) {
                        validators.push({
                            selector: match[1] || 'unknown',
                            event_type: match[2],
                            code: 'isTrusted validation in inline script'
                        });
                    }
                }
            }
            return validators;
        })();
        """,
            default=[],
        )

        if raw and isinstance(raw, list):
            for item in raw:
                try:
                    # Evitar duplicatas
                    selector = item.get("selector", "unknown")
                    already_exists = any(v.element_selector == selector for v in validators)
                    if not already_exists:
                        validators.append(
                            IsTrustedValidator(
                                element_selector=selector,
                                event_types=[item.get("event_type", "click")],
                                validation_code=item.get("code", ""),
                            )
                        )
                except (KeyError, TypeError):
                    pass

        return validators

    def _detect_waf_systems(self) -> List[WAFDetection]:
        """Detecta sistemas WAF/Anti-Bot na página."""
        raw = self._execute_js(_JS_DETECT_WAF, default=[])
        if not raw or not isinstance(raw, list):
            return []

        wafs = []
        for item in raw:
            try:
                wafs.append(
                    WAFDetection(
                        type=item.get("type", "unknown"),
                        confidence=item.get("confidence", 0.0),
                        signatures=item.get("signatures", []),
                        protection_level=item.get("protection_level", "low"),
                    )
                )
            except (KeyError, TypeError) as e:
                self.logger.debug(f"Erro ao processar WAF detection: {e}")

        return wafs

    # =========================================================================
    # Phase 2 dimension analyzers
    # =========================================================================

    def _detect_spa_framework(self) -> Optional[SPAFramework]:
        """Detecta framework SPA na página."""
        raw = self._execute_js(_JS_DETECT_SPA_FRAMEWORK, default=None)
        if not raw or not isinstance(raw, dict):
            return None

        return SPAFramework(
            name=raw.get("name", "unknown"),
            version=raw.get("version"),
            devtools_hook=raw.get("devtools_hook"),
        )

    def _detect_spa_state(self, spa_framework: Optional[SPAFramework]) -> List[StateObject]:
        """Detecta objetos de estado SPA."""
        if not spa_framework:
            return []

        state_script = (
            """
        (function() {
            var states = [];
            var checks = {
                react: [
                    {path: '__REACT_DEVTOOLS_GLOBAL_HOOK__', check: function() { return window.__REACT_DEVTOOLS_GLOBAL_HOOK__; }},
                    {path: '__NEXT_DATA__', check: function() { return window.__NEXT_DATA__; }},
                ],
                vue: [
                    {path: '__VUE__', check: function() { return window.__VUE__; }},
                    {path: '__NUXT__', check: function() { return window.__NUXT__; }},
                ],
                angular: [
                    {path: 'ng', check: function() { return window.ng; }},
                ],
            };
            var framework = '%s';
            var frameworkChecks = checks[framework] || [];
            for (var i = 0; i < frameworkChecks.length; i++) {
                try {
                    var obj = frameworkChecks[i].check();
                    if (obj) {
                        var componentCount = 0;
                        var hasRouter = false;
                        try {
                            if (typeof obj === 'object') {
                                componentCount = Object.keys(obj).length;
                            }
                            hasRouter = !!(window.__NEXT_DATA__ && window.__NEXT_DATA__.page) ||
                                       !!(window.__NUXT__ && window.__NUXT__.$route) ||
                                       !!document.querySelector('[data-reactroot]');
                        } catch(e) {}
                        states.push({
                            path: frameworkChecks[i].path,
                            component_count: componentCount,
                            has_router: hasRouter
                        });
                    }
                } catch(e) {}
            }
            return states;
        })();
        """
            % spa_framework.name
        )

        raw = self._execute_js(state_script, default=[])
        if not raw or not isinstance(raw, list):
            return []

        state_objects = []
        for item in raw:
            try:
                state_objects.append(
                    StateObject(
                        path=item.get("path", ""),
                        component_count=item.get("component_count", 0),
                        has_router=item.get("has_router", False),
                    )
                )
            except (KeyError, TypeError):
                pass

        return state_objects

    def _detect_iframes(self) -> List[IframeInfo]:
        """Detecta iframes na página."""
        raw = self._execute_js(_JS_DETECT_IFRAMES, default=[])
        if not raw or not isinstance(raw, list):
            return []

        iframes = []
        for item in raw:
            try:
                iframes.append(
                    IframeInfo(
                        selector=item.get("selector", "iframe"),
                        src=item.get("src", ""),
                        is_same_origin=item.get("is_same_origin", False),
                        sandbox_attributes=item.get("sandbox_attributes", []),
                        nesting_level=item.get("nesting_level", 0),
                    )
                )
            except (KeyError, TypeError) as e:
                self.logger.debug(f"Erro ao processar iframe: {e}")

        return iframes

    def _detect_redirect_patterns(self) -> List[RedirectPattern]:
        """Detecta padrões de redirecionamento."""
        patterns = []

        # Detectar via CDP Network se disponível
        if self.cdp is not None and self.cdp.is_domain_enabled("Network"):
            try:
                # Verificar performance entries para redirects
                raw = self._execute_js(
                    """
                (function() {
                    var redirects = [];
                    var entries = performance.getEntriesByType('navigation');
                    for (var i = 0; i < entries.length; i++) {
                        if (entries[i].redirectCount > 0) {
                            redirects.push({
                                type: 'http_302',
                                from_url: entries[i].name,
                                to_url: window.location.href,
                                timestamp: entries[i].redirectStart
                            });
                        }
                    }
                    var resources = performance.getEntriesByType('resource');
                    for (var j = 0; j < resources.length; j++) {
                        if (resources[j].redirectStart > 0) {
                            redirects.push({
                                type: 'http_302',
                                from_url: resources[j].name,
                                to_url: resources[j].name,
                                timestamp: resources[j].redirectStart
                            });
                        }
                    }
                    return redirects;
                })();
                """,
                    default=[],
                )

                if raw and isinstance(raw, list):
                    for item in raw:
                        try:
                            patterns.append(
                                RedirectPattern(
                                    type=item.get("type", "http_302"),
                                    from_url=item.get("from_url", ""),
                                    to_url=item.get("to_url", ""),
                                    timestamp=item.get("timestamp", 0.0),
                                )
                            )
                        except (KeyError, TypeError):
                            pass
            except CDPConnectionError:
                pass

        return patterns

    def _detect_monitoring_scripts(self) -> List[MonitoringScript]:
        """Detecta scripts de monitoramento na página."""
        raw = self._execute_js(_JS_DETECT_MONITORING, default=[])
        if not raw or not isinstance(raw, list):
            return []

        scripts = []
        for item in raw:
            try:
                scripts.append(
                    MonitoringScript(
                        type=item.get("type", "unknown"),
                        script_url=item.get("script_url", ""),
                        capabilities=item.get("capabilities", []),
                    )
                )
            except (KeyError, TypeError) as e:
                self.logger.debug(f"Erro ao processar monitoring script: {e}")

        return scripts

    def _detect_api_calls(self) -> List[APICallInfo]:
        """Detecta chamadas de API (XHR/Fetch) via interceptação."""
        api_calls = []

        # Via CDP Network se disponível
        if self.cdp is not None and self.cdp.is_domain_enabled("Network"):
            try:
                # Verificar performance entries para XHR/Fetch
                raw = self._execute_js(
                    """
                (function() {
                    var calls = [];
                    var resources = performance.getEntriesByType('resource');
                    for (var i = 0; i < resources.length; i++) {
                        var r = resources[i];
                        if (r.initiatorType === 'xmlhttprequest' || r.initiatorType === 'fetch') {
                            var isTracking = /analytics|tracking|pixel|beacon|collect|event/i.test(r.name);
                            calls.push({
                                url: r.name,
                                method: 'GET',
                                headers: {},
                                payload: null,
                                triggered_by: 'load',
                                is_tracking: isTracking
                            });
                        }
                    }
                    return calls;
                })();
                """,
                    default=[],
                )

                if raw and isinstance(raw, list):
                    for item in raw:
                        try:
                            api_calls.append(
                                APICallInfo(
                                    url=item.get("url", ""),
                                    method=item.get("method", "GET"),
                                    headers=item.get("headers", {}),
                                    payload=item.get("payload"),
                                    triggered_by=item.get("triggered_by", "load"),
                                    is_tracking=item.get("is_tracking", False),
                                )
                            )
                        except (KeyError, TypeError):
                            pass
            except CDPConnectionError:
                pass

        return api_calls

    # =========================================================================
    # Phase 3 dimension analyzers
    # =========================================================================

    def _detect_critical_cookies(self) -> List[CookieInfo]:
        """Detecta cookies críticos (sessão, auth, tracking)."""
        cookies = []

        # Via CDP Network.getAllCookies (mais completo — inclui httpOnly)
        if self.cdp is not None and self.cdp.is_domain_enabled("Network"):
            try:
                result = self.cdp.execute("Network.getAllCookies", {})
                for cookie in result.get("cookies", []):
                    name = cookie.get("name", "")
                    is_critical = any(
                        pattern in name.lower()
                        for pattern in [
                            "session",
                            "sid",
                            "token",
                            "auth",
                            "jwt",
                            "csrf",
                            "xsrf",
                            "_ga",
                            "__cf",
                            "datadome",
                            "_px",
                        ]
                    )

                    if is_critical:
                        cookies.append(
                            CookieInfo(
                                name=name,
                                value=cookie.get("value", "")[:50],  # Truncar valor
                                domain=cookie.get("domain", ""),
                                path=cookie.get("path", "/"),
                                httponly=cookie.get("httpOnly", False),
                                secure=cookie.get("secure", False),
                                samesite=cookie.get("sameSite", "None"),
                                is_session_critical="session" in name.lower()
                                or "auth" in name.lower(),
                            )
                        )

                return cookies
            except CDPConnectionError as e:
                self.logger.debug(f"CDP Network.getAllCookies falhou: {e}")

        # Fallback: document.cookie (não inclui httpOnly)
        raw = self._execute_js(
            """
        (function() {
            var cookies = [];
            var pairs = document.cookie.split(';');
            for (var i = 0; i < pairs.length; i++) {
                var parts = pairs[i].trim().split('=');
                if (parts.length >= 2) {
                    var name = parts[0].trim();
                    var value = parts.slice(1).join('=').substring(0, 50);
                    var isCritical = /session|sid|token|auth|jwt|csrf|xsrf|_ga|__cf|datadome|_px/i.test(name);
                    if (isCritical) {
                        cookies.push({
                            name: name,
                            value: value,
                            domain: window.location.hostname,
                            path: '/',
                            httponly: false,
                            secure: window.location.protocol === 'https:',
                            samesite: 'None',
                            is_session_critical: /session|auth/i.test(name)
                        });
                    }
                }
            }
            return cookies;
        })();
        """,
            default=[],
        )

        if raw and isinstance(raw, list):
            for item in raw:
                try:
                    cookies.append(
                        CookieInfo(
                            name=item.get("name", ""),
                            value=item.get("value", ""),
                            domain=item.get("domain", ""),
                            path=item.get("path", "/"),
                            httponly=item.get("httponly", False),
                            secure=item.get("secure", False),
                            samesite=item.get("samesite", "None"),
                            is_session_critical=item.get("is_session_critical", False),
                        )
                    )
                except (KeyError, TypeError):
                    pass

        return cookies

    def _detect_storage_data(self) -> Optional[StorageAnalysis]:
        """Analisa localStorage e sessionStorage."""
        raw = self._execute_js(_JS_DETECT_STORAGE, default=None)
        if not raw or not isinstance(raw, dict):
            return None

        return StorageAnalysis(
            local_storage_keys=raw.get("local_storage_keys", []),
            session_storage_keys=raw.get("session_storage_keys", []),
            auth_tokens=raw.get("auth_tokens", []),
            session_data=raw.get("session_data", []),
            fingerprints=raw.get("fingerprints", []),
        )

    def _detect_fingerprinting(self) -> List[FingerprintTechnique]:
        """Detecta técnicas de fingerprinting ativas na página."""
        raw = self._execute_js(_JS_DETECT_FINGERPRINTING, default=[])
        if not raw or not isinstance(raw, list):
            return []

        techniques = []
        for item in raw:
            try:
                techniques.append(
                    FingerprintTechnique(
                        type=item.get("type", "unknown"),
                        library=item.get("library"),
                        code_location=item.get("code_location", ""),
                    )
                )
            except (KeyError, TypeError) as e:
                self.logger.debug(f"Erro ao processar fingerprinting technique: {e}")

        return techniques

    def _detect_user_agent_inconsistencies(self) -> List[str]:
        """Detecta inconsistências no User-Agent."""
        inconsistencies = []

        raw = self._execute_js(
            """
        (function() {
            var issues = [];
            var ua = navigator.userAgent;
            var platform = navigator.platform;
            var vendor = navigator.vendor;

            // Check webdriver flag
            if (navigator.webdriver) {
                issues.push('navigator.webdriver is true (automation detected)');
            }

            // Check platform/UA mismatch
            if (/Windows/.test(ua) && !/Win/.test(platform)) {
                issues.push('UA says Windows but platform is ' + platform);
            }
            if (/Mac/.test(ua) && !/Mac/.test(platform)) {
                issues.push('UA says Mac but platform is ' + platform);
            }
            if (/Linux/.test(ua) && !/Linux/.test(platform)) {
                issues.push('UA says Linux but platform is ' + platform);
            }

            // Check headless indicators
            if (/HeadlessChrome/.test(ua)) {
                issues.push('HeadlessChrome detected in User-Agent');
            }

            // Check Chrome-specific vendor
            if (/Chrome/.test(ua) && vendor !== 'Google Inc.') {
                issues.push('Chrome UA but vendor is not Google Inc. (vendor=' + vendor + ')');
            }

            // Check missing plugins (common in headless)
            if (navigator.plugins.length === 0 && /Chrome/.test(ua)) {
                issues.push('Chrome detected but navigator.plugins is empty (headless indicator)');
            }

            // Check languages
            if (!navigator.languages || navigator.languages.length === 0) {
                issues.push('navigator.languages is empty (automation indicator)');
            }

            return issues;
        })();
        """,
            default=[],
        )

        if raw and isinstance(raw, list):
            inconsistencies = raw

        return inconsistencies

    def _detect_tls_events(self) -> List[TLSEvent]:
        """Detecta eventos TLS via CDP Security domain."""
        events = []

        if self.cdp is not None and self.cdp.is_domain_enabled("Security"):
            try:
                self.cdp.execute("Security.enable", {})
                # Obter estado de segurança atual
                state = self.cdp.execute("Security.getSecurityState", {})
                if state:
                    events.append(
                        TLSEvent(
                            event_type="connection",
                            timestamp=time.time(),
                            certificate_info={
                                "security_state": state.get("securityState", "unknown"),
                            },
                        )
                    )
            except CDPConnectionError as e:
                self.logger.debug(f"CDP Security falhou: {e}")

        return events

    # =========================================================================
    # Phase 4 dimension analyzers
    # =========================================================================

    def _detect_dom_complexity(self) -> Optional[DOMComplexity]:
        """Analisa complexidade do DOM."""
        raw = self._execute_js(_JS_DETECT_DOM_COMPLEXITY, default=None)
        if not raw or not isinstance(raw, dict):
            return None

        return DOMComplexity(
            total_nodes=raw.get("total_nodes", 0),
            max_depth=raw.get("max_depth", 0),
            script_size_kb=raw.get("script_size_kb", 0),
            css_size_kb=raw.get("css_size_kb", 0),
            recommended_timeout_ms=raw.get("recommended_timeout_ms", 1000),
        )

    def _calculate_cognitive_latency(self, dom_complexity: Optional[DOMComplexity]) -> int:
        """
        Calcula latência cognitiva recomendada baseada na complexidade da página.

        Simula o tempo que um humano levaria para processar a página visualmente.

        Args:
            dom_complexity: Complexidade do DOM detectada

        Returns:
            Latência em milissegundos
        """
        if not dom_complexity:
            return 500  # Default mínimo

        # Base: 500ms mínimo
        base_ms = 500

        # +1ms por 10 nodes DOM
        node_factor = dom_complexity.total_nodes // 10

        # +50ms por nível de profundidade acima de 5
        depth_factor = max(0, dom_complexity.max_depth - 5) * 50

        # +100ms por 100kb de scripts
        script_factor = dom_complexity.script_size_kb

        total = base_ms + node_factor + depth_factor + script_factor

        # Limitar entre 500ms e 10000ms
        return max(500, min(10000, total))

    def _detect_idle_detectors(self) -> List[IdleDetector]:
        """Detecta mecanismos de detecção de idle/inatividade."""
        raw = self._execute_js(_JS_DETECT_IDLE_DETECTORS, default=[])
        if not raw or not isinstance(raw, list):
            return []

        detectors = []
        for item in raw:
            try:
                detectors.append(
                    IdleDetector(
                        type=item.get("type", "unknown"),
                        threshold_ms=item.get("threshold_ms", 0),
                        callback_location=item.get("callback_location", ""),
                    )
                )
            except (KeyError, TypeError) as e:
                self.logger.debug(f"Erro ao processar idle detector: {e}")

        return detectors

    def _detect_hot_zones(self) -> List[HotZone]:
        """Detecta zonas de clique natural (botões, links, CTAs)."""
        raw = self._execute_js(_JS_DETECT_HOT_ZONES, default=[])
        if not raw or not isinstance(raw, list):
            return []

        zones = []
        for item in raw:
            try:
                coords = item.get("coordinates", [0, 0, 0, 0])
                click_points = item.get("recommended_click_points", [])

                zones.append(
                    HotZone(
                        element_selector=item.get("element_selector", "unknown"),
                        coordinates=tuple(coords),
                        recommended_click_points=[tuple(p) for p in click_points],
                        priority=item.get("priority", 50),
                    )
                )
            except (KeyError, TypeError) as e:
                self.logger.debug(f"Erro ao processar hot zone: {e}")

        return zones

    def _detect_pow_challenges(self) -> List[PoWChallenge]:
        """Detecta desafios Proof of Work (CAPTCHA, etc)."""
        raw = self._execute_js(_JS_DETECT_POW, default=[])
        if not raw or not isinstance(raw, list):
            return []

        challenges = []
        for item in raw:
            try:
                challenges.append(
                    PoWChallenge(
                        type=item.get("type", "custom"),
                        uses_wasm=item.get("uses_wasm", False),
                        uses_workers=item.get("uses_workers", False),
                        estimated_time_ms=item.get("estimated_time_ms", 5000),
                    )
                )
            except (KeyError, TypeError) as e:
                self.logger.debug(f"Erro ao processar PoW challenge: {e}")

        return challenges

    # =========================================================================
    # Utility methods
    # =========================================================================

    def _calculate_phase_risk(self, dimension_items: list) -> int:
        """
        Calcula risk score de uma fase baseado nas dimensões.

        Args:
            dimension_items: Lista de (items_list, weight) tuples

        Returns:
            Score de risco 0-100
        """
        if not dimension_items:
            return 0

        total_score = 0
        total_weight = 0

        for items, weight in dimension_items:
            score = self._calculate_dimension_score(items, weight)
            total_score += score
            total_weight += weight

        if total_weight == 0:
            return 0

        return min(100, int(total_score / len(dimension_items)))
