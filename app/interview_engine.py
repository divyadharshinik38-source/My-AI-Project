"""
Interview engine -- the state machine driving the whole conversation.

Two entry points, called directly by main.py:

    start_interview(session_id, candidate_dict, curriculum)
        -> (reply: str, done: bool)

    continue_interview(session_id, message)
        -> (reply: str, done: bool, feedback: dict | None)

QUOTA GUARANTEE
----------------
The spec requires >= 8 questions across >= 4 curriculum days. The
planner already guarantees >= 4 distinct days. To guarantee >= 8
TOTAL questions regardless of how many days were planned, each topic
must produce at least `required_per_topic = ceil(8 / num_topics)`
questions (base question + follow-ups). We still ask Gemini's real
judgment for follow-ups first (for quality/relevance) -- we only
force a generic deepening question if quota isn't met AND Gemini
didn't think a follow-up was warranted.
"""

import math

from app.llm import generate_question, generate_followup, generate_feedback
from app.planner import build_interview_plan
from app.session_store import create_session, get_session, InterviewSession


def start_interview(session_id: str, candidate: dict, curriculum: dict) -> tuple[str, bool]:
    plan = build_interview_plan(candidate, curriculum)
    name = candidate["member"]["name"]

    session = create_session(session_id, name, plan)
    session.required_per_topic = math.ceil(8 / len(plan))
    session.questions_asked_this_topic = 1
    session.total_questions_asked = 1

    first_question = generate_question(session.current_topic)
    session.current_question = first_question

    reply = f"Welcome, {name}. Let's begin your interview.\n\n{first_question}"
    return reply, False


def continue_interview(session_id: str, message: str) -> tuple[str, bool, dict | None]:
    session = get_session(session_id)
    if session is None:
        # Defensive: an unknown/expired sessionId should never crash the API.
        return (
            "I couldn't find that interview session. Please start a new interview.",
            True,
            None,
        )

    # Record the answer to whatever we most recently asked.
    session.record_turn(session.current_question, message)

    # Decide: follow up on THIS answer, or move to the next topic?
    reply, done = _decide_next_step(session)

    if done:
        feedback = generate_feedback(session.transcript)
        session.done = True
        return reply, True, feedback

    return reply, False, None


def _decide_next_step(session: InterviewSession) -> tuple[str, bool]:
    under_quota = session.questions_asked_this_topic < session.required_per_topic
    can_still_followup = session.followups_used < session.max_followups_per_topic

    followup_question = None
    if can_still_followup:
        # Always ask Gemini's real opinion first -- this is what makes
        # follow-ups genuinely reference the candidate's actual answer,
        # not a generic "go deeper" prompt.
        followup_question = generate_followup(
            session.current_topic,
            session.current_question,
            session.transcript[-1]["answer"],
        )

    if followup_question is None and under_quota and can_still_followup:
        # Gemini judged the answer as solid, but we haven't hit the
        # per-topic quota yet -- ask a real question anyway, just not
        # a "gotcha" one, so the quota is met without feeling forced.
        followup_question = (
            f"That's a solid answer. Building on that -- what's one trade-off "
            f"or limitation you'd want to flag to a teammate about "
            f'"{session.current_topic["title"]}"?'
        )

    if followup_question is not None:
        session.followups_used += 1
        session.questions_asked_this_topic += 1
        session.total_questions_asked += 1
        session.current_question = followup_question
        return followup_question, False

    # No follow-up warranted/needed -- move to the next topic.
    session.advance_to_next_topic()

    if not session.has_more_topics():
        return "Interview completed.", True

    next_question = generate_question(session.current_topic)
    session.questions_asked_this_topic = 1
    session.total_questions_asked += 1
    session.current_question = next_question
    return next_question, False