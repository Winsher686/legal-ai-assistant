"""文档解析模块：解析 PDF / TXT / DOCX，提取页面文本与页码。"""
import os
from typing import List, Tuple

from app.core.logger import logger


class DocumentParser:
    """按文件类型分发解析。"""

    def parse(self, file_path: str) -> List[Tuple[int, str]]:
        """返回 [(page_number, text), ...]。"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return self._parse_pdf(file_path)
        if ext in (".txt", ".md"):
            return self._parse_text(file_path)
        if ext == ".docx":
            return self._parse_docx(file_path)
        logger.warning("unsupported file type: %s", ext)
        return []

    def _parse_pdf(self, file_path: str) -> List[Tuple[int, str]]:
        pages = []
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(file_path)
            for i, page in enumerate(doc):
                text = page.get_text("text")
                pages.append((i + 1, text))
            doc.close()
        except Exception as e:
            logger.error("pdf parse failed %s: %s", file_path, e)
        return pages

    def _parse_text(self, file_path: str) -> List[Tuple[int, str]]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError:
            with open(file_path, "r", encoding="gbk", errors="ignore") as f:
                text = f.read()
        return [(1, text)]

    def _parse_docx(self, file_path: str) -> List[Tuple[int, str]]:
        try:
            from docx import Document

            doc = Document(file_path)
            text = "\n".join(p.text for p in doc.paragraphs)
            return [(1, text)]
        except Exception as e:
            logger.error("docx parse failed %s: %s", file_path, e)
            return []
