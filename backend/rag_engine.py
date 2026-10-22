import os
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")

EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
)


@lru_cache(maxsize=1)
def get_client():
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def get_embeddings(texts):
    if not texts:
        return np.empty((0, 0), dtype=np.float32)

    response = get_client().embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )

    return np.array(
        [item.embedding for item in response.data],
        dtype=np.float32,
    )


def job_text(job):
    skills = job.get("skills", [])
    if not isinstance(skills, (list, tuple, set)):
        skills = [skills] if skills else []

    return " ".join(
        str(value)
        for value in [
            job.get("title", ""),
            job.get("company", ""),
            job.get("location", ""),
            job.get("job_type", ""),
            job.get("description", ""),
            ", ".join(str(skill) for skill in skills),
        ]
        if value
    )


def _local_rank(query, texts, limit):
    """Rank text locally without any paid API."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
        )
        matrix = vectorizer.fit_transform([query] + texts)
        scores = cosine_similarity(matrix[0:1], matrix[1:]).ravel()

    except (ImportError, ValueError):
        # Built-in fallback if scikit-learn is unavailable or text is empty.
        query_terms = set(re.findall(r"[a-z0-9+#.]+", query.lower()))
        scores = []

        for text in texts:
            words = re.findall(r"[a-z0-9+#.]+", text.lower())
            text_terms = set(words)
            overlap = len(query_terms & text_terms)
            coverage = overlap / max(1, len(query_terms))
            title_bonus = 0.0
            scores.append(min(1.0, coverage + title_bonus))

        scores = np.asarray(scores, dtype=np.float32)

    indices = sorted(
        range(len(scores)),
        key=lambda i: float(scores[i]),
        reverse=True,
    )[:limit]

    return [(int(i), float(scores[i])) for i in indices]


def _rank(query, texts, limit):
    """Prefer hosted embeddings, falling back to local ranking on failure."""
    if not texts:
        return []

    try:
        embeddings = get_embeddings([query] + texts)

        if (
            embeddings.ndim != 2
            or embeddings.shape[0] != len(texts) + 1
            or not np.isfinite(embeddings).all()
        ):
            raise ValueError("Invalid embedding response")

        query_vector = embeddings[0]
        document_vectors = embeddings[1:]

        query_norm = np.linalg.norm(query_vector)
        document_norms = np.linalg.norm(document_vectors, axis=1)
        denominator = document_norms * query_norm

        scores = np.divide(
            document_vectors @ query_vector,
            denominator,
            out=np.zeros(len(texts), dtype=np.float32),
            where=denominator > 0,
        )

        indices = np.argsort(scores)[::-1][:limit]
        return [(int(i), float(scores[i])) for i in indices]

    except Exception as exc:
        # Avoid logging request data, API keys, or response headers.
        print(
            "Hosted embeddings unavailable; using local ranking:",
            type(exc).__name__,
        )
        return _local_rank(query, texts, limit)


def search_jobs(query, jobs, limit=10):
    query = query.strip()
    if not query or not jobs:
        return []

    descriptions = [job_text(job) for job in jobs]
    ranked = _rank(query, descriptions, max(1, int(limit)))
    results = []

    for index, score in ranked:
        job = dict(jobs[index])
        job["match_score"] = round(
            max(0.0, min(100.0, score * 100)), 1
        )
        job["match_reason"] = (
            "Ranked using hosted semantic embeddings."
            if os.getenv("OPENAI_EMBEDDING_MODEL")
            else "Ranked using semantic embeddings when available, "
                 "with local text matching as a fallback."
        )
        results.append(job)

    return results


def document_text(document):
    parts = []

    for key in (
        "title", "name", "company", "location", "kind",
        "source", "description", "content", "text", "language",
    ):
        value = document.get(key)
        if value:
            parts.append(str(value))

    for key in ("skills", "topics"):
        value = document.get(key) or []
        if isinstance(value, (list, tuple, set)):
            parts.extend(str(item) for item in value if item)
        elif value:
            parts.append(str(value))

    return " ".join(parts)


def search_documents(query, documents, limit=10):
    query = query.strip()
    if not query or not documents:
        return []

    limit = max(1, min(int(limit), 25))
    descriptions = [
        document_text(doc) or str(doc.get("id", ""))
        for doc in documents
    ]

    ranked = _rank(query, descriptions, limit)
    results = []

    for index, score in ranked:
        document = dict(documents[index])
        document["match_score"] = round(
            max(0.0, min(100.0, score * 100)), 1
        )
        document["match_reason"] = (
            "Ranked using hosted semantic embeddings when available, "
            "with local text matching as a fallback."
        )
        results.append(document)

    return results
