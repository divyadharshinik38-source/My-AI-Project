# AI Interview Agent

An AI-powered technical interviewer that conducts realistic,
multi-turn interviews personalized to each candidate's actual
progress through the 31-day AI Cohort curriculum — adapting
questions, follow-ups, and difficulty based on real mission history
rather than asking a fixed quiz.

**Live Frontend:** https://cheerful-torte-554076.netlify.app
**Live Backend API:** https://interview-agent-ahj5.onrender.com
**Repository:** https://github.com/divyadharshinik38-source/My-AI-Project

> Note: both the frontend and backend are hosted on free tiers that
> spin down after a period of inactivity. The first request after
> idle time may take 30-60 seconds to respond while the service
> wakes up.

---

## Problem

After completing an intensive AI engineering cohort, learners
struggle to confidently explain the systems they built and the
engineering decisions behind them in real technical interviews.
Generic interview prep tools ask the same questions to everyone —
they don't know what a specific candidate actually struggled with.

## Solution

This agent reads a candidate's real mission history (what they
completed, failed, skipped, or needed multiple attempts on) and
builds a personalized interview plan from it — probing weak spots
first, asking genuine follow-ups that reference the candidate's
actual answers, and producing honest, non-inflated feedback at the
end.

---

## Architecture
Candidate Profile + Curriculum
|
v
┌───────────────────┐
│ Interview Planner │ <- scores/selects 4+ curriculum days to
│ (planner.py) │ probe based on real mission history
└───────────────────┘
|
v
┌───────────────────┐
│ Conversation Loop │ <- state machine: ask -> evaluate ->
│ (interview_engine) │ follow-up or move on
└───────────────────┘
|
v
┌───────────────────┐
│ Session State │ <- per-sessionId in-memory transcript,
│ (session_store.py) │ topic progress, follow-up counts
└───────────────────┘
|
v
┌───────────────────┐
│ Feedback Generator │ <- runs once at the end, synthesizes
│ (part of llm.py) │ structured report from transcript
└───────────────────┘
|
v
┌───────────────────┐
│ Frontend Chat UI │ <- static HTML/JS, calls the API,
│ (frontend/index.html) │ renders conversation + feedback
└───────────────────┘

**Why the planner matters:** two different candidates get visibly
different interviews, because the plan is built from their real
`missions` data (failed > skipped > struggled-but-passed > easy-pass
priority), not a fixed question list.

**Why the quota logic matters:** the spec requires a minimum of 8
questions across 4+ curriculum days. The planner guarantees 4+ days,
but the engine additionally guarantees the question count via
`required_per_topic = ceil(8 / num_topics)` in
`interview_engine.py`, so the minimum is met regardless of how many
topics get planned.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI | Fast to build, clean async support |
| LLM | Groq (`llama-3.3-70b-versatile`) | Migrated from Gemini after hitting a very restrictive free-tier daily quota (20 req/day) mid-development; Groq's free tier gave enough headroom for real testing |
| Session state | In-memory (Python dict) | No persistence required per spec; kept simple intentionally |
| Frontend | Plain HTML/CSS/JS | No build step needed; kept simple given hackathon time constraints |
| Backend hosting | Render | Free tier, simple FastAPI/uvicorn support |
| Frontend hosting | Netlify | Free tier, drag-and-drop static deployment |

---

## API Contract

Single endpoint, per `technical-spec.md`:
POST /api/interview


**Start an interview:**
```json
{
  "sessionId": "abc-123",
  "candidate": { ...candidate.json shape... }
}
```

**Continue an interview:**
```json
{
  "sessionId": "abc-123",
  "message": "candidate's answer"
}
```

**Response (mid-interview):**
```json
{ "reply": "...", "done": false }
```

**Response (interview complete):**
```json
{
  "reply": "Interview completed.",
  "done": true,
  "feedback": {
    "summary": "...",
    "strengths": ["..."],
    "gaps": ["..."],
    "next": ["..."]
  }
}
```

---

## Setup (local)

```powershell
git clone https://github.com/divyadharshinik38-source/My-AI-Project.git
cd My-AI-Project
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

GROQ_API_KEY=your_groq_key_here

Get a free key at https://console.groq.com/keys

**Run the backend:**
```powershell
uvicorn app.main:app --reload --port 8000
```

**Run the frontend** (in a separate terminal):
```powershell
cd frontend
python -m http.server 5500
```
Then open `http://127.0.0.1:5500` in your browser. Update the
`API_BASE` constant near the top of `frontend/index.html` if you
want it to point at your local backend instead of the deployed one.

**Test the backend directly:**
```powershell
python -c "
import requests, json
candidates = json.load(open('data/candidates.json'))['candidates']
r = requests.post('http://127.0.0.1:8000/api/interview', json={'sessionId': 'test-1', 'candidate': candidates[0]})
print(r.status_code, r.json())
"
```

---

## Project structure
interview-agent/
├── app/
│ ├── main.py # FastAPI app, POST /api/interview
│ ├── models.py # Pydantic schemas matching the spec
│ ├── planner.py # picks curriculum days to probe
│ ├── llm.py # Groq wrapper: questions/followups/feedback
│ ├── session_store.py # in-memory interview state
│ └── interview_engine.py # the conversation state machine
├── frontend/
│ ├── index.html # single-file chat UI
│ └── candidates.json # candidate list for the dropdown
├── data/
│ ├── curriculum.json
│ └── candidates.json
├── AI_USAGE_LOG.md
├── PROMPTS.md
├── requirements.txt
└── README.md

---

## Known limitations

- **Sessions are in-memory only** — restarting the backend clears
  all active interviews. Acceptable per spec (no persistent accounts
  required), but worth noting for judges.
- **Free-tier cold starts** — first request after idle time on
  either Render or Netlify may take 30-60 seconds.
- **Follow-up quota can occasionally over-probe** on very short or
  repetitive answers, asking more follow-ups than a real interviewer
  might. Doesn't affect correctness, just interview length in edge
  cases.

## Future scope

- Persistent storage for interview history across sessions
- Difficulty calibration that escalates/simplifies based on running
  performance signal, not just per-topic quota
- Multi-candidate aggregate insights (e.g. "Day 9 is the most
  commonly struggled-with topic across the cohort")