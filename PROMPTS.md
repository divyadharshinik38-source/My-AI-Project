# PROMPTS.md

Real prompts used throughout building the AI Interview Agent, in
chronological order. This is a genuine record of the build process,
not a retroactive summary — see AI_USAGE_LOG.md for the narrative
version of the same work.

---

## 1. Problem selection

> "just tell me whether this project includes Minimum Requirements
> [pasted full spec]... choose the only winning problem statement and
> give the step by step guide for building this"

Result: Selected "The Interview Agent" over the ABTalks redesign and
Autonomous AI Creator problem statements, based on feasibility, AI
depth, and authenticity-review risk analysis.

---

## 2. Architecture and data modeling

> "Step 3 — Pydantic Models (matches the spec exactly) This is the
> contract-critical file — get it byte-exact with `technical-spec.md`."

Result: `app/models.py` — Candidate/Mission/Member/Signals schema
matching the real candidates.json shape, plus InterviewRequest/
InterviewResponse matching technical-spec.md's exact contract.

---

## 3. Interview planner

> "move to Step 4" [after providing curriculum.json and
> candidates.json]

Result: `app/planner.py` — scoring logic prioritizing failed
missions > skipped missions > struggled-but-passed > easy passes,
verified against real candidate records (Sarah Johnson, Isabella
Rossi) to confirm plans genuinely differ per candidate.

---

## 4. Gemini integration (initial)

> "move to Step 5 — the Gemini wrapper (`llm.py`)"

Result: `app/llm.py` initial version using google-generativeai,
later migrated (see entry 10).

---

## 5. Debugging: deprecated SDK + invalid key

> "[pasted] FutureWarning: All support for the `google.generativeai`
> package has ended... google.api_core.exceptions.InvalidArgument:
> 400 API key not valid."

Result: Migrated to the `google-genai` SDK, walked through
regenerating a valid API key from Google AI Studio.

---

## 6. Session state and interview engine

> "move to Step 7 — the interview engine (`interview_engine.py`)"

Discussion covered: how to guarantee the spec's minimum of 8
questions across 4+ days when the planner alone doesn't guarantee
question count — resulted in the `required_per_topic =
ceil(8/num_topics)` quota mechanism in `_decide_next_step()`.

---

## 7. API wiring

> "move to Step 8" [wiring engine into FastAPI's POST /api/interview]

Result: `app/main.py`, tested with FastAPI's TestClient (mocked LLM
calls) to confirm the request/response shape matched
technical-spec.md exactly before running against the real API.

---

## 8. Debugging: session reuse after completion

> "give me the remaining part of my section alone" [backend hardening
> task list, including fixing sessionId reuse after done=true]

Result: Added a completion guard in `app/main.py` returning
"This interview is already complete." instead of undefined behavior.

---

## 9. Debugging: Gemini rate limits (real, live issue)

> "[pasted] google.genai.errors.ServerError: 503 UNAVAILABLE...
> This model is currently experiencing high demand."

> "[pasted] google.genai.errors.ClientError: 429 RESOURCE_EXHAUSTED...
> Quota exceeded for metric: generate_content_free_tier_requests,
> limit: 5, model: gemini-3.6-flash"

> "[pasted] limit: 20, model: gemini-2.5-flash-lite... quotaId:
> GenerateRequestsPerDayPerProjectPerModel-FreeTier"

Diagnosis: Gemini free tier daily quota (20 requests/day on this
project) was exhausted mid-testing.

---

## 10. Provider migration decision

> "or should i use the groq api key free... just tell me what are the
> remaining part"

Result: Migrated `app/llm.py` from Gemini to Groq
(llama-3.3-70b-versatile), keeping identical function signatures
(generate_question, generate_followup, generate_feedback) so no
other module required changes. Verified with a real diagnostic call
before touching the full server.

---

## 11. Full end-to-end verification (backend)

> "[pasted full 18-turn test_full_flow.py output, real questions,
> real follow-ups referencing 'This is my test answer', real
> non-inflated feedback]"

Confirmed: 18 total question turns across all 6 planned topics
(exceeds the 8-question/4-day minimum), honest feedback correctly
identifying zero strengths when answers were genuinely empty,
session-completion guard working correctly.

---

## 12. Deployment (backend)

> "move to next" [after full local verification, requesting
> deployment steps]

Result: Pushed to GitHub (`divyadharshinik38-source/My-AI-Project`),
deployed to Render, environment variable (GROQ_API_KEY) configured
in Render's dashboard rather than committed to the repo. Verified
live: `POST https://interview-agent-ahj5.onrender.com/api/interview`
returns a real generated question with status 200.

---

## 13. Repository audit

> "check the complete project
> https://github.com/divyadharshinik38-source/My-AI-Project/tree/main"

Findings (via actually cloning the public repo, not just visual
inspection): leftover/duplicate files at repo root (`main.py`,
`candidates.json`, `curriculum.json`) from an earlier merge,
unrelated to the real working code; `.env` tracked in git (content
verified harmless via raw byte inspection, not a real leaked key);
broken `.gitignore` (wrong text encoding); README.md still showing
GitHub's auto-generated stub instead of the actual project README.

---

## 14. Repo cleanup

> "i dont understand this [explanation of duplicate main.py issue] ...
> give me the complete resdme.md"

Result: Removed duplicate root-level files via `git rm`, rewrote
`.gitignore` in plain text encoding, untracked `.env`, wrote and
pushed the complete `README.md` (architecture diagram, API contract,
setup instructions, known limitations).

---

## 15. Frontend build

> "lets do the frontend give me the entire codes, files in step by
> step"

Result: `frontend/index.html` — single-file HTML/CSS/JS chat
interface with a candidate dropdown, chat bubbles, and a feedback
card rendered on completion. Verified JS syntax and structural
elements before handoff.

---

## 16. Debugging: CORS and local file-serving

> "[screenshot] Error starting interview: Failed to fetch"

Diagnosis: two separate issues — (1) backend had no CORS middleware,
blocking cross-origin requests from the frontend; (2) opening the
HTML file directly via `file://` blocked `fetch()` calls to
`candidates.json` due to browser local-file security restrictions.

Result: Added `CORSMiddleware` to `app/main.py`; switched to serving
the frontend via `python -m http.server` instead of double-clicking
the file.

---

## 17. Debugging: verifying the CORS fix actually deployed

> "200 None" [result of an initial CORS test that returned no
> access-control-allow-origin header despite the fix being pushed]

Diagnosis: the test method itself was flawed (a plain `requests.get()`
call doesn't send an `Origin` header, so CORS headers are never
returned regardless of server config — not a real bug). Confirmed
the fix was actually live using `curl -i` with an explicit `Origin`
header, and cross-checked against Render's dashboard deploy log
showing the correct commit hash marked "Live."

---

## 18. Frontend deployment

> "https://cheerful-torte-554076.netlify.app"

Result: Frontend deployed to Netlify via drag-and-drop. Encountered
an unexpected password prompt on first load — root-caused to a
Netlify platform default (new sites created after July 28, 2026
default to "Private" visibility). Resolved via Project configuration
→ Visitor access → Project visibility → set to Public.

---

## 19. Final submission verification

> "just tell me does this project satisfies all these conditions
> [pasted full hackathon rules]"

Verification performed: re-cloned the public repo fresh to confirm
actual pushed state (not just local assumptions); checked real
commit timestamps via `git log --reverse` to compare repo creation
time against official kickoff time; confirmed AI_USAGE_LOG.md and
PROMPTS.md both present and pushed.

Finding: repo's first commit timestamp (2026-08-07 19:56:13 IST) was
approximately 4 minutes before the official kickoff (2026-08-07
20:00:00 IST) — flagged as a minor timing note or repo
initialization/setup, with all substantive development commits
following well after kickoff.

---

## 20. Submission mapping

> "Submission [pasted the actual submission form fields]"

Result: Confirmed which live URL to submit — the Netlify frontend
URL (`https://cheerful-torte-554076.netlify.app`), since the form
explicitly requested something a reviewer "can open" (Vercel,
Netlify, or similar), not the raw backend API endpoint.