"""
RAG Query System - Sistema de busca em documentação estruturada.

Implementa indexação e busca TF-IDF em arquivos markdown do Paladin Grimoire.
"""

import math
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class Section:
    """Seção de um documento markdown."""

    title: str
    content: str
    line_start: int
    line_end: int


@dataclass
class Document:
    """Documento indexado."""

    path: str
    sections: List[Section]
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class RAGIndex:
    """Índice invertido para busca rápida."""

    documents: Dict[str, Document] = field(default_factory=dict)
    term_index: Dict[str, List[tuple]] = field(
        default_factory=dict
    )  # term -> [(doc_path, section_idx, tf)]
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class RAGResult:
    """Resultado de uma consulta RAG."""

    document: str  # Nome do documento
    section: str  # Título da seção
    content: str  # Conteúdo relevante
    score: float  # Score de relevância (0-1)


class RAGQuerySystem:
    """Sistema de busca RAG com indexação TF-IDF."""

    def __init__(self, grimoire_path: str = "docs/paladin_grimoire/"):
        """
        Inicializa o sistema RAG.

        Args:
            grimoire_path: Caminho para o diretório do grimoire
        """
        self.grimoire_path = grimoire_path
        self.index = RAGIndex()
        self.failed_files: List[str] = []

        # Indexar documentos na inicialização
        if os.path.exists(grimoire_path):
            self.index_documents()

    def index_documents(self) -> None:
        """
        Indexa todos os arquivos markdown no grimoire.

        Percorre recursivamente o diretório e indexa cada arquivo .md.
        """
        if not os.path.exists(self.grimoire_path):
            return

        self.failed_files = []

        # Percorrer diretório recursivamente
        for root, dirs, files in os.walk(self.grimoire_path):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    try:
                        self._index_file(file_path)
                    except Exception as e:
                        print(f"[RAG] Falha ao indexar {file_path}: {e}")
                        self.failed_files.append(file_path)

        # Atualizar timestamp
        self.index.last_updated = datetime.now()

    def _index_file(self, file_path: str) -> None:
        """
        Indexa um arquivo markdown específico.

        Args:
            file_path: Caminho completo do arquivo
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parsear seções do markdown
        sections = self._parse_markdown_sections(content)

        # Criar documento
        relative_path = os.path.relpath(file_path, self.grimoire_path)
        doc = Document(path=relative_path, sections=sections, metadata={"file_path": file_path})

        # Adicionar ao índice de documentos
        self.index.documents[relative_path] = doc

        # Indexar termos de cada seção
        for section_idx, section in enumerate(sections):
            self._index_section(relative_path, section_idx, section)

    def _parse_markdown_sections(self, content: str) -> List[Section]:
        """
        Parseia seções de um arquivo markdown.

        Seções são delimitadas por headers (##, ###, etc.).

        Args:
            content: Conteúdo do arquivo markdown

        Returns:
            Lista de seções encontradas
        """
        sections = []
        lines = content.split("\n")

        current_section = None
        current_content = []
        current_start = 0

        for line_num, line in enumerate(lines):
            # Detectar header (## ou ###)
            if line.startswith("##"):
                # Salvar seção anterior se existir
                if current_section:
                    sections.append(
                        Section(
                            title=current_section,
                            content="\n".join(current_content),
                            line_start=current_start,
                            line_end=line_num - 1,
                        )
                    )

                # Iniciar nova seção
                current_section = line.lstrip("#").strip()
                current_content = []
                current_start = line_num
            else:
                # Adicionar linha ao conteúdo da seção atual
                if current_section:
                    current_content.append(line)

        # Salvar última seção
        if current_section:
            sections.append(
                Section(
                    title=current_section,
                    content="\n".join(current_content),
                    line_start=current_start,
                    line_end=len(lines) - 1,
                )
            )

        return sections

    def _index_section(self, doc_path: str, section_idx: int, section: Section) -> None:
        """
        Indexa termos de uma seção no índice invertido.

        Args:
            doc_path: Caminho do documento
            section_idx: Índice da seção no documento
            section: Seção a indexar
        """
        # Extrair termos (tokenização simples)
        text = f"{section.title} {section.content}".lower()
        terms = self._tokenize(text)

        # Calcular TF (term frequency)
        term_counts = defaultdict(int)
        for term in terms:
            term_counts[term] += 1

        # Adicionar ao índice invertido
        for term, count in term_counts.items():
            tf = count / len(terms) if terms else 0

            if term not in self.index.term_index:
                self.index.term_index[term] = []

            self.index.term_index[term].append((doc_path, section_idx, tf))

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokeniza texto em termos.

        Remove pontuação, converte para lowercase, remove stopwords.

        Args:
            text: Texto a tokenizar

        Returns:
            Lista de termos
        """
        # Remover pontuação e caracteres especiais
        text = re.sub(r"[^\w\s]", " ", text)

        # Split em palavras
        words = text.split()

        # Remover stopwords comuns (português e inglês)
        stopwords = {
            "a",
            "o",
            "e",
            "de",
            "da",
            "do",
            "em",
            "para",
            "com",
            "por",
            "um",
            "uma",
            "the",
            "is",
            "at",
            "which",
            "on",
            "and",
            "or",
            "to",
            "from",
            "by",
            "as",
        }

        # Filtrar stopwords e palavras muito curtas
        terms = [w.lower() for w in words if len(w) > 2 and w.lower() not in stopwords]

        return terms

    def query(self, query_text: str, top_k: int = 5) -> List[RAGResult]:
        """
        Busca documentação relevante usando TF-IDF.

        Args:
            query_text: Texto da consulta
            top_k: Número máximo de resultados

        Returns:
            Lista de RAGResult ordenada por relevância
        """
        start_time = time.time()

        # Tokenizar query
        query_terms = self._tokenize(query_text)

        if not query_terms:
            return []

        # Calcular scores para cada seção
        section_scores = defaultdict(float)

        for term in query_terms:
            if term in self.index.term_index:
                # Calcular IDF (inverse document frequency)
                # Contar quantos DOCUMENTOS únicos contêm o termo (não seções)
                unique_docs = set(doc_path for doc_path, _, _ in self.index.term_index[term])
                df = len(unique_docs)  # document frequency
                idf = math.log((len(self.index.documents) + 1) / (df + 1))

                # Adicionar score TF-IDF para cada seção que contém o termo
                for doc_path, section_idx, tf in self.index.term_index[term]:
                    section_key = (doc_path, section_idx)
                    section_scores[section_key] += tf * idf

        # Ordenar por score
        sorted_sections = sorted(section_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # Criar resultados
        results = []
        for (doc_path, section_idx), score in sorted_sections:
            doc = self.index.documents[doc_path]
            section = doc.sections[section_idx]

            # Normalizar score para 0-1
            max_score = sorted_sections[0][1] if sorted_sections else 1
            normalized_score = score / max_score if max_score > 0 else 0

            results.append(
                RAGResult(
                    document=doc_path,
                    section=section.title,
                    content=section.content[:500],  # Limitar a 500 chars
                    score=normalized_score,
                )
            )

        # Verificar performance
        elapsed = (time.time() - start_time) * 1000  # ms
        if elapsed > 100:
            print(f"[RAG] Aviso: Busca demorou {elapsed:.2f}ms (limite: 100ms)")

        return results

    def query_with_scores(self, query_text: str, top_k: int = 5) -> list[dict]:
        """
        Busca TF-IDF retornando dicts normalizados para integracao com HybridRAG.
        Cada dict contem: content, source_file, section, score (0-1).
        """
        results = self.query(query_text, top_k=top_k)
        return [
            {
                "content": r.content,
                "source_file": r.document,
                "section": r.section,
                "score": r.score,
                "engine": "tfidf",
            }
            for r in results
        ]

    def get_all_abstractions(self) -> List[str]:
        """
        Retorna lista de todas as abstrações disponíveis.

        Extrai nomes de seções do Abstractions.md.

        Returns:
            Lista de nomes de abstrações
        """
        abstractions = []

        # Procurar Abstractions.md
        for doc_path, doc in self.index.documents.items():
            if "Abstractions.md" in doc_path:
                # Extrair títulos de seções
                for section in doc.sections:
                    # Ignorar seções de resumo e título principal
                    title_lower = section.title.lower()
                    if title_lower not in [
                        "resumo de uso",
                        "resumo",
                        "abstractions",
                        "abstractions - manobras do selum of persistence",
                    ]:
                        abstractions.append(section.title)

        return abstractions

    def get_indexed_files(self) -> List[str]:
        """
        Retorna lista de arquivos indexados.

        Returns:
            Lista de caminhos relativos dos documentos indexados
        """
        return list(self.index.documents.keys())

    def re_index(self) -> None:
        """Re-indexa todos os documentos."""
        self.index = RAGIndex()
        self.index_documents()
