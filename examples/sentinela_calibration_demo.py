"""
Demo: Sentinela Calibration Tool e Learning Mode

Este exemplo demonstra:
1. Modo de Aprendizado (Learning Mode)
2. Sugestões de atualização de templates
3. Filtro de ruído com limpeza automática (ESC)
4. Relatório de aprendizado
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.sentinela.visual_detector import VisualDetector, AnchorPoint
from src.neural_link.telemetry.provider import TelemetryHub


def demo_learning_mode():
    """Demo 1: Learning Mode com sugestões."""
    print("\n=== Demo 1: Learning Mode ===")
    
    hub = TelemetryHub()
    detector = VisualDetector(
        templates_dir="./templates",
        confidence_threshold=0.85,
        learning_mode=True,
        learning_threshold=0.60,
        telemetry_hub=hub
    )
    
    print(f"✓ Learning Mode ativado")
    print(f"  - Confidence threshold: {detector.confidence_threshold}")
    print(f"  - Learning threshold: {detector.learning_threshold}")
    print(f"\nO que é Learning Mode?")
    print(f"  Se um template for detectado com confidence entre 0.60 e 0.85,")
    print(f"  o Sentinela sugere que o template pode precisar de atualização.")
    
    # Configurar anchors
    anchors = [
        AnchorPoint(name="dashboard_logo", template_path="...", required=True),
        AnchorPoint(name="refresh_button", template_path="...", required=True),
        AnchorPoint(name="status_icon", template_path="...", required=True),
    ]
    detector.configure_anchors(anchors)
    
    # Verificar Dashboard (vai gerar sugestões se confidence baixa)
    print(f"\n📊 Verificando Dashboard...")
    is_visible, results = detector.verify_dashboard_visible()
    
    print(f"\nResultado: {'✓ Visível' if is_visible else '✗ Não visível'}")
    
    # Verificar sugestões de aprendizado
    if detector.learning_suggestions:
        print(f"\n⚠ LEARNING MODE: {len(detector.learning_suggestions)} sugestão(ões)")
        print(detector.get_learning_report())
    else:
        print(f"\n✓ Nenhuma sugestão de aprendizado")
    
    # Verificar eventos no TelemetryHub
    events = hub.get_event_log()
    learning_events = [e for e in events if "LEARNING" in e.message]
    
    if learning_events:
        print(f"\n📝 Eventos de Learning no TelemetryHub:")
        for event in learning_events:
            print(f"  - {event.message}")
    
    return len(detector.learning_suggestions) > 0


def demo_noise_clearing():
    """Demo 2: Filtro de ruído com limpeza automática."""
    print("\n=== Demo 2: Filtro de Ruído com ESC ===")
    
    hub = TelemetryHub()
    detector = VisualDetector(
        templates_dir="./templates",
        telemetry_hub=hub
    )
    
    print(f"✓ Detector configurado")
    print(f"\nO que é Noise Clearing?")
    print(f"  Se uma notificação do Windows estiver cobrindo um anchor,")
    print(f"  o Sentinela envia ESC para limpar a tela antes de tentar novamente.")
    
    # Filtrar ruído com limpeza automática
    print(f"\n🔍 Verificando ruído visual...")
    has_noise, detected = detector.filter_noise(clear_on_detection=True)
    
    if has_noise:
        print(f"\n⚠ RUÍDO DETECTADO: {len(detected)} elemento(s)")
        for noise in detected:
            print(f"  - {noise}")
        print(f"\n✓ ESC enviado para limpar a tela")
        print(f"  Aguardando 0.5s para ruído desaparecer...")
    else:
        print(f"\n✓ Ambiente limpo: Nenhum ruído detectado")
    
    # Verificar eventos no TelemetryHub
    events = hub.get_event_log()
    noise_events = [e for e in events if "Noise" in e.message or "cleared" in e.message]
    
    if noise_events:
        print(f"\n📝 Eventos de Ruído no TelemetryHub:")
        for event in noise_events:
            print(f"  - {event.message}")
    
    return has_noise


def demo_calibration_workflow():
    """Demo 3: Workflow completo de calibração."""
    print("\n=== Demo 3: Workflow de Calibração ===")
    
    print(f"\nPasso 1: Capturar templates")
    print(f"  Comando: python -m src.sentinela.tools.capture_templates")
    print(f"  - Abre Dashboard")
    print(f"  - Pede confirmação do usuário")
    print(f"  - Captura 3 anchors automaticamente")
    print(f"  - Salva em ./templates/")
    
    print(f"\nPasso 2: Testar templates")
    print(f"  Comando: python examples/sentinela_visual_demo.py")
    print(f"  - Verifica se anchors são detectados")
    print(f"  - Mostra confidence de cada anchor")
    
    print(f"\nPasso 3: Ajustar se necessário")
    print(f"  Se confidence < 0.85:")
    print(f"  - Learning Mode sugere re-captura")
    print(f"  - Execute capture_templates novamente")
    print(f"  - Ou ajuste confidence_threshold")
    
    print(f"\nPasso 4: Validar em produção")
    print(f"  - Ative Learning Mode")
    print(f"  - Monitore sugestões")
    print(f"  - Atualize templates conforme necessário")
    
    return True


def demo_template_quality_check():
    """Demo 4: Verificação de qualidade de templates."""
    print("\n=== Demo 4: Verificação de Qualidade ===")
    
    detector = VisualDetector(templates_dir="./templates")
    
    print(f"✓ Templates carregados: {detector.template_count}")
    
    print(f"\nQualidade dos templates:")
    for template_name in detector.loaded_templates:
        template = detector._template_cache[template_name]
        height, width = template.shape
        
        # Avaliar qualidade
        quality = "✓ BOA"
        issues = []
        
        if width < 30 or height < 30:
            quality = "⚠ PEQUENO"
            issues.append("Template muito pequeno (mínimo 30x30)")
        
        if width > 200 or height > 200:
            quality = "⚠ GRANDE"
            issues.append("Template muito grande (máximo 200x200)")
        
        if width < 50 and height < 50:
            quality = "✗ RUIM"
            issues.append("Template muito pequeno para detecção confiável")
        
        print(f"\n  {template_name}:")
        print(f"    Dimensões: {width}x{height}")
        print(f"    Qualidade: {quality}")
        
        if issues:
            for issue in issues:
                print(f"    ⚠ {issue}")
    
    return True


def main():
    """Executar todas as demos."""
    print("=" * 70)
    print("Sentinela Calibration & Learning Mode - Demo")
    print("=" * 70)
    
    results = []
    
    # Demo 1: Learning Mode
    results.append(("Learning Mode", demo_learning_mode()))
    
    # Demo 2: Noise Clearing
    results.append(("Noise Clearing", demo_noise_clearing()))
    
    # Demo 3: Calibration Workflow
    results.append(("Calibration Workflow", demo_calibration_workflow()))
    
    # Demo 4: Template Quality
    results.append(("Template Quality Check", demo_template_quality_check()))
    
    # Resumo
    print("\n" + "=" * 70)
    print("Resumo dos Testes")
    print("=" * 70)
    
    for name, success in results:
        status = "✓ EXECUTADO" if success else "✗ FALHOU"
        print(f"{name:.<50} {status}")
    
    print(f"\n💡 Dicas:")
    print(f"  1. Use Learning Mode em produção para detectar templates desatualizados")
    print(f"  2. Execute capture_templates quando UI do Dashboard mudar")
    print(f"  3. Monitore TelemetryHub para eventos de Learning e Noise")
    print(f"  4. Ajuste confidence_threshold baseado no ambiente")
    
    print(f"\n📚 Comandos úteis:")
    print(f"  Capturar templates: python -m src.sentinela.tools.capture_templates")
    print(f"  Testar detecção: python examples/sentinela_visual_demo.py")
    print(f"  Ver este demo: python examples/sentinela_calibration_demo.py")


if __name__ == "__main__":
    main()
