"""
Testes unitários para RAG Query System.
"""

import os
import shutil
import tempfile
import unittest

from src.rag.rag_query_system import RAGQuerySystem


class TestRAGQuerySystem(unittest.TestCase):
    """Testes para RAGQuerySystem."""

    def setUp(self):
        """Criar diretório temporário para testes."""
        self.temp_dir = tempfile.mkdtemp()

        # Criar arquivo markdown de teste
        self.test_md = os.path.join(self.temp_dir, "test.md")
        with open(self.test_md, "w", encoding="utf-8") as f:
            f.write(
                """# Test Document

## strike

**Assinatura**: `strike(selector: str) -> bool`

Executa um clique resiliente.

## scout

**Assinatura**: `scout(possibilities: List) -> WebElement`

Busca elemento com múltiplas estratégias.
"""
            )

    def tearDown(self):
        """Remover diretório temporário."""
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Testa inicialização do RAG."""
        rag = RAGQuerySystem(grimoire_path=self.temp_dir)

        # Deve ter indexado o arquivo
        self.assertEqual(len(rag.get_indexed_files()), 1)
        self.assertIn("test.md", rag.get_indexed_files()[0])

    def test_parse_markdown_sections(self):
        """Testa parsing de seções markdown."""
        rag = RAGQuerySystem(grimoire_path=self.temp_dir)

        content = """## Section 1
Content 1

## Section 2
Content 2
"""
        sections = rag._parse_markdown_sections(content)

        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0].title, "Section 1")
        self.assertEqual(sections[1].title, "Section 2")

    def test_tokenize(self):
        """Testa tokenização de texto."""
        rag = RAGQuerySystem(grimoire_path=self.temp_dir)

        text = "This is a test, with punctuation!"
        tokens = rag._tokenize(text)

        # Deve remover stopwords e pontuação
        self.assertIn("test", tokens)
        self.assertIn("punctuation", tokens)
        self.assertNotIn("is", tokens)  # stopword
        self.assertNotIn("a", tokens)  # stopword

    def test_query_returns_results(self):
        """Testa que query retorna resultados relevantes."""
        rag = RAGQuerySystem(grimoire_path=self.temp_dir)

        results = rag.query("clique resiliente")

        # Deve encontrar seção "strike"
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].section, "strike")

    def test_query_empty_returns_empty(self):
        """Testa que query vazia retorna lista vazia."""
        rag = RAGQuerySystem(grimoire_path=self.temp_dir)

        results = rag.query("")

        self.assertEqual(len(results), 0)

    def test_query_no_match_returns_empty(self):
        """Testa que query sem match retorna lista vazia."""
        rag = RAGQuerySystem(grimoire_path=self.temp_dir)

        results = rag.query("xyzabc123nonexistent")

        self.assertEqual(len(results), 0)

    def test_get_all_abstractions(self):
        """Testa extração de abstrações."""
        # Criar arquivo Abstractions.md no temp dir
        abstractions_file = os.path.join(self.temp_dir, "Abstractions.md")
        with open(abstractions_file, "w", encoding="utf-8") as f:
            f.write(
                """# Abstractions

## strike

Clique resiliente.

## scout

Busca elemento.
"""
            )

        rag = RAGQuerySystem(grimoire_path=self.temp_dir)

        abstractions = rag.get_all_abstractions()

        # Deve encontrar strike e scout
        self.assertIn("strike", abstractions)
        self.assertIn("scout", abstractions)

    def test_failed_files_handling(self):
        """Testa tratamento de arquivos corrompidos."""
        # Criar arquivo inválido
        invalid_file = os.path.join(self.temp_dir, "invalid.md")
        with open(invalid_file, "wb") as f:
            f.write(b"\x80\x81\x82")  # Bytes inválidos

        rag = RAGQuerySystem(grimoire_path=self.temp_dir)

        # Deve ter registrado falha mas continuado
        self.assertGreater(len(rag.failed_files), 0)
        # Deve ter indexado o arquivo válido
        self.assertGreater(len(rag.get_indexed_files()), 0)

    def test_re_index(self):
        """Testa re-indexação."""
        rag = RAGQuerySystem(grimoire_path=self.temp_dir)

        initial_count = len(rag.get_indexed_files())

        # Adicionar novo arquivo
        new_file = os.path.join(self.temp_dir, "new.md")
        with open(new_file, "w", encoding="utf-8") as f:
            f.write("## New Section\nNew content")

        # Re-indexar
        rag.re_index()

        # Deve ter indexado o novo arquivo
        self.assertEqual(len(rag.get_indexed_files()), initial_count + 1)


class TestRAGQuerySystemWithRealGrimoire(unittest.TestCase):
    """Testes com grimoire real."""

    def setUp(self):
        """Verificar se grimoire existe."""
        self.grimoire_path = "docs/paladin_grimoire/"
        if not os.path.exists(self.grimoire_path):
            self.skipTest("Grimoire não encontrado")

    def test_index_real_grimoire(self):
        """Testa indexação do grimoire real."""
        rag = RAGQuerySystem(grimoire_path=self.grimoire_path)

        # Deve ter indexado múltiplos arquivos
        indexed = rag.get_indexed_files()
        self.assertGreater(len(indexed), 0)

        # Deve incluir Abstractions.md
        self.assertTrue(any("Abstractions.md" in f for f in indexed))

    def test_query_strike_abstraction(self):
        """Testa busca por abstração strike."""
        rag = RAGQuerySystem(grimoire_path=self.grimoire_path)

        results = rag.query("clicar resiliente fallback")

        # Deve retornar resultados relevantes
        self.assertGreater(len(results), 0)
        # Verificar que retornou conteúdo
        self.assertGreater(len(results[0].content), 0)

    def test_query_wait_abstraction(self):
        """Testa busca por abstração de espera."""
        rag = RAGQuerySystem(grimoire_path=self.grimoire_path)

        results = rag.query("vigilance aguardar timeout")

        # Deve retornar resultados relevantes
        self.assertGreater(len(results), 0)
        # Verificar que retornou conteúdo
        self.assertGreater(len(results[0].content), 0)

    def test_get_all_abstractions_real(self):
        """Testa extração de todas as abstrações."""
        rag = RAGQuerySystem(grimoire_path=self.grimoire_path)

        abstractions = rag.get_all_abstractions()

        # Deve incluir abstrações principais
        expected = ["strike", "scout", "vigilance", "steady_gaze", "cleansing_aura"]
        for abstraction in expected:
            self.assertIn(abstraction, abstractions)


if __name__ == "__main__":
    unittest.main()
