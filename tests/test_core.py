"""单元测试：文档切片、清洗、检索、图谱、问答（Mock 模式）。

运行：
    USE_MOCK=true pytest tests/ -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("USE_MOCK", "true")
os.environ.setdefault("EMBEDDING_PROVIDER", "mock")
os.environ.setdefault("LLM_PROVIDER", "mock")

from app.document.cleaner import TextCleaner  # noqa: E402
from app.document.splitter import LegalSplitter  # noqa: E402
from app.graph.graph_query import GraphService  # noqa: E402
from app.graph.graph_store import get_graph_store  # noqa: E402
from app.rag.hybrid_search import BM25Retriever, Reranker, rrf_fusion  # noqa: E402
from app.utils.rate_limit import RateLimiter  # noqa: E402
from app.utils.retry import CircuitBreaker, retry_call  # noqa: E402


def test_cleaner_removes_page_footer():
    cleaner = TextCleaner()
    text = "第五章 合同审批流程\n第5页\n公司内部文件\n第一条 合同金额超过500万元需要法务审核"
    result = cleaner.clean(text)
    assert "第5页" not in result
    assert "公司内部文件" not in result
    assert "第一条" in result


def test_splitter_chapter_article():
    splitter = LegalSplitter()
    pages = [(1, "第五章 合同审批管理\n第一条 合同金额超过500万元需要法务审核\n第二条 合同签署前必须完成审批")]
    chunks = splitter.split(pages)
    assert len(chunks) >= 2
    assert chunks[0].chapter == "第五章 合同审批管理"
    assert chunks[0].article == "第一条"


def test_rrf_fusion():
    vec = [{"id": "a", "score": 0.9}, {"id": "b", "score": 0.8}]
    kw = [{"id": "b", "score": 3.0}, {"id": "c", "score": 2.0}]
    fused = rrf_fusion(vec, kw)
    ids = [d["id"] for d in fused]
    assert "a" in ids and "b" in ids and "c" in ids


def test_graph_relation():
    store = get_graph_store()
    store.upsert_node("ContractType", "采购合同")
    store.upsert_node("Process", "法务审核")
    store.add_relation("ContractType", "采购合同", "NEED", "Process", "法务审核")
    related = store.find_related("采购合同")
    assert any(r["relation"] == "NEED" for r in related)


def test_bm25_index_and_search():
    bm25 = BM25Retriever()
    bm25.add([
        {"id": "d1", "content": "采购合同金额超过500万元需要法务审核", "document_id": "doc1"},
        {"id": "d2", "content": "劳动合同签订期限规定", "document_id": "doc1"},
        {"id": "d3", "content": "技术服务合同知识产权归属", "document_id": "doc2"},
    ])
    assert bm25.count() == 3
    results = bm25.search("采购合同 500万", 3)
    assert len(results) > 0
    # 关键词"采购合同"应排在前面
    assert "采购合同" in results[0]["content"]

    # 按文档删除
    bm25.remove_by_document("doc1")
    assert bm25.count() == 1


def test_reranker_fallback():
    reranker = Reranker()
    docs = [{"id": "a", "content": "x", "score": 0.5},
            {"id": "b", "content": "y", "score": 0.9}]
    ranked = reranker.rerank("query", docs)
    # mock 模式降级为按 score 排序
    assert ranked[0]["id"] == "b"


def test_graph_entity_linking():
    service = GraphService()
    # mock 模式降级到规则词典
    entities = service.extract_entities("哪些合同需要法务审核？")
    assert "法务审核" in entities
    # 空问题返回空列表
    assert service.extract_entities("今天天气怎么样") == []


def test_retry_call():
    counter = {"n": 0}

    def flaky():
        counter["n"] += 1
        if counter["n"] < 3:
            raise ConnectionError("temp failure")
        return "ok"

    result = retry_call(flaky, max_retries=5, base_delay=0.01)
    assert result == "ok"
    assert counter["n"] == 3


def test_circuit_breaker():
    breaker = CircuitBreaker("test", failure_threshold=2, cooldown=30.0)

    def fail():
        raise ConnectionError("down")

    for _ in range(2):
        try:
            breaker(fail)
        except ConnectionError:
            pass
    # 达到阈值后进入 open，快速失败
    try:
        breaker(fail)
        assert False, "should raise CircuitOpenError"
    except CircuitBreaker.CircuitOpenError:
        pass


def test_rate_limiter():
    rl = RateLimiter(max_requests=3, window_seconds=60)
    assert all(rl.allow("u1") for _ in range(3))
    assert rl.allow("u1") is False  # 第 4 次拒绝
    assert rl.allow("u2") is True   # 其他用户不受影响
