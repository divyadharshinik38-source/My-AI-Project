"""
FastAPI app -- exposes the single required endpoint:

    POST /api/interview

Behavior is decided by which field is present in the request body:
    - "candidate" present  -> this is turn 1, start a new interview
    - "message" present    -> this is turn 2+, continue the interview

This matches technical-spec.md exactly.
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException

from app.models import InterviewRequest, InterviewResponse, Feedback
from app.interview_engine import start_interview, continue_interview

app = FastAPI(title="AI Interview Agent")

# Curriculum is fixed reference data -- load it once at startup rather
# than on every request. Candidate data, by contrast, arrives IN the
# request body per the spec, so we never load candidates.json server-side.
CURRICULUM_PATH = Path(__file__).parent.parent / "data" / "curriculum.json"
with open(CURRICULUM_PATH) as f:
    CURRICULUM = json.load(f)


@app.get("/health")
def health():
    """Not required by the spec, but useful for your own sanity checks."""
    return {"status": "ok"}


@app.post("/api/interview", response_model=InterviewResponse)
def interview(req: InterviewRequest):
    if req.candidate is not None:
        # Turn 1: start a new interview session.
        candidate_dict = req.candidate.model_dump()
        reply, done = start_interview(req.sessionId, candidate_dict, CURRICULUM)
        return InterviewResponse(reply=reply, done=done)

    if req.message is not None:
        # Turn 2+: continue an existing interview session.
        reply, done, feedback_dict = continue_interview(req.sessionId, req.message)
        feedback = Feedback(**feedback_dict) if feedback_dict else None
        return InterviewResponse(reply=reply, done=done, feedback=feedback)

    # Neither "candidate" nor "message" was provided -- malformed request.
    raise HTTPException(
        status_code=400,
        detail="Request must include either 'candidate' (to start) or 'message' (to continue).",
    )