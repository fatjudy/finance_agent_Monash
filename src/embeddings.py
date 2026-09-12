from __future__ import annotations
import numpy as np
from sentence_transformers import SentenceTransformer
from src.models import Chunk, RetrievedChunk

_MODEL: SentenceTransformer | None = None


def get_model(name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(name)
    return _MODEL


def embed(texts: list[str]) -> np.ndarray:
    model = get_model()
    return model.encode(texts, normalize_embeddings=True)


class EmbeddingIndex:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.vectors = embed([c.text for c in chunks])   # shape (N, 384)


def retrieve_semantic(query: str, index: EmbeddingIndex, top_k: int = 5) -> list[RetrievedChunk]:
    query_vec = embed([query])[0]                        # shape (384,)
    scores = index.vectors @ query_vec                   # cosine sim per chunk, shape (N,)
    order = np.argsort(scores)[::-1][:top_k]             # indices of top_k, high→low
    return [
        RetrievedChunk(
            text=index.chunks[i].text,
            relevance=max(0.0, float(scores[i])),
            metadata=index.chunks[i].metadata,
        )
        for i in order
    ]