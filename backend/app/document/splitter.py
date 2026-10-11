"""Chunk 切片模块：基于「章节 + 条款」优先级的法务文档切片策略。"""
import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.core.config import settings

# 章节标题：第X章 / 第X部分 / 一、二、
_CHAPTER_RE = re.compile(
    r"^(第[一二三四五六七八九十百0-9]+[章节部分篇]|"
    r"[一二三四五六七八九十]+、|"
    r"\d+(\.\d+)*\s+[^\d])"
)
# 条款：第一条 / 第X条 / 1.1 / （一）
_ARTICLE_RE = re.compile(
    r"^(第[一二三四五六七八九十百0-9]+条|"
    r"\d+(\.\d+)*[、.]|"
    r"[（(][一二三四五六七八九十]+[)）])"
)


@dataclass
class Chunk:
    """切片数据对象。"""
    content: str
    chapter: str = ""
    article: str = ""
    page: int = 0


@dataclass
class SplitResult:
    chunks: List[Chunk] = field(default_factory=list)


class LegalSplitter:
    """法务文档切片器：按 章节 → 条款 → 段落 → 长度 优先级切分。"""

    def split(self, pages: List[tuple]) -> List[Chunk]:
        chunks: List[Chunk] = []
        current_chapter = ""
        buffer: List[str] = []
        buffer_article = ""

        def flush_buffer(page: int):
            nonlocal buffer, buffer_article
            if not buffer:
                return
            text = "\n".join(buffer)
            # 按长度二次切分
            for piece in self._split_long(text):
                chunks.append(Chunk(
                    content=piece,
                    chapter=current_chapter,
                    article=buffer_article,
                    page=page,
                ))
            buffer = []
            buffer_article = ""

        for page_num, text in pages:
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue

                # 章节标题
                if _CHAPTER_RE.match(line) and len(line) < 50:
                    flush_buffer(page_num)
                    current_chapter = line
                    continue

                # 条款标题（提取条款编号，内容保留完整文本）
                if _ARTICLE_RE.match(line) and len(line) < 50:
                    flush_buffer(page_num)
                    m = _ARTICLE_RE.match(line)
                    buffer_article = m.group(0).strip()
                    buffer = [line]
                    continue

                buffer.append(line)
            # 每页结束 flush，保留页码
            flush_buffer(page_num)

        return chunks

    def _split_long(self, text: str) -> List[str]:
        """超长文本按字符长度切分，带重叠。"""
        max_len = settings.CHUNK_SIZE
        overlap = settings.CHUNK_OVERLAP
        if len(text) <= max_len:
            return [text]
        pieces = []
        start = 0
        while start < len(text):
            end = min(start + max_len, len(text))
            pieces.append(text[start:end])
            if end == len(text):
                break
            start = end - overlap
        return pieces
