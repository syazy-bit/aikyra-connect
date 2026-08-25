# Development Setup

> Windows-oriented setup for the Aikyra team.

## Prerequisites

| Tool | Version |
|------|---------|
| Git | latest |
| Node.js | 18+ |
| Python | 3.11+ |
| PostgreSQL | 17 |
| Ollama (later phases) | latest |

## 1. Clone & Configure

```bash
git clone <repo-url>
cd aikyra
copy .env.example .env
# Edit .env with your local values. NEVER commit .env.
```

## 2. Database

PostgreSQL is assumed installed locally.

```sql
CREATE DATABASE aikyra;
```

Set `DATABASE_URL` in `.env`:
```
DATABASE_URL=postgresql://postgres:<your-password>@localhost:5432/aikyra
```

## 3. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Verify: http://localhost:8000/health → `{"status": "ok"}`

## 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

Note: Tailwind CSS, React Router, and Recharts are **not installed yet** — they will be added when UI work begins.

## 5. AI (later phases)

```bash
ollama pull <model-name>
```

Model choice will be documented when the AI phase starts.

## Troubleshooting

- **Port conflicts:** backend uses 8000, frontend 5173, Postgres 5432.
- **DB connection refused:** ensure the PostgreSQL service is running (`services.msc`).
- **`python` not found:** try `py`, or add Python to PATH.
