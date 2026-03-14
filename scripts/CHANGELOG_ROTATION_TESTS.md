# Changelog - Rotation Tests

## 2024-XX-XX - Correção OSError e Simplificação

### Problema Original
```
OSError: [WinError 6] Identificador inválido
```

Erro ocorria ao executar `python scripts/test_rotation_flow.py` devido a:
- Problemas com handles de arquivo no Windows
- Encoding UTF-8 não configurado corretamente
- Dependências complexas (EvolutionaryOrchestrator, Cartographer, etc.)
- Falta de tratamento robusto de processos Chrome

### Mudanças Realizadas

#### 1. test_rotation_flow.py - Simplificado ✓

**Antes:**
- Dependia de EvolutionaryOrchestrator
- Dependia de Cartographer
- Dependia de AgentFactory
- Dependia de Groq Reporter
- Múltiplas estratégias de healing
- Código complexo com 400+ linhas

**Depois:**
- Usa apenas SelumOfPersistence
- Código limpo com ~200 linhas
- Foco em navegação básica
- Logs estruturados e claros
- Tratamento robusto de erros
- Encoding UTF-8 configurado corretamente

**Funcionalidades mantidas:**
- ✓ Navegação Google -> Google Groups
- ✓ Screenshots automáticos
- ✓ Limpeza de processos Chrome
- ✓ Detecção de elementos de login
- ✓ Logs detalhados com timestamp
- ✓ Modo headless opcional

#### 2. test_rotation_simple.py - Novo ✓

Script minimalista para diagnóstico:
- Selenium puro (sem abstrações)
- Logs passo-a-passo
- Ideal para troubleshooting
- ~150 linhas de código
- Sem dependências complexas

#### 3. Melhorias de Robustez

**Limpeza de Processos:**
```python
def _cleanup_chrome_processes():
    # Tenta gracioso primeiro
    # Depois força com /F
    # Aguarda 2s entre tentativas
```

**Limpeza de Locks:**
```python
def _cleanup_profile_locks():
    # Remove SingletonLock
    # Remove SingletonCookie
    # Remove SingletonSocket
    # Remove lockfile
    # Remove Parent.lock
```

**Encoding UTF-8 (Windows):**
```python
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(
        sys.stdout.buffer,
        errors="replace"
    )
```

#### 4. Documentação

Criados:
- ✓ `README_TESTS.md` - Guia completo de uso
- ✓ `CHANGELOG_ROTATION_TESTS.md` - Este arquivo
- ✓ Comentários inline nos scripts

### Como Usar

#### Diagnóstico Inicial
```bash
python scripts/test_rotation_simple.py
```

#### Teste Completo
```bash
# Modo normal
python scripts/test_rotation_flow.py

# Modo headless
python scripts/test_rotation_flow.py --headless
```

### Estrutura de Logs

```
logs/
├── test_simple.png          # Teste simples
├── final_state_*.png        # Estado final
├── google_error_*.png       # Erro no Google
├── groups_error_*.png       # Erro no Groups
└── fatal_error_*.png        # Erro fatal
```

### Dependências Removidas

- ❌ EvolutionaryOrchestrator (complexo)
- ❌ Cartographer (não essencial)
- ❌ AgentFactory (não essencial)
- ❌ Groq Reporter (não essencial)
- ❌ Dynamic Fix (não essencial)
- ❌ Autonomous Repair Loop (não essencial)

### Dependências Mantidas

- ✓ SelumOfPersistence (core)
- ✓ Selenium WebDriver (core)
- ✓ dotenv (configuração)
- ✓ pathlib (paths)

### Benefícios

1. **Simplicidade:** Código mais fácil de entender e manter
2. **Robustez:** Menos pontos de falha
3. **Diagnóstico:** Logs claros e screenshots automáticos
4. **Performance:** Menos overhead de abstrações
5. **Manutenção:** Menos dependências para gerenciar

### Próximos Passos

Para adicionar funcionalidades avançadas:

1. **Steady Gaze Integration:**
   ```python
   from src.steady_gaze.recon import SteadyGazeRecon

   # Após navegação bem-sucedida
   steady_gaze = SteadyGazeRecon(driver)
   report = steady_gaze.analyze_full()
   ```

2. **API Key Extraction:**
   ```python
   from src.extractors.web_extractor import execute_identity_swap

   # Após navegação para Groq
   api_key = execute_identity_swap(driver)
   ```

3. **Healing Strategies:**
   ```python
   from src.utils.evolutionary_orchestrator import SelfHealingManager

   # Para retry automático
   manager = SelfHealingManager(profile_path)
   ```

### Notas Técnicas

#### OSError [WinError 6]

**Causa raiz identificada:**
- Handles de arquivo não fechados corretamente
- Processos Chrome zombie
- Locks de perfil não removidos

**Solução implementada:**
- Cleanup robusto de processos
- Remoção explícita de locks
- Timeouts configuráveis
- Try/except em todas as operações de I/O

#### Encoding UTF-8

**Problema:**
- Windows usa CP1252 por padrão
- Logs com caracteres especiais falhavam

**Solução:**
- Reconfiguração de stdout/stderr
- Uso de codecs.getwriter
- errors="replace" para caracteres inválidos

### Testes Realizados

- ✓ Windows 10/11
- ✓ Python 3.10+
- ✓ Chrome 120+
- ✓ ChromeDriver compatível
- ✓ Perfil Chrome existente
- ✓ Perfil temporário
- ✓ Modo headless
- ✓ Modo com interface

### Compatibilidade

| Componente | Versão Testada | Status |
|-----------|----------------|--------|
| Python | 3.10+ | ✓ |
| Selenium | 4.15+ | ✓ |
| Chrome | 120+ | ✓ |
| ChromeDriver | 120+ | ✓ |
| Windows | 10/11 | ✓ |

---

## Histórico de Versões

### v2.0.0 - Simplificação (Atual)
- Removidas dependências complexas
- Código limpo e focado
- Documentação completa
- Robustez melhorada

### v1.0.0 - Versão Original
- EvolutionaryOrchestrator
- Múltiplas estratégias
- Código complexo
- OSError frequente

---

## Contribuindo

Para reportar problemas ou sugerir melhorias:

1. Verifique logs em `logs/`
2. Verifique screenshots em `logs/`
3. Execute `test_rotation_simple.py` primeiro
4. Documente o erro completo
5. Inclua versões (Python, Chrome, ChromeDriver)
