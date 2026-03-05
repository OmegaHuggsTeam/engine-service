# Context Snapshot – Próximo Ciclo de Desenvolvimento

**Data:** 2026-03-01  
**Projeto:** mcp-engine-service (Lab Intelligence)  
**Spec:** `.kiro/specs/selenium-robust-initialization/`

---

## Estado da Infra

| Item | Valor |
|------|-------|
| **OS** | Windows 11 |
| **Python** | 3.14 (pythoncore-3.14-64) |
| **Selenium** | 4.x + webdriver-manager |
| **Chrome** | undetected-chromedriver (evita "navegador não seguro") |
| **Perfil** | Real: `C:\Users\huggs\AppData\Local\Google\Chrome\User Data` |
| **.env** | EXTRACTOR_KILL_CHROME_BEFORE=true, EXTRACTOR_UNDETECTED=true |
| **Build** | Visual Studio C++ (para pyroaring/pyiceberg se necessário) |

---

## O "Muro" Atual

**Problema:** O driver falha ao ser criado com o perfil real. O script nem chega ao loop de Hard Retry nem à navegação.

**Erro típico:**
```
ConnectionResetError: [WinError 10054] Foi forçado o cancelamento de uma conexão existente pelo host remoto
```
- **Onde:** `uc.Chrome(options=opts)` em `_create_undetected_driver` (linha ~129)
- **Quando:** Durante `start_session` / `execute(Command.NEW_SESSION)`
- **Cenário:** Chrome pode abrir brevemente e fechar, ou a conexão com o ChromeDriver é interrompida antes de completar

**Outros erros já vistos:**
- `SessionNotCreatedException: Chrome instance exited`
- `DevToolsActivePort file doesn't exist`
- `session not created`

**Consequência:** O fluxo não chega a `_robust_navigate` nem ao Hard Retry; a falha ocorre em `_get_driver()`.

---

## Solução em Andamento

### Já implementado (design.md)

1. **`_remove_profile_locks()`** – Remove SingletonLock, Parent.lock, lockfile, SingletonSocket  
2. **`_verify_profile_ready()`** – Verifica diretório e locks antes de criar o driver  
3. **`_focus_main_window()`** – `window.focus()` + 2s para mitigar aba fantasma  
4. **`_robust_navigate()`** – driver.get → location.replace → Ctrl+L + send_keys  
5. **Hard Retry (3 tentativas)** – Em `test_rotation_flow.py`  
6. **Verificação de perfil** – Antes do loop, em `test_rotation_flow.py`  
7. **`_kill_chrome_for_profile()`** – taskkill + remoção de locks (test script)

### Pendente / não validado

- O driver não é criado com sucesso com o perfil real, então o Hard Retry e `_robust_navigate` não são exercitados.
- `_cleanup_processes()` centralizado em `_get_driver()` (hoje o cleanup está no test script).
- `_validate_and_cleanup_windows()` (fechar janelas extras).

---

## Próximo Passo Imediato

**Objetivo:** Fazer o driver ser criado com sucesso para poder testar o restante do fluxo.

### Primeira linha de código a testar no retorno

**Opção A – Desativar undetected e usar Selenium padrão**

No `.env`:
```env
EXTRACTOR_UNDETECTED=false
```

Depois rodar:
```powershell
python scripts/test_rotation_flow.py
```

**Opção B – Garantir que o Chrome está morto antes de criar o driver**

Em `test_rotation_flow.py`, antes do loop, chamar `_kill_chrome_for_profile()` mesmo quando o Chrome não parece estar rodando (para limpar processos órfãos):

```python
# Sempre executar cleanup antes do loop (linha ~125)
_log("Limpando processos e locks antes de iniciar...")
_kill_chrome_for_profile()
time.sleep(8)
```

**Opção C – Testar com perfil ChromeSelenium (sem perfil real)**

Comentar ou remover `EXTRACTOR_CHROME_USER_DATA` no `.env` para usar o perfil ChromeSelenium e validar se o fluxo completo (incluindo Hard Retry e `_robust_navigate`) funciona. Depois, voltar ao perfil real.

---

## Arquivos Principais

| Arquivo | Função |
|---------|--------|
| `src/extractors/web_extractor.py` | `_get_driver`, `_robust_navigate`, `_remove_profile_locks`, `_verify_profile_ready`, `_focus_main_window` |
| `scripts/test_rotation_flow.py` | Loop Hard Retry, verificação de perfil, `_kill_chrome_for_profile` |
| `.kiro/specs/selenium-robust-initialization/design.md` | Spec de inicialização robusta |
| `.kiro/specs/selenium-robust-initialization/tasks.md` | Tarefas de implementação |

---

## Comando para Retomar

```powershell
cd C:\labs\inteligence\mcp-engine-service
python scripts/test_rotation_flow.py
```
