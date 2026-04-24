from fastapi import HTTPException, status
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters
from loguru import logger

from app.core.config import get_settings
from app.integrations.groq import get_groq_client
from app.integrations.llamaindex import get_vector_index


def _node_text(node: object) -> str:
    if hasattr(node, "get_content"):
        return node.get_content() or ""
    if hasattr(node, "text"):
        return node.text or ""
    return ""


def _build_sources(nodes: list[object]) -> list[dict[str, str | int]]:
    dedup: set[tuple[str, int]] = set()
    sources: list[dict[str, str | int]] = []

    for node_with_score in nodes:
        node = getattr(node_with_score, "node", node_with_score)
        metadata = getattr(node, "metadata", {}) or {}

        document_id = str(metadata.get("document_id", "unknown"))
        filename = str(metadata.get("filename", "unknown"))
        chunk_index = int(metadata.get("chunk_index", 0))
        key = (document_id, chunk_index)
        if key in dedup:
            continue
        dedup.add(key)

        snippet = _node_text(node).strip().replace("\n", " ")[:280]
        sources.append(
            {
                "document_id": document_id,
                "filename": filename,
                "chunk_index": chunk_index,
                "snippet": snippet,
            }
        )

    return sources


def ask_question(question: str, user_id: str) -> dict[str, object]:
    settings = get_settings()

    try:
        index = get_vector_index()
        retriever = index.as_retriever(
            similarity_top_k=settings.retrieval_top_k,
            filters=MetadataFilters(
                filters=[MetadataFilter(key="user_id", value=user_id)],
            ),
        )
        retrieved_nodes = retriever.retrieve(question)
    except Exception as exc:
        logger.exception("Retrieval failed for user {}: {}", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to retrieve relevant context.",
        ) from exc

    if not retrieved_nodes:
        return {
            "answer": "I could not find relevant information in your uploaded documents.",
            "sources": [],
            "retrieved_chunks": 0,
        }

    context_blocks: list[str] = []
    for idx, node_with_score in enumerate(retrieved_nodes, start=1):
        node = getattr(node_with_score, "node", node_with_score)
        context_blocks.append(f"[{idx}] {_node_text(node)}")

    prompt = (
        "You are LUMI, a source-grounded assistant. Answer only from provided context. "
        "If context is insufficient, say that clearly. Keep answer concise and factual.\n\n"
        f"Question:\n{question}\n\n"
        f"Context:\n{'\n\n'.join(context_blocks)}"
    )

    try:
        groq = get_groq_client()
        completion = groq.chat.completions.create(
            model=settings.groq_model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        answer = completion.choices[0].message.content or "No answer generated."
    except Exception as exc:
        logger.exception("Groq generation failed: {}", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to generate response from language model.",
        ) from exc

    sources = _build_sources(retrieved_nodes)
    return {
        "answer": answer,
        "sources": sources,
        "retrieved_chunks": len(retrieved_nodes),
    }
