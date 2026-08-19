# Project Profile: Semranko (RankWatch Clone)
You are an expert AI software engineer replicating the core functionalities, user workflows, and SEO/rank-tracking features of https://www.rankwatch.com/. The workspace contains a monorepo with both Frontend and Backend systems.

## Tech Stack & Architecture
- **Frontend:** React + Vite
- **Backend:** Python with SQLAlchemy ORM mapped to existing PostgreSQL tables
- **Background Tasks:** Redis Queue (RQ) + RQ Worker for handling heavy rank-check jobs

## Structural Rules (Strict Consistency)
1. **Never Break Existing Implementation:** Before making changes, analyze existing code across frontend and backend. Backward compatibility is non-negotiable.
2. **Backend Routing Architecture:** All HTTP routes must be structured under the `/api` equivalent surface. Group routes strictly inside: `app/api/routes/` (e.g., `app/api/routes/auth.py`, `app/api/routes/rank.py`).
3. **Business Logic Layer:** Keep controllers and core logic separated from endpoints. Place them strictly inside: `app/services/`.
4. **Authentication System:** Implement strict JWT authentication across secured endpoints. Expect and pass the token via the `Authorization: Bearer <token>` header.

## Coding Patterns & Safety
1. **Standardized API Responses:** Every JSON API response must match this precise shape:
   ```json
   {
     "success": true/false,
     "message": "Descriptive message here",
     "data": {} or []
   }
   ```
2. **Zero Hardcoded Secrets:** Never hardcode secret keys, API credentials, Google Console keys, or database credentials. Always load them using environment variables (`os.getenv()`, `process.env`). Prompt the user to update their `.env` file if new keys are required.
3. **Repository Mapping:** Always perform a full project analysis of files and schemas before making multi-file edits. Never make assumptions about table columns or existing file connections.
