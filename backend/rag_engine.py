from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_model():
    """Load the embedding model once and reuse it."""
    return SentenceTransformer(MODEL_NAME)


def job_text(job):
    """Convert a job record into searchable text."""
    skills = ", ".join(job.get("skills", []))

    return " ".join(
        str(value)
        for value in [
            job.get("title", ""),
            job.get("company", ""),
            job.get("location", ""),
            job.get("job_type", ""),
            job.get("description", ""),
            skills,
        ]
        if value
    )


def search_jobs(query, jobs, limit=10):
    """Rank jobs by semantic similarity to a natural-language query."""
    query = query.strip()

    if not query or not jobs:
        return []

    model = get_model()

    descriptions = [job_text(job) for job in jobs]

    embeddings = model.encode(
        [query] + descriptions,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    query_vector = embeddings[0]
    job_vectors = embeddings[1:]

    scores = np.dot(job_vectors, query_vector)

    ranked_indices = np.argsort(scores)[::-1][:limit]

    results = []

    for index in ranked_indices:
        job = dict(jobs[int(index)])
        score = float(scores[int(index)])

        job["match_score"] = round(
            max(0.0, min(100.0, score * 100)), 1
        )
        job["match_reason"] = (
            "Ranked using semantic similarity between your search "
            "and the job title, skills, location, and description."
        )

        results.append(job)

    return results


def document_text(document):
    """Convert a normalized source record into searchable text."""
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
    """Rank mixed-source documents using semantic similarity."""
    query = query.strip()

    if not query or not documents:
        return []

    limit = max(1, min(int(limit), 25))
    model = get_model()

    descriptions = [
        document_text(document) or str(document.get("id", ""))
        for document in documents
    ]

    embeddings = model.encode(
        [query] + descriptions,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    scores = np.dot(embeddings[1:], embeddings[0])
    ranked_indices = np.argsort(scores)[::-1][:limit]

    results = []

    for index in ranked_indices:
        document = dict(documents[int(index)])
        score = float(scores[int(index)])

        document["match_score"] = round(
            max(0.0, min(100.0, score * 100)), 1
        )
        document["match_reason"] = (
            "Ranked by semantic similarity to your query."
        )

        results.append(document)

    return results
