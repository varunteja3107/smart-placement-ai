
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://smart-placement-ai.vercel.app",from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from rag_engine import search_jobs
from job_sources import fetch_remotive_jobs, fetch_jobicy_jobs, fetch_arbeitnow_jobs
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from database import Base, SessionLocal, engine
from models import ApplicationRecord


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Placement AI API",
    description="Campus placement and career intelligence platform",
    version="0.2.0",
)


# --------------------------------------------------
# CORS CONFIGURATION
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://smart-placement-ai.vercel.app",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


# --------------------------------------------------
# LOCAL DEMO JOBS
# --------------------------------------------------

jobs = [
    {
        "id": "JOB-001",
        "title": "Graduate Software Engineer",
        "company": "TechNova Solutions",
        "location": "Bengaluru",
        "job_type": "Full-time",
        "package": "₹8–12 LPA",
        "skills": ["Python", "DSA", "SQL"],
        "min_cgpa": 7.0,
        "deadline": "2026-11-15",
        "status": "Open",
        "description": (
            "Graduate software engineering position for early-career "
            "candidates with Python, data structures, algorithms and SQL."
        ),
    },
    {
        "id": "JOB-002",
        "title": "AI/ML Engineering Intern",
        "company": "NeuralWorks",
        "location": "Remote",
        "job_type": "Internship",
        "package": "₹25,000/month",
        "skills": ["Python", "Machine Learning", "Pandas"],
        "min_cgpa": 7.5,
        "deadline": "2026-11-20",
        "status": "Open",
        "description": (
            "Internship working with Python, machine learning, Pandas "
            "and data analysis."
        ),
    },
    {
        "id": "JOB-003",
        "title": "Frontend Developer",
        "company": "PixelStack Technologies",
        "location": "Hyderabad",
        "job_type": "Full-time",
        "package": "₹6–9 LPA",
        "skills": ["React", "JavaScript", "CSS"],
        "min_cgpa": 6.5,
        "deadline": "2026-11-25",
        "status": "Open",
        "description": (
            "Frontend development role using React, JavaScript, CSS "
            "and modern web technologies."
        ),
    },
    {
        "id": "JOB-004",
        "title": "Cloud Engineering Associate",
        "company": "CloudBridge",
        "location": "Bengaluru",
        "job_type": "Full-time",
        "package": "₹7–10 LPA",
        "skills": ["Linux", "Networking", "Cloud"],
        "min_cgpa": 7.0,
        "deadline": "2026-12-01",
        "status": "Open",
        "description": (
            "Entry-level cloud engineering role involving Linux, "
            "networking and cloud infrastructure."
        ),
    },
]





# --------------------------------------------------
# APPLICATION REQUEST MODEL
# --------------------------------------------------

class ApplicationCreate(BaseModel):
    job_id: str
    student_name: str = Field(min_length=2, max_length=100)
    student_email: EmailStr
    cgpa: float = Field(ge=0, le=10)


# --------------------------------------------------
# BASIC ROUTES
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Welcome to Smart Placement AI",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "Smart Placement AI API",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/dashboard")
def dashboard():
    return {
        "total_students": 1240,
        "partner_companies": 48,
        "active_jobs": sum(
            job["status"] == "Open" for job in jobs
        ),
        "placement_rate": 86.4,
        "applications": len(applications),
        "recent_activity": [
            {
                "type": "system",
                "message": "Smart Placement AI API is running",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }


# --------------------------------------------------
# LOCAL JOB LISTING
# --------------------------------------------------

@app.get("/api/jobs")
def list_jobs(search: str = ""):
    query = search.strip().casefold()

    if not query:
        return jobs

    return [
        job
        for job in jobs
        if query in job["title"].casefold()
        or query in job["company"].casefold()
        or query in job["location"].casefold()
        or any(
            query in skill.casefold()
            for skill in job["skills"]
        )
    ]


# --------------------------------------------------
# AI SEARCH: LOCAL + EXTERNAL JOBS
# --------------------------------------------------

@app.get("/api/jobs/ai-search")
def ai_search_jobs(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Search job feeds with role-aware technical relevance scoring."""
    import html
    import re
    from job_board_links import get_job_board_links

    query = q.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    query_lower = query.lower()
    query_tokens = set(re.findall(r"[a-zA-Z0-9+#.]+", query_lower))

    # These words describe seniority or generic role intent, not technical skills.
    generic = {
        "a", "an", "and", "at", "for", "find", "in", "job", "jobs",
        "me", "of", "on", "or", "search", "the", "to", "with", "work",
        "opening", "openings", "role", "roles", "developer", "engineer",
        "intern", "internship", "fresher", "junior", "graduate",
        "entry", "level", "senior", "staff", "lead", "remote",
    }

    skill_aliases = {
        "python": ("python",),
        "java": ("java", "spring boot", "spring framework"),
        "javascript": ("javascript", "js", "node.js", "nodejs"),
        "typescript": ("typescript", "node.js", "nodejs"),
        "react": ("react", "react.js", "reactjs"),
        "c++": ("c++", "cpp"),
        "c": (" c ", " c/c++ ", " c developer"),
        "sql": ("sql", "mysql", "postgresql", "sqlite"),
        "django": ("django",),
        "flask": ("flask",),
        "fastapi": ("fastapi",),
        "ai": ("artificial intelligence", " ai ", "machine learning", "llm"),
        "machine": ("machine learning", " ml ", "ml engineer"),
        "learning": ("machine learning", "deep learning"),
        "ml": ("machine learning", " ml ", "deep learning"),
        "data": ("data engineer", "data analyst", "data science"),
        "cloud": ("cloud", "aws", "azure", "gcp"),
        "devops": ("devops", "site reliability", "kubernetes", "terraform"),
        "security": ("cybersecurity", "security engineer", "penetration testing"),
    }

    skill_tokens = query_tokens - generic
    early_career = bool(
        query_tokens & {"intern", "internship", "fresher", "junior", "graduate"}
        or "entry level" in query_lower
    )
    technical_query = bool(skill_tokens)

    candidates = []

    def clean(value):
        value = html.unescape(str(value or ""))
        value = re.sub(r"<[^>]*>", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    def add_candidate(job, source, external=False):
        title = clean(job.get("title"))
        company = clean(job.get("company"))
        skills = clean(job.get("skills"))
        description = clean(
            job.get("description") or job.get("jobDescription")
            or job.get("jobExcerpt") or job.get("summary")
        )
        location = clean(job.get("location") or job.get("jobGeo"))
        job_type = clean(job.get("job_type") or job.get("jobType"))
        level = clean(job.get("level"))

        if not title:
            return

        title_l = title.lower()
        skills_l = skills.lower()
        description_l = description.lower()
        metadata_l = " ".join([job_type, level, location]).lower()
        all_text = " ".join(
            [title_l, skills_l, description_l, metadata_l]
        )
        padded_text = f" {all_text} "

        # Exclude obvious non-technical occupations when technical skills
        # are part of the user's query.
        nontechnical = (
            "marketing", "social media", "people ops", "human resources",
            "customer success", "financial consulting", "controller",
            "sales representative", "recruiter", "copywriter",
            "content marketing", "ad operations",
        )
        technical_role = any(term in title_l for term in (
            "software", "developer", "engineer", "programmer", "technology",
            "technical", "data", "machine learning", "artificial intelligence",
            "devops", "cybersecurity", "security", "cloud", "qa", "quality assurance",
            "it ", "java", "python", "frontend", "front-end", "backend", "back-end",
            "full stack", "full-stack", "embedded",
        ))
        if technical_query and any(term in title_l for term in nontechnical):
            if not technical_role:
                return

        score = 0
        reasons = []
        matched_terms = []

        # Generic words can help identify role type, but cannot carry a result
        # whose technical skills do not match the requested role.
        skill_matches = 0
        for token in sorted(skill_tokens, key=len, reverse=True):
            aliases = skill_aliases.get(token, (token,))
            matches = [
                alias for alias in aliases
                if alias in padded_text
            ]
            if not matches:
                continue

            skill_matches += 1
            matched_terms.append(token)

            if any(alias in f" {title_l} " for alias in matches):
                score += 12
                reasons.append(f"title matches {token}")
            elif any(alias in f" {skills_l} " for alias in matches):
                score += 10
                reasons.append(f"skills match {token}")
            else:
                score += 4
                reasons.append(f"description mentions {token}")

        role_words = query_tokens & {
            "developer", "engineer", "software", "programmer",
            "frontend", "backend", "fullstack", "data", "security",
        }
        role_match = any(word in title_l for word in role_words)
        if role_match:
            score += 5
            reasons.append("job title matches role")

        if early_career:
            if any(word in title_l for word in (
                "intern", "internship", "graduate", "junior", "trainee",
                "entry level", "entry-level", "associate",
            )):
                score += 8
                reasons.append("early-career role")
            if any(word in title_l for word in ("senior", "staff", "principal", "director", "head of")):
                score -= 15
                reasons.append("senior-level title is a weaker fit")

        # Technical queries must match at least one requested skill in the
        # title/skills, or two separate requested skills in the description.
        title_or_skills_match = any(
            alias in f" {title_l} " or alias in f" {skills_l} "
            for token in skill_tokens
            for alias in skill_aliases.get(token, (token,))
        )
        if technical_query and not title_or_skills_match:
            return

        if score <= 0:
            return

        score = max(0, min(100, round(score / max(1, len(skill_tokens) * 12 + 13) * 100, 1)))
        item = dict(job)
        item.update({
            "title": title,
            "company": company or "Company not listed",
            "skills": skills,
            "description": description,
            "location": location,
            "job_type": job_type,
            "source": source,
            "match_score": score,
            "match_reason": "; ".join(dict.fromkeys(reasons[:4])) or "Related role",
            "matched_terms": matched_terms,
            "application_method": "External application" if external else "Platform demo listing",
            "apply_url": (
                job.get("apply_url") or job.get("url") or job.get("jobUrl")
                if external else job.get("apply_url")
            ),
        })
        candidates.append(item)

    for job in jobs:
        if str(job.get("status", "Open")).lower() == "open":
            add_candidate(job, "Smart Placement AI")

    sources = [
        ("Remotive", fetch_remotive_jobs),
        ("Jobicy", fetch_jobicy_jobs),
        ("Arbeitnow", fetch_arbeitnow_jobs),
    ]
    for source, fetcher in sources:
        try:
            for job in fetcher(""):
                add_candidate(job, source, external=True)
        except Exception as exc:
            print(f"Job source {source} failed: {exc}")

    unique = {}
    for item in candidates:
        key = (
            item.get("title", "").casefold(),
            item.get("company", "").casefold(),
        )
        if key not in unique or item["match_score"] > unique[key]["match_score"]:
            unique[key] = item

    results = sorted(
        unique.values(),
        key=lambda item: item["match_score"],
        reverse=True,
    )[:limit]

    return {
        "query": query,
        "count": len(results),
        "sources": sorted({item["source"] for item in results}),
        "results": results,
        "job_board_links": get_job_board_links(query),
    }


# --------------------------------------------------
# APPLICATION SUBMISSION
# --------------------------------------------------

@app.post("/api/applications", status_code=201)
def create_application(payload: ApplicationCreate):
    job = next(
        (item for item in jobs if item["id"] == payload.job_id),
        None,
    )

    if not job or job["status"] != "Open":
        raise HTTPException(
            status_code=404,
            detail="Local job not found or closed",
        )

    if payload.cgpa < job["min_cgpa"]:
        raise HTTPException(
            status_code=400,
            detail=f"This job requires a CGPA of at least {job['min_cgpa']}.",
        )

    email = str(payload.student_email).casefold()

    with SessionLocal() as db:
        duplicate = db.scalar(
            select(ApplicationRecord).where(
                ApplicationRecord.job_id == payload.job_id,
                ApplicationRecord.student_email == email,
            )
        )

        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="You have already applied for this job.",
            )

        application = ApplicationRecord(
            id=str(uuid4()),
            job_id=job["id"],
            job_title=job["title"],
            company=job["company"],
            student_name=payload.student_name.strip(),
            student_email=email,
            cgpa=payload.cgpa,
            status="Applied",
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        db.add(application)

        try:
            db.commit()
            db.refresh(application)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Unable to save this application because of a database conflict.",
            )

        return {
            "id": application.id,
            "job_id": application.job_id,
            "job_title": application.job_title,
            "company": application.company,
            "student_name": application.student_name,
            "student_email": application.student_email,
            "cgpa": application.cgpa,
            "status": application.status,
            "created_at": application.created_at,
        }


@app.get("/api/applications")
def list_applications():
    with SessionLocal() as db:
        records = db.scalars(
            select(ApplicationRecord).order_by(
                ApplicationRecord.created_at.desc()
            )
        ).all()

        return [
            {
                "id": item.id,
                "job_id": item.job_id,
                "job_title": item.job_title,
                "company": item.company,
                "student_name": item.student_name,
                "student_email": item.student_email,
                "cgpa": item.cgpa,
                "status": item.status,
                "created_at": item.created_at,
            }
            for item in records
        ]


# Multi-source RAG endpoints
from fastapi import Query as _RAGQuery
from multi_source_rag import (
    get_integration_status,
    search_multisource_rag,
)


@app.get("/api/integrations/status")
def api_integrations_status():
    return {"integrations": get_integration_status()}


@app.get("/api/rag/search")
def api_multi_source_rag_search(
    query: str = _RAGQuery(..., min_length=2, max_length=200),
    limit: int = _RAGQuery(10, ge=1, le=20),
):
    return search_multisource_rag(query, jobs, limit)


# Google Drive OAuth connector
from google_drive_integration import router as google_drive_router
app.include_router(google_drive_router)


# User-provided data import for local RAG development
from local_data_connector import router as local_data_router
app.include_router(local_data_router)


# Hosted-AI career coach endpoint
from hosted_ai import generate_career_answer


@app.get("/api/rag/answer")
def api_rag_answer(
    query: str = Query(..., min_length=2, max_length=500),
):
    try:
        retrieval = search_multisource_rag(query, jobs, limit=6)
        answer = generate_career_answer(
            query,
            retrieval.get("results", []),
        )

        return {
            "query": query,
            "answer": answer,
            "sources_used": retrieval.get("sources_used", []),
            "results": retrieval.get("results", []),
            "warnings": retrieval.get("warnings", []),
        }
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="The AI Career Coach is temporarily unavailable. Check the backend configuration and API access.",
        )
