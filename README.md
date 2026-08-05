# QuizChat — WhatsApp-style Quiz Application

A quiz application with a WhatsApp-inspired chat UI, built on **React + FastAPI + MongoDB**.
Every question attempt is recorded as an event, and four analytics APIs derive insight
(learning velocity, fatigue, question difficulty, chapter/subject mastery) from that event
stream via MongoDB aggregation pipelines.

## Application flow

```
Login (dummy — pick a predefined user)
  → Exam
    → Subject
      → Chapter
        → Quiz (one question at a time, no revisiting, no negative marking)
          → Result (score + per-question review)
```

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 18 + TypeScript, Vite, React Router, Tailwind CSS |
| Backend | FastAPI, Pydantic v2, Motor (async MongoDB driver) |
| Database | MongoDB |
| Seed data | PyMongo (sync) + Faker, driven by a deterministic RNG seed |
| Tests | pytest + pytest-asyncio + mongomock-motor (38 tests) |

## Project structure

```
backend/
  app/
    core/          # settings, DB connection + index creation, error types
    models/        # internal Mongo document shapes (pydantic, not API-facing)
    schemas/       # API-facing request/response schemas (pydantic)
    repositories/   # all MongoDB queries & aggregation pipelines live here
    services/       # business logic: quiz-taking state machine, analytics math
    routers/        # FastAPI route handlers (thin — delegate to services)
    utils/          # pure statistics helpers (shrinkage, normalization, regression)
  scripts/
    seed.py         # entrypoint: wipes + repopulates the database
    generators/     # content/user/event generators used by seed.py
  tests/            # unit + aggregation + concurrency tests

frontend/
  src/
    api/            # thin fetch wrappers per resource, one file per backend router
    components/      # shared chat-UI building blocks
    pages/           # one component per route in the application flow
    context/         # in-memory session (dummy auth)
    hooks/           # quiz-taking state machine (client side)
```

The backend follows a strict layering rule: **routers** parse/validate input and call a
**service**; **services** own all business logic and math and are the only layer allowed to
raise domain errors; **repositories** are the only layer that talks to MongoDB. Nothing skips
a layer. This is what makes `services/analytics_service.py`'s pure functions (e.g.
`compute_lvi_rows`, `compute_qdi_rows`) directly unit-testable with plain dicts — no MongoDB
or FastAPI dependency required to test the actual math.

## Database design

### Collections

| Collection | Purpose |
|---|---|
| `users` | 50 seeded users (dummy auth picks one of these) |
| `exams` → `subjects` → `chapters` → `questions` | Content hierarchy (3 → 10 → 30 → 500) |
| `quiz_attempts` | One document per quiz taken: sampled question IDs, per-question option shuffle order, status |
| `question_events` | **The analytics fact table.** One document per question shown, updated when answered |

### Why `question_events` is the source of truth

Every question attempt captures exactly the fields the spec requires — user, quiz
(`quiz_attempt_id`), question, exam, subject, chapter, shown time, submitted time, response
duration, selected option, correct/incorrect — plus `question_index` (position within the
attempt). `exam_id`/`subject_id`/`chapter_id` are **denormalized** onto every event: every
analytics aggregation filters/groups by these, and denormalizing them avoids a `$lookup` join
on every single query.

There is deliberately **no separate `current_index` pointer** anywhere (e.g. on
`quiz_attempts`) tracking quiz progress. Progress is always derived by counting answered
`question_events` for an attempt. A pointer field and an events collection can drift out of
sync after a crash mid-request; a single source of truth cannot.

### Indexes (`scripts/seed.py`)

```
subjects.exam_id
chapters.subject_id
questions.chapter_id
quiz_attempts: (user_id, status), (user_id, started_at desc)
question_events: (quiz_attempt_id, question_id) unique   -- one event per question per attempt
question_events: (quiz_attempt_id, question_index)        -- "what's the current question"
question_events: (user_id, submitted_at desc)              -- per-user analytics
question_events: question_id                               -- Question Difficulty Index
question_events: chapter_id                                 -- Chapter Mastery
question_events: (exam_id, subject_id, chapter_id)          -- Question Difficulty filters
question_events: (user_id, chapter_id)                      -- Chapter Mastery per user
users.email unique
```

Every index backs an actual query pattern used by either the quiz-taking flow or one of the
four analytics endpoints — none are speculative.

### Quiz-taking guarantees (enforced server-side, not just in the UI)

- **No revisiting:** `GET current-question` always returns the question at index
  `count(answered events)` — there is no way to request an earlier index.
- **No replay / no skipping ahead:** `POST answers` rejects (409) if the submitted
  `question_id` isn't the expected next one, or if that question was already answered.
- **Single correct answer, no negative marking:** score is `correct_count / total_questions`;
  wrong answers cost nothing.

## Analytics implementation

All four run as real MongoDB aggregation pipelines (`app/repositories/event_repo.py`) feeding
plain-Python statistics (`app/services/analytics_service.py`, `app/utils/stats.py`) — nothing
is precomputed or hardcoded.

1. **Learning Velocity Index** (`GET /api/v1/analytics/learning-velocity`)
   `LVI = 100 × (0.5 × accuracy + 0.3 × speed_score + 0.2 × consistency_score)`.
   Speed is min-max normalized *across all users* (5th–95th percentile clipped, so one
   outlier can't compress everyone else's range) and inverted (faster → higher score).
   Consistency is `1 / (1 + coefficient_of_variation(response_time))` — a user with wildly
   swinging response times scores lower even if their *average* speed looks fine. Users are
   ranked descending by LVI.

2. **Fatigue Analysis** (`GET /api/v1/analytics/fatigue?user_id=` or `?quiz_attempt_id=`)
   Buckets a quiz (or a user's full history) into groups of 5 questions (Q1–5, Q6–10, …),
   reporting accuracy and average response time per bucket, plus an accuracy/time trend
   **slope** via linear regression across buckets — not just first-vs-last delta, which is
   noisy on short quizzes.

3. **Question Difficulty Index** (`GET /api/v1/analytics/question-difficulty`)
   `QDI = 100 × (0.7 × (1 − shrunk_accuracy) + 0.3 × normalized_time)`. Both accuracy and
   response time use **Bayesian shrinkage** toward a prior (global mean accuracy; per-chapter
   mean time) weighted by attempt count — a question attempted twice doesn't get to claim
   "0% accuracy, hardest question ever" the way raw accuracy would. Each row is tagged with a
   `confidence` (`low`/`medium`/`high`) based on attempt count so consumers can see *how much*
   to trust a given score. Ranked hardest → easiest.

4. **Chapter/Subject Mastery** *(bonus, beyond the 3 required)*
   (`GET /api/v1/analytics/chapter-mastery?user_id=` or `?chapter_id=`)
   Per-user, per-chapter Bayesian-shrunk accuracy + a within-cohort speed score, rolled up to
   a subject-level score weighted by attempt count. Lets you ask either "how is this user
   doing per chapter" or "how does this chapter's cohort rank."

## API overview

All routes are under `/api/v1`. Full interactive docs at `/docs` once the backend is running.

| Resource | Routes |
|---|---|
| Sessions (dummy auth) | `POST /sessions` |
| Users | `GET /users` |
| Exams | `GET /exams`, `GET /exams/{id}/subjects` |
| Chapters | `GET /subjects/{id}/chapters` |
| Quiz | `POST /quiz-attempts`, `GET /quiz-attempts/{id}/current-question`, `POST /quiz-attempts/{id}/answers`, `GET /quiz-attempts/{id}/result` |
| Analytics | `GET /analytics/learning-velocity`, `GET /analytics/fatigue`, `GET /analytics/question-difficulty`, `GET /analytics/chapter-mastery` |

## Setup

### Option A — Docker Compose (recommended)

```bash
docker compose up --build
```

This starts MongoDB, the backend (`:8000`), and the frontend (`:5173`). Then seed the
database once (in a new terminal, with the stack running):

```bash
docker compose exec backend python -m scripts.seed
```

Open `http://localhost:5173`.

### Option B — Run locally

Requires MongoDB running locally (e.g. `brew services start mongodb-community`).

**Backend:**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m scripts.seed          # populates the database — run once, or anytime to reset
uvicorn app.main:app --reload --port 8000
```

**Frontend** (separate terminal):

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

### Running tests

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

## Configuration

Backend settings (`backend/.env`, see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `MONGO_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `DB_NAME` | `quiz_app` | Database name |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated allowed origins |

Analytics weights (LVI/QDI/Mastery component weights, Bayesian shrinkage strength `k`, quiz
length, attempt-freshness window) are named constants in `backend/app/core/config.py` rather
than inlined — tune them there.

## Assumptions made

- **Dummy auth is genuinely dummy and in-memory.** No passwords, tokens, or persisted
  sessions — picking a user just stores `{id, name}` in a React context for the browser tab's
  lifetime. A hard refresh logs you out by design; this matches "authentication can be dummy."
- **Seed data content is synthetic (Faker-generated), not real exam content.** The assignment
  asks for a seed *script*, not real question banks — question/option text is placeholder
  prose so the volume (500 questions) and structure are realistic even though the wording
  isn't.
- **Historical quiz activity is also simulated**, not just the static content. `scripts/seed.py`
  generates 15–40 realistic-looking completed attempts per user (Zipf-weighted chapter
  popularity, per-user hidden skill profiles for accuracy/speed/fatigue/improvement) so the
  four analytics endpoints have enough signal to demonstrate on a freshly seeded database,
  rather than returning empty tables until real usage accumulates.
- **A quiz samples up to 10 questions** from the chosen chapter without replacement
  (`DEFAULT_QUIZ_LENGTH`), or fewer if the chapter has fewer than 10 questions.
- **An in-progress attempt can be resumed** for 30 minutes (`ATTEMPT_FRESHNESS_MINUTES`);
  after that it's marked abandoned and starting that chapter's quiz again begins fresh. This
  was added to handle accidental refreshes/navigation without violating "no revisiting" (you
  resume where you left off, you don't get to redo answered questions).
- **Options are shuffled per-attempt and persisted** (`option_order` on `quiz_attempts`), so
  the same question shown in two different attempts can display options in a different order,
  but a single attempt is internally consistent across resume/refresh.

## Deployment

Not deployed (optional per the assignment). `backend/api/index.py` is a ready-made Vercel ASGI
entrypoint if serverless deployment is wanted; the frontend is a static Vite build deployable
to any static host, pointed at the deployed API via `VITE_API_BASE_URL`.
