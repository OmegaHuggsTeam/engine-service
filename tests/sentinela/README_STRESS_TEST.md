# Sentinela Vision Stress Test

## Visão Geral

O stress test de longo prazo (`stress_test_vision.py`) valida a estabilidade do VisualDetector sob operação contínua, detectando memory leaks no processamento do OpenCV e implementando auto-recuperação de câmera.

## Funcionalidades

### 1. Monitoramento de Memória

O `MemoryMonitor` rastreia o uso de memória do processo durante o teste:

- **Baseline**: Registra memória inicial ao começar
- **Sampling**: Coleta amostras de memória a cada iteração
- **Leak Detection**: Detecta aumentos constantes de memória
- **Threshold**: Dispara `CatarataError` se aumento exceder limite (padrão: 50 MB)

```python
monitor = MemoryMonitor(leak_threshold_mb=50.0)
monitor.start()

# Durante o teste
current_memory = monitor.sample()
has_leak, increase, diagnosis = monitor.check_for_leak()

if has_leak:
    raise CatarataError(f"Memory leak: {increase:.2f} MB")
```

### 2. Auto-Recuperação de Câmera

O `CameraRecoveryManager` implementa recuperação automática após falhas consecutivas:

- **Failure Tracking**: Conta falhas consecutivas de captura
- **Recovery Trigger**: Ativa recuperação após 3 falhas seguidas
- **Cache Clearing**: Limpa caches do NumPy e Pillow
- **Garbage Collection**: Força coleta de lixo para liberar memória

```python
manager = CameraRecoveryManager(max_consecutive_failures=3)

# Após captura bem-sucedida
manager.record_success()

# Após falha
if manager.record_failure():
    # Trigger recovery
    manager.perform_recovery()
```

### 3. Teste de Estabilidade

O teste principal executa o VisualDetector em loop:

- **Duração**: 5 minutos (configurável)
- **Intervalo**: 2 segundos entre capturas (configurável)
- **Métricas**: Taxa de sucesso, uso de memória, recuperações
- **Relatório**: Estatísticas completas ao final

## Uso

### Execução Básica

```bash
# Teste padrão (5 minutos, intervalo de 2s)
python tests/sentinela/stress_test_vision.py

# Teste customizado (10 minutos, intervalo de 1s)
python tests/sentinela/stress_test_vision.py 600 1.0
```

### Usando o Demo

```bash
# Teste padrão
python examples/sentinela_stress_test_demo.py

# Teste com duração customizada
python examples/sentinela_stress_test_demo.py --duration 600

# Teste com intervalo customizado
python examples/sentinela_stress_test_demo.py --duration 300 --interval 1.0

# Teste com threshold de leak customizado
python examples/sentinela_stress_test_demo.py --leak-threshold 100.0
```

### Testes Unitários

```bash
# Executar testes dos componentes
pytest tests/sentinela/test_stress_test.py -v

# Executar teste de integração (curto)
pytest tests/sentinela/test_stress_test.py::TestStressTestIntegration -v
```

## Interpretação dos Resultados

### Sucesso

```
STRESS TEST COMPLETE
====================================================================
Duration: 300.0 seconds (5.0 minutes)
Iterations: 150
Successful captures: 150
Failed captures: 0
Success rate: 100.0%

Memory Statistics:
  Start: 45.23 MB
  End: 47.89 MB
  Min: 45.12 MB
  Max: 48.01 MB
  Avg: 46.55 MB
  Increase: 2.66 MB
  Samples: 150

Recovery Statistics:
  Total failures: 0
  Total recoveries: 0
  Consecutive failures: 0

Memory leak detected: NO
====================================================================
```

**Interpretação**: Sistema estável, sem memory leaks, sem falhas.

### Memory Leak Detectado

```
====================================================================
MEMORY LEAK DETECTED!
MEMORY LEAK DETECTED: Consistent increase of 75.45 MB (threshold: 50.00 MB)
====================================================================
```

**Causa Provável**:
- OpenCV não está liberando buffers de imagem
- PIL/Pillow mantendo cache excessivo
- NumPy arrays não sendo coletados pelo GC

**Ação**:
- Verificar se `gc.collect()` está sendo chamado
- Revisar uso de arrays NumPy (evitar referências circulares)
- Considerar reduzir frequência de captura

### Falhas de Captura com Recuperação

```
Recovery Statistics:
  Total failures: 9
  Total recoveries: 3
  Consecutive failures: 0
```

**Interpretação**: Sistema teve falhas mas se recuperou automaticamente.

**Causa Provável**:
- Problemas temporários com driver gráfico
- Permissões de screenshot intermitentes
- Recursos do sistema temporariamente indisponíveis

### CatarataError

```
✗ STRESS TEST FAILED: Catarata detected: Screen is black (mean brightness: 3.45 < 10.0)
```

**Causa Provável**:
- Tela realmente preta (screensaver, monitor desligado)
- Permissão de screenshot negada pelo OS
- Driver gráfico com problema

**Ação**:
- Verificar se monitor está ligado
- Verificar permissões de screenshot no OS
- Reiniciar driver gráfico

## Configuração

### Parâmetros do Teste

```python
run_stress_test(
    duration_seconds=300,           # Duração total (5 min)
    capture_interval_seconds=2.0,   # Intervalo entre capturas
    templates_dir="templates",      # Diretório de templates
    leak_threshold_mb=50.0          # Threshold de memory leak
)
```

### Ajuste de Thresholds

**Memory Leak Threshold**:
- **Conservador**: 30 MB (detecta leaks pequenos)
- **Padrão**: 50 MB (balanceado)
- **Permissivo**: 100 MB (apenas leaks grandes)

**Consecutive Failures**:
- **Sensível**: 2 falhas (recupera rapidamente)
- **Padrão**: 3 falhas (balanceado)
- **Tolerante**: 5 falhas (evita recuperações desnecessárias)

## Integração com CI/CD

### GitHub Actions

```yaml
- name: Run Sentinela Stress Test
  run: |
    python tests/sentinela/stress_test_vision.py 60 1.0  # 1 min test
  timeout-minutes: 5
```

### Pytest

```python
@pytest.mark.stress
@pytest.mark.slow
def test_vision_stability():
    """Long-running stability test."""
    results = run_stress_test(duration_seconds=60)
    assert not results['memory_leak_detected']
    assert results['success_rate'] > 95.0
```

## Troubleshooting

### Teste Falha Imediatamente

**Problema**: `TemplateNotFoundError` ou `FileNotFoundError`

**Solução**:
```bash
# Verificar se diretório de templates existe
ls templates/

# Criar templates se necessário
python -m src.sentinela.tools.capture_templates
```

### Memory Leak Falso Positivo

**Problema**: Leak detectado mas memória estável

**Solução**:
- Aumentar `leak_threshold_mb`
- Aumentar duração do teste (mais amostras)
- Verificar se outros processos estão consumindo memória

### Muitas Falhas de Captura

**Problema**: `failed_captures` alto, muitas recuperações

**Solução**:
- Verificar permissões de screenshot no OS
- Reduzir frequência de captura (aumentar intervalo)
- Verificar se display está acessível

## Métricas de Qualidade

### Critérios de Aceitação

Para considerar o sistema estável:

- ✅ **Success Rate**: ≥ 95%
- ✅ **Memory Increase**: < 50 MB em 5 minutos
- ✅ **Recoveries**: ≤ 2 em 5 minutos
- ✅ **No Memory Leak**: Aumento não constante

### Benchmarks

**Hardware de Referência**:
- CPU: Intel i5 ou equivalente
- RAM: 8 GB
- OS: Windows 10/11

**Resultados Esperados**:
- Success Rate: 99-100%
- Memory Increase: 2-5 MB
- Avg Capture Time: < 100ms
- Recoveries: 0

## Desenvolvimento

### Adicionar Novo Monitor

```python
class CustomMonitor:
    def __init__(self):
        self.metrics = []
    
    def sample(self):
        # Coletar métrica
        metric = get_custom_metric()
        self.metrics.append(metric)
    
    def get_statistics(self):
        return {
            "avg": sum(self.metrics) / len(self.metrics),
            "max": max(self.metrics),
            "min": min(self.metrics)
        }
```

### Adicionar Nova Recuperação

```python
def perform_custom_recovery(self):
    """Custom recovery logic."""
    try:
        # Limpar recursos específicos
        clear_custom_cache()
        
        # Reiniciar componente
        restart_component()
        
        return True
    except Exception as e:
        logger.error("Recovery failed: %s", e)
        return False
```

## Referências

- **OpenCV Memory Management**: https://docs.opencv.org/4.x/d1/dfb/intro.html
- **PIL/Pillow Performance**: https://pillow.readthedocs.io/en/stable/handbook/concepts.html
- **Python Memory Profiling**: https://docs.python.org/3/library/tracemalloc.html
- **psutil Documentation**: https://psutil.readthedocs.io/

## Changelog

### v1.0.0 (2024-01-15)
- ✨ Implementação inicial do stress test
- ✨ MemoryMonitor com detecção de leaks
- ✨ CameraRecoveryManager com auto-recuperação
- ✨ Relatório completo de estatísticas
- ✨ Integração com CatarataError
- 📝 Documentação completa
