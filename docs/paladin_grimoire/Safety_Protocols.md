# Safety Protocols - Regras de Segurança Críticas

Este documento define as regras de segurança que DEVEM ser seguidas por todas as abstrações e skills geradas pelo sistema.

**VIOLAÇÃO DESTAS REGRAS RESULTA EM REJEIÇÃO AUTOMÁTICA DO CÓDIGO.**

---

## Regra 1: Nunca Injetar Scripts em Campos Sensíveis

**Descrição**: Campos de senha, cartão de crédito, CPF, e-mail e outros dados pessoais NUNCA devem receber valores via `execute_script`.

**Razão**: 
- Segurança: Scripts podem ser interceptados ou logados
- Detecção de automação: Sites detectam injeção de JavaScript
- Compliance: Violação de políticas de segurança

**Correto**:
```python
# Usar send_keys nativo do Selenium através de abstrações
password_field = selum.scout([{"id": "password"}])
password_field.send_keys("senha_segura")
```

**Incorreto**:
```python
# NUNCA FAÇA ISSO
driver.execute_script("document.querySelector('#password').value = 'senha'")
```

**Campos Sensíveis**:
- Senha (`type="password"`)
- Cartão de crédito
- CVV
- CPF/CNPJ
- E-mail (em contextos de autenticação)
- Dados bancários

---

## Regra 2: Sempre Validar com compile()

**Descrição**: Todo código gerado DEVE passar por `compile()` antes de `exec()`.

**Razão**: Prevenir erros de sintaxe em runtime que podem quebrar o sistema.

**Implementação**:
```python
from src.divine_inspiration import AlchemistsFilter

# Validar sintaxe antes de executar
is_valid, error = AlchemistsFilter.validate_syntax(generated_code)

if not is_valid:
    logger.error(f"Código inválido: {error}")
    return False

# Apenas executar se validação passar
exec(generated_code, namespace)
```

**Quando Aplicar**:
- Antes de registrar skill no skill_registry
- Antes de salvar skill no grimório
- Antes de executar código gerado por LLM

---

## Regra 3: Usar Apenas Abstrações do SelumOfPersistence

**Descrição**: Código gerado NUNCA deve usar Selenium bruto. Apenas abstrações do SelumOfPersistence são permitidas.

**Razão**:
- Resiliência: Abstrações têm fallbacks automáticos
- Manutenibilidade: Código centralizado e testado
- Segurança: Abstrações seguem protocolos de segurança
- Logging: Abstrações geram logs narrativos

**Abstrações Permitidas**:
- `selum.strike()` - Para clicar
- `selum.scout()` - Para localizar com múltiplas estratégias
- `selum.vigilance()` - Para aguardar elementos
- `selum.steady_gaze()` - Para scroll e visibilidade
- `selum.cleansing_aura()` - Para remover overlays
- `selum.invoke_wisdom()` - Para aprendizado
- `selum.divine_inspiration()` - Para auto-evolução
- `selum.execute_skill()` - Para executar skills customizadas

**Código Selenium Bruto PROIBIDO**:
- ❌ `driver.find_element()`
- ❌ `driver.find_elements()`
- ❌ `driver.execute_script()`
- ❌ `WebDriverWait(driver, ...)`
- ❌ `ActionChains(driver)`
- ❌ `driver.get()`
- ❌ `driver.refresh()`

**Exceção**: Código dentro da própria classe `SelumOfPersistence` pode usar `self.driver` diretamente, pois está criando as abstrações.

---

## Regra 4: Sempre Retornar bool em Skills

**Descrição**: Toda skill customizada DEVE retornar `bool` indicando sucesso ou falha.

**Razão**: Permite que o sistema saiba se a skill resolveu o problema e decida próximos passos.

**Assinatura Obrigatória**:
```python
def skill_<nome>(selum: SelumOfPersistence) -> bool:
    """
    Descrição da skill.
    
    Args:
        selum: Instância do SelumOfPersistence
        
    Returns:
        True se objetivo foi atingido, False caso contrário
    """
    try:
        # Implementação usando apenas abstrações do selum
        selum.strike(".target")
        return True
    except Exception as e:
        return False
```

**Validação**:
- Código DEVE conter `return True` ou `return False`
- Código DEVE ter assinatura `def skill_<nome>(selum: SelumOfPersistence) -> bool:`
- Código DEVE ter docstring explicando o objetivo

---

## Regra 5: Capturar Exceções Adequadamente

**Descrição**: Skills DEVEM capturar exceções e retornar `False` ao invés de deixar exceção propagar.

**Razão**: Prevenir que skills quebrem o fluxo principal do Selum.

**Correto**:
```python
def skill_handle_popup(selum: SelumOfPersistence) -> bool:
    """Remove popup de cookies."""
    try:
        selum.strike(".cookie-accept")
        return True
    except Exception as e:
        # Logar erro mas não propagar
        print(f"Skill falhou: {e}")
        return False
```

**Incorreto**:
```python
def skill_handle_popup(selum: SelumOfPersistence) -> bool:
    """Remove popup de cookies."""
    # NUNCA deixe exceção propagar sem capturar
    selum.strike(".cookie-accept")
    return True
```

---

## Regra 6: Não Usar Imports Perigosos

**Descrição**: Skills NUNCA devem importar módulos que permitem acesso ao sistema operacional ou execução arbitrária.

**Imports PROIBIDOS**:
- ❌ `import os`
- ❌ `import sys`
- ❌ `import subprocess`
- ❌ `import eval`
- ❌ `import exec`
- ❌ `import __import__`
- ❌ `import pickle`
- ❌ `import marshal`
- ❌ `import socket`
- ❌ `import requests` (sem validação)

**Imports PERMITIDOS**:
- ✅ `from selenium.webdriver.common.by import By`
- ✅ `import time`
- ✅ `import re`
- ✅ `from typing import ...`

**Razão**: Prevenir execução de código malicioso ou acidental que possa comprometer o sistema.

---

## Regra 7: Limitar Tamanho de HTML Context

**Descrição**: Ao extrair HTML para contexto de erro, SEMPRE limitar a 5000 caracteres.

**Razão**: Prevenir consumo excessivo de memória e tokens do LLM.

**Implementação**:
```python
def _extract_html_context(self, selector: str) -> str:
    """Extrai HTML da área problemática."""
    try:
        body_html = self.driver.find_element("tag name", "body").get_attribute('outerHTML')
        
        # SEMPRE limitar a 5000 chars
        if len(body_html) > 5000:
            return body_html[:5000]
        
        return body_html
    except Exception:
        return ""
```

---

## Regra 8: Validar Retorno de Skills

**Descrição**: Ao executar skill, SEMPRE validar que retorno é `bool`.

**Razão**: Prevenir comportamento inesperado se skill retornar tipo incorreto.

**Implementação**:
```python
def execute_skill(self, skill_name: str) -> bool:
    """Executa skill e valida retorno."""
    if skill_name not in self.skill_registry:
        return False
    
    try:
        result = self.skill_registry[skill_name](self)
        
        # SEMPRE validar tipo de retorno
        if not isinstance(result, bool):
            self.logger.warning(f"Skill '{skill_name}' retornou tipo inválido: {type(result)}")
            return False
        
        return result
    except Exception as e:
        self.logger.error(f"Skill '{skill_name}' falhou: {e}")
        return False
```

---

## Regra 9: Logar Todas as Operações Críticas

**Descrição**: Operações críticas DEVEM gerar logs narrativos usando CombatLogger.

**Operações Críticas**:
- Geração de nova skill
- Validação de código
- Execução de skill
- Persistência no grimório
- Detecção de erro estrutural
- Invocação de Divine Inspiration

**Formato de Log**:
```python
# Usar CombatLogger para logs narrativos
from src.utils.combat_logger import CombatLogger

# Log de sucesso
CombatLogger.result(True, "Skill 'skill_handle_popup' executada com sucesso!")

# Log de erro
CombatLogger.error("Falha ao validar código: SyntaxError na linha 5")

# Log de sabedoria
CombatLogger.wisdom("Consultando grimório para abstrações relevantes...")
```

---

## Regra 10: Atomicidade em Operações de Arquivo

**Descrição**: Ao atualizar arquivos do grimório, GARANTIR atomicidade para prevenir corrupção.

**Razão**: Múltiplas skills podem ser criadas simultaneamente. Arquivo corrompido quebra todo o sistema.

**Implementação**:
```python
import fcntl  # Para file locking no Linux
import msvcrt  # Para file locking no Windows

def _update_abstractions_md(self, skill_info: SkillInfo) -> bool:
    """Atualiza Abstractions.md com atomicidade."""
    file_path = "docs/paladin_grimoire/Abstractions.md"
    
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            # Adquirir lock exclusivo
            if os.name == 'nt':  # Windows
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            else:  # Linux/Mac
                fcntl.flock(f, fcntl.LOCK_EX)
            
            # Escrever conteúdo
            f.write(f"\n## {skill_info.name}\n")
            f.write(f"{skill_info.documentation}\n")
            
            # Lock é liberado automaticamente ao fechar arquivo
        
        return True
    except Exception as e:
        self.logger.error(f"Falha ao atualizar Abstractions.md: {e}")
        return False
```

---

## Checklist de Validação

Antes de aprovar qualquer código gerado, verificar:

- [ ] Código passa em `compile()`
- [ ] Código usa apenas abstrações do SelumOfPersistence
- [ ] Código não usa imports perigosos
- [ ] Código tem assinatura correta: `def skill_<nome>(selum: SelumOfPersistence) -> bool:`
- [ ] Código retorna `bool` explicitamente
- [ ] Código captura exceções adequadamente
- [ ] Código não injeta scripts em campos sensíveis
- [ ] Código tem docstring explicativa
- [ ] Código gera logs narrativos
- [ ] Código segue princípios de atomicidade em I/O

**Se QUALQUER item falhar, código DEVE ser rejeitado.**

---

## Consequências de Violação

**Violação de Regra Crítica (1, 2, 3, 6)**:
- Rejeição imediata do código
- Não permitir re-tentativa
- Logar violação com detalhes
- Emitir SkillRequest para SkillConstructor

**Violação de Regra Importante (4, 5, 7, 8, 9, 10)**:
- Rejeição do código
- Permitir até 3 re-tentativas com feedback
- Se falhar após 3 tentativas, emitir SkillRequest
- Logar todas as tentativas

---

## Atualização de Protocolos

Este documento pode ser atualizado quando:
- Nova vulnerabilidade de segurança é descoberta
- Nova abstração é adicionada ao SelumOfPersistence
- Novo padrão de código é estabelecido
- Feedback de produção indica necessidade de nova regra

**Processo de Atualização**:
1. Propor mudança com justificativa
2. Revisar impacto em código existente
3. Atualizar documento
4. Re-indexar RAG
5. Notificar todos os sistemas dependentes
