"""Retrieval grounding tests. Uses the local embedding model but no LLM/API key."""
import pytest

from src.tools.retrieval import retrieve_finance_documents, RetrieveInput, RetrievalMode


def test_retrieval_returns_grounded_chunks():
    out = retrieve_finance_documents(RetrieveInput(query="duplicate invoice fraud controls", top_k=3))
    assert len(out.chunks) > 0
    top = out.chunks[0]
    assert top.metadata.document_id          # every chunk is citable
    assert 0.0 <= top.relevance <= 1.0       # relevance stays in bounds


def test_topk_bounded():
    with pytest.raises(Exception):
        RetrieveInput(query="x", top_k=999)  # exceeds le=20


def test_empty_query_rejected():
    with pytest.raises(Exception):
        RetrieveInput(query="", top_k=5)


def test_lexical_mode_runs():
    out = retrieve_finance_documents(RetrieveInput(
        query="three-way matching tolerance", top_k=3, mode=RetrievalMode.LEXICAL))
    assert out.mode is RetrievalMode.LEXICAL
