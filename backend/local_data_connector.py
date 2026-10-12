import csv
import io
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent
PRIVATE_DIR = BASE_DIR / ".private"
STORE_FILE = PRIVATE_DIR / "imported_documents.json"

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_RECORDS = 300
ALLOWED_EXTENSIONS = {".txt", ".md", ".csv", ".json"}


def load_imported_documents():
    if not STORE_FILE.exists():
        return []

    try:
        data = json.loads(STORE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def save_imported_documents(documents):
    PRIVATE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    STORE_FILE.write_text(
        json.dumps(documents, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    STORE_FILE.chmod(0o600)


def record_to_document(record, source, filename, index, imported_at):
    if isinstance(record, str):
        content = record
        title = f"{filename} (record {index})"
        url = ""
    elif isinstance(record, dict):
        parts = []
        for key, value in record.items():
            if value is None:
                continue
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            value = str(value).strip()
            if value:
                parts.append(f"{key}: {value}")

        content = "\n".join(parts)
        lower = {str(k).casefold(): v for k, v in record.items()}
        title = next(
            (
                str(lower[k]).strip()
                for k in ("title", "job_title", "subject", "name", "filename")
                if lower.get(k)
            ),
            f"{filename} (record {index})",
        )
        url = next(
            (
                str(lower[k]).strip()
                for k in ("url", "link", "webviewlink", "apply_url", "html_url")
                if lower.get(k)
            ),
            "",
        )
    else:
        content = str(record)
        title = f"{filename} (record {index})"
        url = ""

    content = content.strip()
    if not content:
        return None

    return {
        "id": f"IMPORT-{uuid.uuid4()}",
        "kind": "document",
        "source": source,
        "title": title[:250],
        "company": "",
        "location": "",
        "description": content[:4000],
        "content": content[:4000],
        "url": url,
        "source_file": filename,
        "imported_at": imported_at,
    }


def parse_upload(filename, raw, source, imported_at):
    suffix = Path(filename).suffix.casefold()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Supported files: .txt, .md, .csv and .json",
        )

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File must use UTF-8 text encoding. Export it as UTF-8 and retry.",
        )

    if suffix in {".txt", ".md"}:
        # Split long documents into overlapping searchable chunks.
        chunks = []
        chunk_size = 1800
        stride = 1500
        for start in range(0, len(text), stride):
            chunk = text[start:start + chunk_size].strip()
            if chunk:
                chunks.append(chunk)
            if len(chunks) >= MAX_RECORDS:
                break
        records = [
            {
                "title": f"{filename} (part {i + 1})",
                "content": chunk,
            }
            for i, chunk in enumerate(chunks)
        ]

    elif suffix == ".csv":
        try:
            records = list(csv.DictReader(io.StringIO(text)))[:MAX_RECORDS]
        except csv.Error:
            raise HTTPException(status_code=400, detail="Could not parse this CSV file.")

    else:
        try:
            payload = json.loads(text)
        except ValueError:
            raise HTTPException(status_code=400, detail="This file is not valid JSON.")

        records = payload if isinstance(payload, list) else None
        if records is None and isinstance(payload, dict):
            records = None
            for key in ("results", "jobs", "messages", "items", "records", "data", "files"):
                if isinstance(payload.get(key), list):
                    records = payload[key]
                    break
            if records is None:
                records = [payload]
        if records is None:
            records = [payload]
        records = records[:MAX_RECORDS]

    documents = []
    for i, record in enumerate(records, start=1):
        doc = record_to_document(record, source, filename, i, imported_at)
        if doc:
            documents.append(doc)

    if not documents:
        raise HTTPException(status_code=400, detail="No searchable text was found in this file.")

    return documents


@router.post("/api/integrations/import")
async def import_authorized_export(
    file: UploadFile = File(...),
    source_name: str = Form("Other authorized export"),
):
    filename = Path(file.filename or "upload.txt").name
    source_name = re.sub(r"\s+", " ", source_name).strip()[:80]

    if not source_name:
        raise HTTPException(status_code=400, detail="Choose a source label.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Maximum file size is 10 MB.")

    imported_at = datetime.now(timezone.utc).isoformat()
    new_documents = parse_upload(filename, raw, source_name, imported_at)

    existing = load_imported_documents()
    # Re-importing the same file replaces its previous records for that source.
    existing = [
        doc for doc in existing
        if not (
            doc.get("source") == source_name
            and doc.get("source_file") == filename
        )
    ]

    combined = (existing + new_documents)[-5000:]
    save_imported_documents(combined)

    return {
        "source": source_name,
        "file_name": filename,
        "imported_count": len(new_documents),
        "message": "File imported. Run AI search to retrieve its content.",
    }


@router.get("/api/integrations/imported")
def list_imported_sources():
    documents = load_imported_documents()
    counts = {}
    for doc in documents:
        source = doc.get("source", "Unknown")
        counts[source] = counts.get(source, 0) + 1

    return {
        "document_count": len(documents),
        "source_counts": counts,
        "documents": [
            {
                "id": doc.get("id"),
                "title": doc.get("title"),
                "source": doc.get("source"),
                "source_file": doc.get("source_file"),
                "imported_at": doc.get("imported_at"),
            }
            for doc in documents
        ],
    }
