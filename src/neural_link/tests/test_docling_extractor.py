"""
Tests for Docling Document Extractor.

Uses mocked httpx calls and temporary files.
No real Docling Serve instance or API calls needed.
"""

import json
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from src.extractors.docling_extractor import (
    is_docling_compatible,
    extract_with_docling,
    extract_tables,
    extract_all_documents,
    _split_text,
    _simple_split,
    SUPPORTED_EXTENSIONS,
)


# ==================================================================
# Fixtures
# ==================================================================


SAMPLE_MARKDOWN = """# Document Title

This is the first paragraph of the document. It contains some important information
about the topic being discussed. The content here is substantial enough to test
chunking behavior with reasonable text lengths.

## Section Two

The second section covers additional details. Here we have more text that will
help verify the chunking logic works correctly across section boundaries.

| Column A | Column B | Column C |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| Value 4  | Value 5  | Value 6  |

## Section Three

Final section with concluding remarks. This paragraph wraps up the document
content and provides enough text to generate multiple chunks when combined
with the sections above.
"""


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a fake PDF file (content doesn't matter, we mock the API)."""
    p = tmp_path / "report.pdf"
    p.write_bytes(b"%PDF-1.4 fake content for testing")
    return p


@pytest.fixture
def sample_docx(tmp_path):
    """Create a fake DOCX file."""
    p = tmp_path / "document.docx"
    p.write_bytes(b"PK fake docx content")
    return p


@pytest.fixture
def sample_pptx(tmp_path):
    """Create a fake PPTX file."""
    p = tmp_path / "slides.pptx"
    p.write_bytes(b"PK fake pptx content")
    return p


@pytest.fixture
def sample_image(tmp_path):
    """Create a fake PNG file."""
    p = tmp_path / "scan.png"
    p.write_bytes(b"\x89PNG fake image")
    return p


@pytest.fixture
def sample_txt(tmp_path):
    """Create a .txt file (NOT supported by Docling)."""
    p = tmp_path / "notes.txt"
    p.write_text("Just a text file", encoding="utf-8")
    return p


@pytest.fixture
def docs_dir(tmp_path):
    """Directory with multiple document types."""
    (tmp_path / "doc1.pdf").write_bytes(b"%PDF-1.4 fake")
    (tmp_path / "doc2.docx").write_bytes(b"PK fake")
    (tmp_path / "readme.txt").write_text("not supported", encoding="utf-8")
    (tmp_path / "._hidden.pdf").write_bytes(b"%PDF macOS fork")
    sub = tmp_path / "subdir"
    sub.mkdir()
    (sub / "nested.pdf").write_bytes(b"%PDF-1.4 nested")
    return tmp_path


def _mock_serve_response(markdown: str = SAMPLE_MARKDOWN):
    """Create a mock httpx response matching Docling Serve format."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "document": {
            "md_content": markdown,
        }
    }
    return mock_response


def _mock_serve_table_response():
    """Create a mock httpx response with table data."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "document": {
            "tables": [
                {"markdown": "| A | B |\n|---|---|\n| 1 | 2 |", "content": "table1"},
                {"markdown": "| X | Y |\n|---|---|\n| 3 | 4 |", "content": "table2"},
            ]
        }
    }
    return mock_response


# ==================================================================
# TestIsDoclingCompatible
# ==================================================================


class TestIsDoclingCompatible:
    """Tests for is_docling_compatible() detection."""

    def test_pdf_supported(self):
        assert is_docling_compatible("report.pdf") is True

    def test_docx_supported(self):
        assert is_docling_compatible("document.docx") is True

    def test_pptx_supported(self):
        assert is_docling_compatible("slides.pptx") is True

    def test_html_supported(self):
        assert is_docling_compatible("page.html") is True

    def test_png_supported(self):
        assert is_docling_compatible("scan.png") is True

    def test_jpg_supported(self):
        assert is_docling_compatible("photo.jpg") is True

    def test_jpeg_supported(self):
        assert is_docling_compatible("photo.jpeg") is True

    def test_tiff_supported(self):
        assert is_docling_compatible("scan.tiff") is True

    def test_txt_not_supported(self):
        assert is_docling_compatible("notes.txt") is False

    def test_json_not_supported(self):
        assert is_docling_compatible("data.json") is False

    def test_csv_not_supported(self):
        assert is_docling_compatible("data.csv") is False

    def test_mp4_not_supported(self):
        assert is_docling_compatible("video.mp4") is False

    def test_case_insensitive(self):
        assert is_docling_compatible("REPORT.PDF") is True
        assert is_docling_compatible("Doc.DOCX") is True

    def test_path_object(self):
        assert is_docling_compatible(Path("docs/report.pdf")) is True

    def test_all_supported_extensions(self):
        """Every extension in SUPPORTED_EXTENSIONS must pass."""
        for ext in SUPPORTED_EXTENSIONS:
            assert is_docling_compatible(f"file{ext}") is True


# ==================================================================
# TestSplitText
# ==================================================================


class TestSplitText:
    """Tests for _split_text() and _simple_split() helpers."""

    def test_simple_split_basic(self):
        text = "a" * 100
        chunks = _simple_split(text, chunk_size=30, overlap=10)
        assert len(chunks) > 1
        assert all(len(c) <= 30 for c in chunks)

    def test_simple_split_empty(self):
        assert _simple_split("", chunk_size=100, overlap=10) == []

    def test_simple_split_small_text(self):
        chunks = _simple_split("hello", chunk_size=100, overlap=10)
        assert len(chunks) == 1
        assert chunks[0] == "hello"

    def test_split_text_returns_strings(self):
        text = "Hello world. " * 50
        chunks = _split_text(text, chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 0
        assert all(isinstance(c, str) for c in chunks)

    def test_split_text_respects_size(self):
        text = "Word " * 500
        chunks = _split_text(text, chunk_size=200, chunk_overlap=50)
        # Chunks should be roughly within the size limit (langchain may exceed slightly)
        for c in chunks:
            assert len(c) < 400  # generous upper bound


# ==================================================================
# TestExtractWithDocling
# ==================================================================


class TestExtractWithDocling:
    """Tests for extract_with_docling() main function."""

    @pytest.mark.asyncio
    async def test_basic_extraction_via_serve(self, sample_pdf):
        """Successful extraction via Docling Serve returns chunks."""
        mock_response = _mock_serve_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client):
            chunks = await extract_with_docling(sample_pdf, chunk_size=200, chunk_overlap=50)

        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_chunk_schema(self, sample_pdf):
        """Every chunk must have all required fields."""
        mock_response = _mock_serve_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client):
            chunks = await extract_with_docling(sample_pdf)

        required_fields = {"content", "source_file", "category", "chunk_index", "char_count", "docling_metadata"}
        for chunk in chunks:
            assert required_fields.issubset(chunk.keys()), f"Missing fields: {required_fields - chunk.keys()}"

    @pytest.mark.asyncio
    async def test_chunk_content_not_empty(self, sample_pdf):
        """No chunk should have empty content."""
        mock_response = _mock_serve_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client):
            chunks = await extract_with_docling(sample_pdf)

        for chunk in chunks:
            assert len(chunk["content"].strip()) > 0

    @pytest.mark.asyncio
    async def test_chunk_index_sequential(self, sample_pdf):
        """chunk_index must be sequential starting from 0."""
        mock_response = _mock_serve_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client):
            chunks = await extract_with_docling(sample_pdf, chunk_size=200, chunk_overlap=50)

        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    @pytest.mark.asyncio
    async def test_char_count_matches_content(self, sample_pdf):
        """char_count must match actual content length."""
        mock_response = _mock_serve_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client):
            chunks = await extract_with_docling(sample_pdf)

        for chunk in chunks:
            assert chunk["char_count"] == len(chunk["content"])

    @pytest.mark.asyncio
    async def test_source_file_set(self, sample_pdf):
        """source_file must be the filename."""
        mock_response = _mock_serve_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client):
            chunks = await extract_with_docling(sample_pdf)

        for chunk in chunks:
            assert chunk["source_file"] == "report.pdf"

    @pytest.mark.asyncio
    async def test_category_default(self, sample_pdf):
        """Default category is 'documents'."""
        mock_response = _mock_serve_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client):
            chunks = await extract_with_docling(sample_pdf)

        for chunk in chunks:
            assert chunk["category"] == "documents"

    @pytest.mark.asyncio
    async def test_custom_category(self, sample_pdf):
        """Custom category propagates to all chunks."""
        mock_response = _mock_serve_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client):
            chunks = await extract_with_docling(sample_pdf, category="legal")

        for chunk in chunks:
            assert chunk["category"] == "legal"

    @pytest.mark.asyncio
    async def test_docling_metadata_present(self, sample_pdf):
        """docling_metadata must contain conversion info."""
        mock_response = _mock_serve_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client):
            chunks = await extract_with_docling(sample_pdf)

        for chunk in chunks:
            meta = chunk["docling_metadata"]
            assert meta["conversion_method"] == "docling_serve"
            assert meta["original_extension"] == ".pdf"
            assert "total_chunks" in meta
            assert "chunk_size" in meta
            assert "chunk_overlap" in meta

    @pytest.mark.asyncio
    async def test_unsupported_extension_raises(self, sample_txt):
        """Unsupported file extension raises ValueError."""
        with pytest.raises(ValueError, match="nao suportada"):
            await extract_with_docling(sample_txt)

    @pytest.mark.asyncio
    async def test_nonexistent_file_raises(self, tmp_path):
        """Nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="nao encontrado"):
            await extract_with_docling(tmp_path / "ghost.pdf")

    @pytest.mark.asyncio
    async def test_fallback_to_local_on_connect_error(self, sample_pdf):
        """When Serve is unreachable, falls back to docling local."""
        import httpx as httpx_mod

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx_mod.ConnectError("Connection refused"))

        mock_converter_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = SAMPLE_MARKDOWN
        mock_converter_instance.convert.return_value = mock_result

        with (
            patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client),
            patch(
                "src.extractors.docling_extractor._convert_via_local",
                return_value=SAMPLE_MARKDOWN,
            ) as mock_local,
        ):
            chunks = await extract_with_docling(sample_pdf, chunk_size=200, chunk_overlap=50)

        mock_local.assert_called_once_with(sample_pdf)
        assert len(chunks) > 0
        assert chunks[0]["docling_metadata"]["conversion_method"] == "docling_local"

    @pytest.mark.asyncio
    async def test_runtime_error_when_both_fail(self, sample_pdf):
        """Raises RuntimeError when both Serve and local fail."""
        import httpx as httpx_mod

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx_mod.ConnectError("Connection refused"))

        with (
            patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client),
            patch(
                "src.extractors.docling_extractor._convert_via_local",
                side_effect=ImportError("No module named 'docling'"),
            ),
        ):
            with pytest.raises(RuntimeError, match="Falha ao converter"):
                await extract_with_docling(sample_pdf)

    @pytest.mark.asyncio
    async def test_empty_content_returns_empty(self, sample_pdf):
        """Empty markdown from Docling returns empty list."""
        mock_response = _mock_serve_response(markdown="   ")
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client):
            chunks = await extract_with_docling(sample_pdf)

        assert chunks == []

    @pytest.mark.asyncio
    async def test_docx_extraction(self, sample_docx):
        """DOCX files are processed correctly."""
        mock_response = _mock_serve_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client):
            chunks = await extract_with_docling(sample_docx)

        assert len(chunks) > 0
        assert chunks[0]["source_file"] == "document.docx"
        assert chunks[0]["docling_metadata"]["original_extension"] == ".docx"

    @pytest.mark.asyncio
    async def test_image_ocr_extraction(self, sample_image):
        """Image files (OCR) are processed correctly."""
        ocr_text = "This text was extracted via OCR from a scanned document."
        mock_response = _mock_serve_response(markdown=ocr_text)
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client):
            chunks = await extract_with_docling(sample_image)

        assert len(chunks) > 0
        assert chunks[0]["docling_metadata"]["original_extension"] == ".png"


# ==================================================================
# TestExtractTables
# ==================================================================


class TestExtractTables:
    """Tests for extract_tables() function."""

    @pytest.mark.asyncio
    async def test_extracts_tables(self, sample_pdf):
        """Tables are extracted as individual chunks."""
        mock_response = _mock_serve_table_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client):
            tables = await extract_tables(sample_pdf)

        assert len(tables) == 2

    @pytest.mark.asyncio
    async def test_table_chunk_schema(self, sample_pdf):
        """Table chunks have correct schema."""
        mock_response = _mock_serve_table_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client):
            tables = await extract_tables(sample_pdf)

        required_fields = {"content", "source_file", "category", "chunk_index", "char_count", "docling_metadata"}
        for table in tables:
            assert required_fields.issubset(table.keys())
            assert table["category"] == "tables"
            assert table["docling_metadata"]["content_type"] == "table"

    @pytest.mark.asyncio
    async def test_table_unsupported_extension(self, sample_txt):
        """Unsupported file raises ValueError."""
        with pytest.raises(ValueError, match="nao suportada"):
            await extract_tables(sample_txt)

    @pytest.mark.asyncio
    async def test_table_nonexistent_file(self, tmp_path):
        """Nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="nao encontrado"):
            await extract_tables(tmp_path / "ghost.pdf")

    @pytest.mark.asyncio
    async def test_table_serve_unavailable(self, sample_pdf):
        """RuntimeError when Docling Serve is unreachable."""
        import httpx as httpx_mod

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx_mod.ConnectError("Connection refused"))

        with patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(RuntimeError, match="indisponivel"):
                await extract_tables(sample_pdf)


# ==================================================================
# TestExtractAllDocuments
# ==================================================================


class TestExtractAllDocuments:
    """Tests for extract_all_documents() directory scanner."""

    @pytest.mark.asyncio
    async def test_finds_all_documents(self, docs_dir):
        """Finds and processes all compatible documents recursively."""
        mock_response = _mock_serve_response()
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("src.extractors.docling_extractor.httpx.AsyncClient", return_value=mock_client):
            chunks = await extract_all_documents(docs_dir, chunk_size=200, chunk_overlap=50)

        # Should find doc1.pdf, doc2.docx, nested.pdf (3 files)
        # .txt is skipped, ._hidden.pdf is skipped
        source_files = {c["source_file"] for c in chunks}
        assert "doc1.pdf" in source_files
        assert "doc2.docx" in source_files
        assert "nested.pdf" in source_files
        assert "readme.txt" not in source_files
        assert "._hidden.pdf" not in source_files

    @pytest.mark.asyncio
    async def test_empty_directory(self, tmp_path):
        """Empty directory returns empty list."""
        chunks = await extract_all_documents(tmp_path)
        assert chunks == []

    @pytest.mark.asyncio
    async def test_nonexistent_directory(self, tmp_path):
        """Nonexistent directory returns empty list (no error)."""
        chunks = await extract_all_documents(tmp_path / "nonexistent")
        assert chunks == []
