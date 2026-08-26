# NIGHT Terminal

Personal AI-assisted trading analysis terminal.

## Stack
- Frontend: React + Vite
- Backend: FastAPI
- Analysis: deterministic scoring engine + provider adapters
- Future data: market feed, macro data, calendar, order flow, news

## Features in this MVP
- Pair selector
- Multi-factor bias scoring
- Technical / Volume / Macro / Intermarket / Session / Execution scores
- Buyer aggression and greed metrics
- Trade Readiness Index
- No-trade logic
- Scenario and invalidation output
- Economic calendar mock endpoint
- Provider abstraction ready for real APIs
- Dark terminal UI

## Run locally

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend expects backend at `http://localhost:8000` by default.

## Environment
Copy `.env.example` files and add provider credentials when available.

## Important
This project is an analysis and decision-support tool, not a guarantee of profitability. Scores are probabilities/heuristics and must be calibrated with historical and live results.
