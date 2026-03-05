# Scripts de Teste - Rotation Flow

Este diretório contém scripts de teste para o fluxo de rotação Google Groups.

## Scripts Disponíveis

### 1. test_rotation_simple.py (RECOMENDADO PARA DIAGNÓSTICO)

Script minimalista para diagnóstico de problemas básicos.

**Uso:**
```bash
python scripts/test_rotation_simple.py
```

**O que faz:**
- ✓ Limpa processos Chrome
- ✓ Inicializa ChromeDriver básico
- ✓ Navega para Google
- ✓ Navega para Google Groups
- ✓ Tira screenshot
- ✓ Mostra logs detalhados

**Quando usar:**
- Primeiro teste após instalação
- Diagnóstico de problemas de conexão
- Verificar se ChromeDriver está funcionando
- Testar perfil Chrome

---

### 2. test_rotation_flow.py (VERSÃO COMPLETA)

Script completo com SelumOfPersistence e recursos avançados.

**Uso:**
```bash
# Modo normal (com interface)
python scripts/test_rotation_flow.py

# Modo headless (invisível)
python scripts/test_rotation_flow.py --headless
```

**O que faz:**
- ✓ Usa SelumOfPersistence (camada resiliente)
- ✓ Navegação robusta com retry
- ✓ Logs estruturados
- ✓ Screenshots automáticos
- ✓ Limpeza automática de processos
- ✓ Detecção de elementos de login

**Quando usar:**
- Após test_rotation_simple.py funcionar
- Testes de integração
- Desenvolvimento de features
- Testes automatizados

---

## Solução de Problemas

### OSError: [WinError 6] Identificador inválido

**Causa:** Problemas com handles de arquivo/processo no Windows.

**Solução:**
1. Feche todos os Chrome manualmente
2. Execute: `taskkill /F /IM chrome.exe`
3. Execute: `taskkill /F /IM chromedriver.exe`
4. Aguarde 5 segundos
5. Execute o teste novamente

### Session not created

**Causa:** Perfil Chrome em uso ou corrompido.

**Solução:**
1. Verifique `EXTRACTOR_CHROME_USER_DATA` no `.env`
2. Feche todos os Chrome
3. Delete arquivos de lock:
   - `SingletonLock`
   - `SingletonCookie`
   - `SingletonSocket`
4. Execute o teste novamente

### ChromeDriver não encontrado

**Causa:** ChromeDriver não está no PATH.

**Solução:**
1. Baixe ChromeDriver: https://chromedriver.chromium.org/
2. Coloque no PATH ou na pasta do projeto
3. Ou instale via: `pip install webdriver-manager`

---

## Configuração do Perfil Chrome

Para usar um perfil Chrome existente:

1. Abra Chrome e vá em `chrome://version`
2. Copie o caminho do "Perfil"
3. Adicione no `.env`:
   ```
   EXTRACTOR_CHROME_USER_DATA=C:\Users\SeuUsuario\AppData\Local\Google\Chrome\User Data
   ```

**Importante:** Feche o Chrome antes de executar os testes!

---

## Logs e Screenshots

Todos os logs e screenshots são salvos em:
```
logs/
├── test_simple.png          # Screenshot do teste simples
├── test_error.png           # Screenshot de erro
├── final_state_*.png        # Estado final do teste completo
└── *_error_*.png            # Screenshots de erros específicos
```

---

## Ordem Recomendada de Execução

1. **Primeiro teste:**
   ```bash
   python scripts/test_rotation_simple.py
   ```
   Se funcionar, prossiga para o próximo.

2. **Teste completo:**
   ```bash
   python scripts/test_rotation_flow.py
   ```

3. **Teste headless:**
   ```bash
   python scripts/test_rotation_flow.py --headless
   ```

---

## Suporte

Se os testes continuarem falhando:

1. Verifique versão do Chrome: `chrome://version`
2. Verifique versão do ChromeDriver: `chromedriver --version`
3. Certifique-se que as versões são compatíveis
4. Verifique logs em `logs/`
5. Verifique screenshots em `logs/`

---

## Desenvolvimento

Para adicionar novos testes:

1. Use `test_rotation_simple.py` como base
2. Adicione funcionalidades incrementalmente
3. Mantenha logs detalhados
4. Sempre faça limpeza no `finally`
5. Capture screenshots em caso de erro
