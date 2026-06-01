# Personal AI OS

**An AI assistant that automatically learns your preferences from corrections and applies them consistently.**

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=next.js&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white" />
  <img src="https://img.shields.io/badge/Gemini-8E75B2?style=for-the-badge&logo=google&logoColor=white" />
  <img src="https://img.shields.io/badge/Anthropic-191919?style=for-the-badge&logo=anthropic&logoColor=white" />
</p>

## Overview

Personal AI OS is a production-grade system that creates a personalized AI experience by learning from your corrections and feedback. Unlike simple chatbot wrappers, it features:

- **🧠 Automatic Rule Learning** - Detects corrections and extracts reusable rules
- **⚡ Intelligent Rule Application** - Applies relevant rules without cluttering prompts
- **📊 Confidence Scoring** - Rules gain/lose confidence based on usage
- **⚔️ Rule Conflict Detection** - Auto-detects and resolves contradictory preferences
- **⏳ Versioning & History** - Tracks rule modifications with differential logs and rollback
- **📡 Server-Sent Events (SSE)** - Real-time token streaming with active rule broadcasts
- **🔌 Webhook Event Bus** - Outbound HTTP event notifications signed with HMAC-SHA256 signatures
- **🔱 Timeline Branching** - Fork conversations at any point to spawn new alternate timelines
- **📦 Pre-Built Templates** - One-click category rule import with deduplication checks
- **🔍 Semantic Memory** - Vector search (FAISS) for context-aware rule matching
- **🎯 Full Transparency** - View, edit, and manage all learned preferences

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │    Chat     │  │    Rules    │  │       Timeline          │  │
│  │  Interface  │  │  Dashboard  │  │      (Audit Log)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API
┌────────────────────────────┴────────────────────────────────────┐
│                       Backend (FastAPI)                         │
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
│                        Storage Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  PostgreSQL  │  │    Redis     │  │    FAISS (Vector)    │   │
│  │   (Rules)    │  │   (Cache)    │  │      (Memory)        │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### Core AI Engine

#### 1. Rule Learning
When you correct the AI (e.g., "don't use em dashes"), the system:
- Detects correction intent using LLM
- Extracts a generalized, reusable rule
- Categorizes it (style, tone, formatting, logic, safety)
- Checks for duplicates via semantic similarity
- Assigns initial confidence score (0.5)

#### 2. Rule Application
Every AI response automatically:
- Retrieves user's active rules from cache
- Ranks rules by relevance to current context
- Injects top rules into system prompt
- Tracks which rules were applied

#### 3. Confidence & Decay
Rules have dynamic confidence scores:
- **Reinforcement**: +0.1 when user repeats the preference
- **Application**: Tracked for analytics
- **Decay**: -0.05 per week unused
- **Archival**: Rules below 0.2 confidence are archived

#### 4. Memory System
Lightweight semantic memory:
- Stores interaction embeddings in FAISS
- Enables similarity search for ambiguous cases
- Helps resolve borderline rule applications

### Advanced Backend Services

#### 1. Rule Conflict Detection Engine
Automatically detects when user preferences contradict each other (e.g. "always use formal tone" vs "keep it casual").
- Uses FAISS semantic embeddings for fast O(N) pre-filtering.
- Invokes LLM analysis to determine conflict severity, explanation, and resolution strategies (merge, overwrite, keep newer/older, disable).
- Runs on rule creation/updates and as a scheduled background job.

#### 2. Rule Versioning & Rollback
Maintains audit trail and historical integrity for all user preferences.
- Captures an immutable rule version snapshot before any mutation (edit, reinforcement, or decay).
- Supports listing revision timelines, viewing unified line-by-line diffs, and rolling back to any previous version.

#### 3. Real-Time Chat Streaming (SSE)
Delivers fluid, low-latency AI interactions via Server-Sent Events.
- Streams token-by-token responses using async generators for OpenAI, Google Gemini, and Anthropic Claude.
- Emits structured `rule_applied` packets at the start of the stream, followed by `token` events, and finishes with a metadata `done` packet.
- Intercepts streaming lifecycle to automatically save interactions and mark rules as applied in the database post-stream.

#### 4. Webhook & Event System
Enables external integrations and event-driven architectures.
- Internal `EventBus` decouples service modules by publishing event notifications (e.g. `rule.created`, `chat.completed`).
- Dispatches event payloads to external HTTP webhooks signed with HMAC-SHA256 headers (`X-Webhook-Signature`).
- Handles delivery failures using a background retry dispatcher queue with exponential backoff.

#### 5. Conversation Branching
Provides timeline fork capability.
- Converts conversations into tree-like structures.
- Allows users to fork a conversation at any previous interaction, cloning all messages up to that point into a new conversation thread while keeping the original intact.

#### 6. Bulk Import & Template Packs
Loads and merges large preference databases.
- Performs schema validation and duplicate pre-filtering using semantic search.
- Includes pre-built template JSON packs for *Professional Writing*, *Code Review*, and *Academic Style*.
- Handles duplicate resolution using `skip_duplicates`, `merge` (confidence reinforce), or `overwrite` strategies.

#### 7. Diagnostics & Monitoring
Provides deep status monitoring of critical application resources.
- Performs connectivity and latency checks for PostgreSQL, Redis, and FAISS.
- Displays background scheduler state and job triggers.
- Computes system resource statistics (CPU, memory, system uptime) using `psutil`.

### Frontend Features

#### 🎨 UI & Experience
| Feature | Description | Shortcut |
|---------|-------------|----------|
| **Dark/Light Theme** | Toggle between themes with smooth transitions | — |
| **Command Palette** | Quick access to all commands and navigation | `⌘K` |
| **Animated Particle Background** | Canvas-based floating nodes with connecting lines | — |
| **Focus Mode** | Minimize distractions, intensify particles | `⌘.` |
| **Accent Color Picker** | 8 preset accent colors, live preview | `⌘K` → "Accent" |
| **Animated Status Bar** | Backend health indicator + active rules + last sync | — |
| **Interactive Onboarding Tour** | SVG spotlight-guided tour for new users | `⌘K` → "Tour" |
| **Chat Background Themes** | 6 CSS-only patterns (Dots, Grid, Gradient, Diagonal) | `⌘K` → "Background" |
| **Dynamic Greeting Banner** | Time-aware animated greeting with usage stats and gradient text | — |

#### 💬 Chat
| Feature | Description | Shortcut |
|---------|-------------|----------|
| **Markdown Rendering** | Rich markdown with syntax highlighting | — |
| **Typewriter Effect** | Streaming text animation for AI responses | — |
| **AI Thinking Animation** | Shimmer effect + rotating status messages | — |
| **Smart Suggestions** | Contextual follow-up prompt chips after AI replies | — |
| **Voice Input** | Speech-to-text via Web Speech API | 🎤 button |
| **Emoji Reactions** | React to messages with 👍 ❤️ 😂 🎯 🔥 💡 | Hover message |
| **Message Bookmarks** | Pin important messages for quick reference | Hover message |
| **Chat Export** | Download/copy conversations as Markdown | Export button |
| **Chat Stats** | Message count, word count, session duration | Collapsible bar |
| **Scroll Navigator** | Floating FAB with new message count | Auto on scroll |
| **Read Aloud** | Text-to-speech for AI responses (Web Speech API) | 🔊 button |
| **AI Persona Switcher** | Switch between Creative, Technical, Concise, Professional | Header dropdown |
| **Share Cards** | Generate beautiful gradient cards from messages | Share button |
| **Inline Auto-Complete** | Ghost text suggestions, press Tab to accept | `Tab` |
| **Conversation Summary** | One-click bullet-point summary of chat | Header button |
| **Slash Commands** | `/summarize`, `/translate`, `/bullet`, `/eli5`, `/code` + more | Type `/` |
| **Typing Speed (WPM)** | Live words-per-minute indicator while typing | Auto |
| **AI Response Rating** | 👍👎 with feedback tags and satisfaction sparkline trends | Hover message |
| **Pin to Board** | Pin any AI response to draggable pinboard canvas | Hover message |

#### 🛠️ Productivity
| Feature | Description | Shortcut |
|---------|-------------|----------|
| **Prompt Templates** | Categorized templates + custom saves | 📋 button |
| **Snippet Saver** | Save code blocks from AI responses | `⌘K` → "Snippets" |
| **Quick Notes Scratchpad** | Auto-saving notepad while chatting | `⌘J` |
| **Spotlight Search** | Fuzzy search past conversations | `⌘⇧F` |
| **Keyboard Shortcuts Sheet** | View all available shortcuts | `⌘/` |
| **Pomodoro Timer** | 25/5 focus timer with progress ring and audio alert | `⌘P` |
| **Ambient Sounds** | Rain, Café, White Noise, Fireplace via Web Audio API | `⌘M` |
| **Mood Journal** | Track daily emotions with sparkline chart over 7 days | `⌘E` |
| **Message Pinboard** | Draggable sticky-note canvas with color coding | `⌘B` |
| **Daily Streak Counter** | GitHub-style heatmap with milestone badges | Sidebar 🔥 |
| **🏆 Achievements & Badges** | 15 unlockable badges (Bronze→Platinum) with trophy case | `⌘K` → "Achievements" |
| **🌐 Quick Translate** | One-click translation of AI responses to 8 languages | Globe icon |
| **☁️ Word Cloud** | Interactive word frequency visualization from chat history | `⌘K` → "Word Cloud" |
| **⏳ Focus Session Timer** | Configurable deep work timer (15/25/45/60m) with SVG ring | `⌘K` → "Focus" |
| **🎯 Quick Actions FAB** | Floating radial menu for quick tool access | Bottom-right ⊕ |

#### 📊 Insights & Organization
| Feature | Description | Shortcut |
|---------|-------------|----------|
| **AI Insights Dashboard** | Brain health gauge, rule stats, activity feed | Sidebar → Insights |
| **Notification Center** | Bell icon with unread event badge | Sidebar footer |
| **Conversation Tags** | Color-coded labels (🔴🟡🟢🔵🟣) | Sidebar → 🏷️ |
| **Conversation History** | Auto-saved with sidebar management | Sidebar |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send a message and get AI response with rules applied |
| POST | `/api/chat/stream` | Stream chat tokens real-time via Server-Sent Events (SSE) |
| POST | `/api/feedback` | Submit correction to learn new rule |
| GET | `/api/rules` | List all rules with filters |
| PATCH | `/api/rules/{id}` | Update a rule |
| DELETE | `/api/rules/{id}` | Delete a rule |
| POST | `/api/rules/{id}/toggle` | Toggle rule active/disabled |
| GET | `/api/rules/{id}/versions` | List version history for a rule |
| POST | `/api/rules/{id}/rollback` | Rollback a rule to a specific version number |
| GET | `/api/rules/{id}/versions/{v1}/diff/{v2}` | Get differential unified diff between two rule versions |
| GET | `/api/conflicts` | List detected active rule conflicts |
| POST | `/api/conflicts/{id}/resolve` | Resolve conflict with a chosen strategy |
| POST | `/api/conflicts/scan` | Manually trigger a rule conflict scan |
| POST | `/api/webhooks` | Register a new webhook delivery URL |
| GET | `/api/webhooks` | List user's registered webhooks |
| DELETE | `/api/webhooks/{id}` | Delete a registered webhook |
| GET | `/api/webhooks/{id}/deliveries` | View webhook transmission delivery logs |
| POST | `/api/webhooks/{id}/test` | Trigger a test event payload delivery |
| GET | `/api/conversations` | List user's conversations and message counts |
| POST | `/api/conversations` | Create a new conversation thread |
| POST | `/api/conversations/{id}/fork` | Fork conversation timeline at a specific message |
| GET | `/api/conversations/{id}/tree` | Get conversation branching tree structure |
| PATCH | `/api/conversations/{id}` | Rename a conversation |
| DELETE | `/api/conversations/{id}` | Delete a conversation and optionally cascade forks |
| POST | `/api/rules/import/preview` | Preview duplicate check before executing import |
| POST | `/api/rules/import` | Execute bulk rule import with merge/skip strategy |
| GET | `/api/rules/templates` | List pre-built rule template packs |
| GET | `/api/health` | Comprehensive health dashboard of databases, scheduler, and system resources |
| GET | `/api/health/ready` | Readiness probe check (DB + Redis) |
| GET | `/api/health/live` | Liveness probe check |
| GET | `/api/audit` | Get audit log events |
| GET | `/api/analytics` | Aggregated usage statistics (totals, daily activity, category breakdown) |
| GET | `/api/search` | Full-text search across conversations with snippets |
| GET | `/api/suggestions` | AI-powered rule suggestions from interaction patterns |
| POST | `/api/summarize` | LLM-powered conversation summary with topics & action items |
| GET | `/api/export` | Full data export (rules, conversations, audit) as JSON |

## Quick Start

### Prerequisites
- Python 3.12+ (3.13 recommended)
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- API key for one of: **OpenAI**, **Google Gemini**, or **Anthropic Claude**

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
│   │   │   ├── routes/          # API endpoints (chat, conflicts, versions, stream, webhooks, conversations, rule_import, health, feedback, rules, analytics, search, suggestions, summarize, export)
│   │   │   └── schemas/         # Pydantic schemas (conflicts, versions, webhooks, conversations, rule_import, chat, feedback, rules, analytics, search, suggestions, summarize, export)
│   │   ├── core/
│   │   │   ├── llm.py           # Multi-provider LLM client (OpenAI/Gemini/Anthropic)
│   │   │   ├── prompts.py       # Prompt templates
│   │   │   ├── algorithms.py    # Confidence, decay, ranking
│   │   │   ├── extraction.py    # Rule extraction logic
│   │   │   ├── conflict_detector.py # LLM-based pairwise conflict analysis
│   │   │   ├── events.py        # Internal asynchronous EventBus singleton
│   │   │   └── streaming.py     # SSE chunk streaming engine
│   │   ├── services/
│   │   │   ├── interaction.py   # Main orchestration
│   │   │   ├── rule_engine.py   # Rule CRUD + ranking
│   │   │   ├── memory.py        # Vector search
│   │   │   ├── analytics.py     # Usage statistics aggregation
│   │   │   ├── suggestions.py   # AI-powered rule suggestions
│   │   │   ├── prompt_builder.py
│   │   │   ├── conflicts.py     # Conflict detection orchestration
│   │   │   ├── versioning.py    # Rule history snapshotting and diffing
│   │   │   ├── webhook_service.py # Webhook validation and delivery management
│   │   │   ├── conversation_service.py # Fork tree and branch creation
│   │   │   └── import_service.py # Bulk template imports with duplicate mitigation
│   │   ├── models/              # SQLAlchemy models (user, rule, audit_log, rule_conflict, rule_version, conversation, webhook)
│   │   ├── db/                  # Database connections (session, redis, vector)
│   │   └── jobs/                # Background tasks (scheduler, decay_processor, rule_extractor, conflict_scanner, webhook_dispatcher)
│   ├── tests/                   # Automated pytest suite (conftest, test_conflict_detector, test_conversations, test_imports, test_streaming, test_versioning, test_webhooks)
│   ├── schema.sql
│   └── requirements.txt
│
└── frontend/
    └── src/
        ├── app/
        │   ├── page.tsx         # Chat interface
        │   ├── layout.tsx       # Root layout with all providers
        │   ├── insights/        # AI Insights dashboard
        │   ├── rules/           # Rules management
        │   └── timeline/        # Audit timeline
        ├── components/
        │   ├── ui/
        │   │   ├── CommandPalette.tsx      # ⌘K command palette
        │   │   ├── SpotlightSearch.tsx     # ⌘⇧F conversation search
        │   │   ├── ShortcutsSheet.tsx      # ⌘/ shortcuts modal
        │   │   ├── OnboardingTour.tsx      # Interactive tour
        │   │   ├── ParticleBackground.tsx  # Animated background
        │   │   ├── MarkdownRenderer.tsx    # Rich markdown
        │   │   ├── VoiceInput.tsx          # Speech-to-text
        │   │   ├── ChatExport.tsx          # Export conversations
        │   │   ├── MessageReactions.tsx    # Emoji reactions
        │   │   ├── MessageBookmarks.tsx    # Bookmark messages
        │   │   ├── PromptTemplates.tsx     # Template library
        │   │   ├── ConversationTags.tsx    # Color-coded tags
        │   │   ├── ScrollNavigator.tsx     # Scroll FAB
        │   │   ├── AccentPicker.tsx        # Accent color picker
        │   │   ├── SmartSuggestions.tsx    # Follow-up prompts
        │   │   ├── ThinkingAnimation.tsx   # Loading animation
        │   │   ├── ChatStats.tsx           # Chat metrics
        │   │   ├── Scratchpad.tsx          # Quick notes
        │   │   ├── SnippetSaver.tsx        # Code snippet library
        │   │   ├── NotificationCenter.tsx  # Bell notifications
        │   │   ├── MoodJournal.tsx         # ⌘E mood tracker
        │   │   ├── DailyStreak.tsx         # 🔥 streak heatmap
        │   │   ├── Pinboard.tsx            # ⌘B sticky notes
        │   │   ├── ResponseRating.tsx      # 👍👎 rating system
        │   │   ├── Achievements.tsx        # 🏆 gamification badges
        │   │   ├── QuickTranslate.tsx      # 🌐 one-click translation
        │   │   ├── WordCloud.tsx           # ☁️ word frequency cloud
        │   │   ├── FocusSession.tsx        # ⏳ deep work timer
        │   │   └── QuickActionsFab.tsx     # 🎯 floating action menu
        │   └── layout/
        │       ├── Sidebar.tsx    # Collapsible sidebar
        │       ├── FocusMode.tsx  # ⌘. focus mode
        │       ├── StatusBar.tsx  # Bottom status bar
        │       ├── ThemeProvider.tsx
        │       └── ThemeToggle.tsx
        ├── lib/
        │   ├── api.ts           # API client
        │   └── utils.ts         # Utilities
        └── hooks/               # React hooks
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM provider to use | `openai` |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | OpenAI API key | Required if using OpenAI |
| `GOOGLE_API_KEY` | Google Gemini API key | Required if using Gemini |
| `ANTHROPIC_API_KEY` | Anthropic API key | Required if using Anthropic |
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
