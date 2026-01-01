# Personal AI OS

**An AI assistant that automatically learns your preferences from corrections and applies them consistently.**

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=next.js&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white" />
</p>

## Overview

Personal AI OS is a production-grade system that creates a personalized AI experience by learning from your corrections and feedback. Unlike simple chatbot wrappers, it features:

- **🧠 Automatic Rule Learning** - Detects corrections and extracts reusable rules
- **⚡ Intelligent Rule Application** - Applies relevant rules without cluttering prompts
- **📊 Confidence Scoring** - Rules gain/lose confidence based on usage
- **🔍 Semantic Memory** - Vector search for context-aware rule matching
- **🎯 Full Transparency** - View, edit, and manage all learned preferences

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │    Chat     │  │    Rules    │  │       Timeline          │  │
│  │  Interface  │  │  Dashboard  │  │      (Audit Log)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API
┌────────────────────────────┴────────────────────────────────────┐
│                       Backend (FastAPI)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Interaction │  │  Rule Engine │  │    Prompt Builder    │   │
│  │   Service    │  │   Service    │  │      Service         │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │    Memory    │  │  Background  │  │     Extraction       │   │
│  │   Service    │  │     Jobs     │  │       Logic          │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                        Storage Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  PostgreSQL  │  │    Redis     │  │    FAISS (Vector)    │   │
│  │   (Rules)    │  │   (Cache)    │  │      (Memory)        │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### 1. Rule Learning
When you correct the AI (e.g., "don't use em dashes"), the system:
- Detects correction intent using LLM
- Extracts a generalized, reusable rule
- Categorizes it (style, tone, formatting, logic, safety)
- Checks for duplicates via semantic similarity
- Assigns initial confidence score (0.5)

### 2. Rule Application
Every AI response automatically:
- Retrieves user's active rules from cache
- Ranks rules by relevance to current context
- Injects top rules into system prompt
- Tracks which rules were applied

### 3. Confidence & Decay
Rules have dynamic confidence scores:
- **Reinforcement**: +0.1 when user repeats the preference
- **Application**: Tracked for analytics
- **Decay**: -0.05 per week unused
- **Archival**: Rules below 0.2 confidence are archived

### 4. Memory System
Lightweight semantic memory:
- Stores interaction embeddings in FAISS
- Enables similarity search for ambiguous cases
- Helps resolve borderline rule applications

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send a message and get AI response with rules applied |
| POST | `/api/feedback` | Submit correction to learn new rule |
| GET | `/api/rules` | List all rules with filters |
| PATCH | `/api/rules/{id}` | Update a rule |
| DELETE | `/api/rules/{id}` | Delete a rule |
| POST | `/api/rules/{id}/toggle` | Toggle rule active/disabled |
| GET | `/api/audit` | Get audit log events |

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- OpenAI API key

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your settings (especially OPENAI_API_KEY)

# Initialize database
psql -U postgres -c "CREATE DATABASE personal_ai_os;"
psql -U postgres -d personal_ai_os -f schema.sql

# Start the server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Visit `http://localhost:3000` to use the application.

## Example Interaction

```
User: "Explain how photosynthesis works"

AI: "Photosynthesis is the process by which plants convert light energy—
     typically from the sun—into chemical energy..."

User: "Don't use em dashes, use regular dashes instead"

[System detects correction]
[Extracts rule: "Use regular dashes (-) instead of em dashes (—)"]
[Category: formatting, Confidence: 0.5]

Toast: "✓ Learned preference: Use regular dashes instead of em dashes"

User: "Now explain cellular respiration"

[System applies rule automatically]

AI: "Cellular respiration is how cells break down glucose - a simple sugar - 
     to release energy..."

[Rule applied - no em dashes, confidence boosted]
```

## Project Structure

```
AI OS/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/          # API endpoints
│   │   │   └── schemas/         # Pydantic models
│   │   ├── core/
│   │   │   ├── llm.py           # OpenAI client
│   │   │   ├── prompts.py       # Prompt templates
│   │   │   ├── algorithms.py    # Confidence, decay, ranking
│   │   │   └── extraction.py    # Rule extraction logic
│   │   ├── services/
│   │   │   ├── interaction.py   # Main orchestration
│   │   │   ├── rule_engine.py   # Rule CRUD + ranking
│   │   │   ├── memory.py        # Vector search
│   │   │   └── prompt_builder.py
│   │   ├── models/              # SQLAlchemy models
│   │   ├── db/                  # Database connections
│   │   └── jobs/                # Background tasks
│   ├── schema.sql
│   └── requirements.txt
│
└── frontend/
    └── src/
        ├── app/
        │   ├── page.tsx         # Chat interface
        │   ├── rules/page.tsx   # Rules dashboard
        │   └── timeline/page.tsx # Audit timeline
        ├── components/
        │   ├── ui/              # Base components
        │   └── layout/          # Layout components
        ├── lib/
        │   ├── api.ts           # API client
        │   └── utils.ts         # Utilities
        └── hooks/               # React hooks
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `LLM_MODEL` | Model to use | `gpt-4-turbo-preview` |
| `CONFIDENCE_THRESHOLD` | Min confidence for rule application | `0.3` |
| `DECAY_RATE` | Confidence decay per week | `0.05` |
| `SIMILARITY_THRESHOLD` | Threshold for duplicate detection | `0.85` |

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details.

---

Built with ❤️ for personalized AI experiences.
