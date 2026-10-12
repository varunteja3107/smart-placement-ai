
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

from rag_engine import search_jobs
from job_sources import fetch_remotive_jobs
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
    """Search local and external jobs using semantic similarity."""

    query = q.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Search query is required",
        )

    combined_jobs = []

    # Add local demo jobs.
    for job in jobs:
        if job["status"] != "Open":
            continue

        item = dict(job)
        item["source"] = "Smart Placement AI"
        item["source_url"] = ""
        item["application_method"] = "platform"

        combined_jobs.append(item)

    # Fetch external jobs. A remote API failure must not break local search.
    try:
        external_jobs = fetch_remotive_jobs(query)
    except Exception as exc:
        print(f"External job search failed: {exc}")
        external_jobs = []

    # Avoid duplicate title/company combinations.
    seen = {
        (
            item["title"].strip().casefold(),
            item["company"].strip().casefold(),
        )
        for item in combined_jobs
    }

    for job in external_jobs:
        title = job.get("title") or "Untitled role"
        company = job.get("company") or "Unknown company"

        key = (
            title.strip().casefold(),
            company.strip().casefold(),
        )

        if key in seen:
            continue

        seen.add(key)

        item = dict(job)
        item["title"] = title
        item["company"] = company
        item["source"] = "Remotive"
        item["application_method"] = "external"
        item["min_cgpa"] = None
        item["deadline"] = None
        item["apply_url"] = item.get("source_url", "")

        combined_jobs.append(item)

    # Rank local and external jobs together.
    results = search_jobs(
        query,
        combined_jobs,
        limit=limit,
    )

    # Ensure every result has a consistent source and application URL.
    for result in results:
        result.setdefault("source", "Smart Placement AI")
        result.setdefault("application_method", "platform")

        if result.get("source") == "Remotive":
            result["apply_url"] = result.get("source_url", "")
            result["application_method"] = "external"
        else:
            result["apply_url"] = ""

    return {
        "query": query,
        "count": len(results),
        "sources": ["Smart Placement AI", "Remotive"],
        "results": results,
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
