import os
import sys
import json
import argparse
import httpx
# 添加config路径
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.."))
sys.path.insert(0, ROOT)
from config import settings

# RAG 接口地址
RAG_ENDPOINT = settings.RAG_API_URL


def parse_args():
    parser = argparse.ArgumentParser(description="Query RAG knowledge base")

    # 位置参数（主要参数）
    parser.add_argument(
        "question_positional",
        type=str,
        nargs="?",
        help="Question to ask the RAG system (positional argument)"
    )

    # 兼容旧格式的参数
    parser.add_argument(
        "--query",
        type=str,
        help="Query parameter (alternative to positional question)"
    )
    parser.add_argument(
        "--question",
        type=str,
        help="Question parameter (alternative to positional question)"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of top communities to retrieve"
    )

    args = parser.parse_args()

    # 优先级：positional > --question > --query
    if args.question_positional:
        final_question = args.question_positional
    elif args.question:
        final_question = args.question
    elif args.query:
        final_question = args.query
    else:
        final_question = None

    return argparse.Namespace(
        question=final_question,
        top_k=args.top_k
    )


def query_rag(question: str, top_k: int = 10) -> dict:
    payload = {
        "question": question,
        "top_k_communities": top_k
    }

    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            RAG_ENDPOINT,
            headers={"Content-Type": "application/json"},
            json=payload
        )

        response.raise_for_status()
        return response.json()


def main():
    args = parse_args()

    # 检查问题是否提供
    if not args.question:
        print("❌ Error: No question provided.")
        print("Usage: python query.py \"Your question here\"")
        print("   or: python query.py --query \"Your question here\"")
        print("   or: python query.py --question \"Your question here\"")
        sys.exit(1)

    try:
        result = query_rag(args.question, args.top_k)

        print("=" * 60)
        print("📘 RAG Query Result")
        print("=" * 60)
        print(f"❓ Question:\n{args.question}\n")

        if result.get("success"):
            print("✅ Answer:\n")
            print(result.get("answer", ""))
            if "processing_time" in result:
                print(f"\n⏱ Processing Time: {result['processing_time']:.2f}s")
        else:
            print("❌ Query failed")
            print(json.dumps(result, ensure_ascii=False, indent=2))

    except httpx.HTTPError as e:
        print("❌ HTTP request failed")
        print(str(e))
        sys.exit(1)

    except Exception as e:
        print("❌ Unexpected error")
        print(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
