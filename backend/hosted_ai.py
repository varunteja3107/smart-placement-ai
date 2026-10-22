import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")

CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini")


def generate_career_answer(question, documents):
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    context_parts = []

    for index, document in enumerate(documents[:6], start=1):
        context_parts.append(
            f"Source {index}:\n"
            f"Title: {document.get('title') or document.get('name') or 'Not provided'}\n"
            f"Source: {document.get('source') or 'Unknown'}\n"
            f"Details: {(document.get('description') or document.get('content') or document.get('text') or str(document))[:1800]}"
        )

    context = "\n\n".join(context_parts) or "No relevant records were retrieved."

    response = OpenAI().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are Smart Placement AI's career coach. "
                    "Give practical, clear advice about careers, skills, "
                    "projects, job applications, and interview preparation. "
                    "Use the supplied retrieved context when relevant. "
                    "Do not invent job openings, qualifications, or facts. "
                    "Clearly say when the context does not contain enough "
                    "information. Distinguish general career advice from "
                    "facts supported by the retrieved sources."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Question:\n{question}\n\n"
                    f"Retrieved context:\n{context}\n\n"
                    "Answer the question with actionable next steps."
                ),
            },
        ],
        max_tokens=600,
    )

    return response.choices[0].message.content or (
        "I couldn't generate an answer. Please try again."
    )
