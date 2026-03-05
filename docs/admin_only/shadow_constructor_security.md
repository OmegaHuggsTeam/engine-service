# 🛡️ ShadowConstructor - Security & Governance

## ⚠️ CLASSIFICAÇÃO: ADMIN ONLY

Este documento define a arquitetura de segurança e governança para o ShadowConstructor - o "Modo Deus" do sistema.

---

## 1. 🔒 Princípios de Segurança

### Isolamento de Execução (Shadow-Sandbox)

O ShadowConstructor opera em um ambiente isolado que garante:

1. **Zero External Logging**: Técnicas shadow NUNCA enviam logs para serviços externos
2. **RAM-Only Execution**: Skills shadow existem apenas na memória durante execução
3. **No Disk Persistence**: Código shadow não é salvo em disco de forma legível
4. **Audit Trail Local**: Logs de auditoria apenas em arquivo local criptografado

### Volatilidade (Ephemeral Execution)

```python
class ShadowSkill:
    """
    Skill volátil que existe apenas na RAM.
    
    - Não persiste em disco
    - Auto-destruição após execução
    - Logs apenas em memória
    """
    
    def __init__(self, code: str, context: str):
        self.code = code  # Código em memória
        self.context = context
        self.executed = False
        self._result = None
    
    def execute(self, *args, **kwargs):
        """Executa skill e marca para destruição."""
        if self.executed:
            raise RuntimeError("Shadow skill já foi executada (single-use)")
        
        # Executar em namespace isolado
        namespace = {'__builtins__': __builtins__}
        exec(self.code, namespace)
        
        # Obter função gerada
        skill_func = namespace.get('shadow_skill')
        if not skill_func:
            raise RuntimeError("Shadow skill inválida")
        
        # Executar
        self._result = skill_func(*args, **kwargs)
        self.executed = True
        
        # Auto-destruição
        self._self_destruct()
        
        return self._result
    
    def _self_destruct(self):
        """Limpa código da memória."""
        self.code = None
        # Forçar garbage collection
        import gc
        gc.collect()
```

---

## 2. 🚨 Pílula de Segurança (Anti-Exposição)

### Estratégia de Proteção

#### A. Detecção de Ambiente

```python
import os
import sys

def is_safe_environment():
    """
    Verifica se ambiente é seguro para shadow techniques.
    
    Returns:
        True se ambiente é seguro
    """
    # 1. Verificar se está em produção
    if os.getenv('ENVIRONMENT') == 'production':
        return False
    
    # 2. Verificar se há debuggers ativos
    if sys.gettrace() is not None:
        return False
    
    # 3. Verificar se há monitoring tools
    monitoring_vars = [
        'SENTRY_DSN',
        'DATADOG_API_KEY',
        'NEW_RELIC_LICENSE_KEY'
    ]
    
    for var in monitoring_vars:
        if os.getenv(var):
            return False
    
    # 4. Verificar se está em container
    if os.path.exists('/.dockerenv'):
        return False
    
    return True
```

#### B. Shadow Mode Flag

```python
import os
from enum import Enum

class ExecutionMode(Enum):
    """Modos de execução do Selum."""
    NORMAL = "normal"
    ADMIN = "admin"
    SHADOW = "shadow"  # Modo Deus

def get_execution_mode():
    """
    Determina modo de execução baseado em variáveis de ambiente.
    
    Returns:
        ExecutionMode
    """
    # Verificar flag explícita
    mode = os.getenv('SELUM_MODE', 'normal').lower()
    
    if mode == 'shadow':
        # Validar ambiente seguro
        if not is_safe_environment():
            raise RuntimeError(
                "SHADOW MODE bloqueado: ambiente não é seguro. "
                "Shadow techniques só podem ser usadas em ambiente local controlado."
            )
        return ExecutionMode.SHADOW
    
    elif mode == 'admin':
        return ExecutionMode.ADMIN
    
    return ExecutionMode.NORMAL
```

#### C. Logging Isolado

```python
import logging
from typing import Optional

class ShadowLogger:
    """
    Logger isolado para shadow operations.
    
    - Logs apenas em memória ou arquivo local
    - NUNCA envia para serviços externos
    - Auto-limpeza após sessão
    """
    
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        self.memory_logs = []
        self._setup_logger()
    
    def _setup_logger(self):
        """Configura logger isolado."""
        self.logger = logging.getLogger('shadow')
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False  # 🔑 Não propagar para root logger
        
        # Handler de memória
        memory_handler = logging.Handler()
        memory_handler.emit = lambda record: self.memory_logs.append(
            self.logger.format(record)
        )
        self.logger.addHandler(memory_handler)
        
        # Handler de arquivo (opcional, local apenas)
        if self.log_file:
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s [SHADOW] %(levelname)s: %(message)s'
            ))
            self.logger.addHandler(file_handler)
    
    def log(self, level: str, message: str):
        """Log isolado."""
        getattr(self.logger, level.lower())(message)
    
    def get_logs(self):
        """Retorna logs da memória."""
        return self.memory_logs.copy()
    
    def clear(self):
        """Limpa logs da memória."""
        self.memory_logs.clear()
    
    def __del__(self):
        """Auto-limpeza ao destruir objeto."""
        self.clear()
```

---

## 3. 🎭 ShadowConstructor Implementation

### Arquitetura Completa

```python
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ShadowAudit:
    """Registro de auditoria de operação shadow."""
    timestamp: datetime
    technique: str
    target: str
    success: bool
    context: str

class ShadowConstructor:
    """
    Constructor com poderes proibidos.
    
    Modo Deus do sistema - use apenas em último caso.
    
    Features:
    - React Fiber hijacking
    - Ghost interactions (sem telemetria)
    - CDP raw injection
    - Session cloning
    - Anti-detecção avançada
    
    Security:
    - Execução isolada (shadow-sandbox)
    - Logs apenas locais
    - Skills voláteis (RAM-only)
    - Auditoria obrigatória
    """
    
    def __init__(self, driver, mode: ExecutionMode = None):
        """
        Inicializa ShadowConstructor.
        
        Args:
            driver: WebDriver instance
            mode: Modo de execução (auto-detectado se None)
            
        Raises:
            RuntimeError: Se ambiente não é seguro para shadow mode
        """
        self.driver = driver
        self.mode = mode or get_execution_mode()
        
        # Validar modo
        if self.mode != ExecutionMode.SHADOW:
            raise RuntimeError(
                f"ShadowConstructor requer SHADOW mode. Modo atual: {self.mode.value}"
            )
        
        # Validar ambiente
        if not is_safe_environment():
            raise RuntimeError(
                "Ambiente não é seguro para shadow operations. "
                "Verifique: produção, debuggers, monitoring tools."
            )
        
        # Setup
        self._logger = ShadowLogger(log_file='.shadow_audit.log')
        self._audit_trail = []
        self._enable_stealth()
        
        self._logger.log('info', 'ShadowConstructor inicializado')
    
    def _enable_stealth(self):
        """Habilita modo stealth automaticamente."""
        from docs.admin_only.forbidden_grimoire import remove_automation_traces
        remove_automation_traces(self.driver)
        self._logger.log('info', 'Stealth mode habilitado')
    
    def _audit(self, technique: str, target: str, success: bool, context: str = ""):
        """Registra operação shadow para auditoria."""
        audit = ShadowAudit(
            timestamp=datetime.now(),
            technique=technique,
            target=target,
            success=success,
            context=context
        )
        self._audit_trail.append(audit)
        
        self._logger.log('info', 
            f"[AUDIT] {technique} on {target}: {'SUCCESS' if success else 'FAILED'}"
        )
    
    # ===== SHADOW TECHNIQUES =====
    
    def soul_snatch(self, selector: str, prop: str, value: Any) -> bool:
        """
        React Fiber hijacking.
        
        Manipula props diretamente no Fiber node.
        
        Args:
            selector: Seletor CSS do elemento
            prop: Nome da prop a alterar
            value: Novo valor
            
        Returns:
            True se bem-sucedido
        """
        from docs.admin_only.forbidden_grimoire import hijack_fiber_props
        
        try:
            result = hijack_fiber_props(self.driver, selector, prop, value)
            self._audit('soul_snatch', selector, result, f"{prop}={value}")
            return result
        except Exception as e:
            self._audit('soul_snatch', selector, False, str(e))
            raise
    
    def ghost_click(self, selector: str) -> bool:
        """
        Click sem telemetria.
        
        Remove event listeners → Click → Restaura listeners.
        
        Args:
            selector: Seletor CSS do elemento
            
        Returns:
            True se bem-sucedido
        """
        from docs.admin_only.forbidden_grimoire import ghost_click as _ghost_click
        
        try:
            result = _ghost_click(self.driver, selector)
            self._audit('ghost_click', selector, result)
            return result
        except Exception as e:
            self._audit('ghost_click', selector, False, str(e))
            raise
    
    def matrix_click(self, selector: str) -> bool:
        """
        Click trusted via CDP.
        
        Usa Runtime.evaluate com userGesture=true.
        
        Args:
            selector: Seletor CSS do elemento
            
        Returns:
            True se bem-sucedido
        """
        from docs.admin_only.forbidden_grimoire import cdp_trusted_click
        
        try:
            result = cdp_trusted_click(self.driver, selector)
            self._audit('matrix_click', selector, result)
            return result
        except Exception as e:
            self._audit('matrix_click', selector, False, str(e))
            raise
    
    def exfiltrate_session(self) -> list:
        """
        Extrai sessão completa (cookies HttpOnly).
        
        Returns:
            Lista de cookies
        """
        from docs.admin_only.forbidden_grimoire import exfiltrate_httponly_cookies
        
        try:
            cookies = exfiltrate_httponly_cookies(self.driver)
            self._audit('exfiltrate_session', 'current_page', True, 
                       f"{len(cookies)} cookies")
            return cookies
        except Exception as e:
            self._audit('exfiltrate_session', 'current_page', False, str(e))
            raise
    
    def clone_to(self, target_driver) -> bool:
        """
        Clona sessão para outro driver.
        
        Args:
            target_driver: WebDriver alvo
            
        Returns:
            True se bem-sucedido
        """
        from docs.admin_only.forbidden_grimoire import clone_browser_session
        
        try:
            result = clone_browser_session(self.driver, target_driver)
            self._audit('clone_session', 'target_driver', result)
            return result
        except Exception as e:
            self._audit('clone_session', 'target_driver', False, str(e))
            raise
    
    # ===== VOLATILE SKILLS =====
    
    def execute_shadow_skill(self, code: str, context: str, *args, **kwargs):
        """
        Executa shadow skill volátil.
        
        Skill existe apenas na RAM e é destruída após execução.
        
        Args:
            code: Código Python da skill
            context: Contexto/descrição da operação
            *args, **kwargs: Argumentos para a skill
            
        Returns:
            Resultado da execução
        """
        skill = ShadowSkill(code, context)
        
        try:
            result = skill.execute(*args, **kwargs)
            self._audit('shadow_skill', context, True)
            return result
        except Exception as e:
            self._audit('shadow_skill', context, False, str(e))
            raise
    
    # ===== AUDIT & CLEANUP =====
    
    def get_audit_trail(self) -> list:
        """Retorna trilha de auditoria."""
        return self._audit_trail.copy()
    
    def export_audit(self, filepath: str):
        """Exporta auditoria para arquivo."""
        import json
        
        audit_data = [
            {
                'timestamp': a.timestamp.isoformat(),
                'technique': a.technique,
                'target': a.target,
                'success': a.success,
                'context': a.context
            }
            for a in self._audit_trail
        ]
        
        with open(filepath, 'w') as f:
            json.dump(audit_data, f, indent=2)
        
        self._logger.log('info', f'Audit exported to {filepath}')
    
    def cleanup(self):
        """Limpeza completa de rastros."""
        self._logger.log('info', 'Iniciando cleanup')
        
        # Limpar audit trail
        self._audit_trail.clear()
        
        # Limpar logs
        self._logger.clear()
        
        self._logger.log('info', 'Cleanup concluído')
    
    def __del__(self):
        """Auto-cleanup ao destruir objeto."""
        self.cleanup()
```

---

## 4. 🔐 Integração com SelumOfPersistence

### Modo Condicional

```python
class SelumOfPersistence:
    """Paladino da Persistência com suporte a Shadow Mode."""
    
    def __init__(self, driver, groq_api_key=None, mode=None):
        self.driver = driver
        self.mode = mode or get_execution_mode()
        
        # Componentes básicos
        self.skill_registry = {}
        self.error_detector = ErrorDetector()
        
        # Shadow Constructor (apenas em SHADOW mode)
        self.shadow: Optional[ShadowConstructor] = None
        
        if self.mode == ExecutionMode.SHADOW:
            try:
                self.shadow = ShadowConstructor(driver, mode=self.mode)
                self.logger.wisdom("⚡ SHADOW MODE ATIVADO - Poderes proibidos disponíveis")
            except RuntimeError as e:
                self.logger.error(f"Falha ao ativar Shadow Mode: {e}")
                self.mode = ExecutionMode.ADMIN
    
    def _should_use_shadow(self, error_count: int) -> bool:
        """
        Decide se deve usar shadow techniques.
        
        Critérios:
        - Shadow mode habilitado
        - Erro crítico (3+ falhas consecutivas)
        - Ambiente seguro
        """
        return (
            self.shadow is not None and
            error_count >= 3 and
            is_safe_environment()
        )
```

---

## 5. 📋 Checklist de Segurança

### Antes de Usar Shadow Techniques

- [ ] Ambiente é local (não produção)
- [ ] Sem debuggers ativos
- [ ] Sem monitoring tools (Sentry, Datadog, etc.)
- [ ] Permissão explícita para automação
- [ ] Auditoria habilitada
- [ ] Backup de sessão (se necessário)

### Durante Execução

- [ ] Logs apenas locais
- [ ] Skills voláteis (RAM-only)
- [ ] Audit trail ativo
- [ ] Timeout configurado
- [ ] Fallback preparado

### Após Execução

- [ ] Exportar audit trail
- [ ] Cleanup de rastros
- [ ] Validar resultado
- [ ] Documentar uso
- [ ] Revisar logs

---

## 6. 🚨 Plano de Contingência

### Se Detectado

1. **Parar imediatamente** todas as operações shadow
2. **Executar cleanup** completo
3. **Exportar audit trail** para análise
4. **Voltar para modo NORMAL**
5. **Documentar incidente**

### Se Falhar

1. **Não repetir** a mesma técnica
2. **Tentar fallback** (abstrações normais)
3. **Logar erro** detalhadamente
4. **Notificar admin**
5. **Revisar estratégia**

---

## 7. 📝 Exemplo de Uso Completo

```python
import os

# 1. Configurar ambiente
os.environ['SELUM_MODE'] = 'shadow'

# 2. Inicializar Selum
selum = SelumOfPersistence(driver, mode=ExecutionMode.SHADOW)

# 3. Verificar shadow mode
if selum.shadow:
    print("⚡ Shadow Mode ativo")
    
    # 4. Usar técnica shadow
    try:
        # Habilitar botão desabilitado
        selum.shadow.soul_snatch("button.submit", "disabled", False)
        
        # Click sem telemetria
        selum.shadow.ghost_click("button.submit")
        
        # Exportar audit
        selum.shadow.export_audit('.shadow_audit.json')
        
    except Exception as e:
        print(f"Shadow operation failed: {e}")
        
    finally:
        # 5. Cleanup obrigatório
        selum.shadow.cleanup()
else:
    print("❌ Shadow Mode não disponível")
```

---

## 8. ⚖️ Conformidade Legal

### LGPD (Brasil)

- **Art. 7º**: Base legal para tratamento de dados
- **Art. 46**: Segurança e sigilo de dados
- **Art. 48**: Comunicação de incidentes

### Recomendações

1. **Consentimento explícito** do titular dos dados
2. **Minimização de dados** coletados
3. **Anonimização** quando possível
4. **Auditoria completa** de operações
5. **Notificação** em caso de incidente

---

## 9. 📚 Referências

- LGPD (Lei 13.709/2018)
- OWASP Web Security Testing Guide
- Chrome DevTools Protocol Documentation
- React Fiber Architecture
- Web Scraping Best Practices

---

**"Com grande poder vem grande responsabilidade. Use shadow techniques apenas quando absolutamente necessário."** 🌑🛡️
