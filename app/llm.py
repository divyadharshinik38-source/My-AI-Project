"""
Groq wrapper for the Interview Agent.

Same three responsibilities as before, same function signatures --
only the underlying provider changed (Gemini -> Groq) because Gemini's
free tier daily quota was too restrictive for hackathon-speed testing.

    1. generate_question()  -> ask about a planned curriculum topic
    2. generate_followup()  -> decide + generate a follow-up from an answer
    3. generate_feedback()  -> synthesize the final structured report

Groq's API is OpenAI-compatible, so this uses response_format json_object
for reliable structured output on the followup/feedback calls.
"""

import json
import os
import time

from groq import Groq, APIStatusError
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY not found. Add it to your .env file: "
        "GROQ_API_KEY=your_key_here"
    )

_client = Groq(api_key=API_KEY)

MODEL_NAME = "llama-3.3-70b-versatile"

INTERVIEWER_PERSONA = (
    "You are a calm, rigorous senior AI engineer conducting a real "
    "technical interview. You are direct but respectful, curious "
    "rather than tricky, and you never pad your questions with "
    "unnecessary preamble."
)


def _call_groq(prompt: str, json_mode: bool = False, retries: int = 3, base_delay: float = 3.0) -> str:
    """
    Wraps the actual API call with retry logic for transient errors
    (rate limits, server hiccups). Backs off longer on each retry.
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            kwargs = {
                "model": MODEL_NAME,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = _client.chat.completions.create(**kwargs)
            return response.choices[0].message.content.strip()
        except APIStatusError as e:
            last_error = e
            if attempt < retries:
                time.sleep(base_delay * attempt)
            continue
    raise last_error


def generate_question(topic: dict) -> str:
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
    try:
        return _call_groq(prompt)
    except APIStatusError:
        return (
            f"Let's talk about {topic['title']}. "
            f"Can you walk me through your understanding of it?"
        )


def generate_followup(topic: dict, question: str, answer: str) -> str | None:
    prompt = f"""{INTERVIEWER_PERSONA}

Topic: "{topic['title']}"
You asked: "{question}"
The candidate answered: "{answer}"

Evaluate this answer. Is it shallow, incomplete, or does it reveal a
misconception? If so, write ONE follow-up question that specifically
references a detail from their actual answer. If the answer is
already solid, don't force a follow-up.

Respond with ONLY this JSON object, nothing else:
{{"needs_followup": true or false, "followup_question": "..." or null}}
"""
    try:
        text = _call_groq(prompt, json_mode=True)
        data = json.loads(text)
        if data.get("needs_followup") and data.get("followup_question"):
            return data["followup_question"]
        return None
    except (json.JSONDecodeError, KeyError, APIStatusError):
        return None


def generate_feedback(transcript: list[dict]) -> dict:
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

Respond with ONLY this JSON object, nothing else:
{{
  "summary": "2-3 sentence overall assessment",
  "strengths": ["specific strength tied to a real answer", "..."],
  "gaps": ["specific gap tied to a real answer", "..."],
  "next": ["concrete, actionable next step", "..."]
}}
"""
    try:
        text = _call_groq(prompt, json_mode=True)
        return json.loads(text)
    except (json.JSONDecodeError, KeyError, APIStatusError):
        return {
            "summary": "Interview completed. Feedback generation encountered an issue.",
            "strengths": [],
            "gaps": [],
            "next": ["Review the transcript manually."],
        }