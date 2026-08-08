from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any
import google.generativeai as genai
import json, os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

app = FastAPI(title="AI Interview Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data files
with open("curriculum.json") as f:
    curriculum = json.load(f)

with open("candidates.json") as f:
    candidates_data = json.load(f)

curriculum_days = {d["day"]: d for d in curriculum["days"]}

# In-memory session store
sessions = {}

class InterviewRequest(BaseModel):
    sessionId: str
    candidate: Optional[Any] = None
    message: Optional[str] = None


@app.get("/")
def root():
    return {"message": "AI Interview Agent is running!", "team": "Divya Dharshini & Barkavi"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/candidates")
def get_candidates():
    result = []
    for c in candidates_data["candidates"]:
        member = c["member"]
        missions = c["missions"]
        failed  = [m["title"] for m in missions if not m.get("passed") and not m.get("skipped")]
        skipped = [m["title"] for m in missions if m.get("skipped")]
        passed  = [m["title"] for m in missions if m.get("passed")]
        result.append({
            "id":         member["id"],
            "name":       member["name"],
            "jobRole":    member["jobRole"],
            "experience": member.get("yearsExperience", 0),
            "education":  member.get("education", ""),
            "status":     member.get("status", ""),
            "completed":  passed,
            "failed":     failed,
            "skipped":    skipped,
            "signals":    c.get("signals", {}),
            "missions":   missions,
            "member":     member,
        })
    return result


@app.post("/api/interview")
async def interview(req: InterviewRequest):
    sid = req.sessionId

    # ── START INTERVIEW ──────────────────────────────────────────────────────
    if req.candidate is not None:
        candidate = req.candidate
        member    = candidate.get("member", candidate)
        missions  = candidate.get("missions", [])

        name       = member.get("name", "Candidate") if isinstance(member, dict) else "Candidate"
        job_role   = member.get("jobRole", "Engineer") if isinstance(member, dict) else "Engineer"
        experience = member.get("yearsExperience", 0) if isinstance(member, dict) else 0

        # Prioritise: failed → hard (3+ attempts) → skipped → easy-pass
        failed  = [m for m in missions if not m.get("passed") and not m.get("skipped")]
        hard    = [m for m in missions if m.get("passed") and m.get("attempts", 1) >= 3]
        skipped = [m for m in missions if m.get("skipped")]
        easy    = [m for m in missions if m.get("passed") and m.get("attempts", 1) < 3]

        ordered = (failed + hard + skipped + easy)[:10]

        topics = []
        seen_days = set()
        for m in ordered:
            day  = m.get("day", 0)
            info = curriculum_days.get(day, {})
            if info and day not in seen_days:
                seen_days.add(day)
                status = (
                    "FAILED"   if not m.get("passed") and not m.get("skipped") else
                    "SKIPPED"  if m.get("skipped") else
                    f"PASSED in {m.get('attempts',1)} attempt(s)"
                )
                topics.append({
                    "day":        day,
                    "title":      info.get("title", m.get("title", "")),
                    "objectives": info.get("objectives", [])[:3],
                    "status":     status,
                })

        system_prompt = f"""You are a professional AI technical interviewer conducting a personalized interview for someone who completed the 31-day AI Cohort program.

CANDIDATE:
  Name: {name}
  Role: {job_role}
  Experience: {experience} years

TOPICS TO COVER (ordered by priority — focus on weak areas first):
{json.dumps(topics, indent=2)}

YOUR RULES:
1. Conduct a natural, conversational multi-turn interview — do NOT list all questions at once.
2. Ask a MINIMUM of 8 questions covering at LEAST 4 different curriculum days.
3. After each candidate answer, give a brief acknowledgment (1 sentence) then ask a smart follow-up OR move to the next topic.
4. Adapt difficulty: probe deeper on failed/skipped topics; escalate on topics they aced quickly.
5. Track the questions internally; do NOT announce question numbers.
6. NEVER end the interview before 8 questions.
7. After 8+ questions, if all key topics are covered, wrap up naturally.

START NOW: Greet {name} warmly (2 sentences max) and ask your first technical question."""

        chat = model.start_chat(history=[])
        response = chat.send_message(system_prompt)
        reply = response.text

        sessions[sid] = {
            "chat":           chat,
            "history":        [{"role": "assistant", "content": reply}],
            "question_count": 1,
            "done":           False,
            "name":           name,
            "topics":         topics,
        }

        return {"reply": reply, "done": False}

    # ── CONVERSATION TURN ────────────────────────────────────────────────────
    elif req.message is not None:
        if sid not in sessions:
            raise HTTPException(status_code=404, detail="Session not found. Please start a new interview.")

        sess = sessions[sid]
        if sess["done"]:
            return {"reply": "This interview is already complete. Please start a new one.", "done": True}

        sess["history"].append({"role": "user", "content": req.message})
        sess["question_count"] += 1
        q = sess["question_count"]
        chat = sess["chat"]

        # After 8 questions → generate feedback and close
        if q >= 9:
            feedback_prompt = """The interview has now covered enough ground. 

Generate a JSON performance report. Return ONLY valid JSON, no markdown fences:
{
  "summary": "2-3 sentence holistic summary of the candidate's performance",
  "strengths": ["specific strength 1", "specific strength 2", "specific strength 3"],
  "gaps": ["specific gap 1", "specific gap 2"],
  "next": ["concrete next step 1", "concrete next step 2", "concrete next step 3"]
}

Be honest, specific, and encouraging. Base everything on this conversation."""

            fb_resp = chat.send_message(feedback_prompt)
            try:
                raw = fb_resp.text.strip()
                for fence in ["```json", "```"]:
                    if fence in raw:
                        raw = raw.split(fence)[1].split("```")[0].strip()
                        break
                feedback = json.loads(raw)
            except Exception:
                feedback = {
                    "summary":   f"{sess['name']} demonstrated a solid grasp of core AI engineering concepts from the cohort.",
                    "strengths": ["Good conceptual understanding", "Clear communication", "Practical awareness of RAG and agents"],
                    "gaps":      ["Some advanced topics need deeper hands-on work", "MCP and multi-agent orchestration could use more practice"],
                    "next":      ["Re-do the failed missions", "Build a mini end-to-end RAG project", "Explore LangChain agents with real tools"],
                }

            close_resp = chat.send_message(
                f"Thank {sess['name']} warmly and let them know the interview is complete. "
                "2-3 sentences max, keep it encouraging."
            )

            sess["done"] = True
            return {"reply": close_resp.text, "done": True, "feedback": feedback}

        # Continue interview
        remaining = max(0, 9 - q)
        cont_prompt = f"""Candidate just answered: "{req.message}"

Questions asked so far: {q}. Still need at least {remaining} more question(s).

1. Acknowledge their answer briefly (1 sentence — don't over-praise).
2. Ask a smart follow-up question OR naturally transition to the next priority topic.
3. Stay conversational — this should feel like a real interview, not a quiz.
4. Do NOT end the interview yet."""

        resp = chat.send_message(cont_prompt)
        reply = resp.text
        sess["history"].append({"role": "assistant", "content": reply})

        return {"reply": reply, "done": False}

    else:
        raise HTTPException(status_code=400, detail="Provide either 'candidate' (to start) or 'message' (to continue).")
