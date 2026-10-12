# Smart Placement AI

A student placement platform built with React, Vite, FastAPI, MySQL,
and Retrieval-Augmented Generation (RAG).

## Implemented features

- Job listings and application submission
- MySQL-backed application storage
- Application tracking interface
- Semantic job search using Sentence Transformers
- External job retrieval from Remotive
- Public GitHub repository search
- CSV, JSON, TXT, and Markdown data import for RAG
- Unified search results with sources and relevance scores

## Requirements

- Python 3.12 recommended
- Node.js and npm
- MySQL Server
- Internet access for external job retrieval and the initial embedding-model download

## Database setup

Create the database if it does not already exist:

    mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS smart_placement_ai;"

## Start the backend

From the project directory:

    cd backend
    python3 -m venv venv
    source venv/bin/activate
    python -m pip install -r requirements.txt

Set the MySQL root password in your terminal environment without
putting it in source code:

    export DB_PASSWORD='YOUR_MYSQL_ROOT_PASSWORD'

Start FastAPI:

    python -m uvicorn main:app --reload --port 8000

Keep this terminal open. API documentation is available at:

    http://127.0.0.1:8000/docs

## Start the frontend

Open another terminal:

    cd "$HOME/Desktop/python project/smart-placement-ai/frontend"
    npm install
    npm run dev

Open the local Vite URL printed in the terminal, normally:

    http://localhost:5173

Create a production build with:

    npm run build

## Demo workflow

1. Browse the local job listings.
2. Submit a test application.
3. View the saved application in the Applications page.
4. Import frontend/sample_export.csv.
5. Search for "Python intern data APIs" using AI search.
6. Show the Smart Placement AI, Remotive, GitHub, and imported-data results.

## Current integration limitations

The tested multi-source RAG workflow supports local listings, Remotive,
public GitHub repository metadata, and user-provided data exports.

Google Drive OAuth has not yet been successfully verified. Gmail, LinkedIn,
and Naukri are not fully connected. Do not describe these as completed
integrations until authorization and retrieval have been tested.

This is a local-development demo. Before public deployment, implement
user authentication, role permissions, per-user token storage, and
production-grade secret management.
