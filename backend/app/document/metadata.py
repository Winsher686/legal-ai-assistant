"""Metadata 生成模块：为每个 Chunk 生成来源元数据，用于检索过滤与引用溯源。"""
from typing import Dict


def build_metadata(document_id: str, document_name: str, document_type: str,
                   version: str, chapter: str, article: str, page: int) -> Dict:
    return {
        "document_id": document_id,
        "document_name": document_name,
        "document_type": document_type,
        "chapter": chapter,
        "article": article,
        "page": page,
        "version": version,
    }
