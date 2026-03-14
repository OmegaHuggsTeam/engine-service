"""
Demo: Sentinela Screenshot Analyzer com Teste de Catarata

Este exemplo demonstra:
1. Captura de screenshot
2. Detecção de Catarata (tela preta/permissão negada)
3. Integração com TelemetryHub
4. Template matching básico
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np

from src.neural_link.telemetry.provider import TelemetryHub
from src.sentinela.exceptions import CatarataError, ScreenshotError
from src.sentinela.screenshot_analyzer import ScreenshotAnalyzer


def demo_basic_capture():
    """Demo 1: Captura básica de screenshot."""
    print("\n=== Demo 1: Captura Básica ===")

    analyzer = ScreenshotAnalyzer()

    try:
        screenshot = analyzer.capture_screenshot()
        print(f"✓ Screenshot capturado: {screenshot.shape}")
        print(f"  - Dimensões: {screenshot.shape[1]}x{screenshot.shape[0]}")
        print(f"  - Canais: {screenshot.shape[2]} (RGB)")
        print(f"  - Tipo: {screenshot.dtype}")

        # Converter para grayscale
        gray = analyzer.to_grayscale(screenshot)
        print(f"✓ Convertido para grayscale: {gray.shape}")

        # Calcular brightness médio
        brightness = np.mean(screenshot)
        print(f"✓ Brightness médio: {brightness:.2f}/255")

        return True

    except CatarataError as e:
        print(f"✗ CATARATA DETECTADA: {e}")
        return False
    except ScreenshotError as e:
        print(f"✗ Erro de captura: {e}")
        return False


def demo_with_telemetry():
    """Demo 2: Captura com TelemetryHub."""
    print("\n=== Demo 2: Integração com TelemetryHub ===")

    # Criar TelemetryHub
    hub = TelemetryHub()
    analyzer = ScreenshotAnalyzer(telemetry_hub=hub)

    try:
        analyzer.capture_screenshot()
        print("✓ Screenshot capturado com telemetria")

        # Verificar eventos
        events = hub.get_event_log()
        print(f"✓ Eventos no hub: {len(events)}")

        if len(events) > 0:
            print("\nEventos registrados:")
            for event in events:
                print(f"  - [{event.event_type}] {event.message}")

        return True

    except CatarataError as e:
        print(f"✗ CATARATA DETECTADA: {e}")

        # Verificar se erro foi reportado
        events = hub.get_event_log()
        print(f"\n✓ Erro reportado ao TelemetryHub: {len(events)} evento(s)")

        for event in events:
            print("\nEvento de Catarata:")
            print(f"  - Tipo: {event.event_type}")
            print(f"  - Fonte: {event.source}")
            print(f"  - Mensagem: {event.message}")
            print(f"  - Severidade: {event.data.get('severity')}")
            print(f"  - Tipo de erro: {event.data.get('error_type')}")

        return False


def demo_template_matching():
    """Demo 3: Template matching básico."""
    print("\n=== Demo 3: Template Matching ===")

    analyzer = ScreenshotAnalyzer()

    try:
        # Capturar screenshot
        screenshot = analyzer.capture_screenshot()
        gray = analyzer.to_grayscale(screenshot)

        print("✓ Screenshot preparado para matching")
        print(f"  - Dimensões: {gray.shape}")

        # Criar um template simples (canto superior esquerdo 100x100)
        template = gray[0:100, 0:100]
        print(f"✓ Template criado: {template.shape}")

        # Fazer matching
        confidence, x, y = analyzer.match_template(gray, template)

        print("\nResultado do matching:")
        print(f"  - Confidence: {confidence:.3f}")
        print(f"  - Posição: ({x}, {y})")

        if confidence > 0.9:
            print("  ✓ Match encontrado com alta confiança!")
        else:
            print("  ⚠ Match com baixa confiança")

        # Testar multi-escala
        print("\n✓ Testando matching multi-escala...")
        conf, cx, cy, scale = analyzer.match_multiscale(gray, template, scales=[0.9, 1.0, 1.1])

        print(f"  - Melhor confidence: {conf:.3f}")
        print(f"  - Centro: ({cx}, {cy})")
        print(f"  - Escala: {scale:.1f}x")

        return True

    except CatarataError as e:
        print(f"✗ CATARATA DETECTADA: {e}")
        return False


def main():
    """Executar todas as demos."""
    print("=" * 60)
    print("Sentinela Screenshot Analyzer - Demo")
    print("=" * 60)

    results = []

    # Demo 1: Captura básica
    results.append(("Captura Básica", demo_basic_capture()))

    # Demo 2: Com telemetria
    results.append(("TelemetryHub", demo_with_telemetry()))

    # Demo 3: Template matching
    results.append(("Template Matching", demo_template_matching()))

    # Resumo
    print("\n" + "=" * 60)
    print("Resumo dos Testes")
    print("=" * 60)

    for name, success in results:
        status = "✓ PASSOU" if success else "✗ FALHOU"
        print(f"{name:.<40} {status}")

    total = len(results)
    passed = sum(1 for _, s in results if s)

    print(f"\nTotal: {passed}/{total} demos executadas com sucesso")

    if passed == total:
        print("\n🎉 Todos os testes passaram! Sistema visual operacional.")
    else:
        print("\n⚠ Alguns testes falharam. Verifique a saída acima.")


if __name__ == "__main__":
    main()
