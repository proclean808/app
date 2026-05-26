# Venture Ferret / PlatFormula.ONE

This repository contains a working dual-stack application:

- `backend/` — FastAPI service implementing a research workflow, knowledge graph storage, vector search, and audit telemetry.
- `frontend/` — React UI for triggering research runs, viewing graph nodes, querying semantic retrieval, and auditing workflow events.

## What is real

- The backend exposes real operational endpoints under `/api`.
- The research pipeline uses Firecrawl scraping, Gemini embeddings/extraction, and MongoDB storage.
- The frontend is wired to the backend API and can execute real runs when `REACT_APP_BACKEND_URL` is configured.

## Local development

1. Create a `.env` file in `backend/` with:

```env
MONGO_URL=<your mongodb connection string>
DB_NAME=<database name>
GOOGLE_API_KEY=<google gemini api key>
CORS_ORIGINS=http://localhost:3000
```

2. Install backend dependencies:

```bash
cd backend
python -m pip install -r requirements.txt
```

3. Run the backend:

```bash
cd backend
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

4. Run the frontend:

```bash
cd frontend
yarn install
yarn start
```

5. In development, the frontend defaults to `http://localhost:8000` if `REACT_APP_BACKEND_URL` is not set.

## Notes

- The previous `stripe.com` target domain default was a misleading demo placeholder; the app is designed to analyze arbitrary target domains.
- The core pipeline and graph retrieval are functional, not just mock UI.
