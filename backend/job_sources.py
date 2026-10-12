
import re
import requests

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"

# Reject roles that are clearly senior or managerial.
SENIOR_TITLE_TERMS = [
    "senior",
    "staff engineer",
    "principal",
    "lead engineer",
    "director",
    "vice president",
    "head of ",
    "engineering manager",
    "technical manager",
]

# Technical roles relevant to a computer science student.
TECHNICAL_TITLE_TERMS = [
    "software engineer",
    "software developer",
    "developer",
    "programmer",
    "python",
    "machine learning",
    "artificial intelligence",
    "data analyst",
    "data scientist",
    "data engineer",
    "frontend",
    "front-end",
    "backend",
    "back-end",
    "full stack",
    "web developer",
    "cloud engineer",
    "devops",
    "cybersecurity",
    "security engineer",
    "qa engineer",
    "quality assurance",
    "test engineer",
    "it support",
    "network engineer",
]

# Nontechnical roles to exclude even if their descriptions mention Python.
UNRELATED_TITLE_TERMS = [
    "sales",
    "account executive",
    "recruiter",
    "copywriter",
    "freelance writer",
    "content writer",
    "office assistant",
    "customer service",
    "customer support",
    "service desk",
    "business development",
]

EARLY_CAREER_TERMS = [
    "intern",
    "internship",
    "graduate",
    "new grad",
    "entry level",
    "entry-level",
    "junior",
    "fresher",
    "trainee",
    "apprentice",
    "early career",
]


def fetch_remotive_jobs(search=""):
    """Fetch and filter external technical job listings."""
    params = {"search": search.strip()} if search.strip() else {}

    try:
        response = requests.get(
            REMOTIVE_URL,
            params=params,
            timeout=15,
            headers={"User-Agent": "SmartPlacementAI/1.0"},
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"Remotive request failed: {exc}")
        return []

    results = []

    for item in payload.get("jobs", []):
        title = item.get("title") or "Untitled role"
        company = item.get("company_name") or "Unknown company"
        description = item.get("description") or ""
        tags = item.get("tags") or []

        title_lower = title.casefold()
        description_text = re.sub(
            r"<[^>]+>", " ", description
        ).casefold()

        # Filter based on the job title, not every word in the description.
        if any(term in title_lower for term in SENIOR_TITLE_TERMS):
            continue

        if any(term in title_lower for term in UNRELATED_TITLE_TERMS):
            continue

        if not any(term in title_lower for term in TECHNICAL_TITLE_TERMS):
            continue

        # Exclude explicit experience requirements above two years.
        experience_patterns = [
            r"\bminimum of\s+[3-9]\s+years",
            r"\bat least\s+[3-9]\s+years",
            r"\b[3-9]\+\s+years of experience",
            r"\b[3-9]\s+years of experience required",
            r"\b[3-9]\s+years experience required",
        ]

        if any(
            re.search(pattern, description_text)
            for pattern in experience_patterns
        ):
            continue

        is_early_career = any(
            term in title_lower for term in EARLY_CAREER_TERMS
        )

        results.append({
            "id": f"REMOTIVE-{item.get('id')}",
            "title": title,
            "company": company,
            "location": (
                item.get("candidate_required_location") or "Remote"
            ),
            "job_type": item.get("job_type") or "Not specified",
            "package": item.get("salary") or "Not disclosed",
            "skills": [str(tag) for tag in tags],
            "min_cgpa": None,
            "deadline": None,
            "published_at": item.get("publication_date") or "",
            "status": "Open",
            "description": description,
            "source": "Remotive",
            "source_url": item.get("url") or "",
            "early_career_hint": is_early_career,
        })

    return results

