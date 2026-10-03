import fitz  # PyMuPDF
from docx import Document
from pathlib import Path
import hashlib
import logging

logger = logging.getLogger(__name__)

class DocumentIngestor:
    """Handles extraction of text from various document formats."""

    @staticmethod
    def get_file_hash(file_path: Path) -> str:
        """Returns the SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def extract_text(self, file_path: Path) -> str:
        """Extracts text from PDF, DOCX, or MD files."""
        suffix = file_path.suffix.lower()

        if suffix == ".pdf":
            return self._extract_pdf(file_path)
        elif suffix == ".docx":
            return self._extract_docx(file_path)
        elif suffix in [".md", ".txt"]:
            return self._extract_text_file(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    def _extract_pdf(self, file_path: Path) -> str:
        """Extracts text from PDF using PyMuPDF."""
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text() + "\n"
        return text

    def _extract_docx(self, file_path: Path) -> str:
        """Extracts text from DOCX using python-docx."""
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    def _extract_text_file(self, file_path: Path) -> str:
        """Extracts text from plain text or markdown files."""
        return file_path.read_text(encoding="utf-8")

# Simple OCR placeholder for Phase 1
# In Phase 2/3, we will implement full Tesseract integration in ocr.py
