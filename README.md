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
- **🛡️ Rate Limiting** - Redis-backed sliding window API throttling with per-user quotas
- **📋 Structured Logging** - JSON logs with X-Request-ID correlation for production tracing
- **⏰ Rule Scheduling** - Time-aware rules that auto-activate on schedules or weekdays
- **📜 Audit Trail API** - Paginated, filterable audit logs with stats and CSV export
- **🏷️ Rule Tagging** - Flexible tag-based rule organization with bulk operations
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

#### 8. Rate Limiting & API Throttling
Prevents abuse and controls LLM API costs.
- Redis-backed sliding window rate limiter applied as FastAPI middleware.
- Two tiers: **default** (60 requests/min) and **llm** (10 requests/min for chat/stream/summarize).
- Injects `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` response headers.
- Returns `429 Too Many Requests` with `Retry-After` header when quota exceeded.
- Users identified by `X-User-ID` header, falling back to client IP.

#### 9. Structured Logging & Request Tracing
Production-grade observability for debugging and monitoring.
- JSON-formatted structured logging replacing all `print()` statements.
- `X-Request-ID` correlation ID generated per request and propagated via `contextvars`.
- Every log line includes `request_id`, `user_id`, `timestamp`, and `level` fields.
- Error logs include source file, line number, and function name.
- Request tracing middleware logs method, path, status code, and duration.

#### 10. Rule Scheduling & Time-Awareness
Activate rules only during specific time windows.
- Supports **one-time** windows (start/end datetime) and **recurring** schedules (daily time windows with weekday bitmask).
- Day-of-week bitmask: Mon=1, Tue=2, Wed=4, Thu=8, Fri=16, Sat=32, Sun=64 (127=all, 31=weekdays).
- Time windows use `HH:MM-HH:MM` format with overnight support (e.g., `22:00-06:00`).
- Rule engine filters out inactive rules transparently during prompt assembly.
- Batch-optimized schedule checking avoids N+1 queries.

#### 11. Audit Trail REST API
Full queryable history of every rule lifecycle event.
- Paginated listing with filters: event type, rule ID, date range.
- Aggregate statistics: event counts by type, most recent event.
- CSV export for compliance and external reporting.
- Replaces and supersedes the legacy `/audit` endpoint with richer functionality.

#### 12. Rule Tagging & Grouping
Flexible tag-based rule organization.
- Many-to-many relationship between rules and user-defined tags.
- Tags have custom names and hex color codes.
- Bulk tag operations for batch rule organization.
- Filter rules by tag for focused context management.

#### 13. Rule Effectiveness Analytics
AI-powered scoring of rule performance based on user interactions.
- Automatically tracks rule applications, reinforcements, and overrides.
- Computes effectiveness scores, success rates, and trend vectors.
- Highlights top performing rules, stale rules, and rules requiring correction.
- Scheduled daily recomputation and on-demand stats retrieval.

#### 14. API Key Management
Secure, multi-key authentication with granular access controls and usage tracking.
- SHA-256 hashed storage for keys with client-facing safe prefixes.
- Permissions scope validation (`rules:read`, `rules:write`, `chat`, etc.) and key expiration enforcement.
- Automated API key rotation mechanism.
- Backward compatibility fallback to legacy user identification headers.

#### 15. Rule Dependency Chains
Advanced rule execution graph resolution.
- Declares logic relationships between rules (`requires`, `excludes`, `enhances`).
- Graph cycle-detection to prevent infinite execution loops during creation.
- Prunes rules dynamically at prompt building time based on the status of dependent rules.

#### 16. Background Job Dashboard
Operational observability of the scheduler and background workers.
- Ring-buffered in-memory execution history logs capturing the last 100 runs per job.
- Performance statistics (total runs, error rates, average duration).
- Manual job triggers and pause/resume switches.

#### 17. Data Retention Policies
Automated database maintenance and regulatory compliance utilities.
- Configurable Time-To-Live (TTL) profiles for interactions, audit logs, and conversations.
- Dry-run cleanup preview showing estimated space/record reclamation.
- Daily scheduled background pruning.

#### 18. LLM Cost Tracker & Budget Guardrails
Observability and cost management for model consumption.
- Per-request cost metering based on provider pricing tables.
- Daily and monthly hard budget spend limits to block overspending.
- REST analytics endpoints for trend tracking and breakdowns by model/endpoint.

#### 19. Rule A/B Testing (Experiments)
Controlled A/B testing of rule variants to optimize user experience.
- Random traffic splitting between rule variant A and variant B.
- Simple proportion z-test statistics to dynamically determine winners ($p < 0.05$).
- Auto-promotion of the winning rule and archiving of the losing rule on conclusion.

#### 20. Context-Aware Prompt Profiles
Dynamic system prompts and configuration presets.
- Pre-selects specific rules by tags or categories and overrides parameters (temperature, max_tokens).
- Custom system preamble injection based on active profiles.
- Integrated `profile_id` support inside prompt builder logic.

#### 21. Rule Auto-Archival & Lifecycle Manager
Automated rules lifecycle states and operations.
- Background cron job to identify and archive stale rules with declining confidence.
- Re-triggering or reinforcing archived rules auto-resurrects them with confidence bumps.

#### 22. IP Allowlisting & Session Security
Security hardening for API access keys.
- Locks API key usage to specific IPv4/IPv6 CIDR ranges.
- Tracks active requests by (API key, IP) to log sessions and client metrics.
- Automatic anomaly detection (flags rapid request volume increases or geo-mismatches).

#### 23. Rule Similarity Clusters
Automatic grouping of semantically similar rules for deduplication.
- FAISS-powered pairwise similarity analysis with union-find clustering.
- Auto-generated cluster names based on category analysis.
- LLM-powered cluster merge: consolidates multiple rules into a single generalized rule.

#### 24. Multi-User Shared Rule Library
Community-driven rule sharing and discovery.
- Publish personal rules to a shared library with title, description, and visibility controls.
- Browse, search, and filter shared rules by category, popularity, or rating.
- One-click install clones rules into personal rulesets with attribution tracking.
- 1–5 star rating system with aggregate scoring.

#### 25. Prompt Replay & Regression Testing
Detect regressions or improvements after rule changes.
- Re-runs past interactions against the current rule set and compares outputs.
- Jaccard word-overlap similarity scoring with LLM-based regression/improvement classification.
- Progress tracking, verdict filtering, and diff summaries for each replayed interaction.

#### 26. Rule Change Notifications & Digest
Event notification system with periodic digest generation.
- Queues notifications for rule lifecycle events (created, archived, conflicted, decayed).
- Unread badge count with per-type breakdown.
- LLM-powered daily digest: summarizes 24 hours of audit log activity into natural language.
- Scheduled background job generates digests for all active users.

#### 27. Rule Impact Simulation (Dry-Run)
"What-if" analysis for rule changes without persisting.
- Preview how adding a new rule would change AI responses across test prompts.
- Preview how editing an existing rule would alter outputs (old vs. new content).
- Impact scores (0–1) and word-level diff summaries for each test prompt.

#### 28. Model-Specific Temperature Tuning & Prompt Optimization
Enables overriding LLM generation parameters and customizing prompt templates for specific models or providers.
- Override temperature, max output tokens, or prompt templates per provider (OpenAI, Gemini, Anthropic) or individual model names.
- Auto-applies model-optimized rule variations depending on target provider context during prompt construction.

#### 29. Context-Aware Dynamic Decay with Task Tags
Balances rule expiration based on category/tag activity.
- Expiration penalties dynamically scale down when related tags/categories have not seen recent user interactions.
- Avoids decaying active development rules during periods of purely creative or casual writing sessions.

#### 30. Dynamic Variables & Workspace Shared Parameters
Supports placeholder parameter evaluation inside active rules.
- Enables embedding variables like `{{user_name}}`, `{{current_year}}`, or custom values.
- Variable definitions are shared workspace-wide and resolved at prompt generation time.

#### 31. Automated LLM Adherence Judge & Rule Self-Healing
Uses independent LLM grading to check rule adherence.
- Evaluates interaction outcomes and flags consistent rule violations.
- Suggests self-healed, stricter rule refinements when adherence trends drop below safety thresholds.

#### 32. Rule Execution Graph Visualizer
Topological dependency sorting and conflict detection.
- Renders rules as Directed Acyclic Graphs (DAG) mapping `requires`, `excludes`, and `enhances` constraints.
- Employs cycle-detection algorithms to prevent infinite prompt generation loops.

#### 33. Multi-Provider LLM Fallback & Automatic Retry Policies
Enables robust and resilient text generation.
- Gracefully degrades models (e.g., GPT-4o -> Claude 3.5 -> Gemini) if one provider rate limits or crashes.
- Employs exponential backoff retry algorithms to seamlessly recover from transient errors.

#### 34. Rule Usage Hot-Reload & Prompt Cost Optimizer
Optimizes context window costs dynamically.
- Tracks and rates active rules by their efficiency ratio (impact/token cost).
- Identifies and prunes less critical or low-confidence rules when the total prompt size nears the LLM context limit.

#### 35. Episodic Memory Consolidation & Context Summarizer
Transforms long chat threads into core memories.
- Uses LLM summarization and key-takeaway extraction on expired or lengthy conversation threads.
- Vectorizes memories into a FAISS datastore for semantic relevance search, keeping history alive without context-bloat.

#### 36. Real-Time WebSocket Event & Telemetry Stream
Connects the backend directly to the frontend for real-time visibility.
- Emits real-time diagnostic logs, telemetry, and background job notifications (e.g., decay job finished) over WebSockets.
- Maps socket connections to user contexts for isolated, secure, per-user data streams.

#### 37. Encrypted Rule Portability & Cross-Instance Sync
Provides a secure mechanism to export/import active rules.
- Exports all active rules as a compressed, symmetrically encrypted JSON payload using Fernet encryption.
- Decrypts and dynamically creates rules upon import in another workspace or node, protecting private instructions.

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
| GET | `/api/audit/stats` | Aggregated audit event statistics |
| GET | `/api/audit/{id}` | Get single audit log entry |
| GET | `/api/audit/export/csv` | Export audit logs as CSV |
| GET | `/api/rate-limit/status` | Current user's rate limit quota |
| POST | `/api/rules/{id}/schedules` | Attach a time-based schedule to a rule |
| GET | `/api/rules/{id}/schedules` | List schedules for a rule |
| GET | `/api/rules/{id}/active-now` | Check if a rule is currently active |
| DELETE | `/api/schedules/{id}` | Delete a schedule |
| PATCH | `/api/schedules/{id}/toggle` | Toggle a schedule on/off |
| POST | `/api/tags` | Create a new tag |
| GET | `/api/tags` | List all tags with rule counts |
| PATCH | `/api/tags/{id}` | Update a tag |
| DELETE | `/api/tags/{id}` | Delete a tag |
| POST | `/api/rules/{id}/tags` | Attach tags to a rule |
| DELETE | `/api/rules/{id}/tags` | Remove tags from a rule |
| GET | `/api/tags/{id}/rules` | Get rules by tag |
| POST | `/api/tags/bulk` | Bulk-tag multiple rules |
| GET | `/api/analytics` | Aggregated usage statistics (totals, daily activity, category breakdown) |
| GET | `/api/search` | Full-text search across conversations with snippets |
| GET | `/api/suggestions` | AI-powered rule suggestions from interaction patterns |
| POST | `/api/summarize` | LLM-powered conversation summary with topics & action items |
| GET | `/api/export` | Full data export (rules, conversations, audit) as JSON |
| GET | `/api/rules/effectiveness` | Get user-wide effectiveness report |
| GET | `/api/rules/{rule_id}/effectiveness` | Get effectiveness metrics for a single rule |
| POST | `/api/keys` | Create a new scoped API key |
| GET | `/api/keys` | List active API keys (metadata only) |
| DELETE | `/api/keys/{key_id}` | Revoke/disable an API key |
| POST | `/api/keys/{key_id}/rotate` | Rotate an API key, issuing a new key with same scopes |
| POST | `/api/rules/{rule_id}/dependencies` | Add a dependency to a rule |
| GET | `/api/rules/{rule_id}/dependencies` | List dependencies for a rule |
| DELETE | `/api/dependencies/{dep_id}` | Remove a dependency |
| GET | `/api/rules/dependency-graph` | Retrieve user's full dependency graph |
| GET | `/api/jobs` | List background jobs with status and statistics |
| GET | `/api/jobs/{job_id}/history` | Get run history for a background job |
| POST | `/api/jobs/{job_id}/trigger` | Manually execute a background job |
| PATCH | `/api/jobs/{job_id}/pause` | Pause/resume background job scheduling |
| GET | `/api/retention` | Get active data retention policies |
| PUT | `/api/retention` | Create/update a data retention policy |
| POST | `/api/retention/preview` | Dry-run preview of data retention cleanup |
| POST | `/api/retention/cleanup` | Trigger manual data retention cleanup |
| GET | `/api/retention/stats` | Retrieve database storage usage statistics |

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
│   │   │   ├── streaming.py     # SSE chunk streaming engine
│   │   │   ├── rate_limiter.py  # Redis sliding window rate limiter + middleware
│   │   │   └── logging.py       # JSON structured logger + request tracing middleware
│   │   ├── services/
│   │   │   ├── interaction.py   # Main orchestration
│   │   │   ├── rule_engine.py   # Rule CRUD + ranking (schedule-aware)
│   │   │   ├── memory.py        # Vector search
│   │   │   ├── analytics.py     # Usage statistics aggregation
│   │   │   ├── suggestions.py   # AI-powered rule suggestions
│   │   │   ├── prompt_builder.py
│   │   │   ├── conflicts.py     # Conflict detection orchestration
│   │   │   ├── versioning.py    # Rule history snapshotting and diffing
│   │   │   ├── webhook_service.py # Webhook validation and delivery management
│   │   │   ├── conversation_service.py # Fork tree and branch creation
│   │   │   ├── import_service.py # Bulk template imports with duplicate mitigation
│   │   │   ├── scheduling_service.py # Rule time-window scheduling
│   │   │   ├── audit_service.py  # Audit log querying, stats, and CSV export
│   │   │   └── tag_service.py    # Tag CRUD, rule associations, bulk tagging
│   │   ├── models/              # SQLAlchemy models (user, rule, audit_log, rule_conflict, rule_version, conversation, webhook, rule_schedule, rule_tag)
│   │   ├── db/                  # Database connections (session, redis, vector)
│   │   └── jobs/                # Background tasks (scheduler, decay_processor, rule_extractor, conflict_scanner, webhook_dispatcher)
│   ├── tests/                   # Automated pytest suite (41 tests across 10 test modules)
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
| `RATE_LIMIT_DEFAULT` | Requests/min for general endpoints | `60` |
| `RATE_LIMIT_LLM` | Requests/min for LLM-intensive endpoints | `10` |
| `RATE_LIMIT_BURST` | Burst size for rate limiting | `5` |

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
