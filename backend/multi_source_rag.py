import os
import re
from html import unescape

import requests

from job_sources import fetch_remotive_jobs
from rag_engine import search_documents


def clean_text(value):
    """Remove HTML markup before indexing external descriptions."""
    value = re.sub(r"<[^>]+>", " ", str(value or ""))
    return " ".join(unescape(value).split())


def normalize_job(job, source):
    description = clean_text(job.get("description", ""))

    return {
        "id": str(job.get("id", "")),
        "kind": "job",
        "source": source,
        "title": job.get("title", "Untitled job"),
        "company": job.get("company", "Unknown company"),
        "location": job.get("location", ""),
        "description": description[:4000],
        "content": description[:4000],
        "skills": job.get("skills", []),
        "url": job.get("source_url") or job.get("apply_url") or "",
        "package": job.get("package", "Not disclosed"),
        "published_at": job.get("published_at", ""),
    }


def fetch_github_repositories(query, limit=8):
    """Search public GitHub repository metadata."""
    endpoint = "https://api.github.com/search/repositories"

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "SmartPlacementAI/1.0",
    }

    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params = {
        "q": f"{query.strip()} in:name,description,readme",
        "sort": "updated",
        "order": "desc",
        "per_page": min(max(limit, 1), 10),
    }

    try:
        response = requests.get(
            endpoint,
            headers=headers,
            params=params,
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        # Do not expose API credentials or request headers in error messages.
        print(f"GitHub repository search failed: {type(exc).__name__}")
        return [], "GitHub search was temporarily unavailable."

    documents = []

    for repo in payload.get("items", []):
        topics = repo.get("topics") or []
        description = repo.get("description") or ""

        content = " ".join(
            str(part)
            for part in [
                repo.get("full_name", ""),
                description,
                repo.get("language", ""),
                " ".join(topics),
            ]
            if part
        )

        documents.append({
            "id": f"GITHUB-{repo.get('id')}",
            "kind": "repository",
            "source": "GitHub",
            "title": repo.get("full_name", "GitHub repository"),
            "company": "",
            "location": "",
            "description": description,
            "content": content[:4000],
            "language": repo.get("language") or "",
            "topics": topics,
            "stars": repo.get("stargazers_count", 0),
            "url": repo.get("html_url", ""),
            "updated_at": repo.get("updated_at", ""),
        })

    return documents, None


def search_multisource_rag(query, local_jobs, limit=10):
    """Retrieve and rank relevant documents from several sources."""
    documents = []
    warnings = []

    # Source 1: jobs stored in the current Smart Placement AI backend.
    for job in local_jobs:
        documents.append(normalize_job(job, "Smart Placement AI"))

    # Authorized user-provided exports, stored locally for this development demo.
    try:
        from local_data_connector import load_imported_documents
        documents.extend(load_imported_documents())
    except Exception as exc:
        print(f"Local RAG imports unavailable: {type(exc).__name__}")
        warnings.append("Imported files were temporarily unavailable.")

    # Source 2: external job listings from Remotive.
    try:
        remote_jobs = fetch_remotive_jobs(query)
        documents.extend(
            normalize_job(job, "Remotive")
            for job in remote_jobs
        )
    except Exception as exc:
        print(f"Remotive integration failed: {type(exc).__name__}")
        warnings.append("Remotive search was temporarily unavailable.")

    # Source 3: public GitHub repository metadata.
    github_documents, github_warning = fetch_github_repositories(query)
    documents.extend(github_documents)

    if github_warning:
        warnings.append(github_warning)

    if not documents:
        return {
            "query": query,
            "count": 0,
            "sources_used": [],
            "results": [],
            "warnings": warnings,
        }

    ranked = search_documents(query, documents, limit=limit)

    return {
        "query": query,
        "count": len(ranked),
        "sources_used": sorted({
            item.get("source", "Unknown")
            for item in documents
        }),
        "results": ranked,
        "warnings": warnings,
    }


def get_integration_status():
    """Report setup readiness without revealing credentials."""
    google_configured = bool(
        os.getenv("GOOGLE_CLIENT_ID")
        and os.getenv("GOOGLE_CLIENT_SECRET")
    )

    linkedin_configured = bool(
        os.getenv("LINKEDIN_CLIENT_ID")
        and os.getenv("LINKEDIN_CLIENT_SECRET")
    )

    naukri_feed_configured = bool(
        os.getenv("NAUKRI_FEED_URL")
        or os.getenv("NAUKRI_API_URL")
    )

    return [
        {
            "source": "Smart Placement AI",
            "state": "built_in",
            "details": "Current local job listings.",
        },
        {
            "source": "Remotive",
            "state": "connector_enabled",
            "details": "Public job-search connector; availability depends on the external service.",
        },
        {
            "source": "GitHub",
            "state": "public_search_enabled",
            "details": "Searches public repository metadata. Private repositories are not connected.",
        },
        {
            "source": "Google Drive",
            "state": (
                "credentials_present_flow_needed"
                if google_configured
                else "oauth_setup_needed"
            ),
            "details": "OAuth flow and selected-file access still need to be implemented.",
        },
        {
            "source": "Gmail",
            "state": (
                "credentials_present_flow_needed"
                if google_configured
                else "oauth_setup_needed"
            ),
            "details": "OAuth flow, limited email scopes and authorized message retrieval still need to be implemented.",
        },
        {
            "source": "LinkedIn",
            "state": (
                "credentials_present_access_unverified"
                if linkedin_configured
                else "oauth_and_api_access_needed"
            ),
            "details": "OAuth credentials alone do not establish permission to access restricted LinkedIn APIs.",
        },
        {
            "source": "Naukri",
            "state": (
                "feed_configured_needs_validation"
                if naukri_feed_configured
                else "authorized_feed_needed"
            ),
            "details": "An authorized feed/API adapter must be configured and tested.",
        },
    ]
