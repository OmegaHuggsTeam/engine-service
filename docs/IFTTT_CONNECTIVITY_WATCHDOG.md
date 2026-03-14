# IFTTT Connectivity Watchdog

## Visão Geral

O **IFTTTConnector** é um componente crítico do Sentinela Monitor que garante a entrega confiável de alertas externos via IFTTT Maker Webhooks. Implementa um sistema robusto de verificação de conectividade, retentativa exponencial e detecção de isolamento offline.

## Funcionalidades Principais

### 1. Health Check

Verifica a conectividade com os servidores IFTTT antes de enviar alertas críticos.

```python
connector = IFTTTConnector(webhook_key="your_key")

is_healthy, status, message = connector.health_check()

if is_healthy:
    print("✓ IFTTT connectivity OK")
else:
    print(f"✗ Connectivity issue: {message}")
```

**Verificações Realizadas**:
- ✅ Rede acessível
- ✅ Servidores IFTTT alcançáveis
- ✅ Webhook key válida (não 403/404)

**Status Possíveis**:
- `ONLINE`: Tudo funcionando
- `OFFLINE`: Sem conectividade (403/404/network error)
- `DEGRADED`: Conectividade parcial
- `UNKNOWN`: Status indeterminado

### 2. Offline Isolation Detection

Detecta quando o sistema está isolado da internet e reporta ao TelemetryHub.

**Condições de Isolamento**:
- HTTP 403: Webhook key inválida
- HTTP 404: Endpoint não encontrado
- Network Error: Sem internet/DNS

```python
# Quando isolamento é detectado:
# 1. Status muda para OFFLINE
# 2. Evento OFFLINE_ISOLATION é enviado ao TelemetryHub
# 3. Contador de eventos offline é incrementado

connector.offline_events  # Número de eventos de isolamento
```

### 3. Exponential Retry Logic

Retenta automaticamente alertas falhados com delays exponenciais.

**Delays Padrão**:
- 1ª tentativa: Imediata
- 2ª tentativa: +30 segundos
- 3ª tentativa: +1 minuto
- 4ª tentativa: +5 minutos

```python
# Configuração customizada
retry_config = RetryConfig(
    delays_seconds=[30, 60, 300],  # 30s, 1min, 5min
    max_attempts=3
)

connector = IFTTTConnector(
    webhook_key="your_key",
    retry_config=retry_config
)
```

**Workflow de Retry**:
```
Alert Sent → Failure → Schedule Retry (30s)
                ↓
         Wait 30s → Retry → Failure → Schedule Retry (1min)
                                ↓
                         Wait 1min → Retry → Failure → Schedule Retry (5min)
                                                  ↓
                                           Wait 5min → Retry → Success/Failure
                                                                      ↓
                                                               Log to Obsidian
```

### 4. Critical Alerts with Health Check

Alertas críticos executam health check antes do envio.

```python
success, message = connector.send_alert(
    event_name="telegram_critical",
    value1="🚨 CRITICAL: System failure",
    value2="Component: Database",
    value3="Action: Immediate attention required",
    critical=True  # Triggers health check
)
```

**Comportamento**:
1. Health check é executado
2. Se falhar, alerta é agendado para retry
3. Se passar, alerta é enviado imediatamente

### 5. Obsidian Logging

Falhas definitivas são registradas no Obsidian para auditoria.

```python
class ObsidianLogger:
    def log_failure(self, log_entry: str):
        # Salva em arquivo Markdown
        with open("failures.md", "a") as f:
            f.write(log_entry)

connector = IFTTTConnector(
    webhook_key="your_key",
    obsidian_logger=ObsidianLogger()
)
```

**Formato do Log**:
```markdown
# Alert Failure: alert_123

**Event**: telegram_alert
**Created**: 2024-01-15T10:30:45
**Status**: failed
**Attempts**: 3

## Message

- Value1: Quality score below threshold
- Value2: Agent: agent_123
- Value3: Score: 3.5

## Attempt History

### Attempt 1
- **Time**: 2024-01-15T10:30:45
- **Status**: retrying
- **Error**: Network error: Network unreachable

### Attempt 2
- **Time**: 2024-01-15T10:31:15
- **Status**: retrying
- **Error**: Network error: Network unreachable

### Attempt 3
- **Time**: 2024-01-15T10:32:15
- **Status**: failed
- **Error**: Network error: Network unreachable
```

## Uso Completo

### Configuração Básica

```python
from src.sentinela.ifttt_connector import IFTTTConnector, RetryConfig

# Configurar retry
retry_config = RetryConfig(
    delays_seconds=[30, 60, 300],
    max_attempts=3
)

# Inicializar connector
connector = IFTTTConnector(
    webhook_key=os.getenv("IFTTT_WEBHOOK_KEY"),
    retry_config=retry_config,
    telemetry_hub=telemetry_hub,
    obsidian_logger=obsidian_logger
)
```

### Enviar Alerta Simples

```python
success, message = connector.send_alert(
    event_name="telegram_alert",
    value1="🔔 Quality score alert",
    value2="Agent: agent_123",
    value3="Score: 3.5"
)

if success:
    print("✓ Alert sent successfully")
else:
    print(f"⏱ Alert scheduled for retry: {message}")
```

### Enviar Alerta Crítico

```python
success, message = connector.send_alert(
    event_name="telegram_critical",
    value1="🚨 CRITICAL: System offline",
    critical=True  # Health check first
)
```

### Processar Retries

```python
# Em loop de monitoramento
while True:
    # Processar retries pendentes
    retries_processed = connector.process_retries()

    if retries_processed > 0:
        print(f"Processed {retries_processed} retry(ies)")

    # Aguardar próximo ciclo
    time.sleep(10)
```

### Monitorar Estatísticas

```python
stats = connector.get_statistics()

print(f"Connectivity: {stats['connectivity_status']}")
print(f"Alerts sent: {stats['total_alerts_sent']}")
print(f"Alerts failed: {stats['total_alerts_failed']}")
print(f"Retries: {stats['total_retries']}")
print(f"Offline events: {stats['offline_events']}")
print(f"Pending: {stats['pending_alerts']}")
```

### Ver Alertas Pendentes

```python
pending = connector.get_pending_alerts()

for alert in pending:
    print(f"Alert: {alert['alert_id']}")
    print(f"  Status: {alert['status']}")
    print(f"  Attempts: {alert['attempts']}")
    print(f"  Next retry: {alert['next_retry_at']}")
```

## Integração com TelemetryHub

O connector reporta eventos ao TelemetryHub automaticamente:

```python
# Eventos reportados:
# - OFFLINE_ISOLATION: Quando conectividade falha
# - Alert attempts: Cada tentativa de envio
# - Health checks: Resultados de verificações

# Exemplo de evento OFFLINE_ISOLATION:
{
    "event_type": "LOG",
    "source": "sentinela_ifttt",
    "message": "OFFLINE_ISOLATION: HTTP 403",
    "data": {
        "reason": "HTTP 403",
        "details": "Alert 'alert_123' failed: HTTP 403: Forbidden",
        "connectivity_status": "offline",
        "offline_events_count": 1,
        "timestamp": "2024-01-15T10:30:45"
    }
}
```

## Configuração IFTTT

### 1. Obter Webhook Key

1. Acesse https://ifttt.com/maker_webhooks
2. Clique em "Documentation"
3. Copie sua webhook key (após `/use/`)

### 2. Criar Applet

1. Acesse https://ifttt.com/create
2. **IF**: Webhooks → Receive a web request
   - Event name: `telegram_alert`
3. **THEN**: Telegram → Send message
   - Message: `{{Value1}}\n{{Value2}}\n{{Value3}}`

### 3. Configurar no Sentinela

```bash
# .env
IFTTT_WEBHOOK_KEY=your_webhook_key_here
```

```python
webhook_key = os.getenv("IFTTT_WEBHOOK_KEY")
connector = IFTTTConnector(webhook_key=webhook_key)
```

## Troubleshooting

### Erro 403: Forbidden

**Causa**: Webhook key inválida

**Solução**:
1. Verificar se `IFTTT_WEBHOOK_KEY` está correta
2. Regenerar key no IFTTT se necessário
3. Atualizar `.env` com nova key

### Erro 404: Not Found

**Causa**: Event name não existe no IFTTT

**Solução**:
1. Verificar se applet foi criado no IFTTT
2. Confirmar event name está correto
3. Criar applet se necessário

### Network Error

**Causa**: Sem internet ou DNS falhou

**Solução**:
1. Verificar conectividade de rede
2. Testar DNS: `ping maker.ifttt.com`
3. Verificar firewall/proxy

### Alertas Não Chegam

**Causa**: Applet desativado ou Telegram bloqueado

**Solução**:
1. Verificar applet está ativo no IFTTT
2. Verificar bot do Telegram está funcionando
3. Testar manualmente via IFTTT web interface

### Muitos Retries

**Causa**: Conectividade intermitente

**Solução**:
1. Aumentar delays de retry
2. Reduzir max_attempts
3. Implementar circuit breaker

## Métricas e Monitoramento

### Métricas Importantes

```python
stats = connector.get_statistics()

# Taxa de sucesso
success_rate = (
    stats['total_alerts_sent'] /
    (stats['total_alerts_sent'] + stats['total_alerts_failed']) * 100
)

# Taxa de retry
retry_rate = (
    stats['total_retries'] /
    stats['total_alerts_sent']
)

# Frequência de offline
offline_frequency = stats['offline_events']
```

### Alertas de Monitoramento

Configure alertas para:
- ✅ Taxa de sucesso < 95%
- ✅ Offline events > 5 em 1 hora
- ✅ Pending alerts > 10
- ✅ Retry rate > 2.0

### Dashboard Sugerido

```
┌─────────────────────────────────────────┐
│ IFTTT Connector Status                  │
├─────────────────────────────────────────┤
│ Connectivity: ONLINE                    │
│ Last Health Check: 2 minutes ago        │
│ Last Successful Send: 30 seconds ago    │
├─────────────────────────────────────────┤
│ Alerts Sent: 1,234                      │
│ Alerts Failed: 12                       │
│ Success Rate: 99.0%                     │
├─────────────────────────────────────────┤
│ Total Retries: 45                       │
│ Retry Rate: 0.036                       │
│ Pending Alerts: 2                       │
├─────────────────────────────────────────┤
│ Offline Events: 3                       │
│ Last Offline: 1 hour ago                │
└─────────────────────────────────────────┘
```

## Testes

### Executar Testes Unitários

```bash
pytest tests/sentinela/test_ifttt_connector.py -v
```

### Executar Demo

```bash
# Configurar webhook key
export IFTTT_WEBHOOK_KEY=your_key

# Executar demo
python examples/sentinela_ifttt_demo.py
```

### Testar Manualmente

```bash
# Health check
curl -X POST \
  "https://maker.ifttt.com/trigger/health_check/with/key/YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{}'

# Enviar alerta
curl -X POST \
  "https://maker.ifttt.com/trigger/telegram_alert/with/key/YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"value1":"Test","value2":"Message","value3":"123"}'
```

## Boas Práticas

### 1. Sempre Use Health Check para Alertas Críticos

```python
# ✓ BOM
connector.send_alert(
    event_name="critical_alert",
    value1="System failure",
    critical=True
)

# ✗ RUIM
connector.send_alert(
    event_name="critical_alert",
    value1="System failure"
)
```

### 2. Configure Retry Apropriado

```python
# Para alertas urgentes (delays curtos)
urgent_config = RetryConfig(
    delays_seconds=[10, 30, 60],
    max_attempts=3
)

# Para alertas não-urgentes (delays longos)
normal_config = RetryConfig(
    delays_seconds=[60, 300, 900],  # 1min, 5min, 15min
    max_attempts=3
)
```

### 3. Monitore Offline Events

```python
if connector.offline_events > 5:
    # Muitos eventos offline - investigar
    logger.error("High offline event count: %d", connector.offline_events)
    # Notificar administrador
```

### 4. Processe Retries Regularmente

```python
# Em loop de monitoramento
def monitoring_loop():
    while True:
        # Processar retries a cada 10 segundos
        connector.process_retries()
        time.sleep(10)
```

### 5. Use IDs Únicos para Alertas

```python
# ✓ BOM
alert_id = f"alert_{agent_id}_{int(time.time())}"
connector.send_alert(
    event_name="telegram_alert",
    value1="Message",
    alert_id=alert_id
)

# ✗ RUIM (ID pode duplicar)
connector.send_alert(
    event_name="telegram_alert",
    value1="Message",
    alert_id="alert_1"
)
```

## Referências

- **IFTTT Maker Webhooks**: https://ifttt.com/maker_webhooks
- **IFTTT Documentation**: https://help.ifttt.com/hc/en-us/articles/115010230347
- **Telegram Bot API**: https://core.telegram.org/bots/api
- **Exponential Backoff**: https://en.wikipedia.org/wiki/Exponential_backoff

## Changelog

### v1.0.0 (2024-01-15)
- ✨ Implementação inicial do IFTTTConnector
- ✨ Health check com detecção de 403/404
- ✨ Retry exponencial (30s, 1min, 5min)
- ✨ Detecção de OFFLINE_ISOLATION
- ✨ Integração com TelemetryHub
- ✨ Logging para Obsidian
- ✨ Estatísticas e monitoramento
- 📝 Documentação completa
- ✅ 23 testes unitários (100% passing)
