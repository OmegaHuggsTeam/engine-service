"""
Testes básicos para Selum of Persistence.

Estes testes validam a funcionalidade core do Paladino sem necessidade
de um WebDriver real (usando mocks).
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


def test_imports():
    """Testa se os módulos podem ser importados."""
    try:
        from src.utils.combat_logger import CombatLogger
        from src.utils.selum_of_persistence import SelumOfPersistence
        print("✓ Imports bem-sucedidos")
        return True
    except Exception as e:
        print(f"✗ Falha no import: {e}")
        return False


def test_combat_logger():
    """Testa o CombatLogger."""
    try:
        from src.utils.combat_logger import CombatLogger
        
        # Testar métodos de log
        CombatLogger.turn_action(1, "Teste", "alvo")
        CombatLogger.result(True, "Sucesso")
        CombatLogger.progress("Progresso")
        CombatLogger.wisdom("Sabedoria")
        CombatLogger.warning("Aviso")
        CombatLogger.error("Erro")
        
        print("✓ CombatLogger funcional")
        return True
    except Exception as e:
        print(f"✗ Falha no CombatLogger: {e}")
        return False


def test_selum_structure():
    """Testa a estrutura da classe SelumOfPersistence."""
    try:
        from src.utils.selum_of_persistence import SelumOfPersistence
        
        # Verificar métodos existem
        methods = [
            'strike',
            'scout',
            'vigilance',
            'cleansing_aura',
            'steady_gaze',
            'invoke_wisdom',
            'get_battle_report',
            '_increment_turn',
            '_log_action'
        ]
        
        for method in methods:
            if not hasattr(SelumOfPersistence, method):
                print(f"✗ Método {method} não encontrado")
                return False
        
        print("✓ Estrutura da classe SelumOfPersistence completa")
        return True
    except Exception as e:
        print(f"✗ Falha na estrutura: {e}")
        return False


def test_grimoire_exists():
    """Testa se o grimório (selenium.md) existe."""
    try:
        grimoire_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            '..', 
            'src', 
            'agents', 
            'specs', 
            'selenium.md'
        )
        
        if os.path.exists(grimoire_path):
            with open(grimoire_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Verificar seções essenciais
            required_sections = [
                '# Specialist: selenium',
                '## Library Info',
                '## Common Error Patterns',
                '## Combat Maneuvers',
                '## Evolution History'
            ]
            
            for section in required_sections:
                if section not in content:
                    print(f"✗ Seção '{section}' não encontrada no grimório")
                    return False
            
            print("✓ Grimório (selenium.md) completo e válido")
            return True
        else:
            print("✗ Grimório não encontrado")
            return False
    except Exception as e:
        print(f"✗ Falha ao verificar grimório: {e}")
        return False


def run_all_tests():
    """Executa todos os testes básicos."""
    print("\n" + "=" * 70)
    print("TESTES BÁSICOS - SELUM OF PERSISTENCE")
    print("=" * 70 + "\n")
    
    tests = [
        ("Imports", test_imports),
        ("CombatLogger", test_combat_logger),
        ("Estrutura SelumOfPersistence", test_selum_structure),
        ("Grimório (selenium.md)", test_grimoire_exists),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n[Teste: {test_name}]")
        print("-" * 70)
        if test_func():
            passed += 1
        else:
            failed += 1
    
    # Sumário
    print("\n" + "=" * 70)
    print("SUMÁRIO")
    print("=" * 70)
    print(f"Total: {passed + failed}")
    print(f"Passou: {passed}")
    print(f"Falhou: {failed}")
    
    if failed == 0:
        print("\n✓ TODOS OS TESTES PASSARAM!")
        print("\n🛡️ Selum of Persistence está pronto para o combate!")
        return 0
    else:
        print(f"\n✗ {failed} TESTE(S) FALHARAM")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
