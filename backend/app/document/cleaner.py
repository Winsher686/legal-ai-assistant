"""文本清洗模块：去除页眉页脚页码、统一空白、处理特殊符号。"""
import re

_PAGE_FOOTER_PATTERNS = [
    re.compile(r"^第\s*[\d一二三四五六七八九十]+\s*页\s*$"),
    re.compile(r"^-\s*\d+\s*-$"),
    re.compile(r"^第\s*\d+\s*页\s*共\s*\d+\s*页\s*$"),
    re.compile(r"^公司内部文件\s*$"),
    re.compile(r"^机密\s*$"),
]


class TextCleaner:
    """文本清洗。"""

    def clean(self, text: str) -> str:
        lines = text.splitlines()
        kept = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 去除页眉页脚
            if any(p.match(line) for p in _PAGE_FOOTER_PATTERNS):
                continue
            # 去除纯分隔线
            if re.fullmatch(r"[-=_]{3,}", line):
                continue
            # 统一空白
            line = re.sub(r"\s+", " ", line)
            kept.append(line)
        return "\n".join(kept)
