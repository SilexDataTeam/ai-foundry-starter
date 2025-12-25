# AGENTS.md

This file provides guidance to AI coding assistants when working with code in this repository.

## Project Overview

Silex AI Foundry Starter is a production-ready monorepo for building AI applications with LangChain/LangGraph. It includes a Next.js chat frontend, FastAPI backend with multiple RAG patterns, Kong API gateway for multi-model LLM support, and Kubernetes/OpenShift deployment infrastructure.

## Common Commands

### Frontend (chat-app/)
```bash
cd chat-app
npm install              # Install dependencies
npm run dev              # Start dev server with Turbopack (localhost:3000)
npm run build            # Production build
npm run lint             # Run ESLint
npx prisma migrate dev   # Run database migrations
npx prisma generate      # Generate Prisma client
```

### Backend (backend/)
```bash
cd backend
pip install -r requirements.txt                    # Install dependencies
pip install -r tests/unit/requirements.txt         # Install test dependencies
uvicorn backend.main:app --reload --port 8080      # Start dev server
pytest backend/tests                               # Run all tests
pytest backend/tests/unit/test_events.py           # Run single test file
pytest backend/tests -k "test_name"                # Run specific test
```

### Ingestion Pipeline (pipelines/ingestion/)
```bash
cd pipelines/ingestion
pip install -r requirements.txt
python ingest.py  # Run document ingestion
```

### Container Builds (Podman/Docker)
```bash
# Backend
cd backend && make podman-build && make podman-run

# Frontend
cd chat-app && make podman-build && make podman-run
```

## Architecture

```
├── chat-app/           # Next.js 15 frontend (React 19, Tailwind, Prisma, NextAuth)
├── backend/            # FastAPI backend with LangChain/LangGraph
│   ├── routes/         # API endpoints (events, feedback, chat_title)
│   ├── patterns/       # RAG implementations (selected via USE_CHAIN env var)
│   │   ├── basic_rag_qa/      # Simple RAG with similarity search
│   │   ├── advanced_rag_qa/   # Enhanced RAG with retriever
│   │   ├── agentic_rag/       # Agent-based RAG with tool calling
│   │   └── invoice_agent/     # Specialized invoice processing
│   └── tests/unit/     # pytest tests
├── model-gateway/      # Kong API Gateway configuration
├── pipelines/ingestion/# Document ingestion to PGVector
├── ai-foundry-chart/   # Helm charts for Kubernetes deployment
├── keycloak/           # Authentication service setup
├── vector-database/    # PostgreSQL + PGVector (CNPG)
└── opentelemetry/      # Observability configuration
```

## Key Environment Variables

**Backend:**
- `DISABLE_AUTH=true` - Disable Keycloak auth for local testing
- `DISABLE_TELEMETRY=true` - Disable OpenTelemetry for local testing
- `USE_CHAIN` - Select RAG pattern: `basic_rag_qa`, `advanced_rag_qa`, `agentic_rag`, `invoice_agent`
- `MODEL_GATEWAY_BASE_URL`, `MODEL_GATEWAY_MODEL_ID` - LLM gateway config
- `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_NAME` - PostgreSQL connection
- `COLLECTION_NAME` - Vector store collection name

**Frontend:**
- `DATABASE_URL` - PostgreSQL connection for Prisma
- `NEXTAUTH_URL`, `NEXTAUTH_SECRET` - NextAuth configuration

## Data Flow

1. Frontend sends chat messages via SSE to `/events` endpoint
2. Backend authenticates via Keycloak JWT tokens (unless DISABLE_AUTH)
3. Selected RAG pattern processes the query using LangChain/LangGraph
4. LLM requests route through Kong gateway to configured model
5. Vector similarity search uses PostgreSQL + PGVector
6. Streaming responses return via SSE to frontend

## Testing Notes

- Backend tests use pytest-asyncio for async route testing
- Tests mock external dependencies (LLM, database, Keycloak)
- Run `pytest backend/tests -v` for verbose output
