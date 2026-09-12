from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field
from src.models import Chunk, RetrievedChunk
from src.rag import build_index, retrieve
from src.embeddings import EmbeddingIndex, retrieve_semantic


class RetrievalMode(str, Enum):
    LEXICAL = "lexical"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class RetrieveInput(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=20)
    mode: RetrievalMode = RetrievalMode.HYBRID    

class RetrieveOutput(BaseModel):
    query: str
    mode: RetrievalMode
    chunks: list[RetrievedChunk]


_lexical_index: list[Chunk] | None = None
_embedding_index: EmbeddingIndex | None = None


def _get_lexical() -> list[Chunk]:
    global _lexical_index
    if _lexical_index is None:
        _lexical_index = build_index()
    return _lexical_index


def _get_embedding() -> EmbeddingIndex:
    global _embedding_index
    if _embedding_index is None:
        _embedding_index = EmbeddingIndex(_get_lexical())
    return _embedding_index


def hybrid_retrieve(query: str, top_k: int = 5, pool: int = 10, k: int = 60) -> list[RetrievedChunk]:
    lexical_hits = retrieve(query, _get_lexical(), pool)
    semantic_hits = retrieve_semantic(query, _get_embedding(), pool)

    rrf_scores: dict[tuple, float] = {}
    chunk_by_key: dict[tuple, RetrievedChunk] = {}

    for ranked_list in (lexical_hits, semantic_hits):
        for rank, rc in enumerate(ranked_list):
            key = (rc.metadata.document_id, rc.metadata.section, rc.text)
            rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            chunk_by_key[key] = rc

    best_keys = sorted(rrf_scores, key=lambda key: rrf_scores[key], reverse=True)[:top_k]

    return [
        RetrievedChunk(
            text=chunk_by_key[key].text,
            relevance=rrf_scores[key],
            metadata=chunk_by_key[key].metadata,
        )
        for key in best_keys
    ]

def retrieve_finance_documents(payload: RetrieveInput) -> RetrieveOutput:
    if payload.mode is RetrievalMode.LEXICAL:
        chunks = retrieve(payload.query, _get_lexical(), payload.top_k)
    elif payload.mode is RetrievalMode.SEMANTIC:
        chunks = retrieve_semantic(payload.query, _get_embedding(), payload.top_k)
    else:  # HYBRID
        chunks = hybrid_retrieve(payload.query, payload.top_k)
    return RetrieveOutput(query=payload.query, mode=payload.mode, chunks=chunks)