from __future__ import annotations
import re
from pathlib import Path
import frontmatter
from src.models import Chunk, ChunkMetadata
from src.models import Chunk, ChunkMetadata, RetrievedChunk

CORPUS_DIR = Path(__file__).parent.parent / "data" / "finance_rag_corpus"


def load_corpus(corpus_dir: Path = CORPUS_DIR) -> list[frontmatter.Post]:
    posts = []
    for path in sorted(corpus_dir.glob("*.md")):
        post = frontmatter.load(path)
        posts.append(post)
    return posts

def build_metadata(post: frontmatter.Post, section: str | None = None) -> ChunkMetadata:
    m = post.metadata
    return ChunkMetadata(
        document_id=m["document_id"],
        title=m["title"],
        version=str(m["version"]),          # YAML may read 3.2 as a float — force to str
        status=m["status"],
        classification=m.get("classification"),
        effective_date=m.get("effective_date"),
        section=section,
    )

def chunk_document(post: frontmatter.Post) -> list[Chunk]:
    chunks: list[Chunk] = []
    heading: str | None = None
    lines: list[str] = []

    for line in post.content.splitlines():
        if line.startswith("## "):                       # a new section starts
            if lines:
                chunks.append(Chunk(text="\n".join(lines).strip(),
                                    metadata=build_metadata(post, heading)))
            heading = line[3:].strip()                   # text after "## "
            lines = [line]
        else:
            lines.append(line)

    if lines:                                            # flush the last section
        chunks.append(Chunk(text="\n".join(lines).strip(),
                            metadata=build_metadata(post, heading)))

    return [c for c in chunks if c.text]                 # drop empties


def build_index(corpus_dir: Path = CORPUS_DIR) -> list[Chunk]:
    chunks: list[Chunk] = []
    for post in load_corpus(corpus_dir):
        chunks.extend(chunk_document(post))
    return chunks

STOPWORDS = {"the", "a", "an", "and", "or", "of", "to", "for", "in", "on",
             "is", "are", "be", "must", "by", "with", "that", "this", "no"}


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


def score_chunk(query_terms: set[str], chunk: Chunk) -> float:
    if not query_terms:
        return 0.0
    matched = query_terms & tokenize(chunk.text)
    return len(matched) / len(query_terms)


def retrieve(query: str, index: list[Chunk] | None = None, top_k: int = 5) -> list[RetrievedChunk]:
    if index is None:
        index = build_index()
    query_terms = tokenize(query)
    hits = []
    for chunk in index:
        score = score_chunk(query_terms, chunk)
        if score > 0:
            hits.append(RetrievedChunk(text=chunk.text, relevance=score, metadata=chunk.metadata))
    hits.sort(key=lambda rc: rc.relevance, reverse=True)
    return hits[:top_k]