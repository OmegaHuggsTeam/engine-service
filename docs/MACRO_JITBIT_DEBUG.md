# Depuração Elite: macro-jitbit-test

> **Alinhamento com CONTRIBUTING.md**: Este documento segue as convenções de `docs/` (CONTRIBUTING § Documentação), nomenclatura `kebab-case` para arquivos e estrutura Objetivo → Conteúdo → Exemplos → Referências.

---

## Objetivo

Documentar as **Abstrações de Controle** do macro Jitbit, o protocolo de sanitização e a integração com o Neural Link para garantir loop infinito com idempotência.

---

## Abstrações de Controle

### 1. Abstração de Estado Inicial (Home State)

A coordenada **(443, 422)** não é apenas um ponto; é o **Home State** do macro.

- O macro deve ser tratado como uma **transição de estados** que obrigatoriamente retorna a esse ponto.
- Garante **idempotência do loop**: toda rodada termina no mesmo estado em que começou.
- O script `tools/sanitize_macro_env.py` e o bloco `macro-jitbit-sanitization-block.mcr` restauram o cursor e o foco para o Home State.

### 2. Abstração de Latência (Safety Buffers)

Os delays são **Margens de Segurança de Rede**:

- Qualquer delay **abaixo de 100ms** em trocas de aba é risco de **race condition visual**.
- Delays críticos foram aumentados conforme tabela abaixo.
- O script `tools/mcr_patch.py` aplica automaticamente os Safety Buffers.

| Local | Antes | Depois | Motivo |
|-------|-------|--------|--------|
| Início | 597ms | 800ms | Estabilização de UI |
| Antes de (504, 4) | 927ms | 1200ms | Carregamento de aba |
| Tab → digitação | 3321ms | 4000ms | Formulário dinâmico |
| Após Ctrl+V | 234ms | 400ms | Cola em campo |
| Antes de clique em barra de abas | 2–10ms | 100ms | Troca de contexto |

### 3. Abstração de Limpeza (Garbage Collector)

O bloco `macro-jitbit-sanitization-block.mcr` é o **Garbage Collector**:

- Deve ser injetado em **todos os pontos de saída** (incluindo On Error → GoTo Sanitization).
- Evita acúmulo de **lixo visual** (abas órfãs, pop-ups residuais).
- Sequência: 5× Ctrl+W → Move para Home State → Clique para focar campo inicial.

### 4. Conexão de Telemetria (Neural Link de Diagnóstico)

O webhook **POST /api/v1/jitbit/error** é o Neural Link de Diagnóstico:

- Se o macro falhar, o SpecialistAgent correlaciona a **linha do erro no .mcr** com o **log de rede do Gateway**.
- Payload esperado: `{ "macro": "macro-jitbit-test", "error": "...", "step": "sanitization", "line": 12345 }`
- Permite diagnóstico automático e sugestão de correção (delays, coordenadas).

---

## Estrutura de Fluxo Sanitizado

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│  Execution  │ ──► │ Validation  │ ──► │  Sanitization   │ ──► │    Reset    │
│ Macro roda │     │ SpecialistAgent│     │ sanitize_macro_ │     │ Home State  │
│ nos pontos │     │ checa lead_id │     │ env.py + bloco  │     │ (443, 422)  │
│ críticos   │     │               │     │ MCR (Ctrl+W)    │     │ pronto loop │
└─────────────┘     └─────────────┘     └─────────────────┘     └─────────────┘
```

1. **Execution**: O macro roda nos pontos críticos identificados.
2. **Validation**: O SpecialistAgent checa se o `lead_id` foi gerado (ou critério de sucesso).
3. **Sanitization**: O script `sanitize_macro_env.py` limpa o Chrome; o bloco MCR fecha abas.
4. **Reset**: O sistema volta para o Home State pronto para o loop infinito.

---

## Ferramentas

### Gerar macro corrigido automaticamente

```bash
# Gera macro-jitbit-test-patched.mcr com delays e sanitização
python tools/mcr_patch.py

# Dry-run (apenas stats)
python tools/mcr_patch.py --dry-run

# Home State customizado
python tools/mcr_patch.py --home-x 500 --home-y 400
```

### Reset de ambiente (pré/pós execução)

```bash
python tools/sanitize_macro_env.py --close-tabs 5 --cursor 443 422 --focus "Chrome"
```

---

## Pontos de Falha Identificados

| Linha aprox. | Coordenada | Ação | Gap / Risco |
|--------------|------------|------|-------------|
| 265 | (443, 422) | **Home State** – primeiro clique | Referência |
| 2707 | (504, 4) | Barra de abas | Alto risco – pop-up |
| 3136 | (1472, 403) | Campo Google | Delay aumentado |
| 3280 | - | Tab → digitação | Safety buffer 4000ms |
| 43689 | (336, 26) | Último clique | Sem sanitização → corrigido com bloco |

---

## Integração com SpecialistAgent e n8n

### Webhook no Gateway

```
POST /api/v1/jitbit/error
Body: { "macro": "macro-jitbit-test", "error": "...", "step": "sanitization", "line": 12345 }
Ação: Cria Task no Neo4j, dispara SpecialistAgent.analyze_jitbit_macro_error
```

### Workflow n8n sugerido

1. **Trigger**: Manual ou Schedule
2. **Execute**: `python tools/sanitize_macro_env.py` (pré-run)
3. **Execute**: Macro Jitbit
4. **On Error**: HTTP Request → `POST /api/v1/jitbit/error`

---

## Referências

- [CONTRIBUTING.md](../CONTRIBUTING.md) – Convenções e estrutura
- [specialist-agent.md](specs/agents/specialist-agent.md) – SpecialistAgent
- [macro-jitbit-sanitization-block.mcr](../macro-jitbit-sanitization-block.mcr) – Bloco de sanitização
- [tools/mcr_patch.py](../tools/mcr_patch.py) – Gerador de macro corrigido
- [tools/sanitize_macro_env.py](../tools/sanitize_macro_env.py) – Reset de ambiente
