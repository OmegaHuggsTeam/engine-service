"""
Demo: Sentinela Visual Detector com Ancoragem e Filtro de Ruído

Este exemplo demonstra:
1. Carregamento de templates de ancoragem
2. Verificação de Dashboard visível (3 anchors)
3. Confirmação visual de alerta
4. Filtro de ambiente ruidoso
5. Integração com TelemetryHub
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.neural_link.telemetry.provider import TelemetryHub
from src.sentinela.exceptions import CatarataError
from src.sentinela.visual_detector import AnchorPoint, VisualDetector


def demo_template_loading():
    """Demo 1: Carregamento de templates."""
    print("\n=== Demo 1: Carregamento de Templates ===")

    detector = VisualDetector(templates_dir="./templates")

    print(f"✓ Templates carregados: {detector.template_count}")
    print("\nTemplates disponíveis:")
    for template in detector.loaded_templates:
        print(f"  - {template}")

    return detector


def demo_anchor_configuration(detector):
    """Demo 2: Configuração de anchors."""
    print("\n=== Demo 2: Configuração de Anchors ===")

    # Configurar 3 anchors para identificar Dashboard
    anchors = [
        AnchorPoint(
            name="dashboard_logo",
            template_path="templates/dashboard_logo.png",
            required=True,
            min_confidence=0.85,
        ),
        AnchorPoint(
            name="refresh_button",
            template_path="templates/refresh_button.png",
            required=True,
            min_confidence=0.80,
        ),
        AnchorPoint(
            name="status_icon",
            template_path="templates/status_icon.png",
            required=True,
            min_confidence=0.80,
        ),
    ]

    detector.configure_anchors(anchors)

    print(f"✓ Configurados {len(anchors)} anchor points:")
    for anchor in anchors:
        print(f"  - {anchor.name} (required={anchor.required}, min_conf={anchor.min_confidence})")

    return True


def demo_dashboard_verification(detector):
    """Demo 3: Verificação de Dashboard visível."""
    print("\n=== Demo 3: Verificação de Dashboard (Ancoragem) ===")

    try:
        is_visible, anchor_results = detector.verify_dashboard_visible()

        print("\nResultado da verificação:")
        print(f"  Dashboard visível: {'✓ SIM' if is_visible else '✗ NÃO'}")

        print("\nStatus dos anchors:")
        for anchor_name, result in anchor_results.items():
            status = "✓ DETECTADO" if result.found else "✗ NÃO DETECTADO"
            print(f"  - {anchor_name}: {status} (conf={result.confidence:.3f})")
            if result.found:
                print(f"    Posição: ({result.center_x}, {result.center_y})")

        return is_visible

    except CatarataError as e:
        print(f"✗ CATARATA: {e}")
        return False
    except Exception as e:
        print(f"✗ Erro: {e}")
        return False


def demo_alert_confirmation(detector):
    """Demo 4: Confirmação visual de alerta."""
    print("\n=== Demo 4: Confirmação Visual de Alerta ===")

    try:
        # Procurar template de alerta
        alert_templates = [t for t in detector.loaded_templates if "alert" in t.lower()]

        if not alert_templates:
            print("⚠ Nenhum template de alerta encontrado")
            return False

        alert_template = alert_templates[0]
        print(f"Procurando alerta: {alert_template}")

        confirmed = detector.confirm_alert_visible(alert_template)

        if confirmed:
            print("✓ MISSÃO COMPLETA: Alerta confirmado visível!")
            print("  O Sentinela 'enxergou' o alerta de quality_score baixo")
        else:
            print("✗ Alerta não detectado")
            print("  Missão não pode ser marcada como concluída")

        return confirmed

    except Exception as e:
        print(f"✗ Erro: {e}")
        return False


def demo_noise_filtering(detector):
    """Demo 5: Filtro de ambiente ruidoso."""
    print("\n=== Demo 5: Filtro de Ambiente Ruidoso ===")

    try:
        # Procurar templates de ruído
        noise_templates = [
            t
            for t in detector.loaded_templates
            if any(keyword in t.lower() for keyword in ["notification", "popup", "windows"])
        ]

        if not noise_templates:
            print("⚠ Nenhum template de ruído encontrado")
            return True

        print(f"Verificando {len(noise_templates)} tipos de ruído:")
        for template in noise_templates:
            print(f"  - {template}")

        has_noise, detected_noise = detector.filter_noise(noise_templates=noise_templates)

        if has_noise:
            print(f"\n⚠ RUÍDO DETECTADO: {len(detected_noise)} elemento(s)")
            for noise in detected_noise:
                print(f"  - {noise} (IGNORADO)")
            print("\n✓ Sentinela continua focado no Dashboard")
        else:
            print("\n✓ Ambiente limpo: Nenhum ruído detectado")

        return True

    except Exception as e:
        print(f"✗ Erro: {e}")
        return False


def demo_with_telemetry():
    """Demo 6: Integração completa com TelemetryHub."""
    print("\n=== Demo 6: Integração com TelemetryHub ===")

    hub = TelemetryHub()
    detector = VisualDetector(templates_dir="./templates", telemetry_hub=hub)

    print("✓ TelemetryHub conectado")

    # Configurar anchors
    anchors = [
        AnchorPoint(
            name="dashboard_logo", template_path="templates/dashboard_logo.png", required=True
        ),
    ]
    detector.configure_anchors(anchors)

    # Verificar Dashboard
    try:
        is_visible, _ = detector.verify_dashboard_visible()

        # Verificar eventos no hub
        events = hub.get_event_log()
        print(f"\n✓ Eventos registrados no TelemetryHub: {len(events)}")

        if events:
            print("\nÚltimos eventos:")
            for event in events[-3:]:  # Últimos 3 eventos
                print(f"  - [{event.source}] {event.message}")

        return True

    except Exception as e:
        print(f"✗ Erro: {e}")
        return False


def main():
    """Executar todas as demos."""
    print("=" * 70)
    print("Sentinela Visual Detector - Demo Completo")
    print("Missão 002: Ancoragem, Confirmação Visual e Filtro de Ruído")
    print("=" * 70)

    results = []

    # Demo 1: Template loading
    detector = demo_template_loading()
    results.append(("Template Loading", detector is not None))

    if detector:
        # Demo 2: Anchor configuration
        results.append(("Anchor Configuration", demo_anchor_configuration(detector)))

        # Demo 3: Dashboard verification
        results.append(("Dashboard Verification", demo_dashboard_verification(detector)))

        # Demo 4: Alert confirmation
        results.append(("Alert Confirmation", demo_alert_confirmation(detector)))

        # Demo 5: Noise filtering
        results.append(("Noise Filtering", demo_noise_filtering(detector)))

    # Demo 6: Telemetry integration
    results.append(("Telemetry Integration", demo_with_telemetry()))

    # Resumo
    print("\n" + "=" * 70)
    print("Resumo dos Testes")
    print("=" * 70)

    for name, success in results:
        status = "✓ PASSOU" if success else "✗ FALHOU"
        print(f"{name:.<50} {status}")

    total = len(results)
    passed = sum(1 for _, s in results if s)

    print(f"\nTotal: {passed}/{total} demos executadas com sucesso")

    if passed == total:
        print("\n🎉 Sistema visual completo operacional!")
        print("   - Ancoragem: 3 pontos fixos identificam Dashboard")
        print("   - Confirmação: Alerta visual detectado")
        print("   - Filtro de ruído: Notificações ignoradas")
    else:
        print("\n⚠ Alguns testes falharam. Verifique a saída acima.")


if __name__ == "__main__":
    main()
