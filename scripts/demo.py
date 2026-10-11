"""本地验证脚本：在 Mock 模式下端到端跑通「入库 → 检索 → 问答」。

用法（无需 Milvus/Neo4j/LLM，本地即可运行）：
    USE_MOCK=true python scripts/demo.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

os.environ.setdefault("USE_MOCK", "true")
os.environ.setdefault("EMBEDDING_PROVIDER", "mock")
os.environ.setdefault("LLM_PROVIDER", "mock")

from app.core.config import settings  # noqa: E402
from app.document.pipeline import DocumentPipeline  # noqa: E402
from app.services.chat_service import ChatService  # noqa: E402

SAMPLE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "knowledge_base", "sample", "合同管理制度.md"
)


def main():
    print("=" * 60)
    print("企业法务知识库智能问答系统 —— Mock 模式端到端验证")
    print("=" * 60)

    # 1. 文档入库
    print("\n[1] 文档入库（解析 → 切片 → 向量化 → 图谱）...")
    pipeline = DocumentPipeline()
    result = pipeline.process(
        file_path=SAMPLE_FILE,
        document_id="doc_demo_001",
        document_name="合同管理制度.md",
        document_type="company_policy",
        version="V3.0",
    )
    print(f"    入库结果: {result}")

    # 2. 问答
    print("\n[2] 智能问答测试...")
    chat = ChatService()
    questions = [
        "采购合同超过500万元需要法务审核吗？",
        "哪些合同需要法务审核？",
        "技术服务合同有哪些知识产权风险？",
    ]
    for q in questions:
        resp = chat.ask(q)
        print(f"\n  Q: {q}")
        print(f"  A: {resp['answer']}")
        print(f"  来源数: {len(resp['sources'])}, 可信度: {resp['confidence']}, 意图: {resp['intent']}")
        for s in resp["sources"]:
            print(f"    - {s['document_name']} {s['chapter']} {s['article']} 第{s['page']}页")

    print("\n" + "=" * 60)
    print("验证完成 ✅")
    print("=" * 60)


if __name__ == "__main__":
    main()
