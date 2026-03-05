"""
Testes unitários para o sistema de cache do Steady Gaze.

Feature: steady-gaze-recon
Valida: Requisitos 22.1, 22.2, 22.3, 22.4, 22.5
"""

import time
import pytest
from src.steady_gaze.cache import AnalysisCache
from src.steady_gaze.models import AnalysisReport


@pytest.fixture
def sample_report():
    """Cria um relatório de análise de exemplo para testes."""
    return AnalysisReport(
        url="https://example.com",
        timestamp=time.time(),
        analysis_duration=2.5,
        page_hash="abc123",
        overall_risk_score=50,
        phase_scores={1: 40, 2: 50, 3: 60, 4: 50},
        dimension_scores={"honeypots": 30, "waf": 70},
        phase_1_defense_anatomy=None,
        phase_2_flow_structure=None,
        phase_3_identity_persistence=None,
        phase_4_behavior_timing=None,
        recommendations=[],
        critical_warnings=[]
    )


class TestAnalysisCacheBasics:
    """Testes básicos de funcionalidade do cache."""
    
    def test_cache_initialization_default_ttl(self):
        """Testa inicialização com TTL padrão."""
        cache = AnalysisCache()
        assert cache.ttl == 3600
        assert len(cache) == 0
    
    def test_cache_initialization_custom_ttl(self):
        """Testa inicialização com TTL customizado."""
        cache = AnalysisCache(ttl_seconds=1800)
        assert cache.ttl == 1800
        assert len(cache) == 0
    
    def test_cache_miss_on_empty_cache(self, sample_report):
        """Testa que cache vazio retorna None (cache miss)."""
        cache = AnalysisCache()
        result = cache.get("nonexistent_hash")
        assert result is None
    
    def test_cache_set_and_get(self, sample_report):
        """Testa armazenamento e recuperação básica do cache."""
        cache = AnalysisCache()
        page_hash = "test_hash_123"
        
        cache.set(page_hash, sample_report)
        assert len(cache) == 1
        
        result = cache.get(page_hash)
        assert result is not None
        assert result.url == sample_report.url
        assert result.overall_risk_score == sample_report.overall_risk_score


class TestAnalysisCacheTTL:
    """Testes de validação de TTL (Time To Live)."""
    
    def test_cache_hit_within_ttl(self, sample_report):
        """Testa que cache retorna dados válidos dentro do TTL."""
        cache = AnalysisCache(ttl_seconds=10)
        page_hash = "test_hash_ttl"
        
        cache.set(page_hash, sample_report)
        
        # Imediatamente após set, deve retornar o report
        result = cache.get(page_hash)
        assert result is not None
        assert result.url == sample_report.url
    
    def test_cache_miss_after_ttl_expiration(self, sample_report):
        """Testa que cache retorna None após expiração do TTL."""
        cache = AnalysisCache(ttl_seconds=1)  # TTL de 1 segundo
        page_hash = "test_hash_expired"
        
        cache.set(page_hash, sample_report)
        assert len(cache) == 1
        
        # Aguardar expiração do TTL
        time.sleep(1.1)
        
        result = cache.get(page_hash)
        assert result is None
        assert len(cache) == 0  # Entry deve ser removida
    
    def test_cache_cleanup_expired_entries(self, sample_report):
        """Testa limpeza manual de entradas expiradas."""
        cache = AnalysisCache(ttl_seconds=1)
        
        # Adicionar múltiplas entradas
        cache.set("hash1", sample_report)
        cache.set("hash2", sample_report)
        cache.set("hash3", sample_report)
        assert len(cache) == 3
        
        # Aguardar expiração
        time.sleep(1.1)
        
        # Limpar entradas expiradas
        removed_count = cache.cleanup_expired()
        assert removed_count == 3
        assert len(cache) == 0
    
    def test_cache_cleanup_mixed_entries(self, sample_report):
        """Testa limpeza com entradas válidas e expiradas misturadas."""
        cache = AnalysisCache(ttl_seconds=2)
        
        # Adicionar primeira entrada
        cache.set("hash_old", sample_report)
        
        # Aguardar 1 segundo
        time.sleep(1.1)
        
        # Adicionar segunda entrada (ainda válida)
        cache.set("hash_new", sample_report)
        
        # Aguardar mais 1 segundo (hash_old expira, hash_new ainda válida)
        time.sleep(1.1)
        
        # Limpar entradas expiradas
        removed_count = cache.cleanup_expired()
        assert removed_count == 1
        assert len(cache) == 1
        
        # hash_new ainda deve estar acessível
        result = cache.get("hash_new")
        assert result is not None


class TestAnalysisCacheHashGeneration:
    """Testes de geração de hash de página."""
    
    def test_generate_hash_basic(self):
        """Testa geração básica de hash."""
        url = "https://example.com"
        dom = "<html><body>Test</body></html>"
        
        hash1 = AnalysisCache.generate_page_hash(url, dom)
        
        assert hash1 is not None
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256 produces 64 hex characters
    
    def test_generate_hash_deterministic(self):
        """Testa que hash é determinístico (mesma entrada = mesmo hash)."""
        url = "https://example.com"
        dom = "<html><body>Test</body></html>"
        
        hash1 = AnalysisCache.generate_page_hash(url, dom)
        hash2 = AnalysisCache.generate_page_hash(url, dom)
        
        assert hash1 == hash2
    
    def test_generate_hash_different_urls(self):
        """Testa que URLs diferentes geram hashes diferentes."""
        dom = "<html><body>Test</body></html>"
        
        hash1 = AnalysisCache.generate_page_hash("https://example.com", dom)
        hash2 = AnalysisCache.generate_page_hash("https://different.com", dom)
        
        assert hash1 != hash2
    
    def test_generate_hash_different_dom(self):
        """Testa que estruturas DOM diferentes geram hashes diferentes."""
        url = "https://example.com"
        
        hash1 = AnalysisCache.generate_page_hash(url, "<html><body>Test1</body></html>")
        hash2 = AnalysisCache.generate_page_hash(url, "<html><body>Test2</body></html>")
        
        assert hash1 != hash2
    
    def test_generate_hash_truncates_long_dom(self):
        """Testa que DOM longo é truncado para performance."""
        url = "https://example.com"
        short_dom = "x" * 500
        long_dom = "x" * 2000
        
        # Ambos devem gerar o mesmo hash pois são truncados em 1000 chars
        hash_short = AnalysisCache.generate_page_hash(url, short_dom)
        hash_long = AnalysisCache.generate_page_hash(url, long_dom)
        
        # Hashes devem ser diferentes pois 500 chars != 1000 chars
        assert hash_short != hash_long
        
        # Mas DOM > 1000 chars deve ser truncado
        very_long_dom1 = "x" * 1500
        very_long_dom2 = "x" * 2500
        hash_vlong1 = AnalysisCache.generate_page_hash(url, very_long_dom1)
        hash_vlong2 = AnalysisCache.generate_page_hash(url, very_long_dom2)
        
        # Ambos truncados em 1000 chars, então devem ser iguais
        assert hash_vlong1 == hash_vlong2
    
    def test_generate_hash_empty_dom(self):
        """Testa geração de hash com DOM vazio."""
        url = "https://example.com"
        
        hash1 = AnalysisCache.generate_page_hash(url, "")
        hash2 = AnalysisCache.generate_page_hash(url, None)
        
        assert hash1 is not None
        assert hash2 is not None
        # Ambos devem gerar o mesmo hash (empty string)
        assert hash1 == hash2


class TestAnalysisCacheOperations:
    """Testes de operações do cache."""
    
    def test_cache_clear(self, sample_report):
        """Testa limpeza completa do cache."""
        cache = AnalysisCache()
        
        # Adicionar múltiplas entradas
        cache.set("hash1", sample_report)
        cache.set("hash2", sample_report)
        cache.set("hash3", sample_report)
        assert len(cache) == 3
        
        # Limpar cache
        cache.clear()
        assert len(cache) == 0
        
        # Verificar que todas as entradas foram removidas
        assert cache.get("hash1") is None
        assert cache.get("hash2") is None
        assert cache.get("hash3") is None
    
    def test_cache_overwrite_existing_entry(self, sample_report):
        """Testa sobrescrita de entrada existente."""
        cache = AnalysisCache()
        page_hash = "test_hash"
        
        # Primeira entrada
        cache.set(page_hash, sample_report)
        result1 = cache.get(page_hash)
        assert result1.overall_risk_score == 50
        
        # Sobrescrever com novo report
        new_report = AnalysisReport(
            url="https://example.com",
            timestamp=time.time(),
            analysis_duration=3.0,
            page_hash="abc123",
            overall_risk_score=75,  # Diferente
            phase_scores={1: 70, 2: 75, 3: 80, 4: 75},
            dimension_scores={"honeypots": 60, "waf": 90},
            phase_1_defense_anatomy=None,
            phase_2_flow_structure=None,
            phase_3_identity_persistence=None,
            phase_4_behavior_timing=None,
            recommendations=[],
            critical_warnings=[]
        )
        
        cache.set(page_hash, new_report)
        result2 = cache.get(page_hash)
        assert result2.overall_risk_score == 75
        assert len(cache) == 1  # Ainda apenas uma entrada
    
    def test_cache_multiple_entries(self, sample_report):
        """Testa múltiplas entradas independentes no cache."""
        cache = AnalysisCache()
        
        # Adicionar múltiplas entradas com hashes diferentes
        for i in range(10):
            page_hash = f"hash_{i}"
            cache.set(page_hash, sample_report)
        
        assert len(cache) == 10
        
        # Verificar que todas as entradas são acessíveis
        for i in range(10):
            page_hash = f"hash_{i}"
            result = cache.get(page_hash)
            assert result is not None


class TestAnalysisCacheRoundTrip:
    """Testes de round-trip completo (set -> get -> validate)."""
    
    def test_round_trip_preserves_all_data(self, sample_report):
        """
        Testa que round-trip preserva todos os dados do relatório.
        
        Valida: Requisito 22.2 - Armazenar Analysis_Report em cache
        """
        cache = AnalysisCache()
        page_hash = "test_round_trip"
        
        # Armazenar
        cache.set(page_hash, sample_report)
        
        # Recuperar
        result = cache.get(page_hash)
        
        # Validar que todos os campos foram preservados
        assert result is not None
        assert result.url == sample_report.url
        assert result.timestamp == sample_report.timestamp
        assert result.analysis_duration == sample_report.analysis_duration
        assert result.page_hash == sample_report.page_hash
        assert result.overall_risk_score == sample_report.overall_risk_score
        assert result.phase_scores == sample_report.phase_scores
        assert result.dimension_scores == sample_report.dimension_scores
    
    def test_round_trip_with_hash_generation(self, sample_report):
        """
        Testa round-trip completo incluindo geração de hash.
        
        Valida: Requisitos 22.1, 22.2, 22.3
        """
        cache = AnalysisCache()
        url = "https://example.com/test"
        dom = "<html><body><div>Test content</div></body></html>"
        
        # Gerar hash
        page_hash = AnalysisCache.generate_page_hash(url, dom)
        
        # Armazenar
        cache.set(page_hash, sample_report)
        
        # Recuperar usando o mesmo hash
        result = cache.get(page_hash)
        
        assert result is not None
        assert result.url == sample_report.url
        
        # Gerar hash novamente com mesmos dados
        page_hash2 = AnalysisCache.generate_page_hash(url, dom)
        
        # Deve recuperar o mesmo relatório
        result2 = cache.get(page_hash2)
        assert result2 is not None
        assert result2.url == sample_report.url


class TestAnalysisCacheEdgeCases:
    """Testes de casos extremos e edge cases."""
    
    def test_cache_with_zero_ttl(self, sample_report):
        """Testa cache com TTL zero (expira imediatamente)."""
        cache = AnalysisCache(ttl_seconds=0)
        page_hash = "test_zero_ttl"
        
        cache.set(page_hash, sample_report)
        
        # Mesmo sem delay, deve expirar
        result = cache.get(page_hash)
        assert result is None
    
    def test_cache_with_very_long_ttl(self, sample_report):
        """Testa cache com TTL muito longo."""
        cache = AnalysisCache(ttl_seconds=86400 * 365)  # 1 ano
        page_hash = "test_long_ttl"
        
        cache.set(page_hash, sample_report)
        result = cache.get(page_hash)
        
        assert result is not None
    
    def test_cache_with_special_characters_in_hash(self, sample_report):
        """Testa cache com caracteres especiais no hash."""
        cache = AnalysisCache()
        
        # Hashes SHA256 são sempre hexadecimais, mas testar strings arbitrárias
        special_hashes = [
            "hash-with-dashes",
            "hash_with_underscores",
            "hash.with.dots",
            "hash/with/slashes",
            "hash with spaces"
        ]
        
        for page_hash in special_hashes:
            cache.set(page_hash, sample_report)
            result = cache.get(page_hash)
            assert result is not None
    
    def test_cleanup_on_empty_cache(self):
        """Testa limpeza em cache vazio."""
        cache = AnalysisCache()
        removed_count = cache.cleanup_expired()
        assert removed_count == 0
    
    def test_clear_on_empty_cache(self):
        """Testa clear em cache vazio."""
        cache = AnalysisCache()
        cache.clear()  # Não deve gerar erro
        assert len(cache) == 0
