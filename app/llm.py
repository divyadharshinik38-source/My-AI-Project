"""
Gemini wrapper for the Interview Agent.

Three responsibilities:
    1. generate_question()  -> ask about a planned curriculum topic
    2. generate_followup()  -> decide + generate a follow-up from an answer
    3. generate_feedback()  -> synthesize the final structured report

All three ask Gemini to return STRICT JSON so we can parse reliably.
If parsing ever fails, each function has a safe fallback so the
interview never crashes mid-conversation.
"""

import json
import os
import re

from google import genai
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY not found. Add it to your .env file: "
        "GEMINI_API_KEY=your_key_here"
    )

_client = genai.Client(api_key=API_KEY)

# If this model name 404s for you, open Google AI Studio and copy
# whatever the current recommended flash model name is -- Google
# renames/rotates these periodically.
MODEL_NAME = "gemini-3.6-flash"

INTERVIEWER_PERSONA = (
    "You are a calm, rigorous senior AI engineer conducting a real "
    "technical interview. You are direct but respectful, curious "
    "rather than tricky, and you never pad your questions with "
    "unnecessary preamble."
)


def _extract_json(text: str) -> dict:
    """Gemini sometimes wraps JSON in ```json fences -- strip them."""
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def generate_question(topic: dict) -> str:
    """
    topic is one entry from planner.build_interview_plan(), e.g.
    {"day": 12, "title": "...", "objectives": [...], "reason": "..."}
    """
    prompt = f"""{INTERVIEWER_PERSONA}

The candidate completed Day {topic['day']}: "{topic['title']}"
(module: {topic['module']}).

Why we're probing this topic: {topic['reason']}.

Learning objectives for this day were:
{chr(10).join('- ' + o for o in topic['objectives'])}

Generate ONE interview question that tests genuine understanding of
this topic. If the candidate needed multiple attempts or skipped it,
probe a bit more fundamentally. If they passed easily, ask something
that requires deeper reasoning, not just recall.

Return ONLY the question text, no preamble, no quotes.
"""
    response = _client.models.generate_content(model=MODEL_NAME, contents=prompt)
    return response.text.strip()


def generate_followup(topic: dict, question: str, answer: str) -> str | None:
    """
    Returns a follow-up question string, or None if the answer was
    strong enough to move on.
    """
    prompt = f"""{INTERVIEWER_PERSONA}

Topic: "{topic['title']}"
You asked: "{question}"
The candidate answered: "{answer}"

Evaluate this answer. Is it shallow, incomplete, or does it reveal a
misconception? If so, write ONE follow-up question that specifically
references a detail from their actual answer. If the answer is
already solid, don't force a follow-up.

Respond with ONLY this JSON, nothing else:
{{"needs_followup": true/false, "followup_question": "..." or null}}
"""
    response = _client.models.generate_content(model=MODEL_NAME, contents=prompt)
    try:
        data = _extract_json(response.text)
        if data.get("needs_followup") and data.get("followup_question"):
            return data["followup_question"]
        return None
    except (json.JSONDecodeError, KeyError):
        # Safe fallback: if parsing fails, just move on rather than
        # crash the interview.
        return None


def generate_feedback(transcript: list[dict]) -> dict:
    """
    transcript: list of {"topic": str, "question": str, "answer": str}
    Returns a dict matching the Feedback model:
        {"summary": str, "strengths": [...], "gaps": [...], "next": [...]}
    """
    transcript_text = "\n\n".join(
        f"Topic: {t['topic']}\nQ: {t['question']}\nA: {t['answer']}"
        for t in transcript
    )

    prompt = f"""{INTERVIEWER_PERSONA}

Here is the complete interview transcript:

{transcript_text}

Generate structured, honest feedback. Do not inflate the assessment --
if the candidate was weak on something, say so plainly but
constructively. Base every point on something actually said in the
transcript above.

Respond with ONLY this JSON, nothing else:
{{
  "summary": "2-3 sentence overall assessment",
  "strengths": ["specific strength tied to a real answer", "..."],
  "gaps": ["specific gap tied to a real answer", "..."],
  "next": ["concrete, actionable next step", "..."]
}}
"""
    response = _client.models.generate_content(model=MODEL_NAME, contents=prompt)
    try:
        return _extract_json(response.text)
    except (json.JSONDecodeError, KeyError):
        # Fallback so the API never returns a broken response
        return {
            "summary": "Interview completed. Feedback generation encountered an issue.",
            "strengths": [],
            "gaps": [],
            "next": ["Review the transcript manually."],
        }