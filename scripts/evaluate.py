"""检索效果评估脚本（对应阶段十：RAG 检索效果评估）。

功能：
1. 内置示例数据集（无需外部数据即可跑通）。
2. 支持加载自定义 JSON 数据集（--dataset 指定）。
3. 输出 Recall@K、MRR、Hit@K、NDCG@K 指标。
4. 对比「纯向量检索」 vs 「混合检索（向量+BM25+RRF）」效果。

用法：
    # 使用内置示例数据集
    USE_MOCK=true python scripts/evaluate.py

    # 使用自定义数据集
    USE_MOCK=true python scripts/evaluate.py --dataset /path/to/eval.json

自定义数据集 JSON 格式：
[
    {
        "question": "采购合同超过500万元需要审核吗？",
        "relevant_keywords": ["500万", "法务审核"],   # 命中的判定词
        "relevant_ids": ["doc_001_3"]                 # 可选：精确 chunk id
    }
]

指标说明：
- Hit@K：top-K 中是否至少命中一条相关（0/1 求平均）。
- MRR：首个相关文档排名倒数的平均值。
- NDCG@K：考虑相关文档排名的折损累计增益。

注意：内置示例数据集用「相关关键词」近似标注（无人工标注的 chunk id），
适合验证检索链路与切片质量；真实 Recall@K 需用带 relevant_ids 的标准数据集。
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.environ.setdefault("USE_MOCK", "true")
os.environ.setdefault("EMBEDDING_PROVIDER", "mock")
os.environ.setdefault("LLM_PROVIDER", "mock")

from app.document.pipeline import DocumentPipeline  # noqa: E402
from app.rag.retriever import RAGRetriever  # noqa: E402

SAMPLE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "knowledge_base", "sample", "合同管理制度.md"
)

# 内置示例数据集：问题 -> 相关关键词（也可用 relevant_ids 精确匹配）
BUILTIN_TEST_SET = [
    {"question": "采购合同超过500万元需要审核吗？", "relevant_keywords": ["500万", "法务"]},
    {"question": "哪些合同需要法务审核？", "relevant_keywords": ["法务", "审核"]},
    {"question": "供应商付款周期限制是多少？", "relevant_keywords": ["付款", "周期"]},
    {"question": "技术服务合同知识产权怎么约定？", "relevant_keywords": ["知识产权", "技术服务"]},
    {"question": "合同审批流程由哪个部门负责？", "relevant_keywords": ["审批", "部门"]},
]


def _is_relevant(doc: dict, item: dict) -> bool:
    """判断文档是否相关：优先精确 id 匹配，否则关键词匹配。"""
    relevant_ids = item.get("relevant_ids")
    if relevant_ids:
        if doc.get("id") in relevant_ids:
            return True
        # 若提供了 ids 则只按 id 判定
        return False
    keywords = item.get("relevant_keywords", [])
    content = doc.get("content", "")
    return any(k in content for k in keywords)


def _dcg(rels: list) -> float:
    """折损累计增益。"""
    return sum((2 ** rel - 1) / math.log2(i + 2) for i, rel in enumerate(rels))


def _ndcg_at_k(docs: list, item: dict, k: int) -> float:
    rels = [1 if _is_relevant(d, item) else 0 for d in docs[:k]]
    dcg = _dcg(rels)
    ideal = sorted(rels, reverse=True)
    idcg = _dcg(ideal)
    return dcg / idcg if idcg > 0 else 0.0


def evaluate(test_set: list, k: int = 5, compare_hybrid: bool = True) -> dict:
    """执行评估，返回指标字典。"""
    # 入库
    DocumentPipeline().process(
        SAMPLE_FILE, "doc_eval_001", "合同管理制度.md", "company_policy", "V3.0"
    )
    retriever = RAGRetriever()

    metrics = {"n": len(test_set)}
    for mode in (["vector", "hybrid"] if compare_hybrid else ["hybrid"]):
        hit = mrr = ndcg = 0.0
        for item in test_set:
            question = item["question"]
            docs = retriever.retrieve(question, top_k=k, mode=mode)

            # 相关判定（0/1：是否命中相关文档）
            relevant_found = 1 if any(_is_relevant(d, item) for d in docs) else 0

            # Hit@K
            hit += relevant_found

            # MRR
            for rank, d in enumerate(docs, start=1):
                if _is_relevant(d, item):
                    mrr += 1.0 / rank
                    break

            # NDCG@K
            ndcg += _ndcg_at_k(docs, item, k)

        n = len(test_set)
        metrics[mode] = {
            f"Hit@{k}": hit / n,
            "MRR": mrr / n,
            f"NDCG@{k}": ndcg / n,
        }

    return metrics


def _print_metrics(metrics: dict, k: int):
    print("=" * 56)
    print(f"评测样本数：{metrics['n']}，K={k}")
    print("=" * 56)
    for mode in ["vector", "hybrid"]:
        if mode not in metrics:
            continue
        m = metrics[mode]
        label = "混合检索(向量+BM25+RRF)" if mode == "hybrid" else "纯向量检索"
        print(f"\n【{label}】")
        print(f"  Hit@{k}    = {m[f'Hit@{k}']:.2%}")
        print(f"  MRR        = {m['MRR']:.3f}")
        print(f"  NDCG@{k}    = {m[f'NDCG@{k}']:.3f}")
    print("=" * 56)


def main():
    parser = argparse.ArgumentParser(description="RAG 检索效果评估")
    parser.add_argument("--dataset", type=str, default=None,
                        help="自定义数据集 JSON 路径")
    parser.add_argument("--k", type=int, default=5, help="top-K（默认 5）")
    parser.add_argument("--no-compare", action="store_true",
                        help="不做纯向量 vs 混合检索对比，仅跑混合检索")
    args = parser.parse_args()

    if args.dataset:
        with open(args.dataset, "r", encoding="utf-8") as f:
            test_set = json.load(f)
        print(f"已加载自定义数据集：{args.dataset}（{len(test_set)} 条）")
    else:
        test_set = BUILTIN_TEST_SET
        print(f"使用内置示例数据集（{len(test_set)} 条）")

    metrics = evaluate(test_set, k=args.k, compare_hybrid=not args.no_compare)
    _print_metrics(metrics, args.k)


if __name__ == "__main__":
    main()
